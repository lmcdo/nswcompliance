#!/usr/bin/env python3
"""List the Ku-ring-gai built-form figures that carry upper-level setback legends (read-only).

prior-art-checked: reuse not viable -- the 87 map-legend rows were withheld by
data/not_a_rule_krg_map_legend_2026-10-17.json; nothing in scripts/, services/ or the
frontend records which figure page each legend came from. scripts/page_proof_council.py is
reused only for local_pdf (R2 download + cache).

For each withheld row whose text says 'upper level setback', take the chapter, precinct and
pdf_page, open the pinned chapter PDF and read the figure caption on that page. Exactly one
caption -> its id; zero or several -> null (never guessed). Writes
frontend-nextjs/data/frontage-setback-figures.json. SELECT only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

COUNCIL = "ku_ring_gai"
IDS_FILE = ROOT / "data" / "not_a_rule_krg_map_legend_2026-10-17.json"
OUT = ROOT / "frontend-nextjs" / "data" / "frontage-setback-figures.json"
CAPTION_RE = re.compile(r"Figure\s*(\d+[A-Z]?(?:\.\d+)*(?:-\d+)?):")
UPPER_RE = re.compile(r"upper level setback", re.I)


def pick_caption(page_text: str) -> str | None:
    """The figure id when the page has exactly one distinct caption (trailing colon), else None."""
    found = {m.group(1) for m in CAPTION_RE.finditer(page_text or "")}
    return next(iter(found)) if len(found) == 1 else None


def main() -> int:
    import fitz
    from dotenv import load_dotenv
    import page_proof_council as ppc
    from state_law_proof import connect

    load_dotenv(ROOT / ".env")
    ids = [r["id"] for r in json.loads(IDS_FILE.read_text(encoding="utf8"))]
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """SELECT p.id, p.source_chapter_key, p.v2_precinct_id, p.pdf_page, p.provision_text,
                  r.r2_current_path, r.r2_public_pdf_url
           FROM regulatory_provisions p
           JOIN dcp_chapter_registry r ON r.council = p.source_council
             AND r.chapter_key = p.source_chapter_key AND r.is_active
           WHERE p.id = ANY(%s) AND p.is_current AND p.source_council = %s""",
        (ids, COUNCIL),
    )
    rows = cur.fetchall()
    conn.close()
    kept = [r for r in rows if r[4] and UPPER_RE.search(r[4]) and r[3]]
    print(f"ids={len(ids)} selected={len(rows)} upper-level={len(kept)}")

    chapters: dict[str, dict] = {}
    groups: dict[str, set] = defaultdict(set)
    for _id, ck, pid, page, _t, path, url in kept:
        chapters[ck] = {"r2_path": path, "pdf_url": url}
        groups[ck].add((pid, int(page)))

    cache = Path(tempfile.gettempdir()) / "page_evidence_cache" / "pdf"
    out = []
    n_fig = n_null = 0
    for ck in sorted(groups):
        c = chapters[ck]
        pdf = ppc.local_pdf(c["r2_path"], cache)
        sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
        doc = fitz.open(pdf)
        figs = []
        for pid, page in sorted(groups[ck], key=lambda x: (x[0] or "", x[1])):
            fig = pick_caption(doc[page - 1].get_text()) if 0 < page <= len(doc) else None
            figs.append({"precinct_id": pid, "page": page, "figure": fig})
            n_fig += 1
            n_null += fig is None
        doc.close()
        out.append({"chapter_key": ck, "r2_path": c["r2_path"], "pdf_sha256": sha,
                    "pdf_url": c["pdf_url"], "figures": figs})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated": "2026-10-17",
                               "source": "scripts/frontage_setback_figures.py",
                               "council": COUNCIL, "chapters": out}, indent=2) + "\n",
                   encoding="utf8")
    print(f"chapters={len(out)} figures={n_fig} figure_null={n_null} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
