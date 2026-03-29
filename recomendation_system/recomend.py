import faiss
from recomendation_system.utils import clean
import pandas as pd
import os
import gdown
from collections import Counter

def get_project_root(start_path=None):
    if start_path is None:
        start_path = os.getcwd()

    current = start_path

    while True:
        if os.path.isdir(os.path.join(current, "dataset")):
            return current

        parent = os.path.dirname(current)

        if parent == current:
            raise RuntimeError("Không tìm thấy thư mục 'dataset'")

        current = parent


BASE_DIR = get_project_root()

path = os.path.join(BASE_DIR, 'dataset', '1.3m Linkedin Jobs & Skills (2024) - clean.csv')
index_path = os.path.join(BASE_DIR, 'dataset', 'jobs.index')

def load_data():
    if os.path.exists(path):
        df = pd.read_csv(path)
    else:
        file_id = "1QszBajfKa7kpPQthv3SyjtRwqy3dsCZm"
        url = f"https://drive.google.com/uc?id={file_id}"

        output = path
        gdown.download(url, output, quiet=False)
        df = pd.read_csv(path)
    
    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
    else:
        file_id = "17mcadL2sV2GZdjHfXSsZGHJpy1cbLpO"
        url = f"https://drive.google.com/uc?id={file_id}"

        output = index_path
        gdown.download(url, output, quiet=False)
        index = faiss.read_index(index_path)

    return df, index

def parse_skills(s):
    return set(s.lower().split(", "))


def recomend_skills(model, df, index, user_skills: str, top_k=200):
    user_skills_set = parse_skills(user_skills)
    missing = []
    query = model.encode([user_skills], normalize_embeddings=True)
    D, I = index.search(query, k=top_k)

    for idx in I[0]:
        job_skills = parse_skills(str(df.iloc[idx]["job_skills"]))
        missing += list(job_skills - user_skills_set)

    counter = Counter(missing)
    return counter.most_common(5) 