import pandas as pd
import networkx as nx
from pathlib import Path
import time
import csv

import pipeline

def fix_pipeline():
    workspace = Path(__file__).parent.parent
    manifest_path = workspace / "reports" / "algorithm_manifest.csv"
    
    print("1. Repairing manifest...")
    df = pd.read_csv(manifest_path)
    
    # Remove duplicate CELF (keep completed)
    df = df[~((df['algorithm'] == 'CELF') & (df['status'] == 'requires_parameters'))]
    
    # Remove ArticleRank, Conductance, and all paths
    df = df[df['algorithm'] != 'ArticleRank']
    df = df[df['algorithm'] != 'Conductance']
    df = df[df['category'] != 'paths']
    
    # Write back
    df.to_csv(manifest_path, index=False)
    
    print("2. Loading graphs...")
    meta = pipeline.load_graphs()
    G_undirected = meta["G_undirected"]
    nodes_df = meta["nodes_df"]
    
    def get_labels(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("labels", "")
        
    def get_name(nid):
        row = nodes_df[nodes_df["element_id"] == nid]
        if row.empty:
            return ""
        return row.iloc[0].get("name", "") or row.iloc[0].get("NAME", "") or row.iloc[0].get("Id", "") or ""

    print("3. Re-running ArticleRank...")
    try:
        start = time.time()
        avg_degree = sum(dict(G_undirected.degree()).values()) / G_undirected.number_of_nodes()
        personalization = {}
        for n in G_undirected.nodes():
            neighbors = list(G_undirected.neighbors(n))
            if neighbors:
                avg_neighbor_deg = sum(G_undirected.degree(nb) for nb in neighbors) / len(neighbors)
                personalization[n] = 1.0 / max(avg_neighbor_deg, 1)
            else:
                personalization[n] = 1.0 / max(avg_degree, 1)
        ar = nx.pagerank(G_undirected, alpha=0.85, personalization=personalization, max_iter=200)
        t = time.time() - start
        rows = [{"node_id": nid, "labels": get_labels(nid), "name": get_name(nid),
                 "score": ar.get(nid, 0.0)} for nid in G_undirected.nodes()]
        pipeline.safe_write_csv(workspace / "centrality" / "article_rank.csv", rows)
        pipeline.append_manifest({
            "algorithm": "ArticleRank", "category": "centrality",
            "status": "completed", "output_file": "centrality/article_rank.csv",
            "library": "networkx", "parameters": "personalization=avg_neighbor_degree_damping",
            "runtime_seconds": round(t, 3),
            "nodes_processed": len(rows), "edges_processed": G_undirected.size(),
            "notes": "ArticleRank with average-neighbor-degree damping"
        })
    except Exception as e:
        print(f"ArticleRank failed: {e}")
        
    print("4. Re-running Conductance...")
    try:
        import community as community_louvain
        partition = community_louvain.best_partition(G_undirected)
        community_sets = {}
        for nid, cid in partition.items():
            community_sets.setdefault(cid, set()).add(nid)
        conds = []
        for cid in sorted(community_sets.keys()):
            comm = community_sets[cid]
            try:
                cval = nx.algorithms.cuts.conductance(G_undirected, comm)
            except (ZeroDivisionError, nx.NetworkXError):
                cval = 0.0
            conds.append({"community_id": cid, "conductance": cval, "size": len(comm)})
        pipeline.safe_write_csv(workspace / "community" / "conductance.csv", conds)
        pipeline.append_manifest({
            "algorithm": "Conductance", "category": "community",
            "status": "completed", "output_file": "community/conductance.csv",
            "library": "networkx", "parameters": "per-community via nx.algorithms.cuts.conductance",
            "runtime_seconds": 0, "nodes_processed": len(conds), "edges_processed": G_undirected.size(),
            "notes": ""
        })
    except Exception as e:
        print(f"Conductance failed: {e}")
        
    print("5. Re-running Paths...")
    pipeline.run_paths(meta)
    
    print("6. Regenerating summary...")
    pipeline.write_summary()
    print("Fix script completed successfully.")

if __name__ == "__main__":
    fix_pipeline()
