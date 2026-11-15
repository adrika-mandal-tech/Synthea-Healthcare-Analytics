"""
Synthea Healthcare Analytics Pipeline
======================================
Step 1: Data Inspection & Team Findings Validation (COMPLETED)
Step 2: Temporal Data Export from Neo4j (THIS FILE)
Step 3: Patient-Level Feature Matrix Construction
Step 4: Statistical Analysis & Association Mining
Step 5: Classical ML Prediction
Step 6: Graph Embeddings & GNN
Step 7: Validation & Explainability
Step 8: Clinical Interpretation & Neo4j Write-back
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from neo4j import GraphDatabase

# ============================================================
# CONFIGURATION
# ============================================================
BASE = Path("/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics")
EXPORT_DIR = BASE / "Synthea_Real_Export"
NEO4J_URI = "bolt://100.23.76.198:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "Prajnadb"
REF_DATE = pd.Timestamp("2020-01-01")  # Reference date for age calculation

# ============================================================
# STEP 2: EXPORT TEMPORAL ENCOUNTER-CONDITION DATA
# ============================================================

def export_temporal_data():
    """
    Export encounter-condition relationships from Neo4j to enable temporal analysis.
    This gives us condition onset dates (approximated by encounter dates).
    """
    print("=" * 70)
    print("STEP 2: EXPORTING TEMPORAL ENCOUNTER-CONDITION DATA")
    print("=" * 70)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    
    def run_query(tx, query):
        result = tx.run(query)
        return [record for record in result]
    
    with driver.session() as session:
        # Export all encounter-condition relationships with dates
        query = """
        MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[r:DIAGNOSED_WITH]->(c:Condition)
        RETURN 
            elementId(p) AS patient_id,
            elementId(e) AS encounter_id,
            e.START AS encounter_start,
            e.STOP AS encounter_stop,
            e.ENCOUNTERCLASS AS encounter_class,
            c.CODE AS condition_code,
            c.DESCRIPTION AS condition_description
        ORDER BY p, e.START
        """
        
        result = session.execute_read(run_query, query)
        df = pd.DataFrame([dict(r) for r in result])
        
        print(f"Exported {len(df)} encounter-condition pairs")
        print(f"Unique patients: {df['patient_id'].nunique()}")
        print(f"Unique conditions: {df['condition_code'].nunique()}")
        print(f"Date range: {df['encounter_start'].min()} to {df['encounter_start'].max()}")
        
        # Save to CSV
        output_path = EXPORT_DIR / "encounter_condition_temporal.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved to: {output_path}")
        
        # Also export encounter-reason relationships
        query2 = """
        MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[r:HAS_REASON]->(c:Condition)
        RETURN 
            elementId(p) AS patient_id,
            elementId(e) AS encounter_id,
            e.START AS encounter_start,
            e.STOP AS encounter_stop,
            e.ENCOUNTERCLASS AS encounter_class,
            c.CODE AS condition_code,
            c.DESCRIPTION AS condition_description
        ORDER BY p, e.START
        """
        
        result2 = session.execute_read(run_query, query2)
        df2 = pd.DataFrame([dict(r) for r in result2])
        
        print(f"\nExported {len(df2)} encounter-reason pairs")
        output_path2 = EXPORT_DIR / "encounter_reason_temporal.csv"
        df2.to_csv(output_path2, index=False)
        print(f"Saved to: {output_path2}")
        
        # Export procedures if available
        try:
            query3 = """
            MATCH (p:Patient)-[:UNDERWENT]->(pr:Procedure)
            RETURN 
                elementId(p) AS patient_id,
                elementId(pr) AS procedure_id,
                pr.CODE AS procedure_code,
                pr.DESCRIPTION AS procedure_description
            """
            result3 = session.execute_read(run_query, query3)
            df3 = pd.DataFrame([dict(r) for r in result3])
            print(f"\nExported {len(df3)} patient-procedure pairs")
            output_path3 = EXPORT_DIR / "patient_procedure.csv"
            df3.to_csv(output_path3, index=False)
            print(f"Saved to: {output_path3}")
        except Exception as e:
            print(f"\nProcedures export skipped: {e}")
    
    driver.close()
    return df, df2

# ============================================================
# STEP 3: PATIENT-LEVEL FEATURE MATRIX WITH TEMPORAL DATA
# ============================================================

def build_patient_feature_matrix(enc_cond_df, enc_reason_df):
    """
    Build comprehensive patient-level feature matrix.
    Includes temporal features for prediction tasks.
    """
    print("\n" + "=" * 70)
    print("STEP 3: BUILDING PATIENT-LEVEL FEATURE MATRIX")
    print("=" * 70)
    
    # Load base patient data
    patients = pd.read_csv(EXPORT_DIR / "patients.csv")
    patients['props'] = patients['properties'].apply(json.loads)
    patient_props = pd.json_normalize(patients['props'])
    patient_props['patient_id'] = patients['node_id']
    
    patient_props['BIRTHDATE'] = pd.to_datetime(patient_props['BIRTHDATE'])
    patient_props['DEATHDATE'] = pd.to_datetime(patient_props['DEATHDATE'], errors='coerce')
    patient_props['age'] = (REF_DATE - patient_props['BIRTHDATE']).dt.days / 365.25
    
    # Load encounter data
    encounters = pd.read_csv(EXPORT_DIR / "patient_encounter.csv")
    encounters['props'] = encounters['encounter_properties'].apply(json.loads)
    enc_props = pd.json_normalize(encounters['props'])
    enc_props['patient_id'] = encounters['patient_id']
    enc_props['START'] = pd.to_datetime(enc_props['START'])
    
    # Load medication data
    meds = pd.read_csv(EXPORT_DIR / "patient_medication.csv")
    meds['props'] = meds['medication_properties'].apply(json.loads)
    med_props = pd.json_normalize(meds['props'])
    med_props['patient_id'] = meds['patient_id']
    
    # Load condition data
    conditions = pd.read_csv(EXPORT_DIR / "patient_condition.csv")
    conditions['props'] = conditions['condition_properties'].apply(json.loads)
    cond_props = pd.json_normalize(conditions['props'])
    cond_props['patient_id'] = conditions['patient_id']
    
    # ============================================================
    # BASE FEATURES
    # ============================================================
    features = patient_props[['patient_id', 'GENDER', 'RACE', 'ETHNICITY', 'age', 
                              'HEALTHCARE_EXPENSES', 'HEALTHCARE_COVERAGE', 'MARITAL']].copy()
    
    # Demographic encoding
    features['gender_M'] = (features['GENDER'] == 'M').astype(int)
    features['gender_F'] = (features['GENDER'] == 'F').astype(int)
    features['race_white'] = (features['RACE'] == 'white').astype(int)
    features['race_black'] = (features['RACE'] == 'black').astype(int)
    features['race_asian'] = (features['RACE'] == 'asian').astype(int)
    features['race_native'] = (features['RACE'] == 'native').astype(int)
    features['hispanic'] = (features['ETHNICITY'] == 'hispanic').astype(int)
    features['married'] = (features['MARITAL'] == 'M').astype(int)
    
    # ============================================================
    # ENCOUNTER FEATURES
    # ============================================================
    enc_counts = enc_props.groupby('patient_id').size().reset_index(name='total_encounters')
    features = features.merge(enc_counts, on='patient_id', how='left')
    features['total_encounters'] = features['total_encounters'].fillna(0)
    
    # Encounter type counts
    enc_type_counts = enc_props.groupby(['patient_id', 'ENCOUNTERCLASS']).size().unstack(fill_value=0).reset_index()
    enc_type_counts.columns.name = None
    features = features.merge(enc_type_counts, on='patient_id', how='left')
    for col in ['ambulatory', 'wellness', 'outpatient', 'inpatient', 'emergency', 'urgentcare']:
        if col not in features.columns:
            features[col] = 0
        else:
            features[col] = features[col].fillna(0)
    
    # Temporal encounter features
    enc_temporal = enc_props.groupby('patient_id').agg(
        first_encounter=('START', 'min'),
        last_encounter=('START', 'max'),
        encounter_span_days=('START', lambda x: (x.max() - x.min()).days),
        total_encounter_cost=('TOTAL_CLAIM_COST', 'sum')
    ).reset_index()
    features = features.merge(enc_temporal, on='patient_id', how='left')
    
    # ============================================================
    # CONDITION FEATURES (from temporal data)
    # ============================================================
    # Use first diagnosis date as condition onset
    cond_onset = enc_cond_df.groupby(['patient_id', 'condition_code', 'condition_description'])['encounter_start'].min().reset_index()
    cond_onset = cond_onset.rename(columns={'encounter_start': 'condition_onset_date'})
    
    # Condition counts
    cond_counts = cond_onset.groupby('patient_id').size().reset_index(name='total_conditions')
    features = features.merge(cond_counts, on='patient_id', how='left')
    features['total_conditions'] = features['total_conditions'].fillna(0)
    
    # Key condition indicators
    key_conditions = {
        'has_obesity': '162864005',
        'has_prediabetes': '15777000',
        'has_diabetes': '44054006',
        'has_hypertension': '59621000',
        'has_covid': '840539006',
        'has_heart_failure': '88805009',
        'has_coronary_heart_disease': '53741008',
        'has_myocardial_infarction': '22298006',
        'has_cardiac_arrest': '410429000',
        'has_ards': '67782005',
        'has_respiratory_distress': '271825005',
        'has_hyperlipidemia': '55822004',
        'has_stroke': '230690007',
        'has_acute_kidney_disease': '65710008',
        'has_chronic_kidney_disease': '431855005',
    }
    
    for feat_name, code in key_conditions.items():
        patient_ids_with = set(cond_onset[cond_onset['condition_code'] == code]['patient_id'])
        features[feat_name] = features['patient_id'].isin(patient_ids_with).astype(int)
    
    # Condition onset dates for key conditions
    for feat_name, code in key_conditions.items():
        onset_dates = cond_onset[cond_onset['condition_code'] == code][['patient_id', 'condition_onset_date']]
        onset_dates = onset_dates.rename(columns={'condition_onset_date': f'{feat_name}_onset'})
        features = features.merge(onset_dates, on='patient_id', how='left')
    
    # ============================================================
    # MEDICATION FEATURES
    # ============================================================
    med_counts = med_props.groupby('patient_id').size().reset_index(name='total_medications')
    features = features.merge(med_counts, on='patient_id', how='left')
    features['total_medications'] = features['total_medications'].fillna(0)
    
    # Medication class indicators
    med_classes = {
        'has_hypertension_meds': ['hydrochlorothiazide', 'atenolol', 'amlodipine', 'metoprolol', 
                                  'furosemide', 'lisinopril', 'losartan', 'verapamil', 'digoxin', 
                                  'nitroglycerin', 'warfarin'],
        'has_diabetes_meds': ['metformin', 'insulin', 'glipizide', 'glyburide', 'pioglitazone', 'sitagliptin'],
        'has_lipid_meds': ['simvastatin', 'atorvastatin', 'rosuvastatin', 'pravastatin', 'lovastatin'],
        'has_respiratory_meds': ['albuterol', 'fluticasone', 'prednisone', 'montelukast'],
    }
    
    for feat_name, keywords in med_classes.items():
        meds_filtered = med_props[med_props['DESCRIPTION'].str.contains('|'.join(keywords), case=False, na=False)]
        patient_ids_with = set(meds_filtered['patient_id'])
        features[feat_name] = features['patient_id'].isin(patient_ids_with).astype(int)
    
    # ============================================================
    # UTILIZATION FEATURES
    # ============================================================
    features['high_utilizer'] = (features['total_encounters'] > features['total_encounters'].quantile(0.9)).astype(int)
    features['high_cost'] = (features['HEALTHCARE_EXPENSES'] > features['HEALTHCARE_EXPENSES'].quantile(0.9)).astype(int)
    features['condition_burden'] = features['total_conditions'] / (features['total_encounters'] + 1)
    features['medication_burden'] = features['total_medications'] / (features['total_encounters'] + 1)
    
    # ============================================================
    # COMORBIDITY FEATURES
    # ============================================================
    features['has_any_cardiovascular'] = (
        features['has_hypertension'] + features['has_heart_failure'] + 
        features['has_coronary_heart_disease'] + features['has_myocardial_infarction'] +
        features['has_cardiac_arrest'] + features['has_stroke']
    ).clip(upper=1)
    
    features['has_any_metabolic'] = (
        features['has_obesity'] + features['has_prediabetes'] + 
        features['has_diabetes'] + features['has_hyperlipidemia']
    ).clip(upper=1)
    
    features['has_any_respiratory'] = (
        features['has_covid'] + features['has_ards'] + 
        features['has_respiratory_distress']
    ).clip(upper=1)
    
    # ============================================================
    # SAVE FEATURE MATRIX
    # ============================================================
    output_path = BASE / "patient_features_full.csv"
    features.to_csv(output_path, index=False)
    print(f"\nSaved full patient feature matrix: {features.shape}")
    print(f"Output: {output_path}")
    
    return features

# ============================================================
# STEP 4: DEFINE PREDICTION TARGETS
# ============================================================

def define_prediction_targets(enc_cond_df, features):
    """
    Define clinically meaningful prediction targets with temporal splitting.
    """
    print("\n" + "=" * 70)
    print("STEP 4: DEFINING PREDICTION TARGETS")
    print("=" * 70)
    
    # Get condition onset dates
    cond_onset = enc_cond_df.groupby(['patient_id', 'condition_code'])['encounter_start'].min().reset_index()
    cond_onset = cond_onset.rename(columns={'encounter_start': 'onset_date'})
    
    targets = features[['patient_id']].copy()
    
    # ============================================================
    # TARGET 1: Future Hypertension (temporal)
    # ============================================================
    print("\nTARGET 1: Future Recorded Hypertension Diagnosis")
    htn_onset = cond_onset[cond_onset['condition_code'] == '59621000'][['patient_id', 'onset_date']]
    htn_onset = htn_onset.rename(columns={'onset_date': 'htn_onset_date'})
    targets = targets.merge(htn_onset, on='patient_id', how='left')
    
    # For patients WITHOUT hypertension, target = 0
    # For patients WITH hypertension, use onset date for temporal split
    targets['has_hypertension'] = targets['htn_onset_date'].notna().astype(int)
    print(f"  Positive cases: {targets['has_hypertension'].sum()} ({targets['has_hypertension'].mean()*100:.1f}%)")
    print(f"  Negative cases: {(~targets['has_hypertension'].astype(bool)).sum()}")
    
    # ============================================================
    # TARGET 2: Future Diabetes (temporal)
    # ============================================================
    print("\nTARGET 2: Future Recorded Diabetes Diagnosis")
    dm_codes = ['44054006', '422034002', '368581000119106', '1551000119108', 
                '1501000119109', '90781000119102', '97331000119101']
    dm_onset = cond_onset[cond_onset['condition_code'].isin(dm_codes)]
    dm_onset = dm_onset.groupby('patient_id')['onset_date'].min().reset_index()
    dm_onset = dm_onset.rename(columns={'onset_date': 'dm_onset_date'})
    targets = targets.merge(dm_onset, on='patient_id', how='left')
    
    targets['has_diabetes'] = targets['dm_onset_date'].notna().astype(int)
    print(f"  Positive cases: {targets['has_diabetes'].sum()} ({targets['has_diabetes'].mean()*100:.1f}%)")
    print(f"  Negative cases: {(~targets['has_diabetes'].astype(bool)).sum()}")
    
    # ============================================================
    # TARGET 3: Future Cardiovascular Event
    # ============================================================
    print("\nTARGET 3: Future Recorded Cardiovascular Event (MI, Cardiac Arrest, or Heart Failure)")
    cvd_codes = ['22298006', '410429000', '429007001', '88805009']
    cvd_onset = cond_onset[cond_onset['condition_code'].isin(cvd_codes)]
    cvd_onset = cvd_onset.groupby('patient_id')['onset_date'].min().reset_index()
    cvd_onset = cvd_onset.rename(columns={'onset_date': 'cvd_onset_date'})
    targets = targets.merge(cvd_onset, on='patient_id', how='left')
    
    targets['has_cvd_event'] = targets['cvd_onset_date'].notna().astype(int)
    print(f"  Positive cases: {targets['has_cvd_event'].sum()} ({targets['has_cvd_event'].mean()*100:.1f}%)")
    print(f"  Negative cases: {(~targets['has_cvd_event'].astype(bool)).sum()}")
    
    # ============================================================
    # TARGET 4: High Healthcare Utilization
    # ============================================================
    print("\nTARGET 4: High Healthcare Utilization (>90th percentile encounters)")
    util_threshold = features['total_encounters'].quantile(0.9)
    targets['high_utilizer'] = (features['total_encounters'] > util_threshold).astype(int)
    print(f"  Threshold: >{util_threshold:.0f} encounters")
    print(f"  Positive cases: {targets['high_utilizer'].sum()} ({targets['high_utilizer'].mean()*100:.1f}%)")
    
    # ============================================================
    # TEMPORAL SPLIT STRATEGY
    # ============================================================
    print("\n" + "=" * 70)
    print("TEMPORAL SPLIT STRATEGY")
    print("=" * 70)
    
    enc_temporal = enc_cond_df.groupby('patient_id')['encounter_start'].agg(['min', 'max']).reset_index()
    enc_temporal.columns = ['patient_id', 'first_encounter', 'last_encounter']
    enc_temporal['first_encounter'] = pd.to_datetime(enc_temporal['first_encounter'])
    enc_temporal['last_encounter'] = pd.to_datetime(enc_temporal['last_encounter'])
    targets = targets.merge(enc_temporal, on='patient_id', how='left')
    
    # Define cutoff: use data before 2015-01-01 for training, after for testing
    # This ensures temporal separation
    cutoff_date = pd.Timestamp('2015-01-01', tz='UTC')
    targets['train_period'] = targets['first_encounter'] < cutoff_date
    
    print(f"\nTemporal cutoff: {cutoff_date}")
    print(f"Patients with first encounter before cutoff: {targets['train_period'].sum()}")
    print(f"Patients with first encounter after cutoff: {(~targets['train_period']).sum()}")
    
    # For each target, determine if onset is after cutoff (for temporal evaluation)
    for target_col, date_col in [
        ('has_hypertension', 'htn_onset_date'),
        ('has_diabetes', 'dm_onset_date'),
        ('has_cvd_event', 'cvd_onset_date')
    ]:
        targets[f'{target_col}_temporal_positive'] = (
            (targets[target_col] == 1) & 
            (pd.to_datetime(targets[date_col], errors='coerce') >= cutoff_date)
        ).astype(int)
        print(f"\n{target_col}:")
        print(f"  Temporal positives (onset after cutoff): {targets[f'{target_col}_temporal_positive'].sum()}")
    
    # Save targets
    output_path = BASE / "prediction_targets.csv"
    targets.to_csv(output_path, index=False)
    print(f"\nSaved prediction targets: {output_path}")
    
    return targets

# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    print("Synthea Healthcare Analytics Pipeline")
    print("=====================================\n")
    
    # Step 2: Export temporal data
    enc_cond_df, enc_reason_df = export_temporal_data()
    
    # Step 3: Build feature matrix
    features = build_patient_feature_matrix(enc_cond_df, enc_reason_df)
    
    # Step 4: Define targets
    targets = define_prediction_targets(enc_cond_df, features)
    
    print("\n" + "=" * 70)
    print("PIPELINE SETUP COMPLETE")
    print("=" * 70)
    print(f"Feature matrix: {features.shape}")
    print(f"Targets: {targets.shape}")
    print("\nNext steps:")
    print("1. Statistical analysis (condition associations, demographics)")
    print("2. Classical ML models (Logistic Regression, Random Forest, XGBoost)")
    print("3. Graph embeddings (Node2Vec, FastRP)")
    print("4. GNN models (GraphSAGE, GCN)")
    print("5. Model validation and explainability")
    print("6. Clinical interpretation and Neo4j write-back")
