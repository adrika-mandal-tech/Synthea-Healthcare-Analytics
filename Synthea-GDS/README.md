# Synthea Graph Analytics

This repository builds a healthcare graph analytics pipeline from a Neo4j export into a local, reproducible analysis workflow. The project models clinical and healthcare relationships as a graph, applies multiple algorithm families, and exports the results to CSV files for further analysis, presentation, and downstream machine learning.

## Project objective

The system is designed to answer questions such as:

- Which nodes are most important in the healthcare network?
- Which entities cluster into communities or similar care groups?
- Which pathways are shortest, strongest, or most central?
- Which entities are structurally important as bridges or bottlenecks?
- How can graph embeddings be used for similarity and prediction tasks?

## Core dataset

- Source: Synthea COVID-19 healthcare graph export
- Nodes: 14,753
- Directed relationships: 92,342
- Relationship types: 23
- Node labels: 16
- Verified COVID-19 evidence: condition and reason text includes entries such as "COVID-19" and "Suspected COVID-19"
- Initial graph representation: MultiDiGraph with local undirected and igraph variants for different algorithms

## Pipeline phases

### 1. Data export

The project connects to Neo4j using a read-only Bolt connection and exports the graph snapshot into local CSVs:

- data/nodes.csv
- data/relationships.csv

This protects the live graph while creating a reproducible analysis dataset.

### 2. Graph construction

The project rebuilds the graph in Python using NetworkX and igraph. Different graph views are created based on the algorithm type:

- MultiDiGraph for directed algorithms
- Undirected Graph for community and similarity analysis
- igraph object for efficient clustering workflows
- relationship-specific graph variants for filtered analysis

### 3. Algorithm execution

The project covers six major algorithm families:

1. Centrality
   - PageRank
   - Betweenness Centrality
   - Degree Centrality
   - Closeness Centrality
   - Eigenvector Centrality
   - Harmonic Centrality
   - ArticleRank
   - HITS
   - Articulation Points
   - Bridges
   - CELF

2. Community detection
   - Louvain
   - Leiden
   - Label Propagation
   - K-Core
   - K-Means
   - Triangle Count
   - Clustering Coefficient
   - Modularity
   - Clique Counting
   - SCC / WCC
   - Approximate Max k-Cut

3. Similarity
   - Node Similarity
   - Filtered Node Similarity
   - K-Nearest Neighbors
   - Filtered KNN

4. Pathfinding and connectivity
   - Dijkstra
   - Bellman-Ford
   - A*
   - Yen
   - BFS
   - DFS
   - Minimum Spanning Tree
   - Random Walk
   - Longest Path and DAG traversals

5. DAG analysis
   - Topological Sort
   - Longest Path

6. Embeddings
   - Node2Vec
   - FastRP
   - GraphSAGE
   - HashGNN
   - FastPath

## Result inventory

The project produces the following outputs:

- centrality: 11 CSV files
- community: 17 CSV files
- dag: 2 CSV files
- data: 2 CSV files
- embeddings: 5 CSV files
- paths: 12 CSV files
- reports: 2 CSV files
- similarity: 4 CSV files

Total actual CSV outputs: 55

## Manifest summary

The project manifest records 56 algorithm entries in total:

- Completed: 46
- Requires parameters: 10
- Failed: 0

This distinction is important: a method marked as requires_parameters is not necessarily a broken method, but a method that needs a specific configuration, feature matrix, or domain setting before it can run productively.

## Why HDBSCAN did not produce a final output

HDBSCAN is included in the project manifest as a parameter-dependent algorithm, not as a failed algorithm. This is because HDBSCAN requires a dense numerical feature matrix to cluster points. A raw graph structure alone does not provide the dense matrix input that HDBSCAN expects.

The project records this as:

- algorithm: HDBSCAN
- status: requires_parameters
- parameters: feature_matrix
- output_file: none

This is not a runtime error; it is a modeling constraint. If the pipeline is extended with node features, embeddings, or patient-level attributes, HDBSCAN can be executed properly.

## Technologies used

- Neo4j
- Python
- NetworkX
- igraph
- pandas
- NumPy
- SciPy
- scikit-learn
- python-louvain
- leidenalg
- hdbscan
- Mermaid / HTML for presentation artifacts

## Reporting

The repository includes reports in the reports folder:

- reports/algorithm_manifest.csv
- reports/algorithm_summary.csv

These files capture execution metadata, status, output location, libraries used, and notes for each algorithm. They are essential for documenting the analytic workflow and validating the generated outputs.

## Design strengths

- Captures complex relationships in a healthcare network
- Supports multiple algorithmic lenses on the same graph
- Keeps the graph source stable through export-based analysis
- Produces portable, shareable CSV outputs
- Enables explainable analytics and machine learning-ready feature generation

## Design limitations

- Some algorithms need feature engineering or explicit parameters
- Global graph analytics can be computationally expensive
- Graph formulation strongly affects algorithm behavior
- Not all algorithms are appropriate for raw topology alone

## Final takeaway

This project transforms healthcare data from a transactional or relational source into a graph intelligence layer. It supports ranking, clustering, route analysis, similarity measurement, and representation learning in a single workflow. It is best understood as a graph-based analytics system with strong clinical and methodological potential, while also acknowledging that some algorithms require richer inputs than a bare graph snapshot provides.
