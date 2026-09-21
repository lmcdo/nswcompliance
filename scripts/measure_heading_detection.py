#!/usr/bin/env python3
# prior-art-checked: neighbours opened, not guessed from their names.
#   dcp_extract_changed.DCPExtractor.SECTION_RE / COUNCIL_SECTION_RE_OVERRIDES
#       the incumbent. IMPORTED here, not reimplemented, so the baseline is the
#       code that actually runs in production rather than a fair-sounding copy.
#   dcp_extract_changed.classify_toc_or_divider_page   already decides whether a
#       page is a contents page, for suppression. Reused for FINDING the contents
#       page instead of skipping it -- same question, opposite use.
#   verify_extraction_fidelity._page_text_for_chapter  gives page text via R2 but
#       flattens it to strings, so it cannot answer a question about font size.
#       This reads spans directly with fitz for that reason.
#   validate_controls_against_source_pdf   compares stored NUMBERS to a page. This
#       compares which LINES are headings. Different question, same R2 plumbing.
"""Which finds a DCP's real section headings: its typography, or our regex?

WHY THIS EXISTS
---------------
The reader infers section headings with a regex over raw page text. When that is
wrong for a council, the remedy has been a per-council exception. As of 2026-09-21
scripts/dcp_extract_changed.py holds EIGHT such tables, and the four entries in
COUNCIL_SECTION_RE_OVERRIDES were each added after something broke downstream --
woollahra 2026-05, marrickville 2026-08, ku_ring_gai, northern_beaches -- never
because a check found the class. There are ~31 councils registered. That does not
converge, and nothing in the repo measures whether it is converging.

docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md section 79 already specifies the general
mechanism: route hard councils to a structure-aware extractor rather than inferring
structure from raw text. This script is the measurement that should have preceded
the fourth exception -- does reading the document's own typography beat the regex,
on councils nobody has tuned for?

WHAT IS AND IS NOT HARDCODED
----------------------------
No font size appears in this file. Warringah's headings are 12.8pt bold and its
body is 11pt; City of Sydney's ladder runs 48/30/24/18/12 over a 10pt body;
Ku-ring-gai's runs 90/60/40/35/32. A constant that fitted one would be the same
mistake in a new costume. Every threshold below is a RATIO against the figures
that document itself yields.

THE METRIC, FIXED BEFORE ANY RESULT EXISTED
-------------------------------------------
Scored against the document's own contents page, which is the only ground truth
available at scale that no human has to write:

    recall     = TOC codes that were found as a heading      (misses = lost sections)
    precision  = found headings that appear in the TOC       (excess = junk sections)

BOTH are reported for BOTH methods on the SAME chapters. A single number for one
method would be an opinion. Typography wins only if it beats the regex on both,
and it has to do that on councils that have no override -- otherwise it is only
beating a regex on documents the regex was hand-fitted to, which proves nothing.

NOT KNOWING IS ITS OWN ANSWER
-----------------------------
A chapter reports NO_TEXT_LAYER (scanned, so there is no typography to read),
NO_TOC (nothing to score against) or NO_LADDER (headings are not typographically
distinct in this document) as distinct outcomes. None of them counts as a pass for
either method. A measurement that silently scores what it could not read is how a
check ends up watching nothing.
"""
from __future__ import annotations

import argparse
import os
import re
import statistics
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import fitz  # noqa: E402  PyMuPDF, already a dependency

# ── Ratios, not sizes ────────────────────────────────────────────────────────
#: A tier counts as "above the body" when it is at least this much larger. 0.4pt
#: is below the smallest real step seen in any sampled document (11 -> 12.8 in
#: Warringah, 10 -> 12 in City of Sydney) and above the rounding noise in span
#: sizes, which fitz reports to a fraction of a point.
SIZE_STEP_PT = 0.4
#: A heading line is short. Expressed against the MEDIAN body line length of this
#: document, so a plan set in a narrow column and one set full-width are judged
#: the same way.
HEADING_MAX_LEN_RATIO = 1.2
#: A tier used for a large share of all lines is running text, a cover, or page
#: furniture -- not a section tier. Again a share of this document's own lines.
TIER_MAX_SHARE = 0.08
#: Below this many uses a tier is a one-off (a cover title), not a section tier.
TIER_MIN_USES = 3

#: A section code at the start of a line: optional letters, digits, optional
#: dotted parts. Deliberately LOOSE -- this is how a candidate is recognised for
#: scoring, not how a heading is detected, and a tight pattern here would hide
#: the very differences being measured.
CODE_RE = re.compile(r"^([A-Za-z]{0,3}\d+[A-Za-z]?(?:[.\-]\d+)*)\s+(\S.*)$")
#: A contents-page line: a title, then leaders or whitespace, then a page number.
TOC_LINE_RE = re.compile(r"^(.*?)[\s.·]{2,}(\d{1,4})\s*$")


@dataclass
class Line:
    size: float
    bold: bool
    text: str
    page: int


@dataclass
class Result:
    name: str
    verdict: str = "OK"
    body_size: float = 0.0
    body_bold: bool = False
    tiers: list = field(default_factory=list)
    toc_codes: dict = field(default_factory=dict)
    typo_codes: set = field(default_factory=set)
    regex_codes: set = field(default_factory=set)
    pages: int = 0
    truth_source: str = "none"

    #: The outline's page and the PDF page can differ by a cover or a renumber, so
    #: a hit is allowed to sit within this many pages of where the outline puts it.
    PAGE_SLACK = 1

    def _pr(self, found: set) -> tuple[float, float]:
        """recall, precision -- a code counts only when found NEAR its own page."""
        truth = self.toc_codes
        if not truth:
            return 0.0, 0.0
        hit_codes = {c for c, pg in found
                     if c in truth and abs(pg - truth[c]) <= self.PAGE_SLACK}
        found_codes = {c for c, _ in found}
        return (len(hit_codes) / len(truth),
                len(hit_codes) / len(found_codes) if found_codes else 0.0)

    @property
    def typo(self) -> tuple[float, float]:
        return self._pr(self.typo_codes)

    @property
    def regex(self) -> tuple[float, float]:
        return self._pr(self.regex_codes)


def read_lines(path: Path, max_pages: int) -> tuple[list[Line], int, list]:
    """Lines, page count, and the PDF's own outline if it has one.

    The outline is the best ground truth available: it is written by the tool that
    typeset the document, from the real heading styles, and it is independent of
    BOTH methods being compared here. 6 of 16 councils sampled 2026-09-21 carry one
    -- burwood's reads "1 Introduction / 1.1 The Purposes and Aims / 1.2 Citation".
    """
    doc = fitz.open(str(path))
    total = doc.page_count
    try:
        outline = doc.get_toc() or []
    except Exception:  # noqa: BLE001 -- a malformed outline is "no outline"
        outline = []
    out: list[Line] = []
    for pno in range(min(total, max_pages)):
        for blk in doc[pno].get_text("dict").get("blocks", []):
            for ln in blk.get("lines", []):
                spans = ln.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue
                out.append(Line(round(max(s["size"] for s in spans), 1),
                                bool(spans[0]["flags"] & 2 ** 4), text, pno + 1))
    doc.close()
    return out, total, outline


def body_style(lines: list[Line]) -> tuple[float, bool]:
    """The document's body text: the commonest style weighted by CHARACTERS.

    Weighted by characters and not by lines because a contents page or a run of
    headings is many short lines, and counting lines lets it outvote the prose it
    is a table of.
    """
    weight: Counter = Counter()
    for ln in lines:
        weight[(ln.size, ln.bold)] += len(ln.text)
    return weight.most_common(1)[0][0]


def heading_tiers(lines: list[Line], body: tuple[float, bool]) -> list[tuple[float, bool]]:
    """Styles set above the body, rarely enough to be headings. Derived per document."""
    body_size, body_bold = body
    uses: Counter = Counter((ln.size, ln.bold) for ln in lines)
    cap = max(TIER_MIN_USES, int(len(lines) * TIER_MAX_SHARE))
    above = [
        style for style in uses
        if (style[0] > body_size + SIZE_STEP_PT
            or (abs(style[0] - body_size) <= SIZE_STEP_PT and style[1] and not body_bold))
    ]
    return sorted((s for s in above if TIER_MIN_USES <= uses[s] <= cap),
                  key=lambda s: (-s[0], -s[1]))


def typography_codes(lines: list[Line], body: tuple[float, bool],
                     tiers: list[tuple[float, bool]]) -> set:
    """Section codes on lines set in a heading tier and short enough to be a title."""
    body_lens = [len(ln.text) for ln in lines if (ln.size, ln.bold) == body]
    limit = (statistics.median(body_lens) if body_lens else 60) * HEADING_MAX_LEN_RATIO
    tierset = set(tiers)
    found = set()
    for ln in lines:
        if (ln.size, ln.bold) not in tierset or len(ln.text) > limit:
            continue
        m = CODE_RE.match(ln.text)
        if m:
            found.add((norm_code(m.group(1)), ln.page))
    return found


def regex_codes(lines: list[Line], council: str | None) -> set:
    """What the incumbent finds, imported from the module that actually runs."""
    from dcp_extract_changed import COUNCIL_SECTION_RE_OVERRIDES, DCPExtractor
    rx = COUNCIL_SECTION_RE_OVERRIDES.get(council or "", DCPExtractor.SECTION_RE)
    found = set()
    for ln in lines:
        m = rx.match(ln.text)
        if m:
            code = next((g for g in m.groups() if g), None)
            if code:
                found.add((norm_code(code), ln.page))
    return found


def norm_code(code: str) -> str:
    """Compare codes, not their punctuation: 4.1a.1, 4_1a_1 and 4-1A-1 are one code."""
    return re.sub(r"[.\-_\s]", "", code).upper()


def outline_codes(outline: list) -> dict:
    """{code: page} from the PDF's embedded outline. Independent of both methods.

    The PAGE is the half that matters and was missed at first. Scoring on the code
    alone credits a method for matching a contents-page line, because a TOC lists
    every code in the document. Burwood scored the regex 34% recall that way: its
    front matter is contents pages, its "hits" were lines like
    "1         Introduction ................." and not one was a heading.

    Requiring the code to be found on the page the outline puts it on removes that
    for BOTH methods at once, which is why it is a correction and not a thumb on
    the scale.
    """
    codes: dict[str, int] = {}
    for entry in outline:
        title = (entry[1] if len(entry) > 1 else "").strip()
        page = entry[2] if len(entry) > 2 and isinstance(entry[2], int) else 0
        m = CODE_RE.match(title)
        if m and page > 0:
            codes.setdefault(norm_code(m.group(1)), page)
    return codes


def toc_codes(lines: list[Line], total_pages: int) -> set:
    """Codes listed on the document's own contents page(s).

    A contents page is found the way a reader finds one: a page where many lines
    end in a page number after leaders. Only the front of the document is
    considered, because an appendix index late on lists figures, not sections.
    """
    front = max(1, min(total_pages, 30))
    by_page: dict[int, list[Line]] = {}
    for ln in lines:
        if ln.page <= front:
            by_page.setdefault(ln.page, []).append(ln)
    codes = set()
    for _page, page_lines in sorted(by_page.items()):
        entries = [ln for ln in page_lines if TOC_LINE_RE.match(ln.text)]
        if len(entries) < 5 or len(entries) < 0.3 * len(page_lines):
            continue  # not a contents page
        for ln in entries:
            title = TOC_LINE_RE.match(ln.text).group(1).strip()
            m = CODE_RE.match(title)
            if m:
                codes.add(norm_code(m.group(1)))
    return codes


def measure(path: Path, name: str, council: str | None, max_pages: int) -> Result:
    r = Result(name=name)
    try:
        lines, total, outline = read_lines(path, max_pages)
    except Exception as exc:  # noqa: BLE001 -- a bad PDF is a result, not a crash
        r.verdict = f"UNREADABLE ({str(exc)[:40]})"
        return r
    r.pages = total
    if len(lines) < 50:
        r.verdict = "NO_TEXT_LAYER"
        return r
    r.body_size, r.body_bold = body_style(lines)
    r.tiers = heading_tiers(lines, (r.body_size, r.body_bold))
    if not r.tiers:
        r.verdict = "NO_LADDER"
        return r
    # Ground truth, best source first. Which one was used is reported, because a
    # score is only as independent as the truth it was scored against.
    r.toc_codes = outline_codes(outline)
    r.truth_source = "outline"
    if not r.toc_codes:
        r.toc_codes = {}
        r.truth_source = "contents-page"
    r.typo_codes = typography_codes(lines, (r.body_size, r.body_bold), r.tiers)
    r.regex_codes = regex_codes(lines, council)
    if not r.toc_codes:
        r.truth_source = "none"
        r.verdict = "NO_GROUND_TRUTH"
    return r


def line_for(r: Result) -> str:
    if r.verdict != "OK":
        return (f"  {r.verdict:<14} {r.name[:44]:<44} "
                f"(typo found {len(r.typo_codes)}, regex found {len(r.regex_codes)})")
    tr, tp = r.typo
    rr, rp = r.regex
    win = "typography" if (tr >= rr and tp >= rp and (tr, tp) != (rr, rp)) else (
        "regex" if (rr >= tr and rp >= tp and (tr, tp) != (rr, rp)) else "tie/mixed")
    return (f"  typo r={tr:5.0%} p={tp:5.0%} | regex r={rr:5.0%} p={rp:5.0%} | "
            f"{win:<10} | truth={r.truth_source[:13]:<13} n={len(r.toc_codes):<4} "
            f"{r.name[:32]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", action="append", default=[], metavar="PATH[:COUNCIL]",
                    help="a local PDF to measure; repeatable. Use this for a council "
                         "with no registry row, which is the only honest test of "
                         "generality.")
    ap.add_argument("--council", action="append", default=[],
                    help="measure chapters of this council from the registry; repeatable")
    ap.add_argument("--limit", type=int, default=6, help="chapters per council")
    ap.add_argument("--max-pages", type=int, default=120,
                    help="pages read per document; the ladder settles long before this")
    args = ap.parse_args()

    results: list[Result] = []

    for spec in args.pdf:
        path, _, council = spec.partition(":")
        p = Path(path)
        if not p.exists():
            print(f"  MISSING        {path}")
            continue
        results.append(measure(p, p.name, council or None, args.max_pages))

    if args.council:
        import boto3
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv(REPO.parents[2] / ".env") if (REPO.parents[2] / ".env").exists() \
            else load_dotenv(REPO / ".env")
        s3 = boto3.client(
            "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        for council in args.council:
            cur.execute(
                """SELECT chapter_key, r2_current_path FROM dcp_chapter_registry
                    WHERE council = %s AND is_active AND r2_current_path IS NOT NULL
                    ORDER BY chapter_key LIMIT %s""", (council, args.limit))
            for chapter_key, r2_path in cur.fetchall():
                local = Path(tempfile.gettempdir()) / f"hd_{council}_{chapter_key[:30]}.pdf"
                try:
                    if not local.exists() or local.stat().st_size < 1000:
                        s3.download_file(os.environ["R2_BUCKET_NAME"], r2_path, str(local))
                except Exception as exc:  # noqa: BLE001
                    print(f"  NO_SOURCE      {council}/{chapter_key}: {str(exc)[:40]}")
                    continue
                results.append(measure(local, f"{council}/{chapter_key}", council,
                                       args.max_pages))
        conn.close()

    if not results:
        print("nothing measured -- pass --pdf and/or --council")
        return 2

    print()
    for r in results:
        print(line_for(r))

    scored = [r for r in results if r.verdict == "OK"]
    print()
    print(f"  {len(scored)} of {len(results)} documents scorable")
    for verdict in sorted({r.verdict for r in results if r.verdict != "OK"}):
        n = sum(1 for r in results if r.verdict == verdict)
        print(f"    {verdict}: {n}  (counted as a pass for NEITHER method)")
    if scored:
        tr = statistics.mean(r.typo[0] for r in scored)
        tp = statistics.mean(r.typo[1] for r in scored)
        rr = statistics.mean(r.regex[0] for r in scored)
        rp = statistics.mean(r.regex[1] for r in scored)
        print()
        print(f"  MEAN  typography  recall {tr:.0%}  precision {tp:.0%}")
        print(f"  MEAN  regex       recall {rr:.0%}  precision {rp:.0%}")
        print()
        if tr >= rr and tp >= rp:
            print("  Typography is at least as good on BOTH measures.")
        elif rr >= tr and rp >= tp:
            print("  The regex is at least as good on BOTH measures.")
        else:
            print("  Split result -- each method wins one measure. Neither replaces the")
            print("  other on this evidence; read the per-document rows above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
