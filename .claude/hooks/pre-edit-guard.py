#!/usr/bin/env python3
"""
Pre-edit guard hook for Claude Code.
Blocks edits to sensitive files.
Exit code 2 = block the edit.
"""

import json
import sys

# Read hook input from stdin
try:
    input_data = json.load(sys.stdin)
except:
    sys.exit(0)  # Allow if can't parse

file_path = input_data.get('tool_input', {}).get('file_path', '')
file_path_lower = file_path.lower().replace('\\', '/')

# Files that should NEVER be edited by Claude
BLOCKED_PATTERNS = [
    '.env',
    '.env.local',
    '.env.production',
    'credentials',
    'secrets',
    '.git/',
    'package-lock.json',
    'yarn.lock',
    'pnpm-lock.yaml',
]

# Check if file matches any blocked pattern
for pattern in BLOCKED_PATTERNS:
    if pattern in file_path_lower:
        print(f"BLOCKED: Cannot edit {file_path} (matches '{pattern}')", file=sys.stderr)
        sys.exit(2)  # Block the edit

# Allow the edit
sys.exit(0)
