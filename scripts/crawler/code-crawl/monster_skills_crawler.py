import asyncio
import json
import random
import sys
import queue
import threading

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def extract_skills_from_html(html: str) -> list[str]:
    """Parse skills from job page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    skill_section = soup.select_one("#skillSectionNew")
    if not skill_section:
        return []

    skills = []
    skill_divs = skill_section.find_all(
        "div", class_=lambda x: x and "bg-surface-primary-normal" in x
    )

    for div in skill_divs:
        text = (
            next((p.get_text(strip=True) for p in div.find_all("p") if p.get_text(strip=True)), None)
            or next((a.get_text(strip=True) for a in div.find_all("a") if a.get_text(strip=True)), None)
            or (div.get_text(strip=True) if len(div.get_text(strip=True)) <= 100 else None)
        )
        if text:
            skills.append(text)

    return list(dict.fromkeys(skills))  # deduplicate, preserve order


async def crawl_job_skills(job_links: list, output_file: str) -> list:
    """Visit each job link and extract skills, saving progress after each job."""
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        try:
            for idx, job in enumerate(job_links, 1):
                link = job.get("link")
                print(f"[{idx}/{len(job_links)}] {link or '(no link)'}")

                if not link:
                    job["skills"] = []
                    results.append(job)
                    continue

                try:
                    await page.goto(link, wait_until="load", timeout=120_000)
                    try:
                        await page.wait_for_selector("#skillSectionNew", timeout=10_000)
                    except:
                        print("  -> ⚠️  #skillSectionNew not found or timed out")
                    await asyncio.sleep(1)

                    skills = extract_skills_from_html(await page.content())
                    job["skills"] = skills
                    print(f"  -> {len(skills)} skills: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}")

                except Exception as e:
                    print(f"  -> Error: {e}")
                    job["skills"] = []

                results.append(job)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"  -> Saved {len(results)}/{len(job_links)}")

                await asyncio.sleep(random.uniform(2, 4))

        finally:
            await context.close()
            await browser.close()

    return results


def run_in_thread(coro):
    """Run an async coroutine in a separate thread (avoids event loop conflicts)."""
    result_q = queue.Queue()

    def runner():
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        try:
            result_q.put(("ok", asyncio.run(coro)))
        except Exception as e:
            result_q.put(("error", e))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    status, payload = result_q.get()
    if status == "error":
        raise payload
    return payload


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python monster_skills_crawler_chunk.py <chunk_number>")
        sys.exit(1)

    chunk_num = int(sys.argv[1])
    input_file  = f"data/chunks/monster_jobs_chunk_{chunk_num}.json"
    output_file = f"data/chunks/monster_jobs_with_skills_chunk_{chunk_num}.json"

    print(f"\nLoading jobs from: {input_file}")
    try:
        with open(input_file, encoding="utf-8") as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print(f"File not found. Run split_jobs_into_chunks.py first.")
        sys.exit(1)

    valid_jobs = [j for j in jobs if j.get("link")]
    print(f"Found {len(valid_jobs)}/{len(jobs)} jobs with valid links\n")

    if not valid_jobs:
        print("No valid job links. Exiting.")
        sys.exit(1)

    print(f"{'='*60}\nCrawling chunk {chunk_num} ({len(valid_jobs)} jobs)\n{'='*60}\n")
    results = run_in_thread(crawl_job_skills(valid_jobs, output_file))

    total_skills = sum(len(j.get("skills", [])) for j in results)
    print(f"\n{'='*60}")
    print(f"Done! Crawled {len(results)} jobs, {total_skills} total skills.")
    print(f"Saved to: {output_file}\n{'='*60}")