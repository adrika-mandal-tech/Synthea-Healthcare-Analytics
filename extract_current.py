import re

with open('comprehensive_gds_analytics_report.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all accordion headers
# Pattern: <span>Q\d+: ...</span> or <span>HITL \d+: ...</span>
# We'll capture the question text and then find the direct answer in the following accordion-content.

# Simpler: find all <span>Q\d+: ...</span> and <span>HITL \d+: ...</span>
pattern = re.compile(r'<span>(Q\d+: [^<]+)</span>|<span>(HITL \d+: [^<]+)</span>')
matches = pattern.findall(content)

questions = []
for m in matches:
    if m[0]:
        questions.append(('Q', m[0]))
    else:
        questions.append(('HITL', m[1]))

print(f"Found {len(questions)} question headers")

# For each, find the direct answer
results = []
for typ, qtext in questions:
    # Escape for regex
    qtext_esc = re.escape(qtext)
    # Look for the header, then skip to accordion-content, then find <p><strong>Direct Answer:</strong> ...</p>
    # We'll do a search from the position of the header.
    # Find the header position
    header_match = re.search(qtext_esc, content)
    if not header_match:
        print(f"Could not find header for {qtext}")
        continue
    start = header_match.end()
    # Look for the accordion-content div after the header (there may be a closing </div> and then the div)
    # We'll search for '<div class="accordion-content">' after start
    accordion_match = re.search(r'<div class="accordion-content">', content[start:])
    if not accordion_match:
        print(f"Could not find accordion-content for {qtext}")
        continue
    accordion_start = start + accordion_match.start()
    # Now find the <p><strong>Direct Answer:</strong> inside this accordion-content (could be nested)
    # We'll search from accordion_start for the pattern.
    direct_match = re.search(r'<p><strong>Direct Answer:</strong>(.*?)</p>', content[accordion_start:], re.DOTALL)
    if not direct_match:
        print(f"Could not find direct answer for {qtext}")
        continue
    direct_answer = direct_match.group(1).strip()
    # Clean up whitespace
    direct_answer = ' '.join(direct_answer.split())
    results.append((typ, qtext, direct_answer))

# Output
for typ, qtext, ans in results:
    if typ == 'Q':
        print(f"{qtext}: {ans}")
    else:
        print(f"{qtext}: {ans}")
