# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Compile a flat term list into a single word-boundary regex.

Multi-word phrases are supported; internal whitespace matches any run of
whitespace. Longer terms are tried first so that a phrase like
"guaranteed returns" wins over the bare word "guaranteed" and the finding
reports the most specific term.

Word boundaries do most of the identifier work for free: `_` and letters
are word characters, so ``\\bverified\\b`` never matches inside
``is_verified``, ``verified_at`` or ``isVerified``. Only a flagged word
standing completely alone in code (``verified = true``) needs the
line-context rules in :mod:`prose_gate.exclusions`.
"""

from __future__ import annotations

import re


def compile_terms(terms: list[str]) -> re.Pattern[str] | None:
    """Build one case-insensitive regex matching any term at word boundaries.

    Returns None for an empty term list (nothing to scan for).
    """
    cleaned = sorted(
        {t.strip() for t in terms if t and t.strip()},
        key=len,
        reverse=True,
    )
    if not cleaned:
        return None
    parts = [re.escape(t).replace(r"\ ", r"\s+") for t in cleaned]
    return re.compile(r"\b(" + "|".join(parts) + r")\b", re.IGNORECASE)
