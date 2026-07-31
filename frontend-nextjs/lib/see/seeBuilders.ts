// SEE Builder Functions — deterministic, pure, no side effects.
// Converts property data (LEP constraints, SEPP flags) into structured assessable rows
// for SEE Sections 3 (Pathway), 4 (SEPP Controls), and 5 (LEP Standards).
//
// All citations reference the governing instrument and clause.
// No AI interpretation — only structured data extraction.

import type { PathwayDetermination, SeppAssessableControl, LepAssessableStandard } from './types';
import type { AmenityData, StreetContextData } from '@/hooks/useSpatialContext';
import { HOUSING_SEPP_ZONES } from '@/lib/regulatory-constants';

// ---------------------------------------------------------------------------
// Section 3 — Approval Pathway Determination
// ---------------------------------------------------------------------------

/**
 * Determines the approval pathway and required specialist reports from property data.
 * Extends the determineDevelopmentPathway() logic in SEEDocument.tsx with legislative
 * basis and required reports.
 *
 * @param zone - Zone code e.g. 'E1', 'R2 Low Density Residential'
 * @param inHca - True if site is in a Heritage Conservation Area
 * @param heritageItem - True if site is a listed heritage item
 * @param constraints - Property constraints object from NSW Planning Portal
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildPathwayDetermination(
  zone: string,
  inHca: boolean,
  heritageItem: boolean,
  constraints?: Record<string, any>
): PathwayDetermination {
  const requiredReports: string[] = [];
  const caveats: string[] = [];

  // Accelerated TOD — flag that current LEP controls may change upon rezoning
  if (constraints?.acceleratedTOD?.inAcceleratedPrecinct) {
    const precinctName = constraints.acceleratedTOD.precinctName ?? 'Accelerated TOD Precinct';
    const rezoningDate = constraints.acceleratedTOD.expectedRezoning;
    caveats.push(
      `Site in ${precinctName}${rezoningDate ? ` (expected rezoning: ${rezoningDate})` : ''} — priority precinct under SEPP (Housing) 2021 Part 3B. Current LEP controls apply until rezoning is gazetted. Confirm controls have not changed before lodgement.`
    );
  }

  const caveatsProp = caveats.length > 0 ? caveats : undefined;

  if (heritageItem) {
    requiredReports.push('Heritage Impact Statement (Clause 5.10 LEP)');
    return {
      pathway: 'Development Application (DA)',
      reason: 'Heritage item — CDC and exempt development not permitted for listed heritage items',
      legislative_basis: 'EP&A Act 1979 s 4.15; LEP Clause 5.10',
      required_reports: requiredReports,
      caveats: caveatsProp,
    };
  }

  if (inHca) {
    requiredReports.push('Heritage Impact Statement (Clause 5.10 LEP)');
    requiredReports.push('Clause 5.10 Statement of Heritage Impact');
    // Note: BASIX may also be required depending on works type — flagged generically
    return {
      pathway: 'Development Application (DA)',
      reason: 'Heritage conservation area — CDC and exempt development restricted under SEPP (Exempt & Complying Development Codes) 2008 cl.1.17(1)(a)',
      legislative_basis: 'SEPP (Exempt & Complying Development Codes) 2008 cl.1.17; EP&A Act 1979 s 4.15; LEP Clause 5.10',
      required_reports: requiredReports,
      caveats: caveatsProp,
    };
  }

  // ANEF zone — acoustic report required regardless of pathway
  if (constraints?.anefData?.inAnefZone) {
    requiredReports.push('Acoustic Report (ANEF zone — SEPP Transport Infrastructure 2021)');
  }

  // Contaminated land — site contamination assessment
  if (constraints?.contaminatedLand?.hasNotifiedSites) {
    requiredReports.push('Site Contamination Assessment (SEPP Resilience and Hazards 2021 Ch.4)');
  }

  const zoneCode = zone.split(' ')[0];

  if (HOUSING_SEPP_ZONES.includes(zoneCode)) {
    return {
      pathway: 'Complying Development (CDC) — check eligibility',
      reason: `${zoneCode} zone — Housing SEPP 2021 CDC pathway available for eligible development types and lot configurations`,
      legislative_basis: 'SEPP (Housing) 2021 Part 2; SEPP (Exempt & Complying Development Codes) 2008',
      required_reports: requiredReports,
      caveats: caveatsProp,
    };
  }

  return {
    pathway: 'Development Application (DA)',
    reason: `${zoneCode} zone — not covered by Housing SEPP 2021 CDC pathway. Check SEPP (Exempt & Complying Development Codes) 2008 Schedule 2 for exempt development eligibility.`,
    legislative_basis: 'EP&A Act 1979 s 4.15; SEPP (Exempt & Complying Development Codes) 2008',
    required_reports: requiredReports,
    caveats: caveatsProp,
  };
}

// ---------------------------------------------------------------------------
// Section 4 — SEPP Assessable Controls
// ---------------------------------------------------------------------------

/**
 * Builds the list of applicable SEPP controls from property constraint data.
 * Returns only controls that are active for this property — omits inapplicable instruments.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildSeppControls(
  constraints?: Record<string, any>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lepClauseData?: Record<string, any>
): SeppAssessableControl[] {
  const controls: SeppAssessableControl[] = [];

  if (!constraints) return controls;

  // BASIX — SEPP (Sustainable Buildings) 2022
  if (constraints.basixWater || constraints.basixClimate) {
    const waterTarget = constraints.basixWater ?? 'refer to BASIX tool';
    const climateZone = constraints.basixClimate ?? 'refer to BASIX tool';
    controls.push({
      instrument: 'SEPP (Sustainable Buildings) 2022',
      control: 'BASIX — Water Efficiency',
      requirement: `Water target: ${waterTarget} reduction from baseline`,
      clause: 'BASIX Certificate required — NSW Planning Portal BASIX tool',
      status: 'pending',
    });
    controls.push({
      instrument: 'SEPP (Sustainable Buildings) 2022',
      control: 'BASIX — Energy & Thermal Comfort',
      requirement: `Climate Zone ${climateZone} — energy and thermal targets apply. Refer to BASIX Certificate.`,
      clause: 'BASIX Certificate required — NSW Planning Portal BASIX tool',
      status: 'pending',
    });
  }

  // TOD parking — SEPP (Housing) 2021
  if (constraints.todPrecinct?.inTODArea) {
    const stationName = constraints.todPrecinct.stationName ?? 'nearby station';
    const stationDist = constraints.todPrecinct.stationDistance
      ? `${constraints.todPrecinct.stationDistance}m`
      : 'within 800m';
    controls.push({
      instrument: 'SEPP (Housing) 2021',
      control: 'TOD Parking Reduction',
      requirement: `Reduced parking rates apply — ${stationName} ${stationDist}. Refer to SEPP (Housing) 2021 Clause 24/42/68/74 for applicable rate by development type.`,
      clause: `SEPP (Housing) 2021 — ${constraints.todPrecinct.seppReference ?? 'Transport Oriented Development'}`,
      status: 'pending',
    });
  }

  // ANEF — SEPP (Transport Infrastructure) 2021
  if (constraints.anefData?.inAnefZone) {
    const anefLevel = constraints.anefData.anefLevel ?? 'refer to ANEF contour map';
    const airport = constraints.anefData.airport?.name ?? 'nearby airport';
    controls.push({
      instrument: 'SEPP (Transport Infrastructure) 2021',
      control: 'Aircraft Noise Attenuation',
      requirement: `ANEF ${anefLevel} — ${airport}. Building acceptability and acoustic treatment requirements apply.`,
      clause: 'SEPP (Transport Infrastructure) 2021 — Aircraft Noise',
      status: 'pending',
    });
  }

  // Contamination — SEPP (Resilience and Hazards) 2021 Chapter 4
  if (constraints.contaminatedLand?.hasNotifiedSites) {
    const nearest = constraints.contaminatedLand.nearestSite;
    const detail = nearest
      ? `Nearest notified site: ${nearest.name ?? 'unknown'} (${nearest.distance ?? '?'}m)`
      : 'Notified contaminated site within 500m';
    controls.push({
      instrument: 'SEPP (Resilience and Hazards) 2021',
      control: 'Site Contamination — Chapter 4',
      requirement: `${detail}. Site contamination assessment required before consent.`,
      clause: 'SEPP (Resilience and Hazards) 2021 Chapter 4',
      status: 'pending',
    });
  }

  // Mine Subsidence — SEPP (Resilience and Hazards) 2021 Chapter 3
  if (constraints.mineSubsidence?.inDistrict) {
    const districtName = constraints.mineSubsidence.districtName;
    controls.push({
      instrument: 'SEPP (Resilience and Hazards) 2021',
      control: 'Mine Subsidence — Chapter 3',
      requirement: `Site in mine subsidence district${districtName ? ` (${districtName})` : ''}. Mine Subsidence Board approval required prior to consent for most building works.`,
      clause: 'SEPP (Resilience and Hazards) 2021 Chapter 3',
      status: 'pending',
    });
  }

  // Landslide Risk — LEP Part 5
  if (constraints.landslideRisk?.hasRisk) {
    controls.push({
      instrument: 'LEP Part 5',
      control: 'Landslide Risk',
      requirement: 'Site in landslide risk area. Geotechnical assessment required. Development consent may be refused if risk cannot be mitigated.',
      clause: 'LEP Clause — Landslide Risk Area',
      status: 'pending',
    });
  }

  // Accelerated TOD — SEPP (Housing) 2021 Part 3B
  if (constraints.acceleratedTOD?.inAcceleratedPrecinct) {
    const precinctName = constraints.acceleratedTOD.precinctName ?? 'Accelerated TOD Precinct';
    const rezoningDate = constraints.acceleratedTOD.expectedRezoning;
    controls.push({
      instrument: 'SEPP (Housing) 2021',
      control: 'Accelerated TOD — Rezoning Precinct',
      requirement: `Site in ${precinctName}${rezoningDate ? ` — expected rezoning: ${rezoningDate}` : ''}. Priority precinct for fast-tracked rezoning under SEPP (Housing) 2021 Part 3B. Modified height and FSR controls apply upon rezoning. Confirm current LEP controls govern until rezoning is gazetted.`,
      clause: 'SEPP (Housing) 2021 Part 3B — Accelerated TOD',
      status: 'pending',
    });
  }

  // Drinking Water Catchment — SEPP (Resilience and Hazards) 2021 Chapter 2
  if (constraints.drinkingWaterCatchment?.inCatchment) {
    controls.push({
      instrument: 'SEPP (Resilience and Hazards) 2021',
      control: 'Drinking Water Catchment — Chapter 2',
      requirement: 'Site in drinking water catchment area. Development must not adversely impact drinking water quality. Consultation with water authority may be required.',
      clause: 'SEPP (Resilience and Hazards) 2021 Chapter 2',
      status: 'pending',
    });
  }

  // Void unused param warning
  void lepClauseData;

  return controls;
}

// ---------------------------------------------------------------------------
// Section 5 — LEP Assessable Standards
// ---------------------------------------------------------------------------

/**
 * Builds LEP development standard rows from property context and LEP clause data.
 * Returns only standards that are applicable — omits null/undefined values.
 */
export function buildLepStandards(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  propertyContext: Record<string, any>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lepClauseData?: Record<string, any>,
  proposedValues?: { height?: string; gfa?: string; lotArea?: number; lepCitation?: string }
): LepAssessableStandard[] {
  const standards: LepAssessableStandard[] = [];

  const zone = propertyContext.zone ?? '';
  const zoneCode = zone.split(' ')[0];
  // lepCitation passed from council config — the authoritative instrument name for this LGA.
  // planning_portal_layers.height_map / fsr_map are string values (not objects), so epiName
  // cannot be derived from them. The council config is the single source of truth for LEP name.
  const lepName = proposedValues?.lepCitation ?? 'Local Environmental Plan';

  // Permitted use — always include, confirms proposed development type is allowed in zone
  if (zoneCode) {
    standards.push({
      clause: '2.3',
      control: 'Permitted Use',
      requirement: `Zone ${zoneCode} — confirm proposed development type is a permitted use with or without consent`,
      status: 'pending',
      source: `${lepName} Clause 2.3 — Land Use Zones`,
    });
  }

  // Height of buildings — Clause 4.3
  const heightLimit = lepClauseData?.height_limit ?? propertyContext.lep_controls?.height;
  if (heightLimit) {
    const heightVal = typeof heightLimit === 'number' ? `${heightLimit}m` : `${heightLimit}m`;
    const proposedH = proposedValues?.height ? parseFloat(proposedValues.height) : undefined;
    const limitNum = parseFloat(String(heightLimit));
    const heightStatus: 'complies' | 'varies' | 'pending' =
      proposedH && !isNaN(limitNum) ? (proposedH <= limitNum ? 'complies' : 'varies') : 'pending';
    standards.push({
      clause: '4.3',
      control: 'Height of Buildings',
      requirement: `Maximum ${heightVal}`,
      proposal: proposedH ? `${proposedH}m` : undefined,
      status: heightStatus,
      source: `${lepName} Clause 4.3`,
    });
  }

  // Floor space ratio — Clause 4.4
  const fsr = lepClauseData?.fsr ?? propertyContext.lep_controls?.fsr;
  if (fsr) {
    const proposedGfa = proposedValues?.gfa ? parseFloat(proposedValues.gfa) : undefined;
    const lotArea = proposedValues?.lotArea ?? propertyContext.lot_dimensions?.area;
    const fsrNum = parseFloat(String(fsr));
    let fsrProposal: string | undefined;
    let fsrStatus: 'complies' | 'varies' | 'pending' = 'pending';
    if (proposedGfa && lotArea && !isNaN(fsrNum)) {
      const proposedFsr = proposedGfa / lotArea;
      fsrProposal = `${proposedGfa} m² GFA (${proposedFsr.toFixed(2)}:1)`;
      fsrStatus = proposedFsr <= fsrNum ? 'complies' : 'varies';
    }
    standards.push({
      clause: '4.4',
      control: 'Floor Space Ratio',
      requirement: `Maximum ${fsr}:1`,
      proposal: fsrProposal,
      status: fsrStatus,
      source: `${lepName} Clause 4.4`,
    });
  }

  // Heritage — Clause 5.10
  const inHca = propertyContext.heritage_status?.in_hca;
  const heritageItem = propertyContext.heritage_status?.heritage_item;
  if (heritageItem) {
    standards.push({
      clause: '5.10',
      control: 'Heritage Conservation — Listed Item',
      requirement: `Heritage item ${propertyContext.heritage_status?.item_number ?? ''} — heritage impact assessment and consent required. Heritage Impact Statement must accompany DA.`,
      status: 'pending',
      source: `${lepName} Clause 5.10`,
    });
  } else if (inHca) {
    const hcaName = propertyContext.heritage_status?.hca_name ?? 'Heritage Conservation Area';
    const hcaCode = propertyContext.heritage_status?.hca_code ?? '';
    standards.push({
      clause: '5.10',
      control: 'Heritage Conservation Area',
      requirement: `${hcaName}${hcaCode ? ` (${hcaCode})` : ''} — development must not adversely affect the heritage significance of the conservation area. Statement of Heritage Impact required.`,
      status: 'pending',
      source: `${lepName} Clause 5.10`,
    });
  }

  // Additional local provisions — Clause 6.x (LEP Part 6)
  const localProvisions: string[] = propertyContext.additional_local_provisions ?? [];
  for (const provision of localProvisions) {
    standards.push({
      clause: '6.x',
      control: 'Additional Local Provision',
      requirement: provision,
      status: 'pending',
      source: `${lepName} Part 6`,
    });
  }

  return standards;
}

// ---------------------------------------------------------------------------
// Section 2 — Site Context (spatial data supplement)
// ---------------------------------------------------------------------------

/**
 * Builds deterministic prose for SEE Section 2 Site Context from spatial data.
 * Returns null if insufficient data to produce a meaningful sentence.
 *
 * Output is intended to be appended to siteSuitabilityText in section-aggregation.ts
 * once spatial data is wired into the SEE export flow.
 *
 * OSM attribution note is always appended when data is used.
 */
export function buildSiteContextSection(
  amenity: AmenityData | null,
  streetContext: StreetContextData | null,
  suburb: string,
): string | null {
  const sentences: string[] = [];

  if (streetContext && streetContext.data_confidence !== 'low') {
    const hierarchy = streetContext.street_hierarchy;
    const name = streetContext.street_name ?? 'the local street';
    sentences.push(
      `The site fronts ${name}, a ${hierarchy} road in ${suburb}.`
    );
    if (streetContext.solar_orientation?.solar_access === 'good') {
      sentences.push('Street orientation is favourable for passive solar access.');
    } else if (streetContext.solar_orientation?.solar_access === 'poor') {
      sentences.push('Street orientation is unfavourable for passive solar access — this should be considered in the design response.');
    }
  }

  if (amenity) {
    const score = amenity.walkability_score;
    const categories = (['schools', 'transport', 'parks', 'shops', 'medical'] as const)
      .filter(k => amenity[k] && (amenity[k]!.walking_m) <= 800)
      .map(k => k);

    if (score >= 3 && categories.length > 0) {
      sentences.push(
        `The site has good access to local services, with ${categories.join(', ')} within 800m walking distance (walkability score ${score}/5).`
      );
    } else if (score <= 2) {
      sentences.push(
        `The site has limited walkable access to services (walkability score ${score}/5). Private vehicle access or public transport should be considered in the site analysis.`
      );
    } else {
      sentences.push(`Local service walkability: ${score}/5.`);
    }
  }

  if (sentences.length === 0) return null;

  sentences.push('(Spatial data sourced from OpenStreetMap contributors via city2graph. Verify on site before including in a statutory document.)');
  return sentences.join(' ');
}
