"""Section reader: the model marks where each rule starts and ends; the program copies the council's words.

prior-art-checked: ai_extractor asks a model to RETYPE every rule, so a rule's words are only as exact as the model's
copy, and it reads blind 12-page chunks that cut sections in half. This reader keeps ai_extractor's output shape
(provisions -> provisions_to_sections) and reads the PDF's lines exactly as council_quote proves them
(citation_proof.read_raw_lines + both_orders + council_quote.cased_text + Stream), so a copied rule is the council's
words by construction. Design and measurements: ~/.claude/plans/ce-section-reader-DESIGN-2026-10-14.md.

How it works:
  1. lines   -- every printed line of the chapter, in reading order, with its page; running heads and page numbers out.
  2. pieces  -- consecutive lines up to PIECE_LINES, cut at a heading-like line where one exists, so a rule is not
                split; each piece repeats the last CONTEXT_LINES of the one before, marked as already read.
  3. read    -- the model gets numbered lines and returns ONLY line numbers: headings, and rules as
                {first, last, label, lead_in}. All pieces at once.
  4. build   -- the program joins the lines first..last (the council's words), files each rule under the headings
                above it (the heading lines are printed, by construction), carries a ':' lead-in to its items, and
                checks the boundary rules: in range, no overlap, a rule starting mid-sentence joins the one before,
                and every rule-worded line ends up in a rule or a heading (else it is reported as uncovered).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

# Its neighbours (citation_proof, council_quote, page_coverage, ai_extractor) import each other by bare name, and
# dcp_extract_changed puts only the repo root on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

PIECE_LINES = int(os.getenv("SECTION_READER_PIECE_LINES", "220"))
CONTEXT_LINES = 12
PARALLEL = max(1, int(os.getenv("SECTION_READER_PARALLEL", "8")))
MODEL = os.getenv("SECTION_READER_MODEL", "deepseek/deepseek-v3.2")
LABELS = {"objective", "control", "definition", "note"}
_HEADING = re.compile(r"^\s*(?:part\s+|section\s+|chapter\s+)?[A-Z]?\d+(?:\.\d+)*[A-Z]?\.?\s+\S", re.I)
_PAGE_NO = re.compile(r"^\s*(?:page\s+)?[\dA-Z]{0,3}[-.]?\d{1,4}\s*$", re.I)
_CONDITION = re.compile(r"^\s*(?:where|unless|provided that|except|and|or|but|if)\b", re.I)
_ITEM = re.compile(r"^\s*(?:\(?[a-z]{1,4}[.)]|\(?\d{1,2}[.)]|[A-Z]{1,2}\d{1,2}(?:\.\d+)?|[•\-–])\s+")

PROMPT = """You are marking up a page range of an Australian council Development Control Plan (DCP).
Each line is given as [n] text. Do NOT rewrite any words. Answer with LINE NUMBERS only.

Return JSON: {"headings": [{"line": n, "level": 1-4}], "rules": [{"first": n, "last": n, "label": "...", "lead_in": n or null}]}

headings: lines that are section or sub-section headings (e.g. "4.3 Parking", "Controls", "Objectives",
"C3 Fencing"). level 1 = biggest. Not running page headers, not table or figure captions.

rules: every provision the council states, each as the run of lines from its first to its last line.
- label "objective": an aim, usually under an Objectives heading (often O1, O.1, a)).
- label "control": a requirement, standard, development control or acceptable solution (must, shall, is to be,
  should, minimum, maximum, not permitted, a table row that sets a value).
- label "definition": a defined term. label "note": a note that only explains or refers elsewhere.
- Each numbered or lettered item is its own rule. A sentence ending ":" that introduces items is NOT a rule on its
  own: give its line as "lead_in" on each item it introduces.
- A condition ("where...", "unless...", "provided that...") belongs to the rule it qualifies: keep it inside that
  rule's line range.
- A table row that sets a value is a rule (its first to last line).
- Leave out: contents lists, page headers and footers, captions that only name a figure, history and amendment tables,
  background text that asks nothing of a development.
Lines marked (already read) are context from the previous range: do not return rules that end on them."""


def docling_lines(pdf_path: str) -> list[tuple[int, str]]:
    """(page, text) from Docling's layout model: paragraphs, list items and headings in its reading order, and each
    table row as "cell | cell". The words are the PDF's text layer (OCR off), so they are still the council's.
    Trial line source (SECTION_READER_LINES=docling), scored on the 100-page answer key against chapter_lines."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    opts = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    doc = conv.convert(str(pdf_path)).document
    out: list[tuple[int, str]] = []
    for item, _level in doc.iterate_items():
        prov = getattr(item, "prov", None) or []
        page = prov[0].page_no if prov else (out[-1][0] if out else 1)
        label = str(getattr(item, "label", "")).lower()
        if "page_header" in label or "page_footer" in label:
            continue
        if "table" in label and hasattr(item, "data"):
            grid = item.data.grid or []
            for row in grid:
                cells = [c.text.strip() for c in row if c.text and c.text.strip()]
                if cells:
                    out.append((page, " | ".join(dict.fromkeys(cells))))
            continue
        text = (getattr(item, "text", "") or "").strip()
        if text:
            marker = (getattr(item, "marker", "") or "").strip()
            out.append((page, f"{marker} {text}".strip() if marker and not text.startswith(marker) else text))
    return out


def chapter_lines(pdf_path: str) -> list[tuple[int, str]]:
    """(page, text) for every printed line in reading order, as council_quote proves against; running heads and bare
    page numbers left out."""
    import citation_proof as cp
    import council_quote as cq
    raw, width = cp.read_raw_lines(str(pdf_path))
    cased = cq.cased_text(str(pdf_path))
    # The PDF's own order and top-to-bottom each fail somewhere (citation_proof.both_orders): top-to-bottom interleaves
    # a two-column page (Hornsby 3-14), the PDF's order can put a side heading after its text. Each page is taken in
    # the order whose sentences run on from line to line more often.
    per_order = []
    for reading in cp.both_orders(raw, width):
        st = cq.Stream(reading, cased)
        pages: dict[int, list[str]] = {}
        for ln, text in zip(st.lines, st.text):
            t = text.strip()
            if t and ln.text not in st.repeated and not _PAGE_NO.match(t):
                pages.setdefault(ln.page, []).append(t)
        per_order.append(pages)
    out = []
    for page in sorted(set(per_order[0]) | set(per_order[1])):
        best = max((o.get(page, []) for o in per_order), key=run_on)
        for t in best:
            # Campbelltown draws every line twice, one copy on top of the other (page_coverage), sometimes once with
            # its label and once without ("d) A BASIX ..." / "A BASIX ..."): keep one.
            if out and out[-1][0] == page and (out[-1][1] == t or (
                    _ITEM.sub("", out[-1][1]).strip() == _ITEM.sub("", t).strip()
                    and not (_ITEM.match(out[-1][1]) and _ITEM.match(t)))):   # "(a) X" and "(b) X" are two rules
                continue
            out.append((page, t))
    return out


def run_on(texts: list[str]) -> int:
    """How many lines continue the sentence of the line before (it does not end . ; : and the next starts lower-case).
    An interleaved two-column page breaks most of these. Pure."""
    return sum(1 for a, b in zip(texts, texts[1:])
               if not a.rstrip().endswith((".", ";", ":")) and b[:1].islower())


def pieces(lines: list[tuple[int, str]], size: int = PIECE_LINES) -> list[tuple[int, int, int]]:
    """(context_start, start, end) line ranges, end exclusive. Each piece ends just before a heading-like line when
    one sits in the last third of the window, so rules are not cut. Pure."""
    out, start = [], 0
    while start < len(lines):
        end = min(len(lines), start + size)
        if end < len(lines):
            for i in range(end, start + (2 * size) // 3, -1):
                if _HEADING.match(lines[i][1]) and len(lines[i][1]) < 90:
                    end = i
                    break
        out.append((max(0, start - CONTEXT_LINES), start, end))
        start = end
    return out


def numbered(lines, ctx: int, start: int, end: int) -> str:
    rows = []
    for i in range(ctx, end):
        mark = " (already read)" if i < start else ""
        rows.append(f"[{i}]{mark} p{lines[i][0]}: {lines[i][1]}")
    return "\n".join(rows)


def ask(text: str) -> dict:
    """One model call; the answer as a dict (empty on an unusable answer)."""
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("section_reader needs OPENROUTER_API_KEY")
    body = {"model": MODEL, "temperature": 0, "max_tokens": 16000, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": PROMPT + "\n\n" + text}]}
    for _attempt in range(2):
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            reply = json.load(r)
        content = (((reply.get("choices") or [{}])[0] or {}).get("message") or {}).get("content")
        try:
            d = json.loads(re.sub(r"^```(json)?|```$", "", (content or "").strip(), flags=re.M))
            if isinstance(d, dict) and isinstance(d.get("rules"), list):
                return d
        except (ValueError, TypeError):
            pass
    return {}


_NUM_HEADING = re.compile(r"^\s*(\d+(?:\.\d+){1,4})\s+[A-Z0-9][^.;:]{2,80}$")
_SHORT_TITLE = re.compile(r"^\s*[A-Z][A-Za-z,&/' -]{2,40}$")     # "Massing", "Building entries": no digits, no stop
TITLE_LEVEL = 9


_PART_HEADING = re.compile(r"^\s*(?:part|section|chapter|volume)\s+[A-Z0-9]{1,4}\b", re.I)


def numbered_level(text: str) -> int | None:
    """Level of a numbered heading from its number alone: "Part 4 ..." 1, "4.3 ..." 3, "9.8.5.1 ..." 5 (one more
    per dot, under any Part). None for anything else. Pure."""
    if _PART_HEADING.match(text) and len(text.split()) <= 10 and not text.rstrip().endswith("."):
        return 1
    m = _NUM_HEADING.match(text)
    return min(TITLE_LEVEL - 1, m.group(1).count(".") + 2) if m else None


def is_title(text: str, after: str) -> bool:
    """A short unnumbered title ("Massing", "Building entries"): four words or fewer, no full stop, and the next line
    starts something new (a capital or a label) rather than finishing this one's sentence. Pure."""
    return (bool(_SHORT_TITLE.match(text)) and len(text.split()) <= 4
            and bool(after[:1].isupper() or _ITEM.match(after) or _BARE_LABEL.match(after)))
_BARE_LABEL = re.compile(r"^\s*(?:[A-Z]{1,3}\d{1,3}(?:\.\d+)?|\(?[a-z]{1,3}\)|\d{1,2}\.)\s*$")
_NONE_HERE = re.compile(r"^\s*(?:nil|none|n/a|not applicable)\.?\s*$|^\s*there (?:are|is) no\b", re.I)
_OBJECTIVE_HEAD = re.compile(r"\b(objectives?|desired (?:future )?(?:outcomes?|character)|aims?|intent|purpose)\b", re.I)
_CONTROL_HEAD = re.compile(r"\b(controls?|development standards?|requirements?|acceptable solutions?|"
                           r"design (?:guidance|criteria)|provisions)\b", re.I)


_AIM = re.compile(r"^To\s+(?:[a-z]+\s+){0,2}?(?:provide|ensure|encourage|promote|protect|maintain|achieve|minimise|"
                  r"minimize|reduce|retain|enhance|improve|create|facilitate|support|allow|enable|increase|limit|manage|"
                  r"conserve|preserve|respect|reinforce|integrate|establish|avoid|control|maximise|recognise|"
                  r"accommodate|contribute|deliver|guide|identify|prevent|restrict|set|define|outline)\b")
_DUTY = re.compile(r"\b(?:must|shall|is to be|are to be|(?:is|are) required|(?:is|are) not required|"
                   r"(?:is|are) not permitted|not to exceed|minimum of|maximum of)\b", re.I)


_ROMAN = re.compile(r"^\s*\(?([ivx]{1,5})[.)]\s+")
_LETTER = re.compile(r"^\s*\(?([a-z])[.)]\s+")
_DIGIT = re.compile(r"^\s*\(?(\d{1,2})[.)]\s+")


def _item_kind(text: str) -> str | None:
    for kind, rx in (("roman", _ROMAN), ("digit", _DIGIT), ("letter", _LETTER)):
        if rx.match(text):
            return kind
    return None


def split_items(lines, r: dict) -> list[dict]:
    """One rule per top-level item, the same on every read (the model kept Marrickville 9.8.5.1 C2 i-v whole on one
    read and split it on the next). The top level is the kind of the first item line ("i." / "1." / "a."); a line of
    that kind starts a new rule, deeper items stay with their parent, and the lines before the first item become each
    part's lead-in. A rule with fewer than two top-level items is returned unchanged. Pure."""
    span = list(range(r["first"], r["last"] + 1))
    kinds = [(i, _item_kind(lines[i][1])) for i in span]
    first = next(((i, k) for i, k in kinds if k), None)
    if not first:
        return [r]
    top = [i for i, k in kinds if k == first[1]]
    if len(top) < 2 or first[0] == r["first"] and r.get("lead_in") is None and len(top) < 2:
        return [r]
    lead = r["lead_in"] if first[0] == r["first"] else first[0] - 1
    if first[0] != r["first"] and first[0] - r["first"] > 1:
        return [r]                                   # more than one lead-in line: keep the rule whole
    out = []
    for n, a in enumerate(top):
        b = (top[n + 1] - 1) if n + 1 < len(top) else r["last"]
        out.append({**r, "first": a, "last": b, "lead_in": lead,
                    "text": "\n".join(t for _p, t in lines[a:b + 1]), "page": lines[a][0]})
    return out


def heading_kind(heads: list[str]) -> str | None:
    """'objective' or 'control' from the nearest printed heading that names one (e.g. "Objectives", "Desired
    Outcome", "Controls"), searching up from the closest; None when no heading names either. Pure."""
    for h in reversed(heads):
        o, c = _OBJECTIVE_HEAD.search(h), _CONTROL_HEAD.search(h)
        if o and not c:
            return "objective"
        if c and not o:
            return "control"
    return None


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def build(lines, answers: list[tuple[tuple[int, int, int], dict]]) -> dict:
    """Rules as {code, title, text, page, label, first, last, section, lead_in} from the models' line numbers, plus
    the boundary report and the rule-worded lines no rule covers. Pure."""
    import page_coverage as pc
    heads: dict[int, int] = {}
    spans: dict[int, tuple[int, str, int | None]] = {}     # first -> (last, label, lead_in)
    for (_ctx, start, end), d in answers:
        for h in d.get("headings") or []:
            n, lvl = _int((h or {}).get("line")), _int((h or {}).get("level")) or 2
            if n is not None and start <= n < end:
                heads[n] = max(1, min(4, lvl))
        for r in d.get("rules") or []:
            a, b = _int((r or {}).get("first")), _int((r or {}).get("last"))
            lab = str((r or {}).get("label") or "control").lower()
            if a is None or b is None or not (start <= a <= b < end) or a in heads:
                continue
            spans.setdefault(a, (b, lab if lab in LABELS else "control", _int((r or {}).get("lead_in"))))
    # A short numbered line ("9.8.5.1 76 Wilford Street, Newtown") is a heading whatever the model said: the model
    # marked it on one read of Marrickville 9.8 and not on the next, and the rules' section number moved with it.
    for i, (_p, t) in enumerate(lines):
        lvl = numbered_level(t)
        if lvl:    # the number decides the level, not the model (it put 9.8.5.1 above 9.8.5 on one read)
            heads[i] = lvl
    # Every other heading's level is the program's too: a bare label ("C2") is never a heading, and an unnumbered
    # title ("Massing", "Controls") always sits below the numbered ones -- the model's levels for these varied by read
    # and pushed "9.8.5.1" out of the section path.
    for i in list(heads):
        if numbered_level(lines[i][1]):
            continue
        if _BARE_LABEL.match(lines[i][1]) or _ITEM.match(lines[i][1]):
            del heads[i]
        else:
            heads[i] = TITLE_LEVEL
    # A rule the model started on a heading, a short title or a bare margin label ("9.8.5.1 76 Wilford Street" /
    # "Massing" / "C1" / "Development must ...") starts after them: the heading files it, the title names it, and the
    # bare label numbers it (both found again below from the lines just before the rule).
    trimmed: dict[int, tuple[int, str, int | None]] = {}
    for a, (b, lab, lead) in spans.items():
        while a < b and (a in heads or _BARE_LABEL.match(lines[a][1]) or is_title(lines[a][1], lines[a + 1][1])):
            if not (a in heads or _BARE_LABEL.match(lines[a][1])):
                heads.setdefault(a, TITLE_LEVEL)             # below every numbered heading
            a += 1
        trimmed.setdefault(a, (b, lab, lead))
    spans = trimmed
    report = {"overlaps": 0, "joined_mid_sentence": 0, "lead_ins": 0, "label_from_heading": 0, "lead_ins_rejected": 0, "label_from_words": 0, "none_notes": 0}
    rules: list[dict] = []
    last_end = -1
    for a in sorted(spans):
        b, lab, lead = spans[a]
        if a <= last_end:
            # Overlap: the earlier rule keeps its lines and the later span is dropped whole -- trimming it would serve
            # a fragment missing its opening words. Lines it alone held are listed as uncovered.
            report["overlaps"] += 1
            continue
        first_text = lines[a][1]
        # A rule starting mid-sentence or with a bare condition belongs to the rule just before it.
        if (rules and a == rules[-1]["last"] + 1 and not _ITEM.match(first_text)
                and (first_text[:1].islower() or _CONDITION.match(first_text))
                and not rules[-1]["text"].rstrip().endswith((".", ";"))):
            rules[-1]["last"] = b
            rules[-1]["text"] += "\n" + "\n".join(t for _p, t in lines[a:b + 1])
            report["joined_mid_sentence"] += 1
            last_end = b
            continue
        if lead is None and a > 0 and lines[a - 1][1].rstrip().endswith(":") and _ITEM.match(first_text):
            lead = a - 1
        rules.append({"first": a, "last": b, "label": lab, "lead_in": lead,
                      "text": "\n".join(t for _p, t in lines[a:b + 1]), "page": lines[a][0]})
        last_end = b
    rules = [x for r in rules for x in split_items(lines, r)]
    # A lead-in the model also returned as a one-line rule of its own travels with its items instead.
    leads = {r["lead_in"] for r in rules if r["lead_in"] is not None}
    rules = [r for r in rules if not (r["first"] in leads and r["first"] == r["last"])]
    report["lead_ins"] = len(leads)
    hs = sorted(heads)
    inside_any = {i for r in rules for i in range(r["first"], r["last"] + 1)}
    # A section that says nothing applies ("Nil", "There are no Heritage Conservation Areas in the precinct") is kept
    # as a note: it tells the reader of an address that nothing of that kind applies, rather than leaving a gap.
    for h in hs:
        n = h + 1
        if n < len(lines) and n not in inside_any and n not in heads and _NONE_HERE.match(lines[n][1]):
            rules.append({"first": n, "last": n, "label": "note", "lead_in": None,
                          "text": lines[n][1], "page": lines[n][0]})
            inside_any.add(n)
            report["none_notes"] += 1
    rules.sort(key=lambda r: r["first"])
    for r in rules:
        path: dict[int, str] = {}
        for h in hs:
            if h >= r["first"]:
                break
            path = {k: v for k, v in path.items() if k < heads[h]}
            path[heads[h]] = lines[h][1]
        r["section"] = " > ".join(path[k] for k in sorted(path))
        lead = r["lead_in"]
        if lead is not None and not (0 <= lead < r["first"] and r["first"] - lead <= 40
                                     and lines[lead][1].rstrip().endswith(":")
                                     and not any(lead < h < r["first"] for h in hs)):
            report["lead_ins_rejected"] += 1
            lead = r["lead_in"] = None
        if lead is not None and lines[lead][1] not in r["text"]:
            r["text"] = lines[lead][1] + "\n" + r["text"]
        numbered_heads = [path[k] for k in sorted(path) if re.match(r"^\s*[A-Z]?\d", path[k])]
        m = re.match(r"^\s*([A-Z]?\d+(?:\.\d+)*[A-Z]?)", numbered_heads[-1]) if numbered_heads else None
        item = _ITEM.match(lines[r["first"]][1])
        label = item.group(0).strip().strip("().") if item else ""
        if not label:
            # A label printed on its own beside the text ("C1" in the margin, Marrickville 9.8.5.1) arrives as the
            # line just before the rule: it is the rule's number.
            for b in (r["first"] - 1, r["first"] - 2):
                if b >= 0 and b not in inside_any and _BARE_LABEL.match(lines[b][1]):
                    label = lines[b][1].strip().strip("().")
                    break
        if r["lead_in"] is not None:
            parent = _ITEM.match(lines[r["lead_in"]][1])
            plabel = parent.group(0).strip().strip("().") if parent else ""
            b = r["lead_in"] - 1
            if not plabel and b >= 0 and _BARE_LABEL.match(lines[b][1]):     # "C1" in the margin beside the lead-in
                plabel = lines[b][1].strip().strip("().")
            if plabel and plabel != label:
                label = f"{plabel} {label}".strip()        # Marrickville 9.8.5.1 C2 i, not a bare "i"
        parts = [m.group(1) if m else "", label]
        r["code"] = " ".join(x for x in parts if x) or f"L{r['first']}"
        r["title"] = path[max(path)] if path else ""
        # The label is proven by the printed heading above the rule when one names it; the model's guess otherwise.
        kind = heading_kind([lines[h][1] for h in hs if h < r["first"]][-3:])
        if kind and r["label"] in ("objective", "control"):
            report["label_from_heading"] += r["label"] != kind
            r["label"] = kind
        # The rule's own words outrank both the heading and the model: "To provide ..." is an aim wherever it is
        # printed (Woollahra prints objectives under a Controls heading); "shall", "is required", "must not" make a
        # requirement even when the model filed it as a note or an objective (Campbelltown 3.6.2.2 setbacks).
        body = _ITEM.sub("", lines[r["first"]][1]).strip()
        own = "objective" if _AIM.match(body) else "control" if _DUTY.search(r["text"]) else None
        if own and own != r["label"] and r["label"] in ("objective", "control", "note"):
            report["label_from_words"] += 1
            r["label"] = own
    inside: set[int] = set()
    for r in rules:
        inside.update(range(r["first"], r["last"] + 1))
        if r["lead_in"] is not None:
            inside.add(r["lead_in"])
    uncovered = [(i, p, t) for i, (p, t) in enumerate(lines)
                 if i not in inside and i not in heads and len(t.split()) >= 6 and pc.RULE_WORDS.search(t)]
    report["uncovered"] = len(uncovered)
    return {"rules": rules, "report": report, "uncovered": uncovered[:200]}


WINDOW = int(os.getenv("SECTION_READER_WINDOW", "8"))   # pages either side kept when reading part of a chapter: enough for running heads to repeat


def window_pdf(pdf_path: str, pages: tuple[int, int]) -> tuple[str, int]:
    """A temporary PDF of pages first-WINDOW..last+WINDOW, and the page offset to add back. Reading a 366-page chapter
    to look at 3 of its pages took 80 seconds; the window takes a few."""
    import tempfile
    import fitz
    with fitz.open(pdf_path) as doc:
        a, b = max(1, pages[0] - WINDOW), min(doc.page_count, pages[1] + WINDOW)
        sub = fitz.open()
        sub.insert_pdf(doc, from_page=a - 1, to_page=b - 1)
        path = tempfile.mktemp(suffix=".pdf")
        sub.save(path)
        sub.close()
    return path, a - 1


#: A page counts as a picture page when its pictures cover at least this share of it: the words a rule is printed in
#: may be drawn, not typed (City of Sydney 6.3-111 setbacks, Ku-ring-gai 14E precinct maps beside their objectives).
PICTURE_SHARE = 0.35


def picture_pages(pdf_path: str, pages: list[int]) -> list[int]:
    import fitz
    out = []
    with fitz.open(pdf_path) as doc:
        for p in pages:
            if not 1 <= p <= doc.page_count:      # a window past the last page
                continue
            pg = doc[p - 1]
            area = sum(fitz.Rect(i["bbox"]).get_area() for i in pg.get_image_info()
                       if min(fitz.Rect(i["bbox"]).width, fitz.Rect(i["bbox"]).height) >= 40)
            if area / max(1.0, pg.rect.get_area()) >= PICTURE_SHARE:
                out.append(p)
    return out


#: A page whose text layer is jumbled: justified text stored one word per line, columns interleaved (Campbelltown
#: Part 3 p23). At least this share of its lines are a single word.
SCRAMBLED_SHARE = 0.25


def scrambled_pages(lines: list[tuple[int, str]]) -> list[int]:
    """Pages whose text lines are mostly fragments, so they are read from the page image as well. Pure."""
    by: dict[int, list[str]] = {}
    for p, t in lines:
        by.setdefault(p, []).append(t)
    return [p for p, ts in by.items()
            if len(ts) >= 15 and sum(1 for t in ts if len(t.split()) <= 1) / len(ts) >= SCRAMBLED_SHARE]


def read_pictures(pdf_path: str, pages: list[int], have: list[str]) -> list[dict]:
    """Rules on picture pages read from the page itself by a vision model (ai_extractor's Mistral reader, never
    OpenAI). Its words are retyped, so each is marked source 'picture': the site shows it as the council's words only
    once council_quote proves it (text layer, or the OCR picture proof). Rules already found as text are skipped."""
    import io
    import ai_extractor as ax
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    norm = lambda t: "".join(re.findall(r"[a-z0-9]+", (t or "").lower()))   # noqa: E731
    seen = [norm(t) for t in have]
    out = []

    def one(p: int) -> tuple[int, list[dict]]:
        got = ax._call_and_parse_with_empty_retry("mistral", ax._subset_bytes(reader, p - 1, p), ax.PROMPT)
        return p, got

    done = 0
    results: dict[int, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=min(PARALLEL, max(1, len(pages)))) as pool:
        for p, got in pool.map(one, pages):        # map keeps page order
            results[p] = got
            done += 1
            print(f"    [section-reader] picture page {done}/{len(pages)} (p{p}): {len(got)} rules", flush=True)
    for p in pages:
        for prov in results[p]:
            body = norm(prov.get("text"))
            if len(body) < 8 or any(body[:60] in x or x[:60] in body for x in seen if x):
                continue
            seen.append(body)
            out.append({"first": None, "last": None, "label": "control", "lead_in": None, "section": "",
                        "text": str(prov.get("text") or ""), "page": p, "code": str(prov.get("code") or f"P{p}"),
                        "title": str(prov.get("title") or ""), "source": "picture"})
    return out


REREAD_NOTE = ("\n\nIMPORTANT: a previous reading left these lines out of every rule: {lines}. Each is part of a "
               "rule (or a lead-in or condition of one). Include every one of them in the rule it belongs to.")


def binding(text: str) -> bool:
    """A line written as an obligation (page_coverage._OBLIGATION: must, shall, is to be, is required, not
    permitted ...): the words that, left out of every rule, refuse a chapter -- as the page-coverage guard does."""
    import page_coverage as pc
    return bool(pc._OBLIGATION.search(text.lower()))


def recover_uncovered(lines, answers, out: dict) -> dict:
    """Re-read once each piece holding an obligation line no rule covers, naming those lines; then refuse the chapter
    (ai_extractor.PageLoss, which every caller already refuses on) if any is still in no rule. Lines with weaker rule
    words stay reported in out["uncovered"] only. Calls the model."""
    import ai_extractor as ax
    missing = [i for i, _p, t in out["uncovered"] if binding(t)]
    if not missing:
        return out
    todo = [k for k, ((_c, a, b), _d) in enumerate(answers) if any(a <= i < b for i in missing)]

    def reread(k: int):
        ctx, start, end = answers[k][0]
        mine = [i for i in missing if start <= i < end]
        return k, ask(numbered(lines, ctx, start, end) + REREAD_NOTE.format(lines=mine))

    again = list(answers)
    with ThreadPoolExecutor(max_workers=min(PARALLEL, max(1, len(todo)))) as pool:
        for n, (k, d) in enumerate(pool.map(reread, todo), 1):     # all at once, progress after each
            again[k] = (answers[k][0], d)
            print(f"    [section-reader] re-read {n}/{len(todo)} (p{lines[answers[k][0][1]][0]})", flush=True)
    redo = build(lines, again)
    redo["report"]["reread_pieces"] = sum(1 for (_c, a, b), _d in answers if any(a <= i < b for i in missing))
    still = [(i, p, t) for i, p, t in redo["uncovered"] if binding(t)]
    if still:
        raise ax.PageLoss(f"section_reader: {len(still)} obligation line(s) in no rule after a re-read, e.g. "
                          + "; ".join(f"p{p} '{t[:70]}'" for _i, p, t in still[:5])
                          + ". Refusing the chapter rather than serving it without them.")
    return redo


def read_chapter(pdf_path: str, pages: tuple[int, int] | None = None) -> dict:
    """Read a chapter PDF (optionally only pages first..last) and build its rules. Calls the models."""
    offset = 0
    path = pdf_path
    if pages:
        path, offset = window_pdf(pdf_path, pages)
    source = os.getenv("SECTION_READER_LINES", "").strip().lower()
    if source == "docling_modal":
        from docling_modal import remote_docling_lines as reader
    else:
        reader = docling_lines if source == "docling" else chapter_lines
    lines = [(p + offset, t) for p, t in reader(path)]
    if pages:
        lines = [x for x in lines if pages[0] <= x[0] <= pages[1]]
    ps = pieces(lines)
    from concurrent.futures import as_completed
    got: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=min(PARALLEL, max(1, len(ps)))) as pool:
        futs = {pool.submit(lambda p=p: ask(numbered(lines, *p))): k for k, p in enumerate(ps)}
        for n, fut in enumerate(as_completed(futs), 1):
            k = futs[fut]
            got[k] = fut.result()
            if len(ps) > 3:     # progress as each piece lands (never only at the end, never held up by a slow one)
                print(f"    [section-reader] piece {n}/{len(ps)} (p{lines[ps[k][1]][0]}): "
                      f"{len(got[k].get('rules') or [])} rules", flush=True)
    answers = [(ps[k], got[k]) for k in range(len(ps))]
    out = build(lines, answers)
    out = recover_uncovered(lines, answers, out)
    if pages:
        span = list(range(pages[0], pages[1] + 1))
    else:
        import fitz
        with fitz.open(pdf_path) as doc:
            span = list(range(1, doc.page_count + 1))      # a scanned page gives no text lines but can hold rules
    pics = sorted(set(picture_pages(pdf_path, [p for p in span if p >= 1])) | set(scrambled_pages(lines)))
    if pics:
        if not os.environ.get("MISTRAL_API_KEY"):
            raise RuntimeError(f"section_reader: {len(pics)} picture/jumbled page(s) {pics[:10]} need the vision reader "
                               "and MISTRAL_API_KEY is not set; refusing a chapter with those pages unread")
        out["rules"] += read_pictures(pdf_path, pics, [r["text"] for r in out["rules"]])
    out["picture_pages"] = pics
    out["pieces"] = len(ps)
    out["empty_answers"] = sum(1 for _p, d in answers if not d)
    return out


def to_sections(rules: list[dict]) -> list[dict]:
    """The pipeline's section dicts (ai_extractor.provisions_to_sections), so review queue and commit are unchanged."""
    import ai_extractor as ax
    sections = ax.provisions_to_sections([{"code": r["code"], "title": r["title"], "text": r["text"], "page": r["page"]}
                                          for r in rules])
    # Vision-retyped rules keep their mark. The site shows a rule as the council's words only once council_quote proves
    # it against the PDF (text layer or the OCR picture proof); this mark lets later steps tell them apart.
    for sec, r in zip(sections, [r for r in rules if str(r.get("code") or "").strip()]):
        sec["source"] = (r.get("source") or "text")
    return sections
