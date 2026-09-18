"""The re-pointed source, checked against the registry it actually wrote to.

The pure tests cover the targeting table and the refusal thresholds. They cannot see the
thing that matters afterwards: that northern_beaches really did move off the immutable
2016 file, and has not quietly drifted back.

That file is the reason this exists. "Warringah DCP 2011 - as amended 7 May 2016.pdf" on a
shared bucket can never change, so content_hash always matched provisions_extracted_from_hash
and every freshness check read green while the council went to amendment 23 (Part G10,
commenced 15 September 2025). A test that only mocks the database would have agreed with
the green.

Opt-in as this repo does it: PYTEST_REAL_DB=1 plus @pytest.mark.database, deselected by
default per pytest.ini. Read-only.

    PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database \
        tests/test_repoint_html_book_source_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

COUNCIL, CHAPTER = "northern_beaches", "warringah-dcp-2011-full"


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database "
                    "tests/test_repoint_html_book_source_real_db.py")
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _row():
    import psycopg2

    conn = psycopg2.connect(os.environ.get("DATABASE_URL")
                            or os.environ["SUPABASE_DB_URL"], connect_timeout=20)
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '30s'")
            cur.execute("""
                SELECT council_url, r2_current_path, url_content_length, is_active,
                       r2_public_pdf_url
                FROM dcp_chapter_registry WHERE council = %s AND chapter_key = %s
            """, (COUNCIL, CHAPTER))
            return cur.fetchone()
    finally:
        conn.close()


class TestTheSourceIsNoLongerFrozen:
    def test_the_chapter_still_exists_and_is_active(self):
        _skip_if_no_real_db()
        row = _row()
        assert row is not None, f"{COUNCIL}/{CHAPTER} is not in the registry"
        assert row[3] is True

    def test_it_no_longer_points_at_the_immutable_2016_file(self):
        """The specific trap: a filename carrying its own amendment date is a frozen
        artefact, and its unchanged hash means nothing."""
        _skip_if_no_real_db()
        council_url = (_row()[0] or "").lower()
        assert "as%20amended" not in council_url and "as amended" not in council_url
        assert "shared-drupal-s3fs" not in council_url
        assert "2016" not in council_url

    def test_it_points_at_the_councils_own_whole_book_export(self):
        _skip_if_no_real_db()
        council_url = _row()[0] or ""
        assert council_url.startswith("https://eservices.northernbeaches.nsw.gov.au/")
        # Without children=true the export is a contents page: 1 page, no controls.
        assert "children=true" in council_url and "page=book" in council_url

    def test_the_stored_copy_is_the_render_not_the_old_pdf(self):
        _skip_if_no_real_db()
        path, length = _row()[1], _row()[2]
        assert path and "v-html-" in path, path
        # The render is ~23.5 MB; the superseded 2016 PDF was 11,759,557 bytes.
        assert length and length > 15_000_000, length

    def test_the_source_is_not_the_draft_plan(self):
        """The draft Northern Beaches DCP was on exhibition to 30 August 2026 and is not
        law. Serving from it would be worse than the stale copy this replaced."""
        _skip_if_no_real_db()
        council_url = (_row()[0] or "").lower()
        assert "yoursay" not in council_url and "draft" not in council_url


class TestTheLinkAReaderOpensIsTheCopyTheRulesCameFrom:
    """The repoint moved r2_current_path and left r2_public_pdf_url behind, so the link
    under every Northern Beaches rule opened the April copy while the rules were read from
    the September render. conveyancing_db.py serves COALESCE(r2_public_pdf_url, ...) as
    that link, so this was served, not merely stored — and it is the shape the OC-8
    sub-check exists to catch, which it did: 'active chapters whose public PDF link is not
    their current copy: 1'."""

    def test_the_public_link_ends_with_the_current_path(self):
        _skip_if_no_real_db()
        row = _row()
        path, public = row[1], row[4]
        assert public, "no public link: the rule has nothing to open"
        assert public.endswith("/" + path), (
            f"the link opens a different copy than the rules were read from.\n"
            f"  public: {public}\n  path  : {path}")

    def test_the_public_link_is_not_the_superseded_april_copy(self):
        """Named, not inferred: v1.1-2026-04-27 is the copy it was left pointing at."""
        _skip_if_no_real_db()
        assert "v1.1-2026-04-27" not in (_row()[4] or "")

    def test_no_active_chapter_anywhere_has_this_shape(self):
        """The same query OC-8 runs. Scoped to every council, because a repoint script is
        general and the next one will not be Northern Beaches."""
        _skip_if_no_real_db()
        import psycopg2
        conn = psycopg2.connect(os.environ.get("DATABASE_URL")
                                or os.environ["SUPABASE_DB_URL"], connect_timeout=20)
        try:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '30s'")
                cur.execute(
                    "SELECT council, chapter_key FROM dcp_chapter_registry WHERE is_active "
                    "AND r2_current_path IS NOT NULL AND r2_public_pdf_url IS NOT NULL "
                    "AND right(r2_public_pdf_url, length(r2_current_path) + 1) "
                    "    <> ('/' || r2_current_path)")
                stale = cur.fetchall()
        finally:
            conn.close()
        assert stale == [], f"chapters whose public link is not their current copy: {stale}"
