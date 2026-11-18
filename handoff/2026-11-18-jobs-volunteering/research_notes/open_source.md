# Open-sourcing a NSW planning-compliance project (as of November 2026)

> Information, not legal advice. Items marked **[LAWYER]** need advice from an Australian IP or privacy lawyer before release.
>
> **How this was researched:** the session's network blocked direct fetches of legislation.nsw.gov.au, planningportal.nsw.gov.au, huggingface.co and wikimedia.org.au. Findings on those sites come from search-engine snippets of the pages, not from reading the pages. Check the exact licence wording on each page before relying on it. Repo facts were checked locally (commands are given inline).

## 1. Copyright and licensing of the source material

### Takeaway
Most of the *state* inputs can be republished commercially with attribution: NSW legislation (CC BY 4.0) and Planning Portal and Spatial Services spatial data (CC BY 4.0, with some mirrors still listing CC BY 3.0 AU). **Council DCPs are the real risk.** Their licences vary from CC BY 4.0 to "personal / in-house / non-commercial only, all other rights reserved". Australia has no sui generis database right, so a set of *extracted, restructured facts* (setback numbers, height controls) is on stronger ground than verbatim DCP text. That is an inference from IceTV and Telstra, not a safe harbour **[LAWYER]**.

### Cited findings

**NSW legislation (LEPs, SEPPs)**
- The NSW Legislation website licenses its content under Creative Commons Attribution 4.0 International. It sets out two attribution forms: altered content credits the site as the source with the download date and a link, and unaltered content uses "Sourced from" the site. It warns that CC licences cover copyright only, and that some material on or through the site may not be under CC — [NSW Legislation copyright page](https://legislation.nsw.gov.au/copyright) (search snippet; page not fetched).
- Some NSW agency copyright notices list legislation as *excluded* from their own CC BY terms. Examples are [DCJ](https://dcj.nsw.gov.au/content/dcj/dcj-website/dcj/statements/copyright-and-disclaimer.html) and [Greater Sydney Parklands](https://www.greatersydneyparklands.nsw.gov.au/copyright). These notices cover the agencies' own sites. For legislation text, the legislation.nsw.gov.au licence is the one that applies.
- Background: an AustLII seminar paper (2013) says NSW waived copyright in its legislation in 1995 — reported via search summary, [Cornell JOAL article](https://ojs.law.cornell.edu/index.php/joal/article/download/9/31/102). This is a secondary claim. The current CC BY 4.0 notice is the operative term.

**NSW Planning Portal and data.nsw spatial layers / APIs**
- Planning Portal EPI datasets, for example *Additional Permitted Uses*, are offered under CC BY 4.0 with the attribution "NSW Department of Planning, Housing and Infrastructure" — [Planning Portal open data listing](https://www.planningportal.nsw.gov.au/opendata/dataset/environmental-planning-instrument-permitted-uses); [data.nsw mirror](https://data.nsw.gov.au/data/dataset/3d55e620-6579-4357-9f55-b158bd3e2ca9).
- The ePlanning *Online PCC Data API* and *Online CDC Data API* listings say only "Creative Commons Attribution", with no version — [Online PCC Data API](https://www.planningportal.nsw.gov.au/opendata/dataset/e1e1872c-ad66-43a7-b9b4-2c31df8ad6be); [Online CDC Data API](https://www.planningportal.nsw.gov.au/opendata/dataset/3fe52cdb-5526-4d26-9bc5-c2999e284f75).
- **Conflict:** data.gov.au mirrors of some NSW EPI datasets (Local Provisions, Land Application) list **CC BY 3.0 AU** — [data.gov.au Local Provisions resource](https://www.data.gov.au/data/dataset/nsw-environmental-planning-instrument-local-provisions/resource/127e3437-be5e-4311-a84d-ab7118480850); [Land Application resource](https://www.data.gov.au/data/dataset/nsw-environmental-planning-instrument-land-application-lap/resource/0d54d46d-bff2-47b4-a767-9354a93fba4b). Check each layer on its canonical Planning Portal or data.nsw page.
- I found no general Planning Portal "API terms of use" page. The licence position for the API rests on the per-dataset listings above.
- NSW Spatial Services data is CC BY 4.0, attributed as "© State of New South Wales (Spatial Services, a business unit of the Department of Customer Service NSW)" — [Spatial Services licence item](https://portal.spatial.nsw.gov.au/portal/sharing/rest/content/items/10de9a9d0fa14463af77b4f3e18279a9/data); [spatial.nsw.gov.au/copyright](https://www.spatial.nsw.gov.au/copyright).
- The general Department of Planning notice is at [planning.nsw.gov.au Copyright-and-Disclaimer](https://www.planning.nsw.gov.au/Copyright-and-Disclaimer). It was not fetched.

**Council DCPs**
- Licensing is inconsistent across documents:
  - The Blacktown Growth Centre Precincts DCP (July 2018) is CC BY 4.0, subject also to "the requirements of the Department of Planning and Environment".
  - The Catherine Hill Bay (South) DCP 2012 (Lake Macquarie) allows reproduction only for "personal, in-house or non-commercial use", with all other rights reserved — [Lake Macquarie DCP PDF](https://lakemac.com.au/files/assets/public/v/1/hptrim/land-use-and-planning-planning-development-control-plans-dcp-development-control-plan-dcp-no-1-revision-10-catherine-hill-bay-development-control-plan/catherine-hill-bay-rose-group-land-development-control-plan/catherine-hill-bay-south-development-control-plan-july-2012.pdf).
- Council website terms are commonly non-commercial. Port Macquarie-Hastings allows reproduction for "personal, in-house or non-commercial use, without formal permission and without charge", subject to the Copyright Act 1968 — [PMHC copyright](https://www.pmhc.nsw.gov.au/System-Pages/Copyright-Disclaimer).
- Lithgow warns that DA plans and reports on its site are third-party copyright — [Lithgow copyright](https://www.lithgow.nsw.gov.au/Governance/Access-to-Information/Copyright).

**Crown copyright / 2025–26 reforms**
- The Copyright Amendment Bill 2025 was introduced on 5 November 2025. The Senate committee recommended passage on 19 December 2025. It passed as the **Copyright Amendment Act 2026** (sources say assent around 1 April 2026; in force 2 April 2026, Act No. 29 of 2026). Its headline change is Australia's first statutory **orphan works** scheme. The Crown copyright change is narrow: it only clarifies **duration (s 180)** — [Parliamentary Library Bills Digest No. 33, 2025-26](https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/bd/bd2526/26bd33); [Wikimedia Australia on passage](https://wikimedia.org.au/wiki/Wikimedia_Australia_welcomes_the_passage_of_the_Copyright_Amendment_Act_2026); [MinterEllison](https://www.minterellison.com/articles/orphan-works-remote-learning-copyright-amendment-bill-2025). The two assent dates come from secondary summaries and differ by a day.
- The RAIA submission says the Bill does **not** amend s 176. That section treats works made by consultants under Crown direction as Crown copyright — [RAIA submission, 28 Nov 2025](https://www.architecture.com.au/wp-content/uploads/Copyright-RAIA-28112025.pdf).
- Councils are not "the Crown" for Copyright Act ss 176–178. That is general background and was not verified in this session **[LAWYER]**. So DCP copyright sits with councils (or their consultants) under ordinary rules, whatever the Crown reform does.

**Database / compilation copyright (no sui generis right)**
- *Telstra v Phone Directories* [2010] FCAFC 149 applied *IceTV v Nine* [2009] HCA 14. The White and Yellow Pages were not original literary works. The highly automated compilation process lacked human authorship, the "mere collection of data" was not compilation, and the decision effectively displaced *Desktop Marketing* [2002] FCAFC 112's "sweat of the brow" approach. Special leave to the High Court was refused — [Federal Court judgment](https://www.judgments.fedcourt.gov.au/judgments/Judgments/fca/full/2010/2010fcafc0149); [Bright Law summary](https://www.brightlaw.com.au/telstra-loses-copyright-claim-over-white-pages-and-yellow-pages/); [IceTV (Wikipedia)](https://en.wikipedia.org/wiki/IceTV_Pty_Ltd_v_Nine_Network_Australia_Pty_Ltd).
- The Full Court noted the Act "does not presently deal explicitly with the impact of software on authorship" — [ipwars commentary](https://ipwars.com/still-no-copyright-in-telephone-directories-downunder/2010/12/15/15/55/47/1388/).

### Inferences
- **Republishing LEP/SEPP-derived provisions** (55k rows, with the share that comes from statewide instruments) is low-risk under CC BY 4.0, provided you carry attribution plus the "altered" credit and download date. Ship an `ATTRIBUTION.md` and per-row `source_url` / `retrieved_at` fields.
- **DCP-derived rows** fall into three tiers:
  - (a) Verbatim clause text from non-CC councils: highest risk. Councils that say "non-commercial only" have not licensed commercial republication. A CC BY-NC dataset release would still not cure "all other rights reserved" on derivatives **[LAWYER]**.
  - (b) Extracted numeric controls and structured facts (e.g. "front setback 6 m, zone R2, ref 3.2.1"): IceTV and Telstra suggest facts are not protected, and a short reference is unlikely to be a "substantial part". But clause wording can carry originality, so test this on a sample before release.
  - (c) Your own schema, classification, QA flags and the selection and arrangement: your own copyright, which you can licence as you choose.
- A pragmatic structure: publish (1) code, (2) the schema plus pipeline, (3) state-instrument data in full, (4) DCP data as *structured values + citation + link*, without long verbatim text. Councils already on CC BY can be included in full. Keep a per-council licence table in the dataset card.
- The project's own LLM extraction is automated. On Telstra reasoning, the *output* may itself attract little or no copyright in your favour. A licence on such data may be weak in enforcement terms but is still useful as a signal. This matters if the plan is to "protect" data with ODbL or NC terms.
- CC BY 4.0 on inputs does not require share-alike, so you can pick any outbound licence for derived data, as long as attribution flows through.

### Gaps
- Exact current text of legislation.nsw.gov.au/copyright and of any Planning Portal API terms (the session's network blocked the fetches). Check that the PCC/CDC API "Creative Commons Attribution" version is 4.0.
- A council-by-council licence census of the DCPs actually in the DB. This is needed before release and can be scripted from each council's copyright page.
- Whether NSW s 3.43 EP&A Act DCP publication obligations or the EP&A Regulation create any implied licence to reproduce (the ALRC's discussion of [implied licence](https://www.alrc.gov.au/publication/copyright-and-the-digital-economy-dp-79/14-government-use/use-under-an-implied-licence/) and [statutes requiring public access](https://www.alrc.gov.au/publication/copyright-and-the-digital-economy-alrc-report-122/15-government-use/statutes-requiring-public-access/) is relevant) **[LAWYER]**.
- The status of copyright in NSW Planning Portal "Online DCP" (ePlanning-hosted) content.

## 2. Precedents

### Takeaway
Australian and international precedents show that structured planning and legal data can be openly published. The UK publishes planning data under OGL v3 with open code. PlanningAlerts has scraped council DA listings at national scale for over a decade with no published legal dispute found. The Open Australian Legal Corpus redistributes NSW legislation under source-specific open licences. None of these settles DCP copyright.

### Cited findings
- **PlanningAlerts (OpenAustralia Foundation):** scrapers on morph.io collect council DA listings daily and convert them to machine-readable form. The scraper code is open source — [PlanningAlerts DAP "under the hood"](https://www.planningalerts.org.au/authorities/daps_wa/under_the_hood); [How to write a scraper](https://www.planningalerts.org.au/how_to_write_a_scraper); [morph.io planningalerts-scrapers](https://morph.io/planningalerts-scrapers).
- OAF reports collecting **198,020 DAs in FY2025-26**, up from 155,785 — [OAF 2025-26 year in review](https://oaf.org.au/2026/07/17/a-year-of-putting-democracy-in-more-hands-our-2025-26-in-review/).
- OAF licenses its *own* content under CC BY-NC-SA ("credit us, do not use it commercially, release… under the same licence") — [OAF licence](https://oaf.org.au/licence/).
- No OAF legal analysis or dispute about DA copyright was found.
- **UK Planning Data platform:** dataset pages say "Licensed under the Open Government Licence v.3.0", and the platform code is open source — [planning.data.gov.uk dataset page](https://www.planning.data.gov.uk/dataset/planning-application); [Digital Land quickstart](https://digital-land.github.io/quickstart/); [terms](https://planning.data.gov.uk/terms-and-conditions).
- **NYC zoning:** DCP metadata says the data "is freely available to all New York City agencies and the public". It also warns that the features "are not intended for determining zoning at the individual tax lot level". No explicit licence was found, and data.gov lists "License not specified" — [nyzd metadata](https://www.nyc.gov/assets/planning/download/pdf/data-maps/open-data/nyzd_metadata.pdf?r=1219); [catalog.data.gov Zoning Tax Lot DB](https://catalog.data.gov/dataset/nyc-zoning-tax-lot-database).
- **Open Australian Legal Corpus (Isaacus / Umar Butler):** it lists NSW Legislation as a source. Documents are distributed "under open source licences that, in most cases, allow for both non-commercial and commercial usage", with a per-source LICENCE.md — [HF dataset](https://huggingface.co/datasets/isaacus/open-australian-legal-corpus); [LICENCE.md](https://huggingface.co/datasets/umarbutler/open-australian-legal-corpus/blob/main/README.md).
- The creator tool README states "it is essential that you are authorised to scrape and use the sources' data" — [open-australian-legal-corpus-creator](https://github.com/isaacus-dev/open-australian-legal-corpus-creator). The full licence analysis could not be fetched.

### Inferences
- The OALC is the closest model for a Hugging Face dataset card. It uses a per-source licence table and a "you must be authorised" caveat, and it covers legislation rather than DCPs.
- The NYC disclaimer is a good template for liability language ("not intended for determining zoning at the individual lot level"). That fits the project's own liability-language rules.
- PlanningAlerts suggests councils tolerate the reuse of *factual DA metadata*. That is not evidence about reproducing DCP control text.

### Gaps
- OSM Australia licence waivers (the 2010s ODbL waivers from DCS/Spatial Services and the ABS) were not researched in this session (tool budget).
- The Open Up / National Zoning Atlas licence terms were not researched.
- The OALC licence text for NSW material is unverified because huggingface.co was blocked.

## 3. Licence choice: code and data

### Takeaway
For a solo developer who wants visibility, employment and the option to sell a hosted service: **Apache-2.0 or MIT for libraries, SDKs and scrapers; AGPL-3.0 (or FSL if source-available is acceptable) for the hosted compliance API/app; CC BY 4.0 for the data.** CC BY 4.0 matches the inbound government licences and is the default researchers and companies accept. ODbL's share-alike adds friction and little protection, given the weak copyright position of automated data.

### Cited findings
- Projects such as Unleash moved from Apache-2.0 to AGPLv3 specifically so hosted modifications can't "stay private indefinitely" — [Unleash blog](https://www.getunleash.io/blog/unleash-moving-to-agplv3). Elastic added an AGPL option after its 2021 move away from Apache-2.0 — [TechCrunch timeline](https://techcrunch.com/2024/12/15/open-source-companies-that-go-proprietary-a-timeline).
- The counter-view is that "AGPL license is a non-starter for most companies", so it reduces corporate adoption — [Open Core Ventures](https://opencoreventures.com/blog/agpl-license-is-a-non-starter-for-most-companies).
- The common split is a copyleft backend with permissive SDKs — [Amplify Partners](https://www.amplifypartners.com/blog-posts/how-to-pick-the-right-oss-license-for-your-startup).
- The **Functional Source License** is a "Fair Source" licence that converts to Apache-2.0 or MIT after two years. It is tuned for SaaS companies and is **not OSI-approved** — [fsl.software](https://fsl.software/); [Sentry announcement](https://blog.sentry.io/introducing-the-functional-source-license-freedom-without-free-riding).
- Armin Ronacher argues FSL is preferable to AGPL for businesses — [lucumr.pocoo.org](https://lucumr.pocoo.org/2024/9/23/fsl-agpl-open-source-businesses/).
- These are mainly vendor and opinion sources. No authoritative 2025–26 legal survey was found.

### Inferences
- **Employment value favours an OSI licence.** "Open source" on a CV is cleaner with MIT, Apache-2.0 or AGPL than with FSL or BSL. Apache-2.0 adds an express patent grant, which matters to larger employers.
- **Dual licensing** (AGPL plus a commercial licence) requires you to own all the copyright. That holds today for a solo developer, so add a CLA or DCO-plus-assignment before accepting outside PRs, or you lose the option.
- **Open-core split for this repo:**
  - Open: the extraction pipeline, QA tooling, schema, the state-instrument dataset, and the Planning Portal client.
  - Closed or hosted: the curated DCP corpus where licences are unclear, satellite products, the report UI, and the SLA'd API.
- LLM extraction prompts are your own copyright and can be released. They are often the most-starred part of AI-era repos. Releasing them does cut into a consulting moat.
- Choose **CC BY 4.0** for data rather than CC0. You need attribution to pass through the NSW CC BY chain in any case, and it credits you. Avoid NC licences on data: they block the employers and govtech buyers you want to impress.

### Gaps
- There is no Australian case law on AGPL enforcement.
- [choosealicense.com](https://choosealicense.com) and the OSI pages were not fetched this session. These are standard references for the report writer.

## 4. Pre-release hygiene

### Takeaway
The repo is **not release-ready as-is**. History contains full SQL database dumps and hundreds of CSV row backups, and the LICENSE names another author. Release from a **fresh repository with squashed or curated history** rather than trying to scrub 446 MB of history. Scan with gitleaks and trufflehog first, and rotate every credential that ever appeared.

### Cited findings (repo facts: local commands, run 2026-11-18)
- `head -3 LICENSE` gives `MIT License / Copyright (c) 2025 Cole Medin`. `git log --diff-filter=A -- LICENSE` shows it was added at eedc7d1 (2026-11-03), but the clone is shallow (`git rev-parse --is-shallow-repository` returns `true`, 53 commits visible), so the true origin is earlier.
- `git ls-files | grep -Ei 'backups/' | wc -l` returns **106** tracked files under `backups/`. These include `backups/nsw_planning_dump_20251001_065048.sql`, `emergency_backup_20250920_194031.sql` and `pre_phase1_migration_*.sql`.
- `git log --all --diff-filter=A --name-only --format= | grep -Ei '\.(sql|dump|csv|sqlite|db|parquet|geojson)$' | wc -l` returns **320** data files added in visible history. Many are `data/db_rollback_backups/*.csv`.
- `du -sh .git` returns **446M**.
- `.env.example` and `.claude_backup/.env.example` are tracked. Check that they hold no real values.
- **GitHub guidance:** use `git filter-repo` (the `--sensitive-data-removal` flag needs version ≥2.47). Rewriting changes SHAs and breaks signatures and closed-PR diffs. Cached PR views need GitHub Support to remove. Collaborators' clones are not cleaned. Removing a secret does not undo its exposure, so rotate — [GitHub Docs: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
- **Privacy (DA records):** NSW councils must publish DA information under the GIPA Act and Regulation. Personal information is subject to the s 13 public interest test — [IPC Information Access Guideline 3](https://www.ipc.nsw.gov.au/information-access-guideline-3).
  - In *DRP v Orange City Council* [2020] NSWCATAD 220, objectors' phone numbers and emails were held to be personal information, while opinions about a DA were not — [IPC case note](https://www.ipc.nsw.gov.au/node/1700).
  - Councils such as Randwick redact contact details from published submissions — [Randwick](https://www.randwick.nsw.gov.au/about-us/administration/access-to-information).

### Inferences
- **The "Cole Medin" MIT licence:**
  - MIT requires the copyright notice to be kept in copies of *the software it covers*. If the repo began from a template (the name matches the author of the public "context-engineering" Claude Code template; this is inference and not verified), then any template files still present remain © Cole Medin under MIT. You may relicense your own code, but you must keep his notice for his portions.
  - If none of his code remains, the notice is simply wrong. It currently tells the world that *Cole Medin* licensed the entire project, including your code and data, under MIT. That is incorrect attribution and an implied grant you didn't intend.
  - Fix: decide your licence(s), write `LICENSE` with your own name (or your business entity), and, if template remnants exist, add `THIRD_PARTY_NOTICES` containing the original MIT text. Note that anyone who already received the repo under the MIT notice may argue they have an MIT licence to that version. That only matters if the repo was ever public **[LAWYER if it was public]**.
- **Data dumps:** full production SQL dumps may contain user accounts, emails, customer reports, addresses searched, API keys stored in tables, and Supabase auth rows. These raise Privacy Act 1988 (Cth) issues if you are an APP entity, and reputational issues regardless. The small-business (<$3M turnover) exemption commonly applies to solo developers, but reforms are pending **[LAWYER]**. Do not publish any dump. Generate a fresh, purpose-built export (provisions + overlays only) from a query that is reviewed column by column.
- **Recommended procedure:**
  1. Run `gitleaks detect --log-opts="--all"` and `trufflehog git file://. --only-verified` on a *full* (unshallowed) clone.
  2. Rotate Supabase service keys, GEE credentials, R2 keys and LLM API keys regardless of the results.
  3. Create a new public repo from a clean tree (`git archive` → new init), or use `git filter-repo --path backups/ --path data/db_rollback_backups/ --invert-paths` on a copy.
  4. Keep the private repo as the source of truth.
  5. Review `CLAUDE.md`, `.claude/`, `~/.claude/plans` references and `memory/` for internal business notes, client names and pricing.
  6. Strip internal product names per `.claude/rules/blog-content.md` from public docs if those are IP you want to keep.
- If DA-derived records are in the DB (applicant names, objector details), exclude them from the dataset. Publish only factual planning controls.

### Gaps
- gitleaks and trufflehog official docs were not fetched (budget). Commands above are standard usage, not taken from a source.
- Whether the repo has ever been public, and whether any template files remain (a `git log --follow` on an unshallowed clone would show this).
- Privacy Act tranche-2 reform status as of Nov 2026 was not researched.

## 5. Employment value and getting attention

### Takeaway
There is little rigorous 2025–26 data showing GitHub portfolios get people hired. Qualitative research says hiring managers use open-source work as evidence of *initiative and real-world judgement*. A niche, working, domain-heavy project (NSW planning + LLM extraction + GIS + QA discipline) is the kind of evidence that stands out. Attention comes from a demo, a dataset people can use, and a write-up.

### Cited findings
- An Oct 2025 arXiv study (interviews with US hiring managers) found employers want hard-to-teach traits such as initiative, and showed commonalities in how they want these demonstrated through open-source contributions — [arXiv 2510.25180](https://arxiv.org/html/2510.25180v1).
- A blog summary of a Profy.dev survey of 60+ hiring managers reports **65%** would "definitely" review a portfolio when the candidate lacks experience and **93%** would "probably" look at it. I could not verify the original survey — [summary](https://soychristian.pages.dev/contents/developer-portfolio-guide).
- The widely repeated claim that a "GitHub survey found 70% of employers view OSS favourably" has **no primary source found**. Do not cite it.
- The O'Reilly/IBM survey (late 2020, 3,400 developers and managers) found open-source skills valued over proprietary ones. It is dated — [TechTarget](https://www.techtarget.com/searchapparchitecture/news/252496117/Survey-Open-source-skills-more-valued-than-proprietary-ones).
- Guidance repeated across recruiter blogs is quality over volume, with GitHub not the sole signal — [Underdog.io](https://underdog.io/blog/what-hiring-managers-look-for-on-github); [daily.dev](https://daily.dev/blog/open-source-contributions-matter-hiring/).

### Inferences
- For NSW govtech, proptech and legaltech employers and contracting buyers (councils, DPHI, consultancies), a public, documented pipeline with QA gates, test counts and a data-quality tracker is unusually credible evidence. The repo's rigour (4k+ tests, gate scripts) should be visible in the README.
- Launch package:
  - A README with a 30-second GIF and a live demo for one LGA.
  - A "how it works" diagram.
  - A Hugging Face dataset with a licence-table dataset card, modelled on the OALC.
  - A blog post ("Extracting 55k NSW planning controls with LLMs: what broke").
  - A Show HN post, plus posts to r/australia-tech, OAF, the Code for Australia / govhack communities and LinkedIn.
- Pair the release with an explicit "not legal or planning advice" disclaimer (cf. the NYC metadata wording) to protect liability and reputation.

### Gaps
- No data was found on Show HN success factors or Hugging Face dataset discovery (search returned nothing relevant).

## 6. Monetisation alongside open source

### Takeaway
For an Australian solo developer, realistic income comes from a **hosted API/app plus consulting**, with open source as the funnel. Grants are thin: NLnet's NGI Zero open calls are paused or EU-prioritised. Sponsorship (GitHub Sponsors, Open Collective) seldom pays meaningful amounts for niche domain tools. No sourced figures were found.

### Cited findings
- NLnet temporarily paused its open calls to review NGI Zero. It is accepting only NGI Taler (payments) and NGI Fediversity (hosting) proposals, with a deadline of 1 Aug 2026. The regular call reopens "after the summer of 2026", and the Commons Fund final call closed 1 June 2026 — [NLnet call news](https://nlnet.nl/news/2026/20260601-call.html); [NGI Zero stocktaking](https://nlnet.nl/news/2026/20260612-NGIZero-stocktaking.html).
- NLnet eligibility gives priority to EU and Horizon Europe-associated residents on equal proposals. Non-EU applicants must argue an EU dimension — [NLnet eligibility](https://nlnet.nl/core/eligibility/); [NLnet office hour](https://nlnet.nl/officehour/).
- AGPL plus a commercial licence for hosted use is a recognised open-core path — [Amplify Partners](https://www.amplifypartners.com/blog-posts/how-to-pick-the-right-oss-license-for-your-startup).

### Inferences
- **Hosted API:** sell rate-limited, SLA'd access to the curated, freshness-maintained dataset, plus spatial overlay lookups. The open data is a snapshot, and the value lies in currency, coverage and QA. This fits a CC BY data and AGPL server model.
- **Consulting:** councils, planning consultancies and proptech firms need DCP digitisation. The public repo serves as a capability statement.
- Australian funding options to investigate (not researched): NSW government innovation programs, CSIRO Kick-Start, R&D Tax Incentive (refundable offset for <$20M turnover entities), and the auDA Foundation. Also consider GovHack prizes.
- Set up GitHub Sponsors as low-effort optionality. Do not plan around it.

### Gaps
- GitHub Sponsors fee structure, Open Collective Australian fiscal host options, and Australian grant programs were not verified (the search returned nothing relevant, and the tool budget ran out).
- Sovereign Tech Fund (now Sovereign Tech Agency) eligibility for non-German projects was not researched.
