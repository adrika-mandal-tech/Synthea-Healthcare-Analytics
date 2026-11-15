from __future__ import annotations

from collections import Counter

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

from graph_intelligence.analytics.graph_loader import get_graph_statistics, get_nodes_df
from graph_intelligence.visualization.graph_viz import GraphVisualizer


def render() -> None:
    if st is None:
        return

    st.title("Graph Overview")
    stats = get_graph_statistics()

    cards = [
        ("Nodes", stats.get("node_count", 0)),
        ("Edges", stats.get("edge_count", 0)),
        ("Density", round(stats.get("density", 0.0), 4)),
        ("Avg degree", round(stats.get("avg_degree", 0.0), 3)),
    ]
    cols = st.columns(len(cards))
    for col, (label, value) in zip(cols, cards):
        col.metric(label, value)

    viz = GraphVisualizer("data/nodes.csv", "data/relationships.csv")
    labels = viz.label_distribution()
    rels = viz.relationship_distribution()

    left, right = st.columns(2)
    with left:
        st.subheader("Label distribution")
        if labels:
            st.bar_chart({row["label"]: row["count"] for row in labels})
        else:
            st.info("No label distribution available.")

    with right:
        st.subheader("Relationship types")
        if rels:
            st.bar_chart({row["relationship"]: row["count"] for row in rels})
        else:
            st.info("No relationship data available.")

    nodes_df = get_nodes_df()
    if not nodes_df.empty:
        st.subheader("Top labels")
        top_labels = [{"label": k, "count": v} for k, v in Counter(nodes_df.get("labels", "").fillna("").astype(str)).most_common(10)]
        st.dataframe(top_labels, use_container_width=True)

    st.subheader("Graph metadata")
    st.json({
        "connected_components": stats.get("connected_components", 0),
        "largest_component_size": stats.get("largest_component_size", 0),
        "unique_labels": stats.get("unique_labels", 0),
        "unique_relationship_types": stats.get("unique_relationship_types", 0),
        "directed_edges": stats.get("edge_count", 0),
        "undirected_edges": stats.get("undirected_edge_count", 0),
    })


if __name__ == "__main__":
    render()
