# Volunteer, Open-Source and Pro-Bono Opportunities for an AI-Output Verification / Document-Extraction QA Specialist (as of 18 Nov 2026)

Method note: 17 tool calls (web search only). Direct page fetches were blocked by the session network policy (e.g. `ukgovernmentbeis.github.io` failed to resolve), so most findings rest on search-result summaries of primary pages. Every item below carries its source; claims that rest only on vendor/self-reported or aggregator sources are flagged. Areas not researched within budget are listed under Gaps.

## Q1. Open-source AI evaluation ecosystems (Inspect/inspect_evals, lm-eval-harness, MLCommons, METR, HELM, HF, promptfoo, DeepEval)

### Takeaway
UK AISI's Inspect Evals is the most accessible and visible entry point, but its route changed in 2026: new evals now go through a "register" (issue + arXiv link + source link, bot opens the PR) rather than code PRs, while fixes/updates to existing evals remain welcome. Fixing and verifying existing evals fits a QA/verification profile well. METR's paid task bounty is closed. MLCommons working groups are free for individuals to join.

### Cited Findings
- Inspect Evals (UK AISI) Technical Contribution Guide says it no longer accepts code submissions for new eval implementations; those with an implemented eval should add it to the Inspect Evals Register — [Inspect Evals contributing](https://ukgovernmentbeis.github.io/inspect_evals/contributing) (via search summary)
- README: from 8 May 2026 community contributions move to the `/register/` folder; submission is a GitHub issue with arXiv URL and source link; a bot validates, derives metadata and opens a PR. Fixes and updates to existing evals remain welcome — [inspect_evals README](https://raw.githubusercontent.com/UKGovernmentBEIS/inspect_evals/main/README.md)
- UK AISI says it is seeking new evaluation contributions and has merged evals from "over a dozen" users — [AISI: Inspect Evals](https://www.aisi.gov.uk/work/inspect-evals)
- Inspect Evals was built by UK AISI, Arcadia Impact and Vector Institute; ASET has been contracted with UK AISI since Jan 2025 to manage Inspect Evals (i.e. there are paid maintainer contracts around this repo) — [Manifund: inspect evals](https://manifund.org/projects/inspect-evals); paper on maintaining the repo: [arXiv 2507.06893](https://arxiv.org/html/2507.06893v1)
- inspect-evals 0.22.0 released 25 Sep 2026 (mirror, not verified against official repo) — [CERN PyPI mirror](https://simple-repository.app.cern.ch/project/inspect-evals)
- EleutherAI: no formal membership; participation is voluntary and coordinated via its public Discord; the LM Evaluation Harness supports issues via GitHub and Discord and is the backend for the HF Open LLM Leaderboard — [EleutherAI about](https://eleuther.ai/about); [EleutherAI LLM evaluation](https://eleuther.ai/projects/large-language-model-evaluation)
- EleutherAI's shift to nonprofit allowed it to employ people (no named volunteer-to-hire case found) — [The Decoder](https://the-decoder.com/eleutherai-went-from-discord-coders-to-a-truly-open-ai-research-organization/)
- EleutherAI's "Lessons from the Trenches on Reproducible Evaluation" paper (relevant to verification-of-eval-results skills) — [EleutherAI blog](https://www.eleuther.ai/papers-blog/lessons-from-the-trenches-on-reproducible-evaluation-of-language-models)
- MLCommons AI Risk & Reliability working group (develops AILuminate) "welcome[s] others to join"; membership is free for academics and individuals; join via subscription form. Working group sought regional partners for a culturally specific multimodal benchmark (timeline incl. June 2026 dataset release). AILuminate Global Assurance Program announced Feb 2026 — [MLCommons get involved](https://mlcommons.org/?p=1081); [AILuminate Global Assurance](https://mlcommons.org/2026/02/ailuminate-global-assurance/)
- METR task bounty: paused to new submissions indefinitely (no new submissions as of 18 Nov 2024). Paid $300 per task-hour baseline; 46 of HCAST's tasks came via bounty vs 143 by staff/contractors — [METR taskdev bounty](https://taskdev.metr.org/bounty); [HCAST paper](https://arxiv.org/html/2503.17354v1) — **status: CLOSED / older**

### Inferences
- For a verification specialist, the highest-signal Inspect Evals contribution is now auditing/fixing existing evals (scorer bugs, dataset errors, reproducibility discrepancies) rather than porting new benchmarks — this is exactly where fabricated/conflicting-value detection and mutation-testing skills apply.
- Paid maintenance contracts exist around Inspect Evals (ASET/Arcadia), suggesting a visible route from contributor to contractor, though no named individual case was found.

### Gaps
- No named examples found of inspect_evals or lm-evaluation-harness contributors being hired specifically because of contributions.
- HELM (Stanford CRFM), Hugging Face open evals/leaderboards, OpenAI/Anthropic open eval repos, promptfoo and DeepEval contribution routes were not researched within budget.

## Q2. Fact-checking and information integrity

### Takeaway
Australian fact-checking capacity shrank: RMIT ABC Fact Check ended (replaced by ABC News Verify) and RMIT FactLab reportedly shuttered; AAP FactCheck remains active but lost Google funding. Full Fact's AI is staff-built with no volunteer program found. Wikipedia's WikiProject AI Cleanup is the clearest open volunteer venue for LLM-output verification, and English Wikipedia banned LLM-generated article content in March 2026.

### Cited Findings
- RMIT ABC Fact Check ran 2017–2024; ABC replaced it with internal ABC News Verify — [ABC Friends](https://www.abcfriends.net.au/rmit_fact_checking_partnership_ends); [RMIT info-integrity](https://sites.rmit.edu.au/info-integrity/2025/11/01/rmit-abc-fact-check)
- RMIT FactLab "appears to have quietly shuttered"; Google let its funding deal with AAP FactCheck expire; Australia now has three dedicated fact-checking projects: AAP FactCheck, AFP Fact Check, ABC News Verify — [PIJI](https://piji.com.au/?p=8805) (single source; no official RMIT confirmation found)
- AAP FactCheck still publishing (June 2026 piece), IFCN member — [AAP FactCheck](https://www.aap.com.au/factcheck/disinformation-pages-churn-out-bogus-abc-lawsuits-for-clicks/)
- Full Fact: 34 staff incl. dedicated AI team; tools used by 40+ fact-checking orgs in 30 countries; access via organisational expression-of-interest form; no volunteer or open-source program found — [Full Fact AI](https://fullfact.org/about/ai/); [Full Fact Report 2026](https://fullfact.org/policy/reports/full-fact-report-2026/); [Nieman Lab Jun 2026](https://niemanlab.org/2026/06/full-fact-is-battling-ai-generated-elections-content-with-ai-tools-of-its-own)
- WikiProject AI Cleanup: volunteer effort since late 2023 to find/remove AI-written content; Pangram detector flagged ~20% of new articles/drafts end-2025, falling to ~15–16% early 2026; legacy LLM text from 2022–2026 still needs cleanup — [IEEE Spectrum](https://spectrum.ieee.org/wikipedia-wikiproject-ai-writing-cleanup) (figures relayed partly via aggregators)
- English Wikipedia voted (reported 44–2) on 20 Mar 2026 to prohibit LLMs generating/rewriting article content — [IBTimes UK](https://www.ibtimes.co.uk/english-wikipedia-prohibits-editors-using-ai-protect-purely-human-written-corpus-1827224) (secondary; verify on Wikipedia)

### Inferences
- Wikipedia citation/claim verification (checking whether cited sources actually support LLM-inserted text) maps directly to "fabricated value" detection and has high public visibility, but no evidence of it leading to paid work was found.
- AAP FactCheck is an employer rather than a volunteer program; with Google funding gone, a pro-bono tooling offer (claim-monitoring pipeline with provenance) might be welcome — speculative.

### Gaps
- ClaimBuster, Community Notes contributor/algorithm work, and Wikidata citation-verification bots not researched.
- No evidence found of Wikipedia AI Cleanup volunteers getting hired.

## Q3. Evidence synthesis / science

### Takeaway
LLM data extraction for systematic reviews is an active, formally evaluated area where human verification is the documented bottleneck. Cochrane ran an AI-tools pilot (Q2 2026) prioritising screening and extraction; Bond IEBH (Gold Coast, Australia) runs the Systematic Review Accelerator automation program — a natural local collaborator. pyOpenSci actively recruits volunteer reviewers with mentorship.

### Cited Findings
- Cochrane call for AI tools: submissions due 31 Dec 2025, selection end Q1 2026, three-month pilot from start of Q2 2026, prioritising screening and data extraction — [Cochrane call for proposals](https://www.cochrane.org/zh-hant/about-us/news/call-proposals-ai-tools-transform-evidence-synthesis)
- Cochrane webinar on LLM data extraction incl. a SWAR validating a semi-automated LLM extraction workflow — [Cochrane event](https://www.cochrane.org/events/opportunities-and-challenges-data-extraction-large-language-model)
- 2025 Cochrane ESM study: Elicit extractions on 20 RCTs often only partly matched humans; human verification necessary — [DOAJ](https://doaj.org/article/d3ebb3324435458fafa85feff3baabf5)
- CESAR platform-study protocol (J Clin Epidemiol, 2026) evaluates multiple AI tools vs human-only process across screening and extraction — per search summary of [PMC12462964](https://pmc.ncbi.nlm.nih.gov/articles/PMC12462964) (attribution to that URL not confirmed)
- 2026 JMIR review: 26.1% (n=58) of AI-automation studies addressed data extraction vs 61.7% screening — [JMIR 2026](https://www.jmir.org/2026/1/e81597/PDF)
- Bond IEBH Systematic Review Accelerator: suite of automation tools for evidence reviews — [Bond SRA](https://bond.edu.au/iebh/systematic-review-accelerator-sra); Bond-affiliated generative-AI-in-evidence-synthesis systematic review (Research Synthesis Methods 2025, 16:601–619) — [Cambridge](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/S175928792500016X); Justin Clark (Bond) led ICASR session on harms/benefits of automation — [ICASR](https://icasr.github.io/presentations/2024/clark.pdf)
- pyOpenSci: recruiting volunteer reviewers and editors, mentorship for first reviews; reviews paused 22 Dec 2025–16 Jan 2026 then resumed; 2026 policy notes generative AI is straining volunteer peer review — [pyOpenSci get involved](https://deploy-preview-878--pyos-website.netlify.app/blog/get-involved-with-pyos); [pyOpenSci peer review](https://deploy-preview-883--pyos-website.netlify.app/about-peer-review/) (preview-deploy mirrors of pyopensci.org)

### Inferences
- An extraction-verification harness (fabricated/conflicting value detection against source PDFs) is directly relevant to the documented Cochrane/CESAR bottleneck; contacting Bond IEBH's automation team or ICASR is the most plausible Australian route to a research collaboration or co-authorship.
- pyOpenSci review given the 2026 AI-code strain on reviewers could showcase QA rigour; low time, moderate visibility.

### Gaps
- Monash evidence-synthesis groups, Zooniverse, rOpenSci not researched.
- No evidence found of volunteers being paid/hired through Cochrane AI work; no open Cochrane volunteer call for LLM extraction found.

## Q4. Humanitarian and nonprofit data

### Takeaway
DataKind (global and UK) runs remote pro-bono DataCorps projects (multi-month) via a profile-matching portal; no specific 2026 project list was found. Other organisations were not researched.

### Cited Findings
- DataKind: create volunteer profile for matching; DataCorps = long-term pro-bono teams; DataDives = short events; remote volunteering possible; focus areas incl. humanitarian aid, frontline health, climate — [DataKind volunteer](https://www.datakind.org/join-us/volunteer); [DataKind playbook](https://datakind.github.io/playbook-revamp/how_to_volunteer_at_DK.html)
- DataKind UK runs separate volunteer programme (one-off events, multi-month projects, committees) — [DataKind UK](https://www.datakind.org.uk/volunteer)
- DataKit virtual event listing marked inactive (Apr 2026) — [Civic Tech directory](https://directory.civictech.guide/listing/datakit-events)

### Gaps
- HDX/OCHA, Ushahidi, Code for All, Australian Red Cross, Infoxchange, Data for Good not researched; no hiring-outcome evidence for DataKind found.

## Q5. AI safety-adjacent volunteer/part-time (red-teaming, bounties, hackathons, ANZ community)

### Takeaway
This category has the strongest documented contribution-to-paid-work pipelines: Gray Swan Arena explicitly hires from its leaderboards and relaunched with a $300K competition in Oct 2026; Apart Research hackathons feed fellowships and some documented hires (e.g. METR); Anthropic's Model Safety Bug Bounty (HackerOne, application-based) remained listed in 2026. AI Safety ANZ provides local Sydney community and an annual Australian AI Safety Forum.

### Cited Findings
- Gray Swan relaunched Arena on 20 Oct 2026 with a $300,000 indirect prompt-injection competition; top performers considered for private NDA red-teaming engagements — [Fortune, 20 Oct 2026](https://fortune.com/2026/10/20/exclusive-ai-security-company-gray-swan-red-team-arena-contest-to-jailbreak-ai-agents/)
- Gray Swan reports hiring from Arena: 4 full-time staff, 9 contractors, 1 intern started via challenges (earlier post); Proving Ground "connected dozens of participants to contracts and jobs"; later report says 100+ recruited (company-reported, figures inconsistent) — [Gray Swan Proving Ground](https://www.grayswan.ai/news/introducing-the-gray-swan-ai-proving-ground); [Forbes AU](https://www.forbes.com.au/news/innovation/this-hacker-team-is-bulletproofing-ai-models-for-companies-like-openai-and-anthropic/)
- UK AISI × Gray Swan Agent Red-Teaming challenge: $171,800 pool sponsored by UK AISI, OpenAI, Anthropic, Google DeepMind; prizes to 161 red-teamers — [Gray Swan results](https://www.grayswan.ai/news/uk-aisi-x-gray-swan-agent-red-teaming-challenge-results-snapshot)
- Anthropic Model Safety Bug Bounty on HackerOne seeks universal jailbreaks of Constitutional Classifiers; acceptance required, NDA, free model access (support page dated 16 Mar 2026) — [Anthropic support](https://support.claude.com/en/articles/12119250-model-safety-bug-bounty-program); original program up to $25,000 — [Anthropic, May 2025](https://www.anthropic.com/news/testing-our-safety-defenses-with-a-new-bug-bounty-program); up-to-$35,000 figure appears only in secondary sources (unverified)
- Apart Research: a March 2024 METR×Apart hackathon participant joined METR full-time "largely because of our event"; 10 Code Red Hackathon participants became Apart Lab fellows; ~40% of Studio participants advance to 12–24 week Fellowship; 100+ fellows supported; career moves cited to FAR.ai, Cooperative AI Foundation, etc. (self-reported, not independently audited) — [EA Forum: Apart marginal funding](https://forum.effectivealtruism.org/posts/suvWKJbwfPDsQK3PM/how-apart-research-would-use-marginal-funding-to-scale-ai); [Manifund: Apart](https://manifund.org/projects/apart-research-research-and-talent-acceleration)
- AI Safety ANZ: local groups in Sydney and Melbourne; Australian AI Safety Forum 2026 at University of Sydney, 7–8 July 2026 (past); inaugural AI Safety New Zealand Conference in Christchurch — [Gradient Institute forum 2026](https://gradientinstitute.org/research-publications/australian-ai-safety-forum-2026); [USyd MRI](https://mathematical-research-institute.sydney.edu.au/event/ai-safety-forum-2026/); [AI Safety ANZ AF group](https://www.alignmentforum.org/groups/5drxbFQbLbAmc3GEf); [Christchurch listing](https://www.christchurchnz.com/visit/whats-on/listing/ai-safety-new-zealand-conference-2026-14245)

### Inferences — provisional ranked shortlist (for the report writer)
1. **Gray Swan Arena** (active Oct 2026; hours/week flexible; documented hiring pipeline, prize money). Start: register at app.grayswan.ai/arena.
2. **Inspect Evals fixes/verification + register submissions** (active; ~2–6 h per fix; high visibility with UK AISI and eval labs; paid maintainer contracts exist around it). Start: pick open issues, audit existing evals' scorers/datasets.
3. **Apart Research hackathons → Studio → Fellowship** (weekend sprints, then 12–24 week fellowship; documented hires incl. METR).
4. **Evidence-synthesis extraction verification with Bond IEBH / Cochrane AI methods** (research collaboration, co-authorship; local AU relevance; no hiring evidence found).
5. **Anthropic Model Safety Bug Bounty** (application-gated, payouts per universal jailbreak; less aligned with extraction-QA skills).
6. **WikiProject AI Cleanup / pyOpenSci reviewing / MLCommons AIRR working group / DataKind** (lower direct pay pipeline; reputational/portfolio value).
- AI Safety ANZ Sydney meetups are the local networking layer for 1–3.

### Gaps
- OpenAI bug bounty / safety bounties, AISI-sponsored evals bounties in 2026, and current Apart hackathon calendar not verified.
- No independent (non-self-reported) evidence of hiring rates for Gray Swan or Apart.
- Time commitments are inferred from program formats, not stated hours, except Apart fellowship length and METR (closed) bounty rates.
