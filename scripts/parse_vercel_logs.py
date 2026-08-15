#!/usr/bin/env python3
import json
import sys

with open('C:/Users/lawre/Downloads/logs_result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total log entries: {len(data)}")
print("\n=== Relevant entries ===\n")

count = 0
for entry in data:
    msg = entry.get('message', '') if isinstance(entry, dict) else str(entry)
    if '4-Layer' in msg or 'precinct' in msg.lower():
        print(f"[{entry.get('timestamp', 'no-ts')}]")
        print(msg[:800])
        print('---')
        count += 1
        if count > 30:
            break

print(f"\nFound {count} relevant entries")
