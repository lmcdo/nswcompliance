"""verifyops_classify on the 28 documents the monitor found and left waiting (saved 2026-10-23).

Expected verdicts were read by a person from each document's cover, independently of the code.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verifyops_classify as V  # noqa: E402

DOCS = {d["id"]: d for d in json.loads(
    (ROOT / "tests/fixtures/verifyops/new_docs_2026-10-23.json").read_text(encoding="utf-8"))}
TODAY = date(2026, 10, 23)
# Served rows these duplicates match (id, council_url, content_hash), measured 2026-10-23.
SERVED = {
    805: {"id": 725, "council_url": "https://elsewhere.example/part3.pdf", "content_hash": DOCS[805].get("sha256")},
    812: {"id": 316, "council_url": "https://elsewhere.example/5.1.pdf", "content_hash": DOCS[812].get("sha256")},
    813: {"id": 317, "council_url": "https://elsewhere.example/5.2.pdf", "content_hash": DOCS[813].get("sha256")},
}

EXPECTED = {
    752: "not_dcp", 753: "not_dcp", 754: "not_dcp", 755: "not_dcp", 756: "not_dcp", 757: "not_dcp",
    758: "not_dcp", 785: "red", 786: "red", 793: "not_dcp", 798: "dcp", 799: "not_dcp", 800: "red",
    801: "not_dcp", 802: "not_dcp", 803: "not_dcp", 804: "not_dcp", 805: "duplicate", 806: "red",
    807: "not_dcp", 808: "not_dcp", 809: "not_dcp", 810: "not_dcp", 811: "not_dcp",
    812: "duplicate", 813: "duplicate", 814: "dcp", 815: "red",
}


@pytest.mark.parametrize("doc_id,verdict", sorted(EXPECTED.items()))
def test_each_real_document_gets_the_verdict_a_person_read(doc_id, verdict):
    reg = [SERVED[doc_id]] if doc_id in SERVED else []
    assert V.classify(DOCS[doc_id], reg, TODAY)["verdict"] == verdict


def test_a_duplicate_names_the_served_row():
    assert V.classify(DOCS[805], [SERVED[805]], TODAY)["of"] == 725


def test_a_served_file_under_another_label_is_found_by_address_too():
    doc = dict(DOCS[805], sha256=None)
    row = {"id": 725, "council_url": DOCS[805]["url"].upper(), "content_hash": None}
    assert V.classify(doc, [row], TODAY) == {"verdict": "duplicate", "of": 725, "why": "same address"}


def test_a_row_is_never_its_own_duplicate():
    row = {"id": 805, "council_url": DOCS[805]["url"], "content_hash": DOCS[805]["sha256"]}
    assert V.classify(DOCS[805], [row], TODAY)["verdict"] == "dcp"


def test_bayside_cover_gives_its_one_effective_date():
    v = V.classify(DOCS[805], [], TODAY)
    assert (v["effective"], v["in_force"], v["needs_person"]) == ("2026-04-17", True, False)


def test_a_future_effective_date_is_not_in_force():
    v = V.classify(DOCS[805], [], date(2026, 4, 16))
    assert (v["effective"], v["in_force"]) == ("2026-04-17", False)


def test_a_plan_is_in_force_on_its_effective_day():
    assert V.classify(DOCS[805], [], date(2026, 4, 17))["in_force"] is True


def test_amendment_history_dates_are_not_read():
    # Bayside's page 1 runs on into its Amendment History; only the cover before it counts.
    cover = V.cover_text(DOCS[805]["first_pages_text"])
    assert "Amendment History" not in cover and "Table of Contents" not in cover
    fake = {"id": 1, "url": "x", "first_pages_text": [
        "Example Development Control Plan 2026 Amendment History Effective: 1 January 2010"]}
    assert V.classify(fake, [], TODAY)["effective"] is None


def test_two_dates_on_a_cover_need_a_person():
    doc = {"id": 1, "url": "x", "first_pages_text": [
        "Example Development Control Plan Effective: 1 March 2020 came into effect on 5 May 2024"]}
    v = V.classify(doc, [], TODAY)
    assert (v["effective"], v["needs_person"]) == (None, True)
    assert "more than one" in v["why"]


def test_a_dcp_chapter_with_no_date_needs_a_person():
    v = V.classify(DOCS[814], [], TODAY)
    assert (v["verdict"], v["needs_person"], v["effective"]) == ("dcp", True, None)


def test_a_draft_dcp_is_flagged():
    doc = {"id": 1, "url": "x", "first_pages_text": ["DRAFT Example Development Control Plan 2027"]}
    assert V.classify(doc, [], TODAY)["draft"] is True


def test_a_failed_download_is_red_with_the_reason():
    assert V.classify(DOCS[785], [], TODAY)["why"].startswith("could not read the document")


# ── read_document ─────────────────────────────────────────────────────────────
def test_a_web_page_served_instead_of_a_pdf_is_an_error():
    out = V.read_document(b"<!DOCTYPE html><html>blocked</html>")
    assert out["error"] == "not_pdf" and len(out["sha256"]) == 64


def test_a_damaged_pdf_is_an_error_not_a_crash():
    assert V.read_document(b"%PDF-1.7 garbage")["error"].startswith("unreadable_pdf")


def test_each_written_verdict_is_committed(monkeypatch):
    class Conn:
        commits = 0

        def commit(self):
            Conn.commits += 1

        def rollback(self):
            raise AssertionError("no rollback expected")

    monkeypatch.setattr(V, "pending", lambda c: [{"id": 1, "council": "x", "label": "a", "url": "u1"},
                                                 {"id": 2, "council": "x", "label": "b", "url": "u2"}])
    monkeypatch.setattr(V, "council_rows", lambda c, council: [])
    monkeypatch.setattr(V, "read_document", lambda b: {"sha256": "s", "first_pages_text": DOCS[807]["first_pages_text"]})
    monkeypatch.setattr(V, "write_verdict", lambda c, rid, v: 1)
    assert V.classify_pending(Conn(), lambda u: b"", TODAY, dry_run=False) == {"not_dcp": 2}
    assert Conn.commits == 2
