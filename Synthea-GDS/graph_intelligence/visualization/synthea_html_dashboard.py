from __future__ import annotations

from pathlib import Path
import html

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports"
VIS_DIR = REPORTS_DIR / "visuals" / "meaningful_model"
HTML_PATH = REPORTS_DIR / "synthea_dashboard.html"
VIS_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def metric(value: int | float) -> str:
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        return f"{value:,.2f}"
    return f"{value:,}"


def table(rows: list[list[str]]) -> str:
    out = []
    for idx, row in enumerate(rows):
        bg = "#f8fafc" if idx % 2 else "#ffffff"
        cells = "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
        out.append(f'<tr style="background:{bg};">{cells}</tr>')
    return "<table><tbody>" + "".join(out) + "</tbody></table>"


def build_summary_card() -> str:
    nodes = load_csv(ROOT / "data" / "nodes.csv")
    rels = load_csv(ROOT / "data" / "relationships.csv")
    community = load_csv(ROOT / "community" / "community_detection_summary.csv")
    algo = load_csv(ROOT / "reports" / "algorithm_summary.csv")
    pagerank = load_csv(ROOT / "centrality" / "pagerank.csv")

    total_nodes = len(nodes)
    total_edges = len(rels)
    encounter_count = int((nodes["labels"] == "Encounter").sum()) if "labels" in nodes.columns else 0
    patient_count = int((nodes["labels"] == "Patient").sum()) if "labels" in nodes.columns else 0
    org_count = int((nodes["labels"] == "Organization").sum()) if "labels" in nodes.columns else 0
    algo_total = int(algo["total_algorithms"].iloc[0]) if not algo.empty and "total_algorithms" in algo.columns else 0
    algo_done = int(algo["completed"].iloc[0]) if not algo.empty and "completed" in algo.columns else 0
    requires_params = int(algo["requires_parameters"].iloc[0]) if not algo.empty and "requires_parameters" in algo.columns else 0

    community_max = int(community["communities"].max()) if not community.empty and "communities" in community.columns else 0
    top_entity = "-"
    top_score = "-"
    if not pagerank.empty and "score" in pagerank.columns and "name" in pagerank.columns:
        top = pagerank.sort_values("score", ascending=False).head(1).iloc[0]
        top_entity = str(top.get("name", "-"))
        top_score = f"{float(top.get('score', 0.0)):.6f}"

    cards = [
        ("Nodes", metric(total_nodes)),
        ("Relationships", metric(total_edges)),
        ("Encounters", metric(encounter_count)),
        ("Patients", metric(patient_count)),
        ("Organizations", metric(org_count)),
        ("Completed algorithms", metric(algo_done)),
    ]

    summary_rows = [
        ["Metric", "Value"],
        ["Total nodes", metric(total_nodes)],
        ["Total relationships", metric(total_edges)],
        ["Encounter nodes", metric(encounter_count)],
        ["Patient nodes", metric(patient_count)],
        ["Organization nodes", metric(org_count)],
        ["Algorithms total", metric(algo_total)],
        ["Completed", metric(algo_done)],
        ["Requires parameters", metric(requires_params)],
        ["Community peak", metric(community_max)],
        ["Top PageRank entity", top_entity],
        ["Top PageRank score", top_score],
    ]

    cards_html = "".join(
        f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div></div>'
        for label, value in cards
    )
    summary_html = table(summary_rows)
    return cards_html, summary_html


def build_html() -> str:
    cards_html, summary_html = build_summary_card()

    chart_sections = [
        (
            "Node type distribution",
            "visuals/meaningful_model/node_type_distribution.png",
            "This chart shows the dominant entity classes in the graph. Encounters and organizational nodes lead the structure, which indicates a care-flow network centered on activity and delivery rather than isolated patient records.",
        ),
        (
            "Relationship type distribution",
            "visuals/meaningful_model/relationship_type_distribution.png",
            "The relationship pattern confirms the graph is operational: treatment, prescription, billing, and encounter flows dominate the edge structure and reflect real healthcare process semantics.",
        ),
        (
            "Community structure",
            "visuals/meaningful_model/community_algorithm_summary.png",
            "Community detection reveals multiple dense clusters across the graph, suggesting recurring clinical or organizational neighborhoods that can support segmentation and care-pattern analysis.",
        ),
        (
            "Centrality influence",
            "visuals/meaningful_model/centrality_top_nodes.png",
            "This view highlights the nodes with the greatest structural influence. The most important entities are the recurring operational hubs that connect larger portions of the network.",
        ),
        (
            "Conceptual healthcare knowledge graph",
            "visuals/meaningful_model/conceptual_healthcare_knowledge_graph.png",
            "This conceptual graph explains the healthcare data model at a glance: patient activity connects to encounters, which then link to providers, conditions, medications, and coverage. It captures the operational logic of the Synthea dataset.",
        ),
    ]

    chart_html = "".join(
        f'''
        <div class="chart-card">
          <h2>{title}</h2>
          <img src="{img}" alt="{title}" />
          <p>{text}</p>
        </div>
        '''
        for title, img, text in chart_sections
    )

    key_findings = [
        "The graph is dominated by operational care entities, which points to a workflow-driven healthcare network rather than a purely patient-centric network.",
        "Encounter nodes and relationship flow are the principal structural backbone, meaning treatment activity and care coordination are the main drivers of connectivity.",
        "Community structure shows multiple dense clusters, which supports segmentation and subgroup analysis across clinical or organizational pathways.",
        "PageRank and centrality outputs identify recurring operational hubs that connect broad parts of the healthcare graph.",
        "Most of the algorithm portfolio completed successfully; the remaining parameter-dependent algorithms are expected in graph analysis workflows that require tuning.",
    ]

    findings_html = "".join(f"<li>{html.escape(item)}</li>" for item in key_findings)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Synthea Healthcare Graph Dashboard</title>
  <style>
    :root {{
      --bg: #f3f7fb;
      --panel: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --line: #dfe7f4;
      --primary: #1d4ed8;
      --primary-2: #0f766e;
      --shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: Arial, Helvetica, sans-serif; background: var(--bg); color: var(--ink);
    }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 28px 18px 50px; }}
    .hero {{
      background: linear-gradient(135deg, #0f172a, #1d4ed8 55%, #0ea5e9);
      border-radius: 18px; color: white; padding: 30px 26px; box-shadow: var(--shadow);
    }}
    h1 {{ margin: 0 0 10px; font-size: 2.5rem; }}
    .subtitle {{ max-width: 780px; color: rgba(255,255,255,0.82); line-height: 1.6; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 16px; margin: 24px 0;
    }}
    .card {{
      background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
      padding: 18px 16px; box-shadow: var(--shadow);
    }}
    .label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }}
    .value {{ margin-top: 10px; font-size: 1.7rem; font-weight: 700; }}
    .summary-grid {{
      display: grid; grid-template-columns: 1fr 1.15fr; gap: 20px; margin-bottom: 20px;
      align-items: start;
    }}
    .panel {{
      background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
      padding: 18px; box-shadow: var(--shadow);
    }}
    .summary-highlight {{
      display: flex; flex-direction: column; justify-content: center; gap: 8px;
      padding: 12px 8px; font-size: 1.05rem; line-height: 1.7; color: #334155;
      min-height: 0;
    }}
    .badge {{
      display: inline-block; padding: 5px 12px; border-radius: 999px;
      background: #ecfeff; color: #115e59; border: 1px solid #a7f3d0;
      font-size: 0.78rem; font-weight: 700; margin-bottom: 12px;
    }}
    .panel h2 {{ margin: 0 0 12px; font-size: 1.2rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ background: #eef4ff; color: #1e3a8a; }}
    .chart-grid {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;
    }}
    .chart-card {{
      background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
      padding: 18px; box-shadow: var(--shadow);
    }}
    .chart-card h2 {{ margin-top: 0; margin-bottom: 12px; font-size: 1.15rem; }}
    .chart-card img {{
      display: block; width: 100%; height: auto; max-height: 410px; object-fit: contain;
      border: 1px solid var(--line); border-radius: 10px; background: white;
    }}
    .chart-card p {{ margin: 12px 0 0; line-height: 1.65; color: #334155; }}
    .insights {{
      list-style: none; padding: 0; margin: 0; display: grid; gap: 10px;
    }}
    .insights li {{
      background: #f8fafc; border: 1px solid var(--line); border-radius: 10px;
      padding: 12px 14px; line-height: 1.6;
    }}
    .grid {{
      display: grid; grid-template-columns: 1.1fr 1fr; gap: 20px; margin-top: 20px;
    }}
    .footer {{ margin-top: 24px; color: var(--muted); font-size: 0.9rem; }}
    @media (max-width: 900px) {{
      .summary-grid, .chart-grid, .grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 2rem; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Synthea Healthcare Graph Dashboard</h1>
      <div class="subtitle">
        Executive overview of the generated healthcare knowledge graph. This page brings together the clearest visuals from the project into one readable, insight-driven dashboard based on the real Synthea graph exports.
      </div>
    </section>

    <section class="cards">
      {cards_html}
    </section>

    <section class="summary-grid">
      <div class="panel">
        <div class="badge">Dataset profile</div>
        <h2>Graph overview</h2>
        {summary_html}
      </div>
      <div class="panel">
        <div class="badge">Structural signal</div>
        <h2>Top PageRank entity</h2>
        <div class="summary-highlight">
          <div><strong>Entity:</strong> {html.escape(str((load_csv(ROOT / 'centrality' / 'pagerank.csv').sort_values('score', ascending=False).head(1).iloc[0]['name']) if not load_csv(ROOT / 'centrality' / 'pagerank.csv').empty and 'name' in load_csv(ROOT / 'centrality' / 'pagerank.csv').columns else '-'))}</div>
          <div><strong>Score:</strong> {html.escape(str(f"{float(load_csv(ROOT / 'centrality' / 'pagerank.csv').sort_values('score', ascending=False).head(1).iloc[0]['score']):.6f}" if not load_csv(ROOT / 'centrality' / 'pagerank.csv').empty and 'score' in load_csv(ROOT / 'centrality' / 'pagerank.csv').columns else '-'))}</div>
        </div>
      </div>
    </section>

    <section class="chart-grid">
      {chart_html}
    </section>

    <section class="grid">
      <div class="panel">
        <div class="badge">Narrative</div>
        <h2>Key findings</h2>
        <ul class="insights">{findings_html}</ul>
      </div>
      <div class="panel">
        <div class="badge">Interpretation</div>
        <h2>What the graph is telling us</h2>
        <p style="margin: 0; line-height: 1.75; color: #334155;">
          This graph behaves like a healthcare operations and clinical workflow network. The dominant connectivity is centered around encounters, care events, and institutional relationships, which means the network is driven less by isolated patient records and more by patterns of care delivery, reimbursement logic, and ongoing treatment coordination. The community structure confirms repeated subgroup neighborhoods that can support cohort analysis, anomaly detection, or pathway segmentation.
        </p>
      </div>
    </section>

    <div class="footer">
      Generated from the local Synthea graph exports, analytics outputs, and visualization assets in this repository.
    </div>
  </div>
</body>
</html>
"""


def main() -> None:
    HTML_PATH.write_text(build_html(), encoding="utf-8")
    print(f"Generated clean dashboard: {HTML_PATH}")


if __name__ == "__main__":
    main()
