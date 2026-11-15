"""
Graph Intelligence Platform — Retrieval Layer

Provides structured retrieval for graph structure, analytics, and embeddings.
Each retriever returns structured data, not text blobs.
"""

import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
import networkx as nx

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

# ---------------------------------------------------------------------------
# Evidence Package Data Structures
# ---------------------------------------------------------------------------

@dataclass
class EvidenceItem:
    """Single piece of evidence supporting a claim."""
    source: str  # e.g., "centrality/betweenness_centrality.csv"
    metric: str  # e.g., "betweenness_centrality"
    entity_id: str
    value: Any
    description: str
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidencePackage:
    """Structured evidence package for a query."""
    query: str
    retrieved_entities: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_relationships: List[Dict[str, Any]] = field(default_factory=list)
    analytics: List[EvidenceItem] = field(default_factory=list)
    communities: List[Dict[str, Any]] = field(default_factory=list)
    embeddings: List[Dict[str, Any]] = field(default_factory=list)
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    provenance: List[str] = field(default_factory=list)

    def add_evidence(self, item: EvidenceItem):
        self.evidence_items.append(item)
        if item.source not in self.provenance:
            self.provenance.append(item.source)

    def get_entities(self) -> List[str]:
        """Get unique entity IDs in evidence."""
        return list(set(item.entity_id for item in self.evidence_items))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "retrieved_entities": self.retrieved_entities,
            "retrieved_relationships": self.retrieved_relationships,
            "analytics": [{"source": e.source, "metric": e.metric, "entity_id": e.entity_id,
                          "value": e.value, "description": e.description} for e in self.analytics],
            "communities": self.communities,
            "embeddings": self.embeddings,
            "evidence_count": len(self.evidence_items),
            "provenance": self.provenance,
        }


# ---------------------------------------------------------------------------
# Base Retriever Interface
# ---------------------------------------------------------------------------

class BaseRetriever(ABC):
    """Base class for all retrievers."""

    @abstractmethod
    def retrieve(self, query: str, **kwargs) -> Any:
        """Retrieve data relevant to query."""
        pass

    @abstractmethod
    def get_evidence(self, entity_id: str, **kwargs) -> List[EvidenceItem]:
        """Get evidence items for a specific entity."""
        pass


# ---------------------------------------------------------------------------
# Graph Structure Retriever
# ---------------------------------------------------------------------------

class GraphRetriever(BaseRetriever):
    """Retrieves graph structure: neighbors, paths, subgraphs."""

    def __init__(self):
        self._graphs = None
        self._nodes_df = None
        self._rels_df = None

    def _ensure_loaded(self):
        if self._graphs is None:
            from graph_intelligence.analytics.graph_loader import get_graphs
            self._graphs = get_graphs()
            self._nodes_df = self._graphs["nodes_df"]
            self._rels_df = self._graphs["rels_df"]

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get basic entity info."""
        self._ensure_loaded()
        row = self._nodes_df[self._nodes_df["element_id"] == entity_id]
        if row.empty:
            return None
        r = row.iloc[0]
        return {
            "entity_id": entity_id,
            "labels": r.get("labels", ""),
            "name": r.get("name", "") or r.get("NAME", "") or r.get("Id", ""),
            "properties": {k: v for k, v in r.items()
                          if k not in ["element_id", "labels", "name", "NAME", "Id"]}
        }

    def get_neighbors(self, entity_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get immediate neighbors of an entity."""
        self._ensure_loaded()
        G = self._graphs["G"]  # directed

        neighbors = []
        # Outgoing edges
        for _, dst, data in G.out_edges(entity_id, data=True):
            n_info = self.get_entity(dst)
            if n_info:
                n_info["relationship"] = data.get("type", "")
                n_info["direction"] = "outgoing"
                neighbors.append(n_info)

        # Incoming edges
        for src, _, data in G.in_edges(entity_id, data=True):
            n_info = self.get_entity(src)
            if n_info:
                n_info["relationship"] = data.get("type", "")
                n_info["direction"] = "incoming"
                neighbors.append(n_info)

        return neighbors[:limit]

    def get_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for an entity."""
        self._ensure_loaded()
        G = self._graphs["G"]

        rels = []
        for _, dst, data in G.out_edges(entity_id, data=True):
            rels.append({
                "source": entity_id,
                "target": dst,
                "type": data.get("type", ""),
                "direction": "outgoing",
                "properties": {k: v for k, v in data.items() if k != "type"}
            })
        for src, _, data in G.in_edges(entity_id, data=True):
            rels.append({
                "source": src,
                "target": entity_id,
                "type": data.get("type", ""),
                "direction": "incoming",
                "properties": {k: v for k, v in data.items() if k != "type"}
            })
        return rels

    def get_subgraph(self, entity_ids: List[str], hops: int = 1) -> Dict[str, Any]:
        """Get induced subgraph around entities."""
        self._ensure_loaded()
        G = self._graphs["G_undirected"]

        # Collect nodes within hops
        all_nodes = set(entity_ids)
        for eid in entity_ids:
            if eid in G:
                for hop in range(hops):
                    new_nodes = set()
                    for n in all_nodes:
                        if n in G:
                            new_nodes.update(G.neighbors(n))
                    all_nodes.update(new_nodes)

        subgraph = G.subgraph(all_nodes)

        return {
            "nodes": [
                {
                    "entity_id": n,
                    "labels": self._nodes_df[self._nodes_df["element_id"] == n]["labels"].values[0] if n in self._nodes_df["element_id"].values else "",
                    "name": self._nodes_df[self._nodes_df["element_id"] == n]["name"].values[0] if n in self._nodes_df["element_id"].values else "",
                }
                for n in subgraph.nodes()
            ],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "type": data.get("type", ""),
                }
                for u, v, data in subgraph.edges(data=True)
            ],
            "node_count": subgraph.number_of_nodes(),
            "edge_count": subgraph.number_of_edges(),
        }

    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find shortest path between two entities."""
        self._ensure_loaded()
        G = self._graphs["G_undirected"]

        try:
            path = nx.shortest_path(G, source, target)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def retrieve(self, query: str, **kwargs) -> Dict[str, Any]:
        """Retrieve graph structure relevant to query."""
        # This would use entity resolution to find entities in query
        # For now, return empty - use specific methods
        return {"message": "Use specific methods: get_entity, get_neighbors, get_subgraph, etc."}

    def get_evidence(self, entity_id: str, **kwargs) -> List[EvidenceItem]:
        """Get graph structure evidence for entity."""
        self._ensure_loaded()
        evidence = []

        entity = self.get_entity(entity_id)
        if entity:
            evidence.append(EvidenceItem(
                source="graph/nodes.csv",
                metric="entity_info",
                entity_id=entity_id,
                value=entity,
                description=f"Entity: {entity['name']} ({entity['labels']})"
            ))

        neighbors = self.get_neighbors(entity_id, limit=20)
        if neighbors:
            evidence.append(EvidenceItem(
                source="graph/relationships.csv",
                metric="neighbors",
                entity_id=entity_id,
                value={"count": len(neighbors), "neighbors": neighbors[:10]},
                description=f"{len(neighbors)} neighbors (showing 10)"
            ))

        return evidence


# ---------------------------------------------------------------------------
# Analytics Retriever
# ---------------------------------------------------------------------------

class AnalyticsRetriever(BaseRetriever):
    """Retrieves computed analytics: centrality, community, similarity."""

    def __init__(self):
        self._fact_df = None

    def _ensure_loaded(self):
        if self._fact_df is None:
            from graph_intelligence.intelligence.graph_facts import get_entity_fact_table
            self._fact_df = get_entity_fact_table()

    def get_entity_analytics(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get all analytics for an entity."""
        self._ensure_loaded()

        row = self._fact_df[self._fact_df["node_id"] == entity_id]
        if row.empty:
            return None

        r = row.iloc[0]

        return {
            "entity_id": entity_id,
            "labels": r.get("labels", ""),
            "name": r.get("name", ""),
            "centrality": {
                "degree_centrality": float(r.get("degree_centrality", 0)),
                "betweenness_centrality": float(r.get("betweenness_centrality", 0)),
                "closeness_centrality": float(r.get("closeness_centrality", 0)),
                "eigenvector_centrality": float(r.get("eigenvector_centrality", 0)),
                "harmonic_centrality": float(r.get("harmonic_centrality", 0)),
                "pagerank": float(r.get("pagerank", 0)),
                "article_rank": float(r.get("article_rank", 0)),
                "hits_hub": float(r.get("hits_hub", 0)),
                "hits_authority": float(r.get("hits_authority", 0)),
            },
            "community": {
                "leiden": int(r.get("leiden", -1)),
                "louvain": int(r.get("louvain", -1)),
                "label_propagation": int(r.get("label_propagation", -1)),
                "sllpa": str(r.get("sllpa", "")),
                "k_core": int(r.get("k_core", -1)),
                "kmeans": int(r.get("kmeans", -1)),
                "k1_coloring": int(r.get("k1_coloring", -1)),
            },
            "structural": {
                "clustering_coefficient": float(r.get("clustering_coefficient", 0)),
                "triangle_count": int(r.get("triangle_count", 0)),
                "is_articulation_point": bool(r.get("is_articulation_point", False)),
                "is_bridge_endpoint": bool(r.get("is_bridge_endpoint", False)),
            },
            "embeddings": {
                "node2vec": r.get("node2vec_preview", ""),
                "fastrp": r.get("fastrp_preview", ""),
                "graphsage": r.get("graphsage_preview", ""),
                "hashgnn": r.get("hashgnn_preview", ""),
                "fastpath": r.get("fastpath_preview", ""),
            }
        }

    def get_top_by_metric(self, metric: str, n: int = 10) -> List[Dict[str, Any]]:
        """Get top-N entities by a metric."""
        self._ensure_loaded()

        if metric not in self._fact_df.columns:
            return []

        top = self._fact_df.nlargest(n, metric)
        return top[["node_id", "labels", "name", metric]].to_dict("records")

    def get_community_members(self, community_id: int, algorithm: str = "leiden") -> List[Dict[str, Any]]:
        """Get all entities in a community."""
        self._ensure_loaded()

        if algorithm not in self._fact_df.columns:
            return []

        members = self._fact_df[self._fact_df[algorithm] == community_id]
        return members[["node_id", "labels", "name"]].to_dict("records")

    def get_cross_community_bridges(self, algorithm: str = "leiden", n: int = 20) -> List[Dict[str, Any]]:
        """Get entities that bridge communities (high betweenness + cross-community edges)."""
        self._ensure_loaded()

        # Filter for valid communities
        valid = self._fact_df[self._fact_df[algorithm] >= 0]
        if len(valid) == 0:
            return []

        # Sort by betweenness
        bridges = valid.nlargest(n, "betweenness_centrality")
        return bridges[["node_id", "labels", "name", "betweenness_centrality", algorithm]].to_dict("records")

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get overall graph statistics."""
        self._ensure_loaded()

        from graph_intelligence.analytics.graph_loader import get_graph_statistics
        return get_graph_statistics()

    def retrieve(self, query: str, **kwargs) -> Dict[str, Any]:
        """Retrieve analytics relevant to query."""
        return {"message": "Use specific methods: get_entity_analytics, get_top_by_metric, etc."}

    def get_evidence(self, entity_id: str, **kwargs) -> List[EvidenceItem]:
        """Get analytics evidence for entity."""
        self._ensure_loaded()
        evidence = []

        analytics = self.get_entity_analytics(entity_id)
        if not analytics:
            return evidence

        # Centrality evidence
        for metric, value in analytics["centrality"].items():
            if value > 0:
                evidence.append(EvidenceItem(
                    source=f"centrality/{metric}.csv",
                    metric=metric,
                    entity_id=entity_id,
                    value=value,
                    description=f"{metric}: {value:.6f}"
                ))

        # Community evidence
        for algo, comm_id in analytics["community"].items():
            if isinstance(comm_id, int) and comm_id >= 0:
                evidence.append(EvidenceItem(
                    source=f"community/{algo}.csv",
                    metric=f"{algo}_community",
                    entity_id=entity_id,
                    value=comm_id,
                    description=f"{algo} community: {comm_id}"
                ))

        # Structural evidence
        if analytics["structural"]["is_articulation_point"]:
            evidence.append(EvidenceItem(
                source="centrality/articulation_points.csv",
                metric="is_articulation_point",
                entity_id=entity_id,
                value=True,
                description="Node is an articulation point (removal increases components)"
            ))

        if analytics["structural"]["is_bridge_endpoint"]:
            evidence.append(EvidenceItem(
                source="centrality/bridges.csv",
                metric="is_bridge_endpoint",
                entity_id=entity_id,
                value=True,
                description="Node is an endpoint of a bridge edge"
            ))

        return evidence


# ---------------------------------------------------------------------------
# Embedding Retriever
# ---------------------------------------------------------------------------

class EmbeddingRetriever(BaseRetriever):
    """Retrieves embedding-based similarity."""

    def __init__(self):
        self._embeddings = {}
        self._fact_df = None

    def _ensure_loaded(self):
        if self._fact_df is None:
            from graph_intelligence.intelligence.graph_facts import get_entity_fact_table
            self._fact_df = get_entity_fact_table()

        # Load full embeddings if needed
        if not self._embeddings:
            for method in ["node2vec", "fastrp", "graphsage", "hashgnn", "fastpath"]:
                path = EMBEDDINGS_DIR / f"{method}.csv"
                if path.exists():
                    try:
                        df = pd.read_csv(path)
                        # Store as dict for fast lookup
                        self._embeddings[method] = df.set_index("node_id")["embedding_preview"].to_dict()
                    except Exception:
                        pass

    def get_embedding(self, entity_id: str, method: str = "node2vec") -> Optional[str]:
        """Get embedding preview for entity."""
        self._ensure_loaded()
        return self._embeddings.get(method, {}).get(entity_id)

    def find_similar_by_embedding(self, entity_id: str, method: str = "node2vec",
                                   n: int = 10) -> List[Dict[str, Any]]:
        """Find similar entities by embedding cosine similarity."""
        self._ensure_loaded()

        # For now, use preview string comparison (placeholder)
        # In production, would load full vectors and compute cosine similarity
        preview = self.get_embedding(entity_id, method)
        if not preview:
            return []

        # Return entities with same embedding preview prefix (rough similarity)
        results = []
        for eid, e_preview in self._embeddings.get(method, {}).items():
            if eid != entity_id and e_preview and e_preview.startswith(preview[:20]):
                entity_info = self._fact_df[self._fact_df["node_id"] == eid]
                if not entity_info.empty:
                    r = entity_info.iloc[0]
                    results.append({
                        "entity_id": eid,
                        "labels": r.get("labels", ""),
                        "name": r.get("name", ""),
                        "similarity_hint": "embedding_prefix_match",
                    })
            if len(results) >= n:
                break

        return results

    def retrieve(self, query: str, **kwargs) -> Dict[str, Any]:
        return {"message": "Use specific methods: get_embedding, find_similar_by_embedding"}

    def get_evidence(self, entity_id: str, **kwargs) -> List[EvidenceItem]:
        """Get embedding evidence for entity."""
        self._ensure_loaded()
        evidence = []

        for method in ["node2vec", "fastrp", "graphsage", "hashgnn", "fastpath"]:
            preview = self.get_embedding(entity_id, method)
            if preview:
                evidence.append(EvidenceItem(
                    source=f"embeddings/{method}.csv",
                    metric=f"{method}_embedding",
                    entity_id=entity_id,
                    value=preview[:100],
                    description=f"{method} embedding preview (128-dim)"
                ))

        return evidence


# ---------------------------------------------------------------------------
# Entity Resolution
# ---------------------------------------------------------------------------

class EntityResolver:
    """Resolves entity names/IDs from natural language queries."""

    def __init__(self):
        self._fact_df = None
        self._name_to_id = {}
        self._id_to_info = {}

    def _ensure_loaded(self):
        if self._fact_df is None:
            from graph_intelligence.intelligence.graph_facts import get_entity_fact_table
            self._fact_df = get_entity_fact_table()

            # Build lookup maps
            for _, row in self._fact_df.iterrows():
                eid = row["node_id"]
                name = str(row.get("name", "")).strip().lower()
                name = ' '.join(name.split())  # Normalize whitespace
                if name:
                    self._name_to_id[name] = eid
                self._id_to_info[eid] = {
                    "entity_id": eid,
                    "labels": row.get("labels", ""),
                    "name": row.get("name", ""),
                }

    def resolve(self, query: str) -> List[Dict[str, Any]]:
        """Resolve entities mentioned in query."""
        self._ensure_loaded()
        query_lower = query.lower()

        matches = []

        # Exact name match
        for name, eid in self._name_to_id.items():
            if name in query_lower:
                matches.append(self._id_to_info[eid])

        # Partial match on name
        if not matches:
            for name, eid in self._name_to_id.items():
                words = name.split()
                if any(word in query_lower for word in words if len(word) > 3):
                    matches.append(self._id_to_info[eid])

        # Direct ID match
        for eid in self._id_to_info:
            if eid in query:
                matches.append(self._id_to_info[eid])

        # Deduplicate
        seen = set()
        unique = []
        for m in matches:
            if m["entity_id"] not in seen:
                seen.add(m["entity_id"])
                unique.append(m)

        return unique[:10]


# ---------------------------------------------------------------------------
# Evidence Assembler
# ---------------------------------------------------------------------------

class EvidenceAssembler:
    """Assembles evidence from multiple retrievers into a package."""

    def __init__(self):
        self.graph_retriever = GraphRetriever()
        self.analytics_retriever = AnalyticsRetriever()
        self.embedding_retriever = EmbeddingRetriever()
        self.entity_resolver = EntityResolver()

    def assemble(self, query: str, entity_ids: Optional[List[str]] = None) -> EvidencePackage:
        """Assemble evidence package for a query."""
        package = EvidencePackage(query=query)

        # Resolve entities from query if not provided
        if entity_ids is None:
            resolved = self.entity_resolver.resolve(query)
            entity_ids = [e["entity_id"] for e in resolved]
            package.retrieved_entities = resolved

        # Gather evidence for each entity
        for eid in entity_ids:
            # Graph structure evidence
            graph_evidence = self.graph_retriever.get_evidence(eid)
            package.analytics.extend(graph_evidence)
            package.evidence_items.extend(graph_evidence)
            for item in graph_evidence:
                if item.source not in package.provenance:
                    package.provenance.append(item.source)

            # Analytics evidence
            analytics_evidence = self.analytics_retriever.get_evidence(eid)
            package.analytics.extend(analytics_evidence)
            package.evidence_items.extend(analytics_evidence)
            for item in analytics_evidence:
                if item.source not in package.provenance:
                    package.provenance.append(item.source)

            # Embedding evidence
            embedding_evidence = self.embedding_retriever.get_evidence(eid)
            package.analytics.extend(embedding_evidence)
            package.evidence_items.extend(embedding_evidence)
            for item in embedding_evidence:
                if item.source not in package.provenance:
                    package.provenance.append(item.source)

            # Add full analytics to retrieved_entities
            full_analytics = self.analytics_retriever.get_entity_analytics(eid)
            if full_analytics:
                package.retrieved_entities.append(full_analytics)

            # Add community info
            if full_analytics and "community" in full_analytics:
                for algo, comm_id in full_analytics["community"].items():
                    if isinstance(comm_id, int) and comm_id >= 0:
                        package.communities.append({
                            "algorithm": algo,
                            "community_id": comm_id,
                            "entity_id": eid,
                        })

        return package


# ---------------------------------------------------------------------------
# High-Level Retrieval Functions
# ---------------------------------------------------------------------------

def get_evidence_for_question(question: str) -> EvidencePackage:
    """Main entry point: get evidence package for a natural language question."""
    assembler = EvidenceAssembler()
    package = assembler.assemble(question)

    # Check if resolved entities are specific (not generic categories like Gender, Ethnicity)
    generic_labels = {"gender", "ethnicity", "race", "marital", "prefix", "suffix", "city", "state", "county", "zip"}
    has_specific_entities = False

    for entity in package.retrieved_entities:
        if isinstance(entity, dict):
            labels = entity.get("labels", "").lower()
            # Check if any label is not generic
            entity_labels = [l.strip() for l in labels.split(",") if l.strip()]
            if any(l not in generic_labels for l in entity_labels):
                has_specific_entities = True
                break

    # If no specific entities found, fall back to broad question strategy
    if not has_specific_entities:
        return get_evidence_for_broad_question(question)

    return package


def get_evidence_for_broad_question(question: str) -> EvidencePackage:
    """Get evidence for broad questions that don't mention specific entities.
    Uses analytics retriever to find top entities by relevant metrics."""
    # Create package WITHOUT running entity resolution first
    package = EvidencePackage(query=question)

    retriever = AnalyticsRetriever()
    question_lower = question.lower()

    # Determine relevant metrics from question
    metrics_to_check = []

    if "bridge" in question_lower or "connect" in question_lower:
        metrics_to_check = ["betweenness_centrality", "is_articulation_point", "is_bridge_endpoint"]
    elif "important" in question_lower or "influential" in question_lower or "central" in question_lower:
        metrics_to_check = ["pagerank", "betweenness_centrality", "degree_centrality", "eigenvector_centrality"]
    elif "community" in question_lower:
        metrics_to_check = ["leiden", "louvain"]
    elif "similar" in question_lower:
        metrics_to_check = []

    # Get top entities by each metric
    for metric in metrics_to_check:
        if metric in ["leiden", "louvain"]:
            # For community algorithms, get community stats
            continue
        top = retriever.get_top_by_metric(metric, 20)
        for item in top:
            eid = item["node_id"]
            if eid not in [e.get("entity_id") for e in package.retrieved_entities]:
                analytics = retriever.get_entity_analytics(eid)
                if analytics:
                    package.retrieved_entities.append(analytics)
                    # Add evidence
                    for m, v in analytics["centrality"].items():
                        if v > 0:
                            package.add_evidence(EvidenceItem(
                                source=f"centrality/{m}.csv",
                                metric=m,
                                entity_id=eid,
                                value=v,
                                description=f"{m}: {v:.6f}"
                            ))
                    for algo, comm_id in analytics["community"].items():
                        if isinstance(comm_id, int) and comm_id >= 0:
                            package.add_evidence(EvidenceItem(
                                source=f"community/{algo}.csv",
                                metric=f"{algo}_community",
                                entity_id=eid,
                                value=comm_id,
                                description=f"{algo} community: {comm_id}"
                            ))

    # If still no entities, fall back to general top entities
    if not package.retrieved_entities:
        top = retriever.get_top_by_metric("betweenness_centrality", 20)
        for item in top:
            eid = item["node_id"]
            analytics = retriever.get_entity_analytics(eid)
            if analytics:
                package.retrieved_entities.append(analytics)
                for m, v in analytics["centrality"].items():
                    if v > 0:
                        package.add_evidence(EvidenceItem(
                            source=f"centrality/{m}.csv",
                            metric=m,
                            entity_id=eid,
                            value=v,
                            description=f"{m}: {v:.6f}"
                        ))
                for algo, comm_id in analytics["community"].items():
                    if isinstance(comm_id, int) and comm_id >= 0:
                        package.add_evidence(EvidenceItem(
                            source=f"community/{algo}.csv",
                            metric=f"{algo}_community",
                            entity_id=eid,
                            value=comm_id,
                            description=f"{algo} community: {comm_id}"
                        ))

    return package


def get_entity_profile(entity_id: str) -> Dict[str, Any]:
    """Get complete profile for an entity."""
    assembler = EvidenceAssembler()
    package = assembler.assemble(f"Profile for {entity_id}", [entity_id])
    return package.to_dict()


def search_entities(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for entities matching query."""
    resolver = EntityResolver()
    return resolver.resolve(query)[:limit]