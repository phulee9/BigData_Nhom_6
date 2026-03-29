import os
import csv
from utils.check_job_exists import load_existing_links

def save_jobs_to_csv(jobs, filename="linkedin_jobs.csv"):
    file_exists = os.path.isfile(filename)
    existing_links = load_existing_links(filename)

    new_jobs = [job for job in jobs if job["link"] not in existing_links]

    if not new_jobs:
        print("Không có job mới")
        return

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "company",
                "location",
                "description",
                "link",
                "first_seen"
            ]
        )

        if not file_exists:
            writer.writeheader()

        for job in new_jobs:
            writer.writerow(job)

    print(f"Đã thêm {len(new_jobs)} job mới")