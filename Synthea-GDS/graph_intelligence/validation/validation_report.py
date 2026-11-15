"""
Graph Intelligence Platform — Validation Report Generator

Generates comprehensive validation reports from match results and hallucination detection.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from graph_intelligence.intelligence.retrieval import EvidencePackage
from graph_intelligence.validation.claim_extractor import Claim
from graph_intelligence.validation.evidence_matcher import MatchResult
from graph_intelligence.validation.coverage_calculator import CoverageMetrics
from graph_intelligence.validation.hallucination_detector import HallucinationIssue, HallucinationSeverity


@dataclass
class ValidationReport:
    """Complete validation report for an answer."""
    question: str
    answer: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Overall status
    validation_status: str = "UNKNOWN"  # PASS, PARTIAL, FAIL

    # Coverage metrics
    coverage: CoverageMetrics = None

    # Match results
    matches: List[MatchResult] = field(default_factory=list)

    # Hallucination issues
    issues: List[HallucinationIssue] = field(default_factory=list)

    # Summary counts
    claims_checked: int = 0
    claims_supported: int = 0
    claims_unsupported: int = 0
    claims_contradicted: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0

    def __post_init__(self):
        if self.coverage:
            self.claims_checked = self.coverage.total_claims
            self.claims_supported = self.coverage.claims_supported
            self.claims_contradicted = self.coverage.claims_contradicted
            self.claims_unmatched = self.coverage.claims_unmatched

        self.critical_issues = sum(1 for i in self.issues if i.severity == HallucinationSeverity.CRITICAL)
        self.high_issues = sum(1 for i in self.issues if i.severity == HallucinationSeverity.HIGH)
        self.medium_issues = sum(1 for i in self.issues if i.severity == HallucinationSeverity.MEDIUM)
        self.low_issues = sum(1 for i in self.issues if i.severity == HallucinationSeverity.LOW)

        # Determine overall status
        if self.critical_issues > 0:
            self.validation_status = "FAIL"
        elif self.claims_checked > 0 and self.claims_supported / self.claims_checked < 0.5:
            self.validation_status = "FAIL"
        elif self.high_issues > 0 or self.claims_contradicted > 0:
            self.validation_status = "PARTIAL"
        elif self.claims_checked == 0:
            self.validation_status = "PARTIAL"
        else:
            self.validation_status = "PASS"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "question": self.question,
            "answer": self.answer,
            "timestamp": self.timestamp,
            "validation_status": self.validation_status,
            "claims_checked": self.claims_checked,
            "claims_supported": self.claims_supported,
            "claims_unsupported": self.claims_unmatched,
            "claims_contradicted": self.claims_contradicted,
            "evidence_coverage": self.coverage.claim_coverage if self.coverage else 0,
            "evidence_utilization": self.coverage.evidence_utilization if self.coverage else 0,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "medium_issues": self.medium_issues,
            "low_issues": self.low_issues,
            "issues": [
                {
                    "claim_text": i.claim_text,
                    "claim_type": i.claim_type.value,
                    "severity": i.severity.value,
                    "reason": i.reason,
                    "evidence_context": i.evidence_context,
                    "suggested_correction": i.suggested_correction
                }
                for i in self.issues
            ],
            "matches": [
                {
                    "claim_text": m.claim.text,
                    "claim_type": m.claim.claim_type.value,
                    "match_score": m.match_score,
                    "match_type": m.match_type,
                    "supporting": m.supporting,
                    "contradicting": m.contradicting,
                    "details": m.details,
                    "matched_evidence": [
                        {
                            "entity_id": ev.entity_id,
                            "metric": ev.metric,
                            "value": ev.value,
                            "source": ev.source
                        }
                        for ev in m.matched_evidence
                    ]
                }
                for m in self.matches
            ]
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str, indent=2)

    def to_markdown(self) -> str:
        """Format as markdown report."""
        lines = [
            f"# Validation Report",
            f"",
            f"**Question:** {self.question}",
            f"**Timestamp:** {self.timestamp}",
            f"**Status:** {self.validation_status}",
            f"",
            f"## Summary",
            f"- Claims Checked: {self.claims_checked}",
            f"- Claims Supported: {self.claims_supported}",
            f"- Claims Unsupported: {self.claims_unmatched}",
            f"- Claims Contradicted: {self.claims_contradicted}",
            f"- Evidence Coverage: {self.coverage.claim_coverage:.1%}" if self.coverage else "- Evidence Coverage: N/A",
            f"- Evidence Utilization: {self.coverage.evidence_utilization:.1%}" if self.coverage else "- Evidence Utilization: N/A",
            f"",
            f"## Issues by Severity",
            f"- 🔴 Critical: {self.critical_issues}",
            f"- 🟠 High: {self.high_issues}",
            f"- 🟡 Medium: {self.medium_issues}",
            f"- 🟢 Low: {self.low_issues}",
            f"",
        ]

        if self.issues:
            lines.append("## Issues Detail")
            for issue in self.issues:
                severity_icon = {
                    HallucinationSeverity.CRITICAL: "🔴",
                    HallucinationSeverity.HIGH: "🟠",
                    HallucinationSeverity.MEDIUM: "🟡",
                    HallucinationSeverity.LOW: "🟢"
                }.get(issue.severity, "⚪")

                lines.append(f"### {severity_icon} {issue.claim_type.value}: {issue.claim_text}")
                lines.append(f"**Severity:** {issue.severity.value}")
                lines.append(f"**Reason:** {issue.reason}")
                if issue.evidence_context:
                    lines.append(f"**Evidence Context:** {issue.evidence_context}")
                if issue.suggested_correction:
                    lines.append(f"**Suggested Correction:** {issue.suggested_correction}")
                lines.append("")

        if self.matches:
            lines.append("## Claim-Evidence Matches")
            for match in self.matches:
                status = "✅" if match.supporting else ("❌" if match.contradicting else "⚪")
                lines.append(f"{status} **{match.claim.claim_type.value}**: {match.claim.text}")
                lines.append(f"   - Match Score: {match.match_score:.2f} ({match.match_type})")
                if match.details:
                    lines.append(f"   - Details: {match.details}")
                if match.matched_evidence:
                    for ev in match.matched_evidence:
                        lines.append(f"   - Evidence: {ev.metric} = {ev.value} for {ev.entity_id} [{ev.source}]")
                lines.append("")

        return "\n".join(lines)


def generate_validation_report(question: str, answer: str, matches: List[MatchResult],
                               coverage: CoverageMetrics, issues: List[HallucinationIssue]) -> ValidationReport:
    """Generate a complete validation report."""
    return ValidationReport(
        question=question,
        answer=answer,
        coverage=coverage,
        matches=matches,
        issues=issues
    )