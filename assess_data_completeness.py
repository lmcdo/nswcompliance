#!/usr/bin/env python3
"""
Comprehensive assessment of zone and setback data completeness
Evaluates readiness for frontend queries
"""

import psycopg2
import json
from datetime import datetime

def assess_completeness():
 """Assess zone and setback data completeness for frontend queries"""
 
 conn = psycopg2.connect(
 host='localhost',
 database='nsw_planning', 
 user='postgres',
 password='postgres',
 port='5432'
 )
 cursor = conn.cursor()
 
 assessment = {
 'timestamp': datetime.now().isoformat(),
 'overall_score': 0,
 'coverage': {},
 'gaps': [],
 'strengths': [],
 'recommendations': []
 }
 
 print("=== ZONE AND SETBACK DATA COMPLETENESS ASSESSMENT ===\n")
 
 # 1. Overall Statistics
 cursor.execute("SELECT COUNT(*) FROM zone_setback_rules")
 total_rules = cursor.fetchone()[0]
 
 cursor.execute("SELECT COUNT(DISTINCT zone) FROM zone_setback_rules")
 total_zones = cursor.fetchone()[0]
 
 cursor.execute("SELECT COUNT(DISTINCT council) FROM zone_setback_rules")
 total_councils = cursor.fetchone()[0]
 
 print("OVERALL STATISTICS")
 print(f" Total Rules: {total_rules}")
 print(f" Zones Covered: {total_zones}")
 print(f" Councils: {total_councils}")
 print()
 
 # 2. Council-Zone Coverage Matrix
 print("COUNCIL-ZONE COVERAGE MATRIX")
 print("-" * 60)
 
 cursor.execute("""
 SELECT council, zone, 
 COUNT(*) as rule_count,
 COUNT(DISTINCT boundary_type) as boundary_types,
 AVG(confidence)::decimal(3,2) as avg_confidence
 FROM zone_setback_rules
 GROUP BY council, zone
 ORDER BY council, zone
 """)
 
 coverage_matrix = {}
 for council, zone, count, boundaries, confidence in cursor.fetchall():
 if council not in coverage_matrix:
 coverage_matrix[council] = {}
 coverage_matrix[council][zone] = {
 'rules': count,
 'boundaries': boundaries,
 'confidence': float(confidence)
 }
 
 # Expected zones for Inner West
 expected_zones = {
 'residential': ['R1', 'R2', 'R3', 'R4'],
 'business': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
 'industrial': ['IN1', 'IN2'],
 'recreation': ['RE1', 'RE2'],
 'special': ['SP1', 'SP2']
 }
 
 # Print coverage matrix
 all_zones = set()
 for category, zones in expected_zones.items():
 all_zones.update(zones)
 
 councils = ['Ashfield', 'Leichhardt', 'Marrickville']
 
 # Header
 print(f"{'Zone':<6} | ", end='')
 for council in councils:
 print(f"{council[:8]:<12} | ", end='')
 print()
 print("-" * 60)
 
 # Data rows
 for zone in sorted(all_zones):
 print(f"{zone:<6} | ", end='')
 for council in councils:
 if council in coverage_matrix and zone in coverage_matrix[council]:
 data = coverage_matrix[council][zone]
 status = f"{data['rules']}r/{data['boundaries']}b"
 print(f"{status:<12} | ", end='')
 else:
 print(f"{'MISSING':<12} | ", end='')
 print()
 
 print("\nLegend: Xr/Yb = X rules covering Y boundary types")
 print()
 
 # 3. Boundary Type Completeness
 print(" BOUNDARY TYPE COMPLETENESS")
 cursor.execute("""
 SELECT council, 
 SUM(CASE WHEN boundary_type = 'front' THEN 1 ELSE 0 END) as front,
 SUM(CASE WHEN boundary_type = 'side' THEN 1 ELSE 0 END) as side,
 SUM(CASE WHEN boundary_type = 'rear' THEN 1 ELSE 0 END) as rear,
 SUM(CASE WHEN boundary_type NOT IN ('front','side','rear') THEN 1 ELSE 0 END) as other
 FROM zone_setback_rules
 GROUP BY council
 ORDER BY council
 """)
 
 print(f"{'Council':<15} | Front | Side | Rear | Other")
 print("-" * 50)
 for council, front, side, rear, other in cursor.fetchall():
 print(f"{council:<15} | {front:5} | {side:4} | {rear:4} | {other:5}")
 print()
 
 # 4. Quality Distribution
 print(" DATA QUALITY DISTRIBUTION")
 cursor.execute("""
 SELECT quality_tier, COUNT(*) as count,
 MIN(confidence)::decimal(3,2) as min_conf,
 MAX(confidence)::decimal(3,2) as max_conf,
 AVG(confidence)::decimal(3,2) as avg_conf
 FROM zone_setback_rules
 GROUP BY quality_tier
 ORDER BY 
 CASE quality_tier
 WHEN 'verified' THEN 1
 WHEN 'high' THEN 2
 WHEN 'medium' THEN 3
 ELSE 4
 END
 """)
 
 print(f"{'Tier':<10} | Count | Confidence Range")
 print("-" * 40)
 for tier, count, min_conf, max_conf, avg_conf in cursor.fetchall():
 print(f"{tier:<10} | {count:5} | {min_conf:.2f}-{max_conf:.2f} (avg: {avg_conf:.2f})")
 print()
 
 # 5. Critical Gaps Analysis
 print("WARNING: CRITICAL GAPS")
 gaps = []
 
 # Check for missing R2 data (most common residential)
 cursor.execute("""
 SELECT council, COUNT(*) 
 FROM zone_setback_rules 
 WHERE zone = 'R2' 
 GROUP BY council
 """)
 r2_coverage = {row[0]: row[1] for row in cursor.fetchall()}
 
 for council in councils:
 if council not in r2_coverage or r2_coverage[council] < 3:
 gap = f"{council} has incomplete R2 coverage ({r2_coverage.get(council, 0)} rules)"
 gaps.append(gap)
 print(f" X {gap}")
 
 # Check for missing boundary types
 cursor.execute("""
 SELECT council, zone, 
 ARRAY_AGG(DISTINCT boundary_type) as boundaries
 FROM zone_setback_rules
 WHERE zone IN ('R1', 'R2', 'R3', 'R4')
 GROUP BY council, zone
 """)
 
 for council, zone, boundaries in cursor.fetchall():
 missing = []
 if 'front' not in boundaries:
 missing.append('front')
 if 'side' not in boundaries:
 missing.append('side')
 if 'rear' not in boundaries:
 missing.append('rear')
 
 if missing:
 gap = f"{council} {zone} missing: {', '.join(missing)} setbacks"
 gaps.append(gap)
 print(f" X {gap}")
 
 if not gaps:
 print(" OK No critical gaps detected")
 print()
 
 # 6. Frontend Query Readiness
 print(" FRONTEND QUERY READINESS")
 
 # Test common query patterns
 test_queries = [
 ("R2 Residential in Marrickville", "SELECT COUNT(*) FROM zone_setback_rules WHERE zone = 'R2' AND council = 'Marrickville'"),
 ("B1 Business zones", "SELECT COUNT(*) FROM zone_setback_rules WHERE zone = 'B1'"),
 ("High confidence rules", "SELECT COUNT(*) FROM zone_setback_rules WHERE confidence >= 0.85"),
 ("Complete boundary sets", """
 SELECT COUNT(DISTINCT council || '_' || zone) 
 FROM zone_setback_rules 
 WHERE (council, zone) IN (
 SELECT council, zone 
 FROM zone_setback_rules 
 GROUP BY council, zone 
 HAVING COUNT(DISTINCT boundary_type) >= 3
 )
 """)
 ]
 
 readiness_score = 0
 for query_name, query in test_queries:
 cursor.execute(query)
 result = cursor.fetchone()[0]
 if result > 0:
 status = "OK READY"
 readiness_score += 25
 else:
 status = "X NOT READY"
 print(f" {query_name}: {status} ({result} results)")
 
 print(f"\n Overall Readiness Score: {readiness_score}%")
 assessment['overall_score'] = readiness_score
 print()
 
 # 7. Recommendations
 print(" RECOMMENDATIONS")
 recommendations = []
 
 if total_zones < 10:
 rec = "Extract additional zone data (currently only 7 of 15+ expected zones)"
 recommendations.append(rec)
 print(f" 1. {rec}")
 
 if readiness_score < 75:
 rec = "Improve data quality for production use (current score: {}%)".format(readiness_score)
 recommendations.append(rec)
 print(f" 2. {rec}")
 
 # Check for any zones with only 1 rule
 cursor.execute("""
 SELECT zone, COUNT(*) as count 
 FROM zone_setback_rules 
 GROUP BY zone 
 HAVING COUNT(*) < 3
 """)
 incomplete_zones = cursor.fetchall()
 if incomplete_zones:
 zones_list = ', '.join([z[0] for z in incomplete_zones])
 rec = f"Add more rules for zones with minimal coverage: {zones_list}"
 recommendations.append(rec)
 print(f" 3. {rec}")
 
 if not recommendations:
 print(" OK Data is production-ready!")
 
 print()
 
 # 8. Summary
 print("=" * 60)
 print("SUMMARY")
 print("=" * 60)
 
 completeness_score = min(100, (total_rules / 100) * 100) # Target 100 rules
 coverage_score = (total_zones / 15) * 100 # Target 15 zones
 quality_score = readiness_score
 
 overall_score = (completeness_score + coverage_score + quality_score) / 3
 
 print(f" Completeness: {completeness_score:.0f}% ({total_rules} rules)")
 print(f" Coverage: {coverage_score:.0f}% ({total_zones}/15 zones)")
 print(f" Quality: {quality_score:.0f}%")
 print(f" OVERALL: {overall_score:.0f}%")
 print()
 
 grade = "A" if overall_score >= 90 else "B" if overall_score >= 75 else "C" if overall_score >= 60 else "D"
 print(f" Grade: {grade}")
 
 if grade in ["A", "B"]:
 print(" Status: OK PRODUCTION READY")
 else:
 print(" Status: WARNING: NEEDS IMPROVEMENT")
 
 assessment['gaps'] = gaps
 assessment['recommendations'] = recommendations
 assessment['overall_score'] = overall_score
 
 # Save assessment
 with open('zone_data_assessment.json', 'w') as f:
 json.dump(assessment, f, indent=2)
 
 conn.close()
 return overall_score

if __name__ == "__main__":
 score = assess_completeness()
 print(f"\nAssessment saved to zone_data_assessment.json")