import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from db.queries import (
    get_all_advisors, get_advisor_attendance, get_advisor_degrees,
    get_advisor_jobs, get_panel_selection_summary,
    get_board_president_workload, get_advisor_cooccurrence,
)
from ai.feedback_parser import parse_feedback
from ai.remark_parser import parse_remark
from components.charts import (
    horizontal_bar, pie_chart, heatmap, time_series,
    grouped_bar, funnel_chart, stacked_bar,
)

st.title("Advanced Analytics")
st.caption("Deep-dive analytics uncovering dormant pool patterns, operational bottlenecks, fairness gaps, and feedback quality trends.")

# Load shared data
advisors = get_all_advisors()
attendance = get_advisor_attendance()

tab1, tab2, tab3, tab4 = st.tabs([
    "Pool Health & Quality",
    "Operations & Capacity",
    "Fairness & Equity",
    "Feedback Intelligence",
])


# ═══════════════════════════════════════════════════════════════
# Tab 1: Pool Health & Quality
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Dormant Pool Analysis")
    st.caption("Identifies active advisors with Normal status who have never been called — a large untapped resource for fairer panel distribution.")

    active_normal = advisors[
        (advisors["ACTIVE"] == "Y") &
        (advisors["ADVISOR_STATUS"] == "N")
    ]
    dormant = active_normal[active_normal["NO_OF_TIMES_CALLED"].fillna(0) == 0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Active-Normal Advisors", f"{len(active_normal):,}")
    c2.metric("Never Called (Dormant)", f"{len(dormant):,}")
    c3.metric("Dormant %", f"{len(dormant) / max(len(active_normal), 1) * 100:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        dorm_prof = dormant["PROFESSION_NAME"].value_counts().head(20).reset_index()
        dorm_prof.columns = ["Profession", "Dormant Count"]
        st.plotly_chart(
            horizontal_bar(dorm_prof, "Dormant Count", "Profession", "Dormant Advisors by Profession (Top 20)"),
            use_container_width=True,
        )
    with col2:
        dorm_zone = dormant["ZONE_NAME"].value_counts().reset_index()
        dorm_zone.columns = ["Zone", "Dormant Count"]
        st.plotly_chart(
            pie_chart(dorm_zone.dropna(), "Zone", "Dormant Count", "Dormant Advisors by Zone"),
            use_container_width=True,
        )

    st.divider()

    # ── Profile Completeness ──
    st.subheader("Profile Completeness")
    st.caption("Measures how many advisors have degree and job history data on file. The AI scoring engine assigns default scores to advisors with missing profiles, which may reduce recommendation accuracy.")

    degrees = get_advisor_degrees()
    jobs = get_advisor_jobs()

    has_degree = set(degrees["INDEX_NO"].unique())
    has_job = set(jobs["INDEX_NO"].unique())
    all_ids = set(advisors["INDEX_NO"].unique())

    both = has_degree & has_job
    degree_only = has_degree - has_job
    job_only = has_job - has_degree
    neither = all_ids - has_degree - has_job

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Full Profile (Degree + Job)", f"{len(both):,}")
    c2.metric("Degree Only", f"{len(degree_only):,}")
    c3.metric("Job Only", f"{len(job_only):,}")
    c4.metric("No Profile Data", f"{len(neither):,}")

    col1, col2 = st.columns(2)
    with col1:
        comp_data = pd.DataFrame({
            "Category": ["Full Profile", "Degree Only", "Job Only", "No Data"],
            "Count": [len(both), len(degree_only), len(job_only), len(neither)],
        })
        st.plotly_chart(
            pie_chart(comp_data, "Category", "Count", "Profile Completeness Distribution"),
            use_container_width=True,
        )
    with col2:
        # Completeness by profession
        adv_prof = advisors[["INDEX_NO", "PROFESSION_NAME"]].copy()
        adv_prof["has_degree"] = adv_prof["INDEX_NO"].isin(has_degree)
        adv_prof["has_job"] = adv_prof["INDEX_NO"].isin(has_job)
        adv_prof["complete"] = adv_prof["has_degree"] & adv_prof["has_job"]
        prof_comp = adv_prof.groupby("PROFESSION_NAME").agg(
            total=("INDEX_NO", "count"),
            complete=("complete", "sum"),
        ).reset_index()
        prof_comp["completeness_%"] = (prof_comp["complete"] / prof_comp["total"] * 100).round(1)
        prof_comp = prof_comp[prof_comp["total"] >= 50].sort_values("completeness_%", ascending=False).head(20)
        st.plotly_chart(
            horizontal_bar(prof_comp, "completeness_%", "PROFESSION_NAME",
                           "Profile Completeness % by Profession (min 50 advisors)"),
            use_container_width=True,
        )

    st.divider()

    # ── Retirement Pipeline ──
    st.subheader("Retirement Pipeline by Profession")
    st.caption("Shows the serving vs retired balance per profession. Professions with high retired % may face availability constraints; those heavily serving may have scheduling conflicts.")

    emp_prof = advisors.groupby(["PROFESSION_NAME", "EMPLOYMENT_STATUS"]).size().unstack(fill_value=0)
    if "S" in emp_prof.columns and "R" in emp_prof.columns:
        emp_prof["total"] = emp_prof.sum(axis=1)
        emp_prof["retired_%"] = (emp_prof.get("R", 0) / emp_prof["total"] * 100).round(1)
        emp_prof["serving_%"] = (emp_prof.get("S", 0) / emp_prof["total"] * 100).round(1)
        emp_prof = emp_prof.sort_values("retired_%", ascending=False).head(20).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            display_cols = ["PROFESSION_NAME", "total"]
            if "S" in emp_prof.columns:
                display_cols.append("S")
            if "R" in emp_prof.columns:
                display_cols.append("R")
            display_cols.extend(["serving_%", "retired_%"])
            st.dataframe(
                emp_prof[display_cols].rename(columns={
                    "PROFESSION_NAME": "Profession", "total": "Total",
                    "S": "Serving", "R": "Retired",
                }),
                use_container_width=True, hide_index=True,
            )
        with col2:
            chart_data = emp_prof[["PROFESSION_NAME", "S", "R"]].copy() if "R" in emp_prof.columns else emp_prof
            if "S" in chart_data.columns and "R" in chart_data.columns:
                st.plotly_chart(
                    stacked_bar(chart_data, "PROFESSION_NAME", ["S", "R"], ["Serving", "Retired"],
                                "Serving vs Retired by Profession"),
                    use_container_width=True,
                )


# ═══════════════════════════════════════════════════════════════
# Tab 2: Operations & Capacity
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Panel Approval Funnel")
    st.caption("Tracks the pipeline from panel creation to advisor selection to final approval. A large drop between stages signals operational bottlenecks.")

    panel_summary = get_panel_selection_summary()

    total_panels = len(panel_summary)
    total_assigned = panel_summary["advisor_count"].sum()
    total_selected = panel_summary["selected_count"].sum()
    total_approved = panel_summary["approved_count"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Panels", f"{total_panels:,}")
    c2.metric("Advisors Assigned", f"{total_assigned:,}")
    c3.metric("Selected", f"{total_selected:,}")
    c4.metric("Approved", f"{total_approved:,}", f"{total_approved / max(total_assigned, 1) * 100:.1f}% rate")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            funnel_chart(
                ["Assigned", "Selected", "Approved"],
                [int(total_assigned), int(total_selected), int(total_approved)],
                "Selection-to-Approval Funnel",
            ),
            use_container_width=True,
        )
    with col2:
        # Approval rate by year
        panel_summary["year"] = pd.to_datetime(panel_summary["CREATION_DATE"], errors="coerce").dt.year
        yearly = panel_summary.dropna(subset=["year"]).groupby("year").agg(
            assigned=("advisor_count", "sum"),
            approved=("approved_count", "sum"),
        ).reset_index()
        yearly = yearly[yearly["year"] >= 2008]
        yearly["approval_rate"] = (yearly["approved"] / yearly["assigned"].replace(0, np.nan) * 100).round(1)
        st.plotly_chart(
            time_series(yearly, "year", "approval_rate", "Approval Rate % by Year"),
            use_container_width=True,
        )

    st.divider()

    # ── Board President Workload ──
    st.subheader("Board President Workload")
    st.caption("Reveals workload distribution across board presidents. Severe imbalance means a few presidents handle most panels, risking burnout and bottlenecks.")

    bp_work = get_board_president_workload()
    bp_totals = bp_work.groupby("president").agg(
        total_panels=("panel_count", "sum"),
        total_advisors=("unique_advisors", "sum"),
    ).reset_index().sort_values("total_panels", ascending=False)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Board Presidents", f"{bp_totals['president'].nunique():,}")
    c2.metric("Avg Panels / President", f"{bp_totals['total_panels'].mean():.0f}")
    c3.metric("Max Panels (Single President)", f"{bp_totals['total_panels'].max():,}")

    col1, col2 = st.columns(2)
    with col1:
        top_bp = bp_totals.head(20)
        st.plotly_chart(
            horizontal_bar(top_bp, "total_panels", "president", "Top 20 Presidents by Panel Count"),
            use_container_width=True,
        )
    with col2:
        # Heatmap: president × year
        top10_pres = bp_totals.head(10)["president"].tolist()
        bp_heat = bp_work[bp_work["president"].isin(top10_pres)]
        bp_heat = bp_heat[bp_heat["year"] >= 2016]
        if not bp_heat.empty:
            pivot = bp_heat.pivot_table(
                index="president", columns="year", values="panel_count", aggfunc="sum",
            ).fillna(0).astype(int)
            st.plotly_chart(
                heatmap(pivot, "Top 10 Presidents — Panels per Year"),
                use_container_width=True,
            )

    st.divider()

    # ── Seasonal Capacity ──
    st.subheader("Seasonal Capacity Planner")
    st.caption("Shows monthly and quarterly patterns in panel activity. March-April is the peak interview season, while December-January is the quietest — useful for resource planning.")

    att = attendance.copy()
    att["ATND_DATE"] = pd.to_datetime(att["ATND_DATE"], errors="coerce")
    att["month"] = att["ATND_DATE"].dt.month
    att["year"] = att["ATND_DATE"].dt.year

    col1, col2 = st.columns(2)
    with col1:
        monthly = att.dropna(subset=["month"]).groupby("month").size().reset_index(name="count")
        month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                       7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
        monthly["month_name"] = monthly["month"].map(month_names)
        fig = px.bar(monthly, x="month_name", y="count", title="Attendance Volume by Month",
                     labels={"month_name": "Month", "count": "Attendance Records"}, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Year × Month heatmap
        ym = att.dropna(subset=["year", "month"])
        ym = ym[(ym["year"] >= 2010) & (ym["year"] <= 2025)]
        ym_pivot = ym.groupby(["year", "month"]).size().unstack(fill_value=0)
        ym_pivot.columns = [month_names.get(m, m) for m in ym_pivot.columns]
        st.plotly_chart(
            heatmap(ym_pivot, "Attendance Heatmap — Year x Month"),
            use_container_width=True,
        )

    # Quarterly panel creation
    panel_summary["quarter"] = pd.to_datetime(panel_summary["CREATION_DATE"], errors="coerce").dt.quarter
    panel_summary["year_q"] = panel_summary.get("year", pd.to_datetime(panel_summary["CREATION_DATE"], errors="coerce").dt.year)
    qtr = panel_summary.dropna(subset=["quarter", "year_q"])
    qtr = qtr[(qtr["year_q"] >= 2010) & (qtr["year_q"] <= 2025)]
    qtr_agg = qtr.groupby(["year_q", "quarter"]).size().reset_index(name="panels")
    qtr_agg["period"] = qtr_agg["year_q"].astype(int).astype(str) + " Q" + qtr_agg["quarter"].astype(int).astype(str)
    qtr_agg = qtr_agg.sort_values(["year_q", "quarter"])
    st.plotly_chart(
        time_series(qtr_agg, "period", "panels", "Panel Creation by Quarter"),
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════
# Tab 3: Fairness & Equity
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Geographic Equity Index")
    st.caption("Compares each zone's share of the advisor pool vs its share of actual panel attendance. A positive gap means the zone is over-utilized; negative means under-utilized.")

    # Pool share
    pool_zone = advisors["ZONE_NAME"].value_counts().reset_index()
    pool_zone.columns = ["Zone", "Pool Count"]
    pool_zone["Pool %"] = (pool_zone["Pool Count"] / pool_zone["Pool Count"].sum() * 100).round(1)

    # Attendance share
    att_zone = attendance.merge(advisors[["INDEX_NO", "ZONE_NAME"]], on="INDEX_NO", how="left")
    att_zone_counts = att_zone["ZONE_NAME"].value_counts().reset_index()
    att_zone_counts.columns = ["Zone", "Attendance Count"]
    att_zone_counts["Attendance %"] = (att_zone_counts["Attendance Count"] / att_zone_counts["Attendance Count"].sum() * 100).round(1)

    equity = pool_zone.merge(att_zone_counts, on="Zone", how="outer").fillna(0)
    equity["Gap (pp)"] = (equity["Attendance %"] - equity["Pool %"]).round(1)
    equity = equity.sort_values("Gap (pp)", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(equity, use_container_width=True, hide_index=True)
    with col2:
        eq_chart = equity[equity["Zone"].notna() & (equity["Zone"] != "")].head(8)
        st.plotly_chart(
            grouped_bar(eq_chart, "Zone", ["Pool %", "Attendance %"],
                        ["Pool Share %", "Attendance Share %"],
                        "Pool Share vs Attendance Share by Zone"),
            use_container_width=True,
        )

    # Gender × Zone
    st.markdown("**Gender Representation by Zone**")
    st.caption("Female advisor % per zone — East and North East lag significantly behind the national average.")
    gender_zone = advisors.groupby(["ZONE_NAME", "GENDER"]).size().unstack(fill_value=0)
    if "F" in gender_zone.columns and "M" in gender_zone.columns:
        gender_zone["total"] = gender_zone.sum(axis=1)
        gender_zone["Female %"] = (gender_zone["F"] / gender_zone["total"] * 100).round(1)
        gender_zone = gender_zone.reset_index().sort_values("Female %", ascending=False)
        display = gender_zone[["ZONE_NAME", "M", "F", "total", "Female %"]].rename(
            columns={"ZONE_NAME": "Zone", "M": "Male", "F": "Female", "total": "Total"}
        )
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # ── Co-occurrence ──
    st.subheader("Advisor Co-occurrence Detection")
    st.caption("Identifies advisor pairs who repeatedly serve together on the same panels. High co-occurrence may indicate 'comfort zone' assignments rather than fair rotation.")

    with st.spinner("Computing co-occurrence pairs (this may take a moment)..."):
        cooccur = get_advisor_cooccurrence()

    if cooccur.empty:
        st.info("No co-occurring pairs found with 5+ joint appearances.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Pairs with 5+ Co-occurrences", f"{len(cooccur):,}")
        c2.metric("Max Co-occurrence", f"{cooccur['times_together'].max():,}")

        st.dataframe(
            cooccur.rename(columns={
                "advisor1": "Advisor 1", "advisor2": "Advisor 2",
                "times_together": "Times Together",
            }),
            use_container_width=True, hide_index=True,
        )

    st.divider()

    # ── Org Type Utilization ──
    st.subheader("Organization Type Utilization")
    st.caption("Shows how often advisors from each org type get called. Hospital and State Service advisors are called far more per capita, while PSU advisors are severely under-utilized.")

    org_util = advisors.groupby("ORG_TYPE_DESC").agg(
        pool_count=("INDEX_NO", "count"),
        avg_calls=("NO_OF_TIMES_CALLED", "mean"),
    ).reset_index().sort_values("avg_calls", ascending=False)
    org_util["avg_calls"] = org_util["avg_calls"].round(2)
    org_util = org_util[org_util["pool_count"] >= 20]

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(
            org_util.rename(columns={
                "ORG_TYPE_DESC": "Org Type", "pool_count": "Pool Count",
                "avg_calls": "Avg Times Called",
            }),
            use_container_width=True, hide_index=True,
        )
    with col2:
        st.plotly_chart(
            horizontal_bar(org_util.head(15), "avg_calls", "ORG_TYPE_DESC",
                           "Avg Times Called by Org Type"),
            use_container_width=True,
        )


# ═══════════════════════════════════════════════════════════════
# Tab 4: Feedback Intelligence
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Feedback Grade Inflation")
    st.caption("Tracks average feedback scores over time. A steady upward trend from ~37 (2010) to ~42 (2024) may indicate genuine improvement or systematic grade inflation.")

    att_fb = attendance.copy()
    att_fb["ATND_DATE"] = pd.to_datetime(att_fb["ATND_DATE"], errors="coerce")
    att_fb["year"] = att_fb["ATND_DATE"].dt.year
    att_fb["feedback_score"] = att_fb["FEEDBACK"].apply(parse_feedback)

    scored = att_fb.dropna(subset=["feedback_score"])
    scored["raw_score"] = scored["feedback_score"] * 50  # convert back to 0-50 scale

    # Year-over-year trend
    yearly_fb = scored[scored["year"] >= 2010].groupby("year")["raw_score"].agg(
        ["mean", "count"]
    ).reset_index()
    yearly_fb.columns = ["Year", "Avg Score", "Records"]
    yearly_fb["Avg Score"] = yearly_fb["Avg Score"].round(2)

    col1, col2 = st.columns(2)
    with col1:
        if len(yearly_fb) >= 2:
            earliest = yearly_fb[yearly_fb["Records"] >= 100].iloc[0]
            latest = yearly_fb[yearly_fb["Records"] >= 100].iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{int(earliest['Year'])} Avg", f"{earliest['Avg Score']:.1f} / 50")
            c2.metric(f"{int(latest['Year'])} Avg", f"{latest['Avg Score']:.1f} / 50")
            c3.metric("Change", f"+{latest['Avg Score'] - earliest['Avg Score']:.1f}",
                       f"{(latest['Avg Score'] - earliest['Avg Score']) / earliest['Avg Score'] * 100:.1f}%")

        st.plotly_chart(
            time_series(yearly_fb, "Year", "Avg Score", "Average Feedback Score by Year (out of 50)"),
            use_container_width=True,
        )

    with col2:
        # Uniform scoring detection
        st.markdown("**Uniform Scoring Detection**")
        st.caption("Feedback where evaluators give identical marks across all dimensions (e.g., 8+8+8+8+8=40). High prevalence suggests rubber-stamping rather than differentiated evaluation.")

        def is_uniform(fb):
            if not fb or not isinstance(fb, str):
                return False
            import re
            m = re.match(r'^(\d+)(?:\+\1)+(?:=\d+)?$', fb.strip())
            return m is not None

        att_fb["is_uniform"] = att_fb["FEEDBACK"].apply(is_uniform)
        has_fb = att_fb[att_fb["FEEDBACK"].notna() & (att_fb["FEEDBACK"] != "")]
        uniform_count = has_fb["is_uniform"].sum()
        total_fb = len(has_fb)

        c1, c2 = st.columns(2)
        c1.metric("Uniform Scores", f"{uniform_count:,}")
        c2.metric("% of All Feedback", f"{uniform_count / max(total_fb, 1) * 100:.1f}%")

        # Feedback format breakdown
        def classify_format(fb):
            if not fb or not isinstance(fb, str) or fb.strip() == "":
                return "No Feedback"
            import re
            if re.match(r'^\d+(?:\+\d+){4}=\d+$', fb.strip()):
                return "5-Dimension Numeric"
            if re.match(r'^\d+(?:\+\d+)=\d+$', fb.strip()):
                return "2-Dimension Numeric"
            if re.match(r'^\d+$', fb.strip()):
                return "Single Number"
            return "Qualitative"

        att_fb["format"] = att_fb["FEEDBACK"].apply(classify_format)
        fmt_dist = att_fb["format"].value_counts().reset_index()
        fmt_dist.columns = ["Format", "Count"]
        st.plotly_chart(
            pie_chart(fmt_dist, "Format", "Count", "Feedback Format Breakdown"),
            use_container_width=True,
        )

    st.divider()

    # ── Remark Suitability ──
    st.subheader("Remark-Based Suitability Signals")
    st.caption("The REMARK field contains structured suitability assessments (e.g., 'suitable for PT board') that are currently unused by the AI engine. Parsing these unlocks direct board-matching signals.")

    att_fb["suitability"] = att_fb["REMARK"].apply(parse_remark)
    has_remark = att_fb[att_fb["suitability"].notna()]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Attendance Records", f"{len(att_fb):,}")
    c2.metric("With Suitability Signal", f"{len(has_remark):,}")
    c3.metric("Signal Coverage", f"{len(has_remark) / max(len(att_fb), 1) * 100:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        suit_dist = has_remark["suitability"].value_counts().reset_index()
        suit_dist.columns = ["Category", "Count"]
        label_map = {
            "suitable_all": "Suitable for All Boards",
            "suitable_pt": "Suitable for PT Board",
            "suitable_recruitment": "Suitable for Recruitment",
            "suitable_specialization": "Suitable for Specialization",
            "resource_person": "Resource Person",
            "not_suitable": "Not Suitable",
            "positive": "Positive (Generic)",
        }
        suit_dist["Category"] = suit_dist["Category"].map(label_map).fillna(suit_dist["Category"])
        st.plotly_chart(
            pie_chart(suit_dist, "Category", "Count", "Suitability Signal Distribution"),
            use_container_width=True,
        )

    with col2:
        # Top advisors with suitability signals
        suit_advisors = has_remark.groupby("INDEX_NO")["suitability"].agg(
            signal_count="count",
            categories=lambda x: ", ".join(sorted(set(x))),
        ).reset_index().sort_values("signal_count", ascending=False).head(20)
        suit_advisors = suit_advisors.merge(
            advisors[["INDEX_NO", "PROFESSION_NAME", "ZONE_NAME"]], on="INDEX_NO", how="left"
        )
        st.dataframe(
            suit_advisors.rename(columns={
                "INDEX_NO": "Advisor ID", "signal_count": "Signals",
                "categories": "Categories", "PROFESSION_NAME": "Profession",
                "ZONE_NAME": "Zone",
            }),
            use_container_width=True, hide_index=True,
        )
