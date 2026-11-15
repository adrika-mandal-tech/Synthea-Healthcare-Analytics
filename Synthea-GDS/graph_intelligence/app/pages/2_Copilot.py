from __future__ import annotations

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

from graph_intelligence.agents.graph_agent import run_graph_agent


class _NoOpSpinner:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def render() -> None:
    if st is None:
        return

    st.title("Synthea COVID-19 Copilot")
    st.write("Ask questions about the Synthea COVID-19 healthcare graph using the graph agent and evidence-backed retrieval layer.")
    st.caption("The model can use patient, encounter, organization, condition, and care-flow relationships derived from the COVID-19 dataset.")
    question = st.text_area("Ask a graph question", "Which entities are most central in the COVID-19 referral network?")
    if st.button("Run"):
        spinner = getattr(st, "spinner", _NoOpSpinner)
        with spinner("Running graph agent..."):
            result = run_graph_agent(question, session_id="streamlit")

        st.success("Analysis complete")
        st.subheader("Answer")
        st.write(result.get("answer") or "No answer returned.")

        validation = result.get("validation") or {}
        if validation:
            st.subheader("Validation")
            st.json({
                "status": validation.get("validation_status", "UNKNOWN"),
                "coverage": validation.get("evidence_coverage"),
                "claims_checked": validation.get("claims_checked"),
                "unsupported_claims": validation.get("unsupported_claims", []),
            })

        evidence = result.get("evidence")
        if evidence is not None:
            st.subheader("Evidence")
            st.json({
                "evidence_count": len(getattr(evidence, "evidence_items", []) or []),
                "sources": getattr(evidence, "provenance", []),
            })


if __name__ == "__main__":
    render()
