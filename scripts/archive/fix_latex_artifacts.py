#!/usr/bin/env python3
"""
Task 0.1: Clean LaTeX artifacts from provision_text in regulatory_provisions.

Targets:
  - \mathrm{X} -> X
  - \mathsf{X} -> X
  - $_{X}$ -> X
  - \star_ -> (remove)
  - Spaced digits: "6 0 0" -> "600" (but NOT SEPP section refs like "3.40(5)")
  - { , } -> ,
  - ^ { X } -> X

Creates backup table first. Reports before/after counts.

Usage:
    python scripts/fix_latex_artifacts.py --dry-run   # show what would change
    python scripts/fix_latex_artifacts.py              # apply fixes
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import psycopg2
from psycopg2.extras import RealDictCursor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def clean_latex(text: str) -> str:
    """Apply all LaTeX cleanup rules to a provision text string."""
    if not text:
        return text

    original = text

    # 1a. \mathrm{X} -> X  and  \mathsf{X} -> X (with braces)
    text = re.sub(r'\\mathrm\s*\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathsf\s*\{([^}]*)\}', r'\1', text)

    # 1b. \mathrm X -> X  and  \mathsf X -> X (without braces, single token)
    text = re.sub(r'\\mathrm\s+(\S+)', r'\1', text)
    text = re.sub(r'\\mathsf\s+(\S+)', r'\1', text)

    # 2. $_{X}$ -> X  (subscript notation)
    text = re.sub(r'\$\s*_\s*\{([^}]*)\}\s*\$', r'\1', text)

    # 3. $^{X}$ -> X  (superscript notation)
    text = re.sub(r'\$\s*\^\s*\{([^}]*)\}\s*\$', r'\1', text)

    # 4. \prime -> ' and \prime\prime -> "
    text = re.sub(r'\\prime\s*\\prime', '"', text)
    text = re.sub(r'\\prime', "'", text)

    # 5. Font commands: \tt, \bf, \it, \rm -> remove
    text = re.sub(r'\\(?:tt|bf|it|rm)\s*', '', text)

    # 6. \because, \circ, \underline -> cleanup
    text = re.sub(r'\\because\s*', '', text)
    text = re.sub(r'\\circ', '\u00b0', text)  # degree symbol
    text = re.sub(r'\\underline\s*\{\s*\{([^}]*)\}\s*\}', r'\1', text)  # nested braces
    text = re.sub(r'\\underline\s*\{([^}]*)\}', r'\1', text)

    # 7. $\$ X$ -> $X (LaTeX escaped dollar = real currency)
    text = re.sub(r'\$\s*\\\$\s*([^$]*)\$', r'$\1', text)

    # 8. ${ ... }$ -> content (LaTeX math groups)
    text = re.sub(r'\$\s*\{([^}]*)\}\s*\$', r'\1', text)
    # ${ ... } without closing $ (broken LaTeX)
    text = re.sub(r'\$\s*\{\s*\}', '', text)  # empty ${}
    text = re.sub(r'\$\s*\{([^}]*)\}', r'\1', text)

    # 9. Standalone ^ { X } -> X
    text = re.sub(r'\^\s*\{\s*([^}]*)\s*\}', r'\1', text)

    # 10. \star_ -> remove
    text = re.sub(r'\\star_?\s*', '', text)

    # 11. { , } -> ,
    text = re.sub(r'\{\s*,\s*\}', ',', text)

    # 12. Remaining bare \{ and \} -> remove backslash
    text = re.sub(r'\\([{}])', r'\1', text)

    # 13. Remaining { X } -> X (orphan braces around content)
    text = re.sub(r'\{\s*(\d+)\s*\}', r'\1', text)

    # 14. Remaining bare $ signs (LaTeX delimiters, not currency)
    text = re.sub(r'\$\s*\$', '', text)  # empty $$ pairs
    # $ adjacent to quotes
    text = re.sub(r'"\s*\$', '"', text)  # "$ -> "
    text = re.sub(r'\$\s*"', '"', text)  # $" -> "
    # \$ -> $ (escaped dollar = actual dollar sign)
    text = re.sub(r'\\\$', '$', text)
    # Isolated $ between spaces
    text = re.sub(r'\s\$\s', ' ', text)
    # $ at end of line or before comma/period
    text = re.sub(r'\$\s*([,.\s])', r'\1', text)
    # $\ " -> " (LaTeX escaped space + quote)
    text = re.sub(r'\$\\\s*"', '"', text)

    # 9. Spaced digits: "6 0 0" -> "600", "0 . 6" -> "0.6"
    #    Only match sequences of single digits separated by spaces
    #    that look like they should be one number.
    #    Pattern: 3+ single digits separated by single spaces
    def rejoin_spaced_digits(match):
        return match.group(0).replace(' ', '')

    # Match: digit space digit (at least 2 digits spaced)
    # Lookahead prevents joining when followed by a letter (e.g., "4 2D" is a reference)
    text = re.sub(r'(?<!\d)(\d(?:\s\d){1,})(?![\dA-Za-z])', rejoin_spaced_digits, text)

    # Also fix "0 . 6 : 1" -> "0.6:1" (spaced decimal + ratio)
    text = re.sub(r'(\d)\s+\.\s+(\d)', r'\1.\2', text)
    text = re.sub(r'(\d)\s+:\s+(\d)', r'\1:\2', text)

    # Only collapse double spaces if we actually made other changes
    if text != original:
        text = re.sub(r'  +', ' ', text)

    return text


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Clean LaTeX artifacts from provision text")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--limit", type=int, help="Limit number of provisions to process")
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Count affected provisions
    cur.execute("""
        SELECT COUNT(*) as cnt FROM regulatory_provisions
        WHERE is_current = true
          AND (provision_text LIKE '%%\\mathrm%%'
               OR provision_text LIKE '%%\\mathsf%%'
               OR provision_text LIKE '%%$_{%%'
               OR provision_text LIKE '%%\\star_%%'
               OR provision_text LIKE '%%\\star %%'
               OR provision_text LIKE '%%\\prime%%'
               OR provision_text LIKE '%%\\tt %%'
               OR provision_text LIKE '%%"$%%'
               OR provision_text LIKE '%%$"%%'
               OR provision_text ~ '\\d \\d \\d')
    """)
    total = cur.fetchone()["cnt"]
    print(f"Provisions with LaTeX artifacts: {total}")

    if total == 0:
        print("Nothing to clean.")
        return

    # Create backup (only on real run)
    if not args.dry_run:
        backup_name = "regulatory_provisions_backup_latex"
        cur.execute(f"SELECT to_regclass('{backup_name}')")
        if cur.fetchone()["to_regclass"] is None:
            print(f"Creating backup table: {backup_name}")
            cur.execute(f"""
                CREATE TABLE {backup_name} AS
                SELECT id, provision_text
                FROM regulatory_provisions
                WHERE is_current = true
                  AND (provision_text LIKE '%%\\mathrm%%'
                       OR provision_text LIKE '%%\\mathsf%%'
                       OR provision_text LIKE '%%$_{{%%'
                       OR provision_text LIKE '%%\\star_%%'
                       OR provision_text LIKE '%%\\star %%'
                       OR provision_text LIKE '%%\\prime%%'
                       OR provision_text LIKE '%%\\tt %%'
                       OR provision_text LIKE '%%"$%%'
                       OR provision_text LIKE '%%$"%%'
                       OR provision_text ~ '\\d \\d \\d')
            """)
            conn.commit()
            print(f"Backed up {total} provisions.")
        else:
            print(f"Backup table {backup_name} already exists, skipping.")

    # Fetch and process
    limit_clause = f"LIMIT {args.limit}" if args.limit else ""
    cur.execute(f"""
        SELECT id, provision_text, source_council
        FROM regulatory_provisions
        WHERE is_current = true
          AND (provision_text LIKE '%%\\mathrm%%'
               OR provision_text LIKE '%%\\mathsf%%'
               OR provision_text LIKE '%%$_{{%%'
               OR provision_text LIKE '%%\\star_%%'
               OR provision_text LIKE '%%\\star %%'
               OR provision_text LIKE '%%\\prime%%'
               OR provision_text LIKE '%%\\tt %%'
               OR provision_text LIKE '%%"$%%'
               OR provision_text LIKE '%%$"%%'
               OR provision_text ~ '\\d \\d \\d')
        ORDER BY id
        {limit_clause}
    """)
    provisions = cur.fetchall()

    changed = 0
    unchanged = 0
    samples = []

    for prov in provisions:
        original = prov["provision_text"]
        cleaned = clean_latex(original)

        if cleaned != original:
            changed += 1
            if len(samples) < 5:
                # Show first diff for review
                samples.append({
                    "id": prov["id"],
                    "council": prov["source_council"],
                    "before": original[:200],
                    "after": cleaned[:200],
                })

            if not args.dry_run:
                cur.execute(
                    "UPDATE regulatory_provisions SET provision_text = %s WHERE id = %s",
                    (cleaned, prov["id"])
                )
        else:
            unchanged += 1

    if not args.dry_run:
        conn.commit()

    # Report
    print(f"\n=== RESULTS ===")
    print(f"Total scanned: {len(provisions)}")
    print(f"Changed: {changed}")
    print(f"Unchanged: {unchanged}")
    if args.dry_run:
        print("[DRY RUN -- no changes applied]")

    if samples:
        print(f"\n=== SAMPLES (first {len(samples)}) ===")
        for s in samples:
            print(f"\n--- ID {s['id']} (council={s['council']}) ---")
            print(f"  BEFORE: {s['before']}")
            print(f"  AFTER:  {s['after']}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
