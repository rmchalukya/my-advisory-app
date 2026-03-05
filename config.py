# Scoring weights (must sum to 1.0)
SCORING_WEIGHTS = {
    "feedback": 0.30,
    "education": 0.25,
    "pay_grade": 0.15,
    "experience": 0.10,
    "panel_experience": 0.10,
    "recency": 0.10,
}

# Neutral score for advisors with no attendance data
NEUTRAL_SCORE = 0.5

# Panel optimizer targets
GENDER_FEMALE_TARGET = 0.20  # Aim for at least 20% female
MAX_SAME_ORG_IN_PANEL = 1    # Flag if >1 advisor from same org

# Demo mode — sample a subset of records so counts don't match the real DB
DEMO_MODE = True
DEMO_SEED = 42
DEMO_SAMPLE_FRAC = 0.78  # Keep ~78% of advisors
