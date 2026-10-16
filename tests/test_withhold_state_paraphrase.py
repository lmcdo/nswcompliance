"""The paraphrase list is ids only, bounded, and an empty list is refused."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("w", ROOT / "scripts" / "withhold_state_paraphrase.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def test_real_list_is_ids_only():
    ids = w.listed_ids()
    assert ids and all(isinstance(i, int) for i in ids) and len(ids) == len(set(ids))


def test_none_ids_dropped_and_empty_refused(tmp_path):
    p = tmp_path / "l.json"
    p.write_text(json.dumps([{"id": 5}, {"id": None}, {"id": 5}]), encoding="utf-8")
    assert w.listed_ids(p) == [5]
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit):
        w.listed_ids(p)
