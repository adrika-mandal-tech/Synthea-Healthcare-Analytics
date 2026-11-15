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
    print("=== ALL LABELS ===")
    result = session.execute_read(run_query, "MATCH (n) RETURN labels(n) AS labels, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['labels']}: {r['cnt']}")
    
    print("\n=== ALL RELATIONSHIP TYPES ===")
    result = session.execute_read(run_query, "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['rel']}: {r['cnt']}")
    
    print("\n=== PROCEDURE NODES ===")
    result = session.execute_read(run_query, "MATCH (n:Procedure) RETURN count(*) AS cnt")
    for r in result:
        print(f"  Procedure nodes: {r['cnt']}")
    
    print("\n=== OBSERVATION NODES ===")
    result = session.execute_read(run_query, "MATCH (n:Observation) RETURN count(*) AS cnt")
    for r in result:
        print(f"  Observation nodes: {r['cnt']}")
    
    print("\n=== PATIENT -> PROCEDURE RELATIONSHIPS ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(pr:Procedure) RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['rel']}: {r['cnt']}")
    
    print("\n=== PATIENT -> OBSERVATION RELATIONSHIPS ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(o:Observation) RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['rel']}: {r['cnt']}")
    
    print("\n=== ALLERGY NODES ===")
    result = session.execute_read(run_query, "MATCH (n:Allergy) RETURN count(*) AS cnt")
    for r in result:
        print(f"  Allergy nodes: {r['cnt']}")
    
    print("\n=== IMMUNIZATION NODES ===")
    result = session.execute_read(run_query, "MATCH (n:Immunization) RETURN count(*) AS cnt")
    for r in result:
        print(f"  Immunization nodes: {r['cnt']}")
    
    print("\n=== SAMPLE PROCEDURE PROPERTIES ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(pr:Procedure) RETURN pr LIMIT 3")
    for r in result:
        node = r['pr']
        print(f"  {dict(node)}")
    
    print("\n=== SAMPLE OBSERVATION PROPERTIES ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(o:Observation) RETURN o LIMIT 3")
    for r in result:
        node = r['o']
        print(f"  {dict(node)}")
    
    print("\n=== DIAGNOSED_WITH vs HAS_CONDITION ===")
    result = session.execute_read(run_query, "MATCH ()-[r]->(:Condition) RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['rel']}: {r['cnt']}")
    
    print("\n=== OBESITY DEFINITION ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(c:Condition) WHERE c.DESCRIPTION CONTAINS 'obesity' OR c.DESCRIPTION CONTAINS 'Body mass index' RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== DIABETES DEFINITION ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(c:Condition) WHERE c.DESCRIPTION CONTAINS 'diabetes' OR c.DESCRIPTION CONTAINS 'Diabetes' RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== HYPERTENSION DEFINITION ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(c:Condition) WHERE c.DESCRIPTION CONTAINS 'Hypertension' OR c.DESCRIPTION CONTAINS 'blood pressure' RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== HEART ATTACK DEFINITION ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(c:Condition) WHERE c.DESCRIPTION CONTAINS 'heart attack' OR c.DESCRIPTION CONTAINS 'Myocardial infarction' OR c.DESCRIPTION CONTAINS 'acute myocardial' RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== ARDS DEFINITION ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(c:Condition) WHERE c.DESCRIPTION CONTAINS 'ARDS' OR c.DESCRIPTION CONTAINS 'Acute respiratory distress' RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")
    
    print("\n=== COVID DEFINITION ===")
    result = session.execute_read(run_query, "MATCH (p:Patient)-[r]->(c:Condition) WHERE c.DESCRIPTION CONTAINS 'COVID' OR c.DESCRIPTION CONTAINS 'SARS-CoV-2' RETURN c.CODE, c.DESCRIPTION, count(*) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['c.CODE']} | {r['c.DESCRIPTION']} | {r['cnt']}")

driver.close()
print("\nDone.")
