#!/usr/bin/env python3
"""
Phase 0: DB setup for conveyancing hardcode fixes.
Safe to run multiple times — all statements are idempotent.

Creates:
  - control_type column on dcp_general_requirements
  - unique index for manual setback rows
  - lep_clauses table
  - 4 Inner West LEP 2022 seed rows
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
import psycopg2

def run():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    print("0A: Adding control_type column to dcp_general_requirements ...")
    cur.execute("""
        ALTER TABLE dcp_general_requirements
        ADD COLUMN IF NOT EXISTS control_type TEXT
          CHECK (control_type IS NULL OR control_type IN ('prescribed', 'site_derived'))
    """)

    print("0B: Creating unique index for manual setback rows ...")
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS dcp_manual_setbacks_uq
          ON dcp_general_requirements (former_council, category, subcategory, evidence_type)
          WHERE evidence_type = 'manual'
    """)

    print("0C: Creating lep_clauses table ...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lep_clauses (
            id             serial PRIMARY KEY,
            epi_name       text NOT NULL,
            clause_number  text NOT NULL,
            clause_heading text,
            plain_summary  text NOT NULL,
            source_ref     text NOT NULL,
            effective_date date NOT NULL,
            UNIQUE (epi_name, clause_number)
        )
    """)

    print("0D: Seeding lep_clauses with Inner West LEP 2022 rows ...")
    cur.execute("""
        INSERT INTO lep_clauses
          (epi_name, clause_number, clause_heading, plain_summary, source_ref, effective_date)
        VALUES
          ('Inner West Local Environmental Plan 2022', '4.3C',
           'Height of buildings — Key Sites',
           'Site-specific height controls apply to this lot — may differ from the zone-wide height limit.',
           'Inner West LEP 2022, Clause 4.3C', '2022-11-22'),
          ('Inner West Local Environmental Plan 2022', '4.4',
           'Floor Space Ratio',
           'Site-specific FSR controls apply via Clause 4.4 2B(c).',
           'Inner West LEP 2022, Clause 4.4', '2022-11-22'),
          ('Inner West Local Environmental Plan 2022', '6.14',
           'Affordable housing contribution',
           'Affordable housing contribution may be required for residential development on this lot.',
           'Inner West LEP 2022, Clause 6.14', '2022-11-22'),
          ('Inner West Local Environmental Plan 2022', '6.15',
           'Design excellence',
           'Design excellence process required for certain development types on this lot.',
           'Inner West LEP 2022, Clause 6.15', '2022-11-22')
        ON CONFLICT (epi_name, clause_number) DO NOTHING
    """)

    conn.commit()

    # Verify
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='dcp_general_requirements' AND column_name='control_type'")
    assert cur.fetchone(), "FAIL: control_type column not found"
    print("  OK control_type column present")

    cur.execute("SELECT indexname FROM pg_indexes WHERE indexname='dcp_manual_setbacks_uq'")
    assert cur.fetchone(), "FAIL: unique index not found"
    print("  OK dcp_manual_setbacks_uq index present")

    cur.execute("SELECT to_regclass('public.lep_clauses')")
    assert cur.fetchone()[0], "FAIL: lep_clauses table not found"
    print("  OK lep_clauses table present")

    cur.execute("SELECT COUNT(*) FROM lep_clauses WHERE epi_name = 'Inner West Local Environmental Plan 2022'")
    count = cur.fetchone()[0]
    assert count == 4, f"FAIL: expected 4 lep_clauses rows, got {count}"
    print(f"  OK lep_clauses seeded ({count} rows)")

    cur.close()
    conn.close()
    print("\nPhase 0 complete.")

if __name__ == "__main__":
    run()
