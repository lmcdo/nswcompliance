"""Render a cropped map image for each may-apply area from the council's chapter PDF.

prior-art-checked: new; no existing script crops plan figures (grep render/get_pixmap in scripts/).
Reads DATABASE_URL (SELECT only). PDFs are fetched with curl (urllib gets 403).
Usage: python scripts/render_may_apply_maps.py
Writes data/may_apply_maps/<area_id>.png and index.json. Skips (and records) areas with no figure found.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import fitz
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "chapter_scope" / "suburb_unconfirmed_areas.json"
OUT = ROOT / "data" / "may_apply_maps"
DPI = 150
MARGIN = 8  # points
MIN_FRACTION = 0.25  # a "large figure" covers at least this share of the page
MAX_BYTES = 400_000


def _env(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    for d in (ROOT, *ROOT.parents):
        f = d / ".env"
        if f.exists():
            m = re.search(rf"^{name}=(.*)$", f.read_text(encoding="utf-8"), re.M)
            if m:
                return m.group(1).strip().strip("\"'")
    return ""


def figure_rect(page: fitz.Page) -> fitz.Rect | None:
    """Largest image or drawing cluster on the page, or None if under MIN_FRACTION of the page."""
    pr = page.rect
    cands = [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
    try:
        cands += [fitz.Rect(r) for r in page.cluster_drawings()]
    except Exception:
        pass
    cands = [r & pr for r in cands if not r.is_empty]
    if not cands:
        return None
    best = max(cands, key=lambda r: r.width * r.height)
    return best if best.width * best.height >= MIN_FRACTION * pr.width * pr.height else None


def pick_page(doc: fitz.Document, start: int, title: str) -> tuple[int, fitz.Rect, str] | None:
    n = len(doc)
    r = figure_rect(doc[start - 1]) if 1 <= start <= n else None
    if r:
        return start, r, "large figure on the area's own page"
    skip = {"residential", "medium", "density", "road", "street", "parade"}
    words = [w for w in re.findall(r"[a-z]{4,}", title.lower()) if w not in skip]
    best = None
    for d in (1, -1, 2, -2, 3, -3):
        p = start + d
        if not 1 <= p <= n:
            continue
        txt = doc[p - 1].get_text().lower()
        if not re.search(r"\b(figure|map)\b", txt):
            continue
        r = figure_rect(doc[p - 1])
        if not r:
            continue
        hits = sum(w in txt for w in words)
        if hits >= 2 and (best is None or hits > best[0]):
            best = (hits, p, r)
    if best:
        return best[1], best[2], f"start page {start} had no large figure; page {best[1]} has a Figure/Map caption and {best[0]} title words"
    return None


def save_png(page: fitz.Page, clip: fitz.Rect, path: Path) -> tuple[int, int]:
    scale = DPI / 72
    while True:
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
        data = pix.tobytes("png")
        if len(data) <= MAX_BYTES or scale < 0.5:
            break
        scale *= 0.8
    path.write_bytes(data)
    return pix.width, pix.height


def main() -> None:
    areas = json.loads(SOURCE.read_text(encoding="utf-8"))["areas"]
    cur = psycopg2.connect(_env("DATABASE_URL"), options="-c statement_timeout=30000").cursor()
    # Current version only; one row per chapter, or the chapter is skipped (never a guessed version).
    cur.execute("select council, chapter_key, r2_public_pdf_url from dcp_chapter_registry"
                " where r2_public_pdf_url is not null and is_active")
    rows = cur.fetchall()
    seen: dict[tuple, set] = {}
    for c, k, u in rows:
        seen.setdefault((c, k), set()).add(u)
    urls = {key: next(iter(us)) for key, us in seen.items() if len(us) == 1}
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):  # a rerun must not leave images from an earlier, looser run
        old.unlink()
    index: dict[str, dict] = {}
    docs: dict[str, fitz.Document] = {}
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for a in areas:
            url = urls.get((a["council"], a["chapter_key"]))
            rec: dict = {"chapter_pdf_url": url}
            index[a["area_id"]] = rec
            if not url:
                rec["skipped"] = "no chapter PDF url in dcp_chapter_registry"
                continue
            if url not in docs:
                f = Path(tmp) / f"{len(docs)}.pdf"
                subprocess.run(["curl", "-sSfL", "-o", str(f), url], check=True)
                docs[url] = fitz.open(f)
            try:
                start = int(a.get("applies_to_page"))
            except (TypeError, ValueError):
                rec["skipped"] = "area has no applies_to_page"
                continue
            got = pick_page(docs[url], start, a["title"])
            if not got:
                rec["skipped"] = f"no large figure on page {start} or within 3 pages with a Figure/Map caption naming the area"
                continue
            p, r, how = got
            page = docs[url][p - 1]
            clip = fitz.Rect(r.x0 - MARGIN, r.y0 - MARGIN, r.x1 + MARGIN, r.y1 + MARGIN) & page.rect
            w, h = save_png(page, clip, OUT / f"{a['area_id']}.png")
            rec.update(page=p, file=f"{a['area_id']}.png", width=w, height=h, how_found=how)
        for d in docs.values():
            d.close()
    (OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    ok = sum("file" in v for v in index.values())
    print(f"rendered {ok}, skipped {len(index) - ok}")
    for k, v in index.items():
        if "skipped" in v:
            print("SKIP", k, v["skipped"])


if __name__ == "__main__":
    main()
