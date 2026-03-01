# LGA Extraction Pipeline: Production Implementation

**Created:** 2026-02-13
**Status:** Implementation Specification
**Related:** `lga-onboarding-infrastructure.md` (strategic framework)

---

## Executive Summary

**Goal:** Build a reliable, accurate, complete extraction pipeline that processes any LGA's DCP from PDF → validated database provisions in <8 hours with >95% accuracy.

**Key Requirements:**
- **Reliable:** Zero data loss, automatic retry, comprehensive error handling
- **Accurate:** Dual-pass LLM validation, human review queue for low-confidence results
- **Complete:** 100% provision coverage, no silent failures
- **Auditable:** Full lineage tracking from PDF page → database row
- **Scalable:** Processes 1 LGA (300-page DCP) → 130 LGAs (39,000 pages)

**Current State (Inner West):**
- ✅ **Extraction works** for 3 councils (Ashfield, Leichhardt, Marrickville)
- ⚠️ **Manual configuration** required (4-5 hours per council)
- ❌ **No validation pipeline** (LLM results applied directly without review)
- ❌ **No error recovery** (failures = manual rerun)

**Target State:**
- ✅ **Automated end-to-end** (PDF upload → ready for production)
- ✅ **Built-in validation** (dual-pass LLM + human review queue)
- ✅ **Resilient processing** (automatic retry, dead letter queue)
- ✅ **Quality gates** (provision count checks, missing data alerts)

---

## Architecture Overview

### **Pipeline Stages**

```
┌─────────────────────────────────────────────────────────────────┐
│                      EXTRACTION PIPELINE                         │
└─────────────────────────────────────────────────────────────────┘

Stage 1: PDF Ingestion
├─ Upload PDF to storage (S3/Supabase Storage)
├─ Extract metadata (council, document type, version)
├─ OCR if needed (PDF scanned vs searchable)
└─ Output: Raw PDF + metadata → Stage 2

Stage 2: Structure Discovery
├─ Extract TOC (PDF bookmarks / heading detection)
├─ Detect DCP naming convention (Part/Chapter/Section)
├─ Identify hierarchy depth (2-4 levels)
├─ Generate part_titles config
└─ Output: DCP structure JSON → Stage 3

Stage 3: Page-Level Extraction
├─ Convert PDF pages → images (for PDF link generation)
├─ Extract text per page with layout analysis
├─ Detect section headers, tables, lists
├─ OCR corrections (common artifacts)
└─ Output: page_text[] + page_images[] → Stage 4

Stage 4: Provision Splitting
├─ Detect provision boundaries (C1, C2, O1, etc.)
├─ Link provisions to DCP parts/sections
├─ Extract page numbers (pdf_page, pdf_printed_page)
├─ Generate provision UUIDs for lineage tracking
└─ Output: raw_provisions[] → Stage 5

Stage 5: LLM Enrichment (Dual-Pass)
├─ Pass 1: Marker classification (heritage, flooding, etc.)
├─ Pass 2: Independent re-classification
├─ Validation: Compare Pass 1 vs Pass 2
├─ Flag mismatches or low confidence (<0.9)
└─ Output: tagged_provisions[] + review_queue[] → Stage 6

Stage 6: Spatial Area Linking
├─ Extract spatial areas from provisions (HCAs, precincts)
├─ Pattern matching: DCP section → area slug
├─ Text analysis: area name mentioned
└─ Output: provisions with v2_spatial_area_id → Stage 7

Stage 7: Quality Assurance
├─ Provision count check (expected vs actual)
├─ Missing data detection (NULL markers, topics)
├─ Duplicate detection (same text, different IDs)
├─ Cross-reference validation
└─ Output: QA report + validated_provisions[] → Stage 8

Stage 8: Database Insert
├─ Batch insert provisions (1000 rows/batch)
├─ Update council_config table
├─ Populate spatial_areas table
├─ Create version 1 baseline
└─ Output: DB ready for production
```

---

## Stage 1: PDF Ingestion

### **Input**
```python
{
  "pdf_url": "https://example.com/parramatta-dcp.pdf",
  "council_slug": "parramatta",
  "document_type": "DCP",  # or "LEP", "SEPP"
  "version": "v1.0-baseline",
  "uploaded_by": "user@example.com"
}
```

### **Process**

**1.1 Upload to Storage**
```python
import boto3
from pathlib import Path

def upload_pdf(pdf_path: str, council_slug: str) -> dict:
    """Upload PDF to S3/Supabase Storage."""
    s3 = boto3.client('s3')
    bucket = 'plotdetect-documents'
    key = f'councils/{council_slug}/dcp/{Path(pdf_path).name}'

    with open(pdf_path, 'rb') as f:
        s3.upload_fileobj(f, bucket, key)

    return {
        'storage_url': f's3://{bucket}/{key}',
        'public_url': f'https://{bucket}.s3.amazonaws.com/{key}',
        'file_size_mb': Path(pdf_path).stat().st_size / 1_000_000
    }
```

**1.2 Extract Metadata**
```python
import fitz  # PyMuPDF

def extract_pdf_metadata(pdf_path: str) -> dict:
    """Extract PDF metadata and detect if OCR is needed."""
    doc = fitz.open(pdf_path)

    metadata = {
        'page_count': len(doc),
        'has_toc': len(doc.get_toc()) > 0,
        'is_searchable': False,
        'needs_ocr': False,
        'title': doc.metadata.get('title'),
        'author': doc.metadata.get('author'),
        'creation_date': doc.metadata.get('creationDate')
    }

    # Check if PDF is searchable (has text layer)
    text_content = ''
    for page_num in range(min(5, len(doc))):  # Check first 5 pages
        text_content += doc[page_num].get_text()

    metadata['is_searchable'] = len(text_content.strip()) > 100
    metadata['needs_ocr'] = not metadata['is_searchable']

    doc.close()
    return metadata
```

**1.3 OCR if Needed**
```python
from pdf2image import convert_from_path
import pytesseract

def ocr_pdf(pdf_path: str, output_path: str) -> str:
    """OCR scanned PDF and create searchable PDF."""
    # Convert PDF pages to images
    images = convert_from_path(pdf_path, dpi=300)

    # OCR each page
    searchable_pages = []
    for i, image in enumerate(images):
        # Use Tesseract to get hOCR output
        hocr = pytesseract.image_to_pdf_or_hocr(image, extension='hocr')
        searchable_pages.append(hocr)

    # Combine into searchable PDF
    # (Implementation depends on OCR library - use ocrmypdf for production)
    import ocrmypdf
    ocrmypdf.ocr(pdf_path, output_path, deskew=True, rotate_pages=True)

    return output_path
```

**1.4 Create Document Record**
```python
def create_document_record(
    council_slug: str,
    storage_url: str,
    metadata: dict
) -> int:
    """Create document record in versions.document_versions."""
    import psycopg2

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO versions.document_versions (
            document_id, council_slug, document_type, version_number,
            status, page_count, storage_url, metadata, created_at
        ) VALUES (
            %(document_id)s, %(council_slug)s, %(document_type)s,
            %(version)s, 'processing', %(page_count)s, %(storage_url)s,
            %(metadata)s, NOW()
        )
        RETURNING id
    """, {
        'document_id': f'{council_slug.title()} DCP 2024',
        'council_slug': council_slug,
        'document_type': 'DCP',
        'version': 'v1.0-baseline',
        'page_count': metadata['page_count'],
        'storage_url': storage_url,
        'metadata': metadata
    })

    doc_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return doc_id
```

### **Output**
```python
{
  "document_id": 123,
  "storage_url": "s3://plotdetect-documents/councils/parramatta/dcp/parramatta-dcp-2024.pdf",
  "page_count": 342,
  "is_searchable": True,
  "needs_ocr": False,
  "status": "processing"
}
```

### **Error Handling**
```python
class PDFIngestionError(Exception):
    """Base exception for PDF ingestion failures."""
    pass

def ingest_pdf_with_retry(pdf_path: str, council_slug: str, max_retries: int = 3):
    """Ingest PDF with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            # Upload
            storage = upload_pdf(pdf_path, council_slug)

            # Extract metadata
            metadata = extract_pdf_metadata(pdf_path)

            # OCR if needed
            if metadata['needs_ocr']:
                ocr_path = f'/tmp/{council_slug}_ocr.pdf'
                ocr_pdf(pdf_path, ocr_path)
                pdf_path = ocr_path
                storage = upload_pdf(pdf_path, council_slug)

            # Create record
            doc_id = create_document_record(council_slug, storage['storage_url'], metadata)

            return {'document_id': doc_id, **storage, **metadata}

        except Exception as e:
            if attempt == max_retries - 1:
                # Final attempt failed - log to dead letter queue
                log_to_dlq('pdf_ingestion', {
                    'pdf_path': pdf_path,
                    'council_slug': council_slug,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                raise PDFIngestionError(f"Failed after {max_retries} attempts: {e}")

            # Retry with exponential backoff
            time.sleep(2 ** attempt)
```

---

## Stage 2: Structure Discovery

### **Input**
```python
{
  "document_id": 123,
  "pdf_path": "/path/to/parramatta-dcp.pdf"
}
```

### **Process**

**2.1 Extract Table of Contents**
```python
import fitz

def extract_toc(pdf_path: str) -> list:
    """Extract TOC from PDF bookmarks."""
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()  # Returns [(level, title, page), ...]

    structured_toc = []
    for level, title, page in toc:
        # Detect section number patterns
        section_match = re.match(r'^(Part|Chapter|Section)?\s*([A-Z]?\d+(?:\.\d+)*)\s+(.+)', title, re.IGNORECASE)

        if section_match:
            prefix, number, text = section_match.groups()
            structured_toc.append({
                'level': level,
                'section_id': number,
                'section_prefix': prefix or 'Part',
                'title': text.strip(),
                'page': page,
                'full_text': title
            })
        else:
            # No section number - likely intro/appendix
            structured_toc.append({
                'level': level,
                'section_id': None,
                'section_prefix': None,
                'title': title.strip(),
                'page': page,
                'full_text': title
            })

    doc.close()
    return structured_toc
```

**2.2 Detect Naming Convention**
```python
def detect_naming_convention(toc: list) -> str:
    """Detect DCP naming convention from TOC."""
    prefixes = [item['section_prefix'] for item in toc if item['section_prefix']]

    prefix_counts = {}
    for prefix in prefixes:
        prefix_lower = prefix.lower()
        prefix_counts[prefix_lower] = prefix_counts.get(prefix_lower, 0) + 1

    if not prefix_counts:
        return 'numeric'  # No prefixes found

    # Most common prefix
    most_common = max(prefix_counts, key=prefix_counts.get)
    return most_common  # 'part', 'chapter', 'section'
```

**2.3 LLM-Assisted Part Classification**
```python
def classify_dcp_parts_llm(toc: list, council_slug: str) -> dict:
    """Use LLM to classify DCP parts by content type."""

    prompt = f"""
Analyze this DCP table of contents and classify each part's content type.

Council: {council_slug.title()}

TOC:
{json.dumps(toc, indent=2)}

For each section, classify as:
- statutory: Legal requirements, zoning, land use tables
- general: Council-wide development controls
- zone_specific: Zone-based provisions (R1, R4, B4, etc.)
- dev_type: Development type provisions (dwelling, commercial, etc.)
- constraint: Environmental/heritage constraints
- precinct: Precinct-specific controls
- procedural: Application requirements, processes
- definitions: Glossary, definitions, interpretations

Output JSON only:
{{
  "parts": [
    {{"section_id": "1", "title": "Introduction", "content_type": "procedural"}},
    {{"section_id": "4.1", "title": "Residential Development", "content_type": "dev_type"}},
    ...
  ],
  "naming_convention": "part|chapter|section",
  "max_depth": 3,
  "priority_sections": ["8", "4.1", "2"]  // Most important for compliance
}}
"""

    response = llm.complete(prompt, model='claude-sonnet-4-5')
    result = json.loads(response)

    return result
```

**2.4 Generate council_config Entry**
```python
def generate_council_config(
    council_slug: str,
    toc_analysis: dict
) -> dict:
    """Generate council_config table entry from TOC analysis."""

    part_titles = []
    for part in toc_analysis['parts']:
        part_titles.append({
            'id': part['section_id'],
            'title': part['title'],
            'depth': part.get('level', 1),
            'content_type': part['content_type']
        })

    return {
        'council_slug': council_slug,
        'display_name': council_slug.replace('_', ' ').title(),
        'dcp_naming_convention': toc_analysis['naming_convention'],
        'part_titles': part_titles,
        'max_hierarchy_depth': toc_analysis['max_depth'],
        'priority_markers': [],  # Will be set in Phase 2 (provision density analysis)
        'has_precincts': False,  # Will be detected in Stage 6
        'has_hcas': False,
        'created_at': datetime.now().isoformat()
    }
```

### **Output**
```python
{
  "document_id": 123,
  "toc": [
    {"level": 1, "section_id": "1", "title": "Introduction", "page": 1, "content_type": "procedural"},
    {"level": 1, "section_id": "4", "title": "Development Controls", "page": 45, "content_type": "general"},
    {"level": 2, "section_id": "4.1", "title": "Residential", "page": 46, "content_type": "dev_type"},
    ...
  ],
  "naming_convention": "part",
  "max_depth": 4,
  "council_config": {...}
}
```

### **Error Handling**
- **No TOC found:** Fall back to heading detection (font size, bold text)
- **Malformed section numbers:** Flag for manual review
- **LLM classification fails:** Use rule-based fallback (keyword matching)

---

## Stage 3: Page-Level Extraction

### **Input**
```python
{
  "document_id": 123,
  "pdf_path": "/path/to/parramatta-dcp.pdf",
  "toc": [...]
}
```

### **Process**

**3.1 Convert Pages to Images**
```python
from pdf2image import convert_from_path

def convert_pages_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 150
) -> list:
    """Convert PDF pages to PNG images for web display."""

    images = convert_from_path(pdf_path, dpi=dpi)

    image_paths = []
    for i, image in enumerate(images):
        output_path = f'{output_dir}/page_{i}.png'
        image.save(output_path, 'PNG')
        image_paths.append(output_path)

    return image_paths
```

**3.2 Extract Text with Layout Analysis**
```python
import pdfplumber

def extract_page_text_with_layout(pdf_path: str, page_num: int) -> dict:
    """Extract text with layout structure (tables, lists, headings)."""

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]

        # Extract plain text
        text = page.extract_text()

        # Extract tables
        tables = page.extract_tables()

        # Detect headings (larger font size, bold)
        words = page.extract_words(keep_blank_chars=True)
        headings = []
        for word in words:
            if word['size'] > 12 and 'Bold' in word.get('fontname', ''):
                headings.append({
                    'text': word['text'],
                    'x': word['x0'],
                    'y': word['top'],
                    'size': word['size']
                })

        # Detect lists (indented text with bullets/numbers)
        lines = text.split('\n')
        lists = []
        current_list = []
        for line in lines:
            if re.match(r'^\s*[•\-\*\d+\.]\s+', line):
                current_list.append(line.strip())
            elif current_list:
                lists.append(current_list)
                current_list = []

        return {
            'page_num': page_num,
            'text': text,
            'tables': tables,
            'headings': headings,
            'lists': lists,
            'width': page.width,
            'height': page.height
        }
```

**3.3 OCR Artifact Correction**
```python
def clean_ocr_artifacts(text: str) -> str:
    """Fix common OCR errors and PDF extraction artifacts."""

    corrections = {
        # UTF-8 mojibake
        'â€"': '—',   # em-dash
        'â€™': "'",   # right single quote
        'â€œ': '"',   # left double quote
        'â€\x9d': '"',  # right double quote

        # Common OCR errors
        'rn': 'm',    # "rn" misread as "m"
        '|': 'I',     # pipe misread as capital I (context-dependent)
        '0': 'O',     # zero misread as letter O (context-dependent)

        # Word artifacts
        'Error! Reference source not found.': '[REFERENCE ERROR]',
        'Error! Bookmark not defined.': '[BOOKMARK ERROR]',

        # Extra whitespace
        r'\s+': ' ',  # Multiple spaces → single space
        r'\n{3,}': '\n\n',  # Multiple newlines → double newline
    }

    cleaned = text
    for pattern, replacement in corrections.items():
        cleaned = re.sub(pattern, replacement, cleaned)

    return cleaned.strip()
```

**3.4 Batch Process All Pages**
```python
def extract_all_pages(
    pdf_path: str,
    document_id: int,
    batch_size: int = 50
) -> list:
    """Extract all pages with batching and progress tracking."""

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

    pages_data = []

    for batch_start in range(0, total_pages, batch_size):
        batch_end = min(batch_start + batch_size, total_pages)

        print(f"Processing pages {batch_start}-{batch_end}/{total_pages}")

        for page_num in range(batch_start, batch_end):
            page_data = extract_page_text_with_layout(pdf_path, page_num)
            page_data['text'] = clean_ocr_artifacts(page_data['text'])
            pages_data.append(page_data)

        # Save progress checkpoint
        save_checkpoint(document_id, pages_data)

    return pages_data
```

### **Output**
```python
{
  "document_id": 123,
  "pages": [
    {
      "page_num": 0,
      "text": "Part 4: Development Controls\n\n4.1 Residential Development\n...",
      "tables": [[["Header1", "Header2"], ["Data1", "Data2"]]],
      "headings": [{"text": "Part 4: Development Controls", "size": 16}],
      "lists": [["• Item 1", "• Item 2"]],
      "image_path": "/storage/page_0.png"
    },
    ...
  ],
  "total_pages": 342
}
```

---

## Stage 4: Provision Splitting

### **Input**
```python
{
  "document_id": 123,
  "pages": [...],  # From Stage 3
  "toc": [...]     # From Stage 2
}
```

### **Process**

**4.1 Detect Provision Boundaries**
```python
def detect_provision_markers(text: str) -> list:
    """Detect provision markers (C1, C2, O1, etc.) in text."""

    # Common marker patterns across councils
    patterns = [
        r'\b([CO])\s*(\d+)\b',              # C1, O1
        r'\b([CO])(\d+\.\d+)\b',            # C1.1, O2.3
        r'\b(Control|Objective)\s*(\d+)',   # Control 1, Objective 2
        r'^\s*(\d+)\.\s+',                  # Numbered list (1., 2., 3.)
    ]

    markers = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            markers.append({
                'type': match.group(1) if len(match.groups()) == 2 else 'numbered',
                'number': match.group(2) if len(match.groups()) == 2 else match.group(1),
                'position': match.start(),
                'full_text': match.group(0)
            })

    return sorted(markers, key=lambda x: x['position'])
```

**4.2 Split Text into Provisions**
```python
def split_into_provisions(
    page_text: str,
    page_num: int,
    section_id: str
) -> list:
    """Split page text into individual provisions."""

    markers = detect_provision_markers(page_text)

    if not markers:
        # No markers found - treat entire page as one provision
        return [{
            'provision_text': page_text.strip(),
            'marker_type': None,
            'marker_number': None,
            'page_num': page_num,
            'section_id': section_id
        }]

    provisions = []

    for i, marker in enumerate(markers):
        # Get text from current marker to next marker (or end of page)
        start = marker['position']
        end = markers[i+1]['position'] if i+1 < len(markers) else len(page_text)

        provision_text = page_text[start:end].strip()

        provisions.append({
            'provision_text': provision_text,
            'marker_type': marker['type'],
            'marker_number': marker['number'],
            'page_num': page_num,
            'section_id': section_id,
            'uuid': str(uuid.uuid4())  # For lineage tracking
        })

    return provisions
```

**4.3 Link Provisions to DCP Sections**
```python
def link_provisions_to_sections(
    provisions: list,
    toc: list
) -> list:
    """Link each provision to its DCP part/section from TOC."""

    # Build page-to-section mapping from TOC
    page_section_map = {}
    for item in toc:
        page_section_map[item['page']] = item['section_id']

    # Assign sections to provisions
    for prov in provisions:
        page = prov['page_num']

        # Find nearest TOC section (going backwards)
        section_id = None
        for p in range(page, -1, -1):
            if p in page_section_map:
                section_id = page_section_map[p]
                break

        prov['v2_dcp_part'] = section_id

    return provisions
```

**4.4 Extract Page Numbers**
```python
def extract_page_numbers(page_text: str, page_num: int) -> dict:
    """Extract printed page number from PDF footer/header."""

    # Common page number patterns
    patterns = [
        r'Page\s+(\d+)',                # "Page 45"
        r'^(\d+)\s*$',                  # "45" alone
        r'[\|\s](\d+)[\|\s]',          # "| 45 |"
    ]

    for pattern in patterns:
        match = re.search(pattern, page_text[-200:], re.MULTILINE | re.IGNORECASE)
        if match:
            return {
                'pdf_page': page_num,
                'pdf_printed_page': int(match.group(1))
            }

    # Fallback: assume pdf_page = printed_page
    return {
        'pdf_page': page_num,
        'pdf_printed_page': page_num
    }
```

### **Output**
```python
{
  "document_id": 123,
  "provisions": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "provision_text": "C1\nThe minimum lot size for subdivision shall be 450m².",
      "marker_type": "C",
      "marker_number": "1",
      "page_num": 45,
      "pdf_printed_page": 87,
      "v2_dcp_part": "4.1",
      "section_id": "4.1"
    },
    ...
  ],
  "total_provisions": 1847
}
```

---

## Stage 5: LLM Enrichment (Dual-Pass Validation)

### **Input**
```python
{
  "document_id": 123,
  "provisions": [...]  # From Stage 4
}
```

### **Process**

**5.1 Dual-Pass Marker Classification**
```python
async def classify_provision_dual_pass(
    provision_text: str,
    provision_id: str
) -> dict:
    """Classify provision marker with dual-pass validation."""

    prompt = """
Classify this DCP provision's primary regulatory trigger.

MARKERS (choose ONE):
- heritage: Heritage items, conservation areas, archaeology
- flooding: Flood risk, stormwater, drainage
- tree_canopy: Tree preservation, landscaping, green cover
- parking: Parking rates, vehicle access, loading
- acoustic: Noise, sound attenuation
- height: Building height limits
- fsr: Floor space ratio, GFA
- setback: Building setbacks, boundary clearances
- open_space: Private open space, deep soil
- character: Streetscape character, built form
- subdivision: Lot size, subdivision controls

Provision: "{provision_text}"

Output JSON only:
{{"marker": "heritage", "confidence": 0.95, "reasoning": "Mentions HCA and contributory buildings"}}
"""

    # Pass 1
    response1 = await llm_async.complete(prompt.format(provision_text=provision_text))
    result1 = json.loads(response1)

    # Pass 2 (independent, no context from Pass 1)
    response2 = await llm_async.complete(prompt.format(provision_text=provision_text))
    result2 = json.loads(response2)

    # Validation
    mismatch = result1['marker'] != result2['marker']
    avg_confidence = (result1['confidence'] + result2['confidence']) / 2

    return {
        'provision_id': provision_id,
        'marker': result1['marker'],  # Use Pass 1 as canonical
        'confidence': avg_confidence,
        'mismatch': mismatch,
        'requires_review': mismatch or avg_confidence < 0.9,
        'pass1': result1,
        'pass2': result2
    }
```

**5.2 Batch Processing with Concurrency**
```python
import asyncio
from asyncio import Semaphore

async def enrich_provisions_batch(
    provisions: list,
    batch_size: int = 50,
    max_concurrent: int = 10
) -> tuple:
    """Process provisions in batches with concurrency limit."""

    semaphore = Semaphore(max_concurrent)

    async def classify_with_semaphore(prov):
        async with semaphore:
            return await classify_provision_dual_pass(
                prov['provision_text'],
                prov['uuid']
            )

    auto_tagged = []
    review_queue = []

    # Process in batches to avoid rate limits
    for batch_start in range(0, len(provisions), batch_size):
        batch = provisions[batch_start:batch_start + batch_size]

        print(f"Processing batch {batch_start//batch_size + 1}/{len(provisions)//batch_size + 1}")

        # Concurrent processing within batch
        results = await asyncio.gather(*[
            classify_with_semaphore(prov) for prov in batch
        ])

        for result in results:
            if result['requires_review']:
                review_queue.append(result)
            else:
                auto_tagged.append(result)

        # Rate limiting: 2-second pause between batches
        await asyncio.sleep(2)

    return auto_tagged, review_queue
```

**5.3 Review Queue Interface**
```python
def save_to_review_queue(
    review_items: list,
    document_id: int
) -> str:
    """Save flagged provisions to review queue for human validation."""

    review_file = f'review_queue_{document_id}.json'

    with open(review_file, 'w') as f:
        json.dump({
            'document_id': document_id,
            'total_flagged': len(review_items),
            'flagged_provisions': review_items,
            'created_at': datetime.now().isoformat()
        }, f, indent=2)

    print(f"""
╔══════════════════════════════════════════════════════╗
║       REVIEW QUEUE CREATED                           ║
╠══════════════════════════════════════════════════════╣
║ File: {review_file}                                  ║
║ Flagged provisions: {len(review_items)}              ║
║ Review rate: {len(review_items)/len(auto_tagged)*100:.1f}% ║
╚══════════════════════════════════════════════════════╝

Next step: Review flagged provisions and approve/override classifications.
Run: python review_provisions.py {review_file}
""")

    return review_file
```

### **Output**
```python
{
  "document_id": 123,
  "auto_tagged": 982,  # 53% (high confidence, no mismatch)
  "review_queue": 865,  # 47% (low confidence or mismatch)
  "total_provisions": 1847,
  "review_queue_file": "review_queue_123.json"
}
```

---

## Stage 6: Spatial Area Linking

### **Input**
```python
{
  "document_id": 123,
  "provisions": [...],  # Tagged provisions from Stage 5
  "council_slug": "parramatta"
}
```

### **Process**

**6.1 Extract Spatial Areas from Provisions**
```python
def extract_spatial_areas(provisions: list) -> list:
    """Detect mentions of HCAs, precincts, character areas in provisions."""

    patterns = {
        'hca': r'Heritage Conservation Area\s+([A-Z]?\d+)|HCA\s+([A-Z]?\d+)|C(\d+)',
        'precinct': r'Precinct\s+([A-Z\d]+)|Village\s+([A-Z]+)|Area\s+(\d+)',
        'tod': r'TOD\s+Precinct\s+([A-Z]+)|Station\s+Precinct\s+([A-Z\d]+)'
    }

    spatial_areas = {}

    for prov in provisions:
        for area_type, pattern in patterns.items():
            matches = re.findall(pattern, prov['provision_text'], re.IGNORECASE)
            for match in matches:
                # match is tuple of groups, get first non-empty
                area_id = next((g for g in match if g), None)
                if area_id:
                    key = f'{area_type}_{area_id}'
                    if key not in spatial_areas:
                        spatial_areas[key] = {
                            'area_type': area_type,
                            'area_id': area_id,
                            'db_slug': f'{area_type}_{area_id.lower()}',
                            'display_name': f'{area_type.upper()} {area_id}',
                            'provision_count': 0,
                            'dcp_sections': set()
                        }
                    spatial_areas[key]['provision_count'] += 1
                    spatial_areas[key]['dcp_sections'].add(prov['v2_dcp_part'])

    return list(spatial_areas.values())
```

**6.2 Link Provisions to Spatial Areas**
```python
def link_provisions_to_spatial_areas(
    provisions: list,
    spatial_areas: list
) -> list:
    """Link provisions to spatial areas via text matching and section patterns."""

    for prov in provisions:
        matched_area = None

        # Method 1: Section pattern matching
        for area in spatial_areas:
            if prov['v2_dcp_part'] in area['dcp_sections']:
                matched_area = area['db_slug']
                break

        # Method 2: Text analysis (area name mentioned)
        if not matched_area:
            for area in spatial_areas:
                if area['display_name'].lower() in prov['provision_text'].lower():
                    matched_area = area['db_slug']
                    break

        prov['v2_spatial_area_id'] = matched_area

    return provisions
```

**6.3 Create spatial_areas Table Entries**
```python
def create_spatial_areas(
    council_slug: str,
    spatial_areas: list
) -> None:
    """Insert spatial areas into database."""

    import psycopg2

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    for area in spatial_areas:
        # Infer DCP section pattern from provision sections
        sections = list(area['dcp_sections'])
        section_pattern = sections[0] if len(sections) == 1 else None

        cursor.execute("""
            INSERT INTO spatial_areas (
                council_slug, area_type, db_slug, display_name,
                dcp_section_pattern, created_at
            ) VALUES (
                %(council_slug)s, %(area_type)s, %(db_slug)s, %(display_name)s,
                %(section_pattern)s, NOW()
            )
            ON CONFLICT (council_slug, db_slug) DO NOTHING
        """, {
            'council_slug': council_slug,
            'area_type': area['area_type'],
            'db_slug': area['db_slug'],
            'display_name': area['display_name'],
            'section_pattern': section_pattern
        })

    conn.commit()
    conn.close()
```

### **Output**
```python
{
  "document_id": 123,
  "spatial_areas_detected": 15,
  "provisions_linked": 124,
  "spatial_areas": [
    {"area_type": "hca", "db_slug": "hca_14", "display_name": "HCA 14", "provision_count": 5},
    {"area_type": "precinct", "db_slug": "precinct_a", "display_name": "Precinct A", "provision_count": 18},
    ...
  ]
}
```

---

## Stage 7: Quality Assurance

### **Input**
```python
{
  "document_id": 123,
  "provisions": [...],  # Fully enriched provisions
  "expected_provision_count": 1850  # From manual review or historical data
}
```

### **Process**

**7.1 Provision Count Validation**
```python
def validate_provision_count(
    provisions: list,
    expected_count: int,
    tolerance: float = 0.05
) -> dict:
    """Validate provision count is within expected range."""

    actual_count = len(provisions)
    diff = abs(actual_count - expected_count)
    diff_pct = diff / expected_count

    if diff_pct > tolerance:
        return {
            'passed': False,
            'actual_count': actual_count,
            'expected_count': expected_count,
            'difference': diff,
            'difference_pct': f'{diff_pct*100:.1f}%',
            'error': f'Provision count outside tolerance: {diff} provisions ({diff_pct*100:.1f}%) difference'
        }

    return {
        'passed': True,
        'actual_count': actual_count,
        'expected_count': expected_count,
        'difference': diff
    }
```

**7.2 Missing Data Detection**
```python
def detect_missing_data(provisions: list) -> dict:
    """Detect provisions with missing critical fields."""

    missing_markers = [p for p in provisions if not p.get('marker')]
    missing_topics = [p for p in provisions if not p.get('v2_topic')]
    missing_pages = [p for p in provisions if p.get('pdf_page') is None]
    missing_sections = [p for p in provisions if not p.get('v2_dcp_part')]

    total = len(provisions)

    return {
        'missing_markers': {
            'count': len(missing_markers),
            'percentage': f'{len(missing_markers)/total*100:.1f}%',
            'sample_ids': [p['uuid'] for p in missing_markers[:5]]
        },
        'missing_topics': {
            'count': len(missing_topics),
            'percentage': f'{len(missing_topics)/total*100:.1f}%'
        },
        'missing_pages': {
            'count': len(missing_pages),
            'percentage': f'{len(missing_pages)/total*100:.1f}%'
        },
        'missing_sections': {
            'count': len(missing_sections),
            'percentage': f'{len(missing_sections)/total*100:.1f}%'
        }
    }
```

**7.3 Duplicate Detection**
```python
def detect_duplicates(provisions: list) -> list:
    """Detect provisions with identical text."""

    text_hash_map = {}
    duplicates = []

    for prov in provisions:
        # Create hash of provision text (normalized)
        normalized = prov['provision_text'].strip().lower()
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        text_hash = hashlib.md5(normalized.encode()).hexdigest()

        if text_hash in text_hash_map:
            duplicates.append({
                'original_id': text_hash_map[text_hash],
                'duplicate_id': prov['uuid'],
                'text': prov['provision_text'][:100]
            })
        else:
            text_hash_map[text_hash] = prov['uuid']

    return duplicates
```

**7.4 Generate QA Report**
```python
def generate_qa_report(
    document_id: int,
    provisions: list,
    expected_count: int
) -> dict:
    """Generate comprehensive QA report."""

    count_check = validate_provision_count(provisions, expected_count)
    missing_data = detect_missing_data(provisions)
    duplicates = detect_duplicates(provisions)

    # Overall pass/fail
    qa_passed = (
        count_check['passed'] and
        missing_data['missing_markers']['count'] == 0 and
        len(duplicates) == 0
    )

    report = {
        'document_id': document_id,
        'qa_passed': qa_passed,
        'timestamp': datetime.now().isoformat(),
        'checks': {
            'provision_count': count_check,
            'missing_data': missing_data,
            'duplicates': {
                'count': len(duplicates),
                'samples': duplicates[:5]
            }
        },
        'summary': {
            'total_provisions': len(provisions),
            'auto_tagged': len([p for p in provisions if not p.get('requires_review')]),
            'review_queue': len([p for p in provisions if p.get('requires_review')]),
            'spatial_linked': len([p for p in provisions if p.get('v2_spatial_area_id')])
        }
    }

    # Save report
    with open(f'qa_report_{document_id}.json', 'w') as f:
        json.dump(report, f, indent=2)

    return report
```

### **Output**
```python
{
  "document_id": 123,
  "qa_passed": False,
  "checks": {
    "provision_count": {
      "passed": True,
      "actual_count": 1847,
      "expected_count": 1850,
      "difference": 3
    },
    "missing_data": {
      "missing_markers": {"count": 0, "percentage": "0.0%"},
      "missing_topics": {"count": 124, "percentage": "6.7%"},
      "missing_pages": {"count": 0, "percentage": "0.0%"},
      "missing_sections": {"count": 8, "percentage": "0.4%"}
    },
    "duplicates": {
      "count": 12,
      "samples": [...]
    }
  },
  "summary": {
    "total_provisions": 1847,
    "auto_tagged": 982,
    "review_queue": 865,
    "spatial_linked": 124
  }
}
```

---

## Stage 8: Database Insert

### **Input**
```python
{
  "document_id": 123,
  "provisions": [...],  # QA-validated provisions
  "council_config": {...},
  "spatial_areas": [...]
}
```

### **Process**

**8.1 Batch Insert Provisions**
```python
import psycopg2
from psycopg2.extras import execute_batch

def insert_provisions_batch(
    provisions: list,
    document_id: int,
    batch_size: int = 1000
) -> int:
    """Batch insert provisions into regulatory_provisions table."""

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    inserted_count = 0

    for batch_start in range(0, len(provisions), batch_size):
        batch = provisions[batch_start:batch_start + batch_size]

        # Prepare batch insert
        insert_data = []
        for prov in batch:
            insert_data.append((
                document_id,
                prov['provision_text'],
                prov.get('marker_type'),
                prov.get('marker'),
                prov.get('v2_topic'),
                prov.get('v2_dcp_part'),
                prov.get('pdf_page'),
                prov.get('pdf_printed_page'),
                prov.get('v2_spatial_area_id'),
                prov.get('v2_is_actionable', True),
                prov.get('v2_display_priority', 'standard'),
                prov.get('uuid')
            ))

        # Batch insert
        execute_batch(cursor, """
            INSERT INTO regulatory_provisions (
                document_id, provision_text, provision_marker,
                v2_marker, v2_topic, v2_dcp_part,
                pdf_page, pdf_printed_page, v2_spatial_area_id,
                v2_is_actionable, v2_display_priority, lineage_uuid
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, insert_data)

        inserted_count += len(batch)
        print(f"Inserted {inserted_count}/{len(provisions)} provisions")

    conn.commit()
    conn.close()

    return inserted_count
```

**8.2 Update council_config**
```python
def update_council_config(council_config: dict) -> None:
    """Insert or update council configuration."""

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO council_config (
            council_slug, display_name, dcp_naming_convention,
            part_titles, max_hierarchy_depth, priority_markers,
            has_precincts, has_hcas, created_at
        ) VALUES (
            %(council_slug)s, %(display_name)s, %(dcp_naming_convention)s,
            %(part_titles)s, %(max_hierarchy_depth)s, %(priority_markers)s,
            %(has_precincts)s, %(has_hcas)s, NOW()
        )
        ON CONFLICT (council_slug) DO UPDATE SET
            part_titles = EXCLUDED.part_titles,
            has_precincts = EXCLUDED.has_precincts,
            has_hcas = EXCLUDED.has_hcas,
            updated_at = NOW()
    """, council_config)

    conn.commit()
    conn.close()
```

**8.3 Create Version 1 Baseline**
```python
def create_version_baseline(document_id: int) -> None:
    """Create version 1 baseline for all provisions."""

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Backfill provision_versions table
    cursor.execute("""
        INSERT INTO provision_versions (
            provision_id, version_number, provision_text, v2_marker,
            v2_topic, v2_dcp_part, effective_date, created_at
        )
        SELECT
            id, 1, provision_text, v2_marker, v2_topic, v2_dcp_part,
            NOW(), NOW()
        FROM regulatory_provisions
        WHERE document_id = %s
    """, (document_id,))

    # Update regulatory_provisions with version metadata
    cursor.execute("""
        UPDATE regulatory_provisions
        SET
            current_version_id = pv.id,
            is_current = true,
            version_count = 1,
            first_seen_date = NOW(),
            last_modified_date = NOW()
        FROM provision_versions pv
        WHERE regulatory_provisions.id = pv.provision_id
          AND regulatory_provisions.document_id = %s
    """, (document_id,))

    conn.commit()
    conn.close()
```

**8.4 Update Document Status**
```python
def mark_document_complete(document_id: int) -> None:
    """Mark document as successfully processed."""

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE versions.document_versions
        SET status = 'current', processed_at = NOW()
        WHERE id = %s
    """, (document_id,))

    conn.commit()
    conn.close()
```

### **Output**
```python
{
  "document_id": 123,
  "provisions_inserted": 1847,
  "council_config_updated": True,
  "spatial_areas_created": 15,
  "version_baseline_created": True,
  "status": "current",
  "processing_time_hours": 6.2
}
```

---

## Error Handling & Recovery

### **Dead Letter Queue (DLQ)**

```python
import json
from datetime import datetime

def log_to_dlq(stage: str, error_data: dict) -> None:
    """Log failed processing attempts to dead letter queue."""

    dlq_file = f'dlq_{datetime.now().strftime("%Y%m%d")}.jsonl'

    error_record = {
        'timestamp': datetime.now().isoformat(),
        'stage': stage,
        'error_data': error_data
    }

    with open(dlq_file, 'a') as f:
        f.write(json.dumps(error_record) + '\n')

    print(f"⚠️  Error logged to DLQ: {dlq_file}")
```

### **Checkpoint Recovery**

```python
def save_checkpoint(document_id: int, stage: str, data: dict) -> None:
    """Save processing checkpoint for crash recovery."""

    checkpoint_file = f'checkpoint_{document_id}_{stage}.json'

    with open(checkpoint_file, 'w') as f:
        json.dump({
            'document_id': document_id,
            'stage': stage,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }, f, indent=2)

def load_checkpoint(document_id: int, stage: str) -> dict:
    """Load checkpoint data to resume processing."""

    checkpoint_file = f'checkpoint_{document_id}_{stage}.json'

    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            return json.load(f)

    return None
```

### **Retry Logic**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def process_with_retry(func, *args, **kwargs):
    """Execute function with exponential backoff retry."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"Attempt failed: {e}")
        raise
```

---

## Monitoring & Metrics

### **Pipeline Metrics**

```python
class PipelineMetrics:
    """Track extraction pipeline metrics."""

    def __init__(self, document_id: int):
        self.document_id = document_id
        self.start_time = time.time()
        self.stage_times = {}
        self.provision_count = 0
        self.error_count = 0

    def start_stage(self, stage: str):
        self.stage_times[stage] = {'start': time.time()}

    def end_stage(self, stage: str, provision_count: int = 0):
        elapsed = time.time() - self.stage_times[stage]['start']
        self.stage_times[stage]['duration'] = elapsed
        self.stage_times[stage]['provision_count'] = provision_count

        print(f"✓ {stage}: {elapsed:.1f}s ({provision_count} provisions)")

    def record_error(self, stage: str, error: Exception):
        self.error_count += 1
        print(f"✗ {stage}: {error}")

    def summary(self) -> dict:
        total_time = time.time() - self.start_time

        return {
            'document_id': self.document_id,
            'total_time_seconds': total_time,
            'total_time_hours': total_time / 3600,
            'stages': self.stage_times,
            'provision_count': self.provision_count,
            'error_count': self.error_count,
            'provisions_per_second': self.provision_count / total_time
        }
```

---

## Testing Strategy

### **Unit Tests**

```python
import pytest

def test_detect_provision_markers():
    """Test provision marker detection."""
    text = """
    C1
    The minimum lot size shall be 450m².

    C2
    Building height shall not exceed 9m.
    """

    markers = detect_provision_markers(text)

    assert len(markers) == 2
    assert markers[0]['type'] == 'C'
    assert markers[0]['number'] == '1'
    assert markers[1]['type'] == 'C'
    assert markers[1]['number'] == '2'

def test_clean_ocr_artifacts():
    """Test OCR artifact cleaning."""
    text = "The setbackâ€"measured from the boundary"

    cleaned = clean_ocr_artifacts(text)

    assert cleaned == "The setback—measured from the boundary"
```

### **Integration Tests**

```python
def test_full_extraction_pipeline():
    """Test complete extraction pipeline end-to-end."""

    # Ingest test PDF
    result = ingest_pdf_with_retry('test_dcp.pdf', 'test_council')

    assert result['document_id'] is not None
    assert result['page_count'] > 0

    # Extract pages
    pages = extract_all_pages('test_dcp.pdf', result['document_id'])

    assert len(pages) == result['page_count']

    # Split provisions
    provisions = []
    for page in pages:
        page_provisions = split_into_provisions(page['text'], page['page_num'], '4.1')
        provisions.extend(page_provisions)

    assert len(provisions) > 0

    # Enrich (mock LLM)
    for prov in provisions:
        prov['marker'] = 'height'
        prov['confidence'] = 0.95

    # Insert to DB
    count = insert_provisions_batch(provisions, result['document_id'])

    assert count == len(provisions)
```

---

## Success Metrics

### **Reliability**
- ✅ Zero data loss (100% provision recovery)
- ✅ <1% error rate requiring manual intervention
- ✅ Automatic retry succeeds >95% of the time

### **Accuracy**
- ✅ >95% LLM auto-tagging accuracy (validated against human review)
- ✅ <5% provisions in review queue after dual-pass validation
- ✅ <1% duplicate provisions

### **Completeness**
- ✅ 100% provision coverage (no missing provisions)
- ✅ <1% missing critical fields (marker, topic, page)
- ✅ All QA checks pass before database insert

### **Performance**
- ✅ <8 hours total processing time for 300-page DCP
- ✅ <$50 LLM cost per council (at current Claude pricing)
- ✅ Scalable to 130 LGAs without infrastructure changes

---

## Next Steps

1. **Build Stage 1-4** (non-LLM stages first)
   - PDF ingestion, structure discovery, page extraction, provision splitting
   - Target: 2-3 days development

2. **Integrate LLM Enrichment** (Stage 5)
   - Dual-pass classification with review queue
   - Target: 1-2 days development + prompt tuning

3. **Build QA Pipeline** (Stage 7)
   - Automated validation checks
   - Target: 1 day development

4. **Test on Parramatta DCP**
   - First non-Inner West council
   - Identify edge cases and refine pipeline
   - Target: 1 week testing + iteration

5. **Production Deployment**
   - Deploy to staging, run on all 3 Inner West councils
   - Validate accuracy against existing data
   - Target: 1 week staging + production rollout

**Total Effort Estimate:** 3-4 weeks to production-ready pipeline

---

**Document Status:** ACTIVE - Use as technical reference for extraction pipeline implementation.
