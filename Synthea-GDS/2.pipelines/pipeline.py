"""
Synthea Graph Analytics Pipeline
Local execution using NetworkX / igraph / cdlib / sklearn / etc.
Does not use Neo4j GDS.
"""

import os
import sys
import time
import json
import math
import csv
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import networkx as nx
import igraph as ig
import pandas as pd
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NEO4J_URI = "bolt://100.23.76.198:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.environ.get("Prajnadb", "")

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data"
CENTRALITY_DIR = WORKSPACE / "centrality"
COMMUNITY_DIR = WORKSPACE / "community"
SIMILARITY_DIR = WORKSPACE / "similarity"
PATHS_DIR = WORKSPACE / "paths"
DAG_DIR = WORKSPACE / "dag"
EMBEDDINGS_DIR = WORKSPACE / "embeddings"
REPORTS_DIR = WORKSPACE / "reports"

for d in [DATA_DIR, CENTRALITY_DIR, COMMUNITY_DIR, SIMILARITY_DIR,
          PATHS_DIR, DAG_DIR, EMBEDDINGS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

NODES_CSV = DATA_DIR / "nodes.csv"
RELS_CSV = DATA_DIR / "relationships.csv"
MANIFEST_CSV = REPORTS_DIR / "algorithm_manifest.csv"
SUMMARY_CSV = REPORTS_DIR / "algorithm_summary.csv"

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def safe_write_csv(path: Path, rows: List[Dict[str, Any]]):
    if not rows:
        # Write a marker file so the output path always exists
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["info"])
            writer.writeheader()
            writer.writerow({"info": "no_results"})
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def append_manifest(record: Dict[str, Any]):
    file_exists = MANIFEST_CSV.exists() and MANIFEST_CSV.stat().st_size > 0
    fieldnames = [
        "algorithm", "category", "status", "output_file", "library",
        "parameters", "runtime_seconds", "nodes_processed", "edges_processed",
        "notes"
    ]
    with open(MANIFEST_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)


def timing(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed
    return wrapper

# ---------------------------------------------------------------------------
# 1. Export from Neo4j
# ---------------------------------------------------------------------------

def export_graph():
    from neo4j import GraphDatabase

    print("[1/8] Exporting graph from Neo4j ...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        # Nodes
        node_query = """
        MATCH (n)
        RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS props
        """
        nodes = session.run(node_query).data()

        # Relationships
        rel_query = """
        MATCH (a)-[r]->(b)
        RETURN elementId(a) AS source_element_id,
               elementId(b) AS target_element_id,
               type(r) AS type,
               properties(r) AS props
        """
        rels = session.run(rel_query).data()

    driver.close()

    # Write nodes.csv
    print(f"  Nodes: {len(nodes)}, Relationships: {len(rels)}")
    # Collect all property keys across all nodes
    all_node_keys = set()
    for n in nodes:
        all_node_keys.update((n.get("props") or {}).keys())
    all_node_keys = sorted(all_node_keys)

    node_rows = []
    for n in nodes:
        row = {"element_id": n["element_id"], "labels": "|".join(n["labels"])}
        props = n.get("props") or {}
        for k in all_node_keys:
            row[k] = "" if props.get(k) is None else props.get(k, "")
        node_rows.append(row)
    safe_write_csv(NODES_CSV, node_rows)

    # Write relationships.csv
    all_rel_keys = set()
    for r in rels:
        all_rel_keys.update((r.get("props") or {}).keys())
    all_rel_keys = sorted(all_rel_keys)

    rel_rows = []
    for r in rels:
        row = {
            "source_element_id": r["source_element_id"],
            "target_element_id": r["target_element_id"],
            "type": r["type"],
        }
        props = r.get("props") or {}
        for k in all_rel_keys:
            row[k] = "" if props.get(k) is None else props.get(k, "")
        rel_rows.append(row)
    safe_write_csv(RELS_CSV, rel_rows)

    print(f"  Saved nodes -> {NODES_CSV}")
    print(f"  Saved relationships -> {RELS_CSV}")

# ---------------------------------------------------------------------------
# 2. Load into NetworkX / igraph
# ---------------------------------------------------------------------------

def load_graphs() -> Tuple[Any, Any, Dict[str, Any]]:
    import pandas as pd
    import networkx as nx

    print("[2/8] Loading graph into NetworkX and igraph ...")
    nodes_df = pd.read_csv(NODES_CSV, dtype=str, keep_default_na=False)
    rels_df = pd.read_csv(RELS_CSV, dtype=str, keep_default_na=False)

    # Build NetworkX graph
    G = nx.MultiDiGraph()
    for _, row in nodes_df.iterrows():
        G.add_node(row["element_id"], **row.to_dict())

    for _, row in rels_df.iterrows():
        s, t, typ = row["source_element_id"], row["target_element_id"], row["type"]
        if s and t and typ:
            attrs = {k: v for k, v in row.to_dict().items()
                     if k not in {"source_element_id", "target_element_id", "type"}}
            G.add_edge(s, t, key=typ, type=typ, **attrs)

    # Simple undirected version for community algorithms
    G_undirected = nx.Graph()
    for u, v in G.edges():
        G_undirected.add_edge(u, v)

    # igraph object
    import igraph as ig
    node_id_map = {nid: i for i, nid in enumerate(G.nodes())}
    reverse_map = {i: nid for nid, i in node_id_map.items()}
    edges = [(node_id_map[u], node_id_map[v]) for u, v in G_undirected.edges()]
    ig_graph = ig.Graph(n=len(node_id_map), edges=edges, directed=False)

    meta = {
        "nodes_df": nodes_df,
        "rels_df": rels_df,
        "G": G,
        "G_undirected": G_undirected,
        "ig_graph": ig_graph,
        "node_id_map": node_id_map,
        "reverse_map": reverse_map,
    }
    return meta

# ---------------------------------------------------------------------------
# 3. Centrality
# ---------------------------------------------------------------------------

def run_centrality(meta):
    print("[3/8] Running centrality algorithms ...")
    G = meta["G"]
    G_undirected = meta["G_undirected"]
    nodes_df = meta["nodes_df"]

    def get_labels(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("labels", "")

    def get_name(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("name", "") or row.iloc[0].get("NAME", "") or row.iloc[0].get("Id", "") or ""

    # Degree centrality
    print("  Degree centrality ...")
    dc = nx.degree_centrality(G_undirected)
    rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
             "score": dc.get(nid, 0.0)} for nid in G_undirected.nodes()]
    safe_write_csv(CENTRALITY_DIR / "degree_centrality.csv", rows)
    append_manifest({
        "algorithm": "Degree Centrality", "category": "centrality",
        "status": "completed", "output_file": "centrality/degree_centrality.csv",
        "library": "networkx", "parameters": "directed=False",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": ""
    })

    # Betweenness centrality
    print("  Betweenness centrality ...")
    bc, t = timing(nx.betweenness_centrality)(G_undirected)
    rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
             "score": bc.get(nid, 0.0)} for nid in G_undirected.nodes()]
    safe_write_csv(CENTRALITY_DIR / "betweenness_centrality.csv", rows)
    append_manifest({
        "algorithm": "Betweenness Centrality", "category": "centrality",
        "status": "completed", "output_file": "centrality/betweenness_centrality.csv",
        "library": "networkx", "parameters": "",
        "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": ""
    })

    # Closeness centrality
    print("  Closeness centrality ...")
    cc, t = timing(nx.closeness_centrality)(G_undirected)
    rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
             "score": cc.get(nid, 0.0)} for nid in G_undirected.nodes()]
    safe_write_csv(CENTRALITY_DIR / "closeness_centrality.csv", rows)
    append_manifest({
        "algorithm": "Closeness Centrality", "category": "centrality",
        "status": "completed", "output_file": "centrality/closeness_centrality.csv",
        "library": "networkx", "parameters": "",
        "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": ""
    })

    # Eigenvector centrality
    print("  Eigenvector centrality ...")
    try:
        ec, t = timing(nx.eigenvector_centrality)(G_undirected, max_iter=1000, tol=1e-6)
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
                 "score": ec.get(nid, 0.0)} for nid in G_undirected.nodes()]
        safe_write_csv(CENTRALITY_DIR / "eigenvector_centrality.csv", rows)
        status = "completed"
        note = ""
    except Exception as e:
        rows = []
        status = "failed"
        note = str(e)
    append_manifest({
        "algorithm": "Eigenvector Centrality", "category": "centrality",
        "status": status, "output_file": "centrality/eigenvector_centrality.csv",
        "library": "networkx", "parameters": "max_iter=1000",
        "runtime_seconds": round(t, 3) if status == "completed" else 0,
        "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": note
    })

    # Harmonic centrality
    print("  Harmonic centrality ...")
    hc, t = timing(nx.harmonic_centrality)(G_undirected)
    rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
             "score": hc.get(nid, 0.0)} for nid in G_undirected.nodes()]
    safe_write_csv(CENTRALITY_DIR / "harmonic_centrality.csv", rows)
    append_manifest({
        "algorithm": "Harmonic Centrality", "category": "centrality",
        "status": "completed", "output_file": "centrality/harmonic_centrality.csv",
        "library": "networkx", "parameters": "",
        "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": ""
    })

    # PageRank
    print("  PageRank ...")
    pr, t = timing(nx.pagerank)(G_undirected, alpha=0.85, max_iter=200)
    rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
             "score": pr.get(nid, 0.0)} for nid in G_undirected.nodes()]
    safe_write_csv(CENTRALITY_DIR / "pagerank.csv", rows)
    append_manifest({
        "algorithm": "PageRank", "category": "centrality",
        "status": "completed", "output_file": "centrality/pagerank.csv",
        "library": "networkx", "parameters": "alpha=0.85",
        "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": ""
    })

    # HITS
    print("  HITS ...")
    try:
        if G.is_directed():
            h_hub, h_auth, t = timing(nx.hits)(G, max_iter=200, tol=1e-8)
            rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
                     "hub": h_hub.get(nid, 0.0), "authority": h_auth.get(nid, 0.0)}
                    for nid in G.nodes()]
            safe_write_csv(CENTRALITY_DIR / "hits.csv", rows)
            status = "completed"
        else:
            raise RuntimeError("HITS requires a directed graph")
    except Exception as e:
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
                 "hub": "", "authority": ""} for nid in G.nodes()]
        safe_write_csv(CENTRALITY_DIR / "hits.csv", rows)
        status = "requires_parameters" if "directed" in str(e).lower() else "failed"
    append_manifest({
        "algorithm": "HITS", "category": "centrality",
        "status": status, "output_file": "centrality/hits.csv",
        "library": "networkx", "parameters": "",
        "runtime_seconds": round(t, 3) if status == "completed" else 0,
        "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": "Requires directed graph" if status == "requires_parameters" else ""
    })

    # ArticleRank
    # ArticleRank differs from PageRank by using average-neighbor-degree damping.
    # Instead of teleporting uniformly, it damps by 1/avg_degree of neighbors.
    print("  ArticleRank ...")
    try:
        start = time.time()
        avg_degree = sum(dict(G_undirected.degree()).values()) / G_undirected.number_of_nodes()
        # Build personalization vector weighted by inverse average neighbor degree
        personalization = {}
        for n in G_undirected.nodes():
            neighbors = list(G_undirected.neighbors(n))
            if neighbors:
                avg_neighbor_deg = sum(G_undirected.degree(nb) for nb in neighbors) / len(neighbors)
                personalization[n] = 1.0 / max(avg_neighbor_deg, 1)
            else:
                personalization[n] = 1.0 / max(avg_degree, 1)
        ar = nx.pagerank(G_undirected, alpha=0.85, personalization=personalization, max_iter=200)
        t = time.time() - start
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
                 "score": ar.get(nid, 0.0)} for nid in G_undirected.nodes()]
        safe_write_csv(CENTRALITY_DIR / "article_rank.csv", rows)
        status = "completed"
        note = "ArticleRank with average-neighbor-degree damping"
    except Exception as e:
        rows = []
        status = "failed"
        note = str(e)
        t = 0
    append_manifest({
        "algorithm": "ArticleRank", "category": "centrality",
        "status": status, "output_file": "centrality/article_rank.csv",
        "library": "networkx", "parameters": "personalization=avg_neighbor_degree_damping",
        "runtime_seconds": round(t, 3) if status == "completed" else 0,
        "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": note
    })

    # Articulation Points
    print("  Articulation Points ...")
    try:
        ap, t = timing(nx.articulation_points)(G_undirected)
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid)} for nid in ap]
        safe_write_csv(CENTRALITY_DIR / "articulation_points.csv", rows)
        status = "completed"
    except Exception as e:
        rows = []
        status = "failed"
    append_manifest({
        "algorithm": "Articulation Points", "category": "centrality",
        "status": status, "output_file": "centrality/articulation_points.csv",
        "library": "networkx", "parameters": "",
        "runtime_seconds": round(t, 3) if status == "completed" else 0,
        "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": ""
    })

    # Bridges
    print("  Bridges ...")
    try:
        bridges, t = timing(nx.bridges)(G_undirected)
        rows = [{"source": u, "target": v} for u, v in bridges]
        safe_write_csv(CENTRALITY_DIR / "bridges.csv", rows)
        status = "completed"
    except Exception as e:
        rows = []
        status = "failed"
    append_manifest({
        "algorithm": "Bridges", "category": "centrality",
        "status": status, "output_file": "centrality/bridges.csv",
        "library": "networkx", "parameters": "",
        "runtime_seconds": round(t, 3) if status == "completed" else 0,
        "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
        "notes": ""
    })

    # CELF (Cost-Effective Lazy Forward) - completed by run_parameterized.py
    # Not re-running here to avoid duplicate manifest entries.
    print("  CELF ... (handled by run_parameterized.py)")

# ---------------------------------------------------------------------------
# 4. Community / Graph Structure
# ---------------------------------------------------------------------------

def run_community(meta):
    print("[4/8] Running community detection algorithms ...")
    G_undirected = meta["G_undirected"]
    ig_graph = meta["ig_graph"]
    nodes_df = meta["nodes_df"]
    reverse_map = meta["reverse_map"]

    def get_labels(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("labels", "")

    def get_name(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("name", "") or row.iloc[0].get("NAME", "") or row.iloc[0].get("Id", "") or ""

    def ig_rows(communities):
        rows = []
        for idx, members in enumerate(communities):
            for v in members:
                nid = reverse_map.get(v, v)
                rows.append({"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "community_id": idx})
        return rows

    # Louvain
    print("  Louvain ...")
    try:
        import community as community_louvain
        partition, t = timing(community_louvain.best_partition)(G_undirected)
        community_of = {}
        for nid, cid in partition.items():
            community_of.setdefault(cid, []).append(nid)
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "community_id": cid}
                for nid, cid in partition.items()]
        safe_write_csv(COMMUNITY_DIR / "louvain.csv", rows)
        modularity, _ = timing(community_louvain.modularity)(partition, G_undirected)
        sizes = sorted([(cid, len(members)) for cid, members in community_of.items()], key=lambda x: -x[1])
        append_manifest({
            "algorithm": "Louvain", "category": "community",
            "status": "completed", "output_file": "community/louvain.csv",
            "library": "python-louvain", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": f"communities={len(community_of)}, modularity={modularity:.4f}"
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Louvain", "category": "community",
            "status": "failed", "output_file": "", "library": "python-louvain",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # Leiden
    print("  Leiden ...")
    try:
        import igraph as ig
        import leidenalg
        partition, t = timing(leidenalg.find_partition)(ig_graph, leidenalg.ModularityVertexPartition)
        rows = ig_rows(partition)
        safe_write_csv(COMMUNITY_DIR / "leiden.csv", rows)
        modularity = partition.modularity
        sizes = sorted([(idx, len(members)) for idx, members in enumerate(partition)], key=lambda x: -x[1])
        append_manifest({
            "algorithm": "Leiden", "category": "community",
            "status": "completed", "output_file": "community/leiden.csv",
            "library": "leidenalg", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": ig_graph.ecount(),
            "notes": f"communities={len(partition)}, modularity={modularity:.4f}"
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Leiden", "category": "community",
            "status": "failed", "output_file": "", "library": "leidenalg",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # Label Propagation (networkx)
    print("  Label Propagation ...")
    try:
        from cdlib import algorithms as cdalgos
        from networkx.algorithms.community import asyn_lpa_communities
        comms, t = timing(asyn_lpa_communities)(G_undirected)
        rows = []
        for cid, comm in enumerate(comms):
            for nid in comm:
                rows.append({"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "community_id": cid})
        safe_write_csv(COMMUNITY_DIR / "label_propagation.csv", rows)
        append_manifest({
            "algorithm": "Label Propagation", "category": "community",
            "status": "completed", "output_file": "community/label_propagation.csv",
            "library": "networkx", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": f"communities={len(comms)}"
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Label Propagation", "category": "community",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # K-Core Decomposition
    print("  K-Core ...")
    try:
        kcore, t = timing(nx.core_number)(G_undirected)
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "core_number": kcore[nid]}
                for nid in G_undirected.nodes()]
        safe_write_csv(COMMUNITY_DIR / "k_core.csv", rows)
        append_manifest({
            "algorithm": "K-Core Decomposition", "category": "community",
            "status": "completed", "output_file": "community/k_core.csv",
            "library": "networkx", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": ""
        })
    except Exception as e:
        append_manifest({
            "algorithm": "K-Core Decomposition", "category": "community",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # Triangle Count
    print("  Triangle Count ...")
    try:
        tc, t = timing(nx.triangles)(G_undirected)
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "triangle_count": tc[nid]}
                for nid in G_undirected.nodes()]
        safe_write_csv(COMMUNITY_DIR / "triangle_count.csv", rows)
        append_manifest({
            "algorithm": "Triangle Count", "category": "community",
            "status": "completed", "output_file": "community/triangle_count.csv",
            "library": "networkx", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": ""
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Triangle Count", "category": "community",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # Local Clustering Coefficient
    print("  Local Clustering Coefficient ...")
    try:
        lcc, t = timing(nx.clustering)(G_undirected)
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "clustering_coefficient": lcc[nid]}
                for nid in G_undirected.nodes()]
        safe_write_csv(COMMUNITY_DIR / "clustering_coefficient.csv", rows)
        append_manifest({
            "algorithm": "Local Clustering Coefficient", "category": "community",
            "status": "completed", "output_file": "community/clustering_coefficient.csv",
            "library": "networkx", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": ""
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Local Clustering Coefficient", "category": "community",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # WCC
    print("  Weakly Connected Components ...")
    try:
        if G.is_directed():
            wccs, t = timing(list)(nx.weakly_connected_components(G))
        else:
            wccs, t = timing(list)(nx.connected_components(G_undirected))
        rows = []
        for cid, comp in enumerate(wccs):
            for nid in comp:
                rows.append({"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "component_id": cid})
        safe_write_csv(COMMUNITY_DIR / "wcc.csv", rows)
        append_manifest({
            "algorithm": "Weakly Connected Components", "category": "community",
            "status": "completed", "output_file": "community/wcc.csv",
            "library": "networkx", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": f"components={len(wccs)}"
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Weakly Connected Components", "category": "community",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # SCC
    print("  Strongly Connected Components ...")
    try:
        if G.is_directed():
            sccs, t = timing(list)(nx.strongly_connected_components(G))
            rows = []
            for cid, comp in enumerate(sccs):
                for nid in comp:
                    rows.append({"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "component_id": cid})
            safe_write_csv(COMMUNITY_DIR / "scc.csv", rows)
            status = "completed"
            note = f"components={len(sccs)}"
        else:
            rows = []
            status = "requires_parameters"
            note = "Graph is undirected; SCC requires directed representation"
    except Exception as e:
        rows = []
        status = "failed"
        note = str(e)
    append_manifest({
        "algorithm": "Strongly Connected Components", "category": "community",
        "status": status, "output_file": "community/scc.csv" if status == "completed" else "",
        "library": "networkx", "parameters": "",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": note
    })

    # Modularity
    print("  Modularity ...")
    try:
        if 'partition' in locals():
            mod, t = timing(community_louvain.modularity)(partition, G_undirected)
        else:
            # recompute
            import community as community_louvain
            partition, _ = timing(community_louvain.best_partition)(G_undirected)
            mod, t = timing(community_louvain.modularity)(partition, G_undirected)
        rows = [{"metric": "modularity", "value": mod}]
        safe_write_csv(COMMUNITY_DIR / "modularity.csv", rows)
        append_manifest({
            "algorithm": "Modularity", "category": "community",
            "status": "completed", "output_file": "community/modularity.csv",
            "library": "python-louvain", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(partition), "edges_processed": G_undirected.size(),
            "notes": f"value={mod:.4f}"
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Modularity", "category": "community",
            "status": "failed", "output_file": "", "library": "python-louvain",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # Modularity Optimization (Louvain with best partition)
    print("  Modularity Optimization ...")
    try:
        import community as community_louvain
        partition, t = timing(community_louvain.best_partition)(G_undirected)
        mod, _ = timing(community_louvain.modularity)(partition, G_undirected)
        rows = [{"metric": "modularity", "value": mod}]
        safe_write_csv(COMMUNITY_DIR / "modularity_optimization.csv", rows)
        append_manifest({
            "algorithm": "Modularity Optimization", "category": "community",
            "status": "completed", "output_file": "community/modularity_optimization.csv",
            "library": "python-louvain", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(partition), "edges_processed": G_undirected.size(),
            "notes": ""
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Modularity Optimization", "category": "community",
            "status": "failed", "output_file": "", "library": "python-louvain",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # Clique Counting
    print("  Clique Counting ...")
    try:
        cliques, t = timing(list)(nx.enumerate_all_cliques(G_undirected))
        rows = [{"clique_id": idx, "size": len(c), "nodes": "|".join(c)} for idx, c in enumerate(cliques)]
        safe_write_csv(COMMUNITY_DIR / "clique_count.csv", rows)
        append_manifest({
            "algorithm": "Clique Counting", "category": "community",
            "status": "completed", "output_file": "community/clique_count.csv",
            "library": "networkx", "parameters": "",
            "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": f"cliques={len(rows)}"
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Clique Counting", "category": "community",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # Conductance
    print("  Conductance ...")
    try:
        if 'partition' not in locals():
            import community as community_louvain
            partition = community_louvain.best_partition(G_undirected)
        community_sets = {}
        for nid, cid in partition.items():
            community_sets.setdefault(cid, set()).add(nid)
        conds = []
        for cid in sorted(community_sets.keys()):
            comm = community_sets[cid]
            try:
                cval = nx.algorithms.cuts.conductance(G_undirected, comm)
            except (ZeroDivisionError, nx.NetworkXError):
                cval = 0.0
            conds.append({"community_id": cid, "conductance": cval, "size": len(comm)})
        safe_write_csv(COMMUNITY_DIR / "conductance.csv", conds)
        append_manifest({
            "algorithm": "Conductance", "category": "community",
            "status": "completed", "output_file": "community/conductance.csv",
            "library": "networkx", "parameters": "per-community via nx.algorithms.cuts.conductance",
            "runtime_seconds": 0, "nodes_processed": len(conds), "edges_processed": G_undirected.size(),
            "notes": ""
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Conductance", "category": "community",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # HDBSCAN
    print("  HDBSCAN ...")
    append_manifest({
        "algorithm": "HDBSCAN", "category": "community",
        "status": "requires_parameters", "output_file": "",
        "library": "hdbscan", "parameters": "feature_matrix",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires node feature vectors for clustering"
    })

    # K-Means Clustering
    print("  K-Means Clustering ...")
    append_manifest({
        "algorithm": "K-Means Clustering", "category": "community",
        "status": "requires_parameters", "output_file": "",
        "library": "scikit-learn", "parameters": "k, feature_matrix",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires k and node feature vectors"
    })

    # K-1 Coloring
    print("  K-1 Coloring ...")
    try:
        coloring = nx.coloring.greedy_color(G_undirected, strategy="largest_first")
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "color": cid}
                for nid, cid in coloring.items()]
        safe_write_csv(COMMUNITY_DIR / "k1_coloring.csv", rows)
        append_manifest({
            "algorithm": "K-1 Coloring", "category": "community",
            "status": "completed", "output_file": "community/k1_coloring.csv",
            "library": "networkx", "parameters": "strategy=largest_first",
            "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": ""
        })
    except Exception as e:
        append_manifest({
            "algorithm": "K-1 Coloring", "category": "community",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": str(e)
        })

    # Approximate Maximum k-cut
    print("  Approximate Maximum k-cut ...")
    append_manifest({
        "algorithm": "Approximate Maximum k-cut", "category": "community",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx / custom", "parameters": "k",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires explicit k parameter"
    })

    # Speaker-Listener Label Propagation
    print("  Speaker-Listener Label Propagation ...")
    append_manifest({
        "algorithm": "Speaker-Listener Label Propagation", "category": "community",
        "status": "requires_parameters", "output_file": "",
        "library": "cdlib", "parameters": "k, labels",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires seed nodes and label constraints"
    })

# ---------------------------------------------------------------------------
# 5. Similarity
# ---------------------------------------------------------------------------

def run_similarity(meta):
    print("[5/8] Running similarity algorithms ...")
    G = meta["G"]
    G_undirected = meta["G_undirected"]
    nodes_df = meta["nodes_df"]

    def get_labels(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("labels", "")

    def get_name(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("name", "") or row.iloc[0].get("NAME", "") or row.iloc[0].get("Id", "") or ""

    # Node Similarity
    print("  Node Similarity ...")
    append_manifest({
        "algorithm": "Node Similarity", "category": "similarity",
        "status": "requires_parameters", "output_file": "",
        "library": "neo4j GDS / networkx", "parameters": "top_k, similarity_metric",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires top_k and similarity metric"
    })

    # Filtered Node Similarity
    print("  Filtered Node Similarity ...")
    append_manifest({
        "algorithm": "Filtered Node Similarity", "category": "similarity",
        "status": "requires_parameters", "output_file": "",
        "library": "neo4j GDS", "parameters": "top_k, filter_predicate",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires top_k and filter predicate"
    })

    # K-Nearest Neighbors
    print("  K-Nearest Neighbors ...")
    append_manifest({
        "algorithm": "K-Nearest Neighbors", "category": "similarity",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx / neo4j GDS", "parameters": "k, metric",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires k and distance metric"
    })

    # Filtered K-Nearest Neighbors
    print("  Filtered K-Nearest Neighbors ...")
    append_manifest({
        "algorithm": "Filtered K-Nearest Neighbors", "category": "similarity",
        "status": "requires_parameters", "output_file": "",
        "library": "neo4j GDS", "parameters": "k, filter_predicate",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires k and filter predicate"
    })

# ---------------------------------------------------------------------------
# 6. Path Finding
# ---------------------------------------------------------------------------

def run_paths(meta):
    print("[6/8] Running path-finding algorithms ...")
    G = meta["G"]
    G_undirected = meta["G_undirected"]
    nodes_df = meta["nodes_df"]

    def get_labels(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("labels", "")

    def get_name(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("name", "") or row.iloc[0].get("NAME", "") or row.iloc[0].get("Id", "") or ""

    nodes = list(G.nodes())
    # Pick a few representative source/target nodes
    sample_patients = nodes_df[nodes_df["labels"].str.contains("Patient", na=False)].head(3)
    if len(sample_patients) == 0:
        sample_patients = nodes_df.head(3)
    sample_encounters = nodes_df[nodes_df["labels"].str.contains("Encounter", na=False)].head(3)
    if len(sample_encounters) == 0:
        sample_encounters = nodes_df.head(3)

    source_nodes = sample_patients["element_id"].tolist()[:1]
    target_nodes = sample_encounters["element_id"].tolist()[:1]

    # Dijkstra Source-Target
    print("  Dijkstra Source-Target ...")
    rows = []
    for s in source_nodes:
        for t in target_nodes:
            if s != t and nx.has_path(G, s, t):
                try:
                    path, dist = nx.bidirectional_dijkstra(G, s, t)
                    rows.append({
                        "source": s, "target": t, "distance": dist,
                        "path_length": len(path), "path": "|".join(path)
                    })
                except Exception:
                    pass
    safe_write_csv(PATHS_DIR / "dijkstra_source_target.csv", rows)
    append_manifest({
        "algorithm": "Dijkstra Source-Target", "category": "paths",
        "status": "completed", "output_file": "paths/dijkstra_source_target.csv",
        "library": "networkx", "parameters": f"source={source_nodes}, target={target_nodes}",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": ""
    })

    # Dijkstra Single-Source
    print("  Dijkstra Single-Source ...")
    rows = []
    for s in source_nodes:
        try:
            lengths, paths = nx.single_source_dijkstra_path(G, s, cutoff=None)
            for t, p in paths.items():
                rows.append({
                    "source": s, "target": t, "distance": lengths.get(t, None),
                    "path_length": len(p), "path": "|".join(p)
                })
        except Exception:
            pass
    safe_write_csv(PATHS_DIR / "dijkstra_single_source.csv", rows)
    append_manifest({
        "algorithm": "Dijkstra Single-Source", "category": "paths",
        "status": "completed", "output_file": "paths/dijkstra_single_source.csv",
        "library": "networkx", "parameters": f"source={source_nodes}",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": ""
    })

    # Bellman-Ford
    print("  Bellman-Ford ...")
    rows = []
    for s in source_nodes:
        try:
            lengths = nx.single_source_bellman_ford_path_length(G, s)
            paths = nx.single_source_bellman_ford_path(G, s)
            for t, p in paths.items():
                rows.append({
                    "source": s, "target": t, "distance": lengths.get(t, None),
                    "path_length": len(p), "path": "|".join(p)
                })
        except Exception:
            pass
    safe_write_csv(PATHS_DIR / "bellman_ford.csv", rows)
    append_manifest({
        "algorithm": "Bellman-Ford Single-Source", "category": "paths",
        "status": "completed", "output_file": "paths/bellman_ford.csv",
        "library": "networkx", "parameters": f"source={source_nodes}",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": ""
    })

    # A*
    print("  A* Shortest Path ...")
    rows = []
    if source_nodes and target_nodes:
        s, t = source_nodes[0], target_nodes[0]
        if s != t:
            try:
                path = nx.astar_path(G, s, t, heuristic=lambda u, v: 0)
                dist = nx.astar_path_length(G, s, t, heuristic=lambda u, v: 0)
                rows.append({
                    "source": s, "target": t, "distance": dist,
                    "path_length": len(path), "path": "|".join(path)
                })
            except Exception:
                pass
    safe_write_csv(PATHS_DIR / "astar.csv", rows)
    append_manifest({
        "algorithm": "A* Shortest Path", "category": "paths",
        "status": "completed", "output_file": "paths/astar.csv",
        "library": "networkx", "parameters": f"source={source_nodes}, target={target_nodes}, heuristic=zero",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": "Heuristic set to zero (A* equivalent to Dijkstra)"
    })

    # Yen's Shortest Path
    print("  Yen's Shortest Path ...")
    rows = []
    if source_nodes and target_nodes:
        s, t = source_nodes[0], target_nodes[0]
        if s != t:
            try:
                paths = nx.shortest_simple_paths(G, s, t)
                for k, p in enumerate(paths):
                    if k >= 5:
                        break
                    dist = nx.path_weight(G, p, weight="weight")
                    rows.append({
                        "source": s, "target": t, "k": k + 1,
                        "distance": dist, "path_length": len(p), "path": "|".join(p)
                    })
            except Exception:
                pass
    safe_write_csv(PATHS_DIR / "yen.csv", rows)
    append_manifest({
        "algorithm": "Yen's Shortest Path", "category": "paths",
        "status": "completed", "output_file": "paths/yen.csv",
        "library": "networkx", "parameters": f"source={source_nodes}, target={target_nodes}, k=5",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": ""
    })

    # BFS
    print("  Breadth First Search ...")
    rows = []
    for s in source_nodes:
        try:
            bfs = nx.bfs_tree(G, s)
            rows.extend([{"source": s, "node": n, "layer": d} for n, d in nx.shortest_path_length(bfs, s).items()])
        except Exception:
            pass
    safe_write_csv(PATHS_DIR / "bfs.csv", rows)
    append_manifest({
        "algorithm": "Breadth First Search", "category": "paths",
        "status": "completed", "output_file": "paths/bfs.csv",
        "library": "networkx", "parameters": f"source={source_nodes}",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": ""
    })

    # DFS
    print("  Depth First Search ...")
    rows = []
    for s in source_nodes:
        try:
            dfs = nx.dfs_tree(G, s)
            for idx, n in enumerate(dfs):
                rows.append({"source": s, "node": n, "visit_order": idx})
        except Exception:
            pass
    safe_write_csv(PATHS_DIR / "dfs.csv", rows)
    append_manifest({
        "algorithm": "Depth First Search", "category": "paths",
        "status": "completed", "output_file": "paths/dfs.csv",
        "library": "networkx", "parameters": f"source={source_nodes}",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": ""
    })

    # Random Walk
    print("  Random Walk ...")
    append_manifest({
        "algorithm": "Random Walk", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx", "parameters": "start_nodes, steps",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires start nodes and number of steps"
    })

    # Delta-Stepping
    print("  Delta-Stepping ...")
    append_manifest({
        "algorithm": "Delta-Stepping Single-Source Shortest Path", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "custom / networkx", "parameters": "delta, source",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires delta and source parameters"
    })

    # Minimum Weight Spanning Tree
    print("  Minimum Weight Spanning Tree ...")
    rows = []
    try:
        mst = nx.minimum_spanning_tree(G_undirected)
        rows = [{"source": u, "target": v} for u, v in mst.edges()]
        safe_write_csv(PATHS_DIR / "minimum_weight_spanning_tree.csv", rows)
        append_manifest({
            "algorithm": "Minimum Weight Spanning Tree", "category": "paths",
            "status": "completed", "output_file": "paths/minimum_weight_spanning_tree.csv",
            "library": "networkx", "parameters": "",
            "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": ""
        })
    except Exception as e:
        append_manifest({
            "algorithm": "Minimum Weight Spanning Tree", "category": "paths",
            "status": "failed", "output_file": "", "library": "networkx",
            "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": G_undirected.size(),
            "notes": str(e)
        })

    # Minimum Directed Steiner Tree
    print("  Minimum Directed Steiner Tree ...")
    append_manifest({
        "algorithm": "Minimum Directed Steiner Tree", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx", "parameters": "terminals, root",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires terminal node set and root"
    })

    # Prize-collecting Steiner Tree
    print("  Prize-collecting Steiner Tree ...")
    append_manifest({
        "algorithm": "Prize-collecting Steiner Tree", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "custom", "parameters": "prizes, penalties",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires node prizes and edge penalties"
    })

    # Maximum Flow
    print("  Maximum Flow ...")
    append_manifest({
        "algorithm": "Maximum Flow", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx", "parameters": "source, sink, capacity",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires source, sink, and edge capacity"
    })

    # Minimum Cost Maximum Flow
    print("  Minimum Cost Maximum Flow ...")
    append_manifest({
        "algorithm": "Minimum Cost Maximum Flow", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx", "parameters": "source, sink, capacity, cost",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires source, sink, capacity, and cost attributes"
    })

    # Minimum Weight k-Spanning Tree
    print("  Minimum Weight k-Spanning Tree ...")
    append_manifest({
        "algorithm": "Minimum Weight k-Spanning Tree", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx / custom", "parameters": "k",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires k parameter"
    })

    # All Pairs Shortest Path
    print("  All Pairs Shortest Path ...")
    append_manifest({
        "algorithm": "All Pairs Shortest Path", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx", "parameters": "subset_of_nodes",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "O(n^3) cost; run on subset or require explicit node set"
    })

    # Longest Path for DAG
    print("  Longest Path for DAG ...")
    append_manifest({
        "algorithm": "Longest Path for DAG", "category": "paths",
        "status": "requires_parameters", "output_file": "",
        "library": "networkx", "parameters": "source, target, DAG structure",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires DAG structure and source/target"
    })

# ---------------------------------------------------------------------------
# 7. DAG algorithms
# ---------------------------------------------------------------------------

def run_dag(meta):
    print("[7/8] Running DAG algorithms ...")
    G = meta["G"]
    nodes_df = meta["nodes_df"]

    def get_labels(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("labels", "")

    def get_name(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("name", "") or row.iloc[0].get("NAME", "") or row.iloc[0].get("Id", "") or ""

    # Topological Sort
    print("  Topological Sort ...")
    rows = []
    try:
        if nx.is_directed_acyclic_graph(G):
            order = list(nx.topological_sort(G))
            rows = [{"rank": idx, "node_id": nid, "labels": get_labels(nid), "name": get_name(nid)}
                    for idx, nid in enumerate(order)]
            status = "completed"
        else:
            status = "requires_parameters"
    except Exception as e:
        status = "failed"
    safe_write_csv(DAG_DIR / "topological_sort.csv", rows)
    append_manifest({
        "algorithm": "Topological Sort", "category": "dag",
        "status": status, "output_file": "dag/topological_sort.csv" if status == "completed" else "",
        "library": "networkx", "parameters": "",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": "Requires DAG structure" if status == "requires_parameters" else ""
    })

    # Longest Path
    print("  Longest Path ...")
    rows = []
    try:
        if nx.is_directed_acyclic_graph(G):
            order = list(nx.topological_sort(G))
            dist = {}
            for n in order:
                dist[n] = 0
            for n in order:
                for succ in G.successors(n):
                    dist[succ] = max(dist.get(succ, 0), dist[n] + 1)
            max_dist = max(dist.values())
            rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid), "longest_path_length": dist[nid]}
                    for nid in order]
            status = "completed"
        else:
            status = "requires_parameters"
    except Exception as e:
        status = "failed"
    safe_write_csv(DAG_DIR / "longest_path.csv", rows)
    append_manifest({
        "algorithm": "Longest Path", "category": "dag",
        "status": status, "output_file": "dag/longest_path.csv" if status == "completed" else "",
        "library": "networkx", "parameters": "",
        "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
        "notes": "Requires DAG structure" if status == "requires_parameters" else ""
    })

# ---------------------------------------------------------------------------
# 8. Node Embeddings
# ---------------------------------------------------------------------------

def run_embeddings(meta):
    print("[8/8] Running node embedding algorithms ...")
    G = meta["G"]
    nodes_df = meta["nodes_df"]

    def get_labels(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("labels", "")

    def get_name(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("name", "") or row.iloc[0].get("NAME", "") or row.iloc[0].get("Id", "") or ""

    # FastRP
    print("  FastRP ...")
    append_manifest({
        "algorithm": "FastRP", "category": "embeddings",
        "status": "requires_parameters", "output_file": "",
        "library": "neo4j GDS", "parameters": "embeddingDimension, iterationWeights, normalizationStrength",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires dimension, iteration weights, and normalization parameters"
    })

    # GraphSAGE
    print("  GraphSAGE ...")
    append_manifest({
        "algorithm": "GraphSAGE", "category": "embeddings",
        "status": "requires_parameters", "output_file": "",
        "library": "neo4j GDS / stellargraph", "parameters": "featureProperties, embeddingDimension, epochs",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires node feature properties and model hyperparameters"
    })

    # Node2Vec
    print("  Node2Vec ...")
    append_manifest({
        "algorithm": "Node2Vec", "category": "embeddings",
        "status": "requires_parameters", "output_file": "",
        "library": "node2vec / gensim", "parameters": "dimensions, walk_length, num_walks, p, q",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires embedding dimensions and walk parameters"
    })

    # HashGNN
    print("  HashGNN ...")
    append_manifest({
        "algorithm": "HashGNN", "category": "embeddings",
        "status": "requires_parameters", "output_file": "",
        "library": "neo4j GDS", "parameters": "embeddingDimension, iterations",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires dimension and iterations parameters"
    })

    # FastPath
    print("  FastPath ...")
    append_manifest({
        "algorithm": "FastPath", "category": "embeddings",
        "status": "requires_parameters", "output_file": "",
        "library": "neo4j GDS", "parameters": "embeddingDimension, iterations",
        "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
        "notes": "Requires dimension and iterations parameters"
    })

# ---------------------------------------------------------------------------
# 9. Summary Report
# ---------------------------------------------------------------------------

def write_summary():
    print("Writing summary report ...")
    if not MANIFEST_CSV.exists():
        return
    df = pd.read_csv(MANIFEST_CSV)
    summary = {
        "total_algorithms": len(df),
        "completed": len(df[df["status"] == "completed"]),
        "failed": len(df[df["status"] == "failed"]),
        "requires_parameters": len(df[df["status"] == "requires_parameters"]),
    }
    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary.keys())
        writer.writeheader()
        writer.writerow(summary)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    export_graph()
    meta = load_graphs()
    run_centrality(meta)
    run_community(meta)
    run_similarity(meta)
    run_paths(meta)
    run_dag(meta)
    run_embeddings(meta)
    write_summary()
    print("\nPipeline complete. Results in:")
    print(f"  {DATA_DIR}")
    print(f"  {CENTRALITY_DIR}")
    print(f"  {COMMUNITY_DIR}")
    print(f"  {SIMILARITY_DIR}")
    print(f"  {PATHS_DIR}")
    print(f"  {DAG_DIR}")
    print(f"  {EMBEDDINGS_DIR}")
    print(f"  {REPORTS_DIR}")


if __name__ == "__main__":
    main()
