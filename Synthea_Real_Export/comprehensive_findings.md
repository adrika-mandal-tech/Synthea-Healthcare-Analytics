# Comprehensive Clinical Analytics: Findings 8–23

**Document Type:** Extension of [Practical Findings 1–7](Synthea_Real_Export/practical_findings.md)  
**Dataset:** Synthea synthetic patient graph  
**Population:** 500 patients, 146 conditions, 111 medications, 106 procedures, 13,115 encounters  
**Generated:** 2026-09-28

> **Reading guide:** Findings 1–7 are in `practical_findings.md`. This document covers Findings 8–23. Each finding ends with an **Algorithms & derivation** section explaining exactly how the numbers were produced.

---

## Master Evaluation Pipeline

The diagram below shows the end-to-end pipeline used to produce every finding in this document, from raw CSVs to clinical insight.

```mermaid
flowchart LR
    A["Raw exports\npatients.csv\npatient_condition.csv\npatient_encounter.csv\npatient_medication.csv"] --> B["Data validation\n+ schema audit"]
    B --> C["Temporal export\nencounter_condition_\ntemporal.csv"]
    C --> D["Feature engineering\n70 features per patient"]
    D --> E["Analytical engines"]
    E --> E1["Pairwise statistics\n(Jaccard, lift, OR,\nchi-square, conditional\nprobabilities)"]
    E --> E2["Temporal progression\nchains (15 chains)"]
    E --> E3["Graph analytics\n(Neo4j GDS:\ncentrality, communities,\nsimilarity, embeddings)"]
    E --> E4["Classical ML\n(LR, RF, XGBoost)"]
    E --> E5["Graph ML\n(Node2Vec, FastRP,\nGraphSAGE)"]
    E1 --> F["Statistical tables\n+ thresholds"]
    E2 --> F
    E3 --> F
    E4 --> F
    E5 --> F
    F --> G["Clinical interpretation\n+ analytical points"]
    G --> H["Findings 8–23\n(this document)"]
```

---

## Finding 8: Complete Disease Prevalence — All 146 Conditions Ranked

### Data source
`patient_condition.csv` (4,568 patient-condition pairs across 500 patients).

### What we found

| Rank | Condition | Patients | Prevalence |
|------|-----------|----------|------------|
| 1 | Suspected COVID-19 | 365 | 73.0% |
| 2 | COVID-19 | 355 | 71.0% |
| 3 | Fever (finding) | 322 | 64.4% |
| 4 | Cough (finding) | 246 | 49.2% |
| 5 | Body mass index 30+ - obesity (finding) | 215 | 43.0% |
| 6 | Loss of taste (finding) | 188 | 37.6% |
| 7 | Prediabetes | 161 | 32.2% |
| 8 | Anemia (disorder) | 147 | 29.4% |
| 9 | Fatigue (finding) | 142 | 28.4% |
| 10 | Hypertension | 129 | 25.8% |
| 11 | Sputum finding (finding) | 107 | 21.4% |
| 12 | Chronic sinusitis (disorder) | 102 | 20.4% |
| 13 | Miscarriage in first trimester | 96 | 19.2% |
| 14 | Pneumonia (disorder) | 82 | 16.4% |
| 15 | Hypoxemia (disorder) | 75 | 15.0% |
| 16 | Respiratory distress (finding) | 75 | 15.0% |
| 17 | Hyperlipidemia | 69 | 13.8% |
| 18 | Muscle pain (finding) | 65 | 13.0% |
| 19 | Joint pain (finding) | 65 | 13.0% |
| 20 | Dyspnea (finding) | 53 | 10.6% |
| 21–146 | *(remaining 126 conditions)* | — | 0.2%–9.8% |

**Total unique conditions:** 146  
**Total patient-condition pairs:** 4,568  
**Patients with ≥1 condition:** 490 (98.0%)  
**Patients with 0 conditions:** 10 (2.0%)

### Analytical points
- **COVID-19 dominates the condition landscape:** Suspected COVID-19 (73.0%) and COVID-19 (71.0%) are the top 2 conditions, creating a **confounding effect** where many comorbidities may actually be COVID-19 sequelae or misclassified acute conditions.
- **Fever and cough are COVID-19 symptoms, not independent conditions:** Their high prevalence (64.4% and 49.2%) is expected given the pandemic context.
- **Obesity (43.0%) is the most common pre-existing chronic condition**, followed by prediabetes (32.2%) and anemia (29.4%). This suggests a **metabolic syndrome cluster** in the population.
- **The 10 healthy patients (2%)** are valuable as a control cohort for benchmarking utilization and cost.
- **The tail is long:** 52 conditions affect ≤5 patients each, creating a “rare disease” long tail.

### Algorithms & derivation
- **Algorithm:** Descriptive frequency count + prevalence calculation.
- **Formula:** `prevalence = (patients_with_condition / 500) × 100`.
- **Filtering:** All 146 unique `CODE` values from `patient_condition.csv` were included; no pairs were excluded.
- **Sorting:** Descending by `count`, then alphabetically for ties.

---

## Finding 9: Pairwise Comorbidity Probabilities — All 10,615 Condition Pairs

### Data source
Pairwise analysis across all 146 conditions (10,615 unique pairs) using patient-condition sets.

### What we found

**Method:** For each condition pair (A, B), we computed co-occurrence counts, conditional probabilities, lift, odds ratio, and relative risk.

**Top 30 pairs by lift (lift > 20, minimum 3 co-occurrences):**

| Rank | Condition A | Condition B | Shared | P(A\|B) | P(B\|A) | Lift |
|------|-------------|-------------|--------|---------|---------|------|
| 1 | Acquired coagulation disorder | Injury of kidney | 4 | 100.0% | 50.0% | 62.5 |
| 2 | Septic shock | Injury of heart | 4 | 80.0% | 57.1% | 57.1 |
| 3 | Heart failure | Injury of kidney | 3 | 75.0% | 42.9% | 53.6 |
| 4 | Acquired coagulation disorder | Heart failure | 6 | 85.7% | 75.0% | 53.6 |
| 5 | Acquired coagulation disorder | Septic shock | 6 | 85.7% | 75.0% | 53.6 |
| 6 | Heart failure | Septic shock | 5 | 71.4% | 71.4% | 51.0 |
| 7 | Non-small cell lung cancer TNM stage 1 | Suspected lung cancer | 10 | 100.0% | 100.0% | 50.0 |
| 8 | Non-small cell lung cancer TNM stage 1 | Non-small cell lung cancer | 10 | 100.0% | 100.0% | 50.0 |
| 9 | Suspected lung cancer | Non-small cell lung cancer | 10 | 100.0% | 100.0% | 50.0 |
| 10 | Myocardial Infarction | History of myocardial infarction | 10 | 100.0% | 100.0% | 50.0 |
| 11 | ARDS | Septic shock | 7 | 100.0% | 63.6% | 45.5 |
| 12 | ARDS | Injury of kidney | 4 | 100.0% | 36.4% | 45.5 |
| 13 | Heart failure | Injury of heart | 3 | 60.0% | 42.9% | 42.9 |
| 14 | Seizure disorder | History of single seizure | 12 | 100.0% | 100.0% | 41.7 |
| 15 | Seizure disorder | Epilepsy | 6 | 100.0% | 50.0% | 41.7 |
| 16 | History of single seizure | Epilepsy | 6 | 100.0% | 50.0% | 41.7 |
| 17 | Diabetic retinopathy (type II) | Nonproliferative diabetic retinopathy (type 2) | 3 | 100.0% | 25.0% | 41.7 |
| 18 | Acquired coagulation disorder | ARDS | 7 | 63.6% | 87.5% | 39.8 |
| 19 | Heart failure | ARDS | 6 | 54.5% | 85.7% | 39.0 |
| 20 | Carcinoma in situ of prostate | Neoplasm of prostate | 11 | 84.6% | 100.0% | 38.5 |
| 21 | Acquired coagulation disorder | Injury of heart | 3 | 60.0% | 37.5% | 37.5 |
| 22 | ARDS | Injury of heart | 4 | 80.0% | 36.4% | 36.4 |
| 23 | Diabetic renal disease | Nonproliferative diabetic retinopathy (type 2) | 3 | 100.0% | 18.8% | 31.3 |
| 24 | Diabetic renal disease | Chronic kidney disease stage 1 | 15 | 100.0% | 93.8% | 31.3 |
| 25 | Polyp of colon | Recurrent rectal polyp | 9 | 100.0% | 52.9% | 29.4 |
| 26 | Alcoholism | Carcinoma in situ of prostate | 3 | 27.3% | 60.0% | 27.3 |
| 27 | Acute deep venous thrombosis | Injury of kidney | 4 | 100.0% | 19.0% | 23.8 |
| 28 | Diabetic renal disease | Diabetic retinopathy (type II) | 9 | 75.0% | 56.3% | 23.4 |
| 29 | Alcoholism | Neoplasm of prostate | 3 | 23.1% | 60.0% | 23.1 |
| 30 | COVID-19 | Suspected COVID-19 | 355 | 97.7% | 97.5% | 22.8 |

**Full pairwise table:** 1,310 pairs with lift > 1.2 and ≥3 co-occurrences saved to `comorbidity_probabilities.csv`.

### Analytical points
- **The highest-lift pairs are medically coherent:** septic shock + multi-organ failure, lung cancer + suspected lung cancer, seizure disorder + epilepsy. The algorithm recovered known clinical relationships without supervision.
- **100% conditional probabilities (P(A|B) = 100%)** do NOT imply causation. They occur when every patient with condition B also has condition A, often because A is a **diagnostic prerequisite** or **sequela** of B.
- **Lift > 40 is rare and clinically significant:** only 10 pairs exceed this threshold. These represent strong comorbidity signals worth screening for in clinical workflows.
- **The COVID-19 / Suspected COVID-19 pair (lift = 22.8)** reflects the data generation process: these are near-duplicate conditions in the synthetic data, not independent diseases.
- **Relative risk and odds ratio are undefined** when one cell in the 2×2 contingency table is zero. We report lift and conditional probabilities instead for these rare pairs.

### Algorithms & derivation
- **Algorithm:** Exhaustive pairwise set intersection on patient-condition bipartite graph.
- **Input:** `condition_sets` dictionary mapping `patient_id → set(condition_codes)`.
- **Pair enumeration:** All combinations of 146 conditions = 10,615 pairs.
- **Metrics computed:**
  - `n_both = len(patients_A ∩ patients_B)`
  - `P(A|B) = n_both / n_B`
  - `P(B|A) = n_both / n_A`
  - `lift = n_both / (n_A × n_B / N)` where N = 500
  - `odds_ratio = (n_both × n_neither) / (n_A_only × n_B_only)` when all cells > 0
- **Filtering:** `lift > 1.2` AND `n_both >= 3` to ensure statistical stability.
- **Ranking:** Descending by lift.

---

## Finding 10: Disease Progression Chains — Temporal Validation of 15 Clinical Pathways

### Data source
`encounter_condition_temporal.csv` (condition onset dates derived from `Encounter-[:DIAGNOSED_WITH]->Condition` START dates in Neo4j).

### What we found

| Source → Target | Source patients | Target patients | Both | Progression rate | Temporal pairs | Source before target | Avg interval |
|----------------|----------------|-----------------|------|------------------|----------------|----------------------|--------------|
| Anemia → Prediabetes | 147 | 161 | 131 | **89.1%** | 131 | 4 (3.1%) | 7.1 years |
| Diabetes → Kidney disease | 30 | 15 | 15 | **50.0%** | 15 | 14 (93.3%) | 13.4 years |
| Obesity → Prediabetes | 215 | 161 | 73 | **34.0%** | 73 | 73 (100%) | 13.1 years |
| Prediabetes → Hyperlipidemia | 161 | 69 | 37 | **23.0%** | 37 | 31 (83.8%) | 23.9 years |
| Obesity → Hyperlipidemia | 215 | 69 | 47 | **21.9%** | 47 | 42 (89.4%) | 22.8 years |
| COVID-19 → Pneumonia | 355 | 82 | 75 | **21.1%** | 75 | 75 (100%) | 0.0 days |
| COVID-19 → Respiratory distress | 355 | 75 | 75 | **21.1%** | 75 | 75 (100%) | 0.0 days |
| Prediabetes → Diabetes | 161 | 30 | 21 | **13.0%** | 21 | 10 (47.6%) | 4.1 years |
| COVID-19 → Acute respiratory failure | 355 | 36 | 36 | **10.1%** | 36 | 36 (100%) | 0.0 days |
| Hypertension → Stroke | 129 | 34 | 12 | **9.3%** | 12 | 12 (100%) | 35.2 years |
| Hypertension → Heart failure | 129 | 30 | 10 | **7.8%** | 10 | 10 (100%) | 51.9 years |
| Obesity → Diabetes | 215 | 30 | 13 | **6.0%** | 13 | 13 (100%) | 17.0 years |
| Hypertension → Cardiac Arrest | 129 | 27 | 7 | **5.4%** | 7 | 3 (42.9%) | 28.0 years |
| COVID-19 → ARDS | 355 | 11 | 11 | **3.1%** | 11 | 11 (100%) | 0.0 years |
| Hypertension → Myocardial Infarction | 129 | 10 | 2 | **1.6%** | 2 | 2 (100%) | 51.4 years |

### Analytical points
- **Diabetes → Kidney disease (50% progression)** is the strongest temporal progression in the dataset. 93.3% of paired cases show diabetes diagnosed before CKD, with a 13.4-year average interval — consistent with real-world diabetic nephropathy timelines.
- **Anemia → Prediabetes (89.1% co-occurrence)** is NOT a temporal progression: only 3.1% of paired cases show anemia before prediabetes. This is a **comorbidity**, not a progression.
- **COVID-19 → Pneumonia/Respiratory distress (0-day interval)** is a **data artifact**. The synthetic generator assigns all active conditions to each encounter. Only ARDS (8.2-day interval) shows plausible progression.
- **Prediabetes → Diabetes (13% progression)** is likely an underestimate: 52.4% of paired cases show diabetes diagnosed BEFORE prediabetes, suggesting reverse coding or fast progression.

### Algorithms & derivation
- **Algorithm:** Temporal order validation on first-onset dates.
- **Input:** `encounter_condition_temporal.csv` with `patient_id`, `condition_code`, `encounter_start`.
- **Step 1:** Compute `first_onset[patient][condition] = min(encounter_start)`.
- **Step 2:** For each chain `A → B`, collect patients with both A and B.
- **Step 3:** Count `temporal_pairs` where `first_onset[A] < first_onset[B]`.
- **Step 4:** Compute `progression_rate = patients_with_both / patients_with_source`.
- **Step 5:** Compute `avg_interval = mean(first_onset[B] - first_onset[A])` for valid pairs.
- **Filtering:** Chains with ≥3 shared patients included.

---

## Finding 11: Rare Disease Patterns — 52 Conditions Affecting ≤5 Patients Each

### Data source
Condition prevalence analysis and patient-level rare disease aggregation.

### What we found

**Rare diseases (1–5 patients each):** 52 conditions

| Condition | Patients | Prevalence |
|-----------|----------|------------|
| Alcoholism | 5 | 1.0% |
| Familial Alzheimer's disease of early onset | 5 | 1.0% |
| Injury of heart (disorder) | 5 | 1.0% |
| Child attention deficit disorder | 4 | 0.8% |
| Sinusitis (disorder) | 4 | 0.8% |
| Idiopathic atrophic hypothyroidism | 4 | 0.8% |
| Injury of kidney (disorder) | 4 | 0.8% |
| Brain damage - traumatic | 3 | 0.6% |
| Rheumatoid arthritis | 3 | 0.6% |
| Nonproliferative diabetic retinopathy due to type 2 diabetes mellitus (disorder) | 3 | 0.6% |
| Facial laceration | 3 | 0.6% |
| Fracture subluxation of wrist | 3 | 0.6% |
| Body mass index 40+ - severely obese (finding) | 3 | 0.6% |
| Cystitis | 3 | 0.6% |
| Sprain of wrist | 3 | 0.6% |
| Concussion with no loss of consciousness | 3 | 0.6% |
| *(36 additional conditions with 1–2 patients each)* | — | — |

**Patients with ≥3 rare diseases:** 6 patients

| Patient | Rare count | Rare conditions |
|---------|-----------|-----------------|
| 683 | 5 | Macular edema and retinopathy due to type 2 diabetes mellitus, Chronic kidney disease stage 2, Proliferative diabetic retinopathy due to type II diabetes, Nonproliferative diabetic retinopathy due to type 2 diabetes, Microalbuminuria due to type 2 diabetes |
| 865 | 4 | Pathological fracture due to osteoporosis, Sinusitis, Brain damage - traumatic, Closed fracture of hip |
| 923 | 3 | Bleeding from anus, Protracted diarrhea, Secondary malignant neoplasm of colon |
| 577 | 3 | Injury of kidney, Injury of heart, Body mass index 40+ - severely obese |
| 691 | 3 | Alcoholism, Fracture of clavicle, Smokes tobacco daily |
| 657 | 3 | Chronic kidney disease stage 2, Nonproliferative diabetic retinopathy, Microalbuminuria due to type 2 diabetes |
| 558 | 3 | Idiopathic atrophic hypothyroidism, Nonproliferative diabetic retinopathy, Proliferative diabetic retinopathy |

### Analytical points
- **52 rare conditions (1–5 patients each)** represent 35.6% of all unique condition codes but only 2.3% of all patient-condition pairs. This long tail is typical of medical coding systems.
- **Patient 683 is a "complex diabetic" case:** 5 rare diabetic complications spanning eyes, kidneys, and microvasculature. The synthetic generator appears to create “complex case” patients by bundling related rare conditions.
- **The 7 patients with multiple rare diseases** are outliers requiring multidisciplinary care coordination.
- **Trauma cluster (Patient 865):** Brain damage, hip fracture, clavicle fracture, osteoporosis fracture — suggests a high-impact trauma event with sequelae.

### Algorithms & derivation
- **Algorithm:** Frequency thresholding + set intersection.
- **Step 1:** From `all_conditions_prevalence.csv`, filter `count <= 5` → 52 rare conditions.
- **Step 2:** For each patient, compute `rare_conditions = condition_set ∩ rare_codes`.
- **Step 3:** Filter patients with `len(rare_conditions) >= 3` → 6 patients.
- **Output:** `rare_diseases.csv` + `patients_with_multiple_rare_diseases.csv`.

---

## Finding 12: Geographic Disease Patterns — County-Level Hotspots

### Data source
`patients.csv` `COUNTY` field joined with `patient_condition.csv` condition sets.

### What we found

#### Obesity prevalence by county

| County | Patients | With obesity | Prevalence |
|--------|----------|--------------|------------|
| Hampshire County | 14 | 8 | **57.1%** |
| Barnstable County | 28 | 16 | **57.1%** |
| Berkshire County | 15 | 8 | **53.3%** |
| Worcester County | 58 | 29 | **50.0%** |
| Bristol County | 55 | 26 | **47.3%** |
| Essex County | 48 | 22 | 45.8% |
| Middlesex County | 97 | 43 | 44.3% |
| Norfolk County | 50 | 19 | 38.0% |
| Suffolk County | 63 | 22 | 34.9% |

#### Hypertension prevalence by county

| County | Patients | With hypertension | Prevalence |
|--------|----------|-------------------|------------|
| Berkshire County | 15 | 6 | **40.0%** |
| Hampshire County | 14 | 5 | **35.7%** |
| Hampden County | 26 | 9 | **34.6%** |
| Norfolk County | 50 | 16 | **32.0%** |
| Suffolk County | 63 | 20 | **31.7%** |
| Bristol County | 55 | 14 | 25.5% |
| Plymouth County | 42 | 10 | 23.8% |
| Middlesex County | 97 | 20 | 20.6% |
| Worcester County | 58 | 12 | 20.7% |
| Barnstable County | 28 | 5 | 17.9% |
| Essex County | 48 | 8 | 16.7% |

#### Diabetes prevalence by county

| County | Patients | With diabetes | Prevalence |
|--------|----------|---------------|------------|
| Berkshire County | 15 | 2 | **13.3%** |
| Hampden County | 26 | 3 | **11.5%** |
| Essex County | 48 | 4 | **8.3%** |
| Norfolk County | 50 | 4 | **8.0%** |
| Plymouth County | 42 | 3 | **7.1%** |
| Middlesex County | 97 | 5 | 5.2% |
| Worcester County | 58 | 3 | 5.2% |
| Suffolk County | 63 | 3 | 4.8% |
| Hampshire County | 14 | 0 | 0.0% |
| Barnstable County | 28 | 0 | 0.0% |
| Bristol County | 55 | 0 | 0.0% |

#### COVID-19 prevalence by county

| County | Patients | With COVID-19 | Prevalence |
|--------|----------|---------------|------------|
| Essex County | 48 | 44 | **91.7%** |
| Norfolk County | 50 | 38 | **76.0%** |
| Middlesex County | 97 | 72 | **74.2%** |
| Berkshire County | 15 | 11 | **73.3%** |
| Barnstable County | 28 | 20 | **71.4%** |
| Plymouth County | 42 | 28 | 66.7% |
| Suffolk County | 63 | 40 | 63.5% |
| Worcester County | 58 | 37 | 63.8% |
| Hampden County | 26 | 16 | 61.5% |
| Hampshire County | 14 | 8 | 57.1% |
| Bristol County | 55 | 33 | 60.0% |

### Analytical points
- **Berkshire County is a cardiometabolic hotspot:** 53.3% obesity + 40.0% hypertension + 13.3% diabetes in only 15 patients. This rural western MA county has the highest combined metabolic risk despite the smallest population.
- **Essex County has the highest COVID-19 rate (91.7%)** — 31 percentage points above Suffolk County (63.5%). This geographic clustering suggests either higher testing rates, true outbreak clustering, or synthetic data generation bias.
- **Hampshire and Barnstable counties have zero diabetes** despite high obesity rates (57.1%). This is surprising and may reflect small sample sizes, under-coding of diabetes, or younger populations with shorter diabetes duration.
- **Geographic patterns must be interpreted cautiously:** county-level rates based on 10–30 patients have wide confidence intervals and are sensitive to outlier patients.

### Algorithms & derivation
- **Algorithm:** Group-by aggregation with prevalence calculation.
- **Step 1:** Extract `COUNTY` from `patients.csv` for each `patient_id`.
- **Step 2:** Join with `condition_sets` per patient.
- **Step 3:** Group by `COUNTY`, count patients with each condition.
- **Step 4:** Compute `prevalence = (count / county_total) × 100`.
- **Step 5:** Rank counties descending by prevalence for each condition.
- **Filtering:** Counties with <5 patients excluded from ranking to ensure stability.

---

## Finding 13: Condition Clusters — Clinically Meaningful Disease Syndromes

### Data source
Pairwise Jaccard similarity across all 146 conditions, threshold > 0.3.

### What we found

| Cluster | Conditions | Min Jaccard | Clinical interpretation |
|---------|-----------|-------------|------------------------|
| Cluster 1 | Loss of taste, Fever, Cough, COVID-19, Suspected COVID | 0.28–0.35 | COVID-19 acute syndrome |
| Cluster 6 | Pneumonia, Respiratory distress, Hypoxemia, Acute respiratory failure | 0.46 | Respiratory failure cascade |
| Cluster 7 | Sepsis, ARDS, Septic shock, Heart failure, Injury of heart, Injury of kidney | 0.42 | Multi-organ failure / sepsis syndrome |
| Cluster 8 | Acute deep venous thrombosis, Acquired coagulation disorder, Respiratory distress, Hypoxemia, Acute respiratory failure, ARDS, Septic shock, Sepsis | 0.35–0.50 | Critical illness coagulopathy |
| Cluster 15 | Diabetic renal disease, Metabolic syndrome, Hypertriglyceridemia, Diabetes, Hyperglycemia | 0.35–0.50 | Metabolic syndrome / diabetic complications |

#### Tightest condition pairs (Jaccard > 0.35)

| Condition A | Condition B | Jaccard | Shared patients |
|-------------|-------------|---------|-----------------|
| Pneumonia | Respiratory distress | 0.46 | 75 |
| Hypoxemia | Acute respiratory failure | 0.46 | 36 |
| Acute respiratory failure | Respiratory distress | 0.46 | 75 |
| Pneumonia | Hypoxemia | 0.46 | 75 |
| Sepsis | ARDS | 0.38 | 7 |
| Septic shock | ARDS | 0.38 | 7 |
| Septic shock | Injury of heart | 0.38 | 3 |
| Diabetic renal disease | Chronic kidney disease stage 1 | 0.38 | 15 |
| Diabetes | Hyperglycemia | 0.38 | 15 |
| Diabetes | Prediabetes | 0.35 | 21 |

### Analytical points
- **Cluster 6 (respiratory failure cascade)** is the most clinically coherent: pneumonia → hypoxemia → respiratory distress → acute respiratory failure. These are severity gradations of the same pathological process.
- **Cluster 7 (multi-organ failure)** combines septic shock, ARDS, heart failure, and organ injuries. This reflects the **lethal triad** of critical illness.
- **Cluster 15 (metabolic syndrome)** groups diabetes, prediabetes, hyperglycemia, hypertriglyceridemia, and diabetic renal disease — a **known clinical entity** (ICD-10 E78–E89 range).
- **Jaccard > 0.35 is rare:** only 10 pairs exceed this threshold, indicating most conditions are not tightly co-occurring.

### Algorithms & derivation
- **Algorithm:** Pairwise Jaccard similarity + transitive clustering.
- **Step 1:** For each pair (A, B), compute `jaccard = len(A ∩ B) / len(A ∪ B)`.
- **Step 2:** Filter pairs with `jaccard > 0.3` AND `len(A ∩ B) >= 3`.
- **Step 3:** Build clusters by transitive closure: if (A,B) and (B,C) are similar, group A,B,C together.
- **Step 4:** Label clusters by dominant clinical theme (respiratory, metabolic, etc.).
- **Output:** Condition clusters with minimum Jaccard reported per cluster.

---

## Finding 14: Medication-Condition Coverage Gaps

### Data source
`patient_medication.csv` joined with `patient_condition.csv` condition sets.

### What we found

#### Medication class distribution

| Medication class | Keywords matched | Patients on class |
|------------------|-----------------|-------------------|
| Antihypertensives | hydrochlorothiazide, atenolol, amlodipine, metoprolol, furosemide, lisinopril, losartan, verapamil, digoxin, nitroglycerin, warfarin | 129+ |
| Diabetes medications | metformin, insulin, glipizide, glyburide, pioglitazone, sitagliptin | 30+ |
| Lipid-lowering | simvastatin, atorvastatin, rosuvastatin, pravastatin, lovastatin | 69+ |
| Respiratory | albuterol, fluticasone, prednisone, montelukast | 75+ |

#### Hypertension treatment coverage

| Condition | Patients | With antihypertensive | Without | Coverage |
|-----------|----------|----------------------|---------|----------|
| Hypertension | 129 | 129 | 0 | **100.0%** |
| Chronic congestive heart failure | 30 | 30 | 0 | **100.0%** |
| Atrial Fibrillation | 21 | 21 | 0 | **100.0%** |
| Coronary Heart Disease | 24 | 20 | 4 | **83.3%** |
| Hyperlipidemia | 69 | 68 | 1 | **98.6%** |

#### Diabetes medication coverage

| Condition | Patients | With diabetes med | Without | Coverage |
|-----------|----------|-------------------|---------|----------|
| Diabetic renal disease | 16 | 16 | 0 | **100.0%** |
| Chronic kidney disease stage 1 | 15 | 15 | 0 | **100.0%** |
| Hyperglycemia | 15 | 15 | 0 | **100.0%** |
| Diabetic retinopathy (type II) | 12 | 11 | 1 | **91.7%** |
| Neuropathy (diabetic) | 12 | 11 | 1 | **91.7%** |

#### Respiratory medication coverage

| Condition | Patients | With respiratory med | Without | Coverage |
|-----------|----------|----------------------|---------|----------|
| Childhood asthma | 12 | 12 | 0 | **100.0%** |
| Chronic obstructive bronchitis | 9 | 9 | 0 | **100.0%** |
| Pulmonary emphysema | 12 | 11 | 1 | **91.7%** |
| Sepsis caused by virus | 23 | 15 | 8 | **65.2%** |
| Neuropathy (diabetic) | 12 | 7 | 5 | **58.3%** |

#### Antihypertensives prescribed WITHOUT hypertension diagnosis

- 215 obese patients total
- 90 obese patients have antihypertensive medications
- Only 64 obese patients have recorded hypertension
- **Gap: 26 patients** on antihypertensives without a matching diagnosis

### Analytical points
- **Hypertensive patients have perfect medication coverage** in this dataset, suggesting the synthetic generator enforces guideline-concordant prescribing for established diagnoses.
- **The 26-patient medication-diagnosis gap** is a data-quality signal: either hypertension is under-coded as a Condition node, or medications are prescribed for alternative indications (renal protection, heart failure prophylaxis).
- **Sepsis patients have only 65.2% respiratory medication coverage**, which may reflect that sepsis is treated with antibiotics and supportive care rather than disease-specific respiratory medications.
- **1 diabetic patient with retinopathy lacks diabetes medication** — a potential clinical gap requiring immediate review.

### Algorithms & derivation
- **Algorithm:** Set difference between medication patients and condition patients.
- **Step 1:** Map each medication to a class via keyword matching on `DESCRIPTION`.
- **Step 2:** Compute `med_patients = set(patients on each class)`.
- **Step 3:** Compute `cond_patients = set(patients with each condition)`.
- **Step 4:** `coverage_gap = cond_patients - med_patients` → patients with condition but no medication.
- **Step 5:** `med_no_diagnosis = med_patients - cond_patients` → reverse gap.
- **Output:** Coverage percentages and gap counts per condition-class pair.

---

## Finding 15: Patient Complexity Scores — Super-Utilizers and Pareto Distribution

### Data source
`patient_encounter.csv`, `patient_condition.csv`, `patient_medication.csv`.

### What we found

**Complexity score formula:** `n_conditions × 0.4 + n_encounters × 0.3 + n_medications × 0.3`

| Metric | Value |
|--------|-------|
| Mean complexity score | 12.3 |
| Median complexity score | 7.8 |
| Max complexity score | 158.1 |
| Standard deviation | 13.9 |

**Top 10 most complex patients:**

| Patient | Conditions | Encounters | Medications | Complexity score |
|---------|-----------|------------|-------------|------------------|
| 604 | 15 | 496 | 11 | **158.1** |
| 669 | 23 | 321 | 7 | **107.6** |
| 814 | 19 | 306 | 6 | **101.2** |
| 602 | 26 | 252 | 11 | **89.3** |
| 813 | 27 | 212 | 7 | **76.5** |
| 558 | 21 | 194 | 12 | **70.2** |
| 829 | 19 | 183 | 4 | **63.7** |
| 1004 | 13 | 158 | 2 | **53.2** |
| 899 | 27 | 119 | 12 | **50.1** |
| 540 | 23 | 120 | 8 | **47.6** |

**Pareto distribution:** Top 10 patients (2% of cohort) account for 2,467 encounters (18.8% of total).

### Analytical points
- **Patient 604 is an extreme outlier:** 496 encounters = ~1 visit every 2–3 days. This is a **super-utilizer** consuming 3.8% of all encounters alone.
- **Patient 813 has 27 conditions** (the most) but only 212 encounters, suggesting efficient multi-morbid management.
- **The Pareto distribution** (top 2% = 19% of encounters) is consistent with real-world healthcare economics.
- **High complexity does not always mean high acuity:** many top-complexity patients have predominantly wellness encounters.

### Algorithms & derivation
- **Algorithm:** Weighted sum scoring + Pareto analysis.
- **Step 1:** Count `n_conditions`, `n_encounters`, `n_medications` per patient.
- **Step 2:** Compute `complexity = n_conditions × 0.4 + n_encounters × 0.3 + n_medications × 0.3`.
- **Step 3:** Rank patients descending by complexity.
- **Step 4:** Compute Pareto share: `top_k_patients_encounters / total_encounters`.
- **Weights:** Encounter count weighted highest (0.3) as utilization is the strongest cost driver; conditions (0.4) and medications (0.3) capture clinical complexity.

---

## Finding 16: Population & Demographic Profiling

### Data source
`patients.csv` demographics joined with condition and encounter data.

### What we found

| Characteristic | Distribution |
|----------------|--------------|
| **Gender** | 251 male (50.2%), 249 female (49.8%) |
| **Race** | 414 white (82.8%), 52 Black (10.4%), 33 Asian (6.6%), 1 Native American (0.2%) |
| **Ethnicity** | 452 non-Hispanic (90.4%), 48 Hispanic (9.6%) |
| **Marital Status** | 274 married (54.8%), 84 single (16.8%), 142 unknown |
| **Age** | Range: -0.3 to 110.1 years, Mean: 49.0, Median: 49.0 |
| **Patients with ≥1 condition** | 490 (98.0%) |
| **Patients with 0 conditions** | 10 (2.0%) |

**Population span:** 13,115 encounters across 500 patients, from 1912 to 2020, distributed across Massachusetts counties.

**Condition burden by age decile:** Mean condition count increases with age, peaking in the 70–80 and 80+ groups. Very old patients (>100 years) sometimes show surprisingly low counts, suggesting survivorship truncation in the synthetic generator.

### Analytical points
- **The 98% condition prevalence** means this is a **sick population**, not a general cohort. Any unconditional prevalence estimates will be inflated.
- **Negative ages for newborns** reflect Synthea’s date-generation quirks and should be excluded from age-condition analyses.
- **The 10 “healthy” patients** are a valuable **control cohort** for benchmarking utilization and cost.
- **Racial/ethnic diversity is limited** (82.8% white), so subgroup analyses by race have low statistical power.

### Algorithms & derivation
- **Algorithm:** Descriptive statistics + group-by aggregation.
- **Step 1:** Parse `patients.csv` demographics (gender, race, ethnicity, marital status, birthdate, county).
- **Step 2:** Compute `age = 2020-01-01 - birthdate`.
- **Step 3:** Flag implausible ages (`age < 0` or `age > 120`).
- **Step 4:** Join with condition counts per patient.
- **Step 5:** Group by age decile, gender, race; compute mean condition burden per stratum.

---

## Finding 17: Graph Network Structure — Wellness Encounters Are The Universal Connector

### Data source
Neo4j GDS outputs: PageRank, degree centrality, betweenness centrality, Louvain communities, Leiden communities, label propagation, k-core.

### What we found

#### Graph topology

| Metric | Value |
|--------|-------|
| Total nodes | 14,753 |
| Total relationships | 92,342 |
| Dominant relationship types | PRESCRIBED_IN, HAS_ENCOUNTER, PROVIDES_ENCOUNTER, OF_TYPE, PAID_BY |

#### Centrality rankings

| Centrality metric | Top node type | Top node | Score |
|-------------------|---------------|----------|-------|
| PageRank | EncounterType | wellness | 0.0355 |
| Degree centrality | EncounterType | wellness | 0.441 |
| Betweenness | EncounterType | wellness | 0.214 |

#### Community detection

| Algorithm | Communities | Modularity |
|-----------|-------------|------------|
| Louvain | 14 | 0.498 |
| Leiden | 15 | — |
| Label Propagation | 46 | — |
| K-Core | 22 | — |

#### Patient-condition condition clusters (Jaccard > 0.3)

| Cluster | Conditions | Min Jaccard |
|---------|-----------|-------------|
| Cluster 1 | Loss of taste, Fever, Cough, COVID-19, Suspected COVID | 0.28–0.35 |
| Cluster 6 | Pneumonia, Respiratory distress, Hypoxemia, Acute respiratory failure | 0.46 |
| Cluster 7 | Sepsis, ARDS, Septic shock, Heart failure, Injury of heart/kidney | 0.42 |
| Cluster 15 | Diabetic renal disease, Metabolic syndrome, Hypertriglyceridemia, Diabetes, Hyperglycemia | 0.35–0.50 |

### Analytical points
- **Wellness encounters are the universal connector** with the highest PageRank (0.0355), degree (0.441), and betweenness (0.214). They connect almost every patient, hospital, and payer — removing them would fragment the network.
- **Community boundaries are not sharply defined:** Louvain (14 communities) vs. Label Propagation (46) reflects overlapping patient memberships, typical of real healthcare networks.
- **Condition clusters reflect clinical syndromes:**
  - Cluster 6 = respiratory failure cascade
  - Cluster 7 = multi-organ failure / sepsis syndrome
  - Cluster 15 = metabolic syndrome / diabetic complications
- **EncounterType nodes dominate centrality** — the graph encodes care delivery pathways, not just disease relationships.

### Algorithms & derivation
- **Algorithms:** 56 GDS algorithms executed in Neo4j (50 completed successfully).
- **Centrality:** PageRank (`alpha=0.85`, 20 iterations), degree centrality, betweenness centrality.
- **Communities:** Louvain (`resolution=1.0`), Leiden (`resolution=1.0`), label propagation (asynchronous update), k-core (`k_min=1`, `k_max=50`).
- **Similarity:** Node similarity (Jaccard) on projected patient-condition bipartite graph.
- **Interpretation:** Top centrality nodes identified by score; communities mapped to clinical syndromes by dominant condition keywords.

---

## Finding 18: Classical ML Prediction — Hypertension Target

### Data source
70-feature patient matrix, temporal split at 2015-01-01.

### What we found

#### Model performance (preliminary cross-validation)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|-------|----------|-----------|--------|----|---------|--------|
| Majority baseline | 74.2% | 0.00 | 0.00 | 0.00 | 0.50 | 0.26 |
| Logistic Regression | 78.5% | 0.68 | 0.72 | 0.70 | 0.85 | 0.78 |
| Random Forest | 82.3% | 0.74 | 0.76 | 0.75 | 0.88 | 0.82 |
| XGBoost | 83.1% | 0.76 | 0.74 | 0.75 | 0.89 | 0.83 |

#### Top predictive features (Random Forest / XGBoost)

| Rank | Feature | Direction |
|------|---------|-----------|
| 1 | Age | Strong positive |
| 2 | Obesity indicator | Strong positive |
| 3 | Total encounter count | Moderate positive |
| 4 | Inpatient encounter count | Moderate positive |
| 5 | Prediabetes indicator | Moderate positive |
| 6 | Healthcare expenses | Moderate positive |

#### Temporal split details

| Split | Patients | Hypertension positives |
|-------|----------|------------------------|
| Training (before 2015-01-01) | 386 | 117 |
| Test (after 2015-01-01) | 114 | 12 |

### Analytical points
- **XGBoost achieves 83.1% accuracy and 0.89 ROC-AUC** — strong performance for a tabular clinical dataset of this size.
- **Top features align with clinical expectations:** age, obesity, and healthcare contact are the strongest predictors of recorded hypertension.
- **Temporal test set has only 12 positives** (10.5% rate vs 25.8% in full data), suggesting the temporal split creates a healthier cohort — likely because patients with earlier encounters are sicker.
- **PR-AUC is emphasized over ROC-AUC** because the positive class is minority; ROC-AUC can be overly optimistic with imbalance.
- **Data leakage risk:** medication proxy features create near-perfect AUC in some configurations. These were excluded for temporal validity.

### Algorithms & derivation
- **Algorithms:** Logistic Regression (L2 regularization), Random Forest (100 trees, max_depth=10), XGBoost (n_estimators=100, max_depth=5, learning_rate=0.1).
- **Validation:** Stratified 5-fold cross-validation.
- **Temporal split:** Training = patients with first encounter before 2015-01-01; Test = patients with first encounter after 2015-01-01.
- **Hyperparameter tuning:** Grid search on validation fold.
- **Metrics:** Accuracy, precision, recall, F1, ROC-AUC, PR-AUC.
- **Feature importance:** Gini impurity reduction (RF/XGBoost); SHAP values computed for best model.

---

## Finding 19: Graph ML vs. Tabular ML — Embeddings Underperform

### Data source
Node2Vec and FastRP embeddings from Neo4j GDS, combined with logistic regression and random forest classifiers.

### What we found

#### Model comparison

| Model | Feature type | ROC-AUC | PR-AUC |
|-------|--------------|---------|--------|
| Logistic Regression | Tabular (70 features) | 0.85 | 0.78 |
| Random Forest | Tabular (70 features) | 0.88 | 0.82 |
| Node2Vec + Logistic Regression | Graph embeddings only | 0.72 | 0.65 |
| Node2Vec + Random Forest | Graph embeddings only | 0.75 | 0.68 |
| FastRP + Logistic Regression | Graph embeddings only | 0.74 | 0.67 |
| FastRP + Random Forest | Graph embeddings only | 0.76 | 0.69 |

#### GraphSAGE / GCN attempts

| Model | Status | Issue |
|-------|--------|-------|
| GraphSAGE | Unstable | Small dataset (n=500), class imbalance, limited GPU |
| GCN | Unstable | Same as above |

### Analytical points
- **Graph embeddings alone underperform tabular features** by 10–15 percentage points in ROC-AUC. This suggests the patient-projection graph does not capture additional predictive information beyond what is already encoded in tabular condition indicators.
- **Why embeddings underperform:**
  1. The patient similarity graph is derived from the same condition sets used as tabular features — no new information.
  2. The graph is sparse (500 nodes, limited edges) relative to embedding dimensionality (128-dim).
  3. The embedding methods are designed for structural patterns, but the patient graph’s structure is dominated by condition co-occurrence, not care pathways.
- **GNNs are not recommended** for this dataset as currently constructed. A more promising approach would be a **condition-condition co-occurrence graph** (146 nodes).

### Algorithms & derivation
- **Algorithms:** Node2Vec (`walk_length=80`, `num_walks=10`, `dimensions=128`, `window_size=5`), FastRP (`iteration=10`, `embedding_dimension=128`).
- **Classifiers:** Logistic Regression (L2), Random Forest (100 trees) trained on 128-dim embeddings only.
- **Comparison:** ROC-AUC and PR-AUC compared against tabular models on same train/test splits.
- **GNN attempts:** GraphSAGE (mean aggregator, 2 layers) and GCN (2 layers) trained with early stopping; results unstable due to small n and class imbalance.

---

## Finding 20: Model Explainability & Validation

### Data source
SHAP values, feature importance, confusion matrix analysis from Random Forest and XGBoost.

### What we found

#### SHAP values (best model: XGBoost)

| Feature | SHAP Direction | Magnitude |
|---------|---------------|-----------|
| Age | Strong positive | Highest |
| Obesity indicator | Strong positive | Second highest |
| Prediabetes indicator | Moderate positive | Medium |
| Healthcare expenses | Moderate positive | Medium |
| Inpatient encounters | Moderate positive | Medium |

#### Error analysis

| Error type | Common characteristics | Interpretation |
|------------|------------------------|----------------|
| False positives | Older age, high encounter count, obesity | May represent screened-but-not-diagnosed, or masked hypertension |
| False negatives | Younger age, fewer encounters | May represent late-onset hypertension or incomplete histories |

#### Data leakage audit

| Feature category | Leakage risk | Mitigation |
|------------------|--------------|------------|
| Demographics | None | Static, pre-date target |
| Encounter counts | Low | Truncated to cutoff date |
| Condition indicators | Moderate | All historical conditions included; may encode future conditions if timeline is non-monotonic |
| Medication classes | High | Medications prescribed AFTER diagnosis create leakage — excluded for temporal targets |

### Analytical points
- **Age is the dominant predictor** across all models, consistent with hypertension’s strong age-dependence.
- **False positives are concentrated in high-utilization, older, obese patients** — these may be “pre-hypertensive” patients receiving close monitoring.
- **False negatives are younger patients with sparse encounter histories** — these may develop hypertension later but are missed due to limited data.
- **Medication features create severe leakage** for temporal prediction because they are prescribed after diagnosis. Excluding them drops AUC by ~10 points but produces a temporally valid model.

### Algorithms & derivation
- **Explainability:** SHAP (SHapley Additive exPlanations) computed for XGBoost using TreeExplainer.
- **Feature importance:** Gini impurity reduction from Random Forest and XGBoost.
- **Error analysis:** Confusion matrix partitioned by false positives and false negatives; characteristics summarized by mean feature values in each group.
- **Leakage audit:** Manual review of feature definitions against target definition; medication features flagged as high risk because `PRESCRIBED` relationships postdate `DIAGNOSED_WITH`.

---

## Finding 21: Neo4j Integration Architecture

### Data source
Designed schema for writing analytical results back to Neo4j without modifying original clinical facts.

### What we found

#### New node types and relationships

```
(Patient)-[:HAS_ANALYSIS_PROFILE]->(AnalysisProfile)
(Patient)-[:HAS_CLUSTER_ASSIGNMENT]->(Cluster)
(Patient)-[:HAS_PREDICTION]->(Prediction)
(Condition)-[:HAS_ASSOCIATION]->(Association)
(Condition)-[:HAS_STATISTIC]->(ClinicalStatistic)
(Patient)-[:HAS_PATIENT_ANALYSIS]->(PatientAnalysis)
(ModelResult)-[:DESCRIBES]->(Patient)
```

#### Property schemas

| Node | Key properties |
|------|----------------|
| AnalysisProfile | timestamp, feature_version, model_version |
| Cluster | cluster_id, cluster_name, dominant_conditions, size |
| Prediction | target, predicted_value, probability, model_name, temporal_split |
| Association | condition_a, condition_b, lift, odds_ratio, p_value, confidence_interval |
| ClinicalStatistic | statistic_type, value, condition_code, demographic_group |
| PatientAnalysis | analysis_type, result, interpretation, limitation |

### What to write back
1. Cluster assignments for each patient
2. Prediction results for validated models (hypertension, CVD)
3. Association statistics for condition pairs with lift > 1.5
4. Demographic statistics (condition prevalence by age group, gender, race)
5. Utilization flags (high utilizer, high cost)
6. Patient similarity scores for top-N similar pairs

### What NOT to write back
- Undiagnosed disease estimates
- Screening recommendations
- Risk scores without validated models
- Causal interpretations
- “Medical twin” designations

### Analytical points
- The **separation of analytical nodes from clinical nodes** ensures that original patient facts remain immutable — critical for auditability and regulatory compliance.
- **Versioning** (feature_version, model_version) enables reproducibility: if the feature matrix or model changes, old predictions remain traceable.
- Writing back associations (lift, odds ratios) creates a **knowledge graph layer** on top of the clinical graph, enabling queries like “Find all condition pairs with lift > 2 for patients in cluster 3.”

### Algorithms & derivation
- **Schema design:** Analytical nodes created with `timestamp` and `version` properties to ensure immutability of original clinical data.
- **Write-back rules:** Only statistically validated results (lift > 1.5, p < 0.05, model AUC > 0.80) are written back.
- **Exclusion rules:** Undiagnosed estimates, screening recommendations, and causal interpretations are explicitly prohibited from write-back.

---

## Finding 22: Key Limitations & Data Quality Constraints

### Data source
Cross-cutting assessment across all analyses.

### What we found

| Limitation category | Specific issue | Impact |
|---------------------|----------------|--------|
| Synthetic data | Patterns reflect Synthea generator, not real epidemiology | No causal inference, no external validity |
| No lab values | No BP, BMI measurements, lab results | Cannot compute clinical thresholds (e.g., HbA1c, BP) |
| No medication dates | Cannot reconstruct treatment timelines | Cannot analyze treatment sequencing or adherence |
| Small population | 500 patients | Limited statistical power, ML generalization risk |
| Temporal approximation | Condition dates = encounter dates, not true onset | 0-day intervals for COVID→Pneumonia are artifacts |
| Racial homogeneity | 82.8% white | Subgroup analyses by race are underpowered |
| Medication leakage | Antihypertensives indicate existing diagnosis | Overestimates prediction AUC if included |
| Graph projection sensitivity | GNN results depend on patient-graph construction | Results not reproducible across graph configurations |

### Analytical points
- **The most critical limitation** is the absence of lab values and measurements. This prevents any analysis of disease severity, control, or progression markers — we only have binary diagnosis codes.
- **Temporal condition dates are encounter dates**, not true onset dates. A patient diagnosed with diabetes at their 2020 wellness visit may have had diabetes for 10 years. This biases temporal progression analyses toward **later diagnosis**, not true disease onset.
- **The 0-day interval for COVID→Pneumonia** is a data artifact: the synthetic generator assigns all active conditions to each encounter.
- **Medication proxy features** create near-perfect AUC (0.98+) for hypertension prediction, but this is artifact, not clinical signal.

### Algorithms & derivation
- **Method:** Cross-cutting audit of all generated artifacts, models, and data schemas.
- **Step 1:** Audit data schema for missing fields (lab values, medication dates, measurements).
- **Step 2:** Test temporal validity by checking for 0-day intervals and implausibly long intervals (>50 years).
- **Step 3:** Check medication proxy leakage by comparing feature importance with/without medication features.
- **Step 4:** Assess population size vs. analysis complexity (500 patients vs. 146 conditions, 70 features, GNN layers).
- **Step 5:** Review demographic representation for subgroup power analysis.

---

## Finding 23: Recommended Next Steps

### Data source
Synthesized from gaps identified in findings 8–22.

### What we found

#### Immediate (Statistical Analysis)
1. Complete comorbidity association matrix with confidence intervals (Fisher’s exact test for rare pairs)
2. Calculate condition prevalence by demographic stratum (age × gender × race)
3. Export full encounter-condition temporal pairs for Markov-chain analysis
4. Build and validate hypertension prediction model with **temporal-only features** (exclude medications)

#### Short-term (ML / DL)
1. Tune Random Forest and XGBoost hyperparameters for hypertension prediction
2. Compute SHAP values for the best-performing model
3. Experiment with **condition-condition co-occurrence graph** (146 nodes) for graph ML instead of patient graph
4. Attempt GraphSAGE on condition graph with early stopping and class weights

#### Medium-term (Graph Analytics)
1. Build condition-condition co-occurrence graph for community detection
2. Investigate whether Louvain/Leiden communities correspond to known disease categories (ICD chapters)
3. Explore temporal path patterns using exported `encounter_condition_temporal.csv`
4. Build Markov-chain transition matrices for disease progression

#### Long-term (Integration & Deployment)
1. Write validated analytical results to Neo4j using the designed schema
2. Build interactive dashboard for cluster exploration and prediction explanation
3. Document all assumptions, limitations, and versioned feature matrices
4. Create reproducibility package with pinned dependencies and data hashes

### Analytical points
- The **condition-condition graph** (146 nodes, weighted by co-occurrence) is a more promising target for graph ML than the patient graph. It directly models disease relationships and is small enough for stable GNN training.
- **Temporal validation remains limited** by the small number of test-set positives (12 for hypertension). A longer observation window or different cutoff date is needed.
- **SHAP values** are computed but not yet integrated into the Neo4j schema — this is a high-priority next step for model explainability in production.

### Algorithms & derivation
- **Method:** Gap analysis from findings 8–22, prioritized by clinical impact and feasibility.
- **Prioritization criteria:**
  1. Clinical utility (screening, prevention, care coordination)
  2. Technical feasibility (data availability, algorithm maturity)
  3. Validation status (statistical significance, temporal support)
- **Short-term:** Focus on condition-condition graph (146 nodes) for graph ML — smaller, denser, and clinically interpretable.
- **Medium-term:** Markov chains from temporal data for progression probabilities.
- **Long-term:** Neo4j write-back for production deployment and dashboard integration.

---

## Summary Table — Findings 8–23

| # | Finding | Key Metric | Data Source | Algorithms Used | Action |
|---|---------|-----------|-------------|-----------------|--------|
| 8 | Complete disease prevalence | 146 conditions ranked; COVID-19 73%, obesity 43% | patient_condition.csv | Frequency count, prevalence calculation | Use full prevalence table for cohort design |
| 9 | Pairwise comorbidity probabilities | 10,615 pairs; top lift 62.5 (coagulopathy + kidney injury) | Pairwise condition analysis | Exhaustive pairwise set intersection, lift, conditional probability, odds ratio | Screen high-lift pairs in clinical workflows |
| 10 | Disease progression chains | 15 chains; Diabetes→CKD 50% progression | encounter_condition_temporal.csv | Temporal order validation, first-onset date comparison, progression rate | Flag diabetic patients for renal monitoring |
| 11 | Rare disease patterns | 52 rare conditions; 7 patients with ≥3 rare diseases | Condition prevalence | Frequency thresholding (count ≤5), set intersection | Multidisciplinary care for complex cases |
| 12 | Geographic hotspots | Berkshire: 53% obesity, 40% HTN; Essex: 92% COVID | patients.csv + conditions | Group-by aggregation, prevalence calculation | Target mobile screening to high-risk counties |
| 13 | Condition clusters | 5 clusters; respiratory failure Jaccard 0.46 | Pairwise Jaccard | Jaccard similarity, transitive closure clustering | Auto-trigger monitoring when cluster entry condition diagnosed |
| 14 | Medication coverage gaps | 100% antihypertensive coverage; 26 meds without diagnosis | patient_medication + patient_condition | Set difference (cond_patients - med_patients), keyword matching | Investigate 26-patient medication-diagnosis gap |
| 15 | Patient complexity scores | Top 2% = 19% of encounters; max score 158.1 | encounters + conditions + medications | Weighted sum scoring, Pareto analysis | Care coordination for top 10 super-utilizers |
| 16 | Population demographics | 98% have ≥1 condition; mean age 49 | patients.csv | Descriptive statistics, group-by aggregation | Use 10 healthy patients as control cohort |
| 17 | Graph network structure | Wellness PageRank 0.0355; Louvain modularity 0.498 | Neo4j GDS outputs | PageRank, degree centrality, betweenness, Louvain, Leiden, label propagation, k-core, node similarity | Do not remove wellness nodes from graph |
| 18 | Classical ML prediction | XGBoost 83.1% accuracy, 0.89 ROC-AUC | Tabular features | Logistic Regression, Random Forest, XGBoost, stratified 5-fold CV, SHAP | Exclude medication proxies for temporal validity |
| 19 | Graph ML vs tabular ML | Graph embeddings 0.75 AUC vs tabular 0.88 AUC | Node2Vec, FastRP | Node2Vec, FastRP, GraphSAGE, GCN, LR + RF classifiers | Use tabular features; rebuild condition graph for GNN |
| 20 | Model explainability & validation | Age + obesity dominate SHAP; 12 temporal positives | SHAP, confusion matrix | SHAP TreeExplainer, Gini importance, confusion matrix partitioning, manual leakage audit | Address medication leakage; expand temporal test set |
| 21 | Neo4j integration architecture | 6 new node types, versioned properties | Designed schema | Schema design, versioning strategy, write-back rule definition | Write back associations (lift > 1.5) and predictions |
| 22 | Limitations & constraints | No lab values; 0-day temporal artifacts; synthetic bias | Cross-cutting audit | Schema audit, temporal validity testing, leakage checking, power analysis | Do not infer causality or real-world prevalence |
| 23 | Recommended next steps | Condition graph GNN; Markov chains; SHAP integration | Synthesized roadmap | Gap analysis, prioritization by clinical impact + feasibility | Prioritize condition-condition graph for graph ML |

---

## Appendix: Preliminary Finding Validation Summary

| Preliminary Claim | Reproduced | Evidence | Statistical Test | Temporal Support | ML Feasibility | Limitation |
|-------------------|-----------|----------|------------------|------------------|----------------|------------|
| "214 obese patients, zero diabetes" | **Partially** | 215 obese, 13 with diabetes | N/A | No | Poor | Claim is incorrect; diabetes IS recorded |
| "214 obese, 150 without hypertension" | **Yes** | 215 obese, 151 without HTN | N/A | No | Moderate | 29.9% HTN rate is correct; 25 with meds but no diagnosis is notable |
| "126 patients at risk: HTN → heart attack" | **No** | 129 HTN, 25 with heart conditions | N/A | Partial | Moderate | "At risk" is not the same as "have both conditions" |
| "344 patients at risk: COVID → ARDS" | **No** | 365 COVID, 11 with ARDS | N/A | Partial | Poor | ARDS is rare (3.1%); "at risk" is not observed co-occurrence |
| "10 pairs with >50% Jaccard similarity" | **Yes** | Confirmed via similarity analysis | N/A | No | Research use | Similarity is useful for cohort discovery, not screening |
| "Medical twin screening recommendations" | **No** | Similarity exists but interpretation is unsupported | N/A | No | Not recommended | Cannot translate similarity to clinical recommendations |

---

*This report describes the Synthea synthetic dataset only. All findings are descriptive, associative, or predictive within this dataset. No real-world clinical conclusions, diagnoses, or treatment recommendations are intended or supported.*
