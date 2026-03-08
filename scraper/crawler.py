import asyncio
from playwright.async_api import async_playwright
import os
from urllib.parse import quote
from dotenv import load_dotenv
import random
from utils.now_time import get_today
from utils.save_csv import save_jobs_to_csv

load_dotenv()

USERNAME = os.getenv("LINKEDIN_USERNAME")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")
URL = "https://www.linkedin.com/jobs/search"
PROFILE_PATH = "linkedin_profile"

async def login_linkedin(page):
    await page.goto("https://www.linkedin.com/login")
    await page.wait_for_timeout(random.choice([1000, 1500, 2000, 3000]))

    await page.fill("#username", USERNAME)
    await page.wait_for_timeout(random.choice([1000, 1500, 2000]))

    await page.fill("#password", PASSWORD)
    await page.wait_for_timeout(random.choice([1000, 1500]))

    await page.click("button[type=submit]")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(random.choice([1000, 1500, 2000, 3000]))

async def ensure_login(page):
    await page.goto("https://www.linkedin.com")

    # nếu redirect tới login thì mới login
    if "login" in page.url:
        print("Chưa login → tiến hành login")
        await login_linkedin(page)
    else:
        print("Đã login từ profile")

async def search_jobs(page, keyword, start=0):
    url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&start={start}"
    print("Search URL:", url)

    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(random.choice([1000,1500,2000]))

async def get_links(page):
    print("Lấy links...")
    container = await page.query_selector("#main > div > div.scaffold-layout__list-detail-inner.scaffold-layout__list-detail-inner--grow > div.scaffold-layout__list > div")
    for _ in range(10):
        await container.evaluate("el => el.scrollTop += 1000")
        await page.wait_for_timeout(1000)
    await page.wait_for_selector('div[data-job-id]')

    elements = await page.query_selector_all('div[data-job-id]')

    links = []
    is_exists = set()
 
    for el in elements:
        job_id = await el.get_attribute("data-job-id")
        link = f'https://www.linkedin.com/jobs/view/{job_id}'
        if job_id not in is_exists:
            is_exists.add(job_id)
            links.append(link)
    # with open(f'links_{query}.txt', 'w') as f:
    #     for link in links:
    #         f.write(link + '\n')
    return list(set(links))

async def get_job(page, link):
    print("Đang lấy thông tin job từ link:", link)
    await page.goto(link)
    container = page.locator('#workspace > div > div > div._181b0d94.f53383eb.e1d14876 > div > div > div > div._0d26244a.b902da86._4ce9449f._4d8e8f8c._5a0aee88.ea12a7a2.a2ac8e20 > div > div > div.e8b95380 > div > div._0d26244a.b902da86._4ce9449f._4d8e8f8c._5a0aee88.ea12a7a2._60353d7a > div.b902da86._744bf2ab._5ba7d009.c2660157.ea12a7a2.a2ac8e20').first
    company_name = await container.locator("div").locator("a").inner_text()
    job_title_container = container.locator("+ div")
    job_title = await job_title_container.inner_text()
    location_container = job_title_container.locator("+ div + p")
    # Gia Lâm, Hanoi, Vietnam · 1 tuần trước · 21 ứng viên
    location= await location_container.inner_text()
    location = location.split("·")[0].strip()

    job_container = page.locator('#workspace > div > div > div._181b0d94.f53383eb.e1d14876 > div > div > div > div._0d26244a.b902da86._4ce9449f._4d8e8f8c._5a0aee88.ea12a7a2.c69e5dea > div:nth-child(3) > div > div > div > div > div > p > span')

    job_description = await job_container.inner_text()

    return {
        "link": link,
        "title": job_title,
        "company": company_name,
        "location": location,
        "description": job_description,
        "first_seen": get_today()
    }

async def get_total_jobs(page):
    selector = "#main > div > div.scaffold-layout__list-detail-inner.scaffold-layout__list-detail-inner--grow > div.scaffold-layout__list > header > div.jobs-search-results-list__title-heading.truncate.jobs-search-results-list__text > div > small > span"
    await page.wait_for_selector(selector)
    total_jobs_text = await page.inner_text(selector)

    return int(total_jobs_text.split()[0][:-1].replace('.', ''))

async def get_all_links(page):
    total_jobs = await get_total_jobs(page)
    print("Tổng số jobs:", total_jobs)

    links = set()
    for start in range(0, total_jobs, 25):
        await search_jobs(page, quote('Công nghệ thông tin'), start)
        new_links = await get_links(page)
        print(f"Đã lấy {len(new_links)} links từ trang {start//25 + 1}")
        links.update(new_links)
        await page.wait_for_timeout(random.choice([1000, 1500, 2000]))

    return list(links)

async def scraper_linkedin():
    async with async_playwright() as p:

        context = await p.chromium.launch_persistent_context(
            PROFILE_PATH,
            headless=False
        )

        page = await context.new_page()
        await ensure_login(page)

        query = 'Công nghệ thông tin'
        query = quote(query)
        await search_jobs(page, query)

        jobs = []
        links = await get_all_links(page)
        for link in links:
            job = await get_job(page, link)
            await asyncio.sleep(random.uniform(1, 3))
            jobs.append(job)
        save_jobs_to_csv(jobs)

        await context.close()

asyncio.run(scraper_linkedin())