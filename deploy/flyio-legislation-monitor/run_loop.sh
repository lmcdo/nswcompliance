#!/bin/sh
# Run the NSW legislation monitor once a week from inside the container.
# WHY: this is a run-once script, but it's deployed as an always-on Fly app —
# an always-on app that *exits* gets restart-looped by Fly and then suspended
# ("machines restarting too much"). Looping internally keeps the process alive,
# so the machine stays healthy and the monitor runs weekly. A failed run (e.g.
# missing secret or a PCO 403) is logged but does NOT kill the loop.
#
# PCO's allow-list condition is "run outside Sydney business hours". Each run
# (including the first one after a deploy or restart) waits until 19:00-05:59
# Sydney time. On 2026-11-02 a restart ran it at 16:46 Sydney and every page 403'd.
after_hours() {
  h=$(TZ=Australia/Sydney date +%H)
  [ "$h" -ge 19 ] || [ "$h" -lt 6 ]
}
while true; do
  until after_hours; do
    echo "[run_loop] $(TZ=Australia/Sydney date '+%H:%M') Sydney is business hours; waiting"
    sleep 1800
  done
  echo "[run_loop] $(date -u '+%Y-%m-%d %H:%M:%S UTC'): running legislation monitor"
  python legislation_monitor.py || echo "[run_loop] monitor exited non-zero — will retry next cycle"
  echo "[run_loop] sleeping 7 days"
  sleep 604800
done
