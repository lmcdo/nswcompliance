#!/usr/bin/env bash
# Step 1 tool baseline on the frozen copy of a6d2e378. Saves cmd, exit code, raw output, sha256.
S="$TEMP/qa-frozen-a6d2e378"
V="$TEMP/qa-venv/Scripts"
OUT="$1"   # raw output dir
mkdir -p "$OUT"
FE="$S/frontend-nextjs"
NM="/c/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/frontend-nextjs/node_modules"
[ -e "$FE/node_modules" ] || cmd //c mklink /J "$(cygpath -w "$FE/node_modules")" "$(cygpath -w "$NM")" >/dev/null
EX="node_modules,.git,.venv,venv,venv_linux,.next"

run() {  # name, dir, command...
  local name=$1 dir=$2; shift 2
  local start=$(date +%s)
  (cd "$dir" && "$@") > "$OUT/$name.out" 2> "$OUT/$name.err"
  local code=$?
  printf '%s\t%s\t%s\t%ss\t%s\n' "$name" "$code" "$(sha256sum "$OUT/$name.out" | cut -c1-16)" \
    "$(( $(date +%s) - start ))" "cd ${dir#$S}; $*" >> "$OUT/_runs.tsv"
}
: > "$OUT/_runs.tsv"
run ruff_default    "$S" "$V/ruff.exe" check --no-cache --isolated --output-format concise --exclude "$EX" .
run ruff_swallowed  "$S" "$V/ruff.exe" check --no-cache --isolated --select BLE,S110,S112,E722 --output-format concise --exclude "$EX" .
run radon_cc        "$S" "$V/radon.exe" cc -j -i "$EX" .
run radon_mi        "$S" "$V/radon.exe" mi -j -i "$EX" .
run vulture         "$S" "$V/vulture.exe" . --min-confidence 80 --exclude "$EX"
run bandit          "$S" "$V/bandit.exe" -r . -f json -q -x "./frontend-nextjs/node_modules,./.git"
run pip_audit       "$S" "$V/pip-audit.exe" -r requirements.txt -f json --progress-spinner off
run eslint          "$FE" node node_modules/eslint/bin/eslint.js . -f json
run npm_audit       "$FE" npm audit --json
run knip            "$FE" npx --yes knip@6.43.0 --reporter json --no-progress
run madge_circular  "$FE" npx --yes madge@8.0.0 --circular --json --extensions ts,tsx --ts-config tsconfig.json app components lib hooks
run jscpd           "$S" npx --yes jscpd@5.4.2 --silent --reporters json --output "$OUT/jscpd" --ignore "**/node_modules/**,**/.git/**,**/.next/**" --format "python,typescript,tsx,javascript" .
run pydeps_services "$S" "$V/pydeps.exe" services --show-cycles --no-output --no-show
run line_counts     "$S" bash -c 'git ls-files "*.py" "*.ts" "*.tsx" "*.js" "*.jsx" | grep -v node_modules | while read f; do printf "%s\t%s\n" "$(wc -l < "$f")" "$f"; done'
echo DONE
