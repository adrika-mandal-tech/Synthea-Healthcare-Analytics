from neo4j import GraphDatabase
import csv
import os
import json

# ============================================================
# NEO4J CONNECTION
# ============================================================

URI = "bolt://100.23.76.198:7687"
USERNAME = "neo4j"

# CHANGE THIS to your actual Neo4j password
PASSWORD = "Prajnadb"

# =========================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = os.path.expanduser("~/synthea_export")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# CONNECT TO NEO4J
# ============================================================

print("Connecting to Neo4j...")

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

driver.verify_connectivity()

print("Connected to Neo4j successfully!")
print()


# ============================================================
# 1. EXPORT ALL NODES
# ============================================================

def export_nodes(tx):

    query = """
    MATCH (n)
    RETURN
        elementId(n) AS node_id,
        labels(n) AS labels,
        properties(n) AS properties
    """

    result = tx.run(query)

    path = os.path.join(
        OUTPUT_DIR,
        "nodes.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "node_id",
            "labels",
            "properties"
        ])

        count = 0

        for record in result:

            writer.writerow([
                record["node_id"],
                "|".join(record["labels"]),
                json.dumps(
                    dict(record["properties"]),
                    default=str
                )
            ])

            count += 1

    print(f"Nodes exported: {count}")
    print(f"File: {path}")
    print()


# ============================================================
# 2. EXPORT ALL RELATIONSHIPS
# ============================================================

def export_relationships(tx):

    query = """
    MATCH (a)-[r]->(b)
    RETURN
        elementId(a) AS source,
        labels(a) AS source_labels,
        type(r) AS relationship,
        elementId(b) AS target,
        labels(b) AS target_labels,
        properties(r) AS properties
    """

    result = tx.run(query)

    path = os.path.join(
        OUTPUT_DIR,
        "relationships.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "source",
            "source_labels",
            "relationship",
            "target",
            "target_labels",
            "properties"
        ])

        count = 0

        for record in result:

            writer.writerow([
                record["source"],
                "|".join(record["source_labels"]),
                record["relationship"],
                record["target"],
                "|".join(record["target_labels"]),
                json.dumps(
                    dict(record["properties"]),
                    default=str
                )
            ])

            count += 1

    print(f"Relationships exported: {count}")
    print(f"File: {path}")
    print()


# ============================================================
# 3. EXPORT DATABASE LABEL METADATA
# ============================================================

def export_labels(tx):

    query = """
    MATCH (n)
    UNWIND labels(n) AS label
    RETURN
        label,
        count(*) AS node_count
    ORDER BY node_count DESC
    """

    result = tx.run(query)

    path = os.path.join(
        OUTPUT_DIR,
        "label_metadata.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "label",
            "node_count"
        ])

        for record in result:

            writer.writerow([
                record["label"],
                record["node_count"]
            ])

    print(f"Label metadata exported")
    print(f"File: {path}")
    print()


# ============================================================
# 4. EXPORT RELATIONSHIP METADATA
# ============================================================

def export_relationship_metadata(tx):

    query = """
    MATCH (a)-[r]->(b)
    RETURN
        type(r) AS relationship_type,
        count(*) AS relationship_count
    ORDER BY relationship_count DESC
    """

    result = tx.run(query)

    path = os.path.join(
        OUTPUT_DIR,
        "relationship_metadata.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "relationship_type",
            "relationship_count"
        ])

        for record in result:

            writer.writerow([
                record["relationship_type"],
                record["relationship_count"]
            ])

    print("Relationship metadata exported")
    print(f"File: {path}")
    print()


# ============================================================
# 5. EXPORT PATIENT NODES
# ============================================================

def export_patients(tx):

    query = """
    MATCH (p:Patient)
    RETURN
        elementId(p) AS node_id,
        properties(p) AS properties
    """

    result = tx.run(query)

    path = os.path.join(
        OUTPUT_DIR,
        "patients.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "node_id",
            "properties"
        ])

        count = 0

        for record in result:

            writer.writerow([
                record["node_id"],
                json.dumps(
                    dict(record["properties"]),
                    default=str
                )
            ])

            count += 1

    print(f"Patients exported: {count}")
    print(f"File: {path}")
    print()


# ============================================================
# 6. EXPORT PATIENT-CONDITION RELATIONSHIPS
# ============================================================

def export_patient_conditions(tx):

    query = """
    MATCH (p:Patient)-[r]->(c:Condition)
    RETURN
        elementId(p) AS patient_id,
        elementId(c) AS condition_id,
        type(r) AS relationship,
        properties(c) AS condition_properties
    """

    result = tx.run(query)

    path = os.path.join(
        OUTPUT_DIR,
        "patient_condition.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "patient_id",
            "condition_id",
            "relationship",
            "condition_properties"
        ])

        count = 0

        for record in result:

            writer.writerow([
                record["patient_id"],
                record["condition_id"],
                record["relationship"],
                json.dumps(
                    dict(record["condition_properties"]),
                    default=str
                )
            ])

            count += 1

    print(
        f"Patient-condition relationships exported: {count}"
    )

    print(f"File: {path}")
    print()


# ============================================================
# 7. EXPORT PATIENT-MEDICATION RELATIONSHIPS
# ============================================================

def export_patient_medications(tx):

    query = """
    MATCH (p:Patient)-[r]->(m:Medication)
    RETURN
        elementId(p) AS patient_id,
        elementId(m) AS medication_id,
        type(r) AS relationship,
        properties(m) AS medication_properties
    """

    result = tx.run(query)

    path = os.path.join(
        OUTPUT_DIR,
        "patient_medication.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "patient_id",
            "medication_id",
            "relationship",
            "medication_properties"
        ])

        count = 0

        for record in result:

            writer.writerow([
                record["patient_id"],
                record["medication_id"],
                record["relationship"],
                json.dumps(
                    dict(record["medication_properties"]),
                    default=str
                )
            ])

            count += 1

    print(
        f"Patient-medication relationships exported: {count}"
    )

    print(f"File: {path}")
    print()


# ============================================================
# 8. EXPORT PATIENT-ENCOUNTER RELATIONSHIPS
# ============================================================

def export_patient_encounters(tx):

    query = """
    MATCH (p:Patient)-[r]->(e:Encounter)
    RETURN
        elementId(p) AS patient_id,
        elementId(e) AS encounter_id,
        type(r) AS relationship,
        properties(e) AS encounter_properties
    """

    result = tx.run(query)

    path = os.path.join(
        OUTPUT_DIR,
        "patient_encounter.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "patient_id",
            "encounter_id",
            "relationship",
            "encounter_properties"
        ])

        count = 0

        for record in result:

            writer.writerow([
                record["patient_id"],
                record["encounter_id"],
                record["relationship"],
                json.dumps(
                    dict(record["encounter_properties"]),
                    default=str
                )
            ])

            count += 1

    print(
        f"Patient-encounter relationships exported: {count}"
    )

    print(f"File: {path}")
    print()


# ============================================================
# RUN EVERYTHING
# ============================================================

try:

    with driver.session() as session:

        print("==========================================")
        print("       SYNTHEA NEO4J DATA EXPORT")
        print("==========================================")
        print()

        print("1/8 Exporting all nodes...")
        session.execute_read(export_nodes)

        print("2/8 Exporting all relationships...")
        session.execute_read(export_relationships)

        print("3/8 Exporting label metadata...")
        session.execute_read(export_labels)

        print("4/8 Exporting relationship metadata...")
        session.execute_read(
            export_relationship_metadata
        )

        print("5/8 Exporting patients...")
        session.execute_read(export_patients)

        print("6/8 Exporting patient-condition data...")
        session.execute_read(
            export_patient_conditions
        )

        print("7/8 Exporting patient-medication data...")
        session.execute_read(
            export_patient_medications
        )

        print("8/8 Exporting patient-encounter data...")
        session.execute_read(
            export_patient_encounters
        )

    print("==========================================")
    print("       EXPORT COMPLETED SUCCESSFULLY")
    print("==========================================")
    print()
    print(f"Your files are located at:")
    print(OUTPUT_DIR)
    print()

except Exception as e:

    print()
    print("==========================================")
    print("ERROR")
    print("==========================================")
    print(e)
    print()

finally:

    driver.close()
