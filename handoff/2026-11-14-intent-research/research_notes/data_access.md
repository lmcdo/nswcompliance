# Legitimate Access to Discussion & Social Data for Lead / Pain-Point Discovery (as of Nov 2026)

Research date: 2026-11-14. User context: solo developer, NSW Australia.
Method note: 15 search/fetch calls. Reddit's own help centre (support.reddithelp.com) could not be fetched from this session (host blocked by network allowlist), so Reddit figures come from third-party pages and are flagged. Items marked **[background, not re-verified]** come from prior knowledge with a well-known primary URL but were not re-fetched this session — the report writer should treat them as lower confidence. This is not legal advice.

## Reddit: Data API terms, pricing, commercial rules, 2026 status

### Takeaway
Reddit is now the most locked-down major discussion source: API access is approval-gated under the Responsible Builder Policy (self-service app registration closed late 2025), the free tier (100 QPM OAuth) is non-commercial only, commercial pricing is unpublished/contract-only, and Reddit is actively suing indirect scrapers (including via Google SERPs). A commercial lead-discovery tool should assume it needs a Reddit agreement or must avoid Reddit data.

### Cited Findings
- Free tier: 100 queries/minute per OAuth client, 10 QPM without OAuth; described as non-commercial use only — [Data365](https://data365.co/blog/reddit-api-pricing); [Techloy](https://www.techloy.com/reddit-api-pricing-in-2026-complete-guide-for-developers-and-businesses/) (both third-party; Data365 sells a competing API).
- Responsible Builder Policy: developers must request access and receive explicit approval before accessing any Reddit data via the API; instant self-service OAuth app registration closed in late 2025 — [xpoz.ai](https://www.xpoz.ai/blog/guides/reddit-api-pricing-tiers-and-alternatives/); [Octolens](https://octolens.com/blog/reddit-api-pricing) (third-party summaries; official page support.reddithelp.com not reachable this session).
- Commercial pricing is not published; commonly cited figures are ~$0.24 per 1,000 calls (the 2023 announcement figure) and a reported ~$12,000/yr minimum — both unverified third-party figures — [apiserpent](https://www.apiserpent.com/blog/best-reddit-api-providers-2026); [redditapis.com](https://www.redditapis.com/blogs/reddit-api-pricing-2026).
- Several 2026 sources claim unauthenticated `.json` endpoints began returning 403 in May 2026 — [socialcrawl.dev](https://www.socialcrawl.dev/blog/reddit-data-api-2026); [Medium](https://medium.com/@alex_79882/reddits-api-is-officially-dead-in-2026-here-s-what-i-use-instead-f88ee5b809c8) (low-quality / vendor sources; unconfirmed).
- One source claims the free tier ends March 2027 and new access requests closed Oct 31 (2026) — could NOT be corroborated; treat as unverified rumour — [search results aggregate; see bigideasdb](https://bigideasdb.com/reddit-api-pricing).
- Reddit data licensing: Reddit licenses data to AI companies (Google, OpenAI) and stated Perplexity's suit framing as "a show of force in Reddit's training data negotiations with Google and OpenAI" (Perplexity's characterisation) — [Search Engine Land](https://searchengineland.com/reddit-sues-perplexity-serpapi-scraping-google-463681).
- Oct 2025: Reddit sued SerpApi, Oxylabs, AWMProxy and Perplexity in SDNY, alleging they scraped Reddit content indirectly from Google search results; Reddit planted content visible only to Google's crawler and says it surfaced in Perplexity within hours — [Search Engine Land](https://searchengineland.com/reddit-sues-perplexity-serpapi-scraping-google-463681); [eWeek](https://www.eweek.com/news/reddit-sues-perplexity/).
- Reported July 31, 2026: Judge Engelmayer (SDNY) largely denied SerpApi's motion to dismiss, finding a plausibly pleaded conspiracy with Perplexity — single low-quality source, unconfirmed — [KuCoin news flash](https://www.kucoin.com/news/flash/reddit-lawsuit-against-serpapi-survives-dismissal-motion).
- What compliant third-party tools do: social-listening vendors (e.g. Octolens, which publishes on Reddit API pricing) market Reddit monitoring; some "Reddit API alternative" vendors resell scraped data — [Octolens](https://octolens.com/blog/reddit-api-pricing); [apiserpent](https://www.apiserpent.com/blog/best-reddit-api-providers-2026). No source this session confirmed which specific vendors hold a formal Reddit commercial licence.

### Inferences
- Using SERP APIs to harvest Reddit content is NOT a safe workaround: it is precisely the conduct Reddit is litigating.
- Pragmatic legitimate routes for a solo dev: (a) apply under the Responsible Builder Policy and describe the use honestly; (b) manual/human reading and participation in relevant subreddits; (c) use a vendor that can show a Reddit agreement in writing; (d) Reddit Ads (interest/community targeting) to reach the same audience without data extraction.
- Reselling or storing Reddit content in a commercial product without an agreement is the highest-risk use.

### Gaps
- Official current text of Responsible Builder Policy and Data API Terms (host blocked this session).
- Whether Reddit still offers any self-serve commercial tier in late 2026; actual quote levels.
- Independent confirmation of the July 2026 SerpApi ruling and the "free tier ends March 2027" claim.

## X/Twitter API tiers & pricing; Grok/xAI access to X data

### Takeaway
X moved to pay-per-use as default (Feb 6, 2026), retired the free tier for new developers and auto-migrated Basic subscribers from June 1, 2026. Reads cost about $0.005/post. xAI's API X Search tool is now billed per item ($5/1k posts, $10/1k profiles, plus tokens) since Sept 21, 2026 — a comparable, often more convenient path to X data.

### Cited Findings
- Pay-per-use became default on Feb 6, 2026; free tier closed to new developers; from June 1, 2026 remaining Basic ($200/mo) subscribers auto-migrated to pay-per-use — [Open Terms Archive memo](https://opentermsarchive.org/en/memos/x-replaces-its-dollar200-entry-level-api-plan-with-a-pay-per-use-model/); [Gigazine](https://gigazine.net/gsc_news/en/20260209-x-api-pay-per-use).
- Rates reported: ~$0.005 per post read, $0.015 per post created, $0.20 per created post containing a link; one source lists user lookups at $0.01 — [postproxy.dev](https://postproxy.dev/blog/x-api-pricing-2026); [opentweet.io](https://opentweet.io/x-api-pricing) (third-party; official docs.x.com not fetched).
- Monthly read cap reported as 2M or 3M posts per billing cycle — sources conflict — [bundle.social](https://bundle.social/blog/x-api-pricing-2026-costs-limits); [1322.io](https://1322.io/blog/twitter-api-pricing).
- Possible one-time credits of up to $70 for new paying accounts (single source) — [opentweet.io](https://opentweet.io/how-to/x-api-pay-per-use-explained).
- xAI X Search tool: billed per item fetched — every post returned (incl. parent and quoted posts) counts; $5 per 1k posts and $10 per 1k user profiles, on top of token costs; US regional endpoint 1.1x token rates — [xAI docs: pricing](https://docs.x.ai/developers/pricing); [xAI docs: X Search tool](https://docs.x.ai/developers/tools/x-search.md).
- Older guides list $5 per 1,000 calls; the switch to per-item billing took effect Sept 21, 2026 — [RuntimeWire](https://runtimewire.com/article/xai-is-changing-the-economics-of-x-search-runtimewire-was-built-for-a-narrower-r).

### Inferences
- At $0.005/post, 100k posts/month of keyword monitoring costs ~$500 via the X API; via xAI X Search ~$500 plus tokens. Budget scales linearly; tight keyword filters matter.
- Both are first-party sanctioned routes; scraping X is unnecessary for a solo dev and contrary to X ToS.

### Gaps
- Official docs.x.com pricing table not fetched; confirm read cap and Enterprise availability.
- X Developer Agreement restrictions relevant to lead gen (e.g. off-platform matching, storage limits) not reviewed this session.

## LinkedIn: API limits, Sales Navigator, hiQ outcome, enforcement, ToS

### Takeaway
LinkedIn offers no general-purpose read API for profiles/posts to ordinary developers; Sales Navigator is the sanctioned lead tool. hiQ ultimately lost (2022) on breach of contract, and LinkedIn's 2025 suit forced Proxycurl (~$10M revenue) to shut on July 4, 2025. Scraping or automating LinkedIn is the highest-enforcement-risk route of any platform here.

### Cited Findings
- LinkedIn filed a federal suit against Proxycurl and its founder in January 2025 (announced Jan 24, 2025 by LinkedIn's VP Legal), alleging fake accounts and mass scraping of member profiles — [Social Media Today](https://www.socialmediatoday.com/news/linkedin-wins-legal-case-data-scrapers-proxycurl/756101/).
- Proxycurl shut down July 4, 2025; CEO Steven Goh said fighting was not viable because legal fees are unrecoverable under the American Rule even if they won; ~US$10M revenue business — [Nubela "Goodbye Proxycurl"](https://nubela.co/blog/goodbye-proxycurl/); [StartupHub](https://www.startuphub.ai/news/the-1-linkedin-scraping-startup-proxycurl-shuts-down).
- LinkedIn's suit against another scraper, ProAPIs, was also heading for early resolution; LinkedIn has filed other suits against scrapers — [Bloomberg Law](https://news.bloomberglaw.com/artificial-intelligence/linkedins-war-against-bot-scrapers-ramps-up-as-ai-gets-smarter).
- hiQ v. LinkedIn outcome: after the Ninth Circuit's CFAA rulings (2019, reaffirmed 2022 post-Van Buren) that scraping public pages likely isn't "without authorization", the district court in Nov 2022 found hiQ breached LinkedIn's User Agreement (scraping and fake "turker" accounts), and the parties settled in Dec 2022 with hiQ agreeing to a permanent injunction and to destroy scraped data — **[background, not re-verified]** — [Ninth Circuit 2022 opinion](https://cdn.ca9.uscourts.gov/datastore/opinions/2022/04/18/17-16783.pdf).
- Sales Navigator / LinkedIn API: no source fetched this session. **[background, not re-verified]** LinkedIn's APIs are partner-programme gated (Marketing, Talent, Sales Navigator Application Platform, Community Management); the open self-serve tier is essentially Sign In with LinkedIn + Share — [LinkedIn developer docs](https://learn.microsoft.com/en-us/linkedin/).

### Inferences
- Main lesson of hiQ + Proxycurl: CFAA wins on "public data" do not protect against contract (ToS) claims, fake-account claims, or the cost of litigation. For a solo dev, even a defensible position is unaffordable.
- Browser-extension automation tools that act in a user's logged-in session also breach the User Agreement and risk account restriction.
- Legitimate routes: Sales Navigator (paid seat), LinkedIn ads targeting, manual posting/engagement, and consented data from people who opt in.

### Gaps
- Current Sales Navigator pricing (Core/Advanced) in AUD for 2026 — not retrieved.
- Full list of LinkedIn's 2025–2026 lawsuits against automation tools.

## Facebook/Meta: Groups API, CrowdTangle, Content Library, Meta v. Bright Data, routes

### Takeaway
There is no API route to Facebook Group content for commercial developers: the Groups API was removed (effective Apr 22, 2024), CrowdTangle shut in Aug 2024, and the Meta Content Library is for academic/non-profit researchers only via a Meta-controlled environment. Meta v. Bright Data (Jan 2024) only held that Meta's terms don't bar logged-out scraping of public data by a non-user; logged-in scraping (which is where Group content lives) remains clearly prohibited.

### Cited Findings
- Graph API v19.0 released Jan 23, 2024; Groups API changes apply to all versions from April 22, 2024; publishing to groups and member information access removed; group admins can no longer install apps on groups — [Meta Graph API v19.0 changelog](https://developers.facebook.com/docs/graph-api/changelog/version19.0/); [Make community notice](https://community.make.com/t/due-to-the-deprecation-of-the-facebook-groups-api-we-make-will-be-discontinuing-our-facebook-groups-app/32624.md).
- CrowdTangle shutdown announced March 2024, closed August 14, 2024 — [NPR via Texas Public Radio](https://www.tpr.org/2024-08-14/meta-shutters-tool-used-to-fight-disinformation-despite-outcry).
- Meta Content Library access is restricted to academic and non-profit researchers, excluding most news organisations; CrowdTangle had been open to anyone — [Las Vegas Sun/AP](https://lasvegassun.com/news/2024/aug/14/meta-kills-off-misinformation-tracking-tool-crowdt/); [CJR](https://www.cjr.org/?p=101803).
- MCL API covers public FB/IG content incl. public Pages, groups, events, and is accessible only in a Meta-provided/approved virtual environment — no local download — [Social Media Lab](https://socialmedialab.ca/web/?p=22554).
- Several hundred researchers had MCL access vs tens of thousands for CrowdTangle (2024 figures) — [Engadget](https://www.engadget.com/big-tech/meta-killed-crowdtangle-an-invaluable-research-tool-because-what-it-showed-was-inconvenient-121700584.html).
- Meta v. Bright Data (N.D. Cal., Judge Edward Chen, Jan 23, 2024): summary judgment for Bright Data; Facebook/Instagram terms read as governing logged-in use only, so they bar logged-in scraping but not logged-off scraping; insufficient evidence Bright Data scraped while logged in or reached non-public data; even if terms covered logged-out scraping, Meta could not bind Bright Data after it closed its accounts; survival clause rejected — [Farella Braun + Martel](https://www.fbm.com/business-litigation/publications/major-decision-affects-law-of-scraping-and-online-data-collection-meta-platforms-v-bright-data/); [Eric Goldman blog](https://blog.ericgoldman.org/?p=26009).
- Meta dropped the case and waived appeal; ruling is a non-binding district court decision; site owners may respond by rewriting terms — [MediaPost](https://www.mediapost.com/publications/article/393996/meta-abandons-lawsuit-against-bright-data-over-scr.html); [Lowenstein Sandler](https://www.lowenstein.com/news-insights/publications/client-alerts/meta-v-bright-data-ruling-has-important-implications-for-webscraping-activities-by-investment-advisers-im).

### Inferences
- What Bright Data did NOT decide: privacy-law liability (US or Australian), CFAA, copyright, or anything about logged-in/private-group data; also it binds no other court. Australian Privacy Act exposure is unaffected (see AU section).
- Most valuable FB pain-point data (Groups) requires login and often membership acceptance → scraping it is a clear ToS breach and also likely an "unfair means" collection issue under APP 3.5.
- Legitimate routes: join groups as a genuine member and read/participate manually under each group's rules; partner with group admins (sponsorships, admin-run surveys, opt-in lead forms); run your own group/Page; Meta Ads (interest + Lead Ads, which collect consented contact data); Graph API for Pages you manage.

### Gaps
- Whether MCL eligibility expanded in 2025–2026 (sources mostly 2024; DSA Art. 40 researcher access in EU may have broadened it).
- Meta's post-2024 terms revisions targeting logged-out scraping.

## Other sources (HN, Stack Exchange, Discourse, Product Hunt, YouTube, Quora, Whirlpool, Google search APIs, Bluesky, Threads, Telegram/Discord)

### Takeaway
The cleanest open sources are Hacker News (free official API + Algolia search), Bluesky (open firehose/Jetstream), Stack Exchange API (keyed, with AI-training limits) and many Discourse forums (built-in JSON API, but each forum's own terms govern). Google's general web search API is closing (Custom Search JSON API closed to new customers, shuts Jan 1, 2027) and Bing Search APIs were retired Aug 2025, pushing developers to Brave/Exa/Tavily/SerpAPI-type providers.

### Cited Findings
- Stack Exchange (July 2024): data dump moved behind login; downloaders agree not to use it to train LLMs (earlier draft said non-commercial); critics say this conflicts with CC BY-SA — [DevClass](https://www.devclass.com/development/2024/07/30/stack-exchange-restricts-access-to-dump-of-user-contributed-data-critics-complain-this-contradicts-license/1625192); [heise](https://heise.de/-9823083).
- Stack Overflow's "community data protection" policy directs commercial/AI users to paid data programmes — [Stack Overflow blog, Sep 2024](https://stackoverflow.blog/2024/09/30/ongoing-community-data-protection/?cb=1).
- Google Custom Search JSON API closed to new customers (reported Jan 20, 2026; some sources say 2025) and shuts Jan 1, 2027; replacement Vertex AI Search limited to up to 50 domains — [Apify blog](https://blog.apify.com/google-custom-search-api-alternative/); [Brave](https://brave.com/learn/google-api-shutdown/); [Firecrawl blog](https://www.firecrawl.dev/blog/google-search-json-api-alternative).
- Bing Search APIs retired Aug 11, 2025 — [Brave](https://brave.com/learn/google-api-shutdown/) (single source in this session).
- Hacker News: official Firebase API (free, no key) and Algolia HN Search API — **[background, not re-verified]** — [HackerNews/API GitHub](https://github.com/HackerNews/API); [hn.algolia.com/api](https://hn.algolia.com/api).
- Bluesky: AT Protocol firehose and Jetstream (JSON stream) are openly accessible without auth; content is public by design — **[background, not re-verified]** — [Bluesky docs](https://docs.bsky.app/docs/advanced-guides/firehose).
- Threads: Meta's Threads API (launched 2024) supports publishing, managing own content, and keyword search of public posts with rate limits — **[background, not re-verified]** — [Threads API docs](https://developers.facebook.com/docs/threads).
- YouTube Data API v3: comments readable via commentThreads endpoint, free within a default 10,000 units/day quota — **[background, not re-verified]** — [YouTube quota docs](https://developers.google.com/youtube/v3/determine_quota_cost).
- Product Hunt: public GraphQL API v2, with terms historically restricting commercial use without permission — **[background, not re-verified]** — [Product Hunt API docs](https://api.producthunt.com/v2/docs).

### Inferences
- Discourse forums expose `.json` endpoints by default, but each forum's ToS/robots governs; ask the admin — many will grant permission or a key.
- Quora: no public API; ToS prohibits scraping → manual reading only.
- Whirlpool (Australian forum) and similar AU communities (e.g. OzBargain, Productreview): no public APIs known; treat as manual-read / ask-the-operator. Whirlpool's terms should be checked directly.
- Telegram: public channels can be read via Telegram's official API with a user/bot account; Discord: bots may only read servers they are invited to, and Discord's developer policy restricts data mining — **[background, not re-verified]**; join communities openly and get admin consent.
- For an Australian niche (e.g. NSW planning/property), HN/Bluesky/Stack Exchange are likely low-yield; Facebook Groups, Whirlpool, Reddit AU subs and council/industry forums are higher-yield but the least API-accessible.

### Gaps
- No session sources fetched for HN, Bluesky, Threads, YouTube, Product Hunt, Quora, Whirlpool, Telegram, Discord terms — all background knowledge, need verification.

## Data providers / scraping infrastructure: pricing, use, compliance posture

### Takeaway
Search/extraction APIs (Brave, Exa, Tavily, Firecrawl, SerpAPI, Perplexity Sonar) are cheap ($1–$25 per 1k requests) and good for discovering public discussion pages; scraping-infrastructure vendors (Bright Data, Oxylabs, Apify, ScrapingBee) shift legal risk to the customer — and two of them (SerpApi, Oxylabs) are defendants in Reddit's suit. Using a vendor does not launder ToS or privacy-law exposure.

### Cited Findings
- Brave Search API: ~$5 per 1,000 requests, $5 free credit monthly (card required); independent index — [apiserpent comparison](https://apiserpent.com/blog/best-web-search-api-ai-agents-rag); [beri.net](https://www.beri.net/article/tavily-vs-exa-vs-brave-vs-perplexity-search-api-agent-cost-2026).
- Tavily: credit-based (basic search 1 credit, advanced 2); effective cost estimates ~$8 to ~$24 per 1k depending on depth; down to $0.005/credit at volume — [codenote](https://codenote.pages.dev/en/posts/tavily-alternatives-cost-comparison-search-extract-api/); [beri.net](https://www.beri.net/article/tavily-vs-exa-vs-brave-vs-perplexity-search-api-agent-cost-2026).
- Exa: pay-as-you-go; ~$7/1k search with contents, ~$1/1k contents only in one source vs much higher with highlights in another — [costbench](https://costbench.com/software/web-scraping/exa/); [beri.net](https://www.beri.net/article/tavily-vs-exa-vs-brave-vs-perplexity-search-api-agent-cost-2026).
- Firecrawl: subscription + credits, free tier to a few hundred USD/month; Scale ≈ $600 (~$0.60/1k credits) — [costbench Firecrawl vs Exa](https://www.costbench.com/compare/exa-vs-firecrawl/).
- Reddit is suing SerpApi, Oxylabs and AWMProxy (proxy/SERP providers) plus Perplexity (Oct 2025) — [Search Engine Land](https://searchengineland.com/reddit-sues-perplexity-serpapi-scraping-google-463681).
- Bright Data won Meta v. Bright Data (logged-out public data) and markets itself as collecting only public data — [PR Newswire (Bright Data release)](https://prnewswire.com/news-releases/court-rules-in-favor-of-bright-data-in-meta-v-bright-data-case-reaffirming-the-right-to-collect-public-web-data-302043730.html); [Bright Data blog](https://brightdata.com/blog/web-data/google-search-api).
- Reported: Google's DMCA suit against SerpApi dismissed July 20, 2026 — single unconfirmed source — [KuCoin news flash](https://www.kucoin.com/news/flash/reddit-lawsuit-against-serpapi-survives-dismissal-motion).

### Inferences
- Best fit for a solo dev: a search API (Brave/Exa/Tavily) to find public threads, then read the source via its official API where one exists (HN, Stack Exchange, YouTube, Bluesky) — rather than bulk-scraping platforms.
- Apify: marketplace of community "actors" (many are platform scrapers); compliance is on the user. Common Crawl: free, monthly open web archive, useful for forum discovery but lags and excludes login-walled content; its terms leave publishers' rights intact. Perplexity Sonar: search-grounded LLM API. **[background, not re-verified; prices not retrieved]**

### Gaps
- Current pricing for SerpAPI, Oxylabs, ScrapingBee, Bright Data, Apify, Perplexity Sonar not retrieved this session.

## Law: Australia (Privacy Act, tort, Spam Act, OAIC), US CFAA, EU GDPR

### Takeaway
For an NSW-based developer, the Australian Privacy Act is the main legal exposure, not ToS: scraped personal information (names, handles, posts linked to people) is still "personal information", OAIC has made determinations against scrapers (Clearview) and says scraping may be a covert/unfair means of collection; a statutory privacy tort has applied since 10 June 2025; and the Spam Act requires consent (express preferred) for any commercial email/SMS outreach — scraped contacts give none.

### Cited Findings
- Statutory tort for serious invasions of privacy commenced 10 June 2025; OAIC does not administer it; limitation: 1 year from awareness or 3 years from the invasion; applies only to conduct after 10 June 2025 — [OAIC](https://www.oaic.gov.au/privacy/your-privacy-rights/more-privacy-rights/statutory-tort-for-serious-invasions-of-privacy).
- OAIC has made determinations finding scraping activities interfered with privacy, including where privacy policies didn't adequately describe the scraping (as of Aug 2025) — [DLA Piper Privacy Matters](https://privacymatters.dlapiper.com/2025/09/australia-scraping-the-barrel-when-data-scraping-breaches-the-privacy-act/).
- OAIC's generative-AI developer guidance says building a dataset through web scraping "may constitute a covert and therefore unfair means of collection" — [iTnews](https://www.itnews.com.au/news/oaic-draws-lines-on-data-usage-for-generative-ai-training-612500).
- 2024 privacy reforms (Privacy and Other Legislation Amendment Act 2024) — tort, tiered penalties, etc.; ongoing tranche-2 reforms — [Corrs](https://corrs.com.au/insights/australias-ongoing-privacy-reforms-bolstering-australias-privacy-regulatory-framework); [Ashurst 2026 update](https://www.ashurstperkinscoie.com/en/insights/data-bytes-au-key-australian-privacy-updates-so-far-in-2026/).
- Early tort test case Groth & Groth v Herald and Weekly Times settled Nov 2025 — [search summary of law-firm commentary; see McCullough Robertson](https://mccullough.com.au/2026/01/30/data-privacy-week-privacy-reflections-and-projections/).
- Spam Act: consent express or inferred; inferred only from a clear, current/ongoing relationship, not a one-off enquiry; express preferred; sender bears onus of proving consent — [Allens](https://www.allens.com.au/insights-news/explore/2025/food-and-beverage-law-bulletin-2025/emerging-regulator-views-and-enforcement-risks-in-direct-marketing-and-spam/); [Mondaq/Pointon Partners](https://pointonpartners.com.au/the-spam-act-an-update/).
- Enforcement: Tabcorp penalised $4,003,270 (June 2025) for messages to customers who had withdrawn consent — [ACMA](https://www.acma.gov.au/articles/2025-06/tab-penalised-4-million-spamming-vip-customers); SpinTel infringement notice $653,400 for 99 contraventions (published Nov 2026) — [ACMA notice PDF](https://www.acma.gov.au/sites/default/files/2026-11/Infringement%20Notice%20-%20SpinTel%20Pty%20Ltd%20-%20Spam%20Act%202003_Redacted.pdf).
- OAIC + international regulators joint statement on data scraping (Aug 2023, follow-up Oct 2024) and Clearview AI determination (2021) — **[background, not re-verified]** — [OAIC joint statement](https://www.oaic.gov.au/newsroom/global-expectations-of-social-media-platforms-and-other-sites-to-safeguard-against-unlawful-data-scraping); [OAIC Clearview determination](https://www.oaic.gov.au/privacy/privacy-assessments-and-decisions/privacy-decisions/privacy-determinations/commissioner-initiated-investigation-into-clearview-ai,-inc.-privacy-2021-aicmr-54).
- US CFAA: Van Buren v. US (2021) narrowed "exceeds authorized access" to a gates-up-or-down test; Ninth Circuit in hiQ (2022) held scraping publicly accessible pages likely not "without authorization" — **[background, not re-verified]** — [Supreme Court opinion](https://www.supremecourt.gov/opinions/20pdf/19-783_k53l.pdf); [Ninth Circuit 2022](https://cdn.ca9.uscourts.gov/datastore/opinions/2022/04/18/17-16783.pdf).

### Inferences
- Small-business exemption: Privacy Act APPs generally apply to businesses with >A$3M turnover, so a solo dev may be exempt — but the exemption does not apply to those who trade in personal information (e.g. selling leads/data), and the statutory tort applies regardless of size. **[background, not re-verified; check OAIC]**
- Aggregating posts into per-person "lead profiles" is the riskiest pattern (personal information, potential tort exposure, Spam Act if contacted). Aggregating anonymised pain-point themes is far lower risk.
- Spam Act covers email/SMS/IM commercial messages, not public replies; DMs on platforms may count as electronic messages — conservative assumption: get consent or reply publicly within community rules.
- GDPR applies if targeting/monitoring EU individuals; scraped public data still needs a lawful basis (usually legitimate interests with a balancing test) plus Art. 14 notice — relevant only if expanding to EU. **[background]**

### Gaps
- OAIC's current (2025–2026) primary guidance pages on scraping not fetched; exact APP 3.5 wording on "unfair means" re scraping.
- Status of Privacy Act tranche-2 reforms (small-business exemption removal, "fair and reasonable" test) as of Nov 2026.
