import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from sentence_transformers import SentenceTransformer

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import EMBEDDING_MODEL
from src.recommendation.cv.cv_extractor import extract_cv_file
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


# Fixed config
TOP_JOBS = 10
TOP_SKILLS = 10

KAGGLE_TOP_K = 300
CRAWLER_TOP_K = 50

LOCAL_CV_UPLOAD_DIR = PROJECT_ROOT / "data" / "cv" / "uploads"

POWER_BI_EMBED_URL = "https://app.powerbi.com/reportEmbed?reportId=121495bc-258e-4eda-8c82-40dc35465127&autoAuth=true&ctid=e7572e92-7aee-4713-a3c4-ba64888ad45f"


# ─── Cache ────────────────────────────────────────────────────────────────────

@st.cache_resource
def load_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL)


@st.cache_resource
def load_runtime_indexes_cached():
    return load_default_runtime_indexes()


# ─── CV utilities ─────────────────────────────────────────────────────────────

def save_uploaded_cv(uploaded_file) -> Path:
    LOCAL_CV_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = uploaded_file.name.replace(" ", "_")
    target_path = LOCAL_CV_UPLOAD_DIR / safe_name
    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return target_path


# ─── Recommendation core ──────────────────────────────────────────────────────

def run_recommend_once(
    model: SentenceTransformer,
    runtime_indexes,
    input_data: dict,
) -> dict[str, pd.DataFrame]:
    user_job_title = str(input_data["job_title"] or "").strip()
    user_skills = parse_skills(input_data["skills"])
    user_location = str(input_data["location"] or "Unknown").strip()

    query_texts = build_query_texts(
        job_title=user_job_title,
        skills=user_skills,
        location=user_location,
    )

    query_embeddings = {
        "title_text": encode_query(model=model, text=query_texts["title_text"]),
        "skills_text": encode_query(model=model, text=query_texts["skills_text"]),
        "full_text": encode_query(model=model, text=query_texts["full_text"]),
    }

    all_candidates = {}
    source_top_k = {"kaggle": KAGGLE_TOP_K, "crawler": CRAWLER_TOP_K}

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
        user_job_title=user_job_title,
        user_skills=user_skills,
        user_location=user_location,
    )

    if all_jobs_df.empty:
        return {"top_jobs": pd.DataFrame(), "missing_skills": pd.DataFrame(), "rerank_pool": pd.DataFrame()}

    rerank_pool_df = limit_candidates_by_source(candidates_df=all_jobs_df, source_limits=source_top_k)

    top_jobs_df = (
        rerank_pool_df
        .sort_values(by="final_score", ascending=False)
        .head(TOP_JOBS)
        .copy()
    )

    missing_skills_df = recommend_missing_skills(
        recommended_jobs=rerank_pool_df,
        user_skills=user_skills,
        top_n=TOP_SKILLS,
    )

    return {"top_jobs": top_jobs_df, "missing_skills": missing_skills_df, "rerank_pool": rerank_pool_df}


# ─── Display utilities ────────────────────────────────────────────────────────

def get_job_link(row: pd.Series) -> str:
    for col in ("job_url", "job_link"):
        val = str(row.get(col, "") or "").strip()
        if val:
            return val
    return ""


def show_job_cards(top_jobs: pd.DataFrame) -> None:
    if top_jobs.empty:
        st.warning("No matching jobs found.")
        return

    for idx, row in top_jobs.reset_index(drop=True).iterrows():
        title    = str(row.get("job_title_canonical", "") or "Unknown").strip()
        company  = str(row.get("company", "")            or "Unknown Company").strip()
        location = str(row.get("location_final", "")    or "Unknown").strip()
        source   = str(row.get("source_name", "")       or "").strip()
        score    = float(row.get("final_score", 0) or 0)
        link     = get_job_link(row)

        score_pct = min(int(score * 100), 100)
        score_color = "#10b981" if score_pct >= 70 else "#f59e0b" if score_pct >= 40 else "#6b7280"

        with st.container():
            st.markdown(
                f"""
                <div class="job-card">
                    <div class="job-card-header">
                        <div class="job-rank">#{idx + 1}</div>
                        <div class="job-info">
                            <div class="job-title">{title}</div>
                            <div class="job-meta">
                                <span class="meta-item">🏢 {company}</span>
                                <span class="meta-divider">·</span>
                                <span class="meta-item">📍 {location}</span>
                                <span class="meta-divider">·</span>
                                <span class="meta-badge">{source.upper()}</span>
                            </div>
                        </div>
                        <div class="job-score" style="color:{score_color};">
                            <div class="score-number">{score_pct}%</div>
                            <div class="score-label">Match</div>
                        </div>
                    </div>
                    <div class="score-bar-track">
                        <div class="score-bar-fill" style="width:{score_pct}%; background:{score_color};"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if link:
                st.link_button("View Job →", link, use_container_width=False)
            st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)


def show_missing_skills(missing_skills: pd.DataFrame) -> None:
    if missing_skills.empty:
        st.info("No skill gaps detected.")
        return

    skills = [
        str(row.get("skill", "") or "").strip()
        for _, row in missing_skills.iterrows()
        if str(row.get("skill", "") or "").strip()
    ]

    tags_html = "".join(
        f'<span class="skill-tag"><span class="skill-num">{i+1}</span>{skill}</span>'
        for i, skill in enumerate(skills)
    )
    st.markdown(f'<div class="skills-grid">{tags_html}</div>', unsafe_allow_html=True)


def show_powerbi_embed() -> None:
    st.components.v1.iframe(POWER_BI_EMBED_URL, height=720, scrolling=True)


# ─── Styles ───────────────────────────────────────────────────────────────────

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Page background ── */
.stApp {
    background: #0f1117;
    color: #e2e8f0;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 3rem; max-width: 1400px; }

/* ── Top header ── */
.page-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 28px 0 20px;
    border-bottom: 1px solid #1e2535;
    margin-bottom: 28px;
}
.header-icon {
    width: 48px; height: 48px;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; flex-shrink: 0;
}
.header-text h1 {
    margin: 0; font-size: 26px; font-weight: 700;
    background: linear-gradient(90deg, #e2e8f0, #94a3b8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.4px;
}
.header-text p {
    margin: 2px 0 0; font-size: 14px; color: #64748b; font-weight: 400;
}

/* ── Section labels ── */
.section-label {
    font-size: 11px; font-weight: 600; letter-spacing: 1.5px;
    color: #475569; text-transform: uppercase; margin-bottom: 14px;
}

/* ── Input panel ── */
.input-panel {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 16px;
    padding: 24px;
    height: 100%;
}

/* ── Streamlit inputs override ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #0f1117 !important;
    border: 1px solid #1e2535 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
label[data-testid="stWidgetLabel"] p {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    letter-spacing: 0.3px !important;
    text-transform: uppercase !important;
}

/* ── Radio ── */
.stRadio > div { gap: 8px; }
.stRadio > div > label {
    background: #0f1117 !important;
    border: 1px solid #1e2535 !important;
    border-radius: 8px !important;
    padding: 6px 16px !important;
    color: #94a3b8 !important;
    font-size: 13px !important;
    cursor: pointer;
    transition: all 0.2s;
}
.stRadio > div > label:has(input:checked) {
    border-color: #3b82f6 !important;
    color: #3b82f6 !important;
    background: rgba(59,130,246,0.08) !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px !important;
    padding: 12px 24px !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 28px rgba(99,102,241,0.5) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #161b27 !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid #1e2535 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 8px !important;
    color: #64748b !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 20px !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: #1e2535 !important;
    color: #e2e8f0 !important;
}

/* ── Job card ── */
.job-card {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 14px;
    padding: 18px 20px 14px;
    margin-bottom: 4px;
    transition: border-color 0.2s, transform 0.15s;
}
.job-card:hover {
    border-color: #334155;
    transform: translateX(2px);
}
.job-card-header {
    display: flex;
    align-items: flex-start;
    gap: 14px;
}
.job-rank {
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    color: #475569;
    min-width: 26px;
    padding-top: 3px;
}
.job-info { flex: 1; min-width: 0; }
.job-title {
    font-size: 15px;
    font-weight: 600;
    color: #e2e8f0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 6px;
}
.job-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
}
.meta-item { font-size: 12px; color: #64748b; }
.meta-divider { color: #334155; font-size: 12px; }
.meta-badge {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #3b82f6;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 4px;
    padding: 1px 6px;
}
.job-score {
    text-align: center;
    min-width: 52px;
}
.score-number {
    font-size: 17px;
    font-weight: 700;
    font-family: 'DM Mono', monospace;
    line-height: 1.1;
}
.score-label {
    font-size: 10px;
    color: #475569;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 1px;
}
.score-bar-track {
    height: 3px;
    background: #1e2535;
    border-radius: 99px;
    margin-top: 12px;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.6s ease;
}

/* ── Skills grid ── */
.skills-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 4px;
}
.skill-tag {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    color: #cbd5e1;
    font-weight: 500;
    transition: border-color 0.2s;
}
.skill-tag:hover { border-color: #3b82f6; color: #e2e8f0; }
.skill-num {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #3b82f6;
    font-weight: 600;
    min-width: 14px;
}

/* ── Dividers ── */
.divider {
    height: 1px;
    background: #1e2535;
    margin: 20px 0;
}

/* ── Result pane ── */
.result-panel {
    padding-left: 8px;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #3b82f6 !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0f1117 !important;
    border: 1px dashed #1e2535 !important;
    border-radius: 12px !important;
    color: #64748b !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f1117; }
::-webkit-scrollbar-thumb { background: #1e2535; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #334155; }
</style>
"""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Job & Skill Recommendation",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(STYLES, unsafe_allow_html=True)

    # Header
    st.markdown(
        """
        <div class="page-header">
            <div class="header-icon">💼</div>
            <div class="header-text">
                <h1>Job & Skill Recommendation</h1>
                <p>Powered by semantic search · Kaggle historical jobs + Crawler recent jobs</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner("Loading model and indexes..."):
        model = load_embedding_model()
        runtime_indexes = load_runtime_indexes_cached()

    tab_recommend, tab_powerbi = st.tabs(["  Recommendation  ", "  Power BI Dashboard  "])

    # ── TAB 1: Recommendation ──────────────────────────────────────────────────
    with tab_recommend:
        left_col, right_col = st.columns([1, 1.4], gap="large")

        # INPUT PANEL
        with left_col:
            st.markdown('<div class="section-label">Input</div>', unsafe_allow_html=True)

            input_mode = st.radio(
                "Input method",
                ["Manual entry", "Upload CV (PDF)"],
                horizontal=True,
                label_visibility="collapsed",
            )

            input_data = None

            if input_mode == "Manual entry":
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                job_title = st.text_input("Job Title", value="Data Analyst", placeholder="e.g. Data Engineer")
                skills = st.text_area(
                    "Current Skills",
                    value="SQL, Power BI, Excel",
                    height=110,
                    placeholder="e.g. Python, SQL, Tableau, Machine Learning",
                )
                location = st.text_input("Location", value="Ho Chi Minh, Vietnam", placeholder="e.g. Hanoi, Vietnam")

                input_data = {
                    "job_title": job_title,
                    "skills": skills,
                    "location": location,
                }

            else:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                uploaded_file = st.file_uploader(
                    "Upload your CV",
                    type=["pdf"],
                    label_visibility="collapsed",
                )

                if uploaded_file is not None:
                    if st.button("Extract CV", use_container_width=True):
                        with st.spinner("Extracting CV data..."):
                            cv_path = save_uploaded_cv(uploaded_file)
                            extracted = extract_cv_file(cv_path)
                        st.session_state["cv_extracted"] = extracted

                extracted = st.session_state.get("cv_extracted")

                if extracted:
                    st.success("CV extracted successfully.")
                    st.json(extracted)
                    input_data = {
                        "job_title": extracted.get("job_title", "Unknown"),
                        "skills": extracted.get("current_skills", []),
                        "location": extracted.get("location", "Unknown"),
                    }

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            run_button = st.button("Find Matching Jobs", type="primary", use_container_width=True)

        # RESULT PANEL
        with right_col:
            st.markdown('<div class="section-label">Results</div>', unsafe_allow_html=True)

            if run_button:
                if not input_data:
                    st.error("Please provide your information or upload a CV first.")
                    st.stop()

                if not str(input_data.get("job_title", "")).strip():
                    st.error("Job title is required.")
                    st.stop()

                with st.spinner("Searching for matching jobs..."):
                    result = run_recommend_once(
                        model=model,
                        runtime_indexes=runtime_indexes,
                        input_data=input_data,
                    )
                st.session_state["recommend_result"] = result

            result = st.session_state.get("recommend_result")

            if result:
                st.markdown('<div class="section-label">Top 10 Matching Jobs</div>', unsafe_allow_html=True)
                show_job_cards(result["top_jobs"])

                st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Recommended Skills to Learn</div>', unsafe_allow_html=True)
                show_missing_skills(result["missing_skills"])
            else:
                st.markdown(
                    """
                    <div style="
                        display:flex; flex-direction:column; align-items:center;
                        justify-content:center; padding: 80px 0; text-align:center;
                    ">
                        <div style="font-size:40px; margin-bottom:16px;">🔍</div>
                        <div style="font-size:16px; font-weight:600; color:#475569; margin-bottom:8px;">
                            Ready to find your next opportunity
                        </div>
                        <div style="font-size:13px; color:#334155;">
                            Fill in your details on the left and click <strong style="color:#3b82f6">Find Matching Jobs</strong>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── TAB 2: Power BI ────────────────────────────────────────────────────────
    with tab_powerbi:
        st.markdown('<div class="section-label">Market Analytics Dashboard</div>', unsafe_allow_html=True)
        show_powerbi_embed()


if __name__ == "__main__":
    main()