<!-- prior-art-checked: new draft for external GitHub profile README; no existing profile asset in repo -->
# Draft: GitHub profile README

*Copy into a public repo named `<username>/<username>` (its README shows
on your profile page). Edit the [placeholders]. Keep it under one
screen — it's a landing page, not a CV.*

---

## Lawrence McDonell

I build **verification layers for AI systems working over regulatory
data** — pipelines where every answer cites its source clause, and the
model never gets the last word.

**Current:** a production planning-compliance engine for NSW, Australia.
47,000+ regulatory provisions extracted from planning instruments and
served with per-clause source references and effective dates. AI assists
extraction; deterministic release gates re-verify every stored value
against its own quoted source text; 2,400+ tests enforced as a ratchet
on every push. The product is private — the discipline is public:

- **[prose-gate]([LINK])** — a diff-aware linter that blocks liability
  language ("guaranteed", "compliant", "verified"…) from entering
  user-facing text. Zero dependencies, pre-commit + GitHub Action,
  extracted from the engine's own push gates. Its docs are linted by its
  own strictest preset in CI.
- **[Case study]([LINK])** — *AI-built, not AI-run*: why the answer
  layer of a compliance product must be deterministic, and how LLM-era
  extraction makes the 1990s expert-system guarantees affordable again.

**Background:** shipped commercial interactive software in the
Macromedia Director era; returned to building after years in
[field/role]; chose the hardest reliability problem I could find in my
own backyard.

**Available for contract work:** AI-output verification and QA,
provenance-gated data pipelines, regulatory data extraction.
📫 [email] · [product link]

---

*Notes (delete before publishing):*
- *Pin the prose-gate repo + this profile repo. Two good pins beat six
  mediocre ones.*
- *The contribution graph will be sparse — the "Current" paragraph
  pre-empts it: production work happens in a private repo. Anyone who
  needs proof can be invited as a read-only collaborator for a week.*
- *Update the [field/role] line honestly — the comeback story only works
  if every clause of it is checkable.*
