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
    print("=== DIAGNOSED_WITH STRUCTURE ===")
    result = session.execute_read(run_query, """
        MATCH (a)-[r:DIAGNOSED_WITH]->(b:Condition)
        RETURN labels(a) AS source_labels, labels(b) AS target_labels, count(*) AS cnt
        ORDER BY cnt DESC
    """)
    for r in result:
        print(f"  {r['source_labels']} -> Condition: {r['cnt']}")
    
    print("\n=== SAMPLE DIAGNOSED_WITH PATHS ===")
    result = session.execute_read(run_query, """
        MATCH (a)-[r:DIAGNOSED_WITH]->(c:Condition)
        RETURN labels(a) AS source_labels, elementId(a) AS source_id, 
               c.CODE AS cond_code, c.DESCRIPTION AS cond_desc
        LIMIT 10
    """)
    for r in result:
        print(f"  {r['source_labels']} ({r['source_id']}) -> {r['cond_code']} | {r['cond_desc']}")
    
    print("\n=== PATIENT-CONDITION VIA DIAGNOSED_WITH ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r:DIAGNOSED_WITH]->(c:Condition)
        RETURN elementId(p) AS patient_id, c.CODE AS condition_code, c.DESCRIPTION AS condition_desc
        LIMIT 20
    """)
    for r in result:
        print(f"  {r['patient_id']} -> {r['condition_code']} | {r['condition_desc']}")
    
    print("\n=== ALL PATIENT-CONDITION RELATIONSHIPS (BOTH TYPES) ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(c:Condition)
        RETURN type(r) AS rel_type, count(*) AS cnt
    """)
    for r in result:
        print(f"  {r['rel_type']}: {r['cnt']}")
    
    print("\n=== PATIENTS WITH DIAGNOSED_WITH TO CONDITION ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r:DIAGNOSED_WITH]->(c:Condition)
        RETURN count(DISTINCT p) AS cnt
    """)
    for r in result:
        print(f"  Count: {r['cnt']}")

driver.close()
