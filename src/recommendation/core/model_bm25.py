from __future__ import annotations
from collections import defaultdict
import pandas as pd
from rank_bm25 import BM25Plus

from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
)
from src.recommendation.utils.text import (
    normalize_text_lower,
    parse_skills_lower,
)

SILVER_KAGGLE_JOBS = "silver/kaggle/jobs_silver.parquet"
COL_TITLE = "title_core"
COL_SKILLS = "skills_normalized"
SCORE_THRESHOLD = 0.0
MAX_SIMILAR_ROLES = 10
ROLE_NAME_REPEAT = 2

class BM25PlusRecommender:
    def __init__(self):
        self._bm25: BM25Plus | None = None
        self._doc_roles: list[str] = []
        self._doc_skill_counts: list[dict] = []
        self._doc_job_counts: list[int] = []

    def load_from_minio(self, object_name: str | None = None) -> None:
        client = get_minio_client()

        target_path = object_name or SILVER_KAGGLE_JOBS
        print(f"[BM25+] Đọc Silver từ MinIO: {target_path}")
        silver_df = read_parquet_from_minio(
            client=client,
            object_name=target_path,
        )
        print(f"[BM25+] Loaded: {len(silver_df)} rows")
        print(f"[BM25+] Columns: {list(silver_df.columns)}")

        self._build_bm25(silver_df)

    def load_from_dataframe(self, df: pd.DataFrame) -> None:
        self._build_bm25(df)

    def _build_bm25(self, df: pd.DataFrame) -> None:
        print("[BM25+] Building Unified Document Model...")

        for col in [COL_TITLE, COL_SKILLS]:
            if col not in df.columns:
                raise KeyError(
                    f"[BM25+] Thiếu cột '{col}'. "
                    f"Các cột hiện có: {list(df.columns)}"
                )

        df = df[[COL_TITLE, COL_SKILLS]].copy()
        df["role"] = df[COL_TITLE].apply(normalize_text_lower)
        df["skills_list"] = df[COL_SKILLS].apply(parse_skills_lower)

        df = df[df["role"].str.len() > 0]
        df = df[df["skills_list"].apply(len) > 0]

        if df.empty:
            print("[BM25+] Không có dữ liệu hợp lệ.")
            return

        role_counts = df["role"].value_counts()
        valid_roles = role_counts[role_counts >= 3].index
        df = df[df["role"].isin(valid_roles)]

        if df.empty:
            print("[BM25+] Không có role nào đủ >= 3 jobs.")
            return

        df_exploded = df[["role", "skills_list"]].explode("skills_list")
        df_exploded = df_exploded.rename(columns={"skills_list": "skill"})
        df_exploded = df_exploded[df_exploded["skill"].str.len() > 0]

        role_skill_counts = (
            df_exploded.groupby(["role", "skill"])
            .size()
            .reset_index(name="job_count")
        )

        role_job_counts = df.groupby("role").size().to_dict()

        doc_roles = []
        doc_skill_counts = []
        doc_job_counts = []
        doc_tokens = []

        for role_name, group in role_skill_counts.groupby("role"):
            skill_count_dict = dict(zip(group["skill"], group["job_count"]))
            job_count = role_job_counts.get(role_name, 1)

            tokens = role_name.split() * ROLE_NAME_REPEAT
            for skill, count in skill_count_dict.items():
                tokens.extend(skill.split() * count)

            doc_roles.append(role_name)
            doc_skill_counts.append(skill_count_dict)
            doc_job_counts.append(job_count)
            doc_tokens.append(tokens)

        print(f"[BM25+] Fitting BM25Plus...")
        self._bm25 = BM25Plus(doc_tokens)
        self._doc_roles = doc_roles
        self._doc_skill_counts = doc_skill_counts
        self._doc_job_counts = doc_job_counts

        n_skills = len(set(s for sc in doc_skill_counts for s in sc))
        print(f"[BM25+] Done: {len(doc_roles)} roles, {n_skills} skills")

    def query(
        self,
        target_role: str,
        user_skills: list[str],
        top_k: int = 10,
    ) -> list[dict]:

        if self._bm25 is None:
            return []

        target_role = normalize_text_lower(target_role)
        user_skills_normalized = [
            normalize_text_lower(s) for s in user_skills
            if normalize_text_lower(s)
        ]
        user_skills_set = set(user_skills_normalized)

        query_tokens = target_role.split() + [
            token
            for skill in user_skills_normalized
            for token in skill.split()
        ]

        scores = self._bm25.get_scores(query_tokens)

        top_indices = scores.argsort()[::-1][:MAX_SIMILAR_ROLES]
        matched_roles = [
            (idx, float(scores[idx]))
            for idx in top_indices
            if float(scores[idx]) >= SCORE_THRESHOLD
        ]

        if not matched_roles:
            return []

        max_score = max(s for _, s in matched_roles)
        if max_score > 0:
            matched_roles = [
                (idx, s / max_score) for idx, s in matched_roles
            ]

        skill_scores: dict[str, float] = defaultdict(float)
        skill_job_count: dict[str, int] = defaultdict(int)

        for doc_idx, bm25_score in matched_roles:
            job_count_role = max(self._doc_job_counts[doc_idx], 1)
            for skill, count in self._doc_skill_counts[doc_idx].items():
                if skill in user_skills_set:
                    continue
                skill_scores[skill] += (count / job_count_role) * bm25_score
                skill_job_count[skill] += count

        if not skill_scores:
            return []

        results = [
            {
                "skill": skill,
                "recommend_score": score,
                "job_count": skill_job_count[skill],
            }
            for skill, score in skill_scores.items()
        ]
        results.sort(key=lambda x: x["recommend_score"], reverse=True)
        return results[:top_k]

    def get_roles(self) -> list[str]:
        return sorted(self._doc_roles) if self._doc_roles else []

    def get_role_skills(self, role: str, top_k: int = 20) -> list[dict]:
        if self._bm25 is None:
            return []

        role = normalize_text_lower(role)
        scores = self._bm25.get_scores(role.split())

        top_idx = scores.argmax()
        if scores[top_idx] < SCORE_THRESHOLD:
            return []

        skill_counts = self._doc_skill_counts[top_idx]
        job_count_role = max(self._doc_job_counts[top_idx], 1)

        results = [
            {
                "skill": skill,
                "recommend_score": count / job_count_role,
                "job_count": count,
            }
            for skill, count in skill_counts.items()
        ]
        results.sort(key=lambda x: x["recommend_score"], reverse=True)
        return results[:top_k]

    def find_similar_roles(self, role: str, top_k: int = 5) -> list[tuple[str, float]]:
        if self._bm25 is None:
            return []

        role = normalize_text_lower(role)
        scores = self._bm25.get_scores(role.split())

        top_indices = scores.argsort()[::-1][:top_k]
        return [
            (self._doc_roles[idx], float(scores[idx]))
            for idx in top_indices
            if float(scores[idx]) >= SCORE_THRESHOLD
        ]
