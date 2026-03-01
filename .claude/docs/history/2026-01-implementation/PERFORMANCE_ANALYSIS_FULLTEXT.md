#!/usr/bin/env python3
"""
Benchmark current text search performance (without full-text search)
"""

import sys
import time
sys.path.append('venv_linux/lib/python3.11/site-packages')
from db_safety_wrapper import get_safe_connection

def benchmark_text_searches():
    """Benchmark text search performance"""

    conn = get_safe_connection()
    conn.connect()
    cur = conn.cursor()

    print("\n" + "="*80)
    print("BENCHMARKING CURRENT TEXT SEARCH PERFORMANCE")
    print("="*80)
    print("\nCurrent method: ILIKE (case-insensitive pattern matching)")
    print("Database: 22,648 provisions to search")
    print("-" * 80)

    benchmarks = []

    # ========================================================================
    # BENCHMARK 1: Simple keyword search
    # ========================================================================

    print("\n[BENCHMARK 1] Simple keyword search: 'setback'")
    print("-" * 80)

    # Explain query plan
    cur.execute("""
        EXPLAIN ANALYZE
        SELECT id, ref_number, LEFT(provision_text, 100) as preview
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%setback%'
        AND is_canonical = TRUE
        LIMIT 20
    """)

    plan = cur.fetchall()
    print("\nQuery Plan:")
    for line in plan:
        print(f"  {line[0]}")

    # Actual benchmark
    start = time.time()
    cur.execute("""
        SELECT id, ref_number, LEFT(provision_text, 100) as preview
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%setback%'
        AND is_canonical = TRUE
        LIMIT 20
    """)
    results = cur.fetchall()
    duration_ms = (time.time() - start) * 1000

    print(f"\nResults: {len(results)} rows")
    print(f"Duration: {duration_ms:.2f}ms")

    benchmarks.append({
        'test': 'Simple keyword',
        'query': "ILIKE '%setback%'",
        'rows': len(results),
        'duration_ms': duration_ms
    })

    # ========================================================================
    # BENCHMARK 2: Multi-keyword AND search
    # ========================================================================

    print("\n[BENCHMARK 2] Multi-keyword AND: 'setback' AND 'minimum'")
    print("-" * 80)

    start = time.time()
    cur.execute("""
        SELECT id, ref_number, LEFT(provision_text, 100) as preview
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%setback%'
        AND provision_text ILIKE '%minimum%'
        AND is_canonical = TRUE
        LIMIT 20
    """)
    results = cur.fetchall()
    duration_ms = (time.time() - start) * 1000

    print(f"Results: {len(results)} rows")
    print(f"Duration: {duration_ms:.2f}ms")

    benchmarks.append({
        'test': 'Multi-keyword AND',
        'query': "ILIKE '%setback%' AND ILIKE '%minimum%'",
        'rows': len(results),
        'duration_ms': duration_ms
    })

    # ========================================================================
    # BENCHMARK 3: Phrase search
    # ========================================================================

    print("\n[BENCHMARK 3] Phrase search: 'building height'")
    print("-" * 80)

    start = time.time()
    cur.execute("""
        SELECT id, ref_number, LEFT(provision_text, 100) as preview
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%building height%'
        AND is_canonical = TRUE
        LIMIT 20
    """)
    results = cur.fetchall()
    duration_ms = (time.time() - start) * 1000

    print(f"Results: {len(results)} rows")
    print(f"Duration: {duration_ms:.2f}ms")

    benchmarks.append({
        'test': 'Phrase search',
        'query': "ILIKE '%building height%'",
        'rows': len(results),
        'duration_ms': duration_ms
    })

    # ========================================================================
    # BENCHMARK 4: Complex search
    # ========================================================================

    print("\n[BENCHMARK 4] Complex: ('heritage' OR 'conservation') AND 'zone'")
    print("-" * 80)

    start = time.time()
    cur.execute("""
        SELECT id, ref_number, LEFT(provision_text, 100) as preview
        FROM regulatory_provisions
        WHERE (provision_text ILIKE '%heritage%' OR provision_text ILIKE '%conservation%')
        AND provision_text ILIKE '%zone%'
        AND is_canonical = TRUE
        LIMIT 20
    """)
    results = cur.fetchall()
    duration_ms = (time.time() - start) * 1000

    print(f"Results: {len(results)} rows")
    print(f"Duration: {duration_ms:.2f}ms")

    benchmarks.append({
        'test': 'Complex OR+AND',
        'query': "(ILIKE '%heritage%' OR ILIKE '%conservation%') AND ILIKE '%zone%'",
        'rows': len(results),
        'duration_ms': duration_ms
    })

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)

    print(f"\n{'Test':<20} {'Duration':<15} {'Rows':<10} {'Method'}")
    print("-" * 80)
    for b in benchmarks:
        print(f"{b['test']:<20} {b['duration_ms']:>8.2f}ms      {b['rows']:<10} {b['query'][:40]}")

    avg_duration = sum(b['duration_ms'] for b in benchmarks) / len(benchmarks)
    print("-" * 80)
    print(f"{'Average':<20} {avg_duration:>8.2f}ms")

    print("\n" + "="*80)
    print("ISSUES WITH CURRENT APPROACH")
    print("="*80)

    print("\n1. PERFORMANCE:")
    print("   - Every query scans ALL 22,648 provisions")
    print("   - ILIKE '%keyword%' cannot use standard indexes")
    print(f"   - Average query time: {avg_duration:.2f}ms")
    print("   - Scales linearly with table size (slow as data grows)")

    print("\n2. FUNCTIONALITY:")
    print("   - No ranking by relevance")
    print("   - No stemming (e.g., 'building' won't match 'builds')")
    print("   - No fuzzy matching (typos return nothing)")
    print("   - Complex queries require multiple ILIKE patterns")

    print("\n3. USER EXPERIENCE:")
    if avg_duration > 200:
        print("   - Users perceive delays > 200ms as 'slow'")
        print("   - Current average exceeds this threshold")
    else:
        print("   - Currently acceptable, but will degrade as data grows")

    print("\n" + "="*80 + "\n")

    conn.close()

    return benchmarks

if __name__ == '__main__':
    try:
        benchmarks = benchmark_text_searches()
        sys.exit(0)
    except Exception as e:
        print(f"\nBENCHMARK ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
