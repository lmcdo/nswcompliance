"""
Test Query Performance with New Indexes
Uses EXPLAIN ANALYZE to verify indexes are being used
"""

import psycopg2
import json

def test_index_usage():
    """Test that queries are using the new indexes"""

    print("=" * 80)
    print("INDEX USAGE VERIFICATION - EXPLAIN ANALYZE")
    print("=" * 80)
    print()

    conn = psycopg2.connect(
        host="localhost",
        database="nsw_planning",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    test_queries = [
        {
            "name": "Ashfield Zone+DevType Filtering (GIN indexes)",
            "expected_index": ["idx_dcp_gen_req_zones_gin", "idx_dcp_gen_req_devtypes_gin", "idx_dcp_gen_req_former_council"],
            "query": """
                SELECT COUNT(*)
                FROM dcp_general_requirements
                WHERE lga = 'Inner West'
                AND 'R2' = ANY(applicable_zones)
                AND 'dwelling_house' = ANY(development_types)
                AND former_council = 'Ashfield'
            """
        },
        {
            "name": "Provisions Zone Filtering (GIN index)",
            "expected_index": ["idx_dcp_gen_prov_zones_gin"],
            "query": """
                SELECT COUNT(*)
                FROM dcp_general_provisions
                WHERE lga = 'Inner West'
                AND 'R2' = ANY(applicable_zones)
            """
        },
        {
            "name": "Regulatory Provisions Document ID (B-tree index)",
            "expected_index": ["idx_reg_prov_document_id"],
            "query": """
                SELECT COUNT(*)
                FROM regulatory_provisions
                WHERE document_id ILIKE '%Marrickville%'
            """
        },
        {
            "name": "Former Council Filtering (B-tree index)",
            "expected_index": ["idx_dcp_gen_req_former_council"],
            "query": """
                SELECT COUNT(*)
                FROM dcp_general_requirements
                WHERE former_council = 'Marrickville'
            """
        },
    ]

    results = []

    for test in test_queries:
        print(f"Testing: {test['name']}")
        print("-" * 80)

        # Run EXPLAIN ANALYZE
        explain_query = f"EXPLAIN (ANALYZE, FORMAT JSON) {test['query']}"
        cursor.execute(explain_query)
        explain_result = cursor.fetchone()[0]

        # Extract execution time
        exec_time = explain_result[0]['Execution Time']

        # Check if index was used
        plan_text = json.dumps(explain_result, indent=2)
        indexes_found = []

        for expected_idx in test['expected_index']:
            if expected_idx in plan_text:
                indexes_found.append(expected_idx)

        # Check for sequential scan (bad - means no index used)
        has_seq_scan = "Seq Scan" in plan_text

        # Display results
        print(f"  Execution Time: {exec_time:.2f}ms")

        if indexes_found:
            print(f"  Index Used: YES - {', '.join(indexes_found)}")
            status = "GOOD"
        else:
            print(f"  Index Used: NO")
            status = "WARNING"

        if has_seq_scan:
            print(f"  Sequential Scan: YES (may be OK for small tables)")
        else:
            print(f"  Sequential Scan: NO")

        # Get actual row count
        cursor.execute(test['query'])
        row_count = cursor.fetchone()[0]
        print(f"  Rows Returned: {row_count}")

        results.append({
            "query": test['name'],
            "execution_time_ms": exec_time,
            "indexes_used": indexes_found,
            "has_seq_scan": has_seq_scan,
            "status": status,
            "row_count": row_count
        })

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_queries = len(results)
    using_indexes = sum(1 for r in results if r['indexes_used'])
    avg_time = sum(r['execution_time_ms'] for r in results) / total_queries

    print(f"Total queries tested: {total_queries}")
    print(f"Queries using indexes: {using_indexes}/{total_queries}")
    print(f"Average execution time: {avg_time:.2f}ms")
    print()

    if using_indexes == total_queries:
        print("SUCCESS: All queries are using indexes!")
    else:
        print("WARNING: Some queries not using indexes. Check query patterns.")

    print()
    print("Note: Sequential scans may still appear for:")
    print("  - Very small tables (<1000 rows)")
    print("  - Queries returning large % of table")
    print("  - ILIKE queries (consider full-text search for these)")
    print()

    cursor.close()
    conn.close()

    return using_indexes == total_queries

if __name__ == "__main__":
    success = test_index_usage()
    exit(0 if success else 1)
