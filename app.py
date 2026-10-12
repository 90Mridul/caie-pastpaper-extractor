import streamlit as st
import os
import io
import zipfile
from downloader import fetch_pair, register_active_file, unregister_active_file, clear_all_active_files
from extractor import CAIEExtractor

st.set_page_config(
    page_title="CAIE Past Paper & Mark Scheme Extractor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .header-card {
        padding: 20px 24px;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 20px;
    }
    .badge-sub {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
        background-color: #3b82f6;
        color: white;
        margin-right: 8px;
    }
    .badge-meta {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 500;
        background-color: #475569;
        color: #f1f5f9;
        margin-right: 6px;
    }
    img {
        border-radius: 8px;
        box-shadow: 0 4px 8px -1px rgba(0, 0, 0, 0.3);
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

SUBJECTS = {
    "9709 - Mathematics": "9709",
    "9702 - Physics": "9702",
    "9701 - Chemistry": "9701",
    "9618 - Computer Science": "9618",
    "Custom Subject Code": "custom"
}

SESSIONS = {
    "October / November (Winter - w)": "w",
    "May / June (Summer - s)": "s",
    "February / March (Spring - m)": "m"
}

YEARS = [str(y) for y in range(2025, 2015, -1)]

if "extractor" not in st.session_state:
    st.session_state.extractor = None
if "current_paper_id" not in st.session_state:
    st.session_state.current_paper_id = None
if "loaded_files" not in st.session_state:
    st.session_state.loaded_files = []
if "q_num_input" not in st.session_state:
    st.session_state.q_num_input = 1

# Refresh active status of currently open files
if st.session_state.loaded_files:
    for f in st.session_state.loaded_files:
        register_active_file(f)

# SIDEBAR
with st.sidebar:
    st.title("📑 Exam Parameters")
    
    subj_choice = st.selectbox("Subject", list(SUBJECTS.keys()), index=0)
    if subj_choice == "Custom Subject Code":
        subject_code = st.text_input("Enter 4-digit Syllabus Code", value="9708")
    else:
        subject_code = SUBJECTS[subj_choice]

    col_yr, col_sess = st.columns(2)
    with col_yr:
        selected_year = st.selectbox("Year", YEARS, index=YEARS.index("2022") if "2022" in YEARS else 0)
    with col_sess:
        sess_label = st.selectbox("Series", list(SESSIONS.keys()), index=0)
        selected_session = SESSIONS[sess_label]

    paper_num = st.text_input("Paper Variant (e.g. 12, 42, 22)", value="12")
    
    st.markdown("### 🎯 Question Number")
    q_input = st.number_input(
        "Enter Question Number to Extract",
        min_value=1,
        max_value=30,
        value=st.session_state.q_num_input,
        step=1
    )
    st.session_state.q_num_input = q_input

    paper_key = f"{subject_code}_{selected_session}{selected_year[-2:]}_{paper_num}"

    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_extract = st.button("🚀 Extract", type="primary", use_container_width=True)
    with col_btn2:
        btn_clear = st.button("🗑️ Clear", use_container_width=True)

    if btn_clear:
        if st.session_state.extractor:
            try:
                st.session_state.extractor.close()
            except Exception:
                pass
        for f in st.session_state.loaded_files:
            unregister_active_file(f)
        st.session_state.loaded_files = []
        st.session_state.extractor = None
        st.session_state.current_paper_id = None
        st.rerun()

    st.caption("⏱️ **Auto-clean Enabled**:\nFiles delete automatically 10 minutes after you clear them or switch papers.")

# Main Header
st.markdown("""
<div class="header-card">
    <h2 style="margin:0; font-size: 24px; color:#f8fafc;">A Level CAIE Question & Mark Scheme Extractor</h2>
    <p style="margin:4px 0 0 0; color:#94a3b8; font-size:14px;">
        Direct extraction of the exact question and corresponding marking scheme for Cambridge A Levels.
    </p>
</div>
""", unsafe_allow_html=True)

# Extraction Trigger
if btn_extract or (st.session_state.current_paper_id != paper_key and st.session_state.current_paper_id is not None):
    # Unregister previous files if switching papers
    if st.session_state.extractor:
        try:
            st.session_state.extractor.close()
        except Exception:
            pass
    for f in st.session_state.loaded_files:
        unregister_active_file(f)
    st.session_state.loaded_files = []

    with st.spinner(f"Loading {paper_key} (QP & Mark Scheme)..."):
        qp_path, ms_path, msg = fetch_pair(
            subject_code=subject_code,
            session=selected_session,
            year=selected_year,
            paper_variant=paper_num
        )
        if not qp_path:
            st.error(f"❌ {msg}")
            st.session_state.extractor = None
            st.session_state.current_paper_id = None
        else:
            try:
                ext = CAIEExtractor(qp_path, ms_path)
                st.session_state.extractor = ext
                st.session_state.current_paper_id = paper_key
                st.session_state.loaded_files = [qp_path, ms_path]
                register_active_file(qp_path)
                register_active_file(ms_path)
            except Exception as e:
                st.error(f"Failed to parse PDF: {e}")
                st.session_state.extractor = None
                st.session_state.current_paper_id = None

ext: Optional[CAIEExtractor] = st.session_state.extractor

if ext:
    active_q = int(st.session_state.q_num_input)
    avail = ext.get_available_questions()
    
    top1, top2 = st.columns([3, 1])
    with top1:
        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <span class="badge-sub">{subject_code}</span>
            <span class="badge-meta">{selected_session.upper()}{selected_year[-2:]}</span>
            <span class="badge-meta">Paper {paper_num}</span>
            <span class="badge-meta" style="background-color:#10b981;">Question {active_q}</span>
            <span style="color:#94a3b8; font-size: 13px; margin-left: 8px;">Available questions: {avail}</span>
        </div>
        """, unsafe_allow_html=True)

    qp_images = ext.render_question_images(active_q)
    ms_images = ext.render_mark_scheme_images(active_q)

    with top2:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for idx, img in enumerate(qp_images):
                b = io.BytesIO()
                img.save(b, format="PNG")
                z.writestr(f"{paper_key}_Q{active_q}_part{idx+1}.png", b.getvalue())
            for idx, img in enumerate(ms_images):
                b = io.BytesIO()
                img.save(b, format="PNG")
                z.writestr(f"{paper_key}_Q{active_q}_MS_p{idx+1}.png", b.getvalue())
        zip_buf.seek(0)

        st.download_button(
            label=f"💾 Save Q{active_q} (ZIP)",
            data=zip_buf,
            file_name=f"{paper_key}_Q{active_q}.zip",
            mime="application/zip",
            use_container_width=True
        )

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader(f"📝 Question {active_q}")
        if not qp_images:
            st.warning(f"Question {active_q} could not be found in this Question Paper.")
        else:
            for img in qp_images:
                st.image(img, use_container_width=True)

    with col_right:
        st.subheader(f"✅ Mark Scheme for Question {active_q}")
        if not ms_images:
            st.warning(f"Mark scheme entry for Question {active_q} not found.")
        else:
            for img in ms_images:
                st.image(img, use_container_width=True)

else:
    st.info("👈 Enter the **Subject**, **Year**, **Series**, **Paper Variant**, and **Question Number** in the left sidebar, then click **🚀 Extract**.")
