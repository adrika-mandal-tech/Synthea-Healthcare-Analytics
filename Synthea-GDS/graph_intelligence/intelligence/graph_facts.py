"""
Graph Intelligence Platform — Unified Entity Fact Table

Joins all 55 analytics CSV outputs into a single per-entity fact table.
Each row = one node with all available metrics.
"""

import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).parent.parent.parent
CENTRALITY_DIR = WORKSPACE / "centrality"
COMMUNITY_DIR = WORKSPACE / "community"
SIMILARITY_DIR = WORKSPACE / "similarity"
PATHS_DIR = WORKSPACE / "paths"
DAG_DIR = WORKSPACE / "dag"
EMBEDDINGS_DIR = WORKSPACE / "embeddings"
DATA_DIR = WORKSPACE / "data"

FACT_TABLE_CACHE = WORKSPACE / ".graph_cache" / "entity_facts.parquet"
FACT_TABLE_CSV = WORKSPACE / ".graph_cache" / "entity_facts.csv"

# ---------------------------------------------------------------------------
# CSV Loading Helpers
# ---------------------------------------------------------------------------

CENTRALITY_FILES = {
    "degree_centrality": "degree_centrality.csv",
    "betweenness_centrality": "betweenness_centrality.csv",
    "closeness_centrality": "closeness_centrality.csv",
    "eigenvector_centrality": "eigenvector_centrality.csv",
    "harmonic_centrality": "harmonic_centrality.csv",
    "pagerank": "pagerank.csv",
    "article_rank": "article_rank.csv",
    "hits": "hits.csv",
}

COMMUNITY_FILES = {
    "leiden": "leiden.csv",
    "louvain": "louvain.csv",
    "label_propagation": "label_propagation.csv",
    "sllpa": "sllpa.csv",
    "k_core": "k_core.csv",
    "kmeans": "kmeans.csv",
    "k1_coloring": "k1_coloring.csv",
    "clustering_coefficient": "clustering_coefficient.csv",
    "triangle_count": "triangle_count.csv",
}

EMBEDDING_FILES = {
    "node2vec": "node2vec.csv",
    "fastrp": "fastrp.csv",
    "graphsage": "graphsage.csv",
    "hashgnn": "hashgnn.csv",
    "fastpath": "fastpath.csv",
}

ARTICULATION_FILE = "articulation_points.csv"
BRIDGES_FILE = "bridges.csv"


def load_centrality_csv(filename: str, metric_name: str) -> pd.DataFrame:
    """Load a centrality CSV and rename score column."""
    path = CENTRALITY_DIR / filename
    if not path.exists():
        print(f"  Warning: {path} not found")
        return pd.DataFrame(columns=["node_id", metric_name])

    df = pd.read_csv(path)
    # Standardize columns
    if "score" in df.columns:
        df = df.rename(columns={"score": metric_name})
    elif "hub" in df.columns and "authority" in df.columns:
        # HITS has two scores (hub, authority)
        df = df.rename(columns={"hub": f"{metric_name}_hub",
                                 "authority": f"{metric_name}_authority"})

    # Determine which columns to return
    if metric_name in df.columns:
        return df[["node_id", metric_name]]
    elif f"{metric_name}_hub" in df.columns and f"{metric_name}_authority" in df.columns:
        return df[["node_id", f"{metric_name}_hub", f"{metric_name}_authority"]]
    else:
        # Fallback: return node_id and any score-like column
        score_cols = [c for c in df.columns if c not in ["node_id", "labels", "name"]]
        if score_cols:
            return df[["node_id"] + score_cols]
        return df[["node_id"]]


def load_community_csv(filename: str, metric_name: str) -> pd.DataFrame:
    """Load a community CSV and rename community_id column."""
    path = COMMUNITY_DIR / filename
    if not path.exists():
        print(f"  Warning: {path} not found")
        return pd.DataFrame(columns=["node_id", metric_name])

    df = pd.read_csv(path)
    if "community_id" in df.columns:
        df = df.rename(columns={"community_id": metric_name})
    elif "core_number" in df.columns:
        df = df.rename(columns={"core_number": metric_name})
    elif "cluster_id" in df.columns:
        df = df.rename(columns={"cluster_id": metric_name})
    elif "cluster" in df.columns:
        df = df.rename(columns={"cluster": metric_name})
    elif "color" in df.columns:
        df = df.rename(columns={"color": metric_name})
    elif "clustering_coefficient" in df.columns:
        df = df.rename(columns={"clustering_coefficient": metric_name})
    elif "triangle_count" in df.columns:
        df = df.rename(columns={"triangle_count": metric_name})

    # Return node_id and the metric column (whichever was renamed)
    if metric_name in df.columns:
        return df[["node_id", metric_name]]
    else:
        # Find the non-standard column
        score_cols = [c for c in df.columns if c not in ["node_id", "labels", "name"]]
        if score_cols:
            return df[["node_id"] + score_cols]
        return df[["node_id"]]


def load_embedding_csv(filename: str, metric_name: str) -> pd.DataFrame:
    """Load embedding CSV and extract embedding preview."""
    path = EMBEDDINGS_DIR / filename
    if not path.exists():
        print(f"  Warning: {path} not found")
        return pd.DataFrame(columns=["node_id", f"{metric_name}_preview", f"{metric_name}_dim"])

    df = pd.read_csv(path)
    # Keep node_id and embedding info
    cols = ["node_id"]
    if "embedding_preview" in df.columns:
        cols.append("embedding_preview")
    if "embedding_dim" in df.columns:
        cols.append("embedding_dim")
    return df[cols].rename(columns={
        "embedding_preview": f"{metric_name}_preview",
        "embedding_dim": f"{metric_name}_dim"
    })


def load_articulation_points() -> pd.DataFrame:
    """Load articulation points - binary flag per node."""
    path = CENTRALITY_DIR / ARTICULATION_FILE
    if not path.exists():
        return pd.DataFrame(columns=["node_id", "is_articulation_point"])

    df = pd.read_csv(path)
    # articulation_points.csv has node_id column
    df["is_articulation_point"] = True
    return df[["node_id", "is_articulation_point"]]


def load_bridges() -> pd.DataFrame:
    """Load bridges - these are edges, not nodes. We'll mark endpoint nodes."""
    path = CENTRALITY_DIR / BRIDGES_FILE
    if not path.exists():
        return pd.DataFrame(columns=["node_id", "is_bridge_endpoint"])

    df = pd.read_csv(path)
    # bridges.csv has source, target columns
    endpoints = set()
    for _, row in df.iterrows():
        endpoints.add(row["source"])
        endpoints.add(row["target"])

    bridge_df = pd.DataFrame({"node_id": list(endpoints)})
    bridge_df["is_bridge_endpoint"] = True
    return bridge_df


# ---------------------------------------------------------------------------
# Main Fact Table Builder
# ---------------------------------------------------------------------------

def build_entity_fact_table(force_rebuild: bool = False) -> pd.DataFrame:
    """
    Build unified entity fact table by joining all analytics CSVs.

    Returns DataFrame with one row per node (14,753) and columns for:
    - Base info: node_id, labels, name
    - Centrality: degree, betweenness, closeness, eigenvector, harmonic,
                  pagerank, article_rank, hits_hub, hits_authority
    - Community: leiden, louvain, label_propagation, sllpa, k_core, kmeans,
                 k1_coloring, clustering_coefficient, triangle_count
    - Structural: is_articulation_point, is_bridge_endpoint
    - Embeddings: node2vec_preview, fastrp_preview, graphsage_preview,
                  hashgnn_preview, fastpath_preview (plus dims)
    """
    # Check cache
    if not force_rebuild and FACT_TABLE_CACHE.exists():
        print(f"Loading entity fact table from cache: {FACT_TABLE_CACHE}")
        return pd.read_parquet(FACT_TABLE_CACHE)

    print("Building unified entity fact table...")

    # Start with base nodes
    nodes_df = pd.read_csv(DATA_DIR / "nodes.csv", low_memory=False)
    base_cols = ["element_id", "labels", "name"]
    # Handle different name column names
    name_col = "name" if "name" in nodes_df.columns else ("NAME" if "NAME" in nodes_df.columns else "Id")
    fact_df = nodes_df[["element_id", "labels", name_col]].copy()
    fact_df = fact_df.rename(columns={"element_id": "node_id", name_col: "name"})

    print(f"  Base nodes: {len(fact_df)}")

    # --- Centrality metrics ---
    print("  Joining centrality metrics...")
    for metric_key, filename in CENTRALITY_FILES.items():
        metric_df = load_centrality_csv(filename, metric_key)
        if not metric_df.empty:
            fact_df = fact_df.merge(metric_df, on="node_id", how="left")
            # Count non-null for the main metric or hub/authority
            if metric_key in metric_df.columns:
                non_null = metric_df[metric_key].notna().sum()
            elif f"{metric_key}_hub" in metric_df.columns:
                non_null = metric_df[f"{metric_key}_hub"].notna().sum()
            else:
                non_null = 0
            print(f"    {metric_key}: {non_null} non-null")

    # --- Community metrics ---
    print("  Joining community metrics...")
    for metric_key, filename in COMMUNITY_FILES.items():
        metric_df = load_community_csv(filename, metric_key)
        if not metric_df.empty:
            fact_df = fact_df.merge(metric_df, on="node_id", how="left")
            non_null = metric_df[metric_key].notna().sum() if metric_key in metric_df.columns else 0
            print(f"    {metric_key}: {non_null} non-null")

    # --- Structural flags ---
    print("  Joining structural flags...")
    art_df = load_articulation_points()
    if not art_df.empty:
        fact_df = fact_df.merge(art_df, on="node_id", how="left")
        fact_df["is_articulation_point"] = fact_df["is_articulation_point"].fillna(False)
        print(f"    articulation_points: {fact_df['is_articulation_point'].sum()} flagged")

    bridge_df = load_bridges()
    if not bridge_df.empty:
        fact_df = fact_df.merge(bridge_df, on="node_id", how="left")
        fact_df["is_bridge_endpoint"] = fact_df["is_bridge_endpoint"].fillna(False)
        print(f"    bridge_endpoints: {fact_df['is_bridge_endpoint'].sum()} flagged")

    # --- Embeddings ---
    print("  Joining embedding previews...")
    for metric_key, filename in EMBEDDING_FILES.items():
        metric_df = load_embedding_csv(filename, metric_key)
        if not metric_df.empty:
            fact_df = fact_df.merge(metric_df, on="node_id", how="left")
            preview_col = f"{metric_key}_preview"
            non_null = metric_df[preview_col].notna().sum() if preview_col in metric_df.columns else 0
            print(f"    {metric_key}: {non_null} non-null")

    # Fill NaN for boolean flags
    for col in ["is_articulation_point", "is_bridge_endpoint"]:
        if col in fact_df.columns:
            fact_df[col] = fact_df[col].fillna(False).astype(bool)

    # Fill NaN for community IDs with -1 (only integer community columns)
    community_cols = [c for c in fact_df.columns if c in
                      ["leiden", "louvain", "label_propagation", "sllpa", "k_core",
                       "kmeans", "k1_coloring"]]
    for col in community_cols:
        if col in fact_df.columns:
            # Only convert if numeric
            if pd.api.types.is_numeric_dtype(fact_df[col]):
                fact_df[col] = fact_df[col].fillna(-1).astype(int)
            else:
                fact_df[col] = fact_df[col].fillna(-1)

    # Fill NaN for numeric metrics with 0
    numeric_cols = [c for c in fact_df.columns if c not in
                    ["node_id", "labels", "name", "is_articulation_point", "is_bridge_endpoint"] +
                    community_cols +
                    [c for c in fact_df.columns if c.endswith("_preview") or c.endswith("_dim")]]
    for col in numeric_cols:
        if col in fact_df.columns and fact_df[col].dtype in [np.float64, np.int64, float, int]:
            fact_df[col] = fact_df[col].fillna(0)

    print(f"  Final fact table: {len(fact_df)} rows, {len(fact_df.columns)} columns")

    # Cache
    FACT_TABLE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    fact_df.to_parquet(FACT_TABLE_CACHE, index=False)
    fact_df.to_csv(FACT_TABLE_CSV, index=False)
    print(f"  Cached to {FACT_TABLE_CACHE} and {FACT_TABLE_CSV}")

    return fact_df


def get_entity_fact_table(force_rebuild: bool = False) -> pd.DataFrame:
    """Singleton access to entity fact table."""
    return build_entity_fact_table(force_rebuild=force_rebuild)


# ---------------------------------------------------------------------------
# Entity Lookup Functions
# ---------------------------------------------------------------------------

def get_entity_facts(entity_id: str, fact_df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
    """Get all facts for a single entity by node_id."""
    if fact_df is None:
        fact_df = get_entity_fact_table()

    row = fact_df[fact_df["node_id"] == entity_id]
    if row.empty:
        return None

    return row.iloc[0].to_dict()


def get_entities_by_label(label: str, fact_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Filter entities by label (substring match)."""
    if fact_df is None:
        fact_df = get_entity_fact_table()

    return fact_df[fact_df["labels"].str.contains(label, case=False, na=False)]


def get_top_entities_by_metric(metric: str, n: int = 10,
                                fact_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Get top-N entities by a numeric metric."""
    if fact_df is None:
        fact_df = get_entity_fact_table()

    if metric not in fact_df.columns:
        raise ValueError(f"Metric '{metric}' not in fact table. Available: {list(fact_df.columns)}")

    return fact_df.nlargest(n, metric)[["node_id", "labels", "name", metric]]


def get_community_members(community_id: int, algorithm: str = "leiden",
                          fact_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Get all entities in a specific community."""
    if fact_df is None:
        fact_df = get_entity_fact_table()

    if algorithm not in fact_df.columns:
        raise ValueError(f"Algorithm '{algorithm}' not in fact table")

    return fact_df[fact_df[algorithm] == community_id][["node_id", "labels", "name"]]


def get_cross_community_entities(fact_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Find entities that connect different communities (high betweenness + multiple community neighbors)."""
    if fact_df is None:
        fact_df = get_entity_fact_table()

    # Simple heuristic: high betweenness + articulation point or bridge endpoint
    cols = ["node_id", "labels", "name", "betweenness_centrality",
            "is_articulation_point", "is_bridge_endpoint", "leiden", "louvain"]
    available = [c for c in cols if c in fact_df.columns]

    df = fact_df[available].copy()
    if "betweenness_centrality" in df.columns:
        df = df.nlargest(100, "betweenness_centrality")

    return df


# ---------------------------------------------------------------------------
# Community Fact Table
# ---------------------------------------------------------------------------

def build_community_fact_table(fact_df: Optional[pd.DataFrame] = None) -> Dict[str, pd.DataFrame]:
    """
    Build per-community statistics for each community detection algorithm.

    Returns dict: algorithm -> DataFrame with community stats
    """
    if fact_df is None:
        fact_df = get_entity_fact_table()

    community_algorithms = ["leiden", "louvain", "label_propagation", "sllpa", "kmeans", "k1_coloring"]
    results = {}

    for algo in community_algorithms:
        if algo not in fact_df.columns:
            continue

        communities = fact_df[algo].unique()
        communities = communities[communities >= 0]  # Exclude -1 (unassigned)

        stats = []
        for comm_id in communities:
            members = fact_df[fact_df[algo] == comm_id]
            n = len(members)

            # Label distribution
            label_dist = members["labels"].value_counts().to_dict()

            # Centrality statistics
            centrality_stats = {}
            for metric in ["degree_centrality", "pagerank", "betweenness_centrality", "closeness_centrality"]:
                if metric in members.columns:
                    vals = members[metric].dropna()
                    if len(vals) > 0:
                        centrality_stats[metric] = {
                            "mean": float(vals.mean()),
                            "max": float(vals.max()),
                            "min": float(vals.min()),
                            "std": float(vals.std()) if len(vals) > 1 else 0.0
                        }

            stats.append({
                "community_id": int(comm_id),
                "size": n,
                "label_distribution": label_dist,
                "centrality_stats": centrality_stats,
            })

        results[algo] = pd.DataFrame(stats)
        print(f"  {algo}: {len(results[algo])} communities")

    return results


# ---------------------------------------------------------------------------
# Analytics Metadata / Provenance
# ---------------------------------------------------------------------------

def get_analytics_metadata() -> Dict[str, Any]:
    """Return provenance metadata for all analytics."""
    return {
        "centrality": {
            "degree_centrality": {"algorithm": "Degree Centrality", "library": "NetworkX",
                                   "graph_type": "undirected", "normalized": True},
            "betweenness_centrality": {"algorithm": "Betweenness Centrality", "library": "NetworkX",
                                        "graph_type": "undirected", "normalized": True,
                                        "note": "Brandes algorithm, ~365s runtime"},
            "closeness_centrality": {"algorithm": "Closeness Centrality", "library": "NetworkX",
                                      "graph_type": "undirected", "normalized": True},
            "eigenvector_centrality": {"algorithm": "Eigenvector Centrality", "library": "NetworkX",
                                        "graph_type": "undirected", "max_iter": 1000},
            "harmonic_centrality": {"algorithm": "Harmonic Centrality", "library": "NetworkX",
                                     "graph_type": "undirected", "normalized": True},
            "pagerank": {"algorithm": "PageRank", "library": "NetworkX",
                          "graph_type": "undirected", "alpha": 0.85},
            "article_rank": {"algorithm": "ArticleRank", "library": "NetworkX",
                              "graph_type": "undirected", "note": "Avg-neighbor-degree damping"},
            "hits": {"algorithm": "HITS", "library": "NetworkX",
                      "graph_type": "directed", "note": "Hub/authority scores"},
        },
        "community": {
            "leiden": {"algorithm": "Leiden", "library": "leidenalg/igraph",
                        "communities": 15, "modularity": 0.4996,
                        "note": "Hierarchical modularity, connected partitions guaranteed"},
            "louvain": {"algorithm": "Louvain", "library": "python-louvain",
                         "communities": 14, "modularity": 0.4994,
                         "note": "May produce disconnected communities"},
            "label_propagation": {"algorithm": "Label Propagation", "library": "NetworkX",
                                   "communities": 46},
            "sllpa": {"algorithm": "Speaker-Listener LPA", "library": "cdlib",
                       "communities": 10, "note": "50 iterations, 10 patient seeds"},
            "k_core": {"algorithm": "K-Core Decomposition", "library": "NetworkX",
                        "max_core": 22},
            "kmeans": {"algorithm": "K-Means Clustering", "library": "scikit-learn",
                        "k": 13, "features": ["degree", "pagerank", "clustering", "triangles"]},
        },
        "similarity": {
            "node_similarity": {"algorithm": "Jaccard Node Similarity", "library": "NetworkX",
                                 "sampled": True, "sample_size": 20, "top_k": 10,
                                 "note": "Only 20 patients sampled, NOT population-wide"},
            "knn": {"algorithm": "K-Nearest Neighbors", "library": "NetworkX",
                     "sampled": True, "sample_size": 20, "k": 10,
                     "note": "Only 20 patients sampled, NOT population-wide"},
        },
        "embeddings": {
            "node2vec": {"algorithm": "Node2Vec", "dimensions": 128, "library": "node2vec/gensim"},
            "fastrp": {"algorithm": "FastRP", "dimensions": 128, "library": "custom/Gaussian RP"},
            "graphsage": {"algorithm": "GraphSAGE", "dimensions": 128, "library": "custom/mean agg + Ridge"},
            "hashgnn": {"algorithm": "HashGNN", "dimensions": 128, "library": "custom/random hashing"},
            "fastpath": {"algorithm": "FastPath", "dimensions": 128, "library": "custom/shortest-path vectors"},
        },
        "limitations": [
            "Static graph snapshot (no temporal evolution)",
            "Similarity analysis is sampled (20 patients only) — NOT exhaustive",
            "Some centrality algorithms used undirected approximation of directed graph",
            "HDBSCAN did not produce output (requires feature matrix)",
            "Path algorithms sampled (1-5 source nodes only)",
            "No Neo4j GDS — all algorithms computed locally",
            "Synthetic patient data (Synthea) — not real clinical records",
            "Graph patterns ≠ clinical outcomes — structural analysis only",
        ]
    }


# ---------------------------------------------------------------------------
# Utility: Column Catalog
# ---------------------------------------------------------------------------

def get_fact_table_schema(fact_df: Optional[pd.DataFrame] = None) -> Dict[str, Dict[str, str]]:
    """Return schema description for all columns in fact table."""
    if fact_df is None:
        fact_df = get_entity_fact_table()

    schema = {}
    for col in fact_df.columns:
        dtype = str(fact_df[col].dtype)
        sample = fact_df[col].dropna().iloc[0] if fact_df[col].notna().any() else None
        schema[col] = {
            "dtype": dtype,
            "sample": str(sample)[:100] if sample is not None else "N/A",
            "non_null_count": int(fact_df[col].notna().sum()),
            "null_pct": float(fact_df[col].isna().mean() * 100)
        }
    return schema