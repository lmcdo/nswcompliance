# What to sell, and why — the landing after the August 2026 reliability campaign

**Written 2026-08-08, in plain English, to be read away from the code.**
Detail lives in `~/.claude/plans/ce-calibration-execution-plan-2026-08.md` §6 and
`~/.claude/plans/ce-product-assurance-position-2026-08.md`. This is the argument, not the log.

---

## The short version

We spent a fortnight proving whether the products could be trusted. The answer:

- **Everything the system works out for itself was broken.** All of it.
- **Everything it simply passes along was fine.** Basically all of it.

That is the whole finding, and it points somewhere the campaign didn't expect: **the answer is not
more checking. It is calculating less, and selling the one thing we hold that is a record rather
than an opinion — 181,737 approved building certificates.**

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

## 4. The asset nobody else has

**181,737 complying development certificates. 128 councils. July 2018 to August 2026.**

Counted live on 2026-08-09 — `SELECT count(*) FROM complying_development_certificates`, with
`count(DISTINCT council_name)` for the councils and `min/max(determination_date)` for the span.
An earlier draft of this document said 156,000, which understated the asset by roughly 26,000.

A record of **what actually got approved** — not what the rules say, but what got through.

Why it is different from everything else we hold:

- **It is a record, so there is nothing to check.** You report it. No calibration, no confidence
  story, no quiet failure mode.
- **Nobody can copy it** without the same eight years of collecting.
- **It does not melt.** When the NSW planning reforms publish structured controls at source, that
  kills the rules-based products — and does nothing at all to this one.
- **It answers a question no competitor can touch:** for this kind of build, on this size lot, in
  this council — what actually got approved, how long did it take, and what did it cost?

Archistar tells you what fits. PropCode tells you what the document says. **Nobody tells you what
the council actually waved through.**

And the pitch stops being about accuracy — which is the trap that has swallowed eighteen months.
It becomes *"here's what happened 181,737 times."* Nobody can argue with that, and no verification
apparatus is required to say it.

---

## 5. What to do next — one day, not a fortnight

**Check whether the certificate data is usable.** Not whether it is right — it is a record, it is
right by construction. Three questions only:

1. How many of the 128 councils have real depth, and how many have a handful of rows?
2. Does it carry what was built, what it cost, and the dates?
3. Can it join to the lot database, so "this lot" becomes "lots like this"?

If yes, there is a product nobody else has, and it needs none of the machinery built this
fortnight.
If no, that is known in a day rather than another year.

**This is the opposite kind of work to the last fortnight, and it is the right kind.**

---

## 6. The standing constraint, unchanged

Distribution, not data quality. Nobody knows this exists. That was true before the campaign and it
is true after it. The campaign removed real liabilities and produced real knowledge; it did not
move the constraint, and no further verification work will.

See `~/.claude/plans/biz-idea-verdict-ledger-2026-07.md` and
`~/.claude/plans/ce-property-intelligence-competitive-verdict-2026-07.md` for the research behind
that, which has not changed.
