#!/usr/bin/env python3
"""Simple table structure check"""
import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cur = conn.cursor()

print("DOCUMENTS TABLE STRUCTURE:")
cur.execute("PRAGMA table_info(documents)")
for col in cur.fetchall():
 print(f" {col[1]:<20} {col[2]:<15}")

print("\nSAMPLE DOCUMENTS:")
cur.execute("SELECT * FROM documents LIMIT 3")
for row in cur.fetchall():
 print(f" {row}")

conn.close()