# Positioning paragraph — the answer to "tell me about your background"

Two versions. Memorise **Version A** first. It is the honest one and it is the
one to lead with. **Version B** is the fallback if a first read of a room tells
you A is undershooting — a buyer who reads "AI-assisted" as "not really an
engineer" needs the framing that the *judgement* is the product being sold, not
the typing.

Both versions are 60–90 words. Both are truthful about the AI-assisted nature
of the work. Neither claims a credential you don't hold. Read them out loud
until you can deliver either without looking.

---

## Version A — honest, direct (78 words)

> I'm a product owner who spent the last six weeks running an AI-assisted
> reliability campaign on a NSW planning-compliance product I built. Twenty-plus
> PRs, all on GitHub. Claude wrote most of the code; I directed the work, made
> the calls to shut features down when the evidence said shut them down, and
> designed the checks that catch each class of silent failure. I'm now offering
> that as a five-day fixed-price audit on other people's codebases. Everything
> I say I can prove, live, on my laptop.

**Why it works.** Says AI-assisted first, so nobody catches you hiding it.
"Made the calls to shut features down" is the credential — that is the
judgement a buyer is hiring. "Prove, live, on my laptop" makes the demo the
close.

**Where it undersells.** A senior engineer hearing this may file you as "AI
prompter" and stop listening. If the room is engineering-heavy, switch to B.

---

## Version B — recovers plausibility without lying (88 words)

> I built a NSW planning-compliance product solo and spent the last six weeks
> auditing it against a rule I hadn't seen written down elsewhere: before I
> trust a check, I break the code underneath it and prove the check goes red.
> Twenty-plus PRs on GitHub, most with an AI writing the code and me deciding
> what got shipped, shut down, or rewritten. The finding was that a fortnight
> of gates caught real liabilities the existing 4,000-plus tests missed. I run
> that audit on other codebases now, fixed price, five days.

**Why it works.** Leads with the technical rule, which is the actual
intellectual property. The AI framing is still in there ("most with an AI
writing the code") but it lands after the buyer has already registered the
technique. "4,000-plus tests missed" is the concrete number that stops the
"prompter" frame in its tracks.

**Where it risks trouble.** A buyer who asks "which of the 4,000 tests
specifically, and how did you know they missed it" needs you to point at
`STRATEGY_REVIEW_2026-08-08.md` §4 and PR #856. Have that page open in a tab.

---

## What both versions refuse to say

- "I'm a software engineer with X years of experience." You aren't claiming
  that credential. You are claiming a specific technique with receipts.
- "I discovered / invented the technique." Plant-and-restore is old.
  What you did was insist on it as the standing rule for a codebase.
- "The audit catches every bug." It catches specific classes of silent lie.
  Ordinary bugs are somebody else's job.
- "156,000 approved certificates" or any other product-specific number.
  This is a background paragraph, not a pitch for the product. Keep those
  numbers for a different conversation.

---

## What to say if directly challenged

**"So an AI actually wrote your code?"**
"Most of it, yes. My work is the design of the checks, the calls on what to
ship and what to shut down, and the standing rule that no reliability finding
leaves the repo without a planted defect that would have caught it. If you
want, I can walk you through the two PRs where I overruled the AI and shut
down features it was defending — that's the useful bit."

**"What did you personally write?"**
"The commit messages, the QA reports, and the decision trail — those are all
mine. Where I edited code directly, it's in the diff. But the value I'm
selling isn't lines of code; it's the discipline that says a finding without a
planted-defect proof doesn't count as a finding. That discipline is the same
whether I typed the loop body or Claude did."

Both answers refuse the trap. Do not defend against "you didn't really do
it" — accept it and re-anchor on what you did do.
