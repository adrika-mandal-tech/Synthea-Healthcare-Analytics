# Synthea Graph Analytics — Algorithm Explanations & Usages

## 1. Centrality Algorithms

| Algorithm | Explanation & Usage | Library Used |
|---|---|---|
| **ArticleRank** | PageRank variant with avg-neighbor-degree damping. Reduces rank-spam. | NetworkX |
| **Articulation Points** | Nodes whose removal increases connected components. | NetworkX |
| **Betweenness Centrality** | Fraction of shortest paths passing through a node. Finds referral brokers. | NetworkX |
| **Bridges** | Edges whose removal disconnects the graph. | NetworkX |
| **CELF** | Influence maximization approximated via top-k degree centrality (k=10). | NetworkX + python-louvain |
| **Closeness Centrality** | Inverse of sum of shortest path distances. | NetworkX |
| **Degree Centrality** | Normalized neighbor count. | NetworkX |
| **Eigenvector Centrality** | Importance proportional to neighbor importance via power iteration. | NetworkX |
| **Harmonic Centrality** | Sum of inverse distances; handles disconnected subgraphs. | NetworkX |
| **PageRank** | Random surfer model (α=0.85). | NetworkX |
| **HITS** | Hub/authority scores via power iteration on directed graph. | NetworkX |

## 2. Community Detection Algorithms

| Algorithm | Explanation & Usage | Library Used |
|---|---|---|
| **Clique Counting** | Enumerates complete subgraphs. 159,278 cliques found. | NetworkX |
| **Conductance** | Per-community edge boundary ratio. | NetworkX |
| **K-Core Decomposition** | Iterative removal of nodes with degree < k. | NetworkX |
| **K-1 Coloring** | Greedy coloring; adjacent nodes differ. | NetworkX |
| **K-Means Clustering** | k=13 on degree, PageRank, clustering, triangles. | scikit-learn |
| **Label Propagation** | Asynchronous label adoption. | NetworkX |
| **Leiden** | Hierarchical modularity; 15 communities, Q=0.4996. | leidenalg/igraph |
| **Local Clustering Coefficient** | Fraction of possible triangles that exist. | NetworkX |
| **Louvain** | Greedy modularity; 14 communities, Q=0.4994. | python-louvain |
| **Modularity** | Single Q value for partition quality. | python-louvain |
| **Modularity Optimization** | Repeated best-partition modularity. | python-louvain |
| **Connected Components (SCC/WCC)** | WCC: 1 component. SCC: 14,753 components. | NetworkX |
| **Triangle Count** | Closed triplets per node. | NetworkX |
| **Approx Max k-cut** | Top-5 Louvain communities by size, k=5. | NetworkX + python-louvain |
| **Speaker-Listener Label Propagation** | 50 iterations, 10 patient seeds. | NetworkX + custom |
| **HDBSCAN** | Requires dense feature matrix; no CSV produced. | hdbscan |

## 3. Path-Finding Algorithms

| Algorithm | Explanation & Usage | Library Used |
|---|---|---|
| **Dijkstra Source-Target** | Bidirectional Dijkstra from patient to encounter. | NetworkX |
| **Dijkstra Single-Source** | Shortest paths from one patient to all reachable nodes. | NetworkX |
| **Bellman-Ford SSSP** | V-1 relaxation; handles negative weights. | NetworkX |
| **A* Shortest Path** | Heuristic-guided; zero heuristic used. | NetworkX |
| **Yen's Shortest Path** | k=5 shortest simple paths. | NetworkX |
| **Breadth First Search** | Layer-by-layer traversal. | NetworkX |
| **Depth First Search** | Deep-first traversal. | NetworkX |
| **Random Walk** | 50-step stochastic from 5 patients. | NetworkX |
| **Minimum Weight Spanning Tree** | Kruskal/Prim on undirected graph. | NetworkX |
| **Minimum Directed Steiner Tree** | Shortest path union to terminals. | NetworkX |
| **Prize-collecting Steiner Tree** | Degree prizes, top-10 terminals. | Custom |
| **Maximum Flow** | Unit capacity patients→payers. | NetworkX |
| **Minimum Cost Maximum Flow** | Unit cost, maximize flow. | NetworkX |
| **Minimum Weight k-Spanning Tree** | MST minus k-1 most expensive edges. | NetworkX |
| **All Pairs Shortest Path** | O(n³); run on subset if needed. | NetworkX |
| **Longest Path for DAG** | Bounded DFS, max_length=20. | NetworkX |

## 4. Similarity Algorithms

| Algorithm | Explanation & Usage | Library Used |
|---|---|---|
| **Node Similarity** | Jaccard on neighbor sets, top-k=10. | NetworkX |
| **Filtered Node Similarity** | Jaccard, Patient-Patient only. | NetworkX |
| **K-Nearest Neighbors** | Jaccard, k=10, 20 sampled patients. | NetworkX |
| **Filtered KNN** | Jaccard, Patient-Patient only. | NetworkX |

## 5. Node Embedding Algorithms

| Algorithm | Explanation & Usage | Library Used |
|---|---|---|
| **FastRP** | Gaussian Random Projection, 128-dim. | scikit-learn + numpy |
| **GraphSAGE** | Mean aggregation + Ridge regression. | scikit-learn + numpy |
| **Node2Vec** | Random walks + Skip-gram, 128-dim. | node2vec + gensim |
| **HashGNN** | Random hashing of neighbors, 128-dim. | numpy |
| **FastPath** | Shortest path distance vectors, cutoff=5. | NetworkX + numpy |

## 6. Understanding HDBSCAN

HDBSCAN requires a dense numerical feature matrix as input, not graph topology alone. It was marked `requires_parameters` in the primary pipeline. While a feature matrix can be derived from centrality measures (degree, PageRank, clustering, triangles), this representation may not capture sufficient structural information for meaningful density-based clustering. Alternatives—Leiden (modularity 0.4996) and K-Means (k=13)—have already produced high-quality community structures.
