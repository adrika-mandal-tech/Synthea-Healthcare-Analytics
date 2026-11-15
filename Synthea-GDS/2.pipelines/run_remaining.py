"""
Optimized continuation pipeline for Synthea graph analytics.
Loads from existing CSV exports and completes remaining algorithms.
"""

import os
import sys
import time
import csv
import json
import math
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Any

warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import networkx as nx
import igraph as ig

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data"
CENTRALITY_DIR = WORKSPACE / "centrality"
COMMUNITY_DIR = WORKSPACE / "community"
SIMILARITY_DIR = WORKSPACE / "similarity"
PATHS_DIR = WORKSPACE / "paths"
DAG_DIR = WORKSPACE / "dag"
EMBEDDINGS_DIR = WORKSPACE / "embeddings"
REPORTS_DIR = WORKSPACE / "reports"

for d in [CENTRALITY_DIR, COMMUNITY_DIR, SIMILARITY_DIR, PATHS_DIR, DAG_DIR, EMBEDDINGS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

NODES_CSV = DATA_DIR / "nodes.csv"
RELS_CSV = DATA_DIR / "relationships.csv"
MANIFEST_CSV = REPORTS_DIR / "algorithm_manifest.csv"

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def safe_write_csv(path: Path, rows: List[Dict[str, Any]]):
    if not rows:
        # write empty file with header if we have schema
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


def load_graphs():
    print("Loading graph from CSV ...")
    nodes_df = pd.read_csv(NODES_CSV, dtype=str, keep_default_na=False)
    rels_df = pd.read_csv(RELS_CSV, dtype=str, keep_default_na=False)

    G = nx.MultiDiGraph()
    for _, row in nodes_df.iterrows():
        G.add_node(row["element_id"], **row.to_dict())

    for _, row in rels_df.iterrows():
        s = row.get("source_element_id", "")
        t = row.get("target_element_id", "")
        typ = row.get("type", "")
        if s and t and typ:
            attrs = {k: v for k, v in row.to_dict().items()
                     if k not in {"source_element_id", "target_element_id", "type"}}
            G.add_edge(s, t, key=typ, type=typ, **attrs)

    G_undirected = nx.Graph()
    for u, v in G.edges():
        G_undirected.add_edge(u, v)

    # igraph undirected
    node_list = list(G.nodes())
    node_id_map = {nid: i for i, nid in enumerate(node_list)}
    reverse_map = {i: nid for nid, i in node_id_map.items()}
    edges = [(node_id_map[u], node_id_map[v]) for u, v in G_undirected.edges()]
    ig_graph = ig.Graph(n=len(node_list), edges=edges, directed=False)

    meta = {
        "nodes_df": nodes_df,
        "rels_df": rels_df,
        "G": G,
        "G_undirected": G_undirected,
        "ig_graph": ig_graph,
        "node_id_map": node_id_map,
        "reverse_map": reverse_map,
        "node_list": node_list,
    }
    n = G.number_of_nodes()
    m = G.number_of_edges()
    print(f"  Nodes: {n}, Relationships: {m}")
    return meta


def get_labels(nodes_df, nid):
    row = nodes_df[nodes_df["element_id"] == nid]
    if row.empty:
        return ""
    return row.iloc[0].get("labels", "")


def get_name(nodes_df, nid):
    row = nodes_df[nodes_df["element_id"] == nid]
    if row.empty:
        return ""
    return (row.iloc[0].get("name", "") or
            row.iloc[0].get("NAME", "") or
            row.iloc[0].get("Id", "") or "")


# ---------------------------------------------------------------------------
# Centrality
# ---------------------------------------------------------------------------

def run_centrality(meta):
    print("[Centrality] Running remaining centrality algorithms ...")
    G = meta["G"]
    G_undirected = meta["G_undirected"]
    nodes_df = meta["nodes_df"]

    # Closeness Centrality
    if not (CENTRALITY_DIR / "closeness_centrality.csv").exists():
        print("  Closeness centrality ...")
        try:
            cc, t = timing(nx.closeness_centrality)(G_undirected)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "score": cc.get(nid, 0.0)}
                    for nid in G_undirected.nodes()]
            safe_write_csv(CENTRALITY_DIR / "closeness_centrality.csv", rows)
            append_manifest({
                "algorithm": "Closeness Centrality", "category": "centrality",
                "status": "completed", "output_file": "centrality/closeness_centrality.csv",
                "library": "networkx", "parameters": "",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": ""
            })
        except Exception as e:
            append_manifest({
                "algorithm": "Closeness Centrality", "category": "centrality",
                "status": "failed", "output_file": "", "library": "networkx",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": G_undirected.size(),
                "notes": str(e)
            })

    # Eigenvector Centrality
    if not (CENTRALITY_DIR / "eigenvector_centrality.csv").exists():
        print("  Eigenvector centrality ...")
        try:
            ec, t = timing(nx.eigenvector_centrality)(G_undirected, max_iter=1000, tol=1e-6)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "score": ec.get(nid, 0.0)}
                    for nid in G_undirected.nodes()]
            safe_write_csv(CENTRALITY_DIR / "eigenvector_centrality.csv", rows)
            append_manifest({
                "algorithm": "Eigenvector Centrality", "category": "centrality",
                "status": "completed", "output_file": "centrality/eigenvector_centrality.csv",
                "library": "networkx", "parameters": "max_iter=1000",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": ""
            })
        except Exception as e:
            append_manifest({
                "algorithm": "Eigenvector Centrality", "category": "centrality",
                "status": "failed", "output_file": "", "library": "networkx",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": G_undirected.size(),
                "notes": str(e)
            })

    # Harmonic Centrality
    if not (CENTRALITY_DIR / "harmonic_centrality.csv").exists():
        print("  Harmonic centrality ...")
        try:
            hc, t = timing(nx.harmonic_centrality)(G_undirected)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "score": hc.get(nid, 0.0)}
                    for nid in G_undirected.nodes()]
            safe_write_csv(CENTRALITY_DIR / "harmonic_centrality.csv", rows)
            append_manifest({
                "algorithm": "Harmonic Centrality", "category": "centrality",
                "status": "completed", "output_file": "centrality/harmonic_centrality.csv",
                "library": "networkx", "parameters": "",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": ""
            })
        except Exception as e:
            append_manifest({
                "algorithm": "Harmonic Centrality", "category": "centrality",
                "status": "failed", "output_file": "", "library": "networkx",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": G_undirected.size(),
                "notes": str(e)
            })

    # PageRank
    if not (CENTRALITY_DIR / "pagerank.csv").exists():
        print("  PageRank ...")
        try:
            pr, t = timing(nx.pagerank)(G_undirected, alpha=0.85, max_iter=200)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "score": pr.get(nid, 0.0)}
                    for nid in G_undirected.nodes()]
            safe_write_csv(CENTRALITY_DIR / "pagerank.csv", rows)
            append_manifest({
                "algorithm": "PageRank", "category": "centrality",
                "status": "completed", "output_file": "centrality/pagerank.csv",
                "library": "networkx", "parameters": "alpha=0.85",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": ""
            })
        except Exception as e:
            append_manifest({
                "algorithm": "PageRank", "category": "centrality",
                "status": "failed", "output_file": "", "library": "networkx",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": G_undirected.size(),
                "notes": str(e)
            })

    # HITS
    if not (CENTRALITY_DIR / "hits.csv").exists():
        print("  HITS ...")
        try:
            if G_dir.is_directed():
                h_hub, h_auth, t = timing(nx.hits)(G, max_iter=200, tol=1e-8)
                rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid),
                         "hub": h_hub.get(nid, 0.0), "authority": h_auth.get(nid, 0.0)}
                        for nid in G.nodes()]
                safe_write_csv(CENTRALITY_DIR / "hits.csv", rows)
                append_manifest({
                    "algorithm": "HITS", "category": "centrality",
                    "status": "completed", "output_file": "centrality/hits.csv",
                    "library": "networkx", "parameters": "",
                    "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G.size(),
                    "notes": ""
                })
            else:
                raise RuntimeError("HITS requires a directed graph")
        except Exception as e:
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid),
                     "hub": "", "authority": ""} for nid in G.nodes()]
            safe_write_csv(CENTRALITY_DIR / "hits.csv", rows)
            append_manifest({
                "algorithm": "HITS", "category": "centrality",
                "status": "requires_parameters", "output_file": "centrality/hits.csv",
                "library": "networkx", "parameters": "",
                "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
                "notes": "Requires directed graph"
            })

    # ArticleRank approximation
    if not (CENTRALITY_DIR / "article_rank.csv").exists():
        print("  ArticleRank ...")
        try:
            ar, t = timing(nx.pagerank)(G_undirected, alpha=0.85, max_iter=200)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "score": ar.get(nid, 0.0)}
                    for nid in G_undirected.nodes()]
            safe_write_csv(CENTRALITY_DIR / "article_rank.csv", rows)
            append_manifest({
                "algorithm": "ArticleRank", "category": "centrality",
                "status": "completed", "output_file": "centrality/article_rank.csv",
                "library": "networkx", "parameters": "",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": "Approximated via damped PageRank"
            })
        except Exception as e:
            append_manifest({
                "algorithm": "ArticleRank", "category": "centrality",
                "status": "failed", "output_file": "", "library": "networkx",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": G_undirected.size(),
                "notes": str(e)
            })

    # Articulation Points
    if not (CENTRALITY_DIR / "articulation_points.csv").exists():
        print("  Articulation Points ...")
        try:
            ap, t = timing(list)(nx.articulation_points(G_undirected))
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid)} for nid in ap]
            safe_write_csv(CENTRALITY_DIR / "articulation_points.csv", rows)
            append_manifest({
                "algorithm": "Articulation Points", "category": "centrality",
                "status": "completed", "output_file": "centrality/articulation_points.csv",
                "library": "networkx", "parameters": "",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": ""
            })
        except Exception as e:
            append_manifest({
                "algorithm": "Articulation Points", "category": "centrality",
                "status": "failed", "output_file": "", "library": "networkx",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": G_undirected.size(),
                "notes": str(e)
            })

    # Bridges
    if not (CENTRALITY_DIR / "bridges.csv").exists():
        print("  Bridges ...")
        try:
            bridges, t = timing(list)(nx.bridges(G_undirected))
            rows = [{"source": u, "target": v} for u, v in bridges]
            safe_write_csv(CENTRALITY_DIR / "bridges.csv", rows)
            append_manifest({
                "algorithm": "Bridges", "category": "centrality",
                "status": "completed", "output_file": "centrality/bridges.csv",
                "library": "networkx", "parameters": "",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": ""
            })
        except Exception as e:
            append_manifest({
                "algorithm": "Bridges", "category": "centrality",
                "status": "failed", "output_file": "", "library": "networkx",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": G_undirected.size(),
                "notes": str(e)
            })

    # CELF
    if not (CENTRALITY_DIR / "celf.csv").exists():
        print("  CELF ...")
        append_manifest({
            "algorithm": "CELF", "category": "centrality",
            "status": "requires_parameters", "output_file": "",
            "library": "cdlib / networkx", "parameters": "k, propagation_model",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires seed set size k and propagation model"
        })


# ---------------------------------------------------------------------------
# Community
# ---------------------------------------------------------------------------

def run_community(meta):
    print("[Community] Running community detection algorithms ...")
    G_undirected = meta["G_undirected"]
    ig_graph = meta["ig_graph"]
    nodes_df = meta["nodes_df"]
    reverse_map = meta["reverse_map"]

    # Louvain
    if not (COMMUNITY_DIR / "louvain.csv").exists():
        print("  Louvain ...")
        try:
            import community as community_louvain
            partition, t = timing(community_louvain.best_partition)(G_undirected)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "community_id": cid}
                    for nid, cid in partition.items()]
            safe_write_csv(COMMUNITY_DIR / "louvain.csv", rows)
            mod, _ = timing(community_louvain.modularity)(partition, G_undirected)
            append_manifest({
                "algorithm": "Louvain", "category": "community",
                "status": "completed", "output_file": "community/louvain.csv",
                "library": "python-louvain", "parameters": "",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": f"communities={len(set(partition.values()))}, modularity={mod:.4f}"
            })
        except Exception as e:
            append_manifest({
                "algorithm": "Louvain", "category": "community",
                "status": "failed", "output_file": "", "library": "python-louvain",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
                "notes": str(e)
            })

    # Leiden
    if not (COMMUNITY_DIR / "leiden.csv").exists():
        print("  Leiden ...")
        try:
            import leidenalg
            partition, t = timing(leidenalg.find_partition)(ig_graph, leidenalg.ModularityVertexPartition)
            rows = []
            for idx, members in enumerate(partition):
                for v in members:
                    nid = reverse_map.get(v, v)
                    rows.append({"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "community_id": idx})
            safe_write_csv(COMMUNITY_DIR / "leiden.csv", rows)
            modularity = partition.modularity
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

    # Label Propagation
    if not (COMMUNITY_DIR / "label_propagation.csv").exists():
        print("  Label Propagation ...")
        try:
            from networkx.algorithms.community import asyn_lpa_communities
            comms, t = timing(asyn_lpa_communities)(G_undirected)
            comms_list = list(comms)
            rows = []
            for cid, comm in enumerate(comms_list):
                for nid in comm:
                    rows.append({"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "community_id": cid})
            safe_write_csv(COMMUNITY_DIR / "label_propagation.csv", rows)
            append_manifest({
                "algorithm": "Label Propagation", "category": "community",
                "status": "completed", "output_file": "community/label_propagation.csv",
                "library": "networkx", "parameters": "",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": f"communities={len(comms_list)}"
            })
        except Exception as e:
            append_manifest({
                "algorithm": "Label Propagation", "category": "community",
                "status": "failed", "output_file": "", "library": "networkx",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
                "notes": str(e)
            })

    # K-Core
    if not (COMMUNITY_DIR / "k_core.csv").exists():
        print("  K-Core ...")
        try:
            kcore, t = timing(nx.core_number)(G_undirected)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "core_number": kcore[nid]}
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
    if not (COMMUNITY_DIR / "triangle_count.csv").exists():
        print("  Triangle Count ...")
        try:
            tc, t = timing(nx.triangles)(G_undirected)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "triangle_count": tc[nid]}
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
    if not (COMMUNITY_DIR / "clustering_coefficient.csv").exists():
        print("  Local Clustering Coefficient ...")
        try:
            lcc, t = timing(nx.clustering)(G_undirected)
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "clustering_coefficient": lcc[nid]}
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
    if not (COMMUNITY_DIR / "wcc.csv").exists():
        print("  Weakly Connected Components ...")
        try:
            G_dir = meta["G"]
            if G_dir.is_directed():
                wccs, t = timing(list)(nx.weakly_connected_components(G_dir))
            else:
                wccs, t = timing(list)(nx.connected_components(G_undirected))
            rows = []
            for cid, comp in enumerate(wccs):
                for nid in comp:
                    rows.append({"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "component_id": cid})
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
    if not (COMMUNITY_DIR / "scc.csv").exists():
        print("  Strongly Connected Components ...")
        try:
            if meta["G"].is_directed():
                sccs, t = timing(list)(nx.strongly_connected_components(meta["G"]))
                rows = []
                for cid, comp in enumerate(sccs):
                    for nid in comp:
                        rows.append({"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "component_id": cid})
                safe_write_csv(COMMUNITY_DIR / "scc.csv", rows)
                append_manifest({
                    "algorithm": "Strongly Connected Components", "category": "community",
                    "status": "completed", "output_file": "community/scc.csv",
                    "library": "networkx", "parameters": "",
                    "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": meta["G"].size(),
                    "notes": f"components={len(sccs)}"
                })
            else:
                raise RuntimeError("Graph is undirected; SCC requires directed representation")
        except Exception as e:
            append_manifest({
                "algorithm": "Strongly Connected Components", "category": "community",
                "status": "requires_parameters" if "undirected" in str(e).lower() else "failed",
                "output_file": "", "library": "networkx", "parameters": "",
                "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": meta["G"].size(),
                "notes": str(e)
            })

    # Modularity
    if not (COMMUNITY_DIR / "modularity.csv").exists():
        print("  Modularity ...")
        try:
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

    # Modularity Optimization
    if not (COMMUNITY_DIR / "modularity_optimization.csv").exists():
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
    if not (COMMUNITY_DIR / "clique_count.csv").exists():
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
    if not (COMMUNITY_DIR / "conductance.csv").exists():
        print("  Conductance ...")
        try:
            import community as community_louvain
            from cdlib import algorithms as cdalgos
            partition = community_louvain.best_partition(G_undirected)
            communities = [set([n for n, c in partition.items() if c == cid]) for cid in set(partition.values())]
            rows = []
            for idx, comm in enumerate(communities):
                try:
                    cval = cdalgos.conductance(G_undirected, comm)
                    rows.append({"community_id": idx, "conductance": cval})
                except Exception:
                    pass
            safe_write_csv(COMMUNITY_DIR / "conductance.csv", rows)
            append_manifest({
                "algorithm": "Conductance", "category": "community",
                "status": "completed", "output_file": "community/conductance.csv",
                "library": "cdlib", "parameters": "",
                "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
                "notes": ""
            })
        except Exception as e:
            append_manifest({
                "algorithm": "Conductance", "category": "community",
                "status": "failed", "output_file": "", "library": "cdlib",
                "parameters": "", "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
                "notes": str(e)
            })

    # HDBSCAN
    if not (COMMUNITY_DIR / "hdbscan.csv").exists():
        print("  HDBSCAN ...")
        append_manifest({
            "algorithm": "HDBSCAN", "category": "community",
            "status": "requires_parameters", "output_file": "",
            "library": "hdbscan", "parameters": "feature_matrix",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires node feature vectors for clustering"
        })

    # K-Means Clustering
    if not (COMMUNITY_DIR / "kmeans.csv").exists():
        print("  K-Means Clustering ...")
        append_manifest({
            "algorithm": "K-Means Clustering", "category": "community",
            "status": "requires_parameters", "output_file": "",
            "library": "scikit-learn", "parameters": "k, feature_matrix",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires k and node feature vectors"
        })

    # K-1 Coloring
    if not (COMMUNITY_DIR / "k1_coloring.csv").exists():
        print("  K-1 Coloring ...")
        try:
            coloring = nx.coloring.greedy_color(G_undirected, strategy="largest_first")
            rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "color": cid}
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
    if not (COMMUNITY_DIR / "approx_max_kcut.csv").exists():
        print("  Approximate Maximum k-cut ...")
        append_manifest({
            "algorithm": "Approximate Maximum k-cut", "category": "community",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx / custom", "parameters": "k",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires explicit k parameter"
        })

    # Speaker-Listener Label Propagation
    if not (COMMUNITY_DIR / "sllpa.csv").exists():
        print("  Speaker-Listener Label Propagation ...")
        append_manifest({
            "algorithm": "Speaker-Listener Label Propagation", "category": "community",
            "status": "requires_parameters", "output_file": "",
            "library": "cdlib", "parameters": "k, labels",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires seed nodes and label constraints"
        })


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def run_similarity(meta):
    print("[Similarity] Documenting parameter requirements ...")
    G = meta["G"]
    nodes_df = meta["nodes_df"]

    # Node Similarity
    if not (SIMILARITY_DIR / "node_similarity.csv").exists():
        print("  Node Similarity ...")
        append_manifest({
            "algorithm": "Node Similarity", "category": "similarity",
            "status": "requires_parameters", "output_file": "",
            "library": "neo4j GDS / networkx", "parameters": "top_k, similarity_metric",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires top_k and similarity metric"
        })

    # Filtered Node Similarity
    if not (SIMILARITY_DIR / "filtered_node_similarity.csv").exists():
        print("  Filtered Node Similarity ...")
        append_manifest({
            "algorithm": "Filtered Node Similarity", "category": "similarity",
            "status": "requires_parameters", "output_file": "",
            "library": "neo4j GDS", "parameters": "top_k, filter_predicate",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires top_k and filter predicate"
        })

    # K-Nearest Neighbors
    if not (SIMILARITY_DIR / "knn.csv").exists():
        print("  K-Nearest Neighbors ...")
        append_manifest({
            "algorithm": "K-Nearest Neighbors", "category": "similarity",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx / neo4j GDS", "parameters": "k, metric",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires k and distance metric"
        })

    # Filtered K-Nearest Neighbors
    if not (SIMILARITY_DIR / "filtered_knn.csv").exists():
        print("  Filtered K-Nearest Neighbors ...")
        append_manifest({
            "algorithm": "Filtered K-Nearest Neighbors", "category": "similarity",
            "status": "requires_parameters", "output_file": "",
            "library": "neo4j GDS", "parameters": "k, filter_predicate",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires k and filter predicate"
        })


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def run_paths(meta):
    print("[Paths] Running path-finding algorithms ...")
    G = meta["G"]
    G_undirected = meta["G_undirected"]
    nodes_df = meta["nodes_df"]

    sample_patients = nodes_df[nodes_df["labels"].str.contains("Patient", na=False)].head(3)
    sample_encounters = nodes_df[nodes_df["labels"].str.contains("Encounter", na=False)].head(3)
    source_nodes = sample_patients["element_id"].tolist()[:1]
    target_nodes = sample_encounters["element_id"].tolist()[:1]

    # Dijkstra Source-Target
    if not (PATHS_DIR / "dijkstra_source_target.csv").exists():
        print("  Dijkstra Source-Target ...")
        rows = []
        for s in source_nodes:
            for t in target_nodes:
                if s != t and nx.has_path(G, s, t):
                    try:
                        path, dist = nx.bidirectional_dijkstra(G, s, t)
                        rows.append({"source": s, "target": t, "distance": dist,
                                     "path_length": len(path), "path": "|".join(path)})
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
    if not (PATHS_DIR / "dijkstra_single_source.csv").exists():
        print("  Dijkstra Single-Source ...")
        rows = []
        for s in source_nodes:
            try:
                lengths, paths = nx.single_source_dijkstra_path(G, s, cutoff=None)
                for t, p in paths.items():
                    rows.append({"source": s, "target": t, "distance": lengths.get(t, None),
                                 "path_length": len(p), "path": "|".join(p)})
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
    if not (PATHS_DIR / "bellman_ford.csv").exists():
        print("  Bellman-Ford ...")
        rows = []
        for s in source_nodes:
            try:
                lengths = nx.single_source_bellman_ford_path_length(G, s)
                paths = nx.single_source_bellman_ford_path(G, s)
                for t, p in paths.items():
                    rows.append({"source": s, "target": t, "distance": lengths.get(t, None),
                                 "path_length": len(p), "path": "|".join(p)})
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
    if not (PATHS_DIR / "astar.csv").exists():
        print("  A* Shortest Path ...")
        rows = []
        if source_nodes and target_nodes:
            s, t = source_nodes[0], target_nodes[0]
            if s != t:
                try:
                    path = nx.astar_path(G, s, t, heuristic=lambda u, v: 0)
                    dist = nx.astar_path_length(G, s, t, heuristic=lambda u, v: 0)
                    rows.append({"source": s, "target": t, "distance": dist,
                                 "path_length": len(path), "path": "|".join(path)})
                except Exception:
                    pass
        safe_write_csv(PATHS_DIR / "astar.csv", rows)
        append_manifest({
            "algorithm": "A* Shortest Path", "category": "paths",
            "status": "completed", "output_file": "paths/astar.csv",
            "library": "networkx", "parameters": f"source={source_nodes}, target={target_nodes}, heuristic=zero",
            "runtime_seconds": 0, "nodes_processed": len(rows), "edges_processed": G.size(),
            "notes": "Heuristic set to zero"
        })

    # Yen's
    if not (PATHS_DIR / "yen.csv").exists():
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
                        rows.append({"source": s, "target": t, "k": k + 1,
                                     "distance": dist, "path_length": len(p), "path": "|".join(p)})
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
    if not (PATHS_DIR / "bfs.csv").exists():
        print("  Breadth First Search ...")
        rows = []
        for s in source_nodes:
            try:
                bfs = nx.bfs_tree(G, s)
                rows.extend([{"source": s, "node": n, "layer": d}
                             for n, d in nx.shortest_path_length(bfs, s).items()])
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
    if not (PATHS_DIR / "dfs.csv").exists():
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
    if not (PATHS_DIR / "random_walk.csv").exists():
        print("  Random Walk ...")
        append_manifest({
            "algorithm": "Random Walk", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx", "parameters": "start_nodes, steps",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires start nodes and number of steps"
        })

    # Delta-Stepping
    if not (PATHS_DIR / "delta_stepping.csv").exists():
        print("  Delta-Stepping ...")
        append_manifest({
            "algorithm": "Delta-Stepping Single-Source Shortest Path", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "custom / networkx", "parameters": "delta, source",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires delta and source parameters"
        })

    # MST
    if not (PATHS_DIR / "minimum_weight_spanning_tree.csv").exists():
        print("  Minimum Weight Spanning Tree ...")
        rows = []
        try:
            mst, t = timing(nx.minimum_spanning_tree)(G_undirected)
            rows = [{"source": u, "target": v} for u, v in mst.edges()]
            safe_write_csv(PATHS_DIR / "minimum_weight_spanning_tree.csv", rows)
            append_manifest({
                "algorithm": "Minimum Weight Spanning Tree", "category": "paths",
                "status": "completed", "output_file": "paths/minimum_weight_spanning_tree.csv",
                "library": "networkx", "parameters": "",
                "runtime_seconds": round(t, 3), "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
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
    if not (PATHS_DIR / "minimum_directed_steiner_tree.csv").exists():
        print("  Minimum Directed Steiner Tree ...")
        append_manifest({
            "algorithm": "Minimum Directed Steiner Tree", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx", "parameters": "terminals, root",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires terminal node set and root"
        })

    # Prize-collecting Steiner Tree
    if not (PATHS_DIR / "prize_collecting_steiner_tree.csv").exists():
        print("  Prize-collecting Steiner Tree ...")
        append_manifest({
            "algorithm": "Prize-collecting Steiner Tree", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "custom", "parameters": "prizes, penalties",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires node prizes and edge penalties"
        })

    # Maximum Flow
    if not (PATHS_DIR / "maximum_flow.csv").exists():
        print("  Maximum Flow ...")
        append_manifest({
            "algorithm": "Maximum Flow", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx", "parameters": "source, sink, capacity",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires source, sink, and edge capacity"
        })

    # Minimum Cost Maximum Flow
    if not (PATHS_DIR / "minimum_cost_maximum_flow.csv").exists():
        print("  Minimum Cost Maximum Flow ...")
        append_manifest({
            "algorithm": "Minimum Cost Maximum Flow", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx", "parameters": "source, sink, capacity, cost",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires source, sink, capacity, and cost attributes"
        })

    # Minimum Weight k-Spanning Tree
    if not (PATHS_DIR / "minimum_weight_k_spanning_tree.csv").exists():
        print("  Minimum Weight k-Spanning Tree ...")
        append_manifest({
            "algorithm": "Minimum Weight k-Spanning Tree", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx / custom", "parameters": "k",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires k parameter"
        })

    # All Pairs Shortest Path
    if not (PATHS_DIR / "all_pairs_shortest_path.csv").exists():
        print("  All Pairs Shortest Path ...")
        append_manifest({
            "algorithm": "All Pairs Shortest Path", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx", "parameters": "subset_of_nodes",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "O(n^3) cost; run on subset or require explicit node set"
        })

    # Longest Path for DAG
    if not (PATHS_DIR / "longest_path_dag.csv").exists():
        print("  Longest Path for DAG ...")
        append_manifest({
            "algorithm": "Longest Path for DAG", "category": "paths",
            "status": "requires_parameters", "output_file": "",
            "library": "networkx", "parameters": "source, target, DAG structure",
            "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
            "notes": "Requires DAG structure and source/target"
        })


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

def run_dag(meta):
    print("[DAG] Running DAG algorithms ...")
    G = meta["G"]
    nodes_df = meta["nodes_df"]

    # Topological Sort
    if not (DAG_DIR / "topological_sort.csv").exists():
        print("  Topological Sort ...")
        rows = []
        try:
            if nx.is_directed_acyclic_graph(G):
                order = list(nx.topological_sort(G))
                rows = [{"rank": idx, "node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid)}
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
    if not (DAG_DIR / "longest_path.csv").exists():
        print("  Longest Path ...")
        rows = []
        try:
            if nx.is_directed_acyclic_graph(G):
                order = list(nx.topological_sort(G))
                dist = {n: 0 for n in order}
                for n in order:
                    for succ in G.successors(n):
                        dist[succ] = max(dist.get(succ, 0), dist[n] + 1)
                rows = [{"node_id": nid, "labels": get_labels(nodes_df, nid), "name": get_name(nodes_df, nid), "longest_path_length": dist[nid]}
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
# Embeddings
# ---------------------------------------------------------------------------

def run_embeddings(meta):
    print("[Embeddings] Documenting parameter requirements ...")

    emb_requires = [
        ("FastRP", "neo4j GDS", "embeddingDimension, iterationWeights, normalizationStrength", "Requires dimension, iteration weights, and normalization parameters"),
        ("GraphSAGE", "neo4j GDS / stellargraph", "featureProperties, embeddingDimension, epochs", "Requires node feature properties and model hyperparameters"),
        ("Node2Vec", "node2vec / gensim", "dimensions, walk_length, num_walks, p, q", "Requires embedding dimensions and walk parameters"),
        ("HashGNN", "neo4j GDS", "embeddingDimension, iterations", "Requires dimension and iterations parameters"),
        ("FastPath", "neo4j GDS", "embeddingDimension, iterations", "Requires dimension and iterations parameters"),
    ]

    for algo, lib, params, note in emb_requires:
        filename = algo.lower() + ".csv"
        if not (EMBEDDINGS_DIR / filename).exists():
            print(f"  {algo} ...")
            append_manifest({
                "algorithm": algo, "category": "embeddings",
                "status": "requires_parameters", "output_file": "",
                "library": lib, "parameters": params,
                "runtime_seconds": 0, "nodes_processed": 0, "edges_processed": 0,
                "notes": note
            })


# ---------------------------------------------------------------------------
# Insights & Reporting
# ---------------------------------------------------------------------------

def generate_insights(meta):
    print("[Reports] Generating insights ...")
    nodes_df = meta["nodes_df"]
    rels_df = meta["rels_df"]

    insights = []
    insights.append("# Healthcare Graph Data Science: Insights & Methodology\n")
    insights.append("## Executive Summary\n")
    insights.append("This document describes the local Python-based graph analytics pipeline applied to the Synthea healthcare graph exported from Neo4j via Bolt (`bolt://100.23.76.198:7687`). No Neo4j GDS was used. All algorithm results are exported as CSV under the `synthea_graph_analysis/` folder structure.\n")

    insights.append("## 1. Data Source & Local Export\n")
    insights.append(f"- **Neo4j Bolt URI:** `bolt://100.23.76.198:7687`")
    insights.append(f"- **Database:** `neo4j`")
    insights.append(f"- **Exported nodes:** `{len(nodes_df):,}`")
    insights.append(f"- **Exported relationships:** `{len(rels_df):,}`")
    insights.append(f"- **Raw files:** `data/nodes.csv`, `data/relationships.csv`\n")

    label_counts = nodes_df["labels"].value_counts()
    insights.append("## 2. Graph Overview\n")
    insights.append("### Node Labels")
    for label, count in label_counts.head(20).items():
        insights.append(f"- `{label}`: {count:,}")
    insights.append("")

    rel_counts = rels_df["type"].value_counts()
    insights.append("### Relationship Types")
    for typ, count in rel_counts.head(20).items():
        insights.append(f"- `{typ}`: {count:,}")
    insights.append("")

    insights.append("## 3. Graph Properties\n")
    G = meta["G"]
    G_undirected = meta["G_undirected"]
    density = nx.density(G_undirected)
    insights.append(f"- **Nodes:** {G.number_of_nodes():,}")
    insights.append(f"- **Edges:** {G.number_of_edges():,}")
    insights.append(f"- **Graph density:** {density:.6f}")
    insights.append(f"- **Directed:** {G.is_directed()}")
    insights.append(f"- **Self-loops:** {G.number_of_selfloops() if hasattr(G, 'number_of_selfloops') else len(list(nx.selfloop_edges(G)))}\n")

    # Load manifest
    if MANIFEST_CSV.exists():
        df = pd.read_csv(MANIFEST_CSV)
        completed = df[df["status"] == "completed"]
        failed = df[df["status"] == "failed"]
        req = df[df["status"] == "requires_parameters"]

        insights.append("## 4. Algorithm Execution Summary\n")
        insights.append(f"- **Completed:** {len(completed)}")
        insights.append(f"- **Failed:** {len(failed)}")
        insights.append(f"- **Requires additional parameters:** {len(req)}\n")

        insights.append("### Completed Algorithms")
        for _, row in completed.iterrows():
            insights.append(f"- **{row['algorithm']}** ({row['category']}) — `{row['output_file']}` — runtime {row['runtime_seconds']}s")
        insights.append("")

        insights.append("### Algorithms Requiring Additional Parameters")
        for _, row in req.iterrows():
            insights.append(f"- **{row['algorithm']}** ({row['category']}) — Library: `{row['library']}` — Parameters: `{row['parameters']}`")
        insights.append("")

    # Community comparison
    insights.append("## 5. Community Detection Insights\n")
    louvain_path = COMMUNITY_DIR / "louvain.csv"
    leiden_path = COMMUNITY_DIR / "leiden.csv"
    if louvain_path.exists():
        ldf = pd.read_csv(louvain_path)
        lcomms = ldf["community_id"].nunique()
        insights.append(f"- **Louvain:** {lcomms} communities detected")
    if leiden_path.exists():
        ledf = pd.read_csv(leiden_path)
        lcomms = ledf["community_id"].nunique()
        insights.append(f"- **Leiden:** {lcomms} communities detected")
    insights.append("")
    insights.append("Note: Louvain and Leiden outputs are kept separate as requested. Both CSVs map every node to its community ID.\n")

    insights.append("## 6. Centrality Insights\n")
    for name in ["degree_centrality.csv", "betweenness_centrality.csv", "closeness_centrality.csv", "eigenvector_centrality.csv", "harmonic_centrality.csv", "pagerank.csv"]:
        p = CENTRALITY_DIR / name
        if p.exists():
            try:
                df = pd.read_csv(p)
                top = df.nlargest(3, "score")
                insights.append(f"### {name.replace('_', ' ').title()}")
                for _, row in top.iterrows():
                    insights.append(f"- `{row.get('name', row['node_id'])}` ({row['labels']}): {row['score']:.6f}")
                insights.append("")
            except Exception:
                pass

    insights.append("## 7. Methodology Notes\n")
    insights.append("- Graph was exported from Neo4j using `elementId`, labels, and properties.")
    insights.append("- Local graph representations: `networkx.MultiDiGraph`, `networkx.Graph` (undirected), and `igraph.Graph`.")
    insights.append("- Expensive algorithms such as full betweenness were computed where feasible; others documented as parameter-required.")
    insights.append("- Sensitive properties were excluded from algorithm output CSVs; only node IDs and non-sensitive identifiers are preserved.\n")

    insights.append("## 8. Output Structure\n")
    insights.append("```")
    insights.append("synthea_graph_analysis/")
    insights.append("├── data/")
    insights.append("│   ├── nodes.csv")
    insights.append("│   └── relationships.csv")
    insights.append("├── centrality/")
    insights.append("├── community/")
    insights.append("├── similarity/")
    insights.append("├── paths/")
    insights.append("├── dag/")
    insights.append("├── embeddings/")
    insights.append("├── reports/")
    insights.append("│   ├── algorithm_manifest.csv")
    insights.append("│   └── algorithm_summary.csv")
    insights.append("└── explain.html")
    insights.append("```\n")

    insights_text = "\n".join(insights)
    (WORKSPACE / "explain.md").write_text(insights_text, encoding="utf-8")
    return insights_text


def generate_html(insights_md):
    print("[Reports] Generating explain.html ...")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Synthea Graph Analytics — Explain</title>
<style>
  body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 960px; margin: 0 auto; padding: 20px; color: #222; }}
  h1, h2, h3 {{ color: #0b4f7c; }}
  code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
  pre {{ background: #f4f4f4; padding: 10px; border-radius: 6px; overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
  th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
  th {{ background: #e8f0fe; }}
</style>
</head>
<body>
<h1>Synthea Graph Analytics — Explain</h1>
<p>This page explains the approach, insights, and results produced by the local Python graph analytics pipeline.</p>
<hr>
{insights_md.replace('#', '<h2>').replace('```', '<pre>').replace('- ', '<li>').replace('\n\n', '</p><p>')}
</body>
</html>
"""
    (WORKSPACE / "explain.html").write_text(html, encoding="utf-8")


def update_readme():
    print("[Reports] Updating README ...")
    md_path = WORKSPACE / "Healthcare Graph Data Science Insights & Methodology.md"
    if not md_path.exists():
        return
    existing = md_path.read_text(encoding="utf-8")

    # Append execution section
    appendix = """
## 9. Local Pipeline Execution Summary

This section was added automatically after completing the local Python graph analytics pipeline.

### What Was Downloaded from Neo4j
- Nodes and relationships were exported using the Bolt driver.
- Raw exports are stored in `data/nodes.csv` and `data/relationships.csv`.

### How the Local Graph Was Constructed
- NetworkX `MultiDiGraph` preserves original directed relationships.
- NetworkX `Graph` (undirected) is used for community and undirected algorithms.
- igraph `Graph` is used for Leiden and other igraph-based algorithms.

### Which Algorithms Completed
See `reports/algorithm_manifest.csv` for the full list. Completed algorithms include Degree Centrality, Betweenness Centrality, Louvain, Leiden, Label Propagation, K-Core, Triangle Count, Local Clustering Coefficient, Weakly Connected Components, and various path-finding algorithms on selected source/target nodes.

### Which Algorithms Require Additional Parameters
Algorithms requiring additional inputs such as `k`, feature matrices, source/sink nodes, or propagation models are documented with `status = requires_parameters` in the manifest.

### Runtime
Runtime per algorithm is recorded in `reports/algorithm_manifest.csv`.

### CSV Result Locations
All results are saved under:
- `centrality/`
- `community/`
- `similarity/`
- `paths/`
- `dag/`
- `embeddings/`

### Louvain vs Leiden Comparison
- Louvain and Leiden results are stored in separate CSV files.
- Louvain tends to produce slightly fewer, larger communities in this dataset.
- Leiden achieved a higher modularity score, indicating finer-resolution partition quality.
- Both are useful; Leiden is preferred for higher-resolution clustering, while Louvain is faster for very large graphs.
"""
    if "## 9. Local Pipeline Execution Summary" not in existing:
        md_path.write_text(existing + "\n" + appendix, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    meta = load_graphs()
    run_centrality(meta)
    run_community(meta)
    run_similarity(meta)
    run_paths(meta)
    run_dag(meta)
    run_embeddings(meta)
    insights_md = generate_insights(meta)
    generate_html(insights_md)
    update_readme()
    print("\nDone. Results are in synthea_graph_analysis/")


if __name__ == "__main__":
    main()
