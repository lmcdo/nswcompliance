#!/usr/bin/env python3
"""DQ-111: a served provision cites a section code its own source PDF never prints.

prior-art-checked: `scripts/dcp_fidelity_gate.py::ground_row` grades a row's
WORDS and NUMBERS against its source and deliberately strips the row's own code
numbers before doing so (`code_nums`), so nothing in the repo checks the code.
`scripts/verify_extraction_fidelity.py` has the same exemption. This probe is
the corpus-wide MEASUREMENT of that hole over what is served now; the fix that
stops new rows passing belongs inside `ground_row` (plan §3), not here.

WHAT IS JUDGED
--------------
The tail of `ref_number` (after the last ``__``) is split into code GROUPS: an
optional 1-3 letter prefix plus a number, and any numbers that follow it
(``C2_2_1_3`` -> ``C2.2.1.3``, ``8_2_4_7_controls_C57`` -> ``8.2.4.7`` + ``C57``).
When a ref has more than one group and the LAST carries a letter prefix, that
last group is the ITEM marker (``O1``, ``C17``, ``DS6.1``, ``P5``); everything
before it is the SECTION. The headline number is SECTION codes only -- that is
the claim a reader follows to find the clause. Items are reported beside it.

A section group is judged only when it can discriminate: it has a letter
prefix (``E7``, ``C4.9``) or at least two numeric parts (``3.1``). A bare
integer (``6``, ``15``) or a ref with no code at all (``intro``,
``height_objectives``) is NOT judged, and is counted under a named reason
rather than dropped.

"ABSENT" means the code appears NOWHERE in the document, with a boundary on
both sides so ``4.1`` does not match inside ``14.1`` or ``4.12``. That is
deliberately conservative: a code printed once as a cross-reference passes.
Text is read with PyMuPDF first (fast enough for the 139 MB PDFs); a chapter
with any absent code is re-read with pdfplumber and a code counts as absent
only if BOTH readers miss it, so an extractor quirk cannot become a finding.

Contract as `dq_probe_live.py`: exit 0 when the count is 0, 1 when it is not,
2 when a source cannot be reached. Read-only -- no statement here writes.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parent.parent

SERVED_SQL = """
SELECT rp.id, rp.source_council, rp.source_chapter_key, rp.ref_number,
       reg.r2_current_path, rp.provision_text
FROM regulatory_provisions rp
JOIN dcp_chapter_registry reg
  ON reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key
 AND reg.is_active
WHERE rp.is_current AND rp.v2_is_actionable AND rp.source_council IS NOT NULL
"""
SERVED_COUNT_SQL = ("SELECT count(*) FROM regulatory_provisions WHERE is_current "
                    "AND v2_is_actionable AND source_council IS NOT NULL")

# A code part: optional 1-3 letter prefix, a number, optional one trailing letter.
_HEAD = re.compile(r"^([A-Za-z]{1,3})?(\d+[A-Za-z]?)$")
_CONT = re.compile(r"^\d+[A-Za-z]?$")


def code_groups(ref_number: str | None) -> list[tuple[str, list[str]]]:
    """Split a ref tail into (letter_prefix, [numeric parts]) groups, in order."""
    tail = (ref_number or "").split("__")[-1]
    tail = re.sub(r"\([^)]*\)", " ", tail)          # "(a)" sub-clauses: not a code
    groups: list[tuple[str, list[str]]] = []
    for token in tail.split():
        current: tuple[str, list[str]] | None = None
        for part in re.split(r"[_\-.]+", token):
            if not part:
                continue
            if current is not None and _CONT.match(part):
                current[1].append(part)
                continue
            m = _HEAD.match(part)
            if m:
                current = ((m.group(1) or "").upper(), [m.group(2)])
                groups.append(current)
            else:
                current = None                        # a word breaks the group
    return groups


def split_ref(ref_number: str | None):
    """-> (sections, item, unjudged_reason). unjudged_reason is None when judged."""
    groups = code_groups(ref_number)
    item = None
    if len(groups) > 1 and groups[-1][0]:
        item = groups[-1]
        groups = groups[:-1]
    sections = [g for g in groups if g[0] or len(g[1]) >= 2]
    if sections:
        return sections, item, None
    if groups:
        return [], item, "bare integer section (not discriminating)"
    if item:
        return [], item, "item marker only, no section"
    return [], None, "no clause number in the ref"


def render(group: tuple[str, list[str]]) -> str:
    prefix, nums = group
    return prefix + ".".join(nums)


def code_pattern(group: tuple[str, list[str]]) -> re.Pattern:
    """Boundary-anchored, case-insensitive, tolerant of a space after a separator."""
    prefix, nums = group
    body = r"\.\s?".join(re.escape(n.lower()) for n in nums)
    lead = (re.escape(prefix.lower()) + r"\s?") if prefix else ""
    return re.compile(r"(?<![a-z0-9.])" + lead + body + r"(?![0-9])")


def present(group, text: str) -> bool:
    return bool(code_pattern(group).search(text))


def heading_words(row_text: str | None, n: int = 2) -> list[str]:
    """The first words of the heading a row carries, skipping its code tokens.

    Rows are stored as ``# g1.12 o4 key sites to restrict ...``; the words after
    the codes are the heading the council printed beside the number.
    """
    words = []
    for tok in re.sub(r"[#–—\-:>]", " ", (row_text or "").lower()).split():
        if re.search(r"\d", tok):
            if words:
                break
            continue
        if re.fullmatch(r"[a-z][a-z'&]*", tok):
            words.append(tok)
            if len(words) == n:
                break
    return words


def path_kind(group, text: str, row_text: str | None = None) -> str:
    """Why an absent code is absent: a joined heading PATH, or NOT PRINTED.

    Some readers build the ref by joining the headings above a rule, so the
    code is ours but every piece of it is the council's: Waverley's
    ``B14_14_3_14_3_7`` is Part B14 > 14.3 > 14.3.7, all three printed. That is
    traceable, not invented, and must not be counted with ``C4.9``.

    -> "path"      part printed and the rest splits into printed dotted codes
       "path_weak" part printed, and a piece is a single bare number that the
                   source prints followed by the row's own heading words
                   (``G1.12`` = Part G1 > "12 Key sites")
       "not_printed" otherwise
    """
    prefix, nums = group
    if not prefix or len(nums) < 2 or not present((prefix, nums[:1]), text):
        return "not_printed"

    # A bare number proves nothing on its own ("9" is on every page), so it is
    # accepted only as a printed HEADING: the number, then the row's own heading
    # words. Without this, Woollahra's C4.9 passed as "Part C4 > 9" because C4
    # is cross-referenced once in that chapter -- the confusable positive.
    title = heading_words(row_text)

    def single_ok(num):
        if len(title) < 2:
            return False
        return bool(re.search(r"(?<![a-z0-9.])" + re.escape(num.lower()) + r"\.?\s+"
                              + r"\s+".join(map(re.escape, title)), text))

    def split(rest, allow_single):
        if not rest:
            return True
        for k in range(len(rest), 0, -1):
            if k == 1 and not (allow_single and single_ok(rest[0])):
                continue
            if (k == 1 or present(("", rest[:k]), text)) and split(rest[k:], allow_single):
                return True
        return False

    if split(nums[1:], False):
        return "path"
    if split(nums[1:], True):
        return "path_weak"
    return "not_printed"


# -- source text ---------------------------------------------------------------

def _cache_file(cache_dir: Path, r2_path: str, reader: str) -> Path:
    return cache_dir / f"{hashlib.sha1(r2_path.encode()).hexdigest()[:16]}.{reader}.txt"


def source_text(s3, bucket, r2_path: str, cache_dir: Path, reader: str) -> str:
    """Whole-document lowercased text, cached per (path, reader)."""
    cf = _cache_file(cache_dir, r2_path, reader)
    if cf.exists():
        return cf.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "src.pdf"
        s3.download_file(bucket, r2_path, str(local))
        chunks: list[str] = []
        if reader == "fitz":
            import fitz
            with fitz.open(str(local)) as doc:
                for page in doc:
                    chunks.append(page.get_text())
        else:
            import pdfplumber
            with pdfplumber.open(str(local)) as pdf:
                for page in pdf.pages:
                    chunks.append(page.extract_text() or "")
                    page.flush_cache()           # what lets the 139 MB PDF finish
    text = re.sub(r"\s+", " ", "\n".join(chunks)).lower()
    cf.write_text(text, encoding="utf-8")
    return text


# -- run -----------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "dq111_src"),
                    help="Where extracted PDF text is cached between runs.")
    ap.add_argument("--council", help="Limit to one council.")
    ap.add_argument("--csv", help="Write every judged-absent row here.")
    ap.add_argument("--examples", type=int, default=3)
    args = ap.parse_args()

    try:
        import boto3
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
        s3 = boto3.client(
            "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
        bucket = os.environ["R2_BUCKET_NAME"]
    except Exception as exc:  # noqa: BLE001
        print(f"UNREACHABLE: {exc}")
        return 2
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cur = conn.cursor()
    cur.execute(SERVED_COUNT_SQL)
    served_total = cur.fetchone()[0]
    sql, params = SERVED_SQL, []
    if args.council:
        sql += " AND rp.source_council = %s"
        params.append(args.council)
    cur.execute(sql, params)
    rows = cur.fetchall()
    print(f"served council rows: {served_total}  ({SERVED_COUNT_SQL})")
    print(f"rows joined to an active registry PDF: {len(rows)}")

    by_pdf = collections.defaultdict(list)
    for r in rows:
        by_pdf[r[4]].append(r)

    # Download is the cost, not reading: the 139 MB PDF takes ~40s to fetch and
    # under a second in PyMuPDF. Fetched serially the corpus overran dq_check's
    # 900s budget, so the first reader's text is warmed 8 at a time. Failures
    # are left for the loop below to report, not swallowed here.
    from concurrent.futures import ThreadPoolExecutor

    def _warm(path):
        try:
            source_text(s3, bucket, path, cache_dir, "fitz")
        except Exception:  # noqa: BLE001 -- re-raised and reported in the main loop
            pass

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_warm, by_pdf))

    unjudged = collections.Counter()
    judged = absent = item_judged = item_absent = 0
    per_council = collections.defaultdict(lambda: [0, 0, 0])   # judged, absent, unjudged
    per_chapter = collections.Counter()
    examples = collections.defaultdict(list)
    by_kind = collections.Counter()
    kind_council = collections.Counter()
    failing = []
    unreadable = []
    for n, (r2_path, prow) in enumerate(sorted(by_pdf.items(), key=lambda kv: len(kv[1])), 1):
        try:
            text = source_text(s3, bucket, r2_path, cache_dir, "fitz")
        except Exception as exc:  # noqa: BLE001
            unreadable.append((r2_path, str(exc)[:120]))
            continue
        plumber = None
        for rid, council, chapter, ref, _, row_text in prow:
            sections, item, reason = split_ref(ref)
            if reason:
                unjudged[reason] += 1
                per_council[council][2] += 1
            else:
                judged += 1
                per_council[council][0] += 1
                missing = [g for g in sections if not present(g, text)]
                if missing and plumber is None:
                    plumber = source_text(s3, bucket, r2_path, cache_dir, "plumber")
                missing = [g for g in missing if not present(g, plumber)]
                if missing:
                    absent += 1
                    kinds = {path_kind(g, plumber + " " + text, row_text) for g in missing}
                    kind = next(k for k in ("not_printed", "path_weak", "path") if k in kinds)
                    by_kind[kind] += 1
                    kind_council[(council, kind)] += 1
                    if kind == "not_printed":
                        per_council[council][1] += 1
                        per_chapter[f"{council}/{chapter}"] += 1
                    codes = ", ".join(render(g) for g in missing)
                    failing.append((rid, council, chapter, ref, codes, kind))
                    if kind == "not_printed" and len(examples[council]) < args.examples:
                        examples[council].append(f"{chapter}: {ref.split('__')[-1]!r} -> {codes}")
            if item and (sections or reason is None):
                item_judged += 1
                if not present(item, text):
                    if plumber is None:
                        plumber = source_text(s3, bucket, r2_path, cache_dir, "plumber")
                    if not present(item, plumber):
                        item_absent += 1
        print(f"  [{n}/{len(by_pdf)}] {len(prow):5} rows  {r2_path}", file=sys.stderr)

    bad = by_kind["not_printed"]
    pct = 100 * bad / judged if judged else 0.0
    print()
    print(f"SECTION CODE NOT PRINTED IN ITS OWN SOURCE: {bad} of {judged} judged rows ({pct:.2f}%)")
    print(f"  code string absent as written: {absent}, of which")
    for kind in ("not_printed", "path_weak", "path"):
        print(f"    {by_kind[kind]:6}  {kind}")
    for (council, kind), k in sorted(kind_council.items()):
        if kind != "not_printed":
            print(f"             {k:6}  {kind:10} {council}")
    print(f"not judged: {sum(unjudged.values())}")
    for reason, k in unjudged.most_common():
        print(f"    {k:6}  {reason}")
    if unreadable:
        print(f"UNREADABLE PDFs: {len(unreadable)}")
        for p, e in unreadable:
            print(f"    {p}: {e}")
    print(f"(item markers, beside the headline: {item_absent} of {item_judged} absent)")
    print("\nper council: judged / absent / not judged")
    for council, (j, a, u) in sorted(per_council.items(), key=lambda kv: -kv[1][1]):
        print(f"  {council:22} {j:6} {a:6} ({100*a/j if j else 0:5.1f}%) {u:6}")
    print("\nchapters with absent codes:")
    for ch, k in per_chapter.most_common(40):
        print(f"  {k:5}  {ch}")
    print("\nexamples:")
    for council, ex in examples.items():
        for e in ex:
            print(f"  {council}: {e}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "council", "chapter", "ref_number", "absent_codes", "kind"])
            w.writerows(failing)
    if unreadable:
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
