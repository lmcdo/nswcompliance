# Key Sites Map PDF Image Verification

## Image Files Created

All 17 Key Sites Map clauses now have corresponding PDF page images:

### Part 4 - General Controls
| Clause | Page | Image File | Size |
|--------|------|------------|------|
| 4.3C | 39 | iwlep_clause_4_3C_page_39.png | 1191x1684 |
| 4.4 | 40 | iwlep_clause_4_4_page_40.png | 1191x1684 |

### Part 6 - Site-Specific Controls
| Clause | Page | Image File | Size | Notes |
|--------|------|------------|------|-------|
| 6.14 | 73 | iwlep_clause_6_14_page_73.png | 1191x1684 | 145-155 Parramatta Rd |
| 6.15 | 73 | iwlep_clause_6_15_page_73.png | 1191x1684 | **185 Parramatta Rd** (copy of 6.14) |
| 6.16 | 74 | iwlep_clause_6_16_page_74.png | 1191x1684 | |
| 6.17 | 75 | iwlep_clause_6_17_page_75.png | 1191x1684 | |
| 6.18 | 76 | iwlep_clause_6_18_page_76.png | 1191x1684 | |
| 6.19 | 76 | iwlep_clause_6_19_page_76.png | 1191x1684 | (copy of 6.18) |
| 6.21 | 78 | iwlep_clause_6_21_page_78.png | 1191x1684 | |
| 6.22 | 79 | iwlep_clause_6_22_page_79.png | 1191x1684 | |
| 6.23 | 79 | iwlep_clause_6_23_page_79.png | 1191x1684 | (copy of 6.22) |
| 6.24 | 80 | iwlep_clause_6_24_page_80.png | 1191x1684 | |
| 6.25 | 81 | iwlep_clause_6_25_page_81.png | 1191x1684 | |
| 6.27 | 83 | iwlep_clause_6_27_page_83.png | 1191x1684 | |
| 6.30 | 85 | iwlep_clause_6_30_page_85.png | 1191x1684 | |
| 6.31 | 86 | iwlep_clause_6_31_page_86.png | 1191x1684 | |
| 6.34 | 88 | iwlep_clause_6_34_page_88.png | 1191x1684 | |

## Verification Checklist

✅ All 17 clause numbers have corresponding images
✅ Images extracted at 2x resolution (1191x1684px) for display clarity
✅ Duplicate images created for clauses sharing same page (6.15, 6.19, 6.23)
✅ Image path format: `/pdf-pages/iwlep_clause_{CLAUSE}_page_{PAGE}.png`
✅ LocalProvisionsCard displays images for `mapType === 'KSM'` provisions
✅ ExternalLink icon present for "View LEP" button
✅ Error handling with fallback to legislation URL if image fails to load

## Code Flow

1. **Planning Portal Extraction** (`lib/nsw-planning-portal.ts` lines 614-627)
   - Parses Legislative Clause field from Planning Portal
   - Imports `getKeyS itesProvision` for page numbers
   - Sets `pageNumber` and `mapType: 'KSM'` on provisions

2. **Display Component** (`components/compliance/LocalProvisionsCard.tsx` lines 158-182)
   - Checks condition: `(mapType === 'KSM') && clauseNumber && pageNumber`
   - Generates image src: `/pdf-pages/iwlep_clause_${clauseNumber}_page_${pageNumber}.png`
   - Displays with error handling fallback

3. **External Link** (line 214)
   - Shows ExternalLink icon with "View LEP" text
   - Links to NSW legislation website

## Test Address

**185 Parramatta Road, Annandale NSW 2038**

Expected provisions displayed:
- Clause 4.3C (page 39) - Height of buildings on Key Sites
- Clause 4.4 (page 40) - Floor space ratio
- Clause 6.14 (page 73) - Development at 145-155 Parramatta Road
- Clause 6.15 (page 73) - Development at 168-172 and **185 Parramatta Road**

All should display PDF page images.
