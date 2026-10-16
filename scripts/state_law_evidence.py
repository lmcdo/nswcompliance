#!/usr/bin/env python3
"""Deterministic, evidence-recording proof that a stored state-law rule is a contiguous span of the law.

prior-art-checked: extends scripts/state_law_recopy.py (same unit classes and HTML walker idea) and
state_law_proof.py (snapshot cache + manifest). Those pick a unit by a >= 90% word-run share and judge it with
several checks; this module has ONE exact test per rule and records enough to re-derive the verdict later
(scripts/verify_state_law_evidence.py). No model call, no randomness, no clock.

Versions (written into every evidence record; the verifier refuses a record whose version it does not know):
  NORMALISER  sl-norm/1    char-level: NFKC, dashes/quotes folded, nbsp -> space, markdown marks and zero-width
                           chars dropped, every whitespace run -> one space, ends trimmed.
  PARSER      sl-units/1   the snapshot's HTML cut into text units (clause / sub-clause / paragraph / note / table,
                           by the id the legislation HTML carries) and containers (chapter / part / division /
                           subdivision / schedule), each with [start, end) offsets in the normalised instrument D.
  MATCHERS    sl-excerpt/1, sl-adjacent/1, sl-part/1  (rules 1, 2, 3 below).

The comparison form of a text is its normalised form with all spaces removed ("squash"): layout differences in
spaces ('m 2' / 'm2') do not matter, but a match must start and end on a word boundary of D, so a row can never
match from the middle of a word. A proven span is D[start:end]; the verifier checks squash(D[start:end]) ==
squash(row). Tier 'exact' = character-identical, otherwise 'space-insensitive'.

Rules (a row needs >= MIN_WORDS words; ambiguity always means UNPROVEN):
  1 EXCERPT    exactly one occurrence in the instrument, inside a text unit; the proof names the smallest unit
               containing it and the offsets inside that unit's normalised text.
  2 ADJACENT   exactly one occurrence, inside no single text unit, equal to the concatenation of 2..MAX_ADJ
               consecutive units in document order (one space apart); the proof names each unit.
  3 PART       several occurrences; the old PDF page the row came from prints a Part/Division/Schedule heading;
               exactly one occurrence lies inside that container.
  4 UNPROVEN   everything else, with a reason.
"""
from __future__ import annotations

import bisect
import hashlib
import html
import re
import unicodedata
from array import array
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "law_text_cache"

NORMALISER = "sl-norm/1"
PARSER = "sl-units/1"
M_EXCERPT, M_ADJACENT, M_PART = "sl-excerpt/1", "sl-adjacent/1", "sl-part/1"
KNOWN = {"normaliser": {NORMALISER}, "parser": {PARSER}, "matcher": {M_EXCERPT, M_ADJACENT, M_PART}}

MIN_WORDS = 8
MAX_ADJ = 40

TEXT_UNITS = {"frag-clause", "frag-subclause", "frag-li", "frag-note", "frag-table"}
CONTAINERS = {"frag-chapter": "Chapter", "frag-part": "Part", "frag-division": "Division",
              "frag-subdivision": "Subdivision", "frag-schedule": "Schedule", "frag-clausegroup": "Group"}
BLOCK_TAGS = {"div", "blockquote", "p", "tr", "li", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5", "h6", "br"}
CELL_TAGS = {"td", "th"}
VOID_TAGS = {"br", "img", "meta", "link", "hr", "input", "col", "area", "base", "wbr"}
SKIP_CLASSES = {"frag-historynote"}   # 's 57: Am 2023 (83)' amendment history: editorial, not operative words

_FOLD = {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-", "‘": "'", "’": "'",
         "“": '"', "”": '"', "´": "'", "`": "", "*": "", "_": "", "|": " ", "­": ""}


# ----------------------------------------------------------------------------------------------- normaliser
def _emit_for(ch: str) -> str:
    if ch in _FOLD:
        return _FOLD[ch]
    if ch.isspace():
        return " "
    if ord(ch) < 128:
        return ch
    if unicodedata.category(ch) == "Cf":
        return ""
    c = unicodedata.normalize("NFKC", ch)
    return "".join(" " if x.isspace() else _FOLD.get(x, x) for x in c)


def normalise_with_map(raw: str):
    """(D, smap, emap). smap[i] = offset in D of the first emitted char at/after raw[i]; emap[i] = offset in D just
    after the last emitted char before raw[i]. Both have len(raw)+1 entries."""
    out: list[str] = []
    n = 0
    pending = False
    emap = array("i", [0]) * (len(raw) + 1)
    first = array("i", [-1]) * (len(raw) + 1)
    for i, ch in enumerate(raw):
        emap[i] = n
        for c in _emit_for(ch):
            if c == " ":
                pending = True
                continue
            if pending and n:
                out.append(" ")
                n += 1
            pending = False
            if first[i] == -1:
                first[i] = n
            out.append(c)
            n += 1
    emap[len(raw)] = n
    first[len(raw)] = n
    nxt = n
    for i in range(len(raw), -1, -1):     # backward fill: next emitted char at/after i
        if first[i] == -1:
            first[i] = nxt
        else:
            nxt = first[i]
    return "".join(out), first, emap


def normalise(text: str) -> str:
    return normalise_with_map(text)[0] if text else ""


def row_norm(text: str) -> str:
    """Normalised form of a STORED row: its leading '# title' line, html tags, entities, markdown marks removed."""
    t = text or ""
    s = t.lstrip()
    if s.startswith("#"):
        nl = s.find("\n")
        t = s[nl + 1:] if nl != -1 else ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)", "", t)
    for ch in "*_#":
        t = t.replace(chr(92) + ch, ch)
    t = re.sub(r"^\s*#+\s*", "", t, flags=re.M)
    return normalise(t)


def squash(s: str) -> str:
    return s.replace(" ", "")


def n_words(s: str) -> int:
    return len(s.split())


def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------------- parser
class _Walker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pieces: list[str] = []
        self.pos = 0
        self.stack: list[tuple[str, dict | None, bool]] = []
        self.items: list[dict] = []
        self.skip = 0
        self.dead = 0

    def _emit(self, s: str) -> None:
        if self.skip or self.dead:
            return
        self.pieces.append(s)
        self.pos += len(s)

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            if tag == "br":
                self._emit("\n")
            return
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        uid = a.get("id")
        item = None
        kinds = classes & (TEXT_UNITS | set(CONTAINERS))
        if uid and kinds and not self.skip:
            item = {"id": uid, "cls": sorted(kinds)[0], "rs": self.pos, "re": None}
            self.items.append(item)
        skip = bool(classes & SKIP_CLASSES)
        if skip:
            self.skip += 1
        if tag in ("script", "style"):
            self.dead += 1
        if tag in BLOCK_TAGS:
            self._emit("\n")
        elif tag in CELL_TAGS:
            self._emit(" ")
        self.stack.append((tag, item, skip))

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self._emit("\n")

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        idx = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if idx is None:
            return
        while len(self.stack) > idx:
            t, item, skip = self.stack.pop()
            if t in BLOCK_TAGS:
                self._emit("\n")
            elif t in CELL_TAGS:
                self._emit(" ")
            if item is not None:
                item["re"] = self.pos
            if skip:
                self.skip -= 1
            if t in ("script", "style"):
                self.dead -= 1

    def handle_data(self, data):
        self._emit(data)


@dataclass
class Item:
    id: str
    cls: str
    start: int          # offsets in D
    end: int
    parent: int         # index into Snapshot.items, -1 = none
    heading: str = ""   # containers: 'Part 2 Development for affordable housing'


@dataclass
class Snapshot:
    epi: str
    sha256: str
    D: str
    items: list
    S: str = field(repr=False, default="")
    sidx: array = field(repr=False, default=None)
    by_id: dict = field(repr=False, default_factory=dict)
    starts: list = field(repr=False, default_factory=list)


def parse_snapshot(epi: str, raw_bytes: bytes) -> Snapshot:
    w = _Walker()
    w.feed(raw_bytes.decode("utf-8", errors="replace"))
    w.close()
    raw = "".join(w.pieces)
    D, smap, emap = normalise_with_map(raw)
    items: list[Item] = []
    for it in w.items:
        if it["re"] is None:
            continue
        s, e = smap[it["rs"]], emap[it["re"]]
        if e <= s:
            continue
        head = ""
        if it["cls"] in CONTAINERS:
            lines = [ln for ln in raw[it["rs"]:it["re"]].split("\n") if ln.strip()]
            head = normalise(lines[0])[:120] if lines else ""
        items.append(Item(it["id"], it["cls"], s, e, -1, head))
    items.sort(key=lambda x: (x.start, -x.end))
    stack: list[int] = []
    for k, x in enumerate(items):
        while stack and not (items[stack[-1]].start <= x.start and x.end <= items[stack[-1]].end):
            stack.pop()
        x.parent = stack[-1] if stack else -1
        stack.append(k)
    snap = Snapshot(epi, hashlib.sha256(raw_bytes).hexdigest(), D, items)
    snap.sidx = array("i", [i for i, ch in enumerate(D) if ch != " "])
    snap.S = squash(D)
    for k, x in enumerate(items):
        snap.by_id.setdefault(x.id, k)
    snap.starts = [x.start for x in items]
    return snap


def find_snapshot_file(epi: str, sha256: str, cache: Path = CACHE) -> Path | None:
    """The cached file for `epi` whose bytes hash to `sha256` (pinned by hash, never by file name)."""
    for f in sorted(cache.glob(f"{epi}_*.html")) + sorted((cache / "pit").glob(f"{epi}_*.html")):
        if hashlib.sha256(f.read_bytes()).hexdigest() == sha256:
            return f
    return None


def load_snapshot(epi: str, sha256: str, cache: Path = CACHE) -> Snapshot:
    f = find_snapshot_file(epi, sha256, cache)
    if f is None:
        raise FileNotFoundError(f"no cached snapshot of {epi} with sha256 {sha256}")
    return parse_snapshot(epi, f.read_bytes())


# ----------------------------------------------------------------------------------------------- matching
def _edge_ok(ch: str) -> bool:
    return ch == " " or not (ch.isalnum() or ch in "-'/%")


def word_aligned(D: str, s: int, e: int) -> bool:
    """The span does not begin or end inside a word: the neighbouring char is a space or sentence punctuation."""
    return (s == 0 or _edge_ok(D[s - 1])) and (e == len(D) or _edge_ok(D[e]))


def occurrences(snap: Snapshot, rnorm: str) -> list[tuple[int, int]]:
    """Every [start, end) in D whose squash equals squash(rnorm), starting and ending on a word boundary of D (word_aligned)."""
    q = squash(rnorm)
    out: list[tuple[int, int]] = []
    if not q:
        return out
    D, sidx = snap.D, snap.sidx
    i = snap.S.find(q)
    while i != -1:
        s, e = sidx[i], sidx[i + len(q) - 1] + 1
        if word_aligned(D, s, e):
            out.append((s, e))
        i = snap.S.find(q, i + 1)
    return out


def deepest_text_unit(snap: Snapshot, s: int, e: int) -> int:
    """Index of the smallest TEXT unit containing [s, e), or -1."""
    k = bisect.bisect_right(snap.starts, s) - 1
    while k != -1:
        x = snap.items[k]
        if x.start <= s and e <= x.end and x.cls in TEXT_UNITS:
            return k
        k = x.parent   # every item containing [s, e) is an ancestor-or-self of the last item starting <= s
    return -1


def unit_tile(snap: Snapshot, s: int, e: int) -> list[int] | None:
    """Consecutive text units (outermost at each step, one space apart) tiling exactly [s, e), or None."""
    by_start: dict[int, list[int]] = {}
    k = bisect.bisect_left(snap.starts, s)
    while k < len(snap.items) and snap.items[k].start < e:
        if snap.items[k].cls in TEXT_UNITS and snap.items[k].end <= e:
            by_start.setdefault(snap.items[k].start, []).append(k)
        k += 1
    pos, out = s, []
    while pos < e:
        cands = by_start.get(pos)
        if not cands:
            return None
        k = max(cands, key=lambda c: snap.items[c].end)
        out.append(k)
        pos = snap.items[k].end
        if pos < e:
            if snap.D[pos] != " ":
                return None
            pos += 1
    return out if 2 <= len(out) <= MAX_ADJ else None


def _tier(span_text: str, rnorm: str) -> str:
    return "exact" if span_text == rnorm else "space-insensitive"


def _base(snap: Snapshot) -> dict:
    return {"epi": snap.epi, "snapshot_sha256": snap.sha256, "normaliser": NORMALISER, "parser": PARSER}


def _excerpt(snap: Snapshot, rnorm: str, s: int, e: int, k: int, rule: int, matcher: str) -> dict:
    u = snap.items[k]
    return {**_base(snap), "status": "proven", "rule": rule, "matcher": matcher,
            "units": [{"id": u.id, "cls": u.cls, "start": s - u.start, "end": e - u.start,
                       "unit_chars": u.end - u.start}],
            "abs_start": s, "abs_end": e, "tier": _tier(snap.D[s:e], rnorm), "whole_unit": (s == u.start and e == u.end)}


def prove(snap: Snapshot, rnorm: str) -> dict:
    """Rules 1 and 2 on a NORMALISED row. status: proven | ambiguous (carries `spans`, for rule 3) | unproven."""
    if n_words(rnorm) < MIN_WORDS:
        return {**_base(snap), "status": "unproven", "rule": 4, "reason": "too_short"}
    occ = occurrences(snap, rnorm)
    if not occ:
        return {**_base(snap), "status": "unproven", "rule": 4, "reason": "not_contiguous_in_instrument"}
    if len(occ) > 1:
        units = {deepest_text_unit(snap, s, e) for s, e in occ}
        if len(units) == 1 and -1 not in units:
            return {**_base(snap), "status": "unproven", "rule": 4, "reason": "repeats_inside_one_unit"}
        return {**_base(snap), "status": "ambiguous", "rule": 4, "reason": "occurs_in_several_places", "spans": occ}
    s, e = occ[0]
    k = deepest_text_unit(snap, s, e)
    if k != -1:
        return _excerpt(snap, rnorm, s, e, k, 1, M_EXCERPT)
    tile = unit_tile(snap, s, e)
    if tile is not None:
        parts = [{"id": snap.items[t].id, "cls": snap.items[t].cls, "start": 0,
                  "end": snap.items[t].end - snap.items[t].start} for t in tile]
        return {**_base(snap), "status": "proven", "rule": 2, "matcher": M_ADJACENT, "units": parts,
                "abs_start": s, "abs_end": e, "tier": _tier(snap.D[s:e], rnorm), "whole_unit": True}
    return {**_base(snap), "status": "unproven", "rule": 4, "reason": "inside_no_unit_and_not_unit_aligned"}


def containers_holding(snap: Snapshot, s: int, e: int, kinds=("frag-part", "frag-division", "frag-schedule")) -> list[int]:
    """Containers of the given classes holding [s, e), outermost first."""
    out = []
    k = bisect.bisect_right(snap.starts, s) - 1
    while k != -1:
        x = snap.items[k]
        if x.cls in kinds and x.start <= s and e <= x.end:
            out.append(k)
        k = x.parent
    return out[::-1]


def prove_in_container(snap: Snapshot, rnorm: str, container_id: str) -> dict | None:
    """Rule 3 core: proven iff exactly one occurrence of the row lies inside `container_id` and inside a text unit."""
    k = snap.by_id.get(container_id)
    if k is None or n_words(rnorm) < MIN_WORDS:
        return None
    c = snap.items[k]
    inside = [(s, e) for s, e in occurrences(snap, rnorm) if c.start <= s and e <= c.end]
    if len(inside) != 1:
        return None
    s, e = inside[0]
    u = deepest_text_unit(snap, s, e)
    if u == -1:
        return None
    ev = _excerpt(snap, rnorm, s, e, u, 3, M_PART)
    ev["container_id"], ev["container_heading"] = c.id, c.heading
    return ev


def prove_by_page_heading(snap: Snapshot, rnorm: str, page_text: str) -> dict | None:
    """Rule 3: `page_text` is the text of the old PDF page the row came from. Keep the Part/Division/Schedule
    containers that hold an occurrence AND whose heading ('Part 2 Development for ...') is printed on that page;
    proven iff every such container leads to the same single occurrence. Evidence gets the heading found."""
    if n_words(rnorm) < MIN_WORDS:
        return None
    occ = occurrences(snap, rnorm)
    if len(occ) < 2:
        return None
    page = " " + normalise(page_text) + " "
    cands = {}
    for s, e in occ:
        for k in containers_holding(snap, s, e):
            h = snap.items[k].heading
            if h and (" " + h + " ") in page:
                cands[snap.items[k].id] = h
    found = {}
    for cid, h in sorted(cands.items()):
        r = prove_in_container(snap, rnorm, cid)
        if r:
            found.setdefault((r["abs_start"], r["abs_end"]), (r, h))
    if len(found) != 1:
        return None
    r, h = next(iter(found.values()))
    r["pdf"] = {"page_heading_text": h}
    return r
