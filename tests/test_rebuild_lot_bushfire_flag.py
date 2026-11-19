"""scripts/rebuild_lot_bushfire_flag.py: only lots whose flag really changes are written, and the work is split evenly and without overlap."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import rebuild_lot_bushfire_flag as rf  # noqa: E402


def test_only_real_changes_are_returned_and_null_counts_as_false():
    rows = [("a", True, True), ("b", False, True), ("c", True, False), ("d", None, False), ("e", None, True), ("f", False, False)]
    assert rf.changed_lots(rows) == [("b", False, True), ("c", True, False), ("e", None, True)]


def test_every_first_character_goes_to_exactly_one_worker_and_loads_are_even():
    groups = [("1", 500), ("2", 400), ("3", 300), ("4", 250), ("A", 100), ("/", 50)]
    parts = rf.split_groups(groups, 3)
    flat = [c for p in parts for c in p]
    assert sorted(flat) == sorted(c for c, _ in groups) and len(flat) == len(set(flat))   # no lot group dropped or doubled
    counts = dict(groups)
    loads = [sum(counts[c] for c in p) for p in parts]
    assert max(loads) - min(loads) <= 300


def test_a_single_worker_takes_everything():
    assert sorted(rf.split_groups([("1", 5), ("2", 4)], 1)[0]) == ["1", "2"]


def test_the_update_touches_only_the_bushfire_flag_column_and_never_deletes():
    src = (REPO / "scripts" / "rebuild_lot_bushfire_flag.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "SET bushfire_prone = v.new_flag" in code
    assert "DELETE" not in code.upper() and "TRUNCATE" not in code.upper() and "DROP " not in code.upper()


def test_keyset_workers_leave_the_group_workers_lots_alone():
    assert rf.keep_ids(["1A", "2B", "EC", "3D"], "1E") == ["2B", "3D"]
    assert rf.keep_ids(["1A"], "") == ["1A"]


def test_only_keeps_just_the_named_groups():
    assert rf.keep_ids(["1A", "2B", "EC", "3D"], "", "1E") == ["1A", "EC"]
    assert rf.keep_ids(["1A", "2B", "EC"], "E", "1E") == ["1A"]
