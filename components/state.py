import json
import os
import streamlit as st

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "panels.json")


def init_session_state():
    """Initialize all session state keys. Call once from Home.py."""
    defaults = {
        "panel_step": 1,
        "panel_data": {},
        "shortlisted": None,
        "selected_advisors": None,
        "created_panels": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Load persisted panels on first run
    if not st.session_state.created_panels:
        st.session_state.created_panels = load_panels()


def save_panels():
    """Save created_panels list to JSON file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    panels = st.session_state.created_panels
    with open(STATE_FILE, "w") as f:
        json.dump(panels, f, default=str, indent=2)


def load_panels():
    """Load previously saved panels from JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []
