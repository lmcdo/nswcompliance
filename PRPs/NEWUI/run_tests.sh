#!/bin/bash
# Standalone test runner for PRP-A8

echo "🧪 Running PRP-A8 End-to-End Testing Suite"
echo "==========================================="

cd ../../frontend-nextjs

# Check if server is running
if ! curl -s http://localhost:3007 > /dev/null; then
    echo "⚠️  Development server not running. Starting server..."
    npm run dev &
    SERVER_PID=$!
    sleep 10
    echo "✅ Server started"
else
    echo "✅ Server already running"
    SERVER_PID=""
fi

echo ""
echo "Running comprehensive test suite..."

# Run the master test orchestrator
node tests/e2e/run-all-tests.js

TEST_EXIT_CODE=$?

# Cleanup
if [ ! -z "$SERVER_PID" ]; then
    echo "🛑 Stopping test server..."
    kill $SERVER_PID 2>/dev/null || true
fi

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "🎉 All tests completed successfully!"
else
    echo "❌ Some tests failed. Check output above for details."
fi

exit $TEST_EXIT_CODE
