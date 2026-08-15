#!/usr/bin/env python3
import re
with open('data/lep-html/canterbury-bankstown-lep.html', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('\xa0', ' ')
for m in re.finditer(r'Zone\s+E2', text):
    ctx = text[m.start()-20:m.start()+100].replace('\n', '|')
    print(repr(ctx))
