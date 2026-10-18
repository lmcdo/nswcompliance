#!/usr/bin/env python3
"""Rules-per-address alarm: re-serve a fixed panel of real addresses from production and flag any that moved.

prior-art-checked: reuse not viable because every existing check reads ROWS, not what one address is served.
Four sweeps 2026-10-18 on origin/main cc1ab09c: (1) DB -- DQ-143/144/146 (scripts/dq_probe_live.py) count
known wrong-area defect classes in regulatory_provisions; none calls the serve path for an address.
(2) frontend -- this is not a surface. (3) python -- scripts/address_audit/build_packets.py calls the same
endpoint but samples 10 rules for a person to label and keeps no baseline; check_served_answer_quality.py
scores rows through conveyancing_db; check_served_output.py asserts three HTTP contracts and is wired into
no workflow. (4) plans -- meta-southbridge-jev-hankweave-antibrittle-2026-10-18.md section 4 item 1 names
this check; ce-HANDOFF-2026-10-15.md records that 800-2,750 rules per address went unnoticed.

WHY. The 2026-10-15 address audit found 16 wrong-area rules per 100 served (fixed to a 95% upper bound of
1.89 per 100 by audit runs 6-8, 2026-10-16), and that every address was served 800-2,750 rules. No nightly
check saw either: the database checks count rows, and the audit is a person reading a sample once a month. The
for-property route is where a row becomes an answer (the NULL-precinct leak at route.ts:1129 lived there),
so this measures the route's output for real addresses, every night.

WHAT IT CAN AND CANNOT SAY. The baseline is what each address was served when it was last accepted. The
alarm says an answer CHANGED shape -- widened, shrank, picked up a council or chapter it never had -- or
is plainly broken (zero rules, a precinct rule with no precinct key). It cannot say today's ~1,700 is the
right number: that needs each chapter's land, which is DQ-143/DQ-144's job. A green run means "no worse
than the accepted baseline", never "correct".

INPUTS ARE FROZEN. Each address keeps the exact query the assessment page sent for it (taken from the
2026-10-16 audit, run 8), so a change in the answer comes from the route or the data, not from the Planning
Portal or the geocoder.

    python scripts/address_audit/rules_per_address.py                    # check, exit 0/1/2
    python scripts/address_audit/rules_per_address.py --rebaseline --reason "why the new answer is right"

Exit codes: 0 = every address inside its box; 1 = an address moved or is broken; 2 = could not measure
(production unreachable for more than a fifth of the panel), which is never a pass.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PANEL = Path(__file__).resolve().parent / "rules_per_address_panel.json"
BASE = "https://verify.plotdetect.com.au"
UA = {"User-Agent": "Mozilla/5.0 (rules-per-address-alarm)"}

# Measured run 8 (2026-10-16) -> 2026-10-18 on the 28 panel addresses: the largest day-to-day movement was
# +2.4% (Haberfield) and -3.3% (Northern Beaches). WIDEN is three times that; SHRINK is a loss nobody
# publishes on purpose without saying so.
WIDEN = 0.10
SHRINK = 0.30
MIN_DELTA = 5  # ignore moves of a handful of rules on a small layer
MAX_UNREACHABLE = 0.2
LAYERS = ("generic", "use_specific", "condition", "precinct")


def fetch(params: dict, base: str = BASE, timeout: int = 180) -> dict:
    url = f"{base}/api/provisions/for-property?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read())


def shape(response: dict) -> dict:
    """What one address was served: totals per layer, councils, chapters, precinct rules missing a key."""
    layers = ((response.get("data") or {}).get("by_layer")) or []
    per_layer = {name: 0 for name in LAYERS}
    councils, chapters, unkeyed = set(), set(), 0
    for layer in layers:
        name = layer.get("layer") or "?"
        rows = layer.get("provisions") or []
        per_layer[name] = per_layer.get(name, 0) + len(rows)
        for p in rows:
            councils.add(p.get("source_council") or "?")
            chapters.add(p.get("source_chapter_key") or "?")
            if name == "precinct" and not (p.get("v2_precinct_id") or "").strip():
                unkeyed += 1
    return {"total": sum(per_layer.values()), "layers": per_layer, "councils": sorted(councils),
            "chapters": sorted(chapters), "precinct_unkeyed": unkeyed}


def _moved(label: str, was: int, now: int) -> str | None:
    if now > was * (1 + WIDEN) and now - was >= MIN_DELTA:
        return f"{label} widened {was} -> {now} (+{now - was})"
    if now < was * (1 - SHRINK) and was - now >= MIN_DELTA:
        return f"{label} shrank {was} -> {now} (-{was - now})"
    return None


def judge(entry: dict, now: dict) -> list[str]:
    """Reasons this address is outside its box. Empty list = inside. Pure."""
    found = []
    if now["total"] == 0 and not entry.get("expected_empty"):
        found.append("served 0 rules -- an empty answer with no stated reason")
    if now["precinct_unkeyed"]:
        found.append(f"{now['precinct_unkeyed']} precinct rule(s) with no precinct key (the route.ts:1129 leak)")
    base = entry.get("baseline")
    if not base:
        found.append("no accepted baseline -- run --rebaseline with a reason")
        return found
    for msg in [_moved("total", base["total"], now["total"])] + [
            _moved(name, base["layers"].get(name, 0), now["layers"].get(name, 0)) for name in LAYERS]:
        if msg:
            found.append(msg)
    new_councils = sorted(set(now["councils"]) - set(base["councils"]))
    if new_councils:
        found.append(f"rules from a council it never had: {', '.join(new_councils)}")
    new_chapters = sorted(set(now["chapters"]) - set(base["chapters"]))
    if new_chapters:
        more = f" (+{len(new_chapters) - 5} more)" if len(new_chapters) > 5 else ""
        found.append(f"{len(new_chapters)} chapter(s) it never had: {', '.join(new_chapters[:5])}{more}")
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default=BASE)
    ap.add_argument("--rebaseline", action="store_true", help="accept today's answers as the baseline")
    ap.add_argument("--reason", help="required with --rebaseline: why today's answers are the right baseline")
    args = ap.parse_args()
    if args.rebaseline and not (args.reason or "").strip():
        ap.error("--rebaseline needs --reason")

    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    entries = panel["addresses"]
    red, unreachable = [], []
    for e in entries:
        try:
            now = shape(fetch(e["params"], args.base_url.rstrip("/")))
        except Exception as exc:  # noqa: BLE001 -- any failure to measure is reported, never passed
            unreachable.append(e["key"])
            print(f"  ????  {e['key']} {e['address']}: could not measure ({exc})")
            continue
        was = (e.get("baseline") or {}).get("total")
        if args.rebaseline:
            e["baseline"] = now
        reasons = judge(e, now)
        print(f"  {'FAIL' if reasons else 'ok  '}  {e['key']} {e['address'][:40]:40} {e['lga'][:18]:18} "
              f"{was if was is not None else '-':>5} -> {now['total']:>5}  {now['layers']}")
        for r in reasons:
            print(f"          - {r}")
        if reasons:
            red.append(e["key"])

    if args.rebaseline:
        if unreachable:
            print(f"\nNOT REBASELINED: {len(unreachable)} address(es) could not be measured")
            return 2
        panel.setdefault("history", []).append(
            {"date": dt.date.today().isoformat(), "reason": args.reason.strip()})
        PANEL.write_text(json.dumps(panel, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nBaseline written for {len(entries)} addresses.")

    print()
    if len(unreachable) > MAX_UNREACHABLE * len(entries):
        print(f"RULES PER ADDRESS: UNKNOWN -- {len(unreachable)}/{len(entries)} unreachable. UNKNOWN is not healthy.")
        return 2
    if red:
        print(f"RULES PER ADDRESS: FAILED -- {len(red)}/{len(entries)} address(es) outside their box: {', '.join(red)}")
        return 1
    print(f"RULES PER ADDRESS: PASSED -- {len(entries)} addresses inside their box ({len(unreachable)} unmeasured).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
