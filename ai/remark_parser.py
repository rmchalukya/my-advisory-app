import re


_SUITABILITY_PATTERNS = {
    "suitable_all": [
        r"suitable.?for.?all.?boards",
    ],
    "suitable_pt": [
        r"suitable.?for.?p\.?t\.?.?board",
        r"suitable.?for.?personality.?test",
    ],
    "suitable_recruitment": [
        r"suitable.?for.?recruitment.?board",
        r"suitable.?for.?p\.?t\.?.?board.?/.?recruitment.?board",
    ],
    "suitable_specialization": [
        r"in.?his.?her.?area.?of.?speciali[sz]ation",
        r"suitable.?for.?areas?.?of.?speciali[sz]ation",
        r"suitable.?for.?similar.?board",
    ],
    "resource_person": [
        r"resource.?person",
    ],
    "not_suitable": [
        r"poor",
        r"not.?to.?be.?called",
    ],
}

# Compile all patterns once
_COMPILED = {
    category: [re.compile(p, re.IGNORECASE) for p in patterns]
    for category, patterns in _SUITABILITY_PATTERNS.items()
}

_SKIP_VALUES = {"nil", "n/a", "na", "yes", "yes.", "no", "feedback-not-received",
                "feedback not received", "not available", ""}


def parse_remark(remark_str):
    """Parse REMARK field into a suitability category.

    Returns one of: "suitable_all", "suitable_pt", "suitable_recruitment",
    "suitable_specialization", "resource_person", "not_suitable",
    "positive" (for generic good remarks), or None (for nil/empty/uninformative).
    """
    if remark_str is None:
        return None

    text = str(remark_str).strip()
    if text.lower() in _SKIP_VALUES:
        return None

    # Check suitability patterns
    for category, patterns in _COMPILED.items():
        for pat in patterns:
            if pat.search(text):
                return category

    # Generic positive remarks
    lower = text.lower()
    if any(w in lower for w in ("outstanding", "excellent", "very good", "very-good",
                                 "may be called", "may-be-called")):
        return "positive"
    if lower in ("good",):
        return "positive"

    return None
