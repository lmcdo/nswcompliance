"""dcp_page_repair.py: only a confirmed move changes a link, and every publish re-checks.

Measured 2026-09-26: 45% of 17,489 served rules linked to the first page of the AI reader's
chunk. The repair must correct those it can confirm, leave the rest where they are with a
verdict that says so, and run after every publish so the next extraction cannot undo it.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")

import dcp_page_repair as R  # noqa: E402

ROW = {"id": 7, "pdf_page": 13, "page_range": [13, 14], "r2_current_path": "c/v1/ch.pdf",
       "printed_page_label": None, "page_check": None, "page_source_path": None}
LABELS = {13: "9", 18: "14"}


def test_a_confirmed_move_shifts_the_page_and_its_span_and_takes_that_pages_label():
    p = R.plan_row(ROW, 18, "moved", LABELS)
    assert (p["pdf_page"], p["page_range"], p["printed_page_label"]) == (18, [18, 19], "14")
    assert p["page_check"] == "moved" and p["page_source_path"] == "c/v1/ch.pdf"


def test_an_unresolved_rule_keeps_its_page_and_gets_no_label():
    """Its stored page does not hold it: a label would present a wrong page as the council's."""
    p = R.plan_row(ROW, None, "unresolved", LABELS)
    assert (p["pdf_page"], p["page_range"], p["printed_page_label"]) == (13, [13, 14], None)
    assert p["page_check"] == "unresolved"


def test_a_rule_already_on_its_page_keeps_it_and_gets_its_label():
    p = R.plan_row(ROW, 13, "on_page", LABELS)
    assert (p["pdf_page"], p["page_range"], p["printed_page_label"]) == (13, [13, 14], "9")


def test_no_stored_span_becomes_the_single_new_page():
    assert R.shift_range(None, 13, 18) == [18]
    assert R.shift_range([13], None, 18) == [18]


def test_an_unchanged_row_is_not_rewritten():
    done = dict(ROW, printed_page_label="9", page_check="on_page", page_source_path="c/v1/ch.pdf")
    assert not R.changed(done, R.plan_row(done, 13, "on_page", LABELS))
    assert R.changed(ROW, R.plan_row(ROW, 13, "on_page", LABELS))


def test_every_publish_rechecks_page_links():
    src = (ROOT / "scripts" / "dcp_commit_approved.py").read_text(encoding="utf-8")
    assert '"dcp_page_repair.py"' in src and '"--apply"' in src


def test_it_only_writes_onto_the_pdf_still_in_force():
    src = (ROOT / "scripts" / "dcp_page_repair.py").read_text(encoding="utf-8")
    assert "reg.r2_current_path IS NOT DISTINCT FROM v.src" in src


def test_the_migration_forgets_a_verdict_when_the_text_or_page_changes():
    sql = (ROOT / "migrations" / "079_rule_page_check.sql").read_text(encoding="utf-8")
    assert "NEW.provision_text IS DISTINCT FROM OLD.provision_text" in sql
    assert "NEW.pdf_page IS DISTINCT FROM OLD.pdf_page" in sql
    assert "AFTER UPDATE OF r2_current_path, is_active ON dcp_chapter_registry" in sql


def test_the_health_check_counts_a_rule_with_no_verdict_even_without_a_pdf_path():
    """Cross-review 2026-09-26: NULL source path IS NOT DISTINCT FROM a NULL registry path."""
    src = (ROOT / "scripts" / "dcp_page_repair.py").read_text(encoding="utf-8")
    assert "rp.page_check IS NULL" in src
