# Student launch — the six sends

Drafts for the six recipients named in `ce-institutional-endorsement-gtm-2026-07.md`
§STUDENT LAUNCH. Nothing here has been sent.

**Placement, unchanged:** students are credibility and feedback, **not revenue**. Nothing below
should be read as a funnel.

---

## Before any of these go out

| # | Step | Who |
|---|---|---|
| 1 | Get the 16658 coordinator's name — call **1300 275 887** (UTS DAB Student Centre) | You |
| 2 | Confirm the semester-timing claim against the UTS academic calendar | You |
| 3 | Export `student-brief.md` to PDF — it is markdown, not a sendable attachment | Either |
| 4 | Send one real test submission through a cohort link and confirm the row lands | Either |

On step 4: the production feedback endpoint was probed read-only on 2026-08-19 and returned
real rows over the live database connection, so credentials are set and reachable. That proves
the **read** path. An insert-specific failure — a column default, a permission — would not show
up in that probe, and the cost of finding out from a student is the whole cohort's feedback.

---

## Links to use

| Purpose | URL |
|---|---|
| The tool, cohort-tagged | `https://verify.plotdetect.com.au/assessment?cohort=<code>` |
| Landing page | `https://canibuildit.com.au/for/students` — **see the warning below** |

**⚠ Domain warning.** The `/for/students` page is served only from `canibuildit.com.au`.
`plotdetect.com.au/for/students` returns **404** (checked 2026-08-19; `/for/planners` 404s there
too — every `/for/` page is on the old domain). Every draft below therefore links straight to the
cohort URL on `verify.plotdetect.com.au` and does not mention the landing page. Sending academics
to a domain you are retiring, under a different name from the one you sign off with, costs more
than the page adds. Resolve the domain question before using the landing page in outreach.

**Cohort codes.** Lowercase, digits and dashes, 3–40 characters. Shorter than 3 is silently
ignored — the link still works, the feedback is just untagged, and nobody sees an error.

| Recipient | Code |
|---|---|
| UTS 16658 | `uts-16658` |
| UNSW planning | `unsw-planning` |
| WSU planning | `wsu-planning` |
| UNSW OOPS | `unsw-oops` |
| UNSW CAPS | `unsw-caps` |
| PIA NSW Young Planners | `pia-nsw-yp` |

**Attach the product assurance position to 1, 2 and 3 only.** §6.1 of the calibration plan rules
it a due-diligence artefact rather than marketing, and a lecturer is due diligence. Do not attach
it to the societies, and do not put it on the site.

---

## 1 — UTS 16658 subject coordinator

*Slow, highest value. Reading LEP/DCP controls is the graded task.*
*Salutation: use the real name from step 1. Blind fallback: "16658 Subject Coordinator".*

> **Subject:** Free class access to a NSW planning-controls tool for 16658
>
> Dear [Coordinator name],
>
> I build a NSW planning tool that returns the controls applying to an address — zone, height,
> floor space ratio, minimum lot size, setbacks, heritage, flood, bushfire — and cites each one to
> the clause it came from. It is the desktop-analysis step your Property Development Analysis
> students do by hand before a feasibility.
>
> I would like to offer your cohort free access for the teaching period, and I am happy to run a
> 60-minute guest session. There is no login and nothing to install — students open a link and
> type an address.
>
> I should be straight about what I am asking for, because it is not a testimonial. I want your
> students to find where it is wrong. About one citation in thirteen does not resolve to a clause;
> 28 councils have numeric controls and coverage outside them is thin; nothing in it has been
> checked against what a council would actually approve. A student who has just read the DCP for
> their own site is the best possible reader for that, and I would rather they told me than a
> paying user did.
>
> Two things, if either is of interest:
>
> - **This session** — a guest lecture, or simply students trying it on the site they are already
>   analysing. Neither needs a change to your outline.
> - **Semester 1 2027** — if it earns a place, using it inside an assessment task. I know outlines
>   are written November to December, which is why I am asking now rather than in February.
>
> I have a one-page brief for students that sets out what to look for and lists the known defects
> up front. Happy to send it, or to talk it through on a short call.
>
> Lawrence — PlotDetect
> info@plotdetect.com.au · ABN 76 629 477 885
>
> *Attached: assurance position — what has been validated, what has not, and what cannot be.*
>
> Class link: `https://verify.plotdetect.com.au/assessment?cohort=uts-16658`

---

## 2 — UNSW planning program

*Slow. Archistar entered UNSW by exactly this route.*

> **Subject:** Free cohort access to a NSW planning-controls tool
>
> Dear [name / Program Convenor],
>
> I build a NSW planning tool that returns the controls applying to an address and cites each one
> to its clause — zone, height, FSR, minimum lot size, setbacks, heritage, flood, bushfire. No
> login, nothing to install.
>
> I would like to offer a cohort free access for a teaching period, and to run a guest session if
> that is useful.
>
> What I want back is criticism, not endorsement. One citation in thirteen does not resolve to a
> clause, 28 councils have numeric controls and coverage thins outside them, and none of it has
> been tested against what a council would actually approve. Students reading a DCP for their own
> site will find those edges faster than anyone I could pay.
>
> If a guest session this session is easier than anything structural, that alone is worth the
> conversation — and if it earns a place in an assessment task for Semester 1 2027, outlines are
> written around November, so now is when it would have to start.
>
> Lawrence — PlotDetect
> info@plotdetect.com.au · ABN 76 629 477 885
>
> *Attached: assurance position — what has been validated, what has not, and what cannot be.*
>
> Cohort link: `https://verify.plotdetect.com.au/assessment?cohort=unsw-planning`

---

## 3 — Western Sydney University planning

*Slow. Third attempt at a curriculum champion; WSU students work on the growth-area LGAs where
coverage is strongest.*

> **Subject:** Free cohort access to a NSW planning-controls tool
>
> Dear [name / Program Convenor],
>
> I build a NSW planning tool that returns the planning controls for an address, each cited to the
> clause it came from. Students open a link and type an address — no account, nothing to install.
>
> I would like to offer a cohort free access for a teaching period, and to run a guest session.
>
> I am after the opposite of a testimonial. I want to know where it is wrong: a control the DCP
> requires that it does not show, or a number that contradicts the clause. About one citation in
> thirteen does not resolve, and coverage is uneven — 28 councils have numeric controls, and it is
> thinner elsewhere. Western Sydney LGAs are among the better-covered ones, which is part of why I
> am writing to you.
>
> A guest session needs no change to an outline. If it later earns a place in assessment, Semester
> 1 2027 is the realistic target and outlines are written around November.
>
> Lawrence — PlotDetect
> info@plotdetect.com.au · ABN 76 629 477 885
>
> *Attached: assurance position — what has been validated, what has not, and what cannot be.*
>
> Cohort link: `https://verify.plotdetect.com.au/assessment?cohort=wsu-planning`

---

## 4 — UNSW OOPS (planning society)

*Fast path. No gatekeeper, no curriculum timing. A society night is 15–30 people and can run in
three weeks.*

> **Subject:** A "try to break this" night for OOPS members
>
> Hi [name],
>
> I build a NSW planning tool — you type an address, it returns the controls that apply to it and
> cites each one to the clause. I am looking for planning students to attack it before I put it in
> front of more professionals.
>
> The offer: free access for your members, and I will come and run a session. Format that works
> best is a competition — everyone brings a site they know, and whoever finds the worst error
> wins. I will bring the prize.
>
> No sign-up, no account, nothing to install. Members open a link and start.
>
> Why it is worth an hour of your members' time: reading the DCP against a tool that claims to
> have read it for you is a genuinely useful exercise, and finding the tool wrong is the fun part.
> I will tell them up front what is already broken so nobody wastes the evening on a known bug.
>
> Any night in the next few weeks works for me.
>
> Lawrence — PlotDetect
> info@plotdetect.com.au
>
> Link for members: `https://verify.plotdetect.com.au/assessment?cohort=unsw-oops`

---

## 5 — UNSW CAPS (construction and property society)

*Fast path. Property and construction rather than planning, so the framing is feasibility, not
statutory reading.*

> **Subject:** A "try to break this" night for CAPS members
>
> Hi [name],
>
> I build a NSW planning tool that returns the controls applying to an address — height, floor
> space ratio, minimum lot size, setbacks — each cited to the clause it came from. It is the step
> before a feasibility, done in seconds instead of an afternoon with the LEP open.
>
> I would like to offer your members free access and come and run a session. The format I would
> suggest is a competition: bring a site you know, and whoever finds the worst error in what the
> tool says about it wins.
>
> No account, nothing to install.
>
> For your members the useful part is seeing how much of a feasibility's input is fixed by the
> planning instruments before a single design decision gets made. For me, the useful part is
> people who know a site well telling me the number is wrong.
>
> Any night in the next few weeks suits.
>
> Lawrence — PlotDetect
> info@plotdetect.com.au
>
> Link for members: `https://verify.plotdetect.com.au/assessment?cohort=unsw-caps`

---

## 6 — PIA NSW Young Planners

*Medium speed, adjacent and professional. These are working planners, so the ask is a session,
not an assignment, and the credibility is worth more than the volume of feedback.*

> **Subject:** A session for Young Planners — reading LEP and DCP controls faster
>
> Hi [name],
>
> I build a NSW planning tool that returns the controls applying to any address and cites each one
> to its clause — the desktop-analysis step, done in seconds.
>
> I would like to offer Young Planners members free access, and to run a short session if the
> committee thinks it fits. Practical and source-cited, and I am happy for it to be framed as
> "here is what a tool like this gets right and wrong" rather than a product demo — that is the
> more honest talk and the more interesting one.
>
> What I want in return is the criticism. Working planners will spot the things a tool cannot know
> — that a control is applied differently in practice than it reads, or that a citation points at
> the wrong version of a plan. That is exactly the feedback I cannot generate myself.
>
> Worth a conversation?
>
> Lawrence — PlotDetect
> info@plotdetect.com.au · ABN 76 629 477 885
>
> Members' link: `https://verify.plotdetect.com.au/assessment?cohort=pia-nsw-yp`

---

## What to expect

From the plan's own estimates, unchanged and not re-derived here:

- **1–3 replies from six.** One becomes something this year.
- Societies answer fastest; a capstone cohort is 40–80 students, a society night 15–30.
- **10–20 reports from 30 students if the brief asks specifically; 2–5 if it does not.** This is
  the entire reason the brief exists.
- Most reports will be interface confusion rather than data defects. That is still useful; it is
  just not the prize.

Two report types are worth the exercise on their own: *"the control for my site is missing"* and
*"this number is not what the DCP says."*

## Where the feedback lands

Submissions store the cohort code alongside the report. To read a cohort's feedback, query
`user_feedback` and filter on the code inside `context_data`; `user_type` will be `student` for
anyone who arrived through a valid cohort link, because the widget defaults it.

An untagged visit stores no cohort rather than a placeholder, so an empty result means the link
was not used — not that the feedback was lost.
