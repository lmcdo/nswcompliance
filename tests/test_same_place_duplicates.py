"""same_place_duplicates: only one rule shown twice at the SAME place is listed; the same words elsewhere are kept."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import same_place_duplicates as spd  # noqa: E402

KEY = ("p1", "{ALL}", "{ALL}", "none", None, None, None, None)


def row(i, ref, page, text="Fences must not exceed 1.2m.", key=KEY, doc="D", proven=True):
    return {"id": i, "document_id": doc, "council": "x", "ref": ref, "text": text, "page": page,
            "proven": proven, "key": key}


def ids(groups):
    return sorted(sorted(r["id"] for r in g) for g in groups)


def test_same_ref_is_one_place():
    assert ids(spd.same_place_groups([row(1, "C4 a", 5), row(2, "C4 a~2", 9)])) == [[1, 2]]   # same ref, ~N dropped
    assert ids(spd.same_place_groups([row(1, "Clause 6.6", None), row(2, "6.6", None)])) == [[1, 2]]


def test_same_words_elsewhere_are_kept():
    assert spd.same_place_groups([row(1, "3.30(1)", 61), row(2, "3D.61(1)", 398)]) == []       # another code
    assert spd.same_place_groups([row(1, "4.1", 12), row(2, "4.2", 12)]) == []                 # two clauses, one page
    assert spd.same_place_groups([row(1, "x__Part 8~100", 63), row(2, "x__Part 8~81", 62)]) == []  # a whole Part
    other = ("p2",) + KEY[1:]
    assert spd.same_place_groups([row(1, "C4 a", 5), row(2, "C4 a", 5, key=other)]) == []      # another area
    assert spd.same_place_groups([row(1, "C4 a", 5), row(2, "C4 a", 5, doc="E")]) == []        # another document


def test_kept_row_is_the_proven_clause_labelled_one():
    g = [row(5, "provision_9", 3, proven=True), row(4, "2.34", 3, proven=False), row(7, "Clause 2.34", 3)]
    g.sort(key=spd.keep_order)
    assert g[0]["id"] == 7   # proven, clause-shaped label; lowest id breaks only a full tie


def test_rows_without_a_label_are_not_one_place_by_label():
    # cross-review 2026-10-17: two NULL refs normalise to '' and must not count as the same clause
    assert spd.same_place_groups([row(1, None, 4), row(2, None, 9)]) == []
    assert spd.same_place_groups([row(1, None, 4), row(2, "", 4)]) == []              # nor the same page
