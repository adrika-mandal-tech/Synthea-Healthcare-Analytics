import csv
import os
import re

# Statistics computation
def compute_statistics():
    stats = {}

    # Basic population stats from patient_features_final.csv
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

            # Find the total_conditions column index from header
            if 'total_conditions' in header:
                conditions_idx = header.index('total_conditions')
            else:
                conditions_idx = 24  # fallback
            conditions_sum += float(row[conditions_idx])  # total_conditions
            # Find column indices from header
            encounters_idx = header.index('total_encounters') if 'total_encounters' in header else 17
            expenses_idx = header.index('HEALTHCARE_EXPENSES') if 'HEALTHCARE_EXPENSES' in header else 6
            medications_idx = header.index('total_medications') if 'total_medications' in header else 46

            encounters_sum += float(row[encounters_idx])   # total_encounters
            expenses_sum += float(row[expenses_idx])      # HEALTHCARE_EXPENSES
            medications_sum += float(row[medications_idx])  # total_medications

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

    # Top conditions from all_conditions_prevalence.csv
    with open('all_conditions_prevalence.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        conditions = []
        for row in reader:
            conditions.append({
                'code': row[0],
                'description': row[1],
                'count': int(row[2]),
                'prevalence': float(row[3])
            })
        conditions.sort(key=lambda x: x['prevalence'], reverse=True)
        stats['top_conditions'] = conditions[:10]

    # Top comorbidity pairs by lift
    with open('comorbidity_lift.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        lift_pairs = []
        for row in reader:
            lift_pairs.append({
                'condition_a': row[0],
                'condition_b': row[1],
                'lift': float(row[2])
            })
        lift_pairs.sort(key=lambda x: x['lift'], reverse=True)
        # Filter out zero lift if possible
        non_zero_lift = [p for p in lift_pairs if p['lift'] > 0]
        if non_zero_lift:
            stats['top_lift_pairs'] = non_zero_lift[:5]
        else:
            stats['top_lift_pairs'] = lift_pairs[:5]

    # Top comorbidity pairs by Jaccard
    with open('comorbidity_jaccard.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        jaccard_pairs = []
        for row in reader:
            jaccard_pairs.append({
                'condition_a': row[0],
                'condition_b': row[1],
                'jaccard': float(row[2])
            })
        jaccard_pairs.sort(key=lambda x: x['jaccard'], reverse=True)
        stats['top_jaccard_pairs'] = jaccard_pairs[:5]

    return stats

def update_stats_grid(html_content, stats):
    # Replace the stats-grid content
    start_tag = '<div class="stats-grid">'
    end_tag = '</div>'
    start_index = html_content.find(start_tag)
    if start_index == -1:
        return html_content
    start_index += len(start_tag)
    end_index = html_content.find(end_tag, start_index)
    if end_index == -1:
        return html_content

    new_content = '''
            <div class="stat-card">
                <h3>Total Patients</h3>
                <p>''' + str(stats['total_patients']) + '''</p>
            </div>
            <div class="stat-card">
                <h3>Avg Conditions/Patient</h3>
                <p>''' + f"{stats['avg_conditions']:.2f}" + '''</p>
            </div>
            <div class="stat-card">
                <h3>Avg Encounters/Patient</h3>
                <p>''' + f"{stats['avg_encounters']:.2f}" + '''</p>
            </div>
            <div class="stat-card">
                <h3>Avg Healthcare Expenses</h3>
                <p>$''' + f"{stats['avg_expenses']:,.2f}" + '''</p>
            </div>
    '''

    return html_content[:start_index] + new_content + html_content[end_index:]

def update_question_6(html_content, stats):
    # Find question-6 and update its detailed answer
    # Build the new answer
    top_pairs = stats['top_jaccard_pairs'][:3]
    pairs_text = []
    for pair in top_pairs:
        pairs_text.append('"' + pair["condition_a"] + '" and "' + pair["condition_b"] + '" (Jaccard: ' + format(pair["jaccard"], '.3f') + ')')
    pairs_str = ', '.join(pairs_text)

    new_answer = 'Conditions that commonly occur together are identified by measuring similarity between condition nodes based on shared patient populations. The top comorbidity pairs by Jaccard similarity in our dataset are: ' + pairs_str + '. These pairs represent conditions that frequently co-occur in the same patients, indicating potential pathophysiological connections or shared risk factors.'

    # Pattern to find and replace the detailed answer in question-6
    pattern = r'(<div class="accordion" id="question-6">.*?<div class="accordion-content">.*?<p><strong>Detailed Answer:</strong> )(.*?)(</p>.*?</div>.*?</div>)'

    def replace_func(match):
        return match.group(1) + new_answer + match.group(3)

    return re.sub(pattern, replace_func, html_content, flags=re.DOTALL)

def update_html_file(file_path, stats):
    with open(file_path, 'r') as f:
        content = f.read()

    # Update stats-grid
    content = update_stats_grid(content, stats)

    # Update question 6
    content = update_question_6(content, stats)

    with open(file_path, 'w') as f:
        f.write(content)

def update_markdown_report(stats):
    # Update the report.md file with similar statistics
    md_path = 'report.md'
    with open(md_path, 'r') as f:
        content = f.read()

    # Update the executive summary with real stats
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        if line.strip() == '## Executive Summary':
            # Skip the next few lines to replace the content
            i += 1
            # Skip empty lines and add our content
            while i < len(lines) and (lines[i].strip() == '' or lines[i].startswith('This report') or lines[i].startswith('Key insights')):
                i += 1

            # Add our new executive summary
            new_lines.append('')  # empty line
            new_lines.append('This report presents findings from applying Neo4j Graph Data Science (GDS) algorithms to the Synthea healthcare dataset of ' + str(stats['total_patients']) + ' patients. The analysis reveals patterns in disease burden, patient similarity, clinical pathways, and healthcare utilization that can inform clinical decision-making, public health interventions, and healthcare operations.')
            new_lines.append('')
            new_lines.append('Key insights include:')
            new_lines.append('- The most prevalent conditions are ' + stats['top_conditions'][0]['description'] + ' (' + format(stats['top_conditions'][0]['prevalence'], '.1f') + '%), ' + stats['top_conditions'][1]['description'] + ' (' + format(stats['top_conditions'][1]['prevalence'], '.1f') + '%), and ' + stats['top_conditions'][2]['description'] + ' (' + format(stats['top_conditions'][2]['prevalence'], '.1f') + '%).')
            new_lines.append('- Patients have an average of ' + format(stats['avg_conditions'], '.2f') + ' conditions and ' + format(stats['avg_encounters'], '.2f') + ' encounters each.')
            if len(stats['top_lift_pairs']) > 0 and stats['top_lift_pairs'][0]['lift'] > 0:
                top_lift = stats['top_lift_pairs'][0]
                new_lines.append('- The strongest comorbidity associations are seen in pairs like "' + top_lift["condition_a"] + '" + "' + top_lift["condition_b"] + '" with a lift of ' + format(top_lift["lift"], '.1f') + '.')
            else:
                new_lines.append('- Comorbidity analysis shows significant associations between various condition pairs.')
            new_lines.append('- The Human-in-the-Loop framework ensures that algorithmic findings are validated by clinical expertise.')
            # Skip ahead to continue processing
            # Find the next section header
            while i < len(lines) and not lines[i].startswith('##'):
                i += 1
            continue
        i += 1

    content = '\n'.join(new_lines)

    with open(md_path, 'w') as f:
        f.write(content)

def main():
    os.chdir('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics')
    stats = compute_statistics()

    print("Computed statistics:")
    print("Total patients:", stats['total_patients'])
    print("Average conditions per patient: {:.2f}".format(stats['avg_conditions']))
    print("Average encounters per patient: {:.2f}".format(stats['avg_encounters']))
    print("Average healthcare expenses: ${:,.2f}".format(stats['avg_expenses']))
    print("Top condition:", stats['top_conditions'][0]['description'] + " ({:.1f}%)".format(stats['top_conditions'][0]['prevalence']))
    print("Top Jaccard pair:", stats['top_jaccard_pairs'][0]['condition_a'] + " + " + stats['top_jaccard_pairs'][0]['condition_b'] + " (Jaccard: {:.3f})".format(stats['top_jaccard_pairs'][0]['jaccard']))

    # Update HTML files
    update_html_file('comprehensive_gds_analytics_report.html', stats)
    update_html_file('comprehensive_findings.html', stats)

    # Update Markdown report
    update_markdown_report(stats)

    print("Files updated successfully.")

if __name__ == '__main__':
    main()