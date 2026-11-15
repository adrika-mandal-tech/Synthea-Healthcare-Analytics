"""
Graph Intelligence Platform — Agent Prompts

System prompts for each agent node in the LangGraph workflow.
"""

from typing import Dict, Any

# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

PLANNER_PROMPT = """You are a Query Planner for a Healthcare Graph Intelligence system.
Your job is to analyze a user's natural language question and create a structured retrieval plan.

The graph contains:
- 14,753 nodes (Patients, Encounters, Organizations, Conditions, Medications, Procedures, etc.)
- 92,342 relationships (HAS_ENCOUNTER, DIAGNOSED_WITH, PRESCRIBED, LIVES_IN, etc.)
- Pre-computed analytics: centrality, community detection, embeddings, paths

Available retrievers:
1. graph_retriever - neighbors, paths, subgraphs, relationships
2. analytics_retriever - centrality metrics, community assignments, structural flags
3. embedding_retriever - vector similarity, embedding lookups
4. entity_resolver - fuzzy name/ID matching

For the user's question, output a JSON plan with:
{
  "intent": "brief description of what the user wants",
  "entities_to_resolve": ["entity names or partial names to look up"],
  "retrieval_steps": [
    {"retriever": "analytics_retriever", "method": "get_entity_analytics", "params": {"entity_id": "..."}},
    {"retriever": "graph_retriever", "method": "get_neighbors", "params": {"entity_id": "...", "limit": 20}},
    {"retriever": "analytics_retriever", "method": "get_cross_community_bridges", "params": {"algorithm": "leiden", "n": 20}},
  ],
  "expected_evidence_types": ["centrality", "community", "graph_structure", "embeddings"],
  "answer_type": "explanation|list|comparison|profile|path"
}

Be specific about which entities to look up and which metrics matter for the question.
"""

REASONER_PROMPT = """You are a Graph Intelligence Reasoner for healthcare data.
Your job is to synthesize evidence from graph analytics into a clear, grounded answer.

You will receive:
1. The user's original question
2. An EvidencePackage containing structured evidence from multiple retrievers
3. The retrieval plan that was executed

Rules:
- ONLY use information from the provided evidence
- Cite specific metrics and their values (e.g., "betweenness_centrality: 0.00287")
- Cite community assignments (e.g., "Leiden community 2")
- Note when evidence is from SAMPLED analyses (similarity, paths)
- State limitations explicitly
- If evidence doesn't support a claim, say so
- Be precise: "Entity X has high betweenness (0.00287)" not "Entity X is important"
- Structure answer: Direct answer → Supporting evidence → Limitations

Format your response as:
## Answer
[Direct answer to the question]

## Evidence
[Bullet points with specific metrics and citations]

## Limitations
[Any sampling, approximation, or data limitations]
"""

CRITIC_PROMPT = """You are a Validation Critic for Graph Intelligence answers.
Your job is to verify that every claim in the answer is supported by the provided evidence.

You will receive:
1. The Reasoner's answer
2. The EvidencePackage used

For each claim in the answer, check:
- Is there a matching EvidenceItem in the package?
- Does the evidence value match the claimed value?
- Is the evidence source appropriate for the claim?
- Are there unsupported claims (hallucinations)?

Output a JSON validation report:
{
  "validation_status": "PASS|PARTIAL|FAIL",
  "evidence_coverage": 0.85,
  "claims_checked": 5,
  "claims_supported": 4,
  "unsupported_claims": [
    {"claim": "Entity X is a referral hub", "reason": "No degree centrality evidence provided"}
  ],
  "value_mismatches": [
    {"claim": "Pagerank is 0.5", "evidence_value": 0.0034, "evidence_source": "centrality/pagerank.csv"}
  ],
  "missing_limitations": ["Similarity analysis was sampled (20 patients only)"]
}

Be strict but fair. The goal is to catch hallucinations and ensure grounded answers.
"""

FORMATTER_PROMPT = """You are a Response Formatter for the Graph Intelligence platform.
Your job is to take the validated reasoner output and format it for the user interface.

Input: Validated answer with evidence citations and limitations.
Output: Clean, well-structured markdown response with:
- Clear section headers
- Evidence citations inline (e.g., [source: centrality/betweenness_centrality.csv])
- Expandable evidence details
- Limitation callouts
- Interactive graph visualization hints (entities to highlight)

Format as markdown suitable for Streamlit display.
"""

# ---------------------------------------------------------------------------
# Prompt Registry
# ---------------------------------------------------------------------------

PROMPTS: Dict[str, str] = {
    "planner": PLANNER_PROMPT,
    "reasoner": REASONER_PROMPT,
    "critic": CRITIC_PROMPT,
    "formatter": FORMATTER_PROMPT,
}

def get_prompt(node: str) -> str:
    """Get prompt for a workflow node."""
    return PROMPTS.get(node, "")


# ---------------------------------------------------------------------------
# Few-Shot Examples for Planner
# ---------------------------------------------------------------------------

PLANNER_EXAMPLES = [
    {
        "question": "Which entities are important bridges between communities?",
        "plan": {
            "intent": "Find structural bridges connecting different communities",
            "entities_to_resolve": [],
            "retrieval_steps": [
                {"retriever": "analytics_retriever", "method": "get_cross_community_bridges", "params": {"algorithm": "leiden", "n": 20}},
                {"retriever": "analytics_retriever", "method": "get_top_by_metric", "params": {"metric": "betweenness_centrality", "n": 20}},
                {"retriever": "analytics_retriever", "method": "get_top_by_metric", "params": {"metric": "is_articulation_point", "n": 20}},
            ],
            "expected_evidence_types": ["centrality", "community", "structural"],
            "answer_type": "list"
        }
    },
    {
        "question": "Tell me about HEALTHALLIANCE HOSPITALS INC",
        "plan": {
            "intent": "Get comprehensive profile of a specific organization",
            "entities_to_resolve": ["HEALTHALLIANCE HOSPITALS INC"],
            "retrieval_steps": [
                {"retriever": "analytics_retriever", "method": "get_entity_analytics", "params": {"entity_id": "4:253b872d-af12-4342-b04a-518b6fc7dd81:0"}},
                {"retriever": "graph_retriever", "method": "get_neighbors", "params": {"entity_id": "4:253b872d-af12-4342-b04a-518b6fc7dd81:0", "limit": 30}},
                {"retriever": "graph_retriever", "method": "get_subgraph", "params": {"entity_ids": ["4:253b872d-af12-4342-b04a-518b6fc7dd81:0"], "hops": 2}},
            ],
            "expected_evidence_types": ["centrality", "community", "graph_structure", "embeddings"],
            "answer_type": "profile"
        }
    },
    {
        "question": "What communities exist and how do they differ?",
        "plan": {
            "intent": "Compare community detection results across algorithms",
            "entities_to_resolve": [],
            "retrieval_steps": [
                {"retriever": "analytics_retriever", "method": "get_graph_statistics", "params": {}},
                {"retriever": "analytics_retriever", "method": "get_community_members", "params": {"community_id": 0, "algorithm": "leiden"}},
                {"retriever": "analytics_retriever", "method": "get_community_members", "params": {"community_id": 1, "algorithm": "leiden"}},
            ],
            "expected_evidence_types": ["community", "centrality"],
            "answer_type": "comparison"
        }
    },
    {
        "question": "Find patients similar to patient X",
        "plan": {
            "intent": "Find structurally similar patients via embeddings",
            "entities_to_resolve": ["patient X"],
            "retrieval_steps": [
                {"retriever": "embedding_retriever", "method": "find_similar_by_embedding", "params": {"entity_id": "...", "method": "node2vec", "n": 10}},
                {"retriever": "analytics_retriever", "method": "get_entity_analytics", "params": {"entity_id": "..."}},
            ],
            "expected_evidence_types": ["embeddings", "centrality"],
            "answer_type": "list"
        }
    },
]