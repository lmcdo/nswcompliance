# Techniques for LLM-based detection of latent needs, business pain and buyer intent in online text (state as of Nov 2026)

> Research method note: 15 tool calls. Search-result snippets were the main evidence base. Direct fetches of arxiv.org, papers.ssrn.com, mitsloan.mit.edu and zenml.io failed because those hosts are outside this session's network allowlist, so several figures below come from search summaries of the primary source and **have not been checked against the full PDF**. They are marked "[snippet-level]". Vendor statistics are marked "[vendor claim]".

## 1. Academic work on implicit/latent need detection, purchase intent, customer-need extraction from UGC, JTBD, pain-point mining: what accuracy do LLMs reach compared with humans?

### Takeaway
The strongest marketing-science evidence comes from the Timoshenko & Hauser line. Their 2019 paper showed ML makes need-finding from UGC more efficient. Their 2025 follow-up found that a **supervised fine-tuned LLM matched or beat professional analysts at extracting customer needs, while a base (prompt-only) LLM was not accurate or specific enough.** Peer-reviewed work on detecting B2B buyer intent in social posts with LLMs is thin. Most adjacent research covers e-commerce purchase intent, app-review requirements mining, or survey simulation. Accuracy depends heavily on the label scheme: binary "useful/relevant" tasks reach F1 of about 0.85–0.92, while fine-grained multi-class typing reaches about 0.4–0.75.

### Cited Findings
- **Foundational (2019, pre-LLM):** Timoshenko & Hauser, *Marketing Science*, "Identifying Customer Needs from User-Generated Content". They compared needs found in UGC with needs from interviews and found ML (a CNN filter for informative sentences plus embedding clustering to remove redundancy) made identifying needs from UGC more efficient — [SSRN abstract](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2985759); [ResearchGate](https://www.researchgate.net/publication/330743907_Identifying_Customer_Needs_from_User-Generated_Content)
- **LLM successor:** Timoshenko, Mao & Hauser, "Can Large Language Models Extract Customer Needs as well as Professional Analysts?" (SSRN 5167493, 2025; Marketing Science Institute Working Paper 25-101). In a blind comparison run with a consulting firm, the **supervised fine-tuned LLM was as good as or better than professional analysts**, and the **base LLM was not sufficiently accurate or specific** — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5167493); [MSI Report 25-101](https://thearf-org-unified-admin.s3.amazonaws.com/MSI_Report_25-101.pdf); [MIT Sloan summary](https://mitsloan.mit.edu/ideas-made-to-matter/large-language-models-can-help-professionals-identify-customer-needs). Timoshenko's site listed it as under review in 2026 — [artemtimoshenko.com](https://artemtimoshenko.com/index.html)
- A secondary citation reports that the fine-tuned model reached analyst-level performance **with as few as about 600 training examples** [snippet-level, secondary] — [arXiv 2608.16467 (Computational KJ-Ho)](https://arxiv.org/pdf/2608.16467)
- **Successors (2025–2026):**
  - LLM extraction of value-proposition dimensions (jobs, pains, gains, which map to JTBD) from Samsung Galaxy Watch reviews — [Electronics 14(22):4407, 2025](https://doi.org/10.3390/electronics14224407)
  - A comparative study of LLMs for automating customer-needs analysis on TripAdvisor and Reddit travel posts — [arXiv 2404.17975](https://arxiv.org/pdf/2404.17975v2) (full results not retrieved)
  - Mining *novel* customer needs from UGC using LLM-based data augmentation plus ensemble learning — [Int. J. Production Research, 2026](https://www.tandfonline.com/doi/full/10.1080/00207543.2026.2625971)
  - "Computational KJ-Ho", an insight-extraction framework for large qualitative datasets built on domain-specialised LLMs that aims to remove analyst bias — [arXiv 2608.16467](https://arxiv.org/pdf/2608.16467)
- **Implicit intent:** a 2026 preprint proposes a predefined library of explicit elements for auditable inference of implicit behavioural intent. Its framing is "explicit elements → implicit intent", which fits deterministic, auditable pipelines [title/abstract only] — [arXiv 2606.11207](https://arxiv.org/pdf/2606.11207)
- **Purchase intent (adjacent):** MIND (EMNLP 2024) distils shopping intentions from large vision-language models over e-commerce product metadata. It does not cover social posts — [arXiv 2406.10701](https://arxiv.org/abs/2406.10701v3). A 2025 paper shows LLMs can *simulate* human purchase-intent survey responses through semantic-similarity mapping to Likert scales. This is survey simulation, not detection — [arXiv 2510.08338](https://arxiv.org/abs/2510.08338). A 2025 multimodal intent-recognition survey lists purchase intent as a marketing application — [arXiv 2507.22934](https://arxiv.org/html/2507.22934v1)
- **App-review / requirements mining (closest analogue to "pain" classification, with numbers)** [snippet-level]:
  - Fine-tuned BERT flagging reviews as useful for requirements: **accuracy 92.4%, F1 92.39%** — [arXiv 2409.15473](https://arxiv.org/abs/2409.15473v1)
  - Zero-shot ChatGPT classifying functional/non-functional requirements: **F1 0.842** with an optimised prompt at temperature 0.2, beating traditional ML. The dataset is reported as either 1,880 or 2,000 reviews — [arXiv 2505.04759](https://arxiv.org/html/2505.04759v1)
  - Lightweight open LLMs: user-request classification **F1 0.32–0.74** (best: Llama 3 few-shot at 0.74) and NFR classification **0.40–0.55** — [arXiv 2510.23055](https://arxiv.org/html/2510.23055v1)
  - Adding LLM-labelled data to training sets "significantly enhances" downstream classifier performance — [arXiv 2507.08250 summary](https://arxiv.deeppaper.ai/papers/2507.08250v1)
- **LLM compared with human annotators in general (foundational, 2023):** zero-shot ChatGPT beat MTurk crowd workers by about **25 percentage points** on average across tweet and news annotation tasks, at under $0.003 per annotation (about 30× cheaper). Accuracy was measured as agreement with trained annotators. Binary relevance accuracy ranged from **59% to 83%** depending on dataset — [Gilardi, Alizadeh & Kubli, PNAS 2023 / arXiv 2303.15056](https://arxiv.org/pdf/2303.15056)
- **Pain-point mining in practice is mostly tooling, not research:** Problem Miner, IdeaPicker and Apify's "Reddit Pain Point AI" scrape Reddit and X for complaints and "I wish this existed" posts, and some use keyword seeds like "hate", "frustrated", "how to" before passing posts to the LLM [vendor claim; no accuracy reported] — [Product Hunt: Problem Miner](https://www.producthunt.com/products/problem-miner/launches); [IdeaPicker](https://www.producthunt.com/products/ideapicker); [Apify actor](https://apify.com/wombat951/reddit-pain-point-ai.md). A typical extraction prompt schema has the columns pain point, frequency, intensity, user quote and current workaround — [promptsdaily](https://promptsdaily.substack.com/p/reddit-problem-mining-prompt-system)

### Inferences
- The most consistent research result is that **fine-tuning on a few hundred domain-labelled examples is what closes the gap to expert humans**. Prompt-only base models under-perform on specificity. That makes a small, high-quality gold set a core asset.
- High headline accuracy figures usually come from binary relevance labels. "Is this person a buyer with a specific need?" is a fine-grained, multi-attribute task and should be expected to sit nearer the 0.5–0.75 F1 band without fine-tuning.
- Tools that seed with keywords ("frustrated", "I wish") partly undercut the "beyond keyword" goal. Recall on implicit needs, where no complaint keyword appears, is untested in every source found.

### Gaps
- No peer-reviewed benchmark was found for **B2B buying-intent detection in forum or social posts with LLMs** (precision/recall against humans). This is a genuine evidence gap, not a search miss alone (two searches returned only adjacent work).
- Exact accuracy numbers from Timoshenko, Mao & Hauser (precision/recall of needs, the number of analysts) could not be retrieved because SSRN and MIT Sloan were blocked.
- No dedicated academic paper on **LLM jobs-to-be-done extraction** from social text was found beyond the jobs/pains/gains value-proposition paper.

## 2. Economics: LLM cascades and routing, embeddings and clustering, active learning, outcome labels

### Takeaway
Cascades work: cheap model first, escalate only when uncertain. The 2023 FrugalGPT paper reports up to 98% cost reduction at GPT-4 quality, and 2025–26 work reaches near-large-model quality at about 40% of compute, or with escalation on about 15% of calls. Two caveats apply. First, LLM self-reported confidence is poorly calibrated. Second, when false positives are expensive, a single large model can beat a cascade. For discovery and themes, BERTopic (embeddings + UMAP + HDBSCAN) remains a strong, cheap baseline. LLM topic methods (TopicGPT) align better with human labels but cost more.

### Cited Findings
- **FrugalGPT (foundational, 2023):** three cost levers are prompt adaptation, LLM approximation and LLM cascade. The learned cascade matches GPT-4 with **up to 98% cost reduction**, or improves accuracy by 4% at the same cost, across 12 APIs. Cost = prompt tokens + generation tokens (+ a fixed per-call fee) — [arXiv 2305.05176](https://arxiv.org/pdf/2305.05176); cascade mechanics summary — [bdtechtalks](https://bdtechtalks.com/2023/06/12/reduce-costs-of-chatgpt-gpt-4/)
- **Semantic-agreement cascades (2025):** sample several small models and defer to the large model when they disagree. This reaches roughly target-model quality at **about 40% of compute and up to 60% lower latency**, and needs no trained router. Learned routers must be retrained when the models change — [arXiv 2509.21837](https://arxiv.org/html/2509.21837v3)
- **Generation-margin two-tier selection:** the small model's token-probability margin alone serves as the escalation signal, tested on 9 tasks and 3 model pairs — [arXiv 2405.02134](https://arxiv.org/html/2405.02134v1)
- **ReDAct (2026):** perplexity-based deferral in an agent matched full large-model performance while calling the large model on **about 15% of steps** — [arXiv 2604.07036](https://arxiv.org/pdf/2604.07036)
- **When cascades lose:** an economic evaluation found that a standalone large model often beats a small-to-large cascade **once the cost of an error is high enough**. Cascade error depends on how well the deferral rule tracks the small model's real uncertainty, and cost scales roughly linearly with the deferral rate — [arXiv 2507.03834](https://arxiv.org/pdf/2507.03834)
- **Calibration fixes:** 2026 preprints argue that confidence-threshold deferral is miscalibrated and propose isotonic regression (UCCI) or conformal guarantees [unverified claims] — [Conformal Cascade](https://www.alphaxiv.org/abs/2607.25018.md); [UCCI listing](https://awesomepapers.io/similarity-search/papers/2605.18796)
- RouteLLM figures as relayed by a practitioner blog: about 95% of frontier quality with 85% of queries routed to cheaper models, and 45–85% cost reduction [secondary; not verified against the RouteLLM paper] — [tianpan.co](https://tianpan.co/blog/2025-11-03-llm-routing-model-cascades)
- **Topic discovery:** TopicGPT beat BERTopic on alignment with human labels (harmonic purity 0.74 vs 0.58 on Wiki, 0.57 vs 0.39 on Bills) — [arXiv 2311.01449](https://arxiv.org/pdf/2311.01449). BERTopic generally leads on automated coherence, sometimes with repetitive wording — [LLM-as-evaluator review](https://themoonlight.io/review/bridging-the-evaluation-gap-leveraging-large-language-models-for-topic-model-evaluation). A 2025 Hamburg thesis found BERTopic best overall (low weight: student thesis) — [uni-hamburg](https://www.inf.uni-hamburg.de/en/inst/ab/lt/teaching/theses/completed-theses/2025-ba-schaland.pdf). Small open models (Llama 7B/13B) produce more irrelevant topic labels than GPT-class models — [LimTopic arXiv 2503.10658](https://arxiv.org/pdf/2503.10658). LLM topic modelling has granularity and hallucination problems — [arXiv 2405.00611](https://arxiv.org/pdf/2405.00611)
- **Distillation / LLM labels as training data:** LLM-labelled augmentation improves app-feedback classifiers — [arXiv 2507.08250](https://arxiv.deeppaper.ai/papers/2507.08250v1). LLM-based data augmentation plus an ensemble improves novel-need mining — [IJPR 2026](https://www.tandfonline.com/doi/full/10.1080/00207543.2026.2625971)

### Inferences
- **Economical best-practice pipeline** (synthesis, not from any single source):
  1. Cheap recall stage: embeddings plus semantic search against "need/pain prototype" descriptions, rather than keywords.
  2. A small classifier, fine-tuned or distilled from LLM labels, scores relevance.
  3. A small LLM extracts a structured need/pain record.
  4. Only uncertain or high-value items go to a frontier model or agent. Escalation is based on multi-sample disagreement or margin, not verbalised confidence.
  5. Clustering (BERTopic/HDBSCAN) of the extracted needs measures repetition across communities.
  6. Reply and conversion outcomes feed back as labels for retraining and threshold recalibration.
- Because outreach false positives cost reputation as well as money, arXiv 2507.03834 implies the escalation threshold should be set by the cost of a false positive, not tuned for accuracy alone.

### Gaps
- No primary-source evidence was found for **active learning applied specifically to intent/lead classification**, or for **conversion outcomes used as training labels** in published systems. Practitioner claims exist, but no measured write-ups were retrieved.

## 3. Context following and agentic investigation: thread, author history, cross-community repetition, value-of-information escalation; published GTM-agent systems

### Takeaway
The best-documented production system is Clay's Claygent, a web-research agent run at very large volume. Clay reportedly had to rebuild its evaluation programme after early evals proved inadequate. LLMs can infer author attributes from posting history with high accuracy (85% top-1, ICLR 2024), which makes author-history context powerful but also a privacy risk. Uncertainty-based deferral (perplexity, disagreement) is the published mechanism closest to "agents that decide when to dig deeper". No vendor was found publishing a measured value-of-information design.

### Cited Findings
- **Claygent:** an AI research agent that visits websites live and returns structured answers. A typical task costs 5–15 credits, about $0.15–1.12 per lead including other enrichment [third-party guide] — [Octave guide](https://www.octavehq.com/post/what-is-claygent-clay-ai-research-agent-guide); [Arcade guide](https://www.arcade.software/guides/how-to-use-claygent-ai-research-in-clay)
- Clay reportedly runs **300M+ Claygent runs per month** and **rebuilt its evaluation programme after early evaluations proved inadequate** [secondary summary of a Clay talk; not verified against primary material] — [ZenML LLMOps database](https://www.zenml.io/llmops-database/production-evaluation-and-data-foundations-for-go-to-market-agents). Clay's Head of AI described Claygent as checking whether a company is worth contacting *at a given time* — [Taskade write-up](https://www.taskade.com/wiki/ai-agent-examples/clay-gtm-agents-at-scale)
- **Common Room** says it has agents comparable to Claygent, grounded in a unified "signal graph", with persistent identity profiles that follow people across job changes [vendor claim] — [Common Room vs Clay](https://www.commonroom.io/compare/clay)
- **Author-history inference:** across 9 LLMs (GPT-4, Claude 2, Llama 2, etc.) and 8 attributes (location, income, sex, etc.) on real Reddit profiles, models reached **up to 85% top-1 and about 95% top-3 accuracy**, at 100× lower cost and 240× less time than humans. Text anonymisation and model alignment did not prevent it — [Staab et al., ICLR 2024, arXiv 2310.07298](https://arxiv.org/abs/2310.07298); [ETH project page](https://eth-sri.github.io/publications/staab2023beyond)
- **Uncertainty-triggered escalation in agents:** perplexity-based deferral with about 15% large-model calls (ReDAct) — [arXiv 2604.07036](https://arxiv.org/pdf/2604.07036)

### Inferences
- The Staab result supports the idea that author history improves role, seniority and company-size inference, which is the core of B2B qualification. It is also a regulatory/ethical constraint: profiling individuals from their posting history is exactly what the paper frames as a privacy violation (relevant to GDPR and the Australian Privacy Act).
- "Dig deeper" decisions can reuse cascade machinery. Escalate to thread fetch, author history, then company research only when (a) the classifier is uncertain and (b) the expected deal value justifies the agent cost (about $0.15–1+ per lead in Claygent-style pricing).

### Gaps
- **No engineering blog with measured results** from Exa, Anthropic or OpenAI cookbooks on agentic lead research was retrieved; the search returned nothing on Exa.
- No published study measured the **lift from whole-thread or cross-community context** over single-post classification for intent detection.

## 4. Detecting discussant "state": frustration, workaround language, sunk cost, time pressure, role/seniority, business size

### Takeaway
Evidence is weak. One older academic paper on churn-intent detection exists (CoNLL 2018), along with rule-based frustration-detection patents and vendor blogs. LLM inference of demographics and socioeconomic attributes from text is well evidenced (Staab 2024). No validated study was found for linguistic markers of sunk cost, workaround or time pressure.

### Cited Findings
- Churn-intent classifiers for German and English chatbot and social-media text, trained on social data and transferred to chatbot conversations (foundational, 2018) — [Abbet et al., CoNLL 2018](https://arxiv.org/pdf/1808.08432); [ACL Anthology K18-1016](https://preview.aclanthology.org/teach-a-man-to-fish/K18-1016)
- Rule-based frustration-cue detection in call transcripts, with weighted cues and text offsets. No validation results are reported — [US Patent 11302346](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11302346); [US Patent 11900960](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11900960)
- Vendor heuristics for churn signals include "considering alternatives", time-bound language, and a shift from feature requests to complaints [anecdotal, vendor] — [Zonka Feedback](https://www.zonkafeedback.com/blog/qualitative-analysis-for-churn-detection); [Zigment](https://zigment.ai/blog/optimizing-retention-conversation-analysis-detects-churn); [Enterpret](https://www.enterpret.com/guides/how-to-identify-churn-risk-from-nps-verbatims)
- Practitioner seed phrases for pain and workarounds: "I wish there was", "how do you handle", "how do you solve" — [echai.ventures](https://echai.ventures/how-founders-use-ai/market-research/how-do-i-mine-reddit-reviews-and-online-communities-with-ai-to-find-real-pain-points)
- LLMs infer income, location and similar attributes from Reddit text (85% top-1) — [arXiv 2310.07298](https://arxiv.org/abs/2310.07298)

### Inferences
- Treat "state" features (frustration, workaround, deadline) as LLM-extracted structured fields. Validate each one against a human-labelled sample before using it in scoring, because no published marker set has been validated for buyer intent.

### Gaps
- No research found on **sunk-cost or time-pressure linguistic markers** as purchase predictors, or on **LIWC-style features for B2B intent**.
- No validated method was found for **business-size inference from posts** specifically. Staab covers personal income, not firm size.

## 5. Event/trigger-based signals: conversion effect compared with cold outreach

### Takeaway
Nearly all evidence is vendor-published and uncontrolled. Reported reply rates for trigger-based outreach range from about 4–8% (conservative) to 15–40% (stacked signals), against about 1–4% for cold. The only rigorous timing research is the older speed-to-lead work: HBR 2011 found contact within an hour was about 7× likelier to produce a qualifying conversation. That work concerns inbound response speed, not outbound triggers.

### Cited Findings
- Cold baseline about 3% vs signal-based 15–25% reply [vendor claim] — [LinkedOtter](https://www.linkedotter.com/articles/signal-based-outreach-5x-reply-rate-vs-cold-email-june-2026)
- Job change: 14–22% vs 3–4% untargeted; replies drop after 30 days [vendor] — [FirstSales](https://firstsales.io/blog/job-change-trigger-email/); [Autobound](https://www.autobound.ai/blog/sales-trigger-events-templates)
- Funding trigger: 31% reply rate in an agency's own case study [vendor] — [Cleverly](https://www.cleverly.co/blog/trigger-based-cold-email)
- Stacking 2–3 signals: 25–40% [vendor] — [OneAway](https://oneaway.io/blog/best-email-outreach-signals-triggers-in-2026-ranked); [Airopeway](https://www.airopeway.com/blog/signal-based-outbound-guide)
- Outreach within 24–48 h of a trigger: 3–5× response vs a week or more later [vendor] — [PredictLeads](https://predictleads.com/blog/sales-trigger-events-outbound-timing/)
- Conservative: 4–8% for well-run trigger campaigns vs 1–2% static lists [vendor] — [Puzzleinbox](https://puzzleinbox.com/blog/cold-email-trigger-events-job-change-funding-hiring-2026/)
- **Foundational timing evidence:** Oldroyd, McElheran & Elkington, HBR 2011. Contact within one hour was about 7× likelier to produce a qualifying conversation with a decision maker than waiting another hour, and more than 60× likelier than waiting 24+ hours. The lead-count sample is reported inconsistently (1.25M / 2.2M / 2.24M). The separate 2007 InsideSales/MIT study gives 21× at 5 minutes vs 30 minutes. It measured *qualification*, not closes, and is often misquoted as "21× more likely to close" — [Rework summary](https://resources.rework.com/libraries/marketing-sales-alignment/five-minute-response-sla); [InsideSales/MIT slides](https://pt.slideshare.net/slideshow/insidesales-mit/1809952); [Callingly](https://callingly.com/blog/state-of-speed-to-lead)

### Inferences
- The direction (timely, relevant signal beats cold) is consistent across sources, but the magnitude is unreliable. Any pipeline should run its own holdout control group.
- Regulatory-change triggers, such as a new planning instrument or a rule amendment, are a plausible trigger class. No outreach-conversion evidence was found for them specifically.

### Gaps
- **No controlled or peer-reviewed study** of trigger-based compared with cold B2B outreach conversion was found.
- No evidence was found on **tool-sunset or regulatory-change triggers** specifically.

## 6. Calibration and evaluation: measuring intent-detection precision, feedback loops from reply/conversion data

### Takeaway
Do not trust verbalised LLM confidence. It is systematically overconfident, though reasoning models are better calibrated. Precision should be measured against a human-labelled gold set using metrics suited to the label scheme, and calibrated with held-out data (isotonic/conformal). Clay's experience suggests naive evals fail at scale. No published system with measured reply/conversion feedback loops was found.

### Cited Findings
- LLMs verbalising confidence tend to be overconfident. Calibration improves with scale but remains "far from ideal" — [Xiong et al., ICLR 2024, arXiv 2306.13063](https://arxiv.org/pdf/2306.13063)
- GPT-3.5, GPT-4, LLaMA-2-70b and PaLM 2 have high calibration error and are overconfident most of the time. The paper proposes a Net Calibration Error metric — [Groot & Valdenegro-Toro, TrustNLP 2024](https://aclanthology.org/2024.trustnlp-1.13.pdf)
- Large reasoning models are better calibrated in verbalised confidence than instruction-tuned models — [arXiv 2504.06564](https://arxiv.org/pdf/2504.06564)
- Accuracy in LLM annotation studies is typically defined as agreement with trained annotators — [Gilardi et al.](https://arxiv.org/pdf/2303.15056)
- Clay rebuilt its GTM-agent evaluation after early evals proved inadequate [secondary] — [ZenML](https://www.zenml.io/llmops-database/production-evaluation-and-data-foundations-for-go-to-market-agents)
- Conformal and isotonic calibration proposed for cascade deferral [preprints] — [Conformal Cascade](https://www.alphaxiv.org/abs/2607.25018.md)

### Inferences
- A practical evaluation stack:
  1. A stratified human-labelled gold set, with inter-annotator agreement reported.
  2. Precision@k on the ranked lead list (what sales actually consumes).
  3. Calibration curves or ECE on held-out data.
  4. Downstream reply and meeting rate against a random or holdout control.
  5. Periodic re-labelling to detect drift.

### Gaps
- No published case study with measured numbers was found for **closing the loop from reply/conversion outcomes into classifier retraining** for intent detection.

## 7. Known failure modes: false positives, bias to tech-savvy communities, prompt injection from scraped content, hallucinated lead details

### Takeaway
Prompt injection in scraped web content is now measured in the wild: 15,300 validated instances across 1.2B URLs, about 70% hidden in non-rendered HTML. It directly threatens lead-research agents. Sampling bias toward vocal, tech-savvy communities is widely acknowledged but unquantified. LLM topic and label generation hallucinates, especially on small models.

### Cited Findings
- 15,300 validated indirect-prompt-injection instances across 11,700 pages from 1.2B URLs analysed. About **70% were in non-rendered HTML** (headers, comments, metadata). Researchers say attacks are "no longer hypothetical" — [Infosecurity Magazine](https://www.infosecurity-magazine.com/news/researchers-10-wild-indirect/?from=kiberboloid); [Gurucul](https://gurucul.com/latest-threats/indirect-prompt-injection-in-web-content-targets-ai-agents/); [arXiv 2604.27202](https://arxiv.org/pdf/2604.27202); [web headers study](https://letsdatascience.com/news/web-headers-expose-indirect-prompt-injection-risk-7ffeb9b1)
- Web-search tools in agents can be exploited for data exfiltration — [arXiv 2510.09093](https://arxiv.org/html/2510.09093v1). A red-teaming proxy exists for testing browsing agents — [IPI-proxy arXiv 2605.11868](https://arxiv.org/pdf/2605.11868)
- The root cause is that models cannot reliably separate data from instructions. PortSwigger advises constraining agent permissions even if the attacker steers its plan — [PortSwigger](https://portswigger.net/web-security/llm-attacks/ai-powered-scanner-vulnerabilities). OWASP LLM Top 10 2025 classifies indirect injection under LLM01 — [SPLX](https://splx.ai/blog/indirect-prompt-injection-agentic-ai-security)
- LLM topic modelling suffers granularity and hallucination problems — [arXiv 2405.00611](https://arxiv.org/pdf/2405.00611). Small models produce irrelevant topic labels — [LimTopic](https://arxiv.org/pdf/2503.10658)
- Reddit skews toward vocal, tech-savvy users, so complaint frequency can reflect posting habits rather than market size [practitioner observation, not measured] — synthesis from practitioner sources such as [echai.ventures](https://echai.ventures/how-founders-use-ai/market-research/how-do-i-mine-reddit-reviews-and-online-communities-with-ai-to-find-real-pain-points)
- LLM author profiling works too well (85% top-1), which creates privacy and compliance risk — [arXiv 2310.07298](https://arxiv.org/abs/2310.07298)
- Base LLMs are "not sufficiently accurate or specific" at need extraction without fine-tuning, so the failure mode is generic, vague needs — [Timoshenko, Mao & Hauser](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5167493)

### Inferences
- Mitigations for lead pipelines:
  - Strip HTML comments and metadata before passing scraped content to the LLM.
  - Never let scraped content trigger actions such as sending email or writing to the CRM without validation.
  - Require every extracted lead fact to carry a verbatim source quote and URL, and reject facts that lack one. This is the main defence against hallucinated details.
  - Weight cross-community repetition rather than a single community's volume.

### Gaps
- No quantified study was found of **hallucination rates in LLM lead enrichment** (fabricated names, titles, company facts).
- No measurement was found of **community/demographic bias** in intent-mining coverage (for example, trades or older SME owners who post less online).
- Several primary sources (SSRN, arXiv full text, MIT Sloan, ZenML) could not be fetched because of the session network allowlist. Allowing arxiv.org, papers.ssrn.com, mitsloan.mit.edu and www.zenml.io would make it possible to verify the snippet-level figures above.
