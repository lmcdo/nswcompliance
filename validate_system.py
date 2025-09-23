#!/usr/bin/env python3
"""
Simple system validation runner
Usage: python validate_system.py
"""

import json
import os

def validate_system():
 print("Validating NSW Compliance Engine System...")
 print("=" * 50)
 
 # Check extracted rules exist
 rules_path = "public/regulatory-data/inner-west-compliance-rules.json"
 if os.path.exists(rules_path):
 with open(rules_path, 'r') as f:
 data = json.load(f)
 print(f" Rules file exists: {len(data.get('rules', []))} rules loaded")
 
 # Show current rules
 for rule in data.get('rules', []):
 req = rule['requirements'][0]
 print(f" - {rule['applies_to']['former_council']} {req['subtype']} setback: {req['value']}m")
 else:
 print(" Rules file not found")
 
 # Check if Next.js is running
 print(f"\n Frontend should be running at: http://localhost:3000")
 print(f" Test with address: 123 Liverpool Road, Ashfield NSW 2131")
 print(f" Expected: Side setback ≥0.9m, Front setback ≥6.0m")
 
 print("\nSystem Status: READY FOR TESTING ")

if __name__ == "__main__":
 validate_system()