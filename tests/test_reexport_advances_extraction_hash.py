"""A re-export must advance the extraction hash, or the optimisation self-defeats.

WHAT WENT WRONG
---------------
When a council recompresses a PDF, r2_monitor correctly detects that the text is
identical and skips re-extraction. It updated ``content_hash`` to the new bytes
and left ``provisions_extracted_from_hash`` at the old value.

``provisions_extracted_from_hash`` is written in exactly ONE place - the
extractor - so once those two diverge they stay diverged. And that divergence is
exactly what DQ-70 counts as "the source changed since we extracted". So every
re-export created a permanent false entry, clearable only by the full
re-extraction the branch exists to avoid.

Measured 2026-08-15: 333 of DQ-70's 595 provisions (56%) were one such chapter,
ashfield/chapter-e1-heritage - 25,959,773 bytes recompressed to 3,879,460 with
byte-identical normalised text.

These tests read the SQL rather than run it. Exercising the branch needs a live
council fetch, an R2 round-trip and a database, and a test that needs all three
is a test that gets skipped. What can be asserted cheaply is the property that
was missing: the re-export UPDATE must carry the field, and must not clobber a
NULL.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SOURCE = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")


def _reexport_update_sql() -> str:
    """The UPDATE inside the re-export branch, as written."""
    marker = "[re-export] bytes changed but text identical"
    idx = SOURCE.index(marker)
    # The branch's UPDATE is the next one after the marker; stop at its WHERE.
    tail = SOURCE[idx:]
    start = tail.index("UPDATE dcp_chapter_registry")
    end = tail.index("WHERE id=%s", start)
    return tail[start:end]


def test_the_reexport_branch_exists():
    """Guard the guard: if the branch is renamed these tests must fail loudly."""
    assert "[re-export] bytes changed but text identical" in SOURCE


def test_reexport_update_advances_the_extraction_hash():
    """The regression: the field must be in the SET clause."""
    sql = _reexport_update_sql()
    assert "provisions_extracted_from_hash" in sql, (
        "The re-export branch updates content_hash but not "
        "provisions_extracted_from_hash. They then differ forever, which is what "
        "DQ-70 counts — so every re-export creates a permanent false entry."
    )


def test_reexport_update_leaves_a_null_extraction_hash_null():
    """A chapter never extracted must not be given a hash.

    Setting it would claim provisions exist that do not, which is a worse error
    than the one being fixed: it would make an unextracted chapter look current.
    """
    sql = _reexport_update_sql()
    condensed = re.sub(r"\s+", " ", sql)
    assert "IS NULL" in condensed and "THEN NULL" in condensed, (
        "The extraction hash must be guarded so NULL stays NULL: "
        f"got {condensed!r}"
    )


def test_reexport_update_still_advances_content_hash():
    """The original behaviour must survive the fix."""
    assert "content_hash=%s" in re.sub(r"\s+", " ", _reexport_update_sql())


def test_only_the_extractor_and_the_reexport_branch_write_the_field():
    """If a third writer appears, this reasoning needs revisiting.

    The whole diagnosis rests on the field having exactly one writer before this
    change. A new one silently invalidates that, so it should break a test
    rather than a conclusion.
    """
    writers = set()
    for path in (ROOT / "scripts").glob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"provisions_extracted_from_hash\s*=", text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line = text[line_start:text.find("\n", m.start())]
            if line.lstrip().startswith(("#", "--", "AND", "OR")):
                continue
            writers.add(path.name)
    assert writers <= {"dcp_extract_changed.py", "r2_monitor.py"}, (
        f"a new writer of provisions_extracted_from_hash appeared: {writers}")
