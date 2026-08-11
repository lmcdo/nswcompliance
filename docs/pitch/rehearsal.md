# Rehearsal — the ten questions and the traps underneath

Read aloud. Both the surface answer and the trap answer. Rehearse until neither one requires you to think for more than three seconds.

The point of this list is not to have canned lines. It is to notice, in advance, which questions have a trap under them and which don't — so on the call you know when a follow-up is coming and are already looking at where it lands.

Ordered easiest to hardest. Two of them (Q6 and Q9) are specifically designed to expose whether you are exaggerating your hands-on code role.

------------------------------------------------------------------------

## Q1. "So what is it you're actually offering?"

**Surface answer.** A five-day fixed-price reliability audit. I read your product, I try to plant a defect that would prove one of your product's claims is silently wrong, and if I find one I ship a report with the proof. If I can't, you get a written negative result explaining what I looked for and why I couldn't find it.

**Trap.** *"Isn't that just testing?"*

**Answer to the trap.** No — testing checks that the code does what you told it to. This checks whether the *claims your product makes to users* are things the code is capable of getting wrong. Different axis. On my own codebase, 4,000+ tests were all green through a route that had been broken by a table rename for weeks. Testing didn't catch it. This did.

------------------------------------------------------------------------

## Q2. "How is that different from a security audit or a code review?"

**Surface answer.** Security audits find ways to get in that shouldn't work. Code reviews find style and structure issues. I find statements of fact your product makes to users that turn out to be false — a flood report that says "not in a flood zone" from a check that never ran, a "verified" badge on a scan that produced zero results. Different failure mode. Complementary, not substitute.

**Trap.** *"Fine, so how do we know you'll find anything?"*

**Answer to the trap.** You don't know for certain. That's what the qualifying diagnostic is — a free half-hour where I look at your public surface and either see the shape of something to chase, or say I don't and walk. If I take the engagement, my base rate on my own codebase is that every audit week produced at least one real finding. It's a small sample.

------------------------------------------------------------------------

## Q3. "Show me one of your findings."

**Surface answer.** Open `github.com/lmcdo/nswcompliance/pull/886`. The paid feature — an "adjacent lot construction detector" — had never once returned a positive result in 538 attempts. It was on the price sheet. I shut it down. The PR body has the numbers; the commit message names the customer surfaces I removed it from.

**Trap.** *"Did you write the PR or did the AI?"*

**Answer to the trap.** Claude wrote the code that produced the PR. I made the call to shut the feature down and remove it from nine customer surfaces. The evidence for the call is in the PR body — 538 attempts, zero results — and the decision is mine. If you want to see where I overruled the AI, PR \#886 is the one: the AI was defending the feature and I shut it down anyway.

------------------------------------------------------------------------

## Q4. "What's the deliverable I can show my boss?"

**Surface answer.** Three things — a census script you re-run any time, a QA report in structured JSON that a machine can validate, and at least one finding with a planted-defect proof (or a negative result explaining why there isn't one). Plus a one-hour readout meeting where your engineers ask questions and I answer or say I don't know.

**Trap.** *"So no slide deck?"*

**Answer to the trap.** No. If your boss needs a slide deck, we build one from the report in an hour and I'll help — but the deliverable is the report. Anything the report doesn't back up isn't in the deck.

------------------------------------------------------------------------

## Q5. "Have you done this on someone else's codebase before?"

**Surface answer.** No — this is the first offer. Everything I know about the technique comes from applying it to my own codebase over the last fortnight. Twenty-nine PRs, all on GitHub, all readable. That is the sample.

**Trap.** *"So we're the first customer?"*

**Answer to the trap.** Yes. Which is why the price is banded — the low end of a range that would be higher for a signed reference. Once I have one, the range moves up. What you buy at \$6–10k is the same audit I'll charge \$15k for once someone else has recommended me. That's a real discount, not a sales trick, and it's the only sensible way to price a first engagement.

------------------------------------------------------------------------

## Q6. "How much of the code that produced your findings did you personally write?" — TRAP QUESTION

**Surface answer.** Most of it was written by Claude. I directed the sessions, decided what shipped, wrote the commit messages, wrote the QA reports, and made the calls to shut features down when the evidence said to. Where I edited code directly, it's in the diff. If I said I wrote it, I wrote it; if I said it was AI-assisted, most of the diff is AI.

**Trap.** *"So you're really a prompt engineer, not an engineer."*

**Answer to the trap.** I'm neither. I'm a product owner who found a discipline that works — no reliability finding leaves the repo without a planted defect that would have caught it — and applied it long enough to see whether the discipline holds up. The value I'm selling is the discipline, not the typing. If your view is that a person who directs an AI is not doing engineering, then this isn't a fit and we should end the call — I'm not going to pretend otherwise to close the deal.

------------------------------------------------------------------------

## Q7. "What happens if you don't find anything on our code?"

**Surface answer.** You get the written negative result — what I looked for, why I couldn't plant a proving defect, and what that tells you about where NOT to spend money on hardening. A negative result with evidence is a real deliverable. It has never happened on my codebase; the qualifying diagnostic is designed to catch it before signature.

**Trap.** *"Would you refund us?"*

**Answer to the trap.** If day one convinces me nothing is there, I stop and invoice for the day at \$1,500. The rest isn't owed. That's on page one of the SOW. But this is separate from "the audit ran five days and found nothing" — that outcome is the negative result and it is the deliverable you paid for.

------------------------------------------------------------------------

## Q8. "How do we know the census script you write for us is any good?"

**Surface answer.** Because every check in it maps to a PR on my own repo where the same check caught a real defect. When I write the census for you, I show you the mapping first — "this check corresponds to PR \#859, here's what it caught, here's what it would catch in your code" — before I ship it. And the QA report on the audit itself is validated by `scripts/qa_gate.py`, which requires every `file:line` in it to resolve to real code via AST parsing. So the report can't be plausible-but-wrong.

**Trap.** *"Can we run your gate script against your own audit report?"*

**Answer to the trap.** Yes, and that's the intended check. On day five the report you get includes the exact `python scripts/qa_gate.py <report>.json` command you run to reproduce the validation. If it doesn't pass, don't pay the second half.

------------------------------------------------------------------------

## Q9. "Walk me through how the planted-defect harness actually works." — TRAP QUESTION

**Surface answer.** It's a Python context manager called `planted`. You give it a file, a string to find, and a string to replace it with. It hashes the file, replaces the string, hashes again, and refuses to run the body unless the hash actually changed — a plant that silently no-op'd because of a newline mismatch is the specific failure it exists to catch. On exit — even on a crash — the `finally` block writes the original bytes back and re-hashes to prove the restore. Before it starts, it writes a sidecar backup of the original file; a pre-push git hook refuses to push if any sidecar is on disk, so a plant that died mid-run cannot ship.

**Trap.** *"Which of those design decisions did YOU make?"*

**Answer to the trap.** Three of them. First: fail closed, not open — an earlier version printed "not found" and continued, which is the failure mode of every safety check that fails open, and I told Claude to make it raise. Second: the sidecar has to survive `SIGKILL`, so the pre-push guard is a shell `find` for the sidecar file, not a Python import that could itself be broken. Third: the check for a stuck plant runs in the git hook, not in a test — because a broken test suite can't test itself. Everything else in `falsifiability.py` — the hashing details, the CRLF handling, the atomic sidecar claim — Claude did and I reviewed. If you want to see the review, PR \#890's diff is up.

------------------------------------------------------------------------

## Q10. "Why should we hire you and not someone with fifteen years of engineering behind them?"

**Surface answer.** Someone with fifteen years might well do a better job. I have one thing they might not: a specific rule I applied for a fortnight straight to a codebase I know intimately, and the twenty-nine PRs where applying it caught real liabilities. If a fifteen-year engineer comes with that same evidence, hire them. If they come with a resume and no receipts, this is the safer bet at this price.

**Trap.** *"So you're saying you're cheaper?"*

**Answer to the trap.** Cheaper and specific. A senior engineer's hourly rate makes a five-day fixed-price hard for them; they'd rather hourly and open-ended. I can price this way because the deliverable is scoped and because I'm early and building signal. The price will move up when the signal is there; the offer won't change.

------------------------------------------------------------------------

## Two things that go in every answer, without being said explicitly

- **You know exactly what you are and are not selling.** No credential is claimed that isn't earned. No sentence begins with "I'm the kind of person who…" — every claim points at a PR, a commit, or a decision.
- **You are willing to end the call.** Q6 and Q10 both include a version of "then this isn't a fit." That is the option that keeps every other answer believable. Buyers who feel you need the deal will trust you less than buyers who feel you'd rather not close a bad one.

------------------------------------------------------------------------

## How to rehearse this

Read every question out loud, then answer without looking. Time yourself. The surface answer should take under 30 seconds; the trap answer under 20. If either takes longer, you don't know the answer well enough to say it in front of someone with money.

Do it three times before the first call. Do it once again the morning of. Every call after the first, drop the ones you're already comfortable with, and keep rehearsing Q6 and Q9 forever — those two never get easier because the trap under each moves with each buyer.
