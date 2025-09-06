#!/usr/bin/env python3
"""
Test Domain-Aware Integration
============================

Test script to verify Phase 1A MVP integration works correctly:
1. Domain filtering prevents signage contamination
2. Legal authority tracking is complete
3. UI-compatible format is generated
"""

import sys
import json
import subprocess
from pathlib import Path

def test_domain_aware_integration():
    """Test the complete domain-aware integration"""
    
    print("[TEST] Testing Domain-Aware Integration for Phase 1A MVP")
    print("=" * 60)
    
    # Test cases: Different zones to verify domain filtering
    test_cases = [
        {
            'zone': 'R2', 
            'description': 'Low Density Residential',
            'expected_domain': 'RESIDENTIAL_BUILDINGS',
            'should_exclude': 'SIGNAGE_ADVERTISING'
        },
        {
            'zone': 'R3',
            'description': 'Medium Density Residential', 
            'expected_domain': 'RESIDENTIAL_BUILDINGS',
            'should_exclude': 'SIGNAGE_ADVERTISING'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[TEST {i}] {test_case['description']} Zone ({test_case['zone']})")
        print("-" * 50)
        
        try:
            # Call the enhanced Python engine
            result = subprocess.run([
                sys.executable, 'dynamic_setback_calc.py', 
                test_case['zone'], '12345'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"[FAILED] Script returned error code {result.returncode}")
                print(f"   stderr: {result.stderr}")
                continue
            
            # Parse results
            try:
                setbacks = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                print(f"[FAILED] Invalid JSON output")
                print(f"   stdout: {result.stdout[:200]}...")
                continue
            
            # Verify results
            print(f"[SUCCESS] Retrieved {len(setbacks)} setback requirements")
            
            # Test 1: Domain Classification
            domain_test_passed = True
            for setback in setbacks:
                domain = setback.get('domain_classification', 'UNKNOWN')
                if domain == test_case['should_exclude']:
                    print(f"[CONTAMINATION] Found {domain} in {test_case['zone']} results")
                    domain_test_passed = False
                elif domain == test_case['expected_domain']:
                    print(f"[DOMAIN OK] {domain} correctly classified")
                else:
                    print(f"[DOMAIN OTHER] {domain} (not contamination)")
            
            # Test 2: Legal Authority
            authority_test_passed = True
            for setback in setbacks:
                legal_authority = setback.get('legal_authority', {})
                primary = legal_authority.get('primary_authority', 'MISSING')
                secondary = legal_authority.get('secondary_authority', 'MISSING')
                
                if primary == 'Inner West LEP 2022':
                    print(f"[OK] LEGAL AUTHORITY: {primary} → {secondary}")
                else:
                    print(f"[WARNING]  LEGAL AUTHORITY: {primary} (expected Inner West LEP 2022)")
                    authority_test_passed = False
            
            # Test 3: Cross-Contamination Prevention
            contamination_test_passed = True
            for setback in setbacks:
                checked = setback.get('cross_contamination_checked', False)
                relevance = setback.get('relevance_score', 0)
                
                if checked and relevance >= 0.8:
                    print(f"[OK] CONTAMINATION CHECK: Passed (relevance: {relevance:.2f})")
                else:
                    print(f"[WARNING]  CONTAMINATION CHECK: Failed (relevance: {relevance:.2f})")
                    contamination_test_passed = False
            
            # Overall test result
            if domain_test_passed and authority_test_passed and contamination_test_passed:
                print(f"[SUCCESS] OVERALL: {test_case['zone']} zone test PASSED")
            else:
                print(f"[FAILED] OVERALL: {test_case['zone']} zone test FAILED")
            
            # Sample result display
            if setbacks:
                best_result = max(setbacks, key=lambda x: x.get('relevance_score', 0))
                print(f"\n[SAMPLE] Best Result Sample:")
                print(f"   Boundary: {best_result.get('boundary_type')}")
                print(f"   Setback: {best_result.get('required_setback')}m")
                print(f"   Domain: {best_result.get('domain_classification')}")
                print(f"   Relevance: {best_result.get('relevance_score', 0):.2f}")
                print(f"   Legal Source: {best_result.get('legal_authority', {}).get('primary_authority')}")
                
        except subprocess.TimeoutExpired:
            print(f"[FAILED] FAILED: Script timeout after 30 seconds")
        except Exception as e:
            print(f"[FAILED] FAILED: Unexpected error: {e}")
    
    print(f"\n[COMPLETE] Domain-Aware Integration Testing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_domain_aware_integration()