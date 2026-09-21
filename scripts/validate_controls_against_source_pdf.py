#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no check compares a control against the
# COUNCIL'S PUBLISHED PDF. Four sweeps, 2026-08-08, origin/main f5acb080:
#  (1) validate_control_source_values.py (#868) compares the VALUE to its own stored QUOTE
#      -- passes when the quote itself came from the wrong place (canada_bay 701). That
#      residual is what this closes; together they chain value -> quote -> published page.
#  (2) validate_controls_provenance.py (#866) classifies provenance from the REPO; never
#      opens a document.
#  (3) link_controls_to_provisions.py (#867) matches against the ingested CORPUS -- 42 of
#      1,071 rows, and the corpus is itself extracted, so not an independent authority.
#      measure_control_quote_gap.py measures why that misses; also corpus.
#  (4) numeric_control_review.py is the nearest relative and its R2 wiring is REUSED, not
#      copied. It is a per-chapter human review artifact for when a PDF changes: table
#      extraction only, no pass mark, not a gate, and its imports degrade to None.
#  Frontend: StateLevelControls / DcpStructuredControls / planning-controls /
#  api/dcp/structured-controls all RENDER controls; none verifies one.
"""Is a stored control actually supported by the council document it cites?

WHY
---
The capability statement of 2026-08-08 (`~/.claude/plans/ce-*-capability-statement-2026-08.md`,
section 2.6d) records the controls table as "not compared against anything -- no control
value has been checked against a council's own published statement of that number by an
independent party." This is that comparison. The council's PDF is an authority nothing in
our pipeline produced.

(The path is wildcarded deliberately. That file's name contains the umbrella word banned by
ce-output-grounding-campaign-2026-08 section 7 -- the document itself opens by conceding the
point -- and this repo's liability scan flags the literal string. Spelling it out would make
this file the next place the banned word is quoted from.)

TWO SEPARATE QUESTIONS, NEVER MERGED
------------------------------------
Pre-implementation probing (Marrickville, 2026-08-08) proved they can have different
answers -- the data was right and the citation was wrong -- so reporting one number for
both would hide a real defect behind a good one.

  A. IS THE CONTROL REAL?   Do its numbers and distinguishing words appear together
                            somewhere in the cited document?  -> tests the DATA.
  B. DOES THE PAGE WORK?    Is that somewhere the page the row cites?  -> tests the
                            CITATION a customer would follow.

WHY NOT A VERBATIM TEXT MATCH
-----------------------------
`source_text` is documented everywhere as "the verbatim sentence". For table-derived
controls it is not. Measured example:

  stored : "Seniors housing: 0.2 per unit for residents + 1 per 5 units for visitors
            and carers (Parking Area 1)"
  PDF    : "Seniors housing" | "0.2 per unit for residents + 1 per 5 units for visitors
            & carers"  -- a table row, under the column heading "Car spaces: Parking Area 1"

That is a faithful reconstruction of a table cell plus its row and column labels, not a
quotation. A contiguous-run test would score it near zero and report a false crisis. So
the test is numeric-token presence plus distinguishing-term coverage, which is what a
human checking the table would actually do.

THE MARKS, FIXED BEFORE THE RUN
-------------------------------
  A. DATA -- >= 95% of checkable controls supported somewhere in their cited document.
     A real test: the answer is not known.
  B. CITATION -- MEASURED AND REPORTED, DELIBERATELY UNGRADED on this run. One case was
     inspected during pre-implementation and is known to fail. Setting a target after
     seeing a result is the renegotiation the pre-commitment rule exists to prevent, so
     no pass mark is claimed for B until a run whose outcome was not peeked at.
  HONESTY -- unfetchable documents, pages with no text layer and rows with no quote are
     "could not check": never a pass, never a failure, always excluded from the
     denominator and printed beside every rate.

RED-ABLE FOUR WAYS: a control unsupported by its document; a cited page past the end of
the document; the supported rate below 95%; nothing checkable at all. Falsifiability is
proven by planting defects in the pure core -- `tests/test_controls_against_source_pdf.py`.

Read-only against the database.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# Module scope on purpose: an absent library must make this RED, never a quiet skip.
# numeric_control_review.py's try/except-to-None is the pattern that left 23 tests dark.
import fitz  # PyMuPDF
import psycopg2

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from services.extracted_data_integrity import (  # noqa: E402
    FAILING_STATES,
    NO_VALUE_STORED,
    explain_row,
)

SUPPORTED_ON_CITED_PAGE = "supported_on_cited_page"
SUPPORTED_ELSEWHERE = "supported_on_another_page"
UNSUPPORTED = "unsupported_by_document"
PAGE_OUT_OF_RANGE = "cited_page_past_end_of_document"
DOC_NO_TEXT = "document_has_no_text_layer"
DOC_UNAVAILABLE = "document_unavailable"
NO_QUOTE = "row_has_no_source_text"
# A control can legitimately have NO number: Waverley/Woollahra front setbacks are
# character-based ("consistent with the predominant setback of adjacent development"),
# Woollahra's landscaping is expressed via deep-soil and canopy instead, and a nil
# parking requirement is stored as 0. Measured: 14 of the 152. There is no number to look
# for, so THIS METHOD cannot test them -- which is a limit of the method, not a defect in
# the row. Calling them "unsupported" would manufacture 14 failures out of correct data.
NO_TESTABLE_VALUE = "no_numeric_value_to_check"

COULD_NOT_CHECK = {DOC_NO_TEXT, DOC_UNAVAILABLE, NO_QUOTE, NO_TESTABLE_VALUE}
SUPPORTED = {SUPPORTED_ON_CITED_PAGE, SUPPORTED_ELSEWHERE}
HARD_FAIL = {UNSUPPORTED, PAGE_OUT_OF_RANGE}

TERM_COVERAGE_MIN = 0.70
# Below this many distinguishing words, "supported" means the value is on the page beside
# the one or two words the quote has -- consistent, not pinned. Reported, not enforced:
# raising it to a rule would fail 34 rows whose terseness is the council's table design.
MIN_PINNING_TERMS = 3
PAGE_TOLERANCE = 1
DATA_MARK = 0.95

# Clause markers ("C.05", "O.01", "A.1.2") lead most DCP control sentences. Their digits
# are NOT control values, and treating them as such is a measured false-positive source:
# parramatta id=563 quoted "C.06 On corner lots ... minimum of 3 metres", from which the
# naive reader took numbers {6, 3} and then "found" them on a page discussing 600m2
# suburban lots. This is the same trap the zone-code probe hit -- Woollahra's C1 is
# Control 1 and Ashfield's E1 is a chapter label, not zone codes
# (ce-reliability-retrospective-and-asset-inventory-2026-08 2.1). Stripped, never counted.
_CLAUSE_MARKER = re.compile(r"^\s*[A-Z]{1,2}\.?\s?\d+(?:\.\d+)*\s*", re.I)

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "at", "by", "with",
    "is", "are", "be", "must", "shall", "may", "not", "no", "per", "from", "as", "that",
    "this", "any", "all", "each", "min", "max", "minimum", "maximum", "required",
    "requirement", "m", "mm", "m2", "sqm", "metres", "meters", "than", "greater", "less",
    "up", "where", "which", "if", "it", "its", "one", "two", "shallbe",
}
_WS = re.compile(r"\s+")
_NUM = re.compile(r"\d+(?:\.\d+)?")
# A citation marker is what separates our note from the council's own parenthetical, so
# the test is the marker, never the brackets: "(Table 4, same as RFB)" goes, "(sites
# <800m from railway station)" stays.
_CITE_MARKER = r"DCP|Table|Part(?:\s|$)|Section|Schedule|Figure|Clause|Chapter|s\d|19\d\d|20\d\d"
_CITATION_TAIL = re.compile(rf"\s*\((?=[^)]*(?:{_CITE_MARKER}))[^)]*\)\s*$", re.I)
# "Ashfield DCP 2016 A-Part8 Table 2: Flats -- ..." -- a provenance preamble, which is
# only recognised when it names a plan AND ends at a colon within the first 120
# characters. Without both, a sentence containing a colon would lose its subject.
_PROVENANCE_PREAMBLE = re.compile(r"^[^:]{0,120}?\bDCP\b[^:]{0,120}?:\s*", re.I)

# `explain_value` returns evidence as "<quoted span from the source> -> <derived value>"
# (or "... converted to ...", "... stored as ..."). The quoted span is the part the
# council wrote; everything outside it is our arithmetic.
_EVIDENCE_SPAN = re.compile(r"'([^']*)'|\"([^\"]*)\"")
_WORD = re.compile(r"[a-z][a-z\-']{2,}")


def normalise(text: str) -> str:
    """Fold the differences a PDF text layer adds but a reader would not notice."""
    if not text:
        return ""
    for bad, good in (("‘", "'"), ("’", "'"), ("“", '"'),
                      ("”", '"'), ("–", "-"), ("—", "-"),
                      (" ", " "), ("&", " and ")):
        text = text.replace(bad, good)
    return _WS.sub(" ", text).strip().lower()


def strip_clause_marker(text: str) -> str:
    """Drop a leading clause marker so its digits are never read as a control value."""
    return _CLAUSE_MARKER.sub("", text or "", count=1)


def strip_provenance(text: str) -> str:
    """Remove OUR citation note from a quote, keeping the council's own words.

    `source_text` routinely carries a provenance wrapper that no council page contains:
    a trailing "(Penrith DCP 2014 Part D2)" or "(Table 4, same as RFB)" -- 40 of the 67
    rows unsupported on the 2026-09-18 run -- and sometimes a leading "Ashfield DCP 2016
    A-Part8 Table 2:". Matching those against the page can only ever fail, and it fails in
    the two worst ways: the year becomes a number demanded of the page (leichhardt 1086
    was marked unsupported for want of "2013"), and the citation's words dilute term
    coverage until a control whose value IS on the page misses the bar (penrith 1117,
    50%, with "more than 24m2 of usable private open space" printed on the cited page).

    Only the wrapper goes. A parenthetical the council wrote -- "(sites <800m from railway
    station)" -- carries no citation marker and is left alone, because it is exactly what
    tells two neighbouring table rows apart.
    """
    out = _PROVENANCE_PREAMBLE.sub("", text or "", count=1)
    while True:
        stripped = _CITATION_TAIL.sub("", out, count=1)
        if stripped == out:
            return out.strip()
        out = stripped


def numeric_tokens(text: str) -> list[str]:
    """Numbers in the quote, clause marker removed.

    '0.50', '.5' and '0.5' are one number to a reader, so values are parsed and compared
    numerically rather than as strings.
    """
    out: list[str] = []
    for raw in _NUM.findall(normalise(strip_clause_marker(text))):
        try:
            val = float(raw)
        except ValueError:
            continue
        out.append(f"{val:g}")
    return out


def required_values(value_min, value_max) -> list[str]:
    """The numbers that MUST be on the page: the control's own stored value.

    This is the claim being checked. Numbers scraped from the quote are supporting
    context and can be noisy (clause markers, figure references, cross-references); the
    stored value is the thing the product serves and the thing a reader would verify.
    A control whose own value is absent from the page is unsupported regardless of how
    much of its prose matches.
    """
    out: list[str] = []
    for v in (value_min, value_max):
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        out.append(f"{f:g}")
        # A stored metre value is routinely written in millimetres in the source
        # ("900mm" -> 0.9) and vice versa; accept either spelling of the same quantity.
        if f < 10:
            out.append(f"{f * 1000:g}")
        elif f >= 100:
            out.append(f"{f / 1000:g}")
    return out


def distinctive_terms(text: str) -> list[str]:
    """Content words that identify WHICH control this is (e.g. 'seniors', 'housing')."""
    return sorted({w for w in _WORD.findall(normalise(strip_clause_marker(text)))
                   if w not in _STOP})


def derivation_is_on_page(quote: str, page_nums: set[str],
                          value_min, value_max, unit) -> str | None:
    """Name the rule by which the page supports a value that is NOT written on it.

    A council writes the rate, not the quotient. "1 space per 7 dwellings" is stored as
    0.143, "4m x 4m" as 16, "may be built to the rear boundary" as 0 -- so requiring the
    stored number on the page marks correct rows unsupported. Measured on the first full
    run (2026-09-18): 116 of 767 unsupported, and seven pages opened by hand were all of
    this kind (hornsby 199 "1 space per 7 dwellings", blacktown 350 "1 per 2.5 dwellings",
    randwick 221 "1 visitor space per 4 dwellings", marrickville 1113 "min 4m x 4m",
    penrith 50 "built to the rear boundary").

    The derivation is NOT taken on trust, which would make the check unfalsifiable: the
    rule must be one `explain_row` can name from the quote, AND every quantity that rule
    quoted must itself appear on the cited page. So the chain is value <- quote <- page,
    with an independent authority at the end, and a quote that says 50% behind a stored
    15 (waverley 635) still fails -- no rule explains it.

    Returns the rule name, or None when nothing explains the value from this page.
    """
    row = {"value_min": value_min, "value_max": value_max,
           "source_text": quote, "unit": unit}
    verdict = explain_row(row, value_fields=["value_min", "value_max"],
                          source_field="source_text", unit_field="unit")
    state = verdict["state"]
    if state in FAILING_STATES or state == NO_VALUE_STORED:
        return None
    for detail in verdict["fields"].values():
        if detail["rule"] == NO_VALUE_STORED:
            continue
        evidence = detail.get("evidence")
        if not evidence:
            return None
        # Every number the rule read OUT OF THE QUOTE has to be on the page. Only the
        # quoted span counts: an evidence string reads "'1 ... per 7' -> 0.1429", and the
        # part after the arrow is the derived value -- the very number that is not written
        # on the page and whose absence brought us here. Requiring it would make this
        # branch dead code that silently never fires.
        source_side = " ".join(q or qq for q, qq in _EVIDENCE_SPAN.findall(evidence))
        if not all(n in page_nums for n in numeric_tokens(source_side)):
            return None
    return state


def page_supports(quote: str, page_text: str,
                  value_min=None, value_max=None, unit=None) -> tuple[bool, float, list[str]]:
    """Does this page carry the control's stored VALUE, with enough of its wording?

    Two independent conditions, both required:
      * the stored value appears on the page (in metres or millimetres) -- this is the
        claim under test, and a control missing it is unsupported however well its prose
        matches;
      * at least TERM_COVERAGE_MIN of the quote's distinguishing words appear -- this is
        what stops a bare number matching by coincidence on a long document.

    Returns (supported, term_coverage, missing_values).
    """
    stored_quote = quote          # the row as stored: length is what marks a severed quote
    quote = strip_provenance(quote)
    page = normalise(page_text)
    if not page:
        return False, 0.0, required_values(value_min, value_max) or numeric_tokens(quote)

    page_nums = set(numeric_tokens(page_text))
    # Fall back to the quote's numbers only when the row stores no value at all.
    wanted = required_values(value_min, value_max)
    if wanted:
        missing = [] if any(w in page_nums for w in wanted) else wanted
        # The STORED text, not the stripped one: `explain_row` rejects a quote sitting at
        # the extractor's cut, and trimming even a trailing space would hide that.
        if missing and derivation_is_on_page(stored_quote, page_nums,
                                             value_min, value_max, unit):
            missing = []
    else:
        wanted = numeric_tokens(quote)
        missing = [n for n in wanted if n not in page_nums]

    # Our citation words are not REQUIRED of the page, but they are not thrown away
    # either: "(Table C-B)" is often printed on the page as a real column header, and
    # simply deleting it cost coverage on rows that were matching it. So the denominator
    # is the council's own words and the numerator counts every word that matched --
    # measured on the 2026-09-18 runs, deleting outright fixed 11 rows and broke 11.
    terms = distinctive_terms(quote)
    all_terms = distinctive_terms(stored_quote)
    matched = sum(1 for t in all_terms if t in page)
    coverage = min(1.0, matched / len(terms)) if terms else 0.0

    ok = (not missing) and coverage >= TERM_COVERAGE_MIN and bool(wanted) and bool(terms)
    return ok, coverage, missing


@dataclass
class RowVerdict:
    control_id: int
    lga: str
    control_type: str
    cited_page: int | None
    verdict: str
    found_on_page: int | None = None
    page_delta: int | None = None
    coverage: float = 0.0
    missing_numbers: list[str] = field(default_factory=list)
    note: str = ""
    # How many of the council's OWN words this row could be matched on. A bare table cell
    # ("2 spaces") leaves one or two, and a value found beside one word on a 100-page
    # parking document is consistent with the row without pinning it to that row. 34 of
    # 783 are in that position (2026-09-18). Counted and printed, never silently folded
    # into the pass rate -- an unpinned supported row is weaker evidence than a pinned
    # one, and a reader of the headline is entitled to know how many there are.
    required_terms: int = 0


def classify(control_id: int, lga: str, control_type: str, quote: str | None,
             cited_page: int | None, page_texts: dict[int, str] | None,
             page_count: int | None, value_min=None, value_max=None,
             unit=None) -> RowVerdict:
    """Pure: every document access already done by the caller, so this is testable."""
    # Before the first early return: `mk` closes over it, and a row with no quote
    # reaches `mk` without ever passing the lines below.
    term_count = len(distinctive_terms(strip_provenance(quote or "")))

    def mk(v: str, **kw) -> RowVerdict:
        kw.setdefault("required_terms", term_count)
        return RowVerdict(control_id, lga, control_type, cited_page, v, **kw)

    if not quote or not quote.strip():
        return mk(NO_QUOTE, note="row carries no source_text")
    if page_texts is None:
        return mk(DOC_UNAVAILABLE, note="PDF could not be fetched")
    if not any(normalise(t) for t in page_texts.values()):
        return mk(DOC_NO_TEXT, note="no page in this document has a text layer")
    if cited_page is None:
        return mk(DOC_UNAVAILABLE, note="row carries no pdf_page")
    if page_count is not None and cited_page > page_count:
        return mk(PAGE_OUT_OF_RANGE,
                  note=f"cites page {cited_page}; document has {page_count} pages")

    if not required_values(value_min, value_max) and not numeric_tokens(strip_provenance(quote)):
        return mk(NO_TESTABLE_VALUE,
                  note="control stores no number and its quote contains none; "
                       "this method has nothing to look for")

    window = [p for p in range(cited_page - PAGE_TOLERANCE,
                               cited_page + PAGE_TOLERANCE + 1) if 1 <= p]
    best_cov = 0.0
    best_missing = required_values(value_min, value_max) or numeric_tokens(strip_provenance(quote))
    for p in window:
        if p not in page_texts:
            continue
        ok, cov, missing = page_supports(quote, page_texts[p], value_min, value_max, unit)
        if ok:
            return mk(SUPPORTED_ON_CITED_PAGE, found_on_page=p, page_delta=p - cited_page,
                      coverage=cov)
        if cov > best_cov:
            best_cov, best_missing = cov, missing

    for p in sorted(page_texts):
        if p in window:
            continue
        ok, cov, _ = page_supports(quote, page_texts[p], value_min, value_max, unit)
        if ok:
            return mk(SUPPORTED_ELSEWHERE, found_on_page=p, page_delta=p - cited_page,
                      coverage=cov,
                      note=f"cites page {cited_page}; supported on page {p} "
                           f"({p - cited_page:+d})")

    return mk(UNSUPPORTED, coverage=best_cov, missing_numbers=best_missing,
              note=f"no page carries value {best_missing or '(none stored)'} "
                   f"with >={TERM_COVERAGE_MIN:.0%} of its terms "
                   f"(best coverage {best_cov:.0%})")


@dataclass
class Summary:
    verdicts: list[RowVerdict] = field(default_factory=list)

    @property
    def checkable(self):
        return [v for v in self.verdicts if v.verdict not in COULD_NOT_CHECK]

    @property
    def supported(self):
        return [v for v in self.verdicts if v.verdict in SUPPORTED]

    @property
    def on_cited_page(self):
        return [v for v in self.verdicts if v.verdict == SUPPORTED_ON_CITED_PAGE]

    @property
    def data_rate(self) -> float | None:
        n = len(self.checkable)
        return len(self.supported) / n if n else None

    @property
    def citation_rate(self) -> float | None:
        n = len(self.supported)
        return len(self.on_cited_page) / n if n else None

    def verdict_line(self) -> tuple[bool, str]:
        """Mark A only. B is reported, never graded on this run -- see module docstring."""
        n = len(self.checkable)
        if not n:
            return False, "nothing could be checked -- that is not a pass"
        rate = self.data_rate or 0.0
        bad = [v for v in self.verdicts if v.verdict in HARD_FAIL]
        if rate < DATA_MARK:
            return False, (f"FAIL (mark A): {rate:.1%} of {n} checkable controls are "
                           f"supported by their document; mark is {DATA_MARK:.0%}. "
                           f"{len(bad)} unsupported.")
        return True, (f"PASS (mark A): {rate:.1%} of {n} checkable controls are supported "
                      f"by their cited document; mark is {DATA_MARK:.0%}.")


# ---------------------------------------------------------------------- I/O

def find_env() -> Path | None:
    """This repo is BARE; only the bare root holds .env, never a worktree.

    None when there is none. CI has no .env -- it passes the credentials in the
    environment -- so an absent file is a normal state here, not a fatal one. It
    used to sys.exit, which made a runner's missing .env indistinguishable from a
    broken checkout.
    """
    for base in [REPO_ROOT, *REPO_ROOT.parents]:
        if (base / ".env").exists():
            return base / ".env"
    return None


def load_env() -> None:
    """Fill gaps from the bare root's .env. setdefault, so a real environment wins."""
    path = find_env()
    if path is None:
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def connect():
    """Read-only connection, from DATABASE_URL if there is one and PG* if not.

    This indexed os.environ["PGHOST"] directly, and .github/workflows/data-watch.yml
    passes DATABASE_URL and R2_* and no PG* variables at all -- so the nightly run
    died with KeyError: 'PGHOST' before reading a single row. It had failed every
    night since 2026-09-18 (last success 2026-09-17) when this was found on
    2026-09-21, and because the merge gate's freshness step asks when data-watch
    last SUCCEEDED, that one missing variable was blocking every open PR.

    DATABASE_URL is how every other script under scripts/ connects, so it is
    preferred here rather than added as an afterthought. When neither is available
    the failure names what is missing, instead of a bare KeyError on whichever
    variable happened to be read first.
    """
    load_env()
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if dsn:
        conn = psycopg2.connect(dsn, connect_timeout=30)
    else:
        missing = [k for k in ("PGHOST", "PGUSER", "PGPASSWORD", "PGDATABASE")
                   if not (os.environ.get(k) or "").strip()]
        if missing:
            sys.exit("FATAL: no DATABASE_URL, and no usable PG* fallback -- "
                     f"unset: {', '.join(missing)}. The data-watch workflow "
                     "supplies DATABASE_URL; a local run reads the bare root's .env.")
        conn = psycopg2.connect(
            host=os.environ["PGHOST"], user=os.environ["PGUSER"],
            password=os.environ["PGPASSWORD"], dbname=os.environ["PGDATABASE"],
            port=os.environ.get("PGPORT", "5432"),
            sslmode=os.environ.get("PGSSLMODE", "require"), connect_timeout=30)
    conn.set_session(readonly=True, autocommit=True)
    return conn


ROWS_SQL = """
    SELECT c.id, c.lga, c.control_type, c.source_text, c.pdf_page, g.r2_current_path,
           c.value_min, c.value_max, c.unit
    FROM dcp_setback_controls c
    JOIN dcp_chapter_registry g
      ON g.council = c.lga AND g.chapter_key = c.source_chapter_key
    WHERE c.pdf_page IS NOT NULL
      AND c.is_current = TRUE
      AND g.r2_current_path IS NOT NULL AND g.r2_current_path <> ''
    ORDER BY c.lga, g.r2_current_path, c.pdf_page, c.id
"""


def download_from_r2(r2_path: str, cache: Path) -> Path | None:
    import boto3
    dest = cache / r2_path.replace("/", "__")
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    creds = [os.environ.get(k) for k in
             ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")]
    if not all(creds):
        print("    !! R2 credentials absent")
        return None
    account, key, secret, bucket = creds
    s3 = boto3.client("s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
                      aws_access_key_id=key, aws_secret_access_key=secret,
                      region_name="auto")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        s3.download_file(bucket, r2_path, str(dest))
    except Exception as exc:
        print(f"    !! fetch failed: {type(exc).__name__}: {str(exc)[:100]}")
        return None
    return dest


def read_pages(pdf_path: Path) -> tuple[dict[int, str], int]:
    with fitz.open(pdf_path) as doc:
        return {i + 1: doc[i].get_text() for i in range(doc.page_count)}, doc.page_count


def main() -> int:
    ap = argparse.ArgumentParser(description="Check controls against their source PDF")
    ap.add_argument("--cache", default=None)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    cache = Path(args.cache) if args.cache else Path(tempfile.gettempdir()) / "dcp_pdf_cache"
    cache.mkdir(parents=True, exist_ok=True)

    conn = connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '60s'")
    cur.execute(ROWS_SQL)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    by_doc: dict[str, list] = {}
    for r in rows:
        by_doc.setdefault(r[5], []).append(r)

    print(f"{len(rows)} current controls citing a page, across {len(by_doc)} documents")
    print(f"mark A (data): >={DATA_MARK:.0%} supported by the cited document")
    print("mark B (citation): measured, UNGRADED this run -- one case was peeked at\n")

    s = Summary()
    for n, (r2_path, doc_rows) in enumerate(sorted(by_doc.items()), 1):
        if args.limit and n > args.limit:
            break
        print(f"[{n}/{len(by_doc)}] {r2_path.split('/')[-1]}  ({len(doc_rows)} controls)")
        pdf = download_from_r2(r2_path, cache)
        if pdf is None:
            for cid, lga, ct, _q, pg, _p, _vn, _vx, _u in doc_rows:
                s.verdicts.append(RowVerdict(cid, lga, ct, pg, DOC_UNAVAILABLE,
                                             note="fetch failed"))
            continue
        pages, count = read_pages(pdf)
        with_text = sum(1 for t in pages.values() if t.strip())
        print(f"    {count} pages, {with_text} with a text layer")
        for cid, lga, ct, quote, pg, _p, vmin, vmax, unit in doc_rows:
            s.verdicts.append(
                classify(cid, lga, ct, quote, pg, pages, count, vmin, vmax, unit))

    print(f"\n{'=' * 78}\nRESULTS\n{'=' * 78}")
    tally: dict[str, int] = {}
    for v in s.verdicts:
        tally[v.verdict] = tally.get(v.verdict, 0) + 1
    for verdict, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        flag = ("  <- FAILURE" if verdict in HARD_FAIL else
                "  (could not check)" if verdict in COULD_NOT_CHECK else "")
        print(f"  {verdict:<34} {n:>4}{flag}")

    print(f"\n--- A. DATA: is the control real? ---")
    print(f"  supported by its document      {len(s.supported)} of {len(s.checkable)} checkable"
          f"   ({(s.data_rate or 0):.1%})")
    thin = [v for v in s.supported if v.required_terms < MIN_PINNING_TERMS]
    print(f"  ...of those, thinly pinned     {len(thin)}"
          f"   (quote leaves fewer than {MIN_PINNING_TERMS} distinguishing words, e.g."
          f" '2 spaces': the value is on the cited page, but the wording does not say"
          f" which row of the table it came from)")

    print(f"\n--- B. CITATION: does the page reference work? (UNGRADED) ---")
    cr = s.citation_rate
    print(f"  on the page it cites (+/-{PAGE_TOLERANCE})   {len(s.on_cited_page)} of "
          f"{len(s.supported)} supported   ({(cr or 0):.1%})")
    deltas = [v.page_delta for v in s.verdicts
              if v.verdict == SUPPORTED_ELSEWHERE and v.page_delta is not None]
    if deltas:
        by_delta: dict[int, int] = {}
        for d in deltas:
            by_delta[d] = by_delta.get(d, 0) + 1
        print("  page offsets where it was actually found:")
        for d, n in sorted(by_delta.items(), key=lambda kv: -kv[1])[:12]:
            print(f"      {d:+d} pages : {n}")

    problems = [v for v in s.verdicts if v.verdict in HARD_FAIL]
    if problems:
        print(f"\n{'-' * 78}\nEVERY unsupported control, listed:\n{'-' * 78}")
        for v in problems:
            print(f"  id={v.control_id:<6} {v.lga:<18} {v.control_type:<24} "
                  f"page={v.cited_page}")
            print(f"      {v.note}")

    ok, line = s.verdict_line()
    print(f"\n{'=' * 78}\n{line}\n{'=' * 78}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
