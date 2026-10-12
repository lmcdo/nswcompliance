"""Copy each served council DCP rule's quote from the council's own PDF. Dry run only.

prior-art-checked: nothing copies a council's text back out of its PDF.
`dcp_fidelity_gate.ground_row` checks a row's words and numbers are printed;
`citation_proof` proves its clause number; `dcp_page_repair` / `rule_page_locator`
find its page. All three compare lowercased tokens and write no text. The
full-quote probe (~/.claude/plans/ce-council-words-probes/full_quote_probe.py)
measured the gap this closes: 4,552 of 19,627 served quotes are not printed word
for word (plan: ~/.claude/plans/ce-council-words-PLAN-2026-10-12.md).

THE STATES (per rule)
---------------------
exact          the whole stored quote is printed, in order (spacing, punctuation and
               line breaks ignored). The council's text over that span is copied,
               with its own casing and punctuation.
recovered      the quote is not printed whole, but its opening and closing words are,
               close together: the council's text between them is copied. Or only
               the opening is printed, at a label ("(b)", "C3", "2.1"): copied from
               that label to the next label of the same kind.
not_a_control  map labels or a figure caption, not a rule.
unconfirmed    none of the above; `reason` says why. Numbers from these are never used.

Matching runs on the cached lowercase lines (citation_proof cache) in both reading
orders. The cache is lowercased, so each line's original text is re-read from the
same PDF with PyMuPDF and joined back by position (page, y, x).

Usage:
    python scripts/council_quote.py --dry-run [--council waverley] [--ids 1,2] [--out f.json]
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

CACHE = Path(os.environ.get("TEMP", "/tmp")) / "dq111_lines"
ALNUM = set("abcdefghijklmnopqrstuvwxyz0123456789")
MIN_CHARS = 25          # a shorter quote matches by chance; exact only on its own page or once
ANCHOR = 6              # words in an opening/closing anchor
ANCHOR_SLIDE = 25       # anchors may start this many words into the quote (a running header first)
SPAN_MIN, SPAN_MAX = 0.5, 2.0   # copied span length vs stored quote length
MIN_OVERLAP = 0.6       # share of the stored quote's words the copied text must hold
LABEL_LINES = 40        # a label-bounded copy stops after this many lines...
LABEL_PAGES = 1         # ...or this many page breaks
REPEATED = 5           # a line printed on this many pages is a running header/footer at a copy's edge
OVERSIZED = 2500        # a stored quote this long is several controls: flag for splitting
KNOWN = (126292, 87150, 95878, 105200, 130236, 150954)

_WORD = re.compile(r"[a-z0-9]+")
#: Typesetting ligatures PDFs print as one character: "speciﬁcations" is "specifications".
LIGATURES = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
                           "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"})
_NUM = re.compile(r"\d+(?:\.\d+)?")
_FIGURE = re.compile(r"^\s*(?:figure|fig\.|map|diagram)\s*\d", re.I)
#: A label at a line start, by kind. Kinds must match for a label to end a copy.
_LABELS = (
    ("paren_alpha", re.compile(r"^\(([a-z])\)")),
    ("paren_roman", re.compile(r"^\(((?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii))\)")),
    ("paren_num", re.compile(r"^\((\d{1,2})\)")),
    ("alpha_dot", re.compile(r"^([a-z])[.)]\s")),
    ("num_dot", re.compile(r"^(\d{1,2})[.)]\s")),
    ("code", re.compile(r"^([a-z]{1,3}\d+[a-z]?)(?![\w.])")),
    ("dotted", re.compile(r"^(\d+(?:\.\d+)+)(?![\d.]*\d)")),
)


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").translate(LIGATURES).lower())


def label_kind(text: str) -> tuple[str, str] | None:
    """(kind, depth key) of a label opening this line, else None. Roman before alpha: "(i)"."""
    t = text.strip().lower()
    for kind, rx in (_LABELS[1], _LABELS[0]) + _LABELS[2:]:
        m = rx.match(t)
        if m:
            key = m.group(1)
            if kind == "code":
                key = re.match(r"[a-z]+", key).group(0)      # C3 and C4 are one kind; O1 another  # noqa: zone-codes (DCP control labels)
            elif kind == "dotted":
                key = str(key.count("."))                    # 2.1 and 2.2 are one depth
            else:
                key = ""
            return kind, key
    return None


# -- the council's lines, with their own casing ----------------------------------

def cased_text(pdf_path: str) -> dict:
    """(page, y, x, lowercased text) -> the line as printed. Same join as read_raw_lines."""
    import fitz
    out = {}
    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc, 1):
            for block in page.get_text("dict")["blocks"]:
                for ln in block.get("lines") or []:
                    t = " ".join(s["text"] for s in ln["spans"]).strip()
                    if t:
                        out[(pno, ln["bbox"][1], ln["bbox"][0], t.lower())] = t
    return out


def load_chapter(r2_path: str):
    """Both readings (citation_proof.ChapterLines) and the cased-text map for one chapter PDF."""
    import citation_proof as cp
    import dq_probe_section_code_not_in_source as probe
    local = CACHE / "pdf" / (probe._cache_file(CACHE, r2_path).stem + ".pdf")
    if not local.exists():
        import dcp_page_repair as dpr
        local.parent.mkdir(parents=True, exist_ok=True)
        dpr._s3().download_file(os.environ["R2_BUCKET_NAME"], r2_path, str(local))
    lf = probe._cache_file(CACHE, r2_path)
    if not lf.exists():
        lines, width = cp.read_raw_lines(str(local))
        lf.write_text(json.dumps({"width": width, "lines": [[x.page, x.y, x.x, x.text] for x in lines]}),
                      encoding="utf-8")
    data = json.loads(lf.read_text(encoding="utf-8"))
    readings = cp.both_orders([cp.Line(*x) for x in data["lines"]], data["width"])
    return readings, cased_text(str(local))


class Stream:
    """One reading as a normalized character stream; each character knows its line and offset."""

    def __init__(self, ch, cased: dict):
        self.lines = ch.lines
        self.text = [cased.get((ln.page, ln.y, ln.x, ln.text), ln.text).translate(LIGATURES)
                     for ln in ch.lines]
        self.cased_share = sum(1 for ln in ch.lines if (ln.page, ln.y, ln.x, ln.text) in cased) / max(1, len(ch.lines))
        # Lines whose printed casing was not re-read. A picture label named by OCR ("c3") has no
        # text layer and is short; anything longer must not be passed off as the council's text.
        self.uncased = {i for i, ln in enumerate(ch.lines)
                        if (ln.page, ln.y, ln.x, ln.text) not in cased and len(norm(ln.text)) > 4}
        buf, self.at = [], []
        for i, t in enumerate(self.text):
            for p, c in enumerate(t):
                for c2 in c.lower():
                    if c2 in ALNUM:
                        buf.append(c2)
                        self.at.append((i, p))
        self.s = "".join(buf)
        # A running header/footer/banner: the same line at the same spot on REPEATED+ pages.
        # Position matters: Leichhardt repeats real control wording per site, at varying heights.
        spot = collections.defaultdict(set)
        for ln in ch.lines:
            spot[(ln.text, round(ln.y / 5), round(ln.x / 5))].add(ln.page)
        self.repeated = {k[0] for k, ps in spot.items()
                         if len(ps) >= REPEATED and not label_kind(k[0])}   # "(a)" sits at one spot too
        # Numbers in the lines the reading dropped (page margins, page numbers): "2012", "2.9-7".
        kept = {(ln.page, ln.y, ln.x, ln.text) for ln in ch.lines}
        self.margin_nums = collections.defaultdict(set)
        self.furniture_words = collections.defaultdict(set)   # margins + running headers, per page
        for key in cased:
            if key not in kept:
                self.margin_nums[key[0]].update(_NUM.findall(key[3]))
                self.furniture_words[key[0]].update(_WORD.findall(key[3].translate(LIGATURES)))
        for ln in ch.lines:
            if ln.text in self.repeated:
                self.furniture_words[ln.page].update(_WORD.findall(ln.text.translate(LIGATURES)))

    def casing_unread(self, k0: int, k1: int) -> bool:
        return any(i in self.uncased for i in range(self.at[k0][0], self.at[k1][0] + 1))

    def furniture(self, pages) -> set:
        return set().union(*(self.furniture_words[p] for p in pages))

    def page(self, k: int) -> int:
        return self.lines[self.at[k][0]].page

    def find_all(self, q: str, cap: int = 60) -> list[int]:
        out, k = [], self.s.find(q)
        while k != -1 and len(out) < cap:
            out.append(k)
            k = self.s.find(q, k + 1)
        return out

    def copy(self, k0: int, k1: int) -> str:
        """The council's text from stream char k0 to k1 inclusive, lines joined by newlines.
        A running header or footer (a line printed on REPEATED+ pages) is trimmed from either
        end -- Ashfield prints its chapter banner sideways mid-page, beyond any margin."""
        (i0, p0), (i1, p1) = self.at[k0], self.at[k1]
        first, last = self.text[i0], self.text[i1]
        while p0 > 0 and first[p0 - 1] in "(\"'“‘[":
            p0 -= 1
        while p1 + 1 < len(last) and (last[p1 + 1] in ".;:)%\"'”’]" or last[p1 + 1].isalpha()):
            p1 += 1
        if i0 == i1:
            return first[p0:p1 + 1]
        parts = [(i0, first[p0:])] + [(i, self.text[i]) for i in range(i0 + 1, i1)] + [(i1, last[:p1 + 1])]
        while len(parts) > 1 and self.lines[parts[0][0]].text in self.repeated:
            parts.pop(0)
        while len(parts) > 1 and self.lines[parts[-1][0]].text in self.repeated:
            parts.pop()
        return "\n".join(t for _i, t in parts)

    def copy_from_label(self, k0: int) -> tuple[str, int] | None:
        """From the label opening k0's line (or the label line just above) to before the next
        label of the same kind. None when no label is there."""
        i0 = self.at[k0][0]
        start = None
        for i in (i0, i0 - 1):
            if i >= 0 and (lk := label_kind(self.text[i])):
                start = i
                break
        if start is None:
            return None
        end, breaks = start, 0
        for i in range(start + 1, min(len(self.text), start + LABEL_LINES)):
            if self.lines[i].page != self.lines[i - 1].page:
                breaks += 1
                if breaks > LABEL_PAGES:
                    break
            if label_kind(self.text[i]) == lk or self.lines[i].text.startswith(("figure ", "table ")):
                break
            end = i
        if any(i in self.uncased for i in range(start, end + 1)):
            return None
        return "\n".join(self.text[start:end + 1]), self.lines[start].page


# -- one rule ---------------------------------------------------------------------

def overlap(stored: str, copied: str) -> float:
    a = collections.Counter(_WORD.findall(stored.lower()))
    b = collections.Counter(_WORD.findall(copied.lower()))
    return sum((a & b).values()) / max(1, sum(a.values()))


def missing_numbers(stored: str, copied: str) -> list[str]:
    have = set(_NUM.findall(copied))
    return sorted({n for n in _NUM.findall(stored) if n not in have})


def is_map_labels(body: str) -> bool:
    toks = _WORD.findall(body.lower())
    return len(toks) >= 20 and sum(1 for t in toks if len(t) == 1 and t.isalpha()) / len(toks) >= 0.3


def judge(row: dict, streams: list[Stream]) -> dict:
    import rule_page_locator as rpl
    body = rpl.rule_body(row["provision_text"])
    q = norm(body)
    out = {"id": row["id"], "council": row["source_council"], "stored_page": row["pdf_page"],
           "page_check": row["page_check"], "needs_split": len(body) > OVERSIZED}
    if is_map_labels(body) or _FIGURE.match(body):
        return {**out, "status": "not_a_control", "reason": "map_labels" if is_map_labels(body) else "figure_caption"}
    if len(body) > OVERSIZED:      # several controls in one row: the brief refuses it until split
        return {**out, "status": "unconfirmed", "reason": "oversized"}
    if not any(st.s for st in streams):
        return {**out, "status": "unconfirmed", "reason": "no_text_in_pdf"}

    # exact: the whole quote printed in order
    places = [(st, k) for st in streams for k in st.find_all(q)] if q else []
    pages = {st.page(k) for st, k in places}
    if places and (len(q) >= MIN_CHARS or len(pages) == 1 or row["pdf_page"] in pages):
        st, k = next(((s, k) for s, k in places if s.page(k) == row["pdf_page"]), places[0])
        if st.casing_unread(k, k + len(q) - 1):
            return {**out, "status": "unconfirmed", "reason": "casing_unread"}
        text = st.copy(k, k + len(q) - 1)
        return {**out, "status": "exact", "reason": "one_place" if len(pages) == 1 else f"places:{len(pages)}",
                "quote_page": st.page(k), "quote": text}
    if len(q) < MIN_CHARS:
        return {**out, "status": "unconfirmed", "reason": "too_short" if not places else "too_short_many_places"}

    # recovered: opening and closing words printed close together
    toks = rpl.tokens(body)
    if len(toks) < ANCHOR + 1:
        return {**out, "status": "unconfirmed", "reason": "not_found_short"}
    best = None
    for st in streams:
        starts = None
        for j in range(0, min(ANCHOR_SLIDE, len(toks) - ANCHOR) + 1):
            hits = st.find_all("".join(toks[j:j + ANCHOR]))
            if hits:
                starts = (j, hits)
                break
        if not starts:
            continue
        ends = None
        for j in range(len(toks) - ANCHOR, max(len(toks) - ANCHOR - ANCHOR_SLIDE, starts[0]) - 1, -1):
            a = "".join(toks[j:j + ANCHOR])
            hits = st.find_all(a)
            if hits:
                ends = (j, [h + len(a) - 1 for h in hits])
                break
        for s in starts[1]:
            for e in (ends[1] if ends else []):
                span = e - s + 1
                if not (SPAN_MIN * len(q) <= span <= SPAN_MAX * len(q)) or st.page(e) - st.page(s) > 2:
                    continue
                score = (st.page(s) != row["pdf_page"], abs(span - len(q)))
                if best is None or score < best[0]:
                    best = (score, st, s, e, starts[0], len(toks) - ANCHOR - ends[0])
    if best:
        _sc, st, s, e, head_cut, tail_cut = best
        if st.casing_unread(s, e):
            return {**out, "status": "unconfirmed", "reason": "casing_unread"}
        text = st.copy(s, e)
        ov = overlap(body, text)
        # Words cut from either end must be page furniture: a cut footer ("Sydney DCP 2012 2.9-7")
        # or banner is fine; a cut table row ("Capacity: 300") or opening sentence is not.
        pages = range(st.page(s) - 1, st.page(e) + 2)
        furniture = st.furniture(pages)
        cut = toks[:head_cut] + (toks[len(toks) - tail_cut:] if tail_cut else [])
        real = [t for t in cut if t not in furniture]
        if real:
            lost = sorted({t for t in real if any(c.isdigit() for c in t)})
            return {**out, "status": "unconfirmed", "reason": "values_cut" if lost else "words_cut",
                    "lost_numbers": lost, "cut_words": real[:12]}
        if ov >= MIN_OVERLAP:
            return {**out, "status": "recovered", "reason": "anchors", "quote_page": st.page(s),
                    "quote": text, "overlap": round(ov, 3), "head_cut_words": head_cut,
                    "tail_cut_words": tail_cut,
                    # the complete council text between two printed anchors lacks these: the stored
                    # row's numbers, not the council's. Phase C uses only numbers in the quote.
                    "missing_numbers": [n for n in missing_numbers(body, text)
                                        if not any(n in st.margin_nums[p] for p in pages)]}
        return {**out, "status": "unconfirmed", "reason": "low_overlap", "overlap": round(ov, 3)}

    # recovered: opening only, bounded by the council's own labels
    for st in streams:
        hits = st.find_all("".join(toks[:ANCHOR]))
        hits.sort(key=lambda k: st.page(k) != row["pdf_page"])
        for k in hits:
            got = st.copy_from_label(k)
            if got:
                text, page = got
                ov = overlap(body, text)
                near = range(page - 1, page + 3)
                gone = [n for n in missing_numbers(body, text) if not any(n in st.margin_nums[p] for p in near)]
                if gone:   # a label-bounded copy can stop short of a value: never recovered then
                    return {**out, "status": "unconfirmed", "reason": "values_missing", "lost_numbers": gone}
                if ov >= MIN_OVERLAP and len(norm(text)) <= SPAN_MAX * len(q):
                    return {**out, "status": "recovered", "reason": "label_bounded", "quote_page": page,
                            "quote": text, "overlap": round(ov, 3), "missing_numbers": []}
    found = sum(1 for st in streams for _ in st.find_all("".join(toks[:ANCHOR]), cap=1))
    return {**out, "status": "unconfirmed", "reason": "opening_found_no_bound" if found else "not_found"}


def chapter(args) -> tuple[list[dict], str | None]:
    r2_path, rows = args
    from dotenv import load_dotenv
    load_dotenv(ROOT.parents[2] / ".env" if (ROOT.parents[2] / ".env").exists() else ROOT / ".env")
    try:
        readings, cased = load_chapter(r2_path)
    except Exception as e:  # noqa: BLE001 -- one bad PDF must not stop the fleet
        return [{"id": r["id"], "council": r["source_council"], "stored_page": r["pdf_page"],
                 "page_check": r["page_check"], "needs_split": False, "status": "unconfirmed",
                 "reason": "pdf_unreadable", "source_path": r2_path,
                 "text_md5": hashlib.md5((r["provision_text"] or "").encode("utf-8")).hexdigest()}
                for r in rows], f"{r2_path}: {e}"[:200]
    streams = [Stream(ch, cased) for ch in readings]
    note = None
    if min(st.cased_share for st in streams) < 0.9:
        note = f"{r2_path}: only {min(st.cased_share for st in streams):.0%} of lines re-read with casing"
    out = []
    for r in rows:
        res = judge(r, streams)
        res["source_path"] = r2_path
        res["text_md5"] = hashlib.md5((r["provision_text"] or "").encode("utf-8")).hexdigest()
        out.append(res)
    return out, note


def fetch(council: str | None, ids: list[int] | None) -> list[dict]:
    import psycopg2
    import dcp_page_repair as dpr
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        conn.cursor().execute("SET statement_timeout = 30000")
        rows = dpr.fetch(conn, council)
    finally:
        conn.close()
    return [r for r in rows if not ids or r["id"] in ids]


def write(res: list[dict]) -> int:
    """Store each verdict (migration 111). One transaction per chapter, by primary key, and only
    where the rule's text is still the text that was judged -- a row edited meanwhile keeps NULL,
    which the nightly check reports. Returns rows written."""
    import psycopg2
    from psycopg2.extras import execute_values
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup = ROOT / "data" / "db_rollback_backups" / f"regulatory_provisions_pre_council_quote_{stamp}.csv"
    backup.parent.mkdir(parents=True, exist_ok=True)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = 30000")
        cur.execute("SELECT id, council_quote, quote_page, quote_source_path, quote_status, quote_reason, "
                    "quote_checked_at FROM regulatory_provisions WHERE id = ANY(%s)", ([r["id"] for r in res],))
        with backup.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur.fetchall())
        conn.commit()
        print(f"backup: {backup}")
        by = collections.defaultdict(list)
        for r in res:
            usable = r["status"] in ("exact", "recovered")
            by[r["source_path"]].append((
                r["id"], r["text_md5"], (r["quote"].replace("\x00", "") if usable else None),
                r.get("quote_page") if usable else None, r["source_path"] if usable else None,
                r["status"], r["reason"], r["source_path"]))
        cur.execute("SELECT now()")
        started = cur.fetchone()[0]
        for _path, vals in by.items():
            # Only while the PDF judged is still the chapter's active one: a new PDF in between
            # voids quotes (migration 111), and this must not write the old PDF's back.
            # prior-art-checked: tightens this module's own writer; no other writer of these columns.
            execute_values(cur, """
                UPDATE regulatory_provisions rp
                   SET council_quote = v.q, quote_page = v.pg, quote_source_path = v.src,
                       quote_status = v.st, quote_reason = v.why, quote_checked_at = now()
                  FROM (VALUES %s) AS v(id, md5, q, pg, src, st, why, judged)
                  JOIN dcp_chapter_registry reg ON reg.r2_current_path = v.judged AND reg.is_active
                 WHERE rp.id = v.id AND md5(rp.provision_text) = v.md5 AND rp.is_current
                   AND reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key""",
                vals, template="(%s::int, %s, %s::text, %s::int, %s::text, %s, %s, %s)", page_size=500)
            conn.commit()
        # this run's writes only: an earlier run's stamp must not make a skipped row look stored
        cur.execute("SELECT count(*) FROM regulatory_provisions WHERE id = ANY(%s) AND quote_checked_at >= %s",
                    ([r["id"] for r in res], started))
        return cur.fetchone()[0]
    finally:
        conn.close()


def report(res: list[dict]) -> None:
    c = collections.Counter(r["status"] for r in res)
    print(f"rules: {len(res)}")
    for k in ("exact", "recovered", "not_a_control", "unconfirmed"):
        print(f"  {k:14s} {c.get(k, 0):6d}")
        for (s, why), n in sorted(collections.Counter((r["status"], r["reason"]) for r in res
                                                      if r["status"] == k).items(), key=lambda x: -x[1]):
            print(f"      {why:26s} {n:6d}")
    rec = [r for r in res if r["status"] == "recovered"]
    print(f"  recovered with a stored number not in the council's text: "
          f"{sum(1 for r in rec if r.get('missing_numbers'))}")
    print(f"  quote page differs from stored page (exact+recovered): "
          f"{sum(1 for r in res if r.get('quote_page') not in (None, r['stored_page']))}")
    print(f"  oversized (>{OVERSIZED} chars, several controls): {sum(1 for r in res if r['needs_split'])}")
    print("by council (unconfirmed / total):")
    tot = collections.Counter(r["council"] for r in res)
    unc = collections.Counter(r["council"] for r in res if r["status"] == "unconfirmed")
    for k, n in sorted(tot.items(), key=lambda x: -unc[x[0]])[:12]:
        print(f"  {k:22s} {unc[k]:5d} / {n}")
    for r in res:
        if r["id"] in KNOWN:
            print(f"--- known {r['id']} {r['council']}: {r['status']} ({r['reason']}) "
                  f"page {r.get('quote_page')} (stored {r['stored_page']}) overlap {r.get('overlap')} "
                  f"missing {r.get('missing_numbers')} split {r['needs_split']}")
            if r.get("quote"):
                print("    " + r["quote"][:500].replace("\n", "\n    "))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="judge and report; write nothing")
    mode.add_argument("--apply", action="store_true", help="also store each verdict (migration 111)")
    ap.add_argument("--council")
    ap.add_argument("--ids", help="comma-separated rule ids")
    ap.add_argument("--out", default=str(Path(os.environ.get("CLAUDE_JOB_DIR", ROOT)) / "tmp" / "council_quote_dryrun.json"))
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    from dotenv import load_dotenv
    load_dotenv(ROOT.parents[2] / ".env" if (ROOT.parents[2] / ".env").exists() else ROOT / ".env")
    ids = [int(x) for x in a.ids.split(",")] if a.ids else None
    rows = fetch(a.council, ids)
    by = collections.defaultdict(list)
    for r in rows:
        by[r["r2_current_path"]].append(r)
    res = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for out, note in ex.map(chapter, list(by.items())):
            if note:
                print("NOTE", note)
            res += out
    report(res)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res), encoding="utf-8")
    print(f"written: {a.out}")
    if a.apply:
        n = write(res)
        print(f"stored: {n} of {len(res)} rules")
        return 0 if n == len(res) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
