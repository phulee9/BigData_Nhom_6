import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    EMBEDDING_MODEL,
    GOLD_KAGGLE_BM25_MODEL,
)
from src.storage.minio_client import (
    get_minio_client,
    download_pickle,
)
from src.recommendation.core.model_bm25 import BM25PlusRecommender
from src.recommendation.core.hybrid_rrf import reciprocal_rank_fusion
from src.recommendation.core.recommend import (
    SOURCE_TOP_K,
    build_query_texts,
    encode_query,
    collect_candidates_from_source,
    build_candidate_rows,
    limit_candidates_by_source,
    recommend_missing_skills,
    parse_skills,
    load_default_runtime_indexes,
)
from src.recommendation.core.recommend_job import (
    load_crawler_runtime,
    recommend_jobs_by_faiss,
)
from src.recommendation.cv.cv_extractor import extract_cv_file


load_dotenv()


# =========================================================
# Config
# =========================================================

TOP_SKILLS = 10
TOP_JOBS = 10
KAGGLE_TOP_K = 300
CRAWLER_TOP_K = 50

POWER_BI_URL = "https://app.powerbi.com/reportEmbed?reportId=0b985b96-9184-406d-a4c5-469eba46ecf0&autoAuth=true&ctid=e7572e92-7aee-4713-a3c4-ba64888ad45f"


# =========================================================
# Page setup
# =========================================================

st.set_page_config(
    page_title="Career Recommendation",
    page_icon=None,
    layout="wide",
)

st.markdown(
    """
    <link
      href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
      rel="stylesheet"
    >
    <style>
        /* ====================================================
           ROOT TOKENS
        ==================================================== */
        :root {
            --bg-base:       #070b14;
            --bg-surface:    #0d1424;
            --bg-elevated:   #121c30;
            --bg-hover:      #172135;

            --border-subtle: #1a2640;
            --border-mid:    #223050;
            --border-accent: #3a4d7a;

            --accent-primary: #6c8cf5;
            --accent-glow:    rgba(108, 140, 245, 0.18);
            --accent-green:   #34d399;
            --accent-green-bg: rgba(52, 211, 153, 0.08);
            --accent-amber:   #fbbf24;
            --accent-rose:    #f87171;

            --text-primary:   #e8edf8;
            --text-secondary: #8496b8;
            --text-muted:     #3f5173;
            --text-faint:     #263347;

            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
        }

        /* ====================================================
           GLOBAL RESET
        ==================================================== */
        html, body, [class*="css"] {
            font-family: 'Sora', sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        .stApp {
            background-color: var(--bg-base) !important;
        }

        /* Subtle grid texture overlay */
        .stApp::before {
            content: '';
            position: fixed;
            inset: 0;
            background-image:
                linear-gradient(var(--border-subtle) 1px, transparent 1px),
                linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px);
            background-size: 48px 48px;
            opacity: 0.3;
            pointer-events: none;
            z-index: 0;
        }

        /* ====================================================
           SIDEBAR
        ==================================================== */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1120 0%, #0d1628 100%) !important;
            border-right: 1px solid var(--border-subtle) !important;
        }

        section[data-testid="stSidebar"] > div {
            padding: 1.6rem 1.2rem !important;
        }

        /* Sidebar labels */
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stMarkdown p {
            font-family: 'Sora', sans-serif !important;
            font-size: 11.5px !important;
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
            letter-spacing: 0.2px;
        }

        /* Sidebar section heading */
        section[data-testid="stSidebar"] h3 {
            font-family: 'Sora', sans-serif !important;
            font-size: 9.5px !important;
            font-weight: 700 !important;
            color: var(--text-muted) !important;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 18px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-subtle);
        }

        /* Inputs */
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {
            font-family: 'Sora', sans-serif !important;
            font-size: 13px !important;
            background-color: var(--bg-elevated) !important;
            border: 1px solid var(--border-mid) !important;
            border-radius: var(--radius-md) !important;
            color: var(--text-primary) !important;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        section[data-testid="stSidebar"] input:focus,
        section[data-testid="stSidebar"] textarea:focus {
            border-color: var(--accent-primary) !important;
            box-shadow: 0 0 0 3px var(--accent-glow) !important;
            outline: none;
        }

        /* ====================================================
           BUTTONS
        ==================================================== */
        .stButton > button[kind="primary"] {
            font-family: 'Sora', sans-serif !important;
            font-size: 12.5px !important;
            font-weight: 600 !important;
            letter-spacing: 0.3px;
            background: linear-gradient(135deg, #4f6de0 0%, #7c5cc4 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: var(--radius-md) !important;
            padding: 10px 22px !important;
            transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s !important;
            box-shadow: 0 4px 18px rgba(99, 102, 241, 0.25) !important;
        }

        .stButton > button[kind="primary"]:hover {
            opacity: 0.9 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 24px rgba(99, 102, 241, 0.38) !important;
        }

        .stButton > button[kind="primary"]:active {
            transform: translateY(0) !important;
        }

        .stButton > button {
            font-family: 'Sora', sans-serif !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            border-radius: var(--radius-md) !important;
            border: 1px solid var(--border-mid) !important;
            background-color: var(--bg-elevated) !important;
            color: var(--text-secondary) !important;
            transition: border-color 0.2s, color 0.2s !important;
        }

        .stButton > button:hover {
            border-color: var(--accent-primary) !important;
            color: var(--text-primary) !important;
        }

        /* ====================================================
           MAIN LAYOUT
        ==================================================== */
        .block-container {
            padding: 2.2rem 2.8rem !important;
            max-width: 1300px;
            position: relative;
            z-index: 1;
        }

        /* ====================================================
           HEADER BLOCK
        ==================================================== */
        .app-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            margin-bottom: 28px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-subtle);
        }

        .page-eyebrow {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            font-weight: 500;
            color: var(--accent-primary);
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 6px;
            opacity: 0.8;
        }

        .page-title {
            font-family: 'Sora', sans-serif;
            font-size: 26px;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.6px;
            line-height: 1.15;
            margin: 0;
        }

        .page-title span {
            background: linear-gradient(90deg, #6c8cf5, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .page-sub {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10.5px;
            color: var(--text-muted);
            margin-top: 6px;
        }

        .status-dot {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: 'Sora', sans-serif;
            font-size: 11px;
            color: var(--accent-green);
            font-weight: 500;
        }

        .status-dot::before {
            content: '';
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--accent-green);
            box-shadow: 0 0 6px var(--accent-green);
        }

        /* ====================================================
           METRIC CARDS
        ==================================================== */
        .metric-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-bottom: 24px;
        }

        .metric-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 16px 20px;
            position: relative;
            overflow: hidden;
            transition: border-color 0.25s;
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, #4f6de0, #7c5cc4, transparent);
            opacity: 0.6;
        }

        .metric-card:hover {
            border-color: var(--border-accent);
        }

        .metric-lbl {
            font-family: 'Sora', sans-serif;
            font-size: 9.5px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: var(--text-muted);
            margin-bottom: 8px;
        }

        .metric-val {
            font-family: 'JetBrains Mono', monospace;
            font-size: 28px;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1;
        }

        .metric-val-text {
            font-family: 'Sora', sans-serif;
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.3;
        }

        .metric-icon {
            position: absolute;
            bottom: 14px;
            right: 16px;
            font-size: 22px;
            opacity: 0.08;
        }

        /* ====================================================
           SECTION LABELS
        ==================================================== */
        .section-title {
            font-family: 'Sora', sans-serif;
            font-size: 9.5px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1.3px;
            margin-bottom: 4px;
        }

        .section-note {
            font-family: 'Sora', sans-serif;
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 14px;
            margin-top: 4px;
        }

        /* ====================================================
           RESULT CARDS
        ==================================================== */
        .result-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 14px 18px;
            display: flex;
            align-items: flex-start;
            gap: 16px;
            margin-bottom: 8px;
            transition: border-color 0.2s, background 0.2s, transform 0.15s;
        }

        .result-card:hover {
            border-color: var(--border-accent);
            background: var(--bg-hover);
            transform: translateX(3px);
        }

        .result-num {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 500;
            color: var(--text-faint);
            min-width: 24px;
            padding-top: 3px;
        }

        .result-body { flex: 1; }

        .result-name {
            font-family: 'Sora', sans-serif;
            font-size: 14.5px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
            letter-spacing: -0.1px;
        }

        .result-meta {
            font-family: 'Sora', sans-serif;
            font-size: 11.5px;
            color: var(--text-muted);
            line-height: 1.7;
        }

        .result-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 6px;
        }

        /* Score badges */
        .score-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10.5px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
            background: var(--accent-green-bg);
            color: var(--accent-green);
            border: 1px solid rgba(52, 211, 153, 0.25);
            letter-spacing: 0.3px;
        }

        .score-badge-blue {
            background: rgba(108, 140, 245, 0.08);
            color: var(--accent-primary);
            border: 1px solid rgba(108, 140, 245, 0.2);
        }

        /* Rank pills */
        .rank-pill {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 5px;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
        }

        .job-link {
            font-family: 'Sora', sans-serif;
            font-size: 11.5px;
            font-weight: 500;
            color: var(--accent-primary);
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.2s;
            padding-bottom: 1px;
        }

        .job-link:hover {
            border-color: var(--accent-primary);
        }

        /* ====================================================
           DIVIDER
        ==================================================== */
        .divider {
            height: 1px;
            background: var(--border-subtle);
            margin: 22px 0;
        }

        /* ====================================================
           TABS
        ==================================================== */
        .stTabs [data-baseweb="tab-list"] {
            background: transparent !important;
            border-bottom: 1px solid var(--border-subtle) !important;
            gap: 0 !important;
        }

        .stTabs [data-baseweb="tab"] {
            font-family: 'Sora', sans-serif !important;
            font-size: 12.5px !important;
            font-weight: 500 !important;
            color: var(--text-muted) !important;
            background: transparent !important;
            border: none !important;
            padding: 10px 20px !important;
            border-bottom: 2px solid transparent !important;
            letter-spacing: 0.1px;
            transition: color 0.2s !important;
        }

        .stTabs [aria-selected="true"] {
            font-weight: 600 !important;
            color: var(--text-primary) !important;
            border-bottom: 2px solid var(--accent-primary) !important;
        }

        .stTabs [data-baseweb="tab-highlight"] { display: none !important; }

        /* ====================================================
           ALERTS
        ==================================================== */
        .stAlert {
            font-family: 'Sora', sans-serif !important;
            font-size: 12.5px !important;
            border-radius: var(--radius-md) !important;
            background-color: var(--bg-surface) !important;
            color: var(--text-secondary) !important;
            border: 1px solid var(--border-mid) !important;
        }

        /* ====================================================
           RADIO
        ==================================================== */
        .stRadio > div {
            flex-direction: row !important;
            gap: 8px !important;
        }

        .stRadio label {
            background: var(--bg-elevated) !important;
            border: 1px solid var(--border-mid) !important;
            border-radius: var(--radius-sm) !important;
            padding: 6px 14px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
            transition: all 0.2s !important;
            cursor: pointer;
        }

        .stRadio label:hover {
            border-color: var(--accent-primary) !important;
            color: var(--text-primary) !important;
        }

        /* ====================================================
           FILE UPLOADER
        ==================================================== */
        [data-testid="stFileUploader"] {
            background: var(--bg-elevated) !important;
            border: 1px dashed var(--border-accent) !important;
            border-radius: var(--radius-md) !important;
        }

        /* ====================================================
           SPINNER
        ==================================================== */
        .stSpinner > div {
            font-family: 'Sora', sans-serif !important;
            font-size: 13px !important;
            color: var(--text-muted) !important;
        }

        /* ====================================================
           POWER BI WRAPPER
        ==================================================== */
        .pbi-wrap {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            overflow: hidden;
        }

        .pbi-empty {
            height: 300px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .pbi-empty-icon {
            font-size: 32px;
            opacity: 0.15;
        }

        .pbi-empty-text {
            font-family: 'Sora', sans-serif;
            font-size: 12px;
            color: var(--text-faint);
            text-align: center;
        }

        .pbi-empty-code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: var(--accent-primary);
            opacity: 0.7;
        }

        /* ====================================================
           MISC
        ==================================================== */
        #MainMenu, footer, header { visibility: hidden; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
            background: var(--border-accent);
            border-radius: 4px;
        }

        /* Sidebar logo/brand area */
        .brand-mark {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 22px;
            padding-bottom: 18px;
            border-bottom: 1px solid var(--border-subtle);
        }

        .brand-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: linear-gradient(135deg, #4f6de0, #7c5cc4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 15px;
        }

        .brand-name {
            font-family: 'Sora', sans-serif;
            font-size: 13px;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.2px;
        }

        .brand-version {
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            color: var(--text-muted);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Load resources
# =========================================================

@st.cache_resource(show_spinner=False)
def load_skill_resources():
    client = get_minio_client()
    bm25_recommender: BM25PlusRecommender = download_pickle(
        client=client,
        object_name=GOLD_KAGGLE_BM25_MODEL,
    )
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    runtime_indexes = load_default_runtime_indexes()
    return bm25_recommender, embedding_model, runtime_indexes


@st.cache_resource(show_spinner=False)
def load_job_resources():
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    crawler_runtime = load_crawler_runtime()
    return embedding_model, crawler_runtime


# =========================================================
# Recommendation functions
# =========================================================

def get_embedding_missing_skills(model, runtime_indexes, job_title, user_skills):
    query_texts = build_query_texts(job_title=job_title, skills=user_skills)
    query_embeddings = {
        "title_text": encode_query(model=model, text=query_texts["title_text"]),
        "skills_text": encode_query(model=model, text=query_texts["skills_text"]),
    }
    source_top_k = {"kaggle": KAGGLE_TOP_K, "crawler": CRAWLER_TOP_K}
    all_candidates = {}
    for runtime in runtime_indexes:
        source_name = runtime.source_name
        target_top_k = source_top_k.get(source_name, SOURCE_TOP_K.get(source_name, 100))
        source_candidates = collect_candidates_from_source(
            runtime_index=runtime,
            query_embeddings=query_embeddings,
            top_k_each_index=target_top_k * 2,
        )
        all_candidates.update(source_candidates)
    all_jobs_df = build_candidate_rows(
        candidates=all_candidates,
        runtime_indexes=runtime_indexes,
        user_job_title=job_title,
        user_skills=user_skills,
    )
    if all_jobs_df.empty:
        return pd.DataFrame()
    rerank_pool_df = limit_candidates_by_source(
        candidates_df=all_jobs_df, source_limits=source_top_k
    )
    return recommend_missing_skills(
        recommended_jobs=rerank_pool_df, user_skills=user_skills, top_n=TOP_SKILLS
    )


def recommend_missing_skills_hybrid(job_title, skills):
    bm25_recommender, embedding_model, runtime_indexes = load_skill_resources()
    bm25_results = bm25_recommender.query(
        target_role=job_title, user_skills=skills, top_k=TOP_SKILLS
    )
    embedding_results = get_embedding_missing_skills(
        model=embedding_model,
        runtime_indexes=runtime_indexes,
        job_title=job_title,
        user_skills=skills,
    )
    return reciprocal_rank_fusion(
        bm25_skills=bm25_results, emb_skills=embedding_results, top_k=TOP_SKILLS
    )


def recommend_jobs(job_title, skills, location):
    job_model, crawler_runtime = load_job_resources()
    return recommend_jobs_by_faiss(
        model=job_model,
        runtime=crawler_runtime,
        job_title=job_title,
        skills=skills,
        location=location,
        top_k_each_index=100,
        top_n=TOP_JOBS,
    )


# =========================================================
# Input helpers
# =========================================================

def split_skills(skills_text):
    if not skills_text:
        return []
    return [s.strip() for s in skills_text.split(",") if s.strip()]


def save_uploaded_cv(uploaded_file):
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(uploaded_file.getvalue())
        return Path(f.name)


# =========================================================
# Render helpers
# =========================================================

def render_skill_results(results):
    if not results:
        st.info("Chưa có dữ liệu. Nhập thông tin và nhấn Chạy gợi ý.")
        return
    for i, item in enumerate(results, start=1):
        skill = item.get("skill", "")
        score = item.get("rrf_score", 0)
        job_count = item.get("job_count", 0)
        bm25_rank = item.get("bm25_rank") or "—"
        emb_rank = item.get("emb_rank") or "—"
        badge_class = "score-badge" if i <= 5 else "score-badge score-badge-blue"
        st.markdown(
            f"""
            <div class="result-card">
                <span class="result-num">{i:02d}</span>
                <div class="result-body">
                    <div class="result-name">{skill}</div>
                    <div class="result-meta">
                        <span class="rank-pill">BM25 #{bm25_rank}</span>&nbsp;
                        <span class="rank-pill">Emb #{emb_rank}</span>&nbsp;
                        <span class="rank-pill">{job_count} jobs</span>
                    </div>
                </div>
                <div class="result-right">
                    <span class="{badge_class}">{score:.4f}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_job_results(jobs):
    if jobs is None or (isinstance(jobs, pd.DataFrame) and jobs.empty):
        st.info("Chưa có dữ liệu. Nhập thông tin và nhấn Chạy gợi ý.")
        return
    for i, row in jobs.reset_index(drop=True).iterrows():
        title = str(row.get("title", "") or "").strip()
        location_raw = str(row.get("location_raw", "") or "").strip()
        score = float(row.get("score", 0) or 0)
        link = str(row.get("link", "") or "").strip()
        badge_class = "score-badge" if i < 5 else "score-badge score-badge-blue"
        link_html = (
            f'<a class="job-link" href="{link}" target="_blank">Xem tin tuyển dụng</a>'
            if link else ""
        )
        st.markdown(
            f"""
            <div class="result-card">
                <span class="result-num">{i+1:02d}</span>
                <div class="result-body">
                    <div class="result-name">{title}</div>
                    <div class="result-meta">{location_raw}</div>
                    {link_html}
                </div>
                <div class="result-right">
                    <span class="{badge_class}">{score:.4f}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_power_bi():
    if not POWER_BI_URL:
        st.markdown(
            """
            <div class="pbi-wrap">
                <div class="pbi-empty">
                    <div class="pbi-empty-text">
                        Chưa có báo cáo Power BI<br>
                        <span class="pbi-empty-code">Điền POWER_BI_URL để kích hoạt</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    st.markdown('<div class="pbi-wrap">', unsafe_allow_html=True)
    components.iframe(POWER_BI_URL, height=500, scrolling=True)
    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:
    st.markdown(
        """
        <div class="brand-mark">
            <div class="brand-icon"></div>
            <div>
                <div class="brand-name">CareerAI</div>
                <div class="brand-version">v2.0  BM25 + RRF</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Thông tin đầu vào")

    input_mode = st.radio(
        "Chế độ nhập",
        ["Nhập tay", "Trích xuất từ CV"],
        label_visibility="collapsed",
        horizontal=True,
    )

    job_title = ""
    skills_text = ""
    location = ""

    if input_mode == "Nhập tay":
        job_title = st.text_input("Job title", placeholder="VD: Data Analyst, Backend Developer")
        skills_text = st.text_area("Skills hiện có", placeholder="VD: Python, SQL, Excel", height=110)
        location = st.text_input("Location", placeholder="VD: Hanoi, Ho Chi Minh")

    else:
        uploaded_cv = st.file_uploader("Upload CV (PDF)", type=["pdf"])
        if uploaded_cv is not None:
            if st.button("Trích xuất CV", use_container_width=True):
                with st.spinner("Đang đọc CV..."):
                    temp_cv_path = save_uploaded_cv(uploaded_cv)
                    extracted = extract_cv_file(temp_cv_path)
                    st.session_state["cv_job_title"] = extracted.get("job_title", "")
                    st.session_state["cv_skills"] = ", ".join(extracted.get("current_skills", []))
                    st.session_state["cv_location"] = extracted.get("location", "")

        job_title = st.text_input("Job title", value=st.session_state.get("cv_job_title", ""))
        skills_text = st.text_area("Skills", value=st.session_state.get("cv_skills", ""), height=110)
        location = st.text_input("Location", value=st.session_state.get("cv_location", ""))

    run_button = st.button("Chạy gợi ý", type="primary", use_container_width=True)


skills = split_skills(skills_text)


# =========================================================
# Main content
# =========================================================

st.markdown(
    f"""
    <div class="app-header">
        <div>
            <div class="page-eyebrow">Career Intelligence</div>
            <div class="page-title">Career <span>Recommendation</span></div>
            <div class="page-sub">BM25 + Sentence Embedding + Reciprocal Rank Fusion</div>
        </div>
        <div class="status-dot">System online</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-lbl">Target role</div>
            <div class="metric-val-text">{job_title or "—"}</div>
        </div>
        <div class="metric-card">
            <div class="metric-lbl">Skills hiện có</div>
            <div class="metric-val">{len(skills)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-lbl">Location</div>
            <div class="metric-val-text">{location or "Tất cả"}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-title">Market Intelligence</div>
    <div class="section-note">Báo cáo thị trường lao động — Power BI</div>
    """,
    unsafe_allow_html=True,
)
render_power_bi()

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

if run_button:
    if not job_title:
        st.warning("Vui lòng nhập job title.")
    else:
        with st.spinner("Đang phân tích và xếp hạng..."):
            st.session_state["skill_results"] = recommend_missing_skills_hybrid(
                job_title=job_title, skills=skills
            )
            st.session_state["job_results"] = recommend_jobs(
                job_title=job_title, skills=skills, location=location
            )

tab_skills, tab_jobs = st.tabs(["Gợi ý Skills", "Gợi ý Jobs"])

with tab_skills:
    st.markdown(
        '<div class="section-note" style="margin-top:14px">Kết hợp BM25 và Embedding qua Reciprocal Rank Fusion · Top 10 skills còn thiếu</div>',
        unsafe_allow_html=True,
    )
    render_skill_results(st.session_state.get("skill_results", []))

with tab_jobs:
    st.markdown(
        '<div class="section-note" style="margin-top:14px">Lọc theo location, xếp hạng bằng FAISS theo title và skills · Top 10 jobs phù hợp</div>',
        unsafe_allow_html=True,
    )
    render_job_results(st.session_state.get("job_results", pd.DataFrame()))