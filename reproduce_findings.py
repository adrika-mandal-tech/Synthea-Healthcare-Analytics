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
    print("=== REPRODUCING TEAM FINDING 1: OBESITY AND DIABETES ===")
    
    # Get all patient-condition pairs from both relationship types
    result = session.execute_read(run_query, """
        MATCH (p:Patient)-[r]->(c:Condition)
        RETURN elementId(p) AS patient_id, c.CODE AS condition_code, c.DESCRIPTION AS condition_desc, type(r) AS rel_type
    """)
    
    df = pd.DataFrame([dict(r) for r in result])
    print(f"Total patient-condition pairs: {len(df)}")
    print(f"Unique patients: {df['patient_id'].nunique()}")
    print(f"Unique conditions: {df['condition_code'].nunique()}")
    
    # Obesity cohort
    obesity_codes = ['162864005', '408512008']  # BMI 30+ and BMI 40+
    obesity_patients = df[df['condition_code'].isin(obesity_codes)]['patient_id'].unique()
    print(f"\nObesity cohort size: {len(obesity_patients)}")
    
    # Diabetes codes
    diabetes_codes = ['15777000', '44054006', '422034002', '368581000119106', 
                      '1551000119108', '1501000119109', '90781000119102', '97331000119101']
    diabetes_patients = df[df['condition_code'].isin(diabetes_codes)]['patient_id'].unique()
    print(f"Total diabetes patients: {len(diabetes_patients)}")
    
    # Diabetes in obesity cohort
    obesity_df = df[df['patient_id'].isin(obesity_patients)]
    obesity_diabetes = obesity_df[obesity_df['condition_code'].isin(diabetes_codes)]
    print(f"Obesity patients WITH recorded diabetes: {obesity_diabetes['patient_id'].nunique()}")
    print(f"Obesity patients WITHOUT recorded diabetes: {len(obesity_patients) - obesity_diabetes['patient_id'].nunique()}")
    
    # Check all diabetes-related descriptions in obesity cohort
    print(f"\nDiabetes conditions in obesity cohort:")
    print(obesity_diabetes['condition_desc'].value_counts())
    
    print("\n=== REPRODUCING TEAM FINDING 2: OBESITY AND HYPERTENSION ===")
    htn_code = '59621000'
    obesity_htn = obesity_df[obesity_df['condition_code'] == htn_code]
    print(f"Obesity patients WITH recorded hypertension: {obesity_htn['patient_id'].nunique()}")
    print(f"Obesity patients WITHOUT recorded hypertension: {len(obesity_patients) - obesity_htn['patient_id'].nunique()}")
    
    # Check for antihypertensive medications in obesity cohort
    result_meds = session.execute_read(run_query, """
        MATCH (p:Patient)-[:PRESCRIBED]->(m:Medication)
        RETURN elementId(p) AS patient_id, m.CODE AS med_code, m.DESCRIPTION AS med_desc
    """)
    meds_df = pd.DataFrame([dict(r) for r in result_meds])
    htn_med_keywords = ['hydrochlorothiazide', 'atenolol', 'amlodipine', 'metoprolol', 
                       'furosemide', 'lisinopril', 'losartan', 'verapamil', 'warfarin', 
                       'digoxin', 'nitroglycerin']
    htn_meds = meds_df[meds_df['med_desc'].str.contains('|'.join(htn_med_keywords), case=False, na=False)]
    obesity_htn_meds = htn_meds[htn_meds['patient_id'].isin(obesity_patients)]
    print(f"\nObesity patients with antihypertensive medications: {obesity_htn_meds['patient_id'].nunique()}")
    print("Hypertension meds in obesity cohort:")
    print(obesity_htn_meds['med_desc'].value_counts().head(10))
    
    print("\n=== REPRODUCING TEAM FINDING 3: HYPERTENSION -> HEART ATTACK ===")
    htn_patients = df[df['condition_code'] == htn_code]['patient_id'].unique()
    print(f"Total hypertension patients: {len(htn_patients)}")
    
    # What heart-related conditions exist?
    heart_codes = ['22298006', '399211009', '410429000', '429007001', '88805009', '53741008']
    heart_conditions = ['Myocardial Infarction', 'History of myocardial infarction (situation)',
                       'Cardiac Arrest', 'History of cardiac arrest (situation)',
                       'Chronic congestive heart failure (disorder)', 'Coronary Heart Disease']
    
    htn_heart = df[(df['patient_id'].isin(htn_patients)) & 
                   (df['condition_code'].isin(heart_codes))]
    print(f"Hypertension patients WITH recorded heart conditions: {htn_heart['patient_id'].nunique()}")
    print("Heart conditions in hypertension patients:")
    print(htn_heart['condition_desc'].value_counts())
    
    # How many have both HTN and any heart condition?
    heart_patients = df[df['condition_code'].isin(heart_codes)]['patient_id'].unique()
    htn_and_heart = set(htn_patients) & set(heart_patients)
    print(f"\nPatients with BOTH hypertension AND recorded heart condition: {len(htn_and_heart)}")
    print(f"Hypertension patients WITHOUT recorded heart condition: {len(htn_patients) - len(htn_and_heart)}")
    
    print("\n=== REPRODUCING TEAM FINDING 4: COVID -> ARDS ===")
    covid_codes = ['840544004', '840539006']
    ards_code = '67782005'
    
    covid_patients = df[df['condition_code'].isin(covid_codes)]['patient_id'].unique()
    ards_patients = df[df['condition_code'] == ards_code]['patient_id'].unique()
    
    print(f"COVID patients: {len(covid_patients)}")
    print(f"ARDS patients: {len(ards_patients)}")
    
    covid_ards = set(covid_patients) & set(ards_patients)
    print(f"Patients with BOTH COVID AND ARDS: {len(covid_ards)}")
    
    # Where does 344 come from?
    # Maybe it's COVID + respiratory distress (75) + acute respiratory failure (36)?
    resp_codes = ['271825005', '65710008']  # Respiratory distress, Acute respiratory failure
    covid_resp = df[(df['patient_id'].isin(covid_patients)) & 
                    (df['condition_code'].isin(resp_codes))]
    print(f"COVID patients with respiratory distress/failure: {covid_resp['patient_id'].nunique()}")
    
    print("\n=== DATA AVAILABILITY SUMMARY ===")
    print(f"Patients: 500")
    print(f"Patient-Condition pairs: {len(df)}")
    print(f"Patient-Encounter pairs: 13115")
    print(f"Patient-Medication pairs: {len(meds_df)}")
    print(f"Condition START dates available: NO")
    print(f"Medication START dates available: NO")
    print(f"Observation nodes: NO")
    print(f"Procedure nodes exported: NO")
    print(f"Blood pressure data: NO")
    print(f"BMI data: NO (only obesity condition)")

driver.close()
