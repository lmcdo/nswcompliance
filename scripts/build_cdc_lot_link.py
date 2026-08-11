#!/usr/bin/env python3
"""Link every complying-development certificate to the lot it sits on, and
normalise its development types.

prior-art-checked: reuse not viable because nothing joins certificates to lots.
Four sweeps, 2026-08-10 against b5a4c1cf:
  (1) `git ls-files scripts/ | grep -iE "cdc|certificate|lot_index|lot_join"` ->
      only validate_lot_index.py, a READ-ONLY drift harness comparing
      lot_search_index LEP values against the live MapServer. Different concern.
  (2) `grep -rli "cdc_lot|certificates_by_lot|lots like this|comparable_approvals"`
      over services/ and frontend-nextjs/ -> ZERO.
  (3) information_schema tables matching cdc/certificate/lot_index ->
      complying_development_certificates (source), cdc_eligibility_standards
      (CDC *rules*, not certificates), lot_index_refresh_log (refresh logging).
      No link table exists.
  (4) lot_search_index joins LOTS to PLANNING CONTROLS. This joins CERTIFICATES
      to LOTS. Opposite direction, different key, no overlap.

WHY
---
The certificate table is the one asset here that is a record rather than a
derivation: 181,750 rows, 128 councils, July 2018 to date, arriving daily. It
answers "what actually got approved" -- but only per address, because it carries
no lot identifier of its own. Without a lot link you cannot ask the question
that makes it valuable: for a lot like THIS one, what got approved, how long did
it take, and what did it cost?

WHAT THIS BUILDS
----------------
One additive table, `cdc_lot_link`. Nothing existing is modified. Dropping the
table reverses this script completely.

  cdc_id        uuid  PK, the certificate
  lotidstring   text  the lot the certificate's coordinates fall inside
  lot_area_m2   float denormalised from the cadastre so "lots this size" does
                      not require a 3.2M-row join on every query
  dev_types     text[] development types, normalised (see below)
  match_status  text  matched | no_lot_at_point | no_coordinates
  linked_at     timestamptz

THE DEFECT THIS SCRIPT EXISTS TO NOT REPEAT
-------------------------------------------
`development_type` is jsonb, but it is stored in TWO different shapes:

  171,002 rows  a jsonb array       [{"DevelopmentType": "Dwelling house"}]
   10,748 rows  a jsonb STRING whose text is itself a JSON array --
                double-encoded: "[{\\"DevelopmentType\\": \\"Dwelling house\\"}]"

The obvious implementation guards with `jsonb_typeof(...) = 'array'` and lets
the rest fall through to NULL. That silently empties the "what was built" field
on 5.9% of the corpus, and a NULL there is indistinguishable from a certificate
that genuinely recorded no type. Measured before writing this: decoding the
string shape recovers all 10,748, leaving 0 undecodable, 36 explicitly-empty and
181,714 with types.

So dev_types is three-state and the states are distinguishable:
  {...}   types recorded
  {}      source explicitly recorded none (an empty array)
  NULL    could not decode -- currently zero rows, and if it ever becomes
          non-zero that is a real regression, not a shrug

THREE-STATE MATCHING, NOT TWO
-----------------------------
match_status distinguishes "we looked and the point is inside a lot" from "we
looked and it is not" from "we could not look because there are no coordinates".
A row is written for every certificate either way. Nothing is silently dropped:
an absent link must never be indistinguishable from an unattempted one. This is
also what makes the loop terminate -- a non-matching row still leaves the
pending set.

NO PRIMARY DEVELOPMENT TYPE
---------------------------
A certificate can carry several types ("Dwelling house" + "Swimming pool").
Picking one as primary would be inventing a ranking that no source states, so
the array is stored whole and left for the caller to filter.

IDEMPOTENT AND RESUMABLE
------------------------
Each batch selects only certificates with no row yet, so an interrupted run
resumes where it stopped and a completed run is a no-op. Re-running after new
certificates arrive links only the new ones -- the feed adds rows daily.

MEASURED BEFORE WRITING (2026-08-10, see .claude/.pre-impl-done.json)
  SRID          cadastre geom is 4326 on every row, 0 NULL geoms, so the
                ST_SetSRID(...,4326) literal needs no reprojection
  index         EXPLAIN ANALYZE confirms Index Scan using idx_cadastre_lots_geom
  cost          200 points in 230ms ~= 1.15ms/point -> a 2,000 batch is ~2.3s
                against a 30s ceiling; the full 181,750 is roughly 3.5 minutes
  coordinates   double precision, 0 rows outside the NSW bounding box

    python scripts/build_cdc_lot_link.py            # build or resume
    python scripts/build_cdc_lot_link.py --status   # report only, no writes
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from dotenv import load_dotenv

REPO_ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(REPO_ENV)

import psycopg2  # noqa: E402

BATCH = 2000
STATEMENT_TIMEOUT_MS = 30_000

DDL = """
CREATE TABLE IF NOT EXISTS cdc_lot_link (
    cdc_id       uuid PRIMARY KEY,
    lotidstring  text,
    lot_area_m2  double precision,
    dev_types    text[],
    match_status text NOT NULL,
    linked_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cdc_lot_link_lotidstring ON cdc_lot_link (lotidstring);
CREATE INDEX IF NOT EXISTS idx_cdc_lot_link_status      ON cdc_lot_link (match_status);
CREATE INDEX IF NOT EXISTS idx_cdc_lot_link_devtypes    ON cdc_lot_link USING GIN (dev_types);
CREATE INDEX IF NOT EXISTS idx_cdc_lot_link_area        ON cdc_lot_link (lot_area_m2);
"""

# One batch.
#
# `norm` collapses the two storage shapes of development_type into one jsonb
# array before anything unnests it -- see the module docstring. A row whose
# shape is neither yields NULL there, which is the "could not decode" state and
# is deliberately distinct from the empty array.
#
# LIMIT 1 inside the spatial lateral: a point can fall inside stacked strata
# parcels, so one is taken. That is a simplification, recorded here rather than
# hidden -- for a strata address the linked lot is the parcel footprint, not the
# individual unit.
BATCH_SQL = """
INSERT INTO cdc_lot_link (cdc_id, lotidstring, lot_area_m2, dev_types, match_status)
SELECT
    c.id,
    l.lotidstring,
    l.planlotarea,
    dt.types,
    CASE
        WHEN c.latitude IS NULL OR c.longitude IS NULL THEN 'no_coordinates'
        WHEN l.lotidstring IS NULL                     THEN 'no_lot_at_point'
        ELSE 'matched'
    END
FROM (
    SELECT
        c0.id,
        c0.latitude,
        c0.longitude,
        CASE jsonb_typeof(c0.development_type)
            WHEN 'array'  THEN c0.development_type
            WHEN 'string' THEN (c0.development_type #>> '{}')::jsonb
        END AS dt_norm
    FROM complying_development_certificates c0
    WHERE NOT EXISTS (SELECT 1 FROM cdc_lot_link k WHERE k.cdc_id = c0.id)
    LIMIT %s
) c
LEFT JOIN LATERAL (
    SELECT n.lotidstring, n.planlotarea
    FROM nsw_cadastre_lots n
    WHERE c.latitude IS NOT NULL
      AND c.longitude IS NOT NULL
      AND ST_Intersects(n.geom, ST_SetSRID(ST_MakePoint(c.longitude, c.latitude), 4326))
    LIMIT 1
) l ON TRUE
LEFT JOIN LATERAL (
    SELECT CASE
             WHEN c.dt_norm IS NULL THEN NULL
             ELSE COALESCE(
               (SELECT array_agg(DISTINCT e->>'DevelopmentType')
                  FROM jsonb_array_elements(c.dt_norm) e
                 WHERE e->>'DevelopmentType' IS NOT NULL),
               ARRAY[]::text[])
           END AS types
) dt ON TRUE
ON CONFLICT (cdc_id) DO NOTHING
"""


def connect(readonly: bool):
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        sys.exit("DATABASE_URL not set -- refusing to guess a connection.")
    conn = psycopg2.connect(url, connect_timeout=20)
    conn.set_session(readonly=readonly, autocommit=True)
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
    return conn, cur


def report(cur) -> None:
    cur.execute("SELECT count(*) FROM complying_development_certificates")
    total = cur.fetchone()[0]
    cur.execute("SELECT to_regclass('public.cdc_lot_link') IS NOT NULL")
    if not cur.fetchone()[0]:
        print(f"  certificates {total:,} - link table does not exist yet")
        return
    cur.execute("SELECT match_status, count(*) FROM cdc_lot_link GROUP BY 1 ORDER BY 2 DESC")
    rows = cur.fetchall()
    linked = sum(n for _, n in rows)
    print(f"  certificates {total:,} - linked {linked:,} - remaining {total - linked:,}")
    for status, n in rows:
        pct = 100 * n / linked if linked else 0
        print(f"    {status:<16} {n:>7,}  {pct:5.1f}%")
    cur.execute(
        """SELECT count(*) FILTER (WHERE dev_types IS NULL)            AS undecodable,
                  count(*) FILTER (WHERE dev_types = ARRAY[]::text[])  AS explicitly_none,
                  count(*) FILTER (WHERE array_length(dev_types,1) > 0) AS has_types
           FROM cdc_lot_link"""
    )
    u, e, h = cur.fetchone()
    print(f"    dev_types: {h:,} with types - {e:,} explicitly none - {u:,} undecodable")
    if u:
        print("    ^ undecodable is non-zero: a shape this script has not seen. Investigate.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="report only, no writes")
    ap.add_argument("--batch", type=int, default=BATCH)
    args = ap.parse_args()

    if args.status:
        conn, cur = connect(readonly=True)
        print("cdc_lot_link status")
        report(cur)
        conn.close()
        return 0

    conn, cur = connect(readonly=False)
    cur.execute(DDL)

    cur.execute("SELECT count(*) FROM complying_development_certificates")
    total = cur.fetchone()[0]
    print(f"certificates to link: {total:,}  (batch {args.batch})", flush=True)

    started = time.time()
    batch_no = 0
    while True:
        t0 = time.time()
        cur.execute(BATCH_SQL, (args.batch,))
        n = cur.rowcount
        if n == 0:
            break
        batch_no += 1
        if batch_no % 10 == 0 or batch_no == 1:
            cur.execute("SELECT count(*) FROM cdc_lot_link")
            linked = cur.fetchone()[0]
            print(
                f"  batch {batch_no:>3}  +{n:>5}  linked {linked:>7,}/{total:,}"
                f"  {time.time() - t0:5.1f}s",
                flush=True,
            )

    print(f"\ncomplete in {time.time() - started:.0f}s")
    report(cur)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
