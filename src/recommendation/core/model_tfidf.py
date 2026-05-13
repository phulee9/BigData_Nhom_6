"""
Unified TF-IDF Document Recommender

Gộp role + skills thành 1 "document" duy nhất, dùng TF-IDF cosine
similarity trên toàn bộ document thay vì tách riêng role matching
và skill filtering.

Mỗi role = 1 document, nội dung = role_name + all_skills (giữ duplicates).
Query = target_role + user_skills → cosine similarity → extract missing skills.

Xem chi tiết tại: docs/unified_tfidf_plan.md
"""

from __future__ import annotations

import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import (
    SILVER_KAGGLE_FINAL_CLEAN,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
)
from src.recommendation.utils.text import (
    normalize_text_lower,
    parse_skills_lower,
)


# ──────────────────────────────────────────────
# Level weights mặc định
# ──────────────────────────────────────────────

# Trọng số bổ sung khi level = "senior":
# skills mang tính leadership / architecture được boost
DEFAULT_LEVEL_WEIGHTS = {
    "senior": {
        "leadership": 1.5,
        "team management": 1.5,
        "project management": 1.4,
        "system design": 1.4,
        "architecture": 1.4,
        "mentoring": 1.3,
        "strategic planning": 1.3,
        "stakeholder management": 1.3,
        "risk management": 1.2,
        "budgeting": 1.2,
    },
    "junior": {
        "communication": 1.2,
        "teamwork": 1.2,
        "problem solving": 1.2,
        "time management": 1.1,
    },
}


# ──────────────────────────────────────────────
# TFIDFRecommender — Unified Document Model
# ──────────────────────────────────────────────

class TFIDFRecommender:
    """
    Unified TF-IDF Recommender.

    Thay vì tách riêng role matching và skill filtering,
    gộp role + skills thành 1 document duy nhất.

    Workflow:
    1. Mỗi role trong dataset = 1 document
       Document text = "{role} {role} {skill1} {skill2} ..." (giữ duplicates)
    2. Fit TfidfVectorizer trên tất cả documents
    3. Query = "{target_role} {user_skill1} {user_skill2} ..."
    4. Cosine similarity → tìm roles tương tự nhất
    5. Extract skills từ matched roles, weighted by similarity
    6. Filter bỏ skills user đã có, apply level weights

    Ưu điểm:
    - Role + Skill match trong cùng 1 TF-IDF space
    - "data engineer" + "python" → ưu tiên DE roles dùng python
    - Cross-signal: "ML engineer" + "tensorflow" boost lẫn nhau
    - Chỉ 1 index duy nhất thay vì 3 indexes
    """

    # ── Config ──
    SIMILARITY_THRESHOLD = 0.1     # Ngưỡng sim tối thiểu (thấp vì doc dài)
    MAX_SIMILAR_ROLES = 10         # Số roles tương tự tối đa
    ROLE_NAME_REPEAT = 2           # Lặp role name bao nhiêu lần trong document

    def __init__(self, level_weights: dict | None = None):
        self.level_weights = level_weights or DEFAULT_LEVEL_WEIGHTS
        self._is_loaded = False

        # Unified TF-IDF components
        self._vectorizer: TfidfVectorizer | None = None
        self._doc_matrix = None                      # sparse (n_roles, vocab_size)
        self._doc_roles: list[str] = []              # role name cho mỗi doc
        self._doc_skill_counts: list[dict] = []      # {skill: count} cho mỗi doc
        self._doc_job_counts: list[int] = []         # tổng jobs cho mỗi doc

        # Backward compat: df_tfidf cho save/load matrix
        self.df_tfidf: pd.DataFrame | None = None

    # ────────────── Load data ──────────────

    def load_from_minio(self) -> None:
        """
        Đọc Silver Final Clean từ MinIO, build unified TF-IDF.
        """
        client = get_minio_client()

        print("[TF-IDF] Đọc Silver Final Clean từ MinIO...")
        silver_df = read_parquet_from_minio(
            client=client,
            object_name=SILVER_KAGGLE_FINAL_CLEAN,
        )
        print(f"[TF-IDF] Loaded Silver Final Clean: {len(silver_df)} rows")

        self._build_tfidf(silver_df)
        self._is_loaded = True

    def load_from_dataframe(self, df: pd.DataFrame) -> None:
        """
        Build unified TF-IDF từ DataFrame raw
        (chứa job_title_canonical, skills_canonical).
        """
        self._build_tfidf(df)
        self._is_loaded = True

    def load_matrix(self, matrix_df: pd.DataFrame) -> None:
        """
        Load từ df_tfidf đã lưu (parquet).
        Rebuild vectorizer + doc_matrix từ metadata.

        DataFrame cần có cột: role, skill, score, tf, idf, job_count
        """
        self.df_tfidf = matrix_df.copy()
        self._rebuild_from_df_tfidf()
        self._is_loaded = True

    # ────────────── Build ──────────────

    def _build_tfidf(self, df: pd.DataFrame) -> None:
        """
        Build unified TF-IDF document model.

        Bước 1: Chuẩn hóa role + parse skills
        Bước 2: Group by role → đếm skill frequency
        Bước 3: Tạo document text cho mỗi role
        Bước 4: Fit TfidfVectorizer → doc_matrix
        Bước 5: Build df_tfidf cho backward compat + save
        """
        print("[TF-IDF] Building Unified Document Model...")

        # ── Bước 1: Chuẩn hóa ──
        df = df[["job_title_canonical", "skills_canonical"]].copy()
        df["role"] = df["job_title_canonical"].apply(normalize_text_lower)
        df["skills_list"] = df["skills_canonical"].apply(parse_skills_lower)

        # Bỏ dòng không có role hoặc skills
        df = df[df["role"].str.len() > 0]
        df = df[df["skills_list"].apply(len) > 0]

        if df.empty:
            print("[TF-IDF] Không có dữ liệu hợp lệ.")
            self._set_empty()
            return

        # Lọc role rác (< 3 jobs)
        role_counts = df["role"].value_counts()
        valid_roles = role_counts[role_counts >= 3].index
        df = df[df["role"].isin(valid_roles)]

        if df.empty:
            print("[TF-IDF] Không có role nào đủ >= 3 jobs.")
            self._set_empty()
            return

        # ── Bước 2: Group by role → skill counts ──
        print("[TF-IDF] Grouping by role...")

        # Explode skills
        df_exploded = df[["role", "skills_list"]].explode("skills_list")
        df_exploded = df_exploded.rename(columns={"skills_list": "skill"})
        df_exploded = df_exploded[df_exploded["skill"].str.len() > 0]

        # Đếm skill frequency per role
        role_skill_counts = (
            df_exploded.groupby(["role", "skill"])
            .size()
            .reset_index(name="count")
        )

        # Đếm tổng jobs per role
        role_job_counts = df.groupby("role").size().to_dict()
        total_roles = len(role_job_counts)

        # ── Bước 3: Tạo documents ──
        print("[TF-IDF] Building document texts...")

        doc_roles = []
        doc_skill_counts = []
        doc_job_counts = []
        doc_texts = []

        for role_name, group in role_skill_counts.groupby("role"):
            skill_count_dict = dict(
                zip(group["skill"], group["count"])
            )
            job_count = role_job_counts.get(role_name, 1)

            # Document text = role lặp N lần + skills lặp theo frequency
            parts = [role_name] * self.ROLE_NAME_REPEAT
            for skill, count in skill_count_dict.items():
                parts.extend([skill] * count)

            doc_text = " ".join(parts)

            doc_roles.append(role_name)
            doc_skill_counts.append(skill_count_dict)
            doc_job_counts.append(job_count)
            doc_texts.append(doc_text)

        # ── Bước 4: Fit TF-IDF ──
        print(f"[TF-IDF] Fitting vectorizer on {len(doc_texts)} documents...")

        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),       # unigram + bigram cho "machine learning"
            sublinear_tf=True,        # 1 + log(tf) để tránh skill phổ biến dominate
            min_df=2,                 # bỏ term chỉ xuất hiện ở 1 doc
            max_df=0.95,              # bỏ term xuất hiện ở > 95% docs
            lowercase=True,
        )
        self._doc_matrix = self._vectorizer.fit_transform(doc_texts)
        self._doc_roles = doc_roles
        self._doc_skill_counts = doc_skill_counts
        self._doc_job_counts = doc_job_counts

        # ── Bước 5: Build df_tfidf (backward compat) ──
        self._build_df_tfidf(total_roles)

        n_roles = len(doc_roles)
        n_skills = self.df_tfidf["skill"].nunique() if self.df_tfidf is not None else 0
        vocab_size = len(self._vectorizer.vocabulary_)
        print(f"[TF-IDF] Unified Model built:")
        print(f"  Documents: {n_roles} roles")
        print(f"  Vocab size: {vocab_size} terms")
        print(f"  Unique skills: {n_skills}")
        print(f"  Total entries: {len(self.df_tfidf)}")

    def _build_df_tfidf(self, total_roles: int) -> None:
        """
        Build df_tfidf DataFrame từ doc metadata.
        Dùng cho backward compat (save/load parquet, get_role_skills).

        Tính TF-IDF score cho mỗi (role, skill):
        - TF = count / total_jobs_in_role
        - IDF = log((total_roles + 1) / (roles_with_skill + 1)) + 1
        - Score = TF * IDF
        """
        # Đếm số role chứa mỗi skill
        skill_role_count: dict[str, int] = defaultdict(int)
        for skill_counts in self._doc_skill_counts:
            for skill in skill_counts:
                skill_role_count[skill] += 1

        rows = []
        for i, role in enumerate(self._doc_roles):
            job_count_role = self._doc_job_counts[i]
            for skill, count in self._doc_skill_counts[i].items():
                tf = count / max(job_count_role, 1)
                n_roles_with = skill_role_count.get(skill, 1)
                idf = np.log((total_roles + 1) / (n_roles_with + 1)) + 1.0
                score = tf * idf

                rows.append({
                    "role": role,
                    "skill": skill,
                    "score": score,
                    "tf": tf,
                    "idf": idf,
                    "job_count": count,
                })

        self.df_tfidf = pd.DataFrame(rows)
        if not self.df_tfidf.empty:
            self.df_tfidf = self.df_tfidf.sort_values(
                by=["role", "score"],
                ascending=[True, False],
            ).reset_index(drop=True)

    def _rebuild_from_df_tfidf(self) -> None:
        """
        Rebuild vectorizer + doc_matrix từ df_tfidf đã load.
        Gọi khi load_matrix() từ parquet.
        """
        if self.df_tfidf is None or self.df_tfidf.empty:
            self._set_empty()
            return

        print("[TF-IDF] Rebuilding unified index from saved matrix...")

        # Reconstruct metadata
        doc_roles = []
        doc_skill_counts = []
        doc_job_counts = []
        doc_texts = []

        for role, group in self.df_tfidf.groupby("role"):
            skill_count_dict = dict(
                zip(group["skill"], group["job_count"])
            )
            total_jobs = int(group["job_count"].sum())

            # Rebuild document text
            parts = [role] * self.ROLE_NAME_REPEAT
            for skill, count in skill_count_dict.items():
                parts.extend([skill] * int(count))

            doc_roles.append(role)
            doc_skill_counts.append(skill_count_dict)
            doc_job_counts.append(total_jobs)
            doc_texts.append(" ".join(parts))

        # Refit vectorizer
        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=2,
            max_df=0.95,
            lowercase=True,
        )
        self._doc_matrix = self._vectorizer.fit_transform(doc_texts)
        self._doc_roles = doc_roles
        self._doc_skill_counts = doc_skill_counts
        self._doc_job_counts = doc_job_counts

        n_roles = len(doc_roles)
        vocab_size = len(self._vectorizer.vocabulary_)
        print(f"[TF-IDF] Rebuilt: {n_roles} roles, {vocab_size} vocab terms")

    def _set_empty(self) -> None:
        """Reset tất cả state về empty."""
        self.df_tfidf = pd.DataFrame(
            columns=["role", "skill", "score", "tf", "idf", "job_count"]
        )
        self._vectorizer = None
        self._doc_matrix = None
        self._doc_roles = []
        self._doc_skill_counts = []
        self._doc_job_counts = []

    # ────────────── Query ──────────────

    def query(
        self,
        target_role: str,
        user_skills: list[str],
        level: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Gợi ý skills còn thiếu cho target_role.

        Gộp target_role + user_skills thành 1 query string,
        dùng cosine similarity trên unified TF-IDF space.

        Parameters:
            target_role: Tên vị trí muốn ứng tuyển (vd: "data engineer")
            user_skills: Danh sách skills user đã có
            level: "senior" / "junior" / None – áp dụng level weight
            top_k: Số skills trả về

        Returns:
            List[dict] với keys: skill, score, tf, idf, job_count
        """
        if self._vectorizer is None or self._doc_matrix is None:
            return []

        # 1. Chuẩn hóa input
        target_role = normalize_text_lower(target_role)
        user_skills_normalized = [
            normalize_text_lower(s) for s in user_skills
            if normalize_text_lower(s)
        ]
        user_skills_set = set(user_skills_normalized)

        # 2. Tạo query string = role + skills gộp chung
        query_parts = [target_role] + user_skills_normalized
        query_text = " ".join(query_parts)

        # 3. Transform & cosine similarity
        query_vec = self._vectorizer.transform([query_text])
        sims = cosine_similarity(query_vec, self._doc_matrix).flatten()

        # 4. Lấy top-N documents có sim >= threshold
        top_indices = sims.argsort()[::-1][:self.MAX_SIMILAR_ROLES]
        matched_roles = []
        for idx in top_indices:
            sim = float(sims[idx])
            if sim >= self.SIMILARITY_THRESHOLD:
                matched_roles.append((idx, sim))

        if not matched_roles:
            return []

        # 5. Extract & aggregate skills từ matched roles
        skill_scores: dict[str, float] = defaultdict(float)
        skill_tf: dict[str, float] = {}
        skill_idf: dict[str, float] = {}
        skill_job_count: dict[str, int] = defaultdict(int)

        for doc_idx, sim_score in matched_roles:
            job_count_role = max(self._doc_job_counts[doc_idx], 1)
            skill_counts = self._doc_skill_counts[doc_idx]

            for skill, count in skill_counts.items():
                # Skip skills user đã có
                if skill in user_skills_set:
                    continue

                tf = count / job_count_role
                weighted_score = tf * sim_score

                skill_scores[skill] += weighted_score
                skill_job_count[skill] += count

                # Giữ max tf và idf cho output
                if skill not in skill_tf or tf > skill_tf[skill]:
                    skill_tf[skill] = tf

        if not skill_scores:
            return []

        # Lookup idf từ df_tfidf nếu có
        idf_map = {}
        if self.df_tfidf is not None and not self.df_tfidf.empty:
            idf_map = dict(
                self.df_tfidf.drop_duplicates("skill")
                .set_index("skill")["idf"]
            )

        # 6. Apply level weights
        level_weights = {}
        if level:
            level_key = level.lower().strip()
            level_weights = self.level_weights.get(level_key, {})

        # 7. Build result list
        results = []
        for skill, score in skill_scores.items():
            # Apply level weight
            if level_weights:
                score *= level_weights.get(skill, 1.0)

            results.append({
                "skill": skill,
                "score": score,
                "tf": skill_tf.get(skill, 0.0),
                "idf": idf_map.get(skill, 1.0),
                "job_count": skill_job_count[skill],
            })

        # 8. Sort & return top-K
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # ────────────── Tiện ích ──────────────

    def get_roles(self) -> list[str]:
        """Trả về danh sách tất cả roles trong model."""
        return sorted(self._doc_roles) if self._doc_roles else []

    def get_role_skills(
        self,
        role: str,
        top_k: int = 20,
    ) -> list[dict]:
        """
        Trả về top skills của 1 role (dùng cosine similarity,
        không filter user skills).
        """
        if self._vectorizer is None or self._doc_matrix is None:
            return []

        role = normalize_text_lower(role)

        # Dùng cosine similarity để tìm role tương tự nhất
        query_vec = self._vectorizer.transform([role])
        sims = cosine_similarity(query_vec, self._doc_matrix).flatten()

        top_idx = sims.argmax()
        if sims[top_idx] < self.SIMILARITY_THRESHOLD:
            return []

        # Lấy skills từ matched role
        skill_counts = self._doc_skill_counts[top_idx]
        job_count_role = max(self._doc_job_counts[top_idx], 1)

        # Lookup idf
        idf_map = {}
        if self.df_tfidf is not None and not self.df_tfidf.empty:
            idf_map = dict(
                self.df_tfidf.drop_duplicates("skill")
                .set_index("skill")["idf"]
            )

        results = []
        for skill, count in skill_counts.items():
            tf = count / job_count_role
            idf = idf_map.get(skill, 1.0)
            score = tf * idf

            results.append({
                "skill": skill,
                "score": score,
                "tf": tf,
                "idf": idf,
                "job_count": count,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def find_similar_roles(
        self,
        role: str,
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Public API: tìm roles tương tự trong model.

        Hữu ích cho debug hoặc UI autocomplete.

        Returns:
            List[(role_name, similarity_score)] sắp xếp giảm dần.
        """
        if self._vectorizer is None or self._doc_matrix is None:
            return []

        role = normalize_text_lower(role)
        query_vec = self._vectorizer.transform([role])
        sims = cosine_similarity(query_vec, self._doc_matrix).flatten()

        top_indices = sims.argsort()[::-1][:top_k]
        results = []
        for idx in top_indices:
            sim = float(sims[idx])
            if sim >= self.SIMILARITY_THRESHOLD:
                results.append((self._doc_roles[idx], sim))

        return results

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
