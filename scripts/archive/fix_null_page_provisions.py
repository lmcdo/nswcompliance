#!/usr/bin/env python3
"""
Fix NULL pdf_page provisions for Leichhardt Part G and Part C Section 2 Distinctive Neighbourhoods.

Approach:
  1. Extract text from each PDF page (pdfplumber)
  2. Match each NULL provision to its PDF page via text search
  3. Render matched pages as PNG images (fitz, 2x zoom)
  4. Update regulatory_provisions: pdf_page, pdf_printed_page, pdf_page_image_url
"""

import re
import fitz          # PyMuPDF
import pdfplumber
import psycopg2
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

BASE = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine")

DB_CONFIG = dict(
    host='aws-1-ap-southeast-2.pooler.supabase.com',
    port=5432,
    user='postgres.llzdrxywpziewrzudwhj',
    password='eDDIYq8ottiaO9ll',
    dbname='postgres',
    connect_timeout=30,
)

# document_id → (pdf_path, image_folder, folder_slug)
DOCUMENT_MAP = {
    'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023': (
        BASE / 'downloads/leichhardt/Leichhardt_DCP_2013_Part_G_Section_1-12_Amdt19_Nov2023.pdf',
        BASE / 'frontend-nextjs/public/pdf-pages/leichhardt-part-g',
        'leichhardt-part-g',
    ),
    # All Part C Section 2 Distinctive Neighbourhood sub-documents share the same PDF
    '_PART_C_SECTION_2_': (
        BASE / 'downloads/leichhardt/Leichhardt_DCP_2013_Part_C_Section_2_Reduced.pdf',
        BASE / 'frontend-nextjs/public/pdf-pages/leichhardt-part-c2',
        'leichhardt-part-c2',
    ),
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Strip whitespace/control chars for reliable substring matching."""
    return re.sub(r'\s+', ' ', text or '').strip()


def get_search_snippet(provision_text: str, length: int = 80) -> str:
    """Get a clean snippet from the start of provision text for matching."""
    # Strip markdown-style headers (## heading) that may not appear in PDF
    text = re.sub(r'^#{1,4}\s+.+\n?', '', provision_text.strip(), flags=re.MULTILINE)
    return normalize(text)[:length]


def extract_page_texts(pdf_path: Path) -> dict[int, str]:
    """Return {1-indexed page number: normalized full-page text}."""
    texts = {}
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            raw = page.extract_text() or ''
            texts[i] = normalize(raw)
    print(f"  Extracted text from {len(texts)} pages")
    return texts


def find_page(snippet: str, page_texts: dict[int, str]) -> int | None:
    """Find the first page containing snippet. Returns 1-indexed page or None."""
    if not snippet:
        return None
    for page_num in sorted(page_texts):
        if snippet in page_texts[page_num]:
            return page_num
    # Fallback: try shorter snippet (first 40 chars)
    short = snippet[:40]
    if short:
        for page_num in sorted(page_texts):
            if short in page_texts[page_num]:
                return page_num
    return None


def render_page(pdf_doc, page_num: int, image_dir: Path, folder_slug: str) -> str:
    """Render PDF page to PNG at 2x zoom. Returns relative URL."""
    image_dir.mkdir(parents=True, exist_ok=True)
    filename = f'page_{page_num}.png'
    out_path = image_dir / filename
    if not out_path.exists():
        page = pdf_doc[page_num - 1]  # 0-indexed
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        pix.save(str(out_path))
        size_kb = out_path.stat().st_size / 1024
        print(f"    Rendered page {page_num} -> {filename} ({size_kb:.0f} KB)")
    else:
        print(f"    Page {page_num} image already exists, reusing")
    return f'/pdf-pages/{folder_slug}/{filename}'


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Fetch all NULL provisions grouped by document_id
    cur.execute("""
        SELECT id, document_id, provision_text
        FROM regulatory_provisions
        WHERE pdf_page IS NULL
          AND document_id ILIKE '%leichhardt%'
        ORDER BY document_id, id
    """)
    all_rows = cur.fetchall()
    print(f"Total NULL provisions to fix: {len(all_rows)}")
    print()

    # Group by document_id
    by_doc: dict[str, list] = {}
    for prov_id, doc_id, text in all_rows:
        by_doc.setdefault(doc_id, []).append((prov_id, text))

    total_matched = 0
    total_unmatched = 0

    for doc_id, provisions in by_doc.items():
        print(f"{'='*70}")
        print(f"Document: {doc_id}  ({len(provisions)} provisions)")

        # Resolve PDF path and image folder
        if doc_id in DOCUMENT_MAP:
            pdf_path, image_dir, folder_slug = DOCUMENT_MAP[doc_id]
        elif 'Part_C_Section_2' in doc_id or 'part_c_section_2' in doc_id.lower() or 'C2_2' in doc_id:
            _, (pdf_path, image_dir, folder_slug) = list(DOCUMENT_MAP.items())[1]
        else:
            print(f"  [SKIP] No PDF mapping found for this document_id")
            total_unmatched += len(provisions)
            continue

        if not pdf_path.exists():
            print(f"  [ERROR] PDF not found: {pdf_path}")
            total_unmatched += len(provisions)
            continue

        print(f"  PDF: {pdf_path.name}")

        # Extract page texts
        page_texts = extract_page_texts(pdf_path)

        # Open PDF once for rendering
        fitz_doc = fitz.open(str(pdf_path))

        matched = 0
        unmatched = []

        for prov_id, provision_text in provisions:
            snippet = get_search_snippet(provision_text)
            page_num = find_page(snippet, page_texts)

            if page_num:
                image_url = render_page(fitz_doc, page_num, image_dir, folder_slug)
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET pdf_page = %s,
                        pdf_printed_page = %s,
                        pdf_page_image_url = %s
                    WHERE id = %s
                """, (page_num, page_num, image_url, prov_id))
                matched += 1
                total_matched += 1
            else:
                unmatched.append((prov_id, snippet[:60]))
                total_unmatched += 1

        conn.commit()
        fitz_doc.close()

        print(f"  Matched: {matched}/{len(provisions)}")
        if unmatched:
            print(f"  Unmatched ({len(unmatched)}):")
            for uid, snip in unmatched[:10]:
                print(f"    ID {uid}: {snip!r}")
            if len(unmatched) > 10:
                print(f"    ... and {len(unmatched)-10} more")

    cur.close()
    conn.close()

    print()
    print('='*70)
    print(f"DONE  —  matched: {total_matched}  unmatched: {total_unmatched}")
    print('='*70)
    if total_unmatched:
        print("Note: unmatched provisions still have NULL pdf_page.")
        print("They may use OCR-resistant formatting or be in a different PDF section.")


if __name__ == '__main__':
    main()
