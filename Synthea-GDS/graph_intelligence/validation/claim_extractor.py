"""
Graph Intelligence Platform — Claim Extractor

Extracts structured factual claims from natural language answers.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ClaimType(Enum):
    """Types of claims that can be extracted."""
    METRIC_VALUE = "metric_value"           # "Entity X has betweenness_centrality = 0.002"
    COMMUNITY_MEMBERSHIP = "community"      # "Entity X belongs to Leiden community 3"
    STRUCTURAL_PROPERTY = "structural"      # "Entity X is an articulation point"
    RANKING = "ranking"                     # "Entity X is top-5 by PageRank"
    COMPARISON = "comparison"               # "Entity X has higher betweenness than Y"
    COUNT = "count"                         # "There are 9 Leiden communities"
    EXISTENCE = "existence"                 # "Entity X exists in the graph"
    GENERAL = "general"                     # Other factual claims


@dataclass
class Claim:
    """A single extracted claim from an answer."""
    text: str                          # Original text span
    claim_type: ClaimType              # Type of claim
    entities: List[str]                # Entity IDs mentioned
    metrics: List[str]                 # Metric names mentioned
    values: List[Any]                  # Claimed values
    comparison_ops: List[str]          # Comparison operators (>, <, =, top-N)
    confidence: float = 1.0            # Extraction confidence
    source_sentence: str = ""          # Full sentence containing claim


class ClaimExtractor:
    """Extracts structured claims from natural language answers."""

    # Patterns for different claim types
    METRIC_PATTERN = re.compile(
        r'(?:betweenness_centrality|closeness_centrality|degree_centrality|'
        r'eigenvector_centrality|harmonic_centrality|pagerank|article_rank|'
        r'hits_hub|hits_authority|k_core|is_articulation_point|is_bridge_endpoint)'
        r'\s*[=:]\s*([\d.]+|True|False)',
        re.IGNORECASE
    )

    COMMUNITY_PATTERN = re.compile(
        r'(?:leiden|louvain|label_propagation|kmeans|k1_coloring|sllpa)'
        r'\s*(?:community|cluster)?\s*(?:is|=|:)?\s*(\d+|seed_\d+)',
        re.IGNORECASE
    )

    TOP_N_PATTERN = re.compile(
        r'top[- ]?(\d+)\s+(?:by|for|in)\s+([\w_]+)',
        re.IGNORECASE
    )

    COUNT_PATTERN = re.compile(
        r'(\d+)\s+(?:leiden|louvain|label_propagation|kmeans|k1_coloring)\s+communities',
        re.IGNORECASE
    )

    COMPARISON_PATTERN = re.compile(
        r'(\w+)\s+(?:has|have)\s+(?:higher|lower|greater|less)\s+([\w_]+)\s+than\s+(\w+)',
        re.IGNORECASE
    )

    STRUCTURAL_PATTERN = re.compile(
        r'(?:is|was)\s+(?:an?\s+)?(articulation point|bridge|bridge endpoint)',
        re.IGNORECASE
    )

    def __init__(self):
        self.known_metrics = {
            'degree_centrality', 'betweenness_centrality', 'closeness_centrality',
            'eigenvector_centrality', 'harmonic_centrality', 'pagerank', 'article_rank',
            'hits_hub', 'hits_authority', 'k_core', 'is_articulation_point', 'is_bridge_endpoint'
        }
        self.known_community_algos = {
            'leiden', 'louvain', 'label_propagation', 'kmeans', 'k1_coloring', 'sllpa'
        }

    def extract(self, answer: str) -> List[Claim]:
        """Extract all claims from an answer by parsing entity blocks."""
        claims = []

        # Only extract from the "Answer" section, not "Evidence" or "Limitations"
        answer_section = answer
        if "## Evidence" in answer:
            answer_section = answer.split("## Evidence")[0]
        if "## Limitations" in answer_section:
            answer_section = answer_section.split("## Limitations")[0]

        # Parse entity blocks: **Entity Name** followed by bullet points
        entity_blocks = self._parse_entity_blocks(answer_section)

        for entity_name, entity_lines in entity_blocks:
            # Extract claims from this entity's lines
            for line in entity_lines:
                claims.extend(self._extract_claims_from_line(line, entity_name))

        # Also extract general claims (not tied to specific entity)
        general_section = self._get_general_section(answer_section, entity_blocks)
        if general_section:
            for line in general_section.split('\n'):
                line = line.strip()
                if line:
                    claims.extend(self._extract_claims_from_line(line, None))

        return claims

    def _parse_entity_blocks(self, answer_section: str) -> List[tuple]:
        """Parse the answer into entity blocks: (entity_name, [lines])"""
        blocks = []
        lines = answer_section.split('\n')
        current_entity = None
        current_lines = []

        for line in lines:
            stripped = line.strip()

            # Check for bold entity header
            if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
                # Save previous block
                if current_entity and current_lines:
                    blocks.append((current_entity, current_lines))

                # Start new block
                current_entity = stripped[2:-2].strip()
                current_lines = []
            elif current_entity and stripped.startswith('- '):
                # Metric line belonging to current entity
                current_lines.append(stripped[2:].strip())  # Remove '- ' prefix
            elif current_entity and stripped and not stripped.startswith('###'):
                # Other content for this entity
                current_lines.append(stripped)

        # Don't forget last block
        if current_entity and current_lines:
            blocks.append((current_entity, current_lines))

        return blocks

    def _get_general_section(self, answer_section: str, entity_blocks: List[tuple]) -> str:
        """Get text that's not part of any entity block."""
        # For now, just return empty - we only care about entity-specific claims
        return ""

    def _extract_claims_from_line(self, line: str, entity_name: Optional[str]) -> List[Claim]:
        """Extract claims from a single line, associating with entity_name."""
        claims = []

        # Extract metric value claims
        for match in self.METRIC_PATTERN.finditer(line):
            full_match = match.group(0)
            metric_name = full_match.split('=')[0].split(':')[0].strip().lower()
            value_str = match.group(1)

            entities = [entity_name] if entity_name else self._find_entities_in_line(line)

            try:
                value = float(value_str) if value_str.replace('.', '').replace('-', '').isdigit() else value_str
            except ValueError:
                value = value_str

            claims.append(Claim(
                text=full_match,
                claim_type=ClaimType.METRIC_VALUE,
                entities=entities,
                metrics=[metric_name],
                values=[value],
                comparison_ops=['='],
                confidence=0.9,
                source_sentence=line
            ))

        # Extract community membership claims
        for match in self.COMMUNITY_PATTERN.finditer(line):
            algo_part = match.group(0).split()[0].lower()
            comm_id = match.group(1)

            entities = [entity_name] if entity_name else self._find_entities_in_line(line)

            claims.append(Claim(
                text=match.group(0),
                claim_type=ClaimType.COMMUNITY_MEMBERSHIP,
                entities=entities,
                metrics=[f"{algo_part}_community"],
                values=[comm_id],
                comparison_ops=['='],
                confidence=0.85,
                source_sentence=line
            ))

        return claims

    def _find_entities_in_line(self, line: str) -> List[str]:
        """Find entity references in a line."""
        entities = []

        # Look for Neo4j element IDs
        id_matches = re.findall(r'4:[a-f0-9\-]+:\d+', line)
        entities.extend(id_matches)

        # Look for named entities (capitalized phrases)
        name_matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', line)
        entities.extend(name_matches)

        return entities


def extract_claims(answer: str) -> List[Claim]:
    """Convenience function to extract claims from an answer."""
    extractor = ClaimExtractor()
    return extractor.extract(answer)