#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Check records with actual zone data
results = cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != ''").fetchone()
print(f"Records with zone data: {results[0]}")

# Check if zone field is always null/empty
total_count = cursor.execute("SELECT COUNT(*) FROM regulatory_provisions").fetchone()[0]
print(f"Total records: {total_count}")

# Sample a few records to see zone values
sample_results = cursor.execute("SELECT id, zone, development_type, document_id FROM regulatory_provisions LIMIT 10").fetchall()
print("\nSample zone values:")
for row in sample_results:
    print(f"ID: {row[0]}, Zone: {row[1]}, DevType: {row[2]}, Doc: {row[3][:30]}...")

# Check what domain classifications exist
domain_results = cursor.execute("SELECT DISTINCT domain_classification, COUNT(*) FROM regulatory_provisions GROUP BY domain_classification").fetchall()
print("\nDomain classifications:")
for row in domain_results:
    print(f"Domain: {row[0]}, Count: {row[1]}")

conn.close()