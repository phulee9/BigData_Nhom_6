import asyncio
import json
import random
import sys
import queue
import threading
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

BATCH_SIZE = 1000


def extract_skills_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    skill_section = soup.select_one("#skillSectionNew")
    if not skill_section:
        return []

    skills = []

    skill_divs = skill_section.find_all(
        "div",
        class_=lambda x: x and "bg-surface-primary-normal" in x
    )

    for div in skill_divs:
        text = (
            next(
                (
                    p.get_text(strip=True)
                    for p in div.find_all("p")
                    if p.get_text(strip=True)
                ),
                None
            )
            or next(
                (
                    a.get_text(strip=True)
                    for a in div.find_all("a")
                    if a.get_text(strip=True)
                ),
                None
            )
            or (
                div.get_text(strip=True)
                if len(div.get_text(strip=True)) <= 100
                else None
            )
        )

        if text:
            skills.append(text)

    return list(dict.fromkeys(skills))


def load_jobs(input_file: str) -> list[dict]:
    with open(input_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    if not isinstance(jobs, list):
        raise ValueError("Input file phải là JSON list jobs.")

    return jobs


def get_batch_jobs(jobs: list[dict], batch_number: int, batch_size: int = BATCH_SIZE) -> list[dict]:
    valid_jobs = [job for job in jobs if job.get("link")]

    start = (batch_number - 1) * batch_size
    end = start + batch_size

    return valid_jobs[start:end]


async def crawl_job_skills(job_links: list[dict], output_file: str) -> list[dict]:
    results = []

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        try:
            for idx, job in enumerate(job_links, 1):
                link = job.get("link")
                print(f"[{idx}/{len(job_links)}] {link}")

                try:
                    await page.goto(link, wait_until="load", timeout=120_000)

                    try:
                        await page.wait_for_selector("#skillSectionNew", timeout=10_000)
                    except Exception:
                        print("  -> Không tìm thấy #skillSectionNew hoặc bị timeout")

                    await asyncio.sleep(1)

                    html = await page.content()
                    skills = extract_skills_from_html(html)

                    job["skills"] = skills

                    print(
                        f"  -> {len(skills)} skills: "
                        f"{', '.join(skills[:5])}"
                        f"{'...' if len(skills) > 5 else ''}"
                    )

                except Exception as e:
                    print(f"  -> Lỗi khi crawl skills: {e}")
                    job["skills"] = []

                results.append(job)

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

                print(f"  -> Đã lưu {len(results)}/{len(job_links)} jobs")

                await asyncio.sleep(random.uniform(2, 4))

        finally:
            await context.close()
            await browser.close()

    return results


def run_in_thread(coro):
    result_q = queue.Queue()

    def runner():
        try:
            if sys.platform.startswith("win"):
                asyncio.set_event_loop_policy(
                    asyncio.WindowsProactorEventLoopPolicy()
                )

            result = asyncio.run(coro)
            result_q.put(("ok", result))

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
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python monster_skills_crawler_batch.py <input_jobs_json> <batch_number>")
        print()
        print("Example:")
        print("  python monster_skills_crawler_batch.py monster_jobs.json 1")
        print("  python monster_skills_crawler_batch.py monster_jobs.json 2")
        sys.exit(1)

    input_file = sys.argv[1]
    batch_number = int(sys.argv[2])

    jobs = load_jobs(input_file)
    valid_jobs = [job for job in jobs if job.get("link")]

    batch_jobs = get_batch_jobs(
        jobs=jobs,
        batch_number=batch_number,
        batch_size=BATCH_SIZE
    )

    if not batch_jobs:
        print(f"Không có job nào trong batch {batch_number}.")
        print(f"Tổng số job có link hợp lệ: {len(valid_jobs)}")
        sys.exit(0)

    output_file = f"data/skills_batches/monster_jobs_with_skills_batch_{batch_number}.json"

    print("=" * 60)
    print(f"Input file: {input_file}")
    print(f"Tổng số jobs: {len(jobs)}")
    print(f"Số jobs có link hợp lệ: {len(valid_jobs)}")
    print(f"Batch hiện tại: {batch_number}")
    print(f"Số jobs crawl trong batch này: {len(batch_jobs)}")
    print(f"Output file: {output_file}")
    print("=" * 60)

    results = run_in_thread(
        crawl_job_skills(
            job_links=batch_jobs,
            output_file=output_file
        )
    )

    total_skills = sum(len(job.get("skills", [])) for job in results)

    print("=" * 60)
    print(f"Hoàn thành batch {batch_number}")
    print(f"Đã crawl: {len(results)} jobs")
    print(f"Tổng số skills lấy được: {total_skills}")
    print(f"Kết quả lưu tại: {output_file}")
    print("=" * 60)