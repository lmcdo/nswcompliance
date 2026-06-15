---
globs:
  - "enrichment/**"
  - "scripts/*lga*"
  - "scripts/*dcp*"
  - "scripts/*provision*"
---

# Enrichment & DCP Pipeline Rules

- LGA onboarding: read `docs/DCP_SCOPE_CONFIG_REFERENCE.md` first. Full rules: `enrichment/CLAUDE.md`
- Provision tagging with `v2_applicable_dev_types`: use tag-provisions skill. Run `/classify-lga` first.
- Adding/modifying provision fields, filter rules, section keys, PDF export: run `/dcp-pipeline-checklist` first
