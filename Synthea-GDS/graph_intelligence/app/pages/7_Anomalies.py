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

    st.title("Anomaly Detection")
    st.write("Inspect articulation points, bridges, and structural outliers in the Synthea COVID-19 healthcare graph.")

    anomaly_root = Path(__file__).resolve().parents[2]
    candidate_dirs = [anomaly_root / "centrality", anomaly_root / "community", anomaly_root / "paths"]
    csv_files = []
    for directory in candidate_dirs:
        if directory.exists():
            csv_files.extend(sorted(directory.glob("*.csv")))

    if not csv_files:
        st.info("No anomaly-related outputs are present for the COVID-19 graph yet.")
        return

    file_map = {p.name: p for p in csv_files}
    selected_name = st.selectbox("Metric output", list(file_map.keys())[:20])
    df = pd.read_csv(file_map[selected_name])
    st.dataframe(df.head(20), use_container_width=True)


if __name__ == "__main__":
    render()
