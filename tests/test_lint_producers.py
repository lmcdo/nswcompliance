"""lint_producers must go RED on a new copy of a shared-fact producer, and never pass blind."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "page_integrity"))
import lint_producers as lp  # noqa: E402

PATTERNS = {"council": {"ts": [r"(function|const)\s+(toLgaSlug|councilKey)\b"],
                        "py": [r"def\s+_norm_lga\b"]}}


def _tree(root: Path, ts_body: str = "export function councilKey(n) {}\n") -> None:
    for d in ("frontend-nextjs/app", "frontend-nextjs/lib", "frontend-nextjs/components",
              "frontend-nextjs/hooks", "services"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts/conveyancing_db.py").write_text("x = 1\n")
    (root / "scripts/generate_conveyancing_report.py").write_text("x = 1\n")
    (root / "frontend-nextjs/lib/council-key.ts").write_text(ts_body)
    (root / "services/brief.py").write_text("def _norm_lga(n):\n    return n\n")


@pytest.fixture
def env(tmp_path, monkeypatch):
    pat = tmp_path / "patterns.json"
    pat.write_text(json.dumps(PATTERNS))
    monkeypatch.setattr(lp, "PATTERNS", pat)
    monkeypatch.setattr(lp, "BASELINE", tmp_path / "baseline.json")
    root = tmp_path / "repo"
    _tree(root)
    assert lp.main(["--update", "--allow-raise", "test baseline"], root=root) == 0
    return root


def test_unchanged_tree_is_green(env):
    assert lp.main([], root=env) == 0


def test_new_copy_in_a_new_file_is_red(env):
    (env / "frontend-nextjs/app/route.ts").write_text("const toLgaSlug = (s) => s;\n")
    assert lp.main([], root=env) == 1


def test_second_copy_in_same_file_is_red(env):
    (env / "frontend-nextjs/lib/council-key.ts").write_text(
        "export function councilKey(n) {}\nfunction toLgaSlug(n) {}\n")
    assert lp.main([], root=env) == 1


def test_removed_copy_is_released_not_red_and_update_locks_it(env, capsys):
    (env / "services/brief.py").write_text("x = 1\n")
    assert lp.main([], root=env) == 0
    assert "released" in capsys.readouterr().out
    assert lp.main(["--update"], root=env) == 0
    (env / "services/brief.py").write_text("def _norm_lga(n):\n    return n\n")
    assert lp.main([], root=env) == 1  # the copy cannot come back once released


def test_update_refuses_to_raise_without_reason(env):
    (env / "frontend-nextjs/app/route.ts").write_text("const toLgaSlug = (s) => s;\n")
    assert lp.main(["--update"], root=env) == 1


def test_missing_scope_is_could_not_look(env):
    import shutil
    shutil.rmtree(env / "services")
    assert lp.main([], root=env) == 2


def test_tests_and_node_modules_are_not_counted(env):
    (env / "frontend-nextjs/lib/x.test.ts").write_text("const toLgaSlug = 1\n")
    (env / "frontend-nextjs/lib/node_modules").mkdir()
    (env / "frontend-nextjs/lib/node_modules/y.ts").write_text("const toLgaSlug = 1\n")
    assert lp.main([], root=env) == 0


def test_real_baseline_matches_real_tree():
    """The committed baseline must describe the committed tree, or the ratchet is meaningless."""
    assert lp.main([]) == 0
