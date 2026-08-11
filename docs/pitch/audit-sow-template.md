# Fixed-price reliability audit — scope of work

**One page. Five working days. AUD 6,000–10,000, banded by codebase size.** **One deliverable, one report, one meeting to walk you through them.**

The buyer fills in four fields (bottom of page), signs, we start. No committee, no change orders, no phase-two upsell.

------------------------------------------------------------------------

## What you get

By the end of day five, three artefacts land in your repo on a branch called `audit/reliability-<yyyy-mm-dd>`:

1.  **A census script** — one Python file you can re-run any time — that scans your codebase for the seven classes of silent-lie your product is exposed to. Which of the seven apply to you is decided on day one, not upfront. Every class it checks is one I have already caught on my own codebase; the PRs are in [github.com/lmcdo/nswcompliance](https://github.com/lmcdo/nswcompliance) — the gates themselves from \#347 (May) and the campaign that exercised them from \#835 to \#906 — and I'll show you the ones that map to yours before I write the census for you.

2.  **A structured QA report** using the template at `scripts/qa_report_template.json` from my repo — a JSON file with the findings, the `file:line` for each one, and how each one would show up to your users if unfixed. The report is validated by `scripts/qa_gate.py`, which requires that every `file:line` resolves to a real function in your code via AST parsing. So the findings can't be plausible-but-wrong: they either point at real code or the gate rejects them.

3.  **At least one falsifiable finding** — a specific defect I have demonstrated by planting the change and watching your check go red — **or** a written negative result explaining what I looked for, why I couldn't plant a proving defect, and what that tells you. A negative result with evidence is a real deliverable. A finding without a planted-defect proof is not, and I don't ship them.

Plus a one-hour readout meeting on day five. Your engineers ask questions. I answer or say "I don't know."

------------------------------------------------------------------------

## What I don't get you

- **Not a security audit.** No pen-test, no dependency-CVE sweep, no OWASP checklist. If that's what you want, hire someone who does that.
- **Not a code-quality review.** No opinions on your style, your architecture, or your dependency choices. I flag statements of fact your product makes to users that turn out to be false. Style is not in scope.
- **Not a fix.** I find and prove. Your team fixes. If you want me to also fix, that's a second engagement, priced separately after this one lands.
- **Not a certification.** I don't issue a stamp. What I give you is a report a hostile auditor could read and either verify or overturn using the artefacts in your own repo.

------------------------------------------------------------------------

## Timeline and access

| Day | What I do | What I need from you |
|----|----|----|
| **Day 1** — Census | Read your product surface, run the seven checks on your repo, decide which apply, and write the census script. End of day: a short call to agree which classes we're chasing. | Repo read access (branch + PR history). One engineer on Slack for the day for questions like "does this endpoint have any users." |
| **Day 2** — Plant | Try to plant a defect that would prove a lie is going out to your users. If I find one, prove it. If I can't, keep looking. | Nothing new. |
| **Day 3** — Plant | More of day 2. Half the time an audit spends on this day is figuring out that a finding I was excited about on day 2 is actually fine. | Nothing new. |
| **Day 4** — Write | The QA report, the negative results, the census script with the config for your repo. | Nothing new. |
| **Day 5** — Read out | One-hour Zoom / Meet. Findings, evidence, questions. | The nominated point of contact + up to three engineers. No slide deck expected. |

**One point of contact.** Nominated by you, named on this page. If they're on leave, we reschedule. I don't work around a committee.

------------------------------------------------------------------------

## Pricing — banded by codebase size, in AUD

| Codebase | Fee | Reasoning |
|----|----|----|
| Small — one product surface, \<50k lines, \<5 services | **\$6,000** | Day-one census fits in half a day, so plant time is longer and the finding rate goes up. |
| Medium — one product with a couple of adjacent services, 50–200k lines | **\$8,000** | Middle case. Almost every fixed-price target of mine lands here. |
| Large — multiple products, \>200k lines, or unfamiliar language stack | **\$10,000** | Day one is a full day, and I need to schedule two engineer conversations rather than one. Above this size, we scope differently — this is not the vehicle. |

**Payment terms.** 50% on signature, 50% on day-five readout. Bank transfer or invoice via Xero. No milestones inside the five days — the deliverable is the whole thing, not the parts.

**What the price is not.** It is not competitive with hiring a mid-level engineer for a week. It is priced against the deliverable's expected value: a single false-verdict finding, caught before it reaches customers, is worth this fee many times over — and if nothing is found, the written negative result tells you where **not** to spend on hardening, which is worth roughly the same.

------------------------------------------------------------------------

## Refund posture

If day one convinces me your product is not exposed to any of the seven classes and I have no plausible finding to chase, I say so on day one and invoice for the day at \$1,500. You have paid to find out I can't help, which is a real result, and the rest of the fee is not owed. This has never happened on my own codebase; the point of the qualifying diagnostic (`qualifying-diagnostic.docx`, in this same pack) is to make it not happen on yours.

------------------------------------------------------------------------

## Fields for the buyer to fill in

Paste the below into an email reply. Four lines. Nothing else needed.

    Target product surface : [one URL or repo path — the code and product I'm auditing]
    Access                 : [how I get to the repo — GitHub org invite / gitlab / zip]
    Timeline               : [the calendar week I start; earliest end-of-week deliverable]
    One point of contact   : [name + email + timezone — the person I talk to for five days]

Sign the bottom of this page, reply with those four lines, and I start on the Monday named.

------------------------------------------------------------------------

**Signed** (buyer): \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_\_\_\_\_\_

**Signed** (Lawrence McDonell): \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_\_\_\_\_\_
