#!/usr/bin/env python3
"""Verify the blank line bug in boilerplate pattern."""
import re

# The problematic pattern (as used in classifier)
pattern = re.compile(r'^[\s\.\-_]+$', re.IGNORECASE | re.MULTILINE)

# Test text with blank line at start (like the PDF artifacts)
text1 = """

Error! Reference source not found.
C62 Additions must not compromise the symmetry."""

# Test text without blank line
text2 = """C62 Additions must not compromise the symmetry."""

# Text with just internal newline
text3 = """C62 Additions must not compromise
the symmetry of the pair."""

print("=" * 60)
print("BLANK LINE BUG VERIFICATION")
print("=" * 60)
print()
print("Pattern: ^[\\s\\.\\-_]+$ with MULTILINE flag")
print()

print("Test 1: Text with blank line at start")
print(f"  Text preview: {repr(text1[:60])}")
print(f"  Pattern matches: {bool(pattern.search(text1))}")
if pattern.search(text1):
    print(f"  Match found: {repr(pattern.search(text1).group())}")
print()

print("Test 2: Text without blank line")
print(f"  Text preview: {repr(text2[:60])}")
print(f"  Pattern matches: {bool(pattern.search(text2))}")
print()

print("Test 3: Text with internal newline only")
print(f"  Text preview: {repr(text3[:60])}")
print(f"  Pattern matches: {bool(pattern.search(text3))}")
print()

# Show what the pattern SHOULD be (without MULTILINE affecting ^$)
pattern_fixed = re.compile(r'\A[\s\.\-_]+\Z', re.IGNORECASE)

print("=" * 60)
print("FIXED PATTERN: \\A[\\s\\.\\-_]+\\Z (anchored to string start/end)")
print("=" * 60)
print()
print("Test 1 with fixed pattern:")
print(f"  Pattern matches: {bool(pattern_fixed.search(text1))}")
print()
print("Test 2 with fixed pattern:")
print(f"  Pattern matches: {bool(pattern_fixed.search(text2))}")
