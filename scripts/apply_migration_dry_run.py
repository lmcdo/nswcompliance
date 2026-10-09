"""Run one migration inside a transaction and roll it back (default), or commit with --apply.

prior-art-checked: reuse not viable because no repo script applies a single
migration file with an explicit dry-run; each session hand-wrote this.
Usage: python scripts/apply_migration_dry_run.py migrations/NNN_x.sql [--apply] [--check "SELECT ..."]
"""
import os
import re
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
load_dotenv()
path = sys.argv[1]
apply = "--apply" in sys.argv
check = sys.argv[sys.argv.index("--check") + 1] if "--check" in sys.argv else None
sql = open(path, encoding="utf-8").read()
# Only the migration's own outer transaction lines are removed: a standalone
# BEGIN; / COMMIT; on its own line. Anything else is left untouched; a file with
# other copies of them is refused rather than rewritten (cross-review).
# The optional carriage return is there because files check out CRLF on Windows.
OUTER = re.compile(r"^[ \t]*(BEGIN|COMMIT);[ \t]*\r?$", re.M)
ANY = re.compile(r"\b(BEGIN|COMMIT);")
if len(OUTER.findall(sql)) != 2 or len(ANY.findall(sql)) != 2:
    sys.exit(f"{path}: expected exactly one standalone BEGIN; and COMMIT; -- refusing")
body = OUTER.sub("", sql)
conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=60000")
cur = conn.cursor()
cur.execute(body)
if check:
    cur.execute(check)
    print("check:", cur.fetchone()[0])
(conn.commit if apply else conn.rollback)()
print("COMMITTED" if apply else "ROLLED BACK (dry run)")
conn.close()
