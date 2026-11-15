from __future__ import annotations

from typing import Iterable

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


def render_stat_cards(stats: dict) -> None:
    if st is None:
        return

    cols = st.columns(4)
    values = [
        ("Nodes", stats.get("node_count", 0)),
        ("Edges", stats.get("edge_count", 0)),
        ("Density", round(stats.get("density", 0.0), 4)),
        ("Avg Degree", round(stats.get("avg_degree", 0.0), 3)),
    ]
    for col, (label, value) in zip(cols, values):
        col.metric(label, value)


def render_top_table(rows: Iterable[dict], key_name: str = "label") -> None:
    if st is None:
        return

    row_list = list(rows)
    if not row_list:
        st.caption("No rows available for this view yet.")
        return

    st.dataframe(row_list, use_container_width=True)
