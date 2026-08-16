#!/usr/bin/env python3
"""Re-run layer + applicability tagging for Ku-ring-gai after adding ku-ring-gai alias."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_dcp_layer = NULL, v2_topic = NULL
    WHERE source_council = 'ku_ring_gai' AND is_current = true
    RETURNING id
""")
cleared = len(cur.fetchall())
conn.commit()
cur.close()
conn.close()
print(f"Cleared layer/topic tags for {cleared} provisions")

from enrichment.pipeline import run_layer_tagging, run_applicability_tagging

print("\n[1/2] Layer + topic tagging...")
run_layer_tagging(batch_size=500)

print("\n[2/2] Applicability tagging...")
run_applicability_tagging(batch_size=500)

print("\nDone.")
