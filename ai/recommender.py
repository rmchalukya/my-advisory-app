import pandas as pd
from ai.scoring import compute_advisor_scores


def shortlist_advisors(
    advisors_df,
    attendance_df,
    degrees_df,
    jobs_df,
    advisor_professions_df,
    filters,
    num_needed,
    multiplier=3,
):
    """
    Filter and score advisors, return top candidates.

    Parameters
    ----------
    advisors_df : Full advisor DataFrame
    attendance_df : Attendance DataFrame
    degrees_df : Degrees DataFrame
    jobs_df : Jobs DataFrame
    advisor_professions_df : Advisor-profession mapping
    filters : dict with keys:
        panel_type: "ACADEMIC" | "APPLIED" | "BOTH" | None
        employment: "S" | "R" | "BOTH" | None
        gender: "M" | "F" | "BOTH" | None
        age_min: int | None
        age_max: int | None
        profession_ids: list[int] | None
        specialisation_ids: list[int] | None
        super_specialisation_ids: list[int] | None
        zone_ids: list[int] | None
        level_ids: list[int] | None
        exclude_org_name: str | None
    num_needed : Number of advisors needed
    multiplier : How many times num_needed to return (default 3x)

    Returns
    -------
    DataFrame with filtered advisors + scores, ranked by composite_score
    """
    df = advisors_df.copy()

    # Filter: only normal status, not vigilance-flagged
    df = df[df["ADVISOR_STATUS"] == "N"]
    df = df[df["Vigilance"] == 0]

    # Panel type
    if filters.get("panel_type") and filters["panel_type"] != "BOTH":
        df = df[df["PANEL_TYPE_DESC"] == filters["panel_type"]]

    # Employment
    if filters.get("employment") and filters["employment"] != "BOTH":
        df = df[df["EMPLOYMENT_STATUS"] == filters["employment"]]

    # Gender
    if filters.get("gender") and filters["gender"] != "BOTH":
        df = df[df["GENDER"] == filters["gender"]]

    # Age range
    if filters.get("age_min") is not None:
        df = df[(df["age"].isna()) | (df["age"] >= filters["age_min"])]
    if filters.get("age_max") is not None:
        df = df[(df["age"].isna()) | (df["age"] <= filters["age_max"])]

    # Zone
    if filters.get("zone_ids"):
        df = df[df["OFFICE_ZONE_ID"].isin(filters["zone_ids"])]

    # Level
    if filters.get("level_ids"):
        df = df[df["LEVEL_ID"].isin(filters["level_ids"])]

    # Exclude organization
    if filters.get("exclude_org_name"):
        df = df[df["ORG_INST_UNIV_OTH_NAME"] != filters["exclude_org_name"]]

    # Profession/Specialisation/Super-specialisation filter via advisor_professions
    prof_filter_needed = (
        filters.get("profession_ids")
        or filters.get("specialisation_ids")
        or filters.get("super_specialisation_ids")
    )
    if prof_filter_needed:
        ap = advisor_professions_df.copy()
        if filters.get("profession_ids"):
            ap = ap[ap["PROFESSION_ID"].isin(filters["profession_ids"])]
        if filters.get("specialisation_ids"):
            ap = ap[ap["SPECILISATION_ID"].isin(filters["specialisation_ids"])]
        if filters.get("super_specialisation_ids"):
            ap = ap[ap["SUPER_SPECILISATION_ID"].isin(filters["super_specialisation_ids"])]
        matching_advisors = ap["INDEX_NO"].unique()
        df = df[df["INDEX_NO"].isin(matching_advisors)]

    if df.empty:
        return df

    # Compute scores
    scores = compute_advisor_scores(df, attendance_df, degrees_df, jobs_df)
    df = df.merge(
        scores[["INDEX_NO", "composite_score", "feedback_score", "education_score",
                "pay_score", "experience_score", "panel_exp_score", "recency_score"]],
        on="INDEX_NO",
        how="left",
    )
    df["composite_score"] = df["composite_score"].fillna(0)

    # Sort and limit
    df = df.sort_values("composite_score", ascending=False)
    limit = num_needed * multiplier
    df = df.head(limit)

    # Add rank
    df = df.reset_index(drop=True)
    df["rank"] = df.index + 1

    return df
