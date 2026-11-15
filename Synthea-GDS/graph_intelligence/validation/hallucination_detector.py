"""
Graph Intelligence Platform — Hallucination Detector

Detects unsupported claims, contradictions, and potential hallucinations in answers.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from graph_intelligence.intelligence.retrieval import EvidencePackage, EvidenceItem
from graph_intelligence.validation.claim_extractor import Claim, ClaimType
from graph_intelligence.validation.evidence_matcher import MatchResult
from graph_intelligence.validation.coverage_calculator import CoverageMetrics


class HallucinationSeverity(Enum):
    """Severity levels for detected issues."""
    CRITICAL = "critical"      # Contradicted by evidence
    HIGH = "high"              # Unsupported specific metric claim
    MEDIUM = "medium"          # Unsupported general claim
    LOW = "low"                # Minor unsupported statement


@dataclass
class HallucinationIssue:
    """A detected hallucination or unsupported claim."""
    claim_text: str
    claim_type: ClaimType
    severity: HallucinationSeverity
    reason: str
    evidence_context: str = ""
    suggested_correction: str = ""


class HallucinationDetector:
    """Detects hallucinations and unsupported claims in answers."""

    def __init__(self, min_coverage_threshold: float = 0.5):
        self.min_coverage_threshold = min_coverage_threshold

    def detect(self, matches: List[MatchResult], coverage: CoverageMetrics,
               evidence_package: EvidencePackage) -> List[HallucinationIssue]:
        """Detect hallucinations from match results and coverage."""
        issues = []

        # 1. Check for contradicted claims (CRITICAL)
        for match in matches:
            if match.contradicting:
                issues.append(HallucinationIssue(
                    claim_text=match.claim.text,
                    claim_type=match.claim.claim_type,
                    severity=HallucinationSeverity.CRITICAL,
                    reason=f"Claim contradicted by evidence: {match.details}",
                    evidence_context=f"Evidence: {match.matched_evidence[0].metric} = {match.matched_evidence[0].value} for {match.matched_evidence[0].entity_id}",
                    suggested_correction=f"Correct value: {match.matched_evidence[0].value}"
                ))

        # 2. Check for unsupported specific metric claims (HIGH)
        for match in matches:
            if (match.claim.claim_type == ClaimType.METRIC_VALUE and
                not match.supporting and not match.contradicting):
                issues.append(HallucinationIssue(
                    claim_text=match.claim.text,
                    claim_type=match.claim.claim_type,
                    severity=HallucinationSeverity.HIGH,
                    reason=f"Specific metric value claimed without evidence support",
                    evidence_context=f"No matching evidence found for {match.claim.metrics}"
                ))

        # 3. Check for unsupported community membership claims (HIGH)
        for match in matches:
            if (match.claim.claim_type == ClaimType.COMMUNITY_MEMBERSHIP and
                not match.supporting and not match.contradicting):
                issues.append(HallucinationIssue(
                    claim_text=match.claim.text,
                    claim_type=match.claim.claim_type,
                    severity=HallucinationSeverity.HIGH,
                    reason=f"Community assignment claimed without evidence support",
                    evidence_context=f"No matching evidence found for {match.claim.metrics}"
                ))

        # 4. Check for unsupported structural claims (MEDIUM)
        for match in matches:
            if (match.claim.claim_type == ClaimType.STRUCTURAL_PROPERTY and
                not match.supporting):
                issues.append(HallucinationIssue(
                    claim_text=match.claim.text,
                    claim_type=match.claim.claim_type,
                    severity=HallucinationSeverity.MEDIUM,
                    reason=f"Structural property claimed without evidence support",
                    evidence_context=f"No matching evidence found for {match.claim.metrics}"
                ))

        # 5. Check for unsupported ranking claims (MEDIUM)
        for match in matches:
            if (match.claim.claim_type == ClaimType.RANKING and
                not match.supporting):
                issues.append(HallucinationIssue(
                    claim_text=match.claim.text,
                    claim_type=match.claim.claim_type,
                    severity=HallucinationSeverity.MEDIUM,
                    reason=f"Ranking claim without evidence support",
                    evidence_context=f"No matching evidence for top-{match.claim.values[0] if match.claim.values else 'N'} by {match.claim.metrics}"
                ))

        # 6. Overall low coverage warning
        if coverage.claim_coverage < self.min_coverage_threshold and coverage.total_claims > 0:
            issues.append(HallucinationIssue(
                claim_text="Overall answer",
                claim_type=ClaimType.GENERAL,
                severity=HallucinationSeverity.MEDIUM,
                reason=f"Low evidence coverage: only {coverage.claim_coverage:.1%} of claims supported",
                evidence_context=f"{coverage.claims_supported}/{coverage.total_claims} claims supported"
            ))

        # 7. Check for claims about entities not in evidence
        mentioned_entities = set()
        for match in matches:
            mentioned_entities.update(match.claim.entities)

        evidenced_entities = set(ev.entity_id for ev in evidence_package.evidence_items)
        for entity in mentioned_entities:
            if entity and entity not in evidenced_entities and not any(e in entity for e in evidenced_entities):
                # Check if it's a known entity format
                if entity.startswith("4:") or len(entity) > 20:
                    issues.append(HallucinationIssue(
                        claim_text=f"Reference to entity {entity}",
                        claim_type=ClaimType.EXISTENCE,
                        severity=HallucinationSeverity.LOW,
                        reason=f"Entity referenced but not in retrieved evidence",
                        evidence_context=f"Entity not found in {len(evidence_package.evidence_items)} evidence items"
                    ))

        return issues


def detect_hallucinations(matches: List[MatchResult], coverage: CoverageMetrics,
                          evidence_package: EvidencePackage) -> List[HallucinationIssue]:
    """Convenience function to detect hallucinations."""
    detector = HallucinationDetector()
    return detector.detect(matches, coverage, evidence_package)