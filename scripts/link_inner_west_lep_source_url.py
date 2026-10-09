"""OC-12: set documents.source_url on the Inner West LEP 2022 documents.

The URL is read from instrument_registry (the instrument the legislation monitor
checks weekly), never typed. Only NULL source_url rows are touched.
Dry run by default (rolled back); --apply commits. Run from the rule-scope worktree.
"""
import json
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), "..", "..", "..", ".env"))
apply = "--apply" in sys.argv
URL_SQL = ("SELECT legislation_url FROM instrument_registry "
           "WHERE instrument_key = 'inner_west_lep_2022' AND is_active")

c = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=30000")
cur = c.cursor()
cur.execute("SELECT current_database()")
print("db:", cur.fetchone()[0])
cur.execute(URL_SQL)
(url,), = cur.fetchall()
assert url.startswith("https://legislation.nsw.gov.au/") and "epi-2022-0457" in url, url
cur.execute("SELECT id, source_url FROM documents WHERE document_type = 'LEP' "
            "AND id LIKE 'Inner\\_West\\_Local\\_Environmental\\_Plan\\_2022%' ORDER BY id")
rows = cur.fetchall()
print(len(rows), "documents:", [r[0] for r in rows])
assert rows and all(r[1] is None and r[0].startswith("Inner_West_Local_Environmental_Plan_2022") for r in rows), rows
expected = len(rows)
ids = [r[0] for r in rows]
if apply:
    json.dump({"captured": "2026-10-09", "url_source": URL_SQL, "ids": ids,
               "restore": "UPDATE documents SET source_url = NULL WHERE id = ANY(%(ids)s);"},
              open("data/db_rollback_backups/documents_iw_lep_source_url_pre_2026-10-09.json", "w"), indent=2)
cur.execute("UPDATE documents SET source_url = %s WHERE document_type = 'LEP' "
            "AND id = ANY(%s) AND source_url IS NULL", (url, ids))
assert cur.rowcount == expected, (cur.rowcount, expected)
print("would set" if not apply else "set", cur.rowcount, "->", url)
(c.commit if apply else c.rollback)()
print("COMMITTED" if apply else "ROLLED BACK (dry run)")
c.close()
