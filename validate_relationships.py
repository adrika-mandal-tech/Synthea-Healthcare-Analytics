from neo4j import GraphDatabase
import json
import pandas as pd

URI = "bolt://100.23.76.198:7687"
USERNAME = "neo4j"
PASSWORD = "Prajnadb"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def run_query(tx, query):
    result = tx.run(query)
    return [record for record in result]

with driver.session() as session:
    print("=== DIAGNOSED_WITH vs HAS_CONDITION DETAILED ANALYSIS ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(c:Condition)
        RETURN elementId(p) AS patient_id, c.CODE AS condition_code, type(r) AS rel_type, count(*) AS cnt
        ORDER BY patient_id, condition_code, rel_type
    """)
    
    df = pd.DataFrame([dict(r) for r in result])
    print(f"Total rows: {len(df)}")
    
    # Check for duplicate patient-condition pairs
    dupes = df.groupby(['patient_id', 'condition_code']).size().reset_index(name='count')
    multi_rel = dupes[dupes['count'] > 1]
    print(f"Patient-condition pairs with multiple relationships: {len(multi_rel)}")
    
    if len(multi_rel) > 0:
        print("Sample duplicates:")
        print(multi_rel.head(20))
    
    # Pivot to see which patients have which relationship types
    pivot = df.pivot_table(index=['patient_id', 'condition_code'], 
                           columns='rel_type', 
                           values='cnt', 
                           aggfunc='sum',
                           fill_value=0)
    print(f"\nPivot shape: {pivot.shape}")
    print(f"Patients with HAS_CONDITION only: {(pivot['HAS_CONDITION'] > 0).sum()}")
    print(f"Patients with DIAGNOSED_WITH only: {(pivot['DIAGNOSED_WITH'] > 0).sum()}")
    print(f"Patients with both: {((pivot['HAS_CONDITION'] > 0) & (pivot['DIAGNOSED_WITH'] > 0)).sum()}")
    
    print("\n=== WHY EXPORT HAS 4568 ROWS ===")
    print("If both relationship types exist for same patient-condition, export might deduplicate")
    print("Or DIAGNOSED_WITH might go through a different path")
    
    # Check if any DIAGNOSED_WITH exists in the graph for conditions
    result2 = session.execute_read(run_query, """
        MATCH (p:Patient)-[r:DIAGNOSED_WITH]->(c:Condition)
        RETURN elementId(p) AS patient_id, c.CODE AS condition_code, c.DESCRIPTION AS condition_desc
        LIMIT 20
    """)
    df2 = pd.DataFrame([dict(r) for r in result2])
    print(f"\nSample DIAGNOSED_WITH relationships:")
    print(df2.head(20))
    
    print("\n=== ARE CONDITIONS UNIQUE ACROSS PATIENTS? ===")
    # Check if same condition code has different descriptions
    result3 = session.execute_read(run_query, """
        MATCH (c:Condition)
        RETURN c.CODE AS code, c.DESCRIPTION AS desc, count(*) AS cnt
        ORDER BY code
    """)
    df3 = pd.DataFrame([dict(r) for r in result3])
    print(f"Unique codes: {len(df3)}")
    print(f"Conditions with multiple descriptions: {(df3['cnt'] > 1).sum()}")

driver.close()
