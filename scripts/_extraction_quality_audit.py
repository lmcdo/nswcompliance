#!/usr/bin/env python3
"""Honest quality audit: are provisions granular enough for compliance work?"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# 1. Granularity: provision size distribution per council
print("=== PROVISION SIZE DISTRIBUTION ===")
print("(A planner needs individual checkable controls, not 40K char blobs)")
print()
cur.execute("""
    SELECT source_council,
           COUNT(*) as total,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LENGTH(provision_text))::int as median_chars,
           AVG(LENGTH(provision_text))::int as avg_chars,
           MIN(LENGTH(provision_text)) as min_chars,
           MAX(LENGTH(provision_text)) as max_chars,
           COUNT(*) FILTER (WHERE LENGTH(provision_text) > 10000) as over_10k,
           COUNT(*) FILTER (WHERE LENGTH(provision_text) > 5000) as over_5k,
           COUNT(*) FILTER (WHERE LENGTH(provision_text) < 1000) as under_1k
    FROM regulatory_provisions
    WHERE is_current = true AND source_council IS NOT NULL
    GROUP BY source_council
    ORDER BY source_council
""")
for r in cur.fetchall():
    council, total, median, avg, mn, mx, over10k, over5k, under1k = r
    pct_over10k = over10k / total * 100 if total else 0
    pct_under1k = under1k / total * 100 if total else 0
    print(f"  {council or 'NULL':15s}: {total:5d} provisions | median {median:6d} chars | "
          f"avg {avg:6d} | max {mx:6d} | >10K: {over10k:3d} ({pct_over10k:.0f}%) | <1K: {under1k:3d} ({pct_under1k:.0f}%)")

# 2. What "good" looks like: SEPP provisions (source_council=NULL)
print()
cur.execute("""
    SELECT COUNT(*) as total,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LENGTH(provision_text))::int as median_chars,
           AVG(LENGTH(provision_text))::int as avg_chars
    FROM regulatory_provisions
    WHERE is_current = true AND source_council IS NULL
""")
r = cur.fetchone()
print(f"  SEPP (benchmark): {r[0]:5d} provisions | median {r[1]:6d} chars | avg {r[2]:6d}")

# 3. Actionability rate per council
print("\n=== ACTIONABILITY RATE ===")
print("(What % of provisions are actually compliance-checkable?)")
print()
cur.execute("""
    SELECT source_council,
           COUNT(*) as total,
           COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable,
           COUNT(*) FILTER (WHERE v2_is_actionable = false) as not_actionable,
           COUNT(*) FILTER (WHERE v2_is_actionable IS NULL) as unclassified
    FROM regulatory_provisions
    WHERE is_current = true AND source_council IS NOT NULL
    GROUP BY source_council
    ORDER BY source_council
""")
for r in cur.fetchall():
    council, total, act, notact, unclass = r
    pct = act / total * 100 if total else 0
    print(f"  {council or 'NULL':15s}: {act:4d}/{total:4d} actionable ({pct:.0f}%) | "
          f"not-actionable: {notact} | unclassified: {unclass}")

# 4. Topic coverage per council
print("\n=== TOPIC COVERAGE ===")
print("(Does extraction capture the DCP's actual emphases?)")
print()
cur.execute("""
    SELECT source_council, v2_topic, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE is_current = true AND source_council IS NOT NULL AND v2_topic IS NOT NULL
    GROUP BY source_council, v2_topic
    ORDER BY source_council, cnt DESC
""")
from collections import defaultdict
topics = defaultdict(list)
for r in cur.fetchall():
    topics[r[0]].append((r[1], r[2]))

for council, topic_list in sorted(topics.items()):
    top5 = topic_list[:5]
    topic_str = ", ".join(f"{t}({c})" for t, c in top5)
    total_topics = len(topic_list)
    print(f"  {council:15s}: {total_topics:2d} topics | top: {topic_str}")

# 5. The real question: how many provisions contain actual numeric controls?
print("\n=== NUMERIC CONTROL DENSITY ===")
print("(How many provisions have extractable compliance values?)")
print()
cur.execute("""
    SELECT source_council,
           COUNT(*) as total_actionable,
           COUNT(*) FILTER (WHERE v2_extraction_status = 'complete') as has_rules,
           COUNT(*) FILTER (WHERE v2_extraction_status = 'review_needed') as needs_llm
    FROM regulatory_provisions
    WHERE is_current = true AND source_council IS NOT NULL AND v2_is_actionable = true
    GROUP BY source_council
    ORDER BY source_council
""")
for r in cur.fetchall():
    council, total, complete, needs_llm = r
    pct = complete / total * 100 if total else 0
    print(f"  {council:15s}: {complete:4d}/{total:4d} have deterministic rules ({pct:.0f}%) | "
          f"needs LLM: {needs_llm}")

cur.close()
conn.close()
