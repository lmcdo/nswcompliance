"""Intelligent extraction on, deterministic proof mandatory, and neither quietly undone.

THE DECISION THIS PINS
----------------------
The DCP pipeline was decided in July 2026 as: read the document with an LLM, then
PROVE the result against the council's own PDF before serving it. Both halves were
built. Both then spent months switched off or optional:

  * `AI_EXTRACTION` was opt-in and stayed off for the two months AFTER the extractor
    had been hand-verified on marrickville's worst chapter -- part7-s3-sex-industry,
    28 pages, read line by line against the council's PDF: 49 of 49 objectives and
    controls extracted, every section number correct, zero mislabelling.
  * `enforce_fidelity` ABSTAINED on a batch with no verdicts at all, printing
    "not judged" and committing anyway, which made the proof optional in practice.

What filled the gap was hand-written per-council pattern exceptions -- eight tables
in scripts/dcp_extract_changed.py, four heading overrides added one at a time after
something broke downstream. On northern_beaches the regex reader read fourteen
clause markers as section headings ("O1 To establish a safe internal access road
network", "R2 Dwellings with a street frontage to have a front door directly visible
from the street") and served our own ref slug, "4_1c_7", as the council's section
number on 122 live rows. None of those are mistakes a reader makes.

WHY A TEST AND A LINT AND CI
----------------------------
Every one of those per-council changes passed every existing hook: tests, mutation
testing, the QA gate, the liability scan. The machinery verifies that a change is
CORRECT; nothing asked whether it was the right KIND of change. So this is pinned in
three places on purpose -- a test here, a pre-commit lint, and gates.yml, because a
pre-commit hook is bypassable with --no-verify and a check that can be skipped is
the failure mode being guarded against.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("DATABASE_URL", "postgresql:///test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
    os.environ.setdefault(_k, "test")

_STUBS = ("boto3", "botocore", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()
try:
    import dcp_extract_changed as dx  # noqa: E402
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v

EXTRACT_SRC = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
GUARD_SRC = (ROOT / "scripts" / "dcp_supersede_guard.py").read_text(encoding="utf-8")
HOOK_SRC = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")
CI_SRC = (ROOT / ".github" / "workflows" / "gates.yml").read_text(encoding="utf-8")


class TestIntelligentExtractionIsTheDefault:
    @pytest.mark.parametrize("value,enabled", [
        (None, True), ("", True), ("1", True), ("true", True), ("yes", True),
        ("0", False), ("false", False), ("no", False), ("OFF", False),
    ])
    def test_the_switch_is_opt_out(self, monkeypatch, value, enabled):
        if value is None:
            monkeypatch.delenv("AI_EXTRACTION", raising=False)
        else:
            monkeypatch.setenv("AI_EXTRACTION", value)
        assert dx.ai_extraction_enabled() is enabled

    def test_an_unset_environment_reads_the_document(self, monkeypatch):
        """The whole point. Nobody has to remember to turn it on."""
        monkeypatch.delenv("AI_EXTRACTION", raising=False)
        assert dx.ai_extraction_enabled() is True

    def test_disabling_it_announces_itself(self):
        """A fallback nobody notices is how the regex reader stayed the default for
        two months after the LLM extractor was verified."""
        assert "AI_EXTRACTION is DISABLED" in EXTRACT_SRC

    def test_the_fidelity_gate_is_also_opt_out(self, monkeypatch):
        """Reading intelligently is only safe because the result is proven. Both
        halves have to be on by default or the pairing is broken."""
        monkeypatch.delenv("DCP_FIDELITY_GATE", raising=False)
        assert dx.fidelity_gate_enabled() is True


class TestTheProofIsMandatory:
    def test_the_no_proof_branch_exists_and_raises(self):
        """A batch with approved rows and not one verdict means the gate did not run.
        That used to print "not judged" and commit."""
        tree = ast.parse(GUARD_SRC)
        raising = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and "approved" in ast.dump(node.test) and "graded" in ast.dump(node.test)
            and any(isinstance(n, ast.Raise) for n in ast.walk(node))
        ]
        assert raising, "the no-proof-no-commit branch does not refuse"

    def test_a_skipped_row_is_not_an_unproven_batch(self):
        """classify_provision deliberately leaves boilerplate ungraded. Refusing on
        that would stop every chapter carrying administrative text."""
        assert "nothing approved in this batch" in GUARD_SRC


class TestNeitherHalfCanBeUndoneQuietly:
    LINT = "scripts/lint_extraction_defaults.py"

    def _run(self, *args):
        return subprocess.run([sys.executable, self.LINT, *args], cwd=ROOT,
                              capture_output=True, encoding="utf-8", errors="replace")

    def test_the_lint_passes_on_this_tree(self):
        assert self._run().returncode == 0, "the working tree violates its own rule"

    def test_the_lint_is_in_the_pre_commit_hook(self):
        assert "lint_extraction_defaults.py" in HOOK_SRC

    def test_the_lint_is_ALSO_in_ci(self):
        """The hook is bypassable with --no-verify. A check that can be skipped is
        precisely the failure being guarded against, so it runs in both places."""
        assert "lint_extraction_defaults.py --ci" in CI_SRC

    def test_it_catches_the_switch_being_flipped_back(self, tmp_path):
        """Not a source-text assertion -- the lint is actually run against a mutated
        copy, because a lint that cannot fail is the thing it exists to prevent."""
        import shutil
        work = tmp_path / "repo"
        shutil.copytree(ROOT / "scripts", work / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        src = work / "scripts" / "dcp_extract_changed.py"
        text = src.read_text(encoding="utf-8")
        flipped = text.replace(
            'return os.getenv("AI_EXTRACTION", "").strip().lower() not in (\n'
            '        "0", "false", "no", "off",\n    )',
            'return os.getenv("AI_EXTRACTION", "").strip().lower() in (\n'
            '        "1", "true", "yes",\n    )')
        assert flipped != text, "the opt-out expression has moved; update this test"
        sys.path.insert(0, str(work / "scripts"))
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "lint_under_test", ROOT / self.LINT)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            assert mod.is_opt_out(flipped, "ai_extraction_enabled") is False, (
                "the lint cannot tell opt-in from opt-out")
            assert mod.is_opt_out(text, "ai_extraction_enabled") is True
        finally:
            sys.path.remove(str(work / "scripts"))

    def test_the_docstring_cannot_disguise_an_opt_in_switch(self):
        """The first version scanned every string in the function, so the docstring
        explaining opt-out made a flipped switch look compliant. Found by mutation."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("lint_ut2", ROOT / self.LINT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        disguised = (
            'def f():\n'
            '    """Mentions "0", "false", "no", "off" only in prose."""\n'
            '    return os.getenv("X", "").strip().lower() in ("1", "true", "yes")\n')
        assert mod.is_opt_out(disguised, "f") is False

    def test_it_sees_an_annotated_table(self):
        """COUNCIL_SECTION_RE_OVERRIDES carries a type annotation. Handling only a
        plain Assign made the lint blind to the exact table it was written for."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("lint_ut3", ROOT / self.LINT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        annotated = 'X: dict[str, int] = {"a": 1, "b": 2}\n'
        assert mod.table_keys(annotated, ["X"])["X"] == {"a", "b"}
