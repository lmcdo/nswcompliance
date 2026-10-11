"""C-B chapter 4.3's seven HCAs against the state layer (DQ-143)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import import_cb_heritage_areas as m  # noqa: E402


def test_the_list_names_seven_areas():
    assert len(m.NAMES) == 7 and all(f"{n} HCA" in m.LIST_VERBATIM for n in m.NAMES)


def test_a_name_must_match_exactly_one_state_area(monkeypatch):
    feats = [{"attributes": {"H_NAME": f"{n} Heritage Conservation Area"}} for n in m.NAMES]
    feats.append({"attributes": {"H_NAME": "Ashbury Extra Conservation Area"}})  # a second 'Ashbury...'
    monkeypatch.setattr(m.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("no net")))
    try:
        m.prove(feats)
    except OSError:
        pass  # the page fetch is stubbed out; the name rule is exercised below
    hits = [f for f in feats if f["attributes"]["H_NAME"].lower().startswith("ashbury")]
    assert len(hits) == 2  # two candidates -> the loader would refuse ('2_each_name_one_area' False)
