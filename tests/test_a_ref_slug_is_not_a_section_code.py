"""Our own identifier was being served as the council's section number.

`build_provision_text` writes the ref slug into the provision's first line —
`# 4_1c_7 Visual and Acoustic Privacy`. `dcp_commit_approved._section_header_from_text`
reads `section_header` off that line. `repaired_header` then checked `HAS_CODE.match(head)`,
saw something code-shaped and returned None meaning "already has a code, leave it alone".

But a slug IS the code with its dots replaced by underscores, so HAS_CODE matches it. The
slug won, and `4_1c_7` became the citation shown to a planner. The council's document says
**4.1C.7**. `4_1c_7` never appears in it.

**Measured 2026-09-21 on live `regulatory_provisions`:** 122 current rows, all
`ku_ring_gai`, carry a header opening with an underscore slug — `14a_9 Precinct S3`,
`14b_11 Precinct T4`, `4_1c_7`. `section_code()` recovers a correct dotted code for all
122, so the information was never lost, only overridden.

It also spreads. The commit worker recomputes `section_header` on every commit, so each
re-read of an affected chapter converts twelve more citations. That is what
`dcp_supersede_guard` reported as "12 sections before, 12 after -- 12 lost (100%), 12 new"
when the Ku-ring-gai secondary-dwellings chapter was committed, and why that commit was
refused and rolled back. The guard was right and the renumbering was ours.

The function's own docstring predicted this shape: without the fallback it "recomputes
section_header on EVERY commit from the heading line alone, so
scripts/dcp_restore_section_codes.py would be undone the next time each chapter was
committed". The fallback existed; the short-circuit above it meant it never ran.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dcp_section_code import HAS_CODE, repaired_header, section_code  # noqa: E402

DOC = "Ku-ring-gai_DCP_2024__section_a_part_4_1_secondary_dwellings"
REF = f"{DOC}__4_1c_7"
TITLE = "Visual and Acoustic Privacy"


class TestTheSlugIsReplacedByTheDocumentsCode:
    def test_a_header_opening_with_our_slug_is_corrected(self):
        assert repaired_header(f"4_1c_7 {TITLE}", REF, DOC) == f"4.1c.7 {TITLE}"

    def test_the_title_survives_the_swap(self):
        """Only the leading token changes. Losing the title would trade one defect
        for a worse one -- an addressable row nobody can read."""
        out = repaired_header(f"4_1c_7 {TITLE}", REF, DOC)
        assert out.endswith(TITLE)

    @pytest.mark.parametrize("slug,dotted", [
        ("4_1a_1", "4.1a.1"),
        ("14a_9", "14a.9"),
        ("14b_11", "14b.11"),
        ("14e_11", "14e.11"),
    ])
    def test_the_real_live_shapes(self, slug, dotted):
        """Taken from the 122 rows this was measured on, not invented."""
        ref = f"Ku-ring-gai_DCP_2024__section_b_part_14__{slug}"
        doc = "Ku-ring-gai_DCP_2024__section_b_part_14"
        got = repaired_header(f"{slug} Some Title", ref, doc)
        assert got == f"{dotted} Some Title", f"{slug} was not corrected to {dotted}"

    def test_a_header_that_is_only_the_slug_still_gets_a_title_free_code(self):
        assert repaired_header("4_1c_7", REF, DOC) == "4.1c.7"


class TestItDoesNotRewriteTheDocumentsOwnCode:
    """The rule this function was built on: a stored code came from the document and a
    recovered one is an inference, so an existing code is never overwritten. The swap
    above is not an exception to that -- a slug is ours, not the document's -- and the
    rule itself must still hold."""

    def test_a_dotted_code_is_left_alone(self):
        assert repaired_header(f"4.1c.7 {TITLE}", REF, DOC) is None

    def test_a_DIFFERENT_code_is_left_alone_even_if_it_has_underscores(self):
        """The swap fires only when the token is character-for-character the underscore
        spelling of THIS row's recovered code. Anything else is the document talking."""
        assert repaired_header(f"9_9_9 {TITLE}", REF, DOC) is None

    def test_a_code_shaped_token_that_is_not_this_rows_slug_is_left_alone(self):
        assert repaired_header(f"4_1c_8 {TITLE}", REF, DOC) is None

    def test_no_recoverable_code_means_no_change(self):
        """It must never invent a regulatory reference -- .claude/rules/regulatory-data.md."""
        assert repaired_header("Some Heading", None, None) is None
        assert repaired_header("4_1c_7 x", None, None) is None


class TestTheUnchangedBehaviourStays:
    def test_a_codeless_header_still_gains_its_code(self):
        """The original purpose of the function: 3,501 live rows had no code at all."""
        assert repaired_header("Visual and Acoustic Privacy", REF, DOC) == f"4.1c.7 {TITLE}"

    def test_an_empty_header_returns_the_bare_code(self):
        assert repaired_header(None, REF, DOC) == "4.1c.7"
        assert repaired_header("", REF, DOC) == "4.1c.7"


class TestThePremise:
    def test_has_code_really_does_match_a_slug(self):
        """If this ever stops being true the bug is gone and this file is testing
        nothing -- so it is asserted rather than assumed."""
        assert HAS_CODE.match(f"4_1c_7 {TITLE}"), (
            "HAS_CODE no longer matches a slug; re-read why this fix exists")

    def test_the_dotted_code_was_always_recoverable(self):
        assert section_code(REF, DOC) == "4.1c.7"


class TestTheCommitPathUsesIt:
    def test_the_commit_worker_writes_the_corrected_header(self):
        """End of the chain: the guard refused the Ku-ring-gai commit because this
        produced twelve new codes. It must now produce the twelve live ones."""
        src = (ROOT / "scripts" / "dcp_commit_approved.py").read_text(encoding="utf-8")
        assert "repaired_header(head, ref_number, document_id) or head" in src, (
            "the commit path no longer runs headers through the repair")


class TestACodeWithNoDotsIsNotASlug:
    """`"_" in existing` looks redundant beside the equality test and is not.

    A code can legitimately have no dots at all -- a ref tail of `4a` yields the code
    `4a`. Without the underscore requirement, `existing == code.replace(".", "_")` is
    then `"4a" == "4a"`, the swap fires, and the function returns the header it was
    given instead of None.

    That matters to `dcp_restore_section_codes.py`, which treats any non-None result as
    a repair to apply: it would count an identical value as a change and write it. A
    "repair" tally inflated with no-op writes is how a real repair stops being visible.
    Found by a mutation that survived the first version of this file.
    """

    DOC_4 = "Ku-ring-gai_DCP_2024__section_a_part_4"
    REF_4A = f"{DOC_4}__4a"

    def test_the_code_really_can_have_no_dots(self):
        assert section_code(self.REF_4A, self.DOC_4) == "4a"

    def test_a_dotless_code_already_present_is_left_alone(self):
        assert repaired_header("4a Title", self.REF_4A, self.DOC_4) is None, (
            "returning the same header as a 'repair' makes restore write a no-op")

    def test_a_dotless_code_is_still_added_when_the_header_lacks_one(self):
        assert repaired_header("Title", self.REF_4A, self.DOC_4) == "4a Title"
