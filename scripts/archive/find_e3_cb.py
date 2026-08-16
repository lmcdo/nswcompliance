#!/usr/bin/env python3
import re
with open('data/lep-html/canada-bay-lep.html', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('\xa0', ' ')
text = re.sub(r'(Zone\s+[A-Z][A-Z]?\d?[A-Z]?)\s*\n\s*(?=[A-Z])', r'\1   ', text)
for m in re.finditer(r'Zone\s+E3', text):
    ctx = text[m.start():m.start()+200].replace('\n', '|')
    print(repr(ctx[:200]))
    print()
