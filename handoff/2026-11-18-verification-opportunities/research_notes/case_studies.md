# Case Studies: Business Value of Verification / QA / Eval Engineering for LLM Document Extraction and Generation (2023 – Nov 2026)

Research method note: 14 tool calls (web search snippets plus attempted fetches). Two primary-source fetches failed because the hosts are outside this session's network allowlist (damiencharlotin.com, ai-evals.tools). Most findings below are therefore from search-result syntheses of secondary reporting; where a figure rests on one secondary source it is flagged. Nothing here was fabricated; unverified items are in Gaps.

## Failure cases with measurable cost

### Takeaway
The best-documented Australian failure is Deloitte's DEWR report: an A$440k government review containing fabricated citations and a made-up Federal Court quote, which ended in a refund of the final instalment (A$97,587.11 incl. GST) and a political call for a full refund. All of these errors would have been caught by a check that every quoted or cited item appears in its source. Courts are now generating a steady stream of sanctions, in the thousands, for unverified AI citations, including Victoria and NSW. Air Canada shows that a company is liable for what its bot says, even when the dollar sum is small.

### Cited Findings
**Deloitte Australia / DEWR (2025), the anchor Australian case**
- Contract worth just under A$440,000 (A$439k, about US$290k) for the Targeted Compliance Framework assurance review — [The Register](https://www.theregister.com/2025/10/06/deloitte_ai_report_australia/); [ACS Information Age](https://ia.acs.org.au/article/2025/deloitte-to-refund-government-over-ai-errors.html)
- Errors included fake citations, phantom footnotes and a fabricated quote from a Federal Court judgment — [The Register](https://www.theregister.com/2025/10/06/deloitte_ai_report_australia/)
- The corrected report disclosed use of an "Azure OpenAI GPT-4o based tool chain"; the original did not. Deloitte did not attribute the errors to AI and stood by its findings — [TechRadar](https://www.techradar.com/pro/deloitte-forced-to-refund-aussie-government-after-admitting-it-used-ai-to-produce-error-strewn-report); [Malay Mail/AFP](https://www.malaymail.com/news/world/2025/10/07/deloitte-to-pay-partial-refund-to-australian-govt-for-report-using-ai/193773)
- Refund: a DEWR letter asked Deloitte to repay the final instalment, A$97,587.11 incl. GST (about US$63k). The amount was revealed via Senate Estimates — [DEWR correspondence (PDF)](https://www.dewr.gov.au/aii/download/17418/correspondence-relating-targeted-compliance-framework-assurance-review/41834/correspondence-relating-targeted-compliance-framework-assurance-review/pdf); [CFO Dive](https://www.cfodive.com/news/deloitte-refunds-60k-report-ai-errors-australian-government-accounting/803321/). Early reports (Oct 2025) said the amount was undisclosed.
- The Greens called the refund "measly" and demanded a full refund — [Greens media release](https://greens.org.au/news/media-release/greens-slam-deloittes-unethical-behaviour-and-measly-refund-over-ai-report); [Region Canberra](https://region.com.au/government-urged-to-get-deloittes-total-fee-returned-for-delivering-a-botched-ai-report/911846/)

**Courts: hallucinated citations**
- Victoria, Aug 2025: Rishi Nathwani KC apologised to Justice James Elliott (Supreme Court of Victoria) for filing fabricated quotes from a speech to the state legislature and nonexistent case citations in a teen's murder trial. This caused a 24-hour delay. The lawyers had checked the first citations and assumed the rest were correct. The prosecution also did not check them — [eWeek/AP](https://www.eweek.com/news/australian-lawyer-apologizes-for-feeding-fake-cases-to-murder-trial-judge/); [CP24/AP](https://www.cp24.com/news/world/2025/08/15/australian-lawyer-apologizes-for-ai-generated-errors-in-murder-case/)
- "Mr Dayal" (anonymised), a family law matter, July 2024: a list of authorities prepared with AI legal software was tendered without verification. A separate incident — [Canaltech](https://canaltech.com.br/inteligencia-artificial/advogado-flagrado-usando-citacoes-falsas-geradas-por-ia-e-punido-na-australia/) (secondary; the primary is Dayal [2024] FedCFamC2F 1166, not fetched)
- NSW Supreme Court Practice Note SC Gen 23 was issued 28 Jan 2025 and commenced 3 Feb 2025. The NSW District Court adopts it. It requires verification of citations, and that verification cannot itself be done with a gen-AI program — [Barry Nilsson via Mondaq](https://mondaq.com/australia/information-technology/1751692/nsw-supreme-courts-new-rules-for-ai-in-legal-practice); [NSW District Court Gen AI Practice Note (PDF)](https://districtcourt.nsw.gov.au/documents/practice-notes/Gen_AI_Practice_Note.pdf); [Piper Alderman](https://piperalderman.com.au/insight/generative-ai-and-a-new-era-of-legal-technology-governance-in-the-supreme-court-of-nsw/)
- NSW: Judge Skaros referred a lawyer to the NSW Legal Services Commissioner after problematic AI citations and alleged quotes — [Barry Nilsson via Mondaq](https://mondaq.com/australia/information-technology/1751692/nsw-supreme-courts-new-rules-for-ai-in-legal-practice) (snippet only; case name not confirmed)
- NSW Chief Justice Bell (Sept 2025) was "unapologetic" about the restrictive rule and not ready to scrap it — [Lawyers Weekly](https://www.lawyersweekly.com.au/biglaw/42957-chief-justice-not-ready-to-scrap-restrictive-gen-ai-rule)
- UNSW published a report, "GenAI, Fake Law & Fallout" (Nov 2025), on Australian misuse cases — [UNSW](https://www.unsw.edu.au/news/2025/11/genai-fake-law-and-fallout-report)
- Scale (Charlotin AI Hallucination Cases database): 719 cases globally (Jan 2026), then 1,227 (early 2026), then 1,598 worldwide as of 9 June 2026, adding about 8 per day — [HAQQ tracker](https://haqq.ai/blog/ai-legal-hallucination-audit.html). The US count was 1,058 at the start of June 2026 — [UNC Law Library](https://library.law.unc.edu/2026/06/handling-hallucinations-a-reflection/). One Oct 2026 vendor page quotes a claim of 2,184 worldwide but flags it as unverified — [Vaquill](https://www.vaquill.ai/blog/hallucination-tracker-charlotin-risk-manager). About half the cases involve self-represented litigants — [jlellis.net](https://jlellis.net/blog/how-many-lawyers-have-gotten-in-trouble-because-of-ai-hallucinations-a-lot/). These counts are from different dates and scopes and are not directly comparable.

**Customer-facing generation: Air Canada**
- Moffatt v Air Canada, 2024 BCCRT 149 (14 Feb 2024): the airline was held liable for negligent misrepresentation by its website chatbot about the bereavement fare. Damages were C$650.88, plus C$36.14 interest and C$125 fees, for a total of C$812.02. The tribunal rejected Air Canada's argument that the chatbot was a separate entity responsible for its own actions — [CRT decision](https://decisions.civilresolutionbc.ca/crt/crtd/en/525448/1/document.do); [McCarthy Tétrault](https://www.mccarthy.ca/en/insights/blogs/techlex/moffatt-v-air-canada-misrepresentation-ai-chatbot); [Law360 Canada](https://law360.com/ca/it/articles/1804075/court-rejects-air-canada-s-remarkable-denial-of-liability-regarding-misinformation-by-its-chatbot)

**Legal research products (RAG) still hallucinate**
- The Stanford RegLab/HAI study ("Hallucination-Free?", 2024) found that Lexis+ AI and Thomson Reuters' Ask Practical Law AI gave incorrect information more than 17% of the time, and Westlaw AI-Assisted Research more than 34% of the time. Some summaries say about 33%; this conflicts slightly with the 34% figure — [Stanford HAI](https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries); [paper PDF](https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf); [VentureBeat](https://venturebeat.com/ai/stanford-study-finds-ai-legal-research-tools-prone-to-hallucinations). LexisNexis responded that its linked citations are "hallucination-free". CoCounsel was not tested — [VentureBeat](https://venturebeat.com/ai/stanford-study-finds-ai-legal-research-tools-prone-to-hallucinations). (2024, older)

### Inferences
- The Deloitte case maps almost one-to-one onto the person's competence. "Every extracted value or quote must appear in its source" is precisely the check that would have flagged the fabricated Federal Court quote and the phantom references before delivery. The direct cost was about A$97.6k, plus reputational and political cost. It is a strong opening anecdote for Australian pitches to consultancies, government and Big 4 firms.
- Court practice notes such as NSW SC Gen 23 now treat verification as a professional duty that cannot be delegated to AI. That creates demand for deterministic, non-LLM verification tooling, which matches the person's "deterministic processing only" approach.
- Even mature RAG products from Thomson Reuters and Lexis showed hallucination rates of 17–34% in independent testing. Retrieval alone is not enough; a post-generation verification layer is where value is added.

### Gaps
- Mata v. Avianca (SDNY, June 2023; US$5,000 sanction) is the canonical US case. It is from background knowledge and was not re-verified this session, so cite the primary order before use.
- I could not fetch the Charlotin database for a live Nov 2026 count or an Australia-specific count (host blocked).
- I did not find finance, health or media failure cases with quantified costs in this session (e.g. CNET's 2023 AI-article corrections, Sports Illustrated). They are worth a follow-up search.
- The Judge Skaros referral case name and citation are not confirmed.

## Success cases: eval and verification work that reduced errors or unlocked deployment

### Takeaway
Quantified, independently verified success numbers are scarce. Most come from vendors' own internal benchmarks. The clearest evidence is that leading vendors in high-stakes document generation, such as clinical scribes, market their verification layer as the product. One example is Abridge's "catches 97% of confabulations vs 82% for GPT-4o". Another is Australian company Heidi Health, which publishes a seven-layer evaluation framework.

### Cited Findings
- Abridge (Aug 2025 white paper): on an internal benchmark of more than 10,000 clinical encounters, its system caught 97% of confabulations, compared with 82% for general-purpose GPT-4o ("missing six times as many errors"). The benchmark is internal and not independently verifiable — [HLTH](https://hlth.com/insights/news/abridge-outlines-approach-to-eliminating-ai-hallucinations-in-clinical-notes-2025-08-25); [Becker's white paper](https://go.beckershospitalreview.com/hitwp/the-science-of-confabulation-elimination-toward-hallucination-free-ai-generated-clinical-notes)
- Heidi Health (Melbourne, Australia) publishes an evaluation framework. Each release runs seven evaluation layers in parallel, and the framework explicitly warns that a single "2% hallucination rate" figure "says far less than it appears" — [Heidi Health evaluation framework](https://www.heidihealth.com/resources/evaluation-framework)
- A March 2026 study in *Eye* compared six scribing tools on seven simulated ophthalmology encounters. Heidi was rated highest for documentation quality. The study is small and does not give an accuracy percentage — [iatroX analysis](https://www.iatrox.com/blog/heidi-ii-why-good-clinical-notes-are-not-proof-of-safe-clinical-agents)
- Research baseline: an npj Digital Medicine framework study found a 1.47% hallucination rate and a 3.45% omission rate in clinician-annotated LLM clinical summaries — [framework PDF](https://event.x-on.co.uk/hubfs/AVT/A%20framework%20to%20assess%20clinical%20safty%20and%20hallucination%20rates%20of%20LLMs%20for%20medical%20text%20summarisation_digital.pdf?hsLang=en). Reported scribe hallucination rates range from about 1% to 31% depending on definition — [American Bazaar](https://americanbazaaronline.com/2026/06/19/the-ambient-ai-scribe-illusion-doctors-need-to-pay-attention-483125/)
- Paul Weiss, an early Harvey user, said it could not yet determine ROI — [Yahoo Finance](https://sg.finance.yahoo.com/news/study-ai-copilots-lawyers-says-203106081.html)

### Inferences
- The fact that vendors compete on verification metrics (confabulation-catch rate, layered evals) shows that buyers in regulated domains pay for verified output, not raw generation. The person's "fabricated-value detection" is the same idea as Abridge's "confabulation elimination", applied to structured extraction.
- Heidi Health is an Australian employer whose public framework looks like the person's approach: multiple independent checks and scepticism of single headline numbers. It is a natural target.

### Gaps
- I found no verified, quantified figures this session for Klarna, Hebbia, Rogo, Thomson Reuters CoCounsel eval programs, Anthropic customer case studies, or insurance claims processors. These need follow-up; engineering blogs were not fetched.
- I found no independent head-to-head scribe hallucination comparison.

## Emerging job titles and teams

### Takeaway
"Eval-driven" applied AI roles exist in Sydney in 2026: Airtree's portfolio, Canva, Culture Amp, Checkbox, and gig evaluation work via Mercor and Mindrift. The exact titles "AI Evaluation Engineer" and "AI Quality Engineer" are rare in Australia. Evaluation usually appears as a core duty inside "Applied AI Engineer" or "Data Scientist, AI Evaluation" roles.

### Cited Findings
- "Founding Applied AI Engineer (Eval-Driven)", Sydney, Jan 2026 (Airtree portfolio): shipping design-audit workflows "that consistently meet measurable quality bars" — [Airtree jobs](https://jobs.airtree.vc/companies/airtree-2/jobs/65473669-founding-applied-ai-engineer-eval-driven); [Built In](https://builtin.com/job/founding-applied-ai-engineer-eval-driven/8237657)
- Canva: "Senior Machine Learning Engineer – AI Evaluation Platform (AU remote)". Now closed — [Blackbird jobs](https://jobs.blackbird.vc/companies/canva/jobs/73009806-senior-machine-learning-engineer-ai-evaluation-platform-au-remote)
- Culture Amp: Staff Applied AI Scientist (Sydney). Its AI Engineer ads list experience with "evaluation/benchmarking frameworks for AI systems" — [Blackbird jobs](https://jobs.blackbird.vc/companies/culture-amp/jobs/82397411-staff-applied-ai-scientist); [AI Engineer – Applied AI](https://jobs.blackbird.vc/companies/culture-amp/jobs/71809669-ai-engineer-applied-ai)
- Checkbox (Sydney, hybrid): "Data Scientist, AI Evaluation", designing evaluation frameworks — [jobr.pro listing](https://jobr.pro/job/40659442/data-scientist-ai-evaluation)
- Gig and contract evaluation work: Mercor "Rubrics Evaluator (AI Quality Assurance)" (May 2026, for a leading AI lab), via Hatch — [FinTech Australia jobs](https://jobs.fintechaustralia.org.au/companies/hatch-2-dbae3e38-35ae-47ae-81b2-d0cca9f5277a/jobs/79577661-rubrics-evaluator-ai-quality-assurance). Mindrift "Freelance Agent Evaluation Engineer" (NSW, part-time) — [Hatch](https://hatch.team/job/freelance-agent-evaluation-engineer-job_3EUm6cD97YrtftH2dyEXmXFzJrW)

### Inferences
- For a solo NSW developer, the strongest fits are "Applied AI Engineer (eval-driven)" at startups and "AI evaluation platform" roles at scale-ups (Canva, Culture Amp). Gig eval work (Mercor, Mindrift) gives quick income and credentials but undersells the engineering skill set.
- Pitch language should use the words employers use: "evaluation harness", "measurable quality bars", "benchmarking frameworks", "observability".

### Gaps
- Salary ranges were not captured.
- I did not search for forward-deployed engineer, LLMOps or model-risk/AI-assurance roles at Australian banks (CBA, NAB, Westpac, Macquarie) or Big 4 AI assurance practices. These need follow-up.
- No global job-volume statistics were found.

## Vendors selling verification/eval tooling: market evidence

### Takeaway
Eval and observability tooling has drawn substantial venture capital and, in 2025–26, a wave of acquisitions by large platforms. This signals that verification of LLM output is now treated as core infrastructure. Braintrust's US$800M valuation (Feb 2026) is the most solidly sourced figure. The acquisition figures below come from secondary sources and need checking against primary press releases.

### Cited Findings
- Braintrust: US$80M Series B led by ICONIQ at US$800M post-money (closed 17 Feb 2026), with a16z, Greylock and Elad Gil participating. This is up about 5.3x from its US$36M Series A at about US$150M (Oct 2024). Total raised is about US$121–124M — [FinSMEs](https://www.finsmes.com/2026/02/braintrust-raises-80m-in-series-b-funding.html); [Contrary Research](https://research.contrary.com/company/braintrust); [multiples.vc](https://multiples.vc/private-comps/braintrust)
- Humanloop: the team joined Anthropic in Aug 2025 and the platform was shut down — [ai-evals.tools via search snippet](https://ai-evals.tools/editorial/llm-evals-observability-company-acquisitions); [Atlan](https://atlan.com/know/ai-agent/ai-agent-evals/best-ai-agent-evaluation-platforms/)
- Arize AI: US$70M Series C (Feb 2025, Adams Street). A reported acquisition by Dynatrace for about US$915M (about US$815M cash) in Aug–Oct 2026. Sources conflict on the date; secondary only, unverified — [ai-evals.tools via search snippet](https://ai-evals.tools/editorial/llm-evals-observability-company-acquisitions); [botmemo](https://botmemo.com/ai-observability-llmops-funding-map)
- Galileo: US$45M Series B (Oct 2024; about US$68M total). Reported acquisition by Cisco (announced Apr 2026, completed 22 May 2026, folded into Splunk). Secondary only — [ai-evals.tools via search snippet](https://ai-evals.tools/editorial/llm-evals-observability-company-acquisitions); [devtune](https://devtune.ai/verticals/llm-observability-evals-gateways/galileo)
- Patronus AI: reported US$50M Series B led by Greenfield Partners (Jun 2026), about US$70M total. Secondary only — [Enterprise DNA](https://enterprisedna.co/resources/ai-map/company/patronus/)
- Langfuse (open-source LLM observability, Berlin): acquired by ClickHouse (announced 16 Jan 2026). Terms undisclosed; core stays MIT-licensed — [Tracxn](https://tracxn.com/d/companies/langfuse/__ShKqRFsp1-W_wOiiPE5R9ZjXs68jfy9uv88xZcE9pP0); [druce.ai](https://druce.ai/governance/wiki/vendors/langfuse)
- One aggregator claims about US$6B was raised in AI observability/LLMOps in 2026. This is a low-quality source with an unclear method — [botmemo](https://botmemo.com/ai-observability-llmops-funding-map)

### Inferences
- Large incumbents are buying eval tooling into their platforms: Anthropic (Humanloop), ClickHouse (Langfuse), and reportedly Cisco/Splunk (Galileo) and Dynatrace (Arize). This suggests eval and verification is becoming a standard layer of the enterprise stack. People who can design what to check, rather than only operate a tool, become more valuable as the tools commoditise.
- The person's competence (source-grounding checks, conflict detection, provenance, CI gates) is the design work these tools exist to support. Experience with Braintrust or Langfuse would make a pitch legible to hiring managers.

### Gaps
- Customer pricing (what enterprises pay for Braintrust, Arize, Galileo, Patronus, Cleanlab TLM or Guardrails AI) was not found this session.
- Cleanlab TLM and Guardrails AI funding and status were not researched.
- Primary press releases for the Arize/Dynatrace, Galileo/Cisco and Patronus deals were not fetched (host blocked or not attempted). Treat those deal figures as unverified.
