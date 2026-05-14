export interface VerifyLgaData {
  name: string
  slug: string
  /** Has structured DCP controls in the database */
  hasDcpData: boolean
  /** Geographically adjacent LGAs */
  relatedSlugs: string[]
  faqs: Array<{ q: string; a: string }>
}

export const VERIFY_LGAS: VerifyLgaData[] = [
  // ── Greater Sydney — Inner & East ──────────────────────────────────
  {
    name: 'Inner West',
    slug: 'inner-west',
    hasDcpData: true,
    relatedSlugs: ['bayside', 'canterbury-bankstown', 'lane-cove'],
    faqs: [
      { q: 'What planning controls apply to my Inner West property?', a: 'Inner West properties are governed by the Inner West LEP 2022, SEPP Housing 2021, and the Inner West DCP. Controls cover setbacks, height, floor space ratio, parking, landscaping, and heritage conservation areas. Enter your address above for the full breakdown with clause citations.' },
      { q: 'How do I find setback requirements for the Inner West?', a: 'Setback requirements come from the Inner West DCP and vary by zone, lot size, and precinct. Our tool pulls the specific setback controls for your property — front, side, and rear — with the exact DCP clause references.' },
      { q: 'Does the Inner West have precinct-specific controls?', a: 'Yes. The Inner West DCP has precinct-specific controls for areas like Marrickville, Leichhardt, and Ashfield that carried over from the former councils. Controls vary significantly between precincts.' },
    ],
  },
  {
    name: 'Bayside',
    slug: 'bayside',
    hasDcpData: true,
    relatedSlugs: ['randwick', 'georges-river', 'canterbury-bankstown'],
    faqs: [
      { q: 'What planning controls apply in Bayside?', a: 'Bayside properties are governed by the Bayside LEP 2021, SEPP Housing 2021, and the Bayside DCP. Controls cover height, FSR, setbacks, parking, landscaping, and design requirements. Enter your address above for the specific controls with clause citations.' },
      { q: 'How do heritage controls work in Bayside?', a: 'Heritage items and heritage conservation areas in Bayside are listed in the Bayside LEP. Properties within these areas face additional controls on design, materials, and demolition. The tool shows whether your property is heritage-affected.' },
      { q: 'What parking requirements apply in Bayside?', a: 'Parking rates in Bayside come from the DCP and vary by development type and zone. Residential parking rates are typically 1 space per dwelling for 1-2 bedroom units and 2 spaces for 3+ bedroom dwellings. Check your address for the exact applicable rates.' },
    ],
  },
  {
    name: 'Randwick',
    slug: 'randwick',
    hasDcpData: true,
    relatedSlugs: ['bayside', 'waverley', 'woollahra'],
    faqs: [
      { q: 'What planning controls apply in Randwick?', a: 'Randwick properties are governed by the Randwick LEP 2012 and Randwick DCP 2013. Controls cover height, FSR, setbacks, parking, landscaping, and heritage. Enter your address above for the full set of applicable controls.' },
      { q: 'What are the height limits in Randwick?', a: 'Height limits in Randwick vary by zone and are mapped in the LEP Height of Buildings map. Common residential limits range from 8.5m to 12m. The tool pulls the specific limit for your property from the LEP.' },
      { q: 'Does Randwick have specific controls for multi-dwelling housing?', a: 'Yes. The Randwick DCP has detailed controls for multi-dwelling housing including setbacks, communal open space, private open space, solar access, and landscaping requirements.' },
    ],
  },
  {
    name: 'Waverley',
    slug: 'waverley',
    hasDcpData: true,
    relatedSlugs: ['randwick', 'woollahra', 'bayside'],
    faqs: [
      { q: 'What planning controls apply in Waverley?', a: 'Waverley properties are governed by the Waverley LEP 2012 and Waverley DCP 2012. Controls cover height, FSR, setbacks, parking, landscaping, heritage, and foreshore building lines. Enter your address for the specific controls.' },
      { q: 'Are there special controls near Bondi Beach?', a: 'Yes. Properties near Bondi Beach and other coastal areas are subject to additional DCP controls including foreshore building lines, view sharing provisions, and coastal hazard overlays.' },
      { q: 'What heritage controls apply in Waverley?', a: 'Waverley has heritage conservation areas throughout Bondi, Bronte, and Waverley. Heritage items and HCAs are listed in the LEP. Properties within these areas face additional design and demolition controls.' },
    ],
  },
  {
    name: 'Woollahra',
    slug: 'woollahra',
    hasDcpData: true,
    relatedSlugs: ['waverley', 'randwick', 'bayside'],
    faqs: [
      { q: 'What planning controls apply in Woollahra?', a: 'Woollahra properties are governed by the Woollahra LEP 2014 and Woollahra DCP 2015. Controls cover height, FSR, setbacks, parking, landscaping, heritage, and foreshore areas. Enter your address for the specific controls with clause citations.' },
      { q: 'Does Woollahra have view sharing controls?', a: 'Yes. Woollahra DCP includes view sharing provisions (based on the Tenacity Steps test) that affect developments visible from neighbouring properties, particularly in elevated areas of Double Bay, Point Piper, and Vaucluse.' },
      { q: 'What parking requirements apply in Woollahra?', a: 'Parking requirements come from the Woollahra DCP and vary by development type and proximity to transport. Residential parking rates are typically 1-2 spaces per dwelling depending on unit size.' },
    ],
  },
  {
    name: 'City of Sydney',
    slug: 'city-of-sydney',
    hasDcpData: true,
    relatedSlugs: ['inner-west', 'bayside', 'woollahra', 'randwick'],
    faqs: [
      { q: 'What planning controls apply in the City of Sydney?', a: 'City of Sydney properties are governed by the Sydney LEP 2012 and Sydney DCP 2012. Controls cover height, FSR, setbacks, parking, design excellence, heritage, and active frontage requirements. The CBD and surrounds have some of NSW\'s most detailed planning controls.' },
      { q: 'What design excellence requirements apply in the City of Sydney?', a: 'Buildings over a certain height in the City of Sydney require a design excellence process including a competitive design alternatives process. Requirements vary by precinct and building height.' },
      { q: 'What heritage controls apply in the City of Sydney?', a: 'The City of Sydney has extensive heritage conservation areas across Surry Hills, Paddington, Pyrmont, Glebe, and The Rocks. Heritage items and HCAs are mapped in the LEP with detailed DCP controls for each area.' },
    ],
  },
  {
    name: 'Canada Bay',
    slug: 'canada-bay',
    hasDcpData: true,
    relatedSlugs: ['inner-west', 'burwood', 'strathfield', 'ryde'],
    faqs: [
      { q: 'What planning controls apply in Canada Bay?', a: 'Canada Bay properties are governed by the Canada Bay LEP 2013 and Canada Bay DCP. Controls cover height, FSR, setbacks, parking, landscaping, and foreshore areas along the Parramatta River.' },
      { q: 'What foreshore controls apply in Canada Bay?', a: 'Properties near the Parramatta River foreshore are subject to foreshore building line controls. These restrict development within a setback from the foreshore boundary and may include design requirements.' },
      { q: 'What setback requirements apply in Canada Bay?', a: 'Setback requirements come from the Canada Bay DCP and vary by zone and lot width. The tool shows the specific front, side, and rear setback controls for your property.' },
    ],
  },
  {
    name: 'Burwood',
    slug: 'burwood',
    hasDcpData: true,
    relatedSlugs: ['inner-west', 'canada-bay', 'strathfield', 'canterbury-bankstown'],
    faqs: [
      { q: 'What planning controls apply in Burwood?', a: 'Burwood properties are governed by the Burwood LEP 2012 and Burwood DCP. Controls cover height, FSR, setbacks, parking, landscaping, and heritage. Burwood town centre has specific design and density controls.' },
      { q: 'What setback requirements apply in Burwood?', a: 'Setback requirements come from the Burwood DCP and vary by zone and lot width. Typical residential front setbacks apply across most areas. The tool shows the specific controls for your address.' },
      { q: 'What parking requirements apply in Burwood?', a: 'Parking rates come from the Burwood DCP and vary by development type and proximity to Burwood station. Reduced rates may apply in the town centre.' },
    ],
  },
  {
    name: 'Strathfield',
    slug: 'strathfield',
    hasDcpData: true,
    relatedSlugs: ['burwood', 'canada-bay', 'canterbury-bankstown', 'inner-west'],
    faqs: [
      { q: 'What planning controls apply in Strathfield?', a: 'Strathfield properties are governed by the Strathfield LEP 2012 and Strathfield DCP. Controls cover height, FSR, setbacks, parking, landscaping, and heritage. Strathfield has strict tree preservation controls.' },
      { q: 'What heritage controls apply in Strathfield?', a: 'Strathfield has heritage items and heritage conservation areas, particularly in the established residential streets around Strathfield station. Heritage items are listed in the LEP.' },
      { q: 'What setback requirements apply in Strathfield?', a: 'Setback requirements come from the Strathfield DCP and vary by zone. The tool shows the specific front, side, and rear setback controls for your property with DCP clause references.' },
    ],
  },
  // ── Greater Sydney — North ─────────────────────────────────────────
  {
    name: 'Northern Beaches',
    slug: 'northern-beaches',
    hasDcpData: true,
    relatedSlugs: ['ku-ring-gai', 'lane-cove', 'hornsby'],
    faqs: [
      { q: 'What planning controls apply on the Northern Beaches?', a: 'Northern Beaches properties are governed by the Northern Beaches LEP 2014, Manly LEP 2013, Pittwater LEP 2014, and the consolidated DCP. Controls vary by which former council area your property is in — Warringah, Manly, or Pittwater.' },
      { q: 'Do different parts of the Northern Beaches have different controls?', a: 'Yes. The Northern Beaches was formed from Warringah, Manly, and Pittwater councils. Each former council area has different LEP and DCP controls until the council completes its consolidated LEP. The tool identifies which set of controls applies to your address.' },
      { q: 'What bushfire controls apply on the Northern Beaches?', a: 'Parts of the Northern Beaches are mapped as Bush Fire Prone Land, particularly in the Pittwater and Warringah areas. Properties on BFPL require BAL assessment and AS 3959 compliance for any new building work.' },
    ],
  },
  {
    name: 'Ku-ring-gai',
    slug: 'ku-ring-gai',
    hasDcpData: true,
    relatedSlugs: ['hornsby', 'northern-beaches', 'lane-cove'],
    faqs: [
      { q: 'What planning controls apply in Ku-ring-gai?', a: 'Ku-ring-gai properties are governed by the Ku-ring-gai LEP 2015 and Ku-ring-gai DCP. Controls cover height, FSR, setbacks, tree preservation, heritage, and bushfire. Ku-ring-gai has particularly strict tree and canopy controls.' },
      { q: 'What are the tree preservation controls in Ku-ring-gai?', a: 'Ku-ring-gai has some of NSW\'s strictest tree preservation requirements. The DCP requires canopy retention and replacement planting. Removing trees typically requires council approval and compensatory planting.' },
      { q: 'How does heritage affect development in Ku-ring-gai?', a: 'Ku-ring-gai has extensive heritage conservation areas, particularly in Turramurra, Wahroonga, and Pymble. Properties within HCAs face additional controls on design, materials, and demolition.' },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    hasDcpData: true,
    relatedSlugs: ['ku-ring-gai', 'northern-beaches', 'the-hills-shire'],
    faqs: [
      { q: 'What planning controls apply in Hornsby?', a: 'Hornsby properties are governed by the Hornsby LEP 2013 and Hornsby DCP. Controls cover height, FSR, setbacks, landscaping, bushfire, and biodiversity. Much of the shire has environmental controls due to bushland proximity.' },
      { q: 'What bushfire controls apply in Hornsby?', a: 'Significant portions of Hornsby Shire are mapped as Bush Fire Prone Land. Properties on BFPL require BAL assessment, asset protection zones, and AS 3959-compliant construction.' },
      { q: 'What setback requirements apply in Hornsby?', a: 'Setback requirements come from the Hornsby DCP and vary by zone and lot size. Typical residential front setbacks are 6-7.5m. The tool shows the specific setback controls for your property with DCP clause references.' },
    ],
  },
  {
    name: 'Lane Cove',
    slug: 'lane-cove',
    hasDcpData: true,
    relatedSlugs: ['ryde', 'inner-west', 'northern-beaches'],
    faqs: [
      { q: 'What planning controls apply in Lane Cove?', a: 'Lane Cove properties are governed by the Lane Cove LEP 2009 and Lane Cove DCP. Controls cover height, FSR, setbacks, parking, landscaping, and heritage. Enter your address for the specific controls with clause citations.' },
      { q: 'What height limits apply in Lane Cove?', a: 'Height limits in Lane Cove vary by zone and are mapped in the LEP. Typical residential height limits are 8.5m for low density zones. The tool pulls the specific limit for your property.' },
      { q: 'What parking requirements apply in Lane Cove?', a: 'Parking requirements come from the Lane Cove DCP and vary by development type. Standard residential rates apply. The tool shows the exact parking requirements for your property.' },
    ],
  },
  {
    name: 'Ryde',
    slug: 'ryde',
    hasDcpData: true,
    relatedSlugs: ['lane-cove', 'parramatta', 'hornsby'],
    faqs: [
      { q: 'What planning controls apply in Ryde?', a: 'Ryde properties are governed by the Ryde LEP 2014 and Ryde DCP 2014. Controls cover height, FSR, setbacks, parking, landscaping, and heritage. Enter your address for the specific controls.' },
      { q: 'What setback requirements apply in Ryde?', a: 'Setback requirements come from the Ryde DCP and vary by zone and lot size. The tool pulls the specific front, side, and rear setback controls for your property with the exact DCP clause references.' },
      { q: 'How does Ryde handle dual occupancy development?', a: 'Dual occupancy in Ryde is subject to LEP and DCP controls including minimum lot size, FSR, setbacks, private open space, and landscaping. The tool shows all applicable controls for your address.' },
    ],
  },
  // ── Greater Sydney — West ──────────────────────────────────────────
  {
    name: 'Parramatta',
    slug: 'parramatta',
    hasDcpData: true,
    relatedSlugs: ['blacktown', 'ryde', 'penrith'],
    faqs: [
      { q: 'What planning controls apply in Parramatta?', a: 'Parramatta properties are governed by the Parramatta LEP 2023 and Parramatta DCP. Controls cover height, FSR, setbacks, parking, landscaping, and heritage. Parramatta CBD has specific design excellence provisions.' },
      { q: 'Are there special controls in Parramatta CBD?', a: 'Yes. The Parramatta CBD has additional controls including design excellence requirements for buildings over a certain height, active ground-floor frontage requirements, and specific setback and podium-tower relationships.' },
      { q: 'What heritage controls apply in Parramatta?', a: 'Parramatta has extensive heritage including the oldest European settlement area in Sydney outside the CBD. Heritage items and heritage conservation areas are mapped in the LEP. The tool shows whether your property is heritage-affected.' },
    ],
  },
  {
    name: 'Blacktown',
    slug: 'blacktown',
    hasDcpData: true,
    relatedSlugs: ['parramatta', 'the-hills-shire', 'penrith'],
    faqs: [
      { q: 'What planning controls apply in Blacktown?', a: 'Blacktown properties are governed by the Blacktown LEP 2015 and Blacktown DCP. Controls cover height, FSR, setbacks, parking, and landscaping. New release areas in the North West Growth Area have specific precinct controls.' },
      { q: 'What are the setback requirements in Blacktown?', a: 'Setback requirements come from the Blacktown DCP and vary by zone and lot width. Standard residential setbacks apply across most suburban areas. The tool pulls the specific controls for your address.' },
      { q: 'Are there specific controls for new release areas in Blacktown?', a: 'Yes. New release areas in the North West Growth Area (e.g. Marsden Park, Riverstone) have precinct-specific controls that differ from established suburb controls.' },
    ],
  },
  {
    name: 'The Hills Shire',
    slug: 'the-hills-shire',
    hasDcpData: true,
    relatedSlugs: ['hornsby', 'blacktown', 'penrith'],
    faqs: [
      { q: 'What planning controls apply in The Hills Shire?', a: 'The Hills Shire properties are governed by The Hills LEP 2019 and The Hills DCP. Controls cover height, FSR, setbacks, parking, landscaping, and environmental management. New release areas have specific precinct plans.' },
      { q: 'What controls apply in the Hills new release areas?', a: 'New release areas like Box Hill, North Kellyville, and Balmoral Road have precinct-specific controls covering lot size, setbacks, and infrastructure contributions that differ from established areas.' },
      { q: 'What heritage controls apply in The Hills?', a: 'The Hills Shire has heritage items mainly in older village centres like Rouse Hill and Castle Hill. Heritage items and HCAs are listed in the LEP. The tool shows whether your property is heritage-affected.' },
    ],
  },
  {
    name: 'Cumberland',
    slug: 'cumberland',
    hasDcpData: true,
    relatedSlugs: ['parramatta', 'canterbury-bankstown', 'fairfield', 'blacktown'],
    faqs: [
      { q: 'What planning controls apply in Cumberland?', a: 'Cumberland properties are governed by the Cumberland LEP 2021 and Cumberland DCP. Controls cover height, FSR, setbacks, parking, landscaping, and heritage. Cumberland was formed from Auburn, Holroyd, and parts of Parramatta.' },
      { q: 'Do different parts of Cumberland have different controls?', a: 'Cumberland was formed from Auburn, Holroyd, and parts of Parramatta councils. Some precinct-specific controls from the former councils still apply in different areas. The tool identifies which controls apply to your address.' },
      { q: 'What setback requirements apply in Cumberland?', a: 'Setback requirements come from the Cumberland DCP and vary by zone and lot width. The tool shows the specific front, side, and rear setback controls for your property.' },
    ],
  },
  {
    name: 'Fairfield',
    slug: 'fairfield',
    hasDcpData: true,
    relatedSlugs: ['liverpool', 'cumberland', 'canterbury-bankstown', 'penrith'],
    faqs: [
      { q: 'What planning controls apply in Fairfield?', a: 'Fairfield properties are governed by the Fairfield LEP 2013 and Fairfield DCP. Controls cover height, FSR, setbacks, parking, landscaping, and flood. Parts of Fairfield near the Prospect Creek and Georges River have flood controls.' },
      { q: 'What flood controls apply in Fairfield?', a: 'Properties near Prospect Creek and the Georges River are subject to flood planning controls. These affect permissible development, floor levels, and site design. The tool shows applicable flood overlays.' },
      { q: 'What parking requirements apply in Fairfield?', a: 'Parking rates come from the Fairfield DCP and vary by development type. Standard residential rates apply across most areas. The tool shows the exact parking requirements for your address.' },
    ],
  },
  {
    name: 'Penrith',
    slug: 'penrith',
    hasDcpData: true,
    relatedSlugs: ['blacktown', 'hawkesbury', 'campbelltown'],
    faqs: [
      { q: 'What planning controls apply in Penrith?', a: 'Penrith properties are governed by the Penrith LEP 2010 and Penrith DCP. Controls cover height, FSR, setbacks, parking, landscaping, flood, and bushfire. Flood controls are significant near the Nepean River.' },
      { q: 'How does flood risk affect planning controls in Penrith?', a: 'Parts of Penrith near the Nepean River and South Creek are subject to flood planning controls. These may affect floor levels, setbacks, and the types of development permitted. The tool identifies applicable flood overlays.' },
      { q: 'What setback requirements apply in Penrith?', a: 'Setback requirements come from the Penrith DCP and vary by zone, lot width, and precinct. Standard residential setbacks are typically 4.5-6m front, 0.9-1.5m side. The tool shows the specific controls for your address.' },
    ],
  },
  {
    name: 'Hawkesbury',
    slug: 'hawkesbury',
    hasDcpData: true,
    relatedSlugs: ['penrith', 'the-hills-shire', 'blacktown'],
    faqs: [
      { q: 'What planning controls apply in Hawkesbury?', a: 'Hawkesbury properties are governed by the Hawkesbury LEP 2012 and Hawkesbury DCP. Controls cover height, FSR, setbacks, flood, heritage, and rural land management. Flood controls are particularly significant throughout the Hawkesbury-Nepean valley.' },
      { q: 'How does flood risk affect planning in Hawkesbury?', a: 'The Hawkesbury-Nepean valley has NSW\'s most significant flood risk. Many properties are subject to flood planning controls affecting permissible development, floor levels, and evacuation requirements. The tool shows applicable flood overlays.' },
      { q: 'What heritage controls apply in Hawkesbury?', a: 'Hawkesbury has extensive colonial heritage, particularly around Windsor, Richmond, and Wilberforce. Heritage conservation areas and individual items are mapped in the LEP. The tool shows whether your property is heritage-affected.' },
    ],
  },
  // ── Greater Sydney — South & Southwest ─────────────────────────────
  {
    name: 'Campbelltown',
    slug: 'campbelltown',
    hasDcpData: true,
    relatedSlugs: ['camden', 'liverpool', 'sutherland-shire'],
    faqs: [
      { q: 'What planning controls apply in Campbelltown?', a: 'Campbelltown properties are governed by the Campbelltown LEP 2015 and Campbelltown DCP. Controls cover height, FSR, setbacks, parking, landscaping, flood, and bushfire. Enter your address for the specific controls.' },
      { q: 'What setback requirements apply in Campbelltown?', a: 'Setback requirements come from the Campbelltown DCP and vary by zone and lot width. Standard residential front setbacks are typically 4.5-6m. The tool shows the specific controls for your property.' },
      { q: 'Are there special controls for new development areas in Campbelltown?', a: 'Yes. Growth areas in Campbelltown have precinct-specific controls that differ from established suburbs. The tool identifies which controls apply to your address.' },
    ],
  },
  {
    name: 'Camden',
    slug: 'camden',
    hasDcpData: true,
    relatedSlugs: ['campbelltown', 'liverpool', 'penrith'],
    faqs: [
      { q: 'What planning controls apply in Camden?', a: 'Camden properties are governed by the Camden LEP 2010 and Camden DCP. Controls cover height, FSR, setbacks, parking, and landscaping. New release areas in the South West Growth Area have specific precinct controls.' },
      { q: 'What controls apply in Camden\'s growth areas?', a: 'Growth areas like Oran Park, Leppington, and Spring Farm have precinct-specific controls covering lot size, setbacks, and infrastructure that differ from the established Camden township.' },
      { q: 'What heritage controls apply in Camden?', a: 'Camden has significant colonial heritage around the Camden township and Narellan. Heritage items and conservation areas are listed in the LEP. The tool shows whether your property is heritage-affected.' },
    ],
  },
  {
    name: 'Liverpool',
    slug: 'liverpool',
    hasDcpData: true,
    relatedSlugs: ['campbelltown', 'canterbury-bankstown', 'camden'],
    faqs: [
      { q: 'What planning controls apply in Liverpool?', a: 'Liverpool properties are governed by the Liverpool LEP 2008 and Liverpool DCP. Controls cover height, FSR, setbacks, parking, flood, and landscaping. Liverpool CBD has specific design and density controls.' },
      { q: 'How does flood risk affect planning in Liverpool?', a: 'Parts of Liverpool near the Georges River and its tributaries are subject to flood planning controls. These affect permissible development, floor levels, and site design. The tool shows applicable flood overlays for your address.' },
      { q: 'What controls apply in Liverpool CBD?', a: 'Liverpool CBD has specific controls including higher density allowances, design excellence requirements, and active frontage provisions that differ from suburban residential controls.' },
    ],
  },
  {
    name: 'Sutherland Shire',
    slug: 'sutherland-shire',
    hasDcpData: true,
    relatedSlugs: ['georges-river', 'campbelltown', 'bayside'],
    faqs: [
      { q: 'What planning controls apply in Sutherland Shire?', a: 'Sutherland Shire properties are governed by the Sutherland Shire LEP 2015 and Sutherland Shire DCP 2015. Controls cover height, FSR, setbacks, parking, landscaping, bushfire, and foreshore areas.' },
      { q: 'What bushfire controls apply in Sutherland Shire?', a: 'Significant portions of Sutherland Shire are mapped as Bush Fire Prone Land, particularly near the Royal National Park and Heathcote bushland. Properties on BFPL require BAL assessment and AS 3959 compliance.' },
      { q: 'Are there foreshore controls in Sutherland Shire?', a: 'Yes. Properties near Port Hacking, Botany Bay, and Georges River foreshores are subject to foreshore building line controls. These restrict development within a setback from the foreshore boundary.' },
    ],
  },
  {
    name: 'Georges River',
    slug: 'georges-river',
    hasDcpData: true,
    relatedSlugs: ['bayside', 'canterbury-bankstown', 'sutherland-shire'],
    faqs: [
      { q: 'What planning controls apply in Georges River?', a: 'Georges River properties are governed by the Georges River LEP 2021 and Georges River DCP. Controls cover height, FSR, setbacks, parking, landscaping, and heritage. Enter your address for the specific controls.' },
      { q: 'What heritage controls apply in Georges River?', a: 'Georges River has heritage items and heritage conservation areas, particularly in the former Kogarah and Hurstville areas. Heritage items are listed in the LEP. The tool shows whether your property is heritage-affected.' },
      { q: 'What parking requirements apply in Georges River?', a: 'Parking rates come from the Georges River DCP and vary by development type and location. The tool shows the specific parking requirements applicable to your address.' },
    ],
  },
  {
    name: 'Canterbury-Bankstown',
    slug: 'canterbury-bankstown',
    hasDcpData: true,
    relatedSlugs: ['inner-west', 'bayside', 'georges-river'],
    faqs: [
      { q: 'What planning controls apply in Canterbury-Bankstown?', a: 'Canterbury-Bankstown properties are governed by the Canterbury-Bankstown LEP 2023 and Canterbury-Bankstown DCP. Controls cover height, FSR, setbacks, parking, landscaping, flood, and heritage.' },
      { q: 'Do different parts of Canterbury-Bankstown have different controls?', a: 'The council merged from Canterbury and Bankstown, and some precinct-specific controls from the former councils still apply. The tool identifies which specific controls apply to your address.' },
      { q: 'What flood controls apply in Canterbury-Bankstown?', a: 'Parts of Canterbury-Bankstown near the Cooks River, Georges River, and Duck River are subject to flood planning controls. These affect floor levels, setbacks, and permissible development. Check your address above.' },
    ],
  },
  // ── Regional NSW ───────────────────────────────────────────────────
  {
    name: 'Wollongong',
    slug: 'wollongong',
    hasDcpData: true,
    relatedSlugs: ['wingecarribee', 'campbelltown', 'sutherland-shire'],
    faqs: [
      { q: 'What planning controls apply in Wollongong?', a: 'Wollongong properties are governed by the Wollongong LEP 2009 and Wollongong DCP 2009. Controls cover height, FSR, setbacks, parking, landscaping, bushfire, and coastal hazards.' },
      { q: 'What coastal controls apply in Wollongong?', a: 'Coastal properties in Wollongong are subject to coastal hazard and foreshore building line controls. The Coastal Management SEPP also applies to properties within the coastal zone. The tool identifies applicable overlays.' },
      { q: 'What bushfire controls apply in Wollongong?', a: 'Parts of Wollongong near the Illawarra Escarpment are mapped as Bush Fire Prone Land. Properties on BFPL require BAL assessment and AS 3959 compliance for any new building work.' },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    hasDcpData: true,
    relatedSlugs: ['wollongong', 'campbelltown', 'yass-valley'],
    faqs: [
      { q: 'What planning controls apply in Wingecarribee?', a: 'Wingecarribee properties are governed by the Wingecarribee LEP 2010 and Wingecarribee DCP. Controls cover height, FSR, setbacks, parking, landscaping, heritage, and bushfire. The Southern Highlands has significant heritage controls.' },
      { q: 'What heritage controls apply in Wingecarribee?', a: 'Wingecarribee has extensive heritage particularly in Bowral, Moss Vale, Berrima, and Mittagong. Heritage conservation areas and items are listed in the LEP. The tool shows whether your property is heritage-affected.' },
      { q: 'What bushfire controls apply in Wingecarribee?', a: 'Much of Wingecarribee is mapped as Bush Fire Prone Land due to surrounding bushland. Properties on BFPL require BAL assessment and may need asset protection zones.' },
    ],
  },
  {
    name: 'Clarence Valley',
    slug: 'clarence-valley',
    hasDcpData: true,
    relatedSlugs: ['yass-valley', 'tamworth-regional', 'bathurst-regional'],
    faqs: [
      { q: 'What planning controls apply in Clarence Valley?', a: 'Clarence Valley properties are governed by the Clarence Valley LEP 2011 and Clarence Valley DCP. Controls cover height, setbacks, parking, flood, and environmental management. Flood controls are significant near the Clarence River.' },
      { q: 'How does flood risk affect planning in Clarence Valley?', a: 'The Clarence River and its tributaries create significant flood risk across the LGA. Many properties are subject to flood planning controls affecting permissible development and floor levels.' },
      { q: 'What setback requirements apply in Clarence Valley?', a: 'Setback requirements come from the Clarence Valley DCP and vary by zone. Rural and rural-residential areas have different controls to urban areas. The tool shows the specific controls for your address.' },
    ],
  },
  {
    name: 'Yass Valley',
    slug: 'yass-valley',
    hasDcpData: true,
    relatedSlugs: ['wingecarribee', 'clarence-valley', 'bathurst-regional'],
    faqs: [
      { q: 'What planning controls apply in Yass Valley?', a: 'Yass Valley properties are governed by the Yass Valley LEP 2013 and Yass Valley DCP. Controls cover height, setbacks, parking, landscaping, heritage, and rural land management.' },
      { q: 'What heritage controls apply in Yass Valley?', a: 'Yass Valley has heritage items particularly in the Yass township. Heritage items and conservation areas are listed in the LEP. The tool shows whether your property is heritage-affected.' },
      { q: 'What controls apply to rural properties in Yass Valley?', a: 'Rural properties in Yass Valley are subject to specific controls on dwelling size, setbacks from boundaries, and environmental management including bushfire, biodiversity, and water management.' },
    ],
  },
  {
    name: 'Bathurst Regional',
    slug: 'bathurst-regional',
    hasDcpData: true,
    relatedSlugs: ['forbes', 'yass-valley', 'tamworth-regional'],
    faqs: [
      { q: 'What planning controls apply in Bathurst Regional?', a: 'Bathurst Regional properties are governed by the Bathurst Regional LEP 2014 and Bathurst Regional DCP. Controls cover height, setbacks, parking, heritage, and rural land management.' },
      { q: 'What heritage controls apply in Bathurst?', a: 'Bathurst has extensive colonial and gold-rush era heritage. Heritage items and heritage conservation areas are listed in the LEP. Properties in the Bathurst CBD heritage precinct face specific design controls.' },
      { q: 'What controls apply to rural properties in Bathurst?', a: 'Rural properties are subject to minimum lot size controls, dwelling setbacks, and environmental management provisions including water management and biosecurity.' },
    ],
  },
  {
    name: 'Tamworth Regional',
    slug: 'tamworth-regional',
    hasDcpData: true,
    relatedSlugs: ['bathurst-regional', 'clarence-valley', 'forbes'],
    faqs: [
      { q: 'What planning controls apply in Tamworth Regional?', a: 'Tamworth Regional properties are governed by the Tamworth Regional LEP 2010 and Tamworth Regional DCP. Controls cover height, setbacks, parking, and rural land management.' },
      { q: 'What setback requirements apply in Tamworth?', a: 'Setback requirements come from the Tamworth Regional DCP and vary by zone. Urban Tamworth has different controls to rural and village areas. The tool shows the specific controls for your address.' },
      { q: 'What controls apply in Tamworth\'s rural zones?', a: 'Rural properties are subject to minimum lot size controls, dwelling setbacks from boundaries and roads, and environmental management provisions.' },
    ],
  },
  {
    name: 'Forbes',
    slug: 'forbes',
    hasDcpData: true,
    relatedSlugs: ['bathurst-regional', 'tamworth-regional', 'yass-valley'],
    faqs: [
      { q: 'What planning controls apply in Forbes?', a: 'Forbes properties are governed by the Forbes LEP 2013 and Forbes DCP. Controls cover height, setbacks, parking, heritage, and flood. Flood controls are significant near the Lachlan River.' },
      { q: 'How does flood risk affect planning in Forbes?', a: 'Forbes is subject to significant flood risk from the Lachlan River. Many properties have flood planning controls affecting permissible development, floor levels, and site design.' },
      { q: 'What heritage controls apply in Forbes?', a: 'Forbes has heritage items particularly in the town centre. Heritage items are listed in the LEP. The tool shows whether your property is heritage-affected.' },
    ],
  },
]

export const VERIFY_LGA_SLUG_MAP: Record<string, VerifyLgaData> = Object.fromEntries(
  VERIFY_LGAS.map(lga => [lga.slug, lga])
)
