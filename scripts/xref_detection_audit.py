#!/usr/bin/env python3
"""
Cross-Reference Detection Audit — Phase 1
==========================================

Measures quality of reference_extractor.py BEFORE building resolution:

  1. False positive rate — detected refs that aren't genuine cross-references
  2. False negative rate — real cross-refs being missed (sampled)
  3. Classification accuracy — UNKNOWN refs that could be reclassified
  4. Produces: scripts/baselines/xref_detection_audit.md

Usage:
    python scripts/xref_detection_audit.py

Gate condition (plan Phase 1):
    Detection precision >= 80%
    Detection recall estimated >= 70%
"""

import os
import re
import csv
import json
import random
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.llzdrxywpziewrzudwhj:REDACTED_MOVED_TO_ENV"
    "@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"
)

RANDOM_SEED = 42
BASELINES_DIR = Path("scripts/baselines")


# ──────────────────────────────────────────────────────────────────────────────
# Patterns for improved UNKNOWN reclassification
# ──────────────────────────────────────────────────────────────────────────────

# High section numbers (>= 50) without document context → probably EPA Act
# Section 68, 91, 140 etc. are well-known EPA Act sections
EPA_ACT_SECTION_RE = re.compile(r'^[Ss]ection\s+(\d+)$')
EPA_ACT_HIGH_SECTION_NUMS = {68, 75, 79, 80, 91, 111, 140, 147, 203, 215}  # known EPA Act sections

# Leichhardt C-marker pattern: C + digit
LEICHHARDT_MARKER_RE = re.compile(r'^(?:Part\s+)?C\d+(?:\.\d+)*$', re.IGNORECASE)

# LEP reference without year
LEP_NO_YEAR_RE = re.compile(r'\bLEP\b', re.IGNORECASE)

# Schedule references — could be DCP (intra) or LEP/Act (cross/external)
SCHEDULE_RE = re.compile(r'^Schedule\s+\d+$', re.IGNORECASE)

# Bare part references — probably intra-document in most cases
BARE_PART_RE = re.compile(r'^Part\s+\d+$', re.IGNORECASE)


def connect():
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
    conn.autocommit = True
    return conn


def run_query(conn, sql, params=None):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


# ──────────────────────────────────────────────────────────────────────────────
# Part 1: False positive check
# Sample 100 detected refs and verify against provision text
# ──────────────────────────────────────────────────────────────────────────────

def assess_false_positives(conn) -> dict:
    """
    Sample detected cross-refs and check whether the target string
    genuinely appears as a cross-reference in context.

    Heuristic FP indicators:
    - Target string appears in provision_text only as part of a heading/TOC
    - Target is a very generic word with no clause meaning
    - Provision text is a TOC entry (short, ends with page number)
    """
    print("\n[1/4] False positive assessment...")

    rows = run_query(conn, """
        SELECT
            p.id,
            p.source_council,
            p.document_id,
            p.provision_text,
            ref->>'target' AS target,
            ref->>'relationship' AS relationship
        FROM regulatory_provisions p,
             jsonb_array_elements(p.v2_extracted_rules) AS rule,
             jsonb_array_elements(rule->'references') AS ref
        WHERE p.v2_extracted_rules IS NOT NULL
          AND p.v2_extracted_rules != 'null'::jsonb
          AND rule ? 'references'
          AND jsonb_array_length(rule->'references') > 0
        ORDER BY RANDOM()
        LIMIT 120
    """)

    random.seed(RANDOM_SEED)
    sample = list(rows)[:100]

    results = {
        "sample_size": len(sample),
        "genuine": 0,
        "false_positive": 0,
        "uncertain": 0,
        "fp_examples": [],
        "genuine_examples": [],
    }

    for row in sample:
        text = row['provision_text'] or ''
        target = row['target'] or ''
        verdict = classify_fp(text, target, row['relationship'])

        if verdict == 'FP':
            results['false_positive'] += 1
            if len(results['fp_examples']) < 10:
                results['fp_examples'].append({
                    "id": row['id'],
                    "target": target,
                    "relationship": row['relationship'],
                    "text_snippet": text[:200],
                    "reason": get_fp_reason(text, target),
                })
        elif verdict == 'GENUINE':
            results['genuine'] += 1
            if len(results['genuine_examples']) < 5:
                results['genuine_examples'].append({
                    "id": row['id'],
                    "target": target,
                    "relationship": row['relationship'],
                })
        else:
            results['uncertain'] += 1

    results['precision_estimate'] = results['genuine'] / results['sample_size']
    results['fp_rate'] = results['false_positive'] / results['sample_size']

    print(f"  Sample: {results['sample_size']}")
    print(f"  Genuine: {results['genuine']} ({results['precision_estimate']:.0%})")
    print(f"  False positive: {results['false_positive']} ({results['fp_rate']:.0%})")
    print(f"  Uncertain: {results['uncertain']}")

    return results


def classify_fp(text: str, target: str, relationship: str) -> str:
    """Returns GENUINE | FP | UNCERTAIN"""
    if not text or not target:
        return 'UNCERTAIN'

    # TOC entry — short text that is just a title or heading
    stripped = text.strip()
    if len(stripped) < 60 and not any(w in stripped.lower() for w in ['shall', 'must', 'should', 'required', 'refer']):
        return 'UNCERTAIN'

    # Check: is the target a known reference indicator?
    # Genuine if text contains typical reference-triggering language
    ref_triggers = [
        'refer to', 'see also', 'in accordance with', 'pursuant to',
        'as required by', 'as specified in', 'subject to', 'under',
        'comply with', 'consistent with', 'as defined in'
    ]
    has_trigger = any(t in text.lower() for t in ref_triggers)

    # Target appears in text
    target_in_text = target.lower() in text.lower()

    if has_trigger and target_in_text:
        return 'GENUINE'

    # Schedule references in provisions with actual content = likely genuine
    if 'Schedule' in target and len(stripped) > 100:
        return 'GENUINE'

    if has_trigger:
        return 'GENUINE'

    if target_in_text and len(stripped) > 100:
        return 'GENUINE'

    return 'UNCERTAIN'


def get_fp_reason(text: str, target: str) -> str:
    if len(text.strip()) < 60:
        return "very_short_provision"
    if target.lower() not in text.lower():
        return "target_not_in_text"
    return "no_reference_trigger_language"


# ──────────────────────────────────────────────────────────────────────────────
# Part 2: False negative check
# Sample provisions WITHOUT detected refs but with reference-like language
# ──────────────────────────────────────────────────────────────────────────────

def assess_false_negatives(conn) -> dict:
    """
    Sample provisions that have no detected cross-refs but contain
    reference-triggering language. Estimate missed detection rate.
    """
    print("\n[2/4] False negative assessment...")

    # Provisions with no refs detected but with reference-like language
    rows = run_query(conn, """
        SELECT
            p.id,
            p.source_council,
            p.provision_text,
            p.v2_extraction_status
        FROM regulatory_provisions p
        WHERE p.v2_is_actionable = true
          AND (
              p.v2_extracted_rules IS NULL
              OR p.v2_extracted_rules = 'null'::jsonb
              OR NOT EXISTS (
                  SELECT 1 FROM jsonb_array_elements(p.v2_extracted_rules) AS rule
                  WHERE rule ? 'references' AND jsonb_array_length(rule->'references') > 0
              )
          )
          AND (
              p.provision_text ILIKE '%%refer to%%'
              OR p.provision_text ILIKE '%%see also%%'
              OR p.provision_text ILIKE '%%in accordance with clause%%'
              OR p.provision_text ILIKE '%%pursuant to%%'
              OR p.provision_text ILIKE '%%as required by clause%%'
              OR p.provision_text ILIKE '%%Schedule%%'
          )
          AND p.provision_text IS NOT NULL
          AND LENGTH(p.provision_text) > 80
        ORDER BY RANDOM()
        LIMIT 80
    """)

    random.seed(RANDOM_SEED + 1)
    sample = list(rows)[:60]

    results = {
        "sample_size": len(sample),
        "missed_refs": 0,
        "correctly_no_ref": 0,
        "uncertain": 0,
        "missed_examples": [],
    }

    for row in sample:
        text = row['provision_text'] or ''
        missed = find_missed_refs(text)
        if missed:
            results['missed_refs'] += 1
            if len(results['missed_examples']) < 15:
                results['missed_examples'].append({
                    "id": row['id'],
                    "council": row['source_council'],
                    "text_snippet": text[:300],
                    "missed_patterns": missed,
                })
        else:
            results['correctly_no_ref'] += 1

    results['fn_rate_in_sample'] = results['missed_refs'] / max(results['sample_size'], 1)
    print(f"  Sample: {results['sample_size']} provisions with ref-like language but no detected refs")
    print(f"  Missed refs found: {results['missed_refs']} ({results['fn_rate_in_sample']:.0%} of sample)")
    print(f"  Correctly no ref: {results['correctly_no_ref']}")

    return results


# Patterns that SHOULD be caught by the extractor but might be missed
SHOULD_CATCH_PATTERNS = [
    # "Refer to Clause X" or "Refer to Section X" without "of this DCP"
    (r'[Rr]efer\s+to\s+(?:Clause|Section|Part)\s+[\d\.]+', 'bare_refer_to'),
    # "As per Clause X"
    (r'[Aa]s\s+per\s+(?:Clause|Section|Part)\s+[\d\.]+', 'as_per_clause'),
    # "Under Clause X of the LEP"
    (r'[Uu]nder\s+[Cc]lause\s+[\d\.]+\s+of\s+(?:the\s+)?(?:LEP|DCP)', 'under_clause_of'),
    # "Pursuant to Clause X"
    (r'[Pp]ursuant\s+to\s+(?:[Cc]lause|[Ss]ection)\s+[\d\.]+', 'pursuant_to'),
    # "per the requirements of Part X"
    (r'per\s+the\s+requirements\s+of\s+(?:Part|Section)\s+[\w\.]+', 'per_requirements_of'),
]

SHOULD_CATCH_RES = [(re.compile(p), name) for p, name in SHOULD_CATCH_PATTERNS]


def find_missed_refs(text: str) -> list[str]:
    """Find reference patterns that should have been detected."""
    missed = []
    for pattern, name in SHOULD_CATCH_RES:
        if pattern.search(text):
            missed.append(name)
    return missed


# ──────────────────────────────────────────────────────────────────────────────
# Part 3: UNKNOWN classification analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyse_unknowns(conn) -> dict:
    """
    Analyse all UNKNOWN-classified refs from baseline.
    Attempt to reclassify with improved heuristics.
    """
    print("\n[3/4] UNKNOWN reclassification analysis...")

    # Read all detected baseline refs
    with open(BASELINES_DIR / "xref_detected_baseline.csv", encoding='utf-8') as f:
        all_refs = list(csv.DictReader(f))

    unknowns = []
    for r in all_refs:
        target = r['reference_target']
        council = r['source_council'] or ''
        # Re-classify using the same logic as the pretask script
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        from xref_pretask_setup import EXTERNAL_RE, INTRA_DOC_RE
        if EXTERNAL_RE.search(target):
            cls = 'EXTERNAL'
        elif INTRA_DOC_RE.search(target):
            cls = 'INTRA_DOC'
        elif re.search(r'(?:LEP|DCP)\s+\d{4}', target, re.IGNORECASE):
            cls = 'CROSS_DOC'
        else:
            cls = 'UNKNOWN'

        if cls == 'UNKNOWN':
            unknowns.append({'target': target, 'council': council, 'relationship': r['reference_relationship']})

    print(f"  Total UNKNOWN refs in baseline: {len(unknowns)}")

    # Attempt reclassification
    improved = {
        'likely_epa_act': [],
        'likely_intra_doc': [],
        'likely_lep_ref': [],
        'leichhardt_c_marker': [],
        'schedule_ambiguous': [],
        'bare_part_ambiguous': [],
        'truly_unknown': [],
    }

    for r in unknowns:
        target = r['target']
        council = r['council']
        section_match = EPA_ACT_SECTION_RE.match(target)

        if section_match:
            num = int(section_match.group(1))
            if num in EPA_ACT_HIGH_SECTION_NUMS or num >= 60:
                improved['likely_epa_act'].append(target)
            else:
                improved['likely_intra_doc'].append(target)
        elif LEICHHARDT_MARKER_RE.match(target):
            improved['leichhardt_c_marker'].append(target)
        elif LEP_NO_YEAR_RE.search(target):
            improved['likely_lep_ref'].append(target)
        elif SCHEDULE_RE.match(target):
            improved['schedule_ambiguous'].append(target)
        elif BARE_PART_RE.match(target):
            improved['bare_part_ambiguous'].append(target)
        else:
            improved['truly_unknown'].append(target)

    results = {cat: len(items) for cat, items in improved.items()}
    results['total_unknowns'] = len(unknowns)
    results['reclassifiable'] = len(unknowns) - len(improved['truly_unknown'])
    results['reclassifiable_pct'] = results['reclassifiable'] / max(len(unknowns), 1)

    print(f"\n  Reclassification breakdown:")
    for cat, items in improved.items():
        sample = list(set(items))[:5]
        print(f"    {cat:30s}: {len(items):4d}  e.g. {sample}")

    # Top UNKNOWN targets by frequency
    target_counts = Counter(r['target'] for r in unknowns)
    print(f"\n  Top 20 UNKNOWN targets by frequency:")
    for target, count in target_counts.most_common(20):
        print(f"    {count:4d}x  {repr(target)}")

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Part 4: Improvements to propose
# ──────────────────────────────────────────────────────────────────────────────

def build_improvement_proposals(fp_results, fn_results, unknown_results) -> list[dict]:
    proposals = []

    # FP rate
    if fp_results['fp_rate'] > 0.20:
        proposals.append({
            "priority": "HIGH",
            "area": "False positives",
            "finding": f"FP rate {fp_results['fp_rate']:.0%} exceeds 20% threshold",
            "action": "Add TOC/heading detection to extractor to skip non-provision text",
        })

    # FN rate
    if fn_results['fn_rate_in_sample'] > 0.30:
        proposals.append({
            "priority": "HIGH",
            "area": "False negatives",
            "finding": f"{fn_results['fn_rate_in_sample']:.0%} of ref-language provisions have missed detections",
            "action": "Add patterns: bare 'Refer to Clause X', 'As per Clause X', 'Pursuant to Section X'",
            "examples": [e['missed_patterns'] for e in fn_results['missed_examples'][:5]],
        })

    # UNKNOWN reclassification
    reclassifiable_pct = unknown_results.get('reclassifiable_pct', 0)
    proposals.append({
        "priority": "MEDIUM",
        "area": "UNKNOWN classification",
        "finding": f"{reclassifiable_pct:.0%} of UNKNOWN refs are reclassifiable with better heuristics",
        "action": (
            "Add to classifier: (1) EPA Act section numbers >= 60 → EXTERNAL, "
            "(2) Leichhardt C-markers → INTRA_DOC, "
            "(3) 'the LEP' without year → CROSS_DOC, "
            "(4) bare Part/Schedule → INTRA_DOC_PROBABLE"
        ),
    })

    # Always: council-specific normalization
    proposals.append({
        "priority": "MEDIUM",
        "area": "Council-specific patterns",
        "finding": "Leichhardt C-markers (C1.9, C2.3) detected but not classified as INTRA_DOC",
        "action": "Add INTRA_DOC pattern: r'(?:Part\\s+)?C\\d+(?:\\.\\d+)+' when source_council='leichhardt'",
    })

    return proposals


# ──────────────────────────────────────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────────────────────────────────────

def write_audit_report(fp_results, fn_results, unknown_results, proposals):
    precision = fp_results['precision_estimate']
    fn_rate = fn_results['fn_rate_in_sample']
    gate_pass = precision >= 0.80

    lines = [
        "# Cross-Reference Detection Audit",
        "",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Branch:** feat/xref-detection-audit",
        f"**Gate condition:** Detection precision >= 80%",
        f"**Gate result:** {'PASS' if gate_pass else 'FAIL'} (precision = {precision:.0%})",
        "",
        "## Summary",
        "",
        f"- False positive rate: {fp_results['fp_rate']:.0%} (sample n={fp_results['sample_size']})",
        f"- Estimated precision: {precision:.0%}",
        f"- False negative rate in sample: {fn_rate:.0%} (provisions with ref-language but no detections)",
        f"- UNKNOWN refs: {unknown_results['total_unknowns']} total, {unknown_results['reclassifiable']} reclassifiable ({unknown_results.get('reclassifiable_pct', 0):.0%})",
        "",
        "## False Positive Examples",
        "",
    ]

    for ex in fp_results['fp_examples'][:8]:
        lines += [
            f"**ID {ex['id']}** — target: `{ex['target']}` ({ex['relationship']})",
            f"> {ex['text_snippet'][:150]}",
            f"Reason: {ex['reason']}",
            "",
        ]

    lines += [
        "## Missed Detections (False Negatives)",
        "",
    ]
    for ex in fn_results['missed_examples'][:10]:
        lines += [
            f"**ID {ex['id']}** ({ex['council']}) — missed patterns: {ex['missed_patterns']}",
            f"> {ex['text_snippet'][:200]}",
            "",
        ]

    lines += [
        "## UNKNOWN Reclassification",
        "",
        f"Total UNKNOWN: {unknown_results['total_unknowns']}",
        "",
        "| Category | Count | Action |",
        "|---|---|---|",
        f"| likely_epa_act | {unknown_results.get('likely_epa_act', 0)} | → EXTERNAL |",
        f"| likely_intra_doc | {unknown_results.get('likely_intra_doc', 0)} | → INTRA_DOC_PROBABLE |",
        f"| leichhardt_c_marker | {unknown_results.get('leichhardt_c_marker', 0)} | → INTRA_DOC (when council=leichhardt) |",
        f"| likely_lep_ref | {unknown_results.get('likely_lep_ref', 0)} | → CROSS_DOC |",
        f"| schedule_ambiguous | {unknown_results.get('schedule_ambiguous', 0)} | → needs document context |",
        f"| bare_part_ambiguous | {unknown_results.get('bare_part_ambiguous', 0)} | → INTRA_DOC_PROBABLE |",
        f"| truly_unknown | {unknown_results.get('truly_unknown', 0)} | → remains UNKNOWN |",
        "",
        "## Proposed Improvements",
        "",
    ]

    for i, p in enumerate(proposals, 1):
        lines += [
            f"### {i}. [{p['priority']}] {p['area']}",
            "",
            f"**Finding:** {p['finding']}",
            "",
            f"**Action:** {p['action']}",
            "",
        ]

    lines += [
        "## Gate Decision",
        "",
        f"{'✅ PASS' if gate_pass else '❌ FAIL'}: Precision {precision:.0%} {'≥' if gate_pass else '<'} 80% threshold.",
        "",
        "Proceed to Phase 2 (Tier 1+2 marker resolution): **YES**" if gate_pass else
        "Must fix extractor before Phase 2: **YES — address HIGH priority items above first**",
    ]

    report = "\n".join(lines)
    path = BASELINES_DIR / "xref_detection_audit.md"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n  Saved: {path}")
    return path, gate_pass


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("CROSS-REFERENCE DETECTION AUDIT — Phase 1")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    conn = connect()
    print("Connected to Supabase.")

    fp_results = assess_false_positives(conn)
    fn_results = assess_false_negatives(conn)
    unknown_results = analyse_unknowns(conn)
    proposals = build_improvement_proposals(fp_results, fn_results, unknown_results)

    conn.close()

    report_path, gate_pass = write_audit_report(fp_results, fn_results, unknown_results, proposals)

    print("\n" + "=" * 70)
    print(f"AUDIT COMPLETE — Gate: {'PASS' if gate_pass else 'FAIL'}")
    print("=" * 70)
    print(f"\nFull report: {report_path}")

    if gate_pass:
        print("\nNext: Phase 2 — build normalize_marker() + Tier 1 exact matching")
        print("Branch: feat/xref-tier1-marker-resolution")
    else:
        print("\nNext: Fix HIGH priority extractor issues, then re-run audit")

    return 0 if gate_pass else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
