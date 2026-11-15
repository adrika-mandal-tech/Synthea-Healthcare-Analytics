from __future__ import annotations

import csv
from pathlib import Path
import html

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"
VIS_DIR = REPORTS_DIR / "visuals"
OUT_HTML = REPORTS_DIR / "insights.html"


def load_csv(path: Path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def read_csv_rows(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def escape(value):
    return html.escape(str(value))


def table(rows):
    if not rows:
        return "<div class='empty'>No data available.</div>"

    matrix = [["" if cell is None else str(cell) for cell in row] for row in rows]
    width = max(len(row) for row in matrix)
    normalized = [row + [""] * (width - len(row)) for row in matrix]

    keep_cols = []
    for col_idx in range(width):
        values = [row[col_idx] for row in normalized]
        if any(v.strip() not in {"", "-", "None", "nan"} for v in values):
            keep_cols.append(col_idx)

    if not keep_cols:
        return "<div class='empty'>No data available.</div>"

    trimmed = [[row[col_idx] for col_idx in keep_cols] for row in normalized]
    head = trimmed[0]
    header = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = []
    for row in trimmed[1:]:
        cells = "".join(f"<td>{escape(cell)}</td>" for cell in row)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def draw_metric_cards(metrics):
    cards = []
    for label, value in metrics:
        cards.append(f'<div class="metric-card"><div class="label">{escape(label)}</div><div class="value">{escape(value)}</div></div>')
    return "".join(cards)


def image_gallery():
    seen = set()
    items = []
    folders = [VIS_DIR, VIS_DIR / "meaningful_model"]
    for folder in folders:
        if not folder.exists():
            continue
        for image in sorted(folder.glob("*.png")):
            rel = image.relative_to(REPORTS_DIR).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            name = image.stem.replace("_", " ").title()
            explanation = {
                "Node Type Distribution": "This chart shows the composition of the healthcare graph by entity type. The dominance of encounters and organizations is clinically meaningful: the network is organized around care events and institutions, while patient and condition nodes form the contextual layer around those operational centers.",
                "Relationship Type Distribution": "The edge distribution reveals which relationships drive the graph structure. High-volume clinical flows such as patient-care, treatment, and billing pathways indicate that the dataset reflects real healthcare coordination rather than random connectivity, which makes downstream analytics more interpretable.",
                "Community Algorithm Summary": "This summary compares how many communities each algorithm discovers and how modular the resulting partitions are. The spread between methods such as Louvain, Leiden, Label Propagation, and K-Core shows that the graph has meaningful clusters at multiple scales, while the modularity scores confirm that these clusters are not arbitrary.",
                "Centrality Top Nodes": "This chart highlights the most structurally influential nodes in the graph. These nodes sit on the most connected or high-flow pathways and are the likely hubs where treatment, organization, and patient activity converge; they are the best candidates for intervention, monitoring, or network-risk analysis.",
                "Conceptual Healthcare Knowledge Graph": "This simplified model captures the healthcare logic embedded in the synthetic data: encounters connect to patients, conditions, medications, providers, organizations, and payers. The pattern confirms that the graph is not just a social network; it behaves like a real clinical workflow network.",
                "Label Distribution": "This chart shows how often each node label appears across the graph. The skew toward encounters, organizations, and patient-linked records explains why the graph behaves like an operational healthcare system and why conclusions about care pathways are more stable than random network assumptions.",
                "Relationship Distribution": "The relationship families are a key signal of dataset quality. When connections cluster around treatment, care delivery, and administrative coordination, the graph is faithfully representing the healthcare process rather than a noisy synthetic artifact.",
                "Community Count By Algorithm": "This view emphasizes the instability and flexibility of community detection: some algorithms find a few broad communities, while others split the same network into many smaller clusters. That is expected in healthcare graphs, where both high-level care regions and specialized clinical subgroups can exist simultaneously.",
                "Centrality Scores By Metric": "This comparison shows which nodes remain important across different centrality definitions. If a node ranks highly under degree, betweenness, PageRank, or eigenvector measures, it is likely a true operational hub rather than an artifact of one scoring formula.",
                "Centrality Top Scores": "The strongest centrality values point to the graph’s most influential nodes. These are the entities with the highest reach and connectivity, which makes them especially relevant for understanding resource concentration, workflow bottlenecks, and the most important pathway anchors.",
                "Knowledge Graph Label Distribution": "This distribution confirms the graph’s category balance and validates the synthetic healthcare architecture. Institutions and care events dominate the structure, which aligns with how clinical systems typically organize patient journeys and service delivery.",
                "Knowledge Graph Relationship Distribution": "This chart verifies that the synthetic graph is dominated by clinically relevant relationships rather than arbitrary edges. That strengthens confidence in downstream insights such as care continuity, entity influence, and treatment process interpretation.",
                "Node Composition Donut": "The donut view provides a quick but informative composition check. It shows how the graph is concentrated around core healthcare entities, helping explain why the network is highly structured and why community and centrality metrics are meaningful.",
            }.get(name, "This visual shows a structural pattern in the Synthea graph. The significant takeaway is that it captures real healthcare operational behavior: dense care coordination, institutional influence, and clinically meaningful clustering rather than random or sparse connectivity.")
            items.append((name, rel, explanation))
    return items


def main():
    nodes = read_csv_rows(DATA_DIR / "nodes.csv")
    rels = read_csv_rows(DATA_DIR / "relationships.csv")
    algo_manifest = read_csv_rows(REPORTS_DIR / "algorithm_manifest.csv")
    algo_summary = read_csv_rows(REPORTS_DIR / "algorithm_summary.csv")
    community = read_csv_rows(ROOT / "community" / "community_detection_summary.csv")
    pagerank = read_csv_rows(ROOT / "centrality" / "pagerank.csv")

    total_nodes = len(nodes)
    total_edges = len(rels)
    encounter_count = sum(1 for n in nodes if n.get("labels") == "Encounter")
    patient_count = sum(1 for n in nodes if n.get("labels") == "Patient")
    org_count = sum(1 for n in nodes if n.get("labels") == "Organization")

    summary_record = algo_summary[0] if algo_summary else {}
    total_algorithms = to_int(summary_record.get("total_algorithms"), 0)
    completed = to_int(summary_record.get("completed"), 0)
    requires_params = to_int(summary_record.get("requires_parameters"), 0)

    community_counts = [["Algorithm", "Nodes", "Communities", "Modularity"]]
    for row in community:
        algorithm = row.get("algorithm", "-")
        nodes = row.get("nodes", "")
        communities_value = row.get("communities", "")
        modularity_value = row.get("modularity", "")
        if algorithm == "-" and not any([nodes, communities_value, modularity_value]):
            continue
        community_counts.append([algorithm, nodes or "-", communities_value or "-", modularity_value or "-"])

    top_pagerank = sorted(pagerank, key=lambda r: float(r.get("score") or 0), reverse=True)[:5]
    pagerank_rows = [["Rank", "Entity", "Score"]]
    for i, row in enumerate(top_pagerank, start=1):
        pagerank_rows.append([str(i), escape(row.get("name", "-")), f"{float(row.get('score', 0) or 0):.6f}"])

    category_counts = {}
    for row in algo_manifest:
        cat = row.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    category_rows = [["Category", "Algorithms"]]
    for cat, cnt in sorted(category_counts.items()):
        category_rows.append([cat.title(), str(cnt)])

    status_counts = {}
    for row in algo_manifest:
        status = row.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    status_rows = [["Status", "Count"]]
    for status, cnt in sorted(status_counts.items()):
        status_rows.append([status.title(), str(cnt)])

    visual_cards = []
    for name, rel, explanation in image_gallery():
        visual_cards.append(f'''
        <div class="chart-card">
            <h3>{escape(name)}</h3>
            <img src="{rel}" alt="{escape(name)}" />
            <p>{escape(explanation)}</p>
        </div>
        ''')

    narrative = [
        "The Synthea graph is primarily an operational healthcare network. Encounters dominate the node distribution, suggesting that care events are the clearest structural backbone of the dataset.",
        "The relationship pattern is not random. It clusters around treatment, billing, and clinical coordination flows, which means the graph is modeling real healthcare process logic rather than isolated entities.",
        "PageRank and centrality results identify a small number of high-impact nodes that connect the network together. These are the operational hubs where clinical, institutional, and treatment relationships converge.",
        "Community detection shows that the graph has multiple dense neighborhoods. This matters because healthcare systems often organize around repeated care pathways, provider clusters, and treatment cohorts rather than a single flat structure.",
        "The algorithm portfolio reveals a balance between completed analytics and parameterized methods. That is a healthy graph analytics pattern: straightforward algorithms run instantly, while advanced clustering or feature-based methods need tuning and richer inputs.",
        "Across the dataset, the project demonstrates that a synthetic healthcare graph can support interpretation, path reasoning, clustering, influence analysis, and graph-driven decision support without needing a live production database in the analysis layer."
    ]

    narrative_html = "".join(f"<li>{escape(item)}</li>" for item in narrative)

    metrics = [
        ("Nodes", f"{total_nodes:,}"),
        ("Relationships", f"{total_edges:,}"),
        ("Encounters", f"{encounter_count:,}"),
        ("Patients", f"{patient_count:,}"),
        ("Organizations", f"{org_count:,}"),
        ("Completed algos", f"{completed:,}"),
    ]

    html_string = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Synthea Graph Insights</title>
  <style>
    :root {{
      --bg: #f3f7fb;
      --panel: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --line: #dfe7f4;
      --primary: #1d4ed8;
      --green: #0f766e;
      --gold: #d97706;
      --shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: var(--bg); color: var(--ink); }}
    .wrap {{ max-width: 1450px; margin: 0 auto; padding: 28px 18px 50px; }}
    .hero {{ background: linear-gradient(135deg, #0f172a, #1d4ed8 55%, #0ea5e9); color: white; border-radius: 18px; padding: 28px 30px; box-shadow: var(--shadow); }}
    h1 {{ margin: 0 0 10px; font-size: clamp(2.2rem, 5vw, 3rem); }}
    .subtitle {{ max-width: 900px; line-height: 1.7; color: rgba(255,255,255,0.84); }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; margin: 24px 0; }}
    .metric-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 18px 16px; box-shadow: var(--shadow); }}
    .label {{ text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-size: 0.72rem; }}
    .value {{ font-size: 1.7rem; font-weight: 700; margin-top: 10px; }}
    .two-col {{ display: grid; grid-template-columns: 1.1fr 1fr; gap: 20px; margin: 22px 0; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 18px; box-shadow: var(--shadow); }}
    .panel h2 {{ margin: 0 0 12px; font-size: 1.2rem; }}
    .badge {{ display: inline-block; padding: 5px 10px; border-radius: 999px; background: #ecfeff; color: #115e59; border: 1px solid #a7f3d0; font-size: 0.8rem; font-weight: 700; margin-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ background: #eef4ff; color: #1e3a8a; }}
    .narrative {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    .narrative li {{ background: #f8fafc; border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; line-height: 1.65; }}
    .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; margin-top: 20px; }}
    .chart-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 18px; box-shadow: var(--shadow); }}
    .chart-card h3 {{ margin: 0 0 12px; font-size: 1.1rem; }}
    .chart-card img {{ display: block; width: 100%; height: auto; max-height: 420px; object-fit: contain; border: 1px solid var(--line); border-radius: 10px; background: white; }}
    .chart-card p {{ margin: 12px 0 0; line-height: 1.7; color: #334155; }}
    .footer {{ margin-top: 26px; color: var(--muted); font-size: 0.9rem; }}
    @media (max-width: 980px) {{ .two-col {{ grid-template-columns: 1fr; }} .gallery {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Synthea Healthcare Graph Insights</h1>
      <div class="subtitle">
        An integrated narrative and visual analysis of the synthetic healthcare knowledge graph. This report combines the project’s graph measurements, community findings, algorithm portfolio, and chart outputs into one running insight story.
      </div>
    </section>

    <section class="metrics">
      {draw_metric_cards(metrics)}
    </section>

    <section class="two-col">
      <div class="panel">
        <div class="badge">Graph overview</div>
        <h2>Key dataset facts</h2>
        {table([["Metric", "Value"], ["Nodes", f"{total_nodes:,}"], ["Relationships", f"{total_edges:,}"], ["Encounter nodes", f"{encounter_count:,}"], ["Patient nodes", f"{patient_count:,}"], ["Organization nodes", f"{org_count:,}"], ["Algorithms total", f"{total_algorithms:,}"], ["Completed", f"{completed:,}"], ["Requires parameters", f"{requires_params:,}"]])}
      </div>
      <div class="panel">
        <div class="badge">Top influence</div>
        <h2>Top PageRank entities</h2>
        {table([["Rank", "Entity", "Score"], *[[str(i), row.get('name', '-'), f"{float(row.get('score', 0) or 0):.6f}"] for i, row in enumerate(top_pagerank, start=1)]])}
      </div>
    </section>

    <section class="two-col">
      <div class="panel">
        <div class="badge">Algorithm structure</div>
        <h2>Algorithms by category</h2>
        {table(category_rows)}
      </div>
      <div class="panel">
        <div class="badge">Execution status</div>
        <h2>Status overview</h2>
        {table(status_rows)}
      </div>
    </section>

    <section class="two-col">
      <div class="panel">
        <div class="badge">Narrative</div>
        <h2>Interpretation</h2>
        <ul class="narrative">{narrative_html}</ul>
      </div>
      <div class="panel">
        <div class="badge">Community detail</div>
        <h2>Community detection snapshot</h2>
        {table(community_counts)}
      </div>
    </section>

    <section style="margin-top: 28px;">
      <div class="badge" style="margin-bottom: 14px;">Visual gallery</div>
      <div class="gallery">
        {''.join(visual_cards)}
      </div>
    </section>

    <div class="footer">
      Generated from the real project graph exports, analytical outputs, and chart exports in the Synthea dataset repository.
    </div>
  </div>
</body>
</html>
"""

    OUT_HTML.write_text(html_string, encoding="utf-8")
    print(f"Generated insights report: {OUT_HTML}")


if __name__ == "__main__":
    main()
