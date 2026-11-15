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
    print("=== ENCOUNTER-CONDITION RELATIONSHIPS ===")
    result = session.execute_read(run_query, """
        MATCH (e:Encounter)-[r]->(c:Condition)
        RETURN type(r) AS rel_type, count(*) AS cnt
        ORDER BY cnt DESC
    """)
    for r in result:
        print(f"  {r['rel_type']}: {r['cnt']}")
    
    print("\n=== SAMPLE ENCOUNTER -> CONDITION ===")
    result = session.execute_read(run_query, """
        MATCH (e:Encounter)-[r:DIAGNOSED_WITH]->(c:Condition)
        RETURN elementId(e) AS enc_id, e.START AS enc_start, c.CODE AS cond_code, c.DESCRIPTION AS cond_desc
        LIMIT 10
    """)
    for r in result:
        print(f"  Encounter {r['enc_id']} ({r['enc_start']}) -> {r['cond_code']} | {r['cond_desc']}")
    
    print("\n=== ENCOUNTER -> CONDITION VIA HAS_REASON ===")
    result = session.execute_read(run_query, """
        MATCH (e:Encounter)-[r:HAS_REASON]->(c:Condition)
        RETURN elementId(e) AS enc_id, e.START AS enc_start, c.CODE AS cond_code, c.DESCRIPTION AS cond_desc
        LIMIT 10
    """)
    for r in result:
        print(f"  Encounter {r['enc_id']} ({r['enc_start']}) -> {r['cond_code']} | {r['cond_desc']}")
    
    print("\n=== PATIENT -> ENCOUNTER -> CONDITION (FULL PATH) ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[r:DIAGNOSED_WITH]->(c:Condition)
        RETURN elementId(p) AS patient_id, elementId(e) AS enc_id, e.START AS enc_start, 
               c.CODE AS cond_code, c.DESCRIPTION AS cond_desc
        ORDER BY p, e.START
        LIMIT 20
    """)
    for r in result:
        print(f"  Patient {r['patient_id']} -> Encounter {r['enc_id']} ({r['enc_start']}) -> {r['cond_code']} | {r['cond_desc']}")
    
    print("\n=== HOW MANY CONDITIONS ARE ATTACHED TO ENCOUNTERS? ===")
    result = session.execute_read(run_query, """
        MATCH (e:Encounter)-[r:DIAGNOSED_WITH]->(c:Condition)
        RETURN count(DISTINCT c) AS unique_conditions, count(*) AS total_rels
    """)
    for r in result:
        print(f"  Unique conditions: {r['unique_conditions']}, Total relationships: {r['total_rels']}")
    
    print("\n=== CONDITIONS ONLY IN PATIENT-CONDITION, NOT IN ENCOUNTER-CONDITION ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[:HAS_CONDITION]->(c:Condition)
        WHERE NOT EXISTS {
            MATCH (e:Encounter)-[:DIAGNOSED_WITH]->(c)
        }
        RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 20
    """)
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== CONDITIONS ONLY IN ENCOUNTER-CONDITION, NOT IN PATIENT-CONDITION ===")
    result = session.execute_read(run_query, """
        MATCH (e:Encounter)-[:DIAGNOSED_WITH]->(c:Condition)
        WHERE NOT EXISTS {
            MATCH (p:Patient)-[:HAS_CONDITION]->(c)
        }
        RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 20
    """)
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")

driver.close()
