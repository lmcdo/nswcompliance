# Frontier opportunities for a self-taught AI-output verification engineer (as of 18 Nov 2026)

Method note: 17 web searches, no successful page fetch. alignment.anthropic.com is blocked by this session's network allowlist, so primary program pages could not be read. Most facts below come from search-result summaries of official pages, forum posts and aggregators (grantedai.com, opportunitydesk, etc.). Aggregator-only facts are flagged. Dates were checked against today's date (2026-11-18); past deadlines are marked CLOSED.

## 1. Verification for AI agents and agentic coding: who builds and funds it

### Takeaway
Verifying AI-generated code and governing agents at runtime is now a venture-funded category. Several 2026 rounds use "verification" and "guardrails" as the pitch. The user's hook, QA-gate and mutation-testing stack is the same pattern these companies sell, which makes it a credible portfolio item for hiring or consulting.

### Cited Findings
- Qodo raised a $70M Series B (led by Qumra Capital, $120M total), betting that "verification will define the next phase of software development" (March 2026) — [TechCrunch](https://www.techcrunch.com/2026/03/30/qodo-bets-on-code-verification-as-ai-coding-scales-raises-70m/); [BankInfoSecurity](https://www.bankinfosecurity.com/qodo-targets-ai-code-risks-quality-70m-series-b-raise-a-31317)
- Corridor raised a $25M Series A at a $200M valuation, led by Felicis, for securing AI-generated code (18 Mar 2026) — [Fortune press release](https://fortune.com/press-releases/corridor-raises-25m-series-a-ai-coding-security-2026-03-18)
- Symbiotic Security raised a $10M seed. Its product combines pre-generation guardrails with post-generation verification and auto-remediation — [Symbiotic blog](https://www.symbioticsec.ai/blog/introducing-symbiotic-code-secure-ai-code-generation-backed-by-10m-from-top-investors)
- Backslash Security raised a $19M Series A (KOMPAS VC, Feb 2026) for "vibe coding" security — [Pulse2](https://pulse2.com/backslash-security-19-million-series-a/amp/)
- CodeIntegrity raised a $4.8M seed for runtime guardrails on agentic AI — [Dealroom](https://app.dealroom.co/news/note/codeintegrity-raises-4-8m-seed-to-put-runtime-guardrails-on-agentic-ai). Certiv raised a $4.2M pre-seed to govern autonomous agents in enterprises — [Pulse2](https://pulse2.com/certiv-4-2-million-raised-for-ai-agent-security-platform). Asymptote Labs raised a $5.5M seed for AI agent runtime security — [SecurityWeek](https://www.securityweek.com/asymptote-labs-lands-5-5-million-seed-for-ai-agent-runtime-security/amp/)
- Straion (EU) raised €1.1M to turn company coding rules into machine-readable guardrails for AI coding tools. This is closest to the user's "rules → hooks" practice — [Tech.eu](https://tech.eu/2026/02/24/from-prompt-and-pray-to-production-straion-raises-eur11m-to-govern-ai-coding-at-scale/)
- Baz extended its seed to $17M total and moved code review to the planning stage (Jun 2026) — [Dealroom](https://dealroom.co/news/136346-baz-extends-seed-to-17m-moves-code-review-to-the-planning-stage/)
- Funder view on agent evals: Coefficient Giving (formerly Open Philanthropy) argues that capability evaluations "are not on track for the role they are expected to play" and says "we still think we urgently need more demanding tests of AI agents' capabilities" — [Coefficient Giving](https://coefficientgiving.org/?p=23764)
- METR's HCAST benchmark has 189 tasks. METR staff and contractors built 143; 46 came from the public task bounty. This shows outsiders' tasks do end up in a frontier eval — [HCAST arXiv](https://arxiv.org/html/2503.17354v1); [METR taskdev](https://taskdev.metr.org/introduction/)
- METR's task-dev guide makes a documented QA run a condition of bounty payment. QA discipline is the gating skill — [METR QA guide](https://taskdev.metr.org/quality-assurance/)

### Inferences
- The market is crowded with security-framed products. A less-occupied niche is a "provenance and fabricated-value" verifier for agent outputs in data or extraction pipelines, as opposed to code security. The user already has a real-domain case study (NSW planning provisions).
- An open-source, well-documented Claude Code hook/QA-gate kit, with measured catch rates (e.g. mutation scores, examples of fabricated values caught), would make a portfolio artifact for the companies above and for eval orgs.

### Gaps
- No primary-source "open problems" list for agent verification was retrieved. The METR, Anthropic and AISI research-agenda pages were not fetched.
- SWE-bench variants, tau-bench and agent-reliability leaderboards were not researched in this pass.
- No data found on hiring at these startups or their openness to remote Australian hires.

## 2. Fellowships and programs open to non-academics (eligibility for an Australian, amounts, 2026 status)

### Takeaway
Most 2026 fellowship windows have CLOSED. The routes still open now are rolling: Anthropic Fellows (rolling for cohorts from late Sep 2026 onward), Coefficient Giving's Technical AI Safety RFP (rolling) and Manifund regranting (no deadline). MATS's next window opens around March 2027 for the Residency; check for its fellowship. None of the sources found states a degree requirement for these programs.

### Cited Findings
- **Anthropic Fellows Program:**
  - Paid, four-month, full-time empirical research aimed at an output such as a paper. Areas include safety, security, RL and governance. Stipend reported at US$3,850/week or £2,310/week depending on location — [Built In](https://builtin.com/articles/anthropic-fellows-program); [Greenhouse listing](https://job-boards.greenhouse.io/anthropic/jobs/5023394008)
  - Recent listings say applications are rolling for cohorts beginning late September 2026 and later. Earlier windows (26 Apr 2026 for a 20 Jul cohort) are CLOSED. Constellation runs applications and interviews — [Opportunity Desk](https://opportunitydesk.org/2026/04/15/anthropic-fellows-program-2026/); [Anthropic alignment blog (not fetched)](https://alignment.anthropic.com/2025/anthropic-fellows-program-2026)
  - Separate streams exist, e.g. Economics & Policy (Anthropic Institute) and ML Systems Performance — [Index Ventures listing](https://www.indexventures.com/startup-jobs/anthropic/anthropic-fellows-program-the-anthropic-institute-economics-policy/); [The Rundown jobs](https://jobs.therundown.ai/jobs/440813757-anthropic-fellows-program-ml-systems-performance)
- **MATS:**
  - Autumn 2026 (28 Sep – 4 Dec 2026) closed 7 Jun 2026. Stipend figures conflict between sources: $5k/mo vs $7,680/mo, plus $8k/mo compute — [LessWrong](https://www.lesswrong.com/posts/GufBJNg62gkpbnE4Q/mats-autumn-2026-fellowship-applications-now-open-apply-by); [EA Forum](https://forum.effectivealtruism.org/posts/ms5EypRcnxZYuQ8eQ/mats-autumn-2026-fellowship-apply-by-june-7th)
  - Summer 2026 closed 18 Jan 2026. It offered a $15k stipend, $12k compute, housing and travel, in Berkeley, London or remote — [LessWrong](https://www.lesswrong.com/posts/wTxA7ppCBeqZH37uL/apply-to-mats-summer-2026)
  - The new MATS Residency for experienced people: the Winter 2027 intake closed 31 Oct 2026 and the next window opens March 2027 — [LessWrong](https://www.lesswrong.com/posts/CPmEAky7voGD2o2vD/announcing-the-mats-residency-a-new-path-for-experienced-1)
- **Astra (Constellation):** In person in Berkeley, fully funded, about 5 months. The Strategy & Governance stream deadline of 3 May 2026 is CLOSED (program Sep 2026 – Feb 2027). An expression-of-interest form exists for future cohorts; one third-party page lists a "2027" cohort taking EOIs — [Constellation](https://www.constellation.org/programs/astra); [Constellation empirical](https://constellation.org/programs/astra/empirical); [Opportunities for Youth](https://opportunitiesforyouth.org/2026/09/16/constellation-astra-fellowship-2026-fully-funded-in-person-program-advancing-ai-safety-research/)
- **Coefficient Giving Technical AI Safety RFP:** Rolling, with no fixed deadline. Roughly $40M expected, "open to spending substantially more", and scope includes evaluation and benchmarking of safety properties (aggregator summary). The AI Governance RFP CLOSED on 25 Jan 2026. The AI for Forecasting & Sound Reasoning RFP is CLOSED (update 7 Feb 2026) — [Granted AI](https://grantedai.com/grants/coefficient-giving-technical-ai-safety-research-rfp-alignment-control-cg-d0e1f2a3); [Coefficient Giving forecasting RFP](https://coefficientgiving.org/funds/forecasting/request-for-proposals-ai-for-forecasting-and-sound-reasoning/)
- **UK AISI (AI Security Institute) Challenge Fund:** £50k–£200k per project, open to researchers at UK and international academic institutions and non-profits. It closed 1 Aug 2025 and is listed under "Past Grants". No 2026 round was found — [AISI grants](https://aisi.gov.uk/grants); [Find a Grant](https://find-government-grants.service.gov.uk/grants/aisi-challenge-fund-1)
- **Schmidt Sciences:**
  - The Science of Trustworthy AI RFP has Tier 1 (up to $1M) and Tier 2 ($1–5M+) over 1–3 years. It closed 17 May 2026 — [Granted AI](https://grantedai.com/news/schmidt-sciences-trustworthy-ai-grants-5-million-2026); [Oregon State listing](https://internal.science.oregonstate.edu/rdu/funding/2026-science-of-trustworthy-ai-grant)
  - "Scaling AI Safety for a Multi-Agent World" offers up to $1M. It is reported as joint with Google DeepMind, ARIA, the Cooperative AI Foundation and Google.org, and closed 8 Aug 2026 — [Granted AI](https://grantedai.com/blog/schmidt-sciences-scaling-ai-safety-multi-agent-1-million-august-8-deadline-private-philanthropy-research-strategy-2026); [UAlbany](https://www.albany.edu/node/126771)
  - Both calls are aimed at institutions, so they are a poor fit for a solo developer.
- **Manifund regranting:** Regrantors have $100k+ budgets each and make fast $5k–$50k seed grants, with money in hand in under a week. A 2026 fundraising post is live, and a third-party summary says there is no deadline — [LessWrong "Regranting in 2026"](https://www.lesswrong.com/posts/F8qBjWfAsryeTzbvY/regranting-in-2026-now-more-than-ever); [Manifund regranting data](https://manifund.org/about/regranting-data)

### Inferences
- The most realistic paid entry for this profile is Anthropic Fellows (rolling, empirical, values engineering) or a Manifund micro-grant, $5–50k, to open-source the verification tooling with a public writeup.
- Coefficient Giving's rolling RFP is plausible for an evals/benchmarking project, but a solo non-affiliated applicant would probably need a fiscal sponsor or a strong public track record. This is not verified.

### Gaps
- No search returned AI Safety Camp, SPAR or Apart Lab 2026/27 status. This needs a direct check.
- No Foresight Institute grant information was found, other than an unverified mention of a $200K Foresight-related Manifund grant in Feb 2026.
- Whether the Anthropic Fellows Program accepts remote fellows based in Australia, and its visa or work-authorisation rules, could not be confirmed because the primary page was not fetchable.

## 3. Bounties and competitions

### Takeaway
Paid outsider routes exist but are episodic. Anthropic's model-safety jailbreak bounty is ongoing via HackerOne, invite and NDA. ARC Prize 2026 submissions have CLOSED. The METR task bounty is PAUSED. Gray Swan runs periodic arenas, but no confirmed 2026 challenge was found.

### Cited Findings
- **Anthropic Model Safety Bug Bounty:**
  - Runs on HackerOne with an NDA. Accepted participants can submit jailbreak reports at any time and get a free model alias mirroring live classifiers. The target is universal jailbreaks of Constitutional Classifiers. The help page is dated 16 Mar 2026 — [Claude Help Center](https://support.claude.com/en/articles/12119250-model-safety-bug-bounty-program)
  - Maximum rewards conflict between sources: $15k, $25k or $35k — [Anthropic news](https://www.anthropic.com/news/model-safety-bug-bounty); [HackerOne blog](https://www.hackerone.com/blog/anthropic-expands-their-model-safety-bug-bounty-program)
  - A separate public HackerOne bounty for software vulnerabilities (CVSS-scored) was reported in May 2026 — [The New Stack](https://thenewstack.io/?p=22822600)
- **METR task bounty:** PAUSED indefinitely, closed to new submissions since 18 Nov 2024. It paid about $300 per hour of professional task time and over $100k in total — [METR taskdev](https://taskdev.metr.org/introduction/); [EA Forum](https://forum.effectivealtruism.org/posts/jcLztD7xPKeoxkpoq/bounty-diverse-hard-tasks-for-llm-agents-1)
- **ARC Prize 2026 (ARC-AGI-3, interactive game-like agent environments on Kaggle):**
  - Submissions closed 2 Nov 2026 and results are due 4 Dec 2026 (CLOSED).
  - Prizes: a $700K grand prize for 100%, and a $75K guaranteed top-score pool with milestone prizes. Entries must be open-sourced and run without internet.
  - Milestone #1 was won by Tufa Labs' "The Duck".
  - [ARC Prize 2026](https://arcprize.org/competitions/2026/arc-agi-3); [Milestone #1](https://arcprize.org/blog/arc-prize-2026-milestone-1); [ARC-AGI-3 paper](https://arxiv.org/abs/2603.24621)
- **Gray Swan Arena:** Past challenges include "Harmful AI Assistant" with a $40k pool ($500 each to the top 20 jailbreakers, plus per-model pools) and the DEF CON 33 arena, a $1k pool in 2025 — [Gray Swan](https://app.grayswan.ai/arena/challenge/harmful-ai-assistant/prizes); [DEF CON 33](https://app.grayswan.ai/arena/challenge/def-con-33/prizes)

### Inferences
- Red-team bounties reward adversarial creativity more than verification engineering. The user's comparative advantage is building evals and verifiers, so eval-task contributions are a better fit when METR or similar reopen.
- ARC Prize 2027 is likely to follow the annual pattern, but this is not confirmed.

### Gaps
- Kaggle LLM-evaluation competitions active in Nov 2026 were not found or searched successfully.
- Gray Swan's 2026 calendar was not confirmed.

## 4. Scientific and data verification frontiers

### Takeaway
LLM-based error-checking of scientific papers is an active, partly volunteer-run frontier. Its stated bottleneck is verifying flagged errors, roughly 10% false positives, which is exactly the user's skill. Coverage of FutureHouse, Elicit, C2PA and the Data Provenance Initiative in this pass is thin.

### Cited Findings
- The Black Spatula Project is open source, founded by engineer Steve Newman, with about 8 active developers and hundreds of volunteer advisers. It had analysed about 500 papers. Its system is wrong about an error roughly 10% of the time, and expert verification of flagged errors is its main bottleneck. Cost is about $0.15 to a few dollars per paper — [CO/AI](https://getcoai.com/news/oopsie-prevention-ai-tools-now-scan-scientific-papers-to-catch-critical-research-errors); [Academica](https://academica.ca/top-ten/how-ai-tools-are-being-used-to-identify-errors-in-research-papers-opinion/)
- YesNoError (crypto-funded) scanned more than 37,000 papers in two months — [CO/AI](https://getcoai.com/news/oopsie-prevention-ai-tools-now-scan-scientific-papers-to-catch-critical-research-errors)
- Critics argue that catching calculation errors is "not enough" — [heise](https://heise.de/-10321469); [FQxI](https://qspace.fqxi.org/articles/280/the-ai-paper-proofers)
- Black Spatula was itself started by a solo engineer outside academia, an example of the outsider route.

### Inferences
- A provenance-for-every-number checker that lowers false-positive rates (e.g. requiring a span-level citation and recomputation for each flagged numeric error) directly addresses the stated bottleneck. Contributing it to Black Spatula would be visible, publishable work.

### Gaps
- No 2026 information was retrieved on FutureHouse, Elicit, Consensus, C2PA or the Data Provenance Initiative.
- No Show HN or indie-tool traction data was collected.

## 5. Australian angles

### Takeaway
The Australian AI Safety Institute (AISI-AU) exists and is operational in 2026 within DISR. It works with Gradient Institute on agent risk and with CSIRO on human oversight. Its first publication (Aug 2026) is on agents interacting across organisational boundaries, the area adjacent to agent audit trails. The local community includes the Sydney AI Safety Fellowship (Jan–Mar 2026, CLOSED) and the AI Safety Forum (Sydney, July 2026).

### Cited Findings
- AISI-AU was announced in Nov 2025 under the National AI Plan with A$29.9M, sitting within the Department of Industry, Science and Resources — [HSF Kramer](https://www.hsfkramer.com/insights/2025-11/australia-to-establish-ai-safety-institute); [Investor Daily](https://www.investordaily.com.au/government-launches-national-institute-to-oversee-ai-safety)
- AAP reports Dr Kate Conroy was appointed general manager in May 2026. The institute was already testing models and collaborating with Gradient Institute on AI agents and with CSIRO on human oversight — [AAP](https://aapnews.aap.com.au/news/cheating-deceiving-govt-pledges-to-probe-ai-risks)
- A secondary report says Assistant Minister Andrew Charlton stated on 7 Jul 2026 that the institute was operational and testing frontier models with technical partners — [LetsDataScience](https://letsdatascience.com/news/australia-tests-frontier-ai-models-for-safety-1ac5682c)
- The first AISI-AU publication was a report commissioned from Gradient Institute on the risks of AI agents interacting across organisational boundaries (NAIC blog, 10 Aug 2026). An earlier DISR-funded Gradient report covers risk analysis of governed LLM multi-agent systems — [ai.gov.au](https://www.ai.gov.au/news-and-insights/blog/when-ai-agents-interact-new-research-australian-ai-safety-institute); [Gradient](https://gradientinstitute.org/research-publications/new-report-on-risks-and-controls-for-ai-agents-interacting-across-org-boundaries); [industry.gov.au](https://www.industry.gov.au/publications/risk-analysis-techniques-governed-llm-based-multiagent-systems)
- A UK–Australia AI safety MoU was signed on 24 May 2026 (secondary source) — [softwareseni](https://www.softwareseni.com/australias-ai-safety-institute-explained-funding-functions-and-how-to-engage-with-safety-evaluation/)
- **Sydney AI Safety Fellowship 2026:** ran 10 Jan – 1 Mar 2026, 10 weeks hybrid with 7 in person in Sydney. Deadline 14 Dec 2025 (CLOSED). Organisers are Chris Leong and Jack Payne. This was the third iteration — [EA opportunities](https://www.effectivealtruism.org/opportunities/recLRMMVcT9gvcgeM); [LessWrong](https://www.lesswrong.com/posts/RvzrwrtbA7NfeXgDx/sydney-ai-safety-fellowship-2026-priority-deadline-this)
- **AI Safety Forum 2026** (Sydney Mathematical Research Institute / Gradient, 7–8 Jul 2026), listed on ai.gov.au — [ai.gov.au event](https://www.ai.gov.au/news-and-insights/events/ai-safety-forum-2026); [Gradient](https://gradientinstitute.org/research-publications/australian-ai-safety-forum-2026)
- UTS Human Technology Institute runs fellowships — [UTS HTI](https://www.uts.edu.au/human-technology-institute/projects/hti-fellowships)

### Inferences
- Gradient Institute, as AISI-AU's commissioned research partner on agent risk, is the most direct local door for agent audit-trail and provenance work, via contracting, collaboration or employment. A 2027 Sydney fellowship is plausible but not confirmed.

### Gaps
- No AISI-AU grant program, procurement panel or job listings were found.
- No CSIRO Data61 Responsible AI or National AI Centre program details for 2026 were retrieved.
- No 2027 Sydney fellowship announcement was found.
