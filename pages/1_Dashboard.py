import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from db.queries import get_all_advisors, get_advisor_attendance, get_advisor_professions
from ai.feedback_parser import parse_feedback
from components.charts import horizontal_bar, pie_chart, heatmap, time_series

st.title("Advisor Pool — Pattern Analysis & Insights")
st.caption("Interactive dashboards revealing utilization trends, coverage gaps, and feedback insights across the entire advisor pool.")

# Load data
advisors = get_all_advisors()
attendance = get_advisor_attendance()
professions = get_advisor_professions()

tab1, tab2, tab3, tab4 = st.tabs([
    "Pool Overview", "Utilization Analysis", "Attendance & Feedback", "Coverage Gaps"
])

# ── Tab 1: Advisor Pool Overview ──
with tab1:
    st.caption("A snapshot of the full advisor pool — demographics, profession spread, geographic zones, and employment status.")
    total = len(advisors)
    active = (advisors["ACTIVE"] == "Y").sum()
    male = (advisors["GENDER"] == "M").sum()
    female = (advisors["GENDER"] == "F").sum()
    serving = (advisors["EMPLOYMENT_STATUS"] == "S").sum()
    retired = (advisors["EMPLOYMENT_STATUS"] == "R").sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Advisors", f"{total:,}")
    c2.metric("Active", f"{active:,}")
    c3.metric("Male / Female", f"{male:,} / {female:,}")
    c4.metric("Serving", f"{serving:,}")
    c5.metric("Retired", f"{retired:,}")

    col1, col2 = st.columns(2)

    with col1:
        # Profession distribution
        st.caption("Shows the top 20 professions by advisor count — helps identify which fields dominate the pool.")
        prof_dist = advisors["PROFESSION_NAME"].value_counts().head(20).reset_index()
        prof_dist.columns = ["Profession", "Count"]
        st.plotly_chart(
            horizontal_bar(prof_dist, "Count", "Profession", "Top 20 Professions"),
            use_container_width=True,
        )

    with col2:
        # Zone distribution
        st.caption("Geographic distribution of advisors across zones — highlights regional concentration or gaps.")
        zone_dist = advisors["ZONE_NAME"].value_counts().reset_index()
        zone_dist.columns = ["Zone", "Count"]
        st.plotly_chart(
            pie_chart(zone_dist, "Zone", "Count", "Zone Distribution"),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)

    with col3:
        st.caption("Breakdown by panel type (Academic vs Applied) — shows recruitment vs PT panel advisor availability.")
        pt_dist = advisors["PANEL_TYPE_DESC"].value_counts().reset_index()
        pt_dist.columns = ["Panel Type", "Count"]
        st.plotly_chart(
            pie_chart(pt_dist, "Panel Type", "Count", "Panel Type Split"),
            use_container_width=True,
        )

    with col4:
        st.caption("Serving vs Retired ratio — important for balancing active availability with experienced perspectives.")
        emp_dist = advisors["EMPLOYMENT_STATUS"].value_counts().reset_index()
        emp_dist.columns = ["Status", "Count"]
        emp_dist["Status"] = emp_dist["Status"].map({"S": "Serving", "R": "Retired", "RE": "Re-employed"})
        st.plotly_chart(
            pie_chart(emp_dist.dropna(), "Status", "Count", "Employment Status"),
            use_container_width=True,
        )


# ── Tab 2: Utilization Analysis ──
with tab2:
    st.subheader("The Utilization Problem")
    st.caption("A large portion of the advisor pool has never been called for interviews. This tab identifies under- and over-utilized advisors to enable fairer distribution.")

    times_called = advisors["NO_OF_TIMES_CALLED"].fillna(0)
    never_called = (times_called == 0).sum()
    pct_never = never_called / len(advisors) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Never Called", f"{never_called:,}", f"{pct_never:.0f}% of pool")
    c2.metric("Called 1-5 times", f"{((times_called >= 1) & (times_called <= 5)).sum():,}")
    c3.metric("Called 6+ times", f"{(times_called >= 6).sum():,}")

    # Histogram
    st.caption("Distribution of how many times advisors have been called — excludes the large 'never-called' group to show the spread among active advisors.")
    fig = px.histogram(
        advisors[advisors["NO_OF_TIMES_CALLED"] > 0],
        x="NO_OF_TIMES_CALLED",
        nbins=30,
        title="Distribution of Times Called (excluding never-called)",
        labels={"NO_OF_TIMES_CALLED": "Times Called"},
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # Utilization by profession
        st.caption("Which professions get called the most on average — reveals over-relied-upon specializations.")
        util_prof = advisors.groupby("PROFESSION_NAME").agg(
            total=("INDEX_NO", "count"),
            avg_calls=("NO_OF_TIMES_CALLED", "mean"),
        ).reset_index().sort_values("avg_calls", ascending=False).head(20)
        util_prof["avg_calls"] = util_prof["avg_calls"].round(2)
        st.plotly_chart(
            horizontal_bar(util_prof, "avg_calls", "PROFESSION_NAME",
                           "Avg Times Called by Profession (Top 20)"),
            use_container_width=True,
        )

    with col2:
        # Utilization heatmap: zone × top professions
        st.caption("Heatmap showing average call frequency by Zone and Profession — darker cells indicate heavier reliance on a particular zone-profession combination.")
        top_profs = advisors["PROFESSION_NAME"].value_counts().head(10).index
        heat_data = advisors[advisors["PROFESSION_NAME"].isin(top_profs)]
        heat_pivot = heat_data.pivot_table(
            index="ZONE_NAME", columns="PROFESSION_NAME",
            values="NO_OF_TIMES_CALLED", aggfunc="mean",
        ).fillna(0).round(1)
        st.plotly_chart(
            heatmap(heat_pivot, "Avg Utilization: Zone x Profession"),
            use_container_width=True,
        )

    # Top 25 most called
    st.caption("The most frequently called advisors — useful for identifying potential over-reliance and ensuring rotation.")
    top_called = advisors.nlargest(25, "NO_OF_TIMES_CALLED")[
        ["INDEX_NO", "ADVISOR_NAME", "PROFESSION_NAME", "ZONE_NAME",
         "EMPLOYMENT_STATUS", "NO_OF_TIMES_CALLED"]
    ]
    st.subheader("Top 25 Most Called Advisors")
    st.dataframe(top_called, use_container_width=True, hide_index=True)


# ── Tab 3: Attendance & Feedback ──
with tab3:
    st.subheader("Attendance & Feedback Analysis")
    st.caption("Tracks how often advisors attend panels and the quality of feedback they receive — key inputs for the AI scoring engine.")

    att = attendance.copy()
    att["ATND_DATE"] = pd.to_datetime(att["ATND_DATE"], errors="coerce")
    att["year"] = att["ATND_DATE"].dt.year

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Attendance Records", f"{len(att):,}")
    c2.metric("Unique Advisors Attended", f"{att['INDEX_NO'].nunique():,}")
    has_feedback = att["FEEDBACK"].notna() & (att["FEEDBACK"] != "")
    c3.metric("Records with Feedback", f"{has_feedback.sum():,}")

    col1, col2 = st.columns(2)

    with col1:
        # Attendance over time
        st.caption("Year-wise attendance volume — shows historical panel activity trends.")
        yearly = att.groupby("year").size().reset_index(name="count")
        yearly = yearly[yearly["year"] > 2000]
        st.plotly_chart(
            time_series(yearly, "year", "count", "Attendance Volume by Year"),
            use_container_width=True,
        )

    with col2:
        # Feedback score distribution
        st.caption("Distribution of normalized feedback scores (0 to 1). Numeric feedback like '2+3+4+5+6=20' and qualitative labels like 'Very Good' are both converted to a 0-1 scale.")
        att["feedback_score"] = att["FEEDBACK"].apply(parse_feedback)
        scored = att.dropna(subset=["feedback_score"])
        fig = px.histogram(
            scored, x="feedback_score", nbins=20,
            title="Feedback Score Distribution (normalized 0-1)",
            labels={"feedback_score": "Normalized Score"},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Average feedback by profession
    st.caption("Average feedback score by profession (minimum 10 feedback records) — identifies which professions consistently receive higher panel ratings.")
    scored_with_prof = scored.merge(
        advisors[["INDEX_NO", "PROFESSION_NAME"]], on="INDEX_NO", how="left"
    )
    avg_fb = scored_with_prof.groupby("PROFESSION_NAME")["feedback_score"].agg(
        ["mean", "count"]
    ).reset_index()
    avg_fb.columns = ["Profession", "Avg Score", "Feedback Count"]
    avg_fb = avg_fb[avg_fb["Feedback Count"] >= 10].sort_values("Avg Score", ascending=False).head(20)
    avg_fb["Avg Score"] = avg_fb["Avg Score"].round(3)

    st.plotly_chart(
        horizontal_bar(avg_fb, "Avg Score", "Profession", "Avg Feedback Score by Profession (min 10 records)"),
        use_container_width=True,
    )

    # Flagged advisors
    st.caption("Advisors flagged as 'Not-to-be-called' in feedback — these are excluded from future panel recommendations by the AI engine.")
    not_to_call = att[att["FEEDBACK"].str.lower().str.contains("not-to-be-called|not to be called", na=False)]
    st.metric("'Not-to-be-called' Flagged Records", len(not_to_call))


# ── Tab 4: Coverage Gaps ──
with tab4:
    st.subheader("Coverage Gap Analysis")
    st.caption("Identifies areas where the advisor pool is thin — by specialization, geography, or age — helping plan targeted recruitment.")

    col1, col2 = st.columns(2)

    with col1:
        # Profession × Zone coverage matrix
        st.caption("Advisor count by Profession and Zone — empty or low cells indicate gaps where no or very few advisors are available.")
        top_profs = advisors["PROFESSION_NAME"].value_counts().head(15).index
        coverage = advisors[advisors["PROFESSION_NAME"].isin(top_profs)]
        cov_pivot = coverage.pivot_table(
            index="PROFESSION_NAME", columns="ZONE_NAME",
            values="INDEX_NO", aggfunc="count",
        ).fillna(0).astype(int)
        st.plotly_chart(
            heatmap(cov_pivot, "Advisor Count: Profession x Zone"),
            use_container_width=True,
        )

    with col2:
        # Specializations with fewest advisors
        st.caption("Specializations with 5 or fewer advisors — critical gaps that may need new advisor empanelment.")
        spec_counts = professions.groupby("SPECILISATION_NAME").agg(
            advisor_count=("INDEX_NO", "nunique")
        ).reset_index().sort_values("advisor_count")
        low_specs = spec_counts[spec_counts["advisor_count"] <= 5].head(30)
        st.subheader(f"Specializations with <= 5 Advisors ({len(low_specs)} found)")
        st.dataframe(low_specs, use_container_width=True, hide_index=True)

    # Age distribution by top professions
    st.subheader("Age Distribution by Profession")
    st.caption("Box plots showing the age spread within each profession — helps identify aging specializations that may face a talent shortage.")
    age_data = advisors[advisors["PROFESSION_NAME"].isin(top_profs)].dropna(subset=["age"])
    if not age_data.empty:
        fig = px.box(
            age_data, x="PROFESSION_NAME", y="age",
            title="Age Distribution by Top 15 Professions",
            labels={"PROFESSION_NAME": "Profession", "age": "Age"},
        )
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)

    # Upcoming retirements (advisors aged 60-65)
    near_retirement = advisors[
        (advisors["age"] >= 60) & (advisors["age"] <= 65) & (advisors["EMPLOYMENT_STATUS"] == "S")
    ]
    retire_by_prof = near_retirement.groupby("PROFESSION_NAME").size().reset_index(name="Count")
    retire_by_prof = retire_by_prof.sort_values("Count", ascending=False).head(15)

    st.subheader(f"Serving Advisors Nearing Retirement (age 60-65): {len(near_retirement):,}")
    st.caption("Serving advisors aged 60-65 who may retire soon — professions with high counts here need succession planning.")
    st.plotly_chart(
        horizontal_bar(retire_by_prof, "Count", "PROFESSION_NAME",
                       "Nearing Retirement by Profession"),
        use_container_width=True,
    )
