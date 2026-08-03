# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
from prose_gate.terms import compile_terms


def test_empty_list_returns_none():
    assert compile_terms([]) is None
    assert compile_terms(["", "  "]) is None


def test_matches_word_case_insensitively():
    pattern = compile_terms(["guaranteed"])
    assert pattern.search("This outcome is GUARANTEED to occur.")
    assert pattern.search("guaranteed")
    assert not pattern.search("guarantees")


def test_word_boundaries_skip_identifiers():
    pattern = compile_terms(["verified", "safe"])
    # snake_case, camelCase and suffix joins are single \w+ tokens: no match
    assert not pattern.search("if is_verified and failsafe_mode:")
    assert not pattern.search("const isVerified = check(saferOption)")
    assert not pattern.search("verified_at = now()")
    # a standalone word does match — line-context rules handle those
    assert pattern.search("Data was verified against records.")


def test_phrases_match_across_whitespace_runs():
    pattern = compile_terms(["guaranteed returns"])
    assert pattern.search("offering guaranteed  returns to members")
    assert not pattern.search("guaranteed. Returns are variable.")


def test_longest_term_wins():
    pattern = compile_terms(["guaranteed", "guaranteed returns"])
    match = pattern.search("we promise guaranteed returns")
    assert match.group(1) == "guaranteed returns"


def test_hyphenated_terms():
    pattern = compile_terms(["risk-free"])
    assert pattern.search("a risk-free opportunity")
    assert not pattern.search("risk-freedom")
