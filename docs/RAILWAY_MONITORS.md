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
2. Or run the legislation monitor manually via GitHub Actions (`workflow_dispatch`)

## Reverting to GitHub Actions

The GitHub Actions workflow files still exist with `workflow_dispatch` triggers.
To revert: re-add the `schedule` blocks and remove the Railway cron services.
