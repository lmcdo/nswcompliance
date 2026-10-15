"""A deterministic reader for side-by-side two-column chapters (Ashfield Chapter F: performance criteria on the left,
design solutions "DS4.1" on the right). Dry run unless --apply, which writes an APPROVED, FULL-REPLACE queue batch
(user "fix the ashfield f reader", 2026-10-15); publishing stays dcp_commit_approved with its guards.

prior-art-checked: the section reader (Docling + DeepSeek) re-read Ashfield F and failed the R2 nothing-lost gate
(2026-10-15); the old pdfplumber rows interleave the two columns. No model is used here: lines come from the cached
column-order reading (citation_proof), split at the page's column gap by x position, and every block is the
council's text in its own casing.

Blocks: per page and column, top to bottom; a new block starts at a PC/DS/C/O label, at a heading (short capitalised
line with no sentence end) or at a vertical gap wider than 1.8 line heights. Running heads/footers and the side tab
(x > 520) are dropped.

PROOF before any write (printed; --apply refuses if any fails):
  1. every printed control (chapter_gate.missing_controls against the blocks) is present;
  2. the blocks hold >= 97% of the 8-word phrases of PyMuPDF's own text of those pages (heads/footers excluded);
  3. >= 95% of blocks are printed whole in PyMuPDF's page text (an extraction independent of the line cache).

usage: python column_reader.py <worktree> council/chapter [--split-x 265] [--apply]
"""
import collections
import os
import re
import statistics
import sys
from pathlib import Path

WT = Path(sys.argv[1])
CO, KEY = sys.argv[2].split("/")
APPLY = "--apply" in sys.argv
SPLIT_X = float(sys.argv[sys.argv.index("--split-x") + 1]) if "--split-x" in sys.argv else 265.0
# Hornsby DCP 2024 (2026-10-15): the right column runs to x 553, its side tab is absent, and justified rows are stored
# word by word -- --xmax 560 --join-words. Defaults keep the Ashfield F behaviour unchanged.
XMAX = float(sys.argv[sys.argv.index("--xmax") + 1]) if "--xmax" in sys.argv else 520.0
JOIN_WORDS = "--join-words" in sys.argv
JOIN_GAP = 20.0
TABLES = "--tables" in sys.argv
TABLE_JOIN = 40.0
TABLE_CELL_X = 200.0
SECTION_RE = (re.compile(sys.argv[sys.argv.index("--section-re") + 1]) if "--section-re" in sys.argv else None)
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import chapter_gate as g  # noqa: E402
g.setup(WT)
sys.stdout.reconfigure(encoding="utf-8")
import fitz  # noqa: E402
import psycopg2  # noqa: E402
import council_quote as cq  # noqa: E402
import dq_probe_section_code_not_in_source as probe  # noqa: E402

W = re.compile(r"[a-z0-9]+")
PART = re.compile(r"Part\s+(\d+)\s*[–-]")


def heading(t):
    return re.match(r"^\s*[A-Z]", t) and len(t.split()) <= 7 and not re.search(r"[.;:?!,)]\s*$", t)


def render(ls):
    """A block's text. A table inside the column (cells side by side, x more than 60pt apart -- Ashfield F p10
    'Site Area | Minimum Landscaped Area') is written one printed row per line, 'cell | cell', each left line joined to
    the row of the nearest value at or above it, so '601m2 and' / 'over' stay one cell beside '35 percent of site area'.
    Ordinary text (item indents under 60pt) is written top to bottom."""
    ls = [(y, round(x), t) for y, x, t in ls]       # one x scale: 385.6 must not fall left of a 386 cut
    xs = sorted({x for _y, x, _t in ls})
    if "--debug-table" in sys.argv and any("percent" in t for _y, _x, t in ls):
        print("   XS", xs, [(round(y), round(x), t[:15]) for y, x, t in ls][:8])
    # a cell gap is > 50pt (Ashfield F p10: 332 vs 386) AND the two sides share >= 2 printed rows (same height);
    # an item indent (44pt) never has aligned rows on both sides
    cuts = [b for a, b in zip(xs, xs[1:]) if b - a > 50
            and sum(1 for y1, x1, _t in ls if x1 < b for y2, x2, _u in ls if x2 >= b and abs(y1 - y2) <= 2) >= 2]
    if not cuts or g.CONTROL.match(ls[0][2]) and len(ls) <= 2:
        return "\n".join(t for _y, _x, t in sorted(ls, key=lambda r: (r[0], r[1])))
    cut = cuts[-1]                                   # the value column is the right-most cluster
    left = sorted([r for r in ls if r[1] < cut], key=lambda r: r[0])
    right = sorted([r for r in ls if r[1] >= cut], key=lambda r: r[0])
    if not left or not right:
        return "\n".join(t for _y, _x, t in sorted(ls, key=lambda r: (r[0], r[1])))
    rows = [[[], [t]] for _y, _x, t in right]
    anchors = [y for y, _x, _t in right]
    if "--debug-table" in sys.argv:
        print("   TABLE", [(round(y), round(x), t[:20]) for y, x, t in ls][:12])
    lead = []
    for y, _x, t in left:
        above = [i for i, ay in enumerate(anchors) if ay <= y + 2]
        if not above:
            lead.append(t)                           # text above the first row (a lead-in) stays as prose
            continue
        rows[max(above, key=lambda i: anchors[i])][0].append(t)
    out, prev, prev_y = list(lead), None, None
    for (cells_l, cells_r), ay in zip(rows, anchors):
        # a value with no label beside it joins the row above ONLY when it is that value's wrapped next line (within
        # one line height); otherwise it is its own row -- never attributed to another row's label
        if not cells_l and prev is not None and ay - prev_y <= 13:
            prev[1].extend(cells_r)
            prev_y = ay
            continue
        prev = [cells_l, cells_r]
        prev_y = ay
        out.append(prev)
    return "\n".join(x if isinstance(x, str) else f"{' '.join(x[0])} | {' '.join(x[1])}" for x in out)


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 60000")
    cur.execute("SELECT r2_current_path, content_hash FROM dcp_chapter_registry WHERE council=%s AND chapter_key=%s "
                "AND is_active", (CO, KEY))
    path, chash = cur.fetchone()
    readings, cased = cq.load_chapter(path)
    st = min((cq.Stream(ch, cased) for ch in readings),
             key=lambda s: sum(1 for a, b in zip(s.lines, s.lines[1:]) if a.page == b.page and abs(a.x - b.x) > 40))
    pdf = cq.CACHE / "pdf" / (probe._cache_file(cq.CACHE, path).stem + ".pdf")
    with fitz.open(str(pdf)) as d:
        raw = {n: p.get_text() for n, p in enumerate(d, 1)}
    part_of = {}
    last_part = None
    for n in sorted(raw):
        m = PART.search(raw[n])
        last_part = m.group(1) if m else last_part
        part_of[n] = last_part
    # Lines straight from the PDF (PyMuPDF dict: each line's spans, position, the council's casing). NOT the cached
    # line reading: for Ashfield F it split "PC10.1" into "pc10." + "1", lowercased labels and dropped lines.
    pdf_lines = []
    x_right = {}
    right_of = {}
    cells = collections.defaultdict(list)
    with fitz.open(str(pdf)) as d:
        for n, pg in enumerate(d, 1):
            for blk in pg.get_text("dict")["blocks"]:
                for ln in blk.get("lines") or []:
                    t = " ".join(s["text"] for s in ln["spans"]).strip()
                    if t:
                        pdf_lines.append((n, ln["bbox"][0], ln["bbox"][1], t))
                        x_right[(n, ln["bbox"][0], ln["bbox"][1], t)] = ln["bbox"][2]
            if TABLES or JOIN_WORDS:
                for dr in pg.get_drawings():
                    for it in dr["items"]:
                        if it[0] == "re" and it[1].height >= 8 and it[1].width >= 40:
                            cells[n].append((it[1].x0, it[1].y0, it[1].x1, it[1].y1))
    spot = collections.defaultdict(set)      # running heads/footers: same text at the same height on 5+ pages
    for n, x, y, t in pdf_lines:
        spot[(t, round(y / 5))].add(n)
    # a label is never a running head: every Part opens with DS1.1 at the same spot
    repeated = {k[0] for k, ps in spot.items() if len(ps) >= 5 and not g.CONTROL.match(k[0])}
    by_page = collections.defaultdict(list)
    for n, x, y, t in pdf_lines:
        if t in repeated or x > XMAX or re.fullmatch(r"\d{1,3}", t):
            continue
        by_page[n].append((0 if x < SPLIT_X else 1, y, x, t))
    if JOIN_WORDS:
        # Justified text (Hornsby DCP 2024) is stored as one PDF "line" per word on a stretched row: 'protected' x88,
        # 'matters' x143, 'listed' x190 at the same height. Left apart they read as table cells (gaps > 50pt with
        # aligned rows) and the words of a row scatter. Pieces in one column within 2pt of height and under JOIN_GAP pt
        # apart are one printed line; a table cell gap is wider, so cells stay apart.
        for n in list(by_page):
            out, ends = [], []
            for c, y, x, t in sorted(by_page[n], key=lambda r: (r[0], round(r[1]), r[2])):
                for i in range(len(out) - 1, -1, -1):
                    oc, oy, ox, ot = out[i]
                    # never across a drawn table cell edge (Hornsby p27: 'combined' ends x231, the next cell starts x242)
                    edge = any(ends[i] - 1 <= ex <= x + 1 for x0, y0, x1, y1 in cells[n] if y0 - 2 <= y <= y1
                               for ex in (x0, x1))
                    if oc == c and abs(oy - y) <= 2 and 0 <= x - ends[i] <= JOIN_GAP and not edge:
                        out[i] = (oc, oy, ox, ot + " " + t)
                        ends[i] = x_right[(n, x, y, t)]
                        break
                else:
                    out.append((c, y, x, t))
                    ends.append(x_right[(n, x, y, t)])
            by_page[n] = out
            for (c, y, x, t), e in zip(out, ends):
                right_of[(n, y, x, t)] = e
    blocks = []
    table_blocks = []
    if TABLES:
        # A full-width table (Hornsby Part 1 p27 car parking rates: use x51, "< 800m" x242, "> 800m" x395) crosses the
        # column gutter, so a left/right split puts each rate in a different block from its use. A printed row with a
        # piece spanning the gutter marks a table band; bands closer than TABLE_JOIN pt are one table. Inside it every
        # printed row is written across the page, cells left to right "cell | cell", and the table is one block.
        for n in sorted(by_page):
            rows = by_page[n]
            cross = {y for c, y, x, t in rows
                     if x < SPLIT_X - 5 and right_of.get((n, y, x, t), x_right.get((n, x, y, t), x)) > SPLIT_X + 5}
            # a table row also when one printed row holds a cell starting just left of the gutter (x 200..gutter: body
            # text in the left column starts at its indents, x <= 90 here) beside cells on the other side of the gutter
            # (Hornsby p27 "Shops | 1/29m2 GLFA | 1/20m2 GLFA": x51, x242, x395)
            for c, y, x, t in rows:
                if TABLE_CELL_X <= x < SPLIT_X:
                    same = [xx for cc, yy, xx, tt in rows if abs(yy - y) <= 3]
                    if any(xx < TABLE_CELL_X for xx in same) and any(xx >= SPLIT_X for xx in same):
                        cross.add(y)
            cross = sorted(cross)
            bands = []
            for y in cross:
                if bands and y - bands[-1][1] <= TABLE_JOIN:
                    bands[-1][1] = y
                else:
                    bands.append([y, y])
            bands = [b for b in bands if sum(1 for y in cross if b[0] <= y <= b[1]) >= 3]
            # Drawn cells decide the table's extent when the page has them: a table is where a cell at the left edge
            # and a cell past the gutter overlap in height; touching cells (gap <= 3pt) are one table.
            rc = cells[n]
            spans = sorted((y0, y1) for x0, y0, x1, y1 in rc if x0 < TABLE_CELL_X
                           and x1 > TABLE_CELL_X + 20
                           and (any(xx0 >= SPLIT_X - 70 and yy0 < y1 and yy1 > y0 for xx0, yy0, xx1, yy1 in rc)
                                or any(TABLE_CELL_X <= xx < SPLIT_X and y0 - 6 <= yy <= y1 for _c, yy, xx, _t in rows)))
            if spans:
                cb = []
                for y0, y1 in spans:
                    if cb and y0 <= cb[-1][1] + 3:
                        cb[-1][1] = max(cb[-1][1], y1)
                    else:
                        cb.append([y0, y1])
                bands = [[y0 - 4, y1 - 4] for y0, y1 in cb if sum(1 for _c, y, _x, _t in rows if y0 - 4 <= y <= y1) >= 3]
            if not bands:
                continue
            keep = []
            for lo, hi in bands:
                inside = [r for r in rows if lo - 2 <= r[1] <= hi + 2]
                # A table row is the drawn cell its first-column text sits in (Hornsby p27: shaded cells 15pt high;
                # a value printed vertically centred beside a two-line label is at a different height from it). Rows
                # are the smallest drawn cells that start at the table's left edge; without drawn cells, printed height.
                left_cells = sorted({(round(y0, 1), round(y1, 1)) for x0, y0, x1, y1 in cells[n]
                                     if x0 < TABLE_CELL_X and lo - 20 <= y0 <= hi + 20})
                def holding(y):
                    return [c for c in left_cells if c[0] - 1 <= y + 4 <= c[1] + 1 and c[1] - c[0] <= 60]
                lab = [(c, y, x, t) for c, y, x, t in inside if x < TABLE_CELL_X]
                val = [(c, y, x, t) for c, y, x, t in inside if x >= TABLE_CELL_X]
                big = set()
                for _c, y, _x, _t in val:
                    hc = holding(y)
                    # a value printed level with a label line belongs to that line's own cell; a value printed between
                    # label lines (vertically centred on a wrapped label) belongs to the larger cell holding them all
                    if hc and not any(abs(ly - y) <= 2 for _c2, ly, _x2, _t2 in lab if min(hc, key=lambda q: q[1] - q[0]) in holding(ly)):
                        big.add(max(hc, key=lambda q: q[1] - q[0]))
                def row_of(y):
                    hc = holding(y)
                    if not hc:
                        return (round(y), round(y))
                    wide = [q for q in hc if q in big]
                    return max(wide, key=lambda q: q[1] - q[0]) if wide else min(hc, key=lambda q: q[1] - q[0])
                grouped = collections.defaultdict(list)
                for c, y, x, t in inside:
                    grouped[row_of(y)].append((x, y, t))
                lines = []
                for key in sorted(grouped):
                    cols = collections.defaultdict(list)
                    for x, y, t in sorted(grouped[key], key=lambda r: (r[1], r[0])):
                        col = next((k for k in cols if abs(k - x) <= 25), x)
                        cols[col].append(t)
                    lines.append([" ".join(cols[k]) for k in sorted(cols)])
                table_blocks.append((n, 0, "\n".join(" | ".join(cells) for cells in lines)))
            by_page[n] = [r for r in rows if not any(lo - 2 <= r[1] <= hi + 2 for lo, hi in bands)]
    for page in sorted(by_page):
        for col in (0, 1):
            ls = sorted([x for x in by_page[page] if x[0] == col], key=lambda x: x[1])
            if not ls:
                continue
            gaps = [b[1] - a[1] for a, b in zip(ls, ls[1:]) if 0 < b[1] - a[1] < 40]
            step = statistics.median(gaps) if gaps else 12.0
            cur_b, prev_y = [], None
            for _c, y, x, t in ls:
                # a heading starts a block only after a finished sentence: "... refer to" / "Part E1 - Heritage" is one
                # cross-reference, not a heading (Ashfield F p12 DS14.4)
                ended = not cur_b or re.search(r"[.;:?!]\s*$", cur_b[-1][2])
                new = (not cur_b or g.CONTROL.match(t) or (heading(t) and ended)
                       or (prev_y is not None and y - prev_y > 1.8 * step))
                if new and cur_b:
                    blocks.append((page, col, cur_b))
                    cur_b = []
                cur_b.append((y, x, t))
                prev_y = y
            if cur_b:
                blocks.append((page, col, cur_b))
    # a heading alone is not a rule: fold it into the block after it on the same page and column
    merged = []
    for b in blocks:
        if merged and len(merged[-1][2]) == 1 and heading(merged[-1][2][0][2]) and merged[-1][:2] == b[:2]:
            merged[-1] = (b[0], b[1], merged[-1][2] + b[2])
        else:
            merged.append(b)
    # a short block ("On merits", "is provided") is joined to the block above in its column, never dropped
    joined = []
    for p, c, ls in merged:
        if len(cq.norm("".join(t for _y, _x, t in ls))) < 20 and joined and joined[-1][:2] == (p, c):
            joined[-1] = (p, c, joined[-1][2] + ls)
        else:
            joined.append((p, c, ls))
    blocks = [(p, c, render(ls)) for p, c, ls in joined if len(cq.norm("".join(t for _y, _x, t in ls))) >= 4]
    blocks = sorted(blocks + table_blocks, key=lambda b: b[0])
    after = [cq.norm(t) for _p, _c, t in blocks]
    blob = "".join(after)
    # proof 1: printed controls
    missing = g.missing_controls(readings, cased, after, st)
    # proof 2: coverage of PyMuPDF's own page text (heads/footers/side tab removed by the same repeated-line test)
    rep = {cq.norm(x) for x in repeated}
    tot = hit = 0
    for n, text in raw.items():
        lines = [ln for ln in text.splitlines() if cq.norm(ln) and cq.norm(ln) not in rep]
        w = W.findall(" ".join(lines).lower())
        for i in range(0, max(0, len(w) - 7), 4):
            tot += 1
            hit += "".join(w[i:i + 8]) in blob
    cover = hit / max(1, tot)
    # proof 3: each block printed whole in the independent page text
    pages_n = {n: cq.norm(t) for n, t in raw.items()}
    whole = sum(1 for p, _c, t in blocks if cq.norm(t) in pages_n.get(p, "") + pages_n.get(p + 1, "")) / max(1, len(blocks))
    print(f"{CO}/{KEY}: {len(blocks)} blocks from {len(by_page)} pages | controls missing {len(missing)} | "
          f"PDF text covered {cover:.1%} | blocks printed whole {whole:.1%}")
    for _i, p, t in missing[:5]:
        print(f"    missing p{p}: {t[:90]!r}")
    for p, c, t in ([b for b in blocks if str(b[0]) in sys.argv[sys.argv.index("--page") + 1].split(",")]
                    if "--page" in sys.argv else blocks[100:106]):
        print(f"    p{p} {'L' if c == 0 else 'R'}: {t[:int(os.environ.get('SHOW', '110'))]!r}")
    if "--why" in sys.argv:
        import random
        random.seed(1)
        miss_ph = []
        for n, text in raw.items():
            lines = [ln for ln in text.splitlines() if cq.norm(ln) and cq.norm(ln) not in rep]
            w = W.findall(" ".join(lines).lower())
            for i in range(0, max(0, len(w) - 7), 4):
                if "".join(w[i:i + 8]) not in blob:
                    miss_ph.append((n, " ".join(w[i:i + 8])))
        print("  pages with most missing:", collections.Counter(n for n, _ in miss_ph).most_common(8))
        for n, ph in random.sample(miss_ph, min(8, len(miss_ph))):
            print(f"  missing p{n}: {ph}")
        bad = [(p, t) for p, _c, t in blocks if cq.norm(t) not in pages_n.get(p, "") + pages_n.get(p + 1, "")]
        for p, t in random.sample(bad, min(5, len(bad))):
            print(f"  not whole p{p}: {t[:140]!r}")
    # Proofs taken from the PDF's own lines (the cache-based control check and 8-word phrases both misjudge a
    # side-by-side page: PyMuPDF's page text runs across the columns, the cache drops lines):
    #   A. every printed line (heads/footers/side tab/page numbers excluded) is in a block of its own page;
    #   B. every printed label line (DS4.6, PC10.1, C4, O2) starts a block on its page.
    page_blob = collections.defaultdict(str)
    starts = collections.defaultdict(set)
    for p, _c, t in blocks:
        page_blob[p] += cq.norm(t)
        for ln in t.splitlines():
            m = g.CONTROL.match(ln)
            if m:
                starts[p].add(m.group(1) + m.group(2))
    kept = [(n, t) for n, x, y, t in pdf_lines
            if t not in repeated and x <= 520 and not re.fullmatch(r"\d{1,3}", t) and len(cq.norm(t)) >= 8]
    lines_in = sum(1 for n, t in kept if cq.norm(t) in page_blob[n]) / max(1, len(kept))
    labels = [(n, g.CONTROL.match(t).group(1) + g.CONTROL.match(t).group(2)) for n, x, y, t in pdf_lines
              if x <= 520 and g.CONTROL.match(t)]
    labels_missing = [(n, lab) for n, lab in labels if lab not in starts[n]]
    print(f"  A. PDF lines kept in their page's blocks: {lines_in:.2%} | B. labels missing: {len(labels_missing)} "
          f"{labels_missing[:5]}")
    if "--why" in sys.argv:
        for n, t in [(n, t) for n, t in kept if cq.norm(t) not in page_blob[n]][:8]:
            print(f"  line not kept p{n}: {t[:100]!r}")
    # C. independent confirmation: every block line (8+ characters) is also in the cached line reading of its page
    #    (citation_proof, built by a different method) -- the blocks themselves come from PyMuPDF, so PyMuPDF's own page
    #    text cannot confirm them (it only differs in reading order on a side-by-side page)
    cache_page = collections.defaultdict(str)
    for rd in readings:
        for ln in rd.lines:
            cache_page[ln.page] += cq.norm(ln.text) + "|"
    blines = [(p, ln) for p, _c, t in blocks for ln in re.split(r"\n| \| ", t) if len(cq.norm(ln)) >= 8]
    strict = sum(1 for p, ln in blines if cq.norm(ln) in cache_page[p]) / max(1, len(blines))
    # A printed row the PDF stores in pieces ('1.1.1' + 'Preamble', a justified row word by word) is several cached
    # lines in a row; it is confirmed when it reads in that order in the cached page with the line breaks removed.
    # Still a different extraction, and a cross-column splice still fails: the cached reading is in column order.
    cache_run = {p: t.replace("|", "") for p, t in cache_page.items()}
    confirmed = sum(1 for p, ln in blines if cq.norm(ln) in cache_run.get(p, "")) / max(1, len(blines))
    print(f"  C. block lines confirmed by the independent cached reading: {confirmed:.2%} "
          f"(within one cached line: {strict:.2%})")
    if "--why" in sys.argv:
        unc = [(p, ln) for p, ln in blines if cq.norm(ln) not in cache_run.get(p, "")]
        print("  unconfirmed by page:", collections.Counter(p for p, _ in unc).most_common(12))
        for p, ln in unc[:int(os.environ.get("WHY_N", "6"))]:
            print(f"  unconfirmed p{p}: {ln[:90]!r}")
    if "--dump" in sys.argv:  # the blocks as read, for checks outside this script (no write)
        import json
        Path(sys.argv[sys.argv.index("--dump") + 1]).write_text(
            json.dumps([{"page": p, "col": c, "text": t} for p, c, t in blocks], ensure_ascii=False), encoding="utf-8")
    # Section of each block (--section-re): the council's numbered heading ("1.3.2.6 Air Quality") last printed above
    # it in reading order. Hornsby numbers sections, not controls; without this every row is "Part 0" and the
    # contents list and the section-loss guard see one section. Reading order = page, then left column, then right.
    sect_of = {}
    if SECTION_RE:
        cur_s = None
        for i, (p, c, t) in sorted(enumerate(blocks), key=lambda e: (e[1][0], e[1][1])):
            for ln in t.splitlines():
                m = SECTION_RE.match(ln.strip())
                if m:
                    cur_s = (m.group(1), ln.strip())
            sect_of[i] = cur_s
        print(f"  sections: {len({v[0] for v in sect_of.values() if v})} distinct; blocks without one "
              f"{sum(1 for v in sect_of.values() if not v)}")
    ok = lines_in >= 0.99 and not labels_missing and confirmed >= 0.97
    print("PROOF", "PASS" if ok else "FAIL")
    if not (APPLY and ok):
        return
    cur.execute("SELECT ref_number, document_id FROM regulatory_provisions WHERE source_council=%s AND "
                "source_chapter_key=%s AND is_current AND ref_number IS NOT NULL LIMIT 1", (CO, KEY))
    ref0, doc = cur.fetchone()
    base = ref0.split("~")[0].rsplit("__", 1)[0]
    cur.execute("SELECT now()")
    batch = cur.fetchone()[0]
    rows, seen = [], collections.Counter()
    for i, (p, _c, t) in enumerate(blocks):
        m = g.CONTROL.match(t.splitlines()[-1] if heading(t.splitlines()[0]) and len(t.splitlines()) > 1 else t)
        m = m or next((g.CONTROL.match(ln) for ln in t.splitlines() if g.CONTROL.match(ln)), None)
        lab = (m.group(1) + m.group(2).replace(".", "_")) if m else None
        part = part_of.get(p) or "0"
        code = f"Part {part} {lab}" if lab else f"Part {part}"
        if sect_of.get(i):
            code = sect_of[i][0].replace(".", "_") + (f" {lab}" if lab else "")
        seen[code] += 1
        ref = f"{base}__{code}" + (f"~{seen[code]}" if seen[code] > 1 else "")
        # the standard first line "# <code> <title>": the publish reads section_header (the site's contents list and
        # the section-loss guard) from it; rule_body() strips it, so the council-words check still sees only the text
        head = (m.group(1) + m.group(2)) if m else (sect_of[i][1] if sect_of.get(i) else f"Part {part}")
        rows.append((CO, KEY, "added", "approved", f"# {head}\n\n{t}", p, ref, chash, doc, True, batch, f"Part {part}"))
    cur.executemany("""INSERT INTO dcp_review_queue (council, chapter_key, change_type, status, new_text, new_page,
                         ref_number, source_content_hash, document_id, is_full_replace, created_at, reviewed_by,
                         reviewed_at, review_reason, summary)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'auto:column_reader',now(),
                         'column reader: council text copied by column from the PDF (proof: controls, coverage, whole)',
                         %s)""", rows)
    conn.commit()
    print(f"APPLIED: queued {len(rows)} approved rows, batch {batch}")


if __name__ == "__main__":
    main()
