from __future__ import annotations

from pathlib import Path

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

import pandas as pd


def render() -> None:
    if st is None:
        return

    st.title("Similarity Analysis")
    st.write("Compare patient, provider, and condition similarity using the Synthea COVID-19 graph outputs.")

    similarity_root = Path(__file__).resolve().parents[2] / "similarity"
    csv_files = sorted(similarity_root.glob("*.csv")) if similarity_root.exists() else []
    if not csv_files:
        st.info("No similarity CSV outputs are present yet for the COVID-19 graph.")
        return

    selected = st.selectbox("Similarity output", [p.name for p in csv_files])
    df = pd.read_csv(similarity_root / selected)
    st.dataframe(df.head(20), use_container_width=True)


if __name__ == "__main__":
    render()
