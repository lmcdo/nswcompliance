#!/usr/bin/env python3
# prior-art-checked: no existing script extracts commencement/adoption dates
# from the data/dcps PDFs (repo grep for 'came into effect'/'In Force'/
# commencement extractors, 2026-08-03; scripts/backfill_effective_date.py is
# the RETIRED version-label parser and must not be extended — campaign item 3
# explicitly bans it). This reads the documents' own statements verbatim.
"""Extract each DCP's own commencement/amendment statement into dcp_plan_as_at.

Output-grounding campaign item 3, evidence class 2 (``stated_*``). For every
local plan PDF in ``data/dcps/`` mapped below, scan its opening pages for an
explicit dated statement — "In Force 6 May 2022", "came into effect on
22 August 2024", a LIST OF AMENDMENTS "Date in Force" column — and store the
date, its precision, its kind and the VERBATIM line (with file + page) in
``dcp_plan_as_at.stated_*``.

Precision honesty: only explicit dated phrases are parsed. A file whose
statement pattern no longer matches is SKIPPED and reported — never guessed.
The 2026-08-03 survey of all 30 PDFs found statements in exactly the files
mapped below; the other files were scanned in full and carry none (their LGAs
fall back to the portal record or the registry observation).

SAFETY: dry-run by default; ``--apply`` writes stated_* columns only, via
UPDATE-or-INSERT per LGA with predicted counts. No serving table is touched.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DCP_DIR = os.path.join(REPO_ROOT, "data", "dcps")

MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"], start=1)
}
_MONTH_RE = "|".join(MONTHS)

# Statement patterns, strongest kind first. 'effective' covers "in force" /
# "came into effect" — the date the plan text operates from; 'adopted' is the
# council resolution date and is only used when nothing stronger exists.
_STATEMENTS: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"came into effect(?:\s+on|:)?\s+(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "effective"),
    (re.compile(rf"in force:?\s+(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "effective"),
    (re.compile(rf"effective:?\s*(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "effective"),
    (re.compile(r"effective:?\s*(\d{1,2})/(\d{1,2})/(\d{2,4})", re.I),
     "effective"),
    (re.compile(rf"adopted(?: by council)?(?:\s+on|:)?\s+(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "adopted"),
]

# file (relative to data/dcps) -> served lga slug. File-identity mapping only.
FILE_TO_SLUG: dict[str, str] = {
    "burwood-dcp.pdf": "burwood",
    "campbelltown-part3-low-medium-density.pdf": "campbelltown",
    "hills-shire-part-b-section2-residential.pdf": "the_hills",
    "northern-beaches-warringah-dcp-2011.pdf": "northern_beaches",
    "strathfield-part-a-dwelling-houses.pdf": "strathfield",
    "fairfield-citywide-dcp-2013.pdf": "fairfield",
    os.path.join("randwick", "volume-1-parts-a-c.pdf"): "randwick",
}
# Parramatta states no whole-plan commencement; its LIST OF AMENDMENTS table
# (page 3) carries per-amendment "Date in Force" values.
#
# DQ-62: the latest of those is CURRENCY, not commencement. It used to be
# written into stated_date, which is what put 2024-09-18 on parramatta when the
# plan commenced 2023-09-18 — right day, right month, wrong year, and wrong
# FIELD. An amendment date can never satisfy DQ-60, so this file's result now
# goes to the currency_* columns and stated_date is left for a source that
# actually states a commencement.
AMENDMENT_TABLE_FILE = ("parramatta-dcp-2023.pdf", "parramatta")

# Plans that print a version/amendment table with an "Original" row. That row
# is the commencement (DQ-60); the table's latest date is the currency (DQ-61).
# One table yields both facts, which is why they stopped competing for one
# column.
#
# Wingecarribee publishes its DCP as three town plans. All three state the same
# commencement — Original effective 16 June 2010 — and Part C Sections 2-4,
# which back every control we serve for the shire, are NUMERICALLY IDENTICAL
# across them (verified 2026-08-13: 100/40/16 numeric tokens per section, zero
# differences in all six pairwise comparisons). Only the Bowral plan is mapped
# because our controls were extracted from it and dcp_plan_as_at is keyed by
# council, not by plan (DQ-43).
VERSION_TABLE_FILES: dict[str, str] = {
    "wingecarribee-bowral-town-plan.pdf": "wingecarribee",
}

MAX_SCAN_PAGES = 12

# A plan that prints both its original commencement and a later amendment date
# is the normal case, not an anomaly. Where the two are this far apart the
# later one cannot be a commencement, so taking a maximum silently stores an
# amendment (DQ-62). Three years is generous: a DCP adopted in one year and
# commencing early the next is routine, a ten-year gap is not.
COMMENCEMENT_AMBIGUITY_YEARS = 3


@dataclass
class Stated:
    slug: str
    date_iso: str
    precision: str
    kind: str
    evidence: str


@dataclass
class Currency:
    """WHICH VERSION WE HOLD — deliberately not a Stated.

    Keeping these in separate types is what stops an amendment date being
    upserted into stated_date by a later edit: they are written by different
    SQL, to different columns, and a Currency has no `kind` because it is
    always the same kind of fact.
    """
    slug: str
    date_iso: str
    label: str
    evidence: str


def _to_year(y: int) -> int:
    return y if y >= 100 else 2000 + y


def scan_statement(path: str, rel: str) -> Optional[Stated]:
    import fitz  # PyMuPDF

    slug = FILE_TO_SLUG[rel]
    doc = fitz.open(path)
    try:
        hits: list[Stated] = []
        for pno in range(min(MAX_SCAN_PAGES, len(doc))):
            for raw_line in doc[pno].get_text("text").splitlines():
                line = " ".join(raw_line.split())
                for pat, kind in _STATEMENTS:
                    m = pat.search(line)
                    if not m:
                        continue
                    g = m.groups()
                    try:
                        if g[1].lower() in MONTHS:
                            d = date(int(g[2]), MONTHS[g[1].lower()], int(g[0]))
                        else:
                            d = date(_to_year(int(g[2])), int(g[1]), int(g[0]))
                    except (ValueError, KeyError):
                        continue
                    hits.append(Stated(slug, d.isoformat(), "day", kind,
                                       f"{rel} p{pno + 1}: \"{line[:160]}\""))
        if not hits:
            return None
        # 'effective' beats 'adopted'.
        effective = [h for h in hits if h.kind == "effective"]
        pool = effective or hits

        # DQ-62. This used to `return max(pool, ...)` on the reasoning that a
        # document stating both its original commencement and a later
        # amendment's effective date "must serve the later one". That is the
        # exact inversion of DQ-60: the stored date is the FULL PLAN's
        # commencement, and an amendment's effective date is currency. The rule
        # put an amendment date on parramatta, and the same rule is why four
        # more councils carry a stored commencement a decade later than the
        # plan their own name identifies (measured 2026-08-13: strathfield
        # DCP 2005 -> 2020-09-08, burwood DCP 2013 -> 2026-03-05, fairfield
        # DCP 2013 -> 2024-08-22, the_hills DCP 2012 -> 2022-05-06).
        #
        # Where the spread is wide the document is stating two DIFFERENT facts
        # and this scanner cannot tell which line is which — a cover page gives
        # no "Original" marker to key on. Guessing either end would be choosing
        # a value, so it returns None and is reported as unresolved. Skipping
        # visibly is the house rule; a wrong commencement reads as authoritative
        # and nothing downstream can detect it.
        earliest, latest = min(pool, key=lambda h: h.date_iso), max(pool, key=lambda h: h.date_iso)
        if int(latest.date_iso[:4]) - int(earliest.date_iso[:4]) >= COMMENCEMENT_AMBIGUITY_YEARS:
            return None
        return earliest
    finally:
        doc.close()


def scan_version_table(path: str, rel: str, slug: str
                       ) -> tuple[Optional[Stated], Optional[Currency]]:
    """Read a version table that names its own 'Original' row.

    This is the shape that carries BOTH facts DQ-60 and DQ-61 need, which is
    why it gets a parser of its own rather than another statement pattern:

        Version          Adopted            Effective
        Original         10 March 2010      16 June 2010     <- commencement
        As amended - 1   14 September 2011  5 October 2011
        ...
        As amended - 7   9 September 2015   23 September 2015 <- currency

    Column alignment is NOT trusted. Extracting these three plans with
    ``pdftotext -layout`` showed the Adopted and Effective cells drifting out
    of register on the Moss Vale table (one row carrying a single date, the
    next carrying two), so positional pairing would silently mis-associate.
    Two rules that survive that:

      * commencement = the LAST date on the 'Original' row. Adopted precedes
        Effective in every published layout, and the row is self-labelling.
        Verified against all three Wingecarribee plans, which state different
        adoption dates (10 Mar 2010, 14 Apr 2010, 28 Oct 2009) and the SAME
        effective date, 16 June 2010.
      * currency = the latest date anywhere in the table. Independently
        cross-checked against dcp_chapter_registry.chapter_label, which was
        written from the council's own filenames: Bowral 'as amended 23 Sep
        2015', Mittagong and Moss Vale 'as amended 17 Jun 2015'.

    An 'Original' row with no date returns (None, ...) rather than falling back
    to another row -- the fallback is the defect this function exists to end.
    """
    import fitz

    doc = fitz.open(path)
    try:
        for pno in range(min(MAX_SCAN_PAGES, len(doc))):
            lines = [" ".join(l.split())
                     for l in doc[pno].get_text("text").splitlines()]
            page = "\n".join(lines)
            # Require the table's own header before trusting any row: the word
            # "Original" alone appears in ordinary prose.
            if not re.search(r"\bEffective\b", page, re.I):
                continue
            original = next((l for l in lines if re.match(r"^Original\b", l, re.I)), None)
            if not original:
                continue

            def _dates(text: str) -> list[tuple[date, str]]:
                out: list[tuple[date, str]] = []
                for m in re.finditer(
                        rf"\b(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})\b", text, re.I):
                    try:
                        out.append((date(int(m.group(3)),
                                         MONTHS[m.group(2).lower()],
                                         int(m.group(1))), m.group(0)))
                    except (ValueError, KeyError):
                        continue
                return out

            # Two layouts, because the extractor decides which one you get.
            # `pdftotext -layout` keeps a table row on one line; PyMuPDF's
            # "text" mode emits every CELL on its own line. Handle both:
            # prefer dates on the Original line itself, else read the run of
            # date-only lines that follows it, stopping at the next row label.
            oi = lines.index(original)
            run = _dates(original)
            if not run:
                for l in lines[oi + 1:oi + 8]:
                    s = l.strip()
                    if not s:
                        continue
                    if re.match(r"^(As amended|Version)\b", s, re.I):
                        break
                    ds = _dates(s)
                    if not ds:
                        break
                    run.extend(ds)
            if not run:
                continue
            # Adopted precedes Effective in every published layout, so the LAST
            # date of the row is the one that commenced the plan. Where a row
            # carries only one date we cannot tell which column it is, and
            # guessing is what DQ-62 is about.
            if len(run) < 2:
                continue
            commenced, verbatim = run[-1]
            stated = Stated(
                slug, commenced.isoformat(), "day", "effective",
                f'{rel} p{pno + 1} version table, Original row: '
                f'"{" | ".join(v for _d, v in run)}" — effective {verbatim}')

            all_dates = _dates(page)
            currency = None
            latest, latest_v = max(all_dates, key=lambda t: t[0])
            if latest > commenced:
                label = next((l for l in lines if latest_v in l), "").strip()
                currency = Currency(
                    slug, latest.isoformat(), label[:120],
                    f'{rel} p{pno + 1} version table: latest of '
                    f"{len(all_dates)} dates, {latest_v}")
            return stated, currency
        return None, None
    finally:
        doc.close()


def scan_amendment_table(path: str, rel: str, slug: str) -> Optional[Currency]:
    """Parramatta: the LIST OF AMENDMENTS page lists, per amendment, a 'Date
    Approved by Council' followed by a 'Date in Force'. Dates are therefore
    consumed as ORDERED PAIRS and only the in-force member of each pair is a
    candidate — a page-wide maximum could catch an approved-but-not-yet-in-
    force date (Sol finding 5, 2026-08-03). An odd date count or a pair whose
    in-force precedes its approval breaks the pairing assumption, and the
    file is skipped visibly rather than guessed at.

    DQ-62: returns a Currency, never a Stated. The latest amendment to take
    effect is the version we hold; it is not the plan's commencement, and no
    amount of care about WHICH amendment date to pick makes it one. This
    function returning the wrong TYPE was the defect — the pairing logic below
    was always correct.
    """
    import fitz

    doc = fitz.open(path)
    try:
        for pno in range(min(MAX_SCAN_PAGES, len(doc))):
            text = doc[pno].get_text("text")
            up = text.upper()
            if "LIST OF AMENDMENTS" not in up:
                continue
            # The pairing assumption only holds on the two-date-column layout
            # — require BOTH column headers before trusting positional pairs.
            if "DATE APPROVED" not in up or "DATE IN FORCE" not in up:
                return None
            found: list[tuple[date, str]] = []
            for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text):
                try:
                    found.append((date(int(m.group(3)), int(m.group(2)),
                                       int(m.group(1))), m.group(0)))
                except ValueError:
                    continue
            if not found:
                return None
            if len(found) % 2 != 0:
                return None  # a dateless in-force cell — pairing broken
            pairs = [(found[i], found[i + 1]) for i in range(0, len(found), 2)]
            if any(approved[0] > in_force[0] for approved, in_force in pairs):
                return None  # in-force before approval — not the layout we know
            in_force_dates = [in_force[0] for _approved, in_force in pairs]
            if in_force_dates != sorted(in_force_dates) or \
                    len(set(in_force_dates)) != len(in_force_dates):
                # Amendments are numbered chronologically, so their in-force
                # dates must strictly increase down the table; a stray date
                # from a heading or footer breaks the ordering and the file
                # is skipped visibly rather than guessed at (Sol finding,
                # 2026-08-03).
                return None
            latest, verbatim = max(in_force for _approved, in_force in pairs)
            return Currency(slug, latest.isoformat(),
                            f"latest of {len(pairs)} amendments",
                            f"{rel} p{pno + 1} LIST OF AMENDMENTS: latest Date in "
                            f"Force {verbatim} of {len(pairs)} approved/in-force "
                            f"pairs")
        return None
    finally:
        doc.close()


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Write stated_* columns. Default: dry run.")
    ap.add_argument("--dcp-dir", default=DCP_DIR,
                    help="Location of the plan PDFs (data/dcps is git-ignored, "
                         "so a worktree run must point at the main checkout).")
    args = ap.parse_args()

    dcp_dir = args.dcp_dir
    if not os.path.isdir(dcp_dir):
        print(f"ERROR: {dcp_dir} not found — nothing was scanned, which is not "
              f"a pass. Exiting 2.", file=sys.stderr)
        return 2

    # Three outcomes per mapped file (Sol finding 6, 2026-08-03):
    #   hit          -> upsert the stated date
    #   file present, no statement -> the DOCUMENT changed: clear any stored
    #                   stated date for the slug (checked, none found)
    #   file missing -> a LOCAL checkout gap (data/dcps is git-ignored), says
    #                   nothing about the document: report only, never clear
    results: list[Stated] = []
    currencies: list[Currency] = []
    to_clear: list[tuple[str, str]] = []  # (slug, reason)
    skipped: list[str] = []
    for rel in sorted(FILE_TO_SLUG):
        path = os.path.join(dcp_dir, rel)
        if not os.path.isfile(path):
            skipped.append(f"{rel}: file missing locally — not cleared")
            continue
        hit = scan_statement(path, rel)
        if hit:
            results.append(hit)
        else:
            to_clear.append((FILE_TO_SLUG[rel],
                             f"{rel}: present but no statement matched, or its "
                             f"dated statements span "
                             f"{COMMENCEMENT_AMBIGUITY_YEARS}+ years so which "
                             f"one is the commencement is unresolved (DQ-62)"))

    for rel in sorted(VERSION_TABLE_FILES):
        slug = VERSION_TABLE_FILES[rel]
        path = os.path.join(dcp_dir, rel)
        if not os.path.isfile(path):
            skipped.append(f"{rel}: file missing locally — not cleared")
            continue
        stated, currency = scan_version_table(path, rel, slug)
        if stated:
            results.append(stated)
        else:
            to_clear.append((slug, f"{rel}: no dated 'Original' row found"))
        if currency:
            currencies.append(currency)

    rel, slug = AMENDMENT_TABLE_FILE
    path = os.path.join(dcp_dir, rel)
    if os.path.isfile(path):
        # DQ-62: this yields CURRENCY only. It is deliberately not added to
        # `to_clear` when it finds nothing — the amendment table never had any
        # business setting stated_date, so a miss here says nothing about
        # whether the stored commencement is still good.
        cur_hit = scan_amendment_table(path, rel, slug)
        if cur_hit:
            currencies.append(cur_hit)
    else:
        skipped.append(f"{rel}: file missing locally — not cleared")

    print(f"stated dates (commencement) extracted: {len(results)}")
    for r in results:
        print(f"  {r.slug:18s} {r.date_iso} ({r.precision}, {r.kind})  <- {r.evidence}")
    print(f"currency (version we hold) extracted: {len(currencies)}")
    for c in currencies:
        print(f"  {c.slug:18s} {c.date_iso} [{c.label}]  <- {c.evidence}")
    for slug_, reason in to_clear:
        print(f"  CLEAR   {slug_}: {reason}")
    for s in skipped:
        print(f"  SKIPPED {s}")

    if not args.apply:
        print(f"\nDRY RUN — nothing written. --apply would upsert "
              f"{len(results)} rows' stated_* columns, {len(currencies)} rows' "
              f"currency_* columns, and clear {len(to_clear)} stale stated rows.")
        return 0

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing written. Exiting 2.",
              file=sys.stderr)
        return 2
    # prior-art-checked: connection shape follows the house repair-script
    # pattern (repair_canada_bay_rear_setback.py) — DATABASE_URL + 30s timeout.
    import psycopg2

    # prior-art-checked: this extends this script's own stated_* upsert loop
    # with the stale-row clear rule (Sol finding 6, 2026-08-03); no other
    # module writes the stated_* columns of dcp_plan_as_at.
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    print(f"\npredicted writes: {len(results)} upserts (stated_* columns) "
          f"+ {len(currencies)} upserts (currency_* columns) "
          f"+ up to {len(to_clear)} stale-row clears")
    written = 0
    cur_written = 0
    cleared = 0
    try:
        for r in results:
            cur.execute(
                """
                INSERT INTO dcp_plan_as_at
                    (lga, stated_date, stated_date_precision, stated_date_kind,
                     stated_evidence, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (lga) DO UPDATE SET
                    stated_date = EXCLUDED.stated_date,
                    stated_date_precision = EXCLUDED.stated_date_precision,
                    stated_date_kind = EXCLUDED.stated_date_kind,
                    stated_evidence = EXCLUDED.stated_evidence,
                    updated_at = now()
                """,
                (r.slug, r.date_iso, r.precision, r.kind, r.evidence),
            )
            written += cur.rowcount
        for c in currencies:
            # Separate statement, separate columns. stated_* is never named
            # here, so no future edit to the currency path can reach the
            # commencement column (DQ-62).
            cur.execute(
                """
                INSERT INTO dcp_plan_as_at
                    (lga, currency_date, currency_label, currency_evidence,
                     currency_confirmed_at, updated_at)
                VALUES (%s, %s, %s, %s, NULL, now())
                ON CONFLICT (lga) DO UPDATE SET
                    currency_date = EXCLUDED.currency_date,
                    currency_label = EXCLUDED.currency_label,
                    currency_evidence = EXCLUDED.currency_evidence,
                    updated_at = now()
                """,
                (c.slug, c.date_iso, c.label, c.evidence),
            )
            cur_written += cur.rowcount
        for slug_, reason in to_clear:
            # UPDATE only: clearing is meaningful solely for a row that holds
            # a stale stated date; a fresh all-NULL row would say nothing.
            cur.execute(
                """
                UPDATE dcp_plan_as_at
                   SET stated_date = NULL, stated_date_precision = NULL,
                       stated_date_kind = NULL,
                       stated_evidence = %s, updated_at = now()
                 WHERE lga = %s AND stated_date IS NOT NULL
                """,
                (f"CLEARED {date.today().isoformat()}: {reason}", slug_),
            )
            cleared += cur.rowcount
        conn.commit()
        # prior-art-checked: reuse not viable because scripts/
        # fetch_dcp_as_at_dates.py answers a DIFFERENT question with the
        # portal_* columns — what the Planning Portal ADVERTISES for an LGA,
        # parsed from planName. This writes what OUR EXTRACTED COPY is, read
        # from the document itself. Both are needed precisely because they can
        # disagree, and that disagreement is the staleness signal DQ-61 asks
        # for (liverpool: portal says 'as amended Dec 2019', our PDF is named
        # ...2017). Measured 2026-08-13: portal_date is set on 1 of 28 rows,
        # so the existing path cannot answer currency for the other 27. No new
        # capability — this extends this script's own upsert loop.
        print(f"wrote {written} stated rows (predicted {len(results)}); "
              f"{cur_written} currency rows (predicted {len(currencies)}); "
              f"cleared {cleared} stale stated rows (of {len(to_clear)} candidates)")
        cur.execute("SELECT COUNT(*), COUNT(stated_date), COUNT(currency_date) "
                    "FROM dcp_plan_as_at")
        total, with_stated, with_currency = cur.fetchone()
        print(f"post-write verify: dcp_plan_as_at rows={total}, "
              f"stated_date set={with_stated}, currency_date set={with_currency}")
        # An amendment date in the commencement column is the defect this
        # script caused once already, so the write asserts against it rather
        # than trusting the types to have held.
        cur.execute("SELECT count(*) FROM dcp_plan_as_at "
                    "WHERE stated_date_kind = 'amended'")
        bad = cur.fetchone()[0]
        if bad:
            print(f"ERROR: {bad} row(s) still carry stated_date_kind='amended' "
                  f"— an amendment date is sitting in the commencement column "
                  f"(DQ-60/DQ-62).", file=sys.stderr)
            return 2
        return 0 if written == len(results) and cur_written == len(currencies) else 2
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
