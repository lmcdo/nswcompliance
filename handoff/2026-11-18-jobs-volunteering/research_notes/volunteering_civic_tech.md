# Volunteer and Civic-Tech Opportunities in Australia (NSW focus) for a Solo NSW Planning-Compliance Developer — as of November 2026

> Method note (read first): research ran on 2026-11-18 through web search only. Direct page fetches failed because the session's network blocks these hosts: oaf.org.au, govhack.org, planningalerts.org.au, meetup.com, aurin.org.au and makeadifference.volunteering.nsw.gov.au. So most findings below come from search-result snippets, not full pages. Treat each one as "indicative, verify on the source page". Where a source is older than 2026 it is marked **[older]**.

## 1. OpenAustralia Foundation (PlanningAlerts, They Vote For You, Right To Know): status, contributor routes, NSW DA coverage and gaps

### Takeaway
OAF is active in 2026 and still volunteer- and donation-dependent. PlanningAlerts covers NSW councils, Sydney/Regional Planning Panels and NSW major projects through per-authority scrapers on morph.io. The documented way to contribute is writing or fixing scrapers. I found no evidence that PlanningAlerts serves DA outcomes or planning controls (LEP/DCP/SEPP), so this developer's work fills a gap OAF does not.

### Cited Findings
- OAF published a 2025-26 year-in-review on 17 July 2026. The visible snippet highlights a full rewrite of OpenAustralia.org.au; no PlanningAlerts-specific detail was visible — [OAF 2025-26 in review](https://oaf.org.au/2026/07/17/a-year-of-putting-democracy-in-more-hands-our-2025-26-in-review/)
- The PlanningAlerts sign-up page carries a banner asking for monthly supporters and warning the "library will close" without them. OAF services are funded entirely by donations, which are not currently tax deductible (search snippet) — [PlanningAlerts signup](https://www.planningalerts.org.au/alerts/signup); [OAF home](https://oaf.org.au/)
- PlanningAlerts was still adding authorities in 2026. One council page shows it was first added on 17 Jun 2026 (search snippet) — [PlanningAlerts / Cobar](https://www.planningalerts.org.au/authorities/cobar/applications)
- The NSW Sydney and Regional Planning Panels "under the hood" page describes a daily pipeline: a scraper collects data, which is validated, geocoded and then sent out as alerts. The latest import log seen was dated 27 July 2026 with 756 applications (search snippet) — [Under the hood: NSW planning panels](https://www.planningalerts.org.au/authorities/nsw_jrpp/under_the_hood)
- Other NSW authorities with "under the hood" pages include City of Sydney, North Sydney, Newcastle, Waverley, Shoalhaven, Port Macquarie-Hastings and the NSW DoP Major Project Assessments — [City of Sydney](https://www.planningalerts.org.au/authorities/sydney/under_the_hood); [NSW DoP](https://www.planningalerts.org.au/authorities/nsw_dop/under_the_hood)
- Scrapers live in the `planningalerts-scrapers` org on morph.io, with code on GitHub. The `nsw_planning_major_projects` scraper's most recent run had failed with a connection timeout (exit status 1). Listed contributors include mlandauer and benrfairless — [morph.io nsw_planning_major_projects](https://morph.io/planningalerts-scrapers/nsw_planning_major_projects); [morph.io planningalerts-scrapers](https://morph.io/planningalerts-scrapers)
- The PlanningAlerts FAQ invites people whose authority is missing to "help out by writing a web scraper". Pages suggest forking a broken scraper on GitHub to fix it, and pressing "Watch" on morph.io to get error emails — [PlanningAlerts FAQ](https://planningalerts.org.au/faq)
- OAF removed the long-disabled (since 2019) "write to councillors" feature from PlanningAlerts as code cleanup (post date not shown in snippet) — [OAF PlanningAlerts category](https://oaf.org.au/category/projects/planningalerts-org-au/)
- OAF blog post on "Yimbyism on PlanningAlerts": Sydney YIMBY members have encouraged DA submissions via PlanningAlerts. PlanningAlerts cannot confirm users are YIMBY members because it collects only name and email — [OAF: The increase of Yimbyism on Planning Alerts](https://oaf.org.au/?p=4442)
- OAF projects: PlanningAlerts, They Vote For You, OpenAustralia.org, morph.io, Right To Know — [civictech.guide listing](https://directory.civictech.guide/listing/open-australia-foundation)
- Tech stack: PlanningAlerts is a Ruby on Rails app (a public fork exists at github.com/dbaxa/planningalerts), and the scrapers run on morph.io. The Rails detail comes from my background knowledge plus the repo listing. It is not confirmed by a 2026 page — [GitHub fork](https://github.com/dbaxa/planningalerts)
- The official NSW Online DA Data API (DPHI, CC-BY) covers DAs lodged on the Planning Portal since 2019. Councils were mandated onto the portal from 1 July 2021, so earlier records may be missing. The API had 2026 release notes on 1 Jul, 31 Jul, 28 Aug and 25 Sep — [data.gov.au Online DA Data API](https://www.data.gov.au/data/dataset/nsw-online-da-data-api); [API release notes 25 Sep 2026](https://www.planningportal.nsw.gov.au/sites/default/files/documents/2026/NSW%20Planning%20Portal%20-%20API%20release%20notes_25%20September%202026.pdf)

### Inferences
- Even with a statewide official DA API, PlanningAlerts still runs mostly per-council scrapers for NSW. A contribution that consolidates NSW coverage onto the Online DA Data API could be high-leverage, and the developer already handles NSW Planning Portal data. This needs confirming with OAF maintainers first.
- PlanningAlerts reports lodgements. Its gaps relative to this developer's pipeline appear to be: (a) determination outcomes/conditions, (b) the controls that apply to a site (zoning, LEP/DCP clauses, overlays), and (c) CDC eligibility. These are natural "what applies here?" add-ons, but OAF's mission and capacity to accept them are unverified.
- OAF's donation-only funding and small core team suggest it is unlikely to be a paid employer. It is a reputation and portfolio venue.

### Gaps
- Could not read the 2025-26 review in full (host blocked). PlanningAlerts roadmap, any outcomes feature, and current contributor guidelines are unconfirmed.
- Did not confirm whether PlanningAlerts already ingests the NSW Online DA Data API under another scraper name.

## 2. Civic-tech communities and hackathons: Code for Australia, Code for Sydney, GovHack, Infoxchange, others

### Takeaway
Code for Sydney (monthly hack days in Haymarket) and GovHack (annual, usually late August, with an NSW digital stream) are the most concrete active venues. I could not confirm GovHack 2026 dates, NSW challenges or results. Code for Australia's fellowship places paid technologists in government, but I found no 2026 intake. Infoxchange is active in 2026 but oriented to NFP tech and data support.

### Cited Findings
- **Code for Sydney:** volunteer civic group of developers, designers and activists. It runs monthly hack days at Darling Square Library (Idea Space One), Haymarket, coordinates on Discord, and has about 398 Meetup members. City of Sydney lists a "Code for Sydney Hack Day: Surveillance Society" (date not visible) — [Meetup: Code for Sydney](https://www.meetup.com/codeforsydney); [City of Sydney What's On](https://whatson.cityofsydney.nsw.gov.au/events/code-for-sydney-hack-day-surveillance-society); [Luma monthly hack day](https://luma.com/r43venb5)
- **GovHack:** an annual open-government-data hackathon across Australia and New Zealand, founded in 2009 in Canberra. Teams have 46 hours to produce a project page, proof of concept and video. The 2025 event ran 29–31 August 2025, with national awards on 6 December 2025 **[older]** — [GovHack Wikipedia](https://en.wikipedia.org/wiki/GovHack); [data.vic GovHack 2025 winners](https://www.data.vic.gov.au/govhack-2025-winners-announced); [Finance: GovHack 2025](https://www.finance.gov.au/about-us/news/2025/celebrating-innovation-govhack-2025)
- The GovHack homepage shows "Get Ready for GovHack 2026". No 2026 dates, challenges or winners appeared in search results as of 18 Nov 2026 — [govhack.org](https://govhack.org)
- **GovHack NSW format:** a pre-event "connections" session to meet data owners, a statewide digital competition, and awards 4–6 weeks after the weekend. Contact is nsw@govhack.org — [GovHack NSW](https://govhack.org/locations/new-south-wales/); [Hackerspace NSW (Digital)](https://hackerspace.govhack.org/events/nsw_digital_new_south_wales)
- GovHack recruits volunteer organisers (Competition Lead, Operations Lead, Sponsorship and Partnership Leads). Volunteering NSW lists an "AI Automation Crew for GovHack" role (details not readable) — [GovHack Competition Lead](https://govhack.org/?p=1403); [Volunteering NSW listing](https://makeadifference.volunteering.nsw.gov.au/volunteering/234100/ai-automation-crew-for-govhack)
- GovHack 2023 NSW challenges included cost-of-living (winner "Habitasis", runner-up "(Gov) Affordability Planner", honourable mention "TenancyIQ") **[older]** — [Data.NSW GovHack 2023](https://www.data.nsw.gov.au/blog/govhack-2023)
- **Code for Australia:** a not-for-profit in the Code for All network. Its Fellowship places technologists, designers and organisers inside government agencies for up to a year on agreed challenges. It also runs an Academy for public servants and has worked with the NSW and QLD governments. No 2026 cohort call was found — [CfA Fellowship](https://cfa-website.vercel.app/fellowship/); [civictech.guide CfA](https://directory.civictech.guide/listing/code-for-australia)
- **Infoxchange:** held its Technology for Social Justice Conference in May 2026, addressed by Minister Andrew Leigh. Its Data Catalyst Network (consultative data support for NFPs) is funded by the Paul Ramsay and Minderoo Foundations — [Treasury: Leigh speech 6 May 2026](https://ministers.treasury.gov.au/ministers/andrew-leigh-2025/speeches/address-infoxchange-technology-social-justice-conference-2026); [Infoxchange Data Catalyst Network](https://www.infoxchange.org/au/tags/data-catalyst-network)

### Inferences
- Best fit for this developer: present a lightweight, sanitised slice of the work (for example a "what controls apply to this lot" demo on open data) at Code for Sydney, and enter or mentor at GovHack NSW, where housing and planning datasets are typical. Joining as a GovHack data mentor or organiser builds ties with data.nsw and DPHI data owners.
- A Code for Australia Fellowship is the clearest paid pathway in this cluster, but availability in 2026 is unconfirmed.

### Gaps
- GovHack 2026 dates, NSW challenges, prizes and results were not found. Either they are not indexed or were not visible; check govhack.org and the Hackerspace directly.
- No usable 2026 information was found for Hack for Good, DataKind/Data for Good Australia, Open Knowledge Australia, Digital Rights Watch volunteer calls, Catalysr (a migrant-entrepreneur accelerator, not a volunteer program), or Seek Volunteer tech listings. Their status is unverified, not confirmed inactive.

## 3. Housing and planning advocacy groups and legal centres with data/tool needs

### Takeaway
Sydney YIMBY / Abundant Housing Network Australia, Shelter NSW and the Tenants' Union are active in 2026 and engage on planning reform. Only the Tenants' Union has a documented data tool (Rent Tracker), and AHNA has publicly called for standardised planning data. I found no documented request from EDO, Justice Connect or residents' and heritage groups for planning-controls tooling.

### Cited Findings
- **Sydney YIMBY:** non-profit founded in 2023, chaired by Justin Simon, with 315 members as of June 2025. It advocates for planning and heritage-law reform — [Wikipedia: Sydney YIMBY](https://en.wikipedia.org/wiki/Sydney_YIMBY)
- **Abundant Housing Network Australia:** alliance of Greater Canberra, YIMBY Melbourne, Sydney YIMBY and Greater Brisbane. Its 2024 national urban policy submission calls for "standardising the methodologies, definitions, and data formats used across all jurisdictions" **[2024]** — [AHNA](https://abundanthousing.org.au/); [AHNA NUPC submission](https://infrastructure.gov.au/sites/default/files/documents/nupc-abundant-housing-network-australia.pdf)
- **Shelter NSW:** made a February 2026 submission on the draft Sydney Plan, saying the "new approach" to strategic planning has failed to meet community expectations — [Shelter NSW submission Feb 2026](https://shelternsw.org.au/wp-content/uploads/2026/02/Shelter-NSW_A-new-approach_-draft-Sydney-Plan_Submission_270226.pdf)
- **Tenants' Union of NSW:** runs a Rent Tracker research project to help tenants, researchers and journalists understand NSW rent movements, and is a partner of the UNSW Housing Analytics Lab — [Tenants' Union planning tag](https://tenants.org.au/tag/planning-and-development); [AURIN Housing Analytics Lab](https://aurin.org.au/1-million-in-funding-for-new-housing-analytics-lab/)
- **EDO (NSW):** community legal centre for public-interest environmental law. Search found no current data or tool volunteer program — [search result context](https://www.econetworkps.org/nsw-environmental-planning-laws-under-attack/)
- **Justice Connect:** its Pro Bono Portal matches legal matters to volunteer lawyers and is free to all NSW and Victorian CLCs. More than 160 firms use it. NSW funded its AI legal-triage model, to be free to NSW NFPs. Its volunteering is lawyer-centric; there is no planning-tech volunteer stream — [Justice Connect Pro Bono Portal](https://justiceconnect.org.au/?p=12172); [DCJ NSW release 2021](https://dcj.nsw.gov.au/documents/news-and-media/media-releases-archive/2021/innovative-solutions-for-fairer-justice.pdf) **[older]**

### Inferences
- Plausible pro-bono offers with natural demand: give YIMBY/AHNA groups data on which lots fall in TOD and low-mid-rise housing areas versus heritage and flood constraints, or council-level DA outcome statistics, to support their submissions. Give Shelter NSW or the Tenants' Union analysis for their submissions. These are inferred fits, not documented requests.
- Liability caution: a legal centre (EDO, Justice Connect clients) relying on automated compliance screening raises professional-advice risk. Frame any offer as data and research support, not advice.

### Gaps
- No published "data volunteer wanted" call was found for any of these groups. Arts Law, Landcare and heritage or residents' groups were not researched in depth because of tool limits.

## 4. Universities and research infrastructure (UNSW City Futures, UTS ISF, USyd, AURIN)

### Takeaway
UNSW City Futures is the most relevant hub. It runs the AURIN/ARDC-funded Housing Analytics Lab (a planned planning-approvals dashboard), a GenAI planning assistant project (Urban Copilot) with Archistar and PEXA, and its spinout MapAI. All of these overlap directly with this developer's work, making it the strongest collaboration or employment target. No independent-contributor program was found.

### Cited Findings
- Housing Analytics Lab: a $1M two-year NSW Chief Scientist grant, led by City Futures on behalf of AURIN and the ARDC. It was opened in May 2025 by Premier Minns and is intended to host tools including a map dashboard of historic and live planning approvals across Australia. Partners include the Commonwealth Bank and the Tenants' Union of NSW — [AURIN announcement](https://aurin.org.au/1-million-in-funding-for-new-housing-analytics-lab/); [UNSW newsroom May 2025](https://www.unsw.edu.au/content/unsw-sites/au/en/newsroom/news/2025/05/world-leading-unsw-analytics-lab-opens-to-tackle-housing-crisis.html)
- Urban Copilot: a $6.5M CRC-P GenAI digital assistant for planners, developers and government, with City Futures as lead research partner alongside Archistar, PEXA Group and the City Futures startup MapAI — [UNSW City Futures Analytics](https://www.unsw.edu.au/research/city-futures/our-research/urban-analytics); [Build Australia: MapAI](https://www.buildaustralia.com.au/business_insight/new-ai-platform-simplifies-complex-spatial-analysis/)
- MapAI is an AI geospatial platform from City Futures, backed by UNSW and FrontierSI. Search results describe a launch around November 2026, though source dates are inconsistent — [Build Australia](https://www.buildaustralia.com.au/business_insight/new-ai-platform-simplifies-complex-spatial-analysis/)
- Value Australia is a property valuation tool built by UNSW, FrontierSI and PEXA Insights — [UNSW case study](https://www.unsw.edu.au/arts-design-architecture/our-research/research-impact/case-studies/new-land-valuation-tool-uses-big-data-to-inform-urban-planning-development-and-investment)

### Inferences
- The Housing Analytics Lab's planning-approvals dashboard and Urban Copilot (an LLM planning assistant) overlap closely with this developer's DA-outcome analysis and LLM extraction with QA. Approaching City Futures as a data partner, research assistant or contractor is the clearest route from unpaid contribution to paid work. MapAI and Archistar are related commercial employers.
- Contributing a cleaned dataset, such as structured DCP controls with citations, through AURIN or the Lab could give an independent formal research visibility. AURIN's contribution process for independents was not verified.

### Gaps
- UTS Institute for Sustainable Futures and the University of Sydney urbanism groups were not researched (tool budget). AURIN's data-contribution pathway for non-affiliated people was not confirmed (host blocked).

## 5. Government open data and feedback programs (data.nsw, Planning Portal API, Digital Twin, DPHI)

### Takeaway
DPHI actively maintains the Online DA Data API (several 2026 release notes) and publishes planning data and housing-supply dashboards. I found no formal "API developer community" or volunteer program. Engagement is through public consultations and data-quality feedback.

### Cited Findings
- Online DA Data API: CC-BY, covers DAs since 2019, mandatory for councils from 1 July 2021. Release notes were issued 1 Jul, 31 Jul, 28 Aug and 25 Sep 2026. The September notes add consent surrender through the portal — [data.nsw Online DA Data API](https://www.data.nsw.gov.au/data/dataset/groups/online-da-data-api); [Sep 2026 release notes](https://www.planningportal.nsw.gov.au/sites/default/files/documents/2026/NSW%20Planning%20Portal%20-%20API%20release%20notes_25%20September%202026.pdf)
- A third-party listing documents an undocumented DA Application Tracker endpoint and states it is not affiliated with DPHI — [Apify nsw-da-leads](https://apify.com/spider355/nsw-da-leads.md)
- DPHI publishes a Housing Supply Dashboard and a data and resources hub — [Housing supply dashboard](https://www.planning.nsw.gov.au/data-and-insights/housing-supply/housing-supply-dashboard); [DPHI data and resources](https://www2.planning.nsw.gov.au/data-and-resources)
- NSW Digital case studies on ePlanning and the Digital Housing Pipeline — [NSW Digital Housing Pipeline](https://www.digital.nsw.gov.au/strategy/case-studies/nsw-digital-housing-pipeline)

### Inferences
- Concrete avenues: report data-quality defects found by the pipeline (for example missing pre-2021 DAs or inconsistent outcome fields) to DPHI through the dataset contact; make evidence-based submissions to DPHI consultations on housing reforms using the overlay and DA data; and enter GovHack NSW challenges sponsored by DPHI or DCS.

### Gaps
- No current NSW Spatial Digital Twin community or contribution program was found. Specific open DPHI consultations as of November 2026 were not enumerated.

## 6. Evidence that civic-tech volunteering in Australia leads to jobs, contracts or funding

### Takeaway
The evidence is thin and mostly indirect. The best documented path is volunteer to leadership inside OAF (Henare Degan). Code for Australia fellowships are paid placements born of the civic-tech movement, and there is one 2018 GovHack win tied to a UTS startup program. I found no well-sourced case of a GovHack project becoming a funded company or government contract.

### Cited Findings
- OAF was founded in 2009 by Matthew Landauer and Katherine Szuminska. An OAF post describes the founders plus "an early volunteer, now board member, Henare Degan" doing around 90–95% of the work — [Wikipedia: OAF](https://en.wikipedia.org/wiki/OpenAustralia_Foundation); [OAF about](https://www.oaf.org.au/about/); [mySociety tag](https://www.mysociety.org/tag/openaustralia/)
- Code for Australia Fellows are placed inside agencies for up to a year (a paid engagement). Partners Victoria Legal Aid and Moreton Bay Regional Council reported capacity-building benefits — [CfA Fellowship](https://cfa-website.vercel.app/fellowship/)
- "Startup kickstarter wins GovHack" (UTS, 31 Oct 2018), outcome details not visible **[older]** — [UTS](https://www.uts.edu.au/partners-and-community/initiatives/entrepreneurship/news/startup-kickstarter-wins-govhack)
- A GovHack 2024 project ("Project Haven") continued as a personal project afterwards, with no funding or contract reported — [DEV Community](https://dev.to/ujja/from-govhack-win-to-something-that-actually-matters-2mmi)
- Government money flows to GovHack as sponsorship (for example ABS paid $16,500 in 2021), not to alumni projects — [GovMarket contract](https://govmarket.com.au/contract/sponsorship-of-govhack-australia-ltd-by-australian-bureau-of-statistics-515043) **[older]**
- Philanthropic data-for-good funding exists in 2026 through the Infoxchange Data Catalyst Network (Paul Ramsay and Minderoo) — [Infoxchange](https://www.infoxchange.org/au/tags/data-catalyst-network)

### Inferences
- For this developer, the realistic conversion paths are: (1) contribution to visibility with UNSW City Futures / MapAI / Archistar-type PropTech, leading to contract or employment; (2) civic-tech presence leading to a Code for Australia or government digital role; (3) open data contributions supporting grant applications (for example NSW Chief Scientist or philanthropic data grants). None of these is documented as a repeatable pattern; they are reasoned from the cited ecosystem.

### Gaps
- No systematic study or survey of Australian civic-tech volunteer career outcomes was found. LinkedIn case studies were not accessible.
