"""A chapter matched by two or more links on a council's list is never re-pointed; it is reported.

Real data (fixture, read 2026-10-24): Woollahra's list links each DCP 2015 chapter AND its repealed
pre-2015 plan (three chapters); Randwick's links the in-force Stage 2 file AND an earlier draft
(two parts).
Known-wrong behaviour: "last link wins" flipped the stored link, so Woollahra served-rule chapters were
re-pointed at repealed plans and Randwick at a draft.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
for _k in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_k, "unused-in-this-test")

import r2_monitor as m  # noqa: E402

FX = json.loads((ROOT / "tests" / "fixtures" / "verifyops" / "duplicate_links_2026-10-24.json")
                .read_text(encoding="utf-8"))


def _diff(council):
    return m.diff_urls(FX[council]["discovered"], FX[council]["stored"], None)


def test_woollahra_three_chapters_are_ambiguous_and_not_migrated():
    d = _diff("woollahra")
    keys = sorted(k for k, _, _ in d.ambiguous)
    assert keys == ["chapter-c2-woollahra-hca", "chapter-c3-watsons-bay-hca", "chapter-f1-child-care-centres"]
    assert not {k for k, _, _ in d.url_migrated} & set(keys)


def test_randwick_draft_and_final_are_ambiguous():
    keys = {k for k, _, _ in _diff("randwick").ambiguous}
    assert {"b7-transport-traffic-parking-access", "randwick-dcp-c1-low-density"} <= keys


def test_the_candidates_name_both_documents():
    amb = {k: urls for k, _, urls in _diff("woollahra").ambiguous}
    urls = amb["chapter-c2-woollahra-hca"]
    assert any("chapter-c2-woollahra-hca.pdf" in u for u in urls)
    assert any("woollahra_hca_dcp_amendment_2.pdf" in u for u in urls)


def test_one_link_still_migrates():
    stored = [{"chapter_key": "k", "council_url": "https://c/old.pdf", "check_failures": 0}]
    d = m.diff_urls([{"chapter_key": "k", "url": "https://c/new.pdf", "label": "x"}], stored, None)
    assert d.url_migrated == [("k", "https://c/old.pdf", "https://c/new.pdf")] and d.ambiguous == []


def test_the_same_link_twice_is_not_ambiguous():
    stored = [{"chapter_key": "k", "council_url": "https://c/a.pdf", "check_failures": 0}]
    d = m.diff_urls([{"chapter_key": "k", "url": "https://c/a.pdf", "label": "x"},
                     {"chapter_key": "k", "url": "https://c/a.pdf", "label": "x (PDF)"}], stored, None)
    assert d.ambiguous == [] and d.url_same == ["k"]


def test_ambiguous_is_alerted_and_reseed_skips_it():
    src = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")
    assert "for key, stored_url, urls in diff.ambiguous:" in src
    assert 'results["hub_alerts"].append(f"ambiguous: {council}/{key}")' in src
    src = src.replace("\r\n", "\n")
    assert ("for key in [k for k, v in seen.items() if len(v) > 1]:\n"
            "                        discovered_map.pop(key, None)") in src
