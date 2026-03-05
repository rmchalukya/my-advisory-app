import streamlit as st
import pandas as pd
import numpy as np
from db.connection import load_csv
from config import DEMO_MODE, DEMO_SEED, DEMO_SAMPLE_FRAC


@st.cache_data(ttl=600)
def _get_demo_ids():
    """Get the fixed set of INDEX_NOs to keep in demo mode."""
    advisor_mst = load_csv("advisor_mst")
    sampled = advisor_mst["INDEX_NO"].sample(frac=DEMO_SAMPLE_FRAC, random_state=DEMO_SEED)
    return set(sampled.tolist())


def _demo_filter(df, id_column="INDEX_NO"):
    """Filter dataframe to demo subset if demo mode is on."""
    if not DEMO_MODE:
        return df
    demo_ids = _get_demo_ids()
    return df[df[id_column].isin(demo_ids)].reset_index(drop=True)


@st.cache_data(ttl=600)
def get_all_advisors():
    a = load_csv("advisor_mst")
    p = load_csv("profession_mst")
    d = load_csv("designation_mst")
    ot = load_csv("org_type_mst")
    st2 = load_csv("service_type_mst")
    z = load_csv("zone_mst")
    sm = load_csv("state_mst")
    ps = load_csv("pay_scale_mst")
    lm = load_csv("level_mst")
    pt = load_csv("panel_type_mst")

    df = a.merge(p[["PROFESSION_ID", "PROFESSION_NAME"]], left_on="MAIN_PROFESSION_ID", right_on="PROFESSION_ID", how="left")
    df = df.merge(d[["DESIGNATION_ID", "DESIGNATION_DESC"]], on="DESIGNATION_ID", how="left")
    df = df.merge(ot[["ORG_TYPE_ID", "ORG_TYPE_DESC"]], on="ORG_TYPE_ID", how="left")
    df = df.merge(st2[["SERVICE_TYPE_ID", "SERVICE_TYPE_NAME"]], on="SERVICE_TYPE_ID", how="left")
    df = df.merge(z[["ZONE_ID", "ZONE_NAME"]], left_on="OFFICE_ZONE_ID", right_on="ZONE_ID", how="left")
    df = df.merge(sm[["ZONE_ID", "STATE_ID", "STATE_NAME"]], left_on=["OFFICE_ZONE_ID", "OFFICE_STATE_ID"], right_on=["ZONE_ID", "STATE_ID"], how="left", suffixes=("", "_state"))
    df = df.merge(ps[["PAY_SCALE_ID", "PAY_SCALE_START", "PAY_SCALE_END"]], on="PAY_SCALE_ID", how="left")
    df = df.merge(lm[["LEVEL_ID", "LEVEL_NAME"]], on="LEVEL_ID", how="left")
    df = df.merge(pt[["PANEL_TYPE_ID", "PANEL_TYPE_DESC"]], on="PANEL_TYPE_ID", how="left")

    # Compute age
    df["DATE_OF_BIRTH"] = pd.to_datetime(df["DATE_OF_BIRTH"], errors="coerce")
    valid_dob = df["DATE_OF_BIRTH"].notna() & (df["DATE_OF_BIRTH"] > pd.Timestamp("1900-01-01"))
    df["age"] = np.nan
    df.loc[valid_dob, "age"] = ((pd.Timestamp.now() - df.loc[valid_dob, "DATE_OF_BIRTH"]).dt.days / 365.25).astype(int)

    # Drop helper columns from merges
    drop_cols = [c for c in ["PROFESSION_ID_y", "ZONE_ID", "ZONE_ID_state", "STATE_ID"] if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    if "PROFESSION_ID_x" in df.columns:
        df = df.rename(columns={"PROFESSION_ID_x": "PROFESSION_ID"})

    return _demo_filter(df)


@st.cache_data(ttl=600)
def get_advisor_professions():
    ap = load_csv("advisor_profession")
    p = load_csv("profession_mst")
    s = load_csv("specilisation_mst")
    ss = load_csv("super_specilisation_mst")

    df = ap.merge(p[["PROFESSION_ID", "PROFESSION_NAME"]], on="PROFESSION_ID", how="left")
    df = df.merge(s[["PROFESSION_ID", "SPECILISATION_ID", "SPECILISATION_NAME"]],
                  on=["PROFESSION_ID", "SPECILISATION_ID"], how="left")
    df = df.merge(ss[["PROFESSION_ID", "SPECILISATION_ID", "SUPER_SPECILISATION_ID", "SUPER_SPECILISATION_NAME"]],
                  on=["PROFESSION_ID", "SPECILISATION_ID", "SUPER_SPECILISATION_ID"], how="left")
    return _demo_filter(df)


@st.cache_data(ttl=600)
def get_advisor_attendance():
    df = load_csv("advisor_attendance")
    return _demo_filter(df)


@st.cache_data(ttl=600)
def get_advisor_degrees():
    ad = load_csv("advisor_degree")
    dm = load_csv("degree_mst")
    df = ad.merge(dm[["DEGREE_ID", "DEGREE_NAME"]], on="DEGREE_ID", how="left")
    return _demo_filter(df)


@st.cache_data(ttl=600)
def get_advisor_jobs():
    df = load_csv("advisor_job_detail")
    return _demo_filter(df)


@st.cache_data(ttl=600)
def get_profession_hierarchy():
    p = load_csv("profession_mst")
    s = load_csv("specilisation_mst")
    ss = load_csv("super_specilisation_mst")

    df = p[["PROFESSION_ID", "PROFESSION_NAME"]].merge(
        s[["PROFESSION_ID", "SPECILISATION_ID", "SPECILISATION_NAME"]],
        on="PROFESSION_ID", how="left"
    )
    df = df.merge(
        ss[["PROFESSION_ID", "SPECILISATION_ID", "SUPER_SPECILISATION_ID", "SUPER_SPECILISATION_NAME"]],
        on=["PROFESSION_ID", "SPECILISATION_ID"], how="left"
    )
    df = df.drop_duplicates().sort_values(["PROFESSION_NAME", "SPECILISATION_NAME", "SUPER_SPECILISATION_NAME"])
    return df


@st.cache_data(ttl=600)
def get_board_presidents():
    df = load_csv("board_president_mst")
    df = df[df["ACTIVE"] == "Y"].sort_values("BOARD_PRESIDENT_NAME")
    return df[["BOARD_PRESIDENT_ID", "BOARD_PRESIDENT_NAME"]]


@st.cache_data(ttl=600)
def get_panel_history():
    ds = load_csv("draw_panel_selection")
    dsa = load_csv("draw_panel_seletcted_advisor")

    df = ds.merge(dsa, on="FILE_NO", how="inner", suffixes=("", "_advisor"))

    if "APPROVED_advisor" in df.columns:
        df = df.rename(columns={"APPROVED_advisor": "ADVISOR_APPROVED"})

    return _demo_filter(df)


@st.cache_data(ttl=600)
def get_panel_selection_summary():
    ds = load_csv("draw_panel_selection")
    dsa = load_csv("draw_panel_seletcted_advisor")

    merged = ds[["FILE_NO", "CREATION_DATE", "APPROVED"]].merge(
        dsa, on="FILE_NO", how="inner", suffixes=("", "_adv")
    )

    # Identify the advisor-level APPROVED column
    adv_approved_col = "APPROVED_adv" if "APPROVED_adv" in merged.columns else "APPROVED"

    summary = merged.groupby(["FILE_NO", "CREATION_DATE", "APPROVED"]).agg(
        advisor_count=("INDEX_NO", "count"),
        selected_count=("SELECTION", lambda x: (x == "Y").sum()),
        approved_count=(adv_approved_col, lambda x: (x == "Y").sum()),
    ).reset_index()

    return summary


@st.cache_data(ttl=600)
def get_board_president_workload():
    att = load_csv("advisor_attendance")
    att["ATND_DATE"] = pd.to_datetime(att["ATND_DATE"], errors="coerce")
    att["year"] = att["ATND_DATE"].dt.year

    att = att[att["BP"].notna() & (att["BP"].astype(str) != "")]

    df = att.groupby(["BP", "year"]).agg(
        panel_count=("FILE_NO", "count"),
        unique_advisors=("INDEX_NO", "nunique"),
        first_panel=("ATND_DATE", "min"),
        last_panel=("ATND_DATE", "max"),
    ).reset_index()
    df = df.rename(columns={"BP": "president"})
    return df


@st.cache_data(ttl=600)
def get_advisor_cooccurrence():
    att = load_csv("advisor_attendance")
    pairs = att[["FILE_NO", "INDEX_NO"]].drop_duplicates()

    # Self-join on FILE_NO
    merged = pairs.merge(pairs, on="FILE_NO", suffixes=("_1", "_2"))
    merged = merged[merged["INDEX_NO_1"] < merged["INDEX_NO_2"]]

    cooccur = merged.groupby(["INDEX_NO_1", "INDEX_NO_2"]).size().reset_index(name="times_together")
    cooccur = cooccur[cooccur["times_together"] >= 5]
    cooccur = cooccur.sort_values("times_together", ascending=False).head(50)
    cooccur = cooccur.rename(columns={"INDEX_NO_1": "advisor1", "INDEX_NO_2": "advisor2"})
    return cooccur
