export interface BushfireLgaData {
  name: string
  slug: string
  /** Estimated % of LGA mapped as bush fire prone land */
  bfplCoveragePct: number
  /** Dominant vegetation categories */
  dominantVegetation: string[]
  /** Related LGA slugs for "also check" links */
  relatedSlugs: string[]
  faqs: Array<{ q: string; a: string }>
}

export const BUSHFIRE_LGAS: BushfireLgaData[] = [
  {
    name: 'Blue Mountains',
    slug: 'blue-mountains',
    bfplCoveragePct: 95,
    dominantVegetation: ['Eucalypt forest', 'Woodland', 'Heath'],
    relatedSlugs: ['hawkesbury', 'penrith', 'lithgow'],
    faqs: [
      {
        q: 'How much of the Blue Mountains is bush fire prone land?',
        a: 'Approximately 95% of the Blue Mountains LGA is mapped as bush fire prone land by the NSW Rural Fire Service. This is one of the highest proportions in metropolitan NSW, reflecting the extensive eucalypt forest surrounding the residential corridor along the Great Western Highway.',
      },
      {
        q: 'What BAL rating should I expect in the Blue Mountains?',
        a: 'BAL ratings in the Blue Mountains typically range from BAL-12.5 to BAL-FZ depending on slope, aspect, and distance to vegetation. Properties on ridgelines or adjacent to national park boundaries frequently receive BAL-29 or BAL-40. A formal BAL assessment is required before any building work on bush fire prone land.',
      },
      {
        q: 'Do I need RFS approval to build in the Blue Mountains?',
        a: 'Development on bush fire prone land in the Blue Mountains requires a Bush Fire Safety Authority from the NSW RFS under section 4.14 of the Environmental Planning & Assessment Act 1979. This applies to new dwellings, additions, and granny flats. Processing typically takes 40 business days.',
      },
      {
        q: 'Does bushfire status affect granny flat eligibility in the Blue Mountains?',
        a: 'Properties on bush fire prone land can still build granny flats, but the CDC pathway requires compliance with Planning for Bush Fire Protection 2019. If the property is in a Category 1 vegetation area, a formal BAL assessment is required. The bush fire protection measures add approximately $15,000–$30,000 to construction costs depending on the BAL rating.',
      },
      {
        q: 'What are the extra building costs for bushfire in the Blue Mountains?',
        a: 'AS 3959 construction standards apply to all new buildings on bush fire prone land. At BAL-12.5, additional costs are modest (ember protection, screening). At BAL-29 and above, costs increase significantly due to requirements for non-combustible cladding, tempered glass, steel shutters, and dedicated water supply. Budget $15,000–$50,000 depending on BAL rating.',
      },
    ],
  },
  {
    name: 'Ku-ring-gai',
    slug: 'ku-ring-gai',
    bfplCoveragePct: 70,
    dominantVegetation: ['Eucalypt forest', 'Turpentine-ironbark', 'Rainforest'],
    relatedSlugs: ['hornsby', 'northern-beaches', 'willoughby'],
    faqs: [
      {
        q: 'Is Ku-ring-gai bush fire prone?',
        a: 'Approximately 70% of Ku-ring-gai is mapped as bush fire prone land. The LGA contains extensive areas of remnant bushland in national parks and reserves bordering residential properties. Properties adjacent to Lane Cove, Garigal, and Ku-ring-gai Chase National Parks are most affected.',
      },
      {
        q: 'What BAL ratings are common in Ku-ring-gai?',
        a: 'BAL ratings in Ku-ring-gai vary significantly by street. Properties on the bushland edge typically receive BAL-19 to BAL-40, while properties buffered by other houses may be BAL-LOW. The steep terrain in many parts of Ku-ring-gai increases BAL ratings, as fire travels faster uphill.',
      },
      {
        q: 'How does bushfire status affect property values in Ku-ring-gai?',
        a: 'Bushfire status is a material fact that must be disclosed in Section 10.7 certificates. Properties with high BAL ratings may face higher insurance premiums and additional construction costs for renovations. However, Ku-ring-gai\'s proximity to bushland is also a significant amenity value, and the market impact varies by buyer.',
      },
      {
        q: 'Do I need a BAL assessment to renovate in Ku-ring-gai?',
        a: 'Any building work that requires consent on bush fire prone land requires consideration of bushfire risk. Major renovations and additions require a BAL assessment. Minor works (like a deck or pergola) may not require a formal assessment but must still comply with AS 3959 construction standards.',
      },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    bfplCoveragePct: 65,
    dominantVegetation: ['Eucalypt forest', 'Woodland', 'Heath'],
    relatedSlugs: ['ku-ring-gai', 'the-hills', 'northern-beaches'],
    faqs: [
      {
        q: 'How much of Hornsby Shire is bushfire prone?',
        a: 'Approximately 65% of Hornsby Shire is mapped as bush fire prone land. The Shire borders Berowra Valley, Ku-ring-gai Chase, and Marramarra National Parks. Properties in suburbs like Berowra, Galston, Arcadia, and Hornsby Heights are most affected.',
      },
      {
        q: 'What bushfire categories exist in Hornsby?',
        a: 'Hornsby has Category 1 (highest risk), Category 2, Category 3, and vegetation buffer zones. Category 1 areas are closest to dense eucalypt forest — primarily along the western and northern edges of the Shire bordering national parks.',
      },
      {
        q: 'Can I build a granny flat in bushfire-prone Hornsby?',
        a: 'Yes, but compliance with Planning for Bush Fire Protection 2019 is required. The CDC pathway still applies on bush fire prone land in Hornsby, provided the property meets all SEPP Housing 2021 requirements including bushfire construction standards. Higher BAL ratings increase construction costs.',
      },
      {
        q: 'Does Hornsby flood and bushfire overlap?',
        a: 'Yes. Some properties in the Berowra Creek and Hawkesbury River catchments are affected by both flood planning overlays and bush fire prone land mapping. Properties with both constraints face additional assessment requirements for any development application.',
      },
    ],
  },
  {
    name: 'Sutherland',
    slug: 'sutherland',
    bfplCoveragePct: 55,
    dominantVegetation: ['Eucalypt forest', 'Heath', 'Woodland'],
    relatedSlugs: ['wollongong', 'campbelltown', 'georges-river'],
    faqs: [
      {
        q: 'Is Sutherland Shire bush fire prone?',
        a: 'Approximately 55% of Sutherland Shire is mapped as bush fire prone land. The Royal National Park dominates the southern boundary, and Heathcote National Park the western edge. Suburbs like Engadine, Heathcote, Waterfall, and Bundeena are most affected.',
      },
      {
        q: 'What happened during the 2019–20 bushfires in Sutherland?',
        a: 'The Royal National Park burned extensively during the 2019–20 season, with fires reaching the edges of suburbs including Bundeena. These events led to updated bush fire prone land mapping and increased scrutiny of BAL ratings for properties on the national park boundary.',
      },
      {
        q: 'Does bushfire status affect insurance in Sutherland?',
        a: 'Yes. Properties in bush fire prone areas of Sutherland typically face higher premiums. Some insurers apply exclusions for properties with BAL-40 or BAL-FZ ratings. Use this checker to see your BFPL category, then contact your insurer with the results.',
      },
      {
        q: 'Are there 10/50 clearing entitlements in Sutherland?',
        a: 'The 10/50 vegetation clearing entitlement allows property owners within 10m of a building on bush fire prone land to clear certain trees (within 10m) and understorey vegetation (within 50m) without council approval. However, heritage items and threatened species regulations may restrict clearing in some Sutherland locations.',
      },
    ],
  },
  {
    name: 'Northern Beaches',
    slug: 'northern-beaches',
    bfplCoveragePct: 45,
    dominantVegetation: ['Eucalypt forest', 'Heath', 'Littoral'],
    relatedSlugs: ['ku-ring-gai', 'hornsby', 'willoughby'],
    faqs: [
      {
        q: 'Is the Northern Beaches bush fire prone?',
        a: 'Approximately 45% of the Northern Beaches LGA is mapped as bush fire prone land. Key areas include properties adjacent to Ku-ring-gai Chase and Garigal National Parks, particularly in Ingleside, Terrey Hills, Belrose, Davidson, and Frenchs Forest.',
      },
      {
        q: 'What BAL ratings are common on the Northern Beaches?',
        a: 'BAL ratings vary widely across the LGA. Coastal and harbour suburbs are generally BAL-LOW, while suburbs adjacent to national parks can range from BAL-12.5 to BAL-40. The Ingleside precinct has some of the highest BAL ratings in the LGA.',
      },
      {
        q: 'Does bushfire affect development in Ingleside?',
        a: 'Ingleside is one of the most bushfire-affected areas on the Northern Beaches. The area was identified for potential urban development but bushfire constraints have been a significant planning consideration. Properties in Ingleside typically require formal BAL assessments for any building work.',
      },
      {
        q: 'Can I clear vegetation on my Northern Beaches property?',
        a: 'The 10/50 vegetation clearing entitlement applies on bush fire prone land. However, Northern Beaches Council has significant biodiversity and heritage constraints that may limit clearing. Check with council before undertaking any vegetation removal.',
      },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    bfplCoveragePct: 80,
    dominantVegetation: ['Eucalypt forest', 'Woodland', 'Rainforest'],
    relatedSlugs: ['wollondilly', 'campbelltown', 'shoalhaven'],
    faqs: [
      {
        q: 'How much of Wingecarribee is bush fire prone?',
        a: 'Approximately 80% of Wingecarribee Shire is mapped as bush fire prone land. The Southern Highlands is surrounded by Morton, Kangaroo Valley, and Nattai national parks. Suburbs including Bundanoon, Exeter, Bowral outskirts, and Mittagong fringes are most affected.',
      },
      {
        q: 'What happened during the 2019–20 bushfires in the Southern Highlands?',
        a: 'The Green Wattle Creek and Morton fires significantly impacted Wingecarribee during the 2019–20 season, with Bundanoon, Wingello, and surrounding villages directly threatened. Properties damaged or destroyed had their BFPL mapping and BAL ratings reviewed following the fires.',
      },
      {
        q: 'Is bushfire a concern when buying property in the Southern Highlands?',
        a: 'Bushfire is a material consideration for property purchases in Wingecarribee. Section 10.7 certificates must disclose bush fire prone land status. Buyers should check BAL ratings before purchase, as high BAL ratings affect both construction costs for future work and insurance premiums.',
      },
      {
        q: 'Do I need a bushfire assessment for a shed in Wingecarribee?',
        a: 'Outbuildings on bush fire prone land generally require consideration of bushfire risk. Detached sheds over a certain size may need a BAL assessment and compliance with AS 3959. Check with Wingecarribee Shire Council for specific requirements based on the size and use of the structure.',
      },
    ],
  },
  {
    name: 'Shoalhaven',
    slug: 'shoalhaven',
    bfplCoveragePct: 85,
    dominantVegetation: ['Eucalypt forest', 'Coastal heath', 'Rainforest'],
    relatedSlugs: ['wingecarribee', 'eurobodalla', 'wollongong'],
    faqs: [
      {
        q: 'How much of Shoalhaven is bush fire prone?',
        a: 'Approximately 85% of Shoalhaven is mapped as bush fire prone land, making it one of the most bushfire-affected LGAs in NSW. The area is bordered by Morton National Park and extensive state forests. Nowra, Berry, Huskisson, and South Coast villages are all partially affected.',
      },
      {
        q: 'What happened in the 2019–20 Shoalhaven bushfires?',
        a: 'The Currowan Fire was one of the largest fires in Australia\'s 2019–20 season, burning over 500,000 hectares through Shoalhaven. Villages including Conjola Park, Sussex Inlet, and Lake Tabourie experienced significant property losses. This event led to updated BFPL mapping across the LGA.',
      },
      {
        q: 'What BAL ratings are typical in Shoalhaven?',
        a: 'BAL ratings in Shoalhaven range widely. Coastal properties in established suburbs may be BAL-LOW to BAL-12.5, while rural-residential properties and those adjacent to national parks frequently receive BAL-29 to BAL-FZ. The undulating terrain increases BAL ratings on slopes.',
      },
      {
        q: 'Can I subdivide bushfire prone land in Shoalhaven?',
        a: 'Subdivision on bush fire prone land requires RFS referral and compliance with Planning for Bush Fire Protection 2019. The subdivision must demonstrate adequate asset protection zones, access, water supply, and egress. Some heavily vegetated lots may not be subdividable due to bushfire constraints.',
      },
    ],
  },
  {
    name: 'Penrith',
    slug: 'penrith',
    bfplCoveragePct: 40,
    dominantVegetation: ['Eucalypt forest', 'Cumberland Plain woodland'],
    relatedSlugs: ['blue-mountains', 'hawkesbury', 'the-hills'],
    faqs: [
      {
        q: 'Is Penrith bush fire prone?',
        a: 'Approximately 40% of Penrith LGA is mapped as bush fire prone land. The western and southern areas bordering the Blue Mountains and Nepean River corridor are most affected. Suburbs including Castlereagh, Llandilo, Cranebrook edges, and Mulgoa are in bush fire prone zones.',
      },
      {
        q: 'Does bushfire affect development in western Penrith?',
        a: 'Yes. Development in western Penrith suburbs adjacent to the Blue Mountains requires bushfire assessment. The transition zone between urban Penrith and the Blue Mountains escarpment has increasing BAL ratings. New release areas in the west must address bushfire in their planning proposals.',
      },
      {
        q: 'What bushfire categories exist in Penrith?',
        a: 'Penrith has all bushfire categories — from Category 1 (highest risk) along the Blue Mountains boundary to Category 3 and vegetation buffer zones in the semi-rural west. Eastern Penrith suburbs are generally not affected by bush fire prone land mapping.',
      },
      {
        q: 'Do Penrith flood and bushfire zones overlap?',
        a: 'Yes, particularly along the Nepean River corridor and in low-lying western areas. Properties in Castlereagh and parts of Cranebrook may be affected by both flood planning overlays and bush fire prone land. Dual constraints increase assessment requirements for development applications.',
      },
    ],
  },
]

export const BUSHFIRE_LGA_SLUG_MAP: Record<string, BushfireLgaData> = Object.fromEntries(
  BUSHFIRE_LGAS.map(lga => [lga.slug, lga])
)
