#!/usr/bin/env python3
"""Take in council plan PDFs that a person downloaded by hand (DQ-153).

prior-art-checked: reuse not viable because scripts/manual_verify.py compares one
file at a time and has no list of blocked chapters; this wrapper adds only the
list and the folder loop, and calls the existing `r2_monitor.py --from-file`
intake for the real work (hash check, R2 upload, registry update).

When a council website blocks our monitor (HTTP 403) the plan goes stale. This
does NOT get around the block. It does two things:

  1. No arguments: print every blocked or stale chapter with the council's own
     link and the file name to save it as.
  2. --folder DIR: for each PDF in DIR named <council>__<chapter_key>.pdf, work
     out the file's sha256 and call the existing intake for it. Dry run by
     default; add --apply to write.

    python scripts/manual_intake.py
    python scripts/manual_intake.py --folder C:/Users/me/Downloads/councils
    python scripts/manual_intake.py --folder C:/Users/me/Downloads/councils --apply
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STALE_DAYS = 14

# Same test as DQ-153 (scripts/dq_probe_live.py), listed per chapter.
BLOCKED_CHAPTERS_SQL = """
SELECT r.council, r.chapter_key, r.chapter_label, r.council_url, r.url_last_checked
FROM dcp_chapter_registry r
WHERE r.is_active AND r.doc_type = 'dcp'
  AND EXISTS (SELECT 1 FROM regulatory_provisions p
              WHERE p.source_council = r.council AND p.source_chapter_key = r.chapter_key
                AND p.is_current AND p.v2_is_actionable)
  AND (r.url_last_checked IS NULL OR r.url_last_checked < now() - %s * interval '1 day'
       OR (SELECT x.outcome FROM dcp_monitor_chapter_results x WHERE x.chapter_id = r.id
           ORDER BY x.checked_at DESC, x.id DESC LIMIT 1) = 'waf_blocked')
ORDER BY r.council, r.sort_order, r.chapter_key
"""


def file_name_for(council: str, chapter_key: str) -> str:
    return f"{council}__{chapter_key}.pdf"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def intake_command(council: str, chapter_key: str, pdf: Path, sha: str, apply: bool) -> list[str]:
    """The exact r2_monitor.py call for one downloaded file (dry run unless apply)."""
    cmd = [
        sys.executable, str(HERE / "r2_monitor.py"),
        "--council", council, "--chapter-key", chapter_key,
        "--from-file", str(pdf), "--expect-sha256", sha,
    ]
    if not apply:
        cmd.append("--dry-run")
    return cmd


def match_folder(rows: list[dict], folder: Path) -> tuple[list[tuple[dict, Path]], list[Path], list[dict]]:
    """Split into (matched row+file, files that match no blocked chapter, chapters with no file)."""
    by_name = {file_name_for(r["council"], r["chapter_key"]): r for r in rows}
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    matched = [(by_name[p.name], p) for p in files if p.name in by_name]
    unknown = [p for p in files if p.name not in by_name]
    done = {r["chapter_key"] + "|" + r["council"] for r, _ in matched}
    missing = [r for r in rows if r["chapter_key"] + "|" + r["council"] not in done]
    return matched, unknown, missing


def blocked_chapters(days: int = STALE_DAYS) -> list[dict]:
    import dq_db

    conn = dq_db.connect()
    try:
        cur = conn.cursor()
        cur.execute(BLOCKED_CHAPTERS_SQL, (days,))
        cols = ["council", "chapter_key", "chapter_label", "council_url", "url_last_checked"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def print_list(rows: list[dict]) -> None:
    if not rows:
        print("No blocked or stale chapters. Nothing to take in.")
        return
    council = None
    for r in rows:
        if r["council"] != council:
            council = r["council"]
            print(f"\n{council}")
        last = r["url_last_checked"].date().isoformat() if r["url_last_checked"] else "never"
        print(f"  {r['chapter_key']}  ({r['chapter_label']})  last checked {last}")
        print(f"    open : {r['council_url']}")
        print(f"    save : {file_name_for(r['council'], r['chapter_key'])}")
    print(f"\n{len(rows)} chapter(s) in {len({r['council'] for r in rows})} council(s). "
          "Download each from the council's own site in a normal browser, save under the name shown, "
          "then run with --folder.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", type=Path, help="folder of downloaded PDFs named <council>__<chapter_key>.pdf")
    ap.add_argument("--apply", action="store_true", help="write (default is a dry run)")
    ap.add_argument("--days", type=int, default=STALE_DAYS)
    args = ap.parse_args(argv)

    try:
        rows = blocked_chapters(args.days)
    except RuntimeError as e:
        print(f"UNKNOWN: {e}")
        return 2
    if not args.folder:
        print_list(rows)
        return 0
    if not args.folder.is_dir():
        print(f"Not a folder: {args.folder}")
        return 2

    matched, unknown, missing = match_folder(rows, args.folder)
    print(f"{'APPLY' if args.apply else 'DRY RUN'}: {len(matched)} file(s) match a blocked chapter, "
          f"{len(unknown)} match none, {len(missing)} chapter(s) still have no file.")
    for p in unknown:
        print(f"  skipped (no blocked chapter by this name): {p.name}")
    failed = 0
    for i, (r, pdf) in enumerate(matched, 1):
        sha = sha256_of(pdf)
        print(f"DONE {i - 1}/{len(matched)}  next: {r['council']}/{r['chapter_key']}  sha256 {sha[:12]}")
        rc = subprocess.call(intake_command(r["council"], r["chapter_key"], pdf, sha, args.apply))
        if rc:
            failed += 1
            print(f"  FAILED (exit {rc}): {r['council']}/{r['chapter_key']}")
    print(f"DONE {len(matched)}/{len(matched)}  failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
