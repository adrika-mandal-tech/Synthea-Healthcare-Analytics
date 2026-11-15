# PROJECT_AUDIT.md — GenAI Graph Intelligence & GraphRAG Platform

**Generated:** 2026-09-22  
**Project:** Synthea Healthcare Graph Analytics  
**Phase:** 0 — Complete Repository Audit

---

## 1. Current Architecture Overview

### 1.1 System Summary
The existing project is a **read-only graph analytics pipeline** that:
- Exports a Neo4j healthcare graph (14,753 nodes, 92,342 directed edges, 23 relationship types, 16 node labels)
- Rebuilds the graph locally using NetworkX, igraph, and pandas
- Executes 56 graph algorithms across 6 families
- Produces 55 CSV datasets as outputs
- Generates documentation in HTML and Markdown formats

### 1.2 Data Flow
```
Neo4j (bolt://100.23.76.198:7687)
    ↓ Read-only export
data/nodes.csv (5.6 MB) + data/relationships.csv (10.2 MB)
    ↓ Graph construction
Python: NetworkX MultiDiGraph, Undirected Graph, igraph, 23 relationship-type subgraphs
    ↓ Algorithm execution (6 families)
    ├─ Centrality (11 algos) → centrality/*.csv (11 files)
    ├─ Community (17 algos) → community/*.csv (17 files)
    ├─ Similarity (4 algos) → similarity/*.csv (4 files)
    ├─ Paths (12 completed) → paths/*.csv (12 files)
    ├─ DAG (2 algos) → dag/*.csv (2 files)
    └─ Embeddings (5 algos) → embeddings/*.csv (5 files)
    ↓ Reporting
reports/algorithm_manifest.csv + reports/algorithm_summary.csv
```

### 1.3 Technology Stack
| Category | Libraries |
|----------|-----------|
| Core | Python 3.14, pandas, NumPy, SciPy |
| Graph | NetworkX, igraph |
| Community | python-louvain, leidenalg, cdlib |
| ML/Embeddings | scikit-learn, node2vec, gensim, hdbscan |
| Database | neo4j-driver |
| Documentation | Mermaid.js, HTML |

---

## 2. Existing Components Inventory

### 2.1 Raw Data
| File | Size | Records | Description |
|------|------|---------|-------------|
| `data/nodes.csv` | 5.6 MB | 14,753 | All nodes with labels and properties |
| `data/relationships.csv` | 10.2 MB | 92,342 | All directed relationships with properties |

### 2.2 Centrality Outputs (11 files)
| File | Algorithm | Status | Nodes | Notes |
|------|-----------|--------|-------|-------|
| `degree_centrality.csv` | Degree Centrality | Completed | 14,753 | Normalized neighbor count |
| `betweenness_centrality.csv` | Betweenness Centrality | Completed | 14,753 | Brandes algorithm, 365s runtime |
| `closeness_centrality.csv` | Closeness Centrality | Completed | 14,753 | 67s runtime |
| `eigenvector_centrality.csv` | Eigenvector Centrality | Completed | 14,753 | Power iteration, 2s |
| `harmonic_centrality.csv` | Harmonic Centrality | Completed | 14,753 | 84s runtime |
| `pagerank.csv` | PageRank | Completed | 14,753 | α=0.85, 0.13s |
| `article_rank.csv` | ArticleRank | Completed | 14,753 | Avg-neighbor-degree damping |
| `hits.csv` | HITS | Completed | 14,753 | Hub/authority on directed graph |
| `articulation_points.csv` | Articulation Points | Completed | 96 | DFS-based |
| `bridges.csv` | Bridges | Completed | 96 | Tarjan's algorithm |
| `celf.csv` | CELF | Completed | 10 | Top-k degree (k=10) |

**Key metrics from docs:** Degree max 0.4406% (HEALTHALLIANCE HOSPITALS INC), Betweenness max 0.00287%, PageRank max 0.340%

### 2.3 Community Detection Outputs (17 files)
| File | Algorithm | Status | Communities | Modularity | Notes |
|------|-----------|--------|-------------|------------|-------|
| `louvain.csv` | Louvain | Completed | 14 | 0.4994 | python-louvain |
| `leiden.csv` | Leiden | Completed | 15 | 0.4996 | leidenalg/igraph |
| `label_propagation.csv` | Label Propagation | Completed | 46 | — | NetworkX |
| `sllpa.csv` | Speaker-Listener LPA | Completed | 10 | — | 50 iterations, 10 patient seeds |
| `k_core.csv` | K-Core Decomposition | Completed | 22 (max core) | — | NetworkX |
| `kmeans.csv` | K-Means | Completed | 13 | — | 4 features: degree, pagerank, clustering, triangles |
| `hdbscan.csv` | HDBSCAN | Requires params | — | — | Needs feature matrix |
| `triangle_count.csv` | Triangle Count | Completed | — | — | 159,278 cliques |
| `clustering_coefficient.csv` | Local Clustering | Completed | — | — | NetworkX |
| `wcc.csv` | Weakly Connected Components | Completed | 1 | — | Entire network connected |
| `scc.csv` | Strongly Connected Components | Completed | 14,753 | — | Each node its own SCC |
| `conductance.csv` | Conductance | Completed | 13 | — | Per-community |
| `modularity.csv` | Modularity | Completed | — | 0.4980 | Single Q value |
| `modularity_optimization.csv` | Modularity Optimization | Completed | — | 0.4980 | Repeated best-partition |
| `k1_coloring.csv` | K-1 Coloring | Completed | 5 | — | Largest-first greedy |
| `approx_max_kcut.csv` | Approx Max k-cut | Completed | 5 | — | Top-5 Louvain by size |
| `clique_count.csv` | Clique Counting | Completed | 159,278 | — | All cliques enumerated |

### 2.4 Similarity Outputs (4 files)
| File | Algorithm | Status | Records | Notes |
|------|-----------|--------|---------|-------|
| `node_similarity.csv` | Node Similarity | Completed | 200 | Jaccard, 20 patients, top-10 |
| `filtered_node_similarity.csv` | Filtered Node Similarity | Completed | 200 | Patient-Patient only |
| `knn.csv` | K-Nearest Neighbors | Completed | 200 | k=10, Jaccard |
| `filtered_knn.csv` | Filtered KNN | Completed | 200 | Patient-Patient only |

**Important:** All similarity analysis is **sampled** (20 patients), not exhaustive.

### 2.5 Path Finding Outputs (12 files)
| File | Algorithm | Status | Notes |
|------|-----------|--------|-------|
| `dijkstra_source_target.csv` | Dijkstra Source-Target | Completed | 1 source→target pair |
| `dijkstra_single_source.csv` | Dijkstra Single-Source | Completed | 1 source |
| `bellman_ford.csv` | Bellman-Ford | Completed | 1 source |
| `astar.csv` | A* (zero heuristic) | Completed | 1 pair |
| `yen.csv` | Yen's k=5 | Completed | 1 pair |
| `bfs.csv` | Breadth First Search | Completed | 1 source |
| `dfs.csv` | Depth First Search | Completed | 1 source |
| `random_walk.csv` | Random Walk | Completed | 5 patients, 50 steps |
| `minimum_weight_spanning_tree.csv` | MST | Completed | 14,752 edges |
| `prize_collecting_steiner_tree.csv` | Prize-Collecting Steiner | Completed | Degree prizes, 10 terminals |
| `minimum_weight_k_spanning_tree.csv` | Min Weight k-Spanning Tree | Completed | k=5 |
| `longest_path_dag.csv` | Longest Path DAG | Completed | 2 patients, max_length=20 |

### 2.6 DAG Outputs (2 files)
| File | Algorithm | Status | Notes |
|------|-----------|--------|-------|
| `topological_sort.csv` | Topological Sort | Completed | Kahn's algorithm |
| `longest_path.csv` | Longest Path | Completed | Topological order + DP |

### 2.7 Embedding Outputs (5 files)
| File | Algorithm | Status | Dimensions | Notes |
|------|-----------|--------|------------|-------|
| `node2vec.csv` | Node2Vec | Completed | 128 | Random walks + Skip-gram |
| `fastrp.csv` | FastRP | Completed | 128 | Gaussian Random Projection |
| `graphsage.csv` | GraphSAGE | Completed | 128 | Mean aggregation + Ridge |
| `hashgnn.csv` | HashGNN | Completed | 128 | Random hashing |
| `fastpath.csv` | FastPath | Completed | 128 | Shortest-path distance vectors |

### 2.8 Reports
| File | Description |
|------|-------------|
| `algorithm_manifest.csv` | 58 rows: algorithm, category, status, output, library, params, runtime, nodes, edges, notes |
| `algorithm_summary.csv` | Aggregated counts: completed, requires_parameters, failed |
| `community_detection_summary.csv` | 18 rows comparing all community algorithms |

---

## 3. Reusable Components

### 3.1 Core Infrastructure (High Reuse Value)
| Component | Location | Reuse Strategy |
|-----------|----------|----------------|
| Graph loading pipeline | `pipeline.py:load_graphs()` | Refactor into `graph_intelligence/analytics/graph_loader.py` |
| CSV writing utilities | `pipeline.py:safe_write_csv()` | Reuse directly |
| Manifest logging | `pipeline.py:append_manifest()` | Extend for new analytics |
| Node/label lookup | `get_labels()`, `get_name()` | Move to shared utilities |

### 3.2 Computed Analytics (Direct Integration)
All 55 CSV files are **ready-to-use fact sources**. No recomputation needed.

### 3.3 Documentation (Reference)
- `1.docs/explain_analysis.html` — Complete architecture diagram, algorithm directory
- `1.docs/Healthcare Graph Data Science Insights & Methodology.md` — Clinical context, schema
- `1.docs/explain.md` — Algorithm explanations table
- `1.docs/accuracy_metrics.md` — Validation metrics

---

## 4. Missing Components for GenAI Graph Intelligence Platform

### 4.1 Graph Intelligence Knowledge Layer
| Missing Component | Purpose |
|-------------------|---------|
| `graph_facts.py` | Unified entity fact table joining all centrality/community/embedding metrics |
| `entity_facts.py` | Per-entity structured facts (degree, pagerank, betweenness, community, embedding) |
| `community_facts.py` | Per-community statistics (size, modularity, composition, centrality stats) |
| `relationship_facts.py` | Relationship-type statistics and patterns |
| `analytics_metadata.py` | Provenance, algorithm parameters, sampling notes |

### 4.2 Retrieval Layer
| Missing Component | Purpose |
|-------------------|---------|
| `graph_retriever.py` | Graph structure: neighbors, paths, subgraphs |
| `analytics_retriever.py` | Centrality, community, similarity lookups |
| `embedding_retriever.py` | Vector similarity search on embeddings |
| `entity_resolver.py` | Name/ID fuzzy matching for user queries |
| `evidence_assembler.py` | Combine retrieved facts into evidence packages |

### 4.3 GraphRAG & Agent Layer
| Missing Component | Purpose |
|-------------------|---------|
| `query_planner.py` | Decompose natural language → retrieval plan |
| `graph_rag.py` | Orchestrate multi-source retrieval + evidence assembly |
| `reasoning.py` | LLM reasoning over evidence |
| `validation.py` | Critic: claim verification against evidence |
| `agent/tools.py` | Tool definitions for LangGraph agent |
| `agent/graph_agent.py` | LangGraph workflow: planner → retrievers → assembler → reasoner → critic |

### 4.4 Visualization Layer
| Missing Component | Purpose |
|-------------------|---------|
| `visualization/graph.py` | Interactive subgraph (Plotly/NetworkX) |
| `visualization/communities.py` | Community-level views |
| `visualization/centrality.py` | Centrality distributions, top-N |
| `visualization/embeddings.py` | UMAP/PCA projections |
| `visualization/robustness.py` | Fragmentation curves |

### 4.5 Streamlit Application
| Missing Page | Purpose |
|--------------|---------|
| `app/pages/01_Graph_Overview.py` | Graph health, density, labels, degree distribution |
| `app/pages/02_Graph_Copilot.py` | GenAI Q&A with evidence + graph viz |
| `app/pages/03_Community_Intelligence.py` | Leiden/Louvain comparison, community details |
| `app/pages/04_Entity_Intelligence.py` | Entity profile + "Explain with GenAI" |
| `app/pages/05_Similarity_Cohorts.py` | Similarity networks, nearest neighbors |
| `app/pages/06_Embedding_Intelligence.py` | Embedding projections, clustering |
| `app/pages/07_Structural_Anomalies.py` | Anomaly candidates with metrics |
| `app/pages/08_Robustness.py` | Targeted vs random removal analysis |

---

## 5. Risks & Constraints

### 5.1 Data Constraints
| Risk | Impact | Mitigation |
|------|--------|------------|
| **Sampled similarity** | Only 20 patients analyzed | Clearly label as sampled; don't present as population-wide |
| **Static snapshot** | No temporal evolution | Document as point-in-time analysis |
| **Undirected approximations** | Some algorithms lose directionality | Note which metrics used directed vs undirected |
| **No Neo4j GDS** | Cannot re-run server-side algorithms | Use local cached CSVs only |
| **HDBSCAN incomplete** | No output produced | Exclude from platform or note as unavailable |

### 5.2 Technical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **14k nodes in memory** | Acceptable for Python/NetworkX | Cache loaded graphs; use dictionaries for O(1) lookups |
| **Embedding vectors** | 14k × 128 = ~7MB per method | Load on demand; use numpy memmap if needed |
| **LLM hallucination** | High risk for graph claims | Implement evidence validator (critic) |
| **API key management** | Security | Use .env, never commit secrets |

### 5.3 Clinical/Compliance
| Risk | Impact | Mitigation |
|------|--------|------------|
| **Synthetic patient data** | Not real PHI | Still treat with care; no clinical claims |
| **Graph patterns ≠ clinical outcomes** | Misinterpretation risk | Explicit disclaimers: "structural pattern only" |

---

## 6. Proposed Architecture (MVP → Full)

### 6.1 MVP Scope (Phase 1-3)
```
1. Graph Overview (Streamlit page)
2. Entity Investigator (select entity → metrics + neighborhood + GenAI explain)
3. Graph Copilot (natural language Q&A with evidence)
4. Evidence Validator (critic layer)
5. Interactive Subgraph Visualization (Plotly)
```

**Demo Question:** "Which entities are important bridges between communities, and why?"

**Pipeline:**
```
USER QUESTION
    ↓
QUERY CLASSIFIER / PLANNER
    ↓
CENTRALITY RETRIEVER (betweenness, degree)
    ↓
COMMUNITY RETRIEVER (Leiden, Louvain membership)
    ↓
GRAPH RETRIEVER (neighbors, cross-community edges)
    ↓
EVIDENCE ASSEMBLER (structured evidence package)
    ↓
LLM REASONER (explanation grounded in evidence)
    ↓
CRITIC / VALIDATOR (claim → evidence check)
    ↓
FINAL ANSWER + INTERACTIVE GRAPH
```

### 6.2 Full Platform (Phase 4-6)
Add: Similarity/Cohorts, Embedding Intelligence, Structural Anomalies, Robustness, Automated Reports

### 6.3 Directory Structure (Target)
```
graph_intelligence/
├── analytics/              # Refactored from pipeline.py
│   ├── graph_loader.py
│   ├── centrality.py
│   ├── communities.py
│   ├── similarity.py
│   ├── embeddings.py
│   ├── paths.py
│   └── robustness.py
├── intelligence/
│   ├── graph_facts.py      # Unified fact tables
│   ├── evidence.py         # Evidence package schema
│   ├── entity_resolution.py
│   ├── query_planner.py
│   ├── retrieval.py        # Graph/Analytics/Embedding retrievers
│   ├── graph_rag.py        # RAG orchestration
│   ├── reasoning.py        # LLM reasoning
│   └── validation.py       # Critic/validator
├── agents/
│   ├── graph_agent.py      # LangGraph workflow
│   ├── tools.py            # Agent tool definitions
│   └── prompts.py          # System prompts
├── embeddings/             # Existing CSV files (symlinked)
├── visualization/
│   ├── graph.py
│   ├── communities.py
│   ├── centrality.py
│   ├── embeddings.py
│   └── robustness.py
├── app/
│   ├── app.py              # Streamlit entry
│   ├── pages/              # 8 pages
│   └── components/         # Shared UI components
├── reports/                # Auto-generated reports
├── tests/
└── config/
    └── settings.yaml       # LLM provider, paths, etc.
```

---

## 7. Implementation Phases

### PHASE 0 — AUDIT ✅ COMPLETE
- [x] Repository inspection
- [x] CSV inventory
- [x] Code review
- [x] Documentation review
- [x] PROJECT_AUDIT.md created

### PHASE 1 — GRAPH INTELLIGENCE DATA LAYER
**Files to create:**
1. `graph_intelligence/analytics/graph_loader.py` — Refactored from `pipeline.py:load_graphs()`
2. `graph_intelligence/intelligence/graph_facts.py` — Entity fact table (join all CSVs by node_id)
3. `graph_intelligence/intelligence/community_facts.py` — Community statistics
4. `graph_intelligence/intelligence/analytics_metadata.py` — Provenance metadata

**Key deliverable:** `entity_facts.parquet` or CSV with columns:
```
node_id, labels, name, degree, pagerank, betweenness, closeness, eigenvector, harmonic,
article_rank, hits_hub, hits_authority, leiden_community, louvain_community, k_core,
clustering_coefficient, triangle_count, node2vec_embedding, fastrp_embedding, ...
```

### PHASE 2 — RETRIEVAL LAYER
**Files to create:**
1. `graph_intelligence/intelligence/retrieval.py` — Base retriever classes
2. `graph_intelligence/intelligence/graph_retriever.py` — Neighbors, paths, subgraphs
3. `graph_intelligence/intelligence/analytics_retriever.py` — Centrality/community lookups
4. `graph_intelligence/intelligence/embedding_retriever.py` — Vector similarity
5. `graph_intelligence/intelligence/entity_resolution.py` — Fuzzy name/ID matching
6. `graph_intelligence/intelligence/evidence.py` — EvidencePackage dataclass
7. `graph_intelligence/intelligence/evidence_assembler.py` — Combine multi-source evidence

**Tests:** Unit tests for each retriever returning structured data (not text blobs)

### PHASE 3 — AGENT WORKFLOW
**Files to create:**
1. `graph_intelligence/agents/tools.py` — Tool definitions (get_entity, get_community, find_bridges, etc.)
2. `graph_intelligence/agents/prompts.py` — System prompts for each agent node
3. `graph_intelligence/agents/graph_agent.py` — LangGraph workflow

**Workflow nodes:**
- `planner` → `graph_retriever` → `analytics_retriever` → `embedding_retriever` → `evidence_assembler` → `reasoner` → `critic` → `formatter`

### PHASE 4 — VALIDATION LAYER
**Files to create:**
1. `graph_intelligence/intelligence/validation.py` — Claim extraction + evidence matching
2. Metrics: evidence_coverage, unsupported_claims, validation_status

### PHASE 5 — STREAMLIT UI (MVP Pages)
**Files to create:**
1. `app/app.py` — Entry point, config, session state
2. `app/pages/01_Graph_Overview.py`
3. `app/pages/02_Graph_Copilot.py`
4. `app/pages/03_Community_Intelligence.py`
5. `app/pages/04_Entity_Intelligence.py`
6. `app/components/` — Shared: evidence_panel, graph_viz, metric_cards

### PHASE 6 — ADDITIONAL PAGES & REPORTING
**Files to create:**
1. `app/pages/05_Similarity_Cohorts.py`
2. `app/pages/06_Embedding_Intelligence.py`
3. `app/pages/07_Structural_Anomalies.py`
4. `app/pages/08_Robustness.py`
5. `graph_intelligence/intelligence/reporting.py` — Executive + technical report generation

---

## 8. Exact Files to Create/Modify

### New Files (Priority Order)
| Phase | File | Description |
|-------|------|-------------|
| 1 | `graph_intelligence/analytics/graph_loader.py` | Cached graph loading |
| 1 | `graph_intelligence/intelligence/graph_facts.py` | Unified entity fact table builder |
| 1 | `graph_intelligence/intelligence/community_facts.py` | Community statistics |
| 1 | `graph_intelligence/intelligence/analytics_metadata.py` | Provenance tracking |
| 2 | `graph_intelligence/intelligence/retrieval.py` | Base retriever classes |
| 2 | `graph_intelligence/intelligence/graph_retriever.py` | Graph structure retrieval |
| 2 | `graph_intelligence/intelligence/analytics_retriever.py` | Analytics retrieval |
| 2 | `graph_intelligence/intelligence/embedding_retriever.py` | Embedding retrieval |
| 2 | `graph_intelligence/intelligence/entity_resolution.py` | Entity name/ID resolution |
| 2 | `graph_intelligence/intelligence/evidence.py` | EvidencePackage schema |
| 2 | `graph_intelligence/intelligence/evidence_assembler.py` | Evidence assembly |
| 3 | `graph_intelligence/agents/tools.py` | Agent tool definitions |
| 3 | `graph_intelligence/agents/prompts.py` | System prompts |
| 3 | `graph_intelligence/agents/graph_agent.py` | LangGraph workflow |
| 4 | `graph_intelligence/intelligence/validation.py` | Critic/validator |
| 5 | `app/app.py` | Streamlit entry |
| 5 | `app/pages/01_Graph_Overview.py` | Graph overview page |
| 5 | `app/pages/02_Graph_Copilot.py` | GenAI Q&A page |
| 5 | `app/pages/03_Community_Intelligence.py` | Community page |
| 5 | `app/pages/04_Entity_Intelligence.py` | Entity page |
| 5 | `app/components/evidence_panel.py` | Evidence display component |
| 5 | `app/components/graph_viz.py` | Interactive graph component |
| 5 | `config/settings.yaml` | Configuration |

### Existing Files to Refactor (Not Rewrite)
| File | Action |
|------|--------|
| `pipeline.py` | Extract `load_graphs()` → `graph_loader.py`; keep for reference |
| `run_parameterized.py` | Reference for advanced algorithms; don't modify |
| `1.docs/*` | Reference only; update README later |

### Files to NOT Touch
| File | Reason |
|------|--------|
| All CSV files in `centrality/`, `community/`, `similarity/`, `paths/`, `dag/`, `embeddings/`, `data/` | Source of truth — read only |
| `reports/algorithm_manifest.csv` | Reference metadata |
| `reports/community_detection_summary.csv` | Reference metadata |
| `1.docs/explain_analysis.html` | Documentation reference |

---

## 9. Configuration Requirements

### 9.1 Environment Variables (`.env`)
```bash
# Neo4j (read-only, for potential live queries)
NEO4J_URI=bolt://100.23.76.198:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# LLM Provider
LLM_PROVIDER=openai  # or anthropic, etc.
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=your_key_here
LLM_TEMPERATURE=0.1

# App
STREAMLIT_SERVER_PORT=8501
```

### 9.2 Settings YAML (`config/settings.yaml`)
```yaml
data:
  nodes_csv: "data/nodes.csv"
  relationships_csv: "data/relationships.csv"
  centrality_dir: "centrality"
  community_dir: "community"
  similarity_dir: "similarity"
  paths_dir: "paths"
  dag_dir: "dag"
  embeddings_dir: "embeddings"
  reports_dir: "reports"

graph:
  node_count: 14753
  edge_count: 92342
  labels: 16
  relationship_types: 23

retrieval:
  entity_cache_size: 15000
  embedding_cache: true
  similarity_sample_warning: true

llm:
  provider: "${LLM_PROVIDER}"
  model: "${LLM_MODEL}"
  temperature: 0.1
  max_tokens: 2000

validation:
  enabled: true
  evidence_coverage_threshold: 0.8
```

---

## 10. Next Steps

### Immediate (Start Phase 1)
1. Create `graph_intelligence/` directory structure
2. Build `graph_loader.py` with cached NetworkX/igraph loading
3. Build `graph_facts.py` to join all 55 CSVs into unified entity fact table
4. Verify fact table covers all 14,753 nodes with all available metrics

### Validation Checkpoints
- [ ] Fact table has 14,753 rows
- [ ] All 11 centrality metrics present
- [ ] Both Leiden and Louvain community IDs present
- [ ] All 5 embedding previews available
- [ ] Sampling warnings attached to similarity data
- [ ] Provenance metadata for every column

---

## Appendix: Key Data Samples

### Node ID Format
`4:253b872d-af12-4342-b04a-518b6fc7dd81:0` (Neo4j elementId format)

### Top Node by Degree/PageRank
- **HEALTHALLIANCE HOSPITALS INC** (Organization) — element_id `:0`
- Degree: 0.4406%, PageRank: 0.340%

### Community Comparison
| Algorithm | Communities | Modularity |
|-----------|-------------|------------|
| Louvain | 14 | 0.4994 |
| Leiden | 15 | 0.4996 |

### Sampled Analyses (Must Flag)
- Node Similarity: 20 patients × top-10 = 200 pairs
- KNN: 20 patients × top-10 = 200 pairs
- Path algorithms: 1-5 source nodes only
- Random Walk: 5 patients × 50 steps

---

**End of Audit** — Ready for Phase 1 implementation.