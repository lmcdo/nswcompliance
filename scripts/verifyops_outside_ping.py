"""Tell the outside watchdog (healthchecks.io) whether the daily alarm LOOKED, and send red to Telegram.

v7 step 4 (~/.claude/plans/ce-verifyops-v5-SPEC-2026-10-22.md). The old rule -- ping only when every
check is green -- turns a known, baselined red into an email every 2 days for ever, which teaches the
reader to ignore it. The new rule separates two questions:

  did we look?        every check exited 0 (green) or 1 (red: it looked and found something)
  did the reader hear? any red/could-not-look went to Telegram and Telegram answered "ok": true

  looked AND heard  -> ping <url>         (healthchecks.io stays green)
  anything else     -> ping <url>/fail    (healthchecks.io emails now)
  runner/GitHub dead -> no ping at all     (healthchecks.io emails after the grace period)

A missing exit code means the step crashed before recording one: that is "did not look".

Usage (freshness-alarm.yml):
    python scripts/verifyops_outside_ping.py --rc ledger=1 --rc coverage=0 --rc railway= \
        --report ledger.txt --report coverage.txt
Env: HC_PING_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
Exit 0 only if the chosen ping landed (body "OK"); 1 otherwise (the job goes red as well).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

LOOKED = {"0", "1"}
MAX_LINES = 25  # Telegram caps a message at 4096 chars; 25 lines of keys stays well under
_JOB_LINE = re.compile(r"^(dcp|maintenance)-[\w-]+: ")  # check_railway_jobs_ran problem lines


def decide(rcs: dict[str, str | None], telegram_ok: bool | None) -> str:
    """'success' or 'fail'. telegram_ok is None when nothing needed sending."""
    if not rcs or any((v or "").strip() not in LOOKED for v in rcs.values()):
        return "fail"
    needs_send = any(v.strip() == "1" for v in rcs.values())
    if needs_send and telegram_ok is not True:
        return "fail"
    return "success"


def message(rcs: dict[str, str | None], reports: list[str]) -> str | None:
    """Telegram text, or None when every check was green."""
    if all((v or "").strip() == "0" for v in rcs.values()):
        return None
    head = ", ".join(f"{k}={'crashed' if not (v or '').strip() else v.strip()}" for k, v in rcs.items())
    lines: list[str] = []
    for text in reports:
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(("VERIFYOPS:", "C =", "NEW RED", "RAILWAY-JOBS:", "FAIL", "PASS", "---")) \
                    or _JOB_LINE.match(s):
                lines.append(s)
    more = len(lines) - MAX_LINES
    body = "\n".join(lines[:MAX_LINES]) + (f"\n... {more} more lines in the Actions log" if more > 0 else "")
    return f"DCP alarm (exit codes: {head})\n{body}".strip()


def _post(url: str, data: bytes | None, timeout: int = 20) -> str:
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "compliance-engine-outside-ping/1.0", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed hosts
        return r.read().decode("utf-8", "replace")


def send_telegram(text: str, token: str, chat: str, post=_post) -> bool:
    """True only when Telegram's own answer says ok and names a message id."""
    try:
        ans = json.loads(post(f"https://api.telegram.org/bot{token}/sendMessage",
                              json.dumps({"chat_id": chat, "text": text[:4000]}).encode()))
    except Exception as exc:  # noqa: BLE001 - any failure = the reader did not hear
        print(f"telegram send failed: {type(exc).__name__}")
        return False
    return ans.get("ok") is True and bool((ans.get("result") or {}).get("message_id"))


def ping(url: str, verdict: str, post=_post) -> bool:
    """True only when healthchecks.io's body is OK and not 'OK (not found)' (a URL naming no check)."""
    target = url.rstrip("/") + ("/fail" if verdict == "fail" else "")
    try:
        body = post(target, None)
    except Exception as exc:  # noqa: BLE001
        print(f"could not reach healthchecks.io: {type(exc).__name__}")
        return False
    print(f"healthchecks.io said: {body.strip()}")
    return body.strip().startswith("OK") and "not found" not in body


def main(argv: list[str] | None = None, post=_post) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rc", action="append", default=[], metavar="NAME=CODE")
    ap.add_argument("--report", action="append", default=[], metavar="FILE")
    a = ap.parse_args(argv)
    rcs = {k: v for k, _, v in (r.partition("=") for r in a.rc)}
    reports = [Path(f).read_text(encoding="utf-8", errors="replace") if Path(f).exists() else ""
               for f in a.report]
    hc = os.environ.get("HC_PING_URL", "").strip()
    if not hc:
        print("::error::HC_PING_URL is not set: nothing outside watches this alarm")
        return 1

    text = message(rcs, reports)
    tg_ok: bool | None = None
    if text:
        token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
        tg_ok = send_telegram(text, token, chat, post) if token and chat else False
        print(f"telegram delivered: {tg_ok}")
    verdict = decide(rcs, tg_ok)
    print(f"verdict: {verdict}  ({rcs})")
    return 0 if ping(hc, verdict, post) else 1


if __name__ == "__main__":
    sys.exit(main())
