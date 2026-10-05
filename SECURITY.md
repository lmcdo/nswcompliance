# Security and public-release policy

This document records the current security boundary for preparing the repository for public GitHub publication.

## Never publish

Keep these outside the public repository:

- `.env`, `.env.local`, production environment files, and deployment exports
- API keys, access tokens, passwords, private keys, certificates, and service-role credentials
- Database dumps, rollback exports, local database files, and private review queues
- Personal information, customer or lead data, private addresses, and operational logs
- Internal prompts, agent instructions, tool state, and private development transcripts
- Raw source corpora or generated datasets whose redistribution rights are not established
- Deployment configuration containing private endpoints, credentials, or internal operational details

`.gitignore` is not a security boundary. A file that was previously committed remains in Git history even after it is ignored or deleted from the working tree.

## Current repository findings

The working tree contains local environment files and a tracked `config/secrets-manager.js`. It also contains tracked database backup material, large regulatory source documents, generated data, and numerous local worktrees under `.claude/worktrees`.

These items require classification before publication. Their presence does not by itself establish that a credential is valid, but they must not be treated as public-safe without review.

No credential values are documented here.

## Handling a suspected secret

1. Do not paste or commit the value.
2. Identify the path and secret type without exposing the value.
3. Revoke or rotate the credential through its provider.
4. Determine whether it is present in current files, Git history, or a pushed ref.
5. Remove or redact the affected material using an approved history-remediation process.
6. Re-scan the working tree, reachable history, remote repository, and release artifact.

History rewriting is not a substitute for credential rotation.

## Public-release checks

Before publication, perform a clean-clone audit that verifies:

- no environment files or credentials are tracked
- no database dumps or personal data are present
- no private source corpus is included without redistribution permission
- no internal prompts or operational secrets remain
- the documented setup works without private infrastructure, or clearly identifies required private dependencies
- all quantitative claims are backed by reproducible evaluation artifacts
- regulatory outputs are described as decision support rather than legal or guaranteed compliance advice

## Current preservation

A local Git bundle named `.audit-preservation-2026-09-23.bundle` preserves the current reachable history. It is ignored by Git and must remain private.
