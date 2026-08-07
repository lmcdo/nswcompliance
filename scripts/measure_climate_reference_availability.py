"""Can the pre-committed climate validation actually be run? Measure, don't assume.

prior-art-checked: reuse not viable because nothing in the repo reads the
reference PDF corpus at all. Four-sweep run 2026-08-07: (1) DB — no table holds
APRA/SA3 reference values; `property_reports` carries no climate product.
(2) Frontend — the climate surfaces (`app/climate-risk/`, `ClimateRiskTool.tsx`,
`ClimateRiskResultCard.tsx`, `api/satellite/climate-risk/route.ts`) render score
inputs, none read `climate_risk_intel/`. (3) Python — `climate_risk_score.py`,
`climate_risk_raster.py` and `climate_risk_pipeline.py` read PostGIS and NARCliM
NetCDF only; `git grep -il climate_risk_intel -- '*.py'` returns nothing.
(4) Plans/memory — no prior corpus-scanning tool. The nearest existing artefact,
`data/climate_risk_reference.json`, is the *output* of a manual read of these
PDFs ("extraction_method: Manual extraction from source PDFs") with no script
behind it — that unverifiable manual step is precisely what this replaces.

`docs/CLIMATE_RISK_METHODOLOGY.md` pre-commits one validation for the composite
Climate Risk Awareness Score:

    Spearman rank correlation against APRA SA3 rankings (target rho > 0.7)

That check needs a reference vector: a list of SA3 (or SA4) regions each carrying
a value that can be ranked. This script measures whether such a vector exists in
extractable form in the reference corpus on disk, and prints the verdict.

Why a script and not a prose claim: "no SA3 ranking table exists in the source
PDFs" is a negative claim about a 22-document, ~1,200-page corpus. A negative
claim without a re-runnable command behind it is unsupported, and it silently
rots the day someone drops an APRA data annex into the folder. Running this is
the check. (The count matters: an earlier top-level-only glob missed the five
PDFs in council_strategies/ and still printed a confident verdict over 17.)

THIS SCRIPT IS DELIBERATELY FALSIFIABLE. It exits non-zero when the recorded
verdict (REFERENCE ABSENT) stops being true — i.e. when a usable reference
appears and the correlation becomes runnable. That is the outcome that should
reopen the lane, so it is the outcome that fails the check.

It is NOT wired into CI and gates nothing. Run it on demand:

    python scripts/measure_climate_reference_availability.py
    python scripts/measure_climate_reference_availability.py <corpus-dir>

`climate_risk_intel/` is gitignored, so a git worktree will not contain it. Pass
the corpus directory explicitly to measure it from a worktree checkout.

Absent corpus or absent library is a RED (non-zero exit with a stated reason),
never a green skip: a check that cannot run must not report success. Both PDF
libraries are imported at module scope with no importorskip guard, so a missing
dependency raises ImportError rather than quietly degrading the sweep.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Module-scope imports, deliberately unguarded (calibration campaign discipline,
# PRs #880/#883): an absent library must break the run loudly, not skip it.
import fitz  # PyMuPDF
import pdfplumber

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "climate_risk_intel"

# The reference must be keyed to a rankable geography. These are the ASGS units
# APRA's Insurance CVA reports against (see APRA Mind the Gap 2026, p.15 fn.28).
GEOGRAPHY_TOKENS = ("SA3", "SA4")

# Counted case-insensitively, matching GEOGRAPHY_CONTEXT below. A case-sensitive
# str.count would miss a document writing "sa3" in lowercase and then quietly
# exempt it from the unread-raster guard.
GEOGRAPHY_TOKEN_RES = {
    tok: re.compile(rf"\b{tok}\b", re.I) for tok in GEOGRAPHY_TOKENS
}

# An image covering at least this share of a page is content — a figure, a map,
# a table rendered as a picture — not a logo or a rule. Nothing in this script
# can read inside a raster, so a content image is unread material regardless of
# how much prose sits beside it. Measured: APRA Mind the Gap 2026 pages 16-17,
# which carry the SA3 protection-gap results as Figures 9 and 10, are 20.7% and
# 38.4% image while still holding 2,089 and 796 characters of text.
SUBSTANTIAL_IMAGE_COVERAGE = 0.15

# Detection is deliberately NAME-AGNOSTIC. An earlier draft gated on a
# hand-written list of ~27 NSW place names; NSW has ~130 SA3s, so a genuine
# ranking table using Bathurst, Orange, Goulburn-Mulwaree or Snowy Mountains
# would have scored zero and been reported as "no reference" — a false negative
# in the exact direction that would make the recorded verdict wrong. A geography
# shortlist is also a hardcoded lookup of the kind this repo bans elsewhere.
# What a reference actually looks like, structurally: many rows, each pairing a
# text label with a number, on a page that names an ASGS geography.
# Deliberately does NOT accept the bare word "region": with re.I that matches a
# page headed "Regional insurer results", so a ten-row insurer/revenue table
# would be reported as an SA3 reference. What is being looked for is an ASGS
# unit specifically, which is what the pre-committed validation names.
# SA3/SA4 only — NOT SA2. The pre-committed comparison names SA3, and an SA2
# series cannot be correlated against it without a concordance we do not hold.
GEOGRAPHY_CONTEXT = re.compile(
    r"\bSA[34]\b|\bStatistical Area(?: Level)? [34]\b", re.I
)

# A value cell must parse as a number (percentages, currency and thousands
# separators stripped), not merely contain a digit — a footnote marker or a
# year in a prose cell is not a value.
VALUE_CELL = re.compile(r"^[\s$]*-?\d[\d,]*(?:\.\d+)?\s*%?\s*$")

# A bare 4-digit year is a date, not a measurement. "Bathurst | 2024" is a
# case-study row, not a rankable value, and a column of them would otherwise
# clear the pair bar and fake a reference.
YEAR_LIKE = re.compile(r"^\s*(?:19|20|21)\d{2}\s*$")

# A label cell must carry letters and must not itself be a number.
LABEL_CELL = re.compile(r"[A-Za-z]{3,}")

# Minimum label->value pairs WITHIN ONE TABLE before it could support a rank
# correlation at all. Below this, a Spearman rho is not interpretable. Counting
# document-wide instead of per-table would let ten place names in prose combine
# with an unrelated two-row table to fake a reference.
MIN_REGIONS_FOR_RANKING = 10

# A document whose extracted text is this thin per page has no usable text
# layer (a scan). It cannot be scored as "contains no reference" — nothing was
# read. It makes the whole answer UNKNOWABLE.
MIN_CHARS_PER_PAGE = 50

# A single page below this, carrying a raster image, was effectively not read:
# it could be a scanned table. Counted and reported as a stated ceiling on the
# ABSENT verdict rather than turned into a document-wide RED — measured over
# this corpus, 19 of 1,060 such pages are covers, dividers and full-page
# infographics, and a check that goes red on a cover page is one people learn
# to ignore. The load-bearing document (APRA Mind the Gap 2026) has none.
MIN_CHARS_PER_READ_PAGE = 200


@dataclass
class DocumentScan:
    """Per-document measurement of reference-data availability."""

    path: Path
    pages: int = 0
    text_chars: int = 0
    geography_hits: dict[str, int] = field(default_factory=dict)
    candidate_tables: int = 0
    largest_table_pairs: int = 0
    geography_page_pairs: int = 0
    unread_image_pages: int = 0
    unread_content_pages: int = 0

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def has_text_layer(self) -> bool:
        """False for a scanned document nothing could be read from.

        Distinguished from "read it, found no reference" because the two must
        not share an outcome: an unread document makes the answer UNKNOWABLE.
        """
        return self.pages > 0 and self.text_chars >= self.pages * MIN_CHARS_PER_PAGE

    @property
    def names_a_geography(self) -> bool:
        """True when the document mentions an ASGS unit anywhere."""
        return any(self.geography_hits.get(tok) for tok in GEOGRAPHY_TOKENS)

    @property
    def has_unread_geography_pages(self) -> bool:
        """True when unread raster content sits in a document that talks SA3/SA4.

        This is the combination that makes absence unprovable: the numbers may
        be present as a picture. It is the actual state of APRA Mind the Gap
        2026, whose Figures 9 and 10 ARE the SA3 results and are images.

        Counts content-sized images even on pages carrying plenty of text — a
        figure sits beside prose, and prose next to a map does not mean the map
        was read. A raster in a document that never mentions an ASGS unit is a
        different thing and is reported as a ceiling, not escalated.
        """
        return self.unread_content_pages > 0 and self.names_a_geography

    @property
    def is_candidate_reference(self) -> bool:
        """True when one table in this document pairs enough labels with values.

        Measured per table, never by combining a document-wide name count with
        a separate table count — those can both be satisfied by a document that
        holds no reference at all.
        """
        return self.candidate_tables > 0


def count_label_value_pairs(table: list[list]) -> int:
    """Count rows pairing a distinct text label with a parseable number.

    Args:
        table: One extracted table as a list of rows of cells.

    Returns:
        The number of DISTINCT labels that carry at least one numeric value in
        the same row. Distinct, because a repeated label is one region reported
        twice, not two regions.
    """
    labelled: dict[str, list[float]] = {}
    for row in table:
        cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
        if len(cells) < 2:
            continue
        label = next(
            (c for c in cells if LABEL_CELL.search(c) and not VALUE_CELL.match(c)),
            None,
        )
        if not label:
            continue
        values = [
            _as_number(c)
            for c in cells
            if VALUE_CELL.match(c) and not YEAR_LIKE.match(c)
        ]
        values = [v for v in values if v is not None]
        if values:
            labelled.setdefault(label.casefold(), []).extend(values)

    if not labelled:
        return 0

    # A numbered list is not a measurement. "1 Bathurst / 2 Orange / ..." pairs
    # a label with a number on every row and would otherwise clear the bar with
    # no data in it at all. If every row's only value is its own position, this
    # is an index column, not a series.
    if all(len(v) == 1 for v in labelled.values()):
        singles = sorted(v[0] for v in labelled.values())
        if singles == [float(i) for i in range(1, len(singles) + 1)]:
            return 0

    return len(labelled)


def _as_number(cell: str) -> float | None:
    """Parse a value cell to a float, or None when it will not parse."""
    try:
        return float(cell.strip().lstrip("$").rstrip("%").replace(",", ""))
    except ValueError:
        return None


def _image_coverage(page, images) -> float:
    """Share of the page area covered by raster images (may exceed 1.0)."""
    page_area = abs(page.rect.get_area())
    if not page_area:
        return 0.0
    covered = 0.0
    for img in images:
        for rect in page.get_image_rects(img[0]):
            covered += abs(rect.get_area())
    return covered / page_area


def scan_document(path: Path) -> DocumentScan:
    """Measure one PDF for a rankable label->value reference series.

    Args:
        path: Path to the PDF to scan.

    Returns:
        DocumentScan carrying page count, extracted text length, ASGS
        geography-token counts, and the number of extractable tables that pair
        at least MIN_REGIONS_FOR_RANKING distinct labels with numeric values on
        a page that names a geography.
    """
    scan = DocumentScan(path=path)

    with fitz.open(path) as doc:
        scan.pages = doc.page_count
        pages_text = []
        for page in doc:
            page_text = page.get_text()
            pages_text.append(page_text)
            # A near-empty page carrying a raster could be a scanned table.
            # Counted so the ABSENT verdict can state what it did not read.
            images = page.get_images(full=True)
            if len(page_text.strip()) < MIN_CHARS_PER_READ_PAGE and images:
                scan.unread_image_pages += 1
            # Independent of the text test: a content-sized raster is unread
            # material even on a page full of prose. Nothing here reads inside
            # an image, and a table rendered as a picture is exactly the case
            # that would make an "absent" verdict false.
            if images and _image_coverage(page, images) >= SUBSTANTIAL_IMAGE_COVERAGE:
                scan.unread_content_pages += 1
        text = "\n".join(pages_text)

    scan.text_chars = len(text.strip())
    scan.geography_hits = {
        tok: len(rx.findall(text)) for tok, rx in GEOGRAPHY_TOKEN_RES.items()
    }

    if not scan.has_text_layer:
        # Nothing was read. Do not go looking for tables and do not record a
        # zero — the caller turns this into UNKNOWABLE, not "no reference".
        return scan

    # A choropleth map is a raster: the numbers are not in the file. Only an
    # extractable table can supply a reference vector, so count those directly.
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            # The series must be keyed to a geography, not just be any numeric
            # table. Checked on the page, not by matching hardcoded place names.
            geo_context = bool(GEOGRAPHY_CONTEXT.search(page_text))
            for table in page.extract_tables():
                pairs = count_label_value_pairs(table)
                scan.largest_table_pairs = max(scan.largest_table_pairs, pairs)
                if geo_context:
                    # A ranking split across pages (repeated header, 6 rows each)
                    # clears no single-table bar. Accumulating the geography-page
                    # total surfaces that shape without stitching tables together,
                    # which would need continuation detection this cannot do
                    # reliably. Reported, never silently counted as a candidate.
                    scan.geography_page_pairs += pairs
                    if pairs >= MIN_REGIONS_FOR_RANKING:
                        scan.candidate_tables += 1

    return scan


def _print_ceiling(scans: list[DocumentScan], total_pages: int) -> None:
    """State what the sweep did NOT read, so no verdict overstates its reach.

    Nothing here reads inside a raster. Printing the count and naming every
    affected document keeps that limit visible instead of implicit.
    """
    unread = sum(s.unread_content_pages for s in scans)
    if not unread:
        return
    print(
        f"\n  CEILING: {unread} page(s) of {total_pages} carry a content-sized "
        "image that\n  nothing here can read. A table rendered as a picture on "
        "one of them would\n  not have been detected. Affected:"
    )
    for scan in (s for s in scans if s.unread_content_pages):
        geo = " (names an ASGS geography)" if scan.names_a_geography else ""
        print(f"    {scan.name}: {scan.unread_content_pages}{geo}")
    print(
        "  Documents NOT listed here were read in full."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the sweep and print the verdict.

    Args:
        argv: Optional CLI args. argv[0], when given, overrides the corpus
            directory — needed because `climate_risk_intel/` is gitignored and
            therefore absent from any worktree checkout.

    Returns:
        0 while the recorded verdict (REFERENCE ABSENT) still holds;
        1 when a usable reference has appeared, or when the corpus is missing
        and the question therefore cannot be answered. Both non-zero cases are
        reportable outcomes, not passes.
    """
    args = sys.argv[1:] if argv is None else argv
    corpus_dir = Path(args[0]).expanduser().resolve() if args else CORPUS_DIR

    if not corpus_dir.is_dir():
        print(f"RED: reference corpus not found at {corpus_dir}")
        print(
            "     climate_risk_intel/ is gitignored, so a fresh clone will not "
            "have it.\n"
            "     This is UNKNOWABLE, not a pass: the question was not answered."
        )
        return 1

    # rglob + case-folded suffix, NOT glob("*.pdf"): the corpus has a
    # council_strategies/ subdirectory, and a top-level-only, case-sensitive
    # sweep silently skipped 5 of its 22 documents while still printing a
    # confident verdict over the other 17.
    pdfs = sorted(
        p for p in corpus_dir.rglob("*")
        if p.is_file() and p.suffix.casefold() == ".pdf"
    )
    if not pdfs:
        print(f"RED: no PDFs under {corpus_dir} — nothing to measure.")
        return 1

    print(f"Reference corpus: {corpus_dir}")
    print(f"Documents: {len(pdfs)}\n")
    header = (
        f"{'document':<56}{'pages':>6}{'SA3':>5}{'SA4':>5}"
        f"{'max pairs':>11}{'tables':>8}"
    )
    print(header)
    print("-" * len(header))

    scans = [scan_document(p) for p in pdfs]
    total_pages = 0
    for scan in scans:
        total_pages += scan.pages
        # `or 0` not `.get(tok, 0)`: the default only fires on a MISSING key, so
        # a key present with a None value would print "None" in a count column.
        sa3 = scan.geography_hits.get("SA3") or 0
        sa4 = scan.geography_hits.get("SA4") or 0
        flag = "" if scan.has_text_layer else "   NO TEXT LAYER"
        print(
            f"{scan.name[:55]:<56}{scan.pages:>6}{sa3:>5}{sa4:>5}"
            f"{scan.largest_table_pairs:>11}{scan.candidate_tables:>8}{flag}"
        )

    unreadable = [s for s in scans if not s.has_text_layer]
    candidates = [s for s in scans if s.is_candidate_reference]

    print(f"\nScanned {len(scans)} documents, {total_pages} pages.")
    print(
        "A usable reference needs ONE extractable table pairing at least "
        f"{MIN_REGIONS_FOR_RANKING} distinct\nlabels with numeric values, on a "
        f"page naming an ASGS geography. Documents\nmeeting that bar: "
        f"{len(candidates)}"
    )

    # A positively identified reference answers the existence question, so it is
    # reported BEFORE the unreadable branch. Ordering it the other way let one
    # unrelated scanned brochure suppress a detected annex.
    if candidates:
        print("\nVERDICT: REFERENCE AVAILABLE — the recorded verdict is now FALSE.")
        for scan in candidates:
            print(
                f"  {scan.name}: {scan.candidate_tables} candidate table(s), "
                f"largest pairs {scan.largest_table_pairs}"
            )
        print(
            "\nA candidate reference was detected. Check its geography and what "
            "its numbers\nmeasure before deciding whether to run the "
            "correlation: APRA's CVA reports the\ninsurance protection gap (an "
            "affordability measure), not hazard exposure, so a\nmatching table "
            "is not automatically a usable reference. See the Validation\n"
            "status section of docs/CLIMATE_RISK_METHODOLOGY.md."
        )
        return 1

    if unreadable:
        print(
            f"\nRED: {len(unreadable)} document(s) have no extractable text "
            "layer. Nothing was read\n     from them, so they cannot be scored "
            "as containing no reference:"
        )
        for scan in unreadable:
            print(f"       {scan.name} ({scan.pages} pages, {scan.text_chars} chars)")
        print(
            "     A scanned annex could hold the exact SA3 table this looks "
            "for.\n     Outcome is UNKNOWABLE until these are OCR'd or read by "
            "a person."
        )
        return 1

    # Raster content nobody read, inside a document that DOES discuss SA3/SA4,
    # is the one shape that makes absence unprovable: the numbers may be there
    # as a picture. This is the actual state of APRA Mind the Gap 2026 — its
    # Figures 9 and 10 ARE the SA3 results. "Absent" would be the wrong word.
    # ANY unread content raster blocks the ABSENT verdict, not only one in a
    # document whose *extractable text* names a geography — the heading could
    # itself be inside the image, which is precisely the case that cannot be
    # detected from text. Documents that do name SA3/SA4 are listed first
    # because they are the strong evidence; the rest still bar exit 0.
    blind = [s for s in scans if s.unread_content_pages]
    blind.sort(key=lambda s: (not s.names_a_geography, s.name))
    if blind:
        named = [s for s in blind if s.names_a_geography]
        print(
            "\nVERDICT: REFERENCE NOT EXTRACTABLE — the correlation still "
            "cannot be run,\nbut this is NOT a finding that the data does not "
            "exist."
        )
        for scan in named:
            print(
                f"  {scan.name}: {scan.unread_content_pages} page(s) carry a "
                f"content-sized image\n    that nothing here can read, and the "
                f"document names an ASGS geography."
            )
        rest = len(blind) - len(named)
        if rest:
            print(
                f"  A further {rest} document(s) carry unread content images "
                "without naming an\n    ASGS geography in their extractable "
                "text — which proves nothing either way,\n    because a "
                "heading rendered inside an image cannot be read from text."
            )
        print(
            "\n  The series may be present as a figure or map rather than a "
            "table. Reading\n  it would need OCR, or digitising a choropleth — "
            "which does not recover\n  reliable per-region values in any case.\n"
            "  Outcome is UNKNOWABLE — not a pass, and not a failure of the "
            "score."
        )
        _print_ceiling(scans, total_pages)
        return 1

    # Split-series evidence is checked BEFORE the absent verdict: a ranking
    # continued across pages is possible usable evidence, and asserting absence
    # over it would be the same error in miniature.
    split = [s for s in scans
             if s.candidate_tables == 0
             and s.geography_page_pairs >= MIN_REGIONS_FOR_RANKING]
    if split:
        print(
            "\nVERDICT: POSSIBLE SPLIT SERIES — UNKNOWABLE. No single table "
            "clears the bar,\nbut these documents hold enough label-value pairs "
            "ACROSS tables on geography\npages that a ranking continued over "
            "several pages would look like this.\nTables are not stitched "
            "across pages (continuation detection is not reliable\nhere), so "
            "this is escalated to a person rather than judged:"
        )
        for scan in split:
            print(
                f"  {scan.name}: {scan.geography_page_pairs} pairs across "
                f"geography pages, largest single table {scan.largest_table_pairs}"
            )
        return 1

    print("\nVERDICT: REFERENCE ABSENT — the pre-committed correlation cannot be run.")
    print(
        "  No document pairs a rankable set of labels with numeric values on a\n"
        "  page naming an ASGS geography. APRA's regional results (Mind the Gap\n"
        "  2026, Figures 9-10) are raster images; the underlying SA3 series is\n"
        "  not published in the report.\n"
        "  Outcome is UNKNOWABLE — not a pass, and not a failure of the score."
    )

    _print_ceiling(scans, total_pages)
    return 0


if __name__ == "__main__":
    sys.exit(main())
