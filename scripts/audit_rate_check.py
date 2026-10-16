"""Deterministic check for outreach claim OC-18 (address-audit serious-error rate).

Claim: "In an independent check of the rules shown at random addresses, read by a person against the
council's plan, fewer than 2 in 100 had a serious error (95% confidence). Repeated at least every 30 days."

Method assumption (stated, not hidden): each run is a code first pass over ALL packets (rules shown at the
audited addresses) plus a 10% random sample of the rest; a person reads the flagged + sampled rules. Rules
neither flagged nor sampled are treated as passing the code pass. So the denominator is ALL packets in the
run, and a "read" rule is any label other than 'unread'. The bound is therefore a bound on serious errors
that the code pass or the person finds, per 100 rules shown.

Data: ``data/address_audit/<YYYY-MM-DD>-<name>/`` with ``labels.jsonl`` (rule_key, label, reason[, category]),
``packets.jsonl`` (one line per rule shown) and ``summary.json`` (list, one entry per address).
Labels: ok | minor | unsure | severe | unread. ``unsure`` counts as severe for the bound (conservative).

Bound: exact one-sided 95% Poisson upper limit, chi2.ppf(0.95, 2(k+1)) / 2, per 100 rules.
PASS (exit 0) only if pooled packets >= 500, addresses >= 50, newest run <= 30 days old, bound < 2.0.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from scipy.stats import chi2

DATA = Path(__file__).resolve().parents[1] / "data" / "address_audit"
WINDOW_DAYS = 30
MIN_PACKETS = 500
MIN_ADDRESSES = 50
MAX_BOUND = 2.0
LABELS = {"ok", "minor", "unsure", "severe", "unread"}


def _jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def upper_bound_per_100(k: int, n: int) -> float:
    """Exact one-sided 95% Poisson upper limit on the error rate, per 100 rules, given k events in n rules."""
    return float(chi2.ppf(0.95, 2 * (k + 1)) / 2) / n * 100


def load_runs(data_dir: Path, today: date) -> list[dict]:
    """Every run dir with a dated name and a labels file, within the 30-day window."""
    runs = []
    for d in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", d.name)
        if not m or not (d / "labels.jsonl").exists():
            continue
        run_date = date.fromisoformat(m.group(1))
        age = (today - run_date).days
        if age > WINDOW_DAYS:
            continue
        labels = _jsonl(d / "labels.jsonl")
        bad = [x for x in labels if x.get("label") not in LABELS]
        if bad:
            raise ValueError(f"{d.name}: unknown label {bad[0].get('label')!r}")
        summary = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        runs.append({
            "name": d.name, "date": run_date, "age": age, "labels": labels,
            "packets": len(_jsonl(d / "packets.jsonl")),
            "addresses": sum(1 for a in summary if a.get("served")),
        })
    return runs


def evaluate(data_dir: Path, today: date) -> tuple[bool, str]:
    runs = load_runs(data_dir, today)
    if not runs:
        return False, f"FAIL: no audit run within {WINDOW_DAYS} days of {today}"
    packets = sum(r["packets"] for r in runs)
    addresses = sum(r["addresses"] for r in runs)
    labels = [x for r in runs for x in r["labels"]]
    read = sum(1 for x in labels if x["label"] != "unread")
    severe = sum(1 for x in labels if x["label"] == "severe")
    unsure = sum(1 for x in labels if x["label"] == "unsure")
    newest = min(r["age"] for r in runs)
    bound = upper_bound_per_100(severe + unsure, packets) if packets else float("inf")
    bound_severe = upper_bound_per_100(severe, packets) if packets else float("inf")
    line = (f"runs {len(runs)} | packets {packets} | addresses {addresses} | read {read} | severe {severe} | "
            f"unsure {unsure} | newest run {newest}d old | upper 95% bound per 100: {bound:.2f} "
            f"(severe only {bound_severe:.2f}; unsure counted as severe)")
    reasons = []
    if packets < MIN_PACKETS:
        reasons.append(f"only {packets} rules (need {MIN_PACKETS})")
    if addresses < MIN_ADDRESSES:
        reasons.append(f"only {addresses} addresses (need {MIN_ADDRESSES})")
    if newest > WINDOW_DAYS:
        reasons.append(f"newest run {newest} days old (max {WINDOW_DAYS})")
    if not bound < MAX_BOUND:
        reasons.append(f"upper bound {bound:.2f} per 100 is not below {MAX_BOUND}")
    if reasons:
        return False, f"FAIL: {'; '.join(reasons)}\n{line}"
    return True, f"PASS: {line}"


def main() -> int:
    print("Denominator = ALL packets in each run (code first pass + 10% random sample is the method).")
    ok, msg = evaluate(DATA, date.today())
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
