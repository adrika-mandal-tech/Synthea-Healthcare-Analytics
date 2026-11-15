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

    st.title("Community Explorer")
    root = Path(__file__).resolve().parents[2]
    community_dir = root / "community"

    csv_files = sorted(community_dir.glob("*.csv")) if community_dir.exists() else []
    if not csv_files:
        st.info("No community CSV outputs were found yet.")
        return

    selected = st.selectbox("Community output", [p.name for p in csv_files])
    st.caption(f"Selected file: {selected}")
    df = pd.read_csv(community_dir / selected)
    st.dataframe(df.head(25), use_container_width=True)

    if {"algorithm", "communities"}.issubset(df.columns):
        summary = df[["algorithm", "communities"]].dropna(subset=["communities"]).copy()
        if not summary.empty:
            st.subheader("Community size by algorithm")
            st.bar_chart(summary.set_index("algorithm")["communities"])


if __name__ == "__main__":
    render()
