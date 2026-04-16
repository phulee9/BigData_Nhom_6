import os
import sys
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

sys.path.append(str(Path(__file__).parent / "core"))
sys.path.append(str(Path(__file__).parent / "cv"))

from loader        import load_all_indexes
from recommend     import recommend_skills
from roadmap       import skill_gap_roadmap
from career_switch import career_switch_analysis
from cv_extractor  import read_pdf, extract_cv, dedup_skills


def input_block(tab_key: str):
    # Tra ve (job_title, skills) tu upload CV hoac nhap tay
    input_type = st.radio(
        "Chon cach nhap:",
        ["📄 Upload CV (PDF)", "✏️ Nhap tay"],
        horizontal = True,
        key        = f"radio_{tab_key}"
    )

    job_title, skills = "", []

    if input_type == "📄 Upload CV (PDF)":
        uploaded = st.file_uploader(
            "Chon file CV (PDF)", type=["pdf"], key=f"upload_{tab_key}"
        )

        if uploaded:
            st.success(f"{uploaded.name}")

            if st.button("🤖 Phan tich CV", key=f"analyze_{tab_key}", type="primary"):
                try:
                    with st.spinner("Dang doc PDF..."):
                        cv_text = read_pdf(uploaded)

                    with st.spinner("Groq dang extract skills..."):
                        data = extract_cv(cv_text)

                    if data:
                        st.session_state[f"title_{tab_key}"]  = data.get("vi_tri_ung_tuyen", "")
                        st.session_state[f"skills_{tab_key}"] = dedup_skills(data.get("skills", []))

                except Exception as e:
                    st.error(f"[LOI] {e}")

        if st.session_state.get(f"title_{tab_key}"):
            job_title = st.session_state[f"title_{tab_key}"]
            skills    = st.session_state[f"skills_{tab_key}"]

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Vi tri", job_title)
            with col2:
                st.metric("Skills", len(skills))

            for i, s in enumerate(skills, 1):
                st.write(f"{i}. **{s}**")

    else:
        job_title = st.text_input(
            "Vi tri ung tuyen",
            placeholder = "VD: backend developer...",
            key         = f"title_input_{tab_key}"
        ).lower().strip()

        skills = [
            s.strip().lower()
            for s in st.text_area(
                "Skills hien co (cach nhau bang dau phay)",
                placeholder = "VD: python, sql, docker",
                height      = 100,
                key         = f"skills_input_{tab_key}"
            ).split(",")
            if s.strip()
        ]

    return job_title, skills


# Cau hinh trang
st.set_page_config(page_title="Skill Recommender", page_icon="🎯", layout="centered")
st.title("🎯 Skill Recommender")
st.caption("He thong goi y ky nang dua tren 812,102 tin tuyen dung")


# Load ca 2 index 1 lan duy nhat khi khoi dong
@st.cache_resource
def get_indexes():
    return load_all_indexes()

with st.spinner("Dang khoi dong he thong..."):
    index_old, df_old, index_new, df_new = get_indexes()

# Hien thi so luong jobs tu ca 2 nguon
total_jobs = index_old.ntotal + (index_new.ntotal if index_new else 0)
st.success(f"San sang! {total_jobs:,} jobs trong he thong")
st.divider()

tab1, tab2, tab3 = st.tabs(["🔍 Goi y skills", "📚 Lo trinh hoc", "🔄 Chuyen huong nghe"])


with tab1:
    st.subheader("Goi y skills con thieu")
    job_title_1, skills_1 = input_block("tab1")
    st.divider()

    if st.button("🔍 Goi y", key="btn1", type="primary"):
        if not job_title_1:
            st.warning("Vui long nhap vi tri ung tuyen!")
        elif not skills_1:
            st.warning("Vui long nhap skills hien co!")
        else:
            with st.spinner("Dang phan tich..."):
                result = recommend_skills(
                    cv_skills  = skills_1,
                    job_title  = job_title_1,
                    index_old  = index_old,
                    df_old     = df_old,
                    index_new  = index_new,
                    df_new     = df_new,
                    top_k      = 150,
                    top_skills = 10
                )

            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Jobs cu", result["total_old"])
            with col2:
                st.metric("Jobs moi", result["total_new"])
            with col3:
                st.metric("Skills goi y", len(result["skills_goi_y"]))

            st.subheader("📌 Job titles gan nhat")
            for i, (t, s) in enumerate(
                zip(result["job_titles_gan_nhat"], result["top_scores"]), 1
            ):
                st.write(f"{i}. **{t}** (do tuong dong: {s:.2f})")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("✅ Skills da co")
                for s in result["skills_da_co"]:
                    st.write(f"• {s}")
            with col2:
                st.subheader("📈 Skills nen hoc them")
                for i, item in enumerate(result["skills_goi_y"], 1):
                    st.write(f"{i}. **{item['skill']}** — score: {item['score']}")
                    st.progress(min(item["score"], 1.0))


with tab2:
    st.subheader("Lo trinh hoc skills")
    job_title_2, skills_2 = input_block("tab2")
    st.divider()

    if st.button("📚 Xem lo trinh", key="btn2", type="primary"):
        if not job_title_2:
            st.warning("Vui long nhap vi tri ung tuyen!")
        elif not skills_2:
            st.warning("Vui long nhap skills hien co!")
        else:
            with st.spinner("Dang phan tich..."):
                result = skill_gap_roadmap(
                    cv_skills = skills_2,
                    job_title = job_title_2,
                    df_old        = df_old,
                    index_old = index_old,
                    index_new = index_new,  # ← thêm
                    df_new    = df_new, 
                    top_n     = 5
                )

            if result.get("error"):
                st.error(result["error"])
            else:
                st.divider()
                st.metric("Jobs phan tich", f"{result['total_jobs']:,}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.error("🔴 MUST HAVE")
                    st.caption("Bat buoc phai co")
                    if result["must_have"]:
                        for item in result["must_have"]:
                            st.write(f"• **{item['skill']}** ({item['pct']}%)")
                    else:
                        st.write("Da du!")

                with col2:
                    st.warning("🟡 SHOULD HAVE")
                    st.caption("Nen co")
                    if result["should_have"]:
                        for item in result["should_have"]:
                            st.write(f"• **{item['skill']}** ({item['pct']}%)")
                    else:
                        st.write("Khong can!")

                with col3:
                    st.info("🔵 NICE TO HAVE")
                    st.caption("Them diem")
                    if result["nice_have"]:
                        for item in result["nice_have"]:
                            st.write(f"• **{item['skill']}** ({item['pct']}%)")
                    else:
                        st.write("Khong co!")


with tab3:
    st.subheader("Phan tich chuyen huong nghe nghiep")
    job_from, skills_3 = input_block("tab3")
    st.divider()

    job_to = st.text_input(
        "Vi tri muon chuyen sang",
        placeholder = "VD: devops engineer, data scientist...",
        key         = "job_to"
    )

    if st.button("🔄 Phan tich", key="btn3", type="primary"):
        if not job_from:
            st.warning("Vui long nhap vi tri hien tai!")
        elif not job_to:
            st.warning("Vui long nhap vi tri muon chuyen!")
        elif not skills_3:
            st.warning("Vui long nhap skills hien co!")
        else:
            with st.spinner("Dang phan tich..."):
                result = career_switch_analysis(
                    job_from  = job_from,
                    job_to    = job_to.lower().strip(),
                    cv_skills = skills_3,
                    df        = df_old,
                    top_n     = 20
                )

            if result.get("error"):
                st.error(result["error"])
            else:
                st.divider()
                match_pct = result["match_pct"]
                st.metric("Do phu hop voi vi tri moi", f"{match_pct}%")
                st.progress(match_pct / 100)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.success("✅ Skills CV phu hop")
                    if result["cv_match"]:
                        for s, pct in result["cv_match"]:
                            st.write(f"• **{s}** ({pct}%)")
                    else:
                        st.write("Chua co skills phu hop!")

                with col2:
                    st.info("⭐ Skills dac trung")
                    for s, pct in result["only_to_skills"][:5]:
                        st.write(f"• {s} ({pct}%)")

                with col3:
                    st.error("📖 Can hoc them")
                    if result["need_to_learn"]:
                        for s, pct in result["need_to_learn"]:
                            st.write(f"• **{s}** ({pct}%)")
                    else:
                        st.write("Da du skills!")