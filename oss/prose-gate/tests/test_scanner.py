# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
from prose_gate.exclusions import ExclusionRules
from prose_gate.scanner import scan
from prose_gate.terms import compile_terms

RULES = ExclusionRules()
PATTERN = compile_terms(["guaranteed", "verified", "safe"])


def _files(*lines: str, path: str = "page.tsx"):
    return {path: list(enumerate(lines, start=1))}


def test_finds_flagged_prose_with_line_numbers():
    findings = scan(
        _files(
            "<h1>Results</h1>",
            "<p>Approval is guaranteed for this site.</p>",
        ),
        PATTERN,
        RULES,
    )
    assert len(findings) == 1
    assert findings[0].path == "page.tsx"
    assert findings[0].line == 2
    assert findings[0].term == "guaranteed"


def test_multiple_terms_on_one_line_each_reported():
    findings = scan(
        _files("<p>It is safe and the data is verified.</p>"), PATTERN, RULES
    )
    assert [f.term for f in findings] == ["safe", "verified"]


def test_excluded_lines_produce_no_findings():
    findings = scan(
        _files(
            "// guaranteed by contract",
            'logger.warn("not safe")',
            "const verified = true",
        ),
        PATTERN,
        RULES,
    )
    assert findings == []


def test_bare_pragma_waives_whole_line():
    findings = scan(
        _files("<p>guaranteed and safe</p> {/* prose-gate: allow */}"),
        PATTERN,
        RULES,
    )
    assert findings == []


def test_named_pragma_waives_only_named_terms():
    findings = scan(
        _files("<p>guaranteed and safe</p> {/* prose-gate: allow(safe) */}"),
        PATTERN,
        RULES,
    )
    assert [f.term for f in findings] == ["guaranteed"]


def test_none_pattern_returns_empty():
    assert scan(_files("guaranteed"), None, RULES) == []
