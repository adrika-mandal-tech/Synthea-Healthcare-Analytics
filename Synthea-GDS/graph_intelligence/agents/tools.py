"""
Graph Intelligence Platform — Agent Tools

Tool definitions for the LangGraph agent workflow.
Each tool wraps a retriever method with proper error handling.
"""

from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
import json


# ---------------------------------------------------------------------------
# Tool: Resolve Entity
# ---------------------------------------------------------------------------

@tool
def resolve_entity(query: str) -> str:
    """Resolve entity names/IDs mentioned in a natural language query.

    Args:
        query: Natural language query containing entity names

    Returns:
        JSON list of resolved entities with entity_id, name, labels
    """
    try:
        from graph_intelligence.intelligence.retrieval import search_entities
        results = search_entities(query)
        return json.dumps(results, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Entity Analytics
# ---------------------------------------------------------------------------

@tool
def get_entity_analytics(entity_id: str) -> str:
    """Get all pre-computed analytics for a specific entity.

    Args:
        entity_id: Neo4j element ID (e.g., '4:253b872d-af12-4342-b04a-518b6fc7dd81:0')

    Returns:
        JSON with centrality, community, structural, and embedding metrics
    """
    try:
        from graph_intelligence.intelligence.retrieval import AnalyticsRetriever
        retriever = AnalyticsRetriever()
        result = retriever.get_entity_analytics(entity_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Top Entities by Metric
# ---------------------------------------------------------------------------

@tool
def get_top_entities_by_metric(metric: str, n: int = 10) -> str:
    """Get top-N entities ranked by a centrality/community metric.

    Args:
        metric: Metric name (e.g., 'degree_centrality', 'betweenness_centrality',
                'pagerank', 'closeness_centrality', 'eigenvector_centrality',
                'harmonic_centrality', 'article_rank')
        n: Number of top entities to return (default 10)

    Returns:
        JSON list of entities with metric values
    """
    try:
        from graph_intelligence.intelligence.retrieval import AnalyticsRetriever
        retriever = AnalyticsRetriever()
        result = retriever.get_top_by_metric(metric, n)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Cross-Community Bridges
# ---------------------------------------------------------------------------

@tool
def get_cross_community_bridges(algorithm: str = "leiden", n: int = 20) -> str:
    """Find entities that bridge multiple communities (high betweenness + cross-community edges).

    Args:
        algorithm: Community algorithm ('leiden', 'louvain', 'label_propagation', 'kmeans')
        n: Number of bridge candidates to return

    Returns:
        JSON list of bridge entities with betweenness and community info
    """
    try:
        from graph_intelligence.intelligence.retrieval import AnalyticsRetriever
        retriever = AnalyticsRetriever()
        result = retriever.get_cross_community_bridges(algorithm, n)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Graph Statistics
# ---------------------------------------------------------------------------

@tool
def get_graph_statistics() -> str:
    """Get overall graph statistics (node count, edge count, density, label distribution, etc.).

    Returns:
        JSON with graph-level statistics
    """
    try:
        from graph_intelligence.intelligence.retrieval import AnalyticsRetriever
        retriever = AnalyticsRetriever()
        result = retriever.get_graph_statistics()
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Entity Neighbors
# ---------------------------------------------------------------------------

@tool
def get_entity_neighbors(entity_id: str, limit: int = 50) -> str:
    """Get immediate neighbors of an entity in the graph.

    Args:
        entity_id: Neo4j element ID
        limit: Maximum neighbors to return

    Returns:
        JSON list of neighbor entities with relationship info
    """
    try:
        from graph_intelligence.intelligence.retrieval import GraphRetriever
        retriever = GraphRetriever()
        result = retriever.get_neighbors(entity_id, limit)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Entity Relationships
# ---------------------------------------------------------------------------

@tool
def get_entity_relationships(entity_id: str) -> str:
    """Get all relationships (incoming and outgoing) for an entity.

    Args:
        entity_id: Neo4j element ID

    Returns:
        JSON list of relationships with source, target, type, direction
    """
    try:
        from graph_intelligence.intelligence.retrieval import GraphRetriever
        retriever = GraphRetriever()
        result = retriever.get_relationships(entity_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Subgraph
# ---------------------------------------------------------------------------

@tool
def get_subgraph(entity_ids: List[str], hops: int = 1) -> str:
    """Get induced subgraph around specified entities.

    Args:
        entity_ids: List of Neo4j element IDs
        hops: Number of hops to expand (default 1)

    Returns:
        JSON with nodes and edges in the subgraph
    """
    try:
        from graph_intelligence.intelligence.retrieval import GraphRetriever
        retriever = GraphRetriever()
        result = retriever.get_subgraph(entity_ids, hops)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Find Shortest Path
# ---------------------------------------------------------------------------

@tool
def find_shortest_path(source: str, target: str) -> str:
    """Find shortest path between two entities.

    Args:
        source: Source entity ID
        target: Target entity ID

    Returns:
        JSON list of entity IDs in the path, or null if no path
    """
    try:
        from graph_intelligence.intelligence.retrieval import GraphRetriever
        retriever = GraphRetriever()
        result = retriever.find_shortest_path(source, target)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Community Members
# ---------------------------------------------------------------------------

@tool
def get_community_members(community_id: int, algorithm: str = "leiden") -> str:
    """Get all entities belonging to a specific community.

    Args:
        community_id: Community identifier
        algorithm: Community detection algorithm ('leiden', 'louvain', 'label_propagation', 'kmeans')

    Returns:
        JSON list of entities in the community
    """
    try:
        from graph_intelligence.intelligence.retrieval import AnalyticsRetriever
        retriever = AnalyticsRetriever()
        result = retriever.get_community_members(community_id, algorithm)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Find Similar by Embedding
# ---------------------------------------------------------------------------

@tool
def find_similar_by_embedding(entity_id: str, method: str = "node2vec", n: int = 10) -> str:
    """Find entities with similar embeddings (structural similarity).

    Args:
        entity_id: Neo4j element ID
        method: Embedding method ('node2vec', 'fastrp', 'graphsage', 'hashgnn', 'fastpath')
        n: Number of similar entities to return

    Returns:
        JSON list of similar entities
    """
    try:
        from graph_intelligence.intelligence.retrieval import EmbeddingRetriever
        retriever = EmbeddingRetriever()
        result = retriever.find_similar_by_embedding(entity_id, method, n)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Get Embedding
# ---------------------------------------------------------------------------

@tool
def get_embedding(entity_id: str, method: str = "node2vec") -> str:
    """Get embedding preview for an entity.

    Args:
        entity_id: Neo4j element ID
        method: Embedding method ('node2vec', 'fastrp', 'graphsage', 'hashgnn', 'fastpath')

    Returns:
        JSON with embedding preview string
    """
    try:
        from graph_intelligence.intelligence.retrieval import EmbeddingRetriever
        retriever = EmbeddingRetriever()
        result = retriever.get_embedding(entity_id, method)
        return json.dumps({"entity_id": entity_id, "method": method, "preview": result}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Assemble Evidence
# ---------------------------------------------------------------------------

@tool
def assemble_evidence(question: str, entity_ids: Optional[List[str]] = None) -> str:
    """Assemble comprehensive evidence package for a question.

    Args:
        question: Natural language question
        entity_ids: Optional list of entity IDs to focus on

    Returns:
        JSON EvidencePackage with all retrieved evidence
    """
    try:
        from graph_intelligence.intelligence.retrieval import get_evidence_for_question
        package = get_evidence_for_question(question)
        # Override entity_ids if provided
        if entity_ids:
            from graph_intelligence.intelligence.retrieval import EvidenceAssembler
            assembler = EvidenceAssembler()
            package = assembler.assemble(question, entity_ids)
        return json.dumps(package.to_dict(), default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    resolve_entity,
    get_entity_analytics,
    get_top_entities_by_metric,
    get_cross_community_bridges,
    get_graph_statistics,
    get_entity_neighbors,
    get_entity_relationships,
    get_subgraph,
    find_shortest_path,
    get_community_members,
    find_similar_by_embedding,
    get_embedding,
    assemble_evidence,
]

TOOL_MAP = {tool.name: tool for tool in ALL_TOOLS}


def get_tool(name: str):
    """Get tool by name."""
    return TOOL_MAP.get(name)


def get_all_tools() -> List:
    """Get all tools as list."""
    return ALL_TOOLS