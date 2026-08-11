#!/usr/bin/env bash
# Choose the base commit for the Sol cross-review.
#
# Usage: sol_review_base.sh <merge_base_with_main>
# Prints one commit sha on stdout. Never fails: on any doubt it prints the
# argument it was given, which is the old, conservative behaviour.
#
# WHY THIS EXISTS
# ---------------
# The review used to always read the merge-base with main, so every push
# re-read the ENTIRE branch. On fix/flood-finish (2026-08-10) that meant four
# consecutive blocked pushes each re-reading the same 2,500-line diff. A model
# reading that much does not return the same subset of findings twice, so each
# run surfaced different ones from an unchanged pool — including files last
# touched days earlier that earlier runs had said nothing about. Fixing
# everything found in run N did not reduce what run N+1 could find, and each fix
# made the diff bigger. A non-deterministic sampler is a fine reviewer and a bad
# gate: it has no fixed point unless the input shrinks.
#
# THE CHOICE
# ----------
# Two candidate boundaries; the correct one is whichever is LATER:
#
#   - merge-base with main: excludes commits that came from main, but includes
#     everything this branch has ever done.
#   - the last pushed commit: exactly "what is new since the last review" —
#     UNLESS main was merged into the branch after that push, in which case it
#     also drags in all of main's already-reviewed work. Measured: naively using
#     the last push on fix/flood-finish gave 66 files / 476 KB against the
#     merge-base's 18 files, because a merge of origin/main sat between them.
#
# KNOWN LIMITATION, stated rather than hidden: merging main into a branch resets
# the review to the full branch. That is defensible — branch code combined with
# new main code is genuinely unreviewed in combination — but a long-lived branch
# that keeps merging main keeps paying for a full re-read.
set -u

DUP_BASE="${1:-}"
if [ -z "$DUP_BASE" ]; then
  echo "origin/main"
  exit 0
fi

SOL_BASE="$DUP_BASE"

# An upstream that is NOT an ancestor of HEAD means the branch was rebased or
# force-pushed. The stored boundary no longer describes any commit on this
# history, so it tells us nothing and is ignored.
if git rev-parse --verify --quiet "@{u}" >/dev/null 2>&1 \
   && git merge-base --is-ancestor "@{u}" HEAD 2>/dev/null; then
  SOL_UP=$(git rev-parse "@{u}" 2>/dev/null || echo "")
  # Is the last push a DESCENDANT of the merge-base? Then it is the later
  # boundary, and the right one. If not, main was merged in after that push.
  if [ -n "$SOL_UP" ] && git merge-base --is-ancestor "$DUP_BASE" "$SOL_UP" 2>/dev/null; then
    SOL_BASE="$SOL_UP"
  fi
fi

echo "$SOL_BASE"
