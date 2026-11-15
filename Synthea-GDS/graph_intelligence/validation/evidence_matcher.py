"""
Graph Intelligence Platform — Evidence Matcher

Matches extracted claims to evidence items in the EvidencePackage.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from graph_intelligence.intelligence.retrieval import EvidencePackage, EvidenceItem
from graph_intelligence.validation.claim_extractor import Claim, ClaimType


@dataclass
class MatchResult:
    """Result of matching a claim to evidence."""
    claim: Claim
    matched_evidence: List[EvidenceItem] = None
    match_score: float = 0.0
    match_type: str = "none"  # exact, fuzzy, partial, none
    supporting: bool = False
    contradicting: bool = False
    details: str = ""

    def __post_init__(self):
        if self.matched_evidence is None:
            self.matched_evidence = []


class EvidenceMatcher:
    """Matches claims to evidence items."""

    def __init__(self, fuzzy_threshold: float = 0.7):
        self.fuzzy_threshold = fuzzy_threshold
        self._entity_name_to_id = {}  # Map from entity name to Neo4j ID

    def set_entity_mapping(self, evidence_package: EvidencePackage):
        """Build entity name to ID mapping from retrieved entities."""
        self._entity_name_to_id = {}
        for entity in evidence_package.retrieved_entities:
            if isinstance(entity, dict) and "entity_id" in entity:
                name = entity.get("name", "")
                if isinstance(name, str):
                    name = name.strip().lower()
                    if name and name != "nan":
                        self._entity_name_to_id[name] = entity["entity_id"]
                # Also map by labels
                labels = entity.get("labels", "")
                if isinstance(labels, str):
                    labels = labels.strip().lower()
                    if labels and labels != "nan":
                        for label in labels.split(","):
                            label = label.strip()
                            if label:
                                self._entity_name_to_id[label] = entity["entity_id"]

    def match(self, claims: List[Claim], evidence_package: EvidencePackage) -> List[MatchResult]:
        """Match all claims to evidence."""
        results = []

        for claim in claims:
            match = self._match_single_claim(claim, evidence_package)
            results.append(match)

        return results

    def _match_single_claim(self, claim: Claim, package: EvidencePackage) -> MatchResult:
        """Match a single claim to evidence."""
        best_matches = []
        best_score = 0.0
        match_type = "none"

        for evidence in package.evidence_items:
            score, mtype = self._score_match_with_package(claim, evidence, package)
            # Only consider evidence for the correct entity
            if score > best_score and score > 0.5:  # Must have entity match
                best_score = score
                best_matches = [evidence]
                match_type = mtype
            elif score == best_score and score > 0.5:
                best_matches.append(evidence)

        # Determine if supporting or contradicting
        supporting = False
        contradicting = False
        details = ""

        if best_matches:
            for ev in best_matches:
                if claim.claim_type == ClaimType.METRIC_VALUE:
                    sup, cont, det = self._check_metric_value(claim, ev)
                    if sup:
                        supporting = True
                        details = det
                    elif cont:
                        contradicting = True
                        details = det

                elif claim.claim_type == ClaimType.COMMUNITY_MEMBERSHIP:
                    sup, cont, det = self._check_community(claim, ev)
                    if sup:
                        supporting = True
                        details = det
                    elif cont:
                        contradicting = True
                        details = det

                elif claim.claim_type == ClaimType.RANKING:
                    sup, det = self._check_ranking(claim, ev)
                    if sup:
                        supporting = True
                        details = det

                elif claim.claim_type == ClaimType.COUNT:
                    sup, det = self._check_count(claim, ev)
                    if sup:
                        supporting = True
                        details = det

                elif claim.claim_type == ClaimType.STRUCTURAL_PROPERTY:
                    sup, det = self._check_structural(claim, ev)
                    if sup:
                        supporting = True
                        details = det

        return MatchResult(
            claim=claim,
            matched_evidence=best_matches,
            match_score=best_score,
            match_type=match_type,
            supporting=supporting,
            contradicting=contradicting,
            details=details
        )

    def _score_match(self, claim: Claim, evidence: EvidenceItem) -> Tuple[float, str]:
        """Score how well a claim matches an evidence item. Returns (score, match_type)."""
        # Check entity match
        entity_match = self._entity_match(claim.entities, evidence.entity_id)
        if not entity_match and claim.entities:
            return 0.0, "none"

        # Check metric match
        metric_match = self._metric_match(claim.metrics, evidence.metric)
        if not metric_match:
            return 0.0, "none"

        # If both match
        if entity_match == "exact" and metric_match == "exact":
            return 1.0, "exact"
        elif entity_match == "fuzzy" and metric_match == "exact":
            return 0.85, "fuzzy"
        elif entity_match == "exact" and metric_match == "fuzzy":
            return 0.8, "fuzzy"
        elif entity_match == "fuzzy" and metric_match == "fuzzy":
            return 0.6, "partial"
        elif entity_match == "any" and metric_match == "exact":
            return 0.7, "partial"  # Claim doesn't specify entity, but metric matches
        elif metric_match == "exact":
            return 0.5, "partial"  # Metric matches but entity unclear

        return 0.0, "none"

    def _entity_match(self, claim_entities: List[str], evidence_entity: str) -> str:
        """Check if claim entities match evidence entity."""
        if not claim_entities:
            return "any"

        for ce in claim_entities:
            # Exact match on Neo4j ID
            if ce == evidence_entity:
                return "exact"

            # Fuzzy match on name vs Neo4j ID
            if self._fuzzy_match(ce, evidence_entity) > self.fuzzy_threshold:
                return "fuzzy"

        return "none"

    def _get_entity_name_for_id(self, entity_id: str, package) -> str:
        """Look up entity name from retrieved entities."""
        if not package or not package.retrieved_entities:
            return ""
        for ent in package.retrieved_entities:
            if isinstance(ent, dict) and ent.get("entity_id") == entity_id:
                return ent.get("name", "")
        return ""

    def _entity_match_with_package(self, claim_entities: List[str], evidence_entity: str, package) -> str:
        """Check if claim entities match evidence entity using package for name lookup."""
        if not claim_entities:
            return "any"

        for ce in claim_entities:
            # Ensure ce is a string
            if not isinstance(ce, str):
                ce = str(ce)

            # Exact match on Neo4j ID
            if ce == evidence_entity:
                return "exact"

            # Check if claim entity matches the name of the evidence entity - EXACT match only for names
            evidence_name = self._get_entity_name_for_id(evidence_entity, package)
            if isinstance(evidence_name, str) and evidence_name and evidence_name != "nan":
                # Require exact name match (case-insensitive) for metric value claims
                if ce.strip().lower() == evidence_name.strip().lower():
                    return "exact"

            # Fuzzy match on name with higher threshold
            if self._fuzzy_match(ce, evidence_entity) > 0.9:
                return "fuzzy"

        return "none"

    def _score_match_with_package(self, claim: Claim, evidence: EvidenceItem, package) -> Tuple[float, str]:
        """Score how well a claim matches an evidence item using package for name lookup."""
        # Check entity match with package
        entity_match = self._entity_match_with_package(claim.entities, evidence.entity_id, package)
        if not entity_match and claim.entities:
            return 0.0, "none"

        # Check metric match
        metric_match = self._metric_match(claim.metrics, evidence.metric)
        if not metric_match:
            return 0.0, "none"

        # If both match - require exact entity match for metric values
        if entity_match == "exact" and metric_match == "exact":
            return 1.0, "exact"
        elif entity_match == "exact" and metric_match == "fuzzy":
            return 0.8, "fuzzy"
        elif entity_match == "fuzzy" and metric_match == "exact":
            return 0.5, "partial"  # Fuzzy entity match is risky for metric values
        elif entity_match == "any" and metric_match == "exact":
            return 0.5, "partial"  # Claim doesn't specify entity
        elif metric_match == "exact":
            return 0.3, "partial"  # Metric matches but entity unclear

        return 0.0, "none"

    def _metric_match(self, claim_metrics: List[str], evidence_metric: str) -> str:
        """Check if claim metrics match evidence metric."""
        if not claim_metrics:
            return "none"

        for cm in claim_metrics:
            cm_lower = cm.lower()
            ev_lower = evidence_metric.lower()

            # Exact match
            if cm_lower == ev_lower:
                return "exact"

            # Fuzzy match (high similarity)
            if self._fuzzy_match(cm_lower, ev_lower) > self.fuzzy_threshold:
                return "fuzzy"

            # Partial match - only for prefix/suffix matches like "betweenness" -> "betweenness_centrality"
            # Not for shared substrings like "centrality"
            if cm_lower.endswith('_centrality') and ev_lower.endswith('_centrality'):
                # Both are centrality metrics, check the prefix
                cm_prefix = cm_lower.replace('_centrality', '')
                ev_prefix = ev_lower.replace('_centrality', '')
                if cm_prefix == ev_prefix:
                    return "exact"
                if cm_prefix in ev_prefix or ev_prefix in cm_prefix:
                    return "fuzzy"

            # Generic partial match for other metrics
            if '_' in cm_lower and '_' in ev_lower:
                # Both have underscores, check prefix before underscore
                cm_parts = cm_lower.split('_')
                ev_parts = ev_lower.split('_')
                if cm_parts[0] == ev_parts[0]:
                    return "fuzzy"

        return "none"

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Compute fuzzy string similarity."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _check_metric_value(self, claim: Claim, evidence: EvidenceItem) -> Tuple[bool, bool, str]:
        """Check if evidence supports metric value claim."""
        if not claim.values or not isinstance(evidence.value, (int, float)):
            return False, False, ""

        claimed_value = claim.values[0]
        if isinstance(claimed_value, str):
            try:
                claimed_value = float(claimed_value)
            except ValueError:
                return False, False, ""

        evidence_value = evidence.value

        # Check if values are approximately equal (within 5% relative error)
        if evidence_value == 0:
            rel_error = abs(claimed_value - evidence_value)
        else:
            rel_error = abs(claimed_value - evidence_value) / abs(evidence_value)

        if rel_error <= 0.05:
            return True, False, f"Value matches: claimed {claimed_value}, evidence {evidence_value}"
        elif rel_error <= 0.2:
            return True, False, f"Value approximately matches: claimed {claimed_value}, evidence {evidence_value}"
        else:
            return False, True, f"Value mismatch: claimed {claimed_value}, evidence {evidence_value}"

    def _check_community(self, claim: Claim, evidence: EvidenceItem) -> Tuple[bool, bool, str]:
        """Check if evidence supports community membership claim."""
        if not claim.values:
            return False, False, ""

        claimed_comm = claim.values[0]
        evidence_comm = evidence.value

        # Handle string community IDs (e.g., "seed_1")
        if isinstance(claimed_comm, str) and isinstance(evidence_comm, str):
            if claimed_comm == evidence_comm:
                return True, False, f"Community matches: {claimed_comm}"
            else:
                return False, True, f"Community mismatch: claimed {claimed_comm}, evidence {evidence_comm}"

        # Handle numeric
        try:
            claimed_num = int(claimed_comm) if isinstance(claimed_comm, (str, int)) else claimed_comm
            evidence_num = int(evidence_comm) if isinstance(evidence_comm, (str, int)) else evidence_comm

            if claimed_num == evidence_num:
                return True, False, f"Community matches: {claimed_num}"
            else:
                return False, True, f"Community mismatch: claimed {claimed_num}, evidence {evidence_num}"
        except (ValueError, TypeError):
            return False, False, ""

    def _check_ranking(self, claim: Claim, evidence: EvidenceItem) -> Tuple[bool, str]:
        """Check if evidence supports ranking claim (top-N)."""
        # For ranking claims, we check if the evidence entity is indeed in top-N
        # This would require knowing the full ranking, which we don't have in single evidence item
        # So we return partial support if metric matches
        if claim.metrics and claim.metrics[0].lower() == evidence.metric.lower():
            return True, f"Evidence shows {evidence.metric} = {evidence.value} for {evidence.entity_id}"
        return False, ""

    def _check_count(self, claim: Claim, evidence: EvidenceItem) -> Tuple[bool, str]:
        """Check if evidence supports count claim."""
        # Count claims are about total number of communities
        # Individual evidence items don't directly support this
        return False, ""

    def _check_structural(self, claim: Claim, evidence: EvidenceItem) -> Tuple[bool, str]:
        """Check if evidence supports structural property claim."""
        if claim.metrics and claim.metrics[0].lower() in evidence.metric.lower():
            if evidence.value is True or evidence.value == 1:
                return True, f"Evidence confirms {evidence.metric}"
        return False, ""


def match_claims_to_evidence(claims: List[Claim], evidence_package: EvidencePackage) -> List[MatchResult]:
    """Convenience function to match claims to evidence."""
    matcher = EvidenceMatcher()
    matcher.set_entity_mapping(evidence_package)
    return matcher.match(claims, evidence_package)