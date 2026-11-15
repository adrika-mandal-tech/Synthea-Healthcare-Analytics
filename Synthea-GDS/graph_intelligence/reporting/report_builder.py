from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ReportSection:
    title: str
    content: str = ""
    bullets: List[str] = field(default_factory=list)


class ReportBuilder:
    """Build a simple markdown report from graph analysis details."""

    def __init__(self, title: str, question: str):
        self.title = title
        self.question = question
        self.sections: List[ReportSection] = []

    def add_section(self, title: str, content: str = "", bullets: Optional[List[str]] = None):
        self.sections.append(ReportSection(title=title, content=content, bullets=bullets or []))
        return self

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", f"**Question:** {self.question}", ""]

        for section in self.sections:
            lines.append(f"## {section.title}")
            if section.content:
                lines.append(section.content)
            if section.bullets:
                for bullet in section.bullets:
                    lines.append(f"- {bullet}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"


def build_report(title: str, question: str, summary: Dict[str, Any]) -> str:
    builder = ReportBuilder(title=title, question=question)
    builder.add_section(
        "Executive Summary",
        content="Generated from the local evidence-backed graph analytics pipeline.",
        bullets=[
            f"Nodes analyzed: {summary.get('node_count', 'n/a')}",
            f"Relationships analyzed: {summary.get('edge_count', 'n/a')}",
            f"Top communities: {summary.get('top_communities', 'n/a')}",
        ],
    )
    return builder.to_markdown()


def generate_covid_graph_report(
    output_path: str | Path = "reports/synthea_covid19_report.md",
    title: str = "Synthea COVID-19 Graph Report",
    question: str = "What does the Synthea COVID-19 graph reveal about patient, encounter, and care-network structure?",
) -> str:
    """Generate a markdown report from the live COVID-19 Synthea data files."""
    root = Path(__file__).resolve().parents[2]
    nodes_path = root / "data" / "nodes.csv"
    rels_path = root / "data" / "relationships.csv"
    community_path = root / "community" / "community_detection_summary.csv"

    import pandas as pd

    nodes_df = pd.read_csv(nodes_path, low_memory=False) if nodes_path.exists() else pd.DataFrame()
    rels_df = pd.read_csv(rels_path, low_memory=False) if rels_path.exists() else pd.DataFrame()
    community_df = pd.read_csv(community_path, low_memory=False) if community_path.exists() else pd.DataFrame()

    summary = {
        "node_count": int(len(nodes_df)),
        "edge_count": int(len(rels_df)),
        "top_communities": community_df["communities"].head(3).tolist() if not community_df.empty else "n/a",
        "covid_terms": int(
            nodes_df["REASONDESCRIPTION"].fillna("").astype(str).str.contains("COVID|covid|covid-19|coronavirus", case=False, na=False).sum()
            if "REASONDESCRIPTION" in nodes_df.columns else 0
        ),
    }

    builder = ReportBuilder(title=title, question=question)
    builder.add_section(
        "Dataset Snapshot",
        content="The current report uses the local Synthea COVID-19 export generated from patient, encounter, condition, and organizational relationships.",
        bullets=[
            f"Nodes: {summary['node_count']}",
            f"Relationships: {summary['edge_count']}",
            f"COVID-related reason entries: {summary['covid_terms']}",
            f"Community summary rows: {len(community_df)}",
        ],
    )

    if not community_df.empty:
        top_algorithms = community_df.head(5).to_dict(orient="records")
        builder.add_section(
            "Community Snapshot",
            content="Community detection was run across the COVID-19 graph. The selection below reflects current algorithm outputs from the community folder.",
            bullets=[
                f"{row.get('algorithm', 'unknown')}: {row.get('communities', 'n/a')} communities, modularity={row.get('modularity', 'n/a')}"
                for row in top_algorithms
            ],
        )

    report_text = builder.to_markdown()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text, encoding="utf-8")
    return report_text
