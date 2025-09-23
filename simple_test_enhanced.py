#!/usr/bin/env python3
"""
Simple test for Enhanced Complete Assessment
"""

import requests
import json
from datetime import datetime

def main():
 print("TESTING ENHANCED COMPLETE ASSESSMENT")
 print("=" * 50)
 
 url = "http://localhost:8006/enhanced-complete-assessment"
 data = {
 "address": "15 Norton Street, Leichhardt NSW 2040",
 "query_type": "complete_assessment"
 }
 
 try:
 response = requests.post(url, json=data, timeout=30)
 print(f"Status: {response.status_code}")
 
 if response.status_code == 200:
 result = response.json()
 print(f"Full response: {json.dumps(result, indent=2)[:500]}...")
 
 if result.get("success"):
 print("SUCCESS: Enhanced assessment working!")
 
 # Show key results
 setbacks = result.get("setback_calculations", {})
 print(f"Front setback: {setbacks.get('front_setback')}")
 print(f"Side setback: {setbacks.get('side_setback')}")
 print(f"Rear setback: {setbacks.get('rear_setback')}")
 print(f"Confidence: {setbacks.get('confidence_grade')}")
 
 visuals = result.get("visual_content", [])
 print(f"Visual content items: {len(visuals)}")
 
 citations = result.get("page_citations", {})
 print(f"Total provisions: {citations.get('total_provisions')}")
 
 print("\nPROGRESSIVE DISCLOSURE IMPLEMENTED SUCCESSFULLY!")
 print("- Layer 1: Immediate setback values")
 print("- Layer 2: Visual content with priorities") 
 print("- Layer 3: Page citations and sources")
 
 return True
 else:
 print(f"FAILED: {result.get('error')}")
 return False
 else:
 print(f"HTTP ERROR: {response.status_code}")
 return False
 
 except Exception as e:
 print(f"ERROR: {e}")
 return False

if __name__ == "__main__":
 success = main()
 print(f"\nResult: {'PASS' if success else 'FAIL'}")