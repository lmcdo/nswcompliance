# Marrickville DCP PDF Page Mapping Issue

## Problem

Database `pdf_page` values match image filename page numbers, but **do NOT match the actual DCP page numbers printed on the pages**.

Example:
- Database: `pdf_page = 17`
- Image file: `marr_Marrickville_DCP_2011_-_2_1_Urban_Design_page_17.png`
- **Actual DCP page printed on image: 13**
- **Offset: 4 pages** (cover + TOC before content)

## Root Cause

Marrickville DCP was extracted from **28 separate PDF files**, each starting from page 1 in the PDF file. Each PDF has its own offset due to cover pages, tables of contents, etc.

## PDF Source Documents and Page Ranges

### Part 2 - General Provisions

| PDF Document | File Page Range | Total Pages | Requirements |
|-------------|----------------|-------------|--------------|
| **2.1 Urban Design** | 3-18 | 16 pages | 20 reqs |
| **2.3 Site Context Analysis** | 5-16 | 12 pages | 23 reqs |
| **2.5 Equity of Access** | 9-17 | 9 pages | 15 reqs |
| **2.6 Acoustic and Visual Privacy** | 5-13 | 9 pages | 11 reqs |
| **2.7 Solar Access** | 5-16 | 12 pages | 10 reqs |
| **2.8 Social Impact** | 5-14 | 10 pages | 8 reqs |
| **2.10 Parking** | 10-19 | 10 pages | 16 reqs |
| **2.11 Fencing** | 6-12 | 7 pages | 9 reqs |
| **2.12 Signs and Advertising** | 10-14 | 5 pages | 13 reqs |
| **2.13 Biodiversity** | 6-14 | 9 pages | 8 reqs |
| **2.14 Unique Environmental** | 6-11 | 6 pages | 11 reqs |
| **2.16 Energy Efficiency** | 6-12 | 7 pages | 6 reqs |
| **2.17 Water Sensitive Urban** | 5-13 | 9 pages | 10 reqs |
| **2.25 Stormwater Management** | 5-13 | 9 pages | 8 reqs |

### Part 3 - Subdivision

| PDF Document | File Page Range | Total Pages | Requirements |
|-------------|----------------|-------------|--------------|
| **3.0 Part 3 Subdivision** | 6-10 | 5 pages | 6 reqs |

### Part 4 - Development Types

| PDF Document | File Page Range | Total Pages | Requirements |
|-------------|----------------|-------------|--------------|
| **4.1 Multi Dwelling Housing** | 7-42 | 36 pages | 67 reqs |
| **4.2 Residential Flat Buildings** | 6-36 | 31 pages | 72 reqs |
| **4.3 Boarding Houses** | 5-20 | 16 pages | 17 reqs |
| **4.4 Secondary Dwellings** | 6-16 | 11 pages | 25 reqs |
| **4.5 Dwelling House Alterations** | 6-9 | 4 pages | 8 reqs |

### Part 7 - Special Uses

| PDF Document | File Page Range | Total Pages | Requirements |
|-------------|----------------|-------------|--------------|
| **7.3 Sex Industry and Adult** | 9-17 | 9 pages | 7 reqs |

### Part 8 - Heritage

| PDF Document | File Page Range | Total Pages | Requirements |
|-------------|----------------|-------------|--------------|
| **8.0 Heritage** | 8-60 | 53 pages | 27 reqs |
| **8.0 Heritage Part 1** | 8-62 | 55 pages | 28 reqs |
| **8.0 Heritage Part 2** | 1-58 | 58 pages | 20 reqs |
| **8.0 Heritage Part 3** | 1-60 | 60 pages | 18 reqs |
| **8.0 Heritage Part 4** | 8-58 | 51 pages | 17 reqs |

## Confirmed Offsets (User Reported)

Based on actual DCP page numbers viewed:

| File Page | Actual DCP Page | Offset | PDF Document |
|-----------|----------------|--------|--------------|
| 17 | 13 | -4 | Part 2.1 Urban Design |
| 20 | 6 | -14 | Unknown (need to verify) |
| 32 | 18 | -14 | Unknown (need to verify) |
| 53 | 39 | -14 | Unknown (need to verify) |
| 54 | 40 | -14 | Unknown (need to verify) |
| 56 | 104 | +48 | Unknown (different doc?) |
| 57 | 105 | +48 | Unknown (different doc?) |

## Solutions

### Option A: Quick Fix - Remove Page Numbers from UI
```typescript
// Change button text from "View PDF Page 17" to "View Source PDF"
<Button>View Source PDF</Button>
```

**Pros:** Fast, no data changes
**Cons:** Loses useful page reference information

### Option B: Add Offset Mapping Table
Create a lookup table with offsets for each PDF source:

```sql
CREATE TABLE marrickville_pdf_offsets (
    pdf_source_pattern VARCHAR(255) PRIMARY KEY,
    page_offset INTEGER NOT NULL,
    notes TEXT
);

-- Example data
INSERT INTO marrickville_pdf_offsets VALUES
('2_1_Urban_Design', -4, 'Cover + 3 TOC pages'),
('2_3_Site_Context', -4, 'Similar structure'),
('Heritage_Part1', -7, 'Cover + longer TOC');
```

Then update the API/UI to apply offset when displaying:
```typescript
const displayPage = dbPage + getOffset(pdfSource);
```

**Pros:** Preserves data, can fix per-document
**Cons:** Requires manual determination of each offset

### Option C: OCR Page Numbers from Images
Re-process all images with OCR to detect actual printed page numbers:

```python
# Pseudo-code
for image in pdf_images:
    actual_page = ocr_extract_page_number(image)
    update_database(image_id, actual_page)
```

**Pros:** Most accurate, automatic
**Cons:** Time-consuming, requires OCR setup

### Option D: Update Database with Correct Pages
Manually check each PDF and update database:

```sql
-- Example: Part 2.1 Urban Design has 4-page offset
UPDATE dcp_general_requirements
SET pdf_page = pdf_page - 4
WHERE pdf_page_image_url LIKE '%2_1_Urban_Design%';
```

**Pros:** Permanent fix, accurate
**Cons:** Labor-intensive for 28 PDFs

## Recommendation

**Hybrid Approach:**
1. **Short-term:** Option A - Hide page numbers for now (quick fix)
2. **Medium-term:** Option D - Fix the most-used PDFs (Parts 2.x and 4.x)
3. **Long-term:** Option B - Create offset table for remaining PDFs

Priority PDFs to fix (highest requirement counts):
1. Part 4.2 Residential Flat Buildings (72 reqs)
2. Part 4.1 Multi Dwelling Housing (67 reqs)
3. Part 8.0 Heritage Part 1 (28 reqs)
4. Part 4.4 Secondary Dwellings (25 reqs)
5. Part 2.3 Site Context Analysis (23 reqs)

## Next Steps

1. ✅ Identified 28 separate PDF sources
2. ⬜ Determine offset for top 10 most-used PDFs
3. ⬜ Create SQL update script with offsets
4. ⬜ Verify updates by checking sample images
5. ⬜ Apply same analysis to Ashfield and Leichhardt
