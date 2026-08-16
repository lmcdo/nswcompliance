#!/usr/bin/env python3
"""Quick check of downloaded LEP HTML files."""
import os, re, glob
from bs4 import BeautifulSoup

data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'lep-html')

for f in sorted(glob.glob(os.path.join(data_dir, '*.html'))):
    name = os.path.basename(f)
    size = os.path.getsize(f)
    with open(f, 'r', encoding='utf-8', errors='replace') as fh:
        html = fh.read()
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    zones = list(re.finditer(r'^Zone\s+([A-Z][A-Z]?\d?[A-Z]?)\s+(.+)$', text, re.MULTILINE))
    status = 'OK' if size > 100000 and len(zones) > 0 else ('SPA SHELL' if size < 10000 else 'NO ZONES')
    print(f"  {name:45s}  {size:>10,} bytes  {len(zones):>3} zones  {status}")
