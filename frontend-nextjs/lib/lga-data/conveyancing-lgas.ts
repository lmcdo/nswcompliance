export interface ConveyancingLgaData {
  name: string
  slug: string
  faqs: Array<{ q: string; a: string }>
  relatedSlugs: string[]
}

export const CONVEYANCING_LGAS: ConveyancingLgaData[] = [
  // ── Greater Sydney — Inner & East ──────────────────────────────────
  {
    name: 'City of Sydney',
    slug: 'city-of-sydney',
    relatedSlugs: ['inner-west', 'woollahra', 'bayside', 'randwick'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for City of Sydney?', a: 'LEP zoning, height and FSR controls, heritage status, environmental overlays (flood, acid sulfate, contamination), SEPP overlays, spatial constraints, nearby DA activity, and DCP setback controls — all sourced live from the NSW Planning Portal.' },
      { q: 'Why do conveyancers need a planning disclosure?', a: 'Section 10.7 certificates only disclose statutory instruments. A planning disclosure report fills the gap — showing what can actually be built, what constraints apply, and what development is happening nearby.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report. It covers data that 10.7 certificates don\'t address, such as DCP controls, development feasibility, and nearby DA activity.' },
    ],
  },
  {
    name: 'Inner West',
    slug: 'inner-west',
    relatedSlugs: ['city-of-sydney', 'canada-bay', 'bayside', 'canterbury-bankstown'],
    faqs: [
      { q: 'What planning data is available for Inner West properties?', a: 'Inner West has the most comprehensive coverage — full structured DCP provisions (setbacks, parking, landscaping, site coverage) plus LEP, SEPP, heritage, flood, and spatial overlays.' },
      { q: 'Does the report cover all three former councils?', a: 'Yes — Ashfield, Marrickville, and Leichhardt DCP controls are all included with precinct-level matching for the correct address.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Bayside',
    slug: 'bayside',
    relatedSlugs: ['randwick', 'city-of-sydney', 'georges-river', 'canterbury-bankstown'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Bayside?', a: 'LEP zoning, height and FSR controls, heritage status, flood overlays, acid sulfate soils, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Does the report cover flood risk in Bayside?', a: 'Yes — flood planning area status is checked against NSW statutory overlays and included in both the free summary and full report.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Randwick',
    slug: 'randwick',
    relatedSlugs: ['bayside', 'woollahra', 'waverley', 'city-of-sydney'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Randwick?', a: 'LEP zoning, height and FSR controls, heritage status, coastal and flood overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Are coastal management controls included?', a: 'Yes — SEPP Resilience and Hazards (formerly Coastal Management) overlays are checked and disclosed where they apply.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Waverley',
    slug: 'waverley',
    relatedSlugs: ['woollahra', 'randwick', 'city-of-sydney'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Waverley?', a: 'LEP zoning, height and FSR controls, heritage status, coastal overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Woollahra',
    slug: 'woollahra',
    relatedSlugs: ['waverley', 'city-of-sydney', 'randwick'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Woollahra?', a: 'LEP zoning, height and FSR controls, heritage conservation area status, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Does it flag heritage conservation areas?', a: 'Yes — heritage items and heritage conservation areas from the Woollahra LEP are identified for the specific address.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Canada Bay',
    slug: 'canada-bay',
    relatedSlugs: ['inner-west', 'burwood', 'strathfield', 'city-of-sydney'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Canada Bay?', a: 'LEP zoning, height and FSR controls, heritage status, environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Burwood',
    slug: 'burwood',
    relatedSlugs: ['strathfield', 'canada-bay', 'inner-west', 'canterbury-bankstown'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Burwood?', a: 'LEP zoning, height and FSR controls, heritage status, environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Strathfield',
    slug: 'strathfield',
    relatedSlugs: ['burwood', 'canada-bay', 'cumberland', 'inner-west'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Strathfield?', a: 'LEP zoning, height and FSR controls, heritage status, environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  // ── Greater Sydney — North ──────────────────────────────────
  {
    name: 'Northern Beaches',
    slug: 'northern-beaches',
    relatedSlugs: ['ku-ring-gai', 'hornsby', 'ryde'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Northern Beaches?', a: 'LEP zoning, height and FSR controls, heritage status, bushfire and coastal overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Are bushfire prone land controls included?', a: 'Yes — bushfire prone land mapping is checked and disclosed. Properties on bushfire prone land have additional construction and planning requirements.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Ku-ring-gai',
    slug: 'ku-ring-gai',
    relatedSlugs: ['hornsby', 'northern-beaches', 'ryde'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Ku-ring-gai?', a: 'LEP zoning, height and FSR controls, heritage conservation areas, bushfire overlays, biodiversity, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Does it cover heritage conservation areas in Ku-ring-gai?', a: 'Yes — Ku-ring-gai has extensive heritage conservation areas. The report identifies whether the property is within one and what additional controls apply.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    relatedSlugs: ['ku-ring-gai', 'the-hills-shire', 'northern-beaches', 'ryde'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Hornsby?', a: 'LEP zoning, height and FSR controls, heritage status, bushfire overlays, biodiversity, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Lane Cove',
    slug: 'lane-cove',
    relatedSlugs: ['ryde', 'ku-ring-gai', 'northern-beaches'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Lane Cove?', a: 'LEP zoning, height and FSR controls, heritage status, environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Ryde',
    slug: 'ryde',
    relatedSlugs: ['lane-cove', 'ku-ring-gai', 'parramatta', 'hornsby'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Ryde?', a: 'LEP zoning, height and FSR controls, heritage status, environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  // ── Greater Sydney — West ──────────────────────────────────
  {
    name: 'Parramatta',
    slug: 'parramatta',
    relatedSlugs: ['cumberland', 'blacktown', 'the-hills-shire', 'ryde'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Parramatta?', a: 'LEP zoning, height and FSR controls, heritage status, flood overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Blacktown',
    slug: 'blacktown',
    relatedSlugs: ['parramatta', 'the-hills-shire', 'penrith', 'cumberland'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Blacktown?', a: 'LEP zoning, height and FSR controls, heritage status, flood and environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'The Hills Shire',
    slug: 'the-hills-shire',
    relatedSlugs: ['blacktown', 'hornsby', 'parramatta', 'hawkesbury'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for The Hills Shire?', a: 'LEP zoning, height and FSR controls, heritage status, bushfire and flood overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Penrith',
    slug: 'penrith',
    relatedSlugs: ['blacktown', 'the-hills-shire', 'hawkesbury', 'camden'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Penrith?', a: 'LEP zoning, height and FSR controls, heritage status, flood and bushfire overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Does the report cover flood risk in Penrith?', a: 'Yes — Penrith has significant flood planning areas along the Nepean River. Flood status is checked and disclosed.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Hawkesbury',
    slug: 'hawkesbury',
    relatedSlugs: ['penrith', 'the-hills-shire', 'blacktown'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Hawkesbury?', a: 'LEP zoning, height and FSR controls, heritage status, flood and bushfire overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Is flood risk a major factor in Hawkesbury?', a: 'Yes — Hawkesbury has some of the most extensive flood planning areas in NSW along the Hawkesbury-Nepean River. Flood status is prominently disclosed.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Cumberland',
    slug: 'cumberland',
    relatedSlugs: ['parramatta', 'fairfield', 'blacktown', 'strathfield'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Cumberland?', a: 'LEP zoning, height and FSR controls, heritage status, environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Fairfield',
    slug: 'fairfield',
    relatedSlugs: ['cumberland', 'liverpool', 'canterbury-bankstown', 'parramatta'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Fairfield?', a: 'LEP zoning, height and FSR controls, heritage status, environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  // ── Greater Sydney — South & Southwest ──────────────────────────────────
  {
    name: 'Campbelltown',
    slug: 'campbelltown',
    relatedSlugs: ['camden', 'liverpool', 'canterbury-bankstown'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Campbelltown?', a: 'LEP zoning, height and FSR controls, heritage status, bushfire and environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Camden',
    slug: 'camden',
    relatedSlugs: ['campbelltown', 'liverpool', 'penrith'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Camden?', a: 'LEP zoning, height and FSR controls, heritage status, bushfire and flood overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Is the report useful for new estates in Camden?', a: 'Yes — new estates have specific LEP provisions and SEPP controls. The report identifies the applicable zoning, height limits, and any overlay constraints for the specific lot.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Liverpool',
    slug: 'liverpool',
    relatedSlugs: ['fairfield', 'campbelltown', 'canterbury-bankstown', 'camden'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Liverpool?', a: 'LEP zoning, height and FSR controls, heritage status, flood and environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Sutherland Shire',
    slug: 'sutherland-shire',
    relatedSlugs: ['georges-river', 'bayside', 'campbelltown'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Sutherland Shire?', a: 'LEP zoning, height and FSR controls, heritage status, bushfire, flood and coastal overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'Are bushfire controls included for Sutherland Shire?', a: 'Yes — large areas of Sutherland Shire are bushfire prone land. The report checks and discloses bushfire prone land status.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Georges River',
    slug: 'georges-river',
    relatedSlugs: ['sutherland-shire', 'bayside', 'canterbury-bankstown'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Georges River?', a: 'LEP zoning, height and FSR controls, heritage status, flood and environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Canterbury-Bankstown',
    slug: 'canterbury-bankstown',
    relatedSlugs: ['inner-west', 'georges-river', 'fairfield', 'liverpool'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Canterbury-Bankstown?', a: 'LEP zoning, height and FSR controls, heritage status, flood and environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  // ── Regional NSW ──────────────────────────────────
  {
    name: 'Wollongong',
    slug: 'wollongong',
    relatedSlugs: ['sutherland-shire', 'campbelltown'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Wollongong?', a: 'LEP zoning, height and FSR controls, heritage status, coastal, flood and bushfire overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    relatedSlugs: ['campbelltown', 'camden', 'wollongong'],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Wingecarribee?', a: 'LEP zoning, height and FSR controls, heritage status, bushfire overlays, environmental overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Clarence Valley',
    slug: 'clarence-valley',
    relatedSlugs: [],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Clarence Valley?', a: 'LEP zoning, height and FSR controls, heritage status, flood and coastal overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Yass Valley',
    slug: 'yass-valley',
    relatedSlugs: [],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Yass Valley?', a: 'LEP zoning, height and FSR controls, heritage status, bushfire overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Bathurst Regional',
    slug: 'bathurst-regional',
    relatedSlugs: [],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Bathurst Regional?', a: 'LEP zoning, height and FSR controls, heritage status, flood and bushfire overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Tamworth Regional',
    slug: 'tamworth-regional',
    relatedSlugs: [],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Tamworth Regional?', a: 'LEP zoning, height and FSR controls, heritage status, flood and bushfire overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
  {
    name: 'Forbes',
    slug: 'forbes',
    relatedSlugs: [],
    faqs: [
      { q: 'What does a conveyancing planning disclosure cover for Forbes?', a: 'LEP zoning, height and FSR controls, heritage status, flood overlays, SEPP overlays, nearby DA activity, and DCP setback controls.' },
      { q: 'How quickly is the report generated?', a: 'The free summary is instant. The full PDF report is generated within minutes and emailed to you after payment.' },
      { q: 'Is this a replacement for a Section 10.7 certificate?', a: 'No. This is a supplementary planning intelligence report covering data that 10.7 certificates don\'t address.' },
    ],
  },
]

export const CONVEYANCING_LGA_SLUG_MAP: Record<string, ConveyancingLgaData> =
  Object.fromEntries(CONVEYANCING_LGAS.map(lga => [lga.slug, lga]))
