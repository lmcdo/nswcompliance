#!/usr/bin/env python3
"""Live read-only measurements for the two applicability-config gaps.

prior-art-checked: reuse not viable because `scripts/dq_probe_live.py` is
SQL-only by construction -- its PROBES map is `id -> (headline, sql, params,
means)` and the runner executes the string. Both questions here need the TAGGER
to run against each row's own document_id and text, which no SQL can do. Same
contract as that file on purpose: read-only, exit 0 only when the count is 0,
exit 2 when the database is unreachable, and every number prints how it was
produced.

    DQ-102  a chapter onboarded without a config entry
    DQ-103  config_silent throws away the row's own text evidence

Both are about `ApplicabilityTagger`, both are counted on the SERVED set
(is_current AND v2_is_actionable), and neither can be answered by looking at the
stored columns alone -- which is why both were invisible until 2026-09-23.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import dq_db  # noqa: E402

from enrichment.config import COUNCIL_CONFIGS  # noqa: E402
from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

SERVED = "is_current AND v2_is_actionable AND source_council IS NOT NULL"

#: Councils reachable through the config-driven path. The Inner West three
#: (marrickville, ashfield, leichhardt) go through their own dedicated matchers
#: in `tag_with_provenance` and are deliberately out of scope: they have no
#: chapter_topics map for a chapter to be missing from.
_CONFIG_DRIVEN = sorted({
    k for k in COUNCIL_CONFIGS
    if (COUNCIL_CONFIGS[k].get("chapter_topics") or COUNCIL_CONFIGS[k].get("parts"))
})


def _rows(cur):
    # The currency filter is spelled out here rather than only in SERVED: both
    # is_current and v2_is_actionable have to sit beside the table name or the
    # DB guard cannot see them, and a probe that silently counted superseded
    # rows would report a defect nobody is being served.
    cur.execute(
        """SELECT source_council, document_id, provision_text,
                  v2_dev_type_source
           FROM regulatory_provisions
           WHERE is_current AND v2_is_actionable AND source_council IS NOT NULL"""
    )
    return cur.fetchall()


def _council_key(document_id: str) -> str | None:
    """The COUNCIL_CONFIGS key a document_id matches, by the tagger's own rule."""
    dl = (document_id or "").lower()
    for key in COUNCIL_CONFIGS:
        if key in dl:
            return key
    return None


def probe_102(rows, tagger):
    """Served rows whose council HAS a config but whose chapter matches no entry.

    `_get_config_driven` returns None for them, so they fall through to the text
    regex -- and a text hit is recorded as `text_regex`, a TRUSTED source. The
    row then looks decided when in fact the chapter was never onboarded. Nothing
    counts these: DQ-33 only sees `no_config`, which is what a row gets when the
    text ALSO found nothing, so a chapter is missing from the config silently
    unless its provisions happen to be free of zone and dev-type words.
    """
    hits = {}
    for council, doc, text, _src in rows:
        if _council_key(doc) is None:
            continue
        if tagger._get_config_driven(doc, text or "") is None:
            hits.setdefault((council, doc), 0)
            hits[(council, doc)] += 1
    return sum(hits.values()), hits


def probe_103(rows, tagger):
    """Served rows where a config entry matched, left a key undecided, and the
    row's OWN text carries evidence for that key which is thrown away.

    `tag_with_provenance` skips text extraction whenever ANY config entry
    matched -- `if text and not config` -- on the stated grounds that "the config
    is authoritative". That holds for a key the config DECIDED. It does not hold
    for `config_silent`, whose entire meaning is that nobody decided: the row is
    left reading ALL although evidence for a narrower answer sits in its own
    text. Evidence discarded because of a NON-decision.

    BOTH KEYS, evaluated independently. The first version counted dev types
    alone, and the suppression is per-ENTRY, not per-key: an entry that names
    dev types and omits zones discards the row's zone evidence in exactly the
    same way and would not have been counted, so the check could have read zero
    with the defect fully present on the other column. 1,146 served rows carry
    `v2_zone_source = 'config_silent'` (measured 2026-09-23), so that population
    is real, not hypothetical. Found by the cross-review; it is the shape
    `feedback-a-check-can-watch-the-field-the-fix-abandoned` describes.

    A row counts once per key that is silent AND has discarded evidence, so a
    row silent on both with evidence for both contributes 2.
    """
    hits = {}
    for council, doc, text, _src in rows:
        cfg = tagger._get_config_driven(doc, text or "")
        if not cfg:
            continue
        n = 0
        if (cfg.get("dev_type_source") == "config_silent"
                and tagger._extract_dev_types_from_text(text or "")):
            n += 1
        if (cfg.get("zone_source") == "config_silent"
                and tagger._extract_zones_from_text(text or "")):
            n += 1
        if n:
            hits[(council, doc)] = hits.get((council, doc), 0) + n
    return sum(hits.values()), hits


PROBES = {
    "DQ-102": (
        probe_102,
        "Served rows in a council WITH a config whose chapter matches no entry",
        "Each row belongs to a chapter that was registered and extracted but "
        "never given an applicability entry, so its scope comes from a text "
        "regex recorded as a TRUSTED source. The chapter is missing silently: "
        "DQ-33 counts only `no_config`, which these rows do not reach whenever "
        "their text happens to contain a zone or development-type word.",
    ),
    "DQ-103": (
        probe_103,
        "Discarded text evidence on a key a config entry left undecided (both columns)",
        "`tag_with_provenance` skips text extraction whenever any config entry "
        "matched, for BOTH keys -- including one the entry deliberately left "
        "undecided. `config_silent` means nobody decided that key, so the row is "
        "left reading ALL although evidence for a narrower answer sits in its own "
        "text. This does not hide the control from anyone; it serves the row to "
        "properties the evidence in its own text does not reach, on the strength "
        "of a non-decision. Counted once per silent key with evidence, zones and "
        "dev types alike.",
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--id", required=True, choices=sorted(PROBES))
    ap.add_argument("--limit-print", type=int, default=12)
    args = ap.parse_args()

    fn, headline, means = PROBES[args.id]
    try:
        conn = dq_db.connect()
    except Exception as exc:  # noqa: BLE001
        print(f"{args.id}: UNKNOWN -- database unreachable ({exc}). Nothing was "
              f"checked, which is not a pass.", file=sys.stderr)
        return 2

    try:
        cur = conn.cursor()
        tagger = ApplicabilityTagger()
        count, by_doc = fn(_rows(cur), tagger)
    finally:
        conn.close()

    print(f"{args.id}: {headline}")
    print(f"  count   : {count:,}")
    # is_current AND v2_is_actionable -- the served set, as _rows selects it.
    print(f"  scope   : regulatory_provisions WHERE {SERVED}")
    print(f"  councils: {', '.join(_CONFIG_DRIVEN)}")
    print(f"  means   : {means}")
    if by_doc:
        print(f"  documents ({len(by_doc)}):")
        for (council, doc), n in sorted(by_doc.items(), key=lambda kv: -kv[1])[:args.limit_print]:
            print(f"    {n:>5,}  {council:<22} {doc}")
        if len(by_doc) > args.limit_print:
            print(f"    ... {len(by_doc) - args.limit_print} more")
    return 0 if count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
