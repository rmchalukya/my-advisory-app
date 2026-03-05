import re

# Regex for numeric feedback like "2+3+4+5+6=20"
_NUMERIC_PATTERN = re.compile(r'^([\d]+(?:\+[\d]+)*)=(\d+)$')

# Qualitative feedback mapping (case-insensitive)
_QUALITATIVE_MAP = {
    "outstanding": 0.95,
    "excellent": 0.90,
    "very good": 0.85,
    "very-good": 0.85,
    "good": 0.70,
    "average": 0.50,
    "below average": 0.30,
    "poor": 0.20,
    "not-to-be-called": 0.10,
    "not to be called": 0.10,
}

# Max possible numeric score (5 dimensions × 10 each)
_MAX_NUMERIC_SCORE = 50


def parse_feedback(feedback_str):
    """Parse feedback string and return normalized score (0.0 to 1.0) or None."""
    if not feedback_str or not isinstance(feedback_str, str):
        return None

    text = feedback_str.strip()
    if not text or text.upper() in ("NOT AVAILABLE", "NOT AVAILABLE.", "NA", "N/A", "NULL"):
        return None

    # Try numeric format: "2+3+4+5+6=20"
    match = _NUMERIC_PATTERN.match(text)
    if match:
        total = int(match.group(2))
        parts = match.group(1).split("+")
        max_score = len(parts) * 10  # each dimension max 10
        return min(total / max_score, 1.0)

    # Try qualitative
    lower = text.lower().strip()
    for key, score in _QUALITATIVE_MAP.items():
        if key in lower:
            return score

    # Try if it's just a number
    try:
        val = float(text)
        return min(val / _MAX_NUMERIC_SCORE, 1.0)
    except ValueError:
        pass

    return None


def parse_feedback_detailed(feedback_str):
    """Return a dict with parsed details for display purposes."""
    if not feedback_str or not isinstance(feedback_str, str):
        return {"raw": feedback_str, "score": None, "type": "missing"}

    text = feedback_str.strip()
    normalized = parse_feedback(text)

    if normalized is None:
        return {"raw": text, "score": None, "type": "unavailable"}

    match = _NUMERIC_PATTERN.match(text)
    if match:
        parts = [int(x) for x in match.group(1).split("+")]
        return {
            "raw": text,
            "score": normalized,
            "total": int(match.group(2)),
            "dimensions": parts,
            "type": "numeric",
        }

    return {"raw": text, "score": normalized, "type": "qualitative"}
