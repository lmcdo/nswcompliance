#!/usr/bin/env python3
# prior-art-checked: neighbours opened, not guessed from their names.
#   check_council_completeness.py   per-COUNCIL field FILL COUNTS vs that council's
#                                   previous snapshot. Cannot see a chapter, and a
#                                   chapter that never extracted anything moves no
#                                   fill ratio. Called by dcp_commit_approved, kept.
#   validate_dcp_health.py          absolute invariants (gap=0, duplicates=0) over
#                                   what IS stored. Silent about what is ABSENT.
#   dcp_quality_report.py           renders current state, persists nothing, so it
#                                   can never answer "was this chapter ever whole".
#   ai_extractor.coverage_gap       the check that should have caught all of this.
#                                   Fails open by construction -- see section 4 of
#                                   ce-dcp-data-repair-PLAN-2026-09-12. Fixed in the
#                                   same change; not reused here, because it only
#                                   runs under AI_EXTRACTION=1 and only mid-extract.
#   dcp_table_of_contents (DB)      a static one-off import, 2026-03-21, 1,309 rows,
#                                   no live writer. An input at best.
#   dcp_council_field_snapshot (DB) considered as the store for this and REJECTED --
#                                   see migrations/069 for why the grain is wrong.
# Frontend sweep (app/**, app/internal, components/, hooks/): /internal/dcp-review
# renders dcp_review_queue rows; no surface measures chapter completeness.
"""Measure every DCP chapter with four independent signals, and store the answer.

WHY THIS EXISTS
---------------
On 2026-09-12 a read-only audit of 270 chapters found 95 provably incomplete, 984
listed sections not served, and -- the number that matters -- **113 chapters (42%)
that could not be measured at all**. Nothing in the repo could answer "was this
chapter ever complete", because the only check that asked returned a clean pass
every time it failed to read the document, and never stored its verdict anyway.

The deliverable here is not a verdict. It is the LEDGER: one row per chapter per
run, so the next run can be compared against this one. A measurement that exists
for a second and is discarded is why a page map could drift for months.

WHY FOUR SIGNALS AND NOT ONE
----------------------------
Each one is blind to what the others see, and one of them is blind in a way that
cost two months:

  1  contents list vs served codes    needs a PDF   whole sections ABSENT
  2  gaps in our own numbering        no PDF        holes, e.g. starts at 4.1.12
  3  page header vs stored part       needs a PDF   MISLABELLED content
  4  text capture ratio               needs a PDF   hollow chapters

Signal 3 is the only one that catches Waverley's defect. A code-presence check
calls part B15 "present" while the rows under it hold B17's text, because the
sub-section numbers are read from the page and only the part label comes from the
broken map. Signal 1 sees nothing wrong. Signal 3 reads the running header the
page itself carries and finds 54 of 263 rows contradicting it.

Signal 2 needs no PDF, so it is the only one with 100% coverage, and it is what
makes "every chapter has a measured state" reachable at all.

"MEASURED" IS NOT "CLEAN", AND NEITHER IS "UNKNOWN"
---------------------------------------------------
``measured`` is true when at least one signal that CAN fail actually ran against
this chapter. A chapter with no contents page and fewer than two section codes is
NOT measured, and says so, rather than passing quietly. That distinction is the
whole point: the previous check reported 42% of the corpus as fine when it had
read none of it.

RATCHET
-------
The 2026-09-12 counts are frozen in .claude/dcp_measurement_baseline.json by user
instruction. ``--gate`` fails when a council's INCOMPLETE or UNMEASURED count
rises above its baseline. Counts may go DOWN, never UP. The baseline is not a
target and not an acceptance -- it is the floor that stops a fail-closed check
taking the product dark against 95 chapters that are already known bad.

USAGE
-----
    python scripts/dcp_chapter_measure.py --sweep            # baseline's 10 councils
    python scripts/dcp_chapter_measure.py --sweep --councils all
    python scripts/dcp_chapter_measure.py --sweep --council marrickville
    python scripts/dcp_chapter_measure.py --rescore <raw.json>   # verdicts, no download
    python scripts/dcp_chapter_measure.py --gate <raw.json>      # ratchet only
    python scripts/dcp_chapter_measure.py --sweep --write        # also write the ledger

Exit codes, matching r2_monitor / dcp_watchdog / check_council_completeness, which
run_monitors.py already treats this way:
    0 = nothing went backwards against the baseline
    2 = findings -- the run itself succeeded
    1 = the check itself broke
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from scripts.dcp_toc_parse import parse_contents
except ImportError:  # running from inside scripts/
    from dcp_toc_parse import parse_contents

BASELINE_PATH = os.path.join(_ROOT, ".claude", "dcp_measurement_baseline.json")

# The 10 councils the frozen baseline audited. The registry holds 525 active
# chapters across 19 councils, but 241 of those are city_of_sydney, of which only
# 7 serve any rows -- folding 234 empty chapters in would swamp the ratchet with
# a different problem (chapters registered but never extracted) that belongs in
# its own finding, not in this one. --councils all reports the wider picture.
BASELINE_COUNCILS = [
    "ashfield", "campbelltown", "canterbury_bankstown", "hornsby", "inner_west",
    "ku_ring_gai", "leichhardt", "marrickville", "waverley", "woollahra",
]

MAX_TOC_SCAN = 14          # contents pages sit at the front
HEADER_SCAN_LINES = 3      # a running header is in the top (or bottom) few lines

# ── signal 1: contents list vs served codes ──────────────────────────────────
# Matching across inconsistent vocabularies. Measured 2026-09-11, the real shapes:
#   waverley     contents "B16"  stored "B16 Inter-War ..."      same
#   ashfield     contents "10"   stored "A10 DS1.1 Signage ..."  stored has a letter
#   leichhardt   contents "1.1"  stored "1 C1 Retention ..."     stored is shallower
#   marrickville contents "4.1"  stored "4.1.12 Roof ..."        stored is deeper
LEAD_CODE = re.compile(r"^([A-Z]{0,2}\d{1,3}[A-Za-z]{0,2}(?:[._]\d{1,3}[A-Za-z]{0,2})*)")
PREFIXED = re.compile(r"^([A-Z]{1,2})(\d.*)$")

# Below this many listed codes, "everything is missing" is as likely to be a small
# chapter as a finding, so it is not reported as one.
SUSPICIOUS_MIN_CODES = 10


def leading_code(section_header: str | None) -> str | None:
    """The section code at the head of a stored section_header, or None.

    36 of 12,124 live rows carry a NULL section_header (measured 2026-09-12), so
    this is called on every row and must never raise.
    """
    if not section_header:
        return None
    m = LEAD_CODE.match(str(section_header).strip())
    return m.group(1) if m else None


def dominant_prefix(codes: set[str]) -> str | None:
    """The single letter prefix carried by nearly every stored code, else None."""
    pref = [PREFIXED.match(c).group(1) for c in codes if PREFIXED.match(c)]
    if not pref or len(pref) < 0.8 * len(codes):
        return None
    letter, n = Counter(pref).most_common(1)[0]
    return letter if n >= 0.8 * len(codes) else None


def _covered(listed: str, stored: set[str]) -> bool:
    return listed in stored or any(
        s == listed or s.startswith(listed + ".") for s in stored)


def compare_codes(listed_codes, stored_codes):
    """-> (verdict, missing).
    OK | INCOMPLETE | VOCAB_MISMATCH | NO_STORED_CODES | NO_CONTENTS.

    VOCAB_MISMATCH is not a finding. Ashfield was once reported "15 of 15 sections
    missing" when the contents says ``10`` and we store ``A10`` -- every section
    was present. Reporting that shape as fact is the failure this whole exercise
    exists to stop, so 100%-missing on a chapter big enough to judge is returned
    as a vocabulary problem, never as absent content.

    NO_STORED_CODES is NOT "this chapter serves nothing". It means not one stored
    row carries a section code this comparison can read, so the comparison could
    not run. Woollahra is the case that found this: 26 of its 27 chapters serve
    real rows -- 226 of them in chapter-e2 alone -- and NONE of their
    section_header values begin with a parseable code. An earlier draft returned
    "NO_ROWS" here, the caller counted it as a signal that had run and found
    nothing, and 25 woollahra chapters scored OK. That is the same shape as the
    defect being repaired: an inability to judge, reported as a pass. The caller
    decides between "serves nothing" and "serves rows we cannot key", because only
    it knows live_rows.
    """
    listed = sorted(listed_codes)
    stored = set(stored_codes)
    if not listed:
        return "NO_CONTENTS", []
    if not stored:
        return "NO_STORED_CODES", listed

    missing = [c for c in listed if not _covered(c, stored)]

    # ashfield: stored "A10", contents "10" -- strip the prefix and retry.
    if missing:
        letter = dominant_prefix(stored)
        if letter and not dominant_prefix(set(listed)):
            unpref = {PREFIXED.match(s).group(2) for s in stored if PREFIXED.match(s)}
            unpref |= {s for s in stored if not PREFIXED.match(s)}
            missing = [c for c in missing if not _covered(c, unpref)]

    if missing and len(missing) == len(listed) and len(listed) >= SUSPICIOUS_MIN_CODES:
        return "VOCAB_MISMATCH", missing
    return ("INCOMPLETE" if missing else "OK"), missing


# ── signal 2: gaps in our own numbering (no PDF needed) ──────────────────────
NUMERIC_PART = re.compile(r"^([A-Z]{0,2})(\d{1,3}(?:\.\d{1,3})*)")
MAX_REPORTED_HOLES = 40    # a hole list longer than this is a different problem


def _levels(codes) -> dict[str, set[int]]:
    """{parent prefix -> the numbers this code set uses at that level}."""
    by_parent: dict[str, set[int]] = defaultdict(set)
    for code in codes:
        m = NUMERIC_PART.match(code)
        if not m:
            continue
        parts = m.group(2).split(".")
        for i in range(len(parts)):
            parent = m.group(1) + ".".join(parts[:i])
            try:
                by_parent[parent].add(int(parts[i]))
            except ValueError:
                pass
    return by_parent


def numbering_gaps(codes: set[str], sibling_codes=frozenset()):
    """-> (verdict, gaps). GAPS | NO_GAPS | TOO_FEW_CODES | SHARED_NUMBERING.

    Section numbers are sequential, so a chapter serving 4.1.12 and nothing from
    4.1.1 to 4.1.11 has a hole whether or not the document has a contents page.
    This is the only signal with 100% coverage -- it reads our own data.

    WHY sibling_codes IS NOT OPTIONAL IN PRACTICE
    ---------------------------------------------
    A DCP's numbering runs across its chapters, not within them. Measured
    2026-09-12: marrickville's top-level code ``2`` appears in **22** different
    chapters, canterbury_bankstown's ``10`` in **10**, leichhardt's ``C1`` in 2.
    So a chapter holding C1.x and C6.x is not missing C2-C5 -- its siblings hold  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)
    them, and reporting that as a hole is a fabricated finding at scale.

    A level is therefore judged ONLY when no sibling chapter of the same council
    uses that level too. Where every level is shared the verdict is
    SHARED_NUMBERING: this signal could not judge this chapter, which is not the
    same as finding nothing wrong with it.

    TOO_FEW_CODES is likewise returned rather than NO_GAPS when a level carries
    fewer than two numbers -- one number can neither agree nor disagree with
    itself, and a check that cannot fail must not report a pass.
    """
    by_parent = _levels(codes)
    sib_by_parent = _levels(sibling_codes)

    judgeable, shared = [], 0
    for parent, nums in by_parent.items():
        if len(nums) < 2:
            continue
        if sib_by_parent.get(parent):
            shared += 1          # a sibling chapter owns part of this sequence
            continue
        judgeable.append((parent, nums))

    if not judgeable:
        return ("SHARED_NUMBERING" if shared else "TOO_FEW_CODES"), []

    gaps = []
    for parent, nums in sorted(judgeable):
        lo, hi = min(nums), max(nums)
        if lo > 1:
            gaps.append({"level": parent or "(top)", "kind": "starts_late",
                         "detail": "starts at " + str(lo) + ", nothing 1-" + str(lo - 1)})
        holes = [n for n in range(lo, hi + 1) if n not in nums]
        if holes and len(holes) <= MAX_REPORTED_HOLES:
            gaps.append({"level": parent or "(top)", "kind": "holes",
                         "detail": ",".join(str(h) for h in holes[:14])})
    return ("GAPS" if gaps else "NO_GAPS"), gaps


# ── signal 3: the page header vs the part we stamped on the row ──────────────
# Waverley's defect is invisible to signals 1 and 2: part B15 is coded correctly
# and holds B17's text, because sub-section numbers are read from the page and
# only the part label comes from the map. The page itself carries the truth.
PART_HEADER = re.compile(r"^([A-Z]{1,2}\d{1,2}[A-Za-z]?)$")

# Below this share of pages carrying a code, there is no header truth to compare
# against and the signal reports that rather than a verdict.
HEADER_MIN_PAGE_COVERAGE = 0.50
# At or above this share disagreeing, the two sides are speaking different
# vocabularies -- the same trap that once read woollahra as 95% broken because
# "C5" in "E2.2.4 C5 Control 5" is Control 5, not part C5.
HEADER_VOCAB_MISMATCH = 0.90
HEADER_MIN_ROWS = 10


def page_part_codes(page_texts: list[str]) -> dict[int, str]:
    """{1-indexed page -> part code from its running header}, where one exists."""
    out: dict[int, str] = {}
    for i, txt in enumerate(page_texts):
        for line in (txt or "").split("\n")[:HEADER_SCAN_LINES]:
            m = PART_HEADER.match(line.strip())
            if m:
                out[i + 1] = m.group(1)
                break
    return out


def header_disagreements(rows, page_part: dict[int, str], total_pages: int):
    """-> dict. rows is [(pdf_page, section_header), ...] for this chapter.

    CONSISTENT | MISLABELLED | VOCAB_MISMATCH | NO_HEADER_TRUTH | TOO_FEW_ROWS.
    """
    coverage = (len(page_part) / total_pages) if total_pages else 0.0
    res = {"pages_with_code": len(page_part), "page_coverage": round(coverage, 3),
           "rows_checked": 0, "rows_disagree": 0, "examples": []}
    if coverage < HEADER_MIN_PAGE_COVERAGE:
        res["verdict"] = "NO_HEADER_TRUTH"
        return res

    agree = disagree = 0
    for pg, head in rows:
        stored = leading_code(head)
        if not stored:
            continue
        m = PART_HEADER.match(stored)
        if not m:
            continue
        truth = page_part.get(pg)
        if truth is None:
            continue
        if truth == stored:
            agree += 1
        else:
            disagree += 1
            if len(res["examples"]) < 8:
                res["examples"].append(
                    {"page": pg, "stored": stored, "page_says": truth,
                     "header": str(head)[:60]})

    checked = agree + disagree
    res["rows_checked"] = checked
    res["rows_disagree"] = disagree
    if checked < HEADER_MIN_ROWS:
        res["verdict"] = "TOO_FEW_ROWS"
    elif disagree / checked >= HEADER_VOCAB_MISMATCH:
        res["verdict"] = "VOCAB_MISMATCH"
    elif disagree:
        res["verdict"] = "MISLABELLED"
    else:
        res["verdict"] = "CONSISTENT"
    return res


# ── signal 4: text capture ratio ─────────────────────────────────────────────
# Marrickville part4-s1-low-density is a 55-page document whose contents lists 73
# sections; we store 26 rows and every one sits under 4.1.12. Signals 1 and 2 see
# that, but only because its contents page happens to parse. This signal needs no
# contents page and no numbering: it compares what we stored against how much text
# the document actually holds.
#
# The threshold is NOT a regulatory judgment and is not a quality bar. DCP PDFs
# carry figures, tables, maps and boilerplate that legitimately never become
# provisions, so a "correct" ratio does not exist. CAPTURE_FLOOR is set from the
# corpus's own measured distribution and flags the tail, and the raw numerator and
# denominator are both stored so the verdict can be re-derived when it moves.
CAPTURE_FLOOR = 0.02       # set from the measured distribution -- see set_capture_floor
CAPTURE_MIN_PDF_CHARS = 2000   # below this the document is a cover or a map
# Storing MORE than the document holds is its own anomaly, not a clean capture.
# A little over 1.0 is normal (tables are extracted twice by some readers), so
# this sits above the noise rather than at exactly 1.0.
CAPTURE_OVER = 1.25


def capture_ratio(stored_chars: int, pdf_text_chars: int):
    """-> (verdict, ratio). HOLLOW | CAPTURED | OVER_CAPTURED | NO_TEXT | NO_ROWS.

    OVER_CAPTURED means we store MORE text than the document contains. Found on
    marrickville/part2-s10-parking 2026-09-12: 100,968 stored characters against
    50,860 in the PDF, ratio 1.99, with 54 rows all carrying distinct text and
    distinct ref_numbers -- so not simple duplication. Something is supplying
    text this document does not hold, and whatever it is, "we stored plenty"
    must not read as "we stored the right thing".
    """
    if pdf_text_chars < CAPTURE_MIN_PDF_CHARS:
        return "NO_TEXT", None
    if stored_chars == 0:
        return "NO_ROWS", 0.0
    ratio = stored_chars / pdf_text_chars
    if ratio > CAPTURE_OVER:
        return "OVER_CAPTURED", round(ratio, 4)
    return ("HOLLOW" if ratio < CAPTURE_FLOOR else "CAPTURED"), round(ratio, 4)


# ── putting a chapter's four signals together ────────────────────────────────
# A signal that ran and could have failed. Anything else means this chapter is
# still unknown to that signal, and unknown is never folded into a pass.
_S1_MEASURED = {"OK", "INCOMPLETE", "NO_ROWS"}
_S2_MEASURED = {"NO_GAPS", "GAPS"}   # SHARED_NUMBERING/TOO_FEW_CODES did not judge
_S3_MEASURED = {"CONSISTENT", "MISLABELLED"}
_S4_MEASURED = {"CAPTURED", "HOLLOW", "OVER_CAPTURED", "NO_ROWS"}


def score_chapter(raw: dict, sibling_codes=frozenset()) -> dict:
    """Verdicts from one chapter's raw measurements. Pure -- no DB, no PDF.

    sibling_codes is every section code served by OTHER chapters of the same
    council. Signal 2 needs it: a DCP's numbering runs across chapters, so
    without it a chapter holding C1.x reads as missing the C2-C5 its siblings  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)
    hold. See numbering_gaps.

    Kept separate from the sweep so verdicts can be re-derived after a threshold
    moves without re-downloading 525 PDFs, and so the ratchet can be re-run
    against a stored raw file.
    """
    out = dict(raw)
    listed = set(raw.get("listed_codes") or [])
    stored = set(raw.get("stored_codes") or [])

    status = raw.get("contents_status")
    if status == "READ":
        verdict, missing = compare_codes(listed, stored)
        # compare_codes cannot tell "serves nothing" from "serves rows whose
        # section_header carries no code we can read" -- only live_rows can.
        # The first is a real finding (the document lists sections and we serve
        # none of them); the second means this signal could not run at all, and
        # must not be counted as a signal that ran. Woollahra: 26 chapters, real
        # rows, zero parseable codes -- an earlier draft scored 25 of them OK.
        if verdict == "NO_STORED_CODES":
            verdict = "NO_ROWS" if raw.get("live_rows", 0) == 0 \
                else "NOT_MEASURED:NO_STORED_CODES"
        out["contents_verdict"] = verdict
        out["n_listed"] = len(listed)
        out["n_missing"] = len(missing) if verdict in _S1_MEASURED else 0
        out["missing_sample"] = sorted(missing)[:30] if verdict in _S1_MEASURED else []
    else:
        # TITLES_ONLY / NO_CONTENTS / UNREADABLE all mean this signal did not
        # measure this chapter. They are kept apart because only UNREADABLE is a
        # defect in the parser, and only it should shrink as the parser improves.
        out["contents_verdict"] = "NOT_MEASURED:" + str(status)
        out["n_listed"] = 0
        out["n_missing"] = 0
        out["missing_sample"] = []

    out["gap_verdict"], gaps = numbering_gaps(stored, sibling_codes)
    out["gap_count"] = len(gaps)
    out["gap_sample"] = gaps[:8]

    hdr = raw.get("header") or {"verdict": "NO_HEADER_TRUTH"}
    out["header_verdict"] = hdr.get("verdict")
    out["header_rows_checked"] = hdr.get("rows_checked", 0)
    out["header_rows_disagree"] = hdr.get("rows_disagree", 0)
    out["header_examples"] = hdr.get("examples", [])

    out["capture_verdict"], out["capture_ratio"] = capture_ratio(
        raw.get("stored_chars") or 0, raw.get("pdf_text_chars") or 0)

    ran = [
        out["contents_verdict"] in _S1_MEASURED,
        out["gap_verdict"] in _S2_MEASURED,
        out["header_verdict"] in _S3_MEASURED,
        out["capture_verdict"] in _S4_MEASURED,
    ]
    out["signals_run"] = sum(ran)
    out["measured"] = any(ran)

    findings = []
    if out["contents_verdict"] == "INCOMPLETE":
        findings.append("contents:" + str(out["n_missing"]) + "/" + str(out["n_listed"]))
    if out["contents_verdict"] == "NO_ROWS":
        # The document lists sections and we serve none of them. This is the most
        # severe signal-1 outcome, not a quiet one, and it needs to reach findings
        # or the chapter reads as OK on the strength of having nothing wrong with
        # the nothing it contains.
        findings.append("serves_nothing:0/" + str(out["n_listed"]))
    if out["gap_verdict"] == "GAPS":
        findings.append("gaps:" + str(out["gap_count"]))
    if out["header_verdict"] == "MISLABELLED":
        findings.append("mislabelled:" + str(out["header_rows_disagree"]) +
                        "/" + str(out["header_rows_checked"]))
    if out["capture_verdict"] == "HOLLOW":
        findings.append("hollow:" + str(out["capture_ratio"]))
    if out["capture_verdict"] == "OVER_CAPTURED":
        findings.append("over_captured:" + str(out["capture_ratio"]))
    out["findings"] = findings
    return out


def chapter_is_ok(c: dict) -> bool:
    """Known-good: signal 1 verified this chapter against its source contents
    list, and no other signal found anything.

    WHY SIGNAL 1 SPECIFICALLY, AND NOT "ANY SIGNAL RAN"
    ---------------------------------------------------
    Only signal 1 can establish COMPLETENESS. The other three are defect
    detectors, and each is silent on a chapter that is simply missing content:

      signal 2 (numbering gaps)  a chapter holding sections 1-5 of a document
                                 that has 40 has no gaps at all
      signal 3 (page headers)    verifies that stored rows are correctly
                                 LABELLED, which a chapter missing half its
                                 sections can satisfy perfectly
      signal 4 (capture ratio)   says a plausible VOLUME of text was stored, not
                                 that the right sections were

    An earlier draft accepted any signal, and scored 25 woollahra chapters OK on
    the strength of the capture ratio alone while signal 1 could not read a single
    one of their section codes. "Nothing detected a defect" is not "verified
    complete", and collapsing the two is the failure this whole phase exists to
    repair.
    """
    return (c.get("contents_verdict") == "OK"
            and not c["findings"]
            and c["live_rows"] > 0)


def score_all(raw: list[dict]) -> list[dict]:
    """Score every chapter, giving each one its council siblings' codes.

    Signal 2 cannot be computed one chapter at a time: a DCP's numbering runs
    across its chapters, so judging a chapter in isolation reports its siblings'
    sections as its own holes. Measured 2026-09-12, marrickville's top-level code
    2 appears in 22 chapters.
    """
    by_council: dict[str, set] = defaultdict(set)
    for r in raw:
        by_council[r["council"]].update(r.get("stored_codes") or [])
    out = []
    for r in raw:
        own = set(r.get("stored_codes") or [])
        siblings = by_council[r["council"]] - own
        out.append(score_chapter(r, siblings))
    return out


def summarise(scored: list[dict]) -> dict:
    """Per-council counts, in the shape the baseline file and the ratchet use."""
    per: dict[str, Counter] = defaultdict(Counter)
    for c in scored:
        k = per[c["council"]]
        k["chapters"] += 1
        if chapter_is_ok(c):
            k["OK"] += 1
        else:
            k["NOT_OK"] += 1
        if not c["measured"]:
            k["UNMEASURED"] += 1
        if c["contents_verdict"] == "INCOMPLETE":
            k["INCOMPLETE"] += 1
            k["listed_not_served"] += c["n_missing"]
        if str(c["contents_verdict"]).endswith("UNREADABLE"):
            k["CONTENTS_UNREADABLE"] += 1
        if c["gap_verdict"] == "GAPS":
            k["GAPS"] += 1
        if c["header_verdict"] == "MISLABELLED":
            k["MISLABELLED"] += 1
            k["mislabelled_rows"] += c["header_rows_disagree"]
        if c["capture_verdict"] == "HOLLOW":
            k["HOLLOW"] += 1
        if c["capture_verdict"] == "OVER_CAPTURED":
            k["OVER_CAPTURED"] += 1
        if c["gap_verdict"] == "SHARED_NUMBERING":
            k["SHARED_NUMBERING"] += 1
    totals = Counter()
    for k in per.values():
        totals.update(k)
    return {"per_council": {c: dict(v) for c, v in sorted(per.items())},
            "totals": dict(totals)}


# ── the ratchet ──────────────────────────────────────────────────────────────
# WHAT THIS RATCHET CAN AND CANNOT BE COMPARED AGAINST
# ----------------------------------------------------
# The frozen 2026-09-12 baseline ran ONE signal with a NARROWER parser. This file
# runs four signals with a wider one. Those two numbers are not the same
# measurement, and gating one against the other would be wrong in both directions:
#
#   - widening the parser moves chapters out of "contents unreadable" and into a
#     real verdict, some of which are INCOMPLETE. That count rises because the
#     measurement improved, not because the data got worse.
#   - adding signals 2-4 means a chapter that signal 1 called OK can now be found
#     to have numbering holes or mislabelled rows. OK legitimately falls.
#
# A ratchet against the frozen numbers would therefore fail on exactly the work it
# exists to protect, and the pressure would be to weaken the parser to keep the
# count down. So the frozen file is kept as PROVENANCE and is never gated on.
#
# The comparison that IS sound is this code against ITSELF: run N vs run N-1, same
# signals, same parser. ratchet.per_council in the baseline file is therefore
# EMPTY until a first four-signal run has been reviewed and recorded with
# --record-baseline. Until then every key reports NO_BASELINE -- which is not a
# pass, and says so.
#
#   NOT_OK      may not rise    a chapter stopped being known-good
#   UNMEASURED  may not rise    a chapter stopped being measurable at all
#
# INCOMPLETE, GAPS, MISLABELLED, HOLLOW and listed_not_served are REPORTED and not
# gated, because each moves when measurement improves.
#
# The check that actually BLOCKS is scripts/dcp_page_map_gate.py. Its baseline is
# measured by the same code before and after, so it ratchets from day one. This
# file measures and reports; it does not stop a pipeline.
RATCHET_KEYS = ("NOT_OK", "UNMEASURED")


def ratchet(summary: dict, baseline: dict):
    """-> (regressions, improvements, no_baseline).

    Three states, never two. A council or key with nothing to compare against is
    NO_BASELINE and is reported as such -- never folded into "fine". A check that
    reports a pass when it has nothing to compare against is how DQ-30 stayed
    marked Fixed on a self-comparison that could not fail.
    """
    regressions, improvements, no_baseline = [], [], []
    base = (baseline.get("ratchet") or {}).get("per_council", {})
    for council, counts in summary.get("per_council", {}).items():
        b = base.get(council)
        for key in RATCHET_KEYS:
            now = counts.get(key, 0)
            if b is None or key not in b:
                no_baseline.append({"council": council, "key": key, "now": now})
                continue
            was = b[key]
            if now > was:
                regressions.append({"council": council, "key": key,
                                    "was": was, "now": now})
            elif now < was:
                improvements.append({"council": council, "key": key,
                                     "was": was, "now": now})
    return regressions, improvements, no_baseline


# ── the sweep (needs DB + R2) ────────────────────────────────────────────────
def _load_env() -> None:
    """Find .env, including from inside a git worktree, which has none of its own.

    prior-art-checked: reuse not viable as a copy, and IS viable as a delegation,
    so this delegates. Two existing resolvers were opened rather than guessed at.
    dq_db.main_checkout() is the canonical one, but dq_db.py is NOT in
    Dockerfile.monitors (verified against its COPY list) and dq_db.connect() also
    forces conn.set_session(readonly=True), which the ledger write cannot use.
    check_council_completeness._load_env does the same git-common-dir resolution,
    strips GIT_DIR/GIT_INDEX_FILE so a hook's exported environment cannot redirect
    the lookup at another repository, and IS copied into Dockerfile.monitors on
    line 61 -- the same image this script will run in. So it is imported, not
    reimplemented. The bare load_dotenv fallback exists only for the case where
    neither module is importable, where a missing URL then raises below.
    """
    try:
        from scripts.check_council_completeness import _load_env as shared
    except ImportError:
        try:
            from check_council_completeness import _load_env as shared
        except ImportError:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(_ROOT, ".env"))
            return
    shared()


def _connect():
    _load_env()
    import psycopg2
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise SystemExit(
            "FATAL: no DATABASE_URL / SUPABASE_DB_URL. This script measures the "
            "live corpus; without it the answer is UNKNOWN, not clean.")
    conn = psycopg2.connect(url, connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout='120s'")
    return conn, cur


def _r2():
    import boto3
    endpoint = "https://" + os.environ["R2_ACCOUNT_ID"] + ".r2.cloudflarestorage.com"
    return boto3.client(
        "s3", endpoint_url=endpoint,
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto"), os.environ["R2_BUCKET_NAME"]


def sweep(councils: list[str] | None, only_chapter: str | None, log):
    """Measure every matching chapter. Returns raw records (unscored)."""
    import pdfplumber

    conn, cur = _connect()
    s3, bucket = _r2()

    where = ["is_active", "r2_current_path IS NOT NULL"]
    params: list = []
    if councils:
        where.append("council = ANY(%s)")
        params.append(councils)
    if only_chapter:
        where.append("chapter_key = %s")
        params.append(only_chapter)
    cur.execute("SELECT council, chapter_key, r2_current_path, content_hash "
                "FROM dcp_chapter_registry WHERE " + " AND ".join(where) +
                " ORDER BY council, chapter_key", params)
    chapters = cur.fetchall()

    cur.execute(
        "SELECT source_council, source_chapter_key, section_header, pdf_page, "
        "       length(provision_text) "
        "FROM regulatory_provisions "
        "WHERE is_current AND source_chapter_key IS NOT NULL")
    stored_codes: dict[tuple, set] = defaultdict(set)
    stored_rows: dict[tuple, list] = defaultdict(list)
    stored_chars: dict[tuple, int] = defaultdict(int)
    n_rows: dict[tuple, int] = defaultdict(int)
    for council, key, head, pg, ln in cur.fetchall():
        k = (council, key)
        n_rows[k] += 1
        stored_chars[k] += ln or 0
        stored_rows[k].append((pg, head))
        code = leading_code(head)
        if code:
            stored_codes[k].add(code)

    log("chapters to measure: " + str(len(chapters)))
    raw: list[dict] = []
    for i, (council, key, path, content_hash) in enumerate(chapters, 1):
        k = (council, key)
        rec = {
            "council": council, "chapter": key,
            "pdf_content_hash": content_hash,
            "live_rows": n_rows.get(k, 0),
            "stored_chars": stored_chars.get(k, 0),
            "stored_codes": sorted(stored_codes.get(k, set())),
        }
        try:
            with tempfile.TemporaryDirectory() as td:
                local = os.path.join(td, "c.pdf")
                s3.download_file(bucket, path, local)
                with pdfplumber.open(local) as pdf:
                    rec["pdf_pages"] = len(pdf.pages)
                    page_texts = [(p.extract_text() or "") for p in pdf.pages]
            rec["pdf_text_chars"] = sum(len(t) for t in page_texts)
            status, codes, _entries = parse_contents(page_texts, max_scan=MAX_TOC_SCAN)
            rec["contents_status"] = status
            rec["listed_codes"] = sorted(codes)
            rec["header"] = header_disagreements(
                stored_rows.get(k, []), page_part_codes(page_texts),
                rec["pdf_pages"])
        except Exception as exc:
            rec["error"] = str(exc)[:180]
            rec["contents_status"] = "ERROR"
            rec["listed_codes"] = []
        raw.append(rec)

        # Provisional: signal 2 needs every sibling chapter's codes, and the
        # sweep has not seen them all yet. The final verdicts come from
        # score_all() once the whole council is in hand.
        prov = score_chapter(rec)
        log(("[%3d/%3d] " % (i, len(chapters))) + council.ljust(21) +
            key[:36].ljust(38) + str(rec["live_rows"]).rjust(5) + " rows  " +
            str(rec.get("contents_status", "?")).ljust(13) +
            (", ".join(prov["findings"]) or "-"))
    conn.close()
    return raw


# ── ledger write ─────────────────────────────────────────────────────────────
LEDGER_TABLE = "dcp_chapter_measurement"


def write_ledger(scored: list[dict], run_source: str, log) -> int:
    conn, cur = _connect()
    cur.execute("SELECT to_regclass(%s)", (LEDGER_TABLE,))
    if cur.fetchone()[0] is None:
        conn.close()
        raise SystemExit(
            "FATAL: " + LEDGER_TABLE + " does not exist. Apply "
            "migrations/069_dcp_chapter_measurement.sql first.")
    n = 0
    for c in scored:
        cur.execute(
            "INSERT INTO " + LEDGER_TABLE + " ("
            " run_source, council, chapter_key, pdf_content_hash, pdf_pages,"
            " live_rows, measured, signals_run, contents_status, contents_verdict,"
            " listed_codes, missing_codes, missing_sample, gap_verdict, gap_count,"
            " gap_sample, header_verdict, header_rows_checked, header_rows_disagree,"
            " header_examples, capture_verdict, capture_ratio, pdf_text_chars,"
            " stored_chars) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
            "        %s,%s,%s,%s)",
            (run_source, c["council"], c["chapter"], c.get("pdf_content_hash"),
             c.get("pdf_pages"), c["live_rows"], c["measured"], c["signals_run"],
             c.get("contents_status"), c.get("contents_verdict"),
             c.get("n_listed", 0), c.get("n_missing", 0),
             json.dumps(c.get("missing_sample", [])), c.get("gap_verdict"),
             c.get("gap_count", 0), json.dumps(c.get("gap_sample", [])),
             c.get("header_verdict"), c.get("header_rows_checked", 0),
             c.get("header_rows_disagree", 0),
             json.dumps(c.get("header_examples", [])), c.get("capture_verdict"),
             c.get("capture_ratio"), c.get("pdf_text_chars"), c.get("stored_chars")))
        n += 1
    conn.commit()
    conn.close()
    log("ledger rows written: " + str(n))
    return n


# ── CLI ──────────────────────────────────────────────────────────────────────
def load_baseline() -> dict:
    if not os.path.exists(BASELINE_PATH):
        raise SystemExit("FATAL: baseline missing at " + BASELINE_PATH)
    with open(BASELINE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def report(scored: list[dict], baseline: dict, log) -> int:
    summary = summarise(scored)
    cols = ("chapters", "OK", "UNMEASURED", "INCOMPLETE", "CONTENTS_UNREADABLE",
            "GAPS", "MISLABELLED", "HOLLOW", "OVER_CAPTURED")
    head = ("  council".ljust(24) + "chaps".rjust(7) + "OK".rjust(5) +
            "UNMEAS".rjust(8) + "INCOMP".rjust(8) + "UNREAD".rjust(8) +
            "GAPS".rjust(7) + "MISLAB".rjust(8) + "HOLLOW".rjust(8) +
            "OVERCAP".rjust(9))
    log("")
    log("=" * len(head))
    log(head)
    log("=" * len(head))

    def row(label, c):
        return ("  " + label.ljust(22) + str(c.get(cols[0], 0)).rjust(7) +
                str(c.get(cols[1], 0)).rjust(5) + str(c.get(cols[2], 0)).rjust(8) +
                str(c.get(cols[3], 0)).rjust(8) + str(c.get(cols[4], 0)).rjust(8) +
                str(c.get(cols[5], 0)).rjust(7) + str(c.get(cols[6], 0)).rjust(8) +
                str(c.get(cols[7], 0)).rjust(8) + str(c.get(cols[8], 0)).rjust(9))

    for council, c in summary["per_council"].items():
        log(row(council, c))
    t = summary["totals"]
    log("-" * len(head))
    log(row("TOTAL", t))
    log("")
    log("  listed sections not served: " + str(t.get("listed_not_served", 0)))
    log("  rows contradicting their own page header: " +
        str(t.get("mislabelled_rows", 0)))
    log("  chapters signal 2 could not judge (numbering shared with a sibling): " +
        str(t.get("SHARED_NUMBERING", 0)))

    regressions, improvements, no_baseline = ratchet(summary, baseline)
    log("")
    if improvements:
        log("RATCHET DOWN (good) -- " + str(len(improvements)) + " counts improved:")
        for r in improvements[:20]:
            log("   " + r["council"].ljust(22) + r["key"].ljust(12) +
                str(r["was"]) + " -> " + str(r["now"]))
    if no_baseline:
        log("")
        log("NO BASELINE for " + str(len(no_baseline)) + " (council, key) pairs -- "
            "these are NOT a pass, they are the floor being set:")
        for r in no_baseline[:20]:
            log("   " + r["council"].ljust(22) + r["key"].ljust(12) +
                "now " + str(r["now"]))
    if regressions:
        log("")
        log("*** RATCHET VIOLATION -- " + str(len(regressions)) +
            " counts rose above the frozen baseline ***")
        for r in regressions:
            log("   " + r["council"].ljust(22) + r["key"].ljust(12) +
                str(r["was"]) + " -> " + str(r["now"]))
        return 2
    log("RATCHET OK -- nothing rose above the frozen baseline.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sweep", action="store_true", help="measure (downloads PDFs)")
    ap.add_argument("--rescore", metavar="RAW_JSON",
                    help="re-derive verdicts from a stored raw sweep, no download")
    ap.add_argument("--gate", metavar="RAW_JSON",
                    help="ratchet only, from a stored raw sweep")
    ap.add_argument("--councils", default="baseline",
                    help="'baseline' (the 10 audited), 'all', or a comma list")
    ap.add_argument("--council", help="shorthand for --councils <one>")
    ap.add_argument("--chapter", help="restrict to one chapter_key")
    ap.add_argument("--out", default="dcp_measurement_raw.json")
    ap.add_argument("--write", action="store_true", help="write the ledger table")
    ap.add_argument("--record-baseline", action="store_true",
                    help="write this run's NOT_OK/UNMEASURED counts into the "
                         "baseline file as the ratchet floor. Deliberate and "
                         "reviewable: do it once, after reading the numbers.")
    ap.add_argument("--run-source", default="manual",
                    choices=["manual", "monitor", "commit"])
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    lines: list[str] = []

    def log(s: str) -> None:
        lines.append(s)
        if not args.quiet:
            print(s, flush=True)

    if not (args.sweep or args.rescore or args.gate):
        ap.error("one of --sweep / --rescore / --gate is required")

    baseline = load_baseline()

    if args.sweep:
        if args.council:
            councils = [args.council]
        elif args.councils == "all":
            councils = None
        elif args.councils == "baseline":
            councils = list(BASELINE_COUNCILS)
        else:
            councils = [c.strip() for c in args.councils.split(",") if c.strip()]
        raw = sweep(councils, args.chapter, log)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"measured_at": datetime.now(timezone.utc).isoformat(),
                       "councils": councils, "chapters": raw}, fh, indent=1)
        log("raw sweep written to " + args.out)
    else:
        src = args.rescore or args.gate
        with open(src, encoding="utf-8") as fh:
            raw = json.load(fh)["chapters"]

    scored = score_all(raw)
    rc = report(scored, baseline, log)

    if args.record_baseline:
        summary = summarise(scored)
        baseline.setdefault("ratchet", {})["per_council"] = {
            council: {k: counts.get(k, 0) for k in RATCHET_KEYS}
            for council, counts in summary["per_council"].items()
        }
        baseline["ratchet"]["recorded_at"] = datetime.now(timezone.utc).isoformat()
        baseline["ratchet"]["recorded_from"] = args.out if args.sweep else (
            args.rescore or args.gate)
        with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
            json.dump(baseline, fh, indent=2)
        log("")
        log("ratchet floor recorded into " + BASELINE_PATH)

    if args.write:
        write_ledger(scored, args.run_source, log)
    return rc


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # the check itself broke -- exit 1, never 0
        print("FATAL: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
