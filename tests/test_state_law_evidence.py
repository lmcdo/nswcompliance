"""Rules 1-3 of scripts/state_law_evidence.py and the evidence verifier, on a small synthetic instrument.

Every rule has a test that PASSES on a good input and a test that FAILS (is refused) on a deliberately broken one.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import state_law_evidence as ev  # noqa: E402
import verify_state_law_evidence as vse  # noqa: E402

REPEAT = "The consent authority must not grant consent unless it is satisfied that the development is compatible"


def clause(cid, no, title, body):
    return (f'<div id="{cid}" class="frag-clause"><div role="heading" class="heading"><span class="frag-no">{no}</span>'
            f'&nbsp;&nbsp;<span id="{cid}-he" class="frag-heading">{title}</span></div>'
            f'<blockquote class="children">{body}</blockquote></div>')


def sub(sid, no, text):
    return f'<div id="{sid}" class="frag-subclause"><blockquote><span class="frag-no">{no}</span>&nbsp;{text}</blockquote></div>'


def part(pid, no, title, inner):
    return (f'<div id="{pid}" class="frag-part"><div role="heading" class="heading"><span class="frag-no">{no}</span>'
            f'  <span id="{pid}-he" class="frag-heading">{title}</span></div>{inner}</div>')


HTML = ("<html><body>"
        + clause("sec.1", "1", "Name", "This Policy is the Example Policy 2021 and applies across the whole State of New South Wales.")
        + clause("sec.2", "2", "Aims", "The aims of this Policy are to facilitate the delivery of housing near public transport nodes.")
        + clause("sec.3", "3", "Gap", "An unrelated clause lives here and stays out of every adjacent span in these tests today.")
        + part("ch.1-pt.1", "Part 1", "Preliminary", clause("sec.4", "4", "Consent", REPEAT + " with the surroundings."))
        + part("ch.1-pt.2", "Part 2", "Development in rural areas", clause("sec.5", "5", "Consent", REPEAT + " with rural land."))
        + clause("sec.6", "6", "Twice", sub("sec.6-ssec.1", "(1)", "Every applicant must give written notice to the owner of adjoining land")
                 + sub("sec.6-ssec.2", "(2)", "Every applicant must give written notice to the owner of adjoining land"))
        + "</body></html>")
RAW = HTML.encode("utf-8")
SHA = hashlib.sha256(RAW).hexdigest()
SNAP = ev.parse_snapshot("epi-test", RAW)


def n(t):
    return ev.row_norm(t)


# ---------------------------------------------------------------------------------------- normaliser
def test_normaliser_is_idempotent_and_deterministic():
    t = "# Title\nThe  area of 10² m– **bold** and\nwrapped-\nword"
    a = ev.row_norm(t)
    assert a == ev.row_norm(t) and ev.normalise(a) == a
    assert "Title" not in a and "*" not in a and "wrappedword" in a


# ---------------------------------------------------------------------------------------- rule 1
def test_rule1_excerpt_records_unit_and_offsets():
    row = n("applies across the whole State of New South Wales")
    v = ev.prove(SNAP, row)
    assert v["status"] == "proven" and v["rule"] == 1 and v["matcher"] == ev.M_EXCERPT
    u = v["units"][0]
    assert u["id"] == "sec.1"
    unit = SNAP.items[SNAP.by_id["sec.1"]]
    assert SNAP.D[unit.start + u["start"]: unit.start + u["end"]] == row


def test_rule1_two_subclauses_with_same_words_is_ambiguous():
    v = ev.prove(SNAP, n("Every applicant must give written notice to the owner of adjoining land"))
    assert v["status"] == "ambiguous"        # sec.6-ssec.1 AND ssec.2, no PDF -> never proven


def test_rule1_smallest_unit_is_the_subclause_not_the_clause():
    h = HTML.replace("</body>", clause("sec.7", "7", "Nest", sub("sec.7-ssec.1", "(1)", "A person must keep every record required by this clause for seven years")) + "</body>")
    snap = ev.parse_snapshot("epi-test", h.encode())
    v = ev.prove(snap, n("must keep every record required by this clause for seven years"))
    assert v["units"][0]["id"] == "sec.7-ssec.1"


def test_rule1_refuses_changed_word():
    row = n("applies across the whole State of New South Wales").replace("whole", "entire")
    assert ev.prove(SNAP, row)["status"] == "unproven"


def test_rule1_refuses_row_that_starts_mid_word():
    row = "pplies across the whole State of New South Wales"
    assert ev.prove(SNAP, row)["status"] == "unproven"


def test_rule1_refuses_under_eight_words():
    assert ev.prove(SNAP, n("applies across the whole State"))["reason"] == "too_short"


def test_rule1_repeat_in_two_units_is_ambiguous_not_proven():
    v = ev.prove(SNAP, n(REPEAT))
    assert v["status"] == "ambiguous" and len(v["spans"]) == 2


# ---------------------------------------------------------------------------------------- rule 2
def test_rule2_adjacent_units_concatenation():
    text = ev.D_text = SNAP.D[SNAP.items[SNAP.by_id["sec.1"]].start: SNAP.items[SNAP.by_id["sec.2"]].end]
    v = ev.prove(SNAP, n(text))
    assert v["status"] == "proven" and v["rule"] == 2 and [u["id"] for u in v["units"]] == ["sec.1", "sec.2"]


def test_rule2_refuses_non_adjacent_units():
    one = SNAP.D[SNAP.items[SNAP.by_id["sec.1"]].start: SNAP.items[SNAP.by_id["sec.1"]].end]
    three = SNAP.D[SNAP.items[SNAP.by_id["sec.3"]].start: SNAP.items[SNAP.by_id["sec.3"]].end]
    assert ev.prove(SNAP, n(one + " " + three))["status"] == "unproven"


def test_rule2_refuses_extra_word_between_units():
    a = SNAP.items[SNAP.by_id["sec.1"]]
    b = SNAP.items[SNAP.by_id["sec.2"]]
    text = SNAP.D[a.start:a.end] + " EXTRA " + SNAP.D[b.start:b.end]
    assert ev.prove(SNAP, n(text))["status"] == "unproven"


# ---------------------------------------------------------------------------------------- rule 3
def test_rule3_page_heading_singles_out_one_part():
    v = ev.prove_by_page_heading(SNAP, n(REPEAT), "Header\nPart 2 Development in rural areas\n5 Consent ...")
    assert v and v["rule"] == 3 and v["container_id"] == "ch.1-pt.2" and v["units"][0]["id"] == "sec.5"


def test_rule3_refuses_when_page_has_no_matching_heading():
    assert ev.prove_by_page_heading(SNAP, n(REPEAT), "Part 9 Something else entirely") is None


def test_rule3_refuses_when_the_part_itself_repeats_the_text():
    h = HTML.replace("</body>", part("ch.2-pt.3", "Part 3", "Doubled", clause("sec.8", "8", "A", REPEAT + " one.")
                                      + clause("sec.9", "9", "B", REPEAT + " two.")) + "</body>")
    snap = ev.parse_snapshot("epi-test", h.encode())
    assert ev.prove_in_container(snap, n(REPEAT), "ch.2-pt.3") is None
    assert ev.prove_by_page_heading(snap, n(REPEAT), "Part 3 Doubled") is None


def test_rule3_refuses_when_page_prints_both_parts():
    page = "Part 1 Preliminary ... Part 2 Development in rural areas"
    assert ev.prove_by_page_heading(SNAP, n(REPEAT), page) is None


# ---------------------------------------------------------------------------------------- verifier
def _record(rule_text):
    rn = n(rule_text)
    v = ev.prove(SNAP, rn)
    return {"id": 1, "text_md5": "x", "row_norm": rn, "row_norm_md5": ev.md5(rn),
            "evidence": {k: x for k, x in v.items() if k not in ("status", "spans")}}


def _cache(tmp_path):
    (tmp_path / f"epi-test_2026-10-17.html").write_bytes(RAW)
    return tmp_path


def test_verifier_accepts_good_records(tmp_path):
    cache = _cache(tmp_path)
    assert vse.verify_record(_record("applies across the whole State of New South Wales"), {}, cache) == []
    a, b = SNAP.items[SNAP.by_id["sec.1"]], SNAP.items[SNAP.by_id["sec.2"]]
    assert vse.verify_record(_record(SNAP.D[a.start:b.end]), {}, cache) == []


def test_verifier_rejects_tampered_offsets(tmp_path):
    rec = _record("applies across the whole State of New South Wales")
    rec["evidence"]["abs_start"] += 1
    assert vse.verify_record(rec, {}, _cache(tmp_path))


def test_verifier_rejects_tampered_row_text(tmp_path):
    rec = _record("applies across the whole State of New South Wales")
    rec["row_norm"] = rec["row_norm"].replace("whole", "entire")
    assert vse.verify_record(rec, {}, _cache(tmp_path)) == ["row_norm_md5_mismatch"]


def test_verifier_rejects_wrong_unit_or_snapshot_or_version(tmp_path):
    cache = _cache(tmp_path)
    rec = _record("applies across the whole State of New South Wales")
    r2 = json.loads(json.dumps(rec)); r2["evidence"]["units"][0]["id"] = "sec.2"
    assert vse.verify_record(r2, {}, cache)
    r3 = json.loads(json.dumps(rec)); r3["evidence"]["snapshot_sha256"] = "0" * 64
    assert vse.verify_record(r3, {}, cache) == ["snapshot_missing"]
    r4 = json.loads(json.dumps(rec)); r4["evidence"]["normaliser"] = "sl-norm/9"
    assert vse.verify_record(r4, {}, cache)[0].startswith("unknown_normaliser")


def test_verifier_rejects_a_claim_the_matcher_would_not_make(tmp_path):
    """A forged rule-1 record for text that occurs twice must fail re-derivation."""
    rn = n(REPEAT)
    s, e = ev.occurrences(SNAP, rn)[0]
    k = ev.deepest_text_unit(SNAP, s, e)
    u = SNAP.items[k]
    rec = {"id": 2, "text_md5": "x", "row_norm": rn, "row_norm_md5": ev.md5(rn),
           "evidence": {"epi": "epi-test", "snapshot_sha256": SHA, "normaliser": ev.NORMALISER, "parser": ev.PARSER,
                        "rule": 1, "matcher": ev.M_EXCERPT, "tier": "exact", "abs_start": s, "abs_end": e,
                        "units": [{"id": u.id, "cls": u.cls, "start": s - u.start, "end": e - u.start,
                                   "unit_chars": u.end - u.start}], "whole_unit": False}}
    assert "rederivation_differs" in vse.verify_record(rec, {}, _cache(tmp_path))


def test_verifier_cli_exit_codes(tmp_path):
    cache = _cache(tmp_path)
    good = _record("applies across the whole State of New South Wales")
    f = tmp_path / "e.jsonl"
    f.write_text(json.dumps(good) + "\n", encoding="utf8")
    assert vse.main([str(f), "--cache", str(cache)]) == 0
    bad = json.loads(json.dumps(good)); bad["evidence"]["abs_end"] -= 1
    f.write_text(json.dumps(bad) + "\n", encoding="utf8")
    assert vse.main([str(f), "--cache", str(cache)]) == 1
    f.write_text(json.dumps(good) + "\n", encoding="utf8")
    assert vse.main([str(f), "--cache", str(tmp_path / "none"), "--allow-missing-snapshots"]) == 2
    assert vse.main([str(f), "--cache", str(tmp_path / "none")]) == 1


def test_determinism_same_input_same_evidence():
    row = n("applies across the whole State of New South Wales")
    again = ev.prove(ev.parse_snapshot("epi-test", RAW), row)
    assert again == ev.prove(SNAP, row)
