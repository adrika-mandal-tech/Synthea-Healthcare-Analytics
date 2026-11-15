import re

# Read the HTML file
with open('comprehensive_gds_analytics_report.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Test if we can find the question
question = "Q1: Which patients have similar clinical profiles based on shared conditions?"
pattern = re.escape(question)
match = re.search(pattern, content)
if match:
    print("Question found at position:", match.start())
    print("Context:", repr(content[match.start()-20:match.start()+20]))
else:
    print("Question NOT found")
    # Let's see what similar text exists
    if "Q1:" in content:
        pos = content.find("Q1:")
        print("Found 'Q1:' at:", pos)
        print("Context:", repr(content[pos-20:pos+50]))

# Let's look for the accordion-content div near where we think Q1 is
if "Q1:" in content:
    pos = content.find("Q1:")
    # Look ahead 500 characters
    look_ahead = content[pos:pos+500]
    print("Look ahead from Q1:", repr(look_ahead))
    
    # Look for accordion-content
    accordion_pos = look_ahead.find('accordion-content')
    if accordion_pos != -1:
        print("Found 'accordion-content' at relative position:", accordion_pos)
        print("Context:", repr(look_ahead[accordion_pos-20:accordion_pos+30]))
    else:
        print("Did not find 'accordion-content' in look ahead")
