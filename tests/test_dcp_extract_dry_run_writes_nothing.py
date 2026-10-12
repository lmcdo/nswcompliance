"""A --dry-run of dcp_extract_changed must not run the enrichment phases, which write to every row they select.

prior-art-checked: no existing test covers the enrichment call in main(); the phases themselves are tested in
enrichment's own tests. Found 2026-10-13: a DeepSeek pilot dry run recorded provenance on 2 production rows.
"""
import ast
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")


def _enrichment_guard() -> str:
    main = next(n for n in ast.parse(SRC).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    for node in ast.walk(main):
        if isinstance(node, ast.If) and any(
                isinstance(c, ast.Call) and getattr(c.func, "id", "") == "run_standard_enrichment"
                for c in ast.walk(node)):
            return ast.unparse(node.test)
    raise AssertionError("run_standard_enrichment is no longer called inside an if in main()")


def test_enrichment_runs_only_when_not_a_dry_run():
    assert "not args.dry_run" in _enrichment_guard()
