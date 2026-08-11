# Qualifying diagnostic — 30 minutes, before any engagement

**What this is.** A short exercise I run before I agree to audit anything. Three questions I ask you, two probes I run against public surfaces of your product, and one answer that means I walk away and you know inside half an hour that I wasn't going to help.

**Why I run it.** Because a reliability audit only helps a codebase that has a specific shape. If your product doesn't have that shape, I'm the wrong hire, and pretending otherwise wastes a week of your money.

**Why you should want it.** If I fail your diagnostic, you know quickly and for free. If I pass, we both know the audit will land — which is the argument for the fixed price.

------------------------------------------------------------------------

## The three questions I ask you (5 minutes each)

Answer honestly. I'm not scoring you; I'm looking for a specific shape.

### Q1. What does your product tell a user is true that a lawyer could sue you over if it's wrong?

**Good answers.** "We tell them a property is safe from flooding." "We tell them this loan applicant qualifies." "We tell them this drug interacts with that drug." "We tell them this shipment cleared customs." Anything where the system's output is a claim about the world that a user then relies on.

**Answers that fail the diagnostic.** "Nothing — we're a marketplace / a search / a CMS / a design tool." A product that doesn't make claims of fact doesn't have the class of bug I catch. My audit will find nothing, and you should hire someone who does something else.

**What I'm listening for.** The word "verified" in your marketing, and whether your team flinches when they say it out loud.

### Q2. When was the last time you shipped a fix for something that was silently wrong for weeks?

**Good answers.** Any specific incident. "A route was 500-ing for three days before we noticed." "A form was silently swallowing submissions since February." The messier the story, the better — that's the shape my technique addresses.

**Answers that fail.** "We don't really have those." One of two things is true. Either your monitoring is excellent — in which case I have less to add. Or you don't know they're happening, in which case I could help but you won't listen when I tell you.

**What I'm listening for.** Whether the person answering names the incident themselves without checking anywhere. If they have to look it up, the organisational memory of "silent bugs matter" isn't there.

### Q3. Who inside your organisation is going to be uncomfortable if I find something real?

**Good answers.** "Nobody — we want to know." "The engineer who wrote it will be a bit uncomfortable but they'll want the fix." A named person, with a predicted reaction, and a stated tolerance for the discomfort.

**Answers that fail.** "Nobody, we're all really collaborative" delivered too quickly. That is the sound of the finding being buried on day six by someone who wasn't in the meeting. I don't do audits into organisations that can't name whose feelings are going to get bruised.

**What I'm listening for.** Whether you know your own political geometry. If you don't, I don't want to be the person who accidentally maps it for you.

------------------------------------------------------------------------

## The two probes I run against public surfaces (10 minutes)

Because I don't have your code before the engagement, these run against things anyone can see: your marketing site, your public API responses, or a free-tier version of your product.

### Probe 1 — Marketing-page grep for liability language

I read your product's homepage, product pages, and any public docs, and I look for the exact words that trigger `scripts/liability_language_check.py`:

> `safe`, `feasible`, `compliant`, `should`, `recommend`, `suitable`, `adequate`, `sufficient`, `approved`, `guaranteed`, `certified`, `confirmed`, `verified`, `ensure`, `assure`, `accurate`, `definitive`, `comprehensive`, `reliable`

**What each hit means.** Each one is a claim your product is making publicly. For each, I want to know:

- Is there a computation inside your product that could ever have caused this word to not appear? If not, it's marketing prose and it doesn't matter here.
- If yes, does the computation actually check what the word implies? If no, that is a finding waiting to happen and it's roughly where I'd start.

**The walk-away shape.** Zero hits. If your public surface makes no claim about facts, I have nothing to find and shouldn't audit you.

### Probe 2 — A single public request, replayed twice

If your product has any public endpoint — a free trial, a demo, an API with an open tier — I make one request against it, wait five minutes, make the same request again, and diff the responses.

**What I'm looking for.**

- **Fields that changed for no reason.** A "confidence" field that varies between calls with identical input suggests randomness sitting inside a claim about the world. That is my class of bug.
- **Fields that never change.** A "verdict" or "status" or "recommendation" that returns the same value regardless of input is the fabricated-verdict pattern from PR \#859. Also my class of bug.
- **A field that references something the docs don't mention.** Suggests the code has drifted from the documentation — the `scripts/doc_claims.py` pattern.

**The walk-away shape.** The endpoint is authenticated, and no free tier exists, and the marketing pages carry no liability language. I have no public probe, no public claims, and no way to tell if the audit will land. I decline; you didn't lose an hour.

------------------------------------------------------------------------

## The one answer that means I walk

**"We just want you to look at the code and tell us it's good."**

That is not an audit. It is a signature on a document I don't have the credentials to sign, and any specific finding I produce will get filed as "minor" because the goal was the signature, not the finding.

I will say, verbatim: *"I don't do that job. What I do is find specific statements your product makes that turn out to be false, and prove each one by planting the defect that would have caught it. If that's not what you want, thanks for the call, and best of luck with the search."*

Then I get off the call. This is a not a negotiation — it is the criterion for whether I take any engagement at all, and the whole point of writing it down here is to make it easy to hold on both sides. If I bend it once, every subsequent engagement is defended against it.

------------------------------------------------------------------------

## What you do with this document

You can share it with whoever signs the fee. It is written to be handed to a buyer — the questions are what I will actually ask you, the probes are what I will actually run, and the walk criterion is what I will actually do.

If you'd rather I run the diagnostic on a call, book 30 minutes. If you'd rather run the questions yourself first, do that. If any of them lands wrong on your own team before I'm involved, I promise you'd rather find out before signing than after.

Either way, no fee is quoted until this exercise is done.
