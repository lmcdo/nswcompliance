# Railway Monitor Cron Services

Monitoring infrastructure moved from GitHub Actions to Railway cron jobs (May 2026)
to avoid burning Actions minutes.

## Architecture

One Docker image (`Dockerfile.monitors`) serves all 4 monitors. Each Railway cron
service sets `MONITOR_NAME` to select which monitor runs. The entrypoint is
`scripts/run_monitors.py`.

## Services to Create in Railway Dashboard

Create 4 cron services in the same Railway project as the API:

| Service Name | MONITOR_NAME | Schedule (UTC) | Schedule (AEST) | Notes |
|---|---|---|---|---|
| `monitor-satellite` | `satellite-freshness` | `0 6 * * 1` | Mon 16:00 | Weekly, was daily |
| `monitor-legislation` | `legislation` | `0 8 * * 1` | Mon 18:00 | Weekly Mon |
| `monitor-dcp` | `dcp-monitor` | `0 2 * * 1` | Mon 12:00 | Weekly Mon, all councils sequential |
| `monitor-watchdog` | `dcp-watchdog` | `0 10 * * 3` | Wed 20:00 | Weekly Wed (after Mon DCP run) |

### Creating Each Service

1. Railway Dashboard > Project > New Service > Cron Job
2. Connect to the `nswcompliance` GitHub repo
3. Set **Dockerfile Path** to `Dockerfile.monitors`
4. Set **Start Command** to `python scripts/run_monitors.py`
5. Set the cron schedule
6. Add environment variables (see below)

### Environment Variables

All services need:
- `MONITOR_NAME` — the monitor to run (see table above)
- `DATABASE_URL` — Supabase connection string
- `TELEGRAM_BOT_TOKEN` — VerifyOpsBot token
- `TELEGRAM_CHAT_ID` — alert channel ID

Per-service extras:
- `monitor-satellite`: `GOOGLE_MAPS_API_KEY`, `HC_PING_URL` (= HC_PING_SATELLITE_MONITOR)
- `monitor-legislation`: `HC_PING_URL` (= HC_PING_LEGISLATION_MONITOR)
- `monitor-dcp`: `R2_ACCOUNT_ID`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `HC_PING_URL` (= HC_PING_DCP_MONITOR)
- `monitor-watchdog`: no extras

### Schedule Changes from GitHub Actions

| Monitor | Was | Now | Why |
|---|---|---|---|
| Satellite freshness | Daily | Weekly (Mon) | Reports fail visibly if API is down; weekly detection is sufficient |
| DCP watchdog | Daily | Weekly (Wed) | DCP monitor runs Mon; stuck extractions caught Wed (2-day window vs 25hr threshold still fine) |
| Legislation | Weekly Mon | Weekly Mon | No change |
| DCP monitor | Weekly Mon | Weekly Mon | No change, but runs sequentially instead of 3-parallel matrix |

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
| `dcp-extract` / `dcp-commit` | local/on-demand scripts (below) |
| `dependabot-automerge.yml` | dropped — review dependency PRs manually |
| `notify-failure.yml` | `run_monitors.py` Telegram alerting |

## Maintenance cron services (Dockerfile.maintenance)

A second image (`Dockerfile.maintenance`, heavier — bundles Semgrep + the
mutmut/pytest stack) serves the two read-only weekly maintenance jobs through
the same `scripts/run_monitors.py` dispatcher.

| Service Name | MONITOR_NAME | Schedule (UTC) | Notes |
|---|---|---|---|
| `maintenance-security` | `security` | `0 9 * * 1` | Semgrep ERROR scan, Telegram summary |
| `maintenance-mutation` | `mutation-health` | `0 6 * * 1` | mutmut kill rate on 3 services, Telegram |

Create each like the monitor services, but set **Dockerfile Path** to
`Dockerfile.maintenance`. Env vars: `MONITOR_NAME`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`, and optionally `HC_PING_URL`. Neither writes to the DB.

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
