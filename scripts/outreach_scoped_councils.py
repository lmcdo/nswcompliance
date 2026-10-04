#!/usr/bin/env python3
"""OC-17: which councils the scoped-rules claim may name, computed, and whether the site names exactly them.

prior-art-checked: reuse, not a new measurement. The per-council split CALLS the two machines that
already own the question -- DQ-114's own SQL (dq_probe_live.PROBES) for undecided scope keys, and
dq_probe_applicability_config.probe_115 for declarations with no quoted sentence -- and refuses to
answer if its split no longer adds up to DQ-114's own total. outreach_claim_checks.py was already
over the 500-line limit, so this lives beside it rather than inside it.

THE CLAIM (user ruling 2026-10-03, ce-outreach-narrowed-claims-PROMPT-2026-10-03.md section 5):
  "For the councils listed, every rule shown carries the council's own sentence and the clause it
   came from, in the plan registered as in force. Known exceptions are stated."

It replaced "The rules and numbers shown apply to this property, from the plan in force", which
asserted all councils at once and so stayed red while any one council had a single undecided key.
The new wording is narrower in exactly one way: it names its councils. It does NOT relax what a
named council must satisfy.

HOW A COUNCIL IS LISTED
  * Every OC-17 sub-check that cannot be split by council (DQ-99, DQ-66, DQ-61, the plan-in-force
    confirmation, ...) must pass for the whole fleet. Those run as their own rows in OC-17; if any
    fails, the claim fails outright rather than delisting a guessed council. Stricter than the
    ruling's "a council is listed when all ITS sub-checks pass", never laxer.
  * DQ-114 per council: no served rule in it takes a zone or development-type scope from a
    non-decision, except rows a stated exception names exactly (council + chapter + key).
  * DQ-115 per council: every scope its config declares carries the council's own sentence.
  * No served rule in it takes either scope key from `no_config` -- no entry matched and its text named
    nothing, so it reaches every property and project by fallthrough. DQ-114 leaves this source to
    DQ-33, and DQ-33 is a FLEET FLOOR that may only fall, not a zero: it passes while hundreds of such
    rows sit in a council. The first version of this file listed five councils carrying them (ashfield
    118, marrickville 273, northern_beaches 154+, inner_west 1, cumberland 3) because it read DQ-114
    alone. Caught 2026-10-04 by DQ-105 going red on cumberland, before the list was merged.

THE PUBLISHED LIST is frontend-nextjs/shared/dcp-scoped-councils.json, which the site renders. The
check passes only when that list equals the computed one, in BOTH directions: naming a council that
fails overclaims, and leaving out one that passes makes the page lie in the direction nobody checks.
A stated exception that no longer matches any row is stale and also fails.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
PUBLISHED = ROOT / "frontend-nextjs" / "shared" / "dcp-scoped-councils.json"

#: The schema's own undetermined vocabulary (migration 062), as DQ-114 reads it; no_config is DQ-33's.
_UNDECIDED = "('config_silent', 'filtered_to_all', 'no_document_id')"
#: One row per (council, chapter, key) still undecided -- DQ-114's population, split. The served filter is
#: written out in each SELECT rather than interpolated, so the QA gate's currency check can see it.
_SPLIT_SQL = f"""
SELECT source_council, source_chapter_key, 'applicable_dev_types', count(*) FROM regulatory_provisions
 WHERE is_current AND v2_is_actionable AND source_council IS NOT NULL
   AND (v2_dev_type_source IN {_UNDECIDED} OR v2_dev_type_source IS NULL)
 GROUP BY 1, 2
UNION ALL
SELECT source_council, source_chapter_key, 'applicable_zones', count(*) FROM regulatory_provisions
 WHERE is_current AND v2_is_actionable AND source_council IS NOT NULL
   AND (v2_zone_source IN {_UNDECIDED} OR v2_zone_source IS NULL)
 GROUP BY 1, 2"""

#: Every council serving rule text, with its ACTIVE registry name. The is_active test sits in the join, not
#: the WHERE: a council whose registry row is retired still serves rules, so it stays in the universe with a
#: NULL name, and a published name for it then fails as a mismatch instead of the council vanishing.
#: Keys a served rule takes from no_config, per council -- DQ-33's population, split, counted per key like
#: DQ-114. No stated exception reaches these: an exception names a decision that cannot be expressed, and
#: here nobody decided anything.
_NO_CONFIG_SQL = """
SELECT source_council,
       count(*) FILTER (WHERE v2_dev_type_source = 'no_config')
     + count(*) FILTER (WHERE v2_zone_source = 'no_config')
  FROM regulatory_provisions
 WHERE is_current AND v2_is_actionable AND source_council IS NOT NULL
 GROUP BY 1"""

_UNIVERSE_SQL = """
SELECT DISTINCT p.source_council, r.display_name FROM regulatory_provisions p
  LEFT JOIN lga_registry r ON r.slug = p.source_council AND r.is_active
 WHERE p.is_current AND p.v2_is_actionable AND p.source_council IS NOT NULL"""


def load_published(path: Path | None = None) -> dict:
    return json.loads((path or PUBLISHED).read_text(encoding="utf-8"))


def _dq115_by_council(slugs: list[str]) -> tuple[dict[str, int], list[str]]:
    """probe_115's hits attributed to council slugs by config IDENTITY (aliases share one dict)."""
    from enrichment.config import COUNCIL_CONFIGS
    from dq_probe_applicability_config import probe_115

    _total, hits = probe_115(None, None)
    owner = {id(COUNCIL_CONFIGS[s]): s for s in slugs if s in COUNCIL_CONFIGS}
    per: dict[str, int] = {}
    orphans: list[str] = []
    for (name, entry), n in hits.items():
        slug = owner.get(id(COUNCIL_CONFIGS[name]))
        if slug is None:
            orphans.append(f"{name}/{entry}")  # a config serving no council in the list: never dropped
        else:
            per[slug] = per.get(slug, 0) + n
    return per, orphans


def compute(conn, exceptions: list[dict]) -> tuple[dict[str, str], dict[str, str | None], list[str]]:
    """Return ({slug: why it is NOT listed, '' if it is}, {slug: registry display name}, problems)."""
    from dq_probe_live import PROBES

    problems: list[str] = []
    with conn.cursor() as cur:
        cur.execute(_UNIVERSE_SQL)
        names = {slug: name for slug, name in cur.fetchall()}
        cur.execute(_SPLIT_SQL)
        split = cur.fetchall()
        _h, dq114_sql, params, _m = PROBES["DQ-114"]
        cur.execute(dq114_sql, params)
        dq114_total = cur.fetchone()[0]
        cur.execute(_NO_CONFIG_SQL)
        no_config = {council: n for council, n in cur.fetchall() if n}

    split_total = sum(row[3] for row in split)
    if split_total != dq114_total:
        problems.append(f"the per-council split counts {split_total} keys but DQ-114 counts "
                        f"{dq114_total}: the two queries have drifted apart")

    excused = {(e["council"], ch, e["field"]) for e in exceptions for ch in e["chapters"]}
    used: set = set()
    undecided: dict[str, int] = {}
    for council, chapter, field, n in split:
        if (council, chapter, field) in excused:
            used.add((council, chapter, field))
        else:
            undecided[council] = undecided.get(council, 0) + n
    for key in sorted(excused - used):
        problems.append(f"stated exception {key} matches no served row: it is stale")

    slugs = sorted(names)
    dq115, orphans = _dq115_by_council(slugs)
    problems += [f"DQ-115 hit in a config no served council uses: {o}" for o in orphans]

    reasons = {}
    for slug in slugs:
        why = []
        if undecided.get(slug):
            why.append(f"DQ-114 {undecided[slug]}")
        if no_config.get(slug):
            why.append(f"no_config {no_config[slug]}")
        if dq115.get(slug):
            why.append(f"DQ-115 {dq115[slug]}")
        reasons[slug] = ", ".join(why)
    return reasons, names, problems


def check() -> tuple[str, str]:
    try:
        published = load_published()
        listed = {c["slug"]: c["name"] for c in published["councils"]}
        exceptions = list(published.get("exceptions") or [])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return FAIL, f"scoped-council list: {PUBLISHED.name} unreadable ({exc})"
    try:
        from dq_db import connect
        conn = connect()
    except Exception as exc:  # noqa: BLE001 - unreachable is UNKNOWN, never a pass
        return UNKNOWN, f"scoped-council list: database unreachable ({exc})"
    try:
        reasons, names, problems = compute(conn, exceptions)
    except Exception as exc:  # noqa: BLE001 - a check that no longer runs is broken: FAIL
        return FAIL, f"scoped-council list: could not compute ({exc})"
    finally:
        conn.close()

    should = {s for s, why in reasons.items() if not why}
    for s in sorted(set(listed) - should):
        problems.append(f"published but fails: {s} ({reasons.get(s) or 'serves no rule text'})")
    for s in sorted(should - set(listed)):
        problems.append(f"passes but not published: {s} ({names.get(s)})")
    for s in sorted(set(listed) & should):
        if listed[s] != names.get(s):
            problems.append(f"published name {listed[s]!r} is not the registry's {names.get(s)!r}")
    unlisted = {s: why for s, why in reasons.items() if why}
    detail = (f"councils listed {len(should)} of {len(reasons)}; not listed: "
              f"{', '.join(f'{s} ({w})' for s, w in sorted(unlisted.items())) or 'none'}")
    if problems:
        return FAIL, f"scoped-council list does not match: {'; '.join(problems)}. {detail}"
    return PASS, f"published scoped-council list matches the computed one: {detail}"


if __name__ == "__main__":
    verdict, text = check()
    print(f"  {verdict:<8} {text}")
    sys.exit({PASS: 0, FAIL: 1}.get(verdict, 2))
