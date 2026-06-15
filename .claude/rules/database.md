---
globs:
  - "**/*migration*"
  - "**/*schema*"
  - "scripts/db_*"
  - "services/**"
  - "src/**"
---

# Database Rules

- Before any session involving DB queries, schema changes, or bulk operations: use dbcheck skill
- Read `DB_SCHEMA.md` before writing queries
