"""Export the councils that have withheld area rules to the frontend.

prior-art-checked: reuse not viable -- the listed scripts build unrelated indexes; this is the
only reader of not_covered_2026-10-15.json for the frontend, and no existing shared/ export
carries it.

Source:  data/chapter_scope/not_covered_2026-10-15.json  (withheld_area_rules)
Output:  frontend-nextjs/shared/not-covered-councils.json
         {council_slug: [{chapter_key, reason, count_hint}]}

The address page says so when its council has any entry (OC-21). The areas have no
outline, so the notice is per council, not per address.

Usage: python scripts/export_not_covered_councils.py [--check]
--check exits 1 if the shared file is out of date (the drift test calls build()).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "chapter_scope" / "not_covered_2026-10-15.json"
TARGET = ROOT / "frontend-nextjs" / "shared" / "not-covered-councils.json"


def build(source: Path = SOURCE) -> dict:
    entries = json.loads(source.read_text(encoding="utf-8"))["withheld_area_rules"]
    out: dict[str, dict[str, dict]] = {}
    for e in entries:
        chapters = out.setdefault(e["council"], {})
        row = chapters.setdefault(
            e["chapter_key"],
            {"chapter_key": e["chapter_key"], "title": e.get("title") or e["chapter_key"], "reason": e["reason"],
             "count_hint": 0},
        )
        row["count_hint"] += int(e.get("expect") or len(e.get("ids") or []))
    return {c: sorted(r.values(), key=lambda x: x["chapter_key"]) for c, r in sorted(out.items())}


def render(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    text = render(build())
    if "--check" in sys.argv:
        sys.exit(0 if TARGET.read_text(encoding="utf-8") == text else 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
