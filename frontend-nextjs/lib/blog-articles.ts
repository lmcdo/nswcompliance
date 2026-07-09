/**
 * Blog article metadata — shared between the blog index page and RSS feed.
 */
export interface BlogArticle {
  slug: string;
  title: string;
  description: string;
  category: 'Climate Risk' | 'Planning Reforms' | 'Planning Rules' | 'Property Research';
  date: string;
}

export const ARTICLES: BlogArticle[] = [
  {
    slug: 'conveyancer-duty-climate-risk-nsw',
    title: 'Conveyancers and climate risk: the duty of care in NSW property transactions',
    description: "NSW is buyer-beware, but the duty of care behind a property adviser is widening as flood and climate data goes public. What the standard searches leave out, and what careful practice looks like now.",
    category: 'Climate Risk',
    date: '2026-07-09',
  },
  /* ---- Hub 1: Granny Flat Rules ---- */
  {
    slug: 'can-i-build-a-granny-flat-nsw',
    title: 'Can I build a granny flat on my property in NSW?',
    description: 'Quick eligibility check, CDC vs DA pathways, SEPP requirements, and common blockers — heritage, flood, bushfire, strata, and lot size.',
    category: 'Property Research',
    date: '2026-05-20',
  },
  {
    slug: 'granny-flat-rental-income-roi',
    title: 'Granny flat rental income vs build cost: is it worth it?',
    description: 'Typical build costs, rental yields by location, payback periods, and the hidden cost drivers that affect your return on a secondary dwelling.',
    category: 'Property Research',
    date: '2026-05-20',
  },
  {
    slug: 'dcp-setbacks-granny-flat-nsw',
    title: "Why your council's DCP setbacks for granny flats are different",
    description: 'The SEPP gives one set of standards, but council DCPs often impose stricter controls. How to find your actual setback, landscaping, and parking rules.',
    category: 'Planning Rules',
    date: '2026-05-20',
  },
  {
    slug: 'tiny-houses-nsw-planning-rules',
    title: 'Tiny houses in NSW: what the planning system actually says',
    description: 'NSW has no statutory definition of a tiny house. Where yours falls — caravan, manufactured home, or dwelling — determines your entire approval pathway.',
    category: 'Planning Rules',
    date: '2026-05-20',
  },
  {
    slug: 'heritage-conservation-area-granny-flat-nsw',
    title: "Heritage conservation areas: why you can't build a granny flat (and what to do)",
    description: 'The SEPP CDC pathway is blocked in heritage conservation areas. What the DA process looks like, what councils require, and what is still possible.',
    category: 'Planning Rules',
    date: '2026-05-20',
  },
  {
    slug: 'modular-prefab-homes-nsw-building-bill-2026',
    title: 'Modular and prefab homes in NSW: how the 2026 Building Bill changes everything',
    description: 'The Building Bill formally recognises modular construction and creates a new compliance pathway. Before vs after, who benefits, and implementation timeline.',
    category: 'Planning Reforms',
    date: '2026-05-20',
  },
  /* ---- Hub 2: Buying Property ---- */
  {
    slug: 'section-10-7-flood-risk-nsw',
    title: "The s10.7 flood data gap: what NSW buyers aren't told",
    description: "Your planning certificate says yes or no to flood risk. It doesn't say how deep, how often, or what it costs to insure. Here's what's missing and why.",
    category: 'Property Research',
    date: '2026-05-20',
  },
  {
    slug: 'bushfire-attack-level-bal-property-buyers',
    title: 'Understanding Bushfire Attack Levels (BAL) for property buyers',
    description: "What BAL ratings mean for building costs and insurance, how they're determined, and how to check before you buy.",
    category: 'Property Research',
    date: '2026-05-20',
  },
  {
    slug: 'uninsurable-households-australia-2050',
    title: '1 in 4 Australian households could be uninsurable by 2050',
    description: "The trajectory from 520,000 households in affordability stress today to projected 2.7 million by 2050. Which regions, why it's accelerating, and what to check.",
    category: 'Climate Risk',
    date: '2026-05-20',
  },
  {
    slug: 'section-10-7-certificate-gaps-nsw',
    title: "What a section 10.7 certificate doesn't tell you",
    description: "The planning certificate covers zoning, heritage, and hazard overlays. It misses flood depth, insurance costs, DCP controls, development potential, and more.",
    category: 'Property Research',
    date: '2026-05-20',
  },
  {
    slug: 'regional-property-conveyancing-nsw',
    title: '5 things city conveyancers miss on regional property transactions',
    description: 'On-site sewage, bushfire BAL, minimum lot sizes, Crown roads, and water rights — the checks that trip up metro-trained conveyancers.',
    category: 'Property Research',
    date: '2026-05-20',
  },
  {
    slug: 'qld-seller-disclosure-nsw-comparison',
    title: "QLD seller disclosure regime: what NSW can learn (and what's coming)",
    description: "Queensland requires sellers to disclose known defects. NSW relies on buyer beware. A state-by-state comparison and what the Productivity Commission recommends.",
    category: 'Planning Reforms',
    date: '2026-05-20',
  },
  {
    slug: 'is-my-house-in-a-flood-zone-nsw',
    title: 'Is my house in a flood zone? How to check in NSW',
    description: 'Step-by-step guide to checking flood zone status for any NSW property — free government sources, what the data actually means, and what it misses.',
    category: 'Property Research',
    date: '2026-05-17',
  },
  /* ---- Hub 3: Planning Reforms ---- */
  {
    slug: 'nsw-building-bill-2026-certifier-penalties',
    title: 'The NSW Building Bill 2026: $1.1M certifier penalties and what it means',
    description: 'Maximum penalties up to $1.1M, a Building Commission with investigative powers, and mandatory professional standards. What builders and certifiers need to know.',
    category: 'Planning Reforms',
    date: '2026-05-20',
  },
  {
    slug: 'pattern-book-homes-nsw-cdc-pathway',
    title: 'Pattern Book homes: the 10-day CDC pathway that could save $330K',
    description: 'Pre-approved designs, a 10-day complying development certificate, and estimated $330K savings per dwelling. How the Pattern Book pathway works.',
    category: 'Planning Reforms',
    date: '2026-05-20',
  },
  {
    slug: '128-councils-zero-apis-nsw-planning',
    title: '128 councils, zero APIs: why NSW planning compliance is so hard',
    description: "Every council has different DCP formats, no standardised data, and no APIs. What the Planning Portal covers, what it doesn't, and what digital planning could look like.",
    category: 'Planning Reforms',
    date: '2026-05-20',
  },
  {
    slug: 'merged-lga-different-setback-rules',
    title: 'Why different setback rules in the same merged LGA',
    description: 'NSW council amalgamations left merged LGAs with multiple inherited DCPs. Your neighbour in the same council area can have completely different rules.',
    category: 'Planning Rules',
    date: '2026-05-20',
  },
  {
    slug: 'aasb-s2-mandatory-climate-reporting-property',
    title: 'AASB S2: what mandatory climate reporting means for property',
    description: "Who reports when, what the four pillars require for property portfolios, and where to source the climate risk data you'll need.",
    category: 'Climate Risk',
    date: '2026-05-20',
  },
  {
    slug: 'nathers-ratings-historical-weather-accuracy',
    title: 'NatHERS ratings use historical weather: 7-star might perform like 5-star by 2050',
    description: 'NatHERS simulates energy performance using 1990-2015 weather data. Buildings last 50+ years. The gap between rated and actual performance is growing.',
    category: 'Climate Risk',
    date: '2026-05-20',
  },
  {
    slug: 'ccnh-sepp-nsw-development-changes',
    title: 'What is the CC&NH SEPP? How it changes NSW development',
    description: 'The draft Climate Change and Natural Hazards SEPP consolidates flood, bushfire, and coastal planning into one instrument. What it means for development.',
    category: 'Planning Reforms',
    date: '2026-05-20',
  },
  /* ---- Data Quality & Methodology ---- */
  {
    slug: 'how-we-validate-property-data-nsw',
    title: 'How we validate property data before it reaches you',
    description: 'Every property screening result goes through a 5-pass validation: data source verification, algorithm checks, edge case hardening, connection safety, and output defensibility.',
    category: 'Property Research',
    date: '2026-05-21',
  },
  /* ---- Hub 3 (existing) ---- */
  {
    slug: 'aasb-s2-property-climate-data',
    title: 'AASB S2 and property-level climate data: what fund managers need',
    description: 'How AASB S2 climate disclosure requirements affect property portfolio reporting, and where to source location-specific physical risk data in Australia.',
    category: 'Climate Risk',
    date: '2026-05-17',
  },
  {
    slug: 'apra-cpg-229-property-assessment',
    title: 'APRA CPG 229: climate risk assessment for property lending',
    description: 'A practical guide to meeting APRA CPG 229 requirements for property-secured lending, including physical risk data, scenario analysis, and portfolio screening.',
    category: 'Climate Risk',
    date: '2026-05-17',
  },
  {
    slug: 'climate-risk-data-provider-australia',
    title: 'Climate risk data providers in Australia: a comparison',
    description: 'Comparing Australian climate risk data sources — government, commercial, and open-source — for flood, bushfire, coastal, and heat stress assessment.',
    category: 'Climate Risk',
    date: '2026-05-17',
  },
  {
    slug: 'uninsurable-property-climate-risk',
    title: 'Uninsurable properties: how climate risk is repricing Australian real estate',
    description: 'Insurance withdrawal, premium spikes, and the emerging data infrastructure that buyers need to assess property-level climate exposure before purchase.',
    category: 'Climate Risk',
    date: '2026-05-17',
  },
  /* ---- Hub 4: Regional ---- */
  {
    slug: 'tree-change-checklist-nsw-planning',
    title: 'The tree change checklist: 7 planning checks before you buy rural',
    description: 'Zoning, minimum lot size, bushfire, flood, on-site sewage, water rights, and access — the 7 checks before buying regional property in NSW.',
    category: 'Property Research',
    date: '2026-05-20',
  },
  {
    slug: 'what-can-i-build-rural-land-nsw',
    title: 'What can I build on 5 acres in NSW? Rural zoning explained',
    description: 'RU1, RU2, RU4, R5 — what each rural zone permits, minimum lot sizes by region, and common misunderstandings about rural land use in NSW.',
    category: 'Planning Rules',
    date: '2026-05-20',
  },
  {
    slug: 'subdivide-property-nsw-minimum-lot-sizes',
    title: 'Can I subdivide my property in NSW? Minimum lot sizes explained',
    description: 'How to find your minimum lot size, the three types of subdivision, common blockers, costs, and the dual occupancy pathway.',
    category: 'Planning Rules',
    date: '2026-05-20',
  },
];
