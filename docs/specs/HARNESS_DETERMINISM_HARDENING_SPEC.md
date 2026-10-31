# Harness Determinism Hardening — Spec

Status: DRAFT for approval · 2026-10-31 · branch `ccr-95b51a22-n5fbgc`

## What
Close the gaps that let a model session break data correctness without any code stopping it.

## Why
Static audit (2026-10-31): **0/10** failure modes fully code-enforced, 7 partial, 3 none.
Database writes have **no** harness, git or CI gate at all:
`grep -rhoE 'psycopg2\.connect' --include=*.py enrichment scripts services src | wc -l` → **843** direct
connection sites; 90 of 257 DB-writing files carry no backup/dry-run/`--apply` reference
(command in §7). Live-DB exposure: **UNKNOWN** (no `DATABASE_URL` in the audit session).

## 1. Design principle
Enforce at the **narrowest unavoidable choke point**, not at the call site.

| Layer | Bypassable by the model? | Use for |
|---|---|---|
| Database privileges (Postgres roles) | No (unless it holds the credential) | All writes |
| CI on `pull_request` + merge guard | No (runs off-machine) | Code, tests, baselines |
| Claude PreToolUse hooks | Partly (pattern matching) | Early, cheap feedback |
| git hooks | Yes (`--no-verify`) | Convenience only |
| CLAUDE.md text | Yes | Explanation, never enforcement |

843 connect sites cannot be guarded one by one; **the database is the only choke point
that covers all of them.** Hooks become the fast first warning; Postgres and CI are the guarantee.

## 2. Workstreams

### W1 — Write path: database-enforced (closes modes 1, 3, 7 for data) — P1
1. **Roles.** Create `agent_ro` (SELECT only) and `pipeline_writer` (INSERT/UPDATE on named
   tables; no DELETE/TRUNCATE/DDL). Model sessions receive **only** the `agent_ro` DSN as
   `DATABASE_URL`. `pipeline_writer` DSN lives in a separate env var (`DATABASE_WRITE_URL`)
   that is never placed in a Claude session environment.
2. **Write ticket.** All writes go through one new module `src/db/write_session.py`:
   `with write_session(ticket=...) as cur:` which (a) refuses without `DATABASE_WRITE_URL`,
   (b) requires `--apply` (default dry-run: run in a transaction, print row counts, ROLLBACK),
   (c) verifies a backup newer than 60 min exists for every target table
   (`scripts/backup_database.sh` output manifest), (d) sets `SET LOCAL statement_timeout='30s'`,
   (e) sets `SET LOCAL application_name='<script>:<ticket>'`.
3. **Audit trigger.** Postgres trigger on `regulatory_provisions`, `dcp_setback_controls`
   and every other table `pipeline_writer` can write: logs `application_name`, txid, op, old/new row hash to
   `write_audit_log`. A write with no ticket in `application_name` raises an exception
   inside the trigger — enforcement lives in the DB, not in Python.
4. **Migration of the 257 writers** is incremental: a CI ratchet
   (`scripts/check_direct_db_writes.py --baseline`) counts direct `psycopg2.connect` +
   write-SQL files; the count may only fall. Starts at the measured value, target 0.

### W2 — Gate integrity (mode 6) — P1
- CI step `scripts/check_gate_files_changed.py`: if a PR touches `*baseline*.json`,
  `collect_ignore`, `mutation-baselines.json`, `.githooks/**`, `.claude/hooks/**`,
  `.claude/settings.json`, or `.github/workflows/**`, the PR body must contain a
  `## Gate change` section naming each file + reason; otherwise `gates` fails.
- Ratchet files may move only in the improving direction (already true for quarantine;
  extend the same check to every baseline).

### W3 — Hook coverage fixes (modes 4, 7) — P2
- `surface-prior-art-guard.py` matcher: `Artifact|mcp__claude-artifacts__publish_.*|mcp__claude-artifacts__edit_version`.
- `prior-art-guard.py`: also on `Bash`, when the command writes a file (`>`, `tee`, `sed -i`,
  heredoc to a path under a watched dir).
- New `Bash` hook `no-verify-guard.py`: blocks `--no-verify`, `-n` on commit,
  `core.hooksPath` changes away from `.githooks`, and `PGPASSWORD=`/`psql` with a write DSN.
- Every guard **fails closed** for its block condition, **fails open** only on its own
  internal error, and logs that error to `.claude/hook-errors.log` (counted in W6).

### W4 — Verbatim extraction (mode 3) — P2
- CI + pipeline check `scripts/check_verbatim_provisions.py`: for each new/changed provision,
  normalised text (whitespace, hyphenation, ligatures only) must be a substring of the
  stored source-document text at the cited page. Mismatch → row rejected (`v2_is_actionable=false`,
  reason recorded), never silently served. Deterministic; no model in the loop.

### W5 — Claims carry evidence (modes 2, 5, 9, 10) — P3
- `done-when-gate.py` upgrade: the DONE WHEN command must appear in this turn's Bash
  tool calls and its output must contain the reported value. Format alone no longer passes.
- Subagent results: same rule — a figure in a subagent report counts only if the parent
  re-runs the command or the subagent output includes the command + raw output.

### W6 — Compaction survival (mode 8) — P3
- `PreCompact` hook writes `.claude/state/session-ledger.json` (branch, worktree, PRs,
  every DONE WHEN command+value, production writes from `write_audit_log` for this
  session's `application_name`). `SessionStart` (source=compact) re-injects it. Facts are
  restored from the file, not from the model's summary.

## 3. Out of scope
Making the model itself deterministic (not possible: same input does not guarantee same tokens);
reviewer quality of Sol; product-surface UI changes.

## 4. Correctness rules for every component
- Unknown ≠ zero: every probe prints `UNKNOWN (<reason>)` when it cannot measure.
- No component ever writes production data in its own tests; DB tests use `PYTEST_REAL_DB=1`
  against a branch database only.
- Each component ships with: expected-case, edge-case, failure-case test, and a mutation
  check (`return allow` / `return []` must make a test fail).

## 5. Sequencing
W1.1 roles (one day, highest leverage: removes write capability from model sessions
outright) → W2 → W3 → W1.2–1.4 → W4 → W5 → W6. Each is its own PR.

## 6. Risks
- W1.1 needs Supabase dashboard access by the owner; a model session cannot (and must
  not) create its own write role.
- Existing cron jobs (Railway) must get `DATABASE_WRITE_URL` before `agent_ro` replaces
  `DATABASE_URL` anywhere, or they fail closed — verify with `check_railway_cron_drift.py`.

## 7. Definition of done
New probe `scripts/harness_exposure_probe.py` (part of W2 PR) scores each of the 10 modes
from code facts (hook matchers, CI steps, role grants via `has_table_privilege`) and prints
`exposed: N/10`.

**DONE WHEN:** `python scripts/harness_exposure_probe.py` prints `exposed: 0/10` **and**
`python scripts/check_direct_db_writes.py --count` prints `0`.

Baseline commands (2026-10-31):
```
grep -rlE '\b(INSERT INTO|UPDATE [a-z_]+ SET|DELETE FROM)' --include=*.py enrichment scripts services src | wc -l   # 257
… | xargs grep -lE 'backup|dry.run|--apply' | wc -l                                                               # 167
```
