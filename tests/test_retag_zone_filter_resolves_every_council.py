"""The retag's zone-validity filter must actually resolve a council's zones.

prior-art-checked: tests/test_applicability_slug_docids.py covers the slug ->
config-key matching, tests/test_retag_narrowing_is_classified.py covers the
narrowed/widened classification, and
tests/test_retag_applicability_slug_docids_real_db.py exercises the write path.
None of the three asserts that `_valid_zones_for` RESOLVES -- so the filter
could return None for a whole council and every one of them stayed green.
Swept 2026-10-04 on origin/main 1ac3b74c.

WHAT WENT WRONG, AND WHY NOTHING CAUGHT IT
------------------------------------------
`_valid_zones_for` built its own name match: `council.replace("_", " ")`
substring-tested against `lower(lga)` from lep_zone_coverage. The slug
`ku_ring_gai` becomes "ku ring gai"; the table says "Ku-ring-gai". Neither
string contains the other, so the function returned None -- and None means DO
NOT FILTER.

Measured against the live table on 2026-10-04: FIVE of eighteen served councils
got no zone-validity filtering at all (ashfield, canterbury_bankstown,
ku_ring_gai, leichhardt, marrickville). The filter the script's own docstring
calls "the fix" was not running for any of them.

A no-op is the worst shape of bug this repo keeps meeting: the code is present,
the comment describes the right behaviour, and the absence is invisible because
"no zones to drop" and "could not resolve the council" produce the identical
result. So these tests assert on RESOLUTION, not on the filtered output -- an
assertion about output would have passed throughout.

It was caught by the refusal guard at the end of the same script, which stopped
an authorised production write because two planned rows carried codes their LGA
does not have. The guard worked; the thing it guards did not.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "retag_applicability_slug_docids.py"
SOURCE = SCRIPT.read_text(encoding="utf-8")


class TestItUsesTheSharedResolverAndNotItsOwn:
    """The rule has to be ONE rule. Two copies drift, and the drift is silent.

    These are source-level assertions on purpose: the function is a closure over
    a live cursor inside main(), so it cannot be imported and called without a
    database, and the property worth protecting is structural -- that this file
    does not grow a second ground-truth resolver again.
    """

    def test_the_shared_resolver_is_imported(self):
        assert "from validate_zone_code_validity import" in SOURCE
        assert "load_ground_truth" in SOURCE
        assert "load_slug_resolution" in SOURCE, (
            "load_slug_resolution is what handles both the hyphen/space mismatch "
            "and the merged-council rollup to a parent LGA. Without it a council "
            "whose display name is punctuated silently gets no filtering.")

    def test_valid_zones_for_reads_the_shared_mapping(self):
        """It must look the council up in `slug_key`, not re-derive a name."""
        body = re.search(r"def _valid_zones_for\(.*?\n(?=\s{4}\w|\s{4}plan,)",
                         SOURCE, re.S)
        assert body, "_valid_zones_for not found — did it move or get renamed?"
        text = body.group(0)
        assert "slug_key" in text and "truth" in text, (
            "_valid_zones_for no longer consults the shared resolver")

    def test_it_does_NOT_rebuild_a_name_match(self):
        """The exact shape of the bug, refused by name.

        `replace("_", " ")` against an lga string is how "ku ring gai" failed to
        find "Ku-ring-gai". Any return to a hand-rolled name comparison here
        reintroduces a silent no-op for every punctuated council name.

        Checked against the function's CODE with its docstring stripped: that
        docstring quotes the bad pattern in order to record it, and matching
        prose would make this test fire on its own explanation. Caught on the
        first run of this file.
        """
        body = re.search(r"def _valid_zones_for\(.*?\n(?=\s{4}\w|\s{4}plan,)",
                         SOURCE, re.S)
        code = re.sub(r'""".*?"""', "", body.group(0), flags=re.S)
        assert 'replace("_", " ")' not in code and "replace('_', ' ')" not in code, (
            "_valid_zones_for is matching LGA names by hand again. Slugs are "
            "underscored and lep_zone_coverage.lga is not; use slug_key.")
        assert "by_lga" not in SOURCE, (
            "the second ground-truth lookup (by_lga) is back. The file's own "
            "comment says ground truth is reused rather than reimplemented "
            "because two copies would drift — they did.")

    def test_none_still_means_do_not_filter(self):
        """Not every council has ground truth, and inventing one is worse.

        city_of_sydney does not resolve, and dropping every zone for it would
        look exactly like a successful narrowing. The docstring has to keep
        saying so, because the next person to see a None will be tempted to
        treat it as an empty set.
        """
        body = re.search(r"def _valid_zones_for\(.*?\n(?=\s{4}\w|\s{4}plan,)",
                         SOURCE, re.S)
        assert "do not filter" in body.group(0).lower()


class TestTheRefusalGuardIsStillThere:
    """What actually stopped the bad write. It must not be softened into a filter."""

    def test_an_invalid_planned_code_refuses_rather_than_dropping(self):
        assert "ZONE CODES NOT IN THEIR LGA" in SOURCE
        assert re.search(r"if invalid:\s*\n\s*print\(f?\"ERROR", SOURCE), (
            "the invalid-code path no longer errors. It must REFUSE, not filter: "
            "reaching it means the at-source filter failed, and quietly fixing "
            "the symptom would hide that.")

    def test_it_refuses_before_creating_the_backup_table(self):
        """So a refused run leaves no trace to clean up."""
        err = SOURCE.index("ERROR: ")
        backup = SOURCE.index("CREATE TABLE") if "CREATE TABLE" in SOURCE else len(SOURCE)
        assert err < backup, (
            "the refusal now happens after the backup table is created, so a "
            "refused run leaves an orphan table behind")
