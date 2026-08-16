#!/usr/bin/env python3
"""Check the remaining 25 must/shall provisions still excluded."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

from enrichment.extractors.actionable_classifier import ActionableClassifier

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

classifier = ActionableClassifier()

# Get ALL excluded provisions with must/shall
cur.execute("""
    SELECT id, document_id, provision_text
    FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
    ORDER BY id
""")

rows = cur.fetchall()
print(f"Total excluded with must/shall: {len(rows)}")
print("=" * 80)

for id, doc, text in rows:
    # Why was it excluded?
    is_actionable, reason = classifier.classify(text, doc)

    print(f"\n[{id}] Reason: {reason}")
    print(f"  Doc: {doc}")
    print(f"  Full text:")
    # Handle encoding issues
    try:
        print(f"  {text}")
    except UnicodeEncodeError:
        print(f"  {text.encode('ascii', 'replace').decode()}")
    print("-" * 80)

conn.close()
