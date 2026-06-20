# Fly.io legislation monitor — deploy / fix

Runs the NSW legislation change monitor from a **stable Sydney IP** so the NSW
Legislation export API (PCO) can whitelist it. The app serves stale-able SEPP/LEP
PDF page images, so it must know when the source legislation changes.

## Why it kept getting suspended
`legislation_monitor.py` is run-once. Deployed as an always-on Fly app it ran ->
exited -> Fly restarted it -> loop -> "restarting too much" -> suspended.
`run_loop.sh` now runs the monitor then sleeps 7 days, in a loop, so the process
never exits. A failed run is logged but does not kill the loop.

## One-time setup (from deploy/flyio-legislation-monitor/)
```bash
# 1. Secrets (without these it crashes every cycle)
fly secrets set -a plotdetect-legislation-monitor \
  DATABASE_URL="<supabase url>" TELEGRAM_BOT_TOKEN="<token>" TELEGRAM_CHAT_ID="<chat id>"

# 2. Deploy the weekly-loop image (clears the restart loop)
fly deploy -a plotdetect-legislation-monitor

# 3. Stable egress IP for the PCO whitelist (~$2/mo; needs a card on Billing)
fly ips allocate-v4 -a plotdetect-legislation-monitor

# 4. Print the outbound IP to give PCO
fly ssh console -a plotdetect-legislation-monitor -C "python check_ip.py"
#    -> OUTBOUND_IP=<the IP to whitelist>
```
Then email PCO to whitelist that IP, or ask for an API key (no IP whitelist needed).

The Railway `monitor-legislation` service can't be whitelisted (its IP changes) —
disable/delete it. Legislation monitoring lives only here.
