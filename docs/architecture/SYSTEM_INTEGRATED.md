# The shape of it, in one picture

**Measured 2026-08-09 against `origin/main` at `af7982a8`.** Evidence for every box and every
count is in [VERIFICATION.md](VERIFICATION.md). The technical version of this is
[SYSTEM_TECHNICAL.md](SYSTEM_TECHNICAL.md).

If you only read one thing on this page, read this:

> **Sort every output into two piles. Things the system works out for itself, and things it
> simply passes along. Every single one in the first pile was broken. Basically none in the
> second pile were.**

That is not a quality problem. It is a design finding, it was found by building machinery to
look for it, and the machinery is now standing.

---

```mermaid
flowchart LR
  subgraph PA["① PILE A — the system works these out. Every one was broken."]
    A1["Shadow<br/>checked against pvlib<br/>0.21° of a 0.50° limit"]
    A2["Flood<br/>reproducible<br/>7 points, inconclusive"]
    A3["Granny flat<br/>reproducible<br/>accuracy unmeasured"]
    A4["Solar<br/>source-linked"]
    A5["Climate score<br/>source-linked<br/>uncheckable"]
    A6["Neighbour build<br/>REMOVED<br/>0 readings of 538"]
    A1 ~~~ A2 ~~~ A3 ~~~ A4 ~~~ A5 ~~~ A6
  end

  subgraph PB["② PILE B — passed straight through. Basically none were broken."]
    B1["Zone"]
    B2["Height limit"]
    B3["Floor space ratio"]
    B4["Hazard + heritage overlays"]
    B5["Applications · 243,753"]
    B6["Setback with its clause · 1,071"]
    B1 ~~~ B2 ~~~ B3 ~~~ B4 ~~~ B5 ~~~ B6
  end

  subgraph GATES["③ The seven gates that now stand behind both piles"]
    G1["falsifiability.py<br/>plant a defect,<br/>prove the test reddens"]
    G3["lint_fabricated_verdicts.py<br/>is the verdict backed<br/>by data received?"]
    G4["liability_language_check.py<br/>changed wording"]
    G2["validate_schema_contract.py<br/>table names vs live DB"]
    G5["qa_gate.py<br/>report bound to commit"]
    G6["doc_claims.py<br/>reports only, blocks nothing"]
    G7["pre-push + CI<br/>runs all of it, twice"]
    G1 ~~~ G3 ~~~ G4 ~~~ G2 ~~~ G5 ~~~ G6 ~~~ G7
  end

  PA ==>|"guarded by"| GATES
  PB ==>|"guarded by"| GATES

  classDef rung3 fill:#d6efdc,stroke:#2e7d52,color:#0e2c1c
  classDef rung2 fill:#fdf0cf,stroke:#9a7500,color:#3a2f08
  classDef rung1 fill:#dfeafc,stroke:#3b6fb6,color:#0f2340
  classDef gone fill:#ececec,stroke:#8a8a8a,color:#2b2b2b,stroke-dasharray:4 3
  classDef pass fill:#d7f0f2,stroke:#2b7f89,color:#0c2b2f
  classDef gate fill:#f3e8fd,stroke:#7b4fbe,color:#241038
  classDef gateoff fill:#f0f0f0,stroke:#888,color:#333,stroke-dasharray:4 3

  class A1 rung3
  class A2,A3 rung2
  class A4,A5 rung1
  class A6 gone
  class B1,B2,B3,B4,B5,B6 pass
  class G1,G2,G3,G4,G5,G7 gate
  class G6 gateoff
```

---

## How to read the colours

| Colour | What it means | How many |
|---|---|---|
| **Green — checked against something outside itself** | Compared against an independent authority that could have disagreed, against a pass mark written down *before* the test ran. | **One product.** Shadow sun-geometry. |
| **Amber — reproducible** | Re-running a committed recipe gives the same number. Nothing external has confirmed it is right. | Flood, granny flat. |
| **Blue — source-linked** | We can show where the number came from. That is all. | Solar, climate. |
| **Teal — pass-through** | Not worked out by us at all. Reported as it came from the source, with the source named. | All of Pile B. |
| **Grey dashed** | Removed, or reports without blocking. | The neighbour-construction feature; the doc checker. |

Teal and green are deliberately different. Pile B is not "checked" — it has never needed
checking, which is the whole point.

The word **"verified"** is banned in this project as an umbrella term, because it implies all
three rungs at once. Everything above uses the rung it actually sits on.

Pile B is safe for a specific reason: **a fact with a source attached is nearly free and nearly
always right.** Every number the system works out for itself becomes a permanent liability — it
needs re-checking forever, it goes stale, and it fails quietly.

---

## What the fortnight actually removed

Not a tidy-up. Six things that were untrue and are now gone:

- A **paid feature** that had never once returned a reading in 538 attempts.
- A scientific library named as our method on the report, the marketing page and the disclaimer,
  which no code has ever used.
- A panel that showed a customer their neighbours' street addresses beside an invented rent figure.
- A flood answer that told addresses in **Lismore and Murwillumbah** they were not in a flood
  zone, from a check that never ran.
- A test suite that had silently stopped running for three days while reporting success.
- A safety library named in production that was never installed, so four checks did nothing for months.

---

## The one asset that does not melt

**181,737 complying development certificates. 128 councils. July 2018 to August 2026.**

A record of what actually got approved — not what the rules say, but what got through. It is
different in kind from everything else here:

- **It is a record, so there is nothing to calibrate.** You report it. No confidence story, no
  quiet failure mode.
- **Nobody can copy it** without the same eight years of collecting.
- **It survives the reforms.** When NSW publishes structured planning controls at source, that
  erodes the rules-based products and does nothing at all to this one.

Alongside it sit 62,016 development applications — though those only run back to May 2025, so
the eight-year depth belongs to the certificates alone.

---

## Honest limits of this page

The two piles are a real finding, not a marketing frame — but the boundary is a judgement, and
two items sit near it. Setbacks are drawn in Pile B because each number is stored with the
sentence it came from; the *extraction* that produced them is derived work, and 528 of the 1,071
have no committed recipe to re-run. Flood sits in Pile A because the yes/no is worked out, even
though its inputs are pass-through map layers.

The gates are young. They were built between 6 and 8 August 2026, which is days, not years, of
evidence that they hold. What can be said is narrower and more useful: each one blocks a
specific failure that actually happened, and `falsifiability.py` exists precisely because a test
that has never been shown to fail proves nothing.
