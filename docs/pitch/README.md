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
