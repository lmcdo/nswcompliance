"""The post-write enrichment sequence: which phases run, in what order, and what
happens when one of them breaks.

WHY THIS FILE EXISTS. Three phases that exist and work were called by nothing --
not the extractor, not the commit worker, not any script. They were missed
because the phase list was three lines COPIED into two files, so "the list" was
never a thing anyone could look at. Measured 2026-09-11 before the fix:
v2_provision_type was NULL on 3,216 served rows (marrickville 2,326 of its 2,403
-- 97% of that council had no provision type at all), v2_site_condition_required
on another 3,216, and v2_dev_type_source on 1,142.

These tests do not touch the database. They assert the shape of the sequence and
its failure behaviour, which is where the defect actually lived.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from enrichment import pipeline  # noqa: E402


# --- the list itself -------------------------------------------------------

def test_all_six_phases_are_named_and_every_one_resolves():
    """A renamed or deleted phase must break a test, not go quietly missing.

    That is the whole defect class: a phase can stop being called without
    anything failing, because nothing asserts the list is complete.
    """
    labels = [label for label, _ in pipeline.STANDARD_ENRICHMENT_PHASES]
    fns = [fn for _, fn in pipeline.STANDARD_ENRICHMENT_PHASES]
    assert len(fns) == 6, f"expected six phases, got {len(fns)}: {fns}"
    assert len(set(fns)) == 6, "a phase is listed twice"
    assert len(set(labels)) == 6, "two phases share a label"
    for fn_name in fns:
        assert callable(getattr(pipeline, fn_name, None)), (
            f"{fn_name} is named in STANDARD_ENRICHMENT_PHASES but is not a "
            f"callable in enrichment.pipeline"
        )


def test_the_three_previously_unwired_phases_are_in_the_list():
    fns = [fn for _, fn in pipeline.STANDARD_ENRICHMENT_PHASES]
    for fn_name in ("run_site_condition_tagging", "run_type_classification",
                    "run_applicability_provenance"):
        assert fn_name in fns, f"{fn_name} is not wired -- this is the DEFECT, restored"


def test_numeric_extraction_is_not_wired():
    """run_numeric_extraction filters on v2_enriched_at, a column that exists on
    NO table in this database (information_schema returned empty, 2026-09-11), so
    it raises on its first query. It is dead code that reads as complete.

    Pinned so adding it has to be a deliberate act by someone who fixed it first.
    """
    fns = [fn for _, fn in pipeline.STANDARD_ENRICHMENT_PHASES]
    assert "run_numeric_extraction" not in fns


# --- the order, which is load-bearing twice --------------------------------

def test_actionability_runs_first():
    """Every later phase filters on v2_is_actionable = true. If actionability
    ran late, the others would process nothing and report success -- a silent
    no-op that looks exactly like a clean run."""
    first = pipeline.STANDARD_ENRICHMENT_PHASES[0][1]
    assert first == "run_actionability_classification", (
        f"actionability must run first; the list starts with {first}"
    )


def test_layer_tagging_precedes_applicability_and_the_appended_phases():
    """A derived precinct key also sets v2_dcp_layer='precinct', and layer tagging
    would overwrite it if it ran afterwards (#1080). The call site derives
    precincts after this whole sequence, so layer tagging must sit inside it."""
    fns = [fn for _, fn in pipeline.STANDARD_ENRICHMENT_PHASES]
    layer = fns.index("run_layer_tagging")
    for later in ("run_applicability_tagging", "run_site_condition_tagging",
                  "run_type_classification", "run_applicability_provenance"):
        assert layer < fns.index(later), f"run_layer_tagging must precede {later}"


def test_phases_run_in_the_declared_order():
    calls = []

    def make(name):
        def _fn(batch_size=500):
            calls.append(name)
            return {"total_processed": 0}
        return _fn

    fake = tuple((f"p{i}", f"_seq_{i}") for i in range(4))
    for _, fn_name in fake:
        setattr(pipeline, fn_name, make(fn_name))
    try:
        pipeline.run_standard_enrichment(batch_size=1, phases=fake)
    finally:
        for _, fn_name in fake:
            delattr(pipeline, fn_name)
    assert calls == [fn for _, fn in fake]


# --- failure behaviour -----------------------------------------------------

def test_one_phase_raising_does_not_stop_the_rest():
    """The caller has already committed provisions to the live table. 'One tagger
    broke so four others never ran' is how a partial enrichment becomes a council
    that is invisible in the UI."""
    ran = []

    def boom(batch_size=500):
        raise RuntimeError("deliberate")

    def ok(batch_size=500):
        ran.append("ok")
        return {"total_processed": 7}

    pipeline._t_boom, pipeline._t_ok = boom, ok
    try:
        res = pipeline.run_standard_enrichment(
            batch_size=1, phases=(("boom", "_t_boom"), ("fine", "_t_ok")))
    finally:
        del pipeline._t_boom, pipeline._t_ok

    assert ran == ["ok"], "the phase after the failure did not run"
    assert res["boom"]["error"].startswith("RuntimeError"), res["boom"]
    assert res["fine"] == {"total_processed": 7}


def test_a_phase_that_is_not_defined_is_reported_not_skipped():
    res = pipeline.run_standard_enrichment(
        batch_size=1, phases=(("gone", "_t_does_not_exist"),))
    assert "is not defined" in res["gone"]["error"], (
        "a renamed phase must be loud -- skipping it silently recreates the "
        "exact condition this function was written to end"
    )


def test_a_successful_run_records_no_error_key():
    """The confusable negative: if every result carried an 'error' key the
    caller's `broken` list would be non-empty forever and the warning would
    become noise nobody reads."""
    pipeline._t_good = lambda batch_size=500: {"total_processed": 3}
    try:
        res = pipeline.run_standard_enrichment(
            batch_size=1, phases=(("good", "_t_good"),))
    finally:
        del pipeline._t_good
    assert res["good"] == {"total_processed": 3}
    assert "error" not in res["good"]


# --- the call sites --------------------------------------------------------

@pytest.mark.parametrize("path", [
    "scripts/dcp_commit_approved.py",
    "scripts/dcp_extract_changed.py",
])
def test_both_call_sites_use_the_shared_sequence(path):
    """Source-level, because the alternative is running the real pipeline.

    The defect was the list being duplicated, so the assertion is that neither
    file names the individual phases any more -- a second copy is how three
    phases went missing from both.
    """
    src = (ROOT / path).read_text(encoding="utf-8")
    assert "run_standard_enrichment" in src, f"{path} no longer calls the shared sequence"
    for fn_name in ("run_actionability_classification(", "run_layer_tagging(",
                    "run_applicability_tagging("):
        assert fn_name not in src, (
            f"{path} calls {fn_name} directly again -- the phase list is duplicated, "
            f"which is the defect this change removed"
        )


@pytest.mark.parametrize("path", [
    "scripts/dcp_commit_approved.py",
    "scripts/dcp_extract_changed.py",
])
def test_both_call_sites_report_a_partially_failed_enrichment(path):
    """run_standard_enrichment isolates phase failures, so a caller that ignored
    the returned errors would print 'enrichment complete' over a half-tagged
    council -- turning the isolation into a new way to be silent."""
    src = (ROOT / path).read_text(encoding="utf-8")
    assert 'v.get("error")' in src, (
        f"{path} does not inspect the per-phase results, so a failed phase would "
        f"be reported as a clean enrichment"
    )
