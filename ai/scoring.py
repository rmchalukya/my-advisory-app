import pandas as pd
import numpy as np
from config import SCORING_WEIGHTS, NEUTRAL_SCORE
from ai.feedback_parser import parse_feedback


def compute_advisor_scores(advisors_df, attendance_df, degrees_df, jobs_df):
    """
    Compute composite scores (0-100) for each advisor.

    Parameters
    ----------
    advisors_df : DataFrame from get_all_advisors()
    attendance_df : DataFrame from get_advisor_attendance()
    degrees_df : DataFrame from get_advisor_degrees()
    jobs_df : DataFrame from get_advisor_jobs()

    Returns
    -------
    DataFrame with INDEX_NO and score columns added to advisors_df
    """
    scores = advisors_df[["INDEX_NO"]].copy()

    # 1. Feedback score (0-1)
    feedback_scores = _compute_feedback_scores(attendance_df)
    scores = scores.merge(feedback_scores, on="INDEX_NO", how="left")
    scores["feedback_score"] = scores["feedback_score"].fillna(NEUTRAL_SCORE)

    # 2. Education score (0-1)
    edu_scores = _compute_education_scores(degrees_df)
    scores = scores.merge(edu_scores, on="INDEX_NO", how="left")
    scores["education_score"] = scores["education_score"].fillna(0.3)

    # 3. Pay grade score (0-1)
    pay_scores = _compute_pay_scores(advisors_df)
    scores = scores.merge(pay_scores, on="INDEX_NO", how="left")
    scores["pay_score"] = scores["pay_score"].fillna(0.3)

    # 4. Experience score (0-1)
    exp_scores = _compute_experience_scores(jobs_df)
    scores = scores.merge(exp_scores, on="INDEX_NO", how="left")
    scores["experience_score"] = scores["experience_score"].fillna(0.3)

    # 5. Panel experience score (0-1)
    panel_scores = _compute_panel_experience_scores(attendance_df)
    scores = scores.merge(panel_scores, on="INDEX_NO", how="left")
    scores["panel_exp_score"] = scores["panel_exp_score"].fillna(0.0)

    # 6. Recency score (0-1)
    recency_scores = _compute_recency_scores(attendance_df)
    scores = scores.merge(recency_scores, on="INDEX_NO", how="left")
    scores["recency_score"] = scores["recency_score"].fillna(NEUTRAL_SCORE)

    # Composite score (0-100)
    w = SCORING_WEIGHTS
    scores["composite_score"] = (
        scores["feedback_score"] * w["feedback"]
        + scores["education_score"] * w["education"]
        + scores["pay_score"] * w["pay_grade"]
        + scores["experience_score"] * w["experience"]
        + scores["panel_exp_score"] * w["panel_experience"]
        + scores["recency_score"] * w["recency"]
    ) * 100

    scores["composite_score"] = scores["composite_score"].round(1).clip(0, 100)

    return scores


def _compute_feedback_scores(attendance_df):
    """Average normalized feedback per advisor."""
    if attendance_df.empty:
        return pd.DataFrame(columns=["INDEX_NO", "feedback_score"])

    att = attendance_df[["INDEX_NO", "FEEDBACK"]].copy()
    att["parsed"] = att["FEEDBACK"].apply(parse_feedback)
    att = att.dropna(subset=["parsed"])

    if att.empty:
        return pd.DataFrame(columns=["INDEX_NO", "feedback_score"])

    result = att.groupby("INDEX_NO")["parsed"].mean().reset_index()
    result.columns = ["INDEX_NO", "feedback_score"]
    return result


def _compute_education_scores(degrees_df):
    """Highest degree level per advisor. PhD=1.0, Masters=0.7, Bachelors=0.5, Other=0.3."""
    if degrees_df.empty:
        return pd.DataFrame(columns=["INDEX_NO", "education_score"])

    df = degrees_df[["INDEX_NO", "DEGREE_NAME"]].copy()
    df["DEGREE_NAME"] = df["DEGREE_NAME"].fillna("").str.upper()

    def degree_level(name):
        if not name:
            return 0.3
        if any(kw in name for kw in ["PH.D", "PHD", "DOCTORATE", "D.SC", "D.LITT", "D.PHIL"]):
            return 1.0
        if any(kw in name for kw in ["M.D", "M.S.", "M.TECH", "M.SC", "M.A.", "M.B.A",
                                       "MASTER", "M.PHIL", "M.E.", "M.CH", "D.M.",
                                       "POST GRADUATE", "PG DIPLOMA", "M.COM", "M.ED",
                                       "LL.M", "M.B.B.S"]):
            return 0.7
        if any(kw in name for kw in ["B.TECH", "B.SC", "B.A.", "B.E.", "B.COM",
                                       "BACHELOR", "GRADUATE", "LL.B", "B.ED",
                                       "B.B.A", "B.ARCH"]):
            return 0.5
        return 0.3

    df["level"] = df["DEGREE_NAME"].apply(degree_level)
    result = df.groupby("INDEX_NO")["level"].max().reset_index()
    result.columns = ["INDEX_NO", "education_score"]
    return result


def _compute_pay_scores(advisors_df):
    """Normalize pay scale start value."""
    df = advisors_df[["INDEX_NO", "PAY_SCALE_START"]].copy()
    df["PAY_SCALE_START"] = pd.to_numeric(df["PAY_SCALE_START"], errors="coerce")
    max_pay = df["PAY_SCALE_START"].max()
    if max_pay and max_pay > 0:
        df["pay_score"] = (df["PAY_SCALE_START"] / max_pay).clip(0, 1)
    else:
        df["pay_score"] = 0.3
    return df[["INDEX_NO", "pay_score"]]


def _compute_experience_scores(jobs_df):
    """Total years of experience from job history."""
    if jobs_df.empty:
        return pd.DataFrame(columns=["INDEX_NO", "experience_score"])

    df = jobs_df[["INDEX_NO", "FROM_YEAR", "TO_YEAR"]].copy()
    df["FROM_YEAR"] = pd.to_numeric(df["FROM_YEAR"], errors="coerce")
    df["TO_YEAR"] = pd.to_numeric(df["TO_YEAR"], errors="coerce")
    df["years"] = (df["TO_YEAR"] - df["FROM_YEAR"]).clip(lower=0)

    total = df.groupby("INDEX_NO")["years"].sum().reset_index()
    max_exp = total["years"].max()
    if max_exp and max_exp > 0:
        total["experience_score"] = (total["years"] / max_exp).clip(0, 1)
    else:
        total["experience_score"] = 0.3
    total = total[["INDEX_NO", "experience_score"]]
    return total


def _compute_panel_experience_scores(attendance_df):
    """Number of panels served on, normalized."""
    if attendance_df.empty:
        return pd.DataFrame(columns=["INDEX_NO", "panel_exp_score"])

    counts = attendance_df.groupby("INDEX_NO").size().reset_index(name="panel_count")
    max_count = counts["panel_count"].max()
    if max_count and max_count > 0:
        counts["panel_exp_score"] = (counts["panel_count"] / max_count).clip(0, 1)
    else:
        counts["panel_exp_score"] = 0.0
    return counts[["INDEX_NO", "panel_exp_score"]]


def _compute_recency_scores(attendance_df):
    """How recently the advisor served. More recent = higher score."""
    if attendance_df.empty:
        return pd.DataFrame(columns=["INDEX_NO", "recency_score"])

    df = attendance_df[["INDEX_NO", "ATND_DATE"]].copy()
    df["ATND_DATE"] = pd.to_datetime(df["ATND_DATE"], errors="coerce")
    df = df.dropna(subset=["ATND_DATE"])

    if df.empty:
        return pd.DataFrame(columns=["INDEX_NO", "recency_score"])

    latest = df.groupby("INDEX_NO")["ATND_DATE"].max().reset_index()
    now = pd.Timestamp.now()
    latest["days_ago"] = (now - latest["ATND_DATE"]).dt.days.clip(lower=0)
    max_days = latest["days_ago"].max()
    if max_days and max_days > 0:
        latest["recency_score"] = 1.0 - (latest["days_ago"] / max_days)
    else:
        latest["recency_score"] = NEUTRAL_SCORE
    return latest[["INDEX_NO", "recency_score"]]
