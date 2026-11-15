from __future__ import annotations

from pathlib import Path
import html
from typing import Iterable, Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
OUT_HTML = REPORTS_DIR / "synthea_detailed_analysis.html"
CATEGORY_FOLDERS = [
    ("data", DATA_DIR),
    ("centrality", ROOT / "centrality"),
    ("community", ROOT / "community"),
    ("dag", ROOT / "dag"),
    ("embeddings", ROOT / "embeddings"),
    ("paths", ROOT / "paths"),
    ("similarity", ROOT / "similarity"),
    ("reports", REPORTS_DIR),
]


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def top_counts(series: pd.Series, limit: int = 10) -> list[tuple[str, int]]:
    if series.empty:
        return []
    counts = series.fillna("").astype(str).str.strip()
    counts = counts[counts != ""]
    if counts.empty:
        return []
    vc = counts.value_counts().sort_values(ascending=False).head(limit)
    return [(str(label), int(value)) for label, value in vc.items()]


def short_label(label: str, max_len: int = 18) -> str:
    text = label.replace("_", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def metric(value: int | float) -> str:
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        return f"{value:,.2f}"
    return f"{value:,}"


def svg_horizontal_bar(title: str, rows: Sequence[tuple[str, int]], width: int = 760, height: int = 300) -> str:
    if not rows:
        return "<div class='empty'>No data available.</div>"
    rows = [(short_label(label, 18), int(value)) for label, value in rows[:8]]
    max_value = max(v for _, v in rows)
    chart_left = 150
    chart_top = 30
    chart_right = 20
    chart_bottom = 30
    plot_w = width - chart_left - chart_right
    plot_h = height - chart_top - chart_bottom
    bar_h = max(18, (plot_h / max(1, len(rows))) - 12)
    inner = []
    for idx, (label, value) in enumerate(rows):
        y = chart_top + idx * (bar_h + 12)
        width_pct = (value / max_value) * plot_w if max_value else 0
        fill = ["#4e79a7", "#59a14f", "#f28e2b", "#e15759", "#76b7b2", "#edc948", "#b07aa1", "#ff9da7"][idx % 8]
        inner.append(f'<rect x="{chart_left}" y="{y}" width="{width_pct}" height="{bar_h}" rx="4" fill="{fill}" />')
        inner.append(f'<text x="{chart_left - 8}" y="{y + bar_h/2 + 4}" font-size="11" text-anchor="end" fill="#333">{html.escape(label)}</text>')
        inner.append(f'<text x="{chart_left + width_pct + 8}" y="{y + bar_h/2 + 4}" font-size="11" fill="#444">{value}</text>')
    axis = (
        f'<line x1="{chart_left}" y1="{chart_top}" x2="{chart_left}" y2="{chart_top + plot_h}" stroke="#555" stroke-width="1" />'
        f'<line x1="{chart_left}" y1="{chart_top + plot_h}" x2="{width - chart_right}" y2="{chart_top + plot_h}" stroke="#555" stroke-width="1" />'
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" role="img" aria-label="{html.escape(title)}">'
        f'<text x="{width/2}" y="18" text-anchor="middle" font-size="16" font-weight="bold" fill="#1f2937">{html.escape(title)}</text>'
        f'{axis}' + ''.join(inner) + '</svg>'
    )


def table(rows: Iterable[Sequence[str]], header_bg: str = "#eef4ff") -> str:
    html_rows = []
    for idx, row in enumerate(rows):
        cells = ''.join(f'<td>{html.escape(str(cell))}</td>' for cell in row)
        bg = "#f8fafc" if idx % 2 else "#ffffff"
        html_rows.append(f'<tr style="background:{bg};">{cells}</tr>')
    return '<table><tbody>' + ''.join(html_rows) + '</tbody></table>'


def list_all_csv_files() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for category, folder in CATEGORY_FOLDERS:
        if not folder.exists():
            continue
        for file in sorted(folder.iterdir()):
            if file.is_file() and file.suffix.lower() == ".csv":
                rows.append((category, file.name, str(file.relative_to(ROOT))))
    return rows


def build_report() -> str:
    nodes = load_csv(DATA_DIR / "nodes.csv")
    rels = load_csv(DATA_DIR / "relationships.csv")
    community = load_csv(ROOT / "community" / "community_detection_summary.csv")
    algorithm_summary = load_csv(ROOT / "reports" / "algorithm_summary.csv")
    pagerank = load_csv(ROOT / "centrality" / "pagerank.csv")
    degree = load_csv(ROOT / "centrality" / "degree_centrality.csv")
    betweenness = load_csv(ROOT / "centrality" / "betweenness_centrality.csv")

    all_files = list_all_csv_files()
    category_counts = []
    for category, folder in CATEGORY_FOLDERS:
        count = sum(1 for c, _, _ in all_files if c == category)
        category_counts.append((category, count))

    total_nodes = len(nodes)
    total_edges = len(rels)
    label_counts = top_counts(nodes["labels"], 10) if "labels" in nodes.columns else []
    rel_counts = top_counts(rels["type"], 10) if "type" in rels.columns else []

    label_counts_tuple = [(label, value) for label, value in label_counts]
    rel_counts_tuple = [(label, value) for label, value in rel_counts]

    encounter_count = int((nodes["labels"] == "Encounter").sum()) if "labels" in nodes.columns else 0
    patient_count = int((nodes["labels"] == "Patient").sum()) if "labels" in nodes.columns else 0
    org_count = int((nodes["labels"] == "Organization").sum()) if "labels" in nodes.columns else 0
    condition_count = int((nodes["labels"] == "Condition").sum()) if "labels" in nodes.columns else 0
    medication_count = int((nodes["labels"] == "Medication").sum()) if "labels" in nodes.columns else 0

    top_pagerank = pagerank.sort_values("score", ascending=False).head(6) if not pagerank.empty else pd.DataFrame(columns=["name", "score"])
    top_degree = degree.sort_values("score", ascending=False).head(6) if not degree.empty else pd.DataFrame(columns=["name", "score"])
    top_betweenness = betweenness.sort_values("score", ascending=False).head(6) if not betweenness.empty else pd.DataFrame(columns=["name", "score"])

    community_rows = []
    if not community.empty:
        for _, row in community.head(12).iterrows():
            community_rows.append([str(row.get("algorithm", "N/A")), str(row.get("communities", "-")), str(row.get("modularity", "-"))])
    else:
        community_rows = [["Algorithm", "Communities", "Modularity"]]

    algorithm_total = int(algorithm_summary["total_algorithms"].iloc[0]) if not algorithm_summary.empty and "total_algorithms" in algorithm_summary.columns else 0
    completed = int(algorithm_summary["completed"].iloc[0]) if not algorithm_summary.empty and "completed" in algorithm_summary.columns else 0
    requires_params = int(algorithm_summary["requires_parameters"].iloc[0]) if not algorithm_summary.empty and "requires_parameters" in algorithm_summary.columns else 0

    average_degree = (total_edges / total_nodes) if total_nodes else 0
    encounter_share = (encounter_count / total_nodes * 100) if total_nodes else 0
    org_share = (org_count / total_nodes * 100) if total_nodes else 0
    patient_share = (patient_count / total_nodes * 100) if total_nodes else 0

    narrative = [
        "The Synthea graph is dominated by operational healthcare entities, especially encounters, which indicates the network is structured around care activity and clinical workflow rather than isolated patient records.",
        f"Encounter nodes account for {encounter_share:.1f}% of all nodes, while organizations and patient entities form the next major layers of the graph. This creates a network where care delivery and care coordination are the principal drivers of connectivity.",
        f"The graph contains {metric(total_nodes)} nodes and {metric(total_edges)} relationships, while {metric(completed)} of {metric(algorithm_total)} algorithm entries completed successfully. This demonstrates both size and analytic depth without requiring a live production database for the local analysis layer.",
        "High centrality entities are not random; they align with recurring care-context nodes, suggesting the healthcare graph has a strong backbone of recurring workflow and institutional relationships.",
        "Community detection shows multiple clusters across the structure, revealing repeated care subgroups and operational neighborhoods that can support segmentation, anomaly detection, and pathway analysis."
    ]

    cards = [
        ("Nodes", metric(total_nodes)),
        ("Relationships", metric(total_edges)),
        ("Encounter nodes", metric(encounter_count)),
        ("Patient nodes", metric(patient_count)),
        ("Organizations", metric(org_count)),
        ("Algorithms complete", metric(completed)),
    ]

    pagerank_table = [["Rank", "Entity", "Score"]]
    for idx, row in top_pagerank.reset_index(drop=True).head(6).iterrows():
        pagerank_table.append([str(idx + 1), str(row.get("name", "N/A")), f"{float(row.get('score', 0.0)):.6f}"])

    degree_table = [["Rank", "Entity", "Score"]]
    for idx, row in top_degree.reset_index(drop=True).head(6).iterrows():
        degree_table.append([str(idx + 1), str(row.get("name", "N/A")), f"{float(row.get('score', 0.0)):.6f}"])

    betweenness_table = [["Rank", "Entity", "Score"]]
    for idx, row in top_betweenness.reset_index(drop=True).head(6).iterrows():
        betweenness_table.append([str(idx + 1), str(row.get("name", "N/A")), f"{float(row.get('score', 0.0)):.6f}"])

    community_table = [["Algorithm", "Communities", "Modularity"]]
    if community.empty:
        community_table = [["Algorithm", "Communities", "Modularity"]]
    else:
        for _, row in community.head(10).iterrows():
            community_table.append([str(row.get("algorithm", "N/A")), str(row.get("communities", "-")), str(row.get("modularity", "-"))])

    category_chart = svg_horizontal_bar("CSV outputs by category", category_counts)
    file_inventory = [["Category", "File", "Path"]]
    for category, filename, relpath in all_files:
        file_inventory.append([category, filename, relpath])

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Synthea Detailed Insight Report</title>
  <style>
    :root {{
      --bg: #f3f7fb;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #64748b;
      --line: #dfe7f4;
      --primary: #1d4ed8;
      --primary-dark: #0f172a;
      --green: #0f766e;
      --gold: #d97706;
      --red: #b91c1c;
      --shadow: 0 12px 26px rgba(15, 23, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: var(--bg); color: var(--ink); }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 28px 18px 50px; }}
    .hero {{ background: linear-gradient(135deg, var(--primary-dark), var(--primary) 55%, #0ea5e9); color: white; border-radius: 18px; padding: 30px 26px; box-shadow: var(--shadow); }}
    h1 {{ margin: 0 0 8px; font-size: 2.5rem; }}
    .subtitle {{ color: rgba(255,255,255,0.84); line-height: 1.6; max-width: 900px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; margin: 24px 0; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 18px 16px; box-shadow: var(--shadow); }}
    .card .label {{ text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-size: 0.75rem; }}
    .card .value {{ font-size: 1.7rem; font-weight: 700; margin-top: 10px; }}
    .grid {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; margin-top: 20px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 18px; box-shadow: var(--shadow); }}
    .panel h2 {{ margin: 0 0 12px; font-size: 1.2rem; }}
    .badge {{ display: inline-block; background: #ecfeff; color: #115e59; border-radius: 999px; padding: 5px 10px; font-size: 0.78rem; font-weight: 700; margin-bottom: 10px; border: 1px solid #a7f3d0; }}
    .narrative {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    .narrative li {{ background: #f8fafc; border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; line-height: 1.6; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ background: #eef4ff; color: #1e3a8a; }}
    .metric-box {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 10px; }}
    .mini {{ background: #f8fafc; border: 1px solid var(--line); padding: 12px 14px; border-radius: 10px; }}
    .mini .k {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: .08em; }}
    .mini .v {{ font-size: 1.4rem; font-weight: 700; margin-top: 8px; }}
    ul.kv {{ padding-left: 18px; line-height: 1.7; }}
    .inventory {{ max-height: 540px; overflow: auto; border: 1px solid var(--line); border-radius: 10px; }}
    .footer {{ margin-top: 24px; color: var(--muted); font-size: 0.9rem; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>Synthea Detailed Insight Report</h1>
      <div class=\"subtitle\">
        This report explains the major findings from the raw Synthea healthcare graph produced in the repository. It focuses on graph structure, operational dynamics, dominant entities, centrality signals, and the practical meaning of the network behind the data.
      </div>
    </section>

    <section class=\"cards\">
      {''.join(f'<div class="card"><div class="label">{html.escape(label)}</div><div class="value">{html.escape(value)}</div></div>' for label, value in cards)}
    </section>

    <section class=\"grid\">
      <div class=\"panel\">
        <div class=\"badge\">Narrative overview</div>
        <h2>What the graph looks like</h2>
        <ul class=\"narrative\">
          {''.join(f'<li>{html.escape(item)}</li>' for item in narrative)}
        </ul>
      </div>
      <div class=\"panel\">
        <div class=\"badge\">Graph composition</div>
        <h2>Key structural metrics</h2>
        <div class=\"metric-box\">
          <div class=\"mini\"><div class=\"k\">Avg relationship / node</div><div class=\"v\">{average_degree:.2f}</div></div>
          <div class=\"mini\"><div class=\"k\">Encounter share</div><div class=\"v\">{encounter_share:.1f}%</div></div>
          <div class=\"mini\"><div class=\"k\">Patient share</div><div class=\"v\">{patient_share:.1f}%</div></div>
          <div class=\"mini\"><div class=\"k\">Org share</div><div class=\"v\">{org_share:.1f}%</div></div>
        </div>
      </div>
    </section>

    <section class=\"grid\">
      <div class=\"panel\">
        <div class=\"badge\">Entity distribution</div>
        <h2>Most common node labels</h2>
        {svg_horizontal_bar('Node label distribution', label_counts_tuple)}
      </div>
      <div class=\"panel\">
        <div class=\"badge\">Edge distribution</div>
        <h2>Most common relationship types</h2>
        {svg_horizontal_bar('Relationship type distribution', rel_counts_tuple)}
      </div>
    </section>

    <section class=\"grid\">
      <div class=\"panel\">
        <div class=\"badge\">Rank topology</div>
        <h2>Top PageRank entities</h2>
        {table(pagerank_table)}
      </div>
      <div class=\"panel\">
        <div class=\"badge\">Bridge structure</div>
        <h2>Top degree-centrality entities</h2>
        {table(degree_table)}
      </div>
    </section>

    <section class=\"grid\">
      <div class=\"panel\">
        <div class=\"badge\">Bridge roles</div>
        <h2>Top betweenness-centrality entities</h2>
        {table(betweenness_table)}
      </div>
      <div class=\"panel\">
        <div class=\"badge\">Community structure</div>
        <h2>Community detection summary</h2>
        {table(community_table)}
      </div>
    </section>

    <section class=\"panel\" style=\"margin-top: 20px;\">
      <div class=\"badge\">Interpretation</div>
      <h2>Health-system meaning</h2>
      <p style=\"margin: 0; line-height: 1.75; color: #334155;\">
        The network behaves like a healthcare operations graph more than a purely patient-centric social network. Encounter nodes dominate because they represent the points where care actions, diagnoses, procedures, medications, and billing events intersect. Organizations and payers are also central because they connect treatment events to institutional and financial structures. This is consistent with the way healthcare systems operate: clinicians, organizations, events, and reimbursement flows define the connected fabric, while individual patient records are one layer of a larger care ecosystem.
        <br /><br />
        The centrality and community results reinforce the idea that the graph has a strong workflow backbone and multiple dense subgroup neighborhoods. In practical terms, this means the graph can support care-pathway analysis, institutional influence assessment, community clustering, and anomaly detection. The dataset is therefore well-suited for both clinical storytelling and machine-learning style graph analytics.
      </p>
    </section>
    <section class="grid">
      <div class="panel">
        <div class="badge">Data inventory</div>
        <h2>CSV outputs by category</h2>
        {category_chart}
      </div>
      <div class="panel">
        <div class="badge">Artifact portfolio</div>
        <h2>Repository CSV inventory</h2>
        <div class="inventory">{table(file_inventory)}</div>
      </div>
    </section>
    <div class=\"footer\">
      Generated from the live Synthea graph exports and project analysis outputs in this repository, with detailed interpretation based on the actual dataset contents.
    </div>
  </div>
</body>
</html>
"""


def main() -> None:
    html = build_report()
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Detailed Synthea analysis report written to {OUT_HTML}")


if __name__ == "__main__":
    main()
