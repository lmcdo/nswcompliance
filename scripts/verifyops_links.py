"""Daily council-list check: compare today's list of document links with the last good one.

prior-art-checked: r2_monitor.diff_urls compares hub links with the REGISTRY (which chapter moved,
which is gone, which hub link matches no chapter). It cannot say what changed on the PAGE since
yesterday, because nothing stored yesterday's page. This module does only that: normalise each link,
fingerprint the list, and diff two lists. Unmatched new links are still registered by
r2_monitor._auto_register_chapter; that row (registration_status='auto_detected') stays the review
item and the dedupe state (resolution 10), so no alert table is added here.

Spec: ~/.claude/plans/ce-verifyops-v5-SPEC-2026-10-22.md, v6 resolutions 6, 7, 10 and 12.
Pure functions only; no network, no database.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

#: Query keys that only bust caches. Every OTHER key is kept, because several councils name the
#: document in the query itself: canada_bay `...content/?id=folder-7719479&streamId=...` and
#: liverpool `kapish-api/document?id=290103.2016`. Dropping the whole query (the v6 wording) would
#: fold every one of those links into one.
CACHE_BUSTER_KEYS = frozenset({"v", "ver", "version", "t", "ts", "timestamp", "cb", "_", "itok", "h",
                               "rev", "modified", "download", "dl", "inline"})

#: Drupal appends _0, _1 ... when a file of the same name is uploaded again.
_REUPLOAD = re.compile(r"_(\d{1,2})(\.[a-z0-9]{2,5})$", re.IGNORECASE)

#: More than this share of a council's links changing in one day = the page was redesigned.
REDESIGN_SHARE = 1 / 3
#: ...and at least this many links changed. Bayside lists 7 documents and canada_bay 8 (measured
#: 2026-10-22), so without a floor one new edition on a small page would read as a redesign.
REDESIGN_MIN_LINKS = 5

_DRAFT = re.compile(r"\b(drafts?|exhibitions?|exhibited|proposed|consultations?|have your say)\b",
                    re.IGNORECASE)
_NUMBER = re.compile(r"\b(part|chapter|section|schedule|appendix)\s*([a-z]?\d+(?:\.\d+)*[a-z]?)\b",
                     re.IGNORECASE)


def normalise_href(href: str) -> tuple[str, str]:
    """Return (normalised link, the same link without a trailing `_N` before the extension).

    Lower-cases scheme and host, drops the fragment and cache-buster query keys, sorts the rest,
    decodes the path and strips a trailing slash. The `_N` suffix is NOT removed from the key:
    `dcp_part_3.pdf` is a chapter number as often as it is Drupal's third upload. diff_lists only
    calls it a re-upload when the suffix-free name is the link that left the page.
    """
    parts = urlsplit((href or "").strip())
    path = unquote(parts.path).rstrip("/") or "/"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                             if k.lower() not in CACHE_BUSTER_KEYS))
    scheme, host = parts.scheme.lower(), parts.netloc.lower()
    norm = urlunsplit((scheme, host, path, query, ""))
    m = _REUPLOAD.search(path)
    base = urlunsplit((scheme, host, path[: m.start()] + m.group(2), query, "")) if m else norm
    return norm, base


def normalise_text(text: str | None) -> str:
    """Link text compared lower-cased with whitespace collapsed."""
    return " ".join((text or "").split()).lower()


def link_entries(discovered: list[dict]) -> list[dict]:
    """Scraper output -> stored list entries, one per normalised link, sorted, de-duplicated."""
    seen: dict[str, dict] = {}
    for d in discovered:
        norm, base = normalise_href(d.get("url") or "")
        if norm in seen:
            continue
        seen[norm] = {"href": d.get("url"), "norm": norm, "base": base,
                      "text": normalise_text(d.get("label")), "chapter_key": d.get("chapter_key")}
    return [seen[k] for k in sorted(seen)]


def fingerprint(entries: list[dict]) -> str:
    """sha256 over the sorted normalised links. Equal lists give equal fingerprints."""
    return hashlib.sha256("\n".join(sorted(e["norm"] for e in entries)).encode()).hexdigest()


def is_draft(text: str | None, href: str | None = None) -> bool:
    """Words that mean 'not in force yet'. Labelled, never suppressed."""
    return bool(_DRAFT.search(f"{text or ''} {unquote(href or '')}"))


def chapter_number(text: str | None) -> str | None:
    """'Part 4 Residential' -> 'part 4'; 'Chapter 7.3' -> 'chapter 7.3'. None when there is none."""
    m = _NUMBER.search(text or "")
    return f"{m.group(1).lower()} {m.group(2).lower()}" if m else None


def held_match(text: str | None, held: dict[str, str]) -> str | None:
    """The held chapter a new link most likely replaces: EXACT chapter-number match only.

    `held` maps chapter_key -> chapter_label. Returns a key only when exactly one held chapter carries
    the same number; a fuzzy label match would pair "City East" with "City West" (#1430).
    """
    num = chapter_number(text)
    if not num:
        return None
    hits = [k for k, label in held.items() if chapter_number(label) == num]
    return hits[0] if len(hits) == 1 else None


def _plan_key(text: str | None) -> str:
    t = (text or "").lower().replace("development control plan", "dcp")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def plan_match(text: str | None, plans: list[str] | tuple[str, ...]) -> str | None:
    """A link titled with the whole plan's name AND year, e.g. "Bayside Development Control Plan 2022
    - Amendment 2" for "Bayside DCP 2022". Measured 2026-10-22: Bayside lists its new edition this
    way, with no part number, so the chapter-number match alone never fires there."""
    key = _plan_key(text)
    hits = [p for p in plans if re.search(r"\d{4}", p or "") and _plan_key(p) and _plan_key(p) in key]
    return hits[0] if len(hits) == 1 else None


def likely_replaces(text: str | None, held: dict[str, str], plans=()) -> str | None:
    """What a new link most likely replaces: one held chapter, or the whole named plan."""
    key = held_match(text, held)
    if key:
        return key
    plan = plan_match(text, plans)
    return f"the whole plan ({plan})" if plan else None


@dataclass
class ListDiff:
    new: list[dict] = field(default_factory=list)
    gone: list[dict] = field(default_factory=list)
    reuploads: list[dict] = field(default_factory=list)
    redesigned: bool = False
    first_scan: bool = False


def diff_lists(previous: list[dict] | None, current: list[dict]) -> ListDiff:
    """Today's list against the last list read OK.

    previous None = first scan: everything is saved, nothing is new (the setup run never alerts).
    A re-upload is a new link whose name, without its `_N` suffix, is a link that left the page
    (`x.pdf` -> `x_0.pdf`). It is reported separately and is neither new nor gone.
    """
    if previous is None:
        return ListDiff(first_scan=True)
    prev = {e["norm"]: e for e in previous}
    cur = {e["norm"]: e for e in current}
    new = {k: cur[k] for k in cur.keys() - prev.keys()}
    gone = {k: prev[k] for k in prev.keys() - cur.keys()}
    reup = {k for k, e in new.items() if e.get("base", k) != k and e["base"] in gone}
    replaced = {new[k]["base"] for k in reup}
    out = ListDiff(
        new=[new[k] for k in sorted(new) if k not in reup],
        gone=[gone[k] for k in sorted(gone) if k not in replaced],
        reuploads=[new[k] for k in sorted(reup)],
    )
    changed = len(out.new) + len(out.gone)
    out.redesigned = changed >= REDESIGN_MIN_LINKS and changed / max(len(prev), len(cur), 1) > REDESIGN_SHARE
    return out


def alert_lines(council: str, diff: ListDiff, held: dict[str, str],
                gone_alive: dict[str, bool] | None = None, plans=()) -> list[str]:
    """What to tell a person. A redesign is ONE line, but a new link matching a held chapter still
    gets its own line (resolution 6), so a real new edition is never hidden by the redesign.

    `gone_alive` maps a gone link's norm to whether its file still fetches. Delisted is not gone
    (#1188): a dead file is an alert, a live one is only "possibly repealed or replaced" (7), and a
    link not probed says so rather than guessing.
    """
    if diff.first_scan:
        return []
    lines: list[str] = []
    new = diff.new
    if diff.redesigned:
        lines.append(f"[{council}] page redesigned: {len(diff.new)} new, {len(diff.gone)} gone links "
                     f"- check the scraper")
        new = [e for e in diff.new if likely_replaces(e["text"], held, plans)]
    for e in new:
        match = likely_replaces(e["text"], held, plans)
        tag = " (draft, not in force)" if is_draft(e["text"], e["href"]) else ""
        likely = f" - may replace {match}" if match else ""
        lines.append(f"[{council}] new document{tag}: {e['text'] or '(no title)'} {e['href']}{likely}")
    for e in diff.reuploads:
        lines.append(f"[{council}] possible re-upload: {e['text'] or '(no title)'} {e['href']}")
    if not diff.redesigned:
        alive = gone_alive or {}
        for e in diff.gone:
            state = alive.get(e["norm"])
            what = ("removed and the file no longer opens" if state is False
                    else "taken off the page; file still opens - possibly repealed or replaced" if state
                    else "taken off the page; file not checked")
            lines.append(f"[{council}] {what}: {e['text'] or '(no title)'} {e['href']}")
    return lines
