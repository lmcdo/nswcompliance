"""DQ-32c repair: two served controls whose source text does not support them.

DRY RUN unless --apply. Backs up the affected rows to a dated table first.

id=696 camden secondary_dwelling front_setback 3.0 m
    Its source text is a waste-storage list ("be a hardstand", "Council's
    Waste Management Guideline", "collect and return service"). The 3 m is the
    setback for a BIN HARDSTAND, not for the dwelling. Its slot-mate id=695
    (12 m, actually facade-to-facade separation) is already excluded, so this
    row is currently the ONLY front setback served for Camden secondary
    dwellings. Switching it off removes a false claim; it cannot create one.

id=698 canada_bay dwelling_house front_setback 4.5 m
    Source: "a minimum of 4.5 metres OR no less than the Prevailing Street
    Setback, whichever is the greater." We serve the bare 4.5, which
    UNDERSTATES the requirement. The value is right; the qualifier is missing.
    Adding the condition does not change the number served.
"""
import argparse, os, sys
from dotenv import load_dotenv
load_dotenv()
import psycopg2, psycopg2.extras

BACKUP = "dcp_setback_controls_dq32c_backup_20260817"
REVIEW_REASON_696 = (
    "Source text is a waste-storage control list (hardstand, Waste Management "
    "Guideline, collect-and-return service); the 3 m is the setback for a bin "
    "hardstand, not a secondary dwelling front setback. Excluded pending a "
    "source lookup for the real control. DQ-32c, 2026-08-17."
)
CONDITION_698 = "or the Prevailing Street Setback, whichever is the greater"

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
args = ap.parse_args()

url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
if not url:
    print("ERROR: DATABASE_URL not set.", file=sys.stderr)
    sys.exit(2)
conn = psycopg2.connect(url)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SET statement_timeout = '30000'")

def show(title):
    cur.execute("""SELECT id, lga, dev_type, control_type, value_min, unit,
                          condition, is_current, COALESCE(needs_review,FALSE) nr
                     FROM dcp_setback_controls WHERE id IN (695,696,698,702)
                    ORDER BY id""")
    print(f"\n--- {title}")
    for r in cur.fetchall():
        live = r['is_current'] and not r['nr']
        print(f"   id={r['id']:<4} {r['lga']:11} {str(r['dev_type'])[:18]:18} "
              f"{r['control_type']:14} {r['value_min']}{r['unit'] or ''} "
              f"cond={str(r['condition'])[:46]!r} {'SERVED' if live else 'excluded'}")

print("=" * 76)
print("DQ-32c repair —", "APPLY" if args.apply else "DRY RUN")
print("=" * 76)
show("BEFORE")

# What is left for camden secondary dwellings once 696 goes? Stated, not assumed.
cur.execute("""SELECT id, control_type, value_min, unit, condition
                 FROM dcp_setback_controls
                WHERE lga='camden' AND dev_type='secondary_dwelling'
                  AND is_current AND COALESCE(needs_review,FALSE)=FALSE
                ORDER BY control_type, id""")
rest = cur.fetchall()
print(f"\n--- camden secondary_dwelling, currently served: {len(rest)} controls")
for r in rest:
    print(f"   id={r['id']:<5} {r['control_type']:24} {r['value_min']}{r['unit'] or ''}"
          f"  cond={str(r['condition'])[:40]!r}")
print("   (after this repair, front_setback will be ABSENT rather than wrong)")

if not args.apply:
    print("\nDRY RUN — nothing written. Re-run with --apply.")
    sys.exit(0)

cur.execute(f"SELECT to_regclass('public.{BACKUP}') AS t")
if cur.fetchone()['t']:
    print(f"\nBackup {BACKUP} already exists — refusing to overwrite it.")
    sys.exit(1)
cur.execute(f"""CREATE TABLE {BACKUP} AS
                SELECT * FROM dcp_setback_controls WHERE id IN (696, 698)""")
cur.execute(f"SELECT count(*) AS n FROM {BACKUP}")
print(f"\nBackup {BACKUP}: {cur.fetchone()['n']} rows")

cur.execute("""UPDATE dcp_setback_controls
                  SET needs_review = TRUE, review_reason = %s, is_current = FALSE
                WHERE id = 696 AND is_current = TRUE""", (REVIEW_REASON_696,))
print(f"id=696 excluded: {cur.rowcount} row")
cur.execute("""UPDATE dcp_setback_controls SET condition = %s
                WHERE id = 698 AND (condition IS NULL OR btrim(condition) = '')""",
            (CONDITION_698,))
print(f"id=698 condition set: {cur.rowcount} row")
conn.commit()
show("AFTER")
conn.close()
