#!/usr/bin/env python3
"""
Post-edit code quality hook for Claude Code.
Warns about anti-patterns that have been remediated.
Exit code 0 = allow (with warnings)
Exit code 2 = block (critical issues)
"""

import json
import sys
import re
from pathlib import Path

# Read hook input from stdin
try:
    input_data = json.load(sys.stdin)
except:
    sys.exit(0)  # Allow if can't parse

file_path = input_data.get('tool_input', {}).get('file_path', '')
new_string = input_data.get('tool_input', {}).get('new_string', '')
content = input_data.get('tool_input', {}).get('content', '')

# For Edit tool, check new_string; for Write tool, check content
code_to_check = new_string or content or ''

# Normalize path for comparison
file_path_norm = file_path.lower().replace('\\', '/')

# Skip checking if not in frontend-nextjs
if 'frontend-nextjs' not in file_path_norm:
    sys.exit(0)

# Skip checking hook files, test files, and the pool-manager itself
SKIP_PATTERNS = [
    '.claude/',
    '__tests__',
    '.test.',
    '.spec.',
    'pool-manager.ts',  # The pool manager itself can use new Pool
]

for pattern in SKIP_PATTERNS:
    if pattern in file_path_norm:
        sys.exit(0)

warnings = []
errors = []

# =============================================================================
# Anti-Pattern Checks
# =============================================================================

# 1. Direct Pool instantiation (should use getPool from pool-manager)
if re.search(r'\bnew\s+Pool\s*\(', code_to_check):
    errors.append(
        "POOL: Found 'new Pool()' - use 'import { getPool } from \"@/lib/database/pool-manager\"' instead"
    )

# 2. URL.createObjectURL without tracking (potential memory leak)
if 'URL.createObjectURL' in code_to_check:
    # Check if it's in evidence-manager or has revokeObjectURL nearby
    if 'evidence-manager' not in file_path_norm:
        if 'revokeObjectURL' not in code_to_check:
            warnings.append(
                "MEMORY: Found URL.createObjectURL without revokeObjectURL - ensure cleanup on unmount"
            )

# 3. dangerouslySetInnerHTML without sanitization
if 'dangerouslySetInnerHTML' in code_to_check:
    if 'sanitizeHTML' not in code_to_check and 'DOMPurify' not in code_to_check:
        errors.append(
            "XSS: Found dangerouslySetInnerHTML without sanitization - use sanitizeHTML from '@/lib/sanitize'"
        )

# 4. spawn() without timeout handling (check for patterns suggesting proper cleanup)
if re.search(r'\bspawn\s*\(', code_to_check):
    # Look for timeout/kill patterns
    has_timeout = 'setTimeout' in code_to_check or 'TIMEOUT' in code_to_check
    has_kill = '.kill(' in code_to_check or 'SIGTERM' in code_to_check
    if not (has_timeout and has_kill):
        warnings.append(
            "SUBPROCESS: Found spawn() - ensure timeout handling with .kill() for orphan prevention"
        )

# 5. Magic numbers that should be constants (common ones)
MAGIC_NUMBER_PATTERNS = [
    (r'\b30000\b', 'DB_TIMEOUT_MS or WS_RECONNECT_MAX_MS'),
    (r'\b60000\b', 'RATE_LIMIT_WINDOW_MS'),
    (r'max:\s*20\b', 'DB_POOL_MAX'),
    (r'idleTimeoutMillis:\s*\d+', 'DB_IDLE_TIMEOUT_MS'),
]

# Only check for magic numbers in .ts/.tsx files (not config files)
if file_path_norm.endswith(('.ts', '.tsx')):
    for pattern, constant_name in MAGIC_NUMBER_PATTERNS:
        if re.search(pattern, code_to_check):
            # Skip if already importing from constants
            if '@/lib/constants' not in code_to_check and 'from \'./constants\'' not in code_to_check:
                warnings.append(
                    f"CONSTANTS: Consider using {constant_name} from '@/lib/constants'"
                )
                break  # Only one warning per file

# 6. Creating new database clients instead of using shared pool
if re.search(r'\bnew\s+(PostgresClient|PRPClient|DatabaseClient)\s*\(', code_to_check):
    # Check if passing the shared pool
    if 'getPool()' not in code_to_check:
        warnings.append(
            "DATABASE: Creating new client - ensure it uses getPool() for shared connection pool"
        )

# 7. SSL with rejectUnauthorized: false in production
if 'rejectUnauthorized: false' in code_to_check:
    errors.append(
        "SSL: Found 'rejectUnauthorized: false' - this disables SSL verification (security risk)"
    )

# =============================================================================
# Output Results
# =============================================================================

if errors:
    print("=" * 60, file=sys.stderr)
    print("CODE QUALITY ERRORS (must fix):", file=sys.stderr)
    for err in errors:
        print(f"  ❌ {err}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

if warnings:
    print("-" * 60, file=sys.stderr)
    print("CODE QUALITY WARNINGS (review):", file=sys.stderr)
    for warn in warnings:
        print(f"  ⚠️  {warn}", file=sys.stderr)
    print("-" * 60, file=sys.stderr)

# Exit with error code 2 to block if there are errors
# Warnings are informational only (exit 0)
if errors:
    sys.exit(2)

sys.exit(0)
