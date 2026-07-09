"""Reusable Streamlit view for a data source.

Copied into src/app/present.py for UI apps (needs streamlit + pandas, both added
by the build stage). One call renders a titled, readable view of any source:
key metrics, the full table, and a bar chart on a numeric field.
"""

import pandas as pd
import streamlit as st

from app.data import DataSource


def show_source(source: DataSource) -> None:
    rows = source.fetch()
    frame = pd.DataFrame(rows)

    st.subheader(source.label)
    st.caption(source.description)

    numeric = [c for c in frame.columns if pd.api.types.is_numeric_dtype(frame[c])]
    if numeric:
        columns = st.columns(min(len(numeric), 4))
        for column, field in zip(columns, numeric[:4], strict=False):
            column.metric(field, round(float(frame[field].mean()), 2))

    st.dataframe(frame, use_container_width=True)

    if numeric:
        field = st.selectbox("Chart this field", numeric)
        st.bar_chart(frame.set_index(frame.columns[0])[field])
