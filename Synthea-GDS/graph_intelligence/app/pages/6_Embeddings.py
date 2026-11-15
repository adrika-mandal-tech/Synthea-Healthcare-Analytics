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

    st.title("Embedding Explorer")
    st.write("Compare embedding methods for the Synthea COVID-19 graph, including FastRP, Node2Vec, GraphSAGE, HashGNN, and FastPath.")

    embeddings_root = Path(__file__).resolve().parents[2] / "embeddings"
    csv_files = sorted(embeddings_root.glob("*.csv")) if embeddings_root.exists() else []
    if not csv_files:
        st.info("No embedding outputs are present yet for the COVID-19 graph.")
        return

    selected = st.selectbox("Embedding method", [p.name for p in csv_files])
    df = pd.read_csv(embeddings_root / selected)
    st.dataframe(df.head(15), use_container_width=True)


if __name__ == "__main__":
    render()
