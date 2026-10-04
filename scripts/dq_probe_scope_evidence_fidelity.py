#!/usr/bin/env python3
# prior-art-checked: reuses verify_extraction_fidelity._norm and its
# whole-chapter grounding approach rather than reimplementing. Sweeps 2026-10-03
# on origin/main 251b60ba: scripts/dcp_fidelity_gate.py grades pending
# dcp_review_queue ROWS and writes a verdict onto them;
# scripts/verify_extraction_fidelity.py reports fidelity on committed
# regulatory_provisions; scripts/citation_proof.py proves a clause NUMBER. None
# of the three reads enrichment/config, and scope_evidence is not a provision,
# not a queue row and not a clause number -- it is a claim written in a Python
# file about what a PDF says. scripts/dq_probe_applicability_config.py (DQ-115)
# counts whether that claim EXISTS; nothing tests whether it is TRUE.
"""Check every scope_evidence quote against the chapter PDF it cites.

WHY THIS EXISTS
---------------
DQ-115 requires a declared applicability key to carry the council's own sentence
as data. It counts the string. It cannot tell a transcription from an invention,
so the ~160 quotes now in enrichment/config rest entirely on whoever typed them
-- and transcription errors were made and caught in the session that wrote the
first half of them. A hard filter on what a property is shown, resting on a
quote nobody checked, is the same defect DQ-115 exists to remove, one level up.

So this asks the fidelity gate's question of the config: are these words in that
document?

WHAT A VERDICT MEANS
--------------------
  OK          the quoted span appears in the chapter PDF
  MISSING     the span does NOT appear -- the quote is wrong, or paraphrased
              without being marked as abridged, or cites the wrong chapter
  UNRESOLVED  the entry could not be tied to a single registry chapter with a
              public URL, or the PDF could not be read. NOT a pass: counted and
              printed separately, because "could not check" and "checked and
              clean" are the two states this whole effort exists to keep apart
  UNPARSED    a scope_evidence value with no quoted span in it at all, which
              DQ-115 would still count as evidence present

Exit 0 only when MISSING, UNRESOLVED and UNPARSED are all zero.

MATCHING IS LOOSE ON PUNCTUATION AND STRICT ON WORDS
----------------------------------------------------
Both sides are reduced to lowercase alphanumerics and single spaces before
comparison, because pdfplumber renders curly quotes, en dashes, ligatures and
line-broken hyphenation unpredictably and a verbatim claim should not fail on a
dash. The WORDS and their order must still match exactly, which is what
"verbatim" asserts. A span carrying an ellipsis or a [bracketed interpolation] is
split at those points and every fragment of 20+ characters must appear, so an
abridged quote is checked piecewise rather than waved through.

CHAPTER RESOLUTION NEVER GUESSES
--------------------------------
Four rules in order -- exact chapter_key, "<tail>-" prefix, the single whole-DCP
document (for a `parts` config, whose keys are section codes against one PDF),
then a unique substring. More than one candidate at any step returns None and
the entry is reported UNRESOLVED. Attaching a council's sentence to the wrong
chapter would be worse than leaving it unchecked.

COST
----
The query is one table and 0.08s. The cost is fetching ~111 distinct PDFs, so
they are cached on disk between runs (override with SCOPE_PDF_CACHE). The first
run is slow and this is deliberately NOT wired into pre-push.

Usage:
    python scripts/dq_probe_scope_evidence_fidelity.py
    python scripts/dq_probe_scope_evidence_fidelity.py --council waverley
    python scripts/dq_probe_scope_evidence_fidelity.py --verbose
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dq_db  # noqa: E402
from enrichment.config import COUNCIL_CONFIGS  # noqa: E402

FILTER_KEYS = ("applicable_zones", "applicable_dev_types")
BUCKETS = ("chapter_topics", "parts", "sections")

#: COUNCIL_CONFIGS key -> dcp_chapter_registry.council, where they differ.
#: Found by the pre-implementation value audit, not at runtime: the Warringah
#: config is registered under the PLAN's name while the registry uses the
#: COUNCIL's name, so without this every Warringah entry reports UNRESOLVED and
#: the probe would look clean while checking nothing.
COUNCIL_SLUG_OVERRIDE = {"warringah": "northern_beaches"}

#: Cached chapter PDFs. Re-fetching ~111 documents per run would make this
#: unusable; the cache is keyed by council and chapter so a chapter that is
#: re-published under the same key must be deleted from it by hand.
#:
#: IN-REPO AND GITIGNORED, on purpose. DQ-121 declares this path as its
#: `requires`, so dq_check.py reports UNKNOWN -- "could not run here, and that
#: is not evidence either way" -- instead of a red row on a machine that has
#: never fetched the PDFs. That is DQ-32's precedent: CI's python job has no
#: frontend-nextjs/node_modules, and reading could-not-look as found-something
#: turned main red on 2026-08-12. Override with SCOPE_PDF_CACHE.
CACHE = Path(os.environ.get("SCOPE_PDF_CACHE")
             or Path(__file__).resolve().parents[1] / ".cache" / "scope_pdfs")

#: A span shorter than this is a fragment, not a quotation: it would match almost
#: any planning document and report a false OK.
MIN_SPAN = 30
#: After an abridged quote is split, a fragment this short proves nothing and is
#: skipped rather than asserted.
MIN_FRAGMENT = 20
#: A tail this short matches too many chapter keys for a substring rule to mean
#: anything (Waverley's parts are single letters).
MIN_TAIL_FOR_CONTAINS = 4

#: The two patterns that are PROMISES about the document. See spans() for the
#: looser one that was removed and why.
#:   A: the house style this directory uses -- verbatim: '...'
#:   B: a quoted span that cites the page it came from -- '...' (PDF p167)
#: B is not optional: 12 of Waverley's 22 claims use it rather than `verbatim:`,
#: so without it the probe reported real, page-cited quotations as UNPARSED.
_VERBATIM = re.compile(r"verbatim[:,]?\s*['\"](?P<q>[^'\"]{%d,})" % MIN_SPAN)
_WITH_PAGE = re.compile(
    r"['\"](?P<q>[^'\"]{%d,})['\"]\s*\((?:PDF\s*)?p+\.?\s*\d+" % MIN_SPAN)

_SPLIT_ABRIDGED = re.compile(r"\.{3}|\[[^\]]*\]")


def loose(text: str) -> str:
    """Lowercase alphanumerics and single spaces — nothing else survives.

    Accents are FOLDED, not stripped. Waverley Part D2 prints "café" and the
    config quotes "cafe"; stripping the accent turned the document's word into
    "caf" and reported a correct quote as MISSING. unicodedata.normalize("NFKD")
    decomposes the character so the base letter survives the class filter, which
    is the same discipline as the dash and curly-quote folding below: the probe
    must be loose about how a glyph was encoded and strict about the words.
    """
    folded = unicodedata.normalize("NFKD", text or "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", folded.lower())).strip()


def spans(evidence: str) -> list[str]:
    """The `verbatim:` claims in one scope_evidence value, and only those.

    ONLY `verbatim:` counts. The first version also harvested any long
    single-quoted span, and measured 2026-10-03 that produced three kinds of
    false MISSING, none of them a defect in a config:

      1. OUR OWN PROSE. An apostrophe closes a quote, so "Penrith's own
         introductory Part ..." was extracted as the span "s own introductory
         Part ..." and asserted against the PDF.
      2. NEGATIVE CLAIMS. Several entries record that a chapter carries NO
         "land to which this Part applies" section. Quoting the absent thing is
         the whole point, and the probe demanded it be present.
      3. SECTION TITLES AND PATTERNS mentioned in passing.

    A probe that cries wolf gets switched off, so the rule is now exact:
    `verbatim:` is a promise that these words are in the document, and only
    promises are checked. Evidence that asserts a quotation without marking it
    is reported UNPARSED rather than guessed at.
    """
    found: list[str] = []
    for pattern in (_VERBATIM, _WITH_PAGE):
        for match in pattern.finditer(evidence or ""):
            quote = match.group("q").strip()
            if len(quote) < MIN_SPAN:
                continue
            lq = loose(quote)
            if not any(lq in loose(seen) or loose(seen) in lq for seen in found):
                found.append(quote)
    return found


def check_span(span: str, haystack: str) -> tuple[bool, str]:
    """Is this quoted span in the chapter text? Abridged quotes checked piecewise."""
    fragments = [f for f in _SPLIT_ABRIDGED.split(span) if len(f.strip()) >= MIN_FRAGMENT]
    for fragment in fragments or [span]:
        if loose(fragment) not in haystack:
            return False, fragment.strip()[:110]
    return True, ""


def load_registry(cur) -> dict[str, list[dict]]:
    """Chapters that have a public PDF, by council slug.

    Rows with r2_public_pdf_url NULL are excluded deliberately: 110 of 558 have
    none, and an entry pointing at one is UNRESOLVED rather than clean.
    """
    cur.execute("""SELECT council, chapter_key, r2_public_pdf_url, coalesce(page_end, 0)
                     FROM dcp_chapter_registry
                    WHERE r2_public_pdf_url IS NOT NULL""")
    reg: dict[str, list[dict]] = {}
    for council, key, url, pages in cur.fetchall():
        reg.setdefault(council.replace("-", "_").lower(), []).append(
            dict(key=key, url=url, pages=pages))
    return reg


def resolve(council_slug: str, entry_key: str, bucket: str,
            reg: dict[str, list[dict]]) -> dict | None:
    """Tie a config entry to exactly ONE registry chapter, or return None."""
    cands = reg.get(council_slug, [])
    if not cands:
        return None
    tail = re.sub(r"^chapter[_-]", "", entry_key.lower()).replace("_", "-")

    def bare(c: dict) -> str:
        return re.sub(r"^chapter-", "", c["key"].lower())

    exact = [c for c in cands if bare(c) == tail]
    if len(exact) == 1:
        return exact[0]
    prefixed = [c for c in cands if bare(c).startswith(tail + "-")]
    if len(prefixed) == 1:
        return prefixed[0]
    if bucket == "parts":
        # A `parts` config keys SECTION CODES against one whole-DCP document, so
        # this must come before the substring rule — "A" is a substring of most
        # chapter keys and would be ambiguous for every Waverley Part.
        whole = [c for c in cands if c["pages"] > 150]
        if len(whole) == 1:
            return whole[0]
        if len(cands) == 1:
            return cands[0]
    if len(tail) >= MIN_TAIL_FOR_CONTAINS:
        # Ku-ring-gai's config keys are "part_2_site_analysis" while its registry
        # keys carry a section prefix: "section-a-part-2-site-analysis".
        contained = [c for c in cands if tail in bare(c)]
        if len(contained) == 1:
            return contained[0]
    return None


def chapter_text(chapter: dict, council_slug: str) -> str | None:
    """Fetch (once) and return the whole chapter as loose text, or None.

    Grounds against the WHOLE chapter rather than the cited page, following
    verify_extraction_fidelity._chapter_text: a page number transcribed by hand
    is exactly the kind of claim this probe exists to distrust, and the fidelity
    question that matters is whether the words are in the council's document.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{council_slug}__{chapter['key']}.pdf".replace("/", "_")
    if not path.exists() or path.stat().st_size < 2000:
        try:
            subprocess.run(["curl", "-sS", "-f", "-L", "-o", str(path), chapter["url"]],
                           check=True, timeout=900)
        except (OSError, subprocess.SubprocessError):
            return None
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            text = loose(" ".join((p.extract_text() or "") for p in pdf.pages))
    except Exception:
        return None
    # A second reading, when PyMuPDF is installed. pdfplumber interleaves two-column pages
    # character by character (Canterbury-Bankstown 7.5 p6 reads 'T D C P o h l b'), so a sentence
    # the council printed reads as MISSING. PyMuPDF keeps each column's block intact. Appending it
    # can only turn a false MISSING into OK: a quote must still appear contiguously in ONE reading.
    try:
        import fitz  # PyMuPDF
        with fitz.open(str(path)) as doc:
            text += " " + loose(" ".join(page.get_text() for page in doc))
    except Exception:  # noqa: BLE001 - absent or unreadable: keep the pdfplumber reading alone
        pass
    return text


def elsewhere(span, council_slug, cited_key, reg, text_cache):
    """The council's OTHER chapter holding this span, or None.

    Only called on a miss, because it is expensive: a council can have forty
    chapters and each one is a download and a pdfplumber pass. Already-cached
    chapters are tried first so the common case (a plan-level sentence from an
    introduction chapter that something else already read) costs nothing.
    """
    candidates = [c for c in reg.get(council_slug, []) if c["key"] != cited_key]
    candidates.sort(key=lambda c: (council_slug, c["key"]) not in text_cache)
    for cand in candidates:
        cache_key = (council_slug, cand["key"])
        if cache_key not in text_cache:
            text_cache[cache_key] = chapter_text(cand, council_slug)
        hay = text_cache[cache_key]
        if hay and check_span(span, hay)[0]:
            return cand["key"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Check scope_evidence quotes against their PDFs")
    ap.add_argument("--council", help="limit to one COUNCIL_CONFIGS key")
    ap.add_argument("--verbose", action="store_true", help="print every OK span too")
    args = ap.parse_args()

    with dq_db.session() as conn:
        reg = load_registry(conn.cursor())

    seen_configs: set[int] = set()
    text_cache: dict[tuple[str, str], str | None] = {}
    ok = missing = unresolved = unparsed = inherited = 0
    problems: list[str] = []

    for cfg_key, config in COUNCIL_CONFIGS.items():
        if id(config) in seen_configs:
            continue  # aliases share one dict; counting by name double-counts
        seen_configs.add(id(config))
        if args.council and args.council != cfg_key:
            continue
        slug = (config.get("council") or cfg_key).replace("-", "_").lower()
        slug = COUNCIL_SLUG_OVERRIDE.get(slug, slug)
        for bucket in BUCKETS:
            for entry_key, entry in (config.get(bucket) or {}).items():
                if not isinstance(entry, dict):
                    continue
                evidence = entry.get("scope_evidence") or {}
                for fkey in FILTER_KEYS:
                    claim = evidence.get(fkey)
                    if not claim:
                        continue
                    where = f"{cfg_key}/{bucket}/{entry_key}/{fkey}"
                    quoted = spans(claim)
                    if not quoted:
                        unparsed += 1
                        problems.append(f"  UNPARSED   {where}: evidence carries no quotation")
                        continue
                    chapter = resolve(slug, entry_key, bucket, reg)
                    if chapter is None:
                        unresolved += 1
                        problems.append(f"  UNRESOLVED {where}: no single registry chapter "
                                        f"with a public PDF for {slug}/{entry_key}")
                        continue
                    cache_key = (slug, chapter["key"])
                    if cache_key not in text_cache:
                        text_cache[cache_key] = chapter_text(chapter, slug)
                    haystack = text_cache[cache_key]
                    if not haystack:
                        unresolved += 1
                        problems.append(f"  UNRESOLVED {where}: could not read "
                                        f"{chapter['key']}.pdf")
                        continue
                    for span in quoted:
                        good, bad = check_span(span, haystack)
                        if good:
                            ok += 1
                            if args.verbose:
                                print(f"  OK         {where}: {span[:80]}")
                            continue
                        # An INHERITED sentence legitimately lives in another
                        # chapter: Canterbury's chapter 1.1 carries "This DCP
                        # applies to land within the Canterbury-Bankstown Local
                        # Government Area", and 27 chapters cite it because they
                        # state no scope of their own. Calling that MISSING would
                        # be the probe misreading the config, so the council's
                        # other chapters are searched before a verdict is given
                        # -- and WHERE it was found is printed, so a quote
                        # attributed to the wrong chapter is still visible.
                        found_in = elsewhere(span, slug, chapter["key"], reg, text_cache)
                        if found_in:
                            inherited += 1
                            problems.append(
                                f"  ELSEWHERE  {where}\n"
                                f"             cited      : {chapter['key']}\n"
                                f"             found in   : {found_in}\n"
                                f"             quote      : {bad[:90]}")
                        else:
                            missing += 1
                            problems.append(f"  MISSING    {where}\n"
                                            f"             not in PDF : {bad}\n"
                                            f"             chapter    : {chapter['key']}")

    print("DQ-115f: `verbatim:` quotes checked against the council's own document")
    print(f"  spans OK   : {ok}")
    print(f"  MISSING    : {missing}   <- the words are nowhere in that council's PDFs")
    print(f"  ELSEWHERE  : {inherited}   <- real words, but in a chapter other than the "
          f"one cited (an inherited plan sentence, or a wrong citation)")
    print(f"  UNRESOLVED : {unresolved}   <- could not be checked; NOT a pass")
    print(f"  UNPARSED   : {unparsed}   <- evidence asserts a scope but marks no `verbatim:`")
    if problems:
        print()
        print("\n".join(problems))
    print("\n  means : DQ-115 counts whether a declaration carries a sentence. This checks "
          "whether that sentence is in the council's own document. A MISSING span is a hard "
          "filter on what a property is shown resting on words nobody wrote.")
    return 1 if (missing or unresolved or unparsed) else 0


if __name__ == "__main__":
    sys.exit(main())
