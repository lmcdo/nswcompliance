#!/usr/bin/env python3
"""Run migration 034 and verify."""
import os
import sys
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Check existing columns
cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name = 'instrument_registry' AND column_name IN ('pco_instrument_id', 'austlii_url')"
)
existing = [r[0] for r in cur.fetchall()]
print(f"Existing columns: {existing}")

if len(existing) < 2:
    print("Running migration 034...")
    migration = (Path(__file__).parent.parent / "migrations" / "034_pco_instrument_ids.sql").read_text()
    cur.execute(migration)
    conn.commit()
    print("Migration applied.")
else:
    print("Columns already exist, seeding PCO IDs...")
    cur.execute("UPDATE instrument_registry SET pco_instrument_id = 'epi-2021-0714' WHERE instrument_key = 'sepp_housing_2021'")
    cur.execute("UPDATE instrument_registry SET pco_instrument_id = 'epi-2008-0572' WHERE instrument_key = 'sepp_exempt_complying_2008'")
    cur.execute("UPDATE instrument_registry SET pco_instrument_id = 'epi-2022-0457' WHERE instrument_key = 'inner_west_lep_2022'")
    cur.execute("UPDATE instrument_registry SET austlii_url = 'https://classic.austlii.edu.au/au/legis/nsw/consol_reg/sepp2021448/' WHERE instrument_key = 'sepp_housing_2021'")
    cur.execute("UPDATE instrument_registry SET austlii_url = 'https://classic.austlii.edu.au/au/legis/nsw/consol_reg/seppacdc2008721/' WHERE instrument_key = 'sepp_exempt_complying_2008'")
    conn.commit()
    print("PCO IDs and AustLII URLs seeded.")

# Verify
cur.execute(
    "SELECT instrument_key, pco_instrument_id, austlii_url, legislation_url "
    "FROM instrument_registry WHERE is_active = TRUE ORDER BY instrument_key"
)
print("\nInstrument registry state:")
for row in cur.fetchall():
    key, pco_id, austlii, leg = row
    print(f"  {key:<35} pco={pco_id or '—':<20} austlii={'Y' if austlii else 'N'}  leg={leg[:50]}...")

conn.close()
