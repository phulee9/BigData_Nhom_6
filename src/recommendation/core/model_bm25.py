"""
Unified BM25Plus Document Recommender

Mỗi role = 1 document, nội dung = role_name + all_skills (giữ duplicates).
Query = target_role + user_skills → BM25Plus score → extract missing skills.

Lưu/load bằng pickle — không cần rebuild khi load.
"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
from rank_bm25 import BM25Plus

from src.config import SILVER_KAGGLE_FINAL_CLEAN
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
)
from src.recommendation.utils.text import (
    normalize_text_lower,
    parse_skills_lower,
)


class BM25PlusRecommender:
    """
    Unified BM25Plus Recommender.

    Workflow:
    1. Mỗi role = 1 document (tokens = role words + skill words)
    2. Fit BM25Plus trên tất cả documents
    3. Query = target_role + user_skills → BM25Plus score
    4. Extract missing skills từ matched roles
    """

    SCORE_THRESHOLD = 0.0
    MAX_SIMILAR_ROLES = 10
    ROLE_NAME_REPEAT = 2

    def __init__(self):
        self._bm25: BM25Plus | None = None
        self._doc_roles: list[str] = []
        self._doc_skill_counts: list[dict] = []
        self._doc_job_counts: list[int] = []

    # ────────────── Load ──────────────

    def load_from_minio(self) -> None:
        """Đọc Silver Final Clean từ MinIO, build BM25Plus."""
        client = get_minio_client()

        print("[BM25+] Đọc Silver Final Clean từ MinIO...")
        silver_df = read_parquet_from_minio(
            client=client,
            object_name=SILVER_KAGGLE_FINAL_CLEAN,
        )
        print(f"[BM25+] Loaded: {len(silver_df)} rows")

        self._build_bm25(silver_df)

    def load_from_dataframe(self, df: pd.DataFrame) -> None:
        """Build BM25Plus từ DataFrame (cần job_title_canonical, skills_canonical)."""
        self._build_bm25(df)

    # ────────────── Build ──────────────

    def _build_bm25(self, df: pd.DataFrame) -> None:
        """Build unified BM25Plus từ raw data."""
        print("[BM25+] Building Unified Document Model...")

        df = df[["job_title_canonical", "skills_canonical"]].copy()
        df["role"] = df["job_title_canonical"].apply(normalize_text_lower)
        df["skills_list"] = df["skills_canonical"].apply(parse_skills_lower)

        df = df[df["role"].str.len() > 0]
        df = df[df["skills_list"].apply(len) > 0]

        if df.empty:
            print("[BM25+] Không có dữ liệu hợp lệ.")
            return

        # Lọc role < 3 jobs
        role_counts = df["role"].value_counts()
        valid_roles = role_counts[role_counts >= 3].index
        df = df[df["role"].isin(valid_roles)]

        if df.empty:
            print("[BM25+] Không có role nào đủ >= 3 jobs.")
            return

        # Group by role → skill counts
        df_exploded = df[["role", "skills_list"]].explode("skills_list")
        df_exploded = df_exploded.rename(columns={"skills_list": "skill"})
        df_exploded = df_exploded[df_exploded["skill"].str.len() > 0]

        role_skill_counts = (
            df_exploded.groupby(["role", "skill"])
            .size()
            .reset_index(name="job_count")
        )

        role_job_counts = df.groupby("role").size().to_dict()

        # Build document tokens & fit BM25Plus
        doc_roles = []
        doc_skill_counts = []
        doc_job_counts = []
        doc_tokens = []

        for role_name, group in role_skill_counts.groupby("role"):
            skill_count_dict = dict(zip(group["skill"], group["job_count"]))
            job_count = role_job_counts.get(role_name, 1)

            tokens = role_name.split() * self.ROLE_NAME_REPEAT
            for skill, count in skill_count_dict.items():
                tokens.extend(skill.split() * count)

            doc_roles.append(role_name)
            doc_skill_counts.append(skill_count_dict)
            doc_job_counts.append(job_count)
            doc_tokens.append(tokens)

        print(f"[BM25+] Fitting BM25Plus on {len(doc_tokens)} documents...")
        self._bm25 = BM25Plus(doc_tokens)
        self._doc_roles = doc_roles
        self._doc_skill_counts = doc_skill_counts
        self._doc_job_counts = doc_job_counts

        n_skills = len(set(s for sc in doc_skill_counts for s in sc))
        print(f"[BM25+] Done: {len(doc_roles)} roles, {n_skills} skills")

    # ────────────── Query ──────────────

    def query(
        self,
        target_role: str,
        user_skills: list[str],
        top_k: int = 10,
    ) -> list[dict]:
        """
        Gợi ý skills còn thiếu cho target_role.

        Returns:
            List[dict] với keys: skill, recommend_score, job_count
        """
        if self._bm25 is None:
            return []

        target_role = normalize_text_lower(target_role)
        user_skills_normalized = [
            normalize_text_lower(s) for s in user_skills
            if normalize_text_lower(s)
        ]
        user_skills_set = set(user_skills_normalized)

        # Query tokens = role + skills
        query_tokens = target_role.split() + [
            token
            for skill in user_skills_normalized
            for token in skill.split()
        ]

        # BM25Plus scoring
        scores = self._bm25.get_scores(query_tokens)

        # Top matched roles
        top_indices = scores.argsort()[::-1][:self.MAX_SIMILAR_ROLES]
        matched_roles = [
            (idx, float(scores[idx]))
            for idx in top_indices
            if float(scores[idx]) >= self.SCORE_THRESHOLD
        ]

        if not matched_roles:
            return []

        # Normalize scores to [0, 1]
        max_score = max(s for _, s in matched_roles)
        if max_score > 0:
            matched_roles = [
                (idx, s / max_score) for idx, s in matched_roles
            ]

        # Extract missing skills
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

    # ────────────── Tiện ích ──────────────

    def get_roles(self) -> list[str]:
        """Trả về danh sách tất cả roles."""
        return sorted(self._doc_roles) if self._doc_roles else []

    def get_role_skills(self, role: str, top_k: int = 20) -> list[dict]:
        """Trả về top skills của 1 role."""
        if self._bm25 is None:
            return []

        role = normalize_text_lower(role)
        scores = self._bm25.get_scores(role.split())

        top_idx = scores.argmax()
        if scores[top_idx] < self.SCORE_THRESHOLD:
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
        """Tìm roles tương tự."""
        if self._bm25 is None:
            return []

        role = normalize_text_lower(role)
        scores = self._bm25.get_scores(role.split())

        top_indices = scores.argsort()[::-1][:top_k]
        return [
            (self._doc_roles[idx], float(scores[idx]))
            for idx in top_indices
            if float(scores[idx]) >= self.SCORE_THRESHOLD
        ]
