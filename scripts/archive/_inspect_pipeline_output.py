#!/usr/bin/env python3
"""Inspect pipeline output for a sample of provisions — show what's extracted and what needs LLM."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2
from psycopg2.extras import RealDictCursor
from enrichment.rule_extraction_pipeline import process_provision

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("""
    SELECT id, provision_text, v2_has_numeric_value, section_header, v2_topic, source_council
    FROM regulatory_provisions
    WHERE is_current = true
      AND v2_is_actionable = true
      AND provision_text IS NOT NULL
      AND provision_text != ''
    ORDER BY id
    LIMIT 100
""")
provisions = cur.fetchall()

needs_llm = []
complete_by_type = {}
for prov in provisions:
    result = process_provision(dict(prov))
    status = result["status"]
    rules = result["rules"]
    ct = rules[0]["compliance_type"] if rules else "none"

    if result.get("needs_llm"):
        needs_llm.append({
            "id": prov["id"],
            "council": prov.get("source_council", "?"),
            "topic": prov.get("v2_topic", "?"),
            "text": (prov["provision_text"] or "")[:200],
            "compliance_type": ct,
            "rules": rules,
        })
    else:
        complete_by_type[ct] = complete_by_type.get(ct, 0) + 1

print("=== COMPLETE BY COMPLIANCE TYPE ===")
for ct, count in sorted(complete_by_type.items(), key=lambda x: -x[1]):
    print(f"  {ct}: {count}")

print(f"\n=== NEEDS LLM ({len(needs_llm)}) ===")
for item in needs_llm:
    print(f"\n--- ID {item['id']} ({item['council']}) topic={item['topic']} ---")
    print(f"  Type: {item['compliance_type']}")
    print(f"  Text: {item['text'][:150]}...")
    print(f"  Rules: {json.dumps(item['rules'], indent=2)[:300]}")

cur.close()
conn.close()
