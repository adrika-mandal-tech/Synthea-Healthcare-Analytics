import re

# Read the HTML file
with open('comprehensive_gds_analytics_report.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Test the pattern for Q1
question = "Q1: Which patients have similar clinical profiles based on shared conditions?"
pattern = rf'(<span>{re.escape(question)}</span>\s*</div>\s*<div class="accordion-content">\s*<div>\s*<p><strong>Direct Answer:</strong>).*?(</p>)'

print("Pattern:", pattern)
match = re.search(pattern, content, flags=re.DOTALL)
if match:
    print("Match found!")
    print("Group 1 (before):", repr(match.group(1)[:100]), "...")
    print("Group 2 (after):", repr(match.group(2)))
else:
    print("No match found")

# Let's see what actually comes after the question
actual_pattern = rf'<span>{re.escape(question)}</span>\s*</div>\s*<div class="accordion-content">'
actual_match = re.search(actual_pattern, content, flags=re.DOTALL)
if actual_match:
    print("\nFound accordion-content div")
    # Get what comes after it
    after_content = content[actual_match.end():actual_match.end()+200]
    print("Text after accordion-content:", repr(after_content))
else:
    print("Could not find accordion-content div")
