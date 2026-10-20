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

from typing import NamedTuple

#: The new version must re-link at least this share of the links the live chapter had.
KEEP_MIN = 0.9
#: Below this many live links the share is too noisy to judge; small chapters are not refused.
MIN_LINKED = 5

_LINKED_SQL = """
SELECT count(*) FILTER (WHERE v2_precinct_id IS NOT NULL OR v2_marker IS NOT NULL),
       count(*) FILTER (WHERE v2_precinct_id IS NULL AND v2_marker IS NULL
                          AND v2_applicable_zones IS NOT NULL
                          AND NOT (v2_applicable_zones && ARRAY['ALL']::text[]))
  FROM regulatory_provisions
 WHERE is_current AND source_council = %s AND source_chapter_key = %s"""


class Linked(NamedTuple):
    """A chapter's live area links, in two kinds that are re-made by different machines.

    area: a precinct or marker -- derive_precinct_keys / gate_rules re-make these from the written rules.
    zone: a zone limit and nothing else -- the chapter's applicability config re-applies these to every row
          (v2_zone_source 'config_specific'). Counted apart so one kind can never hide the loss of the other.
    """
    area: int
    zone: int


class AreaLinkLossRefused(Exception):
    """The new version would leave rules that are limited to part of a council shown to the whole council."""


def linked_count(cur, council: str, chapter_key: str) -> Linked:
    """Current rows of the chapter that carry an area link: (precinct or marker, zone limit only)."""
    cur.execute(_LINKED_SQL, (council, chapter_key))
    area, zone = cur.fetchone()
    return Linked(area, zone)


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


def relinkable_ids(cur, council: str, chapter_key: str) -> set:
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
    return linked


def config_zoned_ids(cur, council: str, chapter_key: str, tagger=None) -> set:
    """Current rows of the chapter that enrichment will give a zone limit from the chapter's applicability config.

    The AI re-read of Campbelltown Part 3 (2026-10-18) kept all 504 rules' zones -- enrichment re-applied its zones from
    the chapter config -- but this guard only predicted precinct/gate links, so it saw 0 and refused. Runs the same
    tag_with_provenance enrichment runs, and counts only a 'config_specific' answer: a zone read out of the rule's own
    prose (text_regex) is not counted, since a re-worded rule may no longer say it."""
    if tagger is None:
        try:
            from enrichment.extractors.applicability_tagger import ApplicabilityTagger
        except ImportError as exc:   # the guard then sees fewer links and refuses: the safe direction
            print(f"    [area-link] config zones not predicted ({exc})")
            return set()
        tagger = ApplicabilityTagger()
    cur.execute("""SELECT id, document_id, provision_text, v2_dcp_part, pdf_page FROM regulatory_provisions
                    WHERE is_current AND source_council = %s AND source_chapter_key = %s
                      AND provision_text IS NOT NULL""", (council, chapter_key))
    zoned = set()
    for rid, doc, text, part, page in cur.fetchall():
        zones, _devs, src = tagger.tag_with_provenance(text, doc, part=part, pdf_page=page)
        if src.get("zone_source") == "config_specific" and zones and "ALL" not in zones:
            zoned.add(rid)
    return zoned


def relinkable_count(cur, council: str, chapter_key: str) -> Linked:
    """What the publish-time machines will re-link: (precinct/gate rows, rows with any zone or area link)."""
    area = relinkable_ids(cur, council, chapter_key)
    return Linked(len(area), len(area | config_zoned_ids(cur, council, chapter_key)))


def judge(before: int, after: int) -> bool:
    """True when the new version keeps enough area links. Pure."""
    return before < MIN_LINKED or after >= KEEP_MIN * before


def enforce(cur, council: str, chapter_key: str, before: Linked, allowed: frozenset = frozenset()) -> Linked:
    """Raise AreaLinkLossRefused when the chapter as it now stands (in this transaction) would be re-linked for too
    few rules, judged separately for precinct/marker links and zone-only links. Returns the re-linkable counts."""
    after = relinkable_count(cur, council, chapter_key)
    if judge(before.area, after.area) and judge(before.zone, after.zone):
        return after
    msg = (f"{council}/{chapter_key}: live had {before.area} rules linked to a precinct or marker and {before.zone} "
           f"limited to zones only; the new version would be re-linked for {after.area} by the precinct/gate rules "
           f"and {after.zone} in all (need {KEEP_MIN:.0%} of each). The rest would reach every house in the council.")
    if f"{council}/{chapter_key}" in allowed:
        print(f"    [area-links] ALLOWED by --allow-area-link-loss: {msg}")
        return after
    raise AreaLinkLossRefused("REFUSED: " + msg
                              + f" If intended, re-run with --allow-area-link-loss {council}/{chapter_key}")


class PrecinctKeysUnverified(RuntimeError):
    """Raised AFTER the publish when it could not be confirmed that no precinct-limited rule is live without its
    key. The provisions are committed; raising makes the run end non-zero so the failure is seen, not logged."""


def rederive_after_publish(councils, dry_run: bool = False) -> list[str]:
    """Re-make the precinct keys (v2_precinct_id) of the councils just published. Both publish paths call this.

    A publish inserts every row with no key; only derive_precinct_keys puts them back. dcp_commit_approved ran it
    since 2026-09-10 (a commit had nulled four councils' keys); the direct-to-live path (dcp_extract_changed) never
    did, so on 2026-10-18 the Ku-ring-gai 14A and 14H re-reads went live with 0 of 112 / 0 of 37 rows keyed, and the
    area-link guard passed them because it checks the rules WILL re-link, not that anything runs them.

    THREE THINGS HERE ARE LOAD-BEARING, not style:
      1. Call it AFTER the enrichment phases. A derived key also sets v2_dcp_layer='precinct'; run_layer_tagging
         would overwrite that if it ran last. (It only selects v2_dcp_layer IS NULL rows, so a LATER manual
         enrichment run leaves a derived key alone -- which is why the direct path may call this when its quality
         gate skipped enrichment.)
      2. It is SCOPED PER COUNCIL. run() refuses validate:False rules on a bulk apply and honours them only when a
         council is named, so a bulk call would leave e.g. Ashfield's chapter-D rows unkeyed.
      3. It is wrapped, and it FAILS CLOSED. A derivation error must not fail the publish, but a rule a precinct
         rule should have keyed must not stay live without its key: with no key it is served to every house in the
         council (DQ-143). So after the derivation -- whether it raised, returned non-zero, or "succeeded" and wrote
         nothing (a re-paginated PDF fails closed silently) -- withhold_unkeyed takes those rows off the page.
    """
    councils = sorted(set(councils or ()))
    if not councils or dry_run:
        return []
    print(f"Re-deriving precinct keys for {len(councils)} published council(s)...")
    # The IMPORT is guarded too, and catches Exception: derive_precinct_keys reads
    # data/cos_precinct_page_ranges.json at MODULE level, so a missing data file raises FileNotFoundError, which an
    # `except ImportError` would not catch. Dockerfile.monitors COPYs both the module and that json.
    try:
        try:
            from scripts import derive_precinct_keys as dpk
        except ImportError:  # invoked from inside scripts/
            import derive_precinct_keys as dpk
        derive = dpk.run
    except Exception as exc:  # noqa: BLE001 - module-level file reads raise anything
        raise PrecinctKeysUnverified(
            f"could not load the precinct derivation ({exc}); {', '.join(councils)} published but precinct-limited "
            f"rules may be live without their key and cannot be checked. Check Dockerfile.monitors COPYs "
            f"scripts/derive_precinct_keys.py AND data/cos_precinct_page_ranges.json, then run "
            f"derive_precinct_keys.py --council X --apply per council.") from exc
    unverified: list[str] = []
    withheld: list[str] = []
    for council in councils:
        try:
            rc = derive(council=council, apply=True, validate=False)
        except Exception as exc:  # noqa: BLE001 - never fail a published provision
            print(f"  [warn] precinct re-derivation failed for {council}: {exc}. Rules it should have keyed are "
                  f"withheld below; run `python scripts/derive_precinct_keys.py --council {council} --apply`.")
            rc = None
        n = withhold_unkeyed(dpk, council)
        if n is None:
            unverified.append(council)
        elif n:
            withheld.append(f"{council}: {n} precinct-limited rule(s) withheld (no precinct key). "
                            + RESTORE.format(council=council))
        if rc is None:
            continue
        # run() can signal failure by return value; today only the validate path returns 1, which this call cannot
        # reach. Forward-looking. NOT covered: a page_range rule whose PDF was re-paginated fails closed, writes no
        # keys and returns 0 -- see scripts/audit_precinct_keying_coverage.py.
        if rc:
            print(f"  [warn] precinct re-derivation reported failure (exit {rc}) for {council}. Rules it should "
                  f"have keyed were withheld above; run `python scripts/derive_precinct_keys.py --council {council} "
                  f"--apply`.")
    if unverified:
        raise PrecinctKeysUnverified(
            f"could not check {', '.join(unverified)} for precinct-limited rules live without their key; they may be "
            f"served council-wide. Run derive_precinct_keys.py --council X --apply, then this check again.")
    return withheld


def alert_precinct_keys(councils, dry_run: bool, send) -> None:
    """Run rederive_after_publish for a publish path and send what a person must act on: rules withheld for a
    missing precinct key, or a check that could not run. Never raises: the provisions are committed, and both
    publish paths treat a post-commit step's failure as an alert, not a failed publish (#1080)."""
    try:
        notices = rederive_after_publish(councils, dry_run=dry_run)
    except PrecinctKeysUnverified as exc:
        print(f"  [ERROR] {exc}")
        notices = [f"NOT VERIFIED: {exc}"]
    if notices and send:
        try:
            send("DCP publish: precinct keys need attention\n\n" + "\n".join(notices))
        except Exception as exc:  # noqa: BLE001 - an alert outage must not abort the rest of the publish run
            print(f"  [ERROR] could not send the precinct-key alert ({exc}); notices above")


RESTORE = ("Restore once the keys can be made: python scripts/derive_precinct_keys.py --council {council} --apply, "
           "then python -c \"from enrichment.pipeline import run_actionability_classification as r; "
           "r(force_reprocess=True)\" (re-reads FALSE rows from their text).")


def unkeyed_precinct_ids(cur, dpk, council: str) -> list[int]:
    """Live rows a precinct rule derives a key for, that still have no key. Read-only; runs the same selectors and
    _derive as the derivation itself, so it names exactly the rows the derivation should have keyed."""
    ids: set[int] = set()
    for rule in dpk.RULES:
        if rule["council"] != council:
            continue
        # Same selection as the derivation (all current rows of the rule), so the page-range fingerprint can be
        # judged exactly as it judges it.
        cur.execute(
            f"""SELECT id, document_id, ref_number, pdf_page, source_chapter_key, v2_precinct_id, v2_dcp_layer,
                       v2_dcp_part, provision_text, v2_is_actionable
                  FROM regulatory_provisions
                 WHERE is_current = true AND source_council = %(council)s AND ({rule['where']})""",
            {"council": council, **dict(rule.get("params") or {})})
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        derived = {}
        for row in rows:
            try:
                derived[row["id"]] = dpk._derive(rule["strategy"], row)
            except Exception:  # noqa: BLE001 - a row whose key cannot be worked out is withheld, not served
                derived[row["id"]] = "UNDERIVABLE"
        # A re-paginated PDF fails the rule's fingerprint: the derivation then writes NO key for the rule, and its
        # page map cannot say which rows are local, so every unkeyed live row of the rule is withheld (Sol, 2026-10-20).
        fp = rule.get("fingerprint")
        broken = bool(fp and rows and dpk._fingerprint_reasons(
            fp, [r["pdf_page"] for r in rows if r["pdf_page"] is not None],
            sum(1 for v in derived.values() if v is None), len(rows)))
        for row in rows:
            # TRUE (served now) or NULL (enrichment would switch it on next run): both must be withheld.
            if row["v2_is_actionable"] is not False and row["v2_precinct_id"] is None and (broken or derived[row["id"]]):
                ids.add(row["id"])
    return sorted(ids)


def withhold_unkeyed(dpk, council: str) -> "int | None":
    """Take off the page every live rule the precinct derivation should have keyed but did not. Returns how many,
    or None when the check itself could not run (the caller then fails the run).

    Withheld = v2_is_actionable FALSE. Not NULL: routine enrichment switches NULL rows on from their text alone,
    which would serve the still-unkeyed rule council-wide again (Sol, 2026-10-20); only an explicit
    force_reprocess run re-reads FALSE rows. Recovery, once the keys exist: derive them, then re-read FALSE rows
    (see RESTORE below). Any failure HERE is reported as an error, never swallowed: it is the guard."""
    import psycopg2

    try:
        conn = psycopg2.connect(dpk.DATABASE_URL, connect_timeout=10)
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] could not check {council} for unkeyed precinct rules: {exc}")
        return None
    try:
        cur = conn.cursor()
        ids = unkeyed_precinct_ids(cur, dpk, council)
        if not ids:
            conn.rollback()
            return 0
        cur.execute(
            "UPDATE regulatory_provisions SET v2_is_actionable = FALSE "
            "WHERE id = ANY(%s) AND is_current AND v2_precinct_id IS NULL",
            (ids,),
        )
        n = cur.rowcount
        conn.commit()
        print(f"  [WITHHELD] {n} {council} rule(s) limited to one precinct had no precinct key and were taken off the "
              f"page instead of being shown to every house in the council (ids {ids[:20]}"
              f"{' ...' if len(ids) > 20 else ''}). {RESTORE.format(council=council)}")
        return n
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"  [ERROR] withholding unkeyed precinct rules for {council} failed: {exc}. They may be served "
              f"council-wide until derive_precinct_keys.py --council {council} --apply is run.")
        return None
    finally:
        conn.close()
