#!/bin/bash

echo "================================================================================"
echo "COMPLIANCE CONSTRAINTS - VERIFICATION TEST SUITE"
echo "================================================================================"
echo ""
echo "This will verify that the database has the correct data and structure"
echo "for the API implementation to work correctly."
echo ""

cd "$(dirname "$0")/.."

# Test 1: Database tables
echo ""
echo "Running Test 1: Database Tables Verification..."
python tests/01_verify_database_tables.py
if [ $? -ne 0 ]; then
    echo "✗ Test 1 FAILED"
    exit 1
fi

# Test 2: API queries
echo ""
echo "Running Test 2: API Queries Verification..."
python tests/02_verify_api_queries.py
if [ $? -ne 0 ]; then
    echo "✗ Test 2 FAILED"
    exit 1
fi

# Test 3: Data transform
echo ""
echo "Running Test 3: Data Transformation Verification..."
python tests/03_verify_data_transform.py
if [ $? -ne 0 ]; then
    echo "✗ Test 3 FAILED"
    exit 1
fi

# Test 4: End-to-end
echo ""
echo "Running Test 4: End-to-End Verification..."
python tests/04_verify_end_to_end.py
if [ $? -ne 0 ]; then
    echo "✗ Test 4 FAILED"
    exit 1
fi

echo ""
echo "================================================================================"
echo "✓ ALL TESTS PASSED"
echo "================================================================================"
echo ""
echo "The database is ready and the implementation will work correctly:"
echo "  ✓ development_controls table has 4,526 extracted controls"
echo "  ✓ zone_setback_rules table has 6 curated R2 setbacks"
echo "  ✓ Queries return correct, filtered data"
echo "  ✓ Transforms produce valid constraint objects"
echo "  ✓ End-to-end flow produces correct UI structure"
echo ""
echo "Ready to implement API changes in:"
echo "  - frontend-nextjs/app/api/compliance/constraints/route.ts"
echo "  - frontend-nextjs/components/compliance/ComplianceDashboard.tsx"
echo ""