"""apply_sepp_marker_blind.duplicate_problems: two plan rows must not end as the same rule (2026-10-17)."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import apply_sepp_marker_blind as ap  # noqa: E402


def row(i, ref, text, new_ref=None, doc="doc"):
    return {"id": i, "rule": "recopy", "document_id": doc, "ref_number": ref, "new_ref_number": new_ref,
            "old_text": "old", "new_text": text}


def test_same_label_and_text_refused():
    assert ap.duplicate_problems([row(1, "Clause 6.12", "x"), row(2, "Clause 6.12", "x")], {}, [])


def test_same_text_different_labels_refused():
    # 8759 / 8760 on 2026-10-17: the text is written before the label, so the unique index tripped mid-write
    bad = ap.duplicate_problems([row(1, "Clause 6.24", "x"), row(2, "Clause 6.24", "x", "Clause 6.24(4)")], {}, [])
    assert bad and "duplicate rule" in bad[0]


def test_different_text_passes():
    assert not ap.duplicate_problems([row(1, "Clause 6.24", "x"), row(2, "Clause 6.24", "y")], {}, [])


def test_same_text_other_document_passes():
    assert not ap.duplicate_problems([row(1, "Clause 6.24", "x", doc="a"), row(2, "Clause 6.24", "x", doc="b")], {}, [])


def test_same_text_as_a_served_row_outside_the_plan_refused():
    import hashlib
    m = hashlib.md5("x".encode()).hexdigest()
    assert ap.duplicate_problems([row(1, "Clause 2", "x")], {}, [(9, "doc", "Clause 1", "", m, True)])


def test_same_text_as_a_withheld_row_outside_the_plan_passes():
    import hashlib
    m = hashlib.md5("x".encode()).hexdigest()
    assert not ap.duplicate_problems([row(1, "Clause 2", "x")], {}, [(9, "doc", "Clause 1", "", m, False)])
