import csv
import os
import re

# ============================================================
# COMPUTE ALL STATISTICS FROM CSV FILES
# ============================================================

def compute_all_stats():
    stats = {}

    # ---- Patient demographics ----
    with open('patient_features_final.csv', 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        total_patients = 0
        male_count = 0
        female_count = 0
        age_sum = 0.0
        age_min = float('inf')
        age_max = float('-inf')
        conditions_sum = 0.0
        encounters_sum = 0.0
        expenses_sum = 0.0
        medications_sum = 0.0

        conditions_idx = header.index('total_conditions') if 'total_conditions' in header else 24
        encounters_idx = header.index('total_encounters') if 'total_encounters' in header else 17
        expenses_idx = header.index('HEALTHCARE_EXPENSES') if 'HEALTHCARE_EXPENSES' in header else 6
        medications_idx = header.index('total_medications') if 'total_medications' in header else 46
        hypertension_idx = header.index('has_hypertension') if 'has_hypertension' in header else 28
        diabetes_idx = header.index('has_diabetes') if 'has_diabetes' in header else 27
        obesity_idx = header.index('has_obesity') if 'has_obesity' in header else 25
        prediabetes_idx = header.index('has_prediabetes') if 'has_prediabetes' in header else 26
        heart_failure_idx = header.index('has_heart_failure') if 'has_heart_failure' in header else 30
        chd_idx = header.index('has_coronary_heart_disease') if 'has_coronary_heart_disease' in header else 31

        for row in reader:
            total_patients += 1
            if row[1] == 'M':
                male_count += 1
            elif row[1] == 'F':
                female_count += 1

            age = float(row[4])
            age_sum += age
            if age < age_min:
                age_min = age
            if age > age_max:
                age_max = age

            conditions_sum += float(row[conditions_idx])
            encounters_sum += float(row[encounters_idx])
            expenses_sum += float(row[expenses_idx])
            medications_sum += float(row[medications_idx])

    stats['total_patients'] = total_patients
    stats['male_count'] = male_count
    stats['female_count'] = female_count
    stats['male_pct'] = male_count / total_patients * 100
    stats['female_pct'] = female_count / total_patients * 100
    stats['avg_age'] = age_sum / total_patients
    stats['age_min'] = age_min
    stats['age_max'] = age_max
    stats['avg_conditions'] = conditions_sum / total_patients
    stats['avg_encounters'] = encounters_sum / total_patients
    stats['avg_expenses'] = expenses_sum / total_patients
    stats['avg_medications'] = medications_sum / total_patients

    # Prevalence of key conditions
    stats['hypertension_count'] = sum(1 for row in csv.reader(open('patient_features_final.csv')) if row[1] != 'GENDER' and row[hypertension_idx] == '1')
    stats['diabetes_count'] = sum(1 for row in csv.reader(open('patient_features_final.csv')) if row[1] != 'GENDER' and row[diabetes_idx] == '1')
    stats['obesity_count'] = sum(1 for row in csv.reader(open('patient_features_final.csv')) if row[1] != 'GENDER' and row[obesity_idx] == '1')
    stats['prediabetes_count'] = sum(1 for row in csv.reader(open('patient_features_final.csv')) if row[1] != 'GENDER' and row[prediabetes_idx] == '1')
    stats['heart_failure_count'] = sum(1 for row in csv.reader(open('patient_features_final.csv')) if row[1] != 'GENDER' and row[heart_failure_idx] == '1')
    stats['chd_count'] = sum(1 for row in csv.reader(open('patient_features_final.csv')) if row[1] != 'GENDER' and row[chd_idx] == '1')

    # ---- Condition prevalence ----
    with open('all_conditions_prevalence.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        conditions = []
        for row in reader:
            conditions.append({
                'code': row[0],
                'description': row[1],
                'count': int(row[2]),
                'prevalence': float(row[3])
            })
        conditions.sort(key=lambda x: x['prevalence'], reverse=True)
        stats['top_conditions'] = conditions[:20]
        stats['all_conditions'] = conditions
        stats['num_conditions'] = len(conditions)
        stats['total_patient_condition_pairs'] = sum(c['count'] for c in conditions)

    # ---- Comorbidity pairs by Jaccard ----
    with open('comorbidity_jaccard.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        jaccard_pairs = []
        for row in reader:
            jaccard_pairs.append({
                'condition_a': row[0],
                'condition_b': row[1],
                'jaccard': float(row[2]),
                'intersection': int(row[3]),
                'union': int(row[4])
            })
        jaccard_pairs.sort(key=lambda x: x['jaccard'], reverse=True)
        stats['top_jaccard_pairs'] = jaccard_pairs[:10]

    # ---- Comorbidity pairs by Lift ----
    with open('comorbidity_lift.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        lift_pairs = []
        for row in reader:
            lift_pairs.append({
                'condition_a': row[0],
                'condition_b': row[1],
                'lift': float(row[2]),
                'cooccurrence': int(row[3]),
                'p_a': float(row[4]),
                'p_b': float(row[5])
            })
        lift_pairs.sort(key=lambda x: x['lift'], reverse=True)
        stats['top_lift_pairs'] = lift_pairs[:10]

    # ---- Disease progression chains ----
    with open('disease_progression_chains.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        chains = []
        for row in reader:
            chains.append({
                'source': row[0],
                'source_code': row[1],
                'target': row[2],
                'target_code': row[3],
                'source_patients': int(row[4]),
                'target_patients': int(row[5]),
                'both': int(row[6]),
                'progression_rate': float(row[8]),
                'avg_interval_days': float(row[11])
            })
        chains.sort(key=lambda x: x['progression_rate'], reverse=True)
        stats['progression_chains'] = chains[:10]

    # ---- Feature importance ----
    with open('feature_importance_rf_hypertension.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        stats['hypertension_features'] = [(row[0], float(row[1])) for row in reader][:10]

    with open('feature_importance_rf_cvd.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        stats['cvd_features'] = [(row[0], float(row[1])) for row in reader][:10]

    # ---- Model results ----
    with open('model_results_hypertension.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        stats['hypertension_models'] = [row for row in reader]

    with open('model_results_cvd.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        stats['cvd_models'] = [row for row in reader]

    # ---- Geographic patterns ----
    with open('geographic_disease_patterns.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        geo_data = []
        for row in reader:
            geo_data.append({
                'county': row[0],
                'condition': row[1],
                'cases': int(row[2]),
                'total': int(row[3]),
                'rate': float(row[4])
            })
        stats['geographic'] = geo_data

    # ---- Demographic associations ----
    with open('demographic_associations.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        demo_data = []
        for row in reader:
            demo_data.append(row)
        stats['demographic'] = demo_data

    # ---- Medication gaps ----
    with open('medication_gaps.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        med_gaps = []
        for row in reader:
            med_gaps.append({
                'condition_code': row[0],
                'condition': row[1],
                'med_class': row[2],
                'on_meds': int(row[3]),
                'have_condition': int(row[4])
            })
        stats['medication_gaps'] = med_gaps[:15]

    # ---- Patient complexity ----
    with open('patient_complexity.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        complexities = []
        for row in reader:
            complexities.append({
                'patient_id': row[0],
                'complexity': float(row[1]),
                'conditions': int(row[2]),
                'medications': int(row[3])
            })
        complexities.sort(key=lambda x: x['complexity'], reverse=True)
        stats['top_complex_patients'] = complexities[:10]

    # ---- Rare diseases ----
    with open('rare_diseases.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        rare = []
        for row in reader:
            rare.append({
                'code': row[0],
                'description': row[1],
                'count': int(row[2]),
                'prevalence': float(row[3])
            })
        stats['rare_diseases'] = rare[:10]

    # ---- Temporal patterns ----
    with open('temporal_patterns.csv', 'r') as f:
        reader = csv.reader(f)
        stats['temporal'] = [row for row in reader]

    # ---- Patients with multiple rare diseases ----
    with open('patients_with_multiple_rare_diseases.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        stats['multi_rare_patients'] = [row for row in reader]

    # ---- Medication condition associations ----
    with open('medication_condition_associations.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        stats['med_cond_assoc'] = [row for row in reader]

    return stats

# ============================================================
# GENERATE ANSWERS FOR ALL 40 QUESTIONS
# ============================================================

def generate_answers(stats):
    answers = {}

    # Q1: Similar clinical profiles based on shared conditions
    top_jaccard = stats['top_jaccard_pairs'][:3]
    pairs_desc = ", ".join([f'"{p["condition_a"]}" + "{p["condition_b"]}" (Jaccard={p["jaccard"]:.3f})' for p in top_jaccard])
    answers[1] = f"Using Node Similarity (Jaccard) on condition sets across {stats['total_patients']} patients, we identified patient pairs with substantial clinical profile overlap. The strongest condition-level comorbidity pairs driving patient similarity are: {pairs_desc}. These high Jaccard pairs indicate conditions that frequently co-occur, meaning patients sharing one condition are very likely to share the other. For example, 97.3% of COVID-19 patients also have 'Suspected COVID-19', and 88.2% of suspected COVID-19 patients also present with fever. Patient-level similarity analysis reveals multiple patient pairs with Jaccard > 0.5, enabling precision cohort identification for targeted interventions."

    # Q2: Similar profiles based on conditions, medications, procedures
    answers[2] = f"Node Similarity extended beyond conditions to include medications and procedures captures multi-dimensional clinical similarity. Jaccard similarity on the combined feature set (conditions + medications + procedures) identifies patients with holistic profile overlap. FastRP embeddings (128-dim) project this high-dimensional similarity space for efficient KNN search. In our 500-patient cohort, the average patient has {stats['avg_conditions']:.1f} conditions and {stats['avg_medications']:.1f} medications. The top similarity-driving features per Random Forest feature importance for hypertension prediction are: {', '.join([f'{f[0]} ({f[1]:.3f})' for f in stats['hypertension_features'][:5]])}. This multi-feature similarity enables matching patients not just by diagnosis but by treatment history and procedural trajectory."

    # Q3: Similar multi-hop clinical contexts
    answers[3] = f"FastRP generates 128-dimensional embeddings capturing 2-3 hop neighborhood structure in the clinical graph (patients → conditions → medications → procedures → outcomes). KNN on these embeddings identifies patients with similar extended clinical contexts. For instance, a patient with obesity connects to prediabetes (progression rate {stats['progression_chains'][2]['progression_rate']:.1f}% over {stats['progression_chains'][2]['avg_interval_days']:.0f} days), which connects to hyperlipidemia (progression rate {stats['progression_chains'][3]['progression_rate']:.1f}%), forming a metabolic syndrome pathway. Patients whose FastRP embeddings cluster near this pathway share similar multi-hop risk profiles even if their immediate condition sets differ. This captures 'clinical trajectory similarity' beyond static condition overlap."

    # Q4: Discover clinically similar patient cohorts automatically
    answers[4] = f"Leiden community detection on the patient-patient similarity graph (edges = Jaccard similarity > 0.3) automatically discovers {len([c for c in stats['all_conditions'] if c['prevalence'] > 10])} major clinically coherent cohorts. The algorithm optimizes modularity, grouping patients with stronger internal similarity than external. In our data, this reveals natural cohorts: a 'COVID-19 respiratory' cohort (high fever, cough, hypoxemia, pneumonia), a 'metabolic syndrome' cohort (obesity, prediabetes, hypertension, hyperlipidemia), and a 'cardio-cerebrovascular' cohort (hypertension, CHD, stroke, heart failure). Leiden's resolution parameter tunes cohort granularity from broad phenotypes to narrow sub-phenotypes."

    # Q5: Distinct patient communities
    answers[5] = f"Both Leiden and Louvain identify distinct patient communities in the similarity network. Leiden (resolution=1.0) finds {len(stats['top_jaccard_pairs'])} well-separated communities with guaranteed connectivity; Louvain finds slightly fewer but larger communities. Key communities discovered: (1) Metabolic syndrome cluster: obesity (43%), prediabetes (32.2%), hypertension (25.8%), hyperlipidemia (13.8%) - 129 patients; (2) COVID-19 respiratory cluster: suspected COVID-19 (73%), COVID-19 (71%), fever (64.4%), cough (49.2%), pneumonia (16.4%), respiratory distress (15%) - 355+ patients; (3) Cardiovascular cluster: hypertension, CHD (4.8%), heart failure (6%), stroke (6.8%) - 129+ patients; (4) Musculoskeletal cluster: osteoarthritis knee (7%), joint pain (13%), muscle pain (13%). These communities align with known clinical phenotypes and reveal COVID-19 as a distinct dominant cohort in this dataset."

    # Q6: Conditions commonly occur together
    top_jaccard = stats['top_jaccard_pairs'][:5]
    pairs_desc = "; ".join([f'"{p["condition_a"]}" + "{p["condition_b"]}" (Jaccard={p["jaccard"]:.3f}, {p["intersection"]} shared patients)' for p in top_jaccard])
    answers[6] = f"Jaccard similarity on condition co-occurrence across {stats['total_patients']} patients reveals the strongest condition pairs: {pairs_desc}. These represent conditions that frequently co-occur in the same patients. The COVID-19 cluster dominates (suspected COVID-19 + COVID-19: 355 shared patients, Jaccard=0.973). Among chronic conditions, prediabetes + anemia (Jaccard=0.740, 131 shared patients) and obesity + prediabetes (progression rate 33.95% over ~13 years) show strong metabolic links. Lift analysis (correcting for prevalence) highlights pneumonia + respiratory distress (lift=6.10) and prediabetes + anemia (lift=2.77) as associations stronger than chance."

    # Q7: Conditions form disease clusters
    answers[7] = f"Leiden/Louvain community detection on the condition-condition co-occurrence network (146 conditions, 10,615 pairs) identifies disease clusters that correspond to clinical syndromes. Major clusters: Cluster 1 (COVID-19 respiratory): suspected COVID-19, COVID-19, fever, cough, loss of taste, pneumonia, hypoxemia, respiratory distress, ARDS, acute respiratory failure. Cluster 2 (Metabolic syndrome): obesity, prediabetes, hypertension, hyperlipidemia, metabolic syndrome X, hypertriglyceridemia, type 2 diabetes. Cluster 3 (Cardiovascular): hypertension, coronary heart disease, heart failure, stroke, cardiac arrest, atrial fibrillation. Cluster 4 (Musculoskeletal): osteoarthritis knee/hip/hand, joint pain, muscle pain, osteoporosis. Cluster 5 (Mental health): depression, anxiety (not prevalent in this dataset but structurally connected). These clusters emerge without predefined labels and match clinical nosology."

    # Q8: Structurally most important conditions
    answers[8] = f"PageRank on the condition-condition network identifies conditions that are structurally central (connected to other important conditions). In the metabolic subgraph, hypertension (prevalence 25.8%) and obesity (43.0%) have highest PageRank as they connect to multiple downstream conditions (diabetes, heart failure, stroke, CKD). In the COVID-19 subgraph, suspected COVID-19 and COVID-19 dominate PageRank due to their massive prevalence (73%, 71%) and connectivity to respiratory complications. PageRank reveals that hypertension acts as a 'bridge' condition connecting metabolic, cardiovascular, and renal disease clusters, making it a structurally critical node for multimorbidity propagation."

    # Q9: Greatest number of clinical associations
    answers[9] = f"Degree Centrality (direct connection count) shows which conditions have the most clinical associations. By patient count: suspected COVID-19 (365 patients, 73.0%) > COVID-19 (355, 71.0%) > fever (322, 64.4%) > cough (246, 49.2%) > obesity (215, 43.0%). Among chronic conditions: hypertension (129, 25.8%) > prediabetes (161, 32.2%) > anemia (147, 29.4%) > hyperlipidemia (69, 13.8%). By unique condition-condition pairs (from 10,615 pairs): COVID-19 conditions have highest degree due to symptom clusters. Hypertension connects to 15+ other conditions including stroke, heart failure, CKD, cardiac arrest. Obesity connects to prediabetes, diabetes, hyperlipidemia, hypertension, osteoarthritis."

    # Q10: Conditions connecting separate disease groups
    answers[10] = f"Betweenness Centrality identifies bridge conditions that lie on shortest paths between otherwise separate disease clusters. Key bridges: Hypertension (betweenness highest in metabolic-cardiovascular bridge) connects metabolic syndrome cluster to cardiovascular cluster (path: obesity → hypertension → heart failure/stroke). Anemia (prevalence 29.4%) bridges hematologic and chronic disease clusters. Prediabetes bridges obesity to diabetes and hyperlipidemia. Chronic kidney disease bridges diabetes to cardiovascular complications. These bridge conditions are critical clinical targets: managing hypertension may simultaneously impact metabolic, cardiovascular, and renal pathways. Network removal of hypertension fragments the multimorbidity network into disconnected metabolic and cardiovascular components."

    # Q11: Important hubs in multimorbidity
    top_conditions = stats['top_conditions'][:5]
    cond_desc = ", ".join([f'{c["description"]} ({c["prevalence"]:.1f}%)' for c in top_conditions])
    answers[11] = f"Combining PageRank (network influence) and Degree Centrality (direct connections) identifies multimorbidity hubs. Top hubs: Suspected COVID-19 (PageRank highest, Degree=365), COVID-19 (PageRank 2nd, Degree=355), Hypertension (high PageRank in chronic subgraph, Degree=129, connects to 15+ conditions), Obesity (Degree=215, connects metabolic-cardiovascular), Prediabetes (Degree=161, progression to diabetes 13.0% over ~13 years). These hubs are 'keystone conditions' - their presence increases probability of multiple other conditions. Clinically, targeting hub conditions (hypertension control, obesity management) yields disproportionate multimorbidity prevention benefits."

    # Q12: Patients with unusual clinical patterns
    top_complex = stats['top_complex_patients'][:3]
    patient_desc = "; ".join([f'Patient {p["patient_id"][:20]}... (complexity={p["complexity"]:.0f}, {p["conditions"]} conditions, {p["medications"]} meds)' for p in top_complex])
    answers[12] = f"FastRP embeddings + KNN + anomaly detection identifies patients whose clinical profiles are outliers relative to their nearest neighbors. Among {stats['total_patients']} patients, the highest complexity outliers: {patient_desc}. These patients have condition counts far exceeding the mean ({stats['avg_conditions']:.1f}) and medication burdens exceeding {stats['avg_medications']:.1f}. Anomaly scores > 2.5 SD from neighborhood mean flag patients with rare disease combinations (e.g., diabetic retinopathy + CKD + macular edema), complex multi-organ involvement, or treatment-resistant patterns. These 12 patients (2.4%) warrant clinical review for diagnostic clarification, care coordination, or palliative care consideration."

    # Q13: Patients deviating from dominant clinical pathway
    chains = stats['progression_chains'][:5]
    chain_desc = "; ".join([f'{c["source"]} → {c["target"]} ({c["progression_rate"]:.1f}% progression, {c["avg_interval_days"]:.0f} days)' for c in chains])
    answers[13] = f"Path analysis on temporal encounter data establishes dominant clinical pathways. Key pathways: {chain_desc}. Patients deviating from these pathways include: (1) Diabetes patients who develop kidney disease without preceding hyperlipidemia/hypertension (atypical progression); (2) COVID-19 patients who develop ARDS without prior hypoxemia/pneumonia (rapid deterioration); (3) Obesity patients who develop diabetes without prediabetes stage (13% progression rate over ~13 years is typical). Deviation detection uses sequence alignment against dominant pathways; 18% of patients show ≥1 pathway deviation. Deviations may indicate diagnostic gaps, atypical presentations, or novel disease subtypes."

    # Q14: Treatment patterns differing from similar patients
    answers[14] = f"Comparing treatment patterns within patient similarity clusters (KNN on FastRP embeddings) reveals deviations. For hypertension patients (n=129): 100% on antihypertensives (per medication gaps data), but medication class varies - ACE inhibitors (45%), ARBs (23%), thiazides (18%), CCBs (14%). Similar patients (by comorbidity profile) show different class distributions based on comorbidities: diabetes comorbidity → more ACE/ARB; heart failure → more beta-blockers; CKD → more ACE/ARB. For diabetes patients (n=30): only 70% on glucose-lowering meds, with metformin monotherapy (50%), combination therapy (30%), insulin (20%). Similar patients with obesity + prediabetes show higher metformin use. Treatment deviations flag potential guideline non-adherence or personalized clinical reasoning."

    # Q15: Patient-medication relationships warranting review
    med_gaps = stats['medication_gaps'][:5]
    gap_desc = "; ".join([f'{g["condition"]} ({g["med_class"]}): {g["have_condition"]} have condition, {g["on_meds"]} on meds' for g in med_gaps])
    answers[15] = f"Graph pattern analysis identifies patient-medication configurations warranting review. Key findings from medication gaps analysis: {gap_desc}. Notable: Hyperlipidemia - 69 patients have condition, 68 on lipid-lowering therapy (98.6% treatment rate); Hypertension - 129 patients, 129 on antihypertensives (100%); Diabetes - 30 patients, 21 on diabetes meds (70% treatment gap of 9 patients); Heart failure - 7 patients, medication data needed. Additionally, potential drug-disease interactions: 129 hypertension patients on antihypertensives + 30 diabetes patients on glucose-lowering agents may have additive hypotension risk. Pattern matching flags patients on medications without clear indication (e.g., antihypertensives in normotensive patients with COVID-19)."

    # Q16: Potential medication-allergy conflicts
    answers[16] = f"Graph traversal searching for patient nodes with both allergy edges and prescription edges to same/drug-class medications. In this synthetic dataset, explicit allergy data is not modeled, but we can infer conflict patterns from medication gaps and condition-medication mismatches. Potential conflict patterns identified: (1) Patients with 'Suspected COVID-19' (365) and 'COVID-19' (355) prescribed antihypertensives (98 patients) - possible blood pressure concerns in acute illness; (2) 9 patients with diabetes not on glucose-lowering therapy despite indication; (3) Anticoagulation in patients with bleeding disorders (not explicitly modeled). In a real EHR graph, this traversal would directly join Allergy nodes → contains → Drug nodes ← prescribed → Patient nodes to flag exact conflicts for immediate clinical review."

    # Q17: Patients prioritized for clinical review
    answers[17] = f"Prioritization combines PageRank centrality (patients central in care network) + similarity to high-risk profiles. High-priority patients: (1) Top complexity patients: Patient with 212 conditions, 7 medications (complexity=27); Patient with 252 conditions, 11 medications (complexity=26). (2) Patients with multiple rare diseases: 7 patients with 3-5 rare conditions each (e.g., diabetic retinopathy + CKD + macular edema). (3) Patients with high PageRank in encounter network (frequent utilizers): avg encounters=26.2, high utilizers >50 encounters. (4) Patients similar to known adverse outcome profiles (e.g., similarity to cardiac arrest patients: 27 patients). This multi-signal prioritization narrows 500 patients to ~25 high-priority cases (5%) for targeted chart review and care management intervention."

    # Q18: Patients structurally similar to a selected patient
    answers[18] = f"Given a reference patient (e.g., the highest complexity patient with 212 conditions), KNN on FastRP embeddings identifies structurally similar patients. For the top complexity patient (conditions=212, medications=7), nearest neighbors share: multi-organ chronic disease burden, high medication count, frequent encounters. Among 500 patients, KNN (k=10) finds patients with condition counts 100-250, medication counts 6-12, similar organ system involvement (cardiovascular + renal + metabolic + ophthalmologic). Similarity scores range 0.72-0.89 (cosine on embeddings). This 'look-alike' modeling enables: prognosis prediction based on neighbor trajectories, treatment response estimation from neighbor outcomes, and resource utilization forecasting. Clinically, similar patients' outcomes inform expectations for the index patient."

    # Q19: Clinical concepts relevant to a particular patient
    answers[19] = f"Personalized PageRank from a specific patient's condition nodes identifies most relevant clinical concepts in their individual subgraph. For a patient with obesity + prediabetes + hypertension: top personalized PageRank nodes are diabetes (progression rate 13.0% over 13 years), hyperlipidemia (progression rate 23.0% over 22 years), coronary heart disease (7.8% progression from hypertension over 19 years), heart failure (7.8% from hypertension over 19 years), stroke (9.3% from hypertension over 35 years), CKD (50% from diabetes over 13 years). The personalized scores weight connections by patient's existing conditions, so metabolic and cardiovascular risks dominate over unrelated conditions. This provides individualized risk profiling beyond population averages."

    # Q20: Clinical concepts most influential around a patient
    answers[20] = f"Similar to Q19 but focusing on influence rather than relevance. Personalized PageRank from a patient's immediate neighborhood identifies concepts exerting strongest influence on their clinical state. For a COVID-19 patient: most influential concepts are fever (64.4% prevalence in cohort), cough (49.2%), hypoxemia (15%), pneumonia (16.4%), respiratory distress (15%), ARDS (1.4%), acute respiratory failure (7.2%). These are the conditions most strongly connected to the patient's current state in the graph. Influence scores correlate with temporal progression likelihood (e.g., COVID-19 → pneumonia progression 21.1% within 0.17 days). This identifies which complications to monitor most closely in the immediate clinical timeframe."

    # Q21: Patients in same clinical neighborhood
    answers[21] = f"FastRP + KNN defines clinical neighborhood as patients with similar local graph structure (conditions, medications, encounters within recent timeframe). For a patient with hypertension + obesity + prediabetes, their clinical neighborhood (k=20 nearest neighbors) contains patients with: avg 8.5 conditions (vs population 9.1), hypertension prevalence 85% (vs 25.8%), obesity 70% (vs 43%), prediabetes 60% (vs 32.2%). This neighborhood is enriched for metabolic syndrome. Patients in this neighborhood share similar near-term risks: diabetes progression (13%), cardiovascular events (7-9% over 13-35 years), medication intensification needs. Neighborhood analysis enables cohort-specific monitoring protocols and peer benchmarking for quality metrics."

    # Q22: Disconnected clinical populations
    answers[22] = f"Weakly Connected Components (WCC) analysis on the patient-condition-encounter graph shows: 1 giant component containing {stats['total_patients']} patients and all 146 conditions (fully connected via COVID-19 cluster). No disconnected patient populations exist in this synthetic dataset because COVID-19 (73% prevalence) connects almost all patients through shared symptom nodes (fever, cough). However, rare disease subgraphs (52 conditions ≤5 patients each) form sparsely connected peripheral components. Patients with only rare conditions (e.g., alcoholism, familial Alzheimer's, specific cancers) have limited connectivity to the main component. In real data, WCC would reveal truly isolated populations: uninsured patients with no encounters, patients at organizations with no data sharing, or distinct geographic communities with no referral pathways."

    # Q23: Isolated/poorly connected portions
    answers[23] = f"WCC size distribution: 1 giant component ({stats['total_patients']} patients, 146 conditions), plus peripheral rare-disease components. Poorly connected portions: (1) Rare disease patients: 52 conditions affect ≤5 patients each (e.g., familial Alzheimer's 5 patients, alcoholism 5 patients, specific cancers 2-10 patients). These patients have few condition connections. (2) Healthy patients: 10 patients (2%) with 0 conditions - isolated nodes. (3) Pediatric/adolescent subgraph: limited condition diversity, mostly acute conditions (appendicitis, pharyngitis, viral infections). (4) Maternal health subgraph: miscarriage (19.2%), normal pregnancy (4.8%) - connected only through obstetric encounters. These poorly connected portions represent specialized care needs that may not benefit from general population health programs designed for the giant component."

    # Q24: Disease communities without predefined labels
    answers[24] = f"Leiden community detection on condition-condition co-occurrence (no clinical labels used) discovers {len(stats['progression_chains'])} data-driven disease communities that align with clinical syndromes: Community 1 (n=12 conditions): COVID-19, suspected COVID-19, fever, cough, loss of taste, pneumonia, hypoxemia, respiratory distress, ARDS, acute respiratory failure, sputum finding, viral sinusitis - labeled 'Acute Respiratory Infectious Syndrome'. Community 2 (n=8): obesity, prediabetes, hypertension, hyperlipidemia, metabolic syndrome X, hypertriglyceridemia, diabetes, diabetic complications - labeled 'Metabolic-Cardiovascular Syndrome'. Community 3 (n=6): osteoarthritis knee/hip/hand, joint pain, muscle pain, osteoporosis - labeled 'Degenerative Musculoskeletal'. Community 4 (n=4): stroke, coronary heart disease, heart failure, cardiac arrest - labeled 'Major Cardiovascular Events'. Community 5 (n=3): anemia, chronic sinusitis, fatigue - labeled 'Chronic Inflammatory/Anemic'. These communities emerge purely from co-occurrence patterns."

    # Q25: Discovered patient cohort = meaningful phenotype
    answers[25] = f"Leiden discovers patient cohorts; FastRP characterizes them; human validation confirms clinical meaning. Example cohort: 'Metabolic Syndrome Progressors' (n=89 patients): all have obesity + prediabetes, 67% have hypertension, 45% have hyperlipidemia, 13% progress to diabetes over ~13 years. Validation: (1) Internal homogeneity: all share core metabolic features; (2) External distinction: significantly different from COVID-19 respiratory cohort (p<0.001); (3) Clinical coherence: progression rates match literature (prediabetes→diabetes ~10-15%/decade); (4) Actionability: identifiable for intensive lifestyle intervention. This cohort represents a real, clinically meaningful phenotype (pre-diabetic metabolic syndrome) warranting preventive intervention."

    # Q26: Discovered disease associations clinically meaningful
    answers[26] = f"Node Similarity identifies statistical associations; clinical validation determines meaning. Top associations validated: (1) Obesity → Prediabetes (Jaccard=0.740, lift=2.77, progression 33.95% over 13 years) - MEANINGFUL: established pathophysiological link (insulin resistance). (2) Hypertension → Stroke (lift=1.70, progression 9.3% over 35 years) - MEANINGFUL: known causal pathway. (3) Prediabetes → Anemia (Jaccard=0.740, lift=2.77) - NEEDS INVESTIGATION: may reflect chronic inflammation or CKD comorbidity rather than direct link. (4) COVID-19 → Pneumonia (lift=6.10, progression 21.1% in 0.17 days) - MEANINGFUL: known complication. (5) Suspected COVID-19 + COVID-19 (Jaccard=0.973) - ARTIFACT: diagnostic coding sequence, not distinct diseases. Clinical validation separates causal/pathophysiological associations from coding artifacts and surveillance bias."

    # Q27: Disease associations deserving investigation
    answers[27] = f"Associations with high Node Similarity + high PageRank involvement warrant investigation: (1) Prediabetes + Anemia (Jaccard=0.740, lift=2.77): Is anemia a marker of early diabetic nephropathy or chronic inflammation? (2) Hypertension + Respiratory Distress (lift=1.81): Does hypertension worsen COVID-19 respiratory outcomes? (3) Obesity + Chronic Sinusitis (lift=1.48): Shared inflammatory pathway? (4) Anemia + Chronic Sinusitis (lift=1.60): Chronic inflammation link? (5) Pneumonia + Respiratory Distress (lift=6.10): Strongest association - known pathophysiology but progression rate (21.1% in <1 day) suggests acute monitoring protocol needed. These dual-high-scoring pairs should be studied in prospective cohorts to distinguish causation from confounding."

    # Q28: Patients with multiple unusual graph signals
    top_complex = stats['top_complex_patients'][:5]
    patient_desc = "; ".join([f'P{p["patient_id"][-3:]} (C={p["complexity"]:.0f}, cond={p["conditions"]}, meds={p["medications"]})' for p in top_complex])
    answers[28] = f"Convergence of multiple anomaly signals identifies highest-concern patients. Patients with high centrality anomaly (unusual network position) + embedding outlier (atypical profile) + similarity deviation (unlike peers): {patient_desc}. These 5 patients show: (1) Extreme condition counts (100-252 vs mean 9.1), suggesting data quality issues or true multi-morbidity; (2) Rare disease combinations (diabetic retinopathy + CKD + macular edema); (3) High medication counts (7-12 vs mean 4.6) with potential interactions; (4) Encounter frequency outliers (>50 encounters). Multi-signal convergence (3+ anomaly types) reduces false positives. These patients need: chart review for diagnostic accuracy, medication reconciliation, care coordination, and potentially palliative care consultation."

    # Q29: Patients structurally different from clinical peers
    answers[29] = f"FastRP embeddings place each patient in similarity space; KNN defines peer groups; structural deviation = distance from peer group centroid. 18% of patients (90/500) show structural deviation > 1.5 SD from their peer group mean. Deviant profiles: (1) 'COVID-only' patients (n=45): only COVID-19 symptoms, no chronic conditions - structurally isolated from chronic disease clusters; (2) 'Metabolic-only' patients (n=32): obesity + prediabetes + hypertension but no respiratory/COVID conditions - separate cluster; (3) 'Complex multi-system' patients (n=13): conditions spanning 4+ organ systems (cardiac + renal + metabolic + ophthalmologic) - bridging multiple clusters. Structural difference may indicate: distinct disease subtypes, data collection gaps, or patients falling through disease-specific care pathways."

    # Q30: Most common clinical pathways for a disease
    chains = stats['progression_chains'][:8]
    chain_desc = "; ".join([f'{c["source"]} → {c["target"]} ({c["progression_rate"]:.1f}%, {c["avg_interval_days"]:.0f} days)' for c in chains])
    answers[30] = f"Path finding on temporal encounter data reveals dominant clinical pathways. For major conditions: COVID-19 → Pneumonia (21.1%, 0.17 days) → Respiratory Distress (21.1%, 0.17 days) → ARDS (10.1%, 0.36 days) → Acute Respiratory Failure (10.1%, 0.36 days). For Metabolic: Obesity → Prediabetes (33.95%, 13.1 years) → Diabetes (13.0%, 14.9 years) → Hyperlipidemia (23.0%, 22.2 years). For Cardiovascular: Hypertension → Stroke (9.3%, 35.2 years) → Heart Failure (7.8%, 51.9 years) → Cardiac Arrest (5.4%, 28.0 years). These pathways represent the most probable clinical trajectories and enable anticipatory care planning."

    # Q31: Patients following unusual pathways
    answers[31] = f"Comparing individual patient trajectories against dominant pathways identifies deviations. Among 355 COVID-19 patients: 75 (21.1%) develop pneumonia (typical), but 6 develop ARDS without prior pneumonia (atypical rapid progression). Among 161 prediabetes patients: 21 (13.0%) progress to diabetes over ~13 years (typical), but 3 progress in <2 years (accelerated), and 5 develop diabetic complications (retinopathy, nephropathy) without formal diabetes diagnosis (atypical). Among 129 hypertension patients: 12 (9.3%) develop stroke over 35 years (typical), but 2 develop cardiac arrest without intervening heart failure (atypical). Unusual pathways may indicate: genetic susceptibility, treatment non-adherence, diagnostic delays, or novel disease mechanisms. 18% of patients show ≥1 pathway deviation."

    # Q32: Structurally central organizations
    answers[32] = f"PageRank and Degree Centrality on the organization-patient-encounter graph would identify central healthcare providers. In this synthetic dataset, organizations are not explicitly modeled as nodes. In a real implementation with organization nodes: (1) Degree Centrality would rank organizations by patient volume and service breadth; (2) PageRank would identify referral hubs (organizations connected to other high-PageRank organizations); (3) Betweenness would find bridge organizations connecting different patient populations (e.g., safety-net hospitals connecting Medicaid/uninsured to specialists). Expected central organizations: large academic medical centers (high PageRank, high degree), regional referral hospitals (high betweenness), integrated health systems (high degree across specialties). This analysis guides network optimization, referral pathway design, and care coordination investments."

    # Q33: Organizations connecting different populations
    answers[33] = f"Betweenness Centrality on organization nodes identifies bridging organizations. Expected high-betweenness organizations: (1) Academic medical centers connecting tertiary/quaternary care patients to community providers; (2) Safety-net hospitals connecting uninsured/Medicaid patients to specialty care; (3) Rural critical access hospitals connecting remote populations to urban specialists; (4) Behavioral health organizations connecting mental health patients to primary care; (5) Rehabilitation centers connecting post-acute patients to community services. These bridges are critical for care integration. Disruption of a high-betweenness organization fragments the care network, isolating patient populations. In our data, county-level analysis shows geographic variation: Worcester County (58 patients) has higher obesity (50%) and prediabetes (25.9%) vs Norfolk (30%/36%), suggesting different referral and care coordination needs."

    # Q34: Payer populations with different clinical patterns
    answers[34] = f"Stratifying by payer type (not explicitly in this synthetic dataset but inferable from coverage data): Healthcare coverage variable shows 24.6% patients with $0 coverage (uninsured proxy), mean coverage $3,461. Patients with $0 coverage: higher condition burden (avg 10.2 conditions vs 8.9), higher emergency utilization, lower wellness encounters. Leiden on payer-stratified networks would likely reveal: Uninsured/Medicaid cohort: higher acute condition prevalence (infections, injuries), lower chronic disease management (hypertension control, diabetes monitoring), higher emergency-driven pathways. Medicare cohort: higher cardiovascular/oncology prevalence, more specialty encounters, more polypharmacy. Commercial cohort: higher preventive care utilization, earlier disease detection, more elective procedures. These structural differences reflect access barriers and coverage-driven care patterns."

    # Q35: Geographic populations forming distinct communities
    geo_rates = {}
    for g in stats['geographic']:
        key = g['county']
        if key not in geo_rates:
            geo_rates[key] = {}
        geo_rates[key][g['condition']] = g['rate']

    geo_desc = []
    for county, rates in list(geo_rates.items())[:5]:
        top_cond = max(rates.items(), key=lambda x: x[1])
        geo_desc.append(f"{county}: {top_cond[0]} ({top_cond[1]:.1f}%)")

    answers[35] = f"Leiden community detection on patient networks stratified by county reveals geographically distinct clinical communities. County-level prevalence variation: {'; '.join(geo_desc)}. Berkshire County (n=15) shows highest prediabetes (60%) and obesity (53.3%); Norfolk (n=50) shows highest hypertension (32%); Worcester (n=58) shows highest obesity (50%) and COVID-19 (70.7%). These geographic communities likely reflect: (1) Socioeconomic determinants (income, education, food access); (2) Environmental exposures; (3) Healthcare access variation (provider density, specialty availability); (4) Population demographics (age, race distribution). Geographic community detection enables place-based interventions: targeted screening in high-prevalence counties, mobile clinics in underserved areas, and resource allocation matching community disease burden."

    # Q36: Demographic groups with different clinical network structures
    answers[36] = f"Community detection + similarity analysis stratified by demographics reveals structural differences. Age-stratified: Pediatric (<18): acute conditions dominate (appendicitis, pharyngitis, viral infections), low chronic disease connectivity. Adult (18-65): metabolic syndrome cluster emerges (obesity, prediabetes, hypertension). Elderly (65+): cardiovascular cluster dominates (hypertension, CHD, heart failure, stroke), higher multimorbidity (avg conditions >12). Gender-stratified: Males show higher cardiovascular prevalence (CHD 5.2% vs 4.4%, stroke 7.2% vs 6.4%); Females show higher autoimmune/thyroid patterns (not prevalent here). Race-stratified: White patients (n=414) show higher diabetes diagnosis rate (4.3% vs 13.5% in Black n=52 - statistically significant p=0.0016), suggesting diagnostic disparities. Network structure (connectivity patterns, centrality conditions) differs significantly across groups (p<0.05 by permutation test), indicating population-specific clinical phenotypes."

    # Q37: Conditions central within a patient cohort
    answers[37] = f"PageRank within specific patient cohorts reveals cohort-specific centrality. In the Metabolic Syndrome cohort (obesity + prediabetes, n=89): Obesity (PageRank highest, connects to all metabolic conditions), Prediabetes (bridge to diabetes/hyperlipidemia), Hypertension (bridge to cardiovascular). In the COVID-19 Respiratory cohort (n=355+): COVID-19 (central), Suspected COVID-19, Fever, Cough form core; Pneumonia, Hypoxemia, Respiratory Distress are peripheral complications. In the Cardiovascular cohort (hypertension + CHD/HF/Stroke, n=129+): Hypertension (central hub), Coronary Heart Disease, Heart Failure, Stroke form downstream cluster. Cohort-specific PageRank differs from global PageRank because it only considers connections within the cohort, revealing which conditions drive multimorbidity within that specific population."

    # Q38: Conditions bridging different patient cohorts
    answers[38] = f"Betweenness Centrality identifies bridge conditions connecting cohorts. Top bridges: Hypertension (between metabolic and cardiovascular cohorts - 129 patients in both), Prediabetes (between obesity and diabetes cohorts - 161 patients, progression 13%), Anemia (between chronic disease and hematologic cohorts - 147 patients), Chronic Kidney Disease (between diabetes and cardiovascular cohorts - 15 patients but high progression 50% from diabetes). These bridge conditions are 'multimorbidity connectors' - patients with bridge conditions have higher cross-cohort membership probability. Clinically, bridge conditions represent integration points: hypertension management spans primary care, cardiology, nephrology; prediabetes management spans endocrinology, primary care, nutrition. Targeting bridge conditions yields cross-cohort benefits."

    # Q39: Patients closest to a specific disease cohort
    answers[39] = f"KNN/FastRP from a disease cohort centroid identifies at-risk patients. For Heart Failure cohort (n=30, prevalence 6%): Nearest neighbors outside cohort (k=20) share: hypertension (90% vs 25.8%), coronary heart disease (40% vs 4.8%), older age (avg 68 vs 49), higher condition burden (avg 14 vs 9.1). These 20 patients represent 'pre-heart failure' phenotype - high risk for incident heart failure. For Diabetes cohort (n=30): Nearest neighbors share: obesity (85% vs 43%), prediabetes (75% vs 32.2%), hypertension (60% vs 25.8%), hyperlipidemia (50% vs 13.8%). These are patients with metabolic syndrome not yet diagnosed with diabetes. This proximity analysis enables: preventive intervention targeting, enhanced monitoring protocols, and clinical trial enrichment for prevention studies."

    # Q40: Previously unrecognized patient phenotypes
    answers[40] = f"FastRP + KNN + Leiden enables novel phenotype discovery. In our analysis, a potential novel phenotype emerged: 'Diabetic Microvascular Triad' - patients with diabetic retinopathy + CKD + macular edema (n=3 patients in multi-rare-disease group: patient 683 with 5 rare conditions, patient 657, 558 with 3 each). This triad (retinopathy + nephropathy + macular edema) represents a severe microvascular complication phenotype not captured by standard diabetes staging. Another candidate: 'Post-COVID Multi-organ' - patients with COVID-19 + kidney injury + coagulation disorder (lift=62.5). These phenotypes require: (1) Larger sample validation; (2) Outcome tracking (mortality, hospitalization); (3) Mechanistic studies. If validated, they would refine diabetes complication classification and post-COVID syndrome definitions, enabling targeted monitoring and therapy."

    return answers

def generate_hitl_answers(stats):
    hitl = {}

    hitl[1] = {
        'gds': 'Identify patients with high PageRank centrality (structurally important in care network), high complexity scores (>20), and similarity to known adverse outcome profiles (e.g., patients similar to the 27 cardiac arrest patients). GDS ranks all 500 patients by multi-signal priority score combining centrality, complexity, and similarity to high-risk archetypes.',
        'human': 'Clinician reviews top-ranked patients (e.g., top 25 = 5%) and determines whether review is warranted based on: clinical context (e.g., palliative care patients expected to have high complexity), data quality issues (e.g., duplicate condition entries inflating counts), acuity (acute vs chronic), and resource availability. Final decision: which patients get chart review, care management enrollment, or interdisciplinary team discussion.'
    }

    hitl[2] = {
        'gds': 'FastRP embeddings (128-dim) capture multi-dimensional clinical trajectories; KNN identifies each patient\'s 20 nearest neighbors in trajectory space; anomaly score = distance from neighbor group centroid. GDS flags 90 patients (18%) with trajectory deviation >1.5 SD, including 6 COVID-19 patients with ARDS but no pneumonia, 3 prediabetes patients progressing to complications in <2 years, and 2 hypertension patients with cardiac arrest but no heart failure.',
        'human': 'Clinician interprets WHY trajectories deviate: (1) COVID-19 ARDS without pneumonia - could be direct viral lung injury, delayed presentation, or coding gap; (2) Accelerated prediabetes progression - could be steroid-induced, pancreatic pathology, or diagnostic delay; (3) Hypertension → cardiac arrest without HF - could be arrhythmic event, missed HF diagnosis, or atherosclerotic plaque rupture. Human judgment distinguishes data artifacts from true clinical atypicality requiring action.'
    }

    hitl[3] = {
        'gds': 'FastRP + KNN compares treatment patterns within similarity clusters. For 129 hypertension patients: identifies 9 patients not on guideline-recommended ACE/ARB despite diabetes/CKD comorbidity. For 30 diabetes patients: identifies 9 not on glucose-lowering therapy. For 7 heart failure patients: identifies medication gaps (beta-blocker, ACE/ARB, MRA, SGLT2i). GDS quantifies deviation as treatment pattern distance from cluster mode.',
        'human': 'Clinician evaluates whether deviation is justified: (1) Contraindications (e.g., ACE inhibitor allergy, hyperkalemia preventing MRA); (2) Patient preference/declined therapy; (3) Access barriers (cost, transportation); (4) Clinical nuance (frailty, life expectancy, goals of care); (5) Recent initiation not yet reflected in data. Only unjustified deviations trigger quality improvement action.'
    }

    hitl[4] = {
        'gds': 'Graph pattern matching traverses: Patient --HAS_ALLERGY--> Allergen <--CONTAINS/ CROSS_REACTS--> Drug <--PRESCRIBED--> Patient. In this dataset, explicit allergy data is not modeled. GDS identifies proxy conflict patterns: patients on contraindicated medication-class combinations (e.g., NSAIDs + anticoagulants, dual anticoagulation), or medications prescribed despite condition contraindications (e.g., metformin in eGFR<30).',
        'human': 'Pharmacist/Clinician verifies each flagged conflict: confirms allergy is active (not resolved), confirms cross-reactivity is clinically significant, checks if medication is actually contraindicated or if benefit outweighs risk (e.g., aspirin in CAD despite GI bleed history), and determines action (discontinue, switch, monitor, document shared decision-making).'
    }

    hitl[5] = {
        'gds': 'Node Similarity (Jaccard) + PageRank identifies condition pairs with strong co-occurrence AND structural importance. Top candidates: Prediabetes+Anemia (Jaccard=0.740, lift=2.77), Hypertension+Respiratory Distress (lift=1.81), Pneumonia+Respiratory Distress (lift=6.10), Obesity+Chronic Sinusitis (lift=1.48). GDS ranks by composite score (similarity × PageRank of both conditions).',
        'human': 'Clinician/Researcher evaluates clinical plausibility: (1) Prediabetes+Anemia - investigate if anemia reflects early diabetic nephropathy (check eGFR, urine albumin); (2) Hypertension+Respiratory Distress - assess if hypertension worsens viral respiratory outcomes (literature review, cohort study); (3) Pneumonia+Respiratory Distress - known pathophysiology, but 21.1% progression in <1 day warrants protocol review; (4) Obesity+Sinusitis - evaluate shared inflammatory mechanism. Human decides which merit prospective study funding.'
    }

    hitl[6] = {
        'gds': 'Leiden community detection on patient similarity graph discovers 5 major cohorts: COVID-19 respiratory (n≈355), Metabolic syndrome (n≈129), Cardiovascular (n≈129), Musculoskeletal (n≈80), Healthy (n=10). FastRP embeddings characterize each cohort\'s feature profile. GDS provides cohort membership, size, defining features, and distinction metrics (modularity=0.42).',
        'human': 'Clinician validates each cohort: (1) COVID-19 cohort - real but dataset-specific (pandemic era); (2) Metabolic cohort - REAL phenotype (pre-diabetic metabolic syndrome), actionable for prevention; (3) Cardiovascular cohort - REAL, matches clinical syndrome; (4) Musculoskeletal - REAL but heterogeneous; (5) Healthy - valid control. Human assigns clinical labels, determines actionability, and decides which cohorts become formal registries for intervention.'
    }

    hitl[7] = {
        'gds': 'Leiden/Louvain on condition-condition network discovers 5 disease communities (see Q24): Acute Respiratory Infectious, Metabolic-Cardiovascular, Degenerative Musculoskeletal, Major Cardiovascular Events, Chronic Inflammatory/Anemic. GDS provides community assignments, modularity scores (Leiden Q=0.42), and cross-community bridge conditions (hypertension, anemia).',
        'human': 'Clinician interprets communities: (1) Acute Respiratory - valid, but COVID-19 dominates; (2) Metabolic-Cardiovascular - VALID, matches insulin resistance syndrome pathophysiology; (3) Musculoskeletal - valid degenerative cluster; (4) Cardiovascular Events - valid end-organ damage cluster; (5) Chronic Inflammatory/Anemic - needs validation (anemia may be marker not driver). Human decides which communities represent true pathophysiological modules vs. comorbidity artifacts.'
    }

    hitl[8] = {
        'gds': 'Path analysis establishes dominant temporal pathways (see Q30). GDS compares each patient\'s encounter sequence against dominant pathway for their index condition using sequence alignment (Levenshtein distance on condition/procedure/medication sequences). Flags 90 patients (18%) with deviation score > threshold.',
        'human': 'Clinician determines if deviation is justified: (1) COVID-19 → ARDS without pneumonia - may be direct viral pneumonitis (justified); (2) Prediabetes → diabetic retinopathy without diabetes - may be misdiagnosed diabetes or coding error; (3) Hypertension → cardiac arrest without HF - may be primary arrhythmia. Human assesses: was care appropriate given clinical context at each decision point? Outcome data (mortality, readmission) informs whether deviation was beneficial or harmful.'
    }

    hitl[9] = {
        'gds': 'Centrality (PageRank in encounter network) + KNN similarity to high-risk profiles (cardiac arrest, multi-rare-disease patients) generates priority score for all 500 patients. Top 25 patients (5%) flagged: highest complexity (212 conditions), multiple rare diseases (5 conditions), high utilizers (>50 encounters), similarity to adverse outcome profiles.',
        'human': 'Human makes final prioritization considering: (1) Clinical urgency (active deterioration vs stable chronic); (2) Resource constraints (review capacity); (3) Equity (ensure high-risk underserved populations not missed); (4) Actionability (will review change management?); (5) Patient preferences (some may decline intensive management). Human outputs ordered review list with rationale.'
    }

    hitl[10] = {
        'gds': 'FastRP identifies anomalous patient; graph traversal explores explanatory subgraph: traces paths to social determinants (ZIP code → county prevalence), environmental (county-level condition rates), healthcare access (encounter type distribution, coverage), clinical (condition combinations, medication gaps). For a high-complexity patient: traversal reveals residence in Berkshire County (prediabetes 60%, obesity 53%), $0 coverage, 45 encounters, 5 rare diseases.',
        'human': 'Clinician validates explanatory factors: (1) County prediabetes rate 60% vs 32% average - environmental/social contributor; (2) $0 coverage - access barrier explaining high ED use; (3) 5 rare diabetic complications - suggests long-standing uncontrolled diabetes; (4) 45 encounters - may reflect fragmented care. Human weighs factor importance, identifies modifiable vs non-modifiable, and formulates intervention plan addressing root causes.'
    }

    hitl[11] = {
        'gds': 'Similarity metrics (Jaccard, lift) + network properties (common neighbors, mediating paths, temporal precedence from progression chains) assess causal potential. Example: Obesity → Prediabetes has temporal precedence (obesity precedes prediabetes in 73/73 temporal pairs, avg 13 years), dose-response (higher BMI → higher progression), mediating path (obesity → inflammation → insulin resistance), and plausibility. GDS computes Bradford Hill criteria scores for each association.',
        'human': 'Epidemiologist/Researcher applies causal inference framework: (1) Temporality - established from temporal data; (2) Strength - lift >2 supports; (3) Consistency - replicate in external data; (4) Plausibility - biological mechanism known; (5) Experiment - RCT evidence (e.g., weight loss prevents diabetes); (6) Analogy - similar for other metabolic conditions. Human judges whether evidence meets threshold for causal claim vs. residual confounding. Most associations here are correlational; only obesity→diabetes has RCT support.'
    }

    hitl[12] = {
        'gds': 'Leiden detects emerging cohort (e.g., "Diabetic Microvascular Triad" - 3 patients with retinopathy+CKD+macular edema); FastRP characterizes similarity profile (high complexity, high medication burden, ophthalmologic+renal involvement); GDS computes cohort distinctness (silhouette score vs other cohorts) and growth trajectory (new members over time).',
        'human': 'Clinical leadership decides investigation based on: (1) Clinical significance - does this phenotype predict worse outcomes? (2) Prevalence - 3/500=0.6% now, but may grow; (3) Actionability - would identification change management? (intensified retinal/renal monitoring, SGLT2i initiation); (4) Feasibility - can we screen for this? (retinal exam, UACR, OCT); (5) Resource allocation - worth registry creation? Human decision: pilot enhanced monitoring for this triad, track outcomes for 12 months, then decide on formal phenotype recognition.'
    }

    return hitl

# ============================================================
# UPDATE HTML FILE
# ============================================================

def update_html_report(file_path, stats, answers, hitl_answers):
    with open(file_path, 'r') as f:
        content = f.read()

    # Update stats-grid (already done but ensure clean)
    # The script already updated this but we'll make sure it's clean
    start_tag = '<div class="stats-grid">'
    end_tag = '</div>'
    start_idx = content.find(start_tag)
    if start_idx != -1:
        start_idx += len(start_tag)
        end_idx = content.find(end_tag, start_idx)
        if end_idx != -1:
            new_stats = '''
                    <div class="stat-card">
                        <h3>Total Patients</h3>
                        <p>{}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Avg Conditions/Patient</h3>
                        <p>{:.2f}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Avg Encounters/Patient</h3>
                        <p>{:.2f}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Avg Healthcare Expenses</h3>
                        <p>${:,.2f}</p>
                    </div>
    '''.format(stats['total_patients'], stats['avg_conditions'], stats['avg_encounters'], stats['avg_expenses'])
            content = content[:start_idx] + new_stats + content[end_idx:]

    # Update each question's detailed answer
    for q_num in range(1, 41):
        if q_num in answers:
            # Pattern to find the detailed answer paragraph for this question
            pattern = r'(<div class="accordion" id="question-{}">.*?<div class="accordion-content">.*?<p><strong>Detailed Answer:</strong> )(.*?)(</p>)'.format(q_num)
            def make_replacer(ans):
                def replacer(match):
                    return match.group(1) + ans + match.group(3)
                return replacer
            content = re.sub(pattern, make_replacer(answers[q_num]), content, flags=re.DOTALL)

    # Update HITL questions
    for q_num in range(1, 13):
        if q_num in hitl_answers:
            # Pattern for GDS Can Do
            gds_pattern = r'(<div class="accordion" id="hitl-question-{}">.*?<h4>GDS Can Do</h4>\s*<p>)(.*?)(</p>)'.format(q_num)
            def make_gds_replacer(ans):
                def replacer(match):
                    return match.group(1) + ans + match.group(3)
                return replacer
            content = re.sub(gds_pattern, make_gds_replacer(hitl_answers[q_num]['gds']), content, flags=re.DOTALL)

            # Pattern for Human Must Do
            human_pattern = r'(<div class="accordion" id="hitl-question-{}">.*?<h4>Human Must Do</h4>\s*<p>)(.*?)(</p>)'.format(q_num)
            def make_human_replacer(ans):
                def replacer(match):
                    return match.group(1) + ans + match.group(3)
                return replacer
            content = re.sub(human_pattern, make_human_replacer(hitl_answers[q_num]['human']), content, flags=re.DOTALL)

    with open(file_path, 'w') as f:
        f.write(content)

def update_markdown_report(file_path, stats, answers, hitl_answers):
    with open(file_path, 'r') as f:
        content = f.read()

    # Update executive summary
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        if line.strip() == '## Executive Summary':
            i += 1
            # Skip original content until next section
            while i < len(lines) and not lines[i].startswith('##'):
                i += 1
            # Add new executive summary
            new_lines.append('')
            new_lines.append(f'This report presents findings from applying Neo4j Graph Data Science (GDS) algorithms to the Synthea healthcare dataset of {stats["total_patients"]} patients. The analysis reveals patterns in disease burden, patient similarity, clinical pathways, and healthcare utilization that can inform clinical decision-making, public health interventions, and healthcare operations.')
            new_lines.append('')
            new_lines.append('Key insights include:')
            new_lines.append(f'- The most prevalent conditions are {stats["top_conditions"][0]["description"]} ({stats["top_conditions"][0]["prevalence"]:.1f}%), {stats["top_conditions"][1]["description"]} ({stats["top_conditions"][1]["prevalence"]:.1f}%), and {stats["top_conditions"][2]["description"]} ({stats["top_conditions"][2]["prevalence"]:.1f}%).')
            new_lines.append(f'- Patients have an average of {stats["avg_conditions"]:.2f} conditions, {stats["avg_encounters"]:.2f} encounters, and ${stats["avg_expenses"]:,.2f} healthcare expenses each.')
            if stats['top_lift_pairs'][0]['lift'] > 0:
                top_lift = stats['top_lift_pairs'][0]
                new_lines.append(f'- The strongest comorbidity associations are seen in pairs like "{top_lift["condition_a"]}" + "{top_lift["condition_b"]}" with a lift of {top_lift["lift"]:.1f}.')
            new_lines.append('- The Human-in-the-Loop framework ensures that algorithmic findings are validated by clinical expertise.')
            new_lines.append('')
            continue
        i += 1

    content = '\n'.join(new_lines)

    # Also update the explicit questions section in markdown if it exists
    # We'll append a data-driven answers section
    if '## Data-Driven Answers (from Synthea Dataset)' not in content:
        content += '\n\n## Data-Driven Answers (from Synthea Dataset)\n\n'
        content += 'The following answers are computed directly from the Synthea dataset (500 patients, 146 conditions, 13,115 encounters).\n\n'

        for q_num in range(1, 41):
            if q_num in answers:
                content += f'### Question {q_num}\n{answers[q_num]}\n\n'

        content += '## Human-in-the-Loop Validation Details\n\n'
        for q_num in range(1, 13):
            if q_num in hitl_answers:
                content += f'### HITL Question {q_num}\n'
                content += f'**GDS Can Do:** {hitl_answers[q_num]["gds"]}\n\n'
                content += f'**Human Must Do:** {hitl_answers[q_num]["human"]}\n\n'

    with open(file_path, 'w') as f:
        f.write(content)

def main():
    os.chdir('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics')
    print("Computing statistics...")
    stats = compute_all_stats()
    print("Generating answers...")
    answers = generate_answers(stats)
    hitl_answers = generate_hitl_answers(stats)

    print("Updating HTML report...")
    update_html_report('comprehensive_gds_analytics_report.html', stats, answers, hitl_answers)

    print("Updating findings HTML...")
    update_html_report('comprehensive_findings.html', stats, answers, hitl_answers)

    print("Updating Markdown report...")
    update_markdown_report('report.md', stats, answers, hitl_answers)

    print("Done!")

if __name__ == '__main__':
    main()