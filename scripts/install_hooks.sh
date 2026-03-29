#!/usr/bin/env bash
# Install git hooks from scripts/hooks/ into .git/hooks/.
# Run once after cloning, and after any hook change.
# Called automatically by: npm install (via package.json prepare script) — see below.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="$REPO_ROOT/scripts/hooks"
HOOKS_DEST="$REPO_ROOT/.git/hooks"

echo "Installing git hooks..."

for hook in "$HOOKS_SRC"/*; do
  name=$(basename "$hook")
  dest="$HOOKS_DEST/$name"
  cp "$hook" "$dest"
  chmod +x "$dest"
  echo "  ✅ $name"
done

echo "Done."
