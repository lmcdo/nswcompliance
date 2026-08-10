# What to sell, and why — the landing after the August 2026 reliability campaign

**Written 2026-08-08, in plain English, to be read away from the code.**
Detail lives in `~/.claude/plans/ce-calibration-execution-plan-2026-08.md` §6 and
`~/.claude/plans/ce-product-assurance-position-2026-08.md`. This is the argument, not the log.

---

> ## ⚠ RETRACTION — 2026-08-10
>
> **Section 4 of this document was wrong and is withdrawn.** It recommended leading with the
> complying-development certificate archive. Three of its load-bearing claims were tested two days
> after it was written and none survived:
>
> - **"Nobody can copy it without eight years of collecting."** False. The records come from the
>   NSW Planning Portal, which is public and unauthenticated. This repo's own
>   `memory/reference-da-tracking-mapserver.md` documents a no-auth endpoint carrying ~324,000
>   application records with outcome, cost, dwellings, floor area and coordinates, paginated 4,000
>   at a time. A competent developer rebuilds it in days.
> - **"What the council actually waved through."** Observes nothing. Complying development is a
>   *non-discretionary* pathway — meeting the standards produces the certificate. Where a council
>   actually exercises judgement is development applications, and there the archive is 62,016 rows
>   reaching back only to May 2025. The eight years of depth sit where depth means least.
> - **"A question no competitor can touch."** ~97% of determined applications are approved
>   (149,118 against 4,272 refused). A differentiator has to discriminate; this one cannot.
>
> **All three were checkable in minutes and none of them were checked** — including by the author
> of this document, in the document arguing that unverified derived claims are the whole problem.
> That is the error itself, committed inside its own statement. Left visible rather than edited
> out, because a retraction that hides what was claimed teaches nothing.
>
> Sections 1, 2, 3 and 6 stand — they rest on measurements, not on an argument. Section 5's
> proposed day of work has been done, and section 4 is its answer.
>
> Companion retraction of the same claim in a funding context: PR #908, `docs/SUPPORT_AVENUES.md`.

---

## The short version

We spent a fortnight proving whether the products could be trusted. The answer:

- **Everything the system works out for itself was broken.** All of it.
- **Everything it simply passes along was fine.** Basically all of it.

That is the whole finding, and it points somewhere the campaign didn't expect: **the answer is not
more checking. It is calculating less.**

What to calculate *less of* is settled. **What to lead with instead is deliberately left open** —
see section 4. Installing a replacement headline on the same day one was retracted would repeat
the error being corrected.

---

## 1. What the fortnight actually produced

Roughly PRs #878–#897, 2026-08-06 → 08-08.

**Fixed or removed — things that were untrue:**

- A **paid feature** that had never once returned a reading in 538 attempts.
- A scientific library named as our method on the report, the marketing page and the disclaimer,
  which no code has ever used.
- A panel that showed a customer their neighbours' street addresses with a made-up rent figure
  and a planning judgement about someone else's land.
- A flood answer that told addresses in **Lismore and Murwillumbah** they were not in a flood
  zone, from a check that never ran. Those are the towns at the centre of the 2022 floods.
- Test runs that had silently stopped happening for three days, while reporting success.
- A safety library named in production that was never installed, so four checks did nothing for
  months.

**Checked properly:**

- **Shadow** — compared against an independent sun-position authority. Passed a limit that was
  written down *before* the test ran (worst error 0.21°, limit 0.5°).
- **Flood** — inconclusive. Only seven usable comparison points, and the honest range runs from
  0.49 to 0.97, which is "we don't know" wearing a decimal point.
- **Climate and solar** — cannot be checked at all, for reasons of substance rather than effort.
  Both now carry permanent written limits.
- **Granny flat** — labels now say what the scan actually did. Detection accuracy is still
  unmeasured.

**The most useful number is why there were only seven flood points: our council coverage barely
overlaps the places that flooded.** If a provable flood product is wanted, the job is coverage in
flood-prone councils — Northern Rivers above all — not model work.

---

## 2. The finding that matters more than any of it

Sort every output into two piles.

| Things the system works out itself | Things it just passes along |
|---|---|
| flood yes/no · solar grade · climate score · granny-flat eligibility · shadow impact · ADG pass | zone · height · floor space ratio · overlays · lodged applications · a setback with its clause and page |
| **Every single one was broken** | **Basically none were broken** |

That is not a quality problem, it is a design one. **Every number you work out yourself becomes a
permanent liability** — it needs re-checking forever, it goes stale, and it fails quietly in ways
nobody sees. A fact with a source attached is nearly free and nearly always right.

### And most of what the checking found was our own mess

pvlib named but unused. A satellite detector that never worked. Tests that stopped running. A
flood answer defaulting to "no". **Almost none of that was our data being wrong about the world —
it was our own plumbing being wrong about itself.**

Which means the machinery isn't an advantage. **A competitor with a simpler system never generates
those errors and never needs the cleanup.** Complexity manufactured the problem the apparatus
solves. It is a tax on a choice we made, not a moat.

---

## 3. Two ideas to drop

**Publishing our limitations as marketing.** Every competitor ships "indicative only, verify with
council". Volunteering a detailed account of what we cannot do is unilateral disarmament — buyers
read candour as weakness, not rigour. The limits page is a **due-diligence and hiring artifact**,
not a sales one.

**Selling a check on AI-written planning reports.** The buyer's alternative isn't nothing — it is
doing it properly themselves, which is the reliable method. And whoever chose an AI report already
traded accuracy for speed on purpose. Asking them to buy the accuracy back is asking them to
unwind their own decision.

---

## 4. ~~The asset nobody else has~~ — WITHDRAWN, and what survives it

The certificate archive is real and the count is real — **181,750 records, 128 councils, July 2018
to August 2026**, each figure carrying its own query. What was wrong was the argument built on top
of them, retracted in full at the head of this document.

**The lesson is worth more than the pitch was.** The reasoning failed on three checks that each
take minutes: *is the source actually private, does the process actually involve a decision, and
does the outcome actually vary?* No / no / no. Every derived business claim needs those three
asked of it before it leaves a page — the same discipline this document demands of derived
product claims, which is precisely why writing it here without applying it is the instructive
part.

**What genuinely survives is a field, not a pitch.** A purchaser cannot see an approved-but-unbuilt
development on the adjoining block. That is a real due-diligence signal, it comes from data already
held, and it belongs in the report that already exists — as one more fact passed through, which is
the category section 2 shows to be sound.

**What to lead with instead is deliberately left open.** The only candidate on the record is the
**1,071 source-linked setback controls** — genuinely extracted from council PDFs rather than
downloaded from an open endpoint, and honestly small. Whether that can carry a pitch is untested,
and it will not be asserted here until it is. Installing an untested headline the same day one was
retracted is the error being corrected, not repeated.

---

## 5. What to do next

**Section 5 originally proposed a day spent checking whether the certificate data was usable.**
That day was spent. The answer is section 4: the data is usable and the argument was not. The
question was the wrong one — it asked whether the data was *good*, when what decided it was whether
the data was *ours*, whether the process it records involves a *decision*, and whether the outcome
*varies*.

**The next question is still not a building question.** Distribution remains the constraint —
section 6 — and nothing in the last fortnight moved it. What moves it is asking people who might
pay, which is a week of conversations and no code at all.

---

## 6. The standing constraint, unchanged

Distribution, not data quality. Nobody knows this exists. That was true before the campaign and it
is true after it. The campaign removed real liabilities and produced real knowledge; it did not
move the constraint, and no further verification work will.

See `~/.claude/plans/biz-idea-verdict-ledger-2026-07.md` and
`~/.claude/plans/ce-property-intelligence-competitive-verdict-2026-07.md` for the research behind
that, which has not changed.
