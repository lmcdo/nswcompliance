"""Publish guard: a new version of a chapter must not lose the area links its live rules have.

prior-art-checked: dcp_supersede_guard guards sections, legibility and fidelity, not who a rule reaches. Area links
(v2_precinct_id, v2_marker, v2_applicable_zones) are not stored in the queue: derive_precinct_keys / gate_rules
re-make them after publish from written rules. A link that came from no rule (keyed by hand) or from a rule the
new text no longer fits (a page map, a number pattern) is silently dropped by a full replace. Measured in the
section-reader pilot 2026-10-14: Waverley 4 of 89 Part E links would have survived, Leichhardt C2 124 of 1,009.

Call `before = linked_count(...)` before the swap and `enforce(...)` after it, inside the same uncommitted
transaction: a refusal raises, the caller rolls back and keeps the approval (as the section-loss guard does).
"""
from __future__ import annotations

#: The new version must re-link at least this share of the links the live chapter had.
KEEP_MIN = 0.9
#: Below this many live links the share is too noisy to judge; small chapters are not refused.
MIN_LINKED = 5

_LINKED_SQL = """
SELECT count(*) FROM regulatory_provisions
 WHERE is_current AND source_council = %s AND source_chapter_key = %s
   AND (v2_precinct_id IS NOT NULL OR v2_marker IS NOT NULL
        OR (v2_applicable_zones IS NOT NULL AND NOT (v2_applicable_zones && ARRAY['ALL']::text[])))"""


class AreaLinkLossRefused(Exception):
    """The new version would leave rules that are limited to part of a council shown to the whole council."""


def linked_count(cur, council: str, chapter_key: str) -> int:
    """Current rows of the chapter that carry an area link (precinct, heritage/condition marker, zone limit)."""
    cur.execute(_LINKED_SQL, (council, chapter_key))
    return cur.fetchone()[0]


def fill_parts(cur, council: str, chapter_key: str, tagger=None) -> int:
    """Set v2_dcp_part on the chapter's current rows that have none, with the tagger enrichment uses after publish.

    The Part is what Waverley's precinct rule (column_copy of v2_dcp_part) and its heritage gate rule (Part B8) key
    on, but enrichment fills it only AFTER the commit, so inside the transaction every new row had none and this
    guard predicted 0 of 126 links (2026-10-15) while the published version would carry 1,028 Part E rows. Filling
    it here with the same LayerTopicTagger.tag gives the guard what publish will produce; enrichment later selects
    v2_dcp_layer IS NULL rows and writes the same Part. Returns rows filled."""
    if tagger is None:
        try:
            from enrichment.pipeline import LayerTopicTagger
        except ImportError as exc:   # the guard then sees fewer links and refuses: the safe direction
            print(f"    [area-link] Part not filled ({exc}); the guard judges the rows as they are")
            return 0
        tagger = LayerTopicTagger()
    cur.execute("""SELECT id, document_id, provision_text FROM regulatory_provisions
                    WHERE is_current AND source_council = %s AND source_chapter_key = %s
                      AND v2_dcp_part IS NULL AND provision_text IS NOT NULL""", (council, chapter_key))
    filled = 0
    for rid, doc, text in cur.fetchall():
        part = tagger.tag(doc, text)[1]
        if part:
            cur.execute("UPDATE regulatory_provisions SET v2_dcp_part = %s WHERE id = %s", (part, rid))
            filled += 1
    return filled


def relinkable_count(cur, council: str, chapter_key: str) -> int:
    """Current rows of the chapter that the publish-time rules WILL link: a precinct rule that derives a key for the
    row, or a gate rule whose selector matches it. Read-only; runs the same selectors and _derive as publish."""
    try:
        import derive_precinct_keys as dpk
        import gate_rules as gr
    except ImportError:                       # invoked as scripts.dcp_commit_approved
        from scripts import derive_precinct_keys as dpk
        from scripts import gate_rules as gr
    linked: set[int] = set()
    for rule in dpk.RULES:
        if rule["council"] != council:
            continue
        cur.execute(
            f"""SELECT id, document_id, ref_number, pdf_page, source_chapter_key, v2_precinct_id, v2_dcp_layer,
                       v2_dcp_part, provision_text
                  FROM regulatory_provisions
                 WHERE is_current = true AND source_council = %(council)s AND source_chapter_key = %(key)s
                   AND ({rule['where']})""",
            {"council": council, "key": chapter_key, **dict(rule.get("params") or {})})
        cols = [d[0] for d in cur.description]
        for r in cur.fetchall():
            row = dict(zip(cols, r))
            if dpk._derive(rule["strategy"], row):
                linked.add(row["id"])
    for rule in gr.GATE_RULES:
        if rule["council"] != council:
            continue
        cur.execute(
            f"""SELECT id FROM regulatory_provisions
                 WHERE is_current = true AND source_council = %(council)s AND source_chapter_key = %(key)s
                   AND ({rule['where']})""", {"council": council, "key": chapter_key})
        linked.update(r[0] for r in cur.fetchall())
    return len(linked)


def judge(before: int, after: int) -> bool:
    """True when the new version keeps enough area links. Pure."""
    return before < MIN_LINKED or after >= KEEP_MIN * before


def enforce(cur, council: str, chapter_key: str, before: int, allowed: frozenset = frozenset()) -> int:
    """Raise AreaLinkLossRefused when the chapter as it now stands (in this transaction) would be re-linked for too
    few rules. Returns the re-linkable count."""
    after = relinkable_count(cur, council, chapter_key)
    if judge(before, after):
        return after
    msg = (f"{council}/{chapter_key}: live had {before} rules linked to an area (precinct, marker or zone); the new "
           f"version would be re-linked for {after} ({after / max(1, before):.0%}, need {KEEP_MIN:.0%}). The rest "
           f"would reach every house in the council.")
    if f"{council}/{chapter_key}" in allowed:
        print(f"    [area-links] ALLOWED by --allow-area-link-loss: {msg}")
        return after
    raise AreaLinkLossRefused("REFUSED: " + msg
                              + f" If intended, re-run with --allow-area-link-loss {council}/{chapter_key}")
