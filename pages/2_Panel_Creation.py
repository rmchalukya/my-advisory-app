import streamlit as st
import pandas as pd
from datetime import date
from db.queries import (
    get_all_advisors, get_advisor_attendance, get_advisor_degrees,
    get_advisor_jobs, get_advisor_professions, get_profession_hierarchy,
    get_board_presidents,
)
from ai.recommender import shortlist_advisors
from ai.panel_optimizer import analyze_panel
from components.filters import (
    render_panel_type_filter, render_demographic_filters,
    render_profession_cascade, render_zone_filter, render_level_filter,
    build_filters_dict,
)
from components.charts import radar_chart, score_badge
from components.state import init_session_state, save_panels

init_session_state()

st.title("Create Advisor Panel")
st.caption("A 5-step wizard to build interview panels with AI-powered advisor recommendations and panel health analysis.")

# Progress bar
steps = ["Panel Details", "Board Setup", "Advisor Filters", "AI Shortlisting", "Summary"]
current = st.session_state.panel_step
st.progress((current - 1) / (len(steps) - 1))
st.caption(f"Step {current} of {len(steps)}: **{steps[current - 1]}**")

# Load data
advisors = get_all_advisors()
attendance = get_advisor_attendance()
degrees = get_advisor_degrees()
jobs = get_advisor_jobs()
prof_map = get_advisor_professions()
hierarchy = get_profession_hierarchy()

# ── Step 1: Panel Details ──
if current == 1:
    st.subheader("Step 1: Panel Details")
    st.caption("Define the basic panel parameters — type, file reference, and how many advisors and boards are needed.")

    panel_type = st.radio("Panel Type", ["Recruitment Panel", "PT Panel"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        file_no = st.text_input("File Number", placeholder="e.g. F.1/132(12)/2024-R.II/AC")
    with col2:
        if panel_type == "Recruitment Panel":
            post_name = st.text_input("Post Name", placeholder="e.g. Assistant Professor (Physics)")
        else:
            post_name = st.text_input("Exam Name", placeholder="e.g. Civil Services 2024")

    col3, col4 = st.columns(2)
    with col3:
        num_advisors = st.number_input("Total Advisors Needed", min_value=1, max_value=20, value=3)
    with col4:
        num_boards = st.number_input("Number of Boards", min_value=1, max_value=10, value=1)

    if st.button("Next: Board Setup", type="primary"):
        st.session_state.panel_data["panel_type"] = panel_type
        st.session_state.panel_data["file_no"] = file_no
        st.session_state.panel_data["post_name"] = post_name
        st.session_state.panel_data["num_advisors"] = num_advisors
        st.session_state.panel_data["num_boards"] = num_boards
        st.session_state.panel_step = 2
        st.rerun()

# ── Step 2: Board Setup ──
elif current == 2:
    st.subheader("Step 2: Board Setup")
    st.caption("Configure each interview board — assign a board president, set the number of advisors per board, and select interview dates.")

    presidents = get_board_presidents()
    num_boards = st.session_state.panel_data.get("num_boards", 1)
    total_needed = st.session_state.panel_data.get("num_advisors", 3)

    boards = []
    for i in range(num_boards):
        st.markdown(f"**Board {i + 1}**")
        col1, col2, col3 = st.columns(3)
        with col1:
            bp = st.selectbox(
                f"Board President",
                presidents["BOARD_PRESIDENT_NAME"].tolist(),
                key=f"bp_{i}",
            )
        with col2:
            n = st.number_input(
                f"Advisors Needed",
                min_value=1, max_value=20,
                value=min(total_needed, 3),
                key=f"nadv_{i}",
            )
        with col3:
            d = st.date_input(f"Interview Date", value=date.today(), key=f"date_{i}")
        boards.append({"president": bp, "num_advisors": n, "date": str(d)})
        st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back"):
            st.session_state.panel_step = 1
            st.rerun()
    with col2:
        if st.button("Next: Set Filters", type="primary"):
            st.session_state.panel_data["boards"] = boards
            st.session_state.panel_step = 3
            st.rerun()

# ── Step 3: Advisor Filters ──
elif current == 3:
    st.subheader("Step 3: Advisor Filters")
    st.caption("Narrow down the advisor pool using profession, demographics, zone, and level filters. The AI will score and rank advisors matching these criteria.")

    panel_type_filter = render_panel_type_filter()
    employment, gender, age_range = render_demographic_filters()

    st.divider()
    st.markdown("**Profession / Specialization**")
    prof_ids, spec_ids, super_spec_ids = render_profession_cascade(hierarchy)

    col1, col2 = st.columns(2)
    with col1:
        zone_names = render_zone_filter(advisors)
    with col2:
        level_names = render_level_filter(advisors)

    exclude_org = st.text_input(
        "Exclude Organization (optional)",
        placeholder="Advisors from this org will be excluded",
    )

    total_needed = sum(b["num_advisors"] for b in st.session_state.panel_data.get("boards", []))
    st.caption(f"The AI will show the top candidates as a multiple of the {total_needed} advisor(s) needed, giving you a wider pool to choose from.")
    multiplier = st.slider("Show top N candidates (multiplier)", 2, 5, 3)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back"):
            st.session_state.panel_step = 2
            st.rerun()
    with col2:
        if st.button("Run AI Shortlisting", type="primary"):
            filters = build_filters_dict(
                panel_type_filter, employment, gender, age_range,
                prof_ids, spec_ids, super_spec_ids,
                zone_names, level_names, exclude_org, advisors,
            )
            st.session_state.panel_data["filters"] = filters
            st.session_state.panel_data["multiplier"] = multiplier

            with st.spinner("AI is scoring and ranking advisors..."):
                result = shortlist_advisors(
                    advisors, attendance, degrees, jobs, prof_map,
                    filters, total_needed, multiplier,
                )
                st.session_state.shortlisted = result

            st.session_state.panel_step = 4
            st.rerun()

# ── Step 4: AI-Powered Shortlisting ──
elif current == 4:
    st.subheader("Step 4: AI-Powered Shortlisting")
    st.caption(
        "Advisors are scored on a 0-100 scale using 6 weighted dimensions: "
        "Feedback quality (30%), Educational qualification (25%), Pay grade (15%), "
        "Work experience (10%), Panel experience (10%), and Recency (10%). "
        "Green scores (70+) are strong, yellow (40-70) are moderate, red (<40) need review."
    )

    shortlisted = st.session_state.shortlisted
    if shortlisted is None or shortlisted.empty:
        st.warning("No advisors match the selected filters. Please go back and adjust.")
        if st.button("Back to Filters"):
            st.session_state.panel_step = 3
            st.rerun()
    else:
        st.info(f"Found **{len(shortlisted)}** advisors matching your criteria, ranked by AI score.")

        # Display columns
        display_cols = [
            "rank", "composite_score", "INDEX_NO", "PROFESSION_NAME",
            "DESIGNATION_DESC", "ORG_TYPE_DESC", "ZONE_NAME",
            "GENDER", "EMPLOYMENT_STATUS", "LEVEL_NAME",
            "NO_OF_TIMES_CALLED", "age",
            "feedback_score", "education_score", "pay_score",
        ]
        available_cols = [c for c in display_cols if c in shortlisted.columns]
        display_df = shortlisted[available_cols].copy()

        # Rename for display
        rename_map = {
            "rank": "Rank", "composite_score": "AI Score",
            "INDEX_NO": "ID", "PROFESSION_NAME": "Profession",
            "DESIGNATION_DESC": "Designation", "ORG_TYPE_DESC": "Org Type",
            "ZONE_NAME": "Zone", "GENDER": "Gender",
            "EMPLOYMENT_STATUS": "Employment", "LEVEL_NAME": "Level",
            "NO_OF_TIMES_CALLED": "Times Called", "age": "Age",
            "feedback_score": "Feedback", "education_score": "Education",
            "pay_score": "Pay Grade",
        }
        display_df = display_df.rename(columns=rename_map)

        # Score color formatting
        def highlight_score(val):
            if pd.isna(val):
                return ""
            if val >= 70:
                return "background-color: #d4edda"
            elif val >= 40:
                return "background-color: #fff3cd"
            return "background-color: #f8d7da"

        styled = display_df.style.applymap(highlight_score, subset=["AI Score"])
        st.dataframe(styled, use_container_width=True, hide_index=True, height=500)

        # Selection
        total_needed = sum(b["num_advisors"] for b in st.session_state.panel_data.get("boards", []))
        st.markdown(f"**Select {total_needed} advisors for the panel:**")

        # Auto-recommend button
        col_auto, col_manual = st.columns([1, 3])
        with col_auto:
            auto_select = st.button(f"AI: Auto-select Top {total_needed}", type="secondary")

        advisor_ids = shortlisted["INDEX_NO"].tolist()

        if auto_select:
            selected_ids = advisor_ids[:total_needed]
        else:
            selected_ids = st.multiselect(
                "Select advisors by ID",
                advisor_ids,
                default=advisor_ids[:total_needed],
                max_selections=total_needed * 2,  # allow some flexibility
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Filters"):
                st.session_state.panel_step = 3
                st.rerun()
        with col2:
            if st.button("Analyze Panel", type="primary") and selected_ids:
                selected_df = shortlisted[shortlisted["INDEX_NO"].isin(selected_ids)].copy()
                st.session_state.selected_advisors = selected_df
                st.session_state.panel_step = 5
                st.rerun()

# ── Step 5: Panel Summary + AI Analysis ──
elif current == 5:
    st.subheader("Step 5: Panel Summary & AI Health Card")
    st.caption("Review your final panel composition. The AI analyzes the panel across 4 diversity dimensions and flags any potential issues.")

    selected = st.session_state.selected_advisors
    panel_data = st.session_state.panel_data

    if selected is None or selected.empty:
        st.warning("No advisors selected.")
    else:
        # Panel info
        col1, col2, col3 = st.columns(3)
        col1.metric("Panel Type", panel_data.get("panel_type", ""))
        col2.metric("File Number", panel_data.get("file_no", ""))
        col3.metric("Advisors Selected", len(selected))

        st.divider()

        # Selected advisors table
        st.subheader("Selected Advisors")
        show_cols = ["INDEX_NO", "PROFESSION_NAME", "DESIGNATION_DESC",
                     "ZONE_NAME", "GENDER", "EMPLOYMENT_STATUS",
                     "composite_score"]
        available = [c for c in show_cols if c in selected.columns]
        st.dataframe(selected[available], use_container_width=True, hide_index=True)

        st.divider()

        # AI Panel Health Card
        st.subheader("AI Panel Health Card")
        st.caption(
            "The health card evaluates panel composition on 4 dimensions: "
            "**Gender Balance** (target: 20%+ female), "
            "**Zone Diversity** (geographic spread via Shannon entropy), "
            "**Experience Mix** (serving/retired balance and seniority range), "
            "**Expertise Coverage** (profession breadth). "
            "Higher scores indicate a more balanced and diverse panel."
        )

        health = analyze_panel(selected)

        col1, col2 = st.columns([1, 1])

        with col1:
            # Radar chart
            dim_labels = {
                "gender": "Gender Balance",
                "zone": "Zone Diversity",
                "experience": "Experience Mix",
                "expertise": "Expertise Coverage",
            }
            fig = radar_chart(dim_labels, {dim_labels[k]: v for k, v in health["scores"].items()})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Overall score
            st.markdown("### Overall Panel Score")
            st.markdown(score_badge(health["overall"]), unsafe_allow_html=True)
            st.markdown("")

            # Dimension breakdown
            for dim, label in dim_labels.items():
                score = health["scores"][dim]
                st.markdown(f"**{label}**: {score}/100")
                st.progress(score / 100)

        # Suggestions
        if health["suggestions"]:
            st.subheader("AI Suggestions")
            for s in health["suggestions"]:
                st.warning(s)

        # Conflicts
        if health["conflicts"]:
            st.subheader("Conflicts Detected")
            for c in health["conflicts"]:
                st.error(c)

        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Back to Selection"):
                st.session_state.panel_step = 4
                st.rerun()
        with col2:
            if st.button("Submit Panel", type="primary"):
                panel_record = {
                    **panel_data,
                    "selected_advisors": selected.to_dict("records"),
                    "health": health,
                }
                st.session_state.created_panels.append(panel_record)
                save_panels()
                st.success("Panel submitted successfully!")
                st.balloons()
        with col3:
            if st.button("Create New Panel"):
                st.session_state.panel_step = 1
                st.session_state.panel_data = {}
                st.session_state.shortlisted = None
                st.session_state.selected_advisors = None
                st.rerun()
