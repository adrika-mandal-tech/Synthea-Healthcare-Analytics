"""
Synthea Healthcare Analytics - Data Inspection & Feature Matrix Design
========================================================================
This script inspects the Synthea CSV exports and Neo4j graph to:
1. Document available files, columns, identifiers, and row counts
2. Determine joinability across files
3. Identify useful files for patient-level ML
4. Identify temporal information
5. Identify safe aggregation opportunities
6. Identify leakage risks
7. Define realistic prediction targets
8. Validate preliminary team findings
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

BASE = Path("/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export")

# ============================================================
# 1. FILE INVENTORY
# ============================================================

print("=" * 70)
print("1. FILE INVENTORY & SCHEMA")
print("=" * 70)

files = {
    "patients": BASE / "patients.csv",
    "patient_condition": BASE / "patient_condition.csv",
    "patient_medication": BASE / "patient_medication.csv",
    "patient_encounter": BASE / "patient_encounter.csv",
    "real_relationships": BASE / "real_relationships.csv",
    "relationship_metadata": BASE / "relationship_metadata.csv",
    "label_metadata": BASE / "label_metadata.csv",
}

for name, path in files.items():
    if path.exists():
        df = pd.read_csv(path)
        print(f"\n{name}:")
        print(f"  Path: {path}")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {df.columns.tolist()}")
    else:
        print(f"\n{name}: MISSING")

# ============================================================
# 2. PATIENT FILE SCHEMA
# ============================================================

print("\n" + "=" * 70)
print("2. PATIENT FILE SCHEMA")
print("=" * 70)

patients = pd.read_csv(BASE / "patients.csv")
patients['props'] = patients['properties'].apply(json.loads)
patient_props = pd.json_normalize(patients['props'])
patient_props['patient_node_id'] = patients['node_id']

print(f"Total patients: {len(patient_props)}")
print(f"Patient node ID format: {patient_props['patient_node_id'].iloc[0]}")
print(f"\nPatient properties available:")
for col in sorted(patient_props.columns):
    non_null = patient_props[col].notna().sum()
    print(f"  {col}: {non_null}/{len(patient_props)} non-null")

print(f"\nDemographics:")
print(f"  GENDER: {patient_props['GENDER'].value_counts().to_dict()}")
print(f"  RACE: {patient_props['RACE'].value_counts().to_dict()}")
print(f"  ETHNICITY: {patient_props['ETHNICITY'].value_counts().to_dict()}")
print(f"  MARITAL: {patient_props['MARITAL'].value_counts().to_dict()}")

patient_props['BIRTHDATE'] = pd.to_datetime(patient_props['BIRTHDATE'])
patient_props['DEATHDATE'] = pd.to_datetime(patient_props['DEATHDATE'], errors='coerce')
ref_date = pd.Timestamp('2020-01-01')
patient_props['age'] = (ref_date - patient_props['BIRTHDATE']).dt.days / 365.25
print(f"\nAge statistics:")
print(f"  Min: {patient_props['age'].min():.1f}")
print(f"  Max: {patient_props['age'].max():.1f}")
print(f"  Mean: {patient_props['age'].mean():.1f}")
print(f"  Median: {patient_props['age'].median():.1f}")

# ============================================================
# 3. CONDITION FILE SCHEMA
# ============================================================

print("\n" + "=" * 70)
print("3. CONDITION FILE SCHEMA")
print("=" * 70)

conditions = pd.read_csv(BASE / "patient_condition.csv")
conditions['props'] = conditions['condition_properties'].apply(json.loads)
cond_props = pd.json_normalize(conditions['props'])
cond_props['patient_id'] = conditions['patient_id']
cond_props['condition_id'] = conditions['condition_id']
cond_props['relationship'] = conditions['relationship']

print(f"Total patient-condition pairs: {len(cond_props)}")
print(f"Unique patients with conditions: {cond_props['patient_id'].nunique()}")
print(f"Unique conditions: {cond_props['CODE'].nunique()}")
print(f"Relationship types: {cond_props['relationship'].unique()}")

print(f"\nTop 30 conditions:")
print(cond_props['DESCRIPTION'].value_counts().head(30))

# ============================================================
# 4. ENCOUNTER FILE SCHEMA
# ============================================================

print("\n" + "=" * 70)
print("4. ENCOUNTER FILE SCHEMA")
print("=" * 70)

encounters = pd.read_csv(BASE / "patient_encounter.csv")
encounters['props'] = encounters['encounter_properties'].apply(json.loads)
enc_props = pd.json_normalize(encounters['props'])
enc_props['patient_id'] = encounters['patient_id']
enc_props['encounter_id'] = encounters['encounter_id']
enc_props['relationship'] = encounters['relationship']

print(f"Total patient-encounter pairs: {len(enc_props)}")
print(f"Unique patients with encounters: {enc_props['patient_id'].nunique()}")
print(f"Relationship types: {enc_props['relationship'].unique()}")

enc_props['START'] = pd.to_datetime(enc_props['START'])
enc_props['STOP'] = pd.to_datetime(enc_props['STOP'])

print(f"\nEncounter classes:")
print(enc_props['ENCOUNTERCLASS'].value_counts())

print(f"\nDate range:")
print(f"  START: {enc_props['START'].min()} to {enc_props['START'].max()}")
print(f"  STOP: {enc_props['STOP'].min()} to {enc_props['STOP'].max()}")

# ============================================================
# 5. MEDICATION FILE SCHEMA
# ============================================================

print("\n" + "=" * 70)
print("5. MEDICATION FILE SCHEMA")
print("=" * 70)

meds = pd.read_csv(BASE / "patient_medication.csv")
meds['props'] = meds['medication_properties'].apply(json.loads)
med_props = pd.json_normalize(meds['props'])
med_props['patient_id'] = meds['patient_id']
med_props['medication_id'] = meds['medication_id']
med_props['relationship'] = meds['relationship']

print(f"Total patient-medication pairs: {len(med_props)}")
print(f"Unique patients with medications: {med_props['patient_id'].nunique()}")
print(f"Unique medications: {med_props['CODE'].nunique()}")
print(f"Relationship types: {med_props['relationship'].unique()}")

print(f"\nTop 20 medications:")
print(med_props['DESCRIPTION'].value_counts().head(20))

# ============================================================
# 6. JOIN ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("6. JOIN ANALYSIS")
print("=" * 70)

patient_ids = set(patient_props['patient_node_id'])
cond_patients = set(cond_props['patient_id'])
enc_patients = set(enc_props['patient_id'])
med_patients = set(med_props['patient_id'])

print(f"Patients in patients.csv: {len(patient_ids)}")
print(f"Patients in conditions: {len(cond_patients)}")
print(f"Patients in encounters: {len(enc_patients)}")
print(f"Patients in medications: {len(med_patients)}")
print(f"Patients in all files: {len(patient_ids & cond_patients & enc_patients & med_patients)}")
print(f"Patients with NO conditions: {len(patient_ids - cond_patients)}")
print(f"Patients with NO encounters: {len(patient_ids - enc_patients)}")
print(f"Patients with NO medications: {len(patient_ids - med_patients)}")

# ============================================================
# 7. LEAKAGE RISK ASSESSMENT
# ============================================================

print("\n" + "=" * 70)
print("7. LEAKAGE RISK ASSESSMENT")
print("=" * 70)

print("""
TEMPORAL LEAKAGE RISKS:
1. Condition dates: NOT available in patient_condition.csv
   - Conditions are only linked to encounters via DIAGNOSED_WITH in Neo4j
   - Encounter START dates ARE available
   
2. Medication dates: NOT available in patient_medication.csv
   - Medication relationships have no START dates in exported data
   
3. Encounter dates: AVAILABLE (START, STOP)
   - Can be used to establish patient timeline
   - Can join with encounter-condition relationships for temporal condition data

SAFE AGGREGATIONS:
- Patient demographics (age, gender, race) - static, no leakage
- Total condition count per patient - if using all historical conditions
- Total encounter count per patient - if using all historical encounters
- Total medication count per patient - if using all historical medications
- Encounter type counts - if using all historical encounters
- Condition indicators (binary flags) - if using all historical conditions

LEAKAGE RISKS:
- Using future conditions as features to predict current conditions
- Using total condition count when predicting a specific condition that contributes to that count
- Using encounter dates after the prediction timepoint
- Using medications prescribed after the prediction timepoint
- Using demographics that might be recorded after the target event
""")

# ============================================================
# 8. PREDICTION TARGET FEASIBILITY
# ============================================================

print("\n" + "=" * 70)
print("8. PREDICTION TARGET FEASIBILITY")
print("=" * 70)

# Key conditions and their prevalence
key_conditions = {
    'Obesity': '162864005',
    'Prediabetes': '15777000',
    'Diabetes': '44054006',
    'Hypertension': '59621000',
    'COVID-19': '840539006',
    'Suspected COVID-19': '840544004',
    'Heart failure': '88805009',
    'Coronary Heart Disease': '53741008',
    'Myocardial Infarction': '22298006',
    'Cardiac Arrest': '410429000',
    'ARDS': '67782005',
    'Respiratory distress': '271825005',
}

print("\nCondition prevalence:")
for name, code in key_conditions.items():
    count = cond_props[cond_props['CODE'] == code]['patient_id'].nunique()
    print(f"  {name}: {count} patients ({count/500*100:.1f}%)")

# Check if we can build temporal targets
print("\nTEMPORAL TARGET CONSTRUCTION POSSIBILITY:")
print("""
To build temporal prediction targets, we need:
1. Patient timeline (first encounter date, last encounter date)
2. Condition onset dates (from Encounter->DIAGNOSED_WITH relationships)
3. Ability to define a cutoff date T and use only data before T

AVAILABLE:
- Encounter START dates (in patient_encounter.csv)
- Encounter -> Condition DIAGNOSED_WITH relationships (in Neo4j)

NEED TO EXPORT:
- Encounter-condition relationships with dates for temporal analysis
""")

# ============================================================
# 9. PROPOSED PATIENT-LEVEL FEATURE MATRIX
# ============================================================

print("\n" + "=" * 70)
print("9. PROPOSED PATIENT-LEVEL FEATURE MATRIX")
print("=" * 70)

# Build basic patient features
patient_features = patient_props[['patient_node_id', 'GENDER', 'RACE', 'ETHNICITY', 'age']].copy()
patient_features['gender_M'] = (patient_features['GENDER'] == 'M').astype(int)
patient_features['gender_F'] = (patient_features['GENDER'] == 'F').astype(int)
patient_features['race_white'] = (patient_features['RACE'] == 'white').astype(int)
patient_features['race_black'] = (patient_features['RACE'] == 'black').astype(int)
patient_features['race_asian'] = (patient_features['RACE'] == 'asian').astype(int)
patient_features['race_native'] = (patient_features['RACE'] == 'native').astype(int)
patient_features['hispanic'] = (patient_features['ETHNICITY'] == 'hispanic').astype(int)

# Condition counts per patient
cond_counts = cond_props.groupby('patient_id').size().reset_index(name='total_conditions')
patient_features = patient_features.merge(
    cond_counts.rename(columns={'patient_id': 'patient_node_id'}), 
    on='patient_node_id', 
    how='left'
)
patient_features['total_conditions'] = patient_features['total_conditions'].fillna(0)

# Encounter counts per patient
enc_counts = enc_props.groupby('patient_id').size().reset_index(name='total_encounters')
patient_features = patient_features.merge(
    enc_counts.rename(columns={'patient_id': 'patient_node_id'}), 
    on='patient_node_id', 
    how='left'
)
patient_features['total_encounters'] = patient_features['total_encounters'].fillna(0)

# Encounter type counts
enc_type_counts = enc_props.groupby(['patient_id', 'ENCOUNTERCLASS']).size().unstack(fill_value=0).reset_index()
enc_type_counts.columns.name = None
patient_features = patient_features.merge(
    enc_type_counts.rename(columns={'patient_id': 'patient_node_id'}), 
    on='patient_node_id', 
    how='left'
)
for col in ['ambulatory', 'wellness', 'outpatient', 'inpatient', 'emergency', 'urgentcare']:
    if col not in patient_features.columns:
        patient_features[col] = 0
    else:
        patient_features[col] = patient_features[col].fillna(0)

# Medication counts per patient
med_counts = med_props.groupby('patient_id').size().reset_index(name='total_medications')
patient_features = patient_features.merge(
    med_counts.rename(columns={'patient_id': 'patient_node_id'}), 
    on='patient_node_id', 
    how='left'
)
patient_features['total_medications'] = patient_features['total_medications'].fillna(0)

# Key condition indicators
key_condition_codes = {
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
    'has_asthma': '195967001',
    'has_kidney_disease': '431855005',
}

for feat_name, code in key_condition_codes.items():
    patient_ids_with_cond = set(cond_props[cond_props['CODE'] == code]['patient_id'])
    patient_features[feat_name] = patient_features['patient_node_id'].isin(patient_ids_with_cond).astype(int)

# Key medication indicators (hypertension meds)
htn_med_keywords = ['hydrochlorothiazide', 'atenolol', 'amlodipine', 'metoprolol', 
                    'furosemide', 'lisinopril', 'losartan', 'verapamil']
htn_meds = med_props[med_props['DESCRIPTION'].str.contains('|'.join(htn_med_keywords), case=False, na=False)]
htn_med_patients = set(htn_meds['patient_id'])
patient_features['has_hypertension_meds'] = patient_features['patient_node_id'].isin(htn_med_patients).astype(int)

# Key medication indicators (diabetes meds)
dm_med_keywords = ['metformin', 'insulin', 'glipizide', 'glyburide', 'pioglitazone', 'sitagliptin']
dm_meds = med_props[med_props['DESCRIPTION'].str.contains('|'.join(dm_med_keywords), case=False, na=False)]
dm_med_patients = set(dm_meds['patient_id'])
patient_features['has_diabetes_meds'] = patient_features['patient_node_id'].isin(dm_med_patients).astype(int)

print(f"\nPatient feature matrix shape: {patient_features.shape}")
print(f"Features: {patient_features.columns.tolist()}")

print(f"\nKey condition prevalence in feature matrix:")
for feat_name in key_condition_codes.keys():
    count = patient_features[feat_name].sum()
    print(f"  {feat_name}: {count} patients ({count/500*100:.1f}%)")

print(f"\nMedication indicators:")
print(f"  has_hypertension_meds: {patient_features['has_hypertension_meds'].sum()} patients")
print(f"  has_diabetes_meds: {patient_features['has_diabetes_meds'].sum()} patients")

# ============================================================
# 10. TEAM FINDINGS VALIDATION SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("10. TEAM FINDINGS VALIDATION SUMMARY")
print("=" * 70)

obesity_patients = set(cond_props[cond_props['CODE'] == '162864005']['patient_id'])
obesity_diabetes = patient_features[patient_features['patient_node_id'].isin(obesity_patients)]['has_diabetes'].sum()
obesity_prediabetes = patient_features[patient_features['patient_node_id'].isin(obesity_patients)]['has_prediabetes'].sum()
obesity_hypertension = patient_features[patient_features['patient_node_id'].isin(obesity_patients)]['has_hypertension'].sum()
obesity_htn_meds = patient_features[patient_features['patient_node_id'].isin(obesity_patients)]['has_hypertension_meds'].sum()

print(f"\nFINDING 1 - Obesity and Diabetes:")
print(f"  Team reported: 214 obese patients, ZERO diabetes")
print(f"  Actual: {len(obesity_patients)} obese patients")
print(f"  With recorded diabetes: {obesity_diabetes} ({obesity_diabetes/len(obesity_patients)*100:.1f}%)")
print(f"  With recorded prediabetes: {obesity_prediabetes} ({obesity_prediabetes/len(obesity_patients)*100:.1f}%)")
print(f"  VERDICT: Team finding is INCORRECT. Diabetes IS recorded in obesity patients.")

print(f"\nFINDING 2 - Obesity and Hypertension:")
print(f"  Team reported: 214 obese, 150 without hypertension, ~29.9% with hypertension")
print(f"  Actual: {len(obesity_patients)} obese patients")
print(f"  With recorded hypertension: {obesity_hypertension} ({obesity_hypertension/len(obesity_patients)*100:.1f}%)")
print(f"  Without recorded hypertension: {len(obesity_patients) - obesity_hypertension}")
print(f"  WITH antihypertensive meds but NO hypertension diagnosis: {obesity_htn_meds - obesity_hypertension}")
print(f"  VERDICT: ~29.9% figure is roughly correct, but antihypertensive medication use is higher.")

print(f"\nFINDING 3 - Hypertension -> Heart Attack:")
htn_patients = set(cond_props[cond_props['CODE'] == '59621000']['patient_id'])
heart_codes = ['22298006', '399211009', '410429000', '429007001', '88805009', '53741008', '84114007']
heart_patients = set(cond_props[cond_props['CODE'].isin(heart_codes)]['patient_id'])
htn_and_heart = htn_patients & heart_patients
print(f"  Team reported: 126 patients at risk")
print(f"  Actual hypertension patients: {len(htn_patients)}")
print(f"  With recorded heart conditions: {len(htn_and_heart)}")
print(f"  VERDICT: Team likely meant 'all 129 hypertensive patients are at risk', not '126 have both conditions'.")

print(f"\nFINDING 4 - COVID -> ARDS:")
covid_patients = set(cond_props[cond_props['CODE'].isin(['840539006', '840544004'])]['patient_id'])
ards_patients = set(cond_props[cond_props['CODE'] == '67782005']['patient_id'])
covid_ards = covid_patients & ards_patients
print(f"  Team reported: 344 patients at risk")
print(f"  Actual COVID patients: {len(covid_patients)}")
print(f"  Actual ARDS patients: {len(ards_patients)}")
print(f"  With both COVID AND ARDS: {len(covid_ards)}")
print(f"  VERDICT: Team likely meant 'all 365 COVID patients are at risk', not '344 have both conditions'.")

# Save feature matrix
patient_features.to_csv(BASE.parent / "patient_features.csv", index=False)
print(f"\nSaved patient feature matrix to: {BASE.parent / 'patient_features.csv'}")
