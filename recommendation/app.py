import sys
from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

# =========================================================
# PATH CONFIG
# =========================================================
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from recommendation.core.loader import load_system
from recommendation.core.recommend import recommend_from_cv_input
from recommendation.cv.cv_extractor import extract_and_prepare_cv
from recommendation.core.preprocess import (
    normalize_skill,
    normalize_location,
    process_job_title,
)


# =========================================================
# POWER BI EMBED LINK
# Dán link ở ô "Link to embed this content" của Power BI vào đây
# Ví dụ: https://app.powerbi.com/reportEmbed?reportId=...
# =========================================================
POWERBI_EMBED_URL = "https://app.powerbi.com/reportEmbed?reportId=5b1bcd7b-b8d1-4dec-8472-6513baeaf987&autoAuth=true&ctid=e7572e92-7aee-4713-a3c4-ba64888ad45f"


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Skill Recommendation System",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# CSS — Refined Minimal Dark
# =========================================================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

        *, *::before, *::after { box-sizing: border-box; }

        html, body, .stApp {
            background: #07090f;
            color: #c9d1e0;
            font-family: 'DM Sans', sans-serif;
        }

        header[data-testid="stHeader"] { background: transparent !important; }

        .block-container {
            max-width: 1280px;
            padding: 36px 40px 60px;
        }

        /* ── HERO ── */
        .hero {
            padding: 48px 0 36px;
            border-bottom: 1px solid #141927;
            margin-bottom: 40px;
        }

        .hero-eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #3b82f6;
            margin-bottom: 18px;
        }

        .hero-eyebrow::before {
            content: '';
            display: inline-block;
            width: 20px;
            height: 1.5px;
            background: #3b82f6;
        }

        .hero-title {
            font-size: 42px;
            font-weight: 700;
            letter-spacing: -0.03em;
            color: #f0f4ff;
            line-height: 1.15;
            margin-bottom: 14px;
        }

        .hero-desc {
            font-size: 15px;
            line-height: 1.75;
            color: #5d6b85;
            max-width: 680px;
            font-weight: 400;
        }

        .hero-pills {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 28px;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            background: #0d1117;
            border: 1px solid #1a2235;
            color: #7a8ba8;
            padding: 7px 13px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            font-family: 'DM Mono', monospace;
        }

        .pill-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #10b981;
            flex-shrink: 0;
        }

        /* ── SECTION HEADER ── */
        .sec-header {
            margin-bottom: 20px;
        }

        .sec-label {
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #3b82f6;
            margin-bottom: 6px;
        }

        .sec-title {
            font-size: 22px;
            font-weight: 700;
            color: #edf2ff;
            letter-spacing: -0.02em;
            margin-bottom: 4px;
        }

        .sec-desc {
            font-size: 13.5px;
            color: #4a5568;
            line-height: 1.6;
        }

        /* ── DIVIDER ── */
        .divider {
            height: 1px;
            background: #141927;
            margin: 36px 0;
        }

        /* ── CARD ── */
        .card {
            background: #0d1117;
            border: 1px solid #161d2e;
            border-radius: 14px;
            padding: 28px;
            margin-bottom: 20px;
        }

        .card-title {
            font-size: 15px;
            font-weight: 650;
            color: #dde5f5;
            margin-bottom: 4px;
            letter-spacing: -0.01em;
        }

        .card-desc {
            font-size: 13px;
            color: #3d4f6a;
            line-height: 1.6;
            margin-bottom: 20px;
        }

        /* ── DASHBOARD FRAME ── */
        .db-wrap {
            border: 1px solid #161d2e;
            border-radius: 14px;
            overflow: hidden;
            background: #050709;
        }

        /* ── WARNING / INFO BOXES ── */
        .warn-box {
            background: rgba(234, 179, 8, 0.06);
            border: 1px solid rgba(234, 179, 8, 0.2);
            color: #c4a53a;
            padding: 14px 18px;
            border-radius: 10px;
            font-size: 13.5px;
            line-height: 1.65;
        }

        .info-box {
            background: rgba(59, 130, 246, 0.07);
            border: 1px solid rgba(59, 130, 246, 0.2);
            color: #8ab4f8;
            padding: 14px 18px;
            border-radius: 10px;
            font-size: 13.5px;
            line-height: 1.65;
        }

        /* ── TAGS ── */
        .tag {
            display: inline-block;
            background: #0d1117;
            border: 1px solid #1e2a40;
            color: #8fa3c4;
            border-radius: 6px;
            padding: 5px 11px;
            margin: 3px 4px 3px 0;
            font-size: 12.5px;
            font-weight: 500;
            font-family: 'DM Mono', monospace;
        }

        .tag-rec {
            display: inline-block;
            background: rgba(59, 130, 246, 0.08);
            border: 1px solid rgba(59, 130, 246, 0.22);
            color: #93b4f7;
            border-radius: 6px;
            padding: 6px 11px;
            margin: 4px 5px 4px 0;
            font-size: 12.5px;
            font-weight: 500;
            font-family: 'DM Mono', monospace;
        }

        .muted { color: #3d4f6a; font-size: 13.5px; }

        /* ── INPUTS ── */
        .stTextInput input,
        .stTextArea textarea {
            background: #0a0e17 !important;
            color: #c9d1e0 !important;
            border: 1px solid #1e2a40 !important;
            border-radius: 9px !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 14px !important;
            padding: 10px 14px !important;
            transition: border-color 0.18s ease !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
        }

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: #2d3d55 !important;
        }

        label[data-testid="stWidgetLabel"] p {
            color: #5d7099 !important;
            font-size: 12.5px !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em !important;
            text-transform: uppercase !important;
        }

        /* ── FILE UPLOADER ── */
        .stFileUploader {
            background: #0a0e17;
            border-radius: 12px;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: #0a0e17 !important;
            border: 1.5px dashed #1e2a40 !important;
            border-radius: 10px !important;
        }

        /* ── BUTTONS ── */
        .stButton > button {
            border-radius: 9px !important;
            font-weight: 600 !important;
            font-size: 13.5px !important;
            height: 42px !important;
            background: #1a2844 !important;
            color: #93b4f7 !important;
            border: 1px solid #1e3460 !important;
            transition: background 0.18s, border-color 0.18s !important;
            font-family: 'DM Sans', sans-serif !important;
        }

        .stButton > button:hover {
            background: #1f3460 !important;
            border-color: #3b82f6 !important;
            color: #c0d4ff !important;
        }

        button[kind="primary"],
        .stButton > button[kind="primary"] {
            background: #1e40af !important;
            color: #dbeafe !important;
            border: 1px solid #2563eb !important;
        }

        button[kind="primary"]:hover,
        .stButton > button[kind="primary"]:hover {
            background: #2563eb !important;
            border-color: #3b82f6 !important;
            color: #eff6ff !important;
        }

        /* ── TABS ── */
        [data-baseweb="tab-list"] {
            background: transparent !important;
            border-bottom: 1px solid #141927 !important;
            gap: 0 !important;
        }

        button[data-baseweb="tab"] {
            background: transparent !important;
            color: #3d4f6a !important;
            font-weight: 600 !important;
            font-size: 13.5px !important;
            padding: 12px 20px !important;
            border-radius: 0 !important;
            border-bottom: 2px solid transparent !important;
            font-family: 'DM Sans', sans-serif !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: #e8f0ff !important;
            border-bottom: 2px solid #3b82f6 !important;
        }

        [data-baseweb="tab-highlight"] { display: none !important; }

        /* ── METRICS ── */
        div[data-testid="stMetric"] {
            background: #0a0e17;
            border: 1px solid #161d2e;
            border-radius: 10px;
            padding: 16px 18px;
        }

        div[data-testid="stMetricValue"] {
            font-size: 18px !important;
            font-weight: 700 !important;
            color: #dde5f5 !important;
            font-family: 'DM Mono', monospace !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 11px !important;
            color: #3d4f6a !important;
            font-weight: 600 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
        }

        /* ── DATAFRAME ── */
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #161d2e !important;
        }

        [data-testid="stDataFrame"] iframe {
            border-radius: 10px;
        }

        /* ── EXPANDER ── */
        div[data-testid="stExpander"] {
            background: #0a0e17;
            border: 1px solid #161d2e !important;
            border-radius: 10px;
        }

        div[data-testid="stExpander"] summary {
            color: #5d7099 !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }

        /* ── CODE BLOCK ── */
        .stCode, code, pre {
            font-family: 'DM Mono', monospace !important;
            background: #060810 !important;
            border: 1px solid #161d2e !important;
            border-radius: 8px !important;
            font-size: 12.5px !important;
        }

        /* ── SPINNER ── */
        div[data-testid="stSpinner"] p {
            color: #5d7099 !important;
            font-size: 13px !important;
        }

        /* ── FOOTER ── */
        .footer {
            text-align: center;
            color: #1e2a40;
            font-size: 12px;
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #0d1117;
            font-family: 'DM Mono', monospace;
            letter-spacing: 0.05em;
        }

        /* ── ALERT / WARNING / ERROR ── */
        div[data-testid="stAlert"] {
            border-radius: 10px !important;
            border-width: 1px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# CACHE
# =========================================================
@st.cache_resource(show_spinner=False)
def load_recommendation_system():
    return load_system()


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def build_manual_input(job_title: str, location: str, skills_text: str) -> dict:
    skills = [
        normalize_skill(skill)
        for skill in skills_text.split(",")
        if normalize_skill(skill)
    ]
    return {
        "job_title": process_job_title(job_title),
        "location": normalize_location(location),
        "skills": sorted(list(set(skills))),
    }


def save_uploaded_pdf_to_temp(uploaded_file) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def run_recommend(cv_input, index, metadata, model, retrieve_jobs, rerank_jobs, top_skills):
    return recommend_from_cv_input(
        cv_input=cv_input,
        index=index,
        metadata=metadata,
        model=model,
        retrieve_jobs=retrieve_jobs,
        rerank_jobs=rerank_jobs,
        top_skills=top_skills,
    )


def render_tags(items):
    if not items:
        st.markdown("<span class='muted'>No data available.</span>", unsafe_allow_html=True)
        return
    html = "".join([f"<span class='tag'>{item}</span>" for item in items])
    st.markdown(html, unsafe_allow_html=True)


def render_recommended_skills(items):
    if not items:
        st.info("No missing skills found.")
        return
    html = ""
    for item in items:
        rank = item.get("rank", "")
        skill = item.get("skill", "")
        score = item.get("score", "")
        frequency = item.get("frequency", "")
        html += (
            f"<span class='tag-rec'>"
            f"<span style='opacity:.45;margin-right:5px;'>#{rank}</span>{skill}"
            f"<span style='opacity:.35;margin: 0 4px;'>·</span>"
            f"<span style='opacity:.55;font-size:11px;'>{score} · {frequency}</span>"
            f"</span>"
        )
    st.markdown(html, unsafe_allow_html=True)


def render_cleaned_input(cv_input):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Cleaned Input</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='card-desc'>Normalized information extracted from the CV or manual form.</div>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Job Title", cv_input.get("job_title", "N/A"))
    with col2:
        st.metric("Location", cv_input.get("location", "other"))
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:10px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#3d4f6a;margin-bottom:10px;'>Current Skills</div>",
        unsafe_allow_html=True,
    )
    render_tags(cv_input.get("skills", []))
    st.markdown("</div>", unsafe_allow_html=True)


def render_jobs_table(top_jobs):
    if not top_jobs:
        st.info("No similar jobs found.")
        return
    jobs_df = pd.DataFrame(top_jobs)
    if "score" in jobs_df.columns:
        jobs_df["score"] = jobs_df["score"].astype(float).round(4)
    st.dataframe(jobs_df, use_container_width=True, hide_index=True)


def render_result(result):
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Top 5 Similar Jobs</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-desc'>Ranked by semantic similarity, title match, skill overlap and location match.</div>",
            unsafe_allow_html=True,
        )
        render_jobs_table(result.get("top_5_similar_jobs", []))
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Top 10 Missing Skills</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-desc'>Skills already listed by the user are removed after normalization.</div>",
            unsafe_allow_html=True,
        )
        render_recommended_skills(result.get("top_10_missing_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Scoring method", expanded=False):
        st.write("Search query")
        st.code(result.get("query", ""), language="text")
        st.markdown(
            """
            **Job similarity score:**

            `job_score = 0.50 × semantic + 0.25 × title + 0.15 × skill_overlap + 0.10 × location`

            **Skill ranking score:**

            `skill_score = 0.80 × weighted_job_score + 0.20 × frequency_score`
            """
        )


def process_and_display(cv_input, index, metadata, model, retrieve_jobs, rerank_jobs, top_skills):
    if not cv_input.get("job_title"):
        st.error("Job title is empty after cleaning. Please provide a clearer job title.")
        return
    render_cleaned_input(cv_input)
    with st.spinner("Finding similar jobs and recommending missing skills..."):
        result = run_recommend(
            cv_input=cv_input,
            index=index,
            metadata=metadata,
            model=model,
            retrieve_jobs=retrieve_jobs,
            rerank_jobs=rerank_jobs,
            top_skills=top_skills,
        )
    render_result(result)


# =========================================================
# LOAD BACKEND
# =========================================================
try:
    with st.spinner("Loading recommendation system..."):
        index, metadata, model = load_recommendation_system()
    loaded_message = f"{len(metadata):,} job records"
except Exception as e:
    st.error(f"Failed to load system: {e}")
    st.stop()


# =========================================================
# HERO
# =========================================================
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-eyebrow">Skill Recommendation System</div>
        <div class="hero-title">Career Intelligence<br>Powered by Vector Search</div>
        <div class="hero-desc">
            Combine job market data, sentence embeddings, and hybrid reranking
            to surface the skills that matter most for your target career path.
        </div>
        <div class="hero-pills">
            <span class="pill"><span class="pill-dot"></span>System ready</span>
            <span class="pill">{loaded_message}</span>
            <span class="pill">FAISS · Sentence Embeddings</span>
            <span class="pill">Power BI Dashboard</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# POWER BI DASHBOARD
# =========================================================
st.markdown(
    """
    <div class="sec-header">
        <div class="sec-label">Market Intelligence</div>
        <div class="sec-title">Job Market Dashboard</div>
        <div class="sec-desc">
            Market-level insights from Power BI — job title demand, top skills,
            location distribution, and role-specific skill trends.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if POWERBI_EMBED_URL and POWERBI_EMBED_URL != "PASTE_POWER_BI_EMBED_LINK_HERE":
    st.markdown("<div class='db-wrap'>", unsafe_allow_html=True)
    st.components.v1.iframe(POWERBI_EMBED_URL, height=820, scrolling=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown(
        """
        <div class="warn-box">
            Power BI embed link has not been configured yet.
            Paste your <code style="background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:4px;">reportEmbed</code>
            URL into the <code style="background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:4px;">POWERBI_EMBED_URL</code>
            variable at the top of <code style="background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:4px;">app.py</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)


# =========================================================
# RECOMMENDATION SECTION
# =========================================================
st.markdown(
    """
    <div class="sec-header">
        <div class="sec-label">Recommendation Engine</div>
        <div class="sec-title">Skill Recommendation</div>
        <div class="sec-desc">
            Upload a CV or enter job information manually to find similar roles
            and discover the skills you should prioritize.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_cv, tab_manual, tab_about = st.tabs(["CV Upload", "Manual Input", "About"])


# =========================================================
# CV UPLOAD TAB
# =========================================================
with tab_cv:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.05, 0.95])

    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Upload CV</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-desc'>Upload a PDF CV. The system extracts the target role, location and current skills.</div>",
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "PDF file",
            type=["pdf"],
            label_visibility="collapsed",
        )
        analyze_cv = st.button(
            "Analyze and Recommend",
            type="primary",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Expected Output</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="muted" style="line-height:1.75">
                The result includes normalized input, the five most similar jobs,
                and the top missing skills the user should consider learning.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if analyze_cv:
        if uploaded_file is None:
            st.warning("Please upload a PDF file first.")
        else:
            try:
                with st.spinner("Reading and extracting CV information..."):
                    tmp_path = save_uploaded_pdf_to_temp(uploaded_file)
                    cv_input = extract_and_prepare_cv(tmp_path)
                process_and_display(
                    cv_input=cv_input,
                    index=index,
                    metadata=metadata,
                    model=model,
                    retrieve_jobs=200,
                    rerank_jobs=50,
                    top_skills=10,
                )
            except Exception as e:
                st.error(f"Error: {e}")


# =========================================================
# MANUAL INPUT TAB
# =========================================================
with tab_manual:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Manual Input</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='card-desc'>Enter the target role, preferred location and current skills manually.</div>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        job_title = st.text_input("Target job title", placeholder="Backend Developer")
    with col2:
        location = st.text_input("Location", placeholder="united states, vietnam, remote")
    skills_text = st.text_area(
        "Current skills",
        placeholder="git, node js, sql",
        height=110,
    )
    analyze_manual = st.button(
        "Recommend Skills",
        type="primary",
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if analyze_manual:
        try:
            cv_input = build_manual_input(
                job_title=job_title,
                location=location,
                skills_text=skills_text,
            )
            process_and_display(
                cv_input=cv_input,
                index=index,
                metadata=metadata,
                model=model,
                retrieve_jobs=200,
                rerank_jobs=50,
                top_skills=10,
            )
        except Exception as e:
            st.error(f"Error: {e}")


# =========================================================
# ABOUT TAB
# =========================================================
with tab_about:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>About this system</div>", unsafe_allow_html=True)
    st.markdown(
        """
        This application combines job market data, vector search and hybrid reranking
        to recommend missing skills for a target career path.

        **Main workflow:**

        1. Receive input from CV upload or manual form.
        2. Extract and normalize job title, location and skills.
        3. Encode the query using a sentence embedding model.
        4. Retrieve similar jobs using FAISS.
        5. Rerank jobs using semantic similarity, title similarity, skill overlap and location match.
        6. Aggregate skills from similar jobs.
        7. Remove skills the user already has.
        8. Return similar jobs, missing skills and market-level Power BI insights.
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# FOOTER
# =========================================================
st.markdown(
    "<div class='footer'>Skill Recommendation System</div>",
    unsafe_allow_html=True,
)