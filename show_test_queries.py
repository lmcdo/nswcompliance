import sqlite3
import json

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('=== VERIFICATION TEST QUERIES AND RESULTS ===')
print()

# Get all verification tests that were run
cursor.execute('SELECT test_type, test_name, input_parameters, expected_result, actual_result, test_status, execution_time_ms FROM verification_tests ORDER BY test_type, test_name')
tests = cursor.fetchall()

current_type = None
for test in tests:
 test_type, test_name, input_params, expected, actual, status, exec_time = test

 if test_type != current_type:
 print(f'\n=== {test_type.upper()} TESTS ===')
 current_type = test_type

 print(f'\nTest: {test_name}')
 print(f'Input: {input_params}')
 print(f'Expected: {expected}')
 print(f'Actual: {actual}')
 print(f'Status: {status} ({exec_time}ms)')

print('\n=== PROOF: EXECUTE SAMPLE QUERIES MANUALLY ===')

# Manually execute and show the actual SQL queries
print('\n1. ZONE QUERY TEST: "What can I build in R2?"')
cursor.execute("""
SELECT development_type, permission_status, COUNT(*)
FROM development_permissions
WHERE zone = 'R2' AND development_type IS NOT NULL
GROUP BY development_type, permission_status
ORDER BY permission_status, development_type
""")
r2_results = cursor.fetchall()
print(f'Query returned {len(r2_results)} development type combinations:')
for i, (dev_type, status, count) in enumerate(r2_results[:10]): # Show first 10
 print(f' {i+1}. {dev_type}: {status}')
if len(r2_results) > 10:
 print(f' ... and {len(r2_results)-10} more')

print('\n2. FEASIBILITY TEST: "Can I build dwelling_house in R1?"')
cursor.execute("""
SELECT permission_status, COUNT(*) as count
FROM development_permissions
WHERE zone = 'R1' AND development_type = 'dwelling_house'
GROUP BY permission_status
ORDER BY count DESC
""")
r1_dwelling_results = cursor.fetchall()
print(f'Query result: {r1_dwelling_results}')
print(f'Interpretation: dwelling_house in R1 is {r1_dwelling_results[0][0] if r1_dwelling_results else "not found"}')

print('\n3. FEASIBILITY TEST: "Can I build general_industry in R1?"')
cursor.execute("""
SELECT permission_status, COUNT(*) as count
FROM development_permissions
WHERE zone = 'R1' AND development_type = 'general_industry'
GROUP BY permission_status
ORDER BY count DESC
""")
r1_industry_results = cursor.fetchall()
print(f'Query result: {r1_industry_results}')
print(f'Interpretation: general_industry in R1 is {r1_industry_results[0][0] if r1_industry_results else "not found"}')

print('\n4. PERFORMANCE TEST: Zone query timing')
import time
start_time = time.time()
cursor.execute("SELECT * FROM development_permissions WHERE zone = 'B1'")
b1_results = cursor.fetchall()
execution_time = (time.time() - start_time) * 1000
print(f'B1 zone query: {len(b1_results)} results in {execution_time:.1f}ms')

print('\n5. CONSISTENCY TEST: dwelling_house across residential zones')
residential_zones = ['R1', 'R2', 'R3', 'R4']
for zone in residential_zones:
 cursor.execute("""
 SELECT permission_status
 FROM development_permissions
 WHERE zone = ? AND development_type = 'dwelling_house'
 """, (zone,))
 result = cursor.fetchone()
 status = result[0] if result else 'not found'
 print(f' dwelling_house in {zone}: {status}')

conn.close()