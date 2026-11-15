from neo4j import GraphDatabase
import json

URI = "bolt://100.23.76.198:7687"
USERNAME = "neo4j"
PASSWORD = "Prajnadb"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def run_query(tx, query):
    result = tx.run(query)
    return [record for record in result]

with driver.session() as session:
    print("=== DIAGNOSED_WITH vs HAS_CONDITION ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(c:Condition)
        WITH type(r) AS rel, collect(DISTINCT c.DESCRIPTION) AS descriptions, count(*) AS cnt
        RETURN rel, descriptions[0..5] AS sample, cnt
        ORDER BY cnt DESC
    """)
    for r in result:
        print(f"  {r['rel']}: {r['cnt']} relationships")
        print(f"    Sample: {r['sample']}")
    
    print("\n=== PATIENTS WITH DIAGNOSED_WITH BUT NOT HAS_CONDITION ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r:DIAGNOSED_WITH]->(c:Condition)
        WHERE NOT (p)-[:HAS_CONDITION]->(c)
        RETURN count(DISTINCT p) AS cnt
    """)
    for r in result:
        print(f"  Count: {r['cnt']}")
    
    print("\n=== PATIENTS WITH HAS_CONDITION BUT NOT DIAGNOSED_WITH ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r:HAS_CONDITION]->(c:Condition)
        WHERE NOT (p)-[:DIAGNOSED_WITH]->(c)
        RETURN count(DISTINCT p) AS cnt
    """)
    for r in result:
        print(f"  Count: {r['cnt']}")
    
    print("\n=== CONDITIONS ONLY IN DIAGNOSED_WITH ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[:DIAGNOSED_WITH]->(c:Condition)
        WHERE NOT (p)-[:HAS_CONDITION]->(c)
        RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 20
    """)
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== CONDITIONS ONLY IN HAS_CONDITION ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[:HAS_CONDITION]->(c:Condition)
        WHERE NOT (p)-[:DIAGNOSED_WITH]->(c)
        RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 20
    """)
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== HEART ATTACK / MI CONDITIONS (FULL SEARCH) ===")
    result = session.execute_read(run_query, """
        MATCH (c:Condition)
        WHERE c.DESCRIPTION CONTAINS 'heart' OR c.DESCRIPTION CONTAINS 'myocardial' OR c.DESCRIPTION CONTAINS 'coronary' OR c.DESCRIPTION CONTAINS 'infarction'
        RETURN c.CODE, c.DESCRIPTION
        ORDER BY c.DESCRIPTION
    """)
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']}")
    
    print("\n=== ALL CONDITIONS WITH COUNTS ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(c:Condition)
        RETURN c.CODE, c.DESCRIPTION, count(DISTINCT p) AS patient_count
        ORDER BY patient_count DESC
    """)
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['patient_count']}")
    
    print("\n=== PROCEDURE PROPERTIES SAMPLE ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[:UNDERWENT]->(pr:Procedure)
        RETURN pr.CODE, pr.DESCRIPTION, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 20
    """)
    for r in result:
        print(f"  {r['pr.CODE']} | {r['pr.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== MEDICATION PROPERTIES SAMPLE ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[:PRESCRIBED]->(m:Medication)
        RETURN m.CODE, m.DESCRIPTION, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 20
    """)
    for r in result:
        print(f"  {r['m.CODE']} | {r['m.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== ENCOUNTER CLASSES ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)
        RETURN e.ENCOUNTERCLASS, count(*) AS cnt
        ORDER BY cnt DESC
    """)
    for r in result:
        print(f"  {r['e.ENCOUNTERCLASS']}: {r['cnt']}")
    
    print("\n=== TEMPORAL SPAN OF ENCOUNTERS ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)
        WITH p, min(e.START) AS first_enc, max(e.START) AS last_enc
        RETURN min(first_enc) AS global_min, max(last_enc) AS global_max
    """)
    for r in result:
        print(f"  Global min: {r['global_min']}")
        print(f"  Global max: {r['global_max']}")
    
    print("\n=== TEMPORAL SPAN OF CONDITIONS ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(c:Condition)
        RETURN min(r.START) AS global_min, max(r.START) AS global_max
    """)
    for r in result:
        print(f"  Global min: {r['global_min']}")
        print(f"  Global max: {r['global_max']}")
    
    print("\n=== CONDITIONS WITH START DATES ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(c:Condition)
        WHERE r.START IS NOT NULL
        RETURN count(*) AS cnt
    """)
    for r in result:
        print(f"  Conditions with START: {r['cnt']}")
    
    print("\n=== CONDITIONS WITHOUT START DATES ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(c:Condition)
        WHERE r.START IS NULL
        RETURN count(*) AS cnt
    """)
    for r in result:
        print(f"  Conditions without START: {r['cnt']}")
    
    print("\n=== MEDICATIONS WITH START DATES ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(m:Medication)
        WHERE r.START IS NOT NULL
        RETURN count(*) AS cnt
    """)
    for r in result:
        print(f"  Medications with START: {r['cnt']}")
    
    print("\n=== ALLERGY DATA ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r:ALLERGIC_TO]->(a:Allergy)
        RETURN a.CODE, a.DESCRIPTION, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 10
    """)
    for r in result:
        print(f"  {r['a.CODE']} | {r['a.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== IMMUNIZATION DATA ===")
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(i:Immunization)
        RETURN i.CODE, i.DESCRIPTION, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 10
    """)
    for r in result:
        print(f"  {r['i.CODE']} | {r['i.DESCRIPTION']} | {r['cnt']}")

driver.close()
print("\nDone.")
