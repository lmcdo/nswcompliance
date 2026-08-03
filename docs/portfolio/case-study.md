<!-- prior-art-checked: new external-facing case study; no existing external marketing surface exists (docs/user-stories are product-internal) -->
# AI-built, not AI-run: a planning-compliance engine that never lets the model answer

*Draft for publication. Placeholders in [brackets]. Written to IP rules:
generic descriptions only — say what the machine does, never how.*

---

In 2026, AI permitting tools cleared plans in days that used to take
months. Then the second wave of headlines arrived: pilot programs
reporting 87–92% accuracy, courts logging over 1,600 incidents of
hallucinated citations, and the question nobody had priced in — *who pays
when the AI is wrong?*

I build planning-compliance software for NSW, Australia, and I started
from that question instead of arriving at it.

## The rule the whole system is built around

**The model never answers.** Not "rarely", not "with a disclaimer" —
never. When my product tells a user what planning controls apply to a
property, that answer is a database lookup over regulatory provisions
that were extracted from the source instruments, stored with their exact
source text, section reference and effective date. No generative step
sits between the database and the user.

AI is used in one place only: **ingest**. Language models are genuinely
good at reading a 400-page development control plan and proposing
structure — and genuinely dangerous at being believed. So the pipeline
treats every model output as a claim to be verified, not a fact to be
served:

- Every extracted numeric control is stored **with the quoted source text
  it came from**. Release gates re-derive each number from its own quote
  by named, deterministic rules. A value that can't be traced to its
  quote blocks the release — an unattributable control is
  indistinguishable from a guess.
- Every provision carries a **section reference and effective date**, so
  any answer can be checked against the instrument by a human in
  seconds.
- Source instruments are **monitored for amendments**, because planning
  rules change constantly and a database that was right in March is a
  liability in June. Encoding once is easy; staying true is the product.

## The same discipline, all the way down

The verification posture isn't one feature — it's the whole toolchain.
The codebase ships behind gates that:

- run **2,400+ automated tests** on every push, with test counts enforced
  as a ratchet (the number may rise, never silently fall);
- apply **mutation-testing baselines**, because a test suite that can't
  detect a sabotaged function is decoration;
- block any new user-facing sentence containing **assurance language** —
  words like "guaranteed", "compliant" or "verified" — unless it is a
  quotation from a source document, because interface copy is a legal
  surface too. (I've open-sourced a generic version of that gate:
  [prose-gate]([LINK]) — its own documentation is linted by its own
  strictest preset in CI, and yes, the first run caught two mistakes in
  the essay explaining why it exists.)

## Why this architecture, and why now

Deterministic compliance engines aren't new — governments have been
hand-encoding legislation into rule systems since the 1990s. Those
systems were trustworthy and unaffordable: teams of specialists, years
per statute, and corpora that rotted as the law moved. The new AI tools
inverted the trade: nearly free to build, impossible to fully trust at
the moment of answer.

LLM-assisted extraction collapses the old encoding cost. Deterministic
gates restore the old guarantees. The combination — **AI at ingest,
inside a cage of verification; deterministic at answer** — is the
resolution of a forty-year trade-off, and one person can now operate it:
the system currently serves 47,000+ provisions across 100+ planning
precincts, maintained solo.

## What this is for

Two things.

If you're a **council or government team evaluating AI planning tools**:
the pilots are worth running, and their outputs are worth verifying
independently. That verification — deterministic, clause-cited,
repeatable — is what I do. I'm available for pilot QA and evaluation
work.

If you're a **team shipping LLM features over regulated or messy
government data** and the phrase "the model never answers" sounds like
something you wish your pipeline could say: I take contract engagements
building exactly this kind of verification layer.

**[Name] — [email] — [product link] — [GitHub link]**

---
*[Optional closing note: sample report with per-clause citations
available on request.]*
