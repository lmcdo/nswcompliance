#!/usr/bin/env bash
# Step 2: Codex on 5 stripped pre-fix exports. Settings pinned in docs/qa/review-protocol.md.
B="$TEMP/codex-bench"
go() { n=$1 area=$2
  prompt="$(cat "$B/stance.txt")
$(cat "$B/area-$area.txt")"
  start=$(date +%s)
  codex exec -C "$B/case-$n" --skip-git-repo-check --sandbox read-only --ephemeral --ignore-user-config \
    -c windows.sandbox=unelevated -m gpt-5.6-terra -c model_reasoning_effort=high \
    -o "$B/out-$n.json" "$prompt" < /dev/null > "$B/log-$n.txt" 2>&1
  echo "case-$n exit $? $(( $(date +%s) - start ))s blocked=$(grep -c 'blocked by policy' "$B/log-$n.txt")" >> "$B/runs.txt"; }
: > "$B/runs.txt"
go 1492 monitor & go 1491 monitor & go 1490 served & go 1489 served & go 1481 served & wait
echo ALL DONE
