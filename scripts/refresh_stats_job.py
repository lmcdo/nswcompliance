#!/usr/bin/env python3
"""Weekly secondary-dwelling stats refresh — Railway maintenance cron.

Replaces `.github/workflows/stats-refresh.yml`. Fetches stats from the
Planning Portal, bakes them into the checked-in TypeScript data file, and (if
changed) commits + pushes the update.

Steps mirror the old workflow:
  1. scripts/secondary_dwelling_stats.py --output json  -> /tmp/stats.json
  2. scripts/json_to_ts_stats.py --input ... --output <TS file>
  3. git commit + push if the TS file changed

Auth for push:
  - On Railway: set GIT_PUSH_TOKEN (a GitHub PAT with `contents:write`) and
    GITHUB_REPOSITORY (owner/repo). The push URL is built from these.
  - Locally: leave GIT_PUSH_TOKEN unset and it uses your ambient git creds.
  If the file changed but no push credential is available, the script writes the
  file, reports via Telegram, and exits 2 (degraded) so the change isn't lost.

Env required for the fetch: DA_SUPABASE_URL, DA_SUPABASE_ANON_KEY.

Exit codes:
  0  ran; no change (or pushed successfully)
  2  ran; file changed but could not be pushed (manual commit needed)
  1  a step failed hard
"""

import os
import subprocess
import sys

TS_FILE = "frontend-nextjs/lib/lga-data/secondary-dwelling-stats.ts"
STATS_JSON = "/tmp/stats.json"
PUSH_BRANCH = os.environ.get("STATS_PUSH_BRANCH", "main")


def send_telegram(msg: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        import requests

        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg[:4000], "disable_web_page_preview": True},
            timeout=10,
        )
    except Exception:
        pass


def run(cmd, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def main() -> int:
    # 1. Fetch stats JSON.
    with open(STATS_JSON, "w", encoding="utf-8") as fh:
        fetch = subprocess.run(
            ["python", "scripts/secondary_dwelling_stats.py", "--output", "json"],
            stdout=fh, text=True,
        )
    if fetch.returncode != 0:
        send_telegram("🚨 stats-refresh: fetch step failed")
        return 1

    # 2. Bake into the TS data file.
    conv = run([
        "python", "scripts/json_to_ts_stats.py",
        "--input", STATS_JSON,
        "--output", TS_FILE,
    ])
    if conv.returncode != 0:
        print(conv.stderr[-2000:], file=sys.stderr)
        send_telegram("🚨 stats-refresh: JSON->TS conversion failed")
        return 1

    # 3. Did the file change?
    diff = run(["git", "diff", "--quiet", "--", TS_FILE])
    if diff.returncode == 0:
        print("stats-refresh: no change")
        return 0

    # Stage + commit.
    run(["git", "config", "user.name", "railway-stats-bot"])
    run(["git", "config", "user.email", "stats-bot@users.noreply.github.com"])
    run(["git", "add", TS_FILE])
    # Date is supplied by the environment to keep the script deterministic.
    stamp = os.environ.get("RUN_DATE", "")
    msg = f"chore: refresh secondary dwelling stats {stamp}".strip()
    commit = run(["git", "commit", "-m", msg])
    if commit.returncode != 0:
        print(commit.stderr[-2000:], file=sys.stderr)
        send_telegram("🚨 stats-refresh: git commit failed")
        return 1

    # Push — token-authenticated on Railway, ambient creds locally.
    token = os.environ.get("GIT_PUSH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")  # owner/repo
    if token and repo:
        url = f"https://x-access-token:{token}@github.com/{repo}.git"
        push = run(["git", "push", url, f"HEAD:{PUSH_BRANCH}"])
    else:
        push = run(["git", "push", "origin", f"HEAD:{PUSH_BRANCH}"])

    if push.returncode != 0:
        print(push.stderr[-2000:], file=sys.stderr)
        send_telegram(
            "⚠️ stats-refresh: stats changed and committed locally but PUSH FAILED "
            "(set GIT_PUSH_TOKEN + GITHUB_REPOSITORY on Railway). Manual push needed."
        )
        return 2

    send_telegram(f"✅ stats-refresh: secondary dwelling stats updated and pushed to {PUSH_BRANCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
