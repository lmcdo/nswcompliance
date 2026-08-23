# Linux + DeepSeek Harness Bootstrap Runbook

This runbook is intentionally self-contained so it can be copied to a USB
drive or printed before repartitioning the Windows laptop.

## Goal

Create a Linux dual-boot environment that can:

1. clone and run Compliance Engine reproducibly;
2. run DeepSeek Harness (DSH) against the repository; and
3. retain the repository's existing safety and QA rails when either DSH or
   Codex is used.

## Current repository warning

The first Linux reproducibility repair landed directly on `main` as commit
`50d0157e` (2026-08-21) — it was never pushed as its own branch, so a
`fix/linux-repro-gitignore-holes` branch does not exist on `origin`; a fresh
clone gets this repair simply by being on `main`. That commit:

- stopped `.gitignore` hiding `frontend-nextjs/lib/schemas/*`;
- made the three documented SQL migrations under `frontend-nextjs/migrations/`
  visible to Git;
- marked Windows-only Python dependencies so they're skipped on Linux;
- updated `SETUP.md` with Linux packages and deterministic `npm ci` installs.

A second pass (2026-08-23) found the same gitignore bug one directory level
deeper — `scripts/definitions/`, `scripts/diagnostics/`, `scripts/fixes/`,
`scripts/migrations/`, `scripts/procedural/`, `scripts/sql/`,
`scripts/verification/`, and the root `migrations/` directory were still
losing files to basename globs (`check_*.py`, `fix_*.py`, `*.sql`, ...) that
match at any depth, one level past where the first repair's `!scripts/*.py`-
style negations reach. That pass tracked roughly 70 previously-invisible
files. Verify you're past both repairs before relying on a clone:

```bash
git log --oneline --all --grep="Linux clones reproducible" --grep="scripts.*gitignore" 2>/dev/null
git check-ignore -q scripts/definitions/import_definitions.py && echo "STILL BROKEN" || echo "ok"
```

Do not use `git commit --no-verify`; the normal repository checks must pass.

## 1. Before changing any partition

- [ ] Back up all irreplaceable Windows files to external storage and verify
      that the backup can be read.
- [ ] Save the Windows BitLocker recovery key outside the laptop. Microsoft
      documents the recovery-key process at
      <https://support.microsoft.com/en-us/windows/security/encryption/find-your-bitlocker-recovery-key>.
- [ ] Record the laptop model, disk size, and whether a second SSD is
      available. A second SSD is safer than resizing the Windows system disk.
- [ ] Reserve at least 200 GB for Linux; use 250 GB or more if satellite data,
      caches, or local ML models will be retained.
- [ ] Make a bootable Ubuntu 26.04 LTS USB from the official Ubuntu download.
- [ ] Do not disable Secure Boot merely to install Ubuntu unless the installer
      or a required third-party driver specifically requires it.

Ubuntu 26.04 has improved dual-boot handling for BitLocker-protected Windows
installs, but the BitLocker key and an external backup are still mandatory.
See <https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/>.

## 2. Install Ubuntu safely

1. In Windows, shrink the Windows partition using Disk Management and leave
   the allocated Linux space **unformatted/unallocated**. Do not alter the EFI
   partition or recovery partitions.
2. Boot the Ubuntu USB in **UEFI** mode.
3. Select **Try Ubuntu** first. Confirm Wi-Fi, graphics, sound, suspend/resume,
   keyboard, and an external display if used.
4. Start installation. Choose **Install Ubuntu alongside Windows** or select
   only the known unallocated space / separate SSD.
5. Never select **Erase disk and install Ubuntu** unless intentionally
   replacing Windows.
6. Select Linux disk encryption if offered and keep the passphrase offline.
7. On the first reboot, confirm that both Ubuntu and Windows boot before doing
   any development setup.

Official installation guidance:
<https://documentation.ubuntu.com/desktop/en/26.04/tutorial/install-ubuntu-desktop/>.

If the installer refuses a side-by-side installation because of BitLocker, stop
and reassess rather than manually deleting partitions. Older installer guidance
requires BitLocker to be disabled; do not proceed without the recovery key and
a verified backup:
<https://documentation.ubuntu.com/desktop/en/latest/reference/bitlocker-during-ubuntu-installation/>.

## 3. First Linux boot

Open Terminal and run:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git curl build-essential \
  gdal-bin libgdal-dev libgeos-dev libproj-dev libpq-dev
```

Install current Node.js 20 LTS (at least 20.20) or Node.js 22.22+; the frontend
dependency tree requires a recent Node release. Install a pinned Python 3.11
environment for this repository rather than assuming the distribution's newest
Python is compatible with every pinned scientific/ML package.

Keep project source in the Linux filesystem (for example `~/code/`), not on a
mounted NTFS Windows partition.

## 4. Clone and bootstrap Compliance Engine

Both reproducibility repairs described above are on `main`; no branch switch
is needed.

```bash
mkdir -p ~/code
cd ~/code
git clone <YOUR-REPOSITORY-URL> compliance-engine
cd compliance-engine
git config core.hooksPath .githooks
```

Create the environment files from the repository template. Never copy a secret
into Git, a shell history, a screenshot, or an agent prompt.

```bash
cp .env.example .env
cp .env.example frontend-nextjs/.env.local
chmod 600 .env frontend-nextjs/.env.local
# Edit the two files with the required credentials from the approved stores.
```

Create a Python 3.11 virtual environment and install dependencies:

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-test.txt
```

Install JavaScript dependencies from the committed lockfiles:

```bash
npm ci
cd frontend-nextjs
npm ci
cd ..
```

Initial checks:

```bash
python -m pytest tests/ -x -q --tb=short
cd frontend-nextjs
npm run type-check
npm run build
```

Do not run database migrations against the live Supabase database merely to
test the clone. Follow `DB_SCHEMA.md`, run `scripts/db_safety_check.sh`, and
create a backup before any database operation.

## 5. Install and configure DeepSeek Harness

**Node version caveat:** the DSH GitHub README does not state a minimum Node
version at the time of writing. Third-party install guides (not DeepSeek's own
docs) claim `^22.19.0` or `>=24.x`, which is newer than the Node 20 LTS
installed in step 3 for this repository's frontend. Do not treat either number
as confirmed — run `npx @deepseek-ai/dsh web` and read the actual error if it
refuses to start, or check the README at the URL below before assuming Node 20
is sufficient. If a second Node version is needed, use `nvm` rather than
replacing the version this repository's `SETUP.md` specifies.

The official quick launch is:

```bash
cd ~/code/compliance-engine
npx @deepseek-ai/dsh web
```

The web UI runs on `http://127.0.0.1:3080` by default. In its UI:

1. add the DeepSeek API key under **Settings → Models**;
2. select the cloned Compliance Engine directory as the workspace;
3. use the `workspace-write` permission preset, which asks approval for
   sensitive actions;
4. start with a read-only task: “Summarize this repository and identify its
   main packages.”

DSH is a developer preview. Record the exact DSH/Node version used and check
the official release notes before upgrades:
<https://github.com/deepseek-ai/deepseek-harness>.

## 6. Harness parity requirements

The existing Git hooks are portable and remain the final enforcement point:

- branch guard;
- secret and large-file scans;
- TypeScript baseline gate;
- QA commit-message gate;
- pre-push test and QA validation.

DeepSeek Harness reads both `AGENTS.md` and `CLAUDE.md` by default. The root
`CLAUDE.md` and scoped `CLAUDE.md` files therefore remain usable project
instructions. DSH also supports skills, MCP, plan mode, permissions, hooks,
subagents, and memory through plugins.

The Claude-specific slash-command automation does **not** transfer by itself.
Before relying on DSH for production work, add a repository-owned DSH workflow
that does all of the following before a non-trivial commit:

1. resolves `.qa/reports/<branch-slug>.json` using
   `python scripts/qa_report_path.py --target --relative`;
2. fills the QA report from `scripts/qa_report_template.json` with truthful,
   task-specific evidence;
3. runs `python scripts/qa_gate.py --diff-files <changed-files>`;
4. commits only with the required `QA: Critical|Standard|Minor ...` line.

The JSON report must not be generated as empty theatre. The report is evidence
for the change and its current branch, not a generic permission slip.

## 7. Working with DSH and Codex together

Both harnesses can use the same project rails, but they must not edit the same
worktree concurrently. Use separate worktrees and branches:

```bash
git worktree add ../compliance-engine-dsh -b feat/dsh-workflow
git worktree add ../compliance-engine-codex -b fix/codex-workflow
```

Run one harness in each worktree, with each task committed independently.

## 8. Acceptance test before real work

- [ ] DSH sees the root and scoped project instructions.
- [ ] DSH asks before a write outside the chosen workspace.
- [ ] `git commit` rejects a message without a valid `QA:` line.
- [ ] The QA workflow produces the correct per-branch report and
      `qa_gate.py` accepts it.
- [ ] `git push` runs the repository pre-push checks.
- [ ] Codex can independently read the same repo instructions and pass the
      same Git gates in a separate worktree.
- [ ] Windows still boots successfully after the Linux install.

Do not treat the environment as ready until every item above is checked.
