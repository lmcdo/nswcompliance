#!/usr/bin/env python3
"""
Strip reversed OCR sidebar labels from Ku-ring-gai provision text.

KRG PDFs have rotated section labels (e.g. SUBDIVISION, PARKING, ACCESS) printed
sideways in the page margin. pdfplumber extracts them as isolated uppercase lines
mixed into the provision text. They are noise — not content.

Reversed tokens identified:
  NOISIVIDBUS   = SUBDIVISION
  NOITADILOSNOC = CONSOLIDATION
  SLORTNOC      = CONTROLS
  LARENEG       = GENERAL
  GNIKRAP       = PARKING
  SSECCA        = ACCESS
  NGISED        = DESIGN
  DNA           = AND
  ROF           = FOR (skip — too short, legit uses exist)
  ERUTCURTS     = STRUCTURE
  TNEMPOLEVD    = DEVELOPMENT (partial)

Strategy: remove lines that are ONLY these reversed tokens (standalone lines).
Safe because real English content won't be entirely these tokens.
"""
import argparse, datetime, json, os, sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# These reversed tokens appear as isolated lines — safe to remove as standalone
REVERSED_TOKENS = {
    'NOISIVIDBUS', 'NOITADILOSNOC', 'SLORTNOC', 'LARENEG',
    'GNIKRAP', 'SSECCA', 'NGISED', 'DNA', 'ROF', 'ERUTCURTS',
    'TNEMPOLEVD', 'TNEMPOLEVED', 'LAICREMMOS', 'LAITNEDISER',
    'GNIDLIUB', 'TNEMEGANAM', 'TNEMSSESSA', 'YTITNEDI',
    'NOITCETORP', 'NOITAVRESERP', 'EGATIREH',
    # Signage chapter sidebar labels (identified 2026-03-14)
    'GNISITREVDA',  # ADVERTISING
    'EGANGIS',      # SIGNAGE
    '&',            # standalone ampersand from "DESIGN & ADVERTISING" label
    # Standalone page header lines
    'Ku-ring-gai Development Control Plan',
}

# Also strip isolated part-code lines like "3A", "6B", "8A" that are just page headers
PART_CODE_RE = re.compile(r'^[0-9]+[A-Z]$')

def clean_text(text: str) -> str:
    if not text:
        return text
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Remove standalone reversed tokens
        if stripped in REVERSED_TOKENS:
            continue
        # Remove isolated part codes (e.g. "3A", "6B") that are margin labels
        if PART_CODE_RE.match(stripped):
            continue
        cleaned.append(line)
    # Collapse 3+ consecutive blank lines to 2
    result = re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned))
    return result.strip()


# prior-art-checked: reuse not viable because this guards the same script's
# existing write in place (no new data source); the suggested matches are
# unrelated one-off scripts with no importable backup helper. 2026-10-31.
BACKUP_DIR = Path(__file__).parent.parent / 'data' / 'db_rollback_backups'


def main() -> int:
    """Dry run by default; --apply backs up the old text, then rewrites it.

    This rewrites live provision_text, so it must never run on import and never
    without a copy of what it replaced.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='back up and rewrite (default: dry run)')
    args = parser.parse_args()

    url = os.getenv('SUPABASE_DB_URL')
    if not url:
        print('[ABORT] SUPABASE_DB_URL not set; nothing written.')
        return 1
    conn = psycopg2.connect(url)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, provision_text FROM regulatory_provisions
        WHERE source_council = 'ku_ring_gai' AND is_current = true
    """ + (" FOR UPDATE" if args.apply else ""))
    rows = cur.fetchall()
    print(f"Checking {len(rows)} provisions...")

    updates = []
    old_text = {}
    for pid, text in rows:
        cleaned = clean_text(text)
        if cleaned != (text or '').strip():
            updates.append((cleaned, pid))
            old_text[pid] = text

    print(f"Provisions needing cleanup: {len(updates)}")
    if not args.apply:
        print('DRY RUN: nothing written. Re-run with --apply to back up and rewrite.')
        conn.close()
        return 0
    if not updates:
        conn.close()
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H%M%S')
    backup = BACKUP_DIR / f'krg_reversed_provision_text_pre_{stamp}.json'
    backup.write_text(json.dumps(
        {'table': 'regulatory_provisions', 'column': 'provision_text',
         'rows': [{'id': pid, 'provision_text': t} for pid, t in old_text.items()]}),
        encoding='utf-8')
    print(f"[BACKUP] {len(old_text)} rows -> {backup}")

    # Rows are locked (FOR UPDATE) since the SELECT, and each UPDATE also requires
    # the row still to be current Ku-ring-gai with the text that was backed up, so
    # any concurrent change shows up as a count mismatch and nothing is written.
    changed = 0
    for new_text, pid in updates:
        cur.execute(
            "UPDATE regulatory_provisions SET provision_text = %s WHERE id = %s"
            " AND source_council = 'ku_ring_gai' AND is_current = true"
            " AND provision_text IS NOT DISTINCT FROM %s",
            (new_text, pid, old_text[pid]),
        )
        changed += cur.rowcount
    if changed != len(updates):
        conn.rollback()
        print(f"[ABORT] {changed} of {len(updates)} rows still matched; rolled back, nothing written.")
        conn.close()
        return 1

    conn.commit()
    print(f"Applied {len(updates)} text cleanups.")
    cur.close()
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
