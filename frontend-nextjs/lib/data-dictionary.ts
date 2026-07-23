/**
 * Data dictionary — per-field documentation for the structured planning data
 * PlotDetect serves.
 *
 * Each entry documents one field: what it is, the authoritative source it is
 * read from, the licence and attribution that travel with it, how current it
 * is, and its limits. These pages are the public reference for both AI
 * assistants citing the data and API consumers reading it.
 *
 * Language rule: factual descriptions only. No advice, no fitness-for-purpose
 * claims. Values are read from published government sources and cited to them.
 */

export interface DataDictionaryField {
  slug: string;
  /** Display name, e.g. "Land zone". */
  name: string;
  /** One-sentence definition used in metadata and JSON-LD. */
  shortDefinition: string;
  /** Longer plain-language explanation, one paragraph per array item. */
  explanation: string[];
  /** Name of the authoritative source system or instrument. */
  sourceName: string;
  sourceUrl: string;
  /** Licence under which the source data is published. */
  licence: string;
  /** Attribution statement that accompanies the data. */
  attribution: string;
  /** How and when the source data changes. */
  currency: string;
  /** Factual limits of the field. */
  caveats: string[];
  /** Related PlotDetect pages. */
  related: { href: string; label: string }[];
}

export const DATA_DICTIONARY_FIELDS: DataDictionaryField[] = [
  {
    slug: 'land-zone',
    name: 'Land zone',
    shortDefinition:
      'The land use zone applying to a lot under its Local Environmental Plan, e.g. R2 Low Density Residential.',
    explanation: [
      'Every lot in NSW is assigned a land use zone by the Local Environmental Plan (LEP) that applies to it. The zone code (for example R2, R3, E1, MU1) determines which development types the LEP lists as permitted without consent, permitted with consent, or prohibited on that land.',
      'PlotDetect reads the zone for an address from the NSW Planning Portal at the time a report is generated, and pairs it with the land use table of the applicable LEP where that table is held in structured form.',
    ],
    sourceName: 'NSW Planning Portal / ePlanning Land Zoning spatial layer',
    sourceUrl: 'https://www.planningportal.nsw.gov.au/spatialviewer/',
    licence: 'Creative Commons Attribution (CC-BY)',
    attribution:
      '© State of New South Wales (Department of Planning, Housing and Infrastructure)',
    currency:
      'The Planning Portal layer is updated as LEP amendments are published. PlotDetect queries the live layer per request rather than storing a copy.',
    caveats: [
      'A zone tells you the applicable land use table; it does not by itself state what can be built. Development standards (height, floor space ratio, lot size) and site constraints apply in addition to the zone.',
      'Deferred matters and land covered by a State Environmental Planning Policy can sit outside the standard zone framework.',
    ],
    related: [
      { href: '/tools/zoning-check', label: 'Zoning check tool' },
      { href: '/glossary', label: 'Planning glossary' },
    ],
  },
  {
    slug: 'height-of-building',
    name: 'Height of building control',
    shortDefinition:
      'The maximum building height in metres mapped for a lot under its LEP Height of Buildings map.',
    explanation: [
      'Most LEPs set a maximum building height for land through a Height of Buildings (HOB) map, expressed in metres. The control applies through the LEP clause that references the map — typically clause 4.3.',
      'PlotDetect reads the mapped height value for an address from the NSW Planning Portal ePlanning spatial layer and cites the LEP it belongs to.',
    ],
    sourceName: 'NSW Planning Portal / ePlanning Height of Buildings spatial layer',
    sourceUrl: 'https://www.planningportal.nsw.gov.au/spatialviewer/',
    licence: 'Creative Commons Attribution (CC-BY)',
    attribution:
      '© State of New South Wales (Department of Planning, Housing and Infrastructure)',
    currency:
      'Updated as LEP amendments are published to the Planning Portal. Queried live per request.',
    caveats: [
      'Some land has no mapped height value — in those areas height is governed by other instruments or by DCP controls, and the field is reported as not mapped rather than zero.',
      'State policies (for example the Housing SEPP or the Low and Mid-Rise Housing provisions) can permit heights different from the LEP map in defined areas.',
    ],
    related: [
      { href: '/planning-standards', label: 'SEPP Housing standards' },
      { href: '/assessment', label: 'Compliance check' },
    ],
  },
  {
    slug: 'floor-space-ratio',
    name: 'Floor space ratio control',
    shortDefinition:
      'The maximum ratio of gross floor area to site area mapped for a lot under its LEP Floor Space Ratio map.',
    explanation: [
      'A floor space ratio (FSR) expresses the maximum gross floor area of buildings on a site as a multiple of the site area. An FSR of 0.5:1 on a 600 m² lot corresponds to 300 m² of gross floor area. The control applies through the LEP clause that references the FSR map — typically clause 4.4.',
      'PlotDetect reads the mapped FSR for an address from the NSW Planning Portal ePlanning spatial layer and cites the LEP it belongs to.',
    ],
    sourceName: 'NSW Planning Portal / ePlanning Floor Space Ratio spatial layer',
    sourceUrl: 'https://www.planningportal.nsw.gov.au/spatialviewer/',
    licence: 'Creative Commons Attribution (CC-BY)',
    attribution:
      '© State of New South Wales (Department of Planning, Housing and Infrastructure)',
    currency:
      'Updated as LEP amendments are published to the Planning Portal. Queried live per request.',
    caveats: [
      'Large parts of NSW have no mapped FSR — density there is controlled by other means (landscaped area, site coverage, DCP controls). The field is reported as not mapped in those areas.',
      'The definition of gross floor area varies between instruments; the LEP dictionary definition governs how the ratio is applied.',
    ],
    related: [
      { href: '/glossary', label: 'Planning glossary' },
      { href: '/assessment', label: 'Compliance check' },
    ],
  },
  {
    slug: 'minimum-lot-size',
    name: 'Minimum lot size control',
    shortDefinition:
      'The minimum lot size in square metres mapped for a lot under its LEP Lot Size map.',
    explanation: [
      'LEPs set a minimum lot size for subdivision through a Lot Size map, expressed in square metres or hectares. The control applies through the LEP clause that references the map — typically clause 4.1. Several LEPs also apply minimum lot sizes to particular development types, such as dual occupancies.',
      'PlotDetect reads the mapped minimum lot size for an address from the NSW Planning Portal ePlanning spatial layer and cites the LEP it belongs to.',
    ],
    sourceName: 'NSW Planning Portal / ePlanning Lot Size spatial layer',
    sourceUrl: 'https://www.planningportal.nsw.gov.au/spatialviewer/',
    licence: 'Creative Commons Attribution (CC-BY)',
    attribution:
      '© State of New South Wales (Department of Planning, Housing and Infrastructure)',
    currency:
      'Updated as LEP amendments are published to the Planning Portal. Queried live per request.',
    caveats: [
      'The mapped value governs subdivision; minimum lot sizes for specific development types can be set separately in LEP clauses or state policies.',
      'An existing lot smaller than the mapped minimum is not thereby unusable — the control constrains the creation of new lots.',
    ],
    related: [
      { href: '/tools/subdivision-check', label: 'Subdivision check tool' },
      { href: '/glossary', label: 'Planning glossary' },
    ],
  },
  {
    slug: 'flood-planning-area',
    name: 'Flood planning area',
    shortDefinition:
      'Whether a lot intersects a mapped flood planning area or flood-related overlay.',
    explanation: [
      'Councils map land subject to flood-related development controls, most commonly the flood planning area — land at or below the flood planning level. Where a lot intersects the mapped area, flood-related clauses of the LEP and DCP apply to development on it.',
      'PlotDetect reports whether an address intersects a flood-related overlay held in the NSW Planning Portal spatial layers or in the spatial data PlotDetect ingests from NSW open data, and names the layer the flag came from.',
    ],
    sourceName: 'NSW Planning Portal / ePlanning flood-related spatial layers',
    sourceUrl: 'https://www.planningportal.nsw.gov.au/spatialviewer/',
    licence: 'Creative Commons Attribution (CC-BY)',
    attribution:
      '© State of New South Wales (Department of Planning, Housing and Infrastructure)',
    currency:
      'Overlay layers change when councils adopt new flood studies and map amendments are published.',
    caveats: [
      'An overlay flag is a screening fact, not a flood study. It reports intersection with a published map, not depth, frequency, or hazard category for the lot.',
      'Coverage differs by council: absence of a mapped overlay is not the same as absence of flood risk, and some councils hold flood information outside the published layers.',
    ],
    related: [
      { href: '/flood-risk', label: 'Flood risk pages' },
      { href: '/reports/flood', label: 'Flood screening report' },
    ],
  },
  {
    slug: 'bushfire-prone-land',
    name: 'Bushfire prone land',
    shortDefinition:
      'Whether a lot intersects the Bush Fire Prone Land Map certified for its local government area.',
    explanation: [
      'The NSW Rural Fire Service certifies a Bush Fire Prone Land Map for each local government area. Land on the map is subject to additional planning and construction requirements under the Environmental Planning and Assessment Act and Planning for Bush Fire Protection.',
      'PlotDetect reports whether an address intersects the certified map, and the vegetation category where the layer provides it.',
    ],
    sourceName: 'NSW Rural Fire Service — Bush Fire Prone Land Map',
    sourceUrl: 'https://www.rfs.nsw.gov.au/plan-and-prepare/building-in-a-bush-fire-area/planning-for-bush-fire-protection/bush-fire-prone-land',
    licence: 'Creative Commons Attribution (CC-BY)',
    attribution: '© State of New South Wales (NSW Rural Fire Service)',
    currency:
      'Maps are recertified periodically per council; the spatial layer reflects the current certified map.',
    caveats: [
      'The map flag is not a Bushfire Attack Level (BAL). A BAL is assessed for a specific building footprint against vegetation, slope, and distance.',
      'Mapped categories differ in the controls they trigger; the category, where reported, comes from the published layer.',
    ],
    related: [
      { href: '/bushfire', label: 'Bushfire pages' },
      { href: '/reports/bushfire', label: 'Bushfire screening report' },
    ],
  },
  {
    slug: 'heritage',
    name: 'Heritage listing and conservation areas',
    shortDefinition:
      'Whether a lot is a listed heritage item, within a heritage conservation area, or in proximity to either.',
    explanation: [
      'LEPs list heritage items and heritage conservation areas in Schedule 5, and the heritage clause (typically clause 5.10) applies development controls to listed items, land within conservation areas, and in some cases land in their vicinity.',
      'PlotDetect reports heritage item listings and conservation area membership for an address from the NSW Planning Portal heritage layers and the conservation area boundaries PlotDetect holds, citing the LEP schedule where applicable.',
    ],
    sourceName: 'NSW Planning Portal heritage layers / LEP Schedule 5',
    sourceUrl: 'https://www.planningportal.nsw.gov.au/spatialviewer/',
    licence: 'Creative Commons Attribution (CC-BY)',
    attribution:
      '© State of New South Wales (Department of Planning, Housing and Infrastructure)',
    currency:
      'Updated as LEP heritage schedules are amended and published to the Planning Portal.',
    caveats: [
      'State Heritage Register listings are held separately by Heritage NSW and can apply in addition to LEP listings.',
      'Heritage significance statements and inventory sheets are held by councils; the field reports listing status, not significance detail.',
    ],
    related: [
      { href: '/assessment', label: 'Compliance check (heritage tab)' },
      { href: '/open-data', label: 'Heritage conservation areas dataset' },
    ],
  },
  {
    slug: 'lot-dimensions',
    name: 'Lot dimensions',
    shortDefinition:
      'Lot area, boundary geometry, and derived frontage width from the NSW cadastre.',
    explanation: [
      'The NSW cadastre records the legal boundaries of every lot. From the boundary geometry, lot area and frontage width can be computed for use against controls that reference them, such as minimum lot size or minimum frontage requirements.',
      'PlotDetect reads lot geometry from NSW Spatial Services web services and computes area and width from the published boundary.',
    ],
    sourceName: 'NSW Spatial Services — cadastral web services',
    sourceUrl: 'https://www.spatial.nsw.gov.au/',
    licence:
      'Creative Commons Attribution (CC-BY), per the Spatial Services web services terms',
    attribution: '© State of New South Wales (Spatial Services)',
    currency:
      'The cadastre is maintained continuously as plans are registered; queried live per request.',
    caveats: [
      'Cadastral boundaries are a graphical representation of the legal boundary, not a survey. A registered survey plan governs where the boundary lies.',
      'Computed width depends on which boundary is treated as the frontage; irregular lots can carry more than one defensible value, and the computation method is stated where the value is used.',
    ],
    related: [
      { href: '/tools/subdivision-check', label: 'Subdivision check tool' },
      { href: '/assessment', label: 'Compliance check' },
    ],
  },
  {
    slug: 'land-value',
    name: 'Land value',
    shortDefinition:
      'The Valuer General’s land value for a property — the value of the land alone, excluding structures.',
    explanation: [
      'The NSW Valuer General determines a land value for every property in NSW, used for council rates and land tax. It values the land as if vacant — buildings and other improvements are excluded.',
      'PlotDetect reports the land value published in the Valuer General’s bulk land value data, with its valuation date.',
    ],
    sourceName: 'NSW Valuer General — bulk land values',
    sourceUrl: 'https://data.nsw.gov.au/data/dataset/327f9982-e610-4ffe-a51c-4047e97c7e7d',
    licence: 'Creative Commons Attribution 4.0 (CC-BY 4.0)',
    attribution: '© State of New South Wales (Valuer General)',
    currency:
      'Land values are determined annually at 1 July and published in bulk; the reported value carries its valuation date.',
    caveats: [
      'Land value is not a market price estimate for the property as improved. Sale prices and sales history are published under a different licence and are not part of this dataset.',
      'Values for recently subdivided or amalgamated lots can lag the register.',
    ],
    related: [{ href: '/open-data', label: 'Open data catalogue' }],
  },
  {
    slug: 'development-permissibility',
    name: 'Development permissibility (land use table)',
    shortDefinition:
      'The LEP land use table for a zone: which development types are listed as permitted without consent, permitted with consent, or prohibited.',
    explanation: [
      'Each LEP contains a land use table stating, for every zone, the development types permitted without development consent, permitted with consent, and prohibited. PlotDetect holds these tables in structured form for the councils where extraction is complete, with each entry carrying its permissibility category.',
      'Entries are served only for zone and council combinations that have passed a completeness gate — a zone whose table has not been fully captured returns no entries rather than a partial list.',
    ],
    sourceName: 'Local Environmental Plan land use tables (NSW Legislation)',
    sourceUrl: 'https://legislation.nsw.gov.au/',
    licence: 'NSW legislation is published under Creative Commons Attribution (CC-BY)',
    attribution: '© State of New South Wales',
    currency:
      'Captured from the in-force LEP at extraction time; re-extracted when instruments are amended. Coverage currently spans 26 Sydney-region and surrounding councils.',
    caveats: [
      'A development type absent from the stored table is reported as not listed — not as prohibited. Many LEP zones prohibit unlisted uses through a catch-all clause, and that clause is applied by reading the instrument, not inferred from absence.',
      'Additional permitted uses in LEP Schedule 1 and state policies can permit development the zone table alone would not.',
    ],
    related: [
      { href: '/tools/zoning-check', label: 'Zoning check tool' },
      { href: '/tools/upzoning-check', label: 'Upzoning check tool' },
    ],
  },
];

export function getDataDictionaryField(
  slug: string,
): DataDictionaryField | undefined {
  return DATA_DICTIONARY_FIELDS.find((f) => f.slug === slug);
}
