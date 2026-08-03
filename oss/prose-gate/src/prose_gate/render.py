# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Turn findings into terminal text, JSON, or GitHub annotations."""

from __future__ import annotations

import json

from .scanner import Finding

_GUIDANCE = (
    "Each flagged term is one of:\n"
    "  (a) a quotation from a source document -> keep it, add "
    "`prose-gate: allow(<term>)` with a citation\n"
    "  (b) an identifier or code context the rules missed -> add the pragma "
    "or extend [exclusions]\n"
    "  (c) prose making a promise on your behalf -> reword it as a factual "
    "statement of what the data shows"
)


def _snippet(text: str, limit: int = 120) -> str:
    stripped = text.strip()
    return stripped if len(stripped) <= limit else stripped[: limit - 1] + "…"


def render_text(findings: list[Finding]) -> str:
    if not findings:
        return "prose-gate: no flagged language in scanned lines."
    out: list[str] = []
    for f in findings:
        out.append(f"{f.path}:{f.line}: '{f.term}'")
        out.append(f"    {_snippet(f.text)}")
    files = len({f.path for f in findings})
    out.append("")
    out.append(f"{len(findings)} finding(s) in {files} file(s).")
    out.append(_GUIDANCE)
    return "\n".join(out)


def render_json(findings: list[Finding]) -> str:
    return json.dumps(
        {"count": len(findings), "findings": [f.as_dict() for f in findings]},
        indent=2,
    )


def render_github(findings: list[Finding]) -> str:
    """GitHub Actions workflow annotations, one per finding."""
    return "\n".join(
        f"::error file={f.path},line={f.line}::"
        f"prose-gate flagged '{f.term}': {_snippet(f.text, 80)}"
        for f in findings
    )


RENDERERS = {
    "text": render_text,
    "json": render_json,
    "github": render_github,
}
