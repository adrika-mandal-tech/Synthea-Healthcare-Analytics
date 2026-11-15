from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def export_report(report_text: str, output_path: str | Path, fmt: str = "md") -> Path:
    """Write a generated report to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt.lower() not in {"md", "markdown"}:
        raise ValueError(f"Unsupported report format: {fmt}")
    path.write_text(report_text, encoding="utf-8")
    return path
