#!/usr/bin/env python3
# prior-art-checked: reuse not viable because nothing checks WHO authored a commit.
# Four sweeps 2026-08-09 vs origin/main ca41fcd1: `git grep -nE "user\.email|author.*email"`
# over scripts/ .githooks/ .github/ returns no identity check; .githooks/pre-commit gates
# branch name, secrets, large files, TSC, bracket lint, fail-soft lint, zone codes and
# fabricated verdicts, none of them authorship; .githooks/pre-push runs pytest, jest,
# qa_gate and the liability scan; .github/workflows/gates.yml and main-red-alarm.yml have
# no identity step; scripts/qa_gate.py validates a report, not a committer.
"""Refuse a commit whose author email cannot belong to a real person.

WHY THIS EXISTS
---------------
Between 2026-08-08 10:19 and 2026-08-09, 49 commits in this repo were authored
``t <t@t>`` because a repo-LOCAL git config overrode a perfectly correct global one.
The consequence was invisible in the place anyone looks: `main` stayed clean, because a
GitHub squash-merge re-authors the result, so all 384 commits on main read correctly and
production deployed fine. Only branch commits carried it, and the only symptom was every
Vercel PREVIEW silently refusing to build -- "GitHub couldn't verify an account for the
commit" -- which reads like a Vercel problem, not a config problem. It went unnoticed for
a day across two parallel sessions, and it also meant a day of commits are attributed to
nobody on GitHub.

WHAT IT CHECKS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
It cannot know which humans are allowed to commit here, and pretending otherwise would
mean a list to maintain and a new way to be wrong. So it checks only that an address is
STRUCTURALLY capable of being real, which is exactly what caught this case:

  * a dot in the domain           -- ``t@t`` has none, nor does ``root@localhost``
  * (deliberately NOT a minimum local-part length: `a@b.co` is a valid address, and my
    own selftest caught that rule rejecting one)
  * a domain that is not a known placeholder (localhost, example.com, test, invalid, ...)
  * a name that is not a single character and not an obvious placeholder
  * not the git default of ``user@hostname`` produced when nothing is configured

A real address that simply is not yours will PASS. That is intentional: this is a
typo/placeholder gate, not an authorisation gate.

WHERE IT RUNS, AND WHY BOTH
---------------------------
`--staged` in the pre-commit hook gives immediate feedback with the fix printed.
`--range` in CI is the one that actually holds: hooks are opt-in per clone, this repo has
15+ worktrees, and commits can arrive from an environment whose hooks nobody installed --
which is the likely origin of this very incident. The retrospective's central finding was
that every gate here was client-side and therefore skippable; adding another hook-only
check would repeat it.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

PLACEHOLDER_DOMAINS = {
    "localhost", "localhost.localdomain", "example.com", "example.org", "test",
    "invalid", "local", "none", "null", "email.com", "domain.com", "t", "x", "a",
}
PLACEHOLDER_NAMES = {
    "t", "x", "a", "test", "user", "root", "admin", "unknown", "your name",
    "yourname", "name", "me", "dev", "developer", "temp",
}
# Bots legitimately use addresses that would otherwise look odd.
ALLOWED_PREFIXES = ("dependabot[bot]", "github-actions[bot]", "renovate[bot]")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")


def problem_with(name: str, email: str) -> str | None:
    """Return a reason this identity cannot be a real person, or None if it is plausible."""
    name = (name or "").strip()
    email = (email or "").strip()

    if any(email.startswith(p) or name.startswith(p) for p in ALLOWED_PREFIXES):
        return None
    if not email:
        return "no author email is set at all"
    if not EMAIL_RE.match(email):
        return f"'{email}' is not a well-formed address"

    local, _, domain = email.partition("@")
    domain_l = domain.lower()

    if "." not in domain:
        return (f"'{email}' has no dot in its domain, so it cannot be a deliverable "
                f"address (this is exactly the t@t case)")
    # partition, not split()[0]: it returns "" on an empty string instead of indexing,
    # so there is no input that can raise here.
    if domain_l in PLACEHOLDER_DOMAINS or domain_l.partition(".")[0] in {"localhost", "invalid"}:
        return f"'{email}' uses the placeholder domain '{domain}'"
    if name.lower() in PLACEHOLDER_NAMES:
        return f"the author name '{name}' is a placeholder, not a person"
    if len(name) < 2:
        return f"the author name '{name}' is a single character"
    return None


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def check_staged() -> int:
    name, email = git("config", "user.name"), git("config", "user.email")
    reason = problem_with(name, email)
    if reason is None:
        return 0
    local_n = git("config", "--local", "user.name")
    local_e = git("config", "--local", "user.email")
    glob_n = git("config", "--global", "user.name")
    glob_e = git("config", "--global", "user.email")

    print("\n  COMMIT AUTHOR REJECTED\n")
    print(f"    this commit would be authored:  {name} <{email}>")
    print(f"    {reason}\n")
    if local_e or local_n:
        print(f"    A REPO-LOCAL override is set and it wins over your global config:")
        print(f"      local :  {local_n or '(unset)'} <{local_e or '(unset)'}>")
        print(f"      global:  {glob_n or '(unset)'} <{glob_e or '(unset)'}>")
        print(f"\n    If the global one is right, delete the override:")
        print(f"      git config --local --unset user.name")
        print(f"      git config --local --unset user.email")
    else:
        print(f"    Set an address registered on your GitHub account:")
        print(f"      git config --global user.name  \"Your Name\"")
        print(f"      git config --global user.email \"you@example.com\"")
    print("\n    Why this is blocking: GitHub cannot attribute a commit whose author it")
    print("    cannot resolve, and Vercel then refuses to build its preview. `main` still")
    print("    looks clean because a squash-merge re-authors the commit, so nothing")
    print("    downstream reveals it. Origin: 49 commits authored t@t, 2026-08-08.\n")
    return 1


def check_range(rev_range: str) -> int:
    out = git("log", rev_range, "--no-merges", "--format=%H%x1f%an%x1f%ae")
    if not out:
        print("author check: no non-merge commits in range — nothing to check")
        return 0
    bad = []
    total = 0
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        total += 1
        sha, name, email = parts
        reason = problem_with(name, email)
        if reason:
            bad.append((sha[:8], name, email, reason))
    if not bad:
        print(f"author check: {total} commit(s), all plausibly authored")
        return 0
    print(f"\n  COMMIT AUTHOR REJECTED — {len(bad)} of {total} commit(s)\n")
    for sha, name, email, reason in bad:
        print(f"    {sha}  {name} <{email}>")
        print(f"              {reason}")
    print("\n    A commit GitHub cannot attribute gets no Vercel preview, and shows as")
    print("    authored by nobody. Fix the identity, then rewrite these commits:")
    print("      git config --local --unset user.email   # if a repo override is set")
    print("      git rebase -r --exec 'git commit --amend --no-edit --reset-author' <base>")
    print()
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Reject placeholder commit authors")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true",
                   help="check the identity the next commit would use")
    g.add_argument("--range", dest="rev_range",
                   help="check every commit in a range, e.g. origin/main..HEAD")
    g.add_argument("--selftest", action="store_true", help="prove the rules bite")
    args = ap.parse_args()

    if args.selftest:
        cases = [
            (("t", "t@t"), True), (("Lawrence McDonell", "l@gmail.com"), False),
            (("root", "root@localhost"), True), (("x", "x@x.com"), True),
            (("Real Person", "real.person@example.com"), True),
            (("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com"), False),
            (("A B", "a@b.co"), False), (("Someone", ""), True),
            (("Someone", "not-an-email"), True),
        ]
        failures = 0
        for (n, e), should_fail in cases:
            got = problem_with(n, e) is not None
            ok = got == should_fail
            failures += not ok
            print(f"  {'ok  ' if ok else 'FAIL'}  {n!r} <{e}>  "
                  f"expected {'reject' if should_fail else 'accept'}, "
                  f"got {'reject' if got else 'accept'}")
        print(f"\n{'selftest passed' if not failures else f'{failures} SELFTEST FAILURES'}")
        return 1 if failures else 0

    return check_staged() if args.staged else check_range(args.rev_range)


if __name__ == "__main__":
    raise SystemExit(main())
