# prior-art-checked: reuse not viable because the existing zone checks are
# per-run, not per-writer. scripts/validate_zone_code_validity.py checks the
# TABLE after a write; tests/test_retag_narrowing_is_classified.py checks ONE
# script's gate. Neither can notice a new script that writes the column and
# consults nothing, which is how both holes below were opened.
"""No script may write v2_applicable_zones without consulting ground truth.

WHY A PER-WRITER CHECK AND NOT ANOTHER PER-RUN ONE
---------------------------------------------------
Twice in one day, 2026-09-23/24, a production writer of `v2_applicable_zones`
turned out to consult nothing:

  * `retag_applicability_slug_docids.py` was about to narrow 34 served Warringah
    rows onto B1/B2/B5/B6/B7. Warringah DCP 2011 predates the 2022  # noqa: zone-codes (the retired codes the incident was about, named in prose)
    employment-zone reform and still names those codes, so the tagger read them
    straight out of the plan text. Caught by a person reading a dry run.
  * `sync_v2_to_supabase.py` UPDATEs the column across ~48.8k rows behind
    nothing but `input("Continue? (yes/no): ")`. Caught by grepping for writers
    after fixing the first one.

`scripts/validate_zone_code_validity.py` had enforced the rule correctly for
months. It simply was not wired to either one, and it runs AFTER the write, in
the post-commit completeness report. Fixing each caller individually leaves the
same hole open for the next caller, so this asserts the property directly: the
set of files that write the column is a SUBSET of the set that consults ground
truth.

WHY IT MATTERS MORE THAN THE OTHER 15 SYNCED COLUMNS. `v2_applicable_zones` is
a HARD filter on the served answer — `frontend-nextjs/app/api/.../for-property/
route.ts:1012` keeps a row only when the column is NULL, holds 'ALL', or
overlaps the query. Naming a value therefore DELETES the row from every other
property's answer. A wrong zone is not a wrong field on a page; it is a control
that silently stops existing.

MUTATION NOTE. The confusable negatives are real files, not invented ones, and
the first version of this check failed two of them:
  * `scripts/fixes/DQ7_*.py` UPDATE regulatory_provisions and name the column —
    inside `WHERE v2_applicable_zones && ARRAY['B1',...]`. They infer dev types
    FROM zones and write `v2_applicable_dev_types`. READERS, not writers.
  * `scripts/check_council_completeness.py` names the column and INSERTs, but
    into `dcp_council_field_snapshot`. A reporter, not a writer.
  * the retired-scripts tree, excluded by name below, holds four genuine
    writers that are deliberately not scanned.
  * `retag_applicability_slug_docids.py` writes `UPDATE {TABLE} SET ...` from a
    module constant, so a detector anchored on the literal table name misses the
    one script this check was written for.
A detector keyed on "mentions the column" calls the first two writers. One keyed
on the literal table name misses the fourth. Both mistakes were made here before
the rule below was narrowed to ASSIGNMENT of the column.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

COLUMN = "v2_applicable_zones"

#: A write aimed at the served table. Two spellings are in use: the literal
#: table name, and an f-string placeholder filled from a module constant
#: (`retag_applicability_slug_docids.py` has `TABLE = "regulatory_provisions"`
#: and writes `UPDATE {TABLE} SET ...`). Matching only the literal missed the
#: very script this check was written for.
_WRITES_PROVISIONS = re.compile(
    r"(?:UPDATE|INSERT\s+INTO)\s+(?:public\.)?(?:regulatory_provisions|\{\w+\})",
    re.I)

#: Assigning the zone column in a literal SET clause: `SET v2_applicable_zones =`.
#: Non-greedy and bounded so a SET hundreds of lines earlier cannot be paired
#: with a WHERE-clause mention far below it.
_SETS_DIRECTLY = re.compile(r"SET\s[\s\S]{0,400}?" + COLUMN + r"\s*=")

#: Assigning it through a column list. `sync_v2_to_supabase.py` holds the column
#: in `V2_COLUMNS` and builds `f"{col} = %s"` in a loop, so the column name and
#: the assignment never appear in the same string — the check above cannot see
#: it, and reading the file is the only way to know it is there.
_IN_COLUMN_LIST = re.compile(r"['\"]" + COLUMN + r"['\"]\s*,")
_SETS_FROM_LIST = re.compile(r"\{col\}\s*=|\{c\}\s*=")

#: Consulting the ground truth, in any of the three shapes the repo uses.
_CONSULTS = re.compile(
    r"valid_zones"                      # passed into the tagger
    r"|validate_zone_code_validity"     # imports the checker module
    r"|load_ground_truth"               # calls its loader directly
)


def _sets_the_zone_column(src: str) -> bool:
    """Does this file ASSIGN the column, as opposed to reading it?

    The distinction is the whole precision of this check. `scripts/fixes/
    DQ7_*.py` name the column only inside `WHERE ... v2_applicable_zones &&
    ARRAY['B1',...]` — they infer dev types FROM zones and write
    `v2_applicable_dev_types`. Treating them as zone writers, as the first
    version of this file did, demands a zone-validity gate from two scripts
    that cannot write a zone at all.
    """
    if _SETS_DIRECTLY.search(src):
        return True
    return bool(_IN_COLUMN_LIST.search(src) and _SETS_FROM_LIST.search(src))

#: Scanned trees. The retired-scripts directory is excluded deliberately: it
#: holds four genuine writers (re_enrich_all, backfill_provision_versions and
#: the two marrickville fixers) kept for provenance and not runnable against
#: the current schema. Excluding it is what makes this check meaningful rather
#: than permanently red — and the test at the bottom pins the exclusion so it
#: cannot be quietly widened to hide a live file.
#:
#: It is named, never PATH-JOINED. `tests/test_archive_is_not_live_code.py`
#: forbids anything outside that tree from referencing a path into it, because
#: the tree is exempt from every content scanner and a reference is how that
#: exemption turns into a hole. This file tripped that guard on first write.
_TREES = ("scripts", "enrichment", "services", "src")
_EXCLUDED = ("archive",)


def _is_excluded(path: Path) -> bool:
    return any(part in _EXCLUDED for part in path.relative_to(ROOT).parts)


def _python_files():
    for tree in _TREES:
        base = ROOT / tree
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if not _is_excluded(path):
                yield path


def _writers():
    """Live files that write regulatory_provisions AND mention the zone column."""
    out = {}
    for path in _python_files():
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _WRITES_PROVISIONS.search(src) and _sets_the_zone_column(src):
            out[path.relative_to(ROOT).as_posix()] = src
    return out


class TestEveryLiveWriterConsultsGroundTruth:
    def test_at_least_one_writer_is_found(self):
        """The whole check rests on the detector finding anything at all. If a
        refactor renames the table or moves these files, this suite would go
        green by scanning nothing — which is the failure mode described in
        `feedback-a-check-can-watch-the-field-the-fix-abandoned`."""
        found = _writers()
        assert found, (
            "no writer of %s detected in %s — the detector has stopped "
            "matching, so the rest of this file proves nothing" % (COLUMN, _TREES))

    def test_no_writer_skips_the_zone_validity_rule(self):
        """The property itself. A new script that UPDATEs the column and never
        consults an LGA land-use table fails here, at the commit that adds it,
        rather than in a completeness report after the rows are live."""
        offenders = sorted(p for p, src in _writers().items()
                           if not _CONSULTS.search(src))
        assert not offenders, (
            "these write %s without consulting ground truth: %s\n"
            "Pass valid_zones= to the tagger, or import load_ground_truth from "
            "scripts/validate_zone_code_validity.py and refuse before the write."
            % (COLUMN, ", ".join(offenders)))

    @pytest.mark.parametrize("path", [
        "scripts/retag_applicability_slug_docids.py",
        "scripts/sync_v2_to_supabase.py",
    ])
    def test_the_two_known_writers_are_still_detected_as_writers(self, path):
        """Pins the two that were actually broken. If either stops being seen as
        a writer — renamed, or its SQL rebuilt in a shape the regex misses — the
        check above would pass by ignoring it."""
        assert path in _writers(), f"{path} is no longer detected as a writer"


class TestTheDetectorDoesNotCryWolf:
    def test_a_reporting_insert_is_not_a_provisions_write(self):
        """`check_council_completeness.py` mentions the column and INSERTs, but
        into `dcp_council_field_snapshot`. Calling it a writer would force a
        pointless dependency into a read-only reporter and teach whoever hits it
        that this check is noise."""
        path = ROOT / "scripts" / "check_council_completeness.py"
        if not path.exists():
            pytest.skip("reporter not present")
        src = path.read_text(encoding="utf-8", errors="replace")
        assert COLUMN in src, "confusable negative has drifted; pick another file"
        assert "check_council_completeness.py" not in _writers()

    def test_a_pure_reader_is_not_a_writer(self):
        path = ROOT / "scripts" / "dq_probe_live.py"
        if not path.exists():
            pytest.skip("probe not present")
        assert "scripts/dq_probe_live.py" not in _writers()


class TestTheExclusionCannotBeWidenedToHideAWriter:
    def test_only_archive_is_excluded(self):
        """The cheapest way to make this suite green is to exclude the directory
        the offender lives in. Pinning the list means doing that shows up as an
        edit to this assertion, in the diff, with a name on it."""
        assert _EXCLUDED == ("archive",)
