import os
import streamlit as st
import pandas as pd

CSV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "csv")


@st.cache_data(ttl=600)
def load_csv(table_name):
    """Load a CSV file exported from the MySQL database."""
    path = os.path.join(CSV_DIR, f"{table_name}.csv")
    return pd.read_csv(path, low_memory=False)
