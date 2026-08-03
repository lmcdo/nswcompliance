<!-- prior-art-checked: new external-facing portfolio/marketing assets; no existing surface covers outbound positioning (docs/user-stories are product-internal) -->
# Portfolio & Outreach Assets

Working drafts of every external-facing asset for the two objectives:
**contract income first, product IP protected.** Everything here is written
to the blog-content IP rules (`.claude/rules/blog-content.md`): generic
descriptions only, no internal pipeline/algorithm/infrastructure names.

| File | What it is | Where it ends up |
| --- | --- | --- |
| `case-study.md` | The thesis piece: "AI-built, not AI-run" | Blog post / PDF attached to outreach |
| `outreach-kit.md` | Positioning lines, 4 cold-email templates, prospect criteria, cadence | Your email client |
| `background-ip-checklist.md` | Contract clauses to require/refuse before any client engagement | First negotiation (and your lawyer) |
| `github-profile-README.md` | Draft for the github.com profile README | `<username>/<username>` repo |

## Execution sequence

**Week 1 — publish the evidence**
- [ ] Lift `oss/prose-gate/` to a public repo per `oss/prose-gate/EXTRACTION.md`
      (fresh git history; strip guard comments; check PyPI name)
- [ ] Put the GitHub profile README live (edit placeholders first)
- [ ] Publish `case-study.md` (own blog or a gist/LinkedIn article to start —
      distribution matters more than venue)

**Week 2 — build the demo asset + prospect list**
- [ ] Sample report: generate ONE real report from the live product for a
      property you own or have consent to use. Watermark every page
      ("SAMPLE — not for reliance"), export to PDF. This cannot be mocked —
      it must be real output (data-integrity rule applies to marketing too:
      a fabricated sample shown to a council is a credibility bomb).
- [ ] Build the 30-prospect list using the criteria in `outreach-kit.md`
      (start: NSW Early Adopter grant councils, AI Solutions Panel vendors,
      rules-as-code consultancies)

**Week 3+ — outreach loop**
- [ ] 5 personalised emails/week from the templates; one follow-up each at
      +5 business days; log replies
- [ ] Success metric: conversations started, not downloads or stars
- [ ] First contract negotiation: bring `background-ip-checklist.md` to a
      lawyer BEFORE signing anything

## What stays private (the line not to cross in any asset)

- The operations manual: source-by-source extraction methods, per-council
  configs, amendment-monitoring specifics, QA baselines, cost/time curves
- Internal names of pipelines, algorithms, tables, functions
- Defect statistics (until they're mature enough to be a marketing asset)
- The strict internal variant of the language gate and its tuned baselines

Say WHAT the machine does and THAT it is gated. Never HOW to build it.
