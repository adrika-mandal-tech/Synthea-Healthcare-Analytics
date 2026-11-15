from __future__ import annotations

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

from graph_intelligence.analytics.graph_loader import get_nodes_df


def render() -> None:
    if st is None:
        return

    st.title("Entity Inspector")
    nodes_df = get_nodes_df()
    if nodes_df.empty:
        st.info("No node data is available yet.")
        return

    key_cols = [col for col in ["name", "NAME", "Id", "element_id"] if col in nodes_df.columns]
    search_text = st.text_input("Search entity name or ID")
    if search_text:
        mask = False
        for col in key_cols:
            mask = mask | nodes_df[col].fillna("").astype(str).str.contains(search_text, case=False, na=False)
        matched = nodes_df[mask]
    else:
        matched = nodes_df.head(25)

    st.dataframe(matched.head(25), use_container_width=True)

    if not matched.empty:
        selected = st.selectbox("Choose entity", matched["element_id"].tolist())
        row = matched[matched["element_id"] == selected].iloc[0]
        st.subheader("Entity profile")
        st.json({
            "element_id": row.get("element_id"),
            "name": row.get("name") or row.get("NAME") or row.get("Id"),
            "labels": row.get("labels"),
            "properties": {k: v for k, v in row.items() if k not in {"element_id", "name", "NAME", "Id", "labels"}},
        })


if __name__ == "__main__":
    render()
