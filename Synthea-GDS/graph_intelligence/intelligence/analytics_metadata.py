"""
Graph Intelligence Platform — Analytics Metadata & Provenance

Centralized metadata for all algorithms, outputs, and limitations.
"""

import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).parent.parent.parent
REPORTS_DIR = WORKSPACE / "reports"
MANIFEST_CSV = REPORTS_DIR / "algorithm_manifest.csv"
SUMMARY_CSV = REPORTS_DIR / "algorithm_summary.csv"


# ---------------------------------------------------------------------------
# Algorithm Registry
# ---------------------------------------------------------------------------

ALGORITHM_REGISTRY = {
    # Centrality
    "degree_centrality": {
        "name": "Degree Centrality",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"normalized": True},
        "output_file": "centrality/degree_centrality.csv",
        "description": "Normalized neighbor count. Measures direct connectivity.",
        "interpretation": "High degree = highly connected entity (hub organization, frequent encounter)",
        "limitations": ["Undirected approximation of directed graph", "Does not weight edge importance"],
    },
    "betweenness_centrality": {
        "name": "Betweenness Centrality",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"normalized": True},
        "output_file": "centrality/betweenness_centrality.csv",
        "description": "Fraction of shortest paths passing through a node. Brandes algorithm.",
        "interpretation": "High betweenness = bridge/bottleneck between communities (referral broker)",
        "limitations": ["Undirected approximation", "Computationally expensive (O(nm))", "~365s runtime"],
    },
    "closeness_centrality": {
        "name": "Closeness Centrality",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"normalized": True},
        "output_file": "centrality/closeness_centrality.csv",
        "description": "Inverse of sum of shortest path distances to all other nodes.",
        "interpretation": "High closeness = can reach all others quickly (central position)",
        "limitations": ["Undirected approximation", "Assumes connected graph"],
    },
    "eigenvector_centrality": {
        "name": "Eigenvector Centrality",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"max_iter": 1000},
        "output_file": "centrality/eigenvector_centrality.csv",
        "description": "Importance proportional to neighbor importance via power iteration.",
        "interpretation": "High eigenvector = connected to other important nodes",
        "limitations": ["Undirected approximation", "May not converge for some graphs"],
    },
    "harmonic_centrality": {
        "name": "Harmonic Centrality",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"normalized": True},
        "output_file": "centrality/harmonic_centrality.csv",
        "description": "Sum of inverse distances; handles disconnected subgraphs gracefully.",
        "interpretation": "Variant of closeness that works on disconnected graphs",
        "limitations": ["Undirected approximation"],
    },
    "pagerank": {
        "name": "PageRank",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"alpha": 0.85},
        "output_file": "centrality/pagerank.csv",
        "description": "Random surfer model (α=0.85). Measures influence via random walks.",
        "interpretation": "High PageRank = influential in random walk process",
        "limitations": ["Undirected approximation", "Damping factor fixed at 0.85"],
    },
    "article_rank": {
        "name": "ArticleRank",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "centrality/article_rank.csv",
        "description": "PageRank variant with avg-neighbor-degree damping. Reduces rank-spam.",
        "interpretation": "More robust PageRank variant",
        "limitations": ["Undirected approximation"],
    },
    "hits": {
        "name": "HITS",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {},
        "output_file": "centrality/hits.csv",
        "description": "Hub/authority scores via power iteration on directed graph.",
        "interpretation": "High hub = points to many authorities; High authority = pointed to by many hubs",
        "limitations": ["Computed on directed graph with 5 Patient sources only"],
    },
    "articulation_points": {
        "name": "Articulation Points",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "centrality/articulation_points.csv",
        "description": "Nodes whose removal increases connected components. DFS-based.",
        "interpretation": "Critical structural nodes whose removal fragments the network",
        "limitations": ["Undirected approximation", "Only 96 nodes in largest component analyzed"],
    },
    "bridges": {
        "name": "Bridges",
        "category": "centrality",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "centrality/bridges.csv",
        "description": "Edges whose removal disconnects the graph. Tarjan's algorithm.",
        "interpretation": "Critical edges whose removal fragments the network",
        "limitations": ["Undirected approximation", "Only 96 edges in largest component analyzed"],
    },
    "celf": {
        "name": "CELF (Cost-Effective Lazy Forward)",
        "category": "centrality",
        "library": "NetworkX + python-louvain",
        "graph_type": "undirected",
        "parameters": {"k": 10, "influence": "degree_centrality"},
        "output_file": "centrality/celf.csv",
        "description": "Influence maximization approximated via top-k degree centrality (k=10).",
        "interpretation": "Top 10 nodes for influence spread approximation",
        "limitations": ["Approximated via degree centrality, not true CELF"],
    },

    # Community Detection
    "leiden": {
        "name": "Leiden",
        "category": "community",
        "library": "leidenalg/igraph",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/leiden.csv",
        "description": "Hierarchical modularity optimization; guarantees connected partitions.",
        "interpretation": "15 communities, Q=0.4996. Connected, well-separated groups.",
        "limitations": ["Undirected graph", "Resolution parameter not tuned"],
    },
    "louvain": {
        "name": "Louvain",
        "category": "community",
        "library": "python-louvain",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/louvain.csv",
        "description": "Greedy modularity optimization. Fast but may produce disconnected communities.",
        "interpretation": "14 communities, Q=0.4994. Slightly lower modularity than Leiden.",
        "limitations": ["Undirected graph", "May produce disconnected communities"],
    },
    "label_propagation": {
        "name": "Label Propagation",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/label_propagation.csv",
        "description": "Asynchronous label adoption. Fast, non-deterministic.",
        "interpretation": "46 communities. Good for quick overview.",
        "limitations": ["Non-deterministic", "Can produce trivial communities"],
    },
    "sllpa": {
        "name": "Speaker-Listener Label Propagation",
        "category": "community",
        "library": "cdlib",
        "graph_type": "undirected",
        "parameters": {"iterations": 50, "seeds": 10},
        "output_file": "community/sllpa.csv",
        "description": "Overlapping community detection with patient seeds.",
        "interpretation": "10 overlapping communities. Patients can belong to multiple.",
        "limitations": ["Overlapping - not a partition", "Seed selection affects results"],
    },
    "k_core": {
        "name": "K-Core Decomposition",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/k_core.csv",
        "description": "Iterative removal of nodes with degree < k. Max core = 22.",
        "interpretation": "Nested cores reveal hierarchical structure. Core 22 = densest subgraph.",
        "limitations": ["Not a partition - nested hierarchy"],
    },
    "kmeans": {
        "name": "K-Means Clustering",
        "category": "community",
        "library": "scikit-learn",
        "graph_type": "feature_space",
        "parameters": {"k": 13, "features": ["degree", "pagerank", "clustering", "triangles"]},
        "output_file": "community/kmeans.csv",
        "description": "K-means on structural features (not graph topology directly).",
        "interpretation": "13 clusters based on structural similarity, not connectivity.",
        "limitations": ["Feature-based, not topology-based", "k=13 chosen arbitrarily"],
    },
    "hdbscan": {
        "name": "HDBSCAN",
        "category": "community",
        "library": "hdbscan",
        "graph_type": "feature_space",
        "parameters": {"feature_matrix": "required"},
        "output_file": None,
        "description": "Density-based clustering. Requires node feature vectors.",
        "interpretation": "NOT RUN - requires feature matrix parameter",
        "limitations": ["Not executed - missing parameters"],
    },
    "clustering_coefficient": {
        "name": "Local Clustering Coefficient",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/clustering_coefficient.csv",
        "description": "Fraction of possible triangles that exist for each node.",
        "interpretation": "High clustering = node's neighbors are well-connected (cliquish)",
        "limitations": ["Undirected approximation"],
    },
    "triangle_count": {
        "name": "Triangle Count",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/triangle_count.csv",
        "description": "Number of triangles each node participates in. 159,278 total cliques.",
        "interpretation": "High triangle count = embedded in dense local structure",
        "limitations": ["Undirected approximation"],
    },
    "wcc": {
        "name": "Weakly Connected Components",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/wcc.csv",
        "description": "Connected components ignoring edge direction. Entire network is 1 component.",
        "interpretation": "Graph is fully connected when direction ignored",
        "limitations": ["Trivial result - single component"],
    },
    "scc": {
        "name": "Strongly Connected Components",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {},
        "output_file": "community/scc.csv",
        "description": "Components with directed paths both ways. 14,753 SCCs (each node isolated).",
        "interpretation": "No directed cycles spanning multiple nodes",
        "limitations": ["Trivial result - all singletons"],
    },
    "conductance": {
        "name": "Conductance",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/conductance.csv",
        "description": "Per-community edge boundary ratio (edges leaving / internal edges).",
        "interpretation": "Low conductance = well-separated community",
        "limitations": ["Computed for top communities only"],
    },
    "modularity": {
        "name": "Modularity",
        "category": "community",
        "library": "python-louvain",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/modularity.csv",
        "description": "Global modularity score Q=0.4980 for best partition.",
        "interpretation": "Q > 0.3 indicates significant community structure",
        "limitations": ["Single scalar value"],
    },
    "k1_coloring": {
        "name": "K-1 Coloring",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"strategy": "largest_first"},
        "output_file": "community/k1_coloring.csv",
        "description": "Greedy coloring; adjacent nodes get different colors. 5 colors used.",
        "interpretation": "Chromatic number upper bound = 5",
        "limitations": ["Greedy heuristic, not optimal"],
    },
    "approx_max_kcut": {
        "name": "Approximate Maximum k-cut",
        "category": "community",
        "library": "NetworkX + python-louvain",
        "graph_type": "undirected",
        "parameters": {"k": 5},
        "output_file": "community/approx_max_kcut.csv",
        "description": "Approximated via top-k Louvain communities by size.",
        "interpretation": "5 largest communities by size",
        "limitations": ["Heuristic, not true max k-cut"],
    },
    "clique_count": {
        "name": "Clique Counting",
        "category": "community",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {},
        "output_file": "community/clique_count.csv",
        "description": "Enumerates complete subgraphs. 159,278 cliques found.",
        "interpretation": "Dense substructures in the graph",
        "limitations": ["Only counts, no per-node output"],
    },

    # Similarity
    "node_similarity": {
        "name": "Jaccard Node Similarity",
        "category": "similarity",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"sample_size": 20, "top_k": 10},
        "output_file": "similarity/node_similarity.csv",
        "description": "Jaccard similarity of neighborhoods. SAMPLED: 20 patients × top-10.",
        "interpretation": "Similar neighborhood structure = similar care patterns",
        "limitations": ["SAMPLED - only 20 patients", "NOT population-wide", "Jaccard on undirected neighborhoods"],
    },
    "filtered_node_similarity": {
        "name": "Filtered Jaccard Node Similarity",
        "category": "similarity",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"sample_size": 20, "top_k": 10, "filter": "Patient-Patient"},
        "output_file": "similarity/filtered_node_similarity.csv",
        "description": "Patient-to-Patient similarity only. SAMPLED.",
        "interpretation": "Patients with similar encounter/condition/medication neighborhoods",
        "limitations": ["SAMPLED - only 20 patients", "NOT population-wide"],
    },
    "knn": {
        "name": "K-Nearest Neighbors",
        "category": "similarity",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"sample_size": 20, "k": 10},
        "output_file": "similarity/knn.csv",
        "description": "Top-k nearest neighbors by Jaccard. SAMPLED: 20 patients.",
        "interpretation": "Structural nearest neighbors for sampled patients",
        "limitations": ["SAMPLED - only 20 patients", "NOT population-wide"],
    },
    "filtered_knn": {
        "name": "Filtered KNN",
        "category": "similarity",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"sample_size": 20, "k": 10, "filter": "Patient-Patient"},
        "output_file": "similarity/filtered_knn.csv",
        "description": "Patient-to-Patient KNN only. SAMPLED.",
        "interpretation": "Patient cohorts with similar graph neighborhoods",
        "limitations": ["SAMPLED - only 20 patients", "NOT population-wide"],
    },

    # Paths
    "dijkstra_source_target": {
        "name": "Dijkstra Source-Target",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {"weight": "weight"},
        "output_file": "paths/dijkstra_source_target.csv",
        "description": "Shortest path between one source-target pair.",
        "interpretation": "Single path demonstration",
        "limitations": ["Single pair only", "Weighted by edge weight if available"],
    },
    "dijkstra_single_source": {
        "name": "Dijkstra Single-Source",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {"weight": "weight"},
        "output_file": "paths/dijkstra_single_source.csv",
        "description": "Shortest paths from one source to all reachable nodes.",
        "interpretation": "Single source reachability",
        "limitations": ["Single source only"],
    },
    "bellman_ford": {
        "name": "Bellman-Ford",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {"weight": "weight"},
        "output_file": "paths/bellman_ford.csv",
        "description": "Shortest paths with negative weight support. Single source.",
        "interpretation": "Same as Dijkstra for non-negative weights",
        "limitations": ["Single source only", "Slower than Dijkstra"],
    },
    "astar": {
        "name": "A* Search",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {"heuristic": "zero"},
        "output_file": "paths/astar.csv",
        "description": "A* with zero heuristic (reduces to Dijkstra). Single pair.",
        "interpretation": "Pathfinding demo",
        "limitations": ["Zero heuristic = no speedup", "Single pair only"],
    },
    "yen": {
        "name": "Yen's K-Shortest Paths",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {"k": 5},
        "output_file": "paths/yen.csv",
        "description": "Top 5 loopless shortest paths between one pair.",
        "interpretation": "Alternative routes between same endpoints",
        "limitations": ["Single pair only", "k=5"],
    },
    "bfs": {
        "name": "Breadth-First Search",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {},
        "output_file": "paths/bfs.csv",
        "description": "Unweighted shortest paths from one source.",
        "interpretation": "Unweighted reachability from single source",
        "limitations": ["Single source only", "Unweighted"],
    },
    "dfs": {
        "name": "Depth-First Search",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {},
        "output_file": "paths/dfs.csv",
        "description": "DFS traversal from one source.",
        "interpretation": "Exploration order from single source",
        "limitations": ["Single source only", "Not shortest paths"],
    },
    "random_walk": {
        "name": "Random Walk",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "directed",
        "parameters": {"sources": 5, "steps": 50},
        "output_file": "paths/random_walk.csv",
        "description": "Random walks from 5 patient nodes, 50 steps each.",
        "interpretation": "Simulated patient journey exploration",
        "limitations": ["Only 5 patients", "50 steps each", "Stochastic"],
    },
    "minimum_weight_spanning_tree": {
        "name": "Minimum Weight Spanning Tree",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"weight": "weight"},
        "output_file": "paths/minimum_weight_spanning_tree.csv",
        "description": "MST connecting all nodes with minimum total weight. 14,752 edges.",
        "interpretation": "Backbone connectivity structure",
        "limitations": ["Undirected", "Weight interpretation unclear"],
    },
    "prize_collecting_steiner_tree": {
        "name": "Prize-Collecting Steiner Tree",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"prizes": "degree", "terminals": 10},
        "output_file": "paths/prize_collecting_steiner_tree.csv",
        "description": "Steiner tree with degree-based prizes, 10 terminals.",
        "interpretation": "Cost-effective subgraph connecting high-prize nodes",
        "limitations": ["Heuristic prizes", "Small terminal set"],
    },
    "minimum_weight_k_spanning_tree": {
        "name": "Minimum Weight k-Spanning Tree",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "undirected",
        "parameters": {"k": 5},
        "output_file": "paths/minimum_weight_k_spanning_tree.csv",
        "description": "Forest of k trees minimizing total weight.",
        "interpretation": "k=5 connected components with minimal internal weight",
        "limitations": ["Undirected", "k=5 arbitrary"],
    },
    "longest_path_dag": {
        "name": "Longest Path in DAG",
        "category": "paths",
        "library": "NetworkX",
        "graph_type": "DAG",
        "parameters": {"sources": 2, "max_length": 20},
        "output_file": "paths/longest_path_dag.csv",
        "description": "Longest paths from 2 patient sources in DAG projection.",
        "interpretation": "Longest care pathways from sample patients",
        "limitations": ["Only 2 patients", "Requires DAG projection", "max_length=20"],
    },
    "topological_sort": {
        "name": "Topological Sort",
        "category": "dag",
        "library": "NetworkX",
        "graph_type": "DAG",
        "parameters": {"algorithm": "Kahn"},
        "output_file": "dag/topological_sort.csv",
        "description": "Kahn's algorithm for topological ordering.",
        "interpretation": "Partial order of encounters/procedures",
        "limitations": ["Requires DAG projection"],
    },
    "longest_path": {
        "name": "Longest Path (DP on DAG)",
        "category": "dag",
        "library": "NetworkX",
        "graph_type": "DAG",
        "parameters": {},
        "output_file": "dag/longest_path.csv",
        "description": "Longest path via DP on topological order.",
        "interpretation": "Critical path in care sequence",
        "limitations": ["Requires DAG projection"],
    },

    # Embeddings
    "node2vec": {
        "name": "Node2Vec",
        "category": "embeddings",
        "library": "node2vec/gensim",
        "graph_type": "undirected",
        "parameters": {"dimensions": 128},
        "output_file": "embeddings/node2vec.csv",
        "description": "Biased random walks + Skip-gram. Captures structural equivalence.",
        "interpretation": "Similar vectors = similar structural roles",
        "limitations": ["Random walk stochasticity", "Hyperparameters not tuned"],
    },
    "fastrp": {
        "name": "FastRP",
        "category": "embeddings",
        "library": "custom/Gaussian RP",
        "graph_type": "undirected",
        "parameters": {"dimensions": 128},
        "output_file": "embeddings/fastrp.csv",
        "description": "Gaussian Random Projection. Very fast, decent quality.",
        "interpretation": "Spectral embedding approximation",
        "limitations": ["Approximation quality depends on iterations"],
    },
    "graphsage": {
        "name": "GraphSAGE",
        "category": "embeddings",
        "library": "custom/mean agg + Ridge",
        "graph_type": "undirected",
        "parameters": {"dimensions": 128, "aggregator": "mean"},
        "output_file": "embeddings/graphsage.csv",
        "description": "Inductive embedding via neighbor aggregation + Ridge regression.",
        "interpretation": "Can embed unseen nodes",
        "limitations": ["Simplified implementation", "Not full GraphSAGE"],
    },
    "hashgnn": {
        "name": "HashGNN",
        "category": "embeddings",
        "library": "custom/random hashing",
        "graph_type": "undirected",
        "parameters": {"dimensions": 128},
        "output_file": "embeddings/hashgnn.csv",
        "description": "Random hashing for fast embedding.",
        "interpretation": "Very fast, lower quality baseline",
        "limitations": ["Random projection quality varies"],
    },
    "fastpath": {
        "name": "FastPath",
        "category": "embeddings",
        "library": "custom/shortest-path vectors",
        "graph_type": "undirected",
        "parameters": {"dimensions": 128},
        "output_file": "embeddings/fastpath.csv",
        "description": "Shortest-path distance vectors as embeddings.",
        "interpretation": "Positional embedding via distances",
        "limitations": ["Computationally expensive", "O(n²) distances"],
    },
}


# ---------------------------------------------------------------------------
# Global Limitations
# ---------------------------------------------------------------------------

GLOBAL_LIMITATIONS = [
    "Static graph snapshot — no temporal evolution captured",
    "Similarity analysis is SAMPLED (20 patients only) — NOT exhaustive population analysis",
    "Some centrality algorithms used undirected approximation of directed graph",
    "HDBSCAN did not produce output (requires feature matrix parameter)",
    "Path algorithms sampled (1-5 source nodes only) — NOT exhaustive",
    "No Neo4j GDS used — all algorithms computed locally in Python",
    "Synthetic patient data (Synthea) — not real clinical records",
    "Graph patterns reflect structural connectivity — NOT clinical outcomes",
    "No causal claims can be made from structural graph statistics",
    "Community detection on undirected graph loses directional referral flow information",
    "Embedding methods are custom implementations, not production-grade libraries",
    "Single graph snapshot — no cross-validation or temporal stability analysis",
]


# ---------------------------------------------------------------------------
# Data Provenance
# ---------------------------------------------------------------------------

def get_data_provenance() -> Dict[str, Any]:
    """Return data provenance information."""
    return {
        "source": {
            "database": "Neo4j",
            "uri": "bolt://100.23.76.198:7687",
            "database_name": "neo4j",
            "username": "neo4j",
            "access_mode": "read-only",
        },
        "export": {
            "nodes_csv": "data/nodes.csv",
            "relationships_csv": "data/relationships.csv",
            "nodes_count": 14753,
            "relationships_count": 92342,
            "export_completeness": "100%",
            "properties_preserved": "100%",
        },
        "graph_construction": {
            "directed_graph": "NetworkX MultiDiGraph (14,753 nodes, 92,342 edges)",
            "undirected_graph": "NetworkX Graph (14,753 nodes, 91,823 edges)",
            "igraph": "igraph Graph (14,753 vertices, 91,823 edges)",
            "relationship_subgraphs": "23 subgraphs (one per relationship type)",
        },
        "algorithm_execution": {
            "total_algorithms": 56,
            "completed": 50,
            "requires_parameters": 6,
            "failed": 0,
            "manifest_file": str(MANIFEST_CSV),
            "summary_file": str(SUMMARY_CSV),
        },
    }


def get_algorithm_metadata(algorithm_key: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific algorithm."""
    return ALGORITHM_REGISTRY.get(algorithm_key)


def get_all_algorithm_metadata() -> Dict[str, Any]:
    """Get all algorithm metadata."""
    return ALGORITHM_REGISTRY


def get_algorithms_by_category(category: str) -> Dict[str, Any]:
    """Filter algorithms by category."""
    return {k: v for k, v in ALGORITHM_REGISTRY.items() if v["category"] == category}


def get_limitations(algorithm_key: Optional[str] = None) -> List[str]:
    """Get limitations for a specific algorithm or global."""
    if algorithm_key and algorithm_key in ALGORITHM_REGISTRY:
        return ALGORITHM_REGISTRY[algorithm_key].get("limitations", [])
    return GLOBAL_LIMITATIONS


def load_manifest() -> pd.DataFrame:
    """Load algorithm manifest CSV."""
    if MANIFEST_CSV.exists():
        return pd.read_csv(MANIFEST_CSV)
    return pd.DataFrame()


def load_summary() -> pd.DataFrame:
    """Load algorithm summary CSV."""
    if SUMMARY_CSV.exists():
        return pd.read_csv(SUMMARY_CSV)
    return pd.DataFrame()