"""
Graph Intelligence Platform — Validation Layer

Provides claim extraction, evidence matching, coverage metrics, and hallucination detection.
"""

from .claim_extractor import ClaimExtractor, extract_claims
from .evidence_matcher import EvidenceMatcher, match_claims_to_evidence
from .coverage_calculator import CoverageCalculator, calculate_coverage
from .hallucination_detector import HallucinationDetector, detect_hallucinations
from .validation_report import ValidationReport, generate_validation_report

__all__ = [
    "ClaimExtractor",
    "extract_claims",
    "EvidenceMatcher",
    "match_claims_to_evidence",
    "CoverageCalculator",
    "calculate_coverage",
    "HallucinationDetector",
    "detect_hallucinations",
    "ValidationReport",
    "generate_validation_report",
]