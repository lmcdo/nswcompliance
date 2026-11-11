#!/usr/bin/env bash
S="$TEMP/qa-frozen-a6d2e378"; O="$TEMP/codex-area"
prompt="$(cat "$S/docs/qa/codex-bench/stance.txt")

$(cat "$S/docs/qa/codex-briefs/served-rules.md")"
start=$(date +%s)
codex exec -C "$S" --skip-git-repo-check --sandbox read-only --ephemeral --ignore-user-config \
  -c windows.sandbox=unelevated -m gpt-5.6-terra -c model_reasoning_effort=high \
  -o "$O/out-served.json" "$prompt" < /dev/null > "$O/log-served.txt" 2>&1
echo "served exit $? $(( $(date +%s) - start ))s blocked=$(grep -c 'blocked by policy' "$O/log-served.txt")"
