#!/usr/bin/env bash
# usage: run_captures.sh PANEL.tsv OUTROOT  (run from repo worktree root; 4 in parallel)
panel="$1"; out="$2"; mkdir -p "$out"
n=0
while IFS=$'\t' read -r slug q num street suburb; do
  [ -z "$slug" ] && continue
  ( python -X utf8 scripts/page_integrity/capture.py "$out/$slug" "$q" --number "$num" --street "$street" --suburb "$suburb" > "$out/$slug.log" 2>&1; echo "$slug exit=$?" ) &
  n=$((n+1)); if [ $((n % 4)) -eq 0 ]; then wait; fi
done < "$panel"
wait
