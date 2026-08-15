#!/usr/bin/env python3
"""Debug: check what zone headings look like in LEP HTML."""
import re, sys
from bs4 import BeautifulSoup

fname = sys.argv[1] if len(sys.argv) > 1 else 'data/lep-html/blacktown-lep.html'
with open(fname, 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
text = soup.get_text(separator='\n')

print(f"Total text length: {len(text):,}")

# Look for "Zone" followed by letter+number patterns
print("\n=== Lines starting with 'Zone' ===")
count = 0
for line in text.split('\n'):
    line = line.strip()
    if re.match(r'Zone\s+[A-Z]', line):
        print(f"  {repr(line[:100])}")
        count += 1
        if count > 10:
            break

# Also check for the multiline regex pattern used in scraper
print(f"\n=== Regex finditer ===")
zone_pattern = re.compile(r'^Zone\s+([A-Z][A-Z]?\d?[A-Z]?)\s+(.+)$', re.MULTILINE)
matches = list(zone_pattern.finditer(text))
print(f"Found {len(matches)} matches")
for m in matches[:5]:
    print(f"  {m.group(0)[:80]}")

# Check for "Land Use Table" section
print(f"\n=== 'Land Use Table' occurrences ===")
for i, line in enumerate(text.split('\n')):
    if 'Land Use Table' in line:
        print(f"  Line {i}: {line.strip()[:100]}")

# Check for zone headings in HTML elements
print(f"\n=== Zone headings in HTML ===")
for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span']):
    t = el.get_text().strip()
    if re.match(r'Zone\s+[A-Z]', t) and len(t) < 100:
        print(f"  <{el.name}> {repr(t[:80])}")
        count += 1
        if count > 15:
            break
