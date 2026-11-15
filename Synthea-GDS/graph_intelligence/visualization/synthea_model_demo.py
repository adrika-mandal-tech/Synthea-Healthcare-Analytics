from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "visuals" / "meaningful_model"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def savefig(fig, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT_DIR / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_node_distribution(nodes_df: pd.DataFrame) -> None:
    if nodes_df.empty:
        return
    counts = nodes_df["labels"].fillna("").astype(str).value_counts().head(8)
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x=counts.index, y=counts.values, palette="viridis", ax=ax)
    ax.set_title("Synthea graph: node type distribution")
    ax.set_xlabel("Node label")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=25)
    savefig(fig, "node_type_distribution.png")


def plot_relationship_distribution(rels_df: pd.DataFrame) -> None:
    if rels_df.empty:
        return
    counts = rels_df["type"].fillna("").astype(str).value_counts().head(10)
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(x=counts.values, y=counts.index, palette="magma", orient="h", ax=ax)
    ax.set_title("Synthea graph: relationship type distribution")
    ax.set_xlabel("Count")
    ax.set_ylabel("Relationship type")
    savefig(fig, "relationship_type_distribution.png")


def plot_community_summary() -> None:
    summary = load_csv(ROOT / "community" / "community_detection_summary.csv")
    if summary.empty:
        return
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(data=summary, x="algorithm", y="communities", palette="Set2", ax=ax)
    ax.set_title("Community detection: communities per algorithm")
    ax.set_xlabel("Algorithm")
    ax.set_ylabel("Community count")
    ax.tick_params(axis="x", rotation=25)
    savefig(fig, "community_algorithm_summary.png")


def plot_centrality_summary() -> None:
    metrics = [
        "pagerank",
        "degree_centrality",
        "betweenness_centrality",
        "eigenvector_centrality",
    ]
    frames = []
    for metric in metrics:
        df = load_csv(ROOT / "centrality" / f"{metric}.csv")
        if df.empty:
            continue
        top = df.sort_values("score", ascending=False).head(5).copy()
        top["metric"] = metric
        frames.append(top[["metric", "name", "score"]])
    if not frames:
        return

    combined = pd.concat(frames, ignore_index=True)
    fig, ax = plt.subplots(figsize=(12, 7))

    positions = []
    labels = []
    offset = 0
    for metric in metrics:
        subset = combined[combined["metric"] == metric].head(3).reset_index(drop=True)
        if subset.empty:
            continue
        x_values = np.arange(len(subset)) + offset
        positions.extend(x_values)
        ax.bar(x_values, subset["score"].values, alpha=0.8, label=metric)
        for idx, row in subset.iterrows():
            labels.append(f"{metric[:4]}: {row['name'][:18]}")
        offset += len(subset) + 1

    if positions:
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, rotation=35, ha="right")

    ax.set_title("Top healthcare graph nodes by centrality")
    ax.set_ylabel("Centrality score")
    ax.set_xlabel("Metric and node")
    ax.legend(loc="upper right")
    savefig(fig, "centrality_top_nodes.png")


def plot_conceptual_network() -> None:
    G = nx.DiGraph()
    nodes = {
        "Patient": (0, 0, "#4C78A8"),
        "Encounter": (2, 0, "#54A24B"),
        "Provider": (4, 1, "#F58518"),
        "Condition": (4, -1, "#E45756"),
        "Medication": (6, 0, "#B279A2"),
        "Payer": (2, 2, "#72B7B2"),
    }
    for node, (x, y, color) in nodes.items():
        G.add_node(node, x=x, y=y, color=color)

    edges = [
        ("Patient", "Encounter", "visits"),
        ("Encounter", "Provider", "performed_at"),
        ("Encounter", "Condition", "diagnosed_with"),
        ("Encounter", "Medication", "prescribed"),
        ("Encounter", "Payer", "covered_by"),
    ]
    for src, dst, rel in edges:
        G.add_edge(src, dst, relationship=rel)

    fig, ax = plt.subplots(figsize=(9, 6))
    pos = {node: (x, y) for node, (x, y, _) in nodes.items()}
    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=[data["color"] for _, data in G.nodes(data=True)],
        node_size=1800,
        edgecolors="black",
        linewidths=1,
        ax=ax,
    )
    nx.draw_networkx_edges(G, pos, arrowstyle="-|>", arrows=True, width=2, alpha=0.8, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold", ax=ax)
    ax.set_title("Conceptual Synthea healthcare knowledge graph")
    ax.axis("off")
    savefig(fig, "conceptual_healthcare_knowledge_graph.png")


def build_summary_report(nodes_df: pd.DataFrame, rels_df: pd.DataFrame) -> None:
    label_counts = nodes_df["labels"].fillna("").astype(str).value_counts().head(6)
    rel_counts = rels_df["type"].fillna("").astype(str).value_counts().head(8)
    summary_lines = [
        "# Synthea healthcare knowledge graph summary",
        "",
        f"- Nodes: {len(nodes_df)}",
        f"- Relationships: {len(rels_df)}",
        "",
        "## Most common node types",
    ]
    for label, count in label_counts.items():
        summary_lines.append(f"- {label}: {count} nodes")

    summary_lines.extend(["", "## Most common relationship types"])
    for rel, count in rel_counts.items():
        summary_lines.append(f"- {rel}: {count} edges")

    summary_text = "\n".join(summary_lines) + "\n"
    (ROOT / "reports" / "synthea_graph_summary.txt").write_text(summary_text, encoding="utf-8")


def main() -> None:
    nodes_df = load_csv(ROOT / "data" / "nodes.csv")
    rels_df = load_csv(ROOT / "data" / "relationships.csv")

    if nodes_df.empty or rels_df.empty:
        raise FileNotFoundError("Expected data/nodes.csv and data/relationships.csv to exist in the project root.")

    plot_node_distribution(nodes_df)
    plot_relationship_distribution(rels_df)
    plot_community_summary()
    plot_centrality_summary()
    plot_conceptual_network()
    build_summary_report(nodes_df, rels_df)

    print(f"Saved meaningful Synthea graph visuals to: {OUT_DIR}")
    print("Files generated:")
    for image in sorted(OUT_DIR.glob("*.png")):
        print(f" - {image.name}")
    print("\nSummary report: reports/synthea_graph_summary.txt")


if __name__ == "__main__":
    main()
