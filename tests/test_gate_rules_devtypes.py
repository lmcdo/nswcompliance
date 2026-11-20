"""scripts/gate_rules_devtypes.py: narrow ONLY current ['ALL'] + config_all rows listed by council/chapter/text fingerprint."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import gate_rules_devtypes as g  # noqa: E402
import never_serve  # noqa: E402

TEXT = "Signs at a lower level than 2600mm above the footpath;"


class FakeCur:
    """Returns the rows for the SELECT and records UPDATEs. Rows: (id, text, tags)."""

    def __init__(self, rows):
        self.rows, self.updates, self.selects = rows, [], []

    def execute(self, sql, params=None):
        if sql.lstrip().upper().startswith("SELECT"):
            self.selects.append(params)
        else:
            self.updates.append(params)

    def fetchall(self):
        return self.rows


@pytest.fixture()
def one_entry(monkeypatch):
    e = {"council": "marrickville", "chapter_key": "", "tags": ["signage"], "expect": 1,
         "text_sha256_16": [never_serve.text_key(TEXT)]}
    monkeypatch.setattr(g, "entries", lambda: (e,))
    monkeypatch.setattr(never_serve, "ids", lambda: frozenset({999}))
    return e


def test_narrows_an_all_row_with_a_listed_text(one_entry):
    cur = FakeCur([(1, TEXT, ["ALL"])])
    ch = g.apply_dev_type_limits(cur, None, True)
    assert ch == [(1, "v2_applicable_dev_types", ["ALL"], ["signage"], "dev_type_limits")]
    assert cur.updates == [(["signage"], 1)]
    assert cur.selects == [("marrickville", None)]      # chapter_key "" means no chapter (IS NOT DISTINCT FROM NULL)


def test_dry_run_changes_nothing(one_entry):
    cur = FakeCur([(1, TEXT, ["ALL"])])
    assert len(g.apply_dev_type_limits(cur, None, False)) == 1
    assert cur.updates == []


@pytest.mark.parametrize("tags", [None, [], ["dwelling_house"], ["signage"], ["ALL", "signage"]])
def test_skips_anything_not_exactly_all(one_entry, tags):
    cur = FakeCur([(1, TEXT, tags)])
    assert g.apply_dev_type_limits(cur, None, True) == [] and cur.updates == []


def test_skips_unlisted_text_and_never_serve_ids(one_entry):
    cur = FakeCur([(1, TEXT + " and more", ["ALL"]), (999, TEXT, ["ALL"])])
    assert g.apply_dev_type_limits(cur, None, True) == [] and cur.updates == []


def test_whitespace_and_case_do_not_defeat_the_fingerprint(one_entry):
    cur = FakeCur([(1, "  SIGNS at a lower level\n than 2600mm above the footpath;  ", ["ALL"])])
    assert len(g.apply_dev_type_limits(cur, None, True)) == 1


def test_idempotent_second_run_finds_nothing(one_entry):
    first = FakeCur([(1, TEXT, ["ALL"])])
    g.apply_dev_type_limits(first, None, True)
    second = FakeCur([(1, TEXT, ["signage"])])
    assert g.apply_dev_type_limits(second, None, True) == []


def test_council_and_only_filters(one_entry):
    cur = FakeCur([(1, TEXT, ["ALL"])])
    assert g.apply_dev_type_limits(cur, "parramatta", True) == []
    assert g.apply_dev_type_limits(cur, None, True, {"some_other_rule"}) == []
    assert len(g.apply_dev_type_limits(cur, "marrickville", True, {"dev_type_limits"})) == 1


def test_the_real_file_is_consistent():
    g.entries.cache_clear()
    es = g.entries()                                     # raises on a miscount
    assert len(es) > 100 and sum(e["expect"] for e in es) == 1833
    hierarchy = (ROOT / "frontend-nextjs" / "lib" / "see" / "devTypeHierarchy.ts").read_text(encoding="utf-8")
    slugs = {t for e in es for t in e["tags"]}
    assert slugs <= {"signage", "commercial_premises", "industrial_development"}
    for s in slugs:
        assert re.search(rf"\b{s}\s*:", hierarchy), f"{s} is not a dev type the app knows"
    fps = [f for e in es for f in e["text_sha256_16"]]
    assert all(re.fullmatch(r"[0-9a-f]{16}", f) for f in fps)


def test_a_missing_file_raises(monkeypatch, tmp_path):
    g.entries.cache_clear()
    monkeypatch.setattr(g, "PATH", tmp_path / "nope.json")
    with pytest.raises(FileNotFoundError):
        g.entries()
    g.entries.cache_clear()
