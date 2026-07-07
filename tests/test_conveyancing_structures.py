"""Golden + liability tests — conveyancing "Structures & records" section (Stage 1).

THE DEFINING CONSTRAINT: no rendered string, on ANY branch, may state or imply
that a structure is unapproved / illegal / unauthorised / non-compliant / a
breach / without consent. TestNoVerdictWordEverAppears renders every branch and
fails if any forbidden framing appears — this is the feature's primary defence,
a deterministic guard that does not depend on wording judgment.

Stage 1 uses ONLY application records (no imagery/detection call). Fixtures are
recorded live NSW OnlineDA/OnlineCDC responses (2026-07-07) for the Concord area
(City of Canada Bay), propId 1456609.
"""

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT))

from generate_conveyancing_report import (  # noqa: E402
    build_structures_records_lines,
    get_structures_records_live,
    _STRUCT_GAP_SENTENCE,
    _STRUCT_CONFIDENCE_FLOOR,
)

FIXTURES = Path(__file__).parent / "fixtures" / "structures_records"

# The forbidden framings — a verdict word on any path kills the feature. Matched
# case-insensitively as whole words / phrases against every rendered string.
FORBIDDEN_FRAMINGS = [
    "unapproved", "illegal", "unauthorised", "unauthorized",
    "non-compliant", "noncompliant", "breach", "without consent", "no approval",
]


def _records():
    with open(FIXTURES / "concord_records.json", encoding="utf-8") as fh:
        return json.load(fh)


def _all_strings(out: dict) -> list:
    """Flatten every user-facing string a renderer would print from a result."""
    strings = []
    for key in ("intro", "status_line", "detection_note"):
        if out.get(key):
            strings.append(out[key])
    strings.extend(out.get("record_lines") or [])
    strings.extend(out.get("gap_lines") or [])
    return strings


def _assert_no_verdict(out: dict):
    blob = " \n ".join(_all_strings(out)).lower()
    for word in FORBIDDEN_FRAMINGS:
        assert word not in blob, f"forbidden framing {word!r} appeared: {blob!r}"


# ---------------------------------------------------------------------------
# THE PRIMARY DEFENCE — no verdict word on ANY branch
# ---------------------------------------------------------------------------

class TestNoVerdictWordEverAppears:
    def test_every_branch_is_verdict_free(self):
        recs = _records()
        det_match = [{"label": "dwelling", "confidence": 0.9}]
        det_gap = [{"label": "studio", "confidence": 0.9}]
        det_lowconf = [{"label": "studio", "confidence": 0.1}]
        branches = [
            build_structures_records_lines(None, records_status="failed"),
            build_structures_records_lines(None),
            build_structures_records_lines([]),
            build_structures_records_lines(recs),
            build_structures_records_lines([], detections=det_gap),
            build_structures_records_lines(recs, detections=det_match),
            build_structures_records_lines(recs, detections=det_gap),
            build_structures_records_lines(recs, detections=det_lowconf),
            build_structures_records_lines(recs, detections=[]),
        ]
        for out in branches:
            _assert_no_verdict(out)

    def test_gap_sentence_constant_is_verdict_free(self):
        low = _STRUCT_GAP_SENTENCE.lower()
        for word in FORBIDDEN_FRAMINGS:
            assert word not in low

    def test_generator_source_has_no_verdict_words_in_struct_block(self):
        """The section's own source strings must be verdict-free too — a future
        edit that introduces one fails here even before rendering."""
        src = (_ROOT / "scripts" / "generate_conveyancing_report.py").read_text(encoding="utf-8")
        # scan only the structures block constants region
        start = src.index("_STRUCT_INTRO")
        end = src.index("def build_structures_records_lines")
        block = src[start:end].lower()
        for word in FORBIDDEN_FRAMINGS:
            # the word may appear in COMMENTS explaining the rule; scan only the
            # string-literal constant values by excluding lines starting with #.
            for line in block.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                assert word not in line.lower(), f"{word!r} in struct constant: {line!r}"


# ---------------------------------------------------------------------------
# Three-state records handling
# ---------------------------------------------------------------------------

class TestRecordsStates:
    def test_failed_lookup_is_not_assessed(self):
        out = build_structures_records_lines(None, records_status="failed")
        assert out["not_assessed"] is True
        assert out["status_line"].startswith("Not assessed")
        assert out["record_lines"] == []

    def test_none_records_is_not_assessed_never_no_applications(self):
        """Mutation guard: a None records list must render Not assessed, never
        the 'no applications' sentence (which is only for a successful empty)."""
        out = build_structures_records_lines(None)
        assert out["not_assessed"] is True
        assert "No development or complying-development applications" not in (out["status_line"] or "")

    def test_empty_records_states_none_found_with_hedges(self):
        out = build_structures_records_lines([])
        assert out["not_assessed"] is False
        assert "No development or complying-development applications" in out["status_line"]
        assert "2019" in out["status_line"]
        assert "exempt" in out["status_line"]

    def test_records_present_render_verbatim(self):
        out = build_structures_records_lines(_records())
        assert out["record_lines"]
        joined = " ".join(out["record_lines"])
        # a real recorded PAN + dev_type renders verbatim
        assert "PAN-107653" in joined
        assert "Alterations and additions to residential development" in joined

    def test_stage1_detection_not_run_note(self):
        """Stage 1: detections is None → the honest 'detection not run' note,
        never an implied 'no unauthorised structures'."""
        out = build_structures_records_lines(_records())
        assert out["detection_note"] is not None
        assert "not performed" in out["detection_note"]
        assert out["gap_lines"] == []


# ---------------------------------------------------------------------------
# Gap sentence (Stage 2 machinery) — every hedge clause load-bearing
# ---------------------------------------------------------------------------

class TestGapSentenceHedges:
    def test_unmatched_detection_produces_hedged_sentence(self):
        out = build_structures_records_lines([], detections=[{"label": "cabin", "confidence": 0.9}])
        assert len(out["gap_lines"]) == 1
        gap = out["gap_lines"][0]
        # every hedge clause present (mutation: deleting any fails). After the
        # legal red-team the sentence LEADS with the data window and carries an
        # explicit non-imputation line; it does NOT use the "question" framing.
        assert "2019" in gap
        assert "exempt" in gap
        assert "vendor" in gap
        assert "not, on its own, a finding" in gap  # the non-imputation line
        assert "Section 10.7" in gap
        # the "structure visible ... no record" imputation ordering is gone:
        # the sentence must not OPEN with the incriminating pairing.
        assert not gap.startswith("A structure is visible")

    def test_matched_detection_produces_no_gap(self):
        recs = [{"dev_type": "Secondary dwelling; studio", "description": "studio"}]
        out = build_structures_records_lines(recs, detections=[{"label": "studio", "confidence": 0.9}])
        assert out["gap_lines"] == []

    def test_low_confidence_detection_dropped_no_gap(self):
        """Risk #3: a low-confidence detection (shadow/vegetation) must NOT
        generate a gap line."""
        out = build_structures_records_lines(
            [], detections=[{"label": "shed", "confidence": _STRUCT_CONFIDENCE_FLOOR - 0.01}],
        )
        assert out["gap_lines"] == []

    def test_confidence_at_floor_is_usable(self):
        out = build_structures_records_lines(
            [], detections=[{"label": "shed", "confidence": _STRUCT_CONFIDENCE_FLOOR}],
        )
        assert len(out["gap_lines"]) == 1

    def test_pre2019_approved_structure_is_hedged_by_2019_clause(self):
        """Break-it: a structure approved in 2005 (pre-portal) that shows as a
        gap is made non-accusatory by the ~2019 clause — assert it's present."""
        out = build_structures_records_lines([], detections=[{"label": "garage", "confidence": 0.9}])
        assert "around 2019" in out["gap_lines"][0]


# ---------------------------------------------------------------------------
# get_structures_records_live — fetch orchestration (reuse, no new fetcher)
# ---------------------------------------------------------------------------

class TestGetStructuresRecordsLive:
    """The council name OnlineDA accepts is API-specific and hardcoded maps drift,
    so get_structures_records_live validates against the API's OWN vocabulary
    (_fetch_eplanning_page probe) before trusting a result. These tests drive
    that seam so no live HTTP is made."""

    def _patch(self, monkeypatch, probe_rows, da=None, cc=None, exc=None):
        import pre_da_history as pdh

        def _probe(endpoint, filters, page):
            return probe_rows

        monkeypatch.setattr(pdh, "_fetch_eplanning_page", _probe)
        if exc:
            monkeypatch.setattr(pdh, "get_da_events", lambda c, f: (_ for _ in ()).throw(exc))
        else:
            monkeypatch.setattr(pdh, "get_da_events", lambda c, f: da or [])
            monkeypatch.setattr(pdh, "get_pcc_events", lambda c, f: cc or [])

    def test_no_council_is_failed_not_empty(self):
        recs, status = get_structures_records_live(None, "1 Test St, Suburb NSW")
        assert recs is None
        assert status == "failed"

    def test_council_unrecognised_by_api_fails_closed(self, monkeypatch):
        """The silent-wrong-result guard: a council name the API does not
        recognise returns zero rows (empty probe), which would print a FALSE
        'no records'. It must fail closed to 'Not assessed'."""
        self._patch(monkeypatch, probe_rows=[])  # API returns nothing for this name
        recs, status = get_structures_records_live("Wrong Council Name", "addr")
        assert recs is None
        assert status == "failed"

    def test_recognised_council_returns_records(self, monkeypatch):
        self._patch(
            monkeypatch,
            probe_rows=[{"PlanningPortalApplicationNumber": "PAN-x"}],  # API knows this council
            da=[{"pan": "PAN-1", "app_type": "Development Application"}],
            cc=[{"pan": "CC-1", "app_type": "Construction Certificate"}],
        )
        recs, status = get_structures_records_live("City of Canada Bay Council",
                                                   "14 Stanley Street, Concord NSW 2137")
        assert status == "ok"
        assert {r["pan"] for r in recs} == {"PAN-1", "CC-1"}

    def test_recognised_council_genuine_empty_is_ok_not_failed(self, monkeypatch):
        """A recognised council with no application matching the address is a
        GENUINE empty (status ok, [] records) — distinct from a name mismatch."""
        self._patch(monkeypatch, probe_rows=[{"x": 1}], da=[], cc=[])
        recs, status = get_structures_records_live("Inner West Council", "addr")
        assert status == "ok"
        assert recs == []

    def test_fetch_exception_is_failed(self, monkeypatch):
        self._patch(monkeypatch, probe_rows=[{"x": 1}], exc=RuntimeError(" eplanning down "))
        recs, status = get_structures_records_live("Inner West Council", "addr")
        assert recs is None
        assert status == "failed"
