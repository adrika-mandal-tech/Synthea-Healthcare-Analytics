import re

def extract_first_sentence(text):
    # Extract the first sentence (up to the first period that is followed by space or end)
    # We'll look for the first period that is not part of an abbreviation.
    # Simple: split by '.' and take the first part, then add a period.
    # But we want to keep the period.
    match = re.search(r'^([^.]*\.)', text)
    if match:
        return match.group(1).strip()
    # If no period found, return the first 100 characters or up to first space?
    # We'll return the text up to the first newline or 200 chars.
    match = re.search(r'^([^\n]{0,200})', text)
    if match:
        return match.group(1).strip()
    return text.strip()

def main():
    filename = 'comprehensive_gds_analytics_report.html'
    with open(filename, 'r') as f:
        content = f.read()
    
    # We'll use a regex to find each accordion header and then the following accordion-content.
    # We want to process the content in a way that we can replace.
    # We'll split by the accordion-header, but we need to know the question text.
    # Instead, we'll find all accordion headers and then for each, find the associated accordion-content.
    
    # Pattern for an accordion header: 
    header_pattern = r'(<div class="accordion-header">\s*<span>([^<]+)</span>[\s\S]*?</div>)'
    
    # We'll find all matches of the header pattern.
    matches = list(re.finditer(header_pattern, content))
    if not matches:
        print("No accordion headers found")
        return
    
    # We'll process from the end to the beginning to avoid index shifting.
    # We'll collect the replacements we want to make.
    replacements = []  # each replacement is (start, end, new_text)
    
    for match in matches:
        header_text = match.group(2)  # the text inside the span
        header_start = match.start()
        header_end = match.end()
        
        # Now, we need to find the accordion-content div that follows this header.
        # We'll look for the next '<div class="accordion-content">' after header_end.
        # We'll search from header_end onwards.
        content_start = content.find('<div class="accordion-content">', header_end)
        if content_start == -1:
            print(f"Could not find accordion-content for header: {header_text}")
            continue
        
        # Now, we need to find the end of this accordion-content div.
        # We'll assume that the accordion-content div is well-formed and we can find the matching closing div.
        # We'll start at content_start and parse until we find the closing div for this accordion-content.
        # We'll use a stack for div tags.
        pos = content_start
        stack = 0
        # We'll look for the opening tag we just found.
        opening_tag = '<div class="accordion-content">'
        if not content.startswith(opening_tag, content_start):
            print(f"Expected opening tag not found at {content_start}")
            continue
        pos += len(opening_tag)
        stack = 1  # we have opened one div
        
        # We'll now scan forward until we find the closing div that matches this opening.
        while pos < len(content) and stack > 0:
            # Look for the next div tag (opening or closing)
            # We'll look for '<div' and '</div>'
            div_open = content.find('<div', pos)
            div_close = content.find('</div>', pos)
            
            if div_open == -1 and div_close == -1:
                # No more div tags, break
                break
            
            if div_close != -1 and (div_open == -1 or div_close < div_open):
                # Found a closing div
                stack -= 1
                pos = div_close + 6  # move past '</div>'
            else:
                # Found an opening div
                stack += 1
                pos = div_open + 4  # move past '<div'
                # We need to skip the rest of the tag to get to the '>'
                # Find the next '>'
                gt = content.find('>', div_open)
                if gt == -1:
                    break
                pos = gt + 1
        
        if stack != 0:
            print(f"Could not find matching closing div for accordion-content starting at {content_start}")
            continue
        
        content_end = pos  # this is the index after the closing '</div>' of the accordion-content
        
        # Now, we have the accordion-content div: from content_start to content_end
        accordion_content_div = content[content_start:content_end]
        
        # Now, we want to find the supporting analysis paragraph in this accordion-content div.
        # We'll look for: '<p><strong>Supporting Analysis:</strong>'
        sa_pattern = r'<p><strong>Supporting Analysis:</strong>'
        sa_match = re.search(sa_pattern, accordion_content_div)
        if sa_match:
            # Extract the text of this paragraph until the next '</p>'
            sa_start = sa_match.start()
            # Find the end of the paragraph
            p_end = accordion_content_div.find('</p>', sa_match.end())
            if p_end == -1:
                print(f"Could not find end of p tag for supporting analysis in {header_text}")
                continue
            sa_text = accordion_content_div[sa_match.end():p_end]
            # Extract the first sentence
            direct_answer = extract_first_sentence(sa_text)
        else:
            # If we don't have supporting analysis, we'll try to use the Human Must Do or GSD Can Do?
            # For now, we'll use a placeholder.
            direct_answer = "See supporting analysis for details."
        
        # Now, we want to insert a direct answer paragraph at the beginning of the accordion-content div.
        # We want to insert right after the opening tag '<div class="accordion-content">' and before the first child.
        # The first child is: '\n          <div>'
        # We'll look for the first '<div>' after the opening tag.
        # We'll insert after the opening tag and before the first inner div.
        
        # We'll split the accordion_content_div into:
        #   opening_tag = '<div class="accordion-content">'
        #   the_rest = the part after the opening tag
        opening_tag = '<div class="accordion-content">'
        if not accordion_content_div.startswith(opening_tag):
            print(f"Accordion content div does not start with expected opening tag: {accordion_content_div[:50]}")
            continue
        
        the_rest = accordion_content_div[len(opening_tag):]
        
        # We want to insert: '\n          <p><strong>Direct Answer:</strong> [direct_answer]</p>\n          '
        # before the the_rest.
        new_accordion_content_div = opening_tag + '\n          <p><strong>Direct Answer:</strong> ' + direct_answer + '</p>\n          ' + the_rest
        
        # Now, we need to replace the old accordion_content_div in the content with the new one.
        # The old accordion_content_div is from content_start to content_end.
        # We'll replace that slice with new_accordion_content_div.
        replacements.append((content_start, content_end, new_accordion_content_div))
    
    # Now, apply replacements from the end to the beginning to avoid index shifting.
    replacements.sort(key=lambda x: x[0], reverse=True)
    new_content = content
    for start, end, replacement in replacements:
        new_content = new_content[:start] + replacement + new_content[end:]
    
    # Write back to the file
    with open(filename, 'w') as f:
        f.write(new_content)
    
    print(f"Processed {len(replacements)} questions.")

if __name__ == '__main__':
    main()
