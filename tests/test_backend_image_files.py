"""Every file the backend reads at runtime outside services/ must be COPY'd into its image.

Origin: services/council_key.py reads frontend-nextjs/lib/lga-slug-renames.json; the Railway image
(Dockerfile.python) copied only services/ and some scripts, so /constraint-arithmetic/full failed
in production (502) right after #1374 deployed, 2026-10-19.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_council_key_list_is_in_the_backend_image():
    docker = (ROOT / "Dockerfile.python").read_text(encoding="utf-8")
    assert re.search(r"^COPY frontend-nextjs/lib/lga-slug-renames\.json ", docker, re.M)


def test_council_key_reader_points_at_that_path():
    from services.council_key import _RENAMES_PATH
    assert _RENAMES_PATH.relative_to(ROOT).as_posix() == "frontend-nextjs/lib/lga-slug-renames.json"
