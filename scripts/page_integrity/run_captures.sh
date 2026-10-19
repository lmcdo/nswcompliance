#!/usr/bin/env bash
# usage: run_captures.sh PANEL.tsv OUTROOT  (run from repo worktree root; 4 in parallel)
# SITE_REPORT=1 also fetches the Site Report per address for C7, one at a time, 300 s apart:
# the production route allows ~12 reports per hour.
panel="$1"; out="$2"; mkdir -p "$out"
n=0
while IFS=$'\t' read -r slug q num street suburb; do
  suburb="${suburb%$'\r'}"  # a CRLF checkout of panel.tsv left "WINSTON HILLS\r": no address matched
  [ -z "$slug" ] && continue
  ( python -X utf8 scripts/page_integrity/capture.py "$out/$slug" "$q" --number "$num" --street "$street" --suburb "$suburb" > "$out/$slug.log" 2>&1; echo "$slug exit=$?" ) &
  n=$((n+1)); if [ $((n % 4)) -eq 0 ]; then wait; fi
done < "$panel"
wait
if [ "${SITE_REPORT:-0}" = "1" ]; then
  first=1
  while IFS=$'\t' read -r slug q num street suburb; do
    [ -z "$slug" ] && continue
    [ -d "$out/$slug" ] || continue
    [ "$first" = "1" ] || sleep 300
    first=0
    python -X utf8 scripts/page_integrity/site_report.py "$out/$slug" "$q" >> "$out/$slug.log" 2>&1
    echo "$slug site_report exit=$?"
  done < "$panel"
fi
