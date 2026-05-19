# Verify — Data Integrity & Compliance Position

**Document Owner:** Solvyra Pty Ltd
**Product:** Verify (verify.plotdetect.com.au)
**Last Updated:** 2026-05-20
**Classification:** Internal — Auditor Reference

---

## 1. Product Description

Verify is a property compliance research tool for NSW (New South Wales, Australia). It surfaces planning controls — Development Control Plans (DCPs), Local Environmental Plans (LEPs), and State Environmental Planning Policies (SEPPs) — for a given property address. Users include town planners, architects, buyers agents, and property developers.

Verify **does not** issue compliance certificates, make formal compliance declarations, or submit information to planning authorities. It provides indicative planning information with source references to assist professional users in their own compliance assessments.

---

## 2. Legal and Regulatory Position

### 2.1 No Certification Requirement

There is no NSW regulatory standard requiring certified data integrity for third-party planning information tools. The relevant legislation:

- **Environmental Planning & Assessment Act 1979 (NSW)** — Section 4.16 criminalises false or misleading information in connection with a planning matter. This applies to formal submissions to consent authorities, not to third-party information products.
- **Compliance declarations** (required from 1 July 2021) must be provided by **registered practitioners** via the NSW Planning Portal. The tool providing information is not the entity making the declaration.
- The **NSW Planning Portal** itself carries disclaimers on its data.

### 2.2 Industry Standard

Comparable Australian planning technology products operate under the same disclaimer model:

| Product | Approach |
|---------|----------|
| **Archistar** (government-partnered, eComply) | "Indicative information only." Applicants responsible for verifying all applicable planning controls. No public claims about audit trails or data certification. |
| **Landchecker** | Data "thoroughly collected, analysed, curated and enriched." No public audit trail methodology. |
| **CoreLogic** | Data quality as brand promise. Standard disclaimers on accuracy. |
| **NSW Planning Portal** | Government-operated. Carries its own disclaimers. |

No Australian PropTech or planning compliance company publicly claims ALCOA+ compliance, immutable audit trails, or certified data integrity for extracted regulatory data.

### 2.3 Verify's Disclaimer Model

All Verify outputs carry disclaimers consistent with industry practice:

- Planning information is indicative and sourced from publicly available government instruments
- Users must verify all information against current versions of the relevant planning instruments
- Verify does not provide legal or planning advice
- Source references (DCP section, clause number) are provided for every control to enable independent verification

### 2.4 Professional User Context

The intended users of Verify are planning professionals (town planners, architects, certifiers) who:

- Are professionally trained to interpret planning controls
- Have independent obligations to verify information before relying on it
- Make their own compliance assessments — Verify accelerates their research but does not replace their professional judgment
- Sign compliance declarations in their own capacity, not on behalf of Verify

---

## 3. Data Sources and Provenance

### 3.1 Source Instruments

All planning control data originates from publicly available NSW government instruments:

| Data Type | Source | Authority |
|-----------|--------|-----------|
| **DCP provisions** | Council DCP PDF documents published on council websites | Local councils |
| **DCP numeric controls** (setbacks, parking, height) | Extracted from DCP PDFs, stored in `dcp_setback_controls` | Local councils |
| **LEP controls** (zoning, height limits, FSR, heritage) | NSW Planning Portal API (`layerintersect`, `zone_full`) | NSW Department of Planning |
| **SEPP standards** (Housing SEPP, Codes SEPP) | NSW Legislation website (legislation.nsw.gov.au) | NSW Parliamentary Counsel's Office |
| **Spatial overlays** (flood, bushfire, acid sulfate) | NSW Planning Portal API, PostGIS spatial queries | NSW DPE, local councils |

### 3.2 DCP Source Document Chain

For DCP numeric controls (the primary scope of this document), each data point traces through:

```
Control value (e.g., "rear setback 6m")
  → dcp_setback_controls row (section_ref, source_text, source_chapter_key)
    → dcp_chapter_registry row (chapter_key, content_hash, r2_current_path)
      → R2 object storage (PDF file with SHA-256 content hash)
        → Council website (original source URL)
```

**Source PDFs** are stored in Cloudflare R2 object storage with:
- SHA-256 content hashes for integrity verification
- Version-labelled storage paths (e.g., `source-pdfs/dcps/marrickville/v1.1-2026-05-18/part2-s10-parking.pdf`)
- Download timestamps and source URLs recorded in `dcp_chapter_registry`

### 3.3 Extraction Methods

DCP numeric controls are extracted via three methods, recorded in the `extraction_method` column:

| Method | Description | Usage |
|--------|-------------|-------|
| `text_extraction` | Programmatic text extraction from PDF with regex parsing | Primary automated method |
| `mistral_ocr` | AI-assisted OCR for scanned/image-based PDFs | PDFs without extractable text |
| `manual` | Human reading of source PDF, manual data entry | Complex tables, non-standard formats |
| `manual_insert` | Scripted insert from human-curated data | Batch council onboarding |
| `manual_curation` | Human-reviewed and corrected extraction output | Quality assurance pass |
| `gpt4_extraction` | LLM-assisted extraction with human review | Complex provision interpretation |
| `automatic_extraction` | Fully automated pipeline extraction | Secondary dwelling controls |

Every control row records which method was used. This field is enforced as NOT NULL at the database level.

---

## 4. Data Integrity Controls

### 4.1 Database-Level Enforcement (Implemented)

The following constraints are enforced at the PostgreSQL database level and cannot be bypassed by application code, scripts, or manual dashboard operations:

| Constraint | Type | Purpose |
|-----------|------|---------|
| `fk_dcp_setback_lga` | Foreign Key | `dcp_setback_controls.lga` must reference a valid slug in `lga_registry`. Prevents invalid council identifiers. |
| `dcp_setback_controls_extraction_method_check` | CHECK | `extraction_method` must be one of 7 defined values. Prevents unknown provenance. |
| `extraction_method NOT NULL` | NOT NULL | Every control row must record how it was extracted. No unknown-origin data. |
| `applicability CHECK` | CHECK | `applicability` must be one of 7 defined values (e.g., `universal_residential`, `secondary_dwelling_specific`). |
| `provision_id FK` | Foreign Key | Links to `regulatory_provisions` source record where applicable. |

**`lga_registry` table** — canonical registry of all valid LGA (Local Government Area) slugs with display names. Adding a new council to the system requires registering it here first. This prevents data entry with misspelled or non-existent council identifiers.

### 4.2 Source Document Monitoring

An automated monitoring pipeline tracks the currency of source documents:

| Component | Function | Frequency |
|-----------|----------|-----------|
| `r2_monitor.py` | Detects PDF changes on council websites by comparing content hashes | Scheduled (GitHub Actions) |
| `dcp_watchdog.py` | Alerts on stale data, stuck extractions, and controls flagged for review | Scheduled |
| `legislation_monitor.py` | Detects SEPP/LEP amendments via NSW Parliamentary Counsel's Office XML export | Scheduled |

When a source PDF changes:
1. New PDF version uploaded to R2 with new version label
2. `dcp_chapter_registry.needs_extraction` flagged
3. Provisions re-extracted from updated PDF
4. Affected `dcp_setback_controls` rows flagged with `needs_review = TRUE`
5. Operator alerted via Telegram to verify updated controls

### 4.3 Version Tracking

Each control row records:

| Column | Purpose |
|--------|---------|
| `dcp_version` | Which version of the DCP this control was extracted from |
| `is_current` | Whether this is the currently effective control (FALSE for superseded) |
| `source_chapter_key` | Links to the specific chapter in `dcp_chapter_registry` for traceability |
| `created_at` | Timestamp of when the control was added to the database |
| `effective_date` | Date the source DCP version took legal effect (where known) |
| `last_verified_at` | Last time the source chapter was confirmed unchanged by monitoring |
| `needs_review` | Flag set when source document changes, cleared after human verification |
| `review_reason` | Why the row was flagged (e.g., `chapter_pdf_changed`) |
| `reviewed_at` | Timestamp of last human verification |

### 4.4 Change Detection and Review

The `dcp_chapter_registry` table maintains a complete record for each DCP chapter:

- `content_hash` — SHA-256 hash of the PDF, the primary change detector
- `url_last_checked` — when the monitor last polled the source URL
- `url_last_changed` — when a content change was last detected
- `check_failures` — consecutive download failures (alerts at 3+)
- `r2_version_label` — version of the PDF currently stored (e.g., `v1.1-2026-05-18`)

---

## 5. Data Quality Assessment

### 5.1 Current State (as of 2026-05-20)

| Metric | Value | Status |
|--------|-------|--------|
| Total control rows | 895 | |
| Rows with `is_current = TRUE` | 893 | 2 superseded (known duplicates, corrected) |
| Rows with `extraction_method` set | 895 / 895 | 100% — enforced NOT NULL |
| Rows with `dcp_version` set | 895 / 895 | 100% |
| Rows with `source_chapter_key` set | 895 / 895 | 100% |
| Distinct LGAs covered | 29 | All validated via FK to `lga_registry` |
| Orphaned LGA slugs | 0 | FK prevents insertion of invalid slugs |

### 5.2 Coverage

DCP numeric controls (setbacks, parking, landscaping, height, site coverage) are available for 29 LGAs across Greater Sydney and surrounds. Coverage is expanding council by council.

Full structured DCP provisions (complete provision text with TOC navigation, PDF page images, topic filters, and precinct-specific controls) are available for Inner West Council (Ashfield, Marrickville, Leichhardt DCPs).

SEPP and LEP controls are available for every NSW address via the NSW Planning Portal API.

### 5.3 Known Limitations

| Limitation | Mitigation |
|-----------|------------|
| DCP numeric controls are extracted values, not the authoritative regulation text | Source text snippets and section references provided for every control. Users directed to source PDF for authoritative text. |
| Extraction from complex PDF tables may miss edge cases | Extraction method recorded. Controls flagged for review when source changes. |
| Not all DCP provisions are structured as numeric controls | Full provision text available for Inner West. Other councils show available numeric controls with section references. |
| DCP amendments between monitoring cycles may not be immediately reflected | Monitoring pipeline polls source URLs on schedule. `last_verified_at` indicates data currency. |

---

## 6. Infrastructure and Access Control

### 6.1 Database

- **Platform:** Supabase (managed PostgreSQL)
- **Region:** ap-southeast-2 (Sydney, Australia)
- **Access:** Role-based via Supabase authentication. No public database access.
- **Backups:** Automated daily backups (Supabase managed)

### 6.2 Source Document Storage

- **Platform:** Cloudflare R2 (S3-compatible object storage)
- **Content:** DCP PDF source documents, versioned by extraction date
- **Integrity:** SHA-256 content hashes stored in `dcp_chapter_registry.content_hash`

### 6.3 Application

- **Platform:** Vercel (Next.js)
- **Domain:** verify.plotdetect.com.au
- **Source control:** GitHub (private repository), all changes via pull request with code review

---

## 7. Roadmap: Planned Integrity Enhancements

The following capabilities are planned and will be implemented based on business needs (enterprise customer requirements, investor due diligence, or incident response):

### Tier 2: Operational Traceability (planned)

| Capability | Description | Trigger |
|-----------|-------------|---------|
| **Audit trigger** | Append-only log of all INSERT/UPDATE/DELETE on `dcp_setback_controls` with old/new values, timestamp, and actor | Enterprise customer requirement or SOC 2 |
| **Assessment snapshot** | JSONB capture of exact control values used in each assessment at generation time | Legal challenge requiring "what did user X see on date Y" |
| **Single write path** | All writes to `dcp_setback_controls` through validated module enforcing required fields, dedup, and transactional supersession | Pipeline scaling beyond current team |
| **Enhanced watchdog** | Automated detection of orphaned references, NULL versions, duplicate controls, and stale unverified data | Operational maturity |

### Tier 3: Full Audit Standard (deferred)

| Capability | Description | Trigger |
|-----------|-------------|---------|
| Bitemporal modeling | `valid_from`/`valid_to` on every control for point-in-time regulatory queries | Legal proceeding requiring historical reconstruction |
| Verification workflow | Four-eyes principle with `verified_by` attribution | Professional indemnity insurer requirement |
| Extraction run tracking | Git SHA + config version recorded per extraction for reproducibility | Reproducibility challenge |
| ALCOA+ full compliance | Complete Attributable, Legible, Contemporaneous, Original, Accurate framework | Pharma/government client with GxP requirements |

---

## 8. Quality Assurance Process

### 8.1 Code Quality

- All code changes via pull request with automated checks:
  - TypeScript type checking (0 errors gate)
  - Python test suite (pytest, pre-push hook)
  - Post-edit quality hooks blocking known anti-patterns (connection leaks, unsanitized HTML, direct pool instantiation)
- Pre-PR review checklist covering: DB query filters, null safety, type boundary assumptions, silent failure modes, liability language audit

### 8.2 Adversarial Testing Methodology

Applied to all data pipeline components (established via satellite products QA):

- Grep every `.get(key, default)` for null-value traps
- Grep every `float()`/`int()` for unguarded type coercion
- Check every database connection for proper cleanup (`try/finally`)
- Test boundary values (zero-is-valid, empty strings, unknown classifications)
- Verify error paths fail visibly (exceptions, alerts) not silently (wrong data served)

### 8.3 Pipeline Monitoring

| Monitor | What It Checks | Alert Channel |
|---------|---------------|---------------|
| `dcp_watchdog.py` | Stale chapters, failing downloads, controls needing review, unlinked controls, ePlanning layer health | Telegram |
| `r2_monitor.py` | PDF changes, URL migrations, new/removed chapters, WAF blocks | Telegram |
| `legislation_monitor.py` | SEPP/LEP version changes via PCO XML export | Telegram |
| Vercel deployment | Build success, preview URL generation | GitHub |
| Pre-push hooks | Test suite pass, TypeScript error count | Local terminal |

---

## 9. Incident Response

If a data accuracy issue is reported:

1. **Identify** the affected control row(s) and source chapter
2. **Verify** the current value against the source PDF (via `source_chapter_key` → `dcp_chapter_registry` → R2 PDF)
3. **Correct** the control value via the standard extraction/insert pipeline
4. **Supersede** the incorrect row (`is_current = FALSE`) and insert corrected row
5. **Assess impact** — identify any assessments that may have used the incorrect value (via `created_at` timestamps)
6. **Notify** affected users if the error was material to their assessment

---

## 10. Contact

**Data integrity questions:** Solvyra Pty Ltd
**Product:** verify.plotdetect.com.au
**Source instruments:** Published DCP, LEP, and SEPP documents from NSW councils and the NSW Department of Planning, Housing and Infrastructure
