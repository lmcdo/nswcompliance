<!-- prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md) -->
# prose-gate

**A diff-aware linter that blocks risky assurance language from entering
user-facing text.**

If your product presents analysis of regulated subject matter — property,
planning, financial, legal, health — the words around your data are a legal
surface. Copy that says *"this site is safe to build on"* turns a data
display into something that reads as professional advice. prose-gate is a
zero-dependency gate (pure Python stdlib) that keeps those words out of new
code, in pre-commit and in CI.

```
$ prose-gate --diff-base main
app/report/page.tsx:114: 'guaranteed'
    <p>Council approval is guaranteed for compliant designs.</p>
app/report/page.tsx:114: 'compliant'
    <p>Council approval is guaranteed for compliant designs.</p>

2 finding(s) in 1 file(s).
```

## Why it's different from a word blocklist

1. **Diff-aware.** By default it scans only lines *added* since your base
   branch (`git diff -U0 main...HEAD`). You can adopt it in a ten-year-old
   codebase today: the backlog is not flagged, but every new sentence is
   held to the rule. Audit the backlog separately with `--full`.
2. **It knows code from prose.** `is_verified`, `isVerified` and
   `verified_at` are identifiers, not promises — word-boundary matching
   skips them for free (`_` is a word character). Comments, imports, log
   calls, assertions and declarations are skipped by configurable
   line-context rules. What remains is text a user will read.
3. **Suppressions are visible and countable.** Quoting a source document
   verbatim is legitimate. Mark it inline —
   `<!-- prose-gate: allow(verified) -->` — and the exemption survives code
   review, and can be counted later with `--format json`.

## Install

```bash
pip install prose-gate
```

Requires Python 3.11+. No runtime dependencies.

## Quickstart

```bash
# scan lines added since main (the default mode)
prose-gate

# scan what's staged right now
prose-gate --staged

# audit whole files
prose-gate --full app/report/page.tsx docs/marketing.md

# machine-readable output
prose-gate --format json
```

Exit codes: `0` clean, `1` findings, `2` usage/config error.

## Configuration

Drop a `.prose-gate.toml` in your repo root:

```toml
preset = "assurance"                 # or "financial", "health", or a path to your own TOML
extra_terms = ["flood-proof", "build-ready"]
user_facing = ["*.tsx", "*.jsx", "*.md", "*.html"]   # fnmatch patterns
diff_base = "main"

[exclusions]
comments = true
imports = true
log_calls = true
assertions = true
declarations = true
```

Bundled presets (`prose-gate --list-presets`):

| Preset      | Targets                                                        |
| ----------- | -------------------------------------------------------------- |
| `assurance` | Professional assurance/guarantee words (planning, legal, engineering copy) |
| `financial` | Return promises and risk-minimising phrases                    |
| `health`    | Therapeutic and outcome claims                                 |

Writing your own preset is a 5-line TOML file — see
[docs/custom-presets.md](docs/custom-presets.md).

## In pre-commit

```yaml
repos:
  - repo: https://github.com/OWNER/prose-gate
    rev: v0.1.0
    hooks:
      - id: prose-gate
```

## In GitHub Actions

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0        # needed so the base ref is available to diff
- uses: OWNER/prose-gate@v0.1.0
  with:
    diff-base: origin/main
```

Findings appear as inline PR annotations.

This repository dogfoods itself: CI lints `docs/why.md` with the
`assurance` preset — the essay about assurance language contains none,
except where a pragma marks a deliberate example.

## Limitations (honest ones)

- Line-oriented: a flagged phrase split across a hard line break is missed.
- Heuristics are tuned to prefer false positives over false negatives —
  the pragma is the escape hatch, and it leaves an audit trail.
- Word-boundary matching means inflections need their own entries
  (`guarantee` does not match `guaranteed`); presets carry common forms.
- It gates language, not meaning. *"Flood risk: none"* passes the word
  filter and still over-promises. The gate buys review attention for the
  cases that need a human.

## Why this exists

Longer answer in [docs/why.md](docs/why.md) — the short one: text
generation is getting cheaper and faster than text review, and
deterministic gates are how a small team keeps a large text surface
inside the lines. This tool was extracted from the toolchain of a
production planning-data product, where a stricter version of the
`assurance` preset has gated every push since early 2026.

## License

MIT
