"""The probes are checked the same way the code they watch is checked.

WHY THIS FILE EXISTS
--------------------
A probe that reads the wrong number is worse than no probe, because it reports
clean. On 2026-10-08/09, in ONE session, the same three mistakes were made
repeatedly while building four new DQ rows, and every one of them made a defect
look SMALLER than it was:

  1. A count taken from a query carrying `LIMIT 20`. Cumberland's setback rows
     were below the cut, so the conclusion was "Cumberland has no 6 m front
     setback" when it has one, current, on page 8. A false accusation that
     survived until the rows were listed without the LIMIT.

  2. A probe grouped by `lga` when the serving code scopes by `(lga, dev_type)`.
     A rear setback recorded for `residential_flat_building` satisfied the
     comparison for the whole council and hid the `dwelling_house` gap. DQ-139
     read 1. Scoped correctly it reads 15.

  3. A single `%` in a LIKE pattern. `run()` calls `cur.execute(sql, params)`
     with a tuple, so psycopg2 interpolates and a lone `%` is read as a
     placeholder: `IndexError: tuple index out of range`. Three separate
     occurrences in one session, each costing a round trip to diagnose.

Each check below is one of those three, made mechanical. They are static -- no
database -- so they run anywhere pytest runs.

HOW A VIOLATION IS MEANT TO BE RESOLVED
---------------------------------------
By fixing the probe, not by adding to a baseline. `ACCEPTED` exists only for
probes that predate these checks and whose violation has been read and judged
harmless; adding to it requires the reason to say why the number is still right.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE_FILE = REPO / "scripts" / "dq_probe_live.py"


def _load_probes() -> dict:
    """Import the probe module by path, as dq_check.py does."""
    spec = importlib.util.spec_from_file_location("dq_probe_live_under_test", PROBE_FILE)
    assert spec and spec.loader, PROBE_FILE
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PROBES


PROBES = _load_probes()


def _sql_of(entry) -> str:
    """A probe is (headline, sql, params, meaning); run() unpacks it that way."""
    return entry[1]


def _params_of(entry):
    return entry[2]


def _norm(sql: str) -> str:
    return " ".join(sql.split())


# ---------------------------------------------------------------------------
# 1. A count must not come from a truncated query.
# ---------------------------------------------------------------------------

# A LIMIT is legitimate inside a correlated EXISTS or a scalar subquery that
# picks one row to compare against; it is never legitimate on the population
# being counted. Keyed by DQ id with the reason the LIMIT is sound.
LIMIT_ACCEPTED: dict[str, str] = {}


class TestNoTruncatedCount:
    """Origin: a `LIMIT 20` produced the claim 'Cumberland has no 6 m front
    setback'. It has one, current, page 8 — the rows were simply below the cut."""

    @pytest.mark.parametrize("dq_id", sorted(PROBES))
    def test_count_query_has_no_limit(self, dq_id: str) -> None:
        sql = _norm(_sql_of(PROBES[dq_id]))
        if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
            return
        reason = LIMIT_ACCEPTED.get(dq_id)
        assert reason, (
            f"{dq_id}'s SQL contains LIMIT, so its count is taken from a "
            f"truncated population and can only ever understate the defect. "
            f"Remove the LIMIT, or record in LIMIT_ACCEPTED why this one is "
            f"sound.\n  {sql}"
        )


# ---------------------------------------------------------------------------
# 2. A probe must measure the scope the serving code serves on.
# ---------------------------------------------------------------------------

# Read from the serving code, not chosen. Each entry is "the columns the code
# filters this table by when it answers for one property", so a probe that
# counts the table without mentioning them is counting a coarser population
# than the one a user is ever shown.
SERVING_SCOPE: dict[str, tuple[tuple[str, ...], str]] = {
    "dcp_setback_controls": (
        ("lga", "dev_type"),
        "services/constraint_arithmetic.py::_get_dcp_value takes dev_type, and "
        "scripts/conveyancing_db.py::fetch_dcp_setbacks takes (lga, zone). A "
        "count that ignores dev_type lets one development type's control answer "
        "for another — DQ-139 read 1 instead of 15 that way.",
    ),
    "sepp_structured_requirements": (
        ("applies_to",),
        "lib/pattern-book-eligibility/check-numerics.ts filters on applies_to "
        "(and nothing else, which is DQ-137). A probe over this table that does "
        "not mention applies_to is not measuring what a determination selects.",
    ),
}


# Probes that read a scoped table but are NOT measuring whether a control is
# available for a property. A manufactured date, a review flag or an unusable
# zone code is wrong whatever the development type, so requiring dev_type there
# would be noise. Opt-OUT rather than opt-in, deliberately: a new probe is held
# to the serving scope unless someone writes down why it is exempt, which is the
# same shape as collect_ignore's recorded reasons and schema_contract_baseline.
SCOPE_EXEMPT: dict[str, str] = {
    "DQ-32b": "Counts rows naming a zone the zone filter can never act on. A "
              "zone code that resolves to nothing is broken for every "
              "development type, so dev_type does not scope the defect.",
    "DQ-39": "Counts controls flagged by a derivability sweep -- a metadata "
             "property of the row, independent of who it applies to.",
    "DQ-40": "Counts controls still flagged needs_review. The flag is on the "
             "row, not on a (council, development type) pair.",
    "DQ-41": "Counts controls carrying a manufactured 1 January date. A "
             "fabricated effective date is wrong for every development type.",
    "DQ-61": "Per-council question -- which version of the plan is held -- and "
             "it does mention lga. A plan version is not per development type.",
    "DQ-66": "Per-council question: controls served shire-wide while cited to "
             "one town plan. Scoped by council, not by development type.",
    "DQ-73": "Counts dated controls landing on the 1st of a month, another "
             "fabricated-date signature that is dev_type independent.",
}


class TestProbeScopeMatchesServingScope:
    """Origin: DQ-139 grouped by council while the code serves by council AND
    development type, so 14 of 15 cases were invisible."""

    @pytest.mark.parametrize("dq_id", sorted(PROBES))
    def test_scoped_table_is_measured_at_serving_scope(self, dq_id: str) -> None:
        if dq_id in SCOPE_EXEMPT:
            return
        sql = _norm(_sql_of(PROBES[dq_id]))
        lowered = sql.lower()
        for table, (columns, why) in SERVING_SCOPE.items():
            # Only when the table is actually READ. A probe may name it as a
            # string literal -- DQ-138 lists rule tables in an IN (...) -- and
            # that is not a query against it.
            if not re.search(rf"\b(?:from|join)\s+(?:public\.)?{re.escape(table)}\b",
                             lowered):
                continue
            missing = [c for c in columns if not re.search(rf"\b{c}\b", lowered)]
            assert not missing, (
                f"{dq_id} counts {table} without mentioning {', '.join(missing)}, "
                f"so it measures a coarser population than the serving code.\n"
                f"  why these columns: {why}\n  {sql}"
            )


# ---------------------------------------------------------------------------
# 3. The SQL must survive the way run() executes it.
# ---------------------------------------------------------------------------


class TestProbeSqlIsExecutable:
    """Origin: three separate `IndexError: tuple index out of range` crashes in
    one session, all from a single `%` in a LIKE pattern."""

    @pytest.mark.parametrize("dq_id", sorted(PROBES))
    def test_percent_is_doubled_when_params_are_passed(self, dq_id: str) -> None:
        entry = PROBES[dq_id]
        sql, params = _sql_of(entry), _params_of(entry)
        if params is None:
            return  # psycopg2 does not interpolate without params
        # Strip the legitimate placeholders, then any correctly doubled %%.
        stripped = re.sub(r"%\((?:\w+)\)s|%s", "", sql).replace("%%", "")
        assert "%" not in stripped, (
            f"{dq_id} passes params={params!r}, so psycopg2 interpolates its SQL "
            f"and a lone % is read as a placeholder "
            f"(IndexError: tuple index out of range). Double it to %%.\n"
            f"  {_norm(sql)}"
        )

    @pytest.mark.parametrize("dq_id", sorted(PROBES))
    def test_query_returns_a_single_scalar(self, dq_id: str) -> None:
        # run() does `cur.fetchone()[0]`, so a query returning several ROWS
        # silently reports the first and the rest never surface, and one
        # returning several COLUMNS silently drops all but the first.
        #
        # The test is NOT "must say count(" -- several probes legitimately
        # return a scalar CASE expression (DQ-33, DQ-62, DQ-93, DQ-117, DQ-130,
        # DQ-132, DQ-134 all do, and an earlier version of this check failed
        # every one of them). What matters is one row and one column.
        sql = _norm(_sql_of(PROBES[dq_id]))

        # A CTE's own select list sits before the outer one, so splitting on the
        # first FROM reads the wrong columns. DQ-62 and DQ-132 open with WITH and
        # an earlier version of this check failed both for that reason. Finding
        # the outer SELECT past a CTE needs a parser, so the column count is not
        # asserted here -- stated rather than faked. The outer-GROUP-BY check
        # below is depth-aware and still applies.
        if not re.match(r"\s*with\b", sql, re.IGNORECASE):
            outer = re.split(r"\bFROM\b", sql, maxsplit=1, flags=re.IGNORECASE)[0]
            # Strip function arguments until stable: one pass only removes the
            # innermost parens, which leaves the commas inside a nested call
            # like `COUNT(*) FILTER (WHERE ...)` or `coalesce(a, b)` and reads
            # them as a second selected column.
            bare = outer
            while True:
                stripped = re.sub(r"\([^()]*\)", "", bare)
                if stripped == bare:
                    break
                bare = stripped
            assert "," not in bare, (
                f"{dq_id} selects more than one column; run() reads only the "
                f"first, so the others are invisible.\n  {sql}"
            )

        # A GROUP BY at the OUTER level returns one row per group. Inside a
        # subquery it is fine and common -- the outer count(*) aggregates it --
        # so only an unparenthesised, outer-level GROUP BY is a problem.
        depth, outer_group_by = 0, False
        for match in re.finditer(r"\(|\)|\bgroup\s+by\b", sql, re.IGNORECASE):
            token = match.group(0)
            if token == "(":
                depth += 1
            elif token == ")":
                depth -= 1
            elif depth == 0:
                outer_group_by = True
        assert not outer_group_by, (
            f"{dq_id} has a GROUP BY at the outer level, so it returns one row "
            f"per group and run() reports only the first.\n  {sql}"
        )


class TestTheseChecksCanFail:
    """A check never seen failing proves nothing.

    Each case below plants a real violation into the PROBES dict the checks read
    and asserts the SAME test method rejects it. Running the predicates in
    isolation would not prove the wiring -- the point is that a bad probe added
    to the real file is caught, so the plant goes through the real lookup.
    """

    PLANTED = "DQ-PLANTED"

    def _with_planted(self, monkeypatch: pytest.MonkeyPatch, sql: str, params) -> None:
        monkeypatch.setitem(
            PROBES, self.PLANTED,
            ("planted violation", sql, params, "should never pass"),
        )

    def test_a_truncated_count_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The exact shape that produced "Cumberland has no 6 m front setback".
        self._with_planted(
            monkeypatch,
            "SELECT count(*) FROM (SELECT lga, dev_type FROM dcp_setback_controls"
            " GROUP BY lga, dev_type LIMIT 20) s",
            (),
        )
        with pytest.raises(AssertionError, match="LIMIT"):
            TestNoTruncatedCount().test_count_query_has_no_limit(self.PLANTED)

    def test_the_original_dq139_scope_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # DQ-139 as first written: grouped by council, read 1 instead of 15.
        self._with_planted(
            monkeypatch,
            "SELECT count(*) FROM (SELECT lga FROM dcp_setback_controls"
            " WHERE is_current GROUP BY lga) s",
            (),
        )
        with pytest.raises(AssertionError, match="dev_type"):
            TestProbeScopeMatchesServingScope().test_scoped_table_is_measured_at_serving_scope(
                self.PLANTED
            )

    def test_a_single_percent_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Three IndexError crashes in one session came from exactly this.
        self._with_planted(
            monkeypatch,
            "SELECT count(*) FROM information_schema.tables"
            " WHERE table_name LIKE 'dcp\\_setback\\_controls\\_%'",
            (),
        )
        with pytest.raises(AssertionError, match="%%"):
            TestProbeSqlIsExecutable().test_percent_is_doubled_when_params_are_passed(
                self.PLANTED
            )

    def test_a_multi_row_result_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # run() reads fetchone()[0], so this would report one council's count
        # and silently hide every other council.
        self._with_planted(
            monkeypatch,
            "SELECT count(*) FROM dcp_setback_controls WHERE is_current"
            " AND dev_type IS NOT NULL AND lga IS NOT NULL GROUP BY lga",
            (),
        )
        with pytest.raises(AssertionError, match="GROUP BY at the outer level"):
            TestProbeSqlIsExecutable().test_query_returns_a_single_scalar(self.PLANTED)

    def test_a_multi_column_result_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._with_planted(
            monkeypatch,
            "SELECT count(*), max(value_min) FROM dcp_setback_controls"
            " WHERE lga IS NOT NULL AND dev_type IS NOT NULL",
            (),
        )
        with pytest.raises(AssertionError, match="more than one column"):
            TestProbeSqlIsExecutable().test_query_returns_a_single_scalar(self.PLANTED)

    def test_an_exempted_probe_must_carry_a_reason(self) -> None:
        # SCOPE_EXEMPT is the escape hatch, so it must not become a bare list.
        for dq_id, reason in SCOPE_EXEMPT.items():
            assert dq_id in PROBES, f"{dq_id} is exempted but no longer exists"
            assert len(reason.split()) >= 12, (
                f"{dq_id}'s exemption reason is too thin to review: {reason!r}"
            )
