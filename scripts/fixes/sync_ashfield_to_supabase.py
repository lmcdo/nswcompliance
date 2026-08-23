#!/usr/bin/env python3
"""Sync Ashfield Chapter F fixes to Supabase"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

LOCAL_DB = f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', '127.0.0.1')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'nsw_planning')}"
SUPABASE_DB = os.getenv('SUPABASE_DB_URL')

if not SUPABASE_DB:
    print("ERROR: SUPABASE_DB_URL not set")
    exit(1)

print("Syncing Ashfield fixes to Supabase...")

# Connect to both databases
local_conn = psycopg2.connect(LOCAL_DB)
local_cur = local_conn.cursor()

supa_conn = psycopg2.connect(SUPABASE_DB)
supa_cur = supa_conn.cursor()

# Get Ashfield provisions that were updated
local_cur.execute("""
    SELECT id, v2_is_actionable, v2_dcp_layer, v2_dcp_part,
           v2_applicable_zones, v2_applicable_dev_types, provision_text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND (v2_dcp_layer IS NOT NULL OR v2_is_actionable = true)
""")

provisions = local_cur.fetchall()
print(f"Found {len(provisions)} Ashfield provisions to sync")

# Update Supabase
updated = 0
for prov in provisions:
    prov_id, actionable, layer, part, zones, dev_types, text = prov

    supa_cur.execute("""
        UPDATE regulatory_provisions
        SET v2_is_actionable = %s,
            v2_dcp_layer = %s,
            v2_dcp_part = %s,
            v2_applicable_zones = %s,
            v2_applicable_dev_types = %s,
            provision_text = %s
        WHERE id = %s
    """, (actionable, layer, part, zones, dev_types, text, prov_id))

    if supa_cur.rowcount > 0:
        updated += 1

supa_conn.commit()
print(f"Updated {updated} provisions in Supabase")

# Verify
supa_cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND v2_dcp_layer = 'use_specific'
""")
print(f"Supabase use_specific count: {supa_cur.fetchone()[0]}")

local_conn.close()
supa_conn.close()
print("Done!")
