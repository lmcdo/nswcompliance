#!/usr/bin/env bash
# Re-run of 3 tools that failed on setup in step1_run.sh (logged as attempt 2, first attempt kept).
S="$TEMP/qa-frozen-a6d2e378"; V="$TEMP/qa-venv/Scripts"; OUT="$1"; FE="$S/frontend-nextjs"
run() { local name=$1 dir=$2; shift 2; local start=$(date +%s)
  (cd "$dir" && "$@") > "$OUT/$name.out" 2> "$OUT/$name.err"; local code=$?
  printf '%s\t%s\t%s\t%ss\t%s\n' "$name" "$code" "$(sha256sum "$OUT/$name.out" | cut -c1-16)" "$(( $(date +%s) - start ))" "cd ${dir#$S}; $*" >> "$OUT/_runs.tsv"; }
run eslint_try2    "$FE" node node_modules/eslint/bin/eslint.js . -f json
run knip_try2      "$FE" npx --yes knip@6.43.0 --reporter json --no-progress
run pip_audit_try2 "$S" "$V/pip-audit.exe" -r requirements.txt --no-deps --disable-pip -f json --progress-spinner off
echo DONE
