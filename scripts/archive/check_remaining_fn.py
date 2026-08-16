#!/usr/bin/env python3
"""Check what's still being excluded despite having must/shall."""
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

# Get samples of excluded provisions with must/shall
cur.execute("""
    SELECT id, document_id, provision_text
    FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
    LIMIT 20
""")

print("EXCLUDED PROVISIONS WITH MUST/SHALL:")
print("=" * 70)

for id, doc, text in cur.fetchall():
    # Why was it excluded?
    is_actionable, reason = classifier.classify(text, doc)

    print(f"\n[{id}] Reason: {reason}")
    print(f"  Doc: {doc[:60]}")
    print(f"  Length: {len(text)} chars")
    print(f"  Text: {text[:150]}...")

conn.close()
