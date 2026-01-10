#!/usr/bin/env python3
"""Validate PDF coverage for SEPP requirements."""

import sys, json, re
from pathlib import Path
import requests


class PDFCoverageValidator:
    def __init__(self, sepp_name=None):
        self.sepp_name = sepp_name
        self.missing_pdfs = []
        self.inaccessible_pdfs = []

    def validate(self, data):
        pdf_refs = data.get('pdf_references', [])
        if not pdf_refs:
            print("  No PDF references")
            return True

        if not self.sepp_name and pdf_refs:
            match = re.search(r'/pdf-pages/([^/]+)/', pdf_refs[0].get('url', ''))
            if match:
                self.sepp_name = match.group(1)

        for ref in pdf_refs:
            page, section, url = ref.get('page'), ref.get('section'), ref.get('url')
            if self.sepp_name:
                local = Path(f'frontend-nextjs/public/pdf-pages/{self.sepp_name}/page-{page}.png')
                if not local.exists():
                    self.missing_pdfs.append({'page': page, 'section': section, 'path': str(local)})
            if url:
                try:
                    r = requests.head(url, timeout=10)
                    if r.status_code != 200:
                        self.inaccessible_pdfs.append({'page': page, 'section': section, 'status': r.status_code})
                except Exception as e:
                    self.inaccessible_pdfs.append({'page': page, 'section': section, 'error': str(e)})

        return not self.missing_pdfs and not self.inaccessible_pdfs

    def print_report(self):
        if not self.missing_pdfs and not self.inaccessible_pdfs:
            print("\nOK All PDFs present and accessible!")
            return
        if self.missing_pdfs:
            print(f"\nERROR MISSING LOCAL FILES ({len(self.missing_pdfs)}):")
            for m in self.missing_pdfs:
                print(f"  Page {m['page']} (Section {m['section']}): {m['path']}")
        if self.inaccessible_pdfs:
            print(f"\nERROR INACCESSIBLE R2 URLS ({len(self.inaccessible_pdfs)}):")
            for m in self.inaccessible_pdfs:
                status = m.get('error', f"HTTP {m.get('status')}")
                print(f"  Page {m['page']} (Section {m['section']}): {status}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_pdf_coverage.py data.json")
        sys.exit(1)
    try:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"\nValidating PDF coverage: {sys.argv[1]}")
    print("=" * 60)
    v = PDFCoverageValidator()
    ok = v.validate(data)
    v.print_report()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
