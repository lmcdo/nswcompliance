# Australian demand for verified AI document extraction and AI output assurance (excluding planning compliance), as of November 2026

Method note: all findings come from web search result summaries run on 2026-11-18. Direct page fetches failed because the session's network blocks most hosts (for example dta.gov.au and medicalrepublic.com.au did not resolve). Treat every figure as "per search snippet". Check the primary page before quoting it externally. Items dated before 2026 are marked [OLDER].

## Q1. Mandatory climate disclosure (AASB S2 / ASRS, ASSA 5010)

### Takeaway
This is the strongest and most clearly timed demand pocket. Group 2 entities report for financial years starting on or after 1 July 2026, and Group 3 from 1 July 2027. Their disclosures need limited assurance, moving to reasonable assurance, under ASSA 5010. Most auditors that hold only Group 3 clients are small or mid-tier firms with limited capacity. More than half of Group 1 entities brought in outside expertise.

### Cited Findings
- Group 2 generally starts reporting for financial years beginning on or after 1 July 2026, and Group 3 from 1 July 2027. — [AUASB auditor preparedness summary](https://www.auasb.gov.au/media/ojfjxroz/preparedness-of-australian-auditors_-assurance-summary_web.pdf)
- ASSA 5010 starts with limited assurance (review engagements) and moves to reasonable assurance (audit) over time. — [BDO](https://www.bdo.com.au/en-au/insights/esg-sustainability/proposed-path-to-assurance-over-sustainability-reporting); [CA ANZ](https://www.charteredaccountantsanz.com/news-and-analysis/news/the-current-sustainability-assurance-landscape)
- Group 2 thresholds: one search summary gave two of three: revenue over $200m, gross assets over $500m, or more than 250 employees. Another source framed the thresholds differently, so check the Corporations Act s292A text before quoting. — [KPMG guide](https://assets.kpmg.com/content/dam/kpmg/au/pdf/2024/australian-sustainability-reporting-legislation-standards-guide.pdf) [OLDER 2024]
- The 20 largest assurance providers audit the financial statements of more than 95% of Group 1 entities, 90% of Group 2 entities and about two-thirds of Group 3 entities. Of the 309 identified assurance providers, **238 have only Group 3 clients**, which points to a capacity problem. — [AUASB preparedness summary](https://www.auasb.gov.au/media/ojfjxroz/preparedness-of-australian-auditors_-assurance-summary_web.pdf)
- Assurance providers rate Group 2 and Group 3 entities as less prepared than those entities rate themselves. — [AUASB preparedness summary](https://www.auasb.gov.au/media/ojfjxroz/preparedness-of-australian-auditors_-assurance-summary_web.pdf)
- The auditor survey ran from November 2025 to April 2026, with 23 firm responses and 13 interviews. The report was published around June 2026. — [CA ANZ press release, 21 Aug 2026](https://www.charteredaccountantsanz.com/news-and-analysis/media-centre/press-releases/climate-reporting-drives-firms-to-build-capability-and-seek-external-expertise)
- **More than half of Group 1 entities engaged external expertise** to prepare their climate disclosures. This comes from University of Sydney, Monash and ANU research with CA ANZ, released 21 August 2026. — [University of Sydney](https://www.sydney.edu.au/news-opinion/news/2026/08/21/climate-reporting-drives-firms-to-build-capability-and-seek-expe.html); [CA ANZ](https://www.charteredaccountantsanz.com/news-and-analysis/media-centre/press-releases/climate-reporting-drives-firms-to-build-capability-and-seek-external-expertise)
- CPA Australia and CA ANZ have argued for relaxing Group 3 assurance where an entity has no material climate risks, mainly because of capacity concerns. — [CPA/CA ANZ submission to AUASB](https://auasb.gov.au/media/mltl1yst/sub9-assa5010_cpa-caanz.pdf)
- Mid-tier firms are offering sustainability assurance services, for example William Buck. — [William Buck](https://williambuck.com/services/audit-assurance/sustainability-assurance/)
- Consultancies such as ERM, SLR, Ramboll and Anthesis publish "lessons from Group 1" guides aimed at Group 2 reporters. This shows an active advisory market. — [ERM ASRS guide 2.0 (2026)](https://www.erm.com/globalassets/insights/documents/erm-asrs-guide-2.0---lessons-from-the-frontline-of-mandatory-climate-disclosure-preparation-2026-lr.pdf); [SLR](https://www.slrconsulting.com/afr/insights/mandatory-climate-reporting-in-australia-what-we-can-learn-from-group-1/)

### Inferences
- The buyers who fit a solo engineer best are (a) mid-tier and small audit firms facing their first ASSA 5010 limited-assurance engagements, who need evidence-tracing tools, and (b) Group 2 and Group 3 preparers, or the boutique ESG consultancies serving them, who need emissions activity data pulled from invoices, utility bills, fuel cards and supplier questionnaires with provenance back to the source page.
- Fabricated-value detection fits the assurance problem directly. Every disclosed figure needs an evidence trail, and auditors will sample it.
- Example first project: an "evidence ledger" pipeline for a boutique ESG consultancy or a mid-tier auditor. It extracts Scope 1 and 2 activity data (kWh, litres, GJ) from utility and fuel PDFs into a ledger linked to source page and bounding box, flags values with no source, and exports an auditor sampling pack. The Group 2 first-year cycle runs through 2026–27, so timing is now.

### Gaps
- No published contract sizes or rates for ESG data or assurance work were found.
- Exact Group 2 and Group 3 thresholds were not verified against the legislation.
- Whether Scope 3 reporting relief (first year) applies to Group 2 was not checked.

## Q2. Legal: court generative-AI practice notes and citation verification

### Takeaway
The rules are in force and the incidents keep coming. NSW SC Gen 23 has applied since 3 February 2025. Fabricated-citation cases keep surfacing, including a KC in the Victorian Supreme Court in a murder trial and an immigration matter citing 17 non-existent Federal Court cases. Some lawyers have been referred to regulators or sanctioned. No dedicated Australian citation-verification startup turned up, which suggests a gap, while incumbents (Thomson Reuters) and new entrants (MiAI Law) move in.

### Cited Findings
- NSW Supreme Court Practice Note SC Gen 23 was issued on 21 November 2024 and commenced on 3 February 2025 for all proceedings. [OLDER, still in force] — [NSW Bar Association](https://nswbar.asn.au/the-bar-association/publications/inbrief/view/1ccd75cdd5301be984646305b30152ff)
- SC Gen 23 bars Gen AI from drafting the content of affidavits, witness statements and character references. Expert reports cannot be drafted with Gen AI without the court's leave. Written submissions carry verification duties for citations; the exact wording is in paragraphs 13–16 of the PDF, which was not fetched. — [LSJ](https://lsj.com.au/articles/supreme-court-issues-historic-ai-guidance/); [Cowell Clarke](https://cowellclarke.com.au/insights/using-generative-artificial-intelligence-in-new-south-wales-courts-the-upcoming-dos-and-don-ts-for-practitioners-and-witnesses)
- The NSW District Court adopts SC Gen 23 as amended from time to time. — [District Court Gen AI Practice Note](https://districtcourt.nsw.gov.au/documents/practice-notes/Gen_AI_Practice_Note.pdf)
- The Law Society of NSW has corresponded with the Law Council about AI use in the Federal Court. A letter was republished on its site in 2026. — [Law Society NSW PDF](https://www.lawsociety.com.au/sites/default/files/2026-11/Ltr%20to%20LCA%20-%20AI%20use%20in%20the%20FCA%20-%205.6.25_redacted.pdf)
- A KC, Rishi Nathwani, apologised in the Supreme Court of Victoria murder trial for AI-generated fake quotes and citations. His team "checked that the initial citations were accurate and wrongly assumed the others would also be correct." Sources disagree on the date: AP's URL is August 2025, while a summary said January 2026. — [WTOP/AP](https://wtop.com/australia/2025/08/australian-lawyer-apologizes-for-ai-generated-errors-in-murder-case/)
- In an immigration case, submissions cited 17 Federal Court decisions that do not exist, and the lawyer was referred to the regulator. [OLDER 2025] — [Legal Technology](https://legaltechnology.com/australian-lawyer-reported-to-regulator-for-filing-fake-gen-ai-cases-in-court/)
- The first formal Australian sanction: a Victorian lawyer lost principal status after filing AI-fabricated citations. A 2025 count put instances of bogus AI citations in Australian courts at more than 20. — [Conrad Curry Law](https://conradcurrylaw.com.au/ai-in-the-courtroom-lessons-from-australias-first-ai-related-sanction/); [The Decoder](https://the-decoder.com/judges-slam-lawyers-and-litigants-for-submitting-ai-generated-nonsense-in-australian-courts/)
- Incidents continued into 2026: Oberoi v Douglas [2026] VSCA 31, and a Lawyers Weekly piece in August 2026 calling the criticism "a familiar refrain". — [Lawyers Weekly](https://www.lawyersweekly.com.au/biglaw/44829-blame-the-chatbot-ai-s-solution-to-legal-disciplinary-matters)
- Lawyers Weekly ran "Could your firm pass this AI verification test" (2026). — [Lawyers Weekly](https://www.lawyersweekly.com.au/corporate-counsel/45183-could-your-firm-pass-this-ai-verification-test)
- Vendors: MiAI Law (Australian) raised AUD $2m in March 2026 and offers verification workflows. Thomson Reuters launched Westlaw Advantage Australia at SYNERGY Sydney 2026 with inspectable citations. BriefCatch RealityCheck does citation verification but is US-only. Habeas, CaseChat, JurisTab and BarristerAI focus on research rather than verification. — [ITBrief MiAI](https://itbrief.com.au/story/miai-law-secures-aud-2-million-for-ai-legal-reasoning); [Thomson Reuters](https://insight.thomsonreuters.com.au/legal/posts/westlaw-advantage-australia-more-than-an-ai-upgrade); [ITBrief BriefCatch](https://itbrief.com.au/story/briefcatch-unveils-realitycheck-to-tackle-ai-errors); [Lawyers Weekly Habeas](https://www.lawyersweekly.com.au/biglaw/42157-australian-legal-tech-startup-habeas-cuts-research-time-in-half-firms-report)

### Inferences
- The market gap is an Australia-specific (AustLII/medium-neutral citation) checker that confirms a case exists, that the pinpoint is right, and that the quote actually appears in the judgment. That is the same problem as fabricated-value detection with provenance.
- Likely buyers: small and mid-size firms and barristers' chambers without Westlaw Advantage, legal practice management vendors (LEAP, Smokeball, InfoTrack) as integration partners, and professional indemnity insurers (Lawcover in NSW) as a channel. The last two are inference only and were not researched.
- Example first project: a pre-filing "authorities check" that parses a submission, resolves each citation against AustLII or the court's own judgment sources, verifies pinpoints and quotations, and outputs a report a practitioner can attach to the file. Pilot it with a small firm or a set of chambers. AustLII's terms of use for automated access need checking first.

### Gaps
- No pricing or contract data for Australian legal-tech verification tools.
- Did not verify the exact SC Gen 23 paragraph wording or any 2025–26 amendments.
- Did not research Federal Court, Victoria or Queensland practice notes in detail.

## Q3. Government: DTA policy, AI assurance, NSW AI Assessment Framework, Robodebt, procurement

### Takeaway
Rules with deadlines are creating assurance and evaluation work. The DTA's updated Policy for the responsible use of AI took effect on 15 December 2025, with requirements phasing in through December 2026, including AI impact assessments. NSW redesigned its mandatory AI Assessment Framework in early 2026, with registration and AI Review Committee escalation. The Deloitte–DEWR refund (2025) set the procurement precedent for "AI-fabricated content in a consultant report". Rates for small vendors were not found.

### Cited Findings
- The DTA's updated Policy for the responsible use of AI in government took effect on 15 December 2025. The first new mandatory requirement applies from 15 June 2026, and the rest from December 2026. The update came with a new AI impact assessment tool and procurement guidance. — [DTA article, 12 Jan 2026](https://www.dta.gov.au/articles/ai-policy-update-strengthening-responsible-use-across-government); [DTA media release, 2 Dec 2025](https://www.dta.gov.au/media-releases/ai-policy-overhauled-new-impact-assessment-tool-and-procurement-guidance)
- A third-party tracker says agencies must complete AI impact assessments for in-scope use cases, with a deadline of 15 December 2026. This was not confirmed on the DTA site. — [regulations.ai](https://regulations.ai/regulations/australia-2025-12-dta-ai-impact-assessment-tool)
- DTA guidance on moving AI from proof of concept to scale came out in March 2026, and technical guidance for trustworthy AI agents (an addendum to the AI technical standard) on 4 June 2026. — [DTA, 11 Mar 2026](https://www.dta.gov.au/media-releases/new-guidance-support-ai-project-success); [DTA, 4 Jun 2026](https://www.dta.gov.au/articles/trustworthy-ai-agents-new-technical-guidance)
- The DTA AI technical standard was released in August 2025 [OLDER]. The pilot AI assurance framework dates from September 2024 [OLDER]. — [RIMPA](https://www.rimpa.com.au/resource/new-ai-technical-standard-released-to-guide-responsible-government-use.html); [DTA blog](https://dta.gov.au/blogs/dta-pilots-new-ai-assurance-framework)
- NSW: all NSW Government AI use must apply the AI Assessment Framework (Circular DCS-2024-04). The framework was redesigned in early 2026 to replace "lengthy, subjective self-assessments" with a standards-aligned approach, and high-risk uses now trigger mandatory reviews. — [Digital NSW](https://www.digital.nsw.gov.au/nsw-artificial-intelligence-assurance-framework); [NSW media release](https://www.nsw.gov.au/departments-and-agencies/customer-service/media-releases/nsw-strengthens-ai-oversight-modernised-framework); [iTnews, Jan 2026](https://www.itnews.com.au/news/nsw-gov-to-make-ai-risk-assessments-less-subjective-623185?edate=20260128&eid=1)
- NSW AI Operational Policy: every AI use case must be registered in the AIAF platform, and high and critical cases go to the AI Review Committee. — [TechPartner News](https://www.techpartner.news/news/nsw-govt-issues-ai-operational-policy-627988)
- An audit-related report found 13 of 15 reviewed NSW AI projects had been assessed under the AIAF, recommended that all required solutions be assessed by 30 June 2027, and reported that "NSW agencies cannot say what AI they run". — [IDM](https://idm.net.au/node/15755)
- Deloitte agreed to a partial refund of an A$440,000 DEWR report that contained a fabricated quote from a Federal Court judgment and references to non-existent academic sources. AI use (Azure OpenAI GPT-4o) was disclosed only after the errors were found. Dr Christopher Rudge (University of Sydney) flagged the errors. [OLDER Oct 2025, but the reference incident] — [CFO Dive](https://www.cfodive.com/news/deloitte-refunds-60k-report-ai-errors-australian-government-accounting/); [Accounting Times](https://www.accountingtimes.com.au/technology/deloitte-to-refund-government-after-using-ai-in-440k-report); [Computerworld](https://www.computerworld.com/article/4069521/deloittes-ai-governance-failure-exposes-critical-gap-in-enterprise-quality-controls.html)
- BuyICT approaches to market ask for AI testing, evaluation and red-teaming. One example is an Akkodis/BuyICT AI Engineer role in Canberra to "conduct AI testing, evaluation and validation activities to assess solution accuracy, reliability..." No rate was published. — [Akkodis](https://www.akkodis.com/en-au/careers/jobs/ai-engineer-canberra/6753ea86-4183-44c8-17c9-f1a02c3cdd04)

### Inferences
- Robodebt Royal Commission material was not re-searched here. It remains the well-known Australian precedent for unlawful automated decisions, and together with the ADM privacy reforms (Q7) it drives agency caution.
- Small vendors most likely get in through (a) sub-contracting via BuyICT panel holders (labour-hire firms such as Akkodis), (b) NSW agencies needing evidence for AIAF assessments, and (c) agencies wanting an independent check of AI-assisted consultant deliverables after Deloitte. Option (c) is inference; no tender for it was found.
- Example first project: a "consultant deliverable verification" service. It checks every citation, quote and statistic in an AI-assisted report against its stated source and returns a provenance table. Sell it to an agency or a mid-tier consultancy wanting to avoid a Deloitte-style refund.

### Gaps
- DTA page text could not be fetched, so the exact mandatory requirements and scope (non-corporate Commonwealth entities) are not verified.
- No BuyICT rate cards or contract values for AI assurance were found. Talent International's 2026 rate guide exists but the figures were not visible. — [Talent International](https://www.talentinternational.com/blog/top-tech-contractor-day-rates-australia/)
- No 2026 Robodebt-related follow-up (for example, Commonwealth ADM legislative framework status) was researched.

## Q4. Health and aged care documentation (AI scribes, Aged Care Act)

### Takeaway
AI scribes are under active regulatory pressure. A TGA review of 12 suppliers found 8 likely contained functions that would make them medical devices, and its guidance was updated in October 2026 ahead of amendments from 1 November 2026. AHPRA expects clinicians to check every note. Australian scribe vendors (Heidi, Lyrebird) and health services therefore need independent accuracy evaluation of scribe output. The new Aged Care Act commenced on 1 November 2025, but no AI-specific documentation rule was found.

### Cited Findings
- TGA digital scribes guidance was updated around 16 October 2026 after a targeted review of 12 suppliers. None identified as a medical device, but the TGA found 8 of 12 had functions likely to make them one. A scribe that only records and transcribes is not a device; one that saves notes without clinician review points towards regulation. Related clinical decision support guidance is being aligned with amendments effective 1 November 2026. These come from secondary summaries and were not confirmed on tga.gov.au. — [Pure Global](https://www.pureglobal.com/news/australia-tga-digital-scribes-review-guidance-2026); [Medical Republic](https://www.medicalrepublic.com.au/tga-flags-compliance-action-on-ai-scribes-as-review-finds-safety-concerns/127888)
- The TGA flagged compliance action on AI scribes after its review found safety concerns. — [Medical Republic](https://www.medicalrepublic.com.au/tga-flags-compliance-action-on-ai-scribes-as-review-finds-safety-concerns/127888)
- A February 2026 Senate Estimates briefing described the scribe sector as having "little oversight", per a secondary summary. — [Digital Trends](https://digitaltrends.com/cool-tech/australian-government-warns-doctors-over-ai-scribing-tools-as-privacy-and-safety-concerns-grow)
- AHPRA expects practitioners to obtain informed consent and remain responsible for, and review, AI-generated notes. — [AGPAL](https://www.agpal.com.au/news/artificial-intelligence-in-general-practice-industry-guidance-for-safe-and-smart-use/); [Insight News](https://www.insightnews.com.au/medical-bodies-urge-caution-in-new-guidance-on-use-of-ai-scribes/)
- Victoria's Department of Health issued an ambient AI scribes advisory (June 2026 version), updating Safer Care Victoria's July 2025 advisory. — [health.vic.gov.au](https://www.health.vic.gov.au/sites/default/files/2026-06/ambient-ai-scribes-advisory.docx); [Safer Care Victoria](https://www.safercare.vic.gov.au/sites/default/files/2025-07/Ambient%20AI%20Scribes%20Advisory.pdf)
- Lyrebird Health publishes material on TGA regulation and AI scribes, which shows vendor sensitivity to it. — [Lyrebird](https://www.lyrebirdhealth.com/au/blogs/tga-regulation-and-ai-scribes)
- The Aged Care Act 2024 and the strengthened Quality Standards (7 standards, replacing 8) commenced on 1 November 2025. — [Department of Health](https://www.health.gov.au/our-work/aged-care-reforms/navigating-the-reforms); [Mallesons](https://www.mallesons.com/au/en/insights/latest-thinking/a-new-aged-care-act-what-is-changing-and-what-you-need-to-know.html)

### Inferences
- The opportunity is to evaluate scribe notes, not to build scribes: checking hallucinated findings, omitted medications and wrong doses against the transcript, with provenance from note sentence back to transcript span. Buyers would be hospital and PHN digital health teams, large GP groups doing procurement due diligence, or scribe vendors wanting evidence that review-in-the-loop holds for the TGA. Clinical data access and privacy will slow any solo engagement.
- Aged care is plausible (documentation for audits against the strengthened standards) but no direct evidence of AI-assurance demand was found.

### Gaps
- No primary TGA or AHPRA text was fetched.
- No evidence of procurement or contract sizes for scribe evaluation.
- No source found on AI use in aged care documentation or Commission audit evidence.

## Q5. Financial services (ASIC REP 798, CPS 230, claims, AFCA, advice files)

### Takeaway
ASIC REP 798 (October 2024) found governance lagging AI adoption across 624 use cases at 23 licensees, with heavy reliance on vendor models. The Scams Prevention Framework adds obligations with $50m penalties from (provisionally) 31 March 2027. Both drive demand for AI governance evidence, but no 2026 ASIC follow-up or specific contract evidence was found.

### Cited Findings
- REP 798 "Beware the gap" (29 October 2024) reviewed 624 AI use cases at 23 AFS and credit licensees. 14 planned to increase AI use, and of those 13 were planning or had started a governance uplift. For 13 of 23, at least half their models came from third parties. Only 12 had policies referencing fairness or bias, and only 10 referenced disclosure of AI use to consumers. ASIC says the law is technology-neutral. [OLDER] — [ASIC REP 798](https://asic.gov.au/regulatory-resources/find-a-document/reports/rep-798-beware-the-gap-governance-arrangements-in-the-face-of-ai-innovation/); [MinterEllison](https://www.minterellison.com/articles/asic-urges-stronger-ai-governance-for-afs-and-credit-licensees)
- Scams Prevention Framework: the Act was in force from 21 February 2025. Banks, telcos and digital platforms were designated in late May 2026. Draft codes and rules were released on 28 May 2026. AFCA membership was required by 1 September 2026. Most obligations are expected from 31 March 2027, with penalties up to $50m per contravention. The ACCC is the general regulator, with ASIC for banks and ACMA for telcos. — [ASIC SPF page](https://www.asic.gov.au/regulatory-resources/scams/scams-prevention-framework); [Baker McKenzie, Jun 2026](https://www.bakermckenzie.com/en/insight/publications/2026/06/australia-scams-prevention-draft-code-and-rules-released); [Clayton Utz](https://www.claytonutz.com/insights/2026/june/navigating-the-draft-spf-code-implications-and-responsibilities-for-banks); [HSF Kramer](https://www.hsfkramer.com/th/insights/2026-06/stage-1-of-the-scams-prevention-framework)
- Insurers show an "AI confidence gap", which puts brokers on notice. — [Insurance Business](https://www.insurancebusinessmag.com/au/news/technology/insurers-ai-confidence-gap-puts-brokers-on-notice-588710.aspx)

### Inferences
- The SPF will produce large volumes of documentation (scam reports, complaint files, evidence of "reasonable steps"). Digital platforms and smaller ADIs or telcos needing AFCA-ready case files are a possible extraction and verification market from 2027.
- Example first project: for a smaller AFS licensee or advice group, an AI-assisted advice file review (SOA vs fact-find consistency) with a provenance trail for every finding. This is consistent with REP 798's governance expectations. The project is inferred; no buyer evidence was found.

### Gaps
- Not researched due to the tool budget: APRA CPS 230 (commenced 1 July 2025 per general knowledge, not verified here), AFCA AI complaint data, insurance claims AI incidents, ASIC 2026 AI surveillance.

## Q6. Higher education and research integrity

### Takeaway
TEQSA continues to push assessment reform and lists Gen AI as a sector integrity risk in its Corporate Plan 2026–30. The demand is real but mostly sits inside universities and is pedagogical. It is a weaker fit for paid verification work by a solo engineer.

### Cited Findings
- TEQSA published "Enacting assessment reform in a time of artificial intelligence" (June 2026), the third in its assessment reform series. — [TEQSA PDF](https://www.teqsa.gov.au/sites/default/files/2026-06/enacting-assessment-reform-in-a-time-of-artificial-intelligence-web.pdf)
- TEQSA is moving to a more regulator-led framework from 2026. The Corporate Plan 2026–30 lists Gen AI among emerging risks to integrity and research quality. — [MinterEllison](https://www.minterellison.com/articles/a-year-of-reform-regulatory-changes-and-developments-relating-to-teqsa-in-2026)
- Research integrity concerns about AI (for example "data poisoning") come from a single secondary news source. — [Pick & Scroll](https://pickandscrollnews.beehiiv.com/p/ai-use-in-research-raises-integrity-concerns)

### Inferences
- A possible niche is reference and citation verification for theses, grant applications or systematic reviews. The same tooling as the legal citation checker could be applied to DOIs and Crossref. Buyers are uncertain: graduate research schools, journals, research offices.

### Gaps
- No primary ARC or NHMRC policy on AI in peer review was found, and no university procurement evidence.

## Q7. Other drivers: privacy ADM reforms, NDIS, tenders

### Takeaway
The privacy automated decision-making transparency obligation (APP 1.7–1.9) starts on **10 December 2026**, three weeks from now. Every APP entity using computer programs for significant decisions must describe them in its privacy policy. That requires an inventory of ADM, which is near-term discovery and documentation work. The NDIS new framework planning is in flux, and claims about AI-generated allied health reports could not be verified.

### Cited Findings
- New APP 1.7–1.9 obligations from the Privacy and Other Legislation Amendment Act 2024 commence on 10 December 2026. Privacy policies must disclose the kinds of personal information used in, and the kinds of decisions made by, computer programs that make or substantially assist significant decisions. They apply to decisions after commencement even if the data was collected earlier. — [Mallesons](https://www.mallesons.com/au/en/insights/latest-thinking/opening-the-black-box-adm-transparency-obligations-arrive.html); [Corrs](https://corrs.com.au/insights/automated-decision-making-preparing-for-the-new-transparency-obligation); [Hamilton Locke](https://hamiltonlocke.com.au/transparency-in-automated-decision-making-what-regulated-entities-need-to-know-and-do-before-december-2026/); [Gadens, "five weeks to 10 December"](https://www.gadens.com/insights/five-weeks-to-10-december-as-breaches-grow-and-frontier-ai-sharpens-cyber-threats,-transparency-on-adm-has-never-mattered-more)
- The OAIC is stepping up privacy enforcement, and one firm cites penalties up to about $66,000 for transparency failures (one firm's reading). — [MinterEllison](https://www.minterellison.com/articles/oaic-ramps-up-privacy-enforcement-are-you-ready)
- NDIS new framework planning: consultation fed back on concerns that the assessment tool (I-CAN) could reduce funding for allied health reports. A further consultation ran from August to October 2026, with draft rules due later in 2026. Start dates conflict across sources (1 July 2026 for 16+ versus other framings). — [Department of Health "what we heard"](https://www.health.gov.au/sites/default/files/2026-02/ndis-new-framework-planning-what-we-heard-summary-report.pdf); [How feedback was actioned, Aug 2026](https://www.health.gov.au/sites/default/files/2026-08/ndis-rules-public-consultation-new-framework-planning-how-feedback-was-actioned.pdf)
- A vendor blog claims the NDIA is alert to AI-generated allied health reports in its fraud detection work. **Unverified.** — [Assistive Tech](https://www.assistivetech.com.au/blogs/news/ai-in-clinical-practice-ndis-providers)

### Inferences
- Privacy ADM: law firms will write the policy wording, but the client first has to find out where ADM sits. Extracting decision logic and data fields from system documentation, contracts and vendor specs, with provenance, can be sub-contracted from mid-tier privacy and law firms. The window is short and is mostly remediation after the deadline.
- Tenders and bids: no sources were gathered. Verifying AI-drafted bid responses against compliance matrices is plausible but unevidenced here.

### Gaps
- The OAIC's own ADM guidance status was not confirmed.
- No research on tender or bid document AI, or on NDIS provider audit demand.

## Q8. Synthesis: candidate demand pockets for a solo engineer (ranked by evidence strength)

### Takeaway
Ranked by the strength of evidence in this note: (1) ASRS Group 2/3 evidence extraction and assurance support, (2) Australian legal citation verification, (3) verification of AI-assisted government and consultant deliverables (post-Deloitte, DTA and NSW AIAF), (4) clinical AI scribe output evaluation, (5) privacy ADM inventory before and after 10 December 2026, (6) financial services AI governance evidence and SPF case files (2027), (7) research and thesis citation checking, (8) NDIS and aged care documentation (weak evidence).

### Cited Findings
- See the sections above. Strongest quantified indicators: 238 of 309 assurance providers hold only Group 3 clients ([AUASB](https://www.auasb.gov.au/media/ojfjxroz/preparedness-of-australian-auditors_-assurance-summary_web.pdf)); more than half of Group 1 entities used external expertise ([USyd](https://www.sydney.edu.au/news-opinion/news/2026/08/21/climate-reporting-drives-firms-to-build-capability-and-seek-expe.html)); the A$440k Deloitte refund ([Accounting Times](https://www.accountingtimes.com.au/technology/deloitte-to-refund-government-after-using-ai-in-440k-report)); 8 of 12 scribes likely devices ([Pure Global](https://www.pureglobal.com/news/australia-tga-digital-scribes-review-guidance-2026)); 624 AI use cases with governance lag ([ASIC](https://asic.gov.au/regulatory-resources/find-a-document/reports/rep-798-beware-the-gap-governance-arrangements-in-the-face-of-ai-innovation/)).

### Inferences
- Common thread: each pocket needs "every output value traced to a source span, unsupported values flagged". That is the user's existing capability, carried over to new document types.
- Solo-friendly entry points are boutique and mid-tier intermediaries (ESG consultancies, mid-tier auditors, small law firms and chambers, BuyICT panel primes, privacy law firms) rather than direct enterprise or agency contracts.

### Gaps
- **Rates and contract sizes are the biggest gap.** No verified 2026 day rates for AI evaluation or assurance contractors, and no published contract values for ESG data or legal verification work, were found within the tool budget.
