# LGA Implementation Checklist

Quick-reference checklist for adding a new LGA. See `LGA_AUTOMATION_GUIDE.md` for detailed instructions.

## Pre-Implementation

- [ ] Obtain DCP PDF document
- [ ] Store in `data/pdfs/{council}/`
- [ ] Note DCP name and year: `_________________ DCP ____`

## Phase 1: Document Analysis

| Part | Content | Layer | Topics |
|------|---------|-------|--------|
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |

**Topic Markers Identified:**
- [ ] Section numbers (e.g., 2.6 → privacy)
- [ ] Control codes (e.g., C3 → parking)
- [ ] Chapter headers
- [ ] None found (will use keyword matching)

**Precinct Parts:** ____________________

---

## Phase 2: Configuration

- [ ] Create `enrichment/config/{council}_config.py`
- [ ] Define parts with layer assignments
- [ ] Define topic marker mappings (if applicable)
- [ ] Define precinct list
- [ ] Update `enrichment/extractors/layer_topic_tagger.py`
  - [ ] Add `_tag_{council}()` method
  - [ ] Add council detection in main `tag()` method

---

## Phase 3: Extraction

- [ ] Create `scripts/extract_{council}_dcp.py`
- [ ] Test on first 10 pages (`--dry-run`)
- [ ] Run full extraction
- [ ] Verify provision count: ______ provisions
- [ ] Check page distribution
- [ ] Check for empty provisions

**Extraction Stats:**
```
Total provisions: ______
Pages covered: ______ to ______
Parts extracted: ______________________
```

---

## Phase 4: Enrichment

- [ ] Run layer tagging: `python enrichment/pipeline.py --phase layer`
- [ ] Run site condition tagging: `python enrichment/pipeline.py --phase site_condition`
- [ ] Run type classification: `python enrichment/pipeline.py --phase type`
- [ ] Run numeric extraction: `python enrichment/pipeline.py --phase numeric`
- [ ] Validate enrichment quality

**Enrichment Stats:**
```
Layer distribution:
  generic: ______
  use_specific: ______
  condition: ______
  precinct: ______

Topic coverage: ______%
Estimated accuracy: ______%
```

---

## Phase 5: Precinct Setup

- [ ] Source precinct boundary data
  - [ ] NSW Planning Portal API
  - [ ] Manual GeoJSON creation
- [ ] Insert precincts into database
- [ ] Link provisions to precinct IDs
- [ ] Verify precinct filtering

**Precincts:**
| # | Name | Provisions |
|---|------|------------|
| | | |
| | | |
| | | |

---

## Phase 6: API Configuration

- [ ] Update Inner West mapping (if applicable)
- [ ] Test provision API queries
- [ ] Verify layer filtering
- [ ] Verify topic filtering

---

## Phase 7: Frontend Verification

Test Address: ________________________________

- [ ] Address lookup works
- [ ] Zone detected correctly: ______
- [ ] DCP provisions load
- [ ] TOC structure displays
- [ ] Generic layer shows
- [ ] Use-specific layer filters correctly
- [ ] Condition layer filters correctly (if heritage site)
- [ ] Precinct layer filters correctly
- [ ] Topic pills work
- [ ] PDF page links work

---

## Phase 8: Final QA

### Extraction
- [ ] All DCP parts extracted
- [ ] No duplicate provisions
- [ ] PDF page numbers correct
- [ ] Section headers captured

### Enrichment
- [ ] All provisions have v2_dcp_layer
- [ ] All provisions have v2_dcp_part
- [ ] >90% provisions have v2_topic
- [ ] Topic accuracy >95%

### Precincts
- [ ] All precinct boundaries imported
- [ ] Precinct provisions linked
- [ ] Location filtering works

### Frontend
- [ ] TOC structure correct
- [ ] All filters work
- [ ] Search works
- [ ] PDF links work

---

## Sign-Off

| Phase | Date | Verified By |
|-------|------|-------------|
| Extraction | | |
| Enrichment | | |
| Precincts | | |
| Frontend | | |
| **Final QA** | | |

---

## Notes

```




```

---

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| | |
| | |
| | |
