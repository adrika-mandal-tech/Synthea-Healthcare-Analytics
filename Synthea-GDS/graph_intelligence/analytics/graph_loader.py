"""
Graph Intelligence Platform — Graph Loading Module

Refactored from pipeline.py:load_graphs() with caching and reusable interfaces.
Provides NetworkX MultiDiGraph, Undirected Graph, igraph, and relationship-type subgraphs.
"""

import os
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from functools import lru_cache
import pickle

import networkx as nx
import igraph as ig
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).parent.parent.parent
DATA_DIR = WORKSPACE / "data"
CENTRALITY_DIR = WORKSPACE / "centrality"
COMMUNITY_DIR = WORKSPACE / "community"
SIMILARITY_DIR = WORKSPACE / "similarity"
PATHS_DIR = WORKSPACE / "paths"
DAG_DIR = WORKSPACE / "dag"
EMBEDDINGS_DIR = WORKSPACE / "embeddings"
REPORTS_DIR = WORKSPACE / "reports"

NODES_CSV = DATA_DIR / "nodes.csv"
RELS_CSV = DATA_DIR / "relationships.csv"

# Cache directory for pickled graphs
CACHE_DIR = WORKSPACE / ".graph_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_CACHE_FILE = CACHE_DIR / "graphs.pkl"
NODE_ID_MAP_CACHE = CACHE_DIR / "node_id_map.pkl"
REVERSE_MAP_CACHE = CACHE_DIR / "reverse_map.pkl"
RELS_BY_TYPE_CACHE = CACHE_DIR / "rels_by_type.pkl"

# ---------------------------------------------------------------------------
# Core Graph Loading
# ---------------------------------------------------------------------------

def load_nodes_df() -> pd.DataFrame:
    """Load nodes CSV with optimized dtypes."""
    return pd.read_csv(NODES_CSV, low_memory=False)


def load_relationships_df() -> pd.DataFrame:
    """Load relationships CSV with optimized dtypes."""
    return pd.read_csv(RELS_CSV, low_memory=False)


def build_node_mappings(nodes_df: pd.DataFrame) -> Tuple[Dict[str, int], Dict[int, str]]:
    """Create bidirectional mapping between node_id (str) and integer index."""
    node_ids = nodes_df["element_id"].tolist()
    node_id_map = {nid: idx for idx, nid in enumerate(node_ids)}
    reverse_map = {idx: nid for idx, nid in enumerate(node_ids)}
    return node_id_map, reverse_map


def build_networkx_graphs(nodes_df: pd.DataFrame, rels_df: pd.DataFrame,
                          node_id_map: Dict[str, int]) -> Tuple[nx.MultiDiGraph, nx.Graph]:
    """Build NetworkX MultiDiGraph (directed) and undirected Graph."""
    print("  Building NetworkX graphs...")

    G = nx.MultiDiGraph()
    G_undirected = nx.Graph()

    # Add nodes
    for _, row in nodes_df.iterrows():
        nid = row["element_id"]
        labels = row.get("labels", "")
        name = row.get("name", "") or row.get("NAME", "") or row.get("Id", "") or ""
        G.add_node(nid, labels=labels, name=name)
        G_undirected.add_node(nid, labels=labels, name=name)

    # Add edges - handle different column names
    src_col = "source_element_id" if "source_element_id" in rels_df.columns else "source"
    dst_col = "target_element_id" if "target_element_id" in rels_df.columns else "target"
    type_col = "type" if "type" in rels_df.columns else ("relationship_type" if "relationship_type" in rels_df.columns else "")

    for _, row in rels_df.iterrows():
        src = row[src_col]
        dst = row[dst_col]
        rel_type = row.get(type_col, "") if type_col else ""
        props = {k: v for k, v in row.items() if k not in [src_col, dst_col, type_col]}

        if src in node_id_map and dst in node_id_map:
            G.add_edge(src, dst, type=rel_type, **props)
            G_undirected.add_edge(src, dst, type=rel_type, **props)

    print(f"    Directed: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"    Undirected: {G_undirected.number_of_nodes()} nodes, {G_undirected.number_of_edges()} edges")

    return G, G_undirected


def build_igraph_graph(nodes_df: pd.DataFrame, rels_df: pd.DataFrame,
                       node_id_map: Dict[str, int]) -> ig.Graph:
    """Build igraph Graph for efficient community detection."""
    print("  Building igraph...")

    n_nodes = len(nodes_df)
    edges = []

    src_col = "source_element_id" if "source_element_id" in rels_df.columns else "source"
    dst_col = "target_element_id" if "target_element_id" in rels_df.columns else "target"

    for _, row in rels_df.iterrows():
        src = row[src_col]
        dst = row[dst_col]
        if src in node_id_map and dst in node_id_map:
            edges.append((node_id_map[src], node_id_map[dst]))

    ig_graph = ig.Graph(n=n_nodes, edges=edges, directed=True)

    # Add vertex attributes
    ig_graph.vs["element_id"] = nodes_df["element_id"].tolist()
    ig_graph.vs["labels"] = nodes_df.get("labels", pd.Series([""] * n_nodes)).tolist()
    name_col = "name" if "name" in nodes_df.columns else ("NAME" if "NAME" in nodes_df.columns else ("Id" if "Id" in nodes_df.columns else None))
    if name_col:
        ig_graph.vs["name"] = nodes_df[name_col].fillna("").tolist()
    else:
        ig_graph.vs["name"] = [""] * n_nodes

    # Add edge attributes
    ig_graph.es["type"] = rels_df["type"].tolist()[:len(edges)]

    print(f"    igraph: {ig_graph.vcount()} vertices, {ig_graph.ecount()} edges")

    return ig_graph


def build_relationship_subgraphs(rels_df: pd.DataFrame, node_id_map: Dict[str, int]
                                 ) -> Dict[str, nx.Graph]:
    """Build undirected subgraph per relationship type."""
    print("  Building relationship-type subgraphs...")

    src_col = "source_element_id" if "source_element_id" in rels_df.columns else "source"
    dst_col = "target_element_id" if "target_element_id" in rels_df.columns else "target"
    type_col = "type" if "type" in rels_df.columns else ("relationship_type" if "relationship_type" in rels_df.columns else "")

    rel_types = rels_df[type_col].unique() if type_col else []
    subgraphs = {}

    for rel_type in rel_types:
        G_sub = nx.Graph()

        # Add all nodes first
        for _, row in node_id_map.items():
            G_sub.add_node(row)

        type_edges = rels_df[rels_df[type_col] == rel_type]
        for _, row in type_edges.iterrows():
            src = row[src_col]
            dst = row[dst_col]
            if src in node_id_map and dst in node_id_map:
                G_sub.add_edge(src, dst)

        # Remove isolated nodes
        G_sub.remove_nodes_from(list(nx.isolates(G_sub)))

        if G_sub.number_of_edges() > 0:
            subgraphs[rel_type] = G_sub
            print(f"    {rel_type}: {G_sub.number_of_nodes()} nodes, {G_sub.number_of_edges()} edges")

    return subgraphs


def load_or_build_graphs(force_rebuild: bool = False) -> Dict[str, Any]:
    """
    Load cached graphs or build from CSV.

    Returns dict with:
    - nodes_df, rels_df: DataFrames
    - G: nx.MultiDiGraph (directed)
    - G_undirected: nx.Graph (undirected)
    - ig_graph: igraph.Graph
    - node_id_map: str -> int
    - reverse_map: int -> str
    - subgraphs: dict of nx.Graph per relationship type
    """

    # Check cache
    if not force_rebuild and GRAPH_CACHE_FILE.exists():
        print("Loading graphs from cache...")
        with open(GRAPH_CACHE_FILE, "rb") as f:
            cache = pickle.load(f)
        print(f"  Loaded: {cache['G'].number_of_nodes()} nodes, {cache['G'].number_of_edges()} edges")
        return cache

    print("Building graphs from CSV...")

    # Load data
    nodes_df = load_nodes_df()
    rels_df = load_relationships_df()

    # Build mappings
    node_id_map, reverse_map = build_node_mappings(nodes_df)

    # Save mappings
    with open(NODE_ID_MAP_CACHE, "wb") as f:
        pickle.dump(node_id_map, f)
    with open(REVERSE_MAP_CACHE, "wb") as f:
        pickle.dump(reverse_map, f)

    # Build graphs
    G, G_undirected = build_networkx_graphs(nodes_df, rels_df, node_id_map)
    ig_graph = build_igraph_graph(nodes_df, rels_df, node_id_map)
    subgraphs = build_relationship_subgraphs(rels_df, node_id_map)

    # Save relationship-type edges for subgraphs
    with open(RELS_BY_TYPE_CACHE, "wb") as f:
        pickle.dump(subgraphs, f)

    # Cache everything
    cache = {
        "nodes_df": nodes_df,
        "rels_df": rels_df,
        "G": G,
        "G_undirected": G_undirected,
        "ig_graph": ig_graph,
        "node_id_map": node_id_map,
        "reverse_map": reverse_map,
        "subgraphs": subgraphs,
    }

    with open(GRAPH_CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)

    print("Graphs cached successfully.")

    return cache


def load_subgraphs() -> Dict[str, nx.Graph]:
    """Load just the relationship-type subgraphs from cache."""
    if RELS_BY_TYPE_CACHE.exists():
        with open(RELS_BY_TYPE_CACHE, "rb") as f:
            return pickle.load(f)
    # Fallback: build full graphs
    return load_or_build_graphs()["subgraphs"]


def get_node_labels(nodes_df: pd.DataFrame, node_id: str) -> str:
    """Get labels for a node_id."""
    row = nodes_df[nodes_df["element_id"] == node_id]
    if row.empty:
        return ""
    return row.iloc[0].get("labels", "")


def get_node_name(nodes_df: pd.DataFrame, node_id: str) -> str:
    """Get display name for a node_id."""
    row = nodes_df[nodes_df["element_id"] == node_id]
    if row.empty:
        return ""
    return (row.iloc[0].get("name", "") or
            row.iloc[0].get("NAME", "") or
            row.iloc[0].get("Id", "") or "")


def clear_cache():
    """Remove all cached graph files."""
    for f in [GRAPH_CACHE_FILE, NODE_ID_MAP_CACHE, REVERSE_MAP_CACHE, RELS_BY_TYPE_CACHE]:
        if f.exists():
            f.unlink()
    print("Graph cache cleared.")


# ---------------------------------------------------------------------------
# Singleton Access (for app-wide reuse)
# ---------------------------------------------------------------------------

_graphs_cache: Optional[Dict[str, Any]] = None


def get_graphs(force_rebuild: bool = False) -> Dict[str, Any]:
    """Get singleton graph cache for the application."""
    global _graphs_cache
    if _graphs_cache is None or force_rebuild:
        _graphs_cache = load_or_build_graphs(force_rebuild=force_rebuild)
    return _graphs_cache


def get_nodes_df() -> pd.DataFrame:
    """Get nodes DataFrame from singleton cache."""
    return get_graphs()["nodes_df"]


def get_rels_df() -> pd.DataFrame:
    """Get relationships DataFrame from singleton cache."""
    return get_graphs()["rels_df"]


def get_directed_graph() -> nx.MultiDiGraph:
    """Get directed MultiDiGraph from singleton cache."""
    return get_graphs()["G"]


def get_undirected_graph() -> nx.Graph:
    """Get undirected Graph from singleton cache."""
    return get_graphs()["G_undirected"]


def get_igraph() -> ig.Graph:
    """Get igraph from singleton cache."""
    return get_graphs()["ig_graph"]


def get_node_id_map() -> Dict[str, int]:
    """Get node_id -> index mapping."""
    return get_graphs()["node_id_map"]


def get_reverse_map() -> Dict[int, str]:
    """Get index -> node_id mapping."""
    return get_graphs()["reverse_map"]


def get_subgraphs() -> Dict[str, nx.Graph]:
    """Get relationship-type subgraphs."""
    return get_graphs()["subgraphs"]


# ---------------------------------------------------------------------------
# Graph Statistics
# ---------------------------------------------------------------------------

def get_graph_statistics() -> Dict[str, Any]:
    """Compute basic graph statistics."""
    graphs = get_graphs()
    G = graphs["G"]
    G_undirected = graphs["G_undirected"]
    nodes_df = graphs["nodes_df"]
    rels_df = graphs["rels_df"]

    # Degree stats
    degrees = dict(G_undirected.degree())
    degree_values = list(degrees.values())

    # Label distribution
    label_counts = nodes_df["labels"].value_counts().to_dict()

    # Relationship type distribution
    rel_type_counts = rels_df["type"].value_counts().to_dict()

    # Connected components
    n_components = nx.number_connected_components(G_undirected)
    largest_cc = max(nx.connected_components(G_undirected), key=len)

    stats = {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "undirected_edge_count": G_undirected.number_of_edges(),
        "density": nx.density(G_undirected),
        "avg_degree": np.mean(degree_values) if degree_values else 0,
        "max_degree": max(degree_values) if degree_values else 0,
        "min_degree": min(degree_values) if degree_values else 0,
        "connected_components": n_components,
        "largest_component_size": len(largest_cc),
        "is_connected": n_components == 1,
        "label_distribution": label_counts,
        "relationship_type_distribution": rel_type_counts,
        "unique_labels": nodes_df["labels"].nunique(),
        "unique_relationship_types": rels_df["type"].nunique(),
    }

    return stats