"""
Synthea Healthcare Analytics - Step 5: Statistical Analysis & Classical ML
============================================================================
This script performs:
1. Condition comorbidity analysis (lift, Jaccard, odds ratios, chi-square)
2. Demographic-condition associations
3. Medication-condition associations
4. Classical ML prediction (Logistic Regression, Random Forest, XGBoost)
5. Model validation with temporal split
6. Explainability (SHAP, feature importance)
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from scipy import stats
from scipy.sparse import csr_matrix
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, 
    precision_recall_curve, average_precision_score, f1_score,
    precision_score, recall_score, roc_curve
)
from sklearn.utils.class_weight import compute_class_weight
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
BASE = Path("/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics")
EXPORT_DIR = BASE / "Synthea_Real_Export"
NEO4J_URI = "bolt://100.23.76.198:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "Prajnadb"
REF_DATE = pd.Timestamp("2020-01-01")
CUTOFF_DATE = pd.Timestamp("2015-01-01")
RANDOM_SEED = 42

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def load_data():
    """Load all exported data files."""
    print("Loading data...")
    
    patients = pd.read_csv(EXPORT_DIR / "patients.csv")
    patients['props'] = patients['properties'].apply(json.loads)
    patient_props = pd.json_normalize(patients['props'])
    patient_props['patient_id'] = patients['node_id']
    patient_props['BIRTHDATE'] = pd.to_datetime(patient_props['BIRTHDATE'])
    patient_props['age'] = (REF_DATE - patient_props['BIRTHDATE']).dt.days / 365.25
    
    conditions = pd.read_csv(EXPORT_DIR / "patient_condition.csv")
    conditions['props'] = conditions['condition_properties'].apply(json.loads)
    cond_props = pd.json_normalize(conditions['props'])
    cond_props['patient_id'] = conditions['patient_id']
    
    encounters = pd.read_csv(EXPORT_DIR / "patient_encounter.csv")
    encounters['props'] = encounters['encounter_properties'].apply(json.loads)
    enc_props = pd.json_normalize(encounters['props'])
    enc_props['patient_id'] = encounters['patient_id']
    enc_props['START'] = pd.to_datetime(enc_props['START'])
    
    meds = pd.read_csv(EXPORT_DIR / "patient_medication.csv")
    meds['props'] = meds['medication_properties'].apply(json.loads)
    med_props = pd.json_normalize(meds['props'])
    med_props['patient_id'] = meds['patient_id']
    
    # Load temporal encounter-condition data
    enc_cond = pd.read_csv(EXPORT_DIR / "encounter_condition_temporal.csv")
    enc_cond['encounter_start'] = pd.to_datetime(enc_cond['encounter_start'])
    enc_cond['condition_code'] = enc_cond['condition_code'].astype(str)
    
    print("Data loaded successfully.")
    return patient_props, cond_props, enc_props, med_props, enc_cond

# ============================================================
# SECTION 1: COMORBIDITY ASSOCIATION ANALYSIS
# ============================================================

def comorbidity_analysis(cond_props):
    """
    Analyze condition co-occurrence patterns using:
    - Jaccard similarity
    - Lift
    - Odds ratios
    - Chi-square tests
    """
    print("\n" + "=" * 70)
    print("SECTION 1: COMORBIDITY ASSOCIATION ANALYSIS")
    print("=" * 70)
    
    # Create patient-condition binary matrix
    patient_cond = cond_props.groupby(['patient_id', 'CODE']).size().reset_index(name='count')
    patient_ids = patient_cond['patient_id'].unique()
    condition_codes = patient_cond['CODE'].unique()
    
    # Build sparse binary matrix
    patient_to_idx = {p: i for i, p in enumerate(patient_ids)}
    cond_to_idx = {str(c): i for i, c in enumerate(condition_codes)}
    
    rows = [patient_to_idx[p] for p in patient_cond['patient_id']]
    cols = [cond_to_idx[str(c)] for c in patient_cond['CODE']]
    data = [1] * len(rows)
    
    binary_matrix = csr_matrix((data, (rows, cols)), shape=(len(patient_ids), len(condition_codes)))
    
    # Condition metadata
    cond_meta = cond_props.groupby('CODE').agg({
        'DESCRIPTION': 'first',
        'patient_id': 'count'
    }).rename(columns={'patient_id': 'patient_count'}).reset_index()
    cond_meta['CODE'] = cond_meta['CODE'].astype(str)
    cond_meta['prevalence'] = cond_meta['patient_count'] / 500
    
    # Co-occurrence matrix
    cooc_matrix = binary_matrix.T @ binary_matrix
    cooc_dense = cooc_matrix.toarray()
    
    # Jaccard similarity
    condition_sets = {}
    for _, row in cond_props.iterrows():
        pid = row['patient_id']
        code = str(row['CODE'])
        if pid not in condition_sets:
            condition_sets[pid] = set()
        condition_sets[pid].add(code)
    
    all_conditions = [str(c) for c in condition_codes]
    condition_to_desc = {str(row['CODE']): row['DESCRIPTION'] for _, row in cond_meta.iterrows()}
    
    # Calculate Jaccard for top conditions
    top_conditions = [str(c) for c in cond_meta.nlargest(20, 'patient_count')['CODE'].tolist()]
    
    print("\nTop 20 Conditions by Prevalence:")
    for _, row in cond_meta.nlargest(20, 'patient_count').iterrows():
        print(f"  {row['DESCRIPTION']}: {row['patient_count']} patients ({row['prevalence']*100:.1f}%)")
    
    # Calculate pairwise Jaccard for top conditions
    print("\nPairwise Jaccard Similarity (Top 20 Conditions):")
    jaccard_results = []
    for i, cond_a in enumerate(top_conditions[:10]):
        for cond_b in top_conditions[i+1:10]:
            set_a = set()
            set_b = set()
            for pid, conds in condition_sets.items():
                if cond_a in conds:
                    set_a.add(pid)
                if cond_b in conds:
                    set_b.add(pid)
            
            intersection = len(set_a & set_b)
            union = len(set_a | set_b)
            jaccard = intersection / union if union > 0 else 0
            
            if jaccard > 0.01:  # Only report non-trivial similarities
                jaccard_results.append({
                    'condition_a': condition_to_desc.get(cond_a, cond_a),
                    'condition_b': condition_to_desc.get(cond_b, cond_b),
                    'jaccard': jaccard,
                    'intersection': intersection,
                    'union': union
                })
    
    jaccard_df = pd.DataFrame(jaccard_results).sort_values('jaccard', ascending=False)
    print(jaccard_df.head(15).to_string(index=False))
    
    # Calculate Lift for top condition pairs
    print("\nCondition Co-occurrence Lift (Top Pairs):")
    lift_results = []
    for i, cond_a in enumerate(top_conditions[:15]):
        for cond_b in top_conditions[i+1:15]:
            set_a = set()
            set_b = set()
            for pid, conds in condition_sets.items():
                if cond_a in conds:
                    set_a.add(pid)
                if cond_b in conds:
                    set_b.add(pid)
            
            intersection = len(set_a & set_b)
            pa = len(set_a) / 500
            pb = len(set_b) / 500
            pab = intersection / 500
            lift = pab / (pa * pb) if (pa * pb) > 0 else 0
            
            if lift > 1.1:  # Only report meaningful lifts
                lift_results.append({
                    'condition_a': condition_to_desc.get(cond_a, cond_a),
                    'condition_b': condition_to_desc.get(cond_b, cond_b),
                    'lift': lift,
                    'cooccurrence': intersection,
                    'p_a': pa,
                    'p_b': pb
                })
    
    lift_df = pd.DataFrame(lift_results).sort_values('lift', ascending=False)
    print(lift_df.head(15).to_string(index=False))
    
    # Chi-square test for key pairs
    print("\nChi-Square Tests for Key Condition Pairs:")
    chi2_results = []
    key_pairs = [
        ('162864005', '15777000'),  # Obesity + Prediabetes
        ('162864005', '59621000'),  # Obesity + Hypertension
        ('15777000', '44054006'),   # Prediabetes + Diabetes
        ('59621000', '22298006'),   # Hypertension + MI
        ('840539006', '271825005'), # COVID + Respiratory distress
        ('840539006', '67782005'),  # COVID + ARDS
    ]
    
    for cond_a, cond_b in key_pairs:
        set_a = set()
        set_b = set()
        for pid, conds in condition_sets.items():
            if cond_a in conds:
                set_a.add(pid)
            if cond_b in conds:
                set_b.add(pid)
        
        both = set_a & set_b
        a_only = set_a - set_b
        b_only = set_b - set_a
        neither = set(patient_ids) - set_a - set_b
        
        contingency = np.array([
            [len(both), len(a_only)],
            [len(b_only), len(neither)]
        ])
        
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
        
        # Odds ratio
        if expected[0, 1] > 0 and expected[1, 0] > 0:
            odds_ratio = (contingency[0, 0] * contingency[1, 1]) / (contingency[0, 1] * contingency[1, 0])
        else:
            odds_ratio = np.inf
        
        cond_a_desc = condition_to_desc.get(cond_a, cond_a)
        cond_b_desc = condition_to_desc.get(cond_b, cond_b)
        
        print(f"\n  {cond_a_desc} + {cond_b_desc}:")
        print(f"    Both: {len(both)}, A only: {len(a_only)}, B only: {len(b_only)}, Neither: {len(neither)}")
        print(f"    Chi-square: {chi2:.2f}, p-value: {p_value:.2e}, OR: {odds_ratio:.2f}")
        print(f"    Significant (p < 0.05): {'Yes' if p_value < 0.05 else 'No'}")
        
        chi2_results.append({
            'condition_a': cond_a_desc,
            'condition_b': cond_b_desc,
            'chi2': chi2,
            'p_value': p_value,
            'odds_ratio': odds_ratio,
            'both': len(both)
        })
    
    chi2_df = pd.DataFrame(chi2_results)
    
    # Save results
    jaccard_df.to_csv(BASE / "comorbidity_jaccard.csv", index=False)
    lift_df.to_csv(BASE / "comorbidity_lift.csv", index=False)
    chi2_df.to_csv(BASE / "comorbidity_chi2.csv", index=False)
    
    print("\nSaved comorbidity analysis results.")
    return jaccard_df, lift_df, chi2_df, condition_sets

# ============================================================
# SECTION 2: DEMOGRAPHIC-CONDITION ASSOCIATIONS
# ============================================================

def demographic_analysis(patient_props, cond_props, condition_sets):
    """
    Analyze relationships between demographics and conditions.
    """
    print("\n" + "=" * 70)
    print("SECTION 2: DEMOGRAPHIC-CONDITION ASSOCIATIONS")
    print("=" * 70)
    
    condition_to_desc = dict(zip(cond_props['CODE'].astype(str), cond_props['DESCRIPTION']))
    
    # Build condition -> set of patients mapping
    cond_to_patients = {}
    for pid, conds in condition_sets.items():
        for code in conds:
            if code not in cond_to_patients:
                cond_to_patients[code] = set()
            cond_to_patients[code].add(pid)
    
    # Key conditions to analyze
    key_conditions = {
        'Obesity': '162864005',
        'Prediabetes': '15777000',
        'Diabetes': '44054006',
        'Hypertension': '59621000',
        'COVID-19': '840539006',
        'Heart failure': '88805009',
        'Hyperlipidemia': '55822004',
    }
    
    results = []
    
    for cond_name, cond_code in key_conditions.items():
        cond_patients = cond_to_patients.get(cond_code, set())
        
        print(f"\n--- {cond_name} ---")
        print(f"  Total patients: {len(cond_patients)}")
        
        # Age comparison
        if len(cond_patients) > 0:
            cond_ages = patient_props[patient_props['patient_id'].isin(cond_patients)]['age']
            all_ages = patient_props['age']
            
            t_stat, p_value = stats.ttest_ind(cond_ages, all_ages, nan_policy='omit')
            print(f"  Mean age: {cond_ages.mean():.1f} vs overall {all_ages.mean():.1f} (p={p_value:.4f})")
            
            results.append({
                'condition': cond_name,
                'analysis': 'age',
                'mean_cases': cond_ages.mean(),
                'mean_overall': all_ages.mean(),
                't_stat': t_stat,
                'p_value': p_value
            })
        
        # Gender distribution
        if len(cond_patients) > 0:
            cond_patients_df = patient_props[patient_props['patient_id'].isin(cond_patients)]
            gender_dist = cond_patients_df['GENDER'].value_counts()
            overall_gender = patient_props['GENDER'].value_counts()
            
            # Chi-square for gender
            contingency = np.array([
                [gender_dist.get('M', 0), gender_dist.get('F', 0)],
                [overall_gender.get('M', 0) - gender_dist.get('M', 0), 
                 overall_gender.get('F', 0) - gender_dist.get('F', 0)]
            ])
            
            if contingency.sum() > 0:
                chi2, p_value, _, _ = stats.chi2_contingency(contingency)
                print(f"  Gender: M={gender_dist.get('M', 0)}, F={gender_dist.get('F', 0)} (p={p_value:.4f})")
                
                results.append({
                    'condition': cond_name,
                    'analysis': 'gender',
                    'chi2': chi2,
                    'p_value': p_value
                })
        
        # Race distribution
        if len(cond_patients) > 0:
            cond_patients_df = patient_props[patient_props['patient_id'].isin(cond_patients)]
            race_dist = cond_patients_df['RACE'].value_counts()
            
            print(f"  Race distribution: {dict(race_dist)}")
            
            for race in ['white', 'black', 'asian', 'native']:
                n_cond = race_dist.get(race, 0)
                n_total = (patient_props['RACE'] == race).sum()
                n_rest = len(cond_patients) - n_cond
                
                if n_total > 0 and n_rest > 0:
                    contingency = np.array([
                        [n_cond, n_rest],
                        [n_total - n_cond, 500 - n_total - n_rest]
                    ])
                    
                    if contingency.sum() > 0:
                        chi2, p_value, _, _ = stats.chi2_contingency(contingency)
                        if p_value < 0.1:  # Report marginally significant
                            print(f"    {race}: {n_cond}/{n_total} ({n_cond/n_total*100:.1f}%) (p={p_value:.4f})")
                        
                        results.append({
                            'condition': cond_name,
                            'analysis': f'race_{race}',
                            'count': n_cond,
                            'total': n_total,
                            'p_value': p_value
                        })
    
    # Age group analysis
    print("\n--- Age Group Analysis ---")
    patient_props['age_group'] = pd.cut(patient_props['age'], 
                                        bins=[0, 18, 35, 50, 65, 100], 
                                        labels=['0-18', '19-35', '36-50', '51-65', '65+'])
    
    for cond_name, cond_code in [('Obesity', '162864005'), ('Hypertension', '59621000'), ('Prediabetes', '15777000')]:
        cond_patients = condition_sets.get(cond_code, set())
        if len(cond_patients) == 0:
            continue
        
        cond_df = patient_props[patient_props['patient_id'].isin(cond_patients)]
        age_dist = cond_df['age_group'].value_counts().sort_index()
        total_dist = patient_props['age_group'].value_counts().sort_index()
        
        print(f"\n  {cond_name} by age group:")
        for age_group in age_dist.index:
            n_cond = age_dist.get(age_group, 0)
            n_total = total_dist.get(age_group, 0)
            pct = n_cond / n_total * 100 if n_total > 0 else 0
            print(f"    {age_group}: {n_cond}/{n_total} ({pct:.1f}%)")
    
    demo_df = pd.DataFrame(results)
    demo_df.to_csv(BASE / "demographic_associations.csv", index=False)
    print("\nSaved demographic analysis results.")
    return demo_df

# ============================================================
# SECTION 3: MEDICATION-CONDITION ASSOCIATIONS
# ============================================================

def medication_condition_analysis(med_props, cond_props, condition_sets):
    """
    Analyze medication-condition associations.
    """
    print("\n" + "=" * 70)
    print("SECTION 3: MEDICATION-CONDITION ASSOCIATIONS")
    print("=" * 70)
    
    # Build condition -> set of patients mapping
    cond_to_patients = {}
    for pid, conds in condition_sets.items():
        for code in conds:
            if code not in cond_to_patients:
                cond_to_patients[code] = set()
            cond_to_patients[code].add(pid)
    
    condition_to_desc = dict(zip(cond_props['CODE'].astype(str), cond_props['DESCRIPTION']))
    
    # Define medication classes
    med_classes = {
        'Antihypertensives': ['hydrochlorothiazide', 'atenolol', 'amlodipine', 'metoprolol', 
                              'furosemide', 'lisinopril', 'losartan', 'verapamil', 'digoxin', 
                              'nitroglycerin', 'warfarin'],
        'Diabetes medications': ['metformin', 'insulin', 'glipizide', 'glyburide', 'pioglitazone', 'sitagliptin'],
        'Lipid-lowering': ['simvastatin', 'atorvastatin', 'rosuvastatin', 'pravastatin', 'lovastatin'],
        'Respiratory': ['albuterol', 'fluticasone', 'prednisone', 'montelukast'],
        'Analgesics': ['acetaminophen', 'naproxen', 'ibuprofen', 'morphine', 'oxycodone'],
    }
    
    # Get patients with each medication class
    med_class_patients = {}
    for class_name, keywords in med_classes.items():
        meds_filtered = med_props[med_props['DESCRIPTION'].str.contains('|'.join(keywords), case=False, na=False)]
        med_class_patients[class_name] = set(meds_filtered['patient_id'])
    
    # Key conditions
    key_conditions = {
        'Obesity': '162864005',
        'Prediabetes': '15777000',
        'Diabetes': '44054006',
        'Hypertension': '59621000',
        'COVID-19': '840539006',
        'Heart failure': '88805009',
        'Hyperlipidemia': '55822004',
        'Respiratory distress': '271825005',
    }
    
    print("\nMedication-Condition Co-occurrence:")
    results = []
    
    for med_class, med_patients in med_class_patients.items():
        print(f"\n{med_class} ({len(med_patients)} patients):")
        
        for cond_name, cond_code in key_conditions.items():
            cond_patients = cond_to_patients.get(cond_code, set())
            both = med_patients & cond_patients
            
            if len(both) > 0:
                pct = len(both) / len(cond_patients) * 100
                print(f"  {cond_name}: {len(both)} patients ({pct:.1f}% of {cond_name} patients)")
                
                results.append({
                    'medication_class': med_class,
                    'condition': cond_name,
                    'patients_with_both': len(both),
                    'pct_of_condition': pct
                })
    
    med_cond_df = pd.DataFrame(results)
    med_cond_df.to_csv(BASE / "medication_condition_associations.csv", index=False)
    print("\nSaved medication-condition analysis results.")
    return med_cond_df

# ============================================================
# SECTION 4: CLASSICAL ML PREDICTION
# ============================================================

def build_feature_matrix(patient_props, cond_props, enc_props, med_props, condition_sets):
    """Build comprehensive feature matrix for ML."""
    print("\n" + "=" * 70)
    print("SECTION 4: BUILDING FEATURE MATRIX FOR ML")
    print("=" * 70)
    
    features = patient_props[['patient_id', 'GENDER', 'RACE', 'ETHNICITY', 'age', 
                              'HEALTHCARE_EXPENSES', 'HEALTHCARE_COVERAGE', 'MARITAL']].copy()
    
    # Demographics
    features['gender_M'] = (features['GENDER'] == 'M').astype(int)
    features['gender_F'] = (features['GENDER'] == 'F').astype(int)
    features['race_white'] = (features['RACE'] == 'white').astype(int)
    features['race_black'] = (features['RACE'] == 'black').astype(int)
    features['race_asian'] = (features['RACE'] == 'asian').astype(int)
    features['race_native'] = (features['RACE'] == 'native').astype(int)
    features['hispanic'] = (features['ETHNICITY'] == 'hispanic').astype(int)
    features['married'] = (features['MARITAL'] == 'M').astype(int)
    
    # Encounter features
    enc_counts = enc_props.groupby('patient_id').size().reset_index(name='total_encounters')
    features = features.merge(enc_counts, on='patient_id', how='left')
    features['total_encounters'] = features['total_encounters'].fillna(0)
    
    enc_type_counts = enc_props.groupby(['patient_id', 'ENCOUNTERCLASS']).size().unstack(fill_value=0).reset_index()
    enc_type_counts.columns.name = None
    features = features.merge(enc_type_counts, on='patient_id', how='left')
    for col in ['ambulatory', 'wellness', 'outpatient', 'inpatient', 'emergency', 'urgentcare']:
        if col not in features.columns:
            features[col] = 0
        else:
            features[col] = features[col].fillna(0)
    
    # Condition features
    cond_counts = pd.Series(condition_sets).reset_index()
    cond_counts.columns = ['patient_id', 'conditions']
    cond_counts['total_conditions'] = cond_counts['conditions'].apply(len)
    features = features.merge(cond_counts[['patient_id', 'total_conditions']], on='patient_id', how='left')
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
    }
    
    for feat_name, code in key_conditions.items():
        patient_ids_with = set(condition_sets.get(code, []))
        features[feat_name] = features['patient_id'].isin(patient_ids_with).astype(int)
    
    # Medication features
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
    
    # Utilization features
    features['high_utilizer'] = (features['total_encounters'] > features['total_encounters'].quantile(0.9)).astype(int)
    features['high_cost'] = (features['HEALTHCARE_EXPENSES'] > features['HEALTHCARE_EXPENSES'].quantile(0.9)).astype(int)
    features['condition_burden'] = features['total_conditions'] / (features['total_encounters'] + 1)
    features['medication_burden'] = features['total_medications'] if 'total_medications' in features.columns else 0
    features['medication_burden'] = features['medication_burden'] / (features['total_encounters'] + 1)
    
    # Medication count
    med_counts = med_props.groupby('patient_id').size().reset_index(name='total_medications')
    features = features.merge(med_counts, on='patient_id', how='left')
    features['total_medications'] = features['total_medications'].fillna(0)
    
    # Comorbidity flags
    features['has_any_cardiovascular'] = (
        features['has_hypertension'] + features['has_heart_failure'] + 
        features['has_coronary_heart_disease'] + features['has_myocardial_infarction'] +
        features['has_cardiac_arrest'] + features['has_stroke']
    ).clip(upper=1)
    
    features['has_any_metabolic'] = (
        features['has_obesity'] + features['has_prediabetes'] + 
        features['has_diabetes'] + features['has_hyperlipidemia']
    ).clip(upper=1)
    
    print(f"Feature matrix shape: {features.shape}")
    print(f"Features: {features.columns.tolist()}")
    
    return features

def define_targets(features, enc_cond):
    """Define prediction targets with temporal splitting."""
    print("\n" + "=" * 70)
    print("DEFINING PREDICTION TARGETS")
    print("=" * 70)
    
    targets = features[['patient_id']].copy()
    
    # Get condition onset dates from encounter-condition data
    cond_onset = enc_cond.groupby(['patient_id', 'condition_code'])['encounter_start'].min().reset_index()
    cond_onset = cond_onset.rename(columns={'encounter_start': 'onset_date'})
    
    # Target 1: Hypertension
    htn_onset = cond_onset[cond_onset['condition_code'] == '59621000'][['patient_id', 'onset_date']]
    htn_onset = htn_onset.rename(columns={'onset_date': 'htn_onset_date'})
    targets = targets.merge(htn_onset, on='patient_id', how='left')
    targets['has_hypertension'] = targets['htn_onset_date'].notna().astype(int)
    
    # Target 2: Diabetes
    dm_codes = ['44054006', '422034002', '368581000119106', '1551000119108', 
                '1501000119109', '90781000119102', '97331000119101']
    dm_onset = cond_onset[cond_onset['condition_code'].isin(dm_codes)]
    dm_onset = dm_onset.groupby('patient_id')['onset_date'].min().reset_index()
    dm_onset = dm_onset.rename(columns={'onset_date': 'dm_onset_date'})
    targets = targets.merge(dm_onset, on='patient_id', how='left')
    targets['has_diabetes'] = targets['dm_onset_date'].notna().astype(int)
    
    # Target 3: Cardiovascular event
    cvd_codes = ['22298006', '410429000', '429007001', '88805009', '84114007']
    cvd_onset = cond_onset[cond_onset['condition_code'].isin(cvd_codes)]
    cvd_onset = cvd_onset.groupby('patient_id')['onset_date'].min().reset_index()
    cvd_onset = cvd_onset.rename(columns={'onset_date': 'cvd_onset_date'})
    targets = targets.merge(cvd_onset, on='patient_id', how='left')
    targets['has_cvd_event'] = targets['cvd_onset_date'].notna().astype(int)
    
    # Temporal split
    enc_temporal = enc_cond.groupby('patient_id')['encounter_start'].agg(['min', 'max']).reset_index()
    enc_temporal.columns = ['patient_id', 'first_encounter', 'last_encounter']
    enc_temporal['first_encounter'] = pd.to_datetime(enc_temporal['first_encounter']).dt.tz_localize(None)
    enc_temporal['last_encounter'] = pd.to_datetime(enc_temporal['last_encounter']).dt.tz_localize(None)
    targets = targets.merge(enc_temporal, on='patient_id', how='left')
    
    targets['train_period'] = targets['first_encounter'] < CUTOFF_DATE
    
    print("\nTarget distributions:")
    for col in ['has_hypertension', 'has_diabetes', 'has_cvd_event']:
        pos = targets[col].sum()
        print(f"  {col}: {pos} positive ({pos/500*100:.1f}%)")
    
    return targets

def prepare_model_data(features, targets, target_col, temporal_split=True):
    """Prepare data for modeling."""
    print(f"\nPreparing data for target: {target_col}")
    
    # Remove target condition indicator from features to prevent leakage
    target_condition_map = {
        'has_hypertension': ['has_hypertension'],
        'has_diabetes': ['has_diabetes', 'has_prediabetes'],
        'has_cvd_event': ['has_hypertension', 'has_heart_failure', 'has_coronary_heart_disease', 
                          'has_myocardial_infarction', 'has_cardiac_arrest', 'has_stroke']
    }
    
    features_clean = features.copy()
    cols_to_drop = target_condition_map.get(target_col, [])
    for col in cols_to_drop:
        if col in features_clean.columns:
            features_clean = features_clean.drop(columns=[col])
    
    print(f"Dropped leakage features: {cols_to_drop}")
    print(f"Features columns after cleanup: {features_clean.columns.tolist()}")
    print(f"Targets columns: {targets.columns.tolist()}")
    
    # Merge features and targets
    target_cols_to_merge = [c for c in ['patient_id', target_col, 'train_period', 'first_encounter'] if c in targets.columns]
    print(f"Merging columns: {target_cols_to_merge}")
    
    data = features_clean.merge(targets[target_cols_to_merge], on='patient_id', how='inner')
    print(f"Merged data shape: {data.shape}")
    
    # Define feature columns
    id_cols = ['patient_id', 'GENDER', 'RACE', 'ETHNICITY', 'MARITAL']
    target_cols = [target_col, 'train_period', 'first_encounter']
    feature_cols = [c for c in data.columns if c not in id_cols + target_cols]
    
    X = data[feature_cols].copy()
    y = data[target_col].copy()
    
    # Handle missing values
    X = X.fillna(0)
    
    if temporal_split and 'train_period' in data.columns:
        # Temporal split
        train_mask = data['train_period'] == True
        X_train, X_test = X[train_mask], X[~train_mask]
        y_train, y_test = y[train_mask], y[~train_mask]
    else:
        # Random split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=RANDOM_SEED, stratify=y
        )
    
    print(f"Train set: {len(X_train)} samples, {y_train.sum()} positive ({y_train.mean()*100:.1f}%)")
    print(f"Test set: {len(X_test)} samples, {y_test.sum()} positive ({y_test.mean()*100:.1f}%)")
    
    return X_train, X_test, y_train, y_test, feature_cols

def train_and_evaluate_models(X_train, X_test, y_train, y_test, feature_cols, target_name):
    """Train and evaluate multiple models."""
    print("\n" + "=" * 70)
    print(f"TRAINING MODELS FOR: {target_name}")
    print("=" * 70)
    
    results = []
    
    # 1. Majority Class Baseline
    print("\n--- Majority Class Baseline ---")
    majority_pred = np.zeros(len(y_test))
    majority_acc = np.mean(majority_pred == y_test)
    print(f"Accuracy: {majority_acc:.3f}")
    results.append({
        'model': 'Majority Baseline',
        'accuracy': majority_acc,
        'precision': 0.0,
        'recall': 0.0,
        'f1': 0.0,
        'roc_auc': 0.5,
        'pr_auc': y_test.mean()
    })
    
    # 2. Logistic Regression
    print("\n--- Logistic Regression ---")
    lr_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=RANDOM_SEED))
    ])
    
    lr_pipeline.fit(X_train, y_train)
    lr_pred = lr_pipeline.predict(X_test)
    lr_proba = lr_pipeline.predict_proba(X_test)[:, 1]
    
    lr_roc_auc = roc_auc_score(y_test, lr_proba)
    lr_pr_auc = average_precision_score(y_test, lr_proba)
    lr_f1 = f1_score(y_test, lr_pred, zero_division=0)
    lr_precision = precision_score(y_test, lr_pred, zero_division=0)
    lr_recall = recall_score(y_test, lr_pred, zero_division=0)
    
    print(f"Accuracy: {np.mean(lr_pred == y_test):.3f}")
    print(f"Precision: {lr_precision:.3f}, Recall: {lr_recall:.3f}, F1: {lr_f1:.3f}")
    print(f"ROC-AUC: {lr_roc_auc:.3f}, PR-AUC: {lr_pr_auc:.3f}")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, lr_pred))
    
    results.append({
        'model': 'Logistic Regression',
        'accuracy': np.mean(lr_pred == y_test),
        'precision': lr_precision,
        'recall': lr_recall,
        'f1': lr_f1,
        'roc_auc': lr_roc_auc,
        'pr_auc': lr_pr_auc
    })
    
    # 3. Random Forest
    print("\n--- Random Forest ---")
    rf_model = RandomForestClassifier(n_estimators=200, max_depth=10, 
                                       class_weight='balanced', random_state=RANDOM_SEED)
    rf_model.fit(X_train, y_train)
    rf_pred = rf_model.predict(X_test)
    rf_proba = rf_model.predict_proba(X_test)[:, 1]
    
    rf_roc_auc = roc_auc_score(y_test, rf_proba)
    rf_pr_auc = average_precision_score(y_test, rf_proba)
    rf_f1 = f1_score(y_test, rf_pred, zero_division=0)
    rf_precision = precision_score(y_test, rf_pred, zero_division=0)
    rf_recall = recall_score(y_test, rf_pred, zero_division=0)
    
    print(f"Accuracy: {np.mean(rf_pred == y_test):.3f}")
    print(f"Precision: {rf_precision:.3f}, Recall: {rf_recall:.3f}, F1: {rf_f1:.3f}")
    print(f"ROC-AUC: {rf_roc_auc:.3f}, PR-AUC: {rf_pr_auc:.3f}")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, rf_pred))
    
    # Feature importance
    print("\nTop 10 Feature Importances (Random Forest):")
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)
    print(feature_importance.head(10).to_string(index=False))
    
    results.append({
        'model': 'Random Forest',
        'accuracy': np.mean(rf_pred == y_test),
        'precision': rf_precision,
        'recall': rf_recall,
        'f1': rf_f1,
        'roc_auc': rf_roc_auc,
        'pr_auc': rf_pr_auc
    })
    
    # 4. XGBoost
    print("\n--- XGBoost ---")
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum() if y_train.sum() > 0 else 1
    
    xgb_model = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        scale_pos_weight=scale_pos_weight, random_state=RANDOM_SEED,
        eval_metric='logloss'
    )
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)
    xgb_proba = xgb_model.predict_proba(X_test)[:, 1]
    
    xgb_roc_auc = roc_auc_score(y_test, xgb_proba)
    xgb_pr_auc = average_precision_score(y_test, xgb_proba)
    xgb_f1 = f1_score(y_test, xgb_pred, zero_division=0)
    xgb_precision = precision_score(y_test, xgb_pred, zero_division=0)
    xgb_recall = recall_score(y_test, xgb_pred, zero_division=0)
    
    print(f"Accuracy: {np.mean(xgb_pred == y_test):.3f}")
    print(f"Precision: {xgb_precision:.3f}, Recall: {xgb_recall:.3f}, F1: {xgb_f1:.3f}")
    print(f"ROC-AUC: {xgb_roc_auc:.3f}, PR-AUC: {xgb_pr_auc:.3f}")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, xgb_pred))
    
    # Feature importance
    print("\nTop 10 Feature Importances (XGBoost):")
    xgb_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': xgb_model.feature_importances_
    }).sort_values('importance', ascending=False)
    print(xgb_importance.head(10).to_string(index=False))
    
    results.append({
        'model': 'XGBoost',
        'accuracy': np.mean(xgb_pred == y_test),
        'precision': xgb_precision,
        'recall': xgb_recall,
        'f1': xgb_f1,
        'roc_auc': xgb_roc_auc,
        'pr_auc': xgb_pr_auc
    })
    
    # Summary
    results_df = pd.DataFrame(results)
    print("\n" + "=" * 70)
    print("MODEL COMPARISON SUMMARY")
    print("=" * 70)
    print(results_df.to_string(index=False))
    
    # Save results
    results_df.to_csv(BASE / f"model_results_{target_name}.csv", index=False)
    feature_importance.to_csv(BASE / f"feature_importance_rf_{target_name}.csv", index=False)
    xgb_importance.to_csv(BASE / f"feature_importance_xgb_{target_name}.csv", index=False)
    
    return results_df, lr_pipeline, rf_model, xgb_model

# ============================================================
# SECTION 5: CROSS-VALIDATION
# ============================================================

def cross_validation_analysis(X, y, feature_cols, target_name):
    """Perform stratified cross-validation."""
    print("\n" + "=" * 70)
    print("CROSS-VALIDATION ANALYSIS")
    print("=" * 70)
    
    X_filled = X.fillna(0)
    
    # Logistic Regression CV
    lr_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=RANDOM_SEED))
    ])
    
    lr_scores = cross_val_score(lr_pipeline, X_filled, y, cv=5, scoring='roc_auc', verbose=0)
    print(f"\nLogistic Regression CV ROC-AUC: {lr_scores.mean():.3f} (+/- {lr_scores.std() * 2:.3f})")
    
    # Random Forest CV
    rf_model = RandomForestClassifier(n_estimators=200, max_depth=10, 
                                       class_weight='balanced', random_state=RANDOM_SEED)
    rf_scores = cross_val_score(rf_model, X_filled, y, cv=5, scoring='roc_auc', verbose=0)
    print(f"Random Forest CV ROC-AUC: {rf_scores.mean():.3f} (+/- {rf_scores.std() * 2:.3f})")
    
    # XGBoost CV
    scale_pos_weight = (y == 0).sum() / (y == 1).sum() if y.sum() > 0 else 1
    xgb_model = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        scale_pos_weight=scale_pos_weight, random_state=RANDOM_SEED,
        eval_metric='logloss'
    )
    xgb_scores = cross_val_score(xgb_model, X_filled, y, cv=5, scoring='roc_auc', verbose=0)
    print(f"XGBoost CV ROC-AUC: {xgb_scores.mean():.3f} (+/- {xgb_scores.std() * 2:.3f})")
    
    return {
        'lr_mean': lr_scores.mean(),
        'lr_std': lr_scores.std(),
        'rf_mean': rf_scores.mean(),
        'rf_std': rf_scores.std(),
        'xgb_mean': xgb_scores.mean(),
        'xgb_std': xgb_scores.std()
    }

# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SYNTHEA HEALTHCARE ANALYTICS - STATISTICAL ANALYSIS & CLASSICAL ML")
    print("=" * 70)
    
    # Load data
    patient_props, cond_props, enc_props, med_props, enc_cond = load_data()
    
    # Build condition sets
    condition_sets = {}
    for _, row in cond_props.iterrows():
        pid = row['patient_id']
        code = row['CODE']
        if pid not in condition_sets:
            condition_sets[pid] = set()
        condition_sets[pid].add(code)
    
    # Section 1: Comorbidity Analysis
    jaccard_df, lift_df, chi2_df, condition_sets = comorbidity_analysis(cond_props)
    
    # Section 2: Demographic Analysis
    demo_df = demographic_analysis(patient_props, cond_props, condition_sets)
    
    # Section 3: Medication-Condition Analysis
    med_cond_df = medication_condition_analysis(med_props, cond_props, condition_sets)
    
    # Section 4: Build feature matrix
    features = build_feature_matrix(patient_props, cond_props, enc_props, med_props, condition_sets)
    
    # Define targets
    targets = define_targets(features, enc_cond)
    
    # Save feature matrix and targets
    features.to_csv(BASE / "patient_features_final.csv", index=False)
    targets.to_csv(BASE / "prediction_targets_final.csv", index=False)
    
    # Section 5: ML for Hypertension (best balanced target)
    print("\n" + "=" * 70)
    print("PRIMARY PREDICTION TASK: FUTURE HYPERTENSION")
    print("=" * 70)
    
    X_train, X_test, y_train, y_test, feature_cols = prepare_model_data(
        features, targets, 'has_hypertension', temporal_split=True
    )
    
    results_htn, lr_model, rf_model, xgb_model = train_and_evaluate_models(
        X_train, X_test, y_train, y_test, feature_cols, 'hypertension'
    )
    
    # Cross-validation
    X_full = pd.concat([X_train, X_test])
    y_full = pd.concat([y_train, y_test])
    cv_results = cross_validation_analysis(X_full, y_full, feature_cols, 'hypertension')
    
    # Section 6: Secondary target - Cardiovascular Event
    print("\n" + "=" * 70)
    print("SECONDARY PREDICTION TASK: FUTURE CARDIOVASCULAR EVENT")
    print("=" * 70)
    
    X_train_cvd, X_test_cvd, y_train_cvd, y_test_cvd, feature_cols_cvd = prepare_model_data(
        features, targets, 'has_cvd_event', temporal_split=True
    )
    
    results_cvd, _, _, _ = train_and_evaluate_models(
        X_train_cvd, X_test_cvd, y_train_cvd, y_test_cvd, feature_cols_cvd, 'cvd'
    )
    
    print("\n" + "=" * 70)
    print("STEP 5 COMPLETE: STATISTICAL ANALYSIS & CLASSICAL ML")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - comorbidity_jaccard.csv")
    print("  - comorbidity_lift.csv")
    print("  - comorbidity_chi2.csv")
    print("  - demographic_associations.csv")
    print("  - medication_condition_associations.csv")
    print("  - patient_features_final.csv")
    print("  - prediction_targets_final.csv")
    print("  - model_results_hypertension.csv")
    print("  - model_results_cvd.csv")
    print("  - feature_importance_rf_hypertension.csv")
    print("  - feature_importance_xgb_hypertension.csv")
