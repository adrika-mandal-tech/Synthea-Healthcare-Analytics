"""
Generate comprehensive clinical findings from Synthea dataset
Similar in style to practical_findings.md but with MORE diseases, relations, ratios, probabilities
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE = Path("/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics")
EXPORT_DIR = BASE / "Synthea_Real_Export"
GDS_DIR = BASE / "Synthea-GDS"

# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    # Patients
    patients = pd.read_csv(EXPORT_DIR / "patients.csv")
    patients['props'] = patients['properties'].apply(json.loads)
    patient_props = pd.json_normalize(patients['props'])
    patient_props['patient_id'] = patients['node_id']
    
    # Conditions
    conditions = pd.read_csv(EXPORT_DIR / "patient_condition.csv")
    conditions['props'] = conditions['condition_properties'].apply(json.loads)
    cond_props = pd.json_normalize(conditions['props'])
    cond_props['patient_id'] = conditions['patient_id']
    cond_props['condition_id'] = conditions['condition_id']
    
    # Encounters
    encounters = pd.read_csv(EXPORT_DIR / "patient_encounter.csv")
    encounters['props'] = encounters['encounter_properties'].apply(json.loads)
    enc_props = pd.json_normalize(encounters['props'])
    enc_props['patient_id'] = encounters['patient_id']
    enc_props['START'] = pd.to_datetime(enc_props['START'])
    
    # Medications
    meds = pd.read_csv(EXPORT_DIR / "patient_medication.csv")
    meds['props'] = meds['medication_properties'].apply(json.loads)
    med_props = pd.json_normalize(meds['props'])
    med_props['patient_id'] = meds['patient_id']
    
    # Temporal encounter-condition data
    enc_cond = pd.read_csv(EXPORT_DIR / "encounter_condition_temporal.csv")
    enc_cond['encounter_start'] = pd.to_datetime(enc_cond['encounter_start'])
    enc_cond['condition_code'] = enc_cond['condition_code'].astype(str)
    
    return patient_props, cond_props, enc_props, med_props, enc_cond

# ============================================================
# BUILD CONDITION SETS
# ============================================================

def build_condition_sets(cond_props):
    condition_sets = {}
    for _, row in cond_props.iterrows():
        pid = row['patient_id']
        code = str(row['CODE'])
        if pid not in condition_sets:
            condition_sets[pid] = set()
        condition_sets[pid].add(code)
    return condition_sets

def build_condition_to_patients(condition_sets):
    cond_to_patients = {}
    for pid, conds in condition_sets.items():
        for code in conds:
            if code not in cond_to_patients:
                cond_to_patients[code] = set()
            cond_to_patients[code].add(pid)
    return cond_to_patients

# ============================================================
# FINDING GENERATORS
# ============================================================

def finding_1_total_diseases(cond_props, condition_sets):
    """Total diseases and prevalence analysis"""
    print("\n" + "=" * 80)
    print("FINDING 1: TOTAL DISEASES IN DATASET")
    print("=" * 80)
    
    total_conditions = len(cond_props)
    unique_conditions = cond_props['CODE'].nunique()
    patients_with_conditions = len(condition_sets)
    total_patients = 500
    
    print(f"\nTotal condition codes in dataset: {unique_conditions}")
    print(f"Total patient-condition pairs: {total_conditions}")
    print(f"Patients with at least one condition: {patients_with_conditions}/{total_patients} ({patients_with_conditions/total_patients*100:.1f}%)")
    print(f"Patients with NO conditions: {total_patients - patients_with_conditions}")
    
    # ALL conditions sorted by prevalence
    cond_meta = cond_props.groupby(['CODE', 'DESCRIPTION']).size().reset_index(name='count')
    cond_meta = cond_meta.sort_values('count', ascending=False)
    cond_meta['prevalence'] = cond_meta['count'] / total_patients * 100
    
    print(f"\nALL {unique_conditions} CONDITIONS BY PREVALENCE:")
    print(cond_meta.to_string(index=False))
    
    cond_meta.to_csv(BASE / "all_conditions_prevalence.csv", index=False)
    
    return cond_meta

def finding_2_comorbidity_probabilities(cond_props, condition_sets, cond_to_patients):
    """Comprehensive comorbidity analysis with conditional probabilities"""
    print("\n" + "=" * 80)
    print("FINDING 2: COMORBIDITY PROBABILITIES & RISK RATIOS")
    print("=" * 80)
    
    total_patients = 500
    condition_to_desc = dict(zip(cond_props['CODE'].astype(str), cond_props['DESCRIPTION']))
    
    # Get all condition codes
    all_codes = list(cond_to_patients.keys())
    
    # Calculate all pairwise metrics
    results = []
    
    for i, code_a in enumerate(all_codes):
        for code_b in all_codes[i+1:]:
            patients_a = cond_to_patients.get(code_a, set())
            patients_b = cond_to_patients.get(code_b, set())
            
            both = patients_a & patients_b
            a_only = patients_a - patients_b
            b_only = patients_b - patients_a
            neither = set(condition_sets.keys()) - patients_a - patients_b
            
            n_a = len(patients_a)
            n_b = len(patients_b)
            n_both = len(both)
            n_a_only = len(a_only)
            n_b_only = len(b_only)
            n_neither = len(neither)
            
            if n_a == 0 or n_b == 0:
                continue
            
            # Probabilities
            p_a = n_a / total_patients
            p_b = n_b / total_patients
            p_both = n_both / total_patients
            p_a_given_b = n_both / n_b if n_b > 0 else 0
            p_b_given_a = n_both / n_a if n_a > 0 else 0
            
            # Lift
            lift = p_both / (p_a * p_b) if (p_a * p_b) > 0 else 0
            
            # Odds ratio
            if n_a_only > 0 and n_b_only > 0 and n_neither > 0:
                odds_ratio = (n_both * n_neither) / (len(a_only) * len(b_only))
            else:
                odds_ratio = float('inf') if n_both > 0 else 0
            
            # Relative risk
            denominator = (total_patients - n_a)
            rr = (n_both / n_a) / (len(b_only) / denominator) if n_a > 0 and denominator > 0 and len(b_only) > 0 else 0
            
            # Only include meaningful relationships
            if n_both >= 3 and (lift > 1.2 or p_a_given_b > 0.3 or p_b_given_a > 0.3):
                results.append({
                    'condition_a': condition_to_desc.get(code_a, code_a),
                    'condition_b': condition_to_desc.get(code_b, code_b),
                    'code_a': code_a,
                    'code_b': code_b,
                    'patients_a': n_a,
                    'patients_b': n_b,
                    'patients_both': n_both,
                    'prevalence_a': p_a * 100,
                    'prevalence_b': p_b * 100,
                    'p_a_given_b': p_a_given_b * 100,
                    'p_b_given_a': p_b_given_a * 100,
                    'lift': lift,
                    'odds_ratio': odds_ratio if odds_ratio != float('inf') else 9999,
                    'relative_risk': rr
                })
    
    df = pd.DataFrame(results)
    df = df.sort_values('lift', ascending=False)
    
    print(f"\nFound {len(df)} meaningful condition pairs")
    print("\nTop 30 by Lift:")
    print(df.head(30)[['condition_a', 'condition_b', 'patients_both', 'lift', 'p_a_given_b', 'p_b_given_a']].to_string(index=False))
    
    df.to_csv(BASE / "comorbidity_probabilities.csv", index=False)
    return df

def finding_3_disease_progression_chains(enc_cond, condition_sets):
    """Disease progression chains using temporal data"""
    print("\n" + "=" * 80)
    print("FINDING 3: DISEASE PROGRESSION CHAINS")
    print("=" * 80)
    
    # Get first onset date for each condition per patient
    cond_onset = enc_cond.groupby(['patient_id', 'condition_code'])['encounter_start'].min().reset_index()
    cond_onset = cond_onset.rename(columns={'encounter_start': 'onset_date'})
    
    # Define progression chains to investigate
    chains = [
        ('Obesity', '162864005', 'Prediabetes', '15777000'),
        ('Obesity', '162864005', 'Diabetes', '44054006'),
        ('Prediabetes', '15777000', 'Diabetes', '44054006'),
        ('Hypertension', '59621000', 'Heart failure', '88805009'),
        ('Hypertension', '59621000', 'Myocardial Infarction', '22298006'),
        ('Hypertension', '59621000', 'Cardiac Arrest', '410429000'),
        ('COVID-19', '840539006', 'Pneumonia', '233604007'),
        ('COVID-19', '840539006', 'ARDS', '67782005'),
        ('COVID-19', '840539006', 'Respiratory distress', '271825005'),
        ('COVID-19', '840539006', 'Acute respiratory failure', '65710008'),
        ('Prediabetes', '15777000', 'Hyperlipidemia', '55822004'),
        ('Obesity', '162864005', 'Hyperlipidemia', '55822004'),
        ('Hypertension', '59621000', 'Stroke', '230690007'),
        ('Diabetes', '44054006', 'Kidney disease', '431855005'),
        ('Anemia', '271737000', 'Prediabetes', '15777000'),
    ]
    
    results = []
    
    for name_a, code_a, name_b, code_b in chains:
        patients_a = set()
        patients_b = set()
        patients_both = set()
        patients_a_only = set()
        patients_b_only = set()
        
        for pid, conds in condition_sets.items():
            has_a = code_a in conds
            has_b = code_b in conds
            
            if has_a and has_b:
                patients_both.add(pid)
            elif has_a:
                patients_a_only.add(pid)
            elif has_b:
                patients_b_only.add(pid)
            
            if has_a:
                patients_a.add(pid)
            if has_b:
                patients_b.add(pid)
        
        n_a = len(patients_a)
        n_b = len(patients_b)
        n_both = len(patients_both)
        n_a_only = len(patients_a_only)
        n_b_only = len(patients_b_only)
        
        if n_a == 0:
            continue
        
        # Progression rate: % of source patients who also have target
        progression_rate = n_both / n_a * 100 if n_a > 0 else 0
        
        # Temporal analysis
        temporal_both = 0
        temporal_a_before_b = 0
        avg_interval = []
        
        for pid in patients_both:
            a_dates = cond_onset[(cond_onset['patient_id'] == pid) & (cond_onset['condition_code'] == code_a)]
            b_dates = cond_onset[(cond_onset['patient_id'] == pid) & (cond_onset['condition_code'] == code_b)]
            
            if len(a_dates) > 0 and len(b_dates) > 0:
                a_date = a_dates['onset_date'].iloc[0]
                b_date = b_dates['onset_date'].iloc[0]
                
                if pd.notna(a_date) and pd.notna(b_date):
                    temporal_both += 1
                    if a_date < b_date:
                        temporal_a_before_b += 1
                        interval = (b_date - a_date).days
                        if interval >= 0:
                            avg_interval.append(interval)
        
        avg_interval_days = np.mean(avg_interval) if avg_interval else 0
        
        print(f"\n{name_a} → {name_b}:")
        print(f"  Source patients ({name_a}): {n_a}")
        print(f"  Target patients ({name_b}): {n_b}")
        print(f"  Both conditions: {n_both}")
        print(f"  Source only (at risk): {n_a_only}")
        print(f"  Progression rate: {progression_rate:.1f}%")
        if temporal_both > 0:
            print(f"  Temporal validation: {temporal_both} pairs with dates")
            print(f"  {name_a} before {name_b}: {temporal_a_before_b} ({temporal_a_before_b/temporal_both*100:.1f}%)")
            print(f"  Average interval: {avg_interval_days:.0f} days ({avg_interval_days/365.25:.1f} years)")
        
        results.append({
            'source': name_a,
            'source_code': code_a,
            'target': name_b,
            'target_code': code_b,
            'source_patients': n_a,
            'target_patients': n_b,
            'both': n_both,
            'source_only': n_a_only,
            'progression_rate': progression_rate,
            'temporal_pairs': temporal_both,
            'temporal_a_before_b': temporal_a_before_b,
            'avg_interval_days': avg_interval_days
        })
    
    df = pd.DataFrame(results)
    df = df.sort_values('progression_rate', ascending=False)
    print("\n\nPROGRESSION CHAIN SUMMARY:")
    print(df[['source', 'target', 'source_patients', 'both', 'progression_rate', 'temporal_a_before_b']].to_string(index=False))
    
    df.to_csv(BASE / "disease_progression_chains.csv", index=False)
    return df

def finding_4_rare_disease_patterns(cond_props, condition_sets, cond_to_patients):
    """Rare disease analysis and patterns"""
    print("\n" + "=" * 80)
    print("FINDING 4: RARE DISEASE PATTERNS")
    print("=" * 80)
    
    total_patients = 500
    condition_to_desc = dict(zip(cond_props['CODE'].astype(str), cond_props['DESCRIPTION']))
    
    # Find rare diseases (1-5 patients)
    rare_diseases = []
    for code, patients in cond_to_patients.items():
        if 1 <= len(patients) <= 5:
            rare_diseases.append({
                'code': code,
                'description': condition_to_desc.get(code, code),
                'count': len(patients),
                'prevalence': len(patients) / total_patients * 100
            })
    
    rare_df = pd.DataFrame(rare_diseases).sort_values('count', ascending=False)
    print(f"\nRare diseases (1-5 patients): {len(rare_df)} conditions")
    print(rare_df.to_string(index=False))
    
    # Find patients with multiple rare diseases
    print("\nPatients with 3+ rare diseases:")
    rare_codes = set(rare_df['code'].tolist())
    patients_with_multiple_rare = []
    
    for pid, conds in condition_sets.items():
        rare_count = len(conds & rare_codes)
        if rare_count >= 3:
            rare_conditions = [condition_to_desc.get(c, c) for c in (conds & rare_codes)]
            patients_with_multiple_rare.append({
                'patient_id': pid,
                'rare_count': rare_count,
                'rare_conditions': ', '.join(rare_conditions)
            })
    
    multi_rare_df = pd.DataFrame(patients_with_multiple_rare).sort_values('rare_count', ascending=False)
    print(multi_rare_df.head(20).to_string(index=False))
    
    rare_df.to_csv(BASE / "rare_diseases.csv", index=False)
    multi_rare_df.to_csv(BASE / "patients_with_multiple_rare_diseases.csv", index=False)
    
    return rare_df, multi_rare_df

def finding_5_condition_clusters(cond_props, condition_sets, cond_to_patients):
    """Condition clusters based on co-occurrence"""
    print("\n" + "=" * 80)
    print("FINDING 5: CONDITION CLUSTERS")
    print("=" * 80)
    
    condition_to_desc = dict(zip(cond_props['CODE'].astype(str), cond_props['DESCRIPTION']))
    
    # Find highly connected conditions (high average Jaccard with others)
    all_codes = list(cond_to_patients.keys())
    condition_connectivity = {}
    
    for code in all_codes:
        patients_code = cond_to_patients.get(code, set())
        if len(patients_code) < 3:
            continue
        
        jaccard_sum = 0
        count = 0
        for other_code in all_codes:
            if other_code == code:
                continue
            patients_other = cond_to_patients.get(other_code, set())
            intersection = len(patients_code & patients_other)
            union = len(patients_code | patients_other)
            jaccard = intersection / union if union > 0 else 0
            jaccard_sum += jaccard
            count += 1
        
        avg_jaccard = jaccard_sum / count if count > 0 else 0
        condition_connectivity[code] = avg_jaccard
    
    # Top connected conditions
    top_connected = sorted(condition_connectivity.items(), key=lambda x: x[1], reverse=True)[:30]
    
    print("\nMost 'connective' conditions (high average co-occurrence with other conditions):")
    for code, avg_jaccard in top_connected:
        desc = condition_to_desc.get(code, code)
        n_patients = len(cond_to_patients.get(code, set()))
        print(f"  {desc}: {n_patients} patients, avg Jaccard = {avg_jaccard:.3f}")
    
    # Find condition communities using simple threshold
    print("\nCondition clusters (Jaccard > 0.3):")
    clusters = []
    for code in all_codes:
        patients_code = cond_to_patients.get(code, set())
        if len(patients_code) < 5:
            continue
        
        cluster = [code]
        for other_code in all_codes:
            if other_code == code:
                continue
            patients_other = cond_to_patients.get(other_code, set())
            intersection = len(patients_code & patients_other)
            union = len(patients_code | patients_other)
            jaccard = intersection / union if union > 0 else 0
            if jaccard > 0.3:
                cluster.append(other_code)
        
        if len(cluster) >= 3:
            clusters.append(sorted(cluster))
    
    # Deduplicate clusters
    unique_clusters = []
    for c in clusters:
        if c not in unique_clusters:
            unique_clusters.append(c)
    
    for i, cluster in enumerate(unique_clusters[:15]):
        print(f"\n  Cluster {i+1} ({len(cluster)} conditions):")
        for code in cluster[:8]:
            desc = condition_to_desc.get(code, code)
            n = len(cond_to_patients.get(code, set()))
            print(f"    - {desc} ({n} patients)")
    
    return top_connected, unique_clusters

def finding_6_geographic_disease_patterns(patient_props, cond_props, condition_sets):
    """Geographic disease patterns"""
    print("\n" + "=" * 80)
    print("FINDING 6: GEOGRAPHIC DISEASE PATTERNS")
    print("=" * 80)
    
    condition_to_desc = dict(zip(cond_props['CODE'].astype(str), cond_props['DESCRIPTION']))
    
    # County-level analysis
    county_patients = defaultdict(set)
    for _, row in patient_props.iterrows():
        county = row.get('COUNTY', 'Unknown')
        county_patients[county].add(row['patient_id'])
    
    # Key conditions by county
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
    
    for county, patients in county_patients.items():
        if len(patients) < 5:
            continue
        
        for cond_name, cond_code in key_conditions.items():
            cond_patients = set()
            for pid in patients:
                if pid in condition_sets and cond_code in condition_sets[pid]:
                    cond_patients.add(pid)
            
            if len(cond_patients) > 0:
                results.append({
                    'county': county,
                    'condition': cond_name,
                    'patients_with_condition': len(cond_patients),
                    'total_patients_in_county': len(patients),
                    'prevalence': len(cond_patients) / len(patients) * 100
                })
    
    df = pd.DataFrame(results)
    
    print("\nDisease prevalence by county:")
    for cond_name in key_conditions.keys():
        cond_df = df[df['condition'] == cond_name].sort_values('prevalence', ascending=False)
        print(f"\n{cond_name}:")
        for _, row in cond_df.head(5).iterrows():
            print(f"  {row['county']}: {row['patients_with_condition']}/{row['total_patients_in_county']} ({row['prevalence']:.1f}%)")
    
    df.to_csv(BASE / "geographic_disease_patterns.csv", index=False)
    return df

def finding_7_medication_comorbidity_gaps(med_props, cond_props, condition_sets, cond_to_patients):
    """Medication gaps and unusual prescribing patterns"""
    print("\n" + "=" * 80)
    print("FINDING 7: MEDICATION COMORBIDITY GAPS")
    print("=" * 80)
    
    condition_to_desc = dict(zip(cond_props['CODE'].astype(str), cond_props['DESCRIPTION']))
    
    # Medication classes
    med_classes = {
        'Antihypertensives': ['hydrochlorothiazide', 'atenolol', 'amlodipine', 'metoprolol', 
                              'furosemide', 'lisinopril', 'losartan', 'verapamil', 'digoxin', 
                              'nitroglycerin', 'warfarin'],
        'Diabetes medications': ['metformin', 'insulin', 'glipizide', 'glyburide', 'pioglitazone', 'sitagliptin'],
        'Lipid-lowering': ['simvastatin', 'atorvastatin', 'rosuvastatin', 'pravastatin', 'lovastatin'],
        'Respiratory': ['albuterol', 'fluticasone', 'prednisone', 'montelukast'],
    }
    
    results = []
    
    for med_class, keywords in med_classes.items():
        meds_filtered = med_props[med_props['DESCRIPTION'].str.contains('|'.join(keywords), case=False, na=False)]
        med_patients = set(meds_filtered['patient_id'])
        
        for cond_code, cond_patients in cond_to_patients.items():
            cond_name = condition_to_desc.get(cond_code, cond_code)
            
            # Patients with condition but NO medication
            cond_no_med = cond_patients - med_patients
            
            # Patients with medication but NO condition
            med_no_cond = med_patients - cond_patients
            
            if len(cond_patients) >= 5:
                coverage_rate = (len(cond_patients) - len(cond_no_med)) / len(cond_patients) * 100
                
                if coverage_rate < 100 or len(med_no_cond) > 0:
                    results.append({
                        'medication_class': med_class,
                        'condition': cond_name,
                        'condition_code': cond_code,
                        'patients_with_condition': len(cond_patients),
                        'patients_with_medication': len(cond_patients & med_patients),
                        'patients_without_medication': len(cond_no_med),
                        'coverage_rate': coverage_rate,
                        'patients_with_med_but_no_diagnosis': len(med_no_cond)
                    })
    
    df = pd.DataFrame(results)
    df = df.sort_values(['medication_class', 'coverage_rate'], ascending=[True, False])
    
    print("\nMedication coverage gaps:")
    for med_class in med_classes.keys():
        class_df = df[df['medication_class'] == med_class]
        if len(class_df) > 0:
            print(f"\n{med_class}:")
            for _, row in class_df.head(5).iterrows():
                print(f"  {row['condition']}: {row['coverage_rate']:.1f}% coverage ({row['patients_without_medication']} without medication)")
    
    df.to_csv(BASE / "medication_gaps.csv", index=False)
    return df

def finding_8_payer_condition_patterns(enc_props, cond_props, condition_sets):
    """Payer-condition patterns"""
    print("\n" + "=" * 80)
    print("FINDING 8: PAYER-CONDITION PATTERNS")
    print("=" * 80)
    
    # Need to join encounters with conditions via patient + date
    # For now, use patient-level analysis
    
    # This would require joining encounter conditions with payer info
    # Simplified: analyze condition prevalence by patient payer
    
    print("\nPayer analysis requires encounter-condition-payer join.")
    print("See Synthea-GDS reports for existing payer analysis.")
    
    return None

def finding_9_temporal_analysis(enc_cond, condition_sets):
    """Temporal patterns in condition onset"""
    print("\n" + "=" * 80)
    print("FINDING 9: TEMPORAL CONDITION PATTERNS")
    print("=" * 80)
    
    cond_onset = enc_cond.groupby(['patient_id', 'condition_code'])['encounter_start'].min().reset_index()
    cond_onset = cond_onset.rename(columns={'encounter_start': 'onset_date'})
    
    # Convert to datetime
    cond_onset['onset_date'] = pd.to_datetime(cond_onset['onset_date'])
    
    # Year distribution of condition onset
    cond_onset['year'] = cond_onset['onset_date'].dt.year
    
    key_conditions = {
        'Obesity': '162864005',
        'Prediabetes': '15777000',
        'Diabetes': '44054006',
        'Hypertension': '59621000',
        'COVID-19': '840539006',
    }
    
    results = []
    
    for cond_name, cond_code in key_conditions.items():
        cond_df = cond_onset[cond_onset['condition_code'] == cond_code]
        if len(cond_df) == 0:
            continue
        
        year_dist = cond_df['year'].value_counts().sort_index()
        
        print(f"\n{cond_name} onset by year:")
        for year, count in year_dist.head(10).items():
            print(f"  {year}: {count} patients")
        
        results.append({
            'condition': cond_name,
            'code': cond_code,
            'earliest_year': cond_df['year'].min(),
            'latest_year': cond_df['year'].max(),
            'peak_year': year_dist.idxmax(),
            'peak_count': year_dist.max()
        })
    
    df = pd.DataFrame(results)
    df.to_csv(BASE / "temporal_patterns.csv", index=False)
    return df

def finding_10_patient_complexity(patient_props, condition_sets, enc_props, med_props):
    """Patient complexity scores"""
    print("\n" + "=" * 80)
    print("FINDING 10: PATIENT COMPLEXITY ANALYSIS")
    print("=" * 80)
    
    # Calculate complexity metrics
    patient_complexity = []
    
    for pid in patient_props['patient_id']:
        conds = condition_sets.get(pid, set())
        n_conditions = len(conds)
        
        # Encounter count
        n_encounters = len(enc_props[enc_props['patient_id'] == pid])
        
        # Medication count
        n_meds = len(med_props[med_props['patient_id'] == pid])
        
        # Complexity score
        complexity = n_conditions * 0.4 + n_encounters * 0.3 + n_meds * 0.3
        
        patient_complexity.append({
            'patient_id': pid,
            'n_conditions': n_conditions,
            'n_encounters': n_encounters,
            'n_medications': n_meds,
            'complexity_score': complexity
        })
    
    df = pd.DataFrame(patient_complexity)
    df = df.sort_values('complexity_score', ascending=False)
    
    print("\nTop 20 most complex patients:")
    print(df.head(20)[['patient_id', 'n_conditions', 'n_encounters', 'n_medications', 'complexity_score']].to_string(index=False))
    
    print(f"\nComplexity distribution:")
    print(f"  Mean: {df['complexity_score'].mean():.1f}")
    print(f"  Median: {df['complexity_score'].median():.1f}")
    print(f"  Max: {df['complexity_score'].max():.1f}")
    print(f"  Std: {df['complexity_score'].std():.1f}")
    
    df.to_csv(BASE / "patient_complexity.csv", index=False)
    return df

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE CLINICAL FINDINGS GENERATOR")
    print("=" * 80)
    
    # Load data
    patient_props, cond_props, enc_props, med_props, enc_cond = load_data()
    
    # Build mappings
    condition_sets = build_condition_sets(cond_props)
    cond_to_patients = build_condition_to_patients(condition_sets)
    
    # Generate findings
    cond_meta = finding_1_total_diseases(cond_props, condition_sets)
    comorbidity_df = finding_2_comorbidity_probabilities(cond_props, condition_sets, cond_to_patients)
    progression_df = finding_3_disease_progression_chains(enc_cond, condition_sets)
    rare_df, multi_rare_df = finding_4_rare_disease_patterns(cond_props, condition_sets, cond_to_patients)
    top_connected, clusters = finding_5_condition_clusters(cond_props, condition_sets, cond_to_patients)
    geo_df = finding_6_geographic_disease_patterns(patient_props, cond_props, condition_sets)
    med_gaps_df = finding_7_medication_comorbidity_gaps(med_props, cond_props, condition_sets, cond_to_patients)
    temporal_df = finding_9_temporal_analysis(enc_cond, condition_sets)
    complexity_df = finding_10_patient_complexity(patient_props, condition_sets, enc_props, med_props)
    
    print("\n" + "=" * 80)
    print("ALL FINDINGS GENERATED")
    print("=" * 80)
    print("\nGenerated files:")
    print("  - all_conditions_prevalence.csv")
    print("  - comorbidity_probabilities.csv")
    print("  - disease_progression_chains.csv")
    print("  - rare_diseases.csv")
    print("  - patients_with_multiple_rare_diseases.csv")
    print("  - geographic_disease_patterns.csv")
    print("  - medication_gaps.csv")
    print("  - temporal_patterns.csv")
    print("  - patient_complexity.csv")
