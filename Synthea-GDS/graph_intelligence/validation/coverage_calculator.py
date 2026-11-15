"""
Graph Intelligence Platform — Coverage Calculator

Computes evidence coverage metrics for validation reports.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from graph_intelligence.intelligence.retrieval import EvidencePackage, EvidenceItem
from graph_intelligence.validation.claim_extractor import Claim, ClaimType
from graph_intelligence.validation.evidence_matcher import MatchResult


@dataclass
class CoverageMetrics:
    """Coverage metrics for an answer."""
    total_claims: int = 0
    claims_supported: int = 0
    claims_contradicted: int = 0
    claims_unmatched: int = 0
    evidence_items_used: int = 0
    evidence_items_total: int = 0
    claim_coverage: float = 0.0        # % claims with supporting evidence
    evidence_utilization: float = 0.0  # % evidence items used
    exact_matches: int = 0
    fuzzy_matches: int = 0
    partial_matches: int = 0

    # By claim type
    by_type: Dict[str, Dict[str, int]] = None

    def __post_init__(self):
        if self.by_type is None:
            self.by_type = {}


class CoverageCalculator:
    """Calculates coverage metrics from match results."""

    def __init__(self):
        pass

    def calculate(self, matches: List[MatchResult], evidence_package: EvidencePackage) -> CoverageMetrics:
        """Calculate coverage metrics from match results."""
        metrics = CoverageMetrics()

        metrics.total_claims = len(matches)
        metrics.evidence_items_total = len(evidence_package.evidence_items)

        # Track used evidence items
        used_evidence = set()

        for match in matches:
            claim_type = match.claim.claim_type.value

            if claim_type not in metrics.by_type:
                metrics.by_type[claim_type] = {"total": 0, "supported": 0, "contradicted": 0, "unmatched": 0}

            metrics.by_type[claim_type]["total"] += 1

            if match.supporting:
                metrics.claims_supported += 1
                metrics.by_type[claim_type]["supported"] += 1

                for ev in match.matched_evidence:
                    used_evidence.add(id(ev))

                if match.match_type == "exact":
                    metrics.exact_matches += 1
                elif match.match_type == "fuzzy":
                    metrics.fuzzy_matches += 1
                elif match.match_type == "partial":
                    metrics.partial_matches += 1

            elif match.contradicting:
                metrics.claims_contradicted += 1
                metrics.by_type[claim_type]["contradicted"] += 1

            else:
                metrics.claims_unmatched += 1
                metrics.by_type[claim_type]["unmatched"] += 1

        metrics.evidence_items_used = len(used_evidence)

        # Calculate percentages
        if metrics.total_claims > 0:
            metrics.claim_coverage = metrics.claims_supported / metrics.total_claims

        if metrics.evidence_items_total > 0:
            metrics.evidence_utilization = metrics.evidence_items_used / metrics.evidence_items_total

        return metrics


def calculate_coverage(matches: List[MatchResult], evidence_package: EvidencePackage) -> CoverageMetrics:
    """Convenience function to calculate coverage."""
    calculator = CoverageCalculator()
    return calculator.calculate(matches, evidence_package)