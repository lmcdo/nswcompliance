#!/usr/bin/env python3
"""
Comprehensive DCP Quality Report — Fit-for-Purpose Analysis

Evaluates whether extracted DCP provisions are structurally adequate
for compliance work by planners. Covers all quality dimensions:

  1. Granularity fitness     — are provisions at control level or mega-blobs?
  2. Structural markers      — do provisions contain splittable control markers?
  3. Topic tag accuracy      — do tagged topics match actual content?
  4. Actionability coverage  — what % can be compliance-checked?
  5. Rule extraction depth   — how many have deterministic numeric rules?
  6. Text quality            — artifacts, reversed text, LaTeX remnants?
  7. Coverage completeness   — are all expected DCP topics represented?
  8. Near-duplicate detection — are provisions repeated or overlapping?
  9. Page reference integrity — do provisions have traceable PDF page refs?
 10. Per-council fitness     — overall readiness score per council

Usage:
  python scripts/dcp_quality_report.py                   # all councils
  python scripts/dcp_quality_report.py --council ashfield # single council
  python scripts/dcp_quality_report.py --section 3       # single section
"""
import os, sys, re, argparse
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Config ──────────────────────────────────────────────────────────────────

# Granularity thresholds (chars)
IDEAL_MAX = 2000       # individual control level
ACCEPTABLE_MAX = 5000  # workable but coarse
OVERSIZED = 10000      # too large for compliance use
BLOB = 50000           # essentially unusable

# Expected DCP topics (canonical set for Inner West / typical LGA)
EXPECTED_TOPICS = {
    "parking", "setback", "height", "fsr", "heritage", "trees",
    "fencing", "signage", "landscaping", "stormwater", "waste",
    "privacy", "solar_access", "building_envelope", "access",
    "subdivision", "contamination", "flooding", "bushfire",
    "acoustic", "sustainability", "materials", "safety",
}

# Artifact patterns to detect in provision text
ARTIFACT_PATTERNS = [
    (r'\\mathrm', 'LaTeX \\mathrm'),
    (r'\\mathsf', 'LaTeX \\mathsf'),
    (r'\\prime', 'LaTeX \\prime'),
    (r'\\star', 'LaTeX \\star'),
    (r'\\circ', 'LaTeX \\circ'),
    (r'\\tt\b', 'LaTeX \\tt'),
    (r'\\because', 'LaTeX \\because'),
    (r'\$\s*_\s*\{', 'LaTeX subscript $_{'),
    (r'\$\s*\^\s*\{', 'LaTeX superscript $^{'),
    (r'\\underline', 'LaTeX \\underline'),
    (r'[a-z]{5,}(?:suoenallecsiM|ytilibaniatsuS|senilediuG|tcnicerP|niamoD|egatireH)',
     'Reversed text'),
    (r'(?<!\d)(\d(?:\s\d){2,})(?!\d)', 'Spaced digits'),
    (r'\$\s*\{[^}]*\}\s*\$', 'LaTeX math group'),
]

# Structural control marker patterns
CONTROL_MARKERS = {
    'PC': re.compile(r'(?m)^PC\d'),
    'DS': re.compile(r'(?m)^DS\d'),
    'O (Objective)': re.compile(r'(?m)^O\d'),
    'C (Control)': re.compile(r'(?m)^C\d'),
    'Numbered (X.Y)': re.compile(r'(?m)^\d+\.\d+\s+[A-Z]'),
    'Letter-prefix (B3.1)': re.compile(r'(?m)^[A-Z]\d+\.\d+'),
    'Clause': re.compile(r'(?m)^(?:Clause|clause)\s+\d'),
}

# Topic validation: keywords that should appear if topic is correct
TOPIC_KEYWORDS = {
    'parking': ['parking', 'car space', 'vehicle', 'garage', 'carpark'],
    'setback': ['setback', 'building line', 'boundary', 'front setback'],
    'height': ['height', 'storey', 'metres', 'building height', 'floor'],
    'fsr': ['floor space', 'fsr', 'floor area', 'gross floor'],
    'heritage': ['heritage', 'conservation', 'historic', 'contributory'],
    'trees': ['tree', 'canopy', 'vegetation', 'planting', 'landscape'],
    'fencing': ['fence', 'fencing', 'front fence', 'boundary fence'],
    'signage': ['sign', 'signage', 'advertising', 'display', 'illuminat'],
    'landscaping': ['landscap', 'garden', 'planting', 'open space', 'vegetation'],
    'stormwater': ['stormwater', 'drainage', 'water management', 'runoff'],
    'waste': ['waste', 'garbage', 'recycl', 'bin', 'collection'],
    'privacy': ['privacy', 'overlooking', 'window', 'screening'],
    'solar_access': ['solar', 'sunlight', 'shadow', 'overshadow'],
    'sustainability': ['sustainab', 'energy', 'basix', 'water efficien'],
}


def run_report(council_filter=None, section=None):
    conn = psycopg2.connect(os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    where = "WHERE is_current = true AND source_council IS NOT NULL"
    params = []
    if council_filter:
        where += " AND source_council = %s"
        params.append(council_filter)

    # ── Fetch all provisions ────────────────────────────────────────────
    cur.execute(f"""
        SELECT id, source_council, section_header, v2_topic, v2_is_actionable,
               v2_extraction_status, pdf_page, source_chapter_key,
               LENGTH(provision_text) as chars, provision_text
        FROM regulatory_provisions
        {where}
        ORDER BY source_council, id
    """, params)

    rows = cur.fetchall()
    if not rows:
        print("No provisions found.")
        return

    # Organize by council
    by_council = defaultdict(list)
    for r in rows:
        by_council[r[1]].append({
            'id': r[0], 'council': r[1], 'header': r[2], 'topic': r[3],
            'actionable': r[4], 'extraction_status': r[5], 'pdf_page': r[6],
            'chapter_key': r[7], 'chars': r[8], 'text': r[9],
        })

    councils = sorted(by_council.keys())
    total_provisions = len(rows)

    print("=" * 80)
    print("  DCP QUALITY REPORT — FIT-FOR-PURPOSE ANALYSIS")
    print(f"  {total_provisions} provisions across {len(councils)} councils")
    print("=" * 80)

    # ── Run all sections ────────────────────────────────────────────────
    section_runners = [
        (1, "GRANULARITY FITNESS", report_granularity),
        (2, "STRUCTURAL MARKERS", report_markers),
        (3, "TOPIC TAG ACCURACY", report_topic_accuracy),
        (4, "ACTIONABILITY COVERAGE", report_actionability),
        (5, "RULE EXTRACTION DEPTH", report_extraction),
        (6, "TEXT QUALITY (ARTIFACTS)", report_artifacts),
        (7, "COVERAGE COMPLETENESS", report_coverage),
        (8, "NEAR-DUPLICATE DETECTION", report_duplicates),
        (9, "PAGE REFERENCE INTEGRITY", report_pages),
        (10, "OVERALL FITNESS SCORECARD", report_scorecard),
    ]

    council_scores = {}
    for sec_num, sec_title, sec_fn in section_runners:
        if section and sec_num != section:
            continue

        print(f"\n{'─' * 80}")
        print(f"  {sec_num}. {sec_title}")
        print(f"{'─' * 80}")
        result = sec_fn(by_council, councils, council_scores)
        if result:
            council_scores.update(result)

    cur.close()
    conn.close()

    return council_scores


# ── Quality gate check ─────────────────────────────────────────────────

# Minimum thresholds per dimension for pipeline gate
GATE_THRESHOLDS = {
    'granularity': 50,     # ≥50% at ideal+acceptable level
    'text_quality': 95,    # ≥95% clean (no artifacts)
    'duplicates': 95,      # ≥95% unique
    'pages': 90,           # ≥90% have page refs
}

def check_gate(council_filter=None):
    """Run quality report and check if council passes the gate.

    Returns (passed: bool, failures: list[str]).
    """
    scores = run_report(council_filter=council_filter)
    if not scores:
        return False, ["No scores produced — no provisions found"]

    failures = []
    for council, dims in scores.items():
        for dim, threshold in GATE_THRESHOLDS.items():
            val = dims.get(dim, 0)
            if val < threshold:
                failures.append(
                    f"{council}: {dim} = {val:.1f}% (threshold: {threshold}%)"
                )

    return len(failures) == 0, failures


# ── Section 1: Granularity ──────────────────────────────────────────────

def report_granularity(by_council, councils, scores):
    print()
    print("  Thresholds: ideal <2K | acceptable <5K | oversized <10K | blob >50K")
    print()

    for council in councils:
        provs = by_council[council]
        sizes = [p['chars'] for p in provs]
        n = len(sizes)
        sizes_sorted = sorted(sizes)
        median = sizes_sorted[n // 2] if n else 0
        avg = sum(sizes) // n if n else 0
        mx = max(sizes) if sizes else 0

        ideal = sum(1 for s in sizes if s <= IDEAL_MAX)
        acceptable = sum(1 for s in sizes if IDEAL_MAX < s <= ACCEPTABLE_MAX)
        oversized = sum(1 for s in sizes if ACCEPTABLE_MAX < s <= OVERSIZED)
        blob_count = sum(1 for s in sizes if s > BLOB)
        over10k = sum(1 for s in sizes if s > OVERSIZED)

        pct_fit = (ideal + acceptable) / n * 100 if n else 0
        grade = "PASS" if pct_fit >= 80 else "WARN" if pct_fit >= 50 else "FAIL"

        print(f"  {council:15s} [{grade:4s}] {n:5d} provisions | median {median:6,d} chars | max {mx:6,d}")
        print(f"  {'':15s}  ideal: {ideal:4d} ({ideal/n*100:.0f}%) | "
              f"acceptable: {acceptable:3d} | oversized: {over10k:3d} | blobs(>50K): {blob_count:3d}")

        # Show the worst offenders
        worst = sorted(provs, key=lambda p: p['chars'], reverse=True)[:3]
        if worst and worst[0]['chars'] > OVERSIZED:
            for w in worst:
                if w['chars'] > OVERSIZED:
                    print(f"  {'':15s}  >> {w['chars']:,d} chars: {w['header'][:60]}")
        print()

        scores.setdefault(council, {})['granularity'] = pct_fit

    return scores


# ── Section 2: Structural Markers ───────────────────────────────────────

def report_markers(by_council, councils, scores):
    print()
    print("  Checks whether provisions contain internal control markers")
    print("  (PC/DS, O/C, numbered clauses) that could enable finer splitting.")
    print()

    for council in councils:
        provs = by_council[council]
        large = [p for p in provs if p['chars'] > ACCEPTABLE_MAX]
        if not large:
            print(f"  {council:15s} No oversized provisions — markers not needed")
            print()
            continue

        marker_counts = Counter()
        provs_with_markers = 0
        for p in large:
            found = False
            for name, pat in CONTROL_MARKERS.items():
                matches = pat.findall(p['text'])
                if matches:
                    marker_counts[name] += len(matches)
                    found = True
            if found:
                provs_with_markers += 1

        pct = provs_with_markers / len(large) * 100 if large else 0
        splittable = "YES" if pct >= 60 else "PARTIAL" if pct >= 30 else "NO"

        print(f"  {council:15s} {len(large)} oversized provisions | "
              f"{provs_with_markers} have markers ({pct:.0f}%) — splittable: {splittable}")
        for name, count in marker_counts.most_common(5):
            print(f"  {'':15s}  {name}: {count} markers found")
        print()

        scores.setdefault(council, {})['markers'] = pct

    return scores


# ── Section 3: Topic Tag Accuracy ───────────────────────────────────────

def report_topic_accuracy(by_council, councils, scores):
    print()
    print("  Samples provisions per topic and checks if content matches the tag.")
    print("  A 'mismatch' means the provision text lacks keywords for its topic.")
    print()

    for council in councils:
        provs = by_council[council]
        tagged = [p for p in provs if p['topic']]
        if not tagged:
            print(f"  {council:15s} No topic tags assigned")
            continue

        topic_groups = defaultdict(list)
        for p in tagged:
            topic_groups[p['topic']].append(p)

        total_checked = 0
        total_match = 0
        mismatches_by_topic = {}

        for topic, topic_provs in sorted(topic_groups.items()):
            keywords = TOPIC_KEYWORDS.get(topic)
            if not keywords:
                continue  # skip topics we can't validate

            # Check up to 20 provisions per topic
            sample = topic_provs[:20]
            matches = 0
            for p in sample:
                text_lower = p['text'].lower()
                if any(kw in text_lower for kw in keywords):
                    matches += 1

            total_checked += len(sample)
            total_match += matches
            pct = matches / len(sample) * 100
            if pct < 80:
                mismatches_by_topic[topic] = (len(sample), matches, pct)

        overall_pct = total_match / total_checked * 100 if total_checked else 0
        grade = "PASS" if overall_pct >= 85 else "WARN" if overall_pct >= 65 else "FAIL"

        print(f"  {council:15s} [{grade:4s}] {total_match}/{total_checked} samples match "
              f"({overall_pct:.0f}%) | {len(topic_groups)} topics tagged")

        if mismatches_by_topic:
            for topic, (checked, matched, pct) in sorted(
                mismatches_by_topic.items(), key=lambda x: x[1][2]
            ):
                print(f"  {'':15s}  >> {topic}: {matched}/{checked} match ({pct:.0f}%)")
        print()

        scores.setdefault(council, {})['topic_accuracy'] = overall_pct

    return scores


# ── Section 4: Actionability ────────────────────────────────────────────

def report_actionability(by_council, councils, scores):
    print()
    for council in councils:
        provs = by_council[council]
        n = len(provs)
        actionable = sum(1 for p in provs if p['actionable'] is True)
        not_act = sum(1 for p in provs if p['actionable'] is False)
        null = sum(1 for p in provs if p['actionable'] is None)

        pct = actionable / n * 100 if n else 0
        grade = "PASS" if pct >= 60 else "WARN" if pct >= 30 else "FAIL"

        print(f"  {council:15s} [{grade:4s}] {actionable:4d}/{n:4d} actionable ({pct:.0f}%) | "
              f"not-actionable: {not_act} | unclassified: {null}")

        scores.setdefault(council, {})['actionability'] = pct

    return scores


# ── Section 5: Rule Extraction ──────────────────────────────────────────

def report_extraction(by_council, councils, scores):
    print()
    print("  Of actionable provisions, how many have deterministic rules extracted?")
    print()

    for council in councils:
        provs = by_council[council]
        actionable = [p for p in provs if p['actionable'] is True]
        n = len(actionable)
        if n == 0:
            print(f"  {council:15s} No actionable provisions")
            continue

        complete = sum(1 for p in actionable if p['extraction_status'] == 'complete')
        needs_llm = sum(1 for p in actionable if p['extraction_status'] == 'review_needed')
        other = n - complete - needs_llm

        pct = complete / n * 100 if n else 0
        print(f"  {council:15s} {complete:4d}/{n:4d} deterministic ({pct:.0f}%) | "
              f"needs LLM: {needs_llm} | other: {other}")

        scores.setdefault(council, {})['extraction'] = pct

    return scores


# ── Section 6: Text Quality ─────────────────────────────────────────────

def report_artifacts(by_council, councils, scores):
    print()
    print("  Scans provision text for known artifact patterns.")
    print()

    for council in councils:
        provs = by_council[council]
        artifact_totals = Counter()
        affected_provs = set()

        for p in provs:
            for pattern, name in ARTIFACT_PATTERNS:
                if re.search(pattern, p['text']):
                    artifact_totals[name] += 1
                    affected_provs.add(p['id'])

        n = len(provs)
        affected = len(affected_provs)
        pct_clean = (n - affected) / n * 100 if n else 0
        grade = "PASS" if pct_clean >= 98 else "WARN" if pct_clean >= 90 else "FAIL"

        print(f"  {council:15s} [{grade:4s}] {pct_clean:.1f}% clean | "
              f"{affected}/{n} provisions have artifacts")

        if artifact_totals:
            for name, count in artifact_totals.most_common(5):
                print(f"  {'':15s}  {name}: {count}")
        print()

        scores.setdefault(council, {})['text_quality'] = pct_clean

    return scores


# ── Section 7: Coverage Completeness ────────────────────────────────────

def report_coverage(by_council, councils, scores):
    print()
    print("  Checks which standard DCP topics are present per council.")
    print()

    for council in councils:
        provs = by_council[council]
        topics_found = set()
        topic_counts = Counter()
        for p in provs:
            if p['topic']:
                topics_found.add(p['topic'])
                topic_counts[p['topic']] += 1

        covered = topics_found & EXPECTED_TOPICS
        missing = EXPECTED_TOPICS - topics_found
        extra = topics_found - EXPECTED_TOPICS

        pct = len(covered) / len(EXPECTED_TOPICS) * 100

        print(f"  {council:15s} {len(covered)}/{len(EXPECTED_TOPICS)} expected topics | "
              f"{len(extra)} additional | {len(topics_found)} total")

        # Top topics
        top5 = topic_counts.most_common(5)
        top_str = ", ".join(f"{t}({c})" for t, c in top5)
        print(f"  {'':15s}  top: {top_str}")

        if missing and len(missing) <= 10:
            print(f"  {'':15s}  missing: {', '.join(sorted(missing))}")
        print()

        scores.setdefault(council, {})['coverage'] = pct

    return scores


# ── Section 8: Near-Duplicate Detection ─────────────────────────────────

def report_duplicates(by_council, councils, scores):
    print()
    print("  Detects provisions with identical or near-identical text.")
    print()

    for council in councils:
        provs = by_council[council]
        # Hash first 200 chars for quick duplicate detection
        text_hashes = defaultdict(list)
        for p in provs:
            # Normalize: strip whitespace, lowercase, first 200 chars
            norm = re.sub(r'\s+', ' ', p['text'][:200]).strip().lower()
            text_hashes[norm].append(p['id'])

        dup_groups = {k: v for k, v in text_hashes.items() if len(v) > 1}
        dup_count = sum(len(v) - 1 for v in dup_groups.values())

        n = len(provs)
        pct_unique = (n - dup_count) / n * 100 if n else 100
        grade = "PASS" if pct_unique >= 98 else "WARN" if pct_unique >= 90 else "FAIL"

        print(f"  {council:15s} [{grade:4s}] {dup_count} duplicates in {len(dup_groups)} groups "
              f"| {pct_unique:.1f}% unique")

        if dup_groups:
            shown = 0
            for text_prefix, ids in sorted(dup_groups.items(), key=lambda x: -len(x[1])):
                if shown >= 3:
                    break
                print(f"  {'':15s}  {len(ids)}x: \"{text_prefix[:70]}...\"")
                shown += 1
        print()

        scores.setdefault(council, {})['duplicates'] = pct_unique

    return scores


# ── Section 9: Page Reference Integrity ─────────────────────────────────

def report_pages(by_council, councils, scores):
    print()
    print("  Checks if provisions have PDF page references for planner cross-ref.")
    print()

    for council in councils:
        provs = by_council[council]
        n = len(provs)
        has_page = sum(1 for p in provs if p['pdf_page'] is not None)
        null_page = n - has_page

        pct = has_page / n * 100 if n else 0
        grade = "PASS" if pct >= 95 else "WARN" if pct >= 70 else "FAIL"

        print(f"  {council:15s} [{grade:4s}] {has_page}/{n} have page refs ({pct:.0f}%)")

        if null_page > 0 and null_page <= 20:
            missing = [p for p in provs if p['pdf_page'] is None][:5]
            for m in missing:
                print(f"  {'':15s}  missing: ID {m['id']} — {m['header'][:50]}")
        print()

        scores.setdefault(council, {})['pages'] = pct

    return scores


# ── Section 10: Overall Scorecard ───────────────────────────────────────

def report_scorecard(by_council, councils, scores):
    print()
    print("  Weighted fitness score: granularity 30%, topic accuracy 20%,")
    print("  actionability 15%, extraction 15%, text quality 10%, pages 10%")
    print()

    weights = {
        'granularity': 0.30,
        'topic_accuracy': 0.20,
        'actionability': 0.15,
        'extraction': 0.15,
        'text_quality': 0.10,
        'pages': 0.10,
    }

    print(f"  {'Council':15s} {'Gran':>5s} {'Topic':>6s} {'Actn':>5s} {'Extr':>5s} "
          f"{'TxtQ':>5s} {'Page':>5s} {'SCORE':>7s} {'GRADE':>6s}")
    print(f"  {'─' * 15} {'─' * 5} {'─' * 6} {'─' * 5} {'─' * 5} "
          f"{'─' * 5} {'─' * 5} {'─' * 7} {'─' * 6}")

    for council in councils:
        s = scores.get(council, {})
        weighted = 0
        vals = {}
        for dim, w in weights.items():
            val = s.get(dim, 0)
            vals[dim] = val
            weighted += val * w

        grade = ("A" if weighted >= 85 else "B" if weighted >= 70
                 else "C" if weighted >= 55 else "D" if weighted >= 40 else "F")

        print(f"  {council:15s} {vals.get('granularity', 0):5.0f} "
              f"{vals.get('topic_accuracy', 0):6.0f} {vals.get('actionability', 0):5.0f} "
              f"{vals.get('extraction', 0):5.0f} {vals.get('text_quality', 0):5.0f} "
              f"{vals.get('pages', 0):5.0f} {weighted:7.1f} {grade:>6s}")

    print()
    print("  Grades: A (85+) ready for production | B (70-84) usable with caveats")
    print("         C (55-69) needs improvement   | D (40-54) significant gaps")
    print("         F (<40) not fit for purpose")
    print()

    return scores


# ── Main ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DCP Quality Report')
    parser.add_argument('--council', '-c', help='Filter to single council')
    parser.add_argument('--section', '-s', type=int, help='Run single section (1-10)')
    parser.add_argument('--gate', '-g', action='store_true',
                        help='Run quality gate check — exits 0 (pass) or 1 (fail)')
    args = parser.parse_args()

    if args.gate:
        passed, failures = check_gate(council_filter=args.council)
        if passed:
            print("\n  ✅ QUALITY GATE: PASSED")
            sys.exit(0)
        else:
            print("\n  ❌ QUALITY GATE: FAILED")
            for f in failures:
                print(f"     • {f}")
            sys.exit(1)
    else:
        run_report(council_filter=args.council, section=args.section)
