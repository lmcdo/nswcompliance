#!/usr/bin/env python3
"""Check the remaining 10 provisions with 'shall' still excluded."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2
import re

from enrichment.extractors.actionable_classifier import ActionableClassifier

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

classifier = ActionableClassifier()

# Get ALL excluded provisions with shall
cur.execute("""
    SELECT id, document_id, provision_text
    FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND provision_text ILIKE '%shall%'
    ORDER BY id
""")

rows = cur.fetchall()
print(f"Total excluded with 'shall': {len(rows)}")
print("=" * 80)

shall_pattern = re.compile(r'\bshall\b', re.IGNORECASE)

for id, doc, text in rows:
    # Check if it actually has "shall" as a word
    has_shall = shall_pattern.search(text)

    # Why was it excluded?
    is_actionable, reason = classifier.classify(text, doc)

    print(f"\n[{id}] Has 'shall' word: {bool(has_shall)}")
    print(f"  Classifier says: {reason} (actionable={is_actionable})")
    print(f"  Doc: {doc[:60]}")
    print(f"  Text: {text[:200]}...")
    print("-" * 80)

conn.close()
