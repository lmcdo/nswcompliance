"""Committing an unchanged chapter twice must not insert the provision twice.

Approved rows accumulate. A chapter re-read on 28 July, 2 September and 18 September — with
the council's PDF unchanged throughout — carries three approved batches, all with the SAME
source_content_hash. The commit inserted every one, so the second copy of a provision hit

    uq_provisions_current_identity
    ON (COALESCE(document_id,''), COALESCE(ref_number,''),
        COALESCE(section_header,''), md5(provision_text)) WHERE is_current

and the whole chapter rolled back. Ten chapters failed that way in the 2026-09-18 run:
blacktown, five canterbury_bankstown, both georges_river, hornsby.

The currency guard already in the script cannot see it. That guard skips a chapter whose
approved rows span more than one source hash — it separates different VERSIONS of a
document, and these are repeated READS of one.

Source-shape test: no database, no clock. It reads the query the script actually issues.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "scripts" / "dcp_commit_approved.py").read_text(encoding="utf-8")


def _insert_fetch() -> str:
    """The SELECT whose rows are looped over and inserted as provisions."""
    m = re.search(r"SELECT[^;]*?FROM dcp_review_queue\s*\n\s*WHERE council = %s AND chapter_key"
                  r" = %s AND status = 'approved'[^\"]*?ORDER BY [^\"]*", SRC, re.S)
    assert m, "the insert-site fetch could not be located in dcp_commit_approved.py"
    return " ".join(m.group(0).split())


class TestOnlyTheLatestDecisionPerProvisionIsCommitted:
    def test_the_fetch_deduplicates_by_ref_number(self):
        fetch = _insert_fetch()
        assert "DISTINCT ON (ref_number)" in fetch, fetch

    def test_it_keeps_the_NEWEST_row_for_each_ref(self):
        """id DESC, not ASC: the latest review of a provision is the one that counts. With
        ASC the commit would resurrect July's text over September's."""
        fetch = _insert_fetch()
        assert re.search(r"ORDER BY\s+ref_number,\s*id DESC", fetch), fetch

    def test_the_fetch_still_selects_what_the_insert_loop_unpacks(self):
        """Guards the guard: DISTINCT ON changes the select list's shape if edited
        carelessly, and the loop unpacks five columns positionally."""
        fetch = _insert_fetch()
        for col in ("document_id", "ref_number", "new_text", "new_page", "change_type"):
            assert col in fetch, col
        loop = re.search(r"for document_id, ref_number, new_text, new_page, change_type in rows",
                         SRC)
        assert loop, "the insert loop no longer unpacks five columns — re-check the fetch"

    def test_the_multi_hash_guard_is_still_there(self):
        """This fix is not a replacement for the currency guard. That one stops a STALE
        approval (the PDF changed since review); this one stops a REPEATED one (the PDF did
        not). Removing either brings back a different failure."""
        assert "hash_variants" in SRC
        assert re.search(r"hash_variants\W+.{0,40}>\s*1", SRC, re.S), \
            "the >1 hash-variants skip is gone"
