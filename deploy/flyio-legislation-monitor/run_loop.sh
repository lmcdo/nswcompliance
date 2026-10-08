#!/bin/sh
# Run the NSW legislation monitor once a week from inside the container.
# WHY: this is a run-once script, but it's deployed as an always-on Fly app —
# an always-on app that *exits* gets restart-looped by Fly and then suspended
# ("machines restarting too much"). Looping internally keeps the process alive,
# so the machine stays healthy and the monitor runs weekly. A failed run (e.g.
# missing secret or a PCO 403) is logged but does NOT kill the loop.
while true; do
  echo "[run_loop] $(date -u '+%Y-%m-%d %H:%M:%S UTC'): running legislation monitor"
  python legislation_monitor.py || echo "[run_loop] monitor exited non-zero — will retry next cycle"
  echo "[run_loop] $(date -u '+%Y-%m-%d %H:%M:%S UTC'): running provenance check"
  python provenance_check.py || echo "[run_loop] provenance check FAILED (alert sent) — see output above"
  echo "[run_loop] sleeping 7 days"
  sleep 604800
done
