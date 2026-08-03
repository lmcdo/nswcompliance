# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
from prose_gate.exclusions import ExclusionRules, allowed_terms, is_excluded_line

RULES = ExclusionRules()


def test_comment_lines_excluded_in_code_files():
    assert is_excluded_line("# result is guaranteed here", "app.py", RULES)
    assert is_excluded_line("  // safe to retry", "page.tsx", RULES)
    assert is_excluded_line(" * verified by upstream", "lib.ts", RULES)


def test_markdown_headings_are_not_comments():
    assert not is_excluded_line("# Guaranteed Outcomes", "docs/page.md", RULES)
    assert not is_excluded_line("# heading", "README.markdown", RULES)


def test_imports_and_logs_and_asserts_excluded():
    assert is_excluded_line("from safe_mode import x", "app.py", RULES)
    assert is_excluded_line("import verified_client", "app.py", RULES)
    assert is_excluded_line('console.error("not safe")', "page.tsx", RULES)
    assert is_excluded_line('logger.info("verified ok")', "app.py", RULES)
    assert is_excluded_line("assert result.safe", "test_x.py", RULES)
    assert is_excluded_line("expect(safe).toBe(true)", "x.test.tsx", RULES)


def test_declaration_lines_excluded():
    assert is_excluded_line("const verified = check()", "page.tsx", RULES)
    assert is_excluded_line("def safe(x):", "app.py", RULES)


def test_rules_can_be_disabled():
    lax = ExclusionRules(comments=False)
    assert not is_excluded_line("# guaranteed", "app.py", lax)


def test_prose_lines_not_excluded():
    assert not is_excluded_line(
        "<p>Your approval is guaranteed.</p>", "page.tsx", RULES
    )


def test_pragma_parsing():
    assert allowed_terms("plain prose line") is None
    assert allowed_terms("text  // prose-gate: allow") == set()
    assert allowed_terms("text  # prose-gate: allow(verified)") == {"verified"}
    assert allowed_terms("x <!-- prose-gate: allow(Safe, Guaranteed Returns) -->") == {
        "safe",
        "guaranteed returns",
    }
