"""Run every page-integrity check over capture folders and report counts per check.

    python scripts/page_integrity/check.py FOLDER [FOLDER ...] [--db] [--json OUT]

Checks (see ~/.claude/plans/ce-page-integrity-check-PLAN-2026-10-19.md):
  C1 same fact agrees        C2 yield agrees with the page's permissibility data  # noqa: zone-codes (check ids, not zones)
  C3 honest absence          C4 shown row fits this lot  # noqa: zone-codes (check ids, not zones)
  C5 words on the page       C6 shown numbers recomputed
--db adds the C3 re-ask: an absence the page shows ("not covered") is asked again through the
product's own canonical lookup; data found there means the page said "none" wrongly.

Headline: captures with >=1 flag in C1-C6 (liability-word hits are reported, not counted — many
are quoted regulatory text). Exit 0 clean, 1 any flag, 2 any capture unusable (never a pass).

prior-art-checked: runner over load.py captures; no existing runner for these checks.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import checks_data as cd  # noqa: E402
import checks_reference as cr  # noqa: E402
import checks_xprod as cx  # noqa: E402
import checks_text as ct  # noqa: E402
from load import CaptureUnusable, load  # noqa: E402

CHECKS = (
    ("C1", cd.same_fact_agrees),
    ("C2", ct.check_engines_agree),
    ("C3", cd.honest_absence),
    ("C4", cd.row_fits_lot),
    ("C5", ct.check_words_on_page),
    ("C6", ct.check_derivations),
    ("C7", cx.check_cross_product),  # only where site_report.jsonl.gz was captured
    ("R", cr.check_reference),  # only where tests/fixtures/page_integrity/<slug>/expected.json exists
)
INFO_FACTS = {"liability-word"}


def reask_permissibility(cap) -> list[dict]:
    """C3 re-ask: page says the LEP land-use table does not cover this zone/council; ask the
    product's canonical lookup (intelligence_brief._permitted_engine_forms, which normalises the
    council name with _norm_lga) whether it does."""
    x = cap.last("/api/lep/permissibility")
    if not x or not isinstance(x.get("json"), dict) or x["json"].get("covered") is not False:
        return []
    from services.intelligence_brief import _permitted_engine_forms
    zone, lga = x["query"].get("zone"), x["query"].get("lga")
    forms = _permitted_engine_forms(zone, lga)
    if not forms:
        return []
    return [{"check": "C3", "fact": "permissibility",
             "detail": f"page says not covered for {zone}/{lga!r}; canonical lookup finds {sorted(forms)}",
             "evidence": "/api/lep/permissibility covered:false"}]


def run(folder: Path, db: bool) -> dict:
    try:
        cap = load(folder)
    except CaptureUnusable as e:
        return {"folder": str(folder), "unusable": str(e)}
    flags: list[dict] = []
    for cid, fn in CHECKS:
        for f in fn(cap):
            d = dict(vars(f))
            d["check"] = cid
            flags.append(d)
    if db:
        flags += reask_permissibility(cap)
    not_checked = sorted(k for m in (cd.facts_checked(cap), ct.facts_checked(cap), cx.facts_checked(cap), cr.facts_checked(cap)) for k, v in m.items() if not v)
    return {"folder": str(folder), "address": cap.meta.get("resolved_address"), "flags": flags,
            "not_checked": not_checked}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--db", action="store_true", help="also re-ask absences through the canonical lookup (reads the DB)")
    ap.add_argument("--json", help="write full results here")
    a = ap.parse_args(argv)
    results = [run(Path(f), a.db) for f in a.folders]
    unusable = [r for r in results if "unusable" in r]
    defect_caps = 0
    by_check: Counter = Counter()
    for r in results:
        if "unusable" in r:
            print(f"UNUSABLE  {r['folder']}: {r['unusable']}")
            continue
        real = [f for f in r["flags"] if f["fact"] not in INFO_FACTS]
        info = len(r["flags"]) - len(real)
        defect_caps += bool(real)
        counts = Counter(f["check"] for f in real)
        by_check.update(counts)
        print(f"{r['address'] or r['folder']}: " + " ".join(f"{c}={counts.get(c, 0)}" for c, _ in CHECKS)
              + f" | liability-word={info} | not checked: {', '.join(r['not_checked']) or '-'}")
        for f in real:
            print(f"    {f['check']} {f['fact']}: {f['detail'][:160]}")
    usable = len(results) - len(unusable)
    print(f"\nHEADLINE: {defect_caps} of {usable} captures have >=1 integrity defect (C1-C7, R); "
          + " ".join(f"{c}={by_check.get(c, 0)}" for c, _ in CHECKS)
          + (f"; {len(unusable)} unusable" if unusable else ""))
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    if unusable:
        return 2
    return 1 if defect_caps else 0


if __name__ == "__main__":
    sys.exit(main())
