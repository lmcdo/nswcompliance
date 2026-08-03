# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Line-context rules deciding whether a line is code rather than prose.

The linter's job is to catch flagged words in text a *user* will read.
These rules skip lines that are clearly code-facing: comments, imports,
log calls, assertions and declarations. Each rule can be switched off in
configuration.

An inline pragma lets an author suppress a finding deliberately and
auditable-y::

    <p>Data sourced from council records.</p>  {/* prose-gate: allow(verified) */}

A bare ``prose-gate: allow`` suppresses every term on that line;
``prose-gate: allow(term, other term)`` suppresses only those terms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_COMMENT = re.compile(r"^\s*(#|//|\*|/\*|<!--|--\s)")
_IMPORT = re.compile(r"^\s*(import\s|from\s+\S+\s+import\s)")
_LOG_CALL = re.compile(r"\b(console|logger|logging|log)\.\w+\s*\(")
_ASSERTION = re.compile(r"^\s*(assert\s|assert\(|expect\s*\()")
_DECLARATION = re.compile(
    r"^\s*(const|let|var|def|class|function|type|interface|enum)\s"
)

# Markdown-family files: a leading '#' is a heading (prose), not a comment.
_PROSE_SUFFIXES = (".md", ".mdx", ".markdown", ".txt", ".rst")

PRAGMA = re.compile(r"prose-gate:\s*allow(?:\(([^)]*)\))?", re.IGNORECASE)


@dataclass
class ExclusionRules:
    """Toggles for each line-context rule. All default to on."""

    comments: bool = True
    imports: bool = True
    log_calls: bool = True
    assertions: bool = True
    declarations: bool = True


def is_excluded_line(line: str, path: str, rules: ExclusionRules) -> bool:
    """True when the whole line is code context and scanning it would only
    produce noise."""
    is_prose_file = path.lower().endswith(_PROSE_SUFFIXES)
    if rules.comments and not is_prose_file and _COMMENT.search(line):
        return True
    if rules.imports and _IMPORT.search(line):
        return True
    if rules.log_calls and _LOG_CALL.search(line):
        return True
    if rules.assertions and _ASSERTION.search(line):
        return True
    if rules.declarations and _DECLARATION.search(line):
        return True
    return False


def allowed_terms(line: str) -> set[str] | None:
    """Parse an inline suppression pragma.

    Returns None when the line has no pragma, an empty set for a bare
    ``allow`` (suppress everything on the line), or the lowercased set of
    terms named in ``allow(...)``.
    """
    match = PRAGMA.search(line)
    if not match:
        return None
    inner = match.group(1)
    if inner is None or not inner.strip():
        return set()
    return {t.strip().lower() for t in inner.split(",") if t.strip()}
