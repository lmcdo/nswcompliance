"""The #506-catcher: a pipeline stage cannot be deleted without this test going red.

PR #506 migrated CI from GitHub Actions to Railway and dropped the extract-to-review
stage. Nothing failed. Detection kept flagging chapters, the queue stayed empty, every
dashboard stayed green, and the pipeline sat half-built for months — because a MISSING
stage and a stage with NOTHING TO DO look identical from the outside.

`docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md` §4 Phase 0 names this test and says of it:
"This is the single check that would have caught #506; build it first."

It was specified on 2026-06-20 in commit 4115dbe6, whose message reads "testing &
verification enforced by gates, not documentation" and ends "Docs-only." — 32 lines of
markdown, no code. Three months later the audit for this file found it still unbuilt,
along with four other Phase 0/1 items. Writing down that something must be enforced is
not enforcing it; that is the whole lesson and this file is the correction.

OFFLINE BY CONSTRUCTION
-----------------------
`run_monitors.py` is parsed with `ast`, never imported: importing it pulls the extraction
stack (boto3/pdfplumber), which is absent in the mocked pre-push environment. A gate that
cannot run at the gate is not a gate.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / ".claude" / "dcp_pipeline_manifest.json"
RUN_MONITORS = ROOT / "scripts" / "run_monitors.py"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.exists(), (
        f"{MANIFEST_PATH} is missing — the pipeline contract itself was deleted, which "
        f"disables every check below")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scheduled() -> dict:
    """{monitor name: [cmd parts]} read from source, without importing the module."""
    tree = ast.parse(RUN_MONITORS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "MONITORS" for t in node.targets):
            return {k: v["cmd"] for k, v in ast.literal_eval(node.value).items()}
    pytest.fail("MONITORS is no longer a literal dict in run_monitors.py — this test "
                "parses it statically and can no longer see the schedule")


class TestEveryRequiredStageIsStillScheduled:
    def test_the_manifest_declares_stages(self, manifest):
        assert manifest.get("stages"), "the manifest lists no stages, so it enforces nothing"

    def test_each_stage_has_a_scheduled_job(self, manifest, scheduled):
        missing = [s["id"] for s in manifest["stages"] if s["id"] not in scheduled]
        assert not missing, (
            "these pipeline stages have NO scheduled job — this is exactly the #506 "
            f"failure: {missing}. "
            + " ".join(f"[{s['id']}] {s['if_deleted']}"
                       for s in manifest["stages"] if s["id"] in missing))

    def test_each_stage_runs_the_script_it_promises(self, manifest, scheduled):
        for stage in manifest["stages"]:
            cmd = scheduled.get(stage["id"])
            if cmd is None:
                continue  # reported by the test above
            assert stage["script"] in cmd, (
                f"{stage['id']} is scheduled but no longer runs {stage['script']} "
                f"(runs {cmd!r}). A stage pointed at the wrong script is a deleted "
                f"stage that still looks present.")

    def test_each_stage_keeps_the_arguments_that_make_it_safe(self, manifest, scheduled):
        """--review is what keeps extraction OFF the live table. Dropping it turns a
        read-only stage into one that writes provisions unreviewed."""
        for stage in manifest["stages"]:
            cmd = scheduled.get(stage["id"])
            if cmd is None:
                continue
            for arg in stage.get("requires_args", []):
                assert arg in cmd, (
                    f"{stage['id']} lost the {arg!r} argument (now {cmd!r}); for "
                    f"--review that silently converts a no-write stage into a writing one")

    def test_every_stage_script_exists_on_disk(self, manifest):
        for stage in manifest["stages"]:
            assert (ROOT / stage["script"]).exists(), (
                f"{stage['id']} points at {stage['script']}, which does not exist — the "
                f"job is scheduled and would fail on every run")

    def test_the_extract_to_review_stage_is_present(self, manifest, scheduled):
        """Named explicitly rather than left to the loop. This is the one #506 removed,
        and a regression here must say so in its own words."""
        assert "dcp-extract" in scheduled, (
            "the extract-to-review stage is gone again — chapters will be flagged as "
            "changed and never re-read, with no error anywhere")
        assert any(s["id"] == "dcp-extract" for s in manifest["stages"]), (
            "dcp-extract was removed from the manifest, which would let it be deleted "
            "from the schedule without this test noticing")


class TestTheUnbuiltBacklogStaysVisibleAndOnlyShrinks:
    """The plan's own meta-enforcement: 'the tests must exist, not just run'.

    A gap is allowed to exist — it is not allowed to be forgotten, and the count is not
    allowed to grow. Raising the ceiling to fit a new gap is how a ratchet stops meaning
    anything, which is the rule DQ-33's floor already carries.
    """

    def test_the_backlog_is_recorded(self, manifest):
        assert "unbuilt" in manifest and "unbuilt_ceiling" in manifest

    def test_the_backlog_has_not_grown(self, manifest):
        n, ceiling = len(manifest["unbuilt"]), manifest["unbuilt_ceiling"]
        assert n <= ceiling, (
            f"{n} unbuilt pipeline items against a ceiling of {ceiling}. Build the item "
            f"and lower the ceiling — do not raise the ceiling.")

    def test_the_ceiling_never_rises(self, manifest):
        assert manifest["unbuilt_ceiling"] <= 5, (
            "the ceiling was raised above its 2026-09-22 value of 5. It may only fall.")

    def test_every_gap_cites_the_plan_and_its_evidence(self, manifest):
        """A gap without a doc reference becomes folklore; one without evidence of
        absence is someone's assumption. Both are how 'not built' survives unchallenged."""
        for item in manifest["unbuilt"]:
            assert item.get("doc"), f"{item['id']} cites no section of the plan"
            assert item.get("verified_absent_on"), (
                f"{item['id']} records no check that it is actually absent — it may "
                f"already exist and be sitting in this list unread")
            assert item.get("what"), f"{item['id']} does not say what to build"

    def test_a_built_item_is_removed_rather_than_ticked(self, manifest):
        """No 'status: done' field. An item leaves this list by being deleted from it and
        the ceiling dropping, so the count is always the real remaining work."""
        for item in manifest["unbuilt"]:
            assert "status" not in item and "done" not in item, (
                f"{item['id']} carries a status flag; a 'done' entry left in the list "
                f"inflates the count and hides the real backlog")


class TestAGuardCannotBeDeletedSilently:
    """A guard deleted is the same failure as a stage deleted, and reads the same.

    #506 removed a stage and nothing noticed because nothing asserted the stage was
    there. The same is true of the guards inside the stages: `ping_healthcheck` opened
    with `if not url: return` for months, so every service without an `HC_PING_URL`
    silently had no dead-man's switch. Measured on the live Railway fleet 2026-09-28,
    SIX services shared the literal placeholder `https://hc-ping.com/placeholder-satellite`
    and four more carried nothing — and all ten looked exactly like watched services.

    Offline by construction, like the rest of this file: the guard's file is parsed
    with `ast`, never imported.
    """

    def test_the_manifest_declares_guards(self, manifest):
        assert manifest.get("guards"), (
            "the manifest lists no guards, so a guard can be removed without this "
            "test noticing — the #506 shape one level down")

    def test_the_floor_never_falls(self, manifest):
        assert manifest["guards_floor"] >= 1, (
            "guards_floor was lowered below its 2026-09-28 value of 1. It may only "
            "rise: lowering it is how a deleted guard is made to look legitimate.")

    def test_there_are_at_least_as_many_guards_as_the_floor(self, manifest):
        n, floor = len(manifest["guards"]), manifest["guards_floor"]
        assert n >= floor, (
            f"{n} guards against a floor of {floor} — a guard was removed. Restore it, "
            f"or say in the manifest why the requirement no longer holds.")

    def test_each_guard_names_its_plan_section(self, manifest):
        for g in manifest["guards"]:
            assert g.get("doc"), f"{g['id']} cites no section of the plan"
            assert g.get("purpose"), f"{g['id']} does not say what it enforces"
            assert g.get("if_deleted"), (
                f"{g['id']} does not say what breaks without it, so nobody reviewing "
                f"its removal can weigh the cost")

    def test_each_guard_still_exists_where_it_says(self, manifest):
        for g in manifest["guards"]:
            path = ROOT / g["file"]
            assert path.exists(), f"{g['id']}: {g['file']} is gone"
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = {n.name for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            assert g["function"] in names, (
                f"{g['id']}: {g['function']} is no longer defined in {g['file']}, so "
                f"the guard the manifest promises is not there")

    def test_each_guard_still_has_its_test(self, manifest):
        """A guard with no test is an assertion about the code, not a gate on it."""
        for g in manifest["guards"]:
            path = ROOT / g["test"]
            assert path.exists(), f"{g['id']}: its test {g['test']} is gone"
            assert path.read_text(encoding="utf-8").count("def test_") >= 1, (
                f"{g['id']}: {g['test']} contains no tests")

    def test_a_guard_states_what_it_does_not_cover(self, manifest):
        """The dead-man's-switch guard makes the client side loud and cannot create the
        external checks. A guard that does not name its residual gets read as complete,
        which is how 'the alarm is wired' became true on paper and false in production."""
        for g in manifest["guards"]:
            assert g.get("residual"), (
                f"{g['id']} records no residual. If it genuinely covers everything, say "
                f"so in that field rather than leaving it out")
