import csv
import os

def load_existing_links(filename="linkedin_jobs.csv"):
    if not os.path.exists(filename):
        return set()

    links = set()

    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            links.add(row["link"])

    return links