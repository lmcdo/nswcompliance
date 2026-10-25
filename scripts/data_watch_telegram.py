#!/usr/bin/env python3
# prior-art-checked: data-watch.yml raised only a GitHub issue; Telegram senders exist inside run_monitors.py and
# verifyops_outside_ping.py but both are tied to their own jobs (heartbeat / healthchecks ping).
"""Send data-watch's failing checks to Telegram (2026-10-25).

The live-data checks left the PR gate (#1496) and now report from data-watch, nightly and at 09:30 UTC after
rules go live. Its GitHub issue alone is not read, so red also goes to Telegram. FAILED is the comma-separated
list of step outcomes, in the same order as NAMES (the same list the issue step uses; a test keeps them equal).

Exit 0 when nothing failed or the message was delivered; 1 when something failed and Telegram did not answer
ok -- so a silent alarm turns the run red.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

NAMES = ["defect ledger", "DCP as-at coverage", "satellite manifests", "published figures",
         "LGA capability flags", "schema contract", "controls provenance", "control source values",
         "served-answer quality", "DCP page maps vs their PDFs", "control values vs the council PDF",
         "citation verdicts refresh", "report audit chain", "rules per address"]


def failing(outcomes: str) -> list[str]:
    """Checks that did not pass: 'failure' by name, and anything else but 'success' as "(did not run)" --
    a skipped, cancelled or missing step is not a check that passed (Sol, 2026-10-25)."""
    parts = [o.strip() for o in (outcomes or "").split(",")]
    parts += [""] * (len(NAMES) - len(parts))
    return [n if o == "failure" else f"{n} (did not run)" for n, o in zip(NAMES, parts) if o != "success"]


def message(failed: list[str], run_url: str) -> str:
    return ("data-watch: live data checks failing\n" + "\n".join(f"- {n}" for n in failed)
            + f"\nDetails: {run_url}")


def send(text: str, token: str, chat: str) -> bool:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat, "text": text[:4000]}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 - fixed host
            ans = json.loads(r.read())
    except Exception as exc:  # noqa: BLE001
        print(f"telegram send failed: {type(exc).__name__}")
        return False
    return isinstance(ans, dict) and ans.get("ok") is True and isinstance(ans.get("result"), dict)


def main() -> int:
    failed = failing(os.environ.get("FAILED") or "")
    if not failed:
        print("data-watch: every check passed; nothing sent")
        return 0
    text = message(failed, os.environ.get("RUN_URL") or "")
    print(text)
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN") or "", os.environ.get("TELEGRAM_CHAT_ID") or ""
    if not (token and chat and send(text, token, chat)):
        print("::error::data-watch found failing checks and could not tell Telegram")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
