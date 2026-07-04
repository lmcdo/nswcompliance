#!/usr/bin/env python3
"""Scheduled brief contract-drift check (the S3 'test the context ahead' cron).

prior-art-checked: composes the two existing tools rather than duplicating
them — capture logic mirrors scripts/capture_brief_golden_fixtures.py (in
memory, no fixture writes) and the comparison is scripts/brief_contract_drift
.check_drift. New file only because neither tool runs standalone on a schedule.

Runs the REAL services the brief consumes and diffs their live emissions
against the S2 typed contracts. A government API renaming or dropping a key
alerts HERE — before a user hits a blank card.

Scope: the light READ-ONLY services (DB + public HTTP; ~seconds each). The
heavy raster pipelines (flood/terrain) are excluded — their contracts are the
services' own shared models. bushfire is also excluded: run_bushfire PERSISTS a
property_reports row, and a cron must never write junk report rows into
production data (its contract stays locked by the #598 fixtures/tests).

Exit codes (Railway cron contract, matching run_monitors.py):
  0 = no drift          1 = drift found OR a capture failed (alerts Telegram)

Deploy: railway.brief-drift.toml (weekly). Env: DATABASE_URL,
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (optional HC_PING_URL).
"""
from __future__ import annotations

import os
import sys
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "services"))

# The verified demo lot (Concord) — a stable, real address for live captures.
LAT, LNG, ZONE, PROP_ID = -33.86382, 151.10586, "R3", 1456609
ADDRESS = "14 Stanley Street, Concord"


def _captures() -> dict:
    """service name -> callable returning the raw output the brief's seam sees."""
    import services.intelligence_brief as ib
    from generate_conveyancing_report import detect_strata

    def strata():
        return detect_strata(ADDRESS, LAT, LNG)

    def climate():
        return ib._fetch_climate_risk(LAT, LNG)

    return {"strata": strata, "climate": climate}


def main() -> int:
    from brief_contract_drift import check_outputs
    from run_monitors import ping_healthcheck, send_telegram

    captured: dict = {}
    failures: list[str] = []
    for name, fn in _captures().items():
        try:
            captured[name] = fn()
        except Exception as e:
            failures.append(f"{name}: {type(e).__name__}: {str(e)[:160]}")

    findings, has_drift = check_outputs(captured)
    for f in findings:
        status = "DRIFT" if f["drift"] else "ok"
        print(f"[{status}] {f['service']} missing={f['missing']} extra={f['extra']}")
    for f in failures:
        print(f"[CAPTURE-FAILED] {f}")

    hc_url = os.environ.get("HC_PING_URL") or ""  # env var set-but-empty must not crash the ping
    if has_drift or failures:
        drifted = [f["service"] for f in findings if f["drift"]]
        msg = "⚠️ BRIEF CONTRACT DRIFT CHECK\n"
        if drifted:
            msg += f"Drifted contracts (renamed/dropped keys): {', '.join(drifted)}\n"
        if failures:
            msg += "Capture failures:\n" + "\n".join(f"  - {f}" for f in failures)
        send_telegram(msg)
        ping_healthcheck(hc_url, failed=True)
        return 1

    print(f"BRIEF-DRIFT: PASSED ({len(captured)} live services on contract)")
    ping_healthcheck(hc_url)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        # A crash in the harness itself must page, not vanish.
        traceback.print_exc()
        try:
            from run_monitors import send_telegram
            send_telegram(f"⚠️ brief drift-check harness crashed:\n{traceback.format_exc()[:1500]}")
        except Exception:
            pass
        raise SystemExit(1)
