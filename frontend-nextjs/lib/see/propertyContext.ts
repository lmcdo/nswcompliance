// lib/see/propertyContext.ts
// Shared helpers for building PDF/SEE export data from raw propertyData + lepClauseData.
// Extracted from ProvisionsByTocStructure.tsx (W3-1, W3-2).

import { PropertyContext, ProvisionForPDF } from '@/lib/pdf/types';

export function sanitizeText(text: string | undefined | null): string {
  if (!text) return '';
  return text
    .replace(/â€"/g, '—')
    .replace(/â€˜/g, "'")
    .replace(/â€™/g, "'")
    .replace(/â€œ/g, '"')
    .replace(/â€\u009D/g, '"')
    .replace(/â˜…/g, '★')
    .replace(/Â²/g, '²')
    .replace(/Â°/g, '°')
    .replace(/â€¢/g, '•')
    .replace(/â€¦/g, '…')
    .replace(/Ã©/g, 'é')
    .replace(/Ã¨/g, 'è')
    // Fix spacing artifacts in numbers
    .replace(/(\d)\s+(\d)\s+(\d)\s+(m|c|k)\s+m\s+\$/g, '$1$2$3$4m')  // "1 8 0 m m $" -> "180mm"
    .replace(/\s+\$/g, '')  // Remove trailing "$" artifacts
    .replace(/,\s*#\s*/g, ', ')  // ", #" -> ", "
    .replace(/[\u2018\u2019\u201C\u201D]/g, (match) => {  // Smart quotes to regular quotes
      return match === '\u2018' || match === '\u2019' ? "'" : '"';
    })
    .replace(/·/g, ' · ')  // Fix middle dot spacing
    .replace(/\s{2,}/g, ' ')  // Multiple spaces to single
    .replace(/^[â€"\s]+/, '')
    .trim();
}

/**
 * Clean a raw DB section title for display in the DA mode section list.
 * Handles: UTF-8 corruption (via sanitizeText), trailing dots/spaces, ALL-CAPS → Title Case.
 */
export function cleanSectionTitle(text: string | undefined | null): string {
  const cleaned = sanitizeText(text);
  if (!cleaned) return '';
  // Strip trailing dots and whitespace
  const stripped = cleaned.replace(/[.\s]+$/, '').trim();
  if (!stripped) return '';
  // If the string is all-uppercase (and longer than 3 chars to avoid "C1"), convert to Title Case
  const isAllCaps = stripped === stripped.toUpperCase() && stripped.length > 3 && /[A-Z]/.test(stripped);
  if (!isAllCaps) return stripped;
  return stripped
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Sanitize a number for PDF rendering — returns undefined for invalid or negative values */
function sanitizeNumber(value: unknown): number | undefined {
  if (value === null || value === undefined) return undefined;
  const num = typeof value === 'number' ? value : parseFloat(String(value));
  if (isNaN(num) || !isFinite(num) || Math.abs(num) > 1e15 || num < 0) return undefined;
  return Math.round(num * 100) / 100;
}

/** Extract primary value field from planning portal layer results, skipping metadata keys */
function getLayerValue(results: unknown[] | undefined): string | undefined {
  if (!Array.isArray(results) || !results[0]) return undefined;
  const result = results[0] as Record<string, unknown>;
  const metadataKeys = new Set([
    'Legislative Clause', 'legislationUrl', 'EPI Name', 'Amendment',
    'Commenced Date', 'Published Date', 'Currency Date', 'LGA Name',
    'Units', 'title', 'OBJECTID', 'Shape', 'Shape_Length', 'Shape_Area', 'GlobalID',
  ]);
  const valuesToSkip = new Set(['LEP', 'SEPP', '']);
  for (const key of Object.keys(result)) {
    const value = result[key];
    if (!metadataKeys.has(key) && value != null && !valuesToSkip.has(String(value))) {
      return String(value);
    }
  }
  return undefined;
}

export interface HeritageInput {
  in_hca: boolean;
  hca_name?: string;
  hca_code?: string;
  heritage_item?: boolean;
  item_name?: string;
  item_number?: string;
}

/**
 * Build a PropertyContext from raw property/LEP data.
 * Pure function — no side effects, no async, no fetch calls.
 * Callers can spread in additional PDF-only fields (pattern_book_cdc, pathway_summary).
 */
export function buildPropertyContext(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  propertyData: any,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lepClauseData: any,
  address: string | undefined,
  zone: string | undefined,
  formerCouncil: string,
  heritage: HeritageInput,
  devDescription?: string,
): PropertyContext {
  // Lot dimensions
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nearbyRoads: any[] = propertyData?.nearbyRoads || [];
  const isCornerLot = nearbyRoads.length >= 2;
  const areaNum = sanitizeNumber(propertyData?.lotDimensions?.area);
  const frontageNum = sanitizeNumber(propertyData?.lotDimensions?.frontage);
  const depthNum = sanitizeNumber(propertyData?.lotDimensions?.depth);
  const lotDimensions =
    areaNum !== undefined || frontageNum !== undefined || depthNum !== undefined
      ? {
          area: areaNum,
          frontage: frontageNum,
          depth: depthNum,
          is_corner: isCornerLot,
          corner_roads: isCornerLot ? nearbyRoads.slice(0, 2).map((r) => r.road_name) : [],
        }
      : undefined;

  // LEP controls
  const lepControls = lepClauseData
    ? {
        height: lepClauseData.height_limit || undefined,
        fsr: lepClauseData.fsr || undefined,
        acid_sulfate_soils: lepClauseData.acid_sulfate_soils || undefined,
        permitted_uses: lepClauseData.permitted_uses || [],
        prohibited_uses: lepClauseData.prohibited_uses || [],
      }
    : undefined;

  // Planning portal layers
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const layers: any[] | undefined = propertyData?.planningLayers;
  const planningPortalLayers = layers
    ? {
        heritage_map: getLayerValue(layers.find((l) => l.layerName?.includes('Heritage'))?.results),
        fsr_map: getLayerValue(layers.find((l) => l.layerName?.includes('Floor Space'))?.results),
        height_map: getLayerValue(layers.find((l) => l.layerName?.includes('Height'))?.results),
        acid_sulfate_soils_map: getLayerValue(layers.find((l) => l.layerName?.includes('Acid Sulfate'))?.results),
        local_aboriginal_land_council: getLayerValue(layers.find((l) => l.layerName?.includes('Aboriginal'))?.results),
        sepp_requirements: getLayerValue(layers.find((l) => l.layerName?.includes('Special Provisions'))?.results),
        land_application_map: getLayerValue(layers.find((l) => l.layerName?.includes('Land Application'))?.results),
        regional_plan_boundary: getLayerValue(layers.find((l) => l.layerName?.includes('Regional Plan'))?.results),
        land_zoning_map: getLayerValue(layers.find((l) => l.layerName?.includes('Zoning'))?.results),
        tree_canopy_2019: getLayerValue(layers.find((l) => l.layerName?.includes('2019'))?.results),
        tree_canopy_2022: getLayerValue(layers.find((l) => l.layerName?.includes('2022'))?.results),
        tree_canopy_coverage_class: propertyData?.constraints?.treeCanopy?.coverageClass || undefined,
        terrestrial_biodiversity_map: getLayerValue(layers.find((l) => l.layerName?.includes('Biodiversity'))?.results),
      }
    : undefined;

  // Environmental constraints
  const envC = propertyData?.constraints;
  const anef = propertyData?.anefData;
  const environmentalConstraints = envC
    ? {
        flood_prone: !!envC.floodProne,
        bushfire_prone: !!envC.bushfireProne,
        acid_sulfate_soils: envC.acidSulfateSoils || undefined,
        anef_zone: !!anef?.inAnefZone,
        anef_level: anef?.anefLevel,
        anef_code: anef?.anefCode,
        mine_subsidence: !!envC.mineSubsidence?.inDistrict,
        mine_subsidence_district: envC.mineSubsidence?.districtName,
        landslide_risk: !!envC.landslideRisk?.hasRisk,
        contaminated_land: !!envC.contaminatedLand?.hasNotifiedSites,
        contaminated_site_name: envC.contaminatedLand?.nearestSite?.name,
        contaminated_site_distance: envC.contaminatedLand?.nearestSite?.distance,
        contaminated_management_class: envC.contaminatedLand?.nearestSite?.managementClass || undefined,
        contaminated_type: envC.contaminatedLand?.nearestSite?.contaminationType || undefined,
        landslide_risk_class: envC.landslideRisk?.layClass || undefined,
        drinking_water_catchment: !!envC.drinkingWaterCatchment?.inCatchment,
        terrestrial_biodiversity: !!envC.terrestrialBiodiversity?.inBiodiversityArea,
        coastal_management: !!(envC.coastalEnvironment?.inCoastalArea && envC.coastalEnvironment?.zones?.length),
        coastal_zones: envC.coastalEnvironment?.zones,
      }
    : undefined;

  // Additional local provisions (clause 6.x)
  const additionalLocalProvisions: string[] | undefined =
    envC?.localProvisions && envC.localProvisions.length > 0
      ? envC.localProvisions
          .filter((p: { isNearby?: boolean }) => !p.isNearby)
          .map((p: { clauseNumber?: string; title: string; description?: string }) => {
            const clause = p.clauseNumber ? `Clause ${p.clauseNumber}: ` : '';
            const desc = p.description ? ` — ${p.description}` : '';
            return `${clause}${p.title}${desc}`;
          })
      : undefined;

  return {
    address: address || propertyData?.address || 'Property Address',
    zone: zone || 'Unknown',
    former_council: formerCouncil,
    heritage_status: {
      in_hca: heritage.in_hca,
      hca_name: heritage.hca_name,
      hca_code: heritage.hca_code,
      heritage_item: heritage.heritage_item,
      item_name: heritage.item_name,
      item_number: heritage.item_number,
    },
    lot_dimensions: lotDimensions,
    lep_controls: lepControls,
    planning_portal_layers: planningPortalLayers,
    environmental_constraints: environmentalConstraints,
    additional_local_provisions: additionalLocalProvisions,
    development_description: devDescription,
  };
}

/**
 * Map raw provisions to ProvisionForPDF[], filtering Table of Contents entries.
 * Applies defensive sanitization to provision text and page numbers.
 */
export async function preparePdfProvisions(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  provisions: any[],
  daResponses?: Map<number, { compliance_status: string | null; response_text?: string | null }>,
): Promise<ProvisionForPDF[]> {
  const { isTableOfContents } = await import('@/lib/pdf/formatProvisions');
  return provisions
    .filter((p) => !isTableOfContents(p.provision_text || ''))
    .map((p) => {
      const rawPage = sanitizeNumber(p.pdf_page);
      const pdfPage = rawPage !== undefined ? Math.round(rawPage) : undefined;
      const rawPrinted = sanitizeNumber(p.pdf_printed_page);
      const pdfPrintedPage = rawPrinted !== undefined ? Math.round(rawPrinted) : pdfPage ?? 1;
      const daResponse = daResponses?.get(p.id);
      return {
        id: p.id,
        provision_text: sanitizeText(p.provision_text),
        v2_marker: p.v2_marker || '',
        v2_topic: p.v2_topic || '',
        document_name: p.document_name || '',
        v2_dcp_part: p.v2_dcp_part || '',
        section_header: p.section_header,
        pdf_page: pdfPage,
        pdf_printed_page: pdfPrintedPage,
        v2_is_actionable: p.v2_is_actionable,
        zone_applicability: p.zone_applicability,
        ref_number: p.ref_number,
        ...(daResponse?.compliance_status && {
          da_status: daResponse.compliance_status as 'complies' | 'varies' | 'not_applicable',
          ...(daResponse.response_text && { da_response: daResponse.response_text }),
        }),
      } satisfies ProvisionForPDF;
    });
}
