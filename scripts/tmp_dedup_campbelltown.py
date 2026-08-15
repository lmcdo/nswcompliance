import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Mark old sparse rows as not current (superseded by our detailed extraction)
old_ids = [447, 449]  # dual_occupancy and semi_detached with no condition/source_text
cur.execute("""
UPDATE dcp_setback_controls SET is_current = false, needs_review = true,
    condition = COALESCE(condition, '') || ' [superseded by detailed extraction]'
WHERE id IN %s
""", (tuple(old_ids),))
print(f"Marked {cur.rowcount} old sparse rows as superseded")

# Also check the max_site_coverage rows 448, 450 — they have no value_max
cur.execute("SELECT id, control_type, dev_type, value_min, value_max, unit, condition FROM dcp_setback_controls WHERE id IN (448, 450)")
for r in cur.fetchall():
    print(f"  id={r[0]} {r[1]} {r[2]} min={r[3]} max={r[4]} {r[5]} | {r[6]}")

# Final count
cur.execute('SELECT COUNT(*) FROM dcp_setback_controls WHERE is_current = true')
print(f"\nTotal active rows: {cur.fetchone()[0]}")

conn.close()
