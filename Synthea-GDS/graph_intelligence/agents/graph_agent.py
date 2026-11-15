"""
Graph Intelligence Platform — LangGraph Agent Workflow

Main agent workflow: Planner → Retrievers → Evidence Assembler → Reasoner → Critic → Formatter
"""

import json
import warnings
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from operator import add

warnings.filterwarnings("ignore")

try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
    from langchain_openai import ChatOpenAI
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("Warning: langgraph not available. Install with: pip install langgraph langchain-openai")

try:
    from graph_intelligence.intelligence.retrieval import (
        EvidencePackage, EvidenceItem, EvidenceAssembler,
        get_evidence_for_question, get_entity_profile, search_entities
    )
    from graph_intelligence.agents.tools import get_all_tools, get_tool
    from graph_intelligence.agents.prompts import get_prompt, PLANNER_EXAMPLES
    LOCAL_IMPORTS_AVAILABLE = True
except ImportError as e:
    LOCAL_IMPORTS_AVAILABLE = False
    print(f"Warning: Local imports failed: {e}")


# ---------------------------------------------------------------------------
# State Definition
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """State for the graph intelligence agent workflow."""
    # Input
    question: str
    session_id: str

    # Planning
    plan: Optional[Dict[str, Any]]
    resolved_entities: List[Dict[str, Any]]

    # Retrieval
    evidence_package: Optional[EvidencePackage]
    retrieval_results: List[Dict[str, Any]]

    # Reasoning
    reasoner_answer: str
    reasoner_evidence: List[Dict[str, Any]]

    # Validation
    validation_report: Optional[Dict[str, Any]]
    validation_passed: bool

    # Output
    final_answer: str
    formatted_output: str

    # Metadata
    errors: List[str]
    step_count: int


# ---------------------------------------------------------------------------
# Node: Planner
# ---------------------------------------------------------------------------

def planner_node(state: AgentState) -> Dict[str, Any]:
    """Plan the retrieval strategy for the question."""
    question = state["question"]

    if not LANGGRAPH_AVAILABLE:
        # Fallback: simple heuristic planning
        return _fallback_planner(question)

    # Build planner prompt with examples
    examples_text = "\n".join([
        f"Q: {ex['question']}\nPlan: {json.dumps(ex['plan'])}"
        for ex in PLANNER_EXAMPLES
    ])

    system_prompt = get_prompt("planner") + f"\n\nExamples:\n{examples_text}"

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Question: {question}\n\nOutput JSON plan:")
        ]
        response = llm.invoke(messages)
        plan = json.loads(response.content)
    except Exception as e:
        print(f"Planner LLM failed: {e}, using fallback")
        plan = _fallback_planner(question)

    # Resolve entities mentioned in question
    resolved = search_entities(question)

    return {
        "plan": plan,
        "resolved_entities": resolved,
        "step_count": state.get("step_count", 0) + 1
    }


def _fallback_planner(question: str) -> Dict[str, Any]:
    """Fallback planner using keyword matching."""
    question_lower = question.lower()

    # Default plan
    plan = {
        "intent": "Answer graph intelligence question",
        "entities_to_resolve": [],
        "retrieval_steps": [],
        "expected_evidence_types": ["centrality", "community"],
        "answer_type": "explanation"
    }

    # Detect intent and add appropriate retrieval steps
    if "bridge" in question_lower or "connect" in question_lower:
        plan["intent"] = "Find structural bridges between communities"
        plan["retrieval_steps"] = [
            {"retriever": "analytics_retriever", "method": "get_cross_community_bridges", "params": {"algorithm": "leiden", "n": 20}},
            {"retriever": "analytics_retriever", "method": "get_top_by_metric", "params": {"metric": "betweenness_centrality", "n": 20}},
        ]
        plan["expected_evidence_types"] = ["centrality", "community", "structural"]
        plan["answer_type"] = "list"

    elif "community" in question_lower or "cluster" in question_lower or "communities" in question_lower:
        plan["intent"] = "Analyze community structure"
        plan["retrieval_steps"] = [
            {"retriever": "analytics_retriever", "method": "get_graph_statistics", "params": {}},
            {"retriever": "analytics_retriever", "method": "get_community_members", "params": {"community_id": 0, "algorithm": "leiden"}},
            {"retriever": "analytics_retriever", "method": "get_community_members", "params": {"community_id": 1, "algorithm": "leiden"}},
        ]
        plan["expected_evidence_types"] = ["community", "centrality"]
        plan["answer_type"] = "comparison"

    elif "similar" in question_lower or "like" in question_lower:
        plan["intent"] = "Find similar entities"
        plan["retrieval_steps"] = [
            {"retriever": "embedding_retriever", "method": "find_similar_by_embedding", "params": {"entity_id": "PLACEHOLDER", "method": "node2vec", "n": 10}},
        ]
        plan["expected_evidence_types"] = ["embeddings"]
        plan["answer_type"] = "list"

    elif "profile" in question_lower or "about" in question_lower or "tell me" in question_lower:
        plan["intent"] = "Get entity profile"
        plan["retrieval_steps"] = [
            {"retriever": "analytics_retriever", "method": "get_entity_analytics", "params": {"entity_id": "PLACEHOLDER"}},
            {"retriever": "graph_retriever", "method": "get_neighbors", "params": {"entity_id": "PLACEHOLDER", "limit": 30}},
        ]
        plan["expected_evidence_types"] = ["centrality", "community", "graph_structure", "embeddings"]
        plan["answer_type"] = "profile"

    else:
        # General question - get top entities by key metrics
        plan["retrieval_steps"] = [
            {"retriever": "analytics_retriever", "method": "get_top_by_metric", "params": {"metric": "betweenness_centrality", "n": 15}},
            {"retriever": "analytics_retriever", "method": "get_top_by_metric", "params": {"metric": "pagerank", "n": 15}},
            {"retriever": "analytics_retriever", "method": "get_graph_statistics", "params": {}},
        ]
        plan["answer_type"] = "explanation"

    return plan


# ---------------------------------------------------------------------------
# Node: Entity Resolution
# ---------------------------------------------------------------------------

def entity_resolution_node(state: AgentState) -> Dict[str, Any]:
    """Resolve entity IDs for placeholders in the plan."""
    plan = state.get("plan", {})
    resolved = state.get("resolved_entities", [])

    # Create mapping from entity names to IDs
    entity_map = {e["name"].lower(): e["entity_id"] for e in resolved}

    # Replace PLACEHOLDER in retrieval steps
    for step in plan.get("retrieval_steps", []):
        params = step.get("params", {})
        for key, value in params.items():
            if value == "PLACEHOLDER":
                # Try to find best match from resolved entities
                if resolved:
                    # For profile intent, prefer non-generic entities
                    intent = plan.get("intent", "").lower()
                    if "profile" in intent:
                        # Prefer entities that are not generic categories
                        generic_labels = {"gender", "ethnicity", "race", "marital", "prefix", "suffix", "city", "state", "county", "zip"}
                        for e in resolved:
                            labels = e.get("labels", "").lower()
                            entity_labels = [l.strip() for l in labels.split(",") if l.strip()]
                            if any(l not in generic_labels for l in entity_labels):
                                params[key] = e["entity_id"]
                                break
                        else:
                            # Fallback to first if all are generic
                            params[key] = resolved[0]["entity_id"]
                    else:
                        # Default to first resolved entity
                        params[key] = resolved[0]["entity_id"]
                else:
                    # Use top PageRank entity as default
                    from graph_intelligence.intelligence.retrieval import AnalyticsRetriever
                    retriever = AnalyticsRetriever()
                    top = retriever.get_top_by_metric("pagerank", 1)
                    if top:
                        params[key] = top[0]["node_id"]

    return {
        "plan": plan,
        "resolved_entities": resolved,
        "step_count": state.get("step_count", 0) + 1
    }


# ---------------------------------------------------------------------------
# Node: Retrieval
# ---------------------------------------------------------------------------

def retrieval_node(state: AgentState) -> Dict[str, Any]:
    """Execute retrieval steps from the plan."""
    plan = state.get("plan", {})
    resolved_entities = state.get("resolved_entities", [])

    # Check if we have specific entities or need broad retrieval
    question = state["question"]
    generic_labels = {"gender", "ethnicity", "race", "marital", "prefix", "suffix", "city", "state", "county", "zip"}
    has_specific = False
    for e in resolved_entities:
        labels = e.get("labels", "").lower()
        entity_labels = [l.strip() for l in labels.split(",") if l.strip()]
        if any(l not in generic_labels for l in entity_labels):
            has_specific = True
            break

    # Use broad retrieval if no specific entities resolved
    if not has_specific:
        # Use broad question retrieval instead
        from graph_intelligence.intelligence.retrieval import get_evidence_for_broad_question
        evidence_package = get_evidence_for_broad_question(question)
    else:
        # Standard retrieval with plan
        evidence_package = EvidencePackage(query=state["question"])
        evidence_package.retrieved_entities = resolved_entities

        # Execute each retrieval step
        for step in plan.get("retrieval_steps", []):
            retriever_name = step.get("retriever")
            method_name = step.get("method")
            params = step.get("params", {})

            try:
                if retriever_name == "analytics_retriever":
                    from graph_intelligence.intelligence.retrieval import AnalyticsRetriever
                    retriever = AnalyticsRetriever()
                    method = getattr(retriever, method_name)
                    result = method(**params)
                    state.setdefault("retrieval_results", []).append({
                        "step": step,
                        "result": result,
                        "success": True
                    })

                    # Add to evidence package
                    if method_name == "get_entity_analytics" and result:
                        evidence_package.retrieved_entities.append(result)
                        # Add analytics evidence
                        for metric, value in result.get("centrality", {}).items():
                            if value > 0:
                                evidence_package.add_evidence(EvidenceItem(
                                    source=f"centrality/{metric}.csv",
                                    metric=metric,
                                    entity_id=result["entity_id"],
                                    value=value,
                                    description=f"{metric}: {value:.6f}"
                                ))
                        for algo, comm_id in result.get("community", {}).items():
                            if isinstance(comm_id, int) and comm_id >= 0:
                                evidence_package.add_evidence(EvidenceItem(
                                    source=f"community/{algo}.csv",
                                    metric=f"{algo}_community",
                                    entity_id=result["entity_id"],
                                    value=comm_id,
                                    description=f"{algo} community: {comm_id}"
                                ))

                    elif method_name == "get_cross_community_bridges" and result:
                        for item in result:
                            evidence_package.add_evidence(EvidenceItem(
                                source=f"centrality/betweenness_centrality.csv",
                                metric="betweenness_centrality",
                                entity_id=item["node_id"],
                                value=item.get("betweenness_centrality", 0),
                                description=f"Bridge candidate: {item.get('name', '')} (comm: {item.get('leiden', 'N/A')})"
                            ))

                    elif method_name == "get_top_by_metric" and result:
                        for item in result:
                            metric = step["params"].get("metric", "unknown")
                            evidence_package.add_evidence(EvidenceItem(
                                source=f"centrality/{metric}.csv",
                                metric=metric,
                                entity_id=item["node_id"],
                                value=item.get(metric, 0),
                                description=f"Top {metric}: {item.get('name', '')} = {item.get(metric, 0):.6f}"
                            ))

                elif retriever_name == "graph_retriever":
                    from graph_intelligence.intelligence.retrieval import GraphRetriever
                    retriever = GraphRetriever()
                    method = getattr(retriever, method_name)
                    result = method(**params)
                    state.setdefault("retrieval_results", []).append({
                        "step": step,
                        "result": result,
                        "success": True
                    })

                    if method_name == "get_neighbors" and result:
                        entity_id = params.get("entity_id", "")
                        evidence_package.add_evidence(EvidenceItem(
                            source="graph/relationships.csv",
                            metric="neighbors",
                            entity_id=entity_id,
                            value={"count": len(result), "sample": result[:5]},
                            description=f"{len(result)} neighbors"
                        ))

                elif retriever_name == "embedding_retriever":
                    from graph_intelligence.intelligence.retrieval import EmbeddingRetriever
                    retriever = EmbeddingRetriever()
                    method = getattr(retriever, method_name)
                    result = method(**params)
                    state.setdefault("retrieval_results", []).append({
                        "step": step,
                        "result": result,
                        "success": True
                    })

            except Exception as e:
                state.setdefault("retrieval_results", []).append({
                    "step": step,
                    "result": None,
                    "success": False,
                    "error": str(e)
                })
                state.setdefault("errors", []).append(f"Retrieval failed: {e}")

    return {
        "evidence_package": evidence_package,
        "retrieval_results": state.get("retrieval_results", []),
        "step_count": state.get("step_count", 0) + 1
    }


# ---------------------------------------------------------------------------
# Node: Reasoner
# ---------------------------------------------------------------------------

def reasoner_node(state: AgentState) -> Dict[str, Any]:
    """Generate answer from evidence."""
    question = state["question"]
    evidence_package = state.get("evidence_package")
    plan = state.get("plan", {})

    if not LANGGRAPH_AVAILABLE:
        return _fallback_reasoner(question, evidence_package, plan)

    system_prompt = get_prompt("reasoner")

    # Prepare evidence summary for LLM
    evidence_summary = _summarize_evidence(evidence_package)

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Question: {question}

Plan: {json.dumps(plan, default=str)}

Evidence Summary:
{evidence_summary}

Generate answer:""")
        ]
        response = llm.invoke(messages)
        answer = response.content
    except Exception as e:
        print(f"Reasoner LLM failed: {e}, using fallback")
        answer = _fallback_reasoner(question, evidence_package, plan)

    return {
        "reasoner_answer": answer,
        "reasoner_evidence": evidence_package.evidence_items if evidence_package else [],
        "step_count": state.get("step_count", 0) + 1
    }


def _summarize_evidence(package: Optional[EvidencePackage]) -> str:
    """Create a concise evidence summary for the LLM."""
    if not package:
        return "No evidence available."

    lines = []
    lines.append(f"Entities analyzed: {len(package.retrieved_entities)}")
    lines.append(f"Evidence items: {len(package.evidence_items)}")
    lines.append(f"Provenance sources: {', '.join(package.provenance[:10])}")

    # Group by entity
    for entity in package.retrieved_entities[:5]:
        if isinstance(entity, dict) and "entity_id" in entity:
            lines.append(f"\nEntity: {entity.get('name', '')} ({entity.get('entity_id', '')})")
            lines.append(f"  Labels: {entity.get('labels', '')}")
            if "centrality" in entity:
                for metric, value in entity["centrality"].items():
                    if value > 0:
                        lines.append(f"  {metric}: {value:.6f}")
            if "community" in entity:
                for algo, comm in entity["community"].items():
                    if isinstance(comm, int) and comm >= 0:
                        lines.append(f"  {algo} community: {comm}")

    return "\n".join(lines)


def _fallback_reasoner(question: str, package: Optional[EvidencePackage], plan: Dict[str, Any]) -> str:
    """Fallback reasoner using template-based answers."""
    if not package or not package.evidence_items:
        return "## Answer\nI couldn't retrieve sufficient evidence to answer your question.\n\n## Evidence\nNo evidence items retrieved.\n\n## Limitations\nRetrieval may have failed or question may not match available analytics."

    answer_type = plan.get("answer_type", "explanation")

    if answer_type == "list":
        return _format_list_answer(question, package)
    elif answer_type == "profile":
        return _format_profile_answer(question, package)
    elif answer_type == "comparison":
        return _format_comparison_answer(question, package)
    else:
        return _format_explanation_answer(question, package)


def _format_list_answer(question: str, package: EvidencePackage) -> str:
    """Format answer as a list - only show entities that were actually retrieved."""
    lines = ["## Answer", ""]

    # Build name lookup from retrieved entities only
    retrieved_names = {}
    for entity in package.retrieved_entities:
        if isinstance(entity, dict) and "entity_id" in entity:
            name = entity.get("name", "")
            if name and str(name).lower() != "nan":
                retrieved_names[entity["entity_id"]] = name

    # Group evidence by entity, but only for retrieved entities with valid names
    entity_evidence = {}
    for item in package.evidence_items:
        eid = item.entity_id
        if eid in retrieved_names:
            if eid not in entity_evidence:
                entity_evidence[eid] = {"name": retrieved_names[eid], "items": []}
            entity_evidence[eid]["items"].append(item)

    # Sort by betweenness or primary metric
    for eid, data in sorted(entity_evidence.items(),
                            key=lambda x: max([i.value for i in x[1]["items"]
                                               if isinstance(i.value, (int, float))], default=0),
                            reverse=True)[:15]:
        name = data["name"]
        lines.append(f"**{name}**")
        for item in data["items"][:3]:
            if isinstance(item.value, (int, float)):
                lines.append(f"  - {item.metric}: {item.value:.6f} [{item.source}]")
            else:
                lines.append(f"  - {item.metric}: {item.value} [{item.source}]")

    lines.append("\n## Evidence")
    for item in package.evidence_items[:20]:
        lines.append(f"- {item.entity_id}: {item.metric} = {item.value} (source: {item.source})")

    lines.append("\n## Limitations")
    lines.append("- Similarity analyses are sampled (20 patients only)")
    lines.append("- Centrality computed on undirected graph approximation")
    lines.append("- Static graph snapshot, no temporal evolution")

    return "\n".join(lines)


def _format_profile_answer(question: str, package: EvidencePackage) -> str:
    """Format answer as entity profile."""
    lines = ["## Entity Profile", ""]

    # Prefer non-generic entities for profile
    generic_labels = {"gender", "ethnicity", "race", "marital", "prefix", "suffix", "city", "state", "county", "zip"}
    entity_to_show = None
    for entity in package.retrieved_entities:
        if isinstance(entity, dict):
            labels = entity.get("labels", "").lower()
            entity_labels = [l.strip() for l in labels.split(",") if l.strip()]
            if any(l not in generic_labels for l in entity_labels):
                entity_to_show = entity
                break

    if entity_to_show is None and package.retrieved_entities:
        entity_to_show = package.retrieved_entities[0]

    if entity_to_show and isinstance(entity_to_show, dict):
        lines.append(f"**Name:** {entity_to_show.get('name', 'Unknown')}")
        lines.append(f"**ID:** {entity_to_show.get('entity_id', 'Unknown')}")
        lines.append(f"**Labels:** {entity_to_show.get('labels', 'Unknown')}")
        lines.append("")

        if "centrality" in entity_to_show:
            lines.append("### Centrality Metrics")
            for metric, value in entity_to_show["centrality"].items():
                if value > 0:
                    lines.append(f"- {metric}: {value:.6f} [centrality/{metric}.csv]")
            lines.append("")

        if "community" in entity_to_show:
            lines.append("### Community Memberships")
            for algo, comm in entity_to_show["community"].items():
                if isinstance(comm, int) and comm >= 0:
                    lines.append(f"- {algo}: Community {comm} [community/{algo}.csv]")
            lines.append("")

        if "structural" in entity_to_show:
            lines.append("### Structural Properties")
            for prop, value in entity_to_show["structural"].items():
                if value:
                    lines.append(f"- {prop}: {value}")
            lines.append("")

    lines.append("## Evidence")
    for item in package.evidence_items:
        lines.append(f"- {item.metric}: {item.value} [{item.source}]")

    lines.append("\n## Limitations")
    lines.append("- Centrality computed on undirected graph approximation")
    lines.append("- Static graph snapshot")

    return "\n".join(lines)


def _format_comparison_answer(question: str, package: EvidencePackage) -> str:
    """Format answer as comparison."""
    lines = ["## Community Comparison", ""]

    # Get community stats from evidence
    communities = {}
    for item in package.evidence_items:
        if "community" in item.metric and isinstance(item.value, int):
            algo = item.metric.replace("_community", "")
            if algo not in communities:
                communities[algo] = set()
            communities[algo].add(item.value)

    lines.append("### Communities Detected")
    for algo, comms in communities.items():
        lines.append(f"- {algo}: {len(comms)} communities (IDs: {sorted(comms)[:10]})")

    lines.append("\n## Evidence")
    for item in package.evidence_items[:20]:
        lines.append(f"- {item.metric}: {item.value} [{item.source}]")

    lines.append("\n## Limitations")
    lines.append("- Leiden/Louvain on undirected graph")
    lines.append("- Modularity ~0.499 indicates moderate community structure")

    return "\n".join(lines)


def _format_explanation_answer(question: str, package: EvidencePackage) -> str:
    """Format answer as explanation."""
    lines = ["## Answer", ""]

    if package.evidence_items:
        lines.append(f"Based on {len(package.evidence_items)} evidence items from {len(package.provenance)} sources:")
        lines.append("")

        # Top metrics
        metrics_seen = {}
        for item in package.evidence_items:
            if isinstance(item.value, (int, float)):
                key = item.metric
                if key not in metrics_seen or item.value > metrics_seen[key][0]:
                    metrics_seen[key] = (item.value, item.entity_id, item.source)

        for metric, (value, eid, source) in sorted(metrics_seen.items(),
                                                    key=lambda x: x[1][0],
                                                    reverse=True)[:10]:
            entity_name = ""
            for ent in package.retrieved_entities:
                if isinstance(ent, dict) and ent.get("entity_id") == eid:
                    entity_name = ent.get("name", eid[:20])
                    break
            lines.append(f"- **{metric}**: {value:.6f} ({entity_name}) [{source}]")

    lines.append("\n## Evidence")
    for item in package.evidence_items[:15]:
        lines.append(f"- {item.metric}: {item.value} [{item.source}]")

    lines.append("\n## Limitations")
    lines.append("- Centrality on undirected approximation")
    lines.append("- Sampled similarity/path analyses")
    lines.append("- No causal interpretation of structural metrics")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node: Critic / Validator
# ---------------------------------------------------------------------------

def critic_node(state: AgentState) -> Dict[str, Any]:
    """Validate the reasoner's answer against evidence."""
    answer = state.get("reasoner_answer", "")
    evidence_package = state.get("evidence_package")
    question = state.get("question", "")

    if not LANGGRAPH_AVAILABLE:
        return _fallback_critic(answer, evidence_package, question)

    system_prompt = get_prompt("critic")

    # Prepare evidence for critic
    evidence_list = []
    if evidence_package:
        for item in evidence_package.evidence_items:
            evidence_list.append({
                "source": item.source,
                "metric": item.metric,
                "entity_id": item.entity_id,
                "value": item.value,
                "description": item.description
            })

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Answer to validate:
{answer}

Evidence Package:
{json.dumps(evidence_list, default=str)[:8000]}

Output validation report:""")
        ]
        response = llm.invoke(messages)
        validation = json.loads(response.content)
    except Exception as e:
        print(f"Critic LLM failed: {e}, using fallback")
        validation = _fallback_critic(answer, evidence_package)

    passed = validation.get("validation_status") == "PASS"

    return {
        "validation_report": validation,
        "validation_passed": passed,
        "step_count": state.get("step_count", 0) + 1
    }


def _fallback_critic(answer: str, package: Optional[EvidencePackage], question: str = "") -> Dict[str, Any]:
    """Fallback critic using the new validation layer."""
    if not package:
        return {
            "validation_status": "FAIL",
            "evidence_coverage": 0.0,
            "claims_checked": 0,
            "claims_supported": 0,
            "unsupported_claims": [{"claim": "No evidence package", "reason": "Empty evidence"}],
            "value_mismatches": [],
            "missing_limitations": []
        }

    # Use new validation layer
    try:
        from graph_intelligence.validation import (
            extract_claims,
            match_claims_to_evidence,
            calculate_coverage,
            detect_hallucinations,
            generate_validation_report
        )

        # Extract claims from answer
        claims = extract_claims(answer)

        # Match claims to evidence
        matches = match_claims_to_evidence(claims, package)

        # Calculate coverage
        coverage = calculate_coverage(matches, package)

        # Detect hallucinations
        issues = detect_hallucinations(matches, coverage, package)

        # Generate validation report
        report = generate_validation_report(question, answer, matches, coverage, issues)

        # Convert to expected format
        return report.to_dict()

    except Exception as e:
        print(f"Validation layer failed: {e}, using basic fallback")
        # Fallback to basic checks
        evidence_metrics = set(item.metric for item in package.evidence_items)

        unsupported = []
        if "referral" in answer.lower() and "betweenness_centrality" not in evidence_metrics:
            unsupported.append({"claim": "referral hub/bridge", "reason": "No betweenness centrality evidence"})

        if "similar" in answer.lower() and "node2vec" not in [e.source for e in package.evidence_items]:
            unsupported.append({"claim": "similar entities", "reason": "No embedding evidence"})

        status = "PASS" if len(unsupported) == 0 else ("PARTIAL" if len(unsupported) < 3 else "FAIL")

        return {
            "validation_status": status,
            "evidence_coverage": 1.0 - (len(unsupported) / max(len(evidence_metrics), 1)),
            "claims_checked": len(evidence_metrics),
            "claims_supported": len(evidence_metrics) - len(unsupported),
            "unsupported_claims": unsupported,
            "value_mismatches": [],
            "missing_limitations": ["Similarity analyses are sampled (20 patients only)"]
        }


# ---------------------------------------------------------------------------
# Node: Formatter
# ---------------------------------------------------------------------------

def formatter_node(state: AgentState) -> Dict[str, Any]:
    """Format final answer for display."""
    answer = state.get("reasoner_answer", "")
    validation = state.get("validation_report", {})

    if not LANGGRAPH_AVAILABLE:
        # Just return the reasoner answer with validation note
        formatted = answer
        if validation.get("validation_status") != "PASS":
            formatted += f"\n\n---\n⚠️ **Validation**: {validation.get('validation_status', 'UNKNOWN')} - {len(validation.get('unsupported_claims', []))} unsupported claims"
        return {"final_answer": formatted, "formatted_output": formatted, "step_count": state.get("step_count", 0) + 1}

    system_prompt = get_prompt("formatter")

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Answer:
{answer}

Validation Report:
{json.dumps(validation, default=str)}

Format for display:""")
        ]
        response = llm.invoke(messages)
        formatted = response.content
    except Exception as e:
        print(f"Formatter LLM failed: {e}")
        formatted = answer

    return {
        "final_answer": answer,
        "formatted_output": formatted,
        "step_count": state.get("step_count", 0) + 1
    }


# ---------------------------------------------------------------------------
# Build Workflow
# ---------------------------------------------------------------------------

def build_graph_intelligence_agent():
    """Build the LangGraph workflow."""
    if not LANGGRAPH_AVAILABLE:
        print("LangGraph not available, returning None")
        return None

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("entity_resolution", entity_resolution_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("formatter", formatter_node)

    # Define edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "entity_resolution")
    workflow.add_edge("entity_resolution", "retrieval")
    workflow.add_edge("retrieval", "reasoner")
    workflow.add_edge("reasoner", "critic")
    workflow.add_edge("critic", "formatter")
    workflow.add_edge("formatter", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# High-Level API
# ---------------------------------------------------------------------------

def run_graph_agent(question: str, session_id: str = "default") -> Dict[str, Any]:
    """Run the full graph intelligence agent on a question."""
    if not LANGGRAPH_AVAILABLE:
        # Run fallback pipeline
        return _run_fallback_pipeline(question, session_id)

    agent = build_graph_intelligence_agent()
    if agent is None:
        return _run_fallback_pipeline(question, session_id)

    initial_state = AgentState(
        question=question,
        session_id=session_id,
        plan=None,
        resolved_entities=[],
        evidence_package=None,
        retrieval_results=[],
        reasoner_answer="",
        reasoner_evidence=[],
        validation_report=None,
        validation_passed=False,
        final_answer="",
        formatted_output="",
        errors=[],
        step_count=0
    )

    result = agent.invoke(initial_state)
    return {
        "question": question,
        "answer": result.get("final_answer", ""),
        "formatted": result.get("formatted_output", ""),
        "validation": result.get("validation_report", {}),
        "evidence": result.get("evidence_package"),
        "plan": result.get("plan", {}),
        "errors": result.get("errors", [])
    }


def _run_fallback_pipeline(question: str, session_id: str) -> Dict[str, Any]:
    """Run the agent pipeline without LLM (using fallback functions)."""
    # Plan
    plan = _fallback_planner(question)

    # Resolve entities
    resolved = search_entities(question)

    # Check if we have specific entities
    generic_labels = {"gender", "ethnicity", "race", "marital", "prefix", "suffix", "city", "state", "county", "zip"}
    has_specific = False
    for e in resolved:
        labels = e.get("labels", "").lower()
        entity_labels = [l.strip() for l in labels.split(",") if l.strip()]
        if any(l not in generic_labels for l in entity_labels):
            has_specific = True
            break

    # Retrieve evidence
    if not has_specific:
        # Use broad question retrieval
        from graph_intelligence.intelligence.retrieval import get_evidence_for_broad_question
        package = get_evidence_for_broad_question(question)
    else:
        # Standard retrieval
        assembler = EvidenceAssembler()
        entity_ids = [e["entity_id"] for e in resolved] if resolved else None
        package = assembler.assemble(question, entity_ids)

        # Replace placeholders
        for step in plan.get("retrieval_steps", []):
            params = step.get("params", {})
            for key, value in params.items():
                if value == "PLACEHOLDER" and resolved:
                    # For profile intent, prefer non-generic entities
                    intent = plan.get("intent", "").lower()
                    if "profile" in intent:
                        # Prefer entities that are not generic categories
                        generic_labels = {"gender", "ethnicity", "race", "marital", "prefix", "suffix", "city", "state", "county", "zip"}
                        for e in resolved:
                            labels = e.get("labels", "").lower()
                            entity_labels = [l.strip() for l in labels.split(",") if l.strip()]
                            if any(l not in generic_labels for l in entity_labels):
                                params[key] = e["entity_id"]
                                break
                        else:
                            # Fallback to first if all are generic
                            params[key] = resolved[0]["entity_id"]
                    else:
                        # Default to first resolved entity
                        params[key] = resolved[0]["entity_id"]

        # Execute plan steps
        for step in plan.get("retrieval_steps", []):
            retriever_name = step.get("retriever")
            method_name = step.get("method")
            params = step.get("params", {})

            try:
                if retriever_name == "analytics_retriever":
                    from graph_intelligence.intelligence.retrieval import AnalyticsRetriever
                    retriever = AnalyticsRetriever()
                    method = getattr(retriever, method_name)
                    result = method(**params)

                    if method_name == "get_entity_analytics" and result:
                        for metric, value in result.get("centrality", {}).items():
                            if value > 0:
                                package.add_evidence(EvidenceItem(
                                    source=f"centrality/{metric}.csv",
                                    metric=metric,
                                    entity_id=result["entity_id"],
                                    value=value,
                                    description=f"{metric}: {value:.6f}"
                                ))

                elif retriever_name == "graph_retriever":
                    from graph_intelligence.intelligence.retrieval import GraphRetriever
                    retriever = GraphRetriever()
                    method = getattr(retriever, method_name)
                    result = method(**params)

                elif retriever_name == "embedding_retriever":
                    from graph_intelligence.intelligence.retrieval import EmbeddingRetriever
                    retriever = EmbeddingRetriever()
                    method = getattr(retriever, method_name)
                    result = method(**params)

            except Exception as e:
                print(f"Fallback retrieval failed: {e}")

    # Reason
    answer = _fallback_reasoner(question, package, plan)

    # Validate
    validation = _fallback_critic(answer, package)

    return {
        "question": question,
        "answer": answer,
        "formatted": answer,
        "validation": validation,
        "evidence": package,
        "plan": plan,
        "errors": []
    }


# ---------------------------------------------------------------------------
# Demo / Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test with a sample question
    question = "Which entities are important bridges between communities?"
    print(f"Question: {question}")
    print("Running agent...")

    result = run_graph_agent(question)
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nValidation: {result['validation']}")