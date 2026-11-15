from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd


class GraphVisualizer:
    """Lightweight visualization helpers for graph inventories and summaries."""

    def __init__(self, nodes_path: str | Path = "data/nodes.csv", rels_path: str | Path = "data/relationships.csv"):
        self.nodes_path = Path(nodes_path)
        self.rels_path = Path(rels_path)

    def load_nodes(self) -> pd.DataFrame:
        if not self.nodes_path.exists():
            return pd.DataFrame()
        return pd.read_csv(self.nodes_path, low_memory=False)

    def load_relationships(self) -> pd.DataFrame:
        if not self.rels_path.exists():
            return pd.DataFrame()
        return pd.read_csv(self.rels_path, low_memory=False)

    def label_distribution(self) -> List[Dict[str, Any]]:
        df = self.load_nodes()
        if df.empty:
            return []
        counts = Counter(df.get("labels", "").fillna("").astype(str))
        return [{"label": k, "count": v} for k, v in counts.most_common(12)]

    def relationship_distribution(self) -> List[Dict[str, Any]]:
        df = self.load_relationships()
        if df.empty:
            return []
        counts = Counter(df.get("type", "").fillna("").astype(str))
        return [{"relationship": k, "count": v} for k, v in counts.most_common(12)]

    def community_summary(self, community_summary_path: str | Path = "community/community_detection_summary.csv") -> List[Dict[str, Any]]:
        path = Path(community_summary_path)
        if not path.exists():
            return []
        df = pd.read_csv(path)
        return df.to_dict(orient="records")

    def overview_cards(self) -> Dict[str, Any]:
        nodes = self.load_nodes()
        rels = self.load_relationships()

        return {
            "node_count": int(len(nodes)) if not nodes.empty else 0,
            "edge_count": int(len(rels)) if not rels.empty else 0,
            "unique_labels": int(nodes.get("labels", pd.Series(dtype=str)).nunique()) if not nodes.empty else 0,
            "unique_relationship_types": int(rels.get("type", pd.Series(dtype=str)).nunique()) if not rels.empty else 0,
        }


def summarize_label_distribution(nodes_df: pd.DataFrame) -> List[Dict[str, Any]]:
    if nodes_df.empty:
        return []
    counts = Counter(nodes_df.get("labels", "").fillna("").astype(str))
    return [{"label": k, "count": v} for k, v in counts.most_common(12)]


def summarize_relationship_distribution(rels_df: pd.DataFrame) -> List[Dict[str, Any]]:
    if rels_df.empty:
        return []
    counts = Counter(rels_df.get("type", "").fillna("").astype(str))
    return [{"relationship": k, "count": v} for k, v in counts.most_common(12)]


def summarize_community_algorithms(summary_path: str | Path) -> List[Dict[str, Any]]:
    path = Path(summary_path)
    if not path.exists():
        return []
    return pd.read_csv(path).to_dict(orient="records")
