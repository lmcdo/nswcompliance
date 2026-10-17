import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from frontage_setback_figures import pick_caption


def test_one_caption_gives_id():
    assert pick_caption("x\nFigure 14E.9-6: Building heights\n- 4m upper level setback") == "14E.9-6"


def test_same_caption_twice_is_one():
    assert pick_caption("Figure 14A.3: a\nFigure 14A.3: a") == "14A.3"


def test_two_captions_none():
    assert pick_caption("Figure 14E.9-6: a\nFigure 14E.9-7: b") is None


def test_zero_captions_none():
    assert pick_caption("no figure here") is None
    assert pick_caption("") is None


def test_prose_mention_without_colon_ignored():
    assert pick_caption("as shown in Figure 14E.9-6 the street wall") is None
    assert pick_caption("see Figure 14E.9-5 and\nFigure 14E.9-6: Heights") == "14E.9-6"
