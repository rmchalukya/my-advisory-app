import numpy as np
import pandas as pd
from config import GENDER_FEMALE_TARGET, MAX_SAME_ORG_IN_PANEL


def analyze_panel(selected_advisors_df, required_specs=None):
    """
    Analyze panel composition and return health card.

    Parameters
    ----------
    selected_advisors_df : DataFrame of selected advisors (subset of full advisor data)
    required_specs : list of specialization names that should be covered (optional)

    Returns
    -------
    dict with:
        scores: dict of dimension -> score (0-100)
        overall: float (0-100)
        suggestions: list of str
        conflicts: list of str
    """
    df = selected_advisors_df
    if df.empty:
        return {
            "scores": {"gender": 0, "zone": 0, "experience": 0, "expertise": 0},
            "overall": 0,
            "suggestions": ["No advisors selected."],
            "conflicts": [],
        }

    scores = {}
    suggestions = []
    conflicts = []

    # 1. Gender balance
    scores["gender"] = _gender_score(df, suggestions)

    # 2. Zone diversity
    scores["zone"] = _zone_score(df, suggestions)

    # 3. Experience mix
    scores["experience"] = _experience_score(df, suggestions)

    # 4. Expertise coverage
    scores["expertise"] = _expertise_score(df, required_specs, suggestions)

    # Conflicts: same org appearing multiple times
    _check_org_conflicts(df, conflicts)

    # Overall (weighted average)
    overall = (
        scores["gender"] * 0.25
        + scores["zone"] * 0.25
        + scores["experience"] * 0.25
        + scores["expertise"] * 0.25
    )

    return {
        "scores": scores,
        "overall": round(overall, 1),
        "suggestions": suggestions,
        "conflicts": conflicts,
    }


def _gender_score(df, suggestions):
    total = len(df)
    female_count = (df["GENDER"] == "F").sum()
    female_ratio = female_count / total if total > 0 else 0

    if female_ratio >= GENDER_FEMALE_TARGET:
        score = 100
    elif female_ratio == 0:
        score = 20
        suggestions.append(
            f"Panel has no female advisors. Consider adding at least "
            f"{max(1, int(np.ceil(total * GENDER_FEMALE_TARGET)))} female advisor(s)."
        )
    else:
        score = int((female_ratio / GENDER_FEMALE_TARGET) * 100)
        needed = max(1, int(np.ceil(total * GENDER_FEMALE_TARGET)) - female_count)
        suggestions.append(
            f"Female representation is {female_ratio:.0%} (target: {GENDER_FEMALE_TARGET:.0%}). "
            f"Consider adding {needed} more female advisor(s)."
        )

    return min(score, 100)


def _zone_score(df, suggestions):
    zones = df["ZONE_NAME"].dropna()
    if zones.empty:
        return 50

    zone_counts = zones.value_counts()
    n_zones = len(zone_counts)
    total = len(zones)

    # Shannon entropy normalized to max possible
    if n_zones <= 1:
        score = 20
        dominant = zone_counts.index[0] if len(zone_counts) > 0 else "Unknown"
        suggestions.append(
            f"All advisors are from {dominant} zone. Consider geographic diversity."
        )
    else:
        probs = zone_counts.values / total
        entropy = -np.sum(probs * np.log2(probs))
        max_entropy = np.log2(min(n_zones, 6))  # 6 main zones
        score = int((entropy / max_entropy) * 100) if max_entropy > 0 else 50

        if score < 60:
            dominant = zone_counts.index[0]
            suggestions.append(
                f"Panel is heavily concentrated in {dominant} zone ({zone_counts.iloc[0]}/{total}). "
                f"Consider advisors from underrepresented zones."
            )

    return min(score, 100)


def _experience_score(df, suggestions):
    emp = df["EMPLOYMENT_STATUS"].value_counts()
    serving = emp.get("S", 0)
    retired = emp.get("R", 0)
    total = serving + retired

    if total == 0:
        return 50

    # Ideal mix: some of both
    ratio = min(serving, retired) / total if total > 0 else 0

    # Also check level diversity
    levels = df["LEVEL_NAME"].dropna().nunique()
    level_bonus = min(levels * 10, 30)  # up to 30 points for level diversity

    score = int(ratio * 70) + level_bonus

    if retired == 0 and serving > 2:
        suggestions.append("Panel has no retired advisors. Their experience could add depth.")
    elif serving == 0 and retired > 2:
        suggestions.append("Panel has no serving advisors. Consider adding active professionals.")

    return min(score, 100)


def _expertise_score(df, required_specs, suggestions):
    if not required_specs:
        # No specific requirements - score based on profession diversity
        n_professions = df["PROFESSION_NAME"].dropna().nunique()
        return min(n_professions * 25, 100)

    covered = set(df["PROFESSION_NAME"].dropna().unique())
    required = set(required_specs)
    missing = required - covered

    if not missing:
        score = 100
    else:
        coverage = len(required - missing) / len(required) if required else 1
        score = int(coverage * 100)
        suggestions.append(
            f"Missing expertise in: {', '.join(sorted(missing))}. "
            f"Coverage: {score}%."
        )

    return score


def _check_org_conflicts(df, conflicts):
    orgs = df["ORG_INST_UNIV_OTH_NAME"].dropna()
    if orgs.empty:
        return

    org_counts = orgs.value_counts()
    duplicates = org_counts[org_counts > MAX_SAME_ORG_IN_PANEL]

    for org, count in duplicates.items():
        if org and org.strip():
            conflicts.append(
                f"Organization '{org}' has {count} advisors in the panel "
                f"(max recommended: {MAX_SAME_ORG_IN_PANEL})."
            )
