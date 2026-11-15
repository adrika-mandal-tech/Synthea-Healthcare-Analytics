"""
Graph Intelligence Platform — Community Fact Tables

Detailed per-community statistics and cross-algorithm comparisons.
"""

import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import json

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).parent.parent.parent
COMMUNITY_DIR = WORKSPACE / "community"
COMMUNITY_FACTS_CACHE = WORKSPACE / ".graph_cache" / "community_facts.json"


# ---------------------------------------------------------------------------
# Community Statistics
# ---------------------------------------------------------------------------

def load_community_assignments(algorithm: str) -> pd.DataFrame:
    """Load community assignments for a specific algorithm."""
    file_map = {
        "leiden": "leiden.csv",
        "louvain": "louvain.csv",
        "label_propagation": "label_propagation.csv",
        "sllpa": "sllpa.csv",
        "kmeans": "kmeans.csv",
        "k1_coloring": "k1_coloring.csv",
    }

    if algorithm not in file_map:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    path = COMMUNITY_DIR / file_map[algorithm]
    if not path.exists():
        return pd.DataFrame(columns=["node_id", "community_id"])

    df = pd.read_csv(path)
    if "community_id" in df.columns:
        # Check if community_id is numeric
        if pd.api.types.is_numeric_dtype(df["community_id"]):
            return df[["node_id", "community_id"]]
        else:
            # Non-numeric (like SLLPA seeds) - skip for comparison
            return pd.DataFrame(columns=["node_id", "community_id"])
    elif "cluster_id" in df.columns:
        return df[["node_id", "cluster_id"]].rename(columns={"cluster_id": "community_id"})
    elif "cluster" in df.columns:
        return df[["node_id", "cluster"]].rename(columns={"cluster": "community_id"})
    elif "color" in df.columns:
        return df[["node_id", "color"]].rename(columns={"color": "community_id"})
    elif "core_number" in df.columns:
        return df[["node_id", "core_number"]].rename(columns={"core_number": "community_id"})

    return pd.DataFrame(columns=["node_id", "community_id"])


def load_nodes_df() -> pd.DataFrame:
    """Load nodes DataFrame."""
    return pd.read_csv(WORKSPACE / "data" / "nodes.csv", low_memory=False)


def compute_community_statistics(algorithm: str, nodes_df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """Compute detailed statistics for each community in an algorithm."""
    if nodes_df is None:
        nodes_df = load_nodes_df()

    assignments = load_community_assignments(algorithm)
    if assignments.empty:
        return []

    # Merge with node info
    merged = assignments.merge(nodes_df[["element_id", "labels", "name"]],
                               left_on="node_id", right_on="element_id", how="left")

    communities = merged["community_id"].unique()
    communities = communities[communities >= 0]  # Exclude -1

    stats = []
    for comm_id in communities:
        members = merged[merged["community_id"] == comm_id]
        n = len(members)

        # Label distribution
        label_dist = members["labels"].value_counts().to_dict()

        # Top entities by name
        top_names = members["name"].value_counts().head(5).to_dict()

        stats.append({
            "community_id": int(comm_id),
            "size": n,
            "label_distribution": label_dist,
            "top_entities": top_names,
            "algorithm": algorithm,
        })

    return stats


def compute_all_community_statistics(nodes_df: Optional[pd.DataFrame] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Compute statistics for all community algorithms."""
    algorithms = ["leiden", "louvain", "label_propagation", "sllpa", "kmeans", "k1_coloring"]
    results = {}

    for algo in algorithms:
        try:
            results[algo] = compute_community_statistics(algo, nodes_df)
            print(f"  {algo}: {len(results[algo])} communities")
        except Exception as e:
            print(f"  {algo}: ERROR - {e}")
            results[algo] = []

    return results


def compute_cross_algorithm_comparison(nodes_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Compare community assignments across algorithms (ARI, NMI, overlap)."""
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    if nodes_df is None:
        nodes_df = load_nodes_df()

    algorithms = ["leiden", "louvain", "label_propagation", "sllpa", "kmeans", "k1_coloring"]
    assignments = {}

    for algo in algorithms:
        df = load_community_assignments(algo)
        if not df.empty:
            # Align to nodes_df order
            merged = nodes_df[["element_id"]].merge(df, left_on="element_id", right_on="node_id", how="left")
            # Fill NaN with -1 and ensure int type
            comm_vals = merged["community_id"].fillna(-1)
            # Convert to numeric, non-numeric becomes NaN then -1
            comm_numeric = pd.to_numeric(comm_vals, errors='coerce').fillna(-1).astype(int)
            assignments[algo] = comm_numeric.values

    if len(assignments) < 2:
        return {"error": "Need at least 2 algorithms with assignments"}

    # Pairwise ARI and NMI
    algo_names = list(assignments.keys())
    # Initialize all matrices first
    ari_matrix = {a: {b: None for b in algo_names} for a in algo_names}
    nmi_matrix = {a: {b: None for b in algo_names} for a in algo_names}

    for i, a1 in enumerate(algo_names):
        ari_matrix[a1][a1] = 1.0
        nmi_matrix[a1][a1] = 1.0
        for j, a2 in enumerate(algo_names):
            if j > i:
                try:
                    ari = adjusted_rand_score(assignments[a1], assignments[a2])
                    nmi = normalized_mutual_info_score(assignments[a1], assignments[a2])
                    ari_matrix[a1][a2] = float(ari)
                    ari_matrix[a2][a1] = float(ari)
                    nmi_matrix[a1][a2] = float(nmi)
                    nmi_matrix[a2][a1] = float(nmi)
                except Exception as e:
                    print(f"  Warning: ARI/NMI failed for {a1} vs {a2}: {e}")
                    ari_matrix[a1][a2] = None
                    ari_matrix[a2][a1] = None
                    nmi_matrix[a1][a2] = None
                    nmi_matrix[a2][a1] = None

    # Community size comparison
    size_comparison = {}
    for algo in algo_names:
        valid_comms = assignments[algo][assignments[algo] >= 0]
        if len(valid_comms) == 0:
            size_comparison[algo] = {
                "n_communities": 0,
                "size_distribution": {},
                "avg_size": 0.0,
                "max_size": 0,
                "min_size": 0,
            }
            continue
        comm_ids, counts = np.unique(valid_comms, return_counts=True)
        size_comparison[algo] = {
            "n_communities": len(comm_ids),
            "size_distribution": dict(zip(comm_ids.astype(int).tolist(), counts.astype(int).tolist())),
            "avg_size": float(np.mean(counts)),
            "max_size": int(np.max(counts)),
            "min_size": int(np.min(counts)),
        }

    return {
        "algorithms": algo_names,
        "ari_matrix": ari_matrix,
        "nmi_matrix": nmi_matrix,
        "size_comparison": size_comparison,
    }


def find_cross_community_bridges(algorithm: str = "leiden",
                                  nodes_df: Optional[pd.DataFrame] = None,
                                  rels_df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """Find nodes that connect multiple communities (bridge nodes)."""
    if nodes_df is None:
        nodes_df = load_nodes_df()
    if rels_df is None:
        rels_df = pd.read_csv(WORKSPACE / "data" / "relationships.csv", low_memory=False)

    assignments = load_community_assignments(algorithm)
    if assignments.empty:
        return []

    # Map node_id -> community
    node_to_comm = dict(zip(assignments["node_id"], assignments["community_id"]))

    # For each node, check neighbors' communities
    bridges = []
    for _, node_row in nodes_df.iterrows():
        nid = node_row["element_id"]
        if nid not in node_to_comm:
            continue

        own_comm = node_to_comm[nid]
        if own_comm < 0:
            continue

        # Get neighbors
        neighbors = rels_df[
            (rels_df["source_element_id"] == nid) | (rels_df["target_element_id"] == nid)
        ]
        neighbor_ids = set()
        for _, rel in neighbors.iterrows():
            if rel["source_element_id"] == nid:
                neighbor_ids.add(rel["target_element_id"])
            else:
                neighbor_ids.add(rel["source_element_id"])

        # Count cross-community edges
        cross_comm_neighbors = {}
        for nbr in neighbor_ids:
            if nbr in node_to_comm:
                nbr_comm = node_to_comm[nbr]
                if nbr_comm != own_comm and nbr_comm >= 0:
                    cross_comm_neighbors[nbr_comm] = cross_comm_neighbors.get(nbr_comm, 0) + 1

        if len(cross_comm_neighbors) > 0:
            bridges.append({
                "node_id": nid,
                "name": node_row.get("name", "") or node_row.get("NAME", "") or node_row.get("Id", ""),
                "labels": node_row.get("labels", ""),
                "own_community": int(own_comm),
                "cross_community_edges": cross_comm_neighbors,
                "n_cross_communities": len(cross_comm_neighbors),
                "total_cross_edges": sum(cross_comm_neighbors.values()),
            })

    # Sort by number of cross-communities, then by total cross edges
    bridges.sort(key=lambda x: (x["n_cross_communities"], x["total_cross_edges"]), reverse=True)
    return bridges


def get_community_summary(algorithm: str = "leiden") -> Dict[str, Any]:
    """Get high-level summary for a community algorithm."""
    assignments = load_community_assignments(algorithm)
    if assignments.empty:
        return {"error": f"No data for {algorithm}"}

    comm_ids = assignments["community_id"].unique()
    comm_ids = comm_ids[comm_ids >= 0]

    sizes = assignments[assignments["community_id"] >= 0].groupby("community_id").size()

    return {
        "algorithm": algorithm,
        "n_communities": len(comm_ids),
        "avg_size": float(sizes.mean()),
        "median_size": float(sizes.median()),
        "max_size": int(sizes.max()),
        "min_size": int(sizes.min()),
        "size_distribution": sizes.astype(int).to_dict(),
    }


def build_community_facts_cache(force_rebuild: bool = False) -> Dict[str, Any]:
    """Build and cache all community facts."""
    if not force_rebuild and COMMUNITY_FACTS_CACHE.exists():
        print(f"Loading community facts from cache: {COMMUNITY_FACTS_CACHE}")
        with open(COMMUNITY_FACTS_CACHE, "r") as f:
            return json.load(f)

    print("Building community facts...")
    nodes_df = load_nodes_df()

    results = {
        "statistics": compute_all_community_statistics(nodes_df),
        "comparison": compute_cross_algorithm_comparison(nodes_df),
        "summaries": {},
        "bridges": {},
    }

    for algo in ["leiden", "louvain", "label_propagation", "sllpa", "kmeans", "k1_coloring"]:
        results["summaries"][algo] = get_community_summary(algo)
        results["bridges"][algo] = find_cross_community_bridges(algo, nodes_df)[:50]  # Top 50

    # Cache
    COMMUNITY_FACTS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(COMMUNITY_FACTS_CACHE, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"  Cached to {COMMUNITY_FACTS_CACHE}")
    return results


def load_community_facts() -> Dict[str, Any]:
    """Load cached community facts."""
    if COMMUNITY_FACTS_CACHE.exists():
        with open(COMMUNITY_FACTS_CACHE, "r") as f:
            return json.load(f)
    return build_community_facts_cache()