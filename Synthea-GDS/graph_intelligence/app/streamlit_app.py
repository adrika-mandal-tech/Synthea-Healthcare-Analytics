"""Streamlit entry point for the graph intelligence app."""

from __future__ import annotations

import importlib.util
from pathlib import Path

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

ROOT = Path(__file__).resolve().parents[2]


def _load_page_module(page_name: str):
    page_file = ROOT / "graph_intelligence" / "app" / "pages" / f"{page_name}.py"
    if not page_file.exists():
        raise FileNotFoundError(f"Page file not found: {page_file}")

    module_name = f"synthea_page_{page_name.replace('-', '_').replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, page_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load page module: {page_name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if st is not None:
    st.set_page_config(page_title="Synthea Graph Intelligence", page_icon="🧬", layout="wide")
    st.title("Synthea Graph Intelligence")
    st.caption("Healthcare graph analytics, community exploration, and GenAI Q&A")

    pages = {
        "Overview": "1_Overview",
        "Copilot": "2_Copilot",
        "Community": "3_Community",
        "Entity": "4_Entity",
        "Similarity": "5_Similarity",
        "Embeddings": "6_Embeddings",
        "Anomalies": "7_Anomalies",
        "Robustness": "8_Robustness",
    }

    selected = st.sidebar.radio("Navigation", list(pages.keys()))
    page_name = pages[selected]
    st.sidebar.caption(f"Open page: {page_name}")

    try:
        page = _load_page_module(page_name)
        if hasattr(page, "render"):
            page.render()
        else:
            st.info("This page module is available but does not yet expose a render() function.")
    except Exception as exc:  # pragma: no cover
        st.error(f"Unable to load page '{page_name}': {exc}")


if __name__ == "__main__":
    if st is None:
        raise RuntimeError("streamlit is not installed in the current environment")
