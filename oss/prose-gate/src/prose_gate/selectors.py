# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Decide which files count as user-facing.

Patterns are fnmatch-style. Note that fnmatch's ``*`` also matches path
separators, so ``*.tsx`` matches ``app/deep/nested/page.tsx`` — patterns
select by suffix and shape, not by directory depth.
"""

from __future__ import annotations

import fnmatch


DEFAULT_PATTERNS = [
    "*.tsx",
    "*.jsx",
    "*.html",
    "*.md",
    "*.mdx",
]


def is_user_facing(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, p) for p in patterns)
