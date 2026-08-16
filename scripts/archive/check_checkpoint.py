#!/usr/bin/env python3
import json
import sys

try:
    with open('scripts/checkpoints/topic_classify_checkpoint.json', 'r') as f:
        d = json.load(f)

    processed = len(d.get('processed_ids', []))
    stats = d.get('stats', {})

    print(f"Processed: {processed}")
    print(f"Stats: {stats}")
except FileNotFoundError:
    print("No checkpoint file yet")
except Exception as e:
    print(f"Error: {e}")
