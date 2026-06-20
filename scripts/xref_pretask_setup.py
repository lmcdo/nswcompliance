#!/usr/bin/env python3
"""
Cross-Reference Resolution — Pre-Task Setup
============================================

Runs ALL pre-task steps before any resolution code is written:

  1. Creates Supabase backup table (regulatory_provisions_backup_20260316_pre_xref)
  2. Verifies backup integrity (row count + jsonb spot-check)
  3. Captures baseline metrics → scripts/baselines/xref_baseline_metrics.json
  4. Exports current cross-ref detection state → scripts/baselines/xref_detected_baseline.csv
  5. Builds eval set skeleton (200 stratified provisions) → scripts/baselines/xref_eval_set.csv
     - Auto-labels EXTERNAL refs (SEPP, Act, state instruments)
     - Auto-labels intra-document refs where v2_marker match is unambiguous
     - Flags remainder as "needs_review" with top candidates provided
  6. Documents rollback procedure → scripts/baselines/ROLLBACK_PROCEDURE.md

Run ONCE. Idempotent: checks for existing backup before creating.

Usage:
    python scripts/xref_pretask_setup.py

Output artifacts (all committed to git):
    scripts/baselines/xref_baseline_metrics.json
    scripts/baselines/xref_detected_baseline.csv
    scripts/baselines/xref_eval_set.csv
    scripts/baselines/ROLLBACK_PROCEDURE.md
"""

import os
import sys
import json
import csv
import re
import random
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import psycopg2
import psycopg2.extras

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.llzdrxywpziewrzudwhj:REDACTED_MOVED_TO_ENV"
    "@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"
)

BACKUP_TABLE = "regulatory_provisions_backup_20260316_pre_xref"
EVAL_SET_SIZE = 200
BASELINES_DIR = Path("scripts/baselines")
RANDOM_SEED = 42

# External instrument patterns → label EXTERNAL (no internal provision_id)
EXTERNAL_PATTERNS = [
    r'\bSEPP\b',
    r'State Environmental Planning Policy',
    r'\bEPA Act\b',
    r'Environmental Planning and Assessment Act',
    r'\bBCA\b',
    r'Building Code of Australia',
    r'National Construction Code',
    r'Australian Standards?\b',
    r'\bAS\s+\d{4}',
    r'Roads Act',
    r'Heritage Act',
    r'Biodiversity Conservation Act',
]

# Intra-document patterns — target is in the same document
INTRA_DOC_PATTERNS = [
    r'of this (?:DCP|Development Control Plan|Plan)',
    r'in this (?:DCP|Development Control Plan|Plan)',
    r'this Development Control Plan',
    r'this (?:section|chapter|part)\b',
]

EXTERNAL_RE = re.compile('|'.join(EXTERNAL_PATTERNS), re.IGNORECASE)
INTRA_DOC_RE = re.compile('|'.join(INTRA_DOC_PATTERNS), re.IGNORECASE)

# Marker extraction: pull the code part from reference strings
# "Part C1.9" → "C1.9", "Clause 4.6" → "4.6", "Section B3" → "B3"
MARKER_EXTRACT_RE = re.compile(
    r'(?:Part|Section|Clause|Chapter|cl\.?)\s+([A-Z]?\d+(?:\.\d+)*(?:\.\d+)*)',
    re.IGNORECASE
)


# ──────────────────────────────────────────────────────────────────────────────
# DB helpers
# ──────────────────────────────────────────────────────────────────────────────

def connect():
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
    conn.autocommit = False
    return conn


def run_query(conn, sql, params=None, fetch=True):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
        return cur.rowcount


# ──────────────────────────────────────────────────────────────────────────────
# Step 1 + 2: Backup
# ──────────────────────────────────────────────────────────────────────────────

def create_backup(conn):
    print("\n[1/6] Creating Supabase backup table...")

    # Check if already exists
    exists = run_query(conn, """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = %s
        )
    """, (BACKUP_TABLE,))

    if exists[0]['exists']:
        print(f"  SKIP: {BACKUP_TABLE} already exists")
        # Still verify it
    else:
        print(f"  Creating {BACKUP_TABLE} ...")
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE {BACKUP_TABLE}
                AS SELECT * FROM regulatory_provisions
            """)
            conn.commit()
        print(f"  Created.")

    # Verify
    print("\n[2/6] Verifying backup integrity...")

    live_count = run_query(conn, "SELECT COUNT(*) AS n FROM regulatory_provisions")[0]['n']
    backup_count = run_query(conn, f"SELECT COUNT(*) AS n FROM {BACKUP_TABLE}")[0]['n']

    print(f"  Live table:   {live_count:,} rows")
    print(f"  Backup table: {backup_count:,} rows")

    if live_count != backup_count:
        print(f"  ERROR: Row count mismatch! Backup incomplete.")
        sys.exit(1)

    # Spot-check jsonb column
    spot = run_query(conn, f"""
        SELECT id, v2_extracted_rules IS NOT NULL AS has_rules
        FROM {BACKUP_TABLE}
        WHERE v2_extracted_rules IS NOT NULL
        LIMIT 5
    """)
    print(f"  jsonb spot-check: {len(spot)} rows with v2_extracted_rules (expected >0)")
    if len(spot) == 0:
        print("  WARNING: No rows with v2_extracted_rules in backup — may be pre-enrichment")

    print(f"  PASS: Backup verified ({live_count:,} rows)")
    return live_count


# ──────────────────────────────────────────────────────────────────────────────
# Step 3: Baseline metrics
# ──────────────────────────────────────────────────────────────────────────────

def capture_baseline(conn, live_count):
    print("\n[3/6] Capturing baseline metrics...")

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "backup_table": BACKUP_TABLE,
        "total_provisions": live_count,
    }

    # Extraction status distribution
    status_dist = run_query(conn, """
        SELECT
            COALESCE(v2_extraction_status, 'null') AS status,
            COUNT(*) AS n
        FROM regulatory_provisions
        GROUP BY 1
        ORDER BY n DESC
    """)
    metrics["extraction_status"] = {r['status']: r['n'] for r in status_dist}
    print(f"  Extraction status: {metrics['extraction_status']}")

    # How many provisions have v2_extracted_rules populated
    with_rules = run_query(conn, """
        SELECT COUNT(*) AS n FROM regulatory_provisions
        WHERE v2_extracted_rules IS NOT NULL
          AND v2_extracted_rules != 'null'::jsonb
          AND jsonb_array_length(v2_extracted_rules) > 0
    """)[0]['n']
    metrics["provisions_with_extracted_rules"] = with_rules
    print(f"  Provisions with extracted rules: {with_rules:,}")

    # Cross-ref counts — provisions that have at least one reference
    xref_provision_count = run_query(conn, """
        SELECT COUNT(DISTINCT p.id) AS n
        FROM regulatory_provisions p,
             jsonb_array_elements(p.v2_extracted_rules) AS rule
        WHERE p.v2_extracted_rules IS NOT NULL
          AND p.v2_extracted_rules != 'null'::jsonb
          AND rule ? 'references'
          AND jsonb_array_length(rule->'references') > 0
    """)[0]['n']
    metrics["provisions_with_cross_refs"] = xref_provision_count
    print(f"  Provisions with detected cross-refs: {xref_provision_count:,}")

    # Cross-ref by relationship type
    rel_dist = run_query(conn, """
        SELECT
            ref->>'relationship' AS relationship,
            COUNT(*) AS n
        FROM regulatory_provisions p,
             jsonb_array_elements(p.v2_extracted_rules) AS rule,
             jsonb_array_elements(rule->'references') AS ref
        WHERE p.v2_extracted_rules IS NOT NULL
          AND p.v2_extracted_rules != 'null'::jsonb
          AND rule ? 'references'
          AND jsonb_array_length(rule->'references') > 0
        GROUP BY 1
        ORDER BY n DESC
    """)
    metrics["cross_refs_by_relationship"] = {r['relationship']: r['n'] for r in rel_dist}
    print(f"  Cross-ref relationship distribution: {metrics['cross_refs_by_relationship']}")

    # Cross-ref by council
    council_dist = run_query(conn, """
        SELECT
            p.source_council,
            COUNT(DISTINCT p.id) AS provisions,
            COUNT(*) AS total_refs
        FROM regulatory_provisions p,
             jsonb_array_elements(p.v2_extracted_rules) AS rule,
             jsonb_array_elements(rule->'references') AS ref
        WHERE p.v2_extracted_rules IS NOT NULL
          AND p.v2_extracted_rules != 'null'::jsonb
          AND rule ? 'references'
          AND jsonb_array_length(rule->'references') > 0
        GROUP BY 1
        ORDER BY provisions DESC
    """)
    metrics["cross_refs_by_council"] = [
        {"council": r['source_council'], "provisions": r['provisions'], "total_refs": r['total_refs']}
        for r in council_dist
    ]
    print(f"  Cross-refs by council:")
    for c in metrics["cross_refs_by_council"]:
        print(f"    {c['council']}: {c['provisions']} provisions, {c['total_refs']} refs")

    # Resolution status (new fields not yet populated — expect zeros)
    resolved_count = run_query(conn, """
        SELECT COUNT(*) AS n
        FROM regulatory_provisions p,
             jsonb_array_elements(p.v2_extracted_rules) AS rule,
             jsonb_array_elements(rule->'references') AS ref
        WHERE p.v2_extracted_rules IS NOT NULL
          AND p.v2_extracted_rules != 'null'::jsonb
          AND rule ? 'references'
          AND jsonb_array_length(rule->'references') > 0
          AND ref ? 'resolved_provision_id'
    """)[0]['n']
    metrics["cross_refs_already_resolved"] = resolved_count
    print(f"  Already resolved cross-refs: {resolved_count} (expected 0 before this work)")

    return metrics


# ──────────────────────────────────────────────────────────────────────────────
# Step 4: Export full detected cross-ref baseline CSV
# ──────────────────────────────────────────────────────────────────────────────

def export_detected_baseline(conn):
    print("\n[4/6] Exporting detected cross-refs baseline...")

    rows = run_query(conn, """
        SELECT
            p.id AS provision_id,
            p.source_council,
            p.document_id,
            p.v2_marker,
            LEFT(p.provision_text, 500) AS provision_text_preview,
            ref->>'target' AS reference_target,
            ref->>'relationship' AS reference_relationship
        FROM regulatory_provisions p,
             jsonb_array_elements(p.v2_extracted_rules) AS rule,
             jsonb_array_elements(rule->'references') AS ref
        WHERE p.v2_extracted_rules IS NOT NULL
          AND p.v2_extracted_rules != 'null'::jsonb
          AND rule ? 'references'
          AND jsonb_array_length(rule->'references') > 0
        ORDER BY p.source_council, p.document_id, p.id
    """)

    print(f"  Total detected cross-ref instances: {len(rows):,}")

    outpath = BASELINES_DIR / "xref_detected_baseline.csv"
    with open(outpath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'provision_id', 'source_council', 'document_id', 'v2_marker',
            'provision_text_preview', 'reference_target', 'reference_relationship'
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Saved: {outpath} ({len(rows):,} rows)")
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Step 5: Build eval set skeleton
# ──────────────────────────────────────────────────────────────────────────────

def classify_reference(target: str) -> str:
    """Classify reference type: EXTERNAL | INTRA_DOC | CROSS_DOC | UNKNOWN"""
    if EXTERNAL_RE.search(target):
        return "EXTERNAL"
    if INTRA_DOC_RE.search(target):
        return "INTRA_DOC"
    # Cross-document: contains council name + LEP/DCP + year
    if re.search(r'(?:LEP|DCP)\s+\d{4}', target, re.IGNORECASE):
        return "CROSS_DOC"
    return "UNKNOWN"


def extract_marker_code(target: str) -> str | None:
    """Pull clause/section code from reference string."""
    m = MARKER_EXTRACT_RE.search(target)
    if m:
        return m.group(1)
    return None


def attempt_intra_doc_resolution(conn, document_id: str, target: str) -> list[dict]:
    """Try to find the target provision within the same document."""
    marker_code = extract_marker_code(target)
    if not marker_code:
        return []

    candidates = run_query(conn, """
        SELECT id, v2_marker, LEFT(provision_text, 200) AS text_preview
        FROM regulatory_provisions
        WHERE document_id = %s
          AND v2_marker ILIKE %s
        LIMIT 5
    """, (document_id, f'%{marker_code}%'))

    return [dict(c) for c in candidates]


def build_eval_set(conn, all_rows: list[dict]) -> list[dict]:
    print(f"\n[5/6] Building eval set (target: {EVAL_SET_SIZE} provisions)...")

    random.seed(RANDOM_SEED)

    # Deduplicate to one row per (provision_id, reference_target)
    seen = set()
    unique_rows = []
    for r in all_rows:
        key = (r['provision_id'], r['reference_target'])
        if key not in seen:
            seen.add(key)
            unique_rows.append(dict(r))

    print(f"  Unique (provision, ref) pairs: {len(unique_rows):,}")

    # Classify each reference
    for r in unique_rows:
        r['ref_class'] = classify_reference(r['reference_target'])

    # Stratified sampling
    by_class = defaultdict(list)
    for r in unique_rows:
        by_class[r['ref_class']].append(r)

    print(f"  Reference classes:")
    for cls, items in sorted(by_class.items()):
        print(f"    {cls}: {len(items)}")

    # Target allocation:
    #   INTRA_DOC: 90 (most common, most resolvable — needs biggest coverage)
    #   EXTERNAL:  40 (should all be labeled EXTERNAL — easy ground truth)
    #   CROSS_DOC: 40 (cross-document resolution — medium difficulty)
    #   UNKNOWN:   30 (hardest, diverse patterns)
    target_alloc = {
        "INTRA_DOC": 90,
        "EXTERNAL": 40,
        "CROSS_DOC": 40,
        "UNKNOWN": 30,
    }

    sampled = []
    for cls, target_n in target_alloc.items():
        pool = by_class.get(cls, [])
        n = min(target_n, len(pool))
        sampled.extend(random.sample(pool, n))
        print(f"  Sampled {n}/{target_n} from {cls}")

    # If under 200, top up from whatever's available
    if len(sampled) < EVAL_SET_SIZE:
        already_sampled_ids = {(r['provision_id'], r['reference_target']) for r in sampled}
        remaining = [
            r for r in unique_rows
            if (r['provision_id'], r['reference_target']) not in already_sampled_ids
        ]
        top_up = min(EVAL_SET_SIZE - len(sampled), len(remaining))
        sampled.extend(random.sample(remaining, top_up))
        print(f"  Top-up: added {top_up} more to reach {len(sampled)}")

    print(f"  Final eval set size: {len(sampled)}")

    # Attempt auto-labeling
    print("  Auto-labeling...")
    eval_rows = []
    auto_labeled = 0
    external_labeled = 0
    needs_review = 0

    for r in sampled:
        eval_row = {
            "provision_id": r['provision_id'],
            "source_council": r['source_council'],
            "document_id": r['document_id'],
            "v2_marker": r['v2_marker'],
            "provision_text_preview": r['provision_text_preview'],
            "reference_target": r['reference_target'],
            "reference_relationship": r['reference_relationship'],
            "ref_class": r['ref_class'],
            # Ground truth fields — to be filled
            "correct_provision_id": "",
            "correct_label": "",   # EXTERNAL | INTRA_DOC_RESOLVED | CROSS_DOC_RESOLVED | UNRESOLVABLE
            "resolution_notes": "",
            "auto_candidates": "",
        }

        if r['ref_class'] == "EXTERNAL":
            eval_row["correct_label"] = "EXTERNAL"
            eval_row["correct_provision_id"] = "EXTERNAL"
            eval_row["resolution_notes"] = "Auto-labeled: references external instrument (SEPP/Act)"
            external_labeled += 1

        elif r['ref_class'] == "INTRA_DOC":
            candidates = attempt_intra_doc_resolution(conn, r['document_id'], r['reference_target'])
            if len(candidates) == 1:
                # Unambiguous single match → auto-label
                eval_row["correct_provision_id"] = str(candidates[0]['id'])
                eval_row["correct_label"] = "INTRA_DOC_RESOLVED"
                eval_row["resolution_notes"] = (
                    f"Auto-labeled: single marker match "
                    f"v2_marker={candidates[0]['v2_marker']}"
                )
                auto_labeled += 1
            elif len(candidates) > 1:
                eval_row["correct_label"] = "needs_review"
                eval_row["auto_candidates"] = " | ".join(
                    f"{c['id']}[{c['v2_marker']}]" for c in candidates
                )
                eval_row["resolution_notes"] = f"Multiple marker matches ({len(candidates)}) — review required"
                needs_review += 1
            else:
                eval_row["correct_label"] = "needs_review"
                eval_row["resolution_notes"] = "No marker match found in document"
                needs_review += 1

        else:
            eval_row["correct_label"] = "needs_review"
            eval_row["resolution_notes"] = f"Class={r['ref_class']} — manual review required"
            needs_review += 1

        eval_rows.append(eval_row)

    print(f"  Auto-labeled EXTERNAL:     {external_labeled}")
    print(f"  Auto-labeled INTRA_DOC:    {auto_labeled}")
    print(f"  Needs manual review:       {needs_review}")
    print(f"  Total labeled/semi-labeled: {external_labeled + auto_labeled} / {len(eval_rows)}")

    return eval_rows


# ──────────────────────────────────────────────────────────────────────────────
# Step 6: Write rollback procedure
# ──────────────────────────────────────────────────────────────────────────────

def write_rollback_procedure(live_count: int):
    print("\n[6/6] Writing rollback procedure...")

    content = f"""# Cross-Reference Resolution — Rollback Procedure

**Created:** {datetime.now().isoformat()}
**Backup table:** `{BACKUP_TABLE}`
**Row count at backup time:** {live_count:,}

## When to rollback

- Resolution pipeline produced wrong resolutions at scale (>2% false positive rate)
- Schema change caused unexpected data corruption
- QA check on eval set fails after enrichment run

## Rollback steps

### Option A: Revert v2_extracted_rules only (preferred)

If resolution data was appended to the `references` array within `v2_extracted_rules`,
revert just that field:

```sql
-- Verify counts first
SELECT COUNT(*) FROM {BACKUP_TABLE};
SELECT COUNT(*) FROM regulatory_provisions;

-- Revert (SLOW — ~47k rows, run during off-peak)
UPDATE regulatory_provisions r
SET v2_extracted_rules = b.v2_extracted_rules
FROM {BACKUP_TABLE} b
WHERE r.id = b.id;

-- Verify
SELECT COUNT(*) FROM regulatory_provisions WHERE v2_extracted_rules IS NOT NULL;
```

### Option B: Drop new table(s) only

If resolution data was stored in a new `provision_cross_refs` table:

```sql
DROP TABLE IF EXISTS provision_cross_refs;
-- v2_extracted_rules is untouched, no provision data changed
```

### Option C: Full table restore (nuclear option)

Only if schema columns were added AND data was corrupted:

```sql
-- Drop and recreate from backup (extreme — loses any other changes since backup)
-- NEVER run without explicit confirmation
DROP TABLE regulatory_provisions;
ALTER TABLE {BACKUP_TABLE} RENAME TO regulatory_provisions;
```

**Option C requires re-applying any unrelated changes made after {datetime.now().strftime('%Y-%m-%d')}.**
Do NOT use Option C without checking git log for any other DB changes made after this backup.

## Verify rollback succeeded

```sql
SELECT v2_extraction_status, COUNT(*)
FROM regulatory_provisions
GROUP BY 1;
-- Should match baseline_metrics.json extraction_status values exactly
```

## Keep the backup table

Do NOT drop `{BACKUP_TABLE}` until cross-ref resolution is:
- Fully deployed and validated
- QA report signed off
- At least 30 days of production running without incidents

```sql
-- Only when safe to drop:
DROP TABLE {BACKUP_TABLE};
```
"""

    outpath = BASELINES_DIR / "ROLLBACK_PROCEDURE.md"
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Saved: {outpath}")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("CROSS-REFERENCE RESOLUTION — PRE-TASK SETUP")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Create output dir
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {BASELINES_DIR.resolve()}")

    conn = connect()
    print("Connected to Supabase.")

    try:
        # Steps 1+2: Backup + verify
        live_count = create_backup(conn)

        # Step 3: Baseline metrics
        metrics = capture_baseline(conn, live_count)

        # Save metrics
        metrics_path = BASELINES_DIR / "xref_baseline_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"\n  Saved metrics: {metrics_path}")

        # Step 4: Export all detected cross-refs
        all_rows = export_detected_baseline(conn)

        # Step 5: Build eval set
        eval_rows = build_eval_set(conn, all_rows)

        eval_path = BASELINES_DIR / "xref_eval_set.csv"
        fieldnames = [
            "provision_id", "source_council", "document_id", "v2_marker",
            "provision_text_preview", "reference_target", "reference_relationship",
            "ref_class", "correct_provision_id", "correct_label",
            "resolution_notes", "auto_candidates",
        ]
        with open(eval_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(eval_rows)
        print(f"  Saved eval set: {eval_path} ({len(eval_rows)} rows)")

        # Step 6: Rollback procedure
        write_rollback_procedure(live_count)

    finally:
        conn.close()

    print("\n" + "=" * 70)
    print("PRE-TASK SETUP COMPLETE")
    print("=" * 70)
    print("\nArtifacts created:")
    for f in sorted(BASELINES_DIR.iterdir()):
        size = f.stat().st_size
        print(f"  {f.name}  ({size:,} bytes)")
    print("\nNext steps:")
    print("  1. Commit scripts/baselines/ to git")
    print("  2. Manually review xref_eval_set.csv — label 'needs_review' rows")
    print("  3. Read ce-cross-ref-resolution.md plan before writing any code")
    print("  4. Run resolution in staged rollout (Inner West first)")


if __name__ == "__main__":
    main()
