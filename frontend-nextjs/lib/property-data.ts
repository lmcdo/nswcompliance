/**
 * Property data service for NSW property information
 * Integrates with NSW Planning Portal APIs for real property data
 */

import {
 NSWPlanningPortalService,
 NSWPropertyData,
 PlanningConstraints,
 TODPrecinctInfo,
 AcceleratedTODInfo,
 HIAInfo,
 AnefInfo,
 LotGeometryData,
 StrataInfo,
} from './nsw-planning-portal';
import { SeppRouter, SeppRoutingResult } from './sepp-router';
import { determineFormerCouncilArea as determineFormerCouncilAreaUtil } from './inner-west-mapping';
import { detectLGAFromName, tryGetLGAConfig } from './lga-configs';
import { getSiteSpecificClauses, getSiteSpecificProvisionDetails } from './site-specific-part6-mapping';
import { calculateLotDimensions, type LotDimensions } from './geometry/lot-dimensions';
import { deriveAnefBuildingAcceptability } from './see/propertyUtils';
import { detectCornerLot, type CornerLotResult } from './geometry/corner-lot-detection';

// Re-export TOD/HIA interfaces for use in components
export type { TODPrecinctInfo, AcceleratedTODInfo, HIAInfo };

export interface PropertyConstraints extends PlanningConstraints {
 applicableSepps?: string[];
}

export interface SourceInfo {
 clause: string;
 legislationUrl: string;
 epiName: string;
 amendment?: string;
 commencedDate?: string;
 publishedDate?: string;
 currencyDate?: string;
 lgaName?: string;
 units?: string;
 value?: string;
 title?: string;
}

export interface PropertyData {
 propId: number;
 address: string;
 landValue: string;
 valuationDate: string;
 propertyArea: string;
 zoneDescription: string;
 urbanity: string;
 constraints: PropertyConstraints;
 fsrSource?: SourceInfo;
 heightSource?: SourceInfo;
 minLotSizeSource?: SourceInfo;
 heritage?: {
 isHeritage: boolean;
 heritageType?: string;
 heritageItemName?: string;
 heritageItemNumber?: string;
 heritageClause?: string;
 heritageSignificance?: string;
 heritageLegislationUrl?: string;
 };
 environmental?: {
 acidSulfateSoils?: string;
 basixClimate?: string;
 basixWater?: string;
 floodProne: boolean;
 bushfireProne: boolean;
 };
 geometry: {
 x: number;
 y: number;
 };
 coordinates?: {
 lat: number;
 lon: number;
 };
 seppRouting?: SeppRoutingResult;
 planningLayers?: PlanningLayer[];
 roadClassifications?: any[];
 anefData?: AnefInfo | null;
 lotDetails?: LotDetails;
 lotDimensions?: LotDimensions | null;
 cornerLot?: CornerLotResult | null;
 council?: string;
 strataInfo?: StrataInfo;
}

export interface PlanningLayer {
 id: string;
 layerName: string;
 results: LayerResult[];
}

export interface LayerResult {
 [key: string]: any; // Allow any property from the API
}

export interface LotDetails {
 cadId?: number;
 lotDescription?: string;
 geometry?: any;
}

/**
 * Service for fetching property compliance data from NSW Planning Portal
 */
export class PropertyDataService {
 /**
 * Gets comprehensive property data for compliance checking
 * Uses real NSW Planning Portal APIs
 */
 static async getPropertyComplianceData(address: string): Promise<PropertyData> {
 try {
 // Get real data from NSW Planning Portal
 const nswData = await NSWPlanningPortalService.getPropertyComplianceData(address);
 
 if (!nswData) {
 throw new Error('Property not found in NSW Planning Portal');
 }

 const { propertyData, constraints, layers, roadClassifications, anefData, lotGeometry, strataInfo } = nswData;

 // Derive ANEF building acceptability from level (AS 2021-2015 Table 2.1).
 // NSW Portal only returns anefLevel — per-type acceptability must be derived.
 const enrichedAnefData = anefData
  ? { ...anefData, buildingAcceptability: deriveAnefBuildingAcceptability(anefData.anefLevel ?? null) }
  : null;

 // Calculate lot dimensions (sync) and detect corner lot (async) in parallel
 let lotDimensions: LotDimensions | null = null;
 let cornerLotPromise: Promise<CornerLotResult | null> = Promise.resolve(null);

 if (lotGeometry?.geometry) {
 lotDimensions = calculateLotDimensions(lotGeometry.geometry);
 cornerLotPromise = detectCornerLot(lotGeometry.geometry);
 }

 // Extract source information from layers
 const fsrLayer = layers.find(l => l.layerName === 'Floor Space Ratio Map');
 const heightLayer = layers.find(l => l.layerName === 'Height of Buildings Map');
 const lotSizeLayer = layers.find(l => l.layerName === 'Lot Size Map');
 const heritageLayer = layers.find(l => l.layerName === 'Heritage Map');

 // Build source info with ALL available metadata
 const fsrSource = fsrLayer?.results?.[0] ? {
 clause: fsrLayer.results[0]['Legislative Clause'] || 'Unknown',
 legislationUrl: fsrLayer.results[0]['legislationUrl'] || '',
 epiName: fsrLayer.results[0]['EPI Name'] || 'Unknown',
 amendment: fsrLayer.results[0]['Amendment'] || undefined,
 commencedDate: fsrLayer.results[0]['Commenced Date'] || undefined,
 publishedDate: fsrLayer.results[0]['Published Date'] || undefined,
 currencyDate: fsrLayer.results[0]['Currency Date'] || undefined,
 lgaName: fsrLayer.results[0]['LGA Name'] || undefined,
 title: fsrLayer.results[0]['title'] || undefined,
 value: fsrLayer.results[0]['Floor Space Ratio'] || undefined
 } : undefined;

 const heightSource = heightLayer?.results?.[0] ? {
 clause: heightLayer.results[0]['Legislative Clause'] || 'Unknown',
 legislationUrl: heightLayer.results[0]['legislationUrl'] || '',
 epiName: heightLayer.results[0]['EPI Name'] || 'Unknown',
 amendment: heightLayer.results[0]['Amendment'] || undefined,
 commencedDate: heightLayer.results[0]['Commenced Date'] || undefined,
 publishedDate: heightLayer.results[0]['Published Date'] || undefined,
 currencyDate: heightLayer.results[0]['Currency Date'] || undefined,
 lgaName: heightLayer.results[0]['LGA Name'] || undefined,
 units: heightLayer.results[0]['Units'] || undefined,
 title: heightLayer.results[0]['title'] || undefined,
 value: heightLayer.results[0]['Maximum Building Height'] || undefined
 } : undefined;

 const minLotSizeSource = lotSizeLayer?.results?.[0] ? {
 clause: lotSizeLayer.results[0]['Legislative Clause'] || 'Unknown',
 legislationUrl: lotSizeLayer.results[0]['legislationUrl'] || '',
 epiName: lotSizeLayer.results[0]['EPI Name'] || 'Unknown'
 } : undefined;

 // Heritage information - extract all available fields
 const heritage = constraints.heritage ? {
 isHeritage: true,
 heritageType: constraints.heritageType,
 heritageItemName: constraints.heritageItemName,
 heritageItemNumber: constraints.heritageItemNumber,
 heritageClause: constraints.heritageLegislativeClause,
 heritageSignificance: constraints.heritageSignificance,
 heritageLegislationUrl: constraints.heritageLegislationUrl
 } : { isHeritage: false };

 // Environmental constraints - use extracted data or provide defaults
 const environmental = {
 acidSulfateSoils: constraints.acidSulfateSoils || 'Class 5',
 basixClimate: constraints.basixClimate || 'Class 5',
 basixWater: constraints.basixWater || '40%',
 floodProne: constraints.floodProne,
 bushfireProne: constraints.bushfireProne
 };

 // Convert Web Mercator (x, y) to WGS84 (lat, lon) for geocoding
 const lon = (propertyData.geometry.x / 20037508.34) * 180;
 const lat = (Math.atan(Math.exp((propertyData.geometry.y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;

 // Load precinct service and suburb mapping in parallel
 const [precinctModule, suburbModule] = await Promise.all([
   import('./precinct-service').catch(() => null),
   import('./inner-west-mapping-v2').catch(() => null)
 ]);

 // Match precinct for DCP filtering - precinct data includes formerCouncil from spatial match
 if (precinctModule) {
   try {
     const precinctData = await precinctModule.getPrecinctForAddress(
       propertyData.address,
       constraints.lga || '',
       { lat, lon }
     );

     if (precinctData) {
       constraints.precinctId = precinctData.precinctId;
       constraints.precinctName = precinctData.precinctName;
       if (precinctData.formerCouncil) {
         constraints.formerCouncil = precinctData.formerCouncil;
       }
     }
   } catch (error) {
     console.error('[PropertyDataService] Precinct matching failed:', error);
   }
 }

 // Suburb name matching overrides precinct-derived council for boundary cases like Petersham
 if (suburbModule) {
   try {
     const suburbBasedCouncil = suburbModule.determineFormerCouncilArea(propertyData.address, constraints.lga || '');
     if (suburbBasedCouncil) {
       constraints.formerCouncil = suburbBasedCouncil;
     }
   } catch (error) {
     console.error('[PropertyDataService] Former council mapping failed:', error);
   }
 }

 // Chapter D precinct locality fallback: if PostGIS found no precinct and formerCouncil is now
 // known, query dcp_precinct_localities to match the address suburb against the DB-owned mapping.
 // Must run after suburbModule so formerCouncil is populated.
 if (!constraints.precinctId && constraints.formerCouncil && precinctModule) {
   try {
     const localityPrecinctIds = await precinctModule.getPrecinctFromLocality(
       propertyData.address,
       constraints.formerCouncil,
     );
     if (localityPrecinctIds && localityPrecinctIds.length > 0) {
       constraints.precinctId = localityPrecinctIds.join(',');
       constraints.precinctName = localityPrecinctIds[0];
       console.log(`[PropertyDataService] Locality precinct match: '${constraints.formerCouncil}' → '${constraints.precinctId}'`);
     }
   } catch (error) {
     console.error('[PropertyDataService] Locality precinct lookup failed:', error);
   }
 }

 // For single-council LGAs (e.g. Waverley) the inner-west mapping returns null.
 // Fall back to the LGA config key so the provisions API gets a former_council param.
 if (!constraints.formerCouncil && constraints.lga) {
   try {
     const lgaId = detectLGAFromName(constraints.lga);
     if (lgaId) {
       const lgaConfig = tryGetLGAConfig(lgaId);
       if (lgaConfig && lgaConfig.type === 'single') {
         constraints.formerCouncil = lgaId;
         console.log(`[PropertyDataService] Single-council LGA fallback: formerCouncil = '${lgaId}'`);
       }
     }
   } catch (error) {
     console.error('[PropertyDataService] LGA config fallback failed:', error);
   }
 }

 // Final fallback: for LGAs without a JSON config (e.g. Canterbury-Bankstown, Penrith)
 // normalize the LGA name to a slug so DcpStructuredControls can query dcp_setback_controls.
 // This only fires if formerCouncil is still unset after precinct, suburb, and config lookups.
 if (!constraints.formerCouncil && constraints.lga) {
   const slug = constraints.lga.toLowerCase().trim()
     .replace(/[-\s]+/g, '_')
     .replace(/[^a-z0-9_]/g, '');
   if (slug) {
     constraints.formerCouncil = slug;
     console.log(`[PropertyDataService] LGA slug fallback: formerCouncil = '${slug}'`);
   }
 }

    // Match site-specific Part 6 LEP clauses (based on address and heritage item)
    try {
      const siteSpecificClauseNumbers = getSiteSpecificClauses(propertyData.address);

      // Special case: Haberfield Heritage Conservation Area (C54) -> Clause 6.20
      if (constraints.heritage && constraints.heritageItemNumber === 'C54') {
        if (!siteSpecificClauseNumbers.includes('6.20')) {
          siteSpecificClauseNumbers.push('6.20');
        }
      }

      if (siteSpecificClauseNumbers.length > 0) {
        if (!constraints.localProvisions) {
          constraints.localProvisions = [];
        }

        for (const clauseNumber of siteSpecificClauseNumbers) {
          const details = getSiteSpecificProvisionDetails(clauseNumber);
          if (details) {
            constraints.localProvisions.push({
              title: details.title,
              clauseNumber: clauseNumber,
              pageNumber: details.pageNumber,
              mapType: 'Site-Specific',
              legislationUrl: constraints.heritageLegislationUrl,
              epiName: constraints.lga ? `${constraints.lga} Local Environmental Plan 2022` : undefined
            });
          }
        }
      }
    } catch (error) {
      console.error('[PropertyDataService] Site-specific clause matching failed:', error);
    }

 // Route applicable SEPPs
 const seppRouter = new SeppRouter();
 let applicableSepps = constraints.applicableSepps || [];

 applicableSepps = seppRouter.addContextualSepps(
 'residential_low', // TODO: determine from zone and property
 propertyData.zoneDescription || 'R2',
 heritage.isHeritage,
 applicableSepps
 );

 const seppRouting = seppRouter.routeApplicableSepps(applicableSepps);

 // Resolve corner lot detection (started earlier in parallel with other work)
 const cornerLot = await cornerLotPromise;

 return {
 propId: propertyData.propId,
 address: propertyData.address,
 landValue: propertyData.landValue,
 valuationDate: propertyData.valuationDate,
 propertyArea: propertyData.propertyArea,
 zoneDescription: propertyData.zoneDescription,
 urbanity: propertyData.urbanity,
 constraints,
 fsrSource,
 heightSource,
 minLotSizeSource,
 heritage,
 environmental,
 geometry: propertyData.geometry,
 coordinates: { lat, lon }, // FIX: Add WGS84 coordinates for precinct matching
 seppRouting,
 planningLayers: layers as any, // Pass through ALL layer data
 roadClassifications, // Road functional hierarchy for setback calculations
 anefData: enrichedAnefData, // Aircraft noise exposure forecast data (with derived building acceptability)
 lotDetails: lotGeometry ? {
 cadId: lotGeometry.cadId,
 lotDescription: lotGeometry.lotDescription,
 geometry: lotGeometry.geometry
 } : undefined,
 lotDimensions, // Calculated frontage, depth, area from lot geometry
 cornerLot, // Corner lot detection from adjacent road parcels
 strataInfo,
 };
 
 } catch (error) {
 console.error('Failed to get NSW Planning Portal data:', error);

 // Don't return fallback data - throw error with clear message
 if (error instanceof Error && error.message.includes('abort')) {
   throw new Error('NSW Planning Portal API request timed out. Please try again.');
 }

 if (error instanceof Error && error.message.includes('Property not found')) {
   throw new Error('Property not found in NSW Planning Portal. Please check the address.');
 }

 throw new Error('NSW Planning Portal API not responding. Please try again or check your internet connection.');
 }
 }

 // Fallback data removed - errors now propagate to UI with clear messages
 
 /**
 * Extracts lot size from property area string
 */
 static extractLotSize(propertyAreaString: string): number | null {
 const match = propertyAreaString.match(/([\d.]+)/);
 return match ? parseFloat(match[0]) : null;
 }

 /**
 * Determines former Inner West council area from LGA and address
 * Uses suburb names from NSW Planning Portal address instead of unreliable geometry
 */
 static determineFormerCouncilArea(propertyData: PropertyData): string | null {
 // Special case for demo - treat Telopea as Ashfield for testing
 if (propertyData.address?.toLowerCase().includes('telopea') || 
 propertyData.address?.toLowerCase().includes('wilkinson')) {
 console.log('DEMO: Treating Telopea address as Ashfield for testing unified integration');
 return 'Ashfield';
 }

    // Use the shared utility function
    return determineFormerCouncilAreaUtil(propertyData.address, propertyData.constraints.lga || '');
}
}
