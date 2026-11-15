import re

with open('report.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section with questions
# Pattern for each question: 
# ### Question X: ...
# **Assigned Algorithm:** ...
# **Detailed Answer:** ...
# We'll capture the question number and the detailed answer until next ### or end of section.

# Use regex to find each question block
pattern = re.compile(r'### Question (\d+): (.*?)\n\*\*Assigned Algorithm:\*\* .*?\n\*\*Detailed Answer:\*\* (.*?)(?=\n### Question|\n##|\Z)', re.DOTALL)
matches = pattern.findall(content)

print(f"Found {len(matches)} questions")
for qnum, question_text, detailed in matches:
    # Clean up detailed answer: take first sentence up to period.
    # Remove extra whitespace and newlines.
    detailed_clean = ' '.join(detailed.split())
    # Find first sentence ending with period.
    # Simple: split by '.' and take first part plus '.' if exists.
    sentences = re.split(r'(?<=[.])\s+', detailed_clean)
    if sentences:
        concise = sentences[0]
        # Ensure it ends with a period if not already.
        if not concise.endswith('.'):
            concise += '.'
    else:
        concise = detailed_clean
    print(f"Q{qnum}: {concise}")
