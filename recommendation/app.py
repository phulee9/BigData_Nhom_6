import sys
from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

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
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Skill Recommendation System",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# DARK PROFESSIONAL CSS
# =========================================================
st.markdown(
    """
    <style>
        /* App background */
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(59, 130, 246, 0.15), transparent 34%),
                radial-gradient(circle at top right, rgba(20, 184, 166, 0.12), transparent 30%),
                #0b1120;
            color: #e5e7eb;
        }

        .block-container {
            max-width: 1240px;
            padding-top: 30px;
            padding-bottom: 42px;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #0f172a;
            border-right: 1px solid #1f2937;
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb;
        }

        section[data-testid="stSidebar"] .stSlider label,
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] .stCaption {
            color: #e5e7eb !important;
        }

        /* Text */
        h1, h2, h3, h4, h5, h6, p, label, span, div {
            color: #e5e7eb;
        }

        .muted {
            color: #94a3b8;
            font-size: 14px;
            line-height: 1.6;
        }

        /* Header card */
        .app-header {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.95));
            border: 1px solid #263244;
            border-radius: 22px;
            padding: 34px 38px;
            margin-bottom: 22px;
            box-shadow: 0 20px 48px rgba(0, 0, 0, 0.35);
        }

        .app-title {
            font-size: 36px;
            font-weight: 850;
            color: #f8fafc;
            letter-spacing: -0.04em;
            margin-bottom: 10px;
        }

        .app-description {
            font-size: 15.5px;
            line-height: 1.7;
            color: #cbd5e1;
            max-width: 900px;
        }

        /* Cards */
        .card {
            background: rgba(15, 23, 42, 0.88);
            border: 1px solid #263244;
            border-radius: 18px;
            padding: 24px;
            margin-bottom: 18px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);
        }

        .card-title {
            font-size: 18px;
            font-weight: 760;
            color: #f8fafc;
            margin-bottom: 14px;
        }

        .card-subtitle {
            font-size: 14px;
            color: #94a3b8;
            line-height: 1.6;
            margin-bottom: 14px;
        }

        .section-label {
            font-size: 12px;
            font-weight: 760;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 8px;
        }

        /* Status */
        .status-ready {
            background: rgba(20, 184, 166, 0.12);
            border: 1px solid rgba(45, 212, 191, 0.35);
            color: #ccfbf1;
            padding: 12px 15px;
            border-radius: 14px;
            font-size: 14px;
            margin-bottom: 20px;
        }

        .status-muted {
            background: rgba(15, 23, 42, 0.88);
            border: 1px solid #263244;
            color: #cbd5e1;
            padding: 14px 15px;
            border-radius: 14px;
            font-size: 14px;
        }

        /* Tags */
        .tag {
            display: inline-block;
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid #334155;
            color: #e2e8f0;
            border-radius: 999px;
            padding: 7px 12px;
            margin: 4px 5px 4px 0;
            font-size: 13px;
            font-weight: 620;
        }

        .tag-recommend {
            display: inline-block;
            background: rgba(37, 99, 235, 0.18);
            border: 1px solid rgba(96, 165, 250, 0.45);
            color: #dbeafe;
            border-radius: 999px;
            padding: 8px 12px;
            margin: 5px 6px 5px 0;
            font-size: 13px;
            font-weight: 650;
        }

        .tag-rank {
            color: #93c5fd;
            font-weight: 700;
            margin-right: 4px;
        }

        /* Streamlit components */
        div[data-testid="stMetric"] {
            background: rgba(30, 41, 59, 0.82);
            border: 1px solid #334155;
            border-radius: 15px;
            padding: 15px 16px;
        }

        div[data-testid="stMetricValue"] {
            font-size: 20px;
            color: #f8fafc;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 13px;
            color: #94a3b8;
        }

        .stTextInput input,
        .stTextArea textarea {
            background-color: #111827 !important;
            color: #f8fafc !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
        }

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: #64748b !important;
        }

        .stFileUploader {
            background: rgba(15, 23, 42, 0.65);
            border-radius: 14px;
        }

        .stButton > button {
            border-radius: 12px;
            font-weight: 750;
            height: 44px;
            background: #2563eb;
            color: #ffffff;
            border: 1px solid #3b82f6;
        }

        .stButton > button:hover {
            background: #1d4ed8;
            color: #ffffff;
            border: 1px solid #60a5fa;
        }

        button[kind="primary"] {
            background: linear-gradient(135deg, #2563eb, #14b8a6) !important;
            color: #ffffff !important;
            border: none !important;
        }

        /* Tabs */
        button[data-baseweb="tab"] {
            color: #94a3b8;
            font-weight: 650;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: #f8fafc;
        }

        /* Dataframe */
        .stDataFrame {
            border-radius: 14px;
            overflow: hidden;
        }

        div[data-testid="stDataFrame"] {
            background: rgba(15, 23, 42, 0.9);
        }

        /* Expander */
        div[data-testid="stExpander"] {
            background: rgba(15, 23, 42, 0.88);
            border: 1px solid #263244;
            border-radius: 14px;
        }

        code {
            color: #bfdbfe !important;
        }

        .footer {
            text-align: center;
            color: #64748b;
            font-size: 13px;
            margin-top: 28px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SYSTEM LOADING
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
            f"<span class='tag-recommend'>"
            f"<span class='tag-rank'>{rank}.</span>{skill}"
            f" · score {score}"
            f" · freq {frequency}"
            f"</span>"
        )

    st.markdown(html, unsafe_allow_html=True)


def render_cleaned_input(cv_input):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Cleaned Input</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Job Title", cv_input.get("job_title", "N/A"))

    with col2:
        st.metric("Location", cv_input.get("location", "other"))

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Current Skills</div>", unsafe_allow_html=True)
    render_tags(cv_input.get("skills", []))

    st.markdown("</div>", unsafe_allow_html=True)


def render_jobs_table(top_jobs):
    if not top_jobs:
        st.info("No similar jobs found.")
        return

    jobs_df = pd.DataFrame(top_jobs)

    if "score" in jobs_df.columns:
        jobs_df["score"] = jobs_df["score"].astype(float).round(4)

    st.dataframe(
        jobs_df,
        use_container_width=True,
        hide_index=True,
    )


def render_result(result):
    left, right = st.columns([1.25, 1])

    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Top 5 Similar Jobs</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-subtitle'>Jobs are ranked by semantic similarity, title match, skill overlap, and location match.</div>",
            unsafe_allow_html=True,
        )
        render_jobs_table(result.get("top_5_similar_jobs", []))
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Top 10 Missing Skills</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-subtitle'>Skills already listed by the user are removed after normalization.</div>",
            unsafe_allow_html=True,
        )
        render_recommended_skills(result.get("top_10_missing_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Scoring method", expanded=False):
        st.write("Search query")
        st.code(result.get("query", ""), language="text")

        st.markdown(
            """
            Job similarity score:

            `job_score = 0.50 * semantic_score + 0.25 * title_score + 0.15 * skill_overlap_score + 0.10 * location_score`

            Skill ranking score:

            `skill_score = 0.80 * weighted_job_score + 0.20 * frequency_score`
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
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("### Configuration")

    retrieve_jobs = st.slider(
        "Retrieved jobs",
        min_value=50,
        max_value=500,
        value=200,
        step=50,
    )

    rerank_jobs = st.slider(
        "Reranked jobs",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
    )

    top_skills = st.slider(
        "Recommended skills",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
    )

    st.divider()

    st.markdown("### System")
    st.caption("Local FAISS index, Sentence Transformer, hybrid reranking")

    if st.button("Reload system", use_container_width=True):
        st.cache_resource.clear()
        st.success("Cache cleared. Refresh the page to reload.")


# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
    <div class="app-header">
        <div class="app-title">Skill Recommendation System</div>
        <div class="app-description">
            Recommend missing skills by comparing the user's target role and current skills
            with similar jobs from the job market dataset.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# LOAD BACKEND
# =========================================================
try:
    with st.spinner("Loading system..."):
        index, metadata, model = load_recommendation_system()

    st.markdown(
        f"""
        <div class="status-ready">
            System ready. Loaded <b>{len(metadata):,}</b> job records.
        </div>
        """,
        unsafe_allow_html=True,
    )
except Exception as e:
    st.error(f"Failed to load system: {e}")
    st.stop()


# =========================================================
# MAIN TABS
# =========================================================
tab_cv, tab_manual, tab_dashboard, tab_about = st.tabs(
    ["CV Upload", "Manual Input", "Dashboard", "About"]
)


# =========================================================
# CV UPLOAD TAB
# =========================================================
with tab_cv:
    input_col, guide_col = st.columns([1.05, 0.95])

    with input_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Upload CV</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-subtitle'>Upload a PDF CV. The system will extract role, location, and skills.</div>",
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

    with guide_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Expected Output</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="muted">
            The result includes cleaned input, the five most similar jobs,
            and the ten missing skills that the user should consider learning.
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
                    retrieve_jobs=retrieve_jobs,
                    rerank_jobs=rerank_jobs,
                    top_skills=top_skills,
                )

            except Exception as e:
                st.error(f"Error: {e}")


# =========================================================
# MANUAL INPUT TAB
# =========================================================
with tab_manual:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Manual Input</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='card-subtitle'>Enter the target role, location, and current skills manually.</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        job_title = st.text_input(
            "Target job title",
            placeholder="Backend Developer",
        )

    with col2:
        location = st.text_input(
            "Location",
            placeholder="united states, vietnam, remote",
        )

    skills_text = st.text_area(
        "Current skills",
        placeholder="git, node js, sql",
        height=120,
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
                retrieve_jobs=retrieve_jobs,
                rerank_jobs=rerank_jobs,
                top_skills=top_skills,
            )

        except Exception as e:
            st.error(f"Error: {e}")


# =========================================================
# DASHBOARD TAB
# =========================================================
with tab_dashboard:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Dashboard</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="muted">
        This section can be used to embed a Power BI dashboard after the report is published.
        </div>
        """,
        unsafe_allow_html=True,
    )

    powerbi_iframe_url = st.text_input(
        "Power BI iframe URL",
        placeholder="Paste Power BI embed link here",
    )

    if powerbi_iframe_url:
        st.components.v1.iframe(
            powerbi_iframe_url,
            height=760,
            scrolling=True,
        )
    else:
        st.markdown(
            """
            <div class="status-muted">
                No dashboard link provided.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ABOUT TAB
# =========================================================
with tab_about:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>About</div>", unsafe_allow_html=True)

    st.markdown(
        """
        This system recommends missing skills using job market data.

        Workflow:

        1. Receive job title, location, and current skills.
        2. Normalize and clean the input.
        3. Encode the search query using a sentence embedding model.
        4. Retrieve similar jobs using FAISS.
        5. Rerank jobs using semantic similarity, title similarity, skill overlap, and location match.
        6. Aggregate skills from similar jobs.
        7. Remove skills the user already has.
        8. Return the most similar jobs and the recommended missing skills.
        """
    )

    st.markdown("</div>", unsafe_allow_html=True)


st.markdown(
    "<div class='footer'>Skill Recommendation System</div>",
    unsafe_allow_html=True,
)