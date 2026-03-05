import streamlit as st
import pandas as pd


def render_panel_type_filter():
    return st.radio(
        "Panel Type",
        ["BOTH", "ACADEMIC", "APPLIED"],
        horizontal=True,
    )


def render_demographic_filters():
    col1, col2 = st.columns(2)
    with col1:
        employment = st.radio("Employment Status", ["BOTH", "S", "R"],
                              format_func=lambda x: {"BOTH": "Both", "S": "Serving", "R": "Retired"}[x],
                              horizontal=True)
    with col2:
        gender = st.radio("Gender", ["BOTH", "M", "F"],
                          format_func=lambda x: {"BOTH": "Both", "M": "Male", "F": "Female"}[x],
                          horizontal=True)

    age_range = st.slider("Age Range", 30, 85, (40, 70))
    return employment, gender, age_range


def render_profession_cascade(hierarchy_df):
    """
    Render cascading dropdowns: Profession → Specialization → Super Specialization.
    Returns (profession_ids, specialisation_ids, super_specialisation_ids).
    """
    professions = sorted(hierarchy_df["PROFESSION_NAME"].dropna().unique())
    selected_professions = st.multiselect("Profession", professions)

    selected_prof_ids = []
    selected_spec_ids = []
    selected_super_spec_ids = []

    if selected_professions:
        filtered = hierarchy_df[hierarchy_df["PROFESSION_NAME"].isin(selected_professions)]
        selected_prof_ids = filtered["PROFESSION_ID"].dropna().unique().tolist()

        specs = sorted(filtered["SPECILISATION_NAME"].dropna().unique())
        if specs:
            selected_specs = st.multiselect("Specialization", specs)
            if selected_specs:
                spec_filtered = filtered[filtered["SPECILISATION_NAME"].isin(selected_specs)]
                selected_spec_ids = spec_filtered["SPECILISATION_ID"].dropna().unique().tolist()

                super_specs = sorted(spec_filtered["SUPER_SPECILISATION_NAME"].dropna().unique())
                if super_specs:
                    selected_super = st.multiselect("Super Specialization", super_specs)
                    if selected_super:
                        ss_filtered = spec_filtered[
                            spec_filtered["SUPER_SPECILISATION_NAME"].isin(selected_super)
                        ]
                        selected_super_spec_ids = (
                            ss_filtered["SUPER_SPECILISATION_ID"].dropna().unique().tolist()
                        )

    return selected_prof_ids, selected_spec_ids, selected_super_spec_ids


def render_zone_filter(advisors_df):
    zones = sorted(advisors_df["ZONE_NAME"].dropna().unique())
    return st.multiselect("Zone", zones)


def render_level_filter(advisors_df):
    levels = sorted(advisors_df["LEVEL_NAME"].dropna().unique())
    return st.multiselect("Level", levels)


def build_filters_dict(
    panel_type, employment, gender, age_range,
    prof_ids, spec_ids, super_spec_ids,
    zone_names, level_names, exclude_org,
    advisors_df,
):
    """Build the filters dict expected by recommender.shortlist_advisors."""
    # Convert zone names to IDs
    zone_ids = None
    if zone_names:
        zone_ids = advisors_df[advisors_df["ZONE_NAME"].isin(zone_names)]["OFFICE_ZONE_ID"].dropna().unique().tolist()

    # Convert level names to IDs
    level_ids = None
    if level_names:
        level_ids = advisors_df[advisors_df["LEVEL_NAME"].isin(level_names)]["LEVEL_ID"].dropna().unique().tolist()

    return {
        "panel_type": panel_type if panel_type != "BOTH" else None,
        "employment": employment if employment != "BOTH" else None,
        "gender": gender if gender != "BOTH" else None,
        "age_min": age_range[0] if age_range else None,
        "age_max": age_range[1] if age_range else None,
        "profession_ids": prof_ids or None,
        "specialisation_ids": spec_ids or None,
        "super_specialisation_ids": super_spec_ids or None,
        "zone_ids": zone_ids,
        "level_ids": level_ids,
        "exclude_org_name": exclude_org if exclude_org else None,
    }
