# Synthea quick insights

## Dataset snapshot
- Nodes: 14,753
- Relationships: 92,342
- Project includes 55 generated graph outputs across centrality, community, DAG, path, similarity, and embedding families.

## Key findings
- Graph size: 14753 nodes and 92342 relationships.
- Most populous node label: Encounter (13115 nodes).
- Highest PageRank entity: wellness (EncounterType) with score 0.035452.
- Highest degree-centrality entity: wellness (EncounterType) with score 0.441025.
- Highest betweenness entity: wellness (EncounterType) with score 0.213651.
- Community detection found 159278 maximum communities across algorithms; Louvain yields 14 communities with modularity 0.498.
- Relationship backbone is dominated by healthcare flow/encounter-type edges, not purely patient records; this suggests the graph is a care-network rather than a person-only network.
- The most central entities are encounter types and payers, indicating care pathways are organized around encounter workflow and reimbursement structures.

## Visual outputs
- label_distribution.png
- relationship_distribution.png
- centrality_top_scores.png
- community_summary.png

## Interpretation
The graph is structurally centered on workflow nodes and payer/encounter entities instead of only patient records. This is consistent with a healthcare network where care orchestration, payer relationships, and encounter types drive the connectivity pattern.
