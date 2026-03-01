# Ashfield DCP Chapter D - Boundary Map Images

## Answer to Your Questions

### 1. Why is Ashfield West (D3) missing?

**Root cause:** MinerU PDF extraction error - the "# Part 3" heading was not extracted into the markdown, even though the content is present.

- Table of Contents lists: "3 Ashfield West 57"
- Content exists starting at line 366 with "Ashfield West" text
- BUT: No "# Part 3" heading in markdown → script skipped it
- Markdown jumps: Part 2 → Part 4

**Status:** Content is recoverable - needs manual extraction or script enhancement

---

### 2. Which images correspond to the 8 precincts?

## Boundary Map Images (Parts 1-8)

| Precinct | Name | Image File | You Need to Georeference? |
|----------|------|------------|---------------------------|
| **D1 / Part 1** | Ashfield Town Centre | `58ceae16a2dcff72828f5765ee8eabaaba862a0d150c9384fc58d199620dbbe0.jpg` | **YES** |
| **D2 / Part 2** | Ashfield East (Haberfield res) | `f058dfebd8b0c5b14cf3296df72232589422d6f31a06500778c491122d9ff293.jpg` | **YES** |
| **D3 / Part 3** | Ashfield West | **NOT EXTRACTED** (heading missing) | UNKNOWN |
| **D4 / Part 4** | Croydon Urban Village | `453c6405047ed7a4771546a4a37ddf5fe112856bf7a372197ec85b81a671a06b.jpg` | **YES** |
| **D5 / Part 5** | Neighbourhood Centre (B1) | `ead73837ba6a4c79c27cdabe16d071dd49016e9cde541dc1e506f36bd30c6d7f.jpg` | Maybe (generic zones) |
| **D6 / Part 6** | Enterprise - Parramatta Rd | `b115ca45a36c078f1d4b12927e741bb0c33a0dfd35769a8122e3ce2720691ca9.jpg` | **YES** |
| **D7 / Part 7** | Enterprise - Hurlstone Park | `0c15b7a16cddde42938309409e42963585391f3cb13ed93896a5d4800efff795.jpg` | **YES** |
| **D8 / Part 8** | Summer Hill Urban Village | `40d1688db4db54f4a090125ae1a677618445182d63420cd7e8168cee613eb9d7.jpg` | **YES** |

## Full Image Paths

All images located in:
```
./output/Inner West Ashfield DCP 2016 - Chapter D - Precinct Guidelines with IWLEP 2022 amendments Nov 22/auto/images/
```

### Priority 1: Definitely Georeference These (6 precincts)

1. **D1 - Ashfield Town Centre**
   - `images/58ceae16a2dcff72828f5765ee8eabaaba862a0d150c9384fc58d199620dbbe0.jpg`

2. **D2 - Ashfield East (Haberfield residential)**
   - `images/f058dfebd8b0c5b14cf3296df72232589422d6f31a06500778c491122d9ff293.jpg`

3. **D4 - Croydon Urban Village**
   - `images/453c6405047ed7a4771546a4a37ddf5fe112856bf7a372197ec85b81a671a06b.jpg`

4. **D6 - Enterprise Zone Parramatta Road (Haberfield commercial)**
   - `images/b115ca45a36c078f1d4b12927e741bb0c33a0dfd35769a8122e3ce2720691ca9.jpg`

5. **D7 - Enterprise Zone Hurlstone Park**
   - `images/0c15b7a16cddde42938309409e42963585391f3cb13ed93896a5d4800efff795.jpg`

6. **D8 - Summer Hill Urban Village**
   - `images/40d1688db4db54f4a090125ae1a677618445182d63420cd7e8168cee613eb9d7.jpg`

### Priority 2: Check if These Are Boundary Maps

7. **D5 - Neighbourhood Centre (B1) Zone**
   - `images/ead73837ba6a4c79c27cdabe16d071dd49016e9cde541dc1e506f36bd30c6d7f.jpg`
   - NOTE: This applies to ALL B1 zones, not a specific precinct - may not need georeferencing

### Unknown: Needs Manual Extraction

8. **D3 - Ashfield West**
   - Content exists in markdown but heading was not extracted
   - Image likely exists around line 366-395 in markdown
   - Recommend: Check original PDF page 57 for boundary map

## Single-Site Developments (Skip These)

These are included in extraction but you should NOT georeference (too specific):

- Part 9: Summer Hill Flour Mill Site
- Part 10: Edwards Street - B4 Zone
- Part 11: Industrial Zones
- Part 12: 55-63 Smith Street Summer Hill
- Part 13: 120C Old Canterbury Road

## Action Plan

### For You (Georeferencing):

1. Copy these 6 images to your QGIS working folder
2. Open each in QGIS
3. Georeference using NSW Planning Portal or Google Maps as base layer
4. Export as polygons with precinct_id matching D1, D2, D4, D6, D7, D8
5. Import into `dcp_precinct_boundaries` table

### For Claude (Next Steps):

1. ✓ Provisions extracted (68 from 7 precincts)
2. ✓ Images identified
3. ⏳ Manual fix: Extract Part 3 (Ashfield West) from markdown
4. ⏳ Import provisions to database
5. ⏳ LLM categorization
6. ⏳ Wait for your georeferencing
7. ⏳ Test with Ashfield addresses

## Bottom Line

**You have 6 clear boundary maps to georeference** for the main suburban precincts. Part 3 (Ashfield West) needs investigation - check the original PDF page 57.
