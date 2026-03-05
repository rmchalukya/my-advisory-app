import streamlit as st
from components.state import init_session_state

st.set_page_config(
    page_title="APMS — Advisor Panel Management System",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

st.sidebar.title("APMS")
st.sidebar.caption("Advisor & Interview Panel Management System — UPSC")
st.sidebar.divider()
st.sidebar.markdown("""
**Navigation**

Use the pages in the sidebar to navigate:

1. **Dashboard** — Pattern analysis & insights
2. **Panel Creation** — Create panels with AI recommendations
3. **Panel Review** — Review and export created panels
4. **Advanced Analytics** — Deep-dive into pool health, operations, fairness & feedback
""")

st.title("APMS — Advisor Panel Management System")
st.markdown("### AI-Powered Proof of Concept")

st.markdown("""
Welcome to the APMS POC. This system demonstrates AI capabilities for UPSC's
Advisor and Interview Panel Management:

- **Smart Advisor Shortlisting** — AI scores and ranks advisors based on feedback, qualifications, seniority, and experience
- **Panel Optimization** — AI analyzes panel composition for gender balance, geographic diversity, experience mix, and expertise coverage
- **Pattern Analysis** — Interactive dashboards revealing utilization trends, coverage gaps, and feedback insights

Select a page from the sidebar to get started.
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Advisor Pool")
    try:
        from db.queries import get_all_advisors
        advisors = get_all_advisors()
        st.metric("Total Advisors", f"{len(advisors):,}")
        st.metric("Active", f"{(advisors['ACTIVE'] == 'Y').sum():,}")
    except Exception as e:
        st.error(f"Database connection error: {e}")

with col2:
    st.markdown("#### Professions")
    try:
        st.metric("Profession Categories", f"{advisors['PROFESSION_NAME'].nunique():,}")
        st.metric("Serving / Retired",
                   f"{(advisors['EMPLOYMENT_STATUS'] == 'S').sum():,} / "
                   f"{(advisors['EMPLOYMENT_STATUS'] == 'R').sum():,}")
    except Exception:
        st.info("Load dashboard for details")

with col3:
    st.markdown("#### AI Features")
    st.markdown("""
    - Composite Scoring (6 dimensions)
    - Panel Health Card (4 dimensions)
    - Coverage Gap Detection
    - Utilization Analysis
    """)
