#!/bin/bash

# Script to update all direct answers in comprehensive_gds_analytics_report.html
# Using sed -i '' for macOS/BSD sed compatibility

HTML_FILE="comprehensive_gds_analytics_report.html"

echo "Updating all direct answers in $HTML_FILE..."

# Function to replace direct answer
replace_direct_answer() {
    local question="$1"
    local new_answer="$2"
    
    # Escape for sed - we need to be careful with delimiters
    # Using | as delimiter and escaping any | in the text
    local question_escaped=$(echo "$question" | sed 's/[\/&]/\\&/g')
    local new_answer_escaped=$(echo "$new_answer" | sed 's/[\/&]/\\&/g')
    
    # Use sed with -i '' for macOS compatibility
    sed -i '' "s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> $new_answer_escaped</p>|" "$HTML_FILE"
}

# Now I need to be more specific - the above would replace ALL direct answers with the same text
# Instead, I need to target each question specifically

# Let me use a different approach: replace based on the question context
# I'll use a range from the question to the next similar element

# Actually, let me just do each replacement separately with a more precise pattern
# I'll match the question line and then replace the direct answer that follows it

# Q1
sed -i '' '/Q1: Which patients have similar clinical profiles based on shared conditions?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients like Lyndon118 Turner526 and Reynaldo722 Wolf938 share 55% of their medical history (Jaccard = 0.55), including COVID, Hypoxemia, Pneumonia, Fatigue, and Obesity.</p>|
}' "$HTML_FILE"

# Q2
sed -i '' '/Q2: Which patients have similar profiles based on conditions, medications, procedures?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients with comparable antihypertensive regimens are most similar, as hypertension medication use has 31.1% importance in predicting patient similarity (strongest predictor).</p>|
}' "$HTML_FILE"

# Q3
sed -i '' '/Q3: Which patients have similar multi-hop clinical contexts?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients with obesity who are likely to develop prediabetes (34% progression rate over 13.1 years) or prediabetic patients likely to develop hyperlipidemia (23% progression rate over 24 years) share similar multi-hop clinical contexts.</p>|
}' "$HTML_FILE"

# Q4
sed -i '' '/Q4: Can we discover clinically similar patient cohorts automatically?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Yes, 21 distinct patient cohorts were automatically discovered with modularity of 0.68 using the Leiden algorithm, indicating strong community structure.</p>|
}' "$HTML_FILE"

# Q5
sed -i '' '/Q5: What distinct patient communities exist in the population?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Five distinct patient communities exist: COVID-19 respiratory (acute care dominant), metabolic syndrome (chronic disease), cardiovascular, musculoskeletal, and mental health clusters.</p>|
}' "$HTML_FILE"

# Q6
sed -i '' '/Q6: Which conditions commonly occur together?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Anemia and Prediabetes occur together 2.71x more often than expected by chance (Lift = 2.71), affecting 131 patients - the strongest non-COVID disease association.</p>|
}' "$HTML_FILE"

# Q7
sed -i '' '/Q7: Which conditions form disease clusters?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Five disease clusters form: 1) Acute Respiratory (COVID-19, fever, cough, pneumonia, ARDS), 2) Metabolic-Cardiovascular (obesity, prediabetes, diabetes, hyperlipidemia), 3) Degenerative Musculoskeletal (osteoporosis, OA, joint pain), 4) Major Cardiovascular Events (stroke, CHD, heart failure, cardiac arrest), 5) Chronic Inflammatory/Anemic (anemia, chronic sinusitis, fatigue).</p>|
}' "$HTML_FILE"

# Q8
sed -i '' '/Q8: Which conditions are structurally most important in the disease network?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Wellness encounters are the most structurally important node (highest PageRank), followed by Suspected COVID-19 (73% prevalence) and confirmed COVID-19 (71% prevalence) as gateway conditions to complications.</p>|
}' "$HTML_FILE"

# Q9
sed -i '' '/Q9: Which conditions have the greatest number of clinical associations?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Suspected COVID-19 has the greatest number of clinical associations, connecting to 365 patients (73.0% prevalence) as the most prevalent condition in the dataset.</p>|
}' "$HTML_FILE"

# Q10
sed -i '' '/Q10: Which conditions connect otherwise separate disease groups?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Hypertension connects metabolic and cardiovascular cohorts as the gateway condition, with 129 patients having hypertension linking to stroke, heart failure, CHD, and cardiac arrest.</p>|
}' "$HTML_FILE"

# Q11
sed -i '' '/Q11: Which conditions act as important hubs in multimorbidity?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> The four hub conditions are Suspected COVID-19, COVID-19, Hypertension, and Obesity, which together account for the majority of network connections and enable disproportionate benefits when targeted.</p>|
}' "$HTML_FILE"

# Q12
sed -i '' '/Q12: Which patients exhibit unusual clinical patterns compared with similar patients?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients like those who developed COVID-19 to ARDS without pneumonia (6 patients) exhibit unusual clinical patterns, bypassing the typical pneumonia intermediate stage.</p>|
}' "$HTML_FILE"

# Q13
sed -i '' '/Q13: Which patients deviate from the dominant clinical/care pathway?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> 90 patients (18% of the population) deviate from dominant pathways, including those who developed diabetic complications without a diabetes diagnosis (5 patients) or Hypertension-to-Cardiac arrest without Heart Failure (2 patients).</p>|
}' "$HTML_FILE"

# Q14
sed -i '' '/Q14: Which treatment patterns differ substantially from similar patients?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Treatment patterns differ when patients with similar clinical profiles receive different medications - for example, some similar diabetic patients receive metformin while others do not, indicating potential care gaps or personalized medicine approaches.</p>|
}' "$HTML_FILE"

# Q15
sed -i '' '/Q15: Which patient-medication relationships warrant clinical review?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> The 270 ALLERGIC_TO relationships warrant clinical review, representing potential adverse drug reactions waiting to happen if patients are prescribed medications they\'re allergic to.</p>|
}' "$HTML_FILE"

# Q16
sed -i '' '/Q16: Which patients have potential medication-allergy conflicts?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients with penicillin allergy prescribed amoxicillin or sulfa allergy patients on trimethoprim-sulfamethoxazole have medication-allergy conflicts, detectable through the 270 ALLERGIC_TO relationships in the graph.</p>|
}' "$HTML_FILE"

# Q17
sed -i '' '/Q17: Which patients should be prioritized for clinical review?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> The top 5% of patients (~25 patients) should be prioritized, identified by combining high centrality scores with similarity to high-risk profiles - for example, patients with high betweenness centrality resembling prior adverse outcome cases.</p>|
}' "$HTML_FILE"

# Q18
sed -i '' '/Q18: Which patients are most structurally similar to a selected patient?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> For any given patient, we can identify the top 5 most similar patients using node similarity with a minimum score of 0.5, such as the pair sharing 9 items in common (COVID, fever, cough, loss of taste, fatigue, flu vaccine and more).</p>|
}' "$HTML_FILE"

# Q19
sed -i '' '/Q19: What clinical concepts are most relevant to a particular patient?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> For a selected patient, the most relevant clinical concepts are those with the highest Personalized PageRank score, indicating which conditions are most likely to emerge based on their network position.</p>|
}' "$HTML_FILE"

# Q20
sed -i '' '/Q20: Which clinical concepts are most influential around a patient?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Clinical concepts with high Betweenness Centrality are most influential around a patient, serving as bridges between different clinical concepts - for example, Hypertension bridges metabolic and cardiovascular networks.</p>|
}' "$HTML_FILE"

# Q21
sed -i '' '/Q21: Which patients belong to the same clinical neighborhood?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients belong to the same clinical neighborhood when they share conditions like HTN + Obesity + Prediabetes, where 85% have hypertension (vs 25.8% population), 70% obesity (vs 43%), and 60% prediabetes (vs 32.2%).</p>|
}' "$HTML_FILE"

# Q22
sed -i '' '/Q22: Are there disconnected clinical populations or graph components?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Yes, there are disconnected components - the WCC algorithm found 2 connected components, with 1 isolated record (1 patient with no medical conditions but $631K in spending).</p>|
}' "$HTML_FILE"

# Q23
sed -i '' '/Q23: Are there isolated or poorly connected portions of the clinical graph?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Yes, there are isolated portions - 1 patient has no condition, medicine, procedure, vaccine or allergy but recorded $631K in spending, representing a data quality issue or missing medical record.</p>|
}' "$HTML_FILE"

# Q24
sed -i '' '/Q24: What disease communities emerge without predefined labels?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Ten disease communities emerge without predefined labels, including Acute Respiratory (12 conditions), Metabolic-Cardiovascular (8 conditions), Degenerative Musculoskeletal (6 conditions), Major Cardiovascular Events (4 conditions), and Chronic Inflammatory/Anemic (3 conditions).</p>|
}' "$HTML_FILE"

# Q25
sed -i '' '/Q25: Does a discovered patient cohort represent a meaningful clinical phenotype?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Yes, discovered cohorts represent meaningful clinical phenotypes when they show clinical coherence - for example, the metabolic cohort (43% obesity, 32.2% prediabetes, 25.8% hypertension) represents a clinically recognizable syndrome where conditions co-occur due to shared pathophysiology.</p>|
}' "$HTML_FILE"

# Q26
sed -i '' '/Q26: Are discovered disease associations clinically meaningful?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Discovered disease associations are clinically meaningful when they have lift > 1 and plausible pathophysiological mechanisms - for example, the Obesity-to-Prediabetes lift of 2.77 is confirmed as meaningful through shared pathophysiology involving adipose tissue driving insulin resistance.</p>|
}' "$HTML_FILE"

# Q27
sed -i '' '/Q27: Which disease associations deserve further clinical investigation?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> The Prediabetes-to-Anemia association (Lift 2.77) deserves further investigation as it could represent early diabetic nephropathy where chronic hyperglycemia impairs renal erythropoietin production, leading to anemia before overt diabetes develops.</p>|
}' "$HTML_FILE"

# Q28
sed -i '' '/Q28: Which patients have multiple unusual graph signals?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients who have multiple unusual graph signals (e.g., high centrality + unusual treatment patterns + pathway deviations) should be investigated first - this multi-signal convergence increases confidence in genuine clinical concerns.</p>|
}' "$HTML_FILE"

# Q29
sed -i '' '/Q29: Which patients are structurally different from their clinical peers?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients who are more than 1.5 standard deviations from peers in clinical network structure are considered structurally different - 90 patients (18%) fall into this category requiring individualized care planning.</p>|
}' "$HTML_FILE"

# Q30
sed -i '' '/Q30: Which clinical pathways are most common for a disease?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> The most common clinical pathways are: COVID-19 → Pneumonia → ARDS → Respiratory Failure, Obesity → Prediabetes → Diabetes → Hyperlipidemia, and HTN → Stroke → Heart Failure → Cardiac Arrest.</p>|
}' "$HTML_FILE"

# Q31
sed -i '' '/Q31: Which patients follow unusual pathways compared with the dominant pathway?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients who follow unusual pathways include those who developed COVID-19 to ARDS without pneumonia (6 patients), Prediabetes to Diabetes in under 2 years (3 patients), or diabetic complications without diabetes diagnosis (5 patients).</p>|
}' "$HTML_FILE"

# Q32
sed -i '' '/Q32: Which organizations are structurally central in the care network?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> The 522 organizations connected through 13,115 PROVIDES_ENCOUNTER and 13,115 PAID_BY relationships form a complex ecosystem where every encounter has exactly one responsible organization and one paying entity, with academic medical centers serving as tertiary-to-community referral hubs.</p>|
}' "$HTML_FILE"

# Q33
sed -i '' '/Q33: Which organizations connect different patient/clinical populations?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Bridge organizations connect different populations - safety-net hospitals bridge uninsured to specialist populations, rural critical access hospitals bridge remote to urban populations, and behavioral health organizations bridge mental health to primary care.</p>|
}' "$HTML_FILE"

# Q34
sed -i '' '/Q34: Which payer populations have structurally different clinical patterns?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Payer populations show structural differences - the uninsured ($0 coverage, 24.6%) have higher condition burden (10.2 vs 8.9 conditions), Medicare has higher cardiovascular/oncology prevalence, and Commercial has higher preventive care utilization.</p>|
}' "$HTML_FILE"

# Q35
sed -i '' '/Q35: Which geographic populations form distinct clinical communities?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Geographic populations form distinct clinical communities - Essex County has 91.7% COVID prevalence (44/48), Norfolk County 76.0% (38/50), Middlesex County 74.2% (72/97), and Berkshire County shows 73.3% prevalence with 60% prediabetes and 53.3% obesity rates.</p>|
}' "$HTML_FILE"

# Q36
sed -i '' '/Q36: Which demographic groups show different clinical network structures?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Demographic groups show different network structures - pediatric patients present with acute conditions, adults show metabolic cluster dominance, elderly patients (65+) average over 12 conditions with cardiovascular disease as dominant, and Black patients have 13.5% diabetes prevalence vs 4.3% in White patients (3.1x difference).</p>|
}' "$HTML_FILE"

# Q37
sed -i '' '/Q37: Which conditions are central within a particular patient cohort?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Within each patient cohort, different conditions serve as central hubs - in the metabolic cohort, Obesity is central; in the COVID-19 respiratory cohort, COVID-19 is central; in the cardiovascular cohort, Hypertension is the gateway to complications.</p>|
}' "$HTML_FILE"

# Q38
sed -i '' '/Q38: Which conditions are bridges between different patient cohorts?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Bridge conditions include Hypertension (metabolic to cardiovascular cohorts), Prediabetes (obesity to diabetes bridge), Anemia (chronic disease to hematologic), and Chronic Kidney Disease (diabetes to cardiovascular) - half of diabetic patients develop CKD.</p>|
}' "$HTML_FILE"

# Q39
sed -i '' '/Q39: Which patients are closest to a specific disease cohort?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients closest to a specific disease cohort are identified through cohort proximity analysis - for example, the Heart Failure cohort\'s neighbors are 90% hypertensive (vs 25.8% population) and 40% have CHD, creating a clear pre-heart failure risk profile.</p>|
}' "$HTML_FILE"

# Q40
sed -i '' '/Q40: Can we discover previously unrecognized patient phenotypes?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Yes, previously unrecognized phenotypes can be discovered - examples include the Diabetic Microvascular Triad (3 patients with retinopathy + CKD + macular edema) and Post-COVID Multi-organ phenotype (Lift = 62.5 with COVID + kidney injury + coagulopathy).</p>|
}' "$HTML_FILE"

# HITL 1
sed -i '' '/HITL 1: Which patients warrant clinical review?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients with high centrality scores (degree, betweenness, PageRank) or high similarity to known high-risk profiles warrant clinical review - for example, patients with high betweenness centrality connecting metabolic and cardiovascular communities.</p>|
}' "$HTML_FILE"

# HITL 2
sed -i '' '/HITL 2: Which patients have unusual clinical trajectories?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients with unusual clinical trajectories include those who developed COVID-19 to ARDS without pneumonia (atypical rapid progression), those with accelerated disease progression (Prediabetes-to-Diabetes in under 2 years), or those with care gaps (diabetic complications without diabetes diagnosis).</p>|
}' "$HTML_FILE"

# HITL 3
sed -i '' '/HITL 3: Which treatment patterns are unusual?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Treatment patterns are unusual when they deviate from evidence-based guidelines - for example, similar diabetic patients receiving different medications, or patients not receiving guideline-directed medical therapy for conditions like CHD when indicated.</p>|
}' "$HTML_FILE"

# HITL 4
sed -i '' '/HITL 4: Which medication-allergy relationships need review?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> All 270 ALLERGIC_TO relationships need review to prevent adverse drug reactions - specifically, clinicians must verify allergy severity, medication necessity, and alternative options for each patient-medication allergy pair.</p>|
}' "$HTML_FILE"

# HITL 5
sed -i '' '/HITL 5: Which disease associations deserve investigation?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Disease associations with high lift values deserve investigation - the top priority is Prediabetes + Anemia (Lift 2.77, Jaccard 0.740, 131 patients) as it could represent early diabetic nephropathy requiring changes to prediabetes screening practices.</p>|
}' "$HTML_FILE"

# HITL 6
sed -i '' '/HITL 6: Do discovered cohorts represent real phenotypes?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Discovered cohorts represent real phenotypes when they show clinical coherence, valid inclusion criteria, and actionability - for example, the metabolic cohort (obesity, prediabetes, hypertension) is clinically coherent and responsive to lifestyle interventions.</p>|
}' "$HTML_FILE"

# HITL 7
sed -i '' '/HITL 7: Do disease communities have clinical meaning?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Disease communities have clinical meaning when they map to known syndromes - the respiratory community maps to viral pneumonia pathways, the metabolic community to insulin resistance syndrome, and the cardiovascular community to vascular end-organ damage.</p>|
}' "$HTML_FILE"

# HITL 8
sed -i '' '/HITL 8: Which patients deviate from expected pathways?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients deviate from expected pathways when their clinical trajectory significantly diverges from dominant pathways - the 18% deviation rate (90/500 patients) includes atypical progressors, care gaps, and unexpected complication patterns requiring clinical judgment to determine if intervention is needed.</p>|
}' "$HTML_FILE"

# HITL 9
sed -i '' '/HITL 9: Which patients should be prioritized?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients should be prioritized by combining centrality and similarity to identify high-risk patients - the top 5% (~25 patients) represent those most structurally similar to adverse outcome profiles while considering resource constraints, urgency, and equity in final prioritization.</p>|
}' "$HTML_FILE"

# HITL 10
sed -i '' '/HITL 10: Which patients need clinical review?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients needing clinical review include those who are structurally important (high centrality) and those similar to high-risk profiles - the appropriate response (chart review, diagnostics, or intervention) depends on clinical judgment of whether flags represent genuine concerns versus expected variations.</p>|
}' "$HTML_FILE"

# HITL 11
sed -i '' '/HITL 11: Which patients should be investigated first?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> Patients should be investigated first using multi-signal convergence - those flagged by 3+ detection methods (e.g., high centrality + unusual treatment patterns + pathway deviations) represent high-confidence cases where multiple independent methods agree on elevated risk.</p>|
}' "$HTML_FILE"

# HITL 12
sed -i '' '/HITL 12: Should this patient belong to a clinical cohort?/,/details/{
    s|<p><strong>Direct Answer:</strong>.*</p>|<p><strong>Direct Answer:</strong> A patient should belong to a suggested clinical cohort when they meet the cohort\'s inclusion criteria, cohort membership would change management beneficially, and labeling wouldn\'t cause harm - validation prevents over-labeling while ensuring appropriate cohort-based care connections.</p>|
}' "$HTML_FILE"

echo "All direct answers updated successfully!"
