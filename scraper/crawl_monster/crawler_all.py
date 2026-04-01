"""
Monster.com.vn Combined Crawler
Crawl jobs and extract skills in one pass until reaching target count
Usage: python combined_crawler.py
"""

import asyncio
import json
import random
import sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def combined_crawl(
    output_file: str,
    target_jobs: int = 500,
    headless: bool = True
):
    """
    Combined crawler: fetch jobs and skills in single pass
    
    Args:
        output_file: Path to save JSON file with jobs and skills
        target_jobs: Maximum number of jobs to crawl (default: 500)
        headless: Run browser in headless mode (default: True)
    
    Returns:
        List of job objects with skills
    """
    jobs_with_skills = []
    seen_links = set()
    page_num = 1

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()

        try:
            while len(jobs_with_skills) < target_jobs:
                url = f"https://www.monster.com.vn/search/jobs-{page_num}"
                print(f"\n[Trang {page_num}] Đang cào từ: {url}")

                try:
                    await page.goto(url, wait_until="load", timeout=120000)
                except Exception as e:
                    print(f"[Trang {page_num}] Lỗi tải trang: {str(e)}")
                    break

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select(".jobCardWrapper")

                if not cards:
                    print(f"[Trang {page_num}] Không tìm thấy job cards. Dừng crawl.")
                    break

                print(f"[Trang {page_num}] Tìm thấy {len(cards)} job cards")

                for idx, card in enumerate(cards, 1):
                    if len(jobs_with_skills) >= target_jobs:
                        print(f"[Trang {page_num}] Đã đạt {target_jobs} jobs. Dừng.")
                        break

                    # Extract job info
                    title_el = card.select_one(".jobCardTitle")
                    company_el = card.select_one(".jobCardCompany")
                    location_el = card.select_one(".jobCardLocation")
                    experience_el = card.select_one(".jobCardExperience")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else ""
                    experience = experience_el.get_text(strip=True) if experience_el else ""

                    # Extract link
                    link = ""
                    for a in card.select("a"):
                        href = a.get("href", "")
                        if "/job/" in href and "autoApply" not in href:
                            link = href
                            break

                    # Skip duplicate links
                    if link and link in seen_links:
                        continue

                    if link:
                        seen_links.add(link)
                        link = urljoin("https://www.monster.com.vn", link)

                    job_data = {
                        "title": title,
                        "company": company,
                        "location": location,
                        "experience": experience,
                        "link": link,
                        "skills": [],
                    }

                    # Crawl skills if link exists
                    if link:
                        try:
                            print(f"  [{len(jobs_with_skills) + 1}/{target_jobs}] Cào skills từ: {link}")
                            skill_page = await context.new_page()

                            try:
                                # Goto with shorter timeout, don't wait for networkidle
                                await skill_page.goto(link, wait_until="domcontentloaded", timeout=60000)
                                
                                # Wait for skills section to appear (max 20s)
                                try:
                                    await skill_page.wait_for_selector("#skillSectionNew", timeout=20000)
                                except:
                                    # Skills section timeout, continue anyway
                                    pass
                                
                                skill_html = await skill_page.content()
                                skill_soup = BeautifulSoup(skill_html, "html.parser")

                                # Find skills section - text in p or a tags inside skillSectionNew
                                skill_section = skill_soup.select_one("#skillSectionNew")
                                if not skill_section:
                                    skills = []
                                else:
                                    # Select p and a tags inside bg-surface-primary-normal divs
                                    skill_elements = skill_section.select(".bg-surface-primary-normal p, .bg-surface-primary-normal a")
                                    skills = [
                                        elem.get_text(strip=True) 
                                        for elem in skill_elements 
                                        if elem.get_text(strip=True) 
                                        and "login" not in elem.get_text(strip=True).lower()
                                        and "check" not in elem.get_text(strip=True).lower()
                                    ]
                                
                                job_data["skills"] = skills
                                if not skills:
                                    print(f"    → Không tìm thấy skills")
                                else:
                                    print(f"    → Tìm thấy {len(skills)} skills: {', '.join(skills[:3])}{'...' if len(skills) > 3 else ''}")
                            except Exception as e:
                                print(f"    → Lỗi cào skills: {str(e)}")
                            finally:
                                await skill_page.close()

                        except Exception as e:
                            print(f"  Lỗi xử lý skills: {str(e)}")

                    jobs_with_skills.append(job_data)

                    # Save progress after each job
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(jobs_with_skills, f, ensure_ascii=False, indent=2)

                    # Random delay between job crawls
                    await asyncio.sleep(random.uniform(1.5, 2.5))

                page_num += 1

                # Delay between pages
                await asyncio.sleep(random.uniform(2, 3))

        finally:
            await context.close()
            await browser.close()

    return jobs_with_skills


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Monitor.com.vn Combined Crawler")
    parser.add_argument("--count", type=int, default=500, help="Số jobs cần cào (mặc định: 500)")
    parser.add_argument("--output", type=str, default="monster_jobs_with_skills.json", help="File output")
    parser.add_argument("--headless", action="store_true", help="Chạy browser ở chế độ headless (ẩn window)")
    
    args = parser.parse_args()
    headless = args.headless

    output_file = args.output

    print(f"\n{'=' * 70}")
    print(f"CRAWL JOB + SKILLS - COMBINED VERSION")
    print(f"{'=' * 70}")
    print(f"Mục tiêu: {args.count} jobs")
    print(f"File output: {output_file}")
    print(f"Mode: {'Headless' if headless else 'Visible (Browser hiển thị)'}")
    print(f"{'=' * 70}\n")

    try:
        jobs_with_skills = asyncio.run(combined_crawl(
            output_file=output_file,
            target_jobs=args.count,
            headless=headless
        ))

        print(f"\n{'=' * 70}")
        print(f"HOÀN THÀNH!")
        print(f"{'=' * 70}")
        print(f"Tổng jobs crawled: {len(jobs_with_skills)}")
        total_skills = sum(len(job.get("skills", [])) for job in jobs_with_skills)
        print(f"Tổng skills crawled: {total_skills}")
        print(f"Kết quả lưu tại: {output_file}")
        print(f"{'=' * 70}\n")

    except KeyboardInterrupt:
        print("\n\nCrawl bị dừng bởi người dùng")
        sys.exit(0)
    except Exception as e:
        print(f"\nLỗi: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
