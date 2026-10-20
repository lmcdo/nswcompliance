"""Export the areas whose rules may apply to a property, by suburb, to the frontend.

prior-art-checked: extends scripts/export_not_covered_councils.py (council-wide withheld list)
with a per-suburb list; that script reads a different source and shape.

Source:  data/chapter_scope/suburb_unconfirmed_areas.json  ({"areas": [...]})
Output:  frontend-nextjs/shared/may-apply-areas.json
         {council_slug: {SUBURB: [area, ...]}}  (suburb uppercase, areas sorted by area_id)

Usage: python scripts/export_may_apply_areas.py [--check]
--check exits 1 if the shared file is out of date (the drift test calls build()).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "chapter_scope" / "suburb_unconfirmed_areas.json"
TARGET = ROOT / "frontend-nextjs" / "shared" / "may-apply-areas.json"


def build(source: Path = SOURCE) -> dict:
    areas = json.loads(source.read_text(encoding="utf-8"))["areas"]
    out: dict[str, dict[str, list[dict]]] = {}
    for a in areas:
        suburb = " ".join(str(a["suburb"]).upper().split())
        out.setdefault(a["council"], {}).setdefault(suburb, []).append(a)
    return {
        c: {s: sorted(rows, key=lambda r: r["area_id"]) for s, rows in sorted(subs.items())}
        for c, subs in sorted(out.items())
    }


def render(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    text = render(build())
    if "--check" in sys.argv:
        sys.exit(0 if TARGET.read_text(encoding="utf-8") == text else 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
