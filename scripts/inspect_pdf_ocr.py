#!/usr/bin/env python3
"""Dump OCR'd text from a local PDF for inspection."""
import sys, os, base64, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'dcps')

parser = argparse.ArgumentParser()
parser.add_argument('filename')
parser.add_argument('--pages', default=None, help='e.g. 0-10')
parser.add_argument('--chars', type=int, default=6000)
args = parser.parse_args()

path = os.path.join(DATA_DIR, args.filename)
with open(path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
url = f'data:application/pdf;base64,{b64}'

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])
kwargs = dict(model='mistral-ocr-latest', document={'type': 'document_url', 'document_url': url}, include_image_base64=False)
if args.pages:
    s, e = args.pages.split('-')
    kwargs['pages'] = list(range(int(s), int(e)+1))

pages = client.ocr.process(**kwargs).pages
print(f'Pages: {len(pages)}')
text = '\n'.join(f'[PAGE {p.index+1}]\n{p.markdown}' for p in pages)
print(text[:args.chars])
