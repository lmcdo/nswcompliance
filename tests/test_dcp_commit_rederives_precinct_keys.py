"""Committing provisions nulls their precinct keys. Nothing put them back.

REAL FINDING, measured 2026-09-10 against production. Four councils were serving
provisions with no precinct key at all:

    ashfield      2,041 served,   118 keyed   (should be ~759)
    marrickville  2,403 served,    37 keyed   (should be ~922)
    ku_ring_gai     337 served,     0 keyed   (should be 32)

The precincts had not changed. The keys had been wiped. `dcp_commit_approved`
inserts a reviewed provision with `v2_precinct_id` UNSET -- exactly like
`v2_is_actionable`, `v2_topic` and `v2_applicable_dev_types`, which is why that
module already ends with an enrichment block for that class of field.
`v2_precinct_id` was simply left off its list, so the only thing that ever put a
precinct key back was a human remembering to run derive_precinct_keys by hand.

derive_precinct_keys' own docstring names the cause:

    "precinct keys (v2_precinct_id) were applied to rows BY HAND, so every
     re-extraction nulled them and the manual work recurred."

The fix built in July made the keys DERIVABLE. It did not make anything derive
them. This file pins the wiring that does.

WHAT EACH TEST WOULD CATCH (revert the block and watch these go red):
  - the call is made at all
  - it is SCOPED PER COUNCIL, not bulk -- run() refuses validate:False rules on a
    bulk apply, so a bulk call silently leaves Ashfield's 641 rows unkeyed while
    reporting success. This is the subtle one and the reason for the scoping.
  - it APPLIES rather than dry-runs
  - it runs AFTER layer tagging, which would otherwise overwrite v2_dcp_layer
  - a dry run writes nothing
  - a council whose commit FAILED is not keyed
  - a derivation error does not fail provisions that are already committed
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://x")
os.environ.setdefault("R2_BUCKET_NAME", "x")
os.environ.setdefault("R2_ACCESS_KEY_ID", "x")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "x")
os.environ.setdefault("R2_ACCOUNT_ID", "x")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest  # noqa: E402

import dcp_commit_approved as dca  # noqa: E402


class _Cur:
    """Enough cursor for main(): the dry-run count query and the two cleanup writes."""

    def __init__(self):
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return (3,)

    def fetchall(self):
        # The section-loss guard reads the chapter's live headers before and after
        # the swap. An empty chapter has nothing to lose, so it is allowed through
        # and these tests keep measuring what they were written to measure.
        return []

    def close(self):
        pass


class _Conn:
    def __init__(self):
        self.autocommit = False
        self.commits = 0
        self.rollbacks = 0
        self._cur = _Cur()

    def cursor(self):
        return self._cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


def _wire(monkeypatch, councils, *, fail_on=(), derive_raises=False):
    """Drive main() over `councils`, recording the order of enrichment + derivation.

    Returns the shared `events` list: enrichment phases append their own name, the
    precinct derivation appends ("derive", council, apply, validate). Ordering
    between the two is the point of one of the tests, so they share one list.
    """
    events = []

    monkeypatch.setattr(dca.psycopg2, "connect", lambda *a, **k: _Conn())
    monkeypatch.setattr(
        dca, "find_committable_chapters",
        lambda cur: [{"council": c, "chapter_key": f"chapter-{c}",
                      "approved_hash": "h", "hash_variants": 1} for c in councils],
    )
    monkeypatch.setattr(
        dca, "fetch_registry_chapter",
        lambda cur, council, chapter_key: {"content_hash": "h"},
    )

    def _commit(cur, council, chapter_key, allow_unqueued=False):
        if council in fail_on:
            raise RuntimeError(f"commit blew up for {council}")
        return (2, 5)

    monkeypatch.setattr(dca, "commit_reviewed_from_queue", _commit)

    # The enrichment sequence main() imports from enrichment.pipeline. It used to
    # import the three phases individually; they now live in one ordered list
    # inside the pipeline module, shared with dcp_extract_changed.py, because the
    # duplicated copy is how three further phases came to be called by neither
    # file. The fake records the same events so the ORDER assertions below --
    # layer tagging before precinct derivation (#1080) -- still mean what they did.
    fake_pipeline = type(sys)("enrichment.pipeline")

    def _standard(**kw):
        events.extend(["actionability", "layer", "applicability",
                       "site_condition", "provision_type", "provenance"])
        return {"actionability": {}, "layer + topic": {}, "applicability": {},
                "site condition": {}, "provision type": {},
                "applicability provenance": {}}

    fake_pipeline.run_standard_enrichment = _standard
    # The caller also imports the shared "what counts as failed" helper, because
    # a phase can fail by returning an error COUNT without raising.
    fake_pipeline.phase_failures = lambda results: [
        k for k, v in results.items()
        if isinstance(v, dict) and (v.get("error") or v.get("errors"))
    ]
    monkeypatch.setitem(sys.modules, "enrichment.pipeline", fake_pipeline)

    def _derive(council, apply, validate):
        events.append(("derive", council, apply, validate))
        if derive_raises:
            raise RuntimeError("fingerprint mismatch")
        return 0

    fake_dpk = type(sys)("derive_precinct_keys")
    fake_dpk.run = _derive
    monkeypatch.setitem(sys.modules, "derive_precinct_keys", fake_dpk)
    monkeypatch.setitem(sys.modules, "scripts.derive_precinct_keys", fake_dpk)
    return events


def _derives(events):
    return [e for e in events if isinstance(e, tuple) and e[0] == "derive"]


# ---------------------------------------------------------------------------
# 1. It happens at all, once per council
# ---------------------------------------------------------------------------

def test_every_committed_council_gets_its_precinct_keys_rederived(monkeypatch):
    events = _wire(monkeypatch, ["ashfield", "marrickville"])
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    assert [e[1] for e in _derives(events)] == ["ashfield", "marrickville"], (
        "each council that had provisions inserted must have its precinct keys "
        "re-derived; without this the keys stay NULL until a human notices"
    )


def test_a_council_is_rederived_once_even_with_several_chapters(monkeypatch):
    """Two chapters of one council is still one council-scoped derivation.

    run() keys the whole council in one pass, so calling it per chapter would be
    N identical passes -- wasteful, and it would write the backup CSV N times.
    """
    events = _wire(monkeypatch, ["ashfield", "ashfield"])
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    assert [e[1] for e in _derives(events)] == ["ashfield"]


# ---------------------------------------------------------------------------
# 2. THE SUBTLE ONE: scoped, not bulk
# ---------------------------------------------------------------------------

def test_the_derivation_is_scoped_to_a_named_council_never_bulk(monkeypatch):
    """A bulk call would report success and silently skip the biggest rule.

    derive_precinct_keys.run() carries a deliberate footgun guard:

        if apply and not council and not rule["validate"]:
            SKIPPED on bulk --apply (validate:False; pass --council to apply)

    Ashfield's chapter-D rule is validate:False and covers 641 rows. A bulk apply
    prints a tidy total and leaves every one of them unkeyed. Committing a council
    IS the deliberate per-council act that guard is asking for, so the council name
    must be passed through -- never None.
    """
    events = _wire(monkeypatch, ["ashfield"])
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    called = _derives(events)
    assert called, "no derivation happened at all"
    for _, council, _, _ in called:
        assert council is not None and council != "", (
            "a bulk (council=None) derivation skips validate:False rules, so "
            "Ashfield's 641 chapter-D rows would stay unkeyed while the run "
            "reported success"
        )


def test_it_applies_rather_than_dry_running(monkeypatch):
    """apply=False derives the same keys, prints them, and writes nothing."""
    events = _wire(monkeypatch, ["ashfield"])
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    for _, _, apply, validate in _derives(events):
        assert apply is True, "a dry-run derivation leaves the keys NULL"
        assert validate is False, (
            "validate=True turns the pass into an assertion that derived keys "
            "reproduce EXISTING keys -- freshly committed rows have none, so it "
            "would fail on exactly the rows this exists to key"
        )


# ---------------------------------------------------------------------------
# 3. Ordering against the enrichment phases
# ---------------------------------------------------------------------------

def test_precinct_keys_are_derived_after_layer_tagging(monkeypatch):
    """A derived key also sets v2_dcp_layer='precinct'.

    run_layer_tagging writes the same column. If it ran last it would overwrite
    the precinct layer and the row would stop matching the for-property route's
    precinct filter -- the key present, the layer wrong, nothing served.
    """
    events = _wire(monkeypatch, ["ashfield"])
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    assert "layer" in events, "layer tagging did not run"
    first_derive = next(i for i, e in enumerate(events)
                        if isinstance(e, tuple) and e[0] == "derive")
    assert events.index("layer") < first_derive, (
        "layer tagging must run BEFORE the precinct derivation, or it overwrites "
        "v2_dcp_layer='precinct'"
    )


# ---------------------------------------------------------------------------
# 4. Confusable negatives -- when it must NOT run
# ---------------------------------------------------------------------------

def test_a_dry_run_derives_nothing(monkeypatch):
    """Without --commit the worker reports only. It must not write keys either."""
    events = _wire(monkeypatch, ["ashfield"])
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py"])

    dca.main()

    assert _derives(events) == [], "a dry run wrote precinct keys to production"


def test_a_council_whose_commit_failed_is_not_rederived(monkeypatch):
    """A rolled-back commit inserted no rows, so there is nothing to key.

    Keying it anyway would touch rows the failed run never created -- and would
    make the warning log claim work that did not happen.
    """
    events = _wire(monkeypatch, ["ashfield", "marrickville"], fail_on=("ashfield",))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    assert [e[1] for e in _derives(events)] == ["marrickville"]


def test_nothing_committed_means_no_derivation(monkeypatch):
    events = _wire(monkeypatch, [])
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    assert _derives(events) == []


# ---------------------------------------------------------------------------
# 5. It cannot take the commit down with it
# ---------------------------------------------------------------------------

def test_a_derivation_error_does_not_fail_already_committed_provisions(
        monkeypatch, capsys):
    """The provisions are live before this runs. They can be re-keyed later.

    derive_precinct_keys FAILS CLOSED on a pagination fingerprint mismatch, which
    is a normal outcome after a re-paginated amendment -- so this error is
    expected, not exotic, and must not roll anything back.
    """
    events = _wire(monkeypatch, ["ashfield", "marrickville"], derive_raises=True)
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    rc = dca.main()

    out = capsys.readouterr().out
    assert rc != 1, "a keying failure must not turn a successful commit into a failure"
    assert len(_derives(events)) == 2, (
        "one council's keying error must not stop the next council being keyed"
    )
    assert "derive_precinct_keys.py --council" in out, (
        "the warning must print the exact command that fixes it, or the gap is "
        "silent and recurs -- which is how this bug lasted two months"
    )


# ---------------------------------------------------------------------------
# 6. The import itself can fail, and not with an ImportError
# ---------------------------------------------------------------------------

def test_a_missing_data_file_does_not_crash_an_already_committed_run(
        monkeypatch, capsys):
    """derive_precinct_keys reads a json at MODULE level. That is the risk.

        with open(REPO / "data" / "cos_precinct_page_ranges.json") as _f:

    If that file is not in the image, importing the module raises
    FileNotFoundError -- which `except ImportError` does NOT catch. The provisions
    are committed and live by the time this block runs, so an uncaught raise here
    turns a successful commit into a crashed job and a red monitor alert, for a
    keying step that is re-runnable by hand.

    This pins the broad catch. Revert it to `except ImportError` and this goes red.
    """
    events = _wire(monkeypatch, ["ashfield"])

    broken = type(sys)("derive_precinct_keys")

    def _boom(name):
        # Deliberately GENERIC. An earlier version raised a message containing the
        # filename, which made the "warning names the file" assertion below pass on
        # the exception text rather than on the warning -- it survived mutation of
        # the warning string. The real FileNotFoundError from a container is
        # "[Errno 2] No such file or directory: '/app/data/...'", but the point is
        # that the assertion must be satisfied by OUR message, not the exception's.
        raise FileNotFoundError(2, "No such file or directory")
    monkeypatch.setattr(broken, "__getattr__", _boom, raising=False)
    monkeypatch.setitem(sys.modules, "derive_precinct_keys", broken)
    monkeypatch.setitem(sys.modules, "scripts.derive_precinct_keys", broken)
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    rc = dca.main()

    out = capsys.readouterr().out
    assert rc != 1, "a packaging slip must not fail provisions that are already live"
    assert "could not load the precinct derivation" in out
    assert "cos_precinct_page_ranges.json" in out, (
        "the warning must name the missing file, or the next person sees only "
        "'derivation failed' and has to rediscover the module-level read"
    )


def test_the_image_ships_the_json_the_derivation_reads_at_import():
    """Packaging test: the .py alone is not enough.

    tests/test_dockerfile_monitors_imports.py checks sibling .py imports. It cannot
    see a data file read at module scope, so that class of break would ship green.
    """
    import pathlib
    dockerfile = (pathlib.Path(__file__).resolve().parent.parent
                  / "Dockerfile.monitors").read_text(encoding="utf-8")
    assert "scripts/derive_precinct_keys.py" in dockerfile, (
        "dcp_commit_approved imports it; without the COPY the dcp-commit worker "
        "ModuleNotFounds every night"
    )
    assert "data/cos_precinct_page_ranges.json" in dockerfile, (
        "derive_precinct_keys open()s this at module level, so the import fails "
        "without it -- the .py COPY alone is a half fix"
    )


# ---------------------------------------------------------------------------
# 7. Failure by RETURN VALUE, not just by raising
# ---------------------------------------------------------------------------

def test_a_nonzero_return_is_reported_not_swallowed(monkeypatch, capsys):
    """run() signals failure two ways. An except block only catches one.

    Raised by cross-review on the pre-push run: a non-zero return slides past the
    exception handler, so the job prints its ordinary success summary over a council
    whose keys were never written.

    Checked rather than taken on trust: today run() returns 1 on exactly one path
    (`if validate and validation_failures`) which this call cannot reach, because it
    passes validate=False. So this pins a forward-looking guard -- it costs nothing
    and stops the NEXT non-zero path being silent. It is deliberately not sold as
    the fix for the fingerprint case, which fails closed and returns 0.
    """
    events = _wire(monkeypatch, ["ashfield", "marrickville"])

    failing = type(sys)("derive_precinct_keys")
    def _rc1(council, apply, validate):
        events.append(("derive", council, apply, validate))
        return 1
    failing.run = _rc1
    monkeypatch.setitem(sys.modules, "derive_precinct_keys", failing)
    monkeypatch.setitem(sys.modules, "scripts.derive_precinct_keys", failing)
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    out = capsys.readouterr().out
    assert "exit 1" in out, (
        "a non-zero return must be reported; without this the run looks clean and "
        "the council stays unkeyed"
    )
    assert out.count("--council") >= 2, (
        "each failing council needs its own re-run command, not one generic line"
    )
    assert len(_derives(events)) == 2, (
        "a non-zero return for one council must not stop the next being attempted"
    )


def test_a_zero_return_prints_no_warning(monkeypatch, capsys):
    """The confusable negative. If the success path also warned, the warning would
    be noise on every run and stop being read -- which is how the original bug
    survived two months of nightly logs."""
    _wire(monkeypatch, ["ashfield"])
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    out = capsys.readouterr().out
    assert "precinct re-derivation reported failure" not in out
    assert "[warn] precinct re-derivation failed" not in out
