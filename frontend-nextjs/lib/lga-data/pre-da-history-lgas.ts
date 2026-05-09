export interface PreDaHistoryLgaData {
  name: string
  slug: string
  /** Key risk factors for site history in this LGA */
  riskFactors: string[]
  /** Related LGA slugs for "also check" links */
  relatedSlugs: string[]
  faqs: Array<{ q: string; a: string }>
}

export const PRE_DA_HISTORY_LGAS: PreDaHistoryLgaData[] = [
  // ── Greater Sydney — Inner & East ──────────────────────────────────
  {
    name: 'Inner West',
    slug: 'inner-west',
    riskFactors: ['Heritage conservation areas', 'Terrace house alterations', 'Flood-affected creek lines'],
    relatedSlugs: ['bayside', 'canterbury-bankstown', 'lane-cove'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in the Inner West?',
        a: 'The Inner West has 2,039 heritage items and extensive conservation areas. Unapproved alterations to heritage terraces — rear extensions, roof modifications, facade changes — are common and can surface during DA assessment. A site history report reveals satellite-detected changes and past DA activity before you lodge.',
      },
      {
        q: 'What kind of unapproved works are common in the Inner West?',
        a: 'Rear extensions without consent, converted attics, enclosed verandahs, and unpermitted granny flats are the most common issues. Satellite imagery can detect significant footprint changes over the past eight years, and DA records show whether council approved the work.',
      },
      {
        q: 'Does flood history appear in the Inner West site history report?',
        a: 'Yes. Properties near creek lines in Marrickville, Leichhardt, and Ashfield may show flood event annotations from Copernicus Emergency Management Service data. These events are cross-referenced with DA records to identify post-flood repair works.',
      },
      {
        q: 'How far back does the satellite imagery go?',
        a: 'The report analyses approximately eight years of Sentinel-2 satellite imagery (from 2017 onwards). This captures most recent development activity, vegetation changes, and physical alterations visible from above.',
      },
    ],
  },
  {
    name: 'Bayside',
    slug: 'bayside',
    riskFactors: ['Airport proximity', 'Industrial remediation', 'Coastal erosion'],
    relatedSlugs: ['randwick', 'georges-river', 'canterbury-bankstown'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Bayside?',
        a: 'Bayside includes former industrial areas around Botany Bay and Mascot that may have contamination history. Satellite change detection can reveal land remediation activity, fill operations, and changes to site conditions that affect DA requirements.',
      },
      {
        q: 'Does the report show contamination history?',
        a: 'The report does not directly test for contamination, but satellite-detected earthworks, vegetation die-off patterns, and cross-referenced DA records can indicate remediation activity. Properties near Botany Industrial Park and former landfill sites should check their site history.',
      },
      {
        q: 'What DA activity is common in Bayside?',
        a: 'Bayside has significant redevelopment activity — particularly in Mascot, Arncliffe, and Wolli Creek. The report shows nearby DA and CDC applications within a configurable radius, helping you understand the development context around your site.',
      },
      {
        q: 'How does the report help with a DA in Bayside?',
        a: 'Understanding what council already knows about your site — past approvals, refusals, modifications, and physical changes — helps you anticipate issues before lodging. This is particularly important in Bayside where contamination, aircraft noise, and heritage can create unexpected constraints.',
      },
    ],
  },
  {
    name: 'Randwick',
    slug: 'randwick',
    riskFactors: ['Heritage items', 'Coastal hazard', 'University precinct development'],
    relatedSlugs: ['bayside', 'waverley', 'woollahra'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Randwick?',
        a: 'Randwick has significant heritage constraints, coastal hazard areas, and active development precincts near UNSW and the hospitals. Understanding past site activity and DA history helps identify potential issues before you lodge your own application.',
      },
      {
        q: 'What does satellite imagery reveal in Randwick?',
        a: 'Satellite change detection can show building footprint changes, vegetation clearing, construction activity, and land disturbance. In Randwick, this is particularly useful for identifying unapproved rear additions and changes to properties in heritage conservation areas.',
      },
      {
        q: 'Does the report cover nearby development?',
        a: 'Yes. The report includes DA and CDC applications from the NSW ePlanning Portal within a configurable radius of your address. This helps you understand the development context — what has been approved, refused, or is under assessment nearby.',
      },
    ],
  },
  {
    name: 'Waverley',
    slug: 'waverley',
    riskFactors: ['Heritage conservation areas', 'Coastal hazard', 'High-density redevelopment'],
    relatedSlugs: ['randwick', 'woollahra'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Waverley?',
        a: 'Waverley has extensive heritage conservation areas and high property values that incentivise unapproved works. Satellite imagery and DA records can reveal whether previous owners made changes without council approval — a risk factor for your own DA.',
      },
      {
        q: 'What risks does a site history report identify in Waverley?',
        a: 'Common issues include unapproved extensions, non-compliant pool installations, vegetation removal in tree preservation areas, and building work inconsistent with heritage guidelines. The report flags satellite-detected physical changes and cross-references them with DA records.',
      },
      {
        q: 'Does coastal hazard history appear?',
        a: 'Properties in coastal hazard zones may show relevant annotations. The report cross-references natural disaster events and council records to provide context about site history related to coastal processes.',
      },
    ],
  },
  {
    name: 'Woollahra',
    slug: 'woollahra',
    riskFactors: ['Heritage density', 'Tree preservation', 'Harbour foreshore'],
    relatedSlugs: ['waverley', 'randwick'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Woollahra?',
        a: 'Woollahra has one of the highest heritage item densities in Sydney. Council actively enforces heritage controls, and DA assessors will check site history for inconsistencies between approved plans and actual site conditions. Knowing this before you lodge gives you time to address issues.',
      },
      {
        q: 'What does satellite imagery show in Woollahra?',
        a: 'Significant tree canopy changes, building footprint modifications, pool installations, and garden restructuring are all detectable. Woollahra Council\'s tree preservation order is strictly enforced — satellite evidence of tree removal can create issues for future DAs.',
      },
      {
        q: 'How does site history affect DA outcomes in Woollahra?',
        a: 'Woollahra Council is known for thorough DA assessment. If site conditions don\'t match approved plans from previous applications, council may require rectification before considering your new DA. A site history report helps you identify these issues proactively.',
      },
    ],
  },
  // ── Greater Sydney — North ─────────────────────────────────────────
  {
    name: 'Northern Beaches',
    slug: 'northern-beaches',
    riskFactors: ['Bushfire-affected sites', 'Environmentally sensitive land', 'Coastal hazard'],
    relatedSlugs: ['ku-ring-gai', 'hornsby', 'lane-cove'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check on the Northern Beaches?',
        a: 'The Northern Beaches has significant environmental constraints — bushfire, biodiversity, coastal hazard, and landslip. A site history report reveals past DA activity, satellite-detected land disturbance, and natural disaster events that affect what you can build.',
      },
      {
        q: 'Does the report show bushfire damage history?',
        a: 'The report cross-references satellite imagery with natural disaster event data. Properties in bushfire-affected areas (Ingleside, Terrey Hills, Belrose) may show fire scar annotations and subsequent rebuilding activity.',
      },
      {
        q: 'What vegetation changes are important on the Northern Beaches?',
        a: 'Vegetation clearing without approval is a significant issue in the Northern Beaches, where biodiversity offsets can be very expensive. Satellite imagery can detect canopy loss over the past eight years, and DA records show whether clearing was approved.',
      },
    ],
  },
  {
    name: 'Ku-ring-gai',
    slug: 'ku-ring-gai',
    riskFactors: ['Tree canopy loss', 'Heritage conservation areas', 'Bushfire rebuilds'],
    relatedSlugs: ['hornsby', 'northern-beaches', 'ryde'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Ku-ring-gai?',
        a: 'Ku-ring-gai Council is one of NSW\'s strictest on tree preservation and heritage. Satellite imagery can detect canopy loss that may indicate unapproved tree removal — a serious issue that can delay or derail your DA.',
      },
      {
        q: 'Does tree canopy change show in the report?',
        a: 'Yes. Sentinel-2 satellite imagery detects significant vegetation change over eight years. In Ku-ring-gai, where mature tree canopy is a key planning consideration, this data can reveal whether trees were removed without approval and whether replanting obligations exist.',
      },
      {
        q: 'What DA patterns are common in Ku-ring-gai?',
        a: 'Ku-ring-gai has high rates of DA activity for renovations, additions, and dual occupancies. The report shows nearby DA history within a configurable radius, helping you understand council\'s assessment approach and common conditions applied in your area.',
      },
      {
        q: 'Does bushfire history affect DAs in Ku-ring-gai?',
        a: 'Properties damaged in bushfire events may have post-fire rebuilding DAs on record. The site history report cross-references fire event data with DA records to provide a complete picture of the site\'s recent history.',
      },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    riskFactors: ['Bushfire interface', 'Steep terrain', 'Vegetation clearing'],
    relatedSlugs: ['ku-ring-gai', 'the-hills-shire', 'northern-beaches'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Hornsby?',
        a: 'Hornsby Shire has extensive bushfire-prone land, steep terrain, and environmental constraints. A site history report reveals whether previous owners cleared vegetation, lodged DAs that were refused, or made changes that affect your development potential.',
      },
      {
        q: 'What terrain issues does the report highlight?',
        a: 'Satellite-detected earthworks, retaining wall construction, and land disturbance on steep sites can indicate geotechnical issues. In Hornsby\'s hilly terrain, this context is valuable before designing a development and commissioning geotechnical reports.',
      },
      {
        q: 'Does the report show refused DAs in Hornsby?',
        a: 'Yes. DA records from the NSW ePlanning Portal include approvals, refusals, and modifications. Knowing that a previous DA was refused on your site — and why — helps you avoid the same outcome.',
      },
    ],
  },
  {
    name: 'Lane Cove',
    slug: 'lane-cove',
    riskFactors: ['National park interface', 'Heritage items', 'Medium-density transition'],
    relatedSlugs: ['ryde', 'ku-ring-gai', 'inner-west'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Lane Cove?',
        a: 'Lane Cove is transitioning from low to medium density in some areas, creating significant DA activity. Understanding the development context — what has been approved, refused, or built nearby — helps you design a compliant application.',
      },
      {
        q: 'What does satellite imagery show in Lane Cove?',
        a: 'Building footprint changes, demolition activity, and vegetation changes near Lane Cove National Park are all detectable. The report provides a timeline of physical changes visible from satellite imagery over the past eight years.',
      },
      {
        q: 'How does nearby DA activity affect my application?',
        a: 'Precedent matters. If similar developments have been approved on nearby sites, it strengthens your case. If they have been refused, you need to understand why. The site history report provides this context.',
      },
    ],
  },
  {
    name: 'Ryde',
    slug: 'ryde',
    riskFactors: ['Redevelopment precincts', 'Heritage items', 'Flood-affected areas'],
    relatedSlugs: ['lane-cove', 'ku-ring-gai', 'parramatta'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Ryde?',
        a: 'Ryde has active redevelopment precincts around Macquarie Park and Top Ryde. Understanding DA history, past approvals, and site changes helps you navigate a complex planning environment.',
      },
      {
        q: 'What development trends does the report show in Ryde?',
        a: 'The report shows DA and CDC activity near your address, revealing development trends. In Ryde, this often shows medium-density infill, knock-down rebuilds, and commercial-to-residential conversions.',
      },
      {
        q: 'Does flood history show in Ryde site history reports?',
        a: 'Properties near the Parramatta River and Lane Cove River may show flood event annotations. The report cross-references satellite imagery with emergency management data to identify flood-affected periods.',
      },
    ],
  },
  // ── Greater Sydney — West ──────────────────────────────────────────
  {
    name: 'Parramatta',
    slug: 'parramatta',
    riskFactors: ['Major redevelopment', 'Heritage conservation', 'Flood risk'],
    relatedSlugs: ['blacktown', 'ryde', 'the-hills-shire'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Parramatta?',
        a: 'Parramatta is undergoing massive urban transformation. Understanding the DA history of your site and surrounds is critical — previous approvals, demolition orders, and council conditions all affect what you can build next.',
      },
      {
        q: 'Does the report show heritage constraints in Parramatta?',
        a: 'The report cross-references heritage overlay data. Parramatta has 803 heritage items, including significant colonial-era sites. Heritage status and past heritage-related DA conditions are surfaced in the report.',
      },
      {
        q: 'How does flood history affect DAs in Parramatta?',
        a: 'Properties in the Parramatta River flood plain may show flood event annotations. Past flood-related DA conditions, flood studies referenced in previous approvals, and physical changes after flood events are all relevant context for a new DA.',
      },
      {
        q: 'What does satellite imagery reveal in Parramatta?',
        a: 'Demolition activity, construction timelines, vegetation changes, and large-scale earthworks are all visible. In Parramatta\'s fast-changing landscape, satellite imagery provides an objective record of what has happened on and around your site.',
      },
    ],
  },
  {
    name: 'Blacktown',
    slug: 'blacktown',
    riskFactors: ['New release areas', 'Fill operations', 'Vegetation clearing'],
    relatedSlugs: ['the-hills-shire', 'penrith', 'parramatta'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Blacktown?',
        a: 'Blacktown includes both established suburbs and new release areas. In new estates, understanding fill history, previous land use, and site preparation activity helps identify potential issues. In established areas, unapproved works on older properties can create complications.',
      },
      {
        q: 'Does the report show fill operations?',
        a: 'Satellite imagery can detect significant earthworks and fill operations, which are common in Blacktown\'s new release areas. Properties built on filled land may face geotechnical issues that affect development applications.',
      },
      {
        q: 'What DA patterns are common in Blacktown?',
        a: 'Blacktown has high rates of granny flat CDCs and dual occupancy DAs. The report shows nearby approval patterns, helping you understand what council typically approves in your area.',
      },
    ],
  },
  {
    name: 'The Hills Shire',
    slug: 'the-hills-shire',
    riskFactors: ['Rural-to-urban transition', 'Bushfire history', 'Heritage homesteads'],
    relatedSlugs: ['hornsby', 'blacktown', 'hawkesbury'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in The Hills?',
        a: 'The Hills Shire spans urban, suburban, and rural-residential zones. Site history is particularly important for rural-residential properties where unapproved sheds, cleared vegetation, and informal structures may exist without DA records.',
      },
      {
        q: 'What does satellite imagery show in The Hills?',
        a: 'On large rural-residential lots, satellite imagery can detect shed construction, dam works, vegetation clearing, and earthworks that may not have council approval. This is critical context before lodging your own DA.',
      },
      {
        q: 'How does development history affect The Hills properties?',
        a: 'Properties transitioning from rural to residential use often have complex DA histories. Previous approvals may have conditions about vegetation retention, access, or bushfire protection that carry forward to new development.',
      },
    ],
  },
  {
    name: 'Penrith',
    slug: 'penrith',
    riskFactors: ['Flood and bushfire overlap', 'New release areas', 'Industrial transition'],
    relatedSlugs: ['blue-mountains', 'hawkesbury', 'blacktown'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Penrith?',
        a: 'Penrith has dual natural hazard exposure (flood and bushfire) and significant development activity in new release areas and industrial transition zones. Site history reveals past approvals, natural disaster events, and physical changes that inform your DA strategy.',
      },
      {
        q: 'Does the report show flood and fire history in Penrith?',
        a: 'Yes. The report cross-references satellite imagery with Copernicus Emergency Management data and other event records. Properties along the Nepean River and near the Blue Mountains boundary may show both flood and fire event annotations.',
      },
      {
        q: 'What development patterns does the report reveal in Penrith?',
        a: 'Penrith has high rates of new dwelling construction, granny flat CDCs, and industrial-to-residential conversions. The report shows DA activity near your address, revealing development trends and council assessment patterns.',
      },
    ],
  },
  {
    name: 'Hawkesbury',
    slug: 'hawkesbury',
    riskFactors: ['Extreme flood risk', 'Heritage significance', 'Bushfire history'],
    relatedSlugs: ['penrith', 'the-hills-shire', 'blue-mountains'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Hawkesbury?',
        a: 'Hawkesbury has extreme natural hazard exposure — flood and bushfire. Understanding your site\'s history with these events, plus any past DA activity and conditions, is essential before lodging a new application.',
      },
      {
        q: 'Does the report show flood event history in Hawkesbury?',
        a: 'Yes. The Hawkesbury-Nepean has had major flood events in recent years. The report shows satellite-detected inundation, post-flood repair activity, and cross-references with DA records for flood-related approvals.',
      },
      {
        q: 'What heritage issues affect Hawkesbury DAs?',
        a: 'Hawkesbury has 604 heritage items including colonial-era properties around Windsor and Richmond. The report flags heritage status and shows any heritage-related DA history for your site, helping you anticipate heritage assessment requirements.',
      },
    ],
  },
  // ── Greater Sydney — South & Southwest ─────────────────────────────
  {
    name: 'Campbelltown',
    slug: 'campbelltown',
    riskFactors: ['Bushfire interface', 'New release areas', 'Flood-affected corridors'],
    relatedSlugs: ['camden', 'liverpool', 'sutherland-shire'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Campbelltown?',
        a: 'Campbelltown has both established suburbs with potential unapproved works and new release areas where site preparation history matters. The report reveals DA activity, satellite-detected changes, and natural hazard event history.',
      },
      {
        q: 'What does satellite imagery show in Campbelltown?',
        a: 'Building construction timelines, vegetation clearing (particularly near Dharawal NP), earthworks in new estates, and changes to established properties are all visible over the eight-year imagery period.',
      },
      {
        q: 'Does bushfire event history appear?',
        a: 'Yes. Properties near Dharawal National Park and Georges River bushland may show fire scar annotations from the 2019–20 season. Post-fire rebuilding DA activity is also cross-referenced.',
      },
    ],
  },
  {
    name: 'Camden',
    slug: 'camden',
    riskFactors: ['Rapid greenfield development', 'Agricultural transition', 'Fill operations'],
    relatedSlugs: ['campbelltown', 'liverpool', 'wollongong'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Camden?',
        a: 'Camden is one of NSW\'s fastest-growing LGAs, with extensive greenfield development. Understanding the development history of your site — including fill operations, previous land use, and nearby DA activity — is critical context for a new application.',
      },
      {
        q: 'What does satellite imagery show in Camden?',
        a: 'The eight-year imagery period captures the dramatic transformation of Camden from rural to suburban. Construction timelines, fill operations, road construction, and vegetation clearing are all visible and provide context about your site\'s development history.',
      },
      {
        q: 'How does nearby DA activity affect my Camden application?',
        a: 'In new release areas, nearby DA approvals establish precedent for building form, height, and setbacks. The report shows what council has approved in your area, helping you design a compliant application.',
      },
    ],
  },
  {
    name: 'Liverpool',
    slug: 'liverpool',
    riskFactors: ['Industrial remediation', 'Flood risk', 'Defence land interface'],
    relatedSlugs: ['campbelltown', 'canterbury-bankstown', 'camden'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Liverpool?',
        a: 'Liverpool has industrial transition areas, flood-affected land along the Georges River, and land near Holsworthy Military Reserve. Site history reveals contamination-related DA conditions, flood event impacts, and development patterns that affect your application.',
      },
      {
        q: 'Does the report show industrial history?',
        a: 'Satellite imagery can detect industrial activity, remediation earthworks, and land use changes. In Liverpool\'s industrial areas transitioning to residential, understanding site history is essential for addressing contamination assessment requirements.',
      },
      {
        q: 'How does flood history affect Liverpool DAs?',
        a: 'Properties along the Georges River may show flood event annotations. Previous flood-related DA conditions and flood study references provide context for your own application\'s flood assessment requirements.',
      },
    ],
  },
  {
    name: 'Sutherland Shire',
    slug: 'sutherland-shire',
    riskFactors: ['Bushfire history', 'National park interface', 'Coastal hazard'],
    relatedSlugs: ['wollongong', 'campbelltown', 'georges-river'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Sutherland Shire?',
        a: 'Sutherland Shire has significant bushfire history (2019–20 Royal NP fires), coastal hazard zones, and properties interfacing with national parks. Understanding past site events, DA history, and physical changes is critical context for new development.',
      },
      {
        q: 'Does the report show the 2019–20 fire impacts?',
        a: 'Yes. Properties near Royal National Park and Heathcote National Park may show fire scar annotations from Sentinel-2 satellite imagery. Post-fire rebuilding activity and related DA records are cross-referenced.',
      },
      {
        q: 'What unapproved works are common in Sutherland?',
        a: 'Deck extensions, pool installations, tree removal, and bushland clearing are common unapproved works detected through satellite change analysis. In Sutherland, where properties back onto national parks, these issues can be particularly sensitive.',
      },
    ],
  },
  {
    name: 'Georges River',
    slug: 'georges-river',
    riskFactors: ['Heritage conservation', 'Medium-density transition', 'Riparian corridors'],
    relatedSlugs: ['sutherland-shire', 'bayside', 'canterbury-bankstown'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Georges River?',
        a: 'Georges River Council is actively managing medium-density transition in suburbs like Hurstville, Kogarah, and Penshurst. Understanding what has been approved, refused, and built nearby helps you design a compliant application.',
      },
      {
        q: 'What development patterns does the report show?',
        a: 'The report reveals DA trends — townhouse approvals, dual occupancy patterns, and apartment development activity near your address. This context is valuable for understanding what council is likely to approve.',
      },
      {
        q: 'Does vegetation change matter in Georges River?',
        a: 'Yes. Properties near the Georges River and bushland reserves are subject to biodiversity and vegetation controls. Satellite-detected canopy loss can indicate clearing that may need to be addressed in your DA.',
      },
    ],
  },
  {
    name: 'Canterbury-Bankstown',
    slug: 'canterbury-bankstown',
    riskFactors: ['Industrial transition', 'Flood risk', 'Rapid densification'],
    relatedSlugs: ['georges-river', 'liverpool', 'inner-west'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Canterbury-Bankstown?',
        a: 'Canterbury-Bankstown has significant redevelopment activity and industrial-to-residential transition areas. Understanding past site use, DA history, and development trends helps you navigate the planning process.',
      },
      {
        q: 'What does satellite imagery reveal in Canterbury-Bankstown?',
        a: 'Demolition activity, construction timelines, earthworks, and vegetation changes are all detectable. In areas transitioning from industrial to residential, satellite imagery provides an objective record of site changes.',
      },
      {
        q: 'How does nearby DA activity help my application?',
        a: 'Canterbury-Bankstown has high DA volumes. The report shows what has been approved, refused, and conditioned near your address — valuable precedent for designing your own application.',
      },
    ],
  },
  // ── Greater Sydney — Blue Mountains & surrounds ────────────────────
  {
    name: 'Blue Mountains',
    slug: 'blue-mountains',
    riskFactors: ['Bushfire history', 'Environmental sensitivity', 'Heritage villages'],
    relatedSlugs: ['hawkesbury', 'penrith'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in the Blue Mountains?',
        a: 'The Blue Mountains has extreme bushfire history, sensitive environmental areas, and heritage village character. Understanding past fire events, vegetation changes, DA history, and heritage constraints is essential before lodging any application.',
      },
      {
        q: 'Does the report show the 2019–20 fire impacts?',
        a: 'Yes. Satellite imagery captures fire scars from the 2019–20 season across the Blue Mountains. Post-fire rebuilding activity, emergency DA approvals, and vegetation recovery are all visible in the eight-year imagery timeline.',
      },
      {
        q: 'What heritage issues affect Blue Mountains DAs?',
        a: 'The Blue Mountains has heritage conservation areas in most villages. The report flags heritage status and shows any heritage-related DA history, helping you anticipate assessment requirements for alterations and additions.',
      },
      {
        q: 'Does environmental sensitivity show in the report?',
        a: 'The report shows vegetation change over time. In the Blue Mountains, where biodiversity offsets can be very expensive and vegetation clearing is tightly regulated, this data helps you understand what has changed on your site and whether it was approved.',
      },
    ],
  },
  // ── Regional NSW ───────────────────────────────────────────────────
  {
    name: 'Wollongong',
    slug: 'wollongong',
    riskFactors: ['Escarpment instability', 'Coal mine subsidence', 'Coastal hazard'],
    relatedSlugs: ['sutherland-shire', 'wingecarribee', 'shoalhaven'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Wollongong?',
        a: 'Wollongong has unique geotechnical constraints — escarpment instability and coal mine subsidence — plus coastal hazard and bushfire. Site history reveals past land disturbance, DA conditions related to geotechnical risk, and physical changes that affect development potential.',
      },
      {
        q: 'Does the report show mine subsidence history?',
        a: 'The report does not directly assess mine subsidence, but satellite-detected ground disturbance and cross-referenced DA records may reveal subsidence-related conditions on past approvals. Properties in Subsidence Advisory Areas should check site history.',
      },
      {
        q: 'What does satellite imagery show on the escarpment?',
        a: 'Landslip activity, vegetation changes, and earthworks on and near the Illawarra Escarpment are visible in satellite imagery. This context is valuable for properties in areas subject to geotechnical assessment requirements.',
      },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    riskFactors: ['Bushfire recovery', 'Heritage villages', 'Rural-residential'],
    relatedSlugs: ['campbelltown', 'shoalhaven', 'wollongong'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Wingecarribee?',
        a: 'Wingecarribee was heavily impacted by the 2019–20 bushfires. Understanding fire event history, post-fire DA activity, and site recovery is critical context for new development in the Southern Highlands.',
      },
      {
        q: 'Does the report show fire damage and recovery?',
        a: 'Yes. Satellite imagery captures fire scar extent from the Green Wattle Creek and Morton fires. Vegetation recovery, demolition, and rebuilding activity are visible over the subsequent years.',
      },
      {
        q: 'What heritage issues affect Wingecarribee DAs?',
        a: 'Bowral, Mittagong, and Berrima have significant heritage character. The report flags heritage status and past heritage-related DA conditions, helping you design sympathetic development.',
      },
    ],
  },
  {
    name: 'Shoalhaven',
    slug: 'shoalhaven',
    riskFactors: ['Catastrophic fire history', 'Coastal erosion', 'Flood-fire overlap'],
    relatedSlugs: ['wingecarribee', 'wollongong'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Shoalhaven?',
        a: 'Shoalhaven experienced catastrophic fire in 2019–20 (Currowan Fire) followed by significant flooding. Understanding your site\'s history with these events, plus post-disaster DA activity, is essential context for new development.',
      },
      {
        q: 'Does the report show the Currowan Fire impacts?',
        a: 'Yes. Satellite imagery captures the fire scar from the Currowan Fire (500,000+ hectares). Post-fire rebuilding, emergency DA approvals, and vegetation recovery are all visible in the timeline.',
      },
      {
        q: 'What does the report show for coastal Shoalhaven properties?',
        a: 'Coastal erosion patterns, foreshore changes, and shoreline vegetation changes are visible in satellite imagery. Properties in coastal hazard zones benefit from understanding the physical changes over the past eight years.',
      },
    ],
  },
  {
    name: 'Clarence Valley',
    slug: 'clarence-valley',
    riskFactors: ['Flood-fire sequence', 'Agricultural transition', 'Vegetation clearing'],
    relatedSlugs: ['yass-valley', 'tamworth-regional'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Clarence Valley?',
        a: 'Clarence Valley experienced fires in 2019–20 followed by major flooding in 2021–22. Understanding your site\'s natural disaster history and any post-event DA activity is critical context for new development.',
      },
      {
        q: 'Does the report show flood and fire sequence?',
        a: 'Yes. The eight-year satellite imagery timeline captures both fire scars and flood inundation events. This dual natural hazard history is cross-referenced with DA records to show the full picture of site events.',
      },
      {
        q: 'What vegetation changes matter in Clarence Valley?',
        a: 'Agricultural clearing, forestry activity, and natural disaster impacts on vegetation are all visible. In areas with biodiversity constraints, understanding what vegetation was present before any clearing occurred can affect DA requirements.',
      },
    ],
  },
  {
    name: 'Yass Valley',
    slug: 'yass-valley',
    riskFactors: ['Bushfire proximity to ACT', 'Rural subdivision', 'Woodland clearing'],
    relatedSlugs: ['bathurst-regional', 'clarence-valley'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Yass Valley?',
        a: 'Yass Valley has growing rural-residential development near the ACT border. Understanding site history — past land use, vegetation changes, DA activity, and natural hazard events — helps you navigate the planning process for rural and semi-rural properties.',
      },
      {
        q: 'What does satellite imagery show in Yass Valley?',
        a: 'Farm dam construction, vegetation clearing, shed building, and land disturbance on rural properties are all visible. Many of these activities require DA approval, and satellite evidence of unapproved works can affect your own application.',
      },
      {
        q: 'Does the 2019–20 fire history show?',
        a: 'Yes. Properties near the Brindabella Ranges and areas affected during the 2019–20 season show fire scar annotations. The proximity to the ACT fires that destroyed Orroral Valley is also relevant context.',
      },
    ],
  },
  {
    name: 'Forbes',
    slug: 'forbes',
    riskFactors: ['Flood history', 'Agricultural land use', 'Heritage township'],
    relatedSlugs: ['bathurst-regional'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Forbes?',
        a: 'Forbes is primarily affected by flood risk from the Lachlan River. Understanding flood event history, post-flood repair DA activity, and site changes helps you navigate flood-related development controls.',
      },
      {
        q: 'Does the report show Lachlan River flood events?',
        a: 'Yes. Satellite imagery captures flood inundation events, and the report cross-references with emergency management data. Properties in the Forbes flood plain benefit from understanding the frequency and extent of past inundation.',
      },
      {
        q: 'What heritage issues affect Forbes DAs?',
        a: 'Forbes has a heritage-listed main street and township. The report flags heritage status and any heritage-related DA conditions from past applications on your site.',
      },
    ],
  },
  {
    name: 'Tamworth Regional',
    slug: 'tamworth-regional',
    riskFactors: ['Rural development', 'Woodland clearing', 'Flood-affected areas'],
    relatedSlugs: ['bathurst-regional', 'clarence-valley'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Tamworth?',
        a: 'Tamworth Regional has diverse development — urban infill, rural-residential, and agricultural. Understanding DA history, past land use changes, and any natural hazard events provides context for your application.',
      },
      {
        q: 'What does satellite imagery show around Tamworth?',
        a: 'Construction activity, vegetation clearing, dam building, and agricultural land use changes are all visible. In rural-residential areas, satellite imagery reveals whether previous owners made changes that may require retrospective approval.',
      },
      {
        q: 'Does flood history affect Tamworth DAs?',
        a: 'Properties near the Peel River and its tributaries may show flood event annotations. Past flood-related DA conditions provide context for your application\'s flood assessment requirements.',
      },
    ],
  },
  {
    name: 'Bathurst Regional',
    slug: 'bathurst-regional',
    riskFactors: ['Heritage significance', 'Rural subdivision', 'Mine legacy'],
    relatedSlugs: ['yass-valley', 'forbes', 'tamworth-regional'],
    faqs: [
      {
        q: 'Why run a pre-DA site history check in Bathurst?',
        a: 'Bathurst has significant heritage constraints in the city centre and growing rural-residential development on the outskirts. Understanding site history helps you navigate heritage requirements and identify any past issues that affect your DA.',
      },
      {
        q: 'Does the report show heritage DA history?',
        a: 'Yes. Heritage-related DA conditions from past applications on your site are included. In Bathurst\'s heritage areas, understanding what council has previously approved or conditioned helps you design a sympathetic development.',
      },
      {
        q: 'What does satellite imagery reveal around Bathurst?',
        a: 'Construction activity, vegetation changes, earthworks, and land disturbance are visible over eight years. For rural-residential properties, satellite imagery provides an objective record of changes that may or may not have council approval.',
      },
    ],
  },
]

export const PRE_DA_HISTORY_LGA_SLUG_MAP: Record<string, PreDaHistoryLgaData> = Object.fromEntries(
  PRE_DA_HISTORY_LGAS.map(lga => [lga.slug, lga])
)
