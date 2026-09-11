# Railway Monitor Cron Services

Monitoring infrastructure moved from GitHub Actions to Railway cron jobs (May 2026)
to avoid burning Actions minutes.

## Architecture

One Docker image (`Dockerfile.monitors`) serves the monitors; the heavier weekly
maintenance jobs ship in `Dockerfile.maintenance`. Each Railway cron service sets
`MONITOR_NAME` to select which monitor runs. The entrypoint is
`scripts/run_monitors.py`.

## ⚠ DO NOT ASK THIS FILE WHICH SERVICES EXIST — ask a command

This document carried a table of **4** services while **12** monitor names existed
and **11** services ran. It was written in May 2026 and nothing made it wrong out
loud, so it stayed wrong: it still listed `dcp-extract` and `dcp-commit` as
"local/on-demand scripts" long after both became daily crons, and it gave
`dcp-monitor` a weekly schedule it has not had for months. A transcribed list is
how this file went wrong, so the list is gone.

```bash
# The monitor names the runner will accept — the authoritative set
grep -n '": {$' scripts/run_monitors.py

# The schedules declared in version control
ls railway*.toml && grep -H cronSchedule railway*.toml

# What Railway ACTUALLY runs, which is the only answer that counts
railway status --json | python -c "import sys,json; d=json.JSONDecoder().raw_decode(sys.stdin.read())[0]; [print(f\"{s['node']['serviceName']:<24} {s['node'].get('cronSchedule') or '-'}\") for e in d['environments']['edges'] for s in e['node']['serviceInstances']['edges']]"
```

**The third command is not optional.** Railway applies config-as-code **only where
no dashboard value is set**, so a schedule typed into the dashboard wins over the
`.toml` forever after and the file becomes a comment that reads like
configuration. `scripts/check_railway_cron_drift.py` compares the two and is wired
into `gates.yml` — but it **cannot see `monitor-satellite` or `monitor-watchdog`**,
because both share `railway.monitors.toml`, which declares no `cronSchedule` of its
own. Those two are the services whose live schedule nothing in the repo verifies.

**Config-as-code is deprecated.** The Railway CLI now warns that
`railway.json` / `railway.toml` are superseded by its newer Infrastructure-as-Code
format (a TypeScript config, which this repo does not use and has no file for yet);
existing files keep working until **2026-12-01**.

### Creating Each Service

1. Railway Dashboard > Project > New Service > Cron Job
2. Connect to the `nswcompliance` GitHub repo
3. Set **Dockerfile Path** to `Dockerfile.monitors`
4. Set **Start Command** to `python scripts/run_monitors.py`
5. Set the cron schedule
6. Add environment variables (see below)

### Environment Variables

**Railway environment variables are PER-SERVICE**, not shared across services in a
project unless explicitly wired as Shared Variables. With a dozen similarly-named
services (`dcp-monitor` vs `dcp-extract` especially) it is easy to set a variable on
the wrong one — confirmed as the cause of a real incident on 2026-09-07, where
`HC_PING_URL` was set but alerts kept reporting it missing for three consecutive
daily runs because it had gone onto a sibling service. `run_monitors.py` prints
`Env missing: [...]` on **every** failure alert regardless of cause, which made an
unrelated OOM crash read as if the missing variable had caused it.

All services need:
- `MONITOR_NAME` — the monitor to run (`grep -n '": {$' scripts/run_monitors.py`)
- `DATABASE_URL` — Supabase connection string
- `TELEGRAM_BOT_TOKEN` — VerifyOpsBot token
- `TELEGRAM_CHAT_ID` — alert channel ID

Per-service extras:
- `monitor-satellite`: `GOOGLE_MAPS_API_KEY`, `HC_PING_URL` (= HC_PING_SATELLITE_MONITOR)
- `monitor-legislation`: `HC_PING_URL` (= HC_PING_LEGISLATION_MONITOR)
- `monitor-dcp`: `R2_ACCOUNT_ID`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `HC_PING_URL` (= HC_PING_DCP_MONITOR)
- `monitor-watchdog`: no extras — **including no `HC_PING_URL`, so there is no
  dead-man's switch.** Its own run log prints `Env missing: ['HC_PING_URL']`. If the
  weekly cron ever stops firing, nothing reports it: silence and health look the
  same. Verified running 2026-09-11 (Wed 09-09 10:01 UTC, exit 2, Telegram sent).

### Schedule Changes from GitHub Actions

| Monitor | Was | Now | Why |
|---|---|---|---|
| Satellite freshness | Daily | Weekly (Mon) | Reports fail visibly if API is down; weekly detection is sufficient |
| DCP watchdog | Daily | Weekly (Wed) | DCP monitor runs Mon; stuck extractions caught Wed (2-day window vs 25hr threshold still fine) |
| Legislation | Weekly Mon | Weekly Mon | No change |
| DCP monitor | Weekly Mon | **fortnightly, 1st + 15th** | Demoted twice since; runs sequentially, not a 3-parallel matrix. The live value is `0 2 1,15 * *` — re-check with the commands above rather than trusting this row |

## Playwright Note

The legislation monitor uses Playwright as a fallback when NSW Legislation returns
HTTP 403 (IP-based blocking). Playwright is NOT installed in the monitors image
to keep it lightweight. If Railway IPs get blocked, either:
1. Add `pip install playwright && playwright install chromium --with-deps` to the Dockerfile
2. Or run the legislation monitor manually on demand (`python scripts/legislation_monitor.py`)

---

# GitHub Actions retirement (June 2026)

GitHub Actions was fully removed. Everything it did now lives in one of two
homes already used by the project:

- **Code-change gates → local git hooks** (`.githooks/`, enabled via
  `git config core.hooksPath .githooks`). `pre-commit` runs the TSC error-count
  gate + secret/large-file/bracket checks; `pre-push` runs pytest (1794+),
  the mutation-baseline ratchet, Jest (615+), QA-report validation, and the
  liability-language scan. Vercel's preview build remains the server-side
  build/type backstop on every push.
- **Scheduled jobs → Railway cron** (this doc).

### What happened to each workflow

| Old workflow | New home |
|---|---|
| `validate.yml` (tsc + build) | pre-commit TSC gate; Vercel preview build |
| `python-tests.yml` (pytest, hypothesis, contracts, QA, liability) | pre-push hook |
| `mutation-gate.yml` (PR mutation comment) | pre-push mutation-baseline ratchet |
| `security.yml` — Semgrep | **Railway cron `maintenance-security`** (below) |
| `security.yml` — npm audit | GitHub **Dependabot** (`.github/dependabot.yml`) — vulnerability alerts, no Actions minutes |
| `stats-refresh.yml` | local/on-demand script (below) |
| `mutation-weekly.yml` (GH issue) | **Railway cron `maintenance-mutation`** (Telegram report) |
| `dcp-monitor` / `dcp-watchdog` | already Railway cron (above) |
| `dcp-extract` / `dcp-commit` | **Railway crons, both DAILY** — `dcp-extract` `0 3 * * *`, `dcp-commit` `0 9 * * *`. This row said "local/on-demand scripts" long after they became scheduled jobs; corrected 2026-09-11 |
| `dependabot-automerge.yml` | dropped — review dependency PRs manually |
| `notify-failure.yml` | `run_monitors.py` Telegram alerting |

## Maintenance cron services (Dockerfile.maintenance)

A second image (`Dockerfile.maintenance`, heavier — bundles Semgrep + the
mutmut/pytest stack) serves the two read-only weekly maintenance jobs through
the same `scripts/run_monitors.py` dispatcher.

| Service Name | MONITOR_NAME | Schedule (UTC) | Notes |
|---|---|---|---|
| `maintenance-security` | `security` | `0 9 * * 1` (weekly Mon) | Semgrep ERROR scan, Telegram summary |
| `maintenance-mutation` | `mutation-health` | `0 6 1 * *` (monthly, 1st) | mutmut kill rate on 3 services, Telegram |

The build + schedule are committed as config-as-code — point each service's
**Settings > Config as code (Config Path)** at its toml and the Dockerfile +
cron are applied automatically:

- `maintenance-security`  -> `railway.maintenance-security.toml`  (cron `0 9 * * 1`)
- `maintenance-mutation`  -> `railway.maintenance-mutation.toml` (cron `0 6 1 * *`)

Env vars are still set per-service in the dashboard (Railway does not manage
secrets via toml): `MONITOR_NAME`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
and optionally `HC_PING_URL`. Neither service writes to the DB.

Mutation runs **monthly** (not weekly) — kill rate decays slowly, so weekly
mutmut compute is wasted. Adjust the cron in the toml if you disagree.

## Run locally / on-demand (not scheduled)

These need a working git checkout or interactive judgement, so they are not
Railway crons:

```bash
# Secondary-dwelling stats refresh (regenerates the checked-in TS + commits)
#   needs DA_SUPABASE_URL, DA_SUPABASE_ANON_KEY in env
python scripts/refresh_stats_job.py

# DCP change pipeline (human-gated). Detection runs weekly on Railway
# (monitor-dcp); extraction + commit are run by you after review:
python scripts/dcp_extract_changed.py --review --council "<COUNCIL>"   # review, no DB writes
python scripts/dcp_extract_changed.py --council "<COUNCIL>"            # commit to production DB
```

> Note: the old `dcp-commit.yml` referenced `scripts/dcp_post_commit_check.py`,
> which no longer exists — that post-commit validation step was already dead.

## Reverting

The workflow files were deleted; recover any from git history
(`git show <commit>:.github/workflows/<name>.yml`) if you ever want Actions back.
