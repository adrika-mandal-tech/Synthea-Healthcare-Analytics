# 7 Practical Findings From Our GDS Analysis

Each finding explains: what algorithm I used, how it works, what I found, and what you can actually DO with it.

---

## Finding 1: Anemia + Prediabetes Are Suspiciously Linked (Lift = 2.71)

### Which algorithm?
**Disease Co-occurrence Analysis** — I built a bipartite graph (Patient ↔ Condition), then counted how often every pair of diseases appears in the same patient.

### How it works mathematically?
I used a metric called **Lift** to find disease pairs that appear together MORE often than you'd expect by random chance.

```
Lift = P(Disease A AND Disease B) / (P(Disease A) × P(Disease B))
```

- **Lift = 1.0** → The two diseases appear together exactly as often as you'd expect by chance. No relationship.
- **Lift > 1.0** → They appear together MORE than expected. Something links them.
- **Lift < 1.0** → They appear together LESS than expected. They avoid each other.

### What I found?

| Disease Pair | Patients with Both | Lift | Meaning |
|---|---|---|---|
| **Anemia + Prediabetes** | **131 patients** | **2.71** | Appear together 2.71x more than chance — strongest non-COVID link |
| COVID-19 + Fever | 314 patients | 1.34 | Expected (fever is a COVID symptom) |
| Obesity + Hypertension | 64 patients | ~0.94 | Slightly LESS than expected — surprising |

The Anemia + Prediabetes pair has a Lift of **2.71** — the highest non-trivial Lift in the entire database. This means patients with anemia are 2.71 times more likely to also have prediabetes than you'd expect if the two were unrelated.

### Why this matters?
This is a known medical relationship — iron deficiency affects insulin metabolism. But the point is: **the graph found it automatically, without anyone telling it to look for it.** If this were a real hospital system, the algorithm would flag this pattern and a doctor could say: "Every anemia patient should be screened for prediabetes."

### The actual Cypher query to find these patients:
```cypher
MATCH (p:Patient)-[:HAS_CONDITION]->(c1:Condition {DESCRIPTION: 'Anemia (disorder)'})
WHERE NOT (p)-[:HAS_CONDITION]->(:Condition {DESCRIPTION: 'Prediabetes'})
RETURN p.name AS patient_to_screen
```

---

## Finding 2: 214 Obese Patients Are NOT Being Screened for Diabetes

### Which algorithm?
**Undiagnosed Risk Detection** — Using the graph's Patient → HAS_CONDITION → Condition paths, I checked known medical progression chains: "If you have Disease A, you're at risk for Disease B."

### How it works?
I defined known medical progressions:
```
Obesity → Diabetes (risk factor)
Obesity → Hypertension (risk factor)
Prediabetes → Diabetes (progression)
Hypertension → Heart Attack (complication)
COVID-19 → ARDS (complication)
```

Then for each chain, I counted:
- How many patients have the SOURCE condition
- How many of those ALSO have the TARGET condition (already progressed)
- How many have the source but NOT the target (**at risk but undiagnosed**)

### What I found?

| Risk Chain | Have Source | Already Progressed | AT RISK (not yet diagnosed) | Progression Rate |
|---|---|---|---|---|
| **Obesity → Diabetes** | **214** | **0** | **214 patients** | **0%** |
| **Obesity → Hypertension** | **214** | **64** | **150 patients** | **29.9%** |
| **Hypertension → Heart Attack** | **129** | **3** | **126 patients** | **2.3%** |
| **COVID → ARDS** | **355** | **11** | **344 patients** | **3.1%** |
| **Prediabetes → Diabetes** | **161** | **0** | **161 patients** | **0%** |
| **Suspected COVID → Confirmed** | **365** | **355** | **10 patients** | **97.3%** |

The big ones:

**214 obese patients** have NOT been diagnosed with diabetes. Given that obesity is the #1 risk factor for Type 2 Diabetes, every single one should at minimum be tested for blood sugar levels.

**150 obese patients** have NOT been diagnosed with hypertension. But we know 29.9% of obese patients already HAVE hypertension in our data. So statistically, ~45 of those 150 might have undiagnosed high blood pressure.

**126 hypertension patients** have NOT had a heart attack yet. 2.3% already have. These 126 are the patients who need cardiac monitoring.

### Why this matters?
This is **preventive medicine powered by graphs.** Instead of waiting for patients to walk in with a heart attack, the system flags: "These 126 patients have hypertension and haven't been checked for cardiac issues — schedule them for screening."

### The Cypher query:
```cypher
MATCH (p:Patient)-[:HAS_CONDITION]->(:Condition {DESCRIPTION: 'Body mass index 30+ - obesity (finding)'})
WHERE NOT (p)-[:HAS_CONDITION]->(:Condition {DESCRIPTION: 'Hypertension'})
RETURN p.name AS screen_for_hypertension
```

---

## Finding 3: Patient Pairs with 55% Identical Medical Histories

### Which algorithm?
**Jaccard Node Similarity** (one of MY 9 algorithms) — I compared every patient's connections (conditions, encounters, medications) and computed how much overlap they share.

### How it works mathematically?

```
Jaccard(Patient A, Patient B) = |Neighbors(A) ∩ Neighbors(B)| / |Neighbors(A) ∪ Neighbors(B)|
```

In English: count the stuff they share, divide by the total unique stuff between them.

Example from our data:
- **Damion480 Jerde200** is connected to: Suspected COVID, Fever, Cough, Fatigue, Loss of taste, Headache (6 things)
- **Augustine565 Block661** is connected to: Suspected COVID, Fever, Cough, Fatigue, Loss of taste (5 things)
- **Shared:** Suspected COVID, Fever, Cough, Fatigue, Loss of taste = 5 things
- **Total unique:** 6 things (the 5 shared + Headache)
- **Jaccard = 5/6 = 0.83** for conditions only

The overall Jaccard (including ALL connections — encounters, hospitals, etc.) came out to **0.55**.

### What I found?

| Patient A | Patient B | Jaccard | Shared Conditions | Recommendation |
|---|---|---|---|---|
| Damion480 Jerde200 | Augustine565 Block661 | 0.55 | COVID, Fever, Cough, Fatigue, Loss of taste | — |
| Augustine565 Block661 | Timmy68 Macejkovic424 | 0.55 | COVID, Fever, Cough, Loss of taste | Screen Augustine for Sore throat |
| Lyndon118 Turner526 | Reynaldo722 Wolf938 | 0.55 | COVID, Hypoxemia, Pneumonia, Fatigue, Obesity | **Screen Lyndon for Acute respiratory failure** |
| Lazaro919 Stiedemann542 | Julio255 Sanches349 | 0.53 | COVID, Fever, Cough | **Screen Lazaro for Dyspnea, Wheezing** |

### The critical one:
**Lyndon118 Turner526** and **Reynaldo722 Wolf938** share 5 serious conditions including Hypoxemia (low blood oxygen) and Pneumonia. Reynaldo ALSO has Acute Respiratory Failure. Lyndon does NOT — yet.

Given their 54.5% similarity, Lyndon is a strong candidate for respiratory failure monitoring. If this were a real hospital, the system would flag: "This patient looks a lot like another patient who developed respiratory failure — put them on a watchlist."

### Why this matters?
This is basically **Netflix recommendations for healthcare.** "Patients who had what you have also developed X — we should check for X."

---

## Finding 4: Essex County Has 92% COVID Rate — Highest in Massachusetts

### Which algorithm?
**Geographic Disease Clustering** — I traversed the graph path Patient → LIVES_IN → City → IN_COUNTY → County, then grouped conditions by county to find geographic hotspots.

### How it works?
The graph structure naturally encodes geography:
```
Patient --LIVES_IN--> City --IN_COUNTY--> County --IN_STATE--> State
```

I followed these paths for every patient, grouped them by county, and computed disease rates per county.

### What I found?

| County | Patients | COVID Rate | Obesity Rate | Hypertension Rate |
|---|---|---|---|---|
| **Essex County** | 48 | **92%** | 46% | 17% |
| Norfolk County | 48 | 79% | 31% | 33% |
| Middlesex County | 94 | 76% | 44% | 30% |
| Plymouth County | 41 | 73% | 34% | 24% |
| Berkshire County | 15 | 73% | **53%** | **40%** |
| Worcester County | 58 | 71% | **50%** | 16% |
| Suffolk County | 59 | 61% | 41% | 34% |

**Essex County** has a 92% COVID rate — 31 percentage points higher than Suffolk County (61%). If a public health agency saw this, they'd focus testing and vaccination resources on Essex County.

**Berkshire County** has the highest obesity (53%) and hypertension (40%) rates despite having only 15 patients. Small sample, but if confirmed, it needs targeted wellness programs.

**Worcester County** has 50% obesity — half the patients are obese. Combined with only 16% hypertension diagnosis rate, there are likely undiagnosed hypertension cases hiding there (from Finding 2, we know 29.9% of obese patients develop hypertension).

### Why this matters?
Public health departments allocate resources geographically. This analysis tells them exactly where to focus: COVID testing → Essex County, Obesity programs → Berkshire/Worcester, Cardiac screening → Berkshire.

---

## Finding 5: Medicare Patients Cost 2.5x More Than UnitedHealthcare Patients

### Which algorithm?
**Insurance Coverage Gap Analysis** — Using the graph path Encounter → PAID_BY → Payer, I grouped all encounters by insurance company and computed average costs, emergency rates, and visit volumes.

### What I found?

| Insurance | Total Visits | Avg Cost Per Visit | Emergency Rate |
|---|---|---|---|
| **Medicare** | **2,343** | **\$1,315** | **4.4%** |
| NO_INSURANCE | 2,191 | \$969 | 2.2% |
| Blue Cross Blue Shield | 1,514 | \$1,035 | 2.4% |
| Aetna | 1,379 | \$812 | 2.3% |
| Medicaid | 1,365 | \$587 | 2.9% |
| UnitedHealthcare | 1,366 | **\$535** | 1.5% |
| Cigna | 1,129 | \$593 | 2.7% |

### Three key findings:

**1. Medicare is 2.5x more expensive per visit than UnitedHealthcare (\$1,315 vs \$535).** Medicare covers elderly patients who have more conditions, need more tests, and stay longer. This isn't fraud — it's expected — but the magnitude (2.5x) is worth tracking.

**2. NO_INSURANCE is the 2nd busiest payer (2,191 visits).** That's nearly as many as Medicare. These are uninsured patients costing the system \$969 per visit on average — costs that hospitals absorb. That's \$2.1 million in uncompensated care.

**3. Medicare has the highest ER rate (4.4%)** — 102 emergency visits. This suggests Medicare patients are sicker overall and more likely to need emergency intervention. Medicaid is also high at 2.9%.

### Why this matters?
Hospital CFOs care about payer mix. If a hospital's patient base shifts toward more Medicare/uninsured patients, their revenue drops (lower reimbursement) while costs rise (sicker patients). This analysis quantifies exactly how much.

---

## Finding 6: One Patient Had 496 Hospital Visits and Cost \$1.83 Million

### Which algorithm?
**High-Cost Patient Profiling** — I traversed Patient → expenses and Patient → HAS_ENCOUNTER to find outlier patients with extreme healthcare utilization.

### What I found?

| Patient | Total Expenses | Conditions | Hospital Visits |
|---|---|---|---|
| **Quintin944 Runte676** | **\$1,826,531** | **15** | **496** |
| Will178 Wehner319 | \$1,817,455 | 6 | 25 |
| Isreal8 Ferry570 | \$1,814,109 | 14 | 37 |
| Danilo179 Larkin917 | \$1,773,634 | **22** | 68 |
| Javier97 Medina536 | \$1,750,737 | **27** | 25 |
| Rick943 Thompson596 | \$1,751,298 | 9 | **5** |

**Quintin944** has 496 hospital visits — nearly 1 visit every other day across the data period. With 15 conditions and \$1.83M in expenses, this is a "super-utilizer" — a tiny fraction of patients who consume a massive share of healthcare resources.

**Javier97** has 27 conditions (the most of anyone) but only 25 visits. He's medically complex but doesn't visit often — meaning each visit handles multiple conditions, which is efficient.

**Rick943** spent \$1.75M across only 5 visits. That's \$350,000 per visit. This suggests catastrophic events — major surgeries, ICU stays, or transplants.

### Why this matters?
In healthcare economics, the top 5% of patients typically consume 50% of total spending. Identifying these patients BEFORE they hit crisis lets hospitals intervene early — assign care coordinators, set up chronic disease management programs, schedule regular checkups to prevent expensive ER visits.

---

## Finding 7: The "Wellness" Hub — Why Routine Checkups Hold the Entire System Together

### Which algorithms?
**Eigenvector Centrality + Harmonic Centrality + ArticleRank** (3 of MY algorithms) — all three independently ranked "wellness" encounters as the #1 most important node type.

The other intern's algorithms confirmed this: **PageRank** ranked the same wellness-related node (14343) as #1, and it had **6,506 connections** (44% of the database).

### How Eigenvector works?
Regular degree counts connections. Eigenvector says: "You're important if your NEIGHBORS are important."

```
For each node: score = (1/λ) × sum of (scores of all neighbors)
```

Where λ is the largest eigenvalue of the adjacency matrix. This is solved iteratively — start with equal scores, multiply by the adjacency matrix, normalize, repeat until stable. It's the same math as PageRank but without the teleportation (damping factor).

### Why "wellness" wins across ALL algorithms?

Because wellness checkups are the one activity that connects:
- **Almost every patient** (routine annual checkups)
- **Almost every hospital** (every facility does wellness visits)
- **Almost every insurance company** (all plans cover preventive care)
- **Many conditions** (conditions get diagnosed during wellness visits)

It's the universal connector — the "Kevin Bacon" of the healthcare network. Remove wellness visits and the graph fractures into isolated patient-hospital pairs with no common thread.

### Why this matters?
If a health system cuts funding for preventive wellness programs, they're not just removing checkups — they're removing the structural backbone that connects patients to the rest of the healthcare ecosystem. The graph proves this mathematically: wellness is the highest-centrality node by every measure we tested.

---

## Summary Table — All 7 Findings

| # | Finding | Algorithm(s) Used | Key Number | Action |
|---|---|---|---|---|
| 1 | Anemia + Prediabetes co-occur 2.71x more than expected | Co-occurrence + Lift | Lift = 2.71 | Screen all anemia patients for prediabetes |
| 2 | 214 obese patients not screened for diabetes | Graph path traversal | 214 at-risk | Schedule diabetes screening |
| 3 | Patient pairs with 55% identical history | Jaccard Similarity | 10 pairs > 50% | Use for treatment recommendations |
| 4 | Essex County has 92% COVID rate | Geographic clustering | 92% vs 61% in Suffolk | Target testing resources |
| 5 | Medicare costs 2.5x more per visit than United | Payer analysis | \$1,315 vs \$535 | Monitor payer mix |
| 6 | One patient cost \$1.83M across 496 visits | High-cost profiling | \$1.83M / 496 visits | Assign care coordinator |
| 7 | Wellness visits are the structural backbone | Eigenvector + Harmonic + ArticleRank | #1 across 3 algorithms | Don't cut preventive care funding |
