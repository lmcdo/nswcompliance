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
  // ── Greater Sydney — Inner & East ──────────────────────────────────
  {
    name: 'Inner West',
    slug: 'inner-west',
    bfplCoveragePct: 2,
    dominantVegetation: ['Urban remnant', 'Riparian corridor'],
    relatedSlugs: ['bayside', 'canterbury-bankstown', 'lane-cove'],
    faqs: [
      { q: 'Is the Inner West bush fire prone?', a: 'Only about 2% of the Inner West LGA is mapped as bush fire prone land. Small pockets exist along creek corridors and near remnant bushland in parks. The vast majority of residential properties are not on BFPL.' },
      { q: 'Do I need a bushfire assessment for my Inner West property?', a: 'Most Inner West properties do not require a BAL assessment. However, if your property is within the mapped BFPL area — even in a vegetation buffer zone — any new building work triggers AS 3959 considerations. Check your specific address above.' },
      { q: 'Does low bushfire risk affect my Inner West insurance premium?', a: 'Generally no. Properties not on bush fire prone land are not subject to bushfire insurance loading. If your property IS mapped as BFPL (even at BAL-LOW), some insurers may apply a small loading.' },
    ],
  },
  {
    name: 'Bayside',
    slug: 'bayside',
    bfplCoveragePct: 5,
    dominantVegetation: ['Coastal heath', 'Urban remnant'],
    relatedSlugs: ['randwick', 'georges-river', 'canterbury-bankstown'],
    faqs: [
      { q: 'Is Bayside bush fire prone?', a: 'Approximately 5% of Bayside LGA is mapped as bush fire prone land. Affected areas are primarily near remnant bushland around Botany Bay foreshore reserves and parts of the former Rockdale LGA near Bardwell Valley.' },
      { q: 'What BAL rating should I expect in Bayside?', a: 'Most Bayside properties are not on BFPL. Where BFPL does apply, ratings are typically BAL-LOW or BAL-12.5 due to the small scale of adjacent vegetation and flat terrain.' },
      { q: 'Does bushfire status appear on my Bayside Section 10.7?', a: 'Yes. If your property is mapped as bush fire prone land, this is disclosed on the Section 10.7 planning certificate. Even BAL-LOW designation appears.' },
    ],
  },
  {
    name: 'Randwick',
    slug: 'randwick',
    bfplCoveragePct: 3,
    dominantVegetation: ['Coastal heath', 'Eastern Suburbs Banksia Scrub'],
    relatedSlugs: ['bayside', 'waverley', 'woollahra'],
    faqs: [
      { q: 'Is Randwick bush fire prone?', a: 'About 3% of Randwick LGA is mapped as bush fire prone land. The main affected area is around Malabar Headland, Randwick Environment Park, and the Eastern Suburbs Banksia Scrub remnants near La Perouse.' },
      { q: 'Does Eastern Suburbs Banksia Scrub create bushfire risk?', a: 'Eastern Suburbs Banksia Scrub is a critically endangered ecological community. Where it borders residential properties, it can trigger BFPL mapping. However, vegetation clearing is heavily restricted due to its conservation status.' },
      { q: 'Do I need a BAL assessment in Randwick?', a: 'Only if your property is on mapped BFPL. The vast majority of Randwick residential properties are not affected. Properties near Malabar, La Perouse, and some parts of Matraville should check above.' },
    ],
  },
  {
    name: 'Waverley',
    slug: 'waverley',
    bfplCoveragePct: 1,
    dominantVegetation: ['Coastal heath'],
    relatedSlugs: ['randwick', 'woollahra'],
    faqs: [
      { q: 'Is Waverley bush fire prone?', a: 'Less than 1% of Waverley LGA is mapped as bush fire prone land. Small areas near coastal headlands may be mapped. Waverley is one of the least bushfire-affected LGAs in NSW.' },
      { q: 'Do I need to check bushfire status for a Waverley property?', a: 'While unlikely to be affected, it is still worth checking if your property borders parkland or headland reserves. Bush fire prone land status is disclosed on Section 10.7 certificates.' },
    ],
  },
  {
    name: 'Woollahra',
    slug: 'woollahra',
    bfplCoveragePct: 2,
    dominantVegetation: ['Urban remnant', 'Harbour foreshore'],
    relatedSlugs: ['waverley', 'randwick'],
    faqs: [
      { q: 'Is Woollahra bush fire prone?', a: 'About 2% of Woollahra is mapped as bush fire prone land, primarily around harbour foreshore reserves and some larger private gardens with significant tree canopy.' },
      { q: 'Does bushfire affect heritage properties in Woollahra?', a: 'For the small overlap of heritage and BFPL, both heritage conservation requirements and bushfire construction standards apply. This can create competing obligations.' },
      { q: 'Do I need a BAL assessment for renovations in Woollahra?', a: 'Only if your property is on mapped BFPL. Given the very low coverage, most renovations do not require bushfire consideration.' },
    ],
  },
  // ── Greater Sydney — North ─────────────────────────────────────────
  {
    name: 'Northern Beaches',
    slug: 'northern-beaches',
    bfplCoveragePct: 45,
    dominantVegetation: ['Eucalypt forest', 'Heath', 'Littoral'],
    relatedSlugs: ['ku-ring-gai', 'hornsby', 'lane-cove'],
    faqs: [
      { q: 'Is the Northern Beaches bush fire prone?', a: 'Approximately 45% of the Northern Beaches LGA is mapped as bush fire prone land. Key areas include properties adjacent to Ku-ring-gai Chase and Garigal National Parks, particularly in Ingleside, Terrey Hills, Belrose, Davidson, and Frenchs Forest.' },
      { q: 'What BAL ratings are common on the Northern Beaches?', a: 'BAL ratings vary widely. Coastal and harbour suburbs are generally BAL-LOW, while suburbs adjacent to national parks can range from BAL-12.5 to BAL-40. Ingleside has some of the highest ratings.' },
      { q: 'Does bushfire affect development in Ingleside?', a: 'Ingleside is one of the most bushfire-affected areas on the Northern Beaches. Properties there typically require formal BAL assessments for any building work.' },
    ],
  },
  {
    name: 'Ku-ring-gai',
    slug: 'ku-ring-gai',
    bfplCoveragePct: 70,
    dominantVegetation: ['Eucalypt forest', 'Turpentine-ironbark', 'Rainforest'],
    relatedSlugs: ['hornsby', 'northern-beaches', 'ryde'],
    faqs: [
      { q: 'Is Ku-ring-gai bush fire prone?', a: 'Approximately 70% of Ku-ring-gai is mapped as bush fire prone land. Properties adjacent to Lane Cove, Garigal, and Ku-ring-gai Chase National Parks are most affected.' },
      { q: 'What BAL ratings are common in Ku-ring-gai?', a: 'BAL ratings vary significantly by street. Properties on the bushland edge typically receive BAL-19 to BAL-40, while properties buffered by other houses may be BAL-LOW. Steep terrain increases ratings.' },
      { q: 'How does bushfire status affect property values in Ku-ring-gai?', a: 'Bushfire status is a material fact disclosed in Section 10.7 certificates. Properties with high BAL ratings may face higher insurance premiums and additional construction costs.' },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    bfplCoveragePct: 65,
    dominantVegetation: ['Eucalypt forest', 'Woodland', 'Heath'],
    relatedSlugs: ['ku-ring-gai', 'the-hills-shire', 'northern-beaches'],
    faqs: [
      { q: 'How much of Hornsby Shire is bushfire prone?', a: 'Approximately 65% of Hornsby Shire is mapped as bush fire prone land. The Shire borders Berowra Valley, Ku-ring-gai Chase, and Marramarra National Parks.' },
      { q: 'What bushfire categories exist in Hornsby?', a: 'Hornsby has Category 1 (highest risk), Category 2, Category 3, and vegetation buffer zones. Category 1 areas are closest to dense eucalypt forest along the western and northern edges.' },
      { q: 'Can I build a granny flat in bushfire-prone Hornsby?', a: 'Yes, but compliance with Planning for Bush Fire Protection 2019 is required. The CDC pathway still applies on BFPL in Hornsby, provided the property meets all SEPP Housing 2021 requirements.' },
    ],
  },
  {
    name: 'Lane Cove',
    slug: 'lane-cove',
    bfplCoveragePct: 20,
    dominantVegetation: ['Eucalypt forest', 'Turpentine-ironbark'],
    relatedSlugs: ['ryde', 'ku-ring-gai', 'northern-beaches'],
    faqs: [
      { q: 'Is Lane Cove bush fire prone?', a: 'Approximately 20% of Lane Cove LGA is mapped as bush fire prone land. The main affected area is along the Lane Cove River and Lane Cove National Park.' },
      { q: 'What BAL ratings are common in Lane Cove?', a: 'Properties directly adjacent to Lane Cove National Park may receive BAL-12.5 to BAL-29. Properties buffered by one or more rows of houses are typically BAL-LOW or not on BFPL.' },
      { q: 'Does bushfire affect unit development in Lane Cove?', a: 'Multi-dwelling buildings on BFPL must comply with AS 3959 and may require a Bush Fire Safety Authority from the RFS.' },
    ],
  },
  {
    name: 'Ryde',
    slug: 'ryde',
    bfplCoveragePct: 12,
    dominantVegetation: ['Eucalypt forest', 'Turpentine-ironbark'],
    relatedSlugs: ['lane-cove', 'ku-ring-gai', 'parramatta'],
    faqs: [
      { q: 'Is Ryde bush fire prone?', a: 'Approximately 12% of Ryde LGA is mapped as bush fire prone land. Affected areas are primarily along the Lane Cove River and near Field of Mars Reserve.' },
      { q: 'What areas of Ryde are most affected?', a: 'Properties near Field of Mars Reserve in East Ryde, along the Lane Cove River in Marsfield, and near Denistone East bushland reserves are most likely to be on BFPL.' },
      { q: 'Does bushfire affect granny flat eligibility in Ryde?', a: 'Properties on BFPL can still build granny flats via CDC, but must comply with Planning for Bush Fire Protection 2019. Most exclusions in Ryde relate to heritage or lot size rather than bushfire.' },
    ],
  },
  // ── Greater Sydney — West ──────────────────────────────────────────
  {
    name: 'Parramatta',
    slug: 'parramatta',
    bfplCoveragePct: 8,
    dominantVegetation: ['Cumberland Plain woodland', 'Riparian'],
    relatedSlugs: ['blacktown', 'ryde', 'the-hills-shire'],
    faqs: [
      { q: 'Is Parramatta bush fire prone?', a: 'About 8% of the City of Parramatta is mapped as bush fire prone land. Affected areas are primarily along the Parramatta River corridor, near Lake Parramatta Reserve, and around remnant Cumberland Plain woodland.' },
      { q: 'Does bushfire affect development in Parramatta CBD?', a: 'No. Parramatta CBD and its immediate surrounds are not on bush fire prone land. BFPL mapping affects fringe suburbs with remnant bushland.' },
      { q: 'What vegetation types create bushfire risk in Parramatta?', a: 'Cumberland Plain woodland is the dominant vegetation type. This is a critically endangered ecological community, which means vegetation clearing for bushfire protection may be restricted.' },
    ],
  },
  {
    name: 'Blacktown',
    slug: 'blacktown',
    bfplCoveragePct: 15,
    dominantVegetation: ['Cumberland Plain woodland', 'Eucalypt forest'],
    relatedSlugs: ['the-hills-shire', 'penrith', 'parramatta'],
    faqs: [
      { q: 'Is Blacktown bush fire prone?', a: 'Approximately 15% of Blacktown LGA is mapped as bush fire prone land. The western and north-western areas — including parts of Riverstone, Marsden Park fringes, and Shanes Park — are most affected.' },
      { q: 'Does bushfire affect new housing estates in Blacktown?', a: 'Some new release areas adjoin bushland. These estates must address bushfire at the subdivision stage, with asset protection zones built into lot layouts.' },
      { q: 'Can I build a granny flat on BFPL land in Blacktown?', a: 'Yes. Granny flats via CDC on BFPL land must comply with Planning for Bush Fire Protection 2019 and AS 3959. Bushfire compliance adds modest cost at BAL-12.5.' },
    ],
  },
  {
    name: 'The Hills Shire',
    slug: 'the-hills-shire',
    bfplCoveragePct: 30,
    dominantVegetation: ['Eucalypt forest', 'Cumberland Plain woodland'],
    relatedSlugs: ['hornsby', 'blacktown', 'hawkesbury'],
    faqs: [
      { q: 'How much of The Hills Shire is bush fire prone?', a: 'Approximately 30% is mapped as BFPL. The northern and western rural-residential areas — Glenorie, Dural, Kenthurst, Annangrove — are most affected. Urban corridors around Castle Hill and Baulkham Hills are generally not on BFPL.' },
      { q: 'What BAL ratings are common in The Hills?', a: 'Urban areas near Castle Hill are typically BAL-LOW. Semi-rural properties in Glenorie, Dural, and Kenthurst often receive BAL-19 to BAL-40 depending on proximity to bushland and slope.' },
      { q: 'Does bushfire affect granny flat eligibility in The Hills?', a: 'Rural-residential lots often qualify on lot size. BFPL status does not exclude CDC eligibility but requires compliance with Planning for Bush Fire Protection 2019. Construction costs increase with BAL rating.' },
    ],
  },
  {
    name: 'Penrith',
    slug: 'penrith',
    bfplCoveragePct: 40,
    dominantVegetation: ['Eucalypt forest', 'Cumberland Plain woodland'],
    relatedSlugs: ['blue-mountains', 'hawkesbury', 'blacktown'],
    faqs: [
      { q: 'Is Penrith bush fire prone?', a: 'Approximately 40% of Penrith LGA is mapped as bush fire prone land. The western and southern areas bordering the Blue Mountains and Nepean River corridor are most affected.' },
      { q: 'Does bushfire affect development in western Penrith?', a: 'Yes. The transition zone between urban Penrith and the Blue Mountains escarpment has increasing BAL ratings. New release areas must address bushfire in planning proposals.' },
      { q: 'Do Penrith flood and bushfire zones overlap?', a: 'Yes, particularly along the Nepean River corridor. Properties in Castlereagh and parts of Cranebrook may be affected by both flood and bushfire constraints.' },
    ],
  },
  {
    name: 'Hawkesbury',
    slug: 'hawkesbury',
    bfplCoveragePct: 60,
    dominantVegetation: ['Eucalypt forest', 'Woodland', 'Riparian'],
    relatedSlugs: ['penrith', 'the-hills-shire', 'blue-mountains'],
    faqs: [
      { q: 'How much of Hawkesbury is bush fire prone?', a: 'Approximately 60% of Hawkesbury LGA is mapped as bush fire prone land. Rural-residential areas in Kurrajong, Kurmond, Bilpin, and the Colo Valley are heavily affected.' },
      { q: 'Do Hawkesbury flood and bushfire overlap?', a: 'Yes — Hawkesbury has one of Australia\'s most significant dual natural hazard exposures. The Hawkesbury-Nepean floodplain is bordered by heavily forested escarpments.' },
      { q: 'Does bushfire affect subdivisions in Hawkesbury?', a: 'Subdivision on BFPL requires RFS referral and compliance with Planning for Bush Fire Protection 2019. Asset protection zones, access, and water supply requirements limit subdivision potential.' },
    ],
  },
  // ── Greater Sydney — South & Southwest ─────────────────────────────
  {
    name: 'Campbelltown',
    slug: 'campbelltown',
    bfplCoveragePct: 35,
    dominantVegetation: ['Eucalypt forest', 'Cumberland Plain woodland'],
    relatedSlugs: ['camden', 'liverpool', 'sutherland-shire'],
    faqs: [
      { q: 'Is Campbelltown bush fire prone?', a: 'Approximately 35% of Campbelltown LGA is mapped as bush fire prone land. The western and southern areas bordering Dharawal National Park and Georges River are most affected.' },
      { q: 'What happened during the 2019–20 bushfires in Campbelltown?', a: 'The Green Wattle Creek fire reached the southwestern edge of Campbelltown. Properties in Wedderburn and near Dharawal NP were directly threatened, leading to updated BFPL mapping.' },
      { q: 'Does bushfire affect new estates in Campbelltown?', a: 'Parts of Menangle Park and Gilead release areas adjoin bushland. Individual lots on the bushland edge may be on BFPL and require AS 3959 construction.' },
    ],
  },
  {
    name: 'Camden',
    slug: 'camden',
    bfplCoveragePct: 20,
    dominantVegetation: ['Cumberland Plain woodland', 'Eucalypt forest'],
    relatedSlugs: ['campbelltown', 'liverpool', 'wollongong'],
    faqs: [
      { q: 'Is Camden bush fire prone?', a: 'Approximately 20% of Camden LGA is mapped as bush fire prone land. The southern and western fringes near the Nepean River corridor and remnant bushland are most affected.' },
      { q: 'Does bushfire affect new housing in Camden?', a: 'Most new estates (Oran Park, Gregory Hills) were master-planned with bushfire in mind. Some edge lots may still be on BFPL and require AS 3959 construction.' },
      { q: 'What vegetation creates bushfire risk in Camden?', a: 'Cumberland Plain woodland is the main vegetation type. This endangered ecological community limits vegetation clearing options.' },
    ],
  },
  {
    name: 'Liverpool',
    slug: 'liverpool',
    bfplCoveragePct: 15,
    dominantVegetation: ['Cumberland Plain woodland', 'Riparian'],
    relatedSlugs: ['campbelltown', 'canterbury-bankstown', 'camden'],
    faqs: [
      { q: 'Is Liverpool bush fire prone?', a: 'Approximately 15% of Liverpool LGA is mapped as bush fire prone land. Affected areas are primarily near the Georges River, Holsworthy Military Reserve, and remnant woodland in the rural west.' },
      { q: 'Does Holsworthy affect bushfire risk in Liverpool?', a: 'The Holsworthy Military Reserve contains large tracts of bushland that create BFPL mapping on adjacent residential properties. Suburbs bordering the reserve are affected.' },
      { q: 'Does bushfire overlap with flood risk in Liverpool?', a: 'Some areas along the Georges River are affected by both flood and bushfire constraints.' },
    ],
  },
  {
    name: 'Sutherland Shire',
    slug: 'sutherland-shire',
    bfplCoveragePct: 55,
    dominantVegetation: ['Eucalypt forest', 'Heath', 'Woodland'],
    relatedSlugs: ['wollongong', 'campbelltown', 'georges-river'],
    faqs: [
      { q: 'Is Sutherland Shire bush fire prone?', a: 'Approximately 55% of Sutherland Shire is mapped as bush fire prone land. The Royal National Park dominates the southern boundary, and Heathcote National Park the western edge.' },
      { q: 'What happened during the 2019–20 bushfires in Sutherland?', a: 'The Royal National Park burned extensively, with fires reaching the edges of suburbs including Bundeena. This led to updated BFPL mapping.' },
      { q: 'Does bushfire status affect insurance in Sutherland?', a: 'Yes. Properties in bush fire prone areas typically face higher premiums. Some insurers apply exclusions for BAL-40 or BAL-FZ ratings.' },
    ],
  },
  {
    name: 'Georges River',
    slug: 'georges-river',
    bfplCoveragePct: 10,
    dominantVegetation: ['Eucalypt forest', 'Coastal heath'],
    relatedSlugs: ['sutherland-shire', 'bayside', 'canterbury-bankstown'],
    faqs: [
      { q: 'Is Georges River bush fire prone?', a: 'Approximately 10% of Georges River LGA is mapped as bush fire prone land. Affected areas are primarily along the Georges River and near remnant bushland in Oatley, Lugarno, and Peakhurst Heights.' },
      { q: 'Do I need a BAL assessment in Georges River?', a: 'Only if your property is on mapped BFPL. Most properties — particularly in Hurstville, Kogarah, and Mortdale — are not affected.' },
      { q: 'Does bushfire affect granny flat eligibility in Georges River?', a: 'For the small proportion on BFPL, the CDC pathway still applies but requires compliance with Planning for Bush Fire Protection 2019. Most exclusions relate to lot size or strata.' },
    ],
  },
  {
    name: 'Canterbury-Bankstown',
    slug: 'canterbury-bankstown',
    bfplCoveragePct: 8,
    dominantVegetation: ['Cumberland Plain woodland', 'Riparian'],
    relatedSlugs: ['georges-river', 'liverpool', 'inner-west'],
    faqs: [
      { q: 'Is Canterbury-Bankstown bush fire prone?', a: 'About 8% is mapped as bush fire prone land. Affected areas are primarily along creek corridors, near Salt Pan Creek Reserve, and around remnant bushland in the south-western suburbs.' },
      { q: 'What areas are on BFPL?', a: 'Properties near Salt Pan Creek (Padstow, Revesby), the Georges River (East Hills, Panania), and remnant bushland in Milperra are most likely to be on BFPL.' },
      { q: 'Does low BFPL coverage mean I can ignore bushfire?', a: 'If your property is not on mapped BFPL, bushfire standards do not apply. But if it IS mapped — even in a vegetation buffer zone — all requirements apply. Always check your specific address.' },
    ],
  },
  // ── Greater Sydney — Blue Mountains & surrounds ────────────────────
  {
    name: 'Blue Mountains',
    slug: 'blue-mountains',
    bfplCoveragePct: 95,
    dominantVegetation: ['Eucalypt forest', 'Woodland', 'Heath'],
    relatedSlugs: ['hawkesbury', 'penrith'],
    faqs: [
      { q: 'How much of the Blue Mountains is bush fire prone land?', a: 'Approximately 95% of the Blue Mountains LGA is mapped as bush fire prone land — one of the highest proportions in metropolitan NSW.' },
      { q: 'What BAL rating should I expect in the Blue Mountains?', a: 'BAL ratings typically range from BAL-12.5 to BAL-FZ depending on slope, aspect, and distance to vegetation. Properties adjacent to national park boundaries frequently receive BAL-29 or BAL-40.' },
      { q: 'Do I need RFS approval to build in the Blue Mountains?', a: 'Development on bush fire prone land requires a Bush Fire Safety Authority from the NSW RFS under section 4.14 of the EP&A Act. Processing typically takes 40 business days.' },
      { q: 'What are the extra building costs for bushfire in the Blue Mountains?', a: 'AS 3959 construction standards apply. At BAL-12.5, costs are modest (ember protection). At BAL-29+, costs increase significantly — non-combustible cladding, tempered glass, steel shutters. Budget $15,000–$50,000 depending on BAL rating.' },
    ],
  },
  // ── Regional NSW ───────────────────────────────────────────────────
  {
    name: 'Wollongong',
    slug: 'wollongong',
    bfplCoveragePct: 50,
    dominantVegetation: ['Eucalypt forest', 'Rainforest', 'Heath'],
    relatedSlugs: ['sutherland-shire', 'wingecarribee', 'shoalhaven'],
    faqs: [
      { q: 'How much of Wollongong is bush fire prone?', a: 'Approximately 50%. The Illawarra Escarpment forms a continuous bushfire interface along the western edge of the city.' },
      { q: 'Does the Illawarra Escarpment increase BAL ratings?', a: 'Yes. The steep slope significantly increases BAL ratings. Properties at the escarpment base can receive BAL-40 or BAL-FZ.' },
      { q: 'Can I build on the Illawarra Escarpment?', a: 'Development faces multiple constraints: bushfire, geotechnical stability, and biodiversity. Wollongong DCP Chapter E13 provides specific guidance.' },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    bfplCoveragePct: 80,
    dominantVegetation: ['Eucalypt forest', 'Woodland', 'Rainforest'],
    relatedSlugs: ['campbelltown', 'shoalhaven', 'wollongong'],
    faqs: [
      { q: 'How much of Wingecarribee is bush fire prone?', a: 'Approximately 80%. The Southern Highlands is surrounded by Morton, Kangaroo Valley, and Nattai national parks.' },
      { q: 'What happened during the 2019–20 bushfires?', a: 'The Green Wattle Creek and Morton fires significantly impacted Wingecarribee, with Bundanoon, Wingello, and surrounding villages directly threatened.' },
      { q: 'Is bushfire a concern when buying in the Southern Highlands?', a: 'Yes. Section 10.7 certificates disclose BFPL status. Buyers should check BAL ratings before purchase, as high ratings affect construction costs and insurance.' },
    ],
  },
  {
    name: 'Shoalhaven',
    slug: 'shoalhaven',
    bfplCoveragePct: 85,
    dominantVegetation: ['Eucalypt forest', 'Coastal heath', 'Rainforest'],
    relatedSlugs: ['wingecarribee', 'wollongong'],
    faqs: [
      { q: 'How much of Shoalhaven is bush fire prone?', a: 'Approximately 85% — one of the most bushfire-affected LGAs in NSW. Bordered by Morton National Park and extensive state forests.' },
      { q: 'What happened in the 2019–20 Shoalhaven bushfires?', a: 'The Currowan Fire burned over 500,000 hectares. Villages including Conjola Park, Sussex Inlet, and Lake Tabourie experienced significant property losses.' },
      { q: 'Can I subdivide bushfire prone land in Shoalhaven?', a: 'Subdivision on BFPL requires RFS referral and compliance with Planning for Bush Fire Protection 2019. Asset protection zones, access, and water supply requirements apply.' },
    ],
  },
  {
    name: 'Clarence Valley',
    slug: 'clarence-valley',
    bfplCoveragePct: 70,
    dominantVegetation: ['Eucalypt forest', 'Rainforest', 'Wet sclerophyll'],
    relatedSlugs: ['yass-valley', 'tamworth-regional'],
    faqs: [
      { q: 'How much of Clarence Valley is bush fire prone?', a: 'Approximately 70%. Extensive state forests and national parks surround the area. Towns including Grafton outskirts and Yamba surrounds are affected.' },
      { q: 'Does flood and bushfire overlap in Clarence Valley?', a: 'Yes. The 2019–20 fires and subsequent 2021–22 floods demonstrated both risks in quick succession.' },
      { q: 'What BAL ratings are common?', a: 'Rural properties frequently receive BAL-19 to BAL-40. Properties in Grafton urban area are generally less affected.' },
    ],
  },
  {
    name: 'Yass Valley',
    slug: 'yass-valley',
    bfplCoveragePct: 65,
    dominantVegetation: ['Woodland', 'Dry sclerophyll', 'Grassland'],
    relatedSlugs: ['bathurst-regional', 'clarence-valley'],
    faqs: [
      { q: 'How much of Yass Valley is bush fire prone?', a: 'Approximately 65%. Extensive woodland and dry sclerophyll forest are the main vegetation types.' },
      { q: 'Were the 2019–20 bushfires significant in Yass Valley?', a: 'Yes. Parts were affected, particularly southern areas near Wee Jasper and the Brindabella Ranges. The proximity to the ACT heightened awareness.' },
      { q: 'What BAL ratings are common around Murrumbateman?', a: 'Properties in the village are generally BAL-LOW, but surrounding rural-residential lots frequently receive BAL-12.5 to BAL-29.' },
    ],
  },
  {
    name: 'Forbes',
    slug: 'forbes',
    bfplCoveragePct: 15,
    dominantVegetation: ['Woodland', 'Grassland'],
    relatedSlugs: ['bathurst-regional'],
    faqs: [
      { q: 'Is Forbes bush fire prone?', a: 'About 15%. The area is predominantly flat agricultural land. BFPL mapping applies mainly to remnant woodland patches and along creek corridors.' },
      { q: 'Does flood or bushfire affect Forbes more?', a: 'Forbes is historically more affected by flooding (Lachlan River). However, BFPL mapping does exist on woodland areas.' },
    ],
  },
  {
    name: 'Tamworth Regional',
    slug: 'tamworth-regional',
    bfplCoveragePct: 35,
    dominantVegetation: ['Woodland', 'Dry sclerophyll', 'Grassland'],
    relatedSlugs: ['bathurst-regional', 'clarence-valley'],
    faqs: [
      { q: 'How much of Tamworth is bush fire prone?', a: 'Approximately 35%. The eastern ranges and areas near state forests are most affected. Properties in Tamworth city centre are generally not on BFPL.' },
      { q: 'What vegetation creates bushfire risk?', a: 'Dry sclerophyll woodland and eucalypt forest on the eastern slopes are the main vegetation types driving BFPL mapping.' },
      { q: 'What BAL ratings are common?', a: 'BAL-LOW in urban areas to BAL-19 to BAL-29 on rural-residential properties near woodland. The relatively gentle terrain keeps ratings lower.' },
    ],
  },
  {
    name: 'Bathurst Regional',
    slug: 'bathurst-regional',
    bfplCoveragePct: 40,
    dominantVegetation: ['Woodland', 'Dry sclerophyll', 'Box-gum woodland'],
    relatedSlugs: ['yass-valley', 'forbes', 'tamworth-regional'],
    faqs: [
      { q: 'How much of Bathurst is bush fire prone?', a: 'Approximately 40%. State forests and woodland in the surrounding hills create BFPL mapping. Properties in Bathurst city are generally not on BFPL.' },
      { q: 'What vegetation creates bushfire risk?', a: 'Box-gum woodland (White Box-Yellow Box-Blakely\'s Red Gum) is significant. This critically endangered ecological community restricts vegetation clearing.' },
      { q: 'What BAL ratings are common?', a: 'City properties are generally not on BFPL. Rural-residential properties receive BAL-12.5 to BAL-29 depending on proximity to woodland and slope.' },
    ],
  },
]

export const BUSHFIRE_LGA_SLUG_MAP: Record<string, BushfireLgaData> = Object.fromEntries(
  BUSHFIRE_LGAS.map(lga => [lga.slug, lga])
)
