"""frontend-nextjs/shared/not-covered-councils.json must match the data file (OC-21)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import export_not_covered_councils as ex  # noqa: E402


def test_shared_file_matches_data_file():
    assert ex.TARGET.read_text(encoding="utf-8") == ex.render(ex.build()), (
        "run: python scripts/export_not_covered_councils.py"
    )


def test_every_council_has_a_chapter_and_reason():
    for council, rows in ex.build().items():
        assert rows, council
        assert all(r["chapter_key"] and r["reason"] for r in rows)
