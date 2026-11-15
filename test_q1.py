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
    # Show what the replacement would be
    new_answer = "Patients like Lyndon118 Turner526 and Reynaldo722 Wolf938 share 55% of their medical history (Jaccard = 0.55), including COVID, Hypoxemia, Pneumonia, Fatigue, and Obesity."
    replaced = f'{match.group(1)}{new_answer}{match.group(2)}'
    print("Replacement would work")
else:
    print("No match found")
    
    # Let's debug step by step
    print("\n--- Debugging ---")
    # 1. Find the question
    question_pattern = re.escape(question)
    question_match = re.search(question_pattern, content)
    if question_match:
        print(f"1. Question found at position {question_match.start()}")
        # 2. Look for closing </div> after question
        after_question = content[question_match.end():]
        closing_div_match = re.search(r'</div>', after_question)
        if closing_div_match:
            print(f"2. Closing </div> found at relative position {closing_div_match.start()}")
            # 3. Look for accordion-content div
            after_closing_div = after_question[closing_div_match.end():]
            accordion_match = re.search(r'<div class="accordion-content">', after_closing_div)
            if accordion_match:
                print(f"3. accordion-content div found at relative position {accordion_match.start()}")
                # 4. Look what comes after accordion-content div
                after_accordion = after_closing_div[accordion_match.end():]
                print(f"4. Text after accordion-content div: {repr(after_accordion[:100])}")
                
                # Check if it starts with whitespace then <p>
                if re.match(r'\s*<p><strong>Direct Answer:</strong>', after_accordion):
                    print("5. FOUND: Whitespace then <p><strong>Direct Answer:</strong> directly after accordion-content")
                else:
                    print("5. Did NOT find expected pattern after accordion-content")
                    # Show first few possibilities
                    for i, char in enumerate(after_accordion[:20]):
                        print(f"   Char {i}: {repr(char)}")
            else:
                print("3. accordion-content div NOT found")
        else:
            print("2. Closing </div> NOT found")
    else:
        print("1. Question NOT found")
