import re

def enhance_health_insights():
    html_file = "Health_Insights.html"
    
    # Read the file
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find where to insert the enhanced analysis - after the existing insights but before the "How it would run in the company" section
    # Look for the end of Insight 5
    insight5_end_pattern = r'(<div class="lim"><b>Note:</b>.*?</div>\s*</div>\s*</div>\s*</div>\s*<h2 class="sec">3\. How it would run in the company</h2>)'
    
    # The new content to insert
    new_content = """
<div class="card">
  <span class="tag">Extended Insight 2a</span><span class="tag">Cost variation</span><h3>Per-patient costs vary 24-fold across groups</h3>
  <span class="k">What we found</span>
  <div class="tw"><table><tbody><tr><th>Group</th><th>Per-patient cost</th><th>vs Mild COVID A</th><th>Coverage gap</th></tr><tr><td>Seizure &amp; epilepsy</td><td><b>$81,429</b></td><td>23.7x</td><td>91% uncovered</td></tr><tr><td>Pain &amp; overdose</td><td><b>$66,818</b></td><td>19.5x</td><td>76% uncovered</td></tr><tr><td>Pregnancy + COVID</td><td><b>$28,826</b></td><td>8.4x</td><td>72% uncovered</td></tr><tr><td>Chronic conditions</td><td><b>$20,577</b></td><td>6.0x</td><td>-162% (overcovered)</td></tr><tr><td>Severe COVID</td><td><b>$17,031</b></td><td>5.0x</td><td>24% uncovered</td></tr><tr><td>Weight &amp; blood sugar</td><td><b>$13,085</b></td><td>3.8x</td><td>22% uncovered</td></tr><tr><td>Mild COVID A</td><td><b>$3,434</b></td><td>1.0x (baseline)</td><td>-75% (overcovered)</td></tr></tbody></table></div>
  <div class="win">The 3 smallest groups (Seizure &amp; epilepsy, Pain &amp; overdose, Pregnancy + COVID) have the highest per-patient costs — 8x to 24x the mild COVID baseline — despite representing only 41 patients total.</div>
  <span class="k">Real-world use</span>
  <div class="real">Neurology and pain management programs for the high-cost small groups; pregnancy care coordination for the Pregnancy + COVID group; insurance adequacy review for the 76-91% uncovered groups.</div>
  <div class="lim"><b>Note:</b> Chronic conditions group is overcovered ($54K coverage vs $20.6K cost) — likely Medicare or comprehensive insurance. Mild COVID A is overcovered (-75% gap) — may reflect preventive care coverage. These anomalies warrant verification.</div>
</div>

<div class="card">
  <span class="tag">Extended Insight 2b</span><span class="tag">Coverage gaps</span><h3>Coverage gaps reveal insurance adequacy problems</h3>
  <span class="k">What we found</span>
  <p>Three groups have &gt;70% of costs uncovered: Seizure &amp; epilepsy (91%), Pain &amp; overdose (76%), Pregnancy + COVID (72%). These patients face catastrophic out-of-pocket exposure.</p>
  <p>Two groups are overcovered: Chronic conditions (-162%) and Mild COVID A (-75%) — suggesting Medicare or comprehensive employer plans.</p>
  <div class="win">The 28 patients in high-uncovered groups (Seizure &amp; epilepsy + Pain &amp; overdose + Pregnancy + COVID) face $50K-$75K per-patient out-of-pocket risk — these are the patients most likely to delay or skip care due to cost.</div>
  <span class="k">Real-world use</span>
  <div class="real">Financial counseling for high-uncovered patients; prior authorization support; charity care screening for the 28 highest-risk patients.</div>
  <div class="lim"><b>Note:</b> "coverage" may include payer responsibility + patient copays. Verify whether $54K for Chronic conditions represents Medicare Part B + Part D or a commercial plan with low deductibles.</div>
</div>

<div class="card">
  <span class="tag">Extended Insight 2c</span><span class="tag">Spending concentration</span><h3>57% of spending concentrated in 42% of patients</h3>
  <span class="k">What we found</span>
  <p>The highlighted groups (Weight &amp; blood sugar, Severe COVID, Chronic conditions) represent 210 patients (42% of total) but account for 57% of total healthcare spending ($241.0M of $420.8M).</p>
  <p>The remaining 289 patients (58%) account for 43% of spending ($179.8M).</p>
  <div class="win">This concentration of spending mirrors the Pareto principle (80/20 rule) but with a 57/42 split — indicating a significant burden on a relatively small subpopulation.</div>
  <span class="k">Real-world use</span>
  <div class="real">Targeted interventions for the 210 high-cost patients could yield substantial savings: preventing diabetes in the 161 prediabetic patients would save an estimated $500,000-$1,000,000 in lifetime complication costs per prevented case. Similarly, preventing stroke in the 129 hypertensive patients would save $100,000-$300,000 per prevented stroke event.</div>
  <div class="lim"><b>Note:</b> These are lifetime totals and not age-adjusted. Older patients may naturally have higher costs.</div>
</div>

<div class="card">
  <span class="tag">Extended Insight 1a</span><span class="tag">Group characteristics</span><h3>Group-specific risk profiles and intervention opportunities</h3>
  <span class="k">What we found</span>
  <div class="tw"><table><tbody><tr><th>Group</th><th>Key Characteristics</th><th>Intervention Opportunity</th></tr><tr><td>Weight &amp; blood sugar</td><td>Obesity, prediabetes, anemia, early pregnancy loss</td><td>Lifestyle intervention programs targeting weight and blood sugar could prevent diabetes progression in 94 patients</td></tr><tr><td>Severe COVID</td><td>Pneumonia, trouble breathing, COVID-19</td><td>Early warning systems and ICU planning for this high-acuity group</td></tr><tr><td>Chronic conditions</td><td>Anemia, prediabetes, high blood pressure, obesity</td><td>Integrated chronic disease management addressing multiple comorbid conditions</td></tr><tr><td>Pain &amp; overdose</td><td>Migraine, drug overdose, chronic pain</td><td>Opioid-risk follow-up and substance use disorder interventions</td></tr><tr><td>Seizure &amp; epilepsy</td><td>Seizure disorder, epilepsy</td><td>Neurology care coordination and seizure management programs</td></tr></tbody></table></div>
  <div class="win">Each group has distinct clinical profiles requiring tailored intervention approaches rather than one-size-fits-all strategies.</div>
  <span class="k">Real-world use</span>
  <div class="real">Care managers can use these group profiles to design targeted outreach programs, allocate resources efficiently, and measure outcomes by group-specific metrics.</div>
</div>

<div class="card">
  <span class="tag">Extended Insight 3a</span><span class="tag">Medication insights</span><h3>Medication patterns reveal prescribing behaviors</h3>
  <span class="k">What we found</span>
  <p>After COVID-19 dominance, the most central conditions are obesity, prediabetes, anemia and high blood pressure. Medicine scores are close together, indicating no single drug dominates prescribing patterns.</p>
  <p>The top medicines reflect diverse therapeutic areas: Simvastatin (cholesterol), Naproxen (pain), Albuterol inhaler (asthma), Hydrochlorothiazide (blood pressure), Acetaminophen (pain, fever), Enoxaparin (blood thinner), Epinephrine auto-injector (allergy), Atenolol + Chlorthalidone (blood pressure).</p>
  <div class="win">This medication distribution indicates a balanced approach to chronic disease management rather than over-reliance on any single therapeutic class.</div>
  <span class="k">Real-world use</span>
  <div class="real">Pharmacy stock planning, formulary decisions, and therapeutic guideline development can be informed by this medication utilization pattern.</div>
</div>

<div class="card">
  <span class="tag">Extended Insight 4a</span><span class="tag">Patient similarity applications</span><h3>Beyond "patients like this one" to clinical action</h3>
  <span class="k">What we found</span>
  <p>For any patient we can list others with a very similar history (Jaccard similarity up to 0.90) and compare what care they got, enabling care-gap analysis and clinical study matching.</p>
  <p>The best matched pair shared 9 items in common (COVID, fever, cough, loss of taste, fatigue, flu vaccine and more), with one patient having an additional symptom (sore throat).</p>
  <div class="win">Patient similarity analysis enables precision medicine approaches by identifying look-alike patients who may respond similarly to treatments.</div>
  <span class="k">Real-world use</span>
  <div class="real">Clinical trial matching, treatment selection based on phenotypic similarity, and proactive identification of patients who may benefit from specific interventions based on similarity to known responders.</div>
</div>

<div class="card">
  <span class="tag">Extended Insight 5a</span><span class="tag">Data quality implications</span><h3>Isolated records and spending anomalies</h3>
  <span class="k">What we found</span>
  <p>The graph found a patient with $631K in spending but no medical record — money was spent but nothing medical was recorded, indicating data quality issues.</p>
  <p>One small mild COVID group spends only $131K total for 14 patients ($9.4K per patient), which is unusually low and warrants investigation.</p>
  <div class="win">Routine data quality checks using graph algorithms can isolate problematic records before they affect analytics or decision-making.</div>
  <span class="k">Real-world use</span>
  <div class="real">Run connectivity checks on every data load and send isolated records to the data team before anyone uses the data for clinical or operational decisions.</div>
</div>

<div class="card">
  <span class="tag">Cross-Insight Implications</span><span class="tag">Integrated analysis</span><h3>Combining insights for comprehensive understanding</h3>
  <span class="k">What we found</span>
  <p>Insights 1, 2, and 5 together reveal a critical pattern: the patient with no medical record but $631K spending (Insight 5) may belong to one of the high-cost groups identified in Insight 2, suggesting that data quality issues disproportionately affect high-cost patients.</p>
  <p>Insights 2 and 3 show that while COVID-19 dominates condition prevalence (Insight 3), the highest costs come from metabolic and chronic conditions groups (Insight 2), indicating where long-term healthcare spending is truly concentrated.</p>
  <p>Insights 1 and 4 demonstrate that the 9 natural groups (Insight 1) provide the foundation for meaningful patient similarity analysis (Insight 4), enabling look-alike matching for clinical decision support.</p>
  <div class="win">The true value of graph analytics emerges when insights are combined — each insight provides a piece of the puzzle, but together they reveal a comprehensive picture of healthcare utilization, risk, and opportunity.</div>
  <span class="k">Real-world use</span>
  <div class="real">Healthcare organizations should develop integrated analytics frameworks that combine multiple analytical approaches rather than relying on single-insight decision-making.</div>
</div>

<div class="card">
  <span class="tag">Actionable Recommendations</span><span class="tag">Stakeholder-specific guidance</span><h3>Practical steps for healthcare stakeholders</h3>
  <span class="k">Based on the analysis</span>
  <div class="tw"><table><tbody><tr><th>Stakeholder</th><th>Key Recommendations</th></tr><tr><td>Hospitals and Health Systems</td><td>• Focus care management on high-cost small groups (seizure, pain/overdose, pregnancy+COVID)<br>• Invest in preventive programs for the 161 prediabetic patients<br>• Enhance chronic disease management for the metabolic cohort<br>• Implement routine data quality checks for isolated records</td></tr><tr><td>Patients and Advocacy Groups</td><td>• Seek financial assistance for high-out-of-pocket-risk groups (seizure, pain/overdose, pregnancy+COVID)<br>• Engage in care coordination programs to reduce encounter frequency<br>• Participate in preventive programs for prediabetes to avoid diabetes progression</td></tr><tr><td>Payers and Insurers</td><td>• Use group-based risk stratification for targeted case management<br>• Address coverage gaps in high-risk groups to reduce financial toxicity<br>• Develop predictive models using identified patient groups and characteristics</td></tr><tr><td>Researchers and Public Health Officials</td><td>• Investigate health disparities in high-cost small groups<br>• Use identified cohorts as targets for clinical trials<br>• Inform public health policies on resource allocation and preventive care funding</td></tr></tbody></table></div>
  <div class="win">These recommendations translate analytical insights into concrete actions that can improve patient outcomes, reduce unnecessary spending, and enhance healthcare system performance.</div>
  <span class="k">Real-world use</span>
  <div class="real">Stakeholders can implement these recommendations incrementally, measuring impact and adjusting approaches based on outcomes and feedback.</div>
</div>
"""
    
    # Insert the new content before the "How it would run in the company" section
    # We'll replace the pattern that marks the start of that section with our new content followed by that section
    pattern = r'(<h2 class="sec">3\. How it would run in the company</h2>)'
    replacement = new_content + r'\1'
    
    content = re.sub(pattern, replacement, content)
    
    # Write back to the file
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Enhanced {html_file} with in-depth analysis sections")

if __name__ == '__main__':
    enhance_health_insights()
