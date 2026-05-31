
import asyncio
import json
import random
import sys
import queue
import threading
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def crawl_all_jobs(output_file: str):
    jobs = []
    seen_links = set()
    page_num = 1

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()

        try:
            while True:
                url = f"https://www.monster.com.vn/search/jobs-{page_num}"
                print(f"Dang crawl trang {page_num}: {url}")

                # Retry logic with exponential backoff
                retry_count = 0
                max_retries = 3
                page_loaded = False
                
                while retry_count < max_retries and not page_loaded:
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        page_loaded = True
                    except Exception as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"  ⚠️  Trang {page_num} lỗi, retry lần {retry_count}/{max_retries}...")
                            await asyncio.sleep(random.uniform(3, 5))
                        else:
                            print(f"  ❌ Trang {page_num} fail sau {max_retries} lần retry. Dung crawl.")
                            raise
                
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                cards = soup.select(".jobCardWrapper")
                if not cards:
                    print(f"Trang {page_num} khong con job card. Dung crawl.")
                    break

                print(f"Trang {page_num}: tim thay {len(cards)} job card")

                page_added = 0
                for card in cards:
                    title_el = card.select_one(".jobCardTitle")
                    company_el = card.select_one(".jobCardCompany")
                    location_el = card.select_one(".jobCardLocation")
                    experience_el = card.select_one(".jobCardExperience")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else ""
                    experience = experience_el.get_text(strip=True) if experience_el else ""

                    link = ""
                    for a in card.select("a"):
                        href = a.get("href", "")
                        if "/job/" in href and "autoApply" not in href:
                            link = href
                            break

                    if link and link in seen_links:
                        continue

                    if link:
                        seen_links.add(link)
                        link = urljoin("https://www.monster.com.vn", link)

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "experience": experience,
                        "link": link,
                    })
                    page_added += 1

                print(f"Trang {page_num}: them moi {page_added} jobs (khong trung link)")
                
                # Save data after each page
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(jobs, f, ensure_ascii=False, indent=2)
                print(f"Trang {page_num}: {len(jobs)} jobs da luu vao {output_file}")

                page_num += 1
                await asyncio.sleep(random.uniform(3, 6))
        finally:
            await context.close()
            await browser.close()

    return jobs


def run_async_in_thread(coro):
    result_queue = queue.Queue()

    def runner():
        try:
            if sys.platform.startswith("win"):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            result = asyncio.run(coro)
            result_queue.put(("ok", result))
        except Exception as exc:
            result_queue.put(("error", exc))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    status, payload = result_queue.get()
    if status == "error":
        raise payload
    return payload


if __name__ == "__main__":
    # Configuration
    output_file = "monster_jobs.json"

    # Run crawler
    print(f"\nBat dau crawl all jobs (crawl den khi het)")
    print("=" * 60)
    
    all_jobs = run_async_in_thread(crawl_all_jobs(output_file=output_file))

    # Final results
    print("=" * 60)
    print(f"Hoan thanh! Tong so jobs da crawl: {len(all_jobs)}")
    print(f"Ket qua da luu vao file: {output_file}")
    print("\nDang chay xong!")
