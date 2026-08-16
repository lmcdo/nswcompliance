#!/usr/bin/env python3
import json
with open('enrichment/review_queue_20260313_124921.json') as f:
    q = json.load(f)
types = set()
for item in q:
    for rule in item.get('attempted_rules', []):
        vt = rule.get('value_type')
        if vt:
            types.add(vt)
    for err in item.get('validation_errors', []):
        print(err)
print()
print('Value types causing failures:', types)
