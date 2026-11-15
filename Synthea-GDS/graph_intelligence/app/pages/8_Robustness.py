from __future__ import annotations

from pathlib import Path

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


def render() -> None:
    if st is None:
        return

    st.title("Robustness Overview")
    st.write("Assess sensitivity and stability of graph algorithms on the Synthea COVID-19 dataset.")

    root = Path(__file__).resolve().parents[2]
    report_dir = root / "reports"
    if report_dir.exists():
        files = sorted(report_dir.glob("*.csv"))
        if files:
            st.caption(f"Available report artifacts: {[p.name for p in files]}")
            return

    st.caption("Robustness checks can be added here once parameter sweeps or stability runs are exported for the COVID-19 graph.")


if __name__ == "__main__":
    render()
