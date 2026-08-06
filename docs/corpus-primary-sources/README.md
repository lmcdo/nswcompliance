# NDIS Corpus — Primary-Source Drop Folder

## Purpose

Extracted text of Australian Federal Register and NDIA / NDIS Commission primary-source documents used by the NDIS scoping and (later) the Rules Engine corpus. This is where the founder drops verbatim source material after fetching it from an AU network, so the rest of the repo can cite it without needing to re-fetch from a sandboxed environment.

Every document here is the **input** to the C1, C2, C3, and Z3 verification steps in `docs/ndis-technical-and-compliance-scope.md`.

## How to add a document

1. Fetch the PDF from an AU home network (or directly from the primary source in a browser).
2. Extract text locally with layout preserved:
   ```
   pdftotext -layout source.pdf source.txt
   ```
3. Drop the `.txt` file into this folder.
4. `git add` and commit the `.txt`.

The PDF itself is `.gitignore`d — do NOT commit PDFs. They are large binaries; the extracted `.txt` is what the repo needs.

Markdown notes (`.md`) alongside the text are fine and welcome — e.g. a per-document `NOTES.md` capturing the copyright notice verbatim, the fetch date, and the fetch URL.

## Naming convention

Match the source identifier so downstream tooling can dispatch on the filename:

- Federal Register instruments — the F- or C-number:
  - `F2018L00629.txt` (Code of Conduct Rules)
  - `F2018L00631.txt` (Provider Registration & Practice Standards Rules)
  - `F2018L00632.txt` (Restrictive Practices & Behaviour Support Rules)
  - `F2018L00633.txt` (Incident Management & Reportable Incidents Rules)
  - `F2018L00634.txt` (Complaints Management & Resolution Rules)
  - `F2018N00041.txt` (Quality Indicators Guidelines)
  - `F2024L01257.txt` (NDIS Supports Transitional Rules 2024 — SUNSET-PENDING)
  - `F2025L01383.txt` (Approved Quality Auditors Rules 2025)
  - `C2013A00020.txt` (NDIS Act 2013)
- NDIA-published operational documents — a descriptive slug:
  - `pricing-arrangements-2026-27.txt`
  - `ndis-support-catalogue-2026-27.txt`
- NDIS Commission guidance documents — a descriptive slug:
  - `practice-standards-booklet-v4.txt`
  - `code-of-conduct-guidance.txt`
  - `regulated-restrictive-practices-guide.txt`
  - `detailed-guidance-incident-management-2024-09.txt`
  - `detailed-guidance-complaints-2024-09.txt`
  - `worker-screening-qa.txt`
  - `provider-toolkit.txt`

## Copyright notice capture (required for C1, C2, C3, Z3)

Alongside each `.txt`, add a `<name>-NOTICE.md` file with the verbatim copyright notice from the document's front matter or footer. Example:

```
# F2018L00631 — Copyright Notice (as captured)

Fetched from: https://www.legislation.gov.au/F2018L00631/latest/text
Fetched on:   2026-08-06
Fetched by:   <founder initials>

Notice verbatim:
> [paste the copyright notice text exactly as it appears in the PDF]
```

Any per-document override of the site-wide licence baseline (CC BY-NC 3.0 AU for NDIA / Commission content; CC BY 4.0 for Federal Register content) is what these NOTICE files are for. If a document declares something different, escalate to Z3 in the scoping doc.

## What NOT to put here

- PDFs (gitignored).
- Text extractions that contain participant PII, personal case details, or any material that is not the published primary source.
- Third-party commentary or blog posts — this folder is for primary sources only.

## See also

- `docs/ndis-technical-and-compliance-scope.md` §C1, §C2, §C3, §C11, §Z3 — the scoping decisions that consume this folder.
