from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
OUT_HTML = REPORTS_DIR / "knowledge_graph_upload_dashboard.html"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def to_js_obj(df: pd.DataFrame):
    return df.where(pd.notna(df), None).to_dict(orient="records")


def build_default_graph():
    nodes = read_csv(DATA_DIR / "nodes.csv")
    rels = read_csv(DATA_DIR / "relationships.csv")

    node_id_col = "element_id" if "element_id" in nodes.columns else "Id" if "Id" in nodes.columns else "id"
    edge_src = "source_element_id" if "source_element_id" in rels.columns else "source" if "source" in rels.columns else "source_id"
    edge_dst = "target_element_id" if "target_element_id" in rels.columns else "target" if "target" in rels.columns else "target_id"
    edge_type = "type" if "type" in rels.columns else "relationship"

    if nodes.empty:
        return {"nodes": [], "edges": []}

    node_records = []
    for _, row in nodes.head(2000).iterrows():
        node_id = row.get(node_id_col, "")
        if pd.isna(node_id):
            continue
        label = row.get("labels") or row.get("label") or "Unknown"
        name = row.get("name") or row.get("NAME") or str(node_id)
        node_records.append({
            "id": str(node_id),
            "label": str(label),
            "name": str(name),
            "group": str(label),
        })

    edge_records = []
    for _, row in rels.head(3000).iterrows():
        src = row.get(edge_src)
        dst = row.get(edge_dst)
        relationship = row.get(edge_type) or "RELATED_TO"
        if pd.isna(src) or pd.isna(dst):
            continue
        edge_records.append({
            "source": str(src),
            "target": str(dst),
            "type": str(relationship),
            "weight": 1.0,
        })

    return {"nodes": node_records, "edges": edge_records}


def compute_summary(graph):
    nodes = graph["nodes"]
    edges = graph["edges"]
    labels = [n.get("label", "Unknown") for n in nodes]
    relationship_types = [e.get("type", "RELATED_TO") for e in edges]
    unique_labels = sorted(set(labels))
    unique_relationship_types = sorted(set(relationship_types))
    summary = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "unique_labels": len(unique_labels),
        "unique_relationship_types": len(unique_relationship_types),
        "top_labels": sorted({label: labels.count(label) for label in unique_labels}.items(), key=lambda kv: kv[1], reverse=True)[:8],
        "top_rel_types": sorted({rel: relationship_types.count(rel) for rel in unique_relationship_types}.items(), key=lambda kv: kv[1], reverse=True)[:8],
    }
    return summary


def build_html():
    default_graph = build_default_graph()
    summary = compute_summary(default_graph)
    default_json = json.dumps(default_graph, ensure_ascii=False)

    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Synthea Knowledge Graph Studio</title>
  <style>
    :root {{
      --bg: #070b12;
      --bg-2: #111827;
      --panel: rgba(17, 24, 39, 0.9);
      --panel-strong: rgba(20, 27, 39, 0.96);
      --silver: #dfe7f1;
      --silver-soft: #b5c2d1;
      --gold: #f4c96a;
      --gold-strong: #d59b2d;
      --teal: #7bd8cb;
      --line: rgba(255,255,255,0.08);
      --text: #edf4ff;
      --muted: #a7b3c6;
      --danger: #ff8d6b;
      --shadow: 0 20px 45px rgba(0,0,0,0.45);
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0;
      font-family: Inter, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(244,201,106,0.15), transparent 20%),
        radial-gradient(circle at top right, rgba(186,196,255,0.15), transparent 18%),
        linear-gradient(180deg, #060910 0%, #111827 100%);
    }}
    .app {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 24px 18px 42px;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 18px 22px;
      border: 1px solid var(--line);
      background: rgba(18, 24, 39, 0.8);
      backdrop-filter: blur(10px);
      box-shadow: var(--shadow);
      border-radius: 18px;
      margin-bottom: 18px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 14px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--silver);
    }}
    .brand-mark {{
      width: 38px;
      height: 38px;
      display: grid;
      place-items: center;
      border-radius: 12px;
      background: linear-gradient(135deg, var(--gold) 0%, #f5d88f 25%, #d5d9e0 60%, #8a8f9c 100%);
      color: #1c1b1a;
      font-size: 1.3rem;
      box-shadow: 0 10px 22px rgba(244, 201, 106, 0.35);
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }}
    .button, .file-label {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 16px;
      border-radius: 12px;
      border: 1px solid rgba(244,201,106,0.5);
      background: linear-gradient(135deg, rgba(244,201,106,0.18), rgba(255,255,255,0.03));
      color: var(--text);
      cursor: pointer;
      font-weight: 600;
      text-decoration: none;
      transition: 0.2s ease;
    }}
    .button:hover, .file-label:hover {{ transform: translateY(-1px); box-shadow: 0 10px 20px rgba(244,201,106,0.18); }}
    input[type=\"file\"] {{ display: none; }}
    .hero {{
      display: grid;
      grid-template-columns: 1.7fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
      padding: 18px 18px 16px;
    }}
    .hero-copy {{
      background:
        linear-gradient(135deg, rgba(244,201,106,0.08), rgba(255,255,255,0.03)),
        rgba(10,14,20,0.85);
      border: 1px solid rgba(244,201,106,0.2);
      overflow: hidden;
      min-height: 230px;
    }}
    .eyebrow {{
      color: var(--gold);
      letter-spacing: 0.17em;
      text-transform: uppercase;
      font-size: 0.7rem;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2.1rem, 3vw, 3.3rem);
      line-height: 1.08;
      letter-spacing: -0.04em;
    }}
    .hero-copy p {{
      margin-top: 14px;
      max-width: 700px;
      font-size: 1.03rem;
      line-height: 1.7;
      color: var(--muted);
    }}
    .glow-card {{
      position: relative;
      min-height: 230px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      background: radial-gradient(circle at 15% 30%, rgba(244,201,106,0.26), transparent 18%), linear-gradient(135deg, rgba(255,255,255,0.04), rgba(10,14,20,0.7));
    }}
    .mini-stat-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(120px, 1fr));
      gap: 12px;
      margin-top: 10px;
    }}
    .mini-stat {{
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 10px;
    }}
    .mini-stat .label {{
      color: var(--muted);
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .mini-stat .value {{
      font-size: 1.45rem;
      font-weight: 700;
      margin-top: 8px;
      color: var(--silver);
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .stat-card {{
      background: rgba(17,24,39,0.9);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 14px;
      box-shadow: var(--shadow);
    }}
    .stat-card .label {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.7rem;
    }}
    .stat-card .value {{
      margin-top: 10px;
      font-size: 2rem;
      font-weight: 800;
      color: var(--silver);
    }}
    .content {{
      display: grid;
      grid-template-columns: 1.3fr 0.7fr;
      gap: 18px;
      margin-top: 18px;
    }}
    .graph-shell {{
      position: relative;
      min-height: 560px;
      background: linear-gradient(180deg, rgba(8,14,20,0.9), rgba(17,24,39,0.88));
      border-radius: 20px;
      overflow: hidden;
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}
    .graph-shell .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 18px 0;
      color: var(--silver);
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    #graphCanvas {{
      width: 100%;
      height: 500px;
      display: block;
      background: radial-gradient(circle at center, rgba(188,195,215,0.05), transparent 55%);
      cursor: grab;
      touch-action: none;
      user-select: none;
      border-radius: 14px;
    }}
    #graphCanvas:active {{
      cursor: grabbing;
    }}
    #graphTooltip {{
      position: fixed;
      z-index: 30;
      pointer-events: none;
      background: rgba(12,18,26,0.96);
      color: var(--text);
      border: 1px solid rgba(244,201,106,0.5);
      border-radius: 10px;
      padding: 8px 10px;
      font-size: 0.74rem;
      line-height: 1.45;
      box-shadow: 0 14px 30px rgba(0,0,0,0.4);
      opacity: 0;
      transform: translate(12px, 12px);
      transition: opacity 0.12s ease;
      white-space: nowrap;
      max-width: 260px;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .side-stack {{
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}
    .list {{
      margin: 0;
      padding: 0;
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .list li {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      color: var(--silver);
    }}
    .tag {{
      display: inline-block;
      padding: 5px 8px;
      border-radius: 999px;
      background: rgba(244,201,106,0.15);
      border: 1px solid rgba(244,201,106,0.3);
      color: var(--gold);
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .kpi {{
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
    }}
    .kpi .value {{
      font-size: 1.4rem;
      font-weight: 800;
      color: var(--gold);
    }}
    .kpi .label {{
      font-size: 0.72rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-top: 6px;
    }}
    .muted {{ color: var(--muted); }}
    .footer {{
      margin-top: 20px;
      color: var(--muted);
      font-size: 0.9rem;
      text-align: center;
    }}
    @media (max-width: 980px) {{
      .hero, .content {{ grid-template-columns: 1fr; }}
      .topbar {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <div class=\"app\">
    <div class=\"topbar\">
      <div class=\"brand\">
        <div class=\"brand-mark\">G</div>
        Synthea Knowledge Graph Studio
      </div>
      <div class=\"controls\">
        <label class=\"file-label\" for=\"csvUpload\">Upload CSV</label>
        <input id=\"csvUpload\" type=\"file\" accept=\".csv,text/csv\" />
        <button class=\"button\" id=\"loadSample\" type=\"button\">Load default Synthea graph</button>
      </div>
    </div>

    <section class=\"hero\">
      <div class=\"panel hero-copy\">
        <div class=\"eyebrow\">Healthcare intelligence</div>
        <h1>Graph-driven analytics for clinical structure, influence, and similarity.</h1>
        <p>
          Upload a CSV file or load the bundled Synthea graph to inspect node relationships, centrality-like influence, cluster structure, and entity similarity. The interface blends black-silver visuals with golden information emphasis to resemble a premium knowledge graph dashboard.
        </p>
      </div>
      <div class=\"panel glow-card\">
        <div class=\"tag\">Live signal</div>
        <div class=\"mini-stat-grid\">
          <div class=\"mini-stat\"><div class=\"label\">Nodes</div><div class=\"value\" id=\"miniNodes\">{summary['node_count']}</div></div>
          <div class=\"mini-stat\"><div class=\"label\">Edges</div><div class=\"value\" id=\"miniEdges\">{summary['edge_count']}</div></div>
          <div class=\"mini-stat\"><div class=\"label\">Labels</div><div class=\"value\" id=\"miniLabels\">{summary['unique_labels']}</div></div>
          <div class=\"mini-stat\"><div class=\"label\">Relations</div><div class=\"value\" id=\"miniRelations\">{summary['unique_relationship_types']}</div></div>
        </div>
      </div>
    </section>

    <section class=\"stats\">
      <div class=\"stat-card\"><div class=\"label\">Node count</div><div class=\"value\" id=\"nodeCount\">{summary['node_count']}</div></div>
      <div class=\"stat-card\"><div class=\"label\">Relationship count</div><div class=\"value\" id=\"edgeCount\">{summary['edge_count']}</div></div>
      <div class=\"stat-card\"><div class=\"label\">Median degree</div><div class=\"value\" id=\"medianDegree\">0</div></div>
      <div class=\"stat-card\"><div class=\"label\">Top cluster</div><div class=\"value\" id=\"topCluster\">0</div></div>
      <div class=\"stat-card\"><div class=\"label\">Similarity index</div><div class=\"value\" id=\"similarityIndex\">0.00</div></div>
    </section>

    <section class=\"content\">
      <div class=\"graph-shell\">
        <div class=\"header\"><span>Knowledge graph</span><span class=\"muted\" id=\"graphStatus\">Connected</span></div>
        <svg id=\"graphCanvas\" viewBox=\"0 0 960 500\" preserveAspectRatio=\"xMidYMid meet\"></svg>
      </div>

      <div class=\"side-stack\">
        <div class=\"panel\">
          <div class=\"tag\">Entity leaders</div>
          <ul class=\"list\" id=\"leaderList\"></ul>
        </div>
        <div class=\"panel\">
          <div class=\"tag\">Cluster signal</div>
          <ul class=\"list\" id=\"clusterList\"></ul>
        </div>
        <div class=\"panel\">
          <div class=\"tag\">Similarity snapshot</div>
          <ul class=\"list\" id=\"similarityList\"></ul>
        </div>
      </div>
    </section>

    <section class=\"content\" style=\"margin-top: 18px;\">
      <div class=\"panel\">
        <div class=\"tag\">Label distribution</div>
        <div class=\"kpis\" id=\"labelKpis\"></div>
      </div>
      <div class=\"panel\">
        <div class=\"tag\">Relationship mix</div>
        <div class=\"kpis\" id=\"relationKpis\"></div>
      </div>
    </section>

    <div class=\"footer\">Generated from the local Synthea graph exports or from a user-uploaded CSV dataset.</div>
  </div>

  <script>
    const defaultGraph = __DEFAULT_JSON__;

    const state = {{
      nodes: [],
      edges: [],
      hover: null,
      width: 960,
      height: 500,
      scale: 1,
      panX: 0,
      panY: 0,
      panning: false,
      panStartX: 0,
      panStartY: 0,
      lastPointerX: 0,
      lastPointerY: 0
    }};

    function setTooltip(event, htmlText) {{
      const tooltip = document.getElementById('graphTooltip');
      if (!tooltip) return;
      tooltip.innerHTML = htmlText;
      tooltip.style.opacity = '1';
      tooltip.style.left = (event.clientX + 18) + 'px';
      tooltip.style.top = (event.clientY + 18) + 'px';
    }}

    function hideTooltip() {{
      const tooltip = document.getElementById('graphTooltip');
      if (!tooltip) return;
      tooltip.style.opacity = '0';
    }}

    function applyViewportTransform() {{
      const svg = document.getElementById('graphCanvas');
      if (!svg) return;
      const viewport = svg.querySelector('#graphViewport');
      if (!viewport) return;
      viewport.setAttribute('transform', 'translate(' + state.panX + ', ' + state.panY + ') scale(' + state.scale + ')');
    }}

    function getSvgCoordinates(event) {{
      const svg = document.getElementById('graphCanvas');
      if (!svg) return {{ x: 0, y: 0 }};
      const rect = svg.getBoundingClientRect();
      const px = ((event.clientX - rect.left) / rect.width) * state.width;
      const py = ((event.clientY - rect.top) / rect.height) * state.height;
      return {{ x: px, y: py }};
    }}

    function setupCanvasInteractions() {{
      const svg = document.getElementById('graphCanvas');
      if (!svg || svg.dataset.interactionsBound === 'true') return;
      svg.dataset.interactionsBound = 'true';

      svg.addEventListener('wheel', function(event) {{
        event.preventDefault();
        const point = getSvgCoordinates(event);
        const prevScale = state.scale;
        const delta = event.deltaY < 0 ? 1.14 : 0.88;
        const nextScale = Math.min(2.8, Math.max(0.45, prevScale * delta));
        const worldX = (point.x - state.panX) / prevScale;
        const worldY = (point.y - state.panY) / prevScale;
        state.scale = nextScale;
        state.panX = point.x - worldX * nextScale;
        state.panY = point.y - worldY * nextScale;
        applyViewportTransform();
      }}, {{ passive: false }});

      svg.addEventListener('pointerdown', function(event) {{
        if (event.target.closest('[data-node-id]')) return;
        state.panning = true;
        state.panStartX = event.clientX;
        state.panStartY = event.clientY;
        state.lastPointerX = state.panX;
        state.lastPointerY = state.panY;
        svg.setPointerCapture(event.pointerId);
      }});

      svg.addEventListener('pointermove', function(event) {{
        if (!state.panning) return;
        const dx = event.clientX - state.panStartX;
        const dy = event.clientY - state.panStartY;
        state.panX = state.lastPointerX + (dx / state.scale);
        state.panY = state.lastPointerY + (dy / state.scale);
        applyViewportTransform();
      }});

      svg.addEventListener('pointerup', function() {{
        state.panning = false;
      }});
      svg.addEventListener('pointerleave', function() {{
        state.panning = false;
      }});
    }}

    function parseCSV(text) {{
      const rows = [];
      let row = [];
      let value = '';
      let inQuotes = false;

      for (let i = 0; i < text.length; i += 1) {{
        const ch = text[i];
        const isNewline = ch === String.fromCharCode(10) || ch === String.fromCharCode(13);
        if (ch === '"') {{
          if (inQuotes && text[i + 1] === '"') {{
            value += '"';
            i += 1;
          }} else {{
            inQuotes = !inQuotes;
          }}
        }} else if (ch === ',' && !inQuotes) {{
          row.push(value);
          value = '';
        }} else if (isNewline && !inQuotes) {{
          if (ch === String.fromCharCode(13) && text[i + 1] === String.fromCharCode(10)) i += 1;
          row.push(value);
          if (row.some(function(cell) {{ return cell !== ''; }})) {{
            rows.push(row);
          }}
          row = [];
          value = '';
        }} else {{
          value += ch;
        }}
      }}

      if (value.length || row.length) {{
        row.push(value);
        if (row.some(function(cell) {{ return cell !== ''; }})) {{
          rows.push(row);
        }}
      }}

      if (!rows.length) return [];

      const headers = rows[0].map(function(h) {{ return h.trim(); }});
      return rows.slice(1).filter(function(rowItem) {{ return rowItem.length >= headers.length; }}).map(function(rowItem) {{
        const obj = {{}};
        headers.forEach(function(header, idx) {{
          obj[header] = rowItem[idx] !== undefined ? rowItem[idx].trim() : '';
        }});
        return obj;
      }});
    }}

    function mergeGraphs(graphA, graphB) {{
      const mergedNodes = new Map();
      const mergedEdges = [];

      function addNode(node) {{
        if (!node || !node.id) return;
        const rawId = String(node.id);
        if (!mergedNodes.has(rawId)) {{
          mergedNodes.set(rawId, {{
            id: rawId,
            label: String(node.label ?? node.labels ?? 'Unknown'),
            name: String(node.name ?? node.NAME ?? rawId),
            group: String(node.group ?? node.label ?? node.labels ?? 'Unknown')
          }});
        }}
      }

      for (const node of (graphA && graphA.nodes) || []) addNode(node);
      for (const node of (graphB && graphB.nodes) || []) addNode(node);

      for (const edge of (graphA && graphA.edges) || []) mergedEdges.push(edge);
      for (const edge of (graphB && graphB.edges) || []) mergedEdges.push(edge);

      const edgeSeen = new Set();
      const uniqueEdges = [];
      for (const edge of mergedEdges) {{
        const key = [String(edge.source || ''), String(edge.target || ''), String(edge.type || 'RELATED_TO')].join('::');
        if (!edgeSeen.has(key)) {{
          edgeSeen.add(key);
          uniqueEdges.push(edge);
        }}
      }}

      for (const edge of uniqueEdges) {{
        if (edge && edge.source) addNode({{ id: edge.source, label: 'Inferred', name: edge.source, group: 'Inferred' }});
        if (edge && edge.target) addNode({{ id: edge.target, label: 'Inferred', name: edge.target, group: 'Inferred' }});
      }}

      return {{ nodes: Array.from(mergedNodes.values()), edges: uniqueEdges }};
    }}

    function normalizeGraph(rawNodes, rawEdges) {{
      const nodeMap = new Map();
      const seenNodes = new Set();
      const nodeRows = rawNodes || [];
      const edgeRows = rawEdges || [];

      function addNode(node) {{
        if (!node || !node.id) return;
        const id = String(node.id);
        const label = String(node.label ?? node.labels ?? node.type ?? 'Unknown');
        const name = String(node.name ?? node.NAME ?? node.label ?? id);
        if (!seenNodes.has(id)) {{
          nodeMap.set(id, {{ id: id, label: label, name: name, group: label }});
          seenNodes.add(id);
        }}
      }

      for (const node of nodeRows) addNode(node);
      for (const edge of edgeRows) {{
        if (edge && edge.source) addNode({{ id: edge.source, label: 'Inferred', name: edge.source, group: 'Inferred' }});
        if (edge && edge.target) addNode({{ id: edge.target, label: 'Inferred', name: edge.target, group: 'Inferred' }});
      }}

      const edges = [];
      for (const edge of edgeRows) {{
        const source = String(edge.source ?? edge.source_element_id ?? edge.from ?? edge.src ?? '');
        const target = String(edge.target ?? edge.target_element_id ?? edge.to ?? edge.dst ?? '');
        const type = String(edge.type ?? edge.relationship ?? edge.label ?? 'RELATED_TO');
        const weight = Number(edge.weight ?? edge.score ?? edge.strength ?? 1);
        if (!source || !target) continue;
        const normalized = {{ source: source, target: target, type: type, weight: Number.isFinite(weight) ? weight : 1 }};
        edges.push(normalized);
      }}

      const nodes = Array.from(nodeMap.values());
      return {{ nodes: nodes, edges: edges }};
    }}

    function inflateGraphFromCsvText(text) {{
      const rows = parseCSV(text);
      if (!rows.length) return {{ nodes: [], edges: [] }};

      const hasEdges = rows.some(function(row) {{ return 'source' in row || 'source_element_id' in row || 'target' in row || 'target_element_id' in row || 'from' in row || 'to' in row; }});
      const hasNodes = rows.some(function(row) {{ return 'element_id' in row || 'id' in row || 'labels' in row || 'label' in row || 'name' in row; }});

      if (!hasNodes && !hasEdges) return {{ nodes: [], edges: [] }};

      const nodeList = [];
      const edgeList = [];

      rows.forEach(function(row) {{
        const isNodeRow = ('element_id' in row || 'id' in row || 'labels' in row || 'label' in row || 'name' in row) && !('source_element_id' in row || 'source' in row || 'target' in row || 'target_element_id' in row || 'from' in row || 'to' in row);
        const isEdgeRow = 'source_element_id' in row || 'source' in row || 'target' in row || 'target_element_id' in row || 'from' in row || 'to' in row;

        if (isNodeRow) {{
          nodeList.push({{ id: row.element_id ?? row.id ?? row.name, label: row.labels ?? row.label ?? 'Unknown', name: row.name ?? row.NAME ?? row.label ?? row.element_id ?? row.id }});
        }}
        if (isEdgeRow) {{
          edgeList.push({{ source: row.source_element_id ?? row.source ?? row.from ?? row.src, target: row.target_element_id ?? row.target ?? row.to ?? row.dst, type: row.type ?? row.relationship ?? row.label ?? 'RELATED_TO', weight: Number(row.weight ?? row.score ?? row.strength ?? 1) }});
        }}
      }});

      return normalizeGraph(nodeList, edgeList);
    }}

    function buildDegreeMap(nodes, edges) {{
      const degree = new Map();
      for (const node of nodes) degree.set(node.id, 0);
      for (const edge of edges) {{
        if (!degree.has(edge.source)) degree.set(edge.source, 0);
        if (!degree.has(edge.target)) degree.set(edge.target, 0);
        degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
        degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
      }}
      return degree;
    }}

    function computeCentrality(nodes, edges) {{
      const degree = buildDegreeMap(nodes, edges);
      const scoreMap = new Map();
      for (const node of nodes) scoreMap.set(node.id, 1 + (degree.get(node.id) || 0) * 0.2);
      return Array.from(scoreMap.entries()).map(function(entry) {{ return {{ id: entry[0], score: entry[1] }}; }}).sort(function(a, b) {{ return b.score - a.score; }}).slice(0, 10);
    }}

    function computeClusterSummary(nodes, edges) {{
      const visited = new Set();
      const groups = [];
      const adjacency = new Map();
      for (const node of nodes) adjacency.set(node.id, []);
      for (const edge of edges) {{
        if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
        if (!adjacency.has(edge.target)) adjacency.set(edge.target, []);
        adjacency.get(edge.source).push(edge.target);
        adjacency.get(edge.target).push(edge.source);
      }}

      for (const node of nodes) {{
        if (visited.has(node.id)) continue;
        const queue = [node.id];
        const group = [];
        visited.add(node.id);
        while (queue.length) {{
          const current = queue.shift();
          group.push(current);
          for (const neighbor of adjacency.get(current) || []) {{
            if (!visited.has(neighbor)) {{
              visited.add(neighbor);
              queue.push(neighbor);
            }}
          }}
        }}
        groups.push(group);
      }}
      return groups.sort(function(a, b) {{ return b.length - a.length; }}).slice(0, 5).map(function(group, idx) {{ return {{ index: idx + 1, size: group.length, label: 'Cluster ' + (idx + 1) }}; }});
    }}

    function computeSimilarity(nodes, edges) {{
      const neighbors = new Map();
      for (const node of nodes) neighbors.set(node.id, new Set());
      for (const edge of edges) {{
        if (neighbors.has(edge.source)) neighbors.get(edge.source).add(edge.target);
        if (neighbors.has(edge.target)) neighbors.get(edge.target).add(edge.source);
      }}
      const sims = [];
      const ids = nodes.map(function(node) {{ return node.id; }});
      for (let i = 0; i < ids.length; i += 1) {{
        for (let j = i + 1; j < ids.length; j += 1) {{
          const a = ids[i];
          const b = ids[j];
          const union = new Set([...(neighbors.get(a) || new Set()), ...(neighbors.get(b) || new Set())]);
          const inter = [...(neighbors.get(a) || new Set())].filter(function(value) {{ return (neighbors.get(b) || new Set()).has(value); }});
          const score = union.size ? inter.length / union.size : 0;
          if (score > 0.1) sims.push({{ a: a, b: b, score: score }});
        }}
      }}
      sims.sort(function(a, b) {{ return b.score - a.score; }});
      return sims.slice(0, 5);
    }}

    function updateStats(graph) {{
      const nodes = graph.nodes;
      const edges = graph.edges;
      const degreeMap = buildDegreeMap(nodes, edges);
      const degrees = Array.from(degreeMap.values());
      const median = degrees.length ? degrees.slice().sort(function(a, b) {{ return a - b; }})[Math.floor(degrees.length / 2)] : 0;
      const leaders = computeCentrality(nodes, edges).slice(0, 5);
      const clusters = computeClusterSummary(nodes, edges).slice(0, 3);
      const similarity = computeSimilarity(nodes, edges).slice(0, 3);
      const labelCounts = {{}};
      for (const node of nodes) {{ labelCounts[node.label] = (labelCounts[node.label] || 0) + 1; }}
      const relationshipCounts = {{}};
      for (const edge of edges) {{ relationshipCounts[edge.type] = (relationshipCounts[edge.type] || 0) + 1; }}

      document.getElementById('nodeCount').textContent = nodes.length;
      document.getElementById('edgeCount').textContent = edges.length;
      document.getElementById('medianDegree').textContent = median;
      document.getElementById('topCluster').textContent = clusters[0] ? clusters[0].size : 0;
      document.getElementById('similarityIndex').textContent = (similarity[0] ? similarity[0].score : 0).toFixed(2);
      document.getElementById('miniNodes').textContent = nodes.length;
      document.getElementById('miniEdges').textContent = edges.length;
      document.getElementById('miniLabels').textContent = new Set(nodes.map(function(node) {{ return node.label; }})).size;
      document.getElementById('miniRelations').textContent = new Set(edges.map(function(edge) {{ return edge.type; }})).size;

      const leaderList = document.getElementById('leaderList');
      leaderList.innerHTML = leaders.map(function(entry, idx) {{
        const node = nodes.find(function(item) {{ return item.id === entry.id; }});
        return '<li><span>' + (idx + 1) + '. ' + (node ? node.name : entry.id) + '</span><strong>' + entry.score.toFixed(2) + '</strong></li>';
      }}).join('');

      const clusterList = document.getElementById('clusterList');
      clusterList.innerHTML = clusters.map(function(cluster) {{ return '<li><span>' + cluster.label + '</span><strong>' + cluster.size + '</strong></li>'; }}).join('');

      const similarityList = document.getElementById('similarityList');
      similarityList.innerHTML = similarity.map(function(pair) {{ return '<li><span>' + pair.a.slice(0, 18) + ' / ' + pair.b.slice(0, 18) + '</span><strong>' + pair.score.toFixed(2) + '</strong></li>'; }}).join('') || '<li><span>No strong similarity pairs</span><strong>0</strong></li>';

      const labelKpis = document.getElementById('labelKpis');
      const labelEntries = Object.entries(labelCounts).sort(function(a, b) {{ return b[1] - a[1]; }}).slice(0, 6);
      labelKpis.innerHTML = labelEntries.map(function(entry) {{ return '<div class="kpi"><div class="value">' + entry[1] + '</div><div class="label">' + entry[0] + '</div></div>'; }}).join('');

      const relationKpis = document.getElementById('relationKpis');
      const relationEntries = Object.entries(relationshipCounts).sort(function(a, b) {{ return b[1] - a[1]; }}).slice(0, 6);
      relationKpis.innerHTML = relationEntries.map(function(entry) {{ return '<div class="kpi"><div class="value">' + entry[1] + '</div><div class="label">' + entry[0] + '</div></div>'; }}).join('');
    }}

    function computeDisplayGraph(graph) {{
      const baseNodes = graph.nodes || [];
      const baseEdges = graph.edges || [];
      const degreeMap = buildDegreeMap(baseNodes, baseEdges);
      const nodeIds = new Set(baseNodes.map(function(node) {{ return String(node.id); }}));

      if (baseNodes.length <= 140) {{
        return {{ nodes: baseNodes, edges: baseEdges }};
      }}

      const ranked = baseNodes
        .map(function(node) {{
          return {{ node: node, degree: degreeMap.get(String(node.id)) || 0 }};
        }})
        .sort(function(a, b) {{ return b.degree - a.degree; }})
        .slice(0, 140);

      const keep = new Set(ranked.map(function(item) {{ return String(item.node.id); }}));
      for (const edge of baseEdges) {{
        if (keep.has(String(edge.source)) || keep.has(String(edge.target))) {{
          keep.add(String(edge.source));
          keep.add(String(edge.target));
        }}
      }}

      const filteredNodes = baseNodes.filter(function(node) {{ return keep.has(String(node.id)); }});
      const filteredEdges = baseEdges.filter(function(edge) {{
        return keep.has(String(edge.source)) && keep.has(String(edge.target));
      }});

      return {{ nodes: filteredNodes, edges: filteredEdges }};
    }}

    function computeLayout(nodes, edges) {{
      const width = state.width;
      const height = state.height;
      const pos = new Map();
      const centerX = width / 2;
      const centerY = height / 2;

      if (!nodes.length) return pos;

      const maxRadius = Math.min(Math.max(120, nodes.length * 8), 260);
      nodes.forEach(function(node, idx) {{
        const angle = (2 * Math.PI * idx) / Math.max(1, nodes.length);
        const radius = maxRadius + (idx % 5) * 16;
        pos.set(node.id, {{
          x: centerX + Math.cos(angle) * radius,
          y: centerY + Math.sin(angle) * radius * 0.82
        }});
      }});

      const iterations = Math.min(110, Math.max(45, nodes.length * 2));
      for (let iter = 0; iter < iterations; iter += 1) {{
        const forces = new Map();
        nodes.forEach(function(node) {{ forces.set(node.id, {{ x: 0, y: 0 }}); }});

        for (let i = 0; i < nodes.length; i += 1) {{
          for (let j = i + 1; j < nodes.length; j += 1) {{
            const a = nodes[i];
            const b = nodes[j];
            const pa = pos.get(a.id);
            const pb = pos.get(b.id);
            if (!pa || !pb) continue;

            const dx = pb.x - pa.x;
            const dy = pb.y - pa.y;
            const distSq = dx * dx + dy * dy + 0.0001;
            const dist = Math.sqrt(distSq);
            const repel = 12000 / distSq;
            const fx = (dx / dist) * repel;
            const fy = (dy / dist) * repel;

            forces.get(a.id).x -= fx;
            forces.get(a.id).y -= fy;
            forces.get(b.id).x += fx;
            forces.get(b.id).y += fy;
          }}
        }}

        edges.forEach(function(edge) {{
          const source = pos.get(edge.source);
          const target = pos.get(edge.target);
          if (!source || !target) return;

          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const targetDist = 150;
          const spring = (dist - targetDist) * 0.12;
          const fx = (dx / dist) * spring;
          const fy = (dy / dist) * spring;

          forces.get(edge.source).x += fx;
          forces.get(edge.source).y += fy;
          forces.get(edge.target).x -= fx;
          forces.get(edge.target).y -= fy;
        }});

        nodes.forEach(function(node) {{
          const force = forces.get(node.id);
          const point = pos.get(node.id);
          if (!force || !point) return;

          const len = Math.hypot(force.x, force.y) || 1;
          const maxStep = 12;
          const scale = Math.min(len, maxStep) / len;
          point.x += force.x * scale * 0.18;
          point.y += force.y * scale * 0.18;

          const margin = 40;
          point.x = Math.min(width - margin, Math.max(margin, point.x));
          point.y = Math.min(height - margin, Math.max(margin, point.y));
        }});
      }

      return pos;
    }}

    function drawGraph(graph) {{
      const svg = document.getElementById('graphCanvas');
      const width = state.width;
      const height = state.height;
      svg.innerHTML = '';

      const display = computeDisplayGraph(graph);
      const nodes = display.nodes;
      const edges = display.edges;
      const pos = computeLayout(nodes, edges);
      const typeColors = {{
        'RELATED_TO': '#dfe7f1',
        'LIVES_IN': '#f4c96a',
        'IN_COUNTY': '#7bd8cb',
        'IN_STATE': '#d59b2d',
        'HAS': '#a6d8ff',
        'PART_OF': '#caa7ff'
      }};

      const degrees = buildDegreeMap(nodes, edges);
      const maxDegree = Math.max(1, ...Array.from(degrees.values()));

      const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      background.setAttribute('x', '0');
      background.setAttribute('y', '0');
      background.setAttribute('width', String(width));
      background.setAttribute('height', String(height));
      background.setAttribute('fill', 'rgba(5, 10, 18, 0.6)');
      svg.appendChild(background);

      const viewport = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      viewport.setAttribute('id', 'graphViewport');
      svg.appendChild(viewport);

      const edgeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      viewport.appendChild(edgeLayer);

      edges.forEach(function(edge) {{
        const source = pos.get(edge.source);
        const target = pos.get(edge.target);
        if (!source || !target) return;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', source.x);
        line.setAttribute('y1', source.y);
        line.setAttribute('x2', target.x);
        line.setAttribute('y2', target.y);
        line.setAttribute('stroke', typeColors[edge.type] || '#dfe7f1');
        line.setAttribute('stroke-opacity', '0.46');
        line.setAttribute('stroke-width', String(Math.max(1, (edge.weight || 1) * 1.2)));
        line.style.cursor = 'pointer';
        line.addEventListener('pointermove', function(event) {{
          const midX = (source.x + target.x) / 2;
          const midY = (source.y + target.y) / 2;
          setTooltip(event, '<strong>' + String(edge.type || 'RELATED_TO') + '</strong><br>' + String(edge.source) + ' → ' + String(edge.target));
          line.setAttribute('stroke-opacity', '0.9');
          line.setAttribute('stroke-width', String(Math.max(2, (edge.weight || 1) * 1.8)));
        }});
        line.addEventListener('pointerleave', function() {{
          hideTooltip();
          line.setAttribute('stroke-opacity', '0.46');
          line.setAttribute('stroke-width', String(Math.max(1, (edge.weight || 1) * 1.2)));
        }});
        edgeLayer.appendChild(line);
      }});

      const nodeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      viewport.appendChild(nodeLayer);

      nodes.forEach(function(node) {{
        const point = pos.get(node.id);
        if (!point) return;
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('data-node-id', String(node.id));
        group.style.cursor = 'pointer';

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        const degreeSize = 9 + ((degrees.get(node.id) || 0) / maxDegree) * 18;
        const label = String(node.label ?? node.labels ?? 'Unknown');
        const fill = label.includes('Organization') ? '#f4c96a' : label.includes('Patient') ? '#dfe7f1' : label.includes('City') || label.includes('State') || label.includes('County') ? '#7bd8cb' : '#a6d8ff';

        circle.setAttribute('cx', point.x);
        circle.setAttribute('cy', point.y);
        circle.setAttribute('r', String(Math.max(7, degreeSize)));
        circle.setAttribute('fill', fill);
        circle.setAttribute('stroke', 'rgba(255,255,255,0.8)');
        circle.setAttribute('stroke-width', '1.1');
        group.appendChild(circle);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        const name = String(node.name || node.id || 'Unnamed');
        text.setAttribute('x', point.x + 14);
        text.setAttribute('y', point.y - 8);
        text.setAttribute('fill', '#edf4ff');
        text.setAttribute('font-size', '10.5');
        text.style.fontWeight = '600';
        text.textContent = name.slice(0, 18);
        group.appendChild(text);

        const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        title.textContent = name + ' (' + label + ')';
        group.appendChild(title);

        group.addEventListener('pointerenter', function(event) {{
          circle.setAttribute('stroke', '#f4c96a');
          circle.setAttribute('stroke-width', '2.3');
          setTooltip(event, '<strong>' + name + '</strong><br><span style="color:#a7b3c6;">' + label + '</span>');
        }});
        group.addEventListener('pointermove', function(event) {{
          setTooltip(event, '<strong>' + name + '</strong><br><span style="color:#a7b3c6;">' + label + '</span>');
        }});
        group.addEventListener('pointerleave', function() {{
          circle.setAttribute('stroke', 'rgba(255,255,255,0.8)');
          circle.setAttribute('stroke-width', '1.1');
          hideTooltip();
        }});

        nodeLayer.appendChild(group);
      }});

      applyViewportTransform();
      setupCanvasInteractions();
    }}

    function renderGraph(graph) {{
      state.nodes = graph.nodes;
      state.edges = graph.edges;
      updateStats(graph);
      drawGraph(graph);
    }}

    function useAdhocGraph(graph) {{
      const cleaned = normalizeGraph(graph.nodes || [], graph.edges || []);
      if (!cleaned.nodes.length) {{
        document.getElementById('graphStatus').textContent = 'No valid graph';
        return;
      }}
      document.getElementById('graphStatus').textContent = 'Connected';
      renderGraph(cleaned);
    }}

    function handleFileUpload(event) {{
      const files = Array.from(event.target.files || []);
      if (!files.length) return;

      Promise.all(files.map(function(file) {{
        return new Promise(function(resolve, reject) {{
          const reader = new FileReader();
          reader.onload = function() {{
            try {{
              const text = String(reader.result || '');
              resolve(inflateGraphFromCsvText(text));
            }} catch (error) {{
              reject(error);
            }}
          }};
          reader.onerror = function() {{ reject(reader.error || new Error('File read failed')); }};
          reader.readAsText(file);
        }});
      }})).then(function(graphs) {{
        let merged = {{ nodes: [], edges: [] }};
        for (const graph of graphs) merged = mergeGraphs(merged, graph);
        if (!merged.nodes.length && !merged.edges.length) {{
          document.getElementById('graphStatus').textContent = 'No graph data found';
          return;
        }}
        document.getElementById('graphStatus').textContent = 'Connected';
        useAdhocGraph(merged);
      }}).catch(function(error) {{
        document.getElementById('graphStatus').textContent = 'Parse error';
        console.error(error);
      }});
    }}

    document.getElementById('csvUpload').addEventListener('change', handleFileUpload);
    document.getElementById('loadSample').addEventListener('click', function() {{ useAdhocGraph(defaultGraph); }});
    useAdhocGraph(defaultGraph);
  </script>
</body>
</html>
"""
    html = html.replace("__DEFAULT_JSON__", default_json)
    for key, value in summary.items():
        html = html.replace(f"{{summary['{key}']}}", str(value))
    html = html.replace("{{", "{").replace("}}", "}")
    return html


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(build_html(), encoding="utf-8")
    print(f"Generated knowledge graph upload dashboard: {OUT_HTML}")


if __name__ == "__main__":
    main()
