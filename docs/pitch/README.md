# Pitch package — sources

The seven documents behind the fixed-price reliability-audit offer. **These markdown files are
the source.** The `.docx`, `.html` and `.pdf` a buyer receives are generated from them and are not
tracked here — they are rebuildable and binaries age badly in git.

| File | What it is | Who sees it |
|---|---|---|
| `positioning-paragraph.md` | Two answers to "tell me about your background" | Internal — rehearsal |
| `cheat-sheet.md` | The seven checks, one line each, with the PR for each | Internal — glance at during a call |
| `rehearsal.md` | Ten questions and the traps under them | Internal |
| `red-flags.md` | Four engagement shapes to decline | Internal |
| `demo-runbook.md` | The three-minute live plant-and-restore demo | Internal |
| `qualifying-diagnostic.md` | Three questions and two probes, run before quoting | Buyer-facing |
| `audit-sow-template.md` | One-page scope of work, five days, fixed price | Buyer-facing, signed |

## Regenerating the buyer-facing formats

```bash
cd docs/pitch
for f in *.md; do
  b="${f%.md}"; [ "$b" = "README" ] && continue
  T=$(sed -n 's/^# //p' "$f" | head -1)
  pandoc "$f" -f gfm -t html5 -s --metadata title="$T" -H style.html -o "../../out/$b.html"
  pandoc "$f" -f gfm -o "../../out/$b.docx"
done
```
PDFs are printed from the HTML with headless Chromium (A4, 18/16 mm margins, backgrounds on).

> ⚠ **`style.html` does not exist — this command cannot run as written.** Checked
> 2026-08-17: it is in neither `docs/pitch/` nor the generated `pitch-package/`, so the
> stylesheet that produced the 2026-08-10 HTML was never committed and is gone. This is
> the same failure the section below describes — a rendered artefact whose source was
> discarded — repeated one level up, in the tooling rather than the content. Either drop
> `-H style.html` and accept pandoc's default styling, or write the stylesheet and commit
> it here before regenerating.
>
> **The package contains no images.** No `<img>`, no data URIs, no image files: the PDFs
> are styled text at 69–100 KB. If a buyer-facing version needs a diagram, it does not
> exist yet.

## Why the sources are in the repo at all

The 2026-08-09 edition was generated and the markdown thrown away, so correcting it meant
reverse-engineering seven documents out of their own HTML. Two PR attributions were wrong and a
figure was 26,000 out; neither could be fixed at source because there was no source.

## Standing rule for these documents

**Every claim in them is checkable, so check it before sending.** The 2026-08-10 review found
that two of the seven checks were credited to a PR containing neither of them, one tool was
presented as enforced when it is wired to nothing, and two cited documents did not exist on
`main`. A pitch whose whole subject is verifying claims cannot afford unverified ones — a buyer
who opens a linked PR and finds something unrelated has learned everything they need.

### Re-checked 2026-08-17

**What held.** All seven script paths still exist on `main`, and all seven PR attributions are
correct — each PR genuinely contains the script it is credited with. The 2026-08-10 correction
did its job.

**What did not, and both errors ran the same way — understating the work:**

- **`doc_claims.py` was described as "not yet wired to a hook or CI".** It is wired, and was
  wired by **#890, the very PR that row cites**: `qa_gate.py` loads it through
  `_load_doc_claims()`, and `qa_gate` runs in `pre-push` and in the `gates` workflow. It runs
  in observation mode — reports, never blocks — which is the accurate claim and a stronger one.
  The reason it read as unwired is that nothing greps for `doc_claims` in `.githooks/` or
  `.github/`; the call is a `spec_from_file_location` inside another script. **A check can be
  wired without being named anywhere you would think to look.**
- **"4,024 Python tests"** — `--collect-only` read **5,460** on 2026-08-17. The document now
  carries the command instead of the number, because this figure has now been wrong twice.

**Method note for the next re-check.** Both errors were found by asking the repository rather
than re-reading the document. Grepping for the script name would have confirmed the wrong
answer on `doc_claims`; what settled it was following what `qa_gate.py` actually imports.
