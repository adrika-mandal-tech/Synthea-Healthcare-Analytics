import pandas as pd
import json

# Load patients
patients = pd.read_csv('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export/patients.csv')
patients['props'] = patients['properties'].apply(json.loads)
patient_props = pd.json_normalize(patients['props'])
patient_props['patient_id'] = patients['node_id']
patient_props['BIRTHDATE'] = pd.to_datetime(patient_props['BIRTHDATE'])
patient_props['DEATHDATE'] = pd.to_datetime(patient_props['DEATHDATE'], errors='coerce')

# Load conditions
conditions = pd.read_csv('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export/patient_condition.csv')
conditions['props'] = conditions['condition_properties'].apply(json.loads)
cond_props = pd.json_normalize(conditions['props'])
cond_props['patient_id'] = conditions['patient_id']
cond_props['condition_id'] = conditions['condition_id']

# Find obesity patients
obesity_conditions = cond_props[cond_props['DESCRIPTION'] == 'Body mass index 30+ - obesity (finding)']
obesity_patients = obesity_conditions['patient_id'].unique()
print(f"Patients with obesity: {len(obesity_patients)}")

# For each obesity patient, get all their conditions
obesity_patient_conditions = cond_props[cond_props['patient_id'].isin(obesity_patients)]
print(f"\nTotal condition records for obesity patients: {len(obesity_patient_conditions)}")

# Check for diabetes in obesity patients
diabetes_conditions = ['Prediabetes', 'Diabetes', 'Diabetic retinopathy associated with type II diabetes mellitus (disorder)',
                       'Neuropathy due to type 2 diabetes mellitus (disorder)',
                       'Nonproliferative diabetic retinopathy due to type 2 diabetes mellitus (disorder)',
                       'Proliferative diabetic retinopathy due to type II diabetes mellitus (disorder)',
                       'Microalbuminuria due to type 2 diabetes mellitus (disorder)',
                       'Macular edema and retinopathy due to type 2 diabetes mellitus (disorder)']

obesity_diabetes = obesity_patient_conditions[obesity_patient_conditions['DESCRIPTION'].isin(diabetes_conditions)]
print(f"\nObesity patients with diabetes-related conditions: {obesity_diabetes['patient_id'].nunique()}")
if len(obesity_diabetes) > 0:
    print(obesity_diabetes['DESCRIPTION'].value_counts())

# Check for hypertension in obesity patients
obesity_hypertension = obesity_patient_conditions[obesity_patient_conditions['DESCRIPTION'] == 'Hypertension']
print(f"\nObesity patients with hypertension: {obesity_hypertension['patient_id'].nunique()}")

# Patients with obesity but no hypertension
obesity_no_htn = set(obesity_patients) - set(obesity_hypertension['patient_id'].unique())
print(f"Obesity patients WITHOUT hypertension: {len(obesity_no_htn)}")

# Get demographics for obesity patients
obesity_demo = patient_props[patient_props['patient_id'].isin(obesity_patients)]
print(f"\nObesity patient demographics:")
print(f"  Gender: {obesity_demo['GENDER'].value_counts().to_dict()}")
print(f"  Race: {obesity_demo['RACE'].value_counts().to_dict()}")
print(f"  Age range: {(pd.Timestamp('2020-01-01') - obesity_demo['BIRTHDATE']).dt.days / 365.25}")
print(f"  Mean age: {((pd.Timestamp('2020-01-01') - obesity_demo['BIRTHDATE']).dt.days / 365.25).mean():.1f}")

# Check medications for obesity patients
meds = pd.read_csv('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export/patient_medication.csv')
meds['props'] = meds['medication_properties'].apply(json.loads)
med_props = pd.json_normalize(meds['props'])
med_props['patient_id'] = meds['patient_id']

obesity_meds = med_props[med_props['patient_id'].isin(obesity_patients)]
htn_meds = obesity_meds[obesity_meds['DESCRIPTION'].str.contains('hydrochlorothiazide|atenolol|amlodipine|metoprolol|furosemide|lisinopril|losartan|verapamil|warfarin|digoxin|nitroglycerin', case=False, na=False)]
print(f"\nObesity patients on antihypertensive meds: {htn_meds['patient_id'].nunique()}")
if len(htn_meds) > 0:
    print(htn_meds['DESCRIPTION'].value_counts().head(10))

# Check encounters for obesity patients
enc = pd.read_csv('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export/patient_encounter.csv')
enc['props'] = enc['encounter_properties'].apply(json.loads)
enc_props = pd.json_normalize(enc['props'])
enc_props['patient_id'] = enc['patient_id']
enc_props['START'] = pd.to_datetime(enc_props['START'])

obesity_enc = enc_props[enc_props['patient_id'].isin(obesity_patients)]
print(f"\nObesity patient encounters: {len(obesity_enc)}")
print(f"Encounter classes: {obesity_enc['ENCOUNTERCLASS'].value_counts().to_dict()}")