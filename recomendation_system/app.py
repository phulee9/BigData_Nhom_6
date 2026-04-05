import streamlit as st
import sys
import os
import json
import fitz
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent))

from recommend     import load_index, recommend_skills
from roadmap       import skill_gap_roadmap
from career_switch import career_switch_analysis


# ── Đọc PDF ───────────────────────────────────────────
def read_pdf(uploaded_file) -> str:
    try:
        doc   = fitz.open(
            stream   = uploaded_file.read(),
            filetype = "pdf"
        )
        pages = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
        doc.close()
        return "\n".join(pages)
    except Exception as e:
        st.error(f"Lỗi đọc PDF: {e}")
        return ""


# ── Groq extract CV ───────────────────────────────────
SYSTEM_PROMPT_CV = """You are a CV skill extractor.
Extract ONLY the 5 most important skills for the applied job position.
Rules:
- KEEP: programming languages, frameworks, tools, software, certifications
- REMOVE: soft skills, personality traits, company names, school names
- Return exactly 5 skills ranked by importance
Output ONLY this JSON:
{
  "vi_tri_ung_tuyen": "job title in lowercase",
  "skills": ["skill1", "skill2", "skill3", "skill4", "skill5"]
}"""


def extract_cv_groq(cv_text: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY") or \
              os.environ.get("GROQ_API_KEY_1")
    if not api_key:
        st.error("Không có GROQ_API_KEY trong .env!")
        return {}
    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model    = "llama-3.3-70b-versatile",
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_CV},
                {"role": "user",
                 "content": f"Extract from this CV:\n\n{cv_text[:8000]}"}
            ],
            temperature     = 0.0,
            max_tokens      = 1024,
            response_format = {"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Groq lỗi: {e}")
        return {}


# ── Dedup skills ──────────────────────────────────────
def dedup_skills(skills_raw: list) -> list:
    seen   = set()
    result = []
    for s in skills_raw:
        s_clean = s.lower().strip()
        if s_clean and s_clean not in seen:
            seen.add(s_clean)
            result.append(s_clean)
    return result


# ── Cấu hình trang ────────────────────────────────────
st.set_page_config(
    page_title = "Skill Recommender",
    page_icon  = "🎯",
    layout     = "centered"
)

st.title("🎯 Skill Recommender")
st.caption("Hệ thống gợi ý kỹ năng dựa trên 812,102 tin tuyển dụng")

# ── Load index 1 lần ──────────────────────────────────
@st.cache_resource
def get_index():
    return load_index()

with st.spinner("Đang khởi động hệ thống..."):
    index, df = get_index()

st.success(f"✓ Sẵn sàng! {index.ntotal:,} jobs trong hệ thống")
st.divider()


# ── Helper: 2 kiểu input ──────────────────────────────
def input_block(tab_key: str):
    """Trả về (job_title, skills) từ upload CV hoặc nhập tay"""

    input_type = st.radio(
        "Chọn cách nhập:",
        ["📄 Upload CV (PDF)", "✏️ Nhập tay"],
        horizontal = True,
        key        = f"radio_{tab_key}"
    )

    job_title = ""
    skills    = []

    # ── Upload CV ─────────────────────────────────────
    if input_type == "📄 Upload CV (PDF)":
        uploaded = st.file_uploader(
            "Chọn file CV (PDF)",
            type = ["pdf"],
            key  = f"upload_{tab_key}"
        )

        if uploaded:
            st.success(f"✓ {uploaded.name}")

            if st.button(
                "🤖 Phân tích CV",
                key  = f"analyze_{tab_key}",
                type = "primary"
            ):
                with st.spinner("Đang đọc PDF..."):
                    cv_text = read_pdf(uploaded)

                if cv_text:
                    with st.spinner("Groq đang extract skills..."):
                        data = extract_cv_groq(cv_text)

                    if data:
                        skills_clean = dedup_skills(
                            data.get("skills", [])
                        )
                        st.session_state[f"title_{tab_key}"] = \
                            data.get("vi_tri_ung_tuyen", "")
                        st.session_state[f"skills_{tab_key}"] = \
                            skills_clean

        # Hiển thị kết quả nếu đã extract
        if st.session_state.get(f"title_{tab_key}"):
            job_title = st.session_state[f"title_{tab_key}"]
            skills    = st.session_state[f"skills_{tab_key}"]

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Vị trí", job_title)
            with col2:
                st.metric("Skills", len(skills))

            for i, s in enumerate(skills, 1):
                st.write(f"{i}. **{s}**")

    # ── Nhập tay ──────────────────────────────────────
    else:
        job_title_input = st.text_input(
            "Vị trí ứng tuyển",
            placeholder = "VD: backend developer...",
            key         = f"title_input_{tab_key}"
        )
        skills_input = st.text_area(
            "Skills hiện có (cách nhau bằng dấu phẩy)",
            placeholder = "VD: python, sql, docker",
            height      = 100,
            key         = f"skills_input_{tab_key}"
        )

        job_title = job_title_input.lower().strip()
        skills    = [
            s.strip().lower()
            for s in skills_input.split(",")
            if s.strip()
        ]

    return job_title, skills


# ── 3 Tabs ────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🔍 Gợi ý skills",
    "📚 Lộ trình học",
    "🔄 Chuyển hướng nghề"
])

# ══════════════════════════════════════════════════════
# TAB 1 — Gợi ý skills
# ══════════════════════════════════════════════════════
with tab1:
    st.subheader("Gợi ý skills còn thiếu")

    job_title_1, skills_1 = input_block("tab1")

    st.divider()

    if st.button("🔍 Gợi ý", key="btn1", type="primary"):
        if not job_title_1:
            st.warning("Vui lòng nhập vị trí ứng tuyển!")
        elif not skills_1:
            st.warning("Vui lòng nhập skills hiện có!")
        else:
            with st.spinner("Đang phân tích..."):
                result = recommend_skills(
                    cv_skills  = skills_1,
                    job_title  = job_title_1,
                    index      = index,
                    df         = df,
                    top_k      = 150,
                    top_skills = 10
                )

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Jobs phân tích", result["total_candidates"])
            with col2:
                st.metric("Skills gợi ý", len(result["skills_goi_y"]))

            st.subheader("📌 Job titles gần nhất")
            for i, (t, s) in enumerate(
                zip(result["job_titles_gan_nhat"],
                    result["top_scores"]), 1
            ):
                st.write(f"{i}. **{t}** (độ tương đồng: {s:.2f})")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("✅ Skills đã có")
                for s in result["skills_da_co"]:
                    st.write(f"• {s}")

            with col2:
                st.subheader("📈 Skills nên học thêm")
                total = result["total_candidates"]
                for i, item in enumerate(result["skills_goi_y"], 1):
                    pct = round(item["count"] / total * 100)
                    st.write(f"{i}. **{item['skill']}** — {pct}% jobs")
                    st.progress(pct / 100)


# ══════════════════════════════════════════════════════
# TAB 2 — Lộ trình học
# ══════════════════════════════════════════════════════
with tab2:
    st.subheader("Lộ trình học skills")

    job_title_2, skills_2 = input_block("tab2")

    st.divider()

    if st.button("📚 Xem lộ trình", key="btn2", type="primary"):
        if not job_title_2:
            st.warning("Vui lòng nhập vị trí ứng tuyển!")
        elif not skills_2:
            st.warning("Vui lòng nhập skills hiện có!")
        else:
            with st.spinner("Đang phân tích..."):
                result = skill_gap_roadmap(
                    cv_skills = skills_2,
                    job_title = job_title_2,
                    df        = df,
                    top_n     = 5
                )

            if result.get("error"):
                st.error(result["error"])
            else:
                st.divider()
                st.metric(
                    "Jobs phân tích",
                    f"{result['total_jobs']:,}"
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.error("🔴 MUST HAVE")
                    st.caption("Bắt buộc phải có")
                    if result["must_have"]:
                        for item in result["must_have"]:
                            st.write(
                                f"• **{item['skill']}**"
                                f" ({item['pct']}%)"
                            )
                    else:
                        st.write("✓ Đã đủ!")

                with col2:
                    st.warning("🟡 SHOULD HAVE")
                    st.caption("Nên có")
                    if result["should_have"]:
                        for item in result["should_have"]:
                            st.write(
                                f"• **{item['skill']}**"
                                f" ({item['pct']}%)"
                            )
                    else:
                        st.write("✓ Không cần!")

                with col3:
                    st.info("🔵 NICE TO HAVE")
                    st.caption("Thêm điểm")
                    if result["nice_have"]:
                        for item in result["nice_have"]:
                            st.write(
                                f"• **{item['skill']}**"
                                f" ({item['pct']}%)"
                            )
                    else:
                        st.write("✓ Không có!")


# ══════════════════════════════════════════════════════
# TAB 3 — Chuyển hướng nghề
# ══════════════════════════════════════════════════════
with tab3:
    st.subheader("Phân tích chuyển hướng nghề nghiệp")

    job_from, skills_3 = input_block("tab3")

    st.divider()

    job_to = st.text_input(
        "Vị trí muốn chuyển sang",
        placeholder = "VD: devops engineer, data scientist...",
        key         = "job_to"
    )

    if st.button("🔄 Phân tích", key="btn3", type="primary"):
        if not job_from:
            st.warning("Vui lòng nhập vị trí hiện tại!")
        elif not job_to:
            st.warning("Vui lòng nhập vị trí muốn chuyển!")
        elif not skills_3:
            st.warning("Vui lòng nhập skills hiện có!")
        else:
            with st.spinner("Đang phân tích..."):
                result = career_switch_analysis(
                    job_from  = job_from,
                    job_to    = job_to.lower().strip(),
                    cv_skills = skills_3,
                    df        = df,
                    top_n     = 20
                )

            if result.get("error"):
                st.error(result["error"])
            else:
                st.divider()

                match_pct = result["match_pct"]
                st.metric(
                    "Độ phù hợp với vị trí mới",
                    f"{match_pct}%"
                )
                st.progress(match_pct / 100)

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.success("✅ Skills CV phù hợp")
                    if result["cv_match"]:
                        for s, pct in result["cv_match"]:
                            st.write(f"• **{s}** ({pct}%)")
                    else:
                        st.write("Chưa có skills phù hợp!")

                with col2:
                    st.info("⭐ Skills đặc trưng")
                    for s in result["only_to_skills"][:5]:
                        st.write(f"• {s}")

                with col3:
                    st.error("📖 Cần học thêm")
                    if result["need_to_learn"]:
                        for s, pct in result["need_to_learn"]:
                            st.write(f"• **{s}** ({pct}%)")
                    else:
                        st.write("✓ Đã đủ skills!")