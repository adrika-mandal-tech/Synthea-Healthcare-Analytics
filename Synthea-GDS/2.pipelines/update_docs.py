import re
import pandas as pd
from pathlib import Path

workspace = Path(__file__).parent.parent

# 1. Update explain.md
explain_md_path = workspace / 'explain.md'
md_text = explain_md_path.read_text()

# Fix Density
md_text = md_text.replace('- **Graph density:** 0.000844', '- **Graph density (Undirected):** 0.000849')

# Build new algorithms list
manifest_path = workspace / "reports" / "algorithm_manifest.csv"
df = pd.read_csv(manifest_path)
completed_df = df[df['status'] == 'completed']
req_df = df[df['status'] == 'requires_parameters']

# Replace counts
md_text = re.sub(r'- \*\*Completed:\*\* \d+', f'- **Completed:** {len(completed_df)}', md_text)
md_text = re.sub(r'- \*\*Requires additional parameters:\*\* \d+', f'- **Requires additional parameters:** {len(req_df)}', md_text)

completed_list = []
for _, row in completed_df.iterrows():
    completed_list.append(f"- **{row['algorithm']}** ({row['category']}) — `{row['output_file']}` — runtime {row['runtime_seconds']}s")
completed_text = "\n".join(sorted(completed_list))

# Find the section and replace it
section_pattern = re.compile(r'### Completed Algorithms\n.*?(?=\n### Requires Additional Parameters|\Z)', re.DOTALL)
md_text = section_pattern.sub(f'### Completed Algorithms\n{completed_text}\n\n', md_text)

# Also update the CSV structure counts
md_text = re.sub(r'- \*\*52\*\* total output CSV files', '- **50** total output CSV files', md_text)

explain_md_path.write_text(md_text)

# 2. Update explain.html
explain_html_path = workspace / 'explain.html'
html_text = explain_html_path.read_text()
html_text = html_text.replace('<strong>52</strong> CSV files generated', '<strong>50</strong> CSV files generated')
html_text = html_text.replace('<strong>32</strong> completed', f'<strong>{len(completed_df)}</strong> completed')
html_text = html_text.replace('<strong>24</strong> require additional parameters', f'<strong>{len(req_df)}</strong> require additional parameters')
explain_html_path.write_text(html_text)

print("Updated explain.md and explain.html successfully.")
