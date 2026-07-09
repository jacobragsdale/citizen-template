"""Streamlit UI for the app.

Run locally:  uv run --env-file .env streamlit run src/app/ui.py
The build stage replaces the placeholders and the body with the real app.
Data comes from app.data; app.present.show_source renders any source.
"""

import streamlit as st

from app.data import get_source, list_sources
from app.present import show_source

st.set_page_config(page_title="APP_TITLE", layout="wide")
st.title("APP_TITLE")
st.write("APP_DESCRIPTION")

# --- Pick a data source ---------------------------------------------------
# The build stage narrows this to the source(s) the citizen chose (and may drop
# the picker if there is only one).
labels = {s.label: s.key for s in list_sources()}
choice = st.selectbox("Data source", list(labels))

# One call renders metrics + table + chart. The build stage replaces or extends
# this with the app's real inputs, actions, and outputs.
show_source(get_source(labels[choice]))
