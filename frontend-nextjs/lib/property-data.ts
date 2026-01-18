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
 LotGeometryData
} from './nsw-planning-portal';
import { SeppRouter, SeppRoutingResult } from './sepp-router';
import { determineFormerCouncilArea as determineFormerCouncilAreaUtil } from './inner-west-mapping';
import { getSiteSpecificClauses, getSiteSpecificProvisionDetails } from './site-specific-part6-mapping';
import { calculateLotDimensions, type LotDimensions } from './geometry/lot-dimensions';
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

 const { propertyData, constraints, layers, roadClassifications, anefData, lotGeometry } = nswData;

 // Calculate lot dimensions from geometry
 let lotDimensions: LotDimensions | null = null;
 if (lotGeometry?.geometry) {
 lotDimensions = calculateLotDimensions(lotGeometry.geometry);
 if (lotDimensions) {
 console.log(`[PropertyDataService] Calculated lot dimensions: frontage=${lotDimensions.frontage}m, depth=${lotDimensions.depth}m, area=${lotDimensions.area}m²`);
 }
 }

 // Detect corner lot from adjacent road parcels
 let cornerLot: CornerLotResult | null = null;
 if (lotGeometry?.geometry) {
 cornerLot = await detectCornerLot(lotGeometry.geometry);
 if (cornerLot.confidence > 0) {
 console.log(`[PropertyDataService] Corner lot detection: isCornerLot=${cornerLot.isCornerLot}, roads=[${cornerLot.adjacentRoads.join(', ')}]`);
 } else if (cornerLot.error) {
 console.warn(`[PropertyDataService] Corner lot detection failed: ${cornerLot.error}`);
 }
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
 // Formula from nsw-planning-portal.ts lines 637-640
 const lon = (propertyData.geometry.x / 20037508.34) * 180;
 const lat = (Math.atan(Math.exp((propertyData.geometry.y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;
 console.log(`[PropertyDataService] Converted coordinates: Web Mercator (${propertyData.geometry.x}, ${propertyData.geometry.y}) → WGS84 (lat: ${lat.toFixed(6)}, lon: ${lon.toFixed(6)})`);

 // Match precinct for DCP filtering - precinct data includes formerCouncil from spatial match
 try {
   const { getPrecinctForAddress } = await import('./precinct-service');
   const precinctData = await getPrecinctForAddress(
     propertyData.address,
     constraints.lga || '',
     { lat, lon }  // Pass coordinates with correct property names
   );

   if (precinctData) {
     constraints.precinctId = precinctData.precinctId;
     console.log(`[PropertyDataService] Precinct matched: ${precinctData.precinctId} (${precinctData.precinctName})`);

     // Use formerCouncil from precinct spatial match (most reliable)
     if (precinctData.formerCouncil) {
       constraints.formerCouncil = precinctData.formerCouncil;
       console.log(`[PropertyDataService] Former council from precinct: ${precinctData.formerCouncil}`);
     }
   }
 } catch (error) {
   console.log('[PropertyDataService] Precinct matching failed:', error);
 }

 // ALWAYS check suburb name for former council - more reliable than precinct boundaries
 // Suburb name matching overrides precinct-derived council for boundary cases like Petersham
 try {
   const { determineFormerCouncilArea } = await import('./inner-west-mapping-v2');
   const suburbBasedCouncil = determineFormerCouncilArea(propertyData.address, constraints.lga || '');
   if (suburbBasedCouncil) {
     if (constraints.formerCouncil && constraints.formerCouncil !== suburbBasedCouncil) {
       console.log(`[PropertyDataService] Suburb override: ${constraints.formerCouncil} → ${suburbBasedCouncil}`);
     }
     constraints.formerCouncil = suburbBasedCouncil;
     console.log(`[PropertyDataService] Former council from suburb: ${suburbBasedCouncil}`);
   }
 } catch (error) {
   console.log('[PropertyDataService] Former council mapping failed:', error);
 }


    // Match site-specific Part 6 LEP clauses (based on address and heritage item)
    try {
      const siteSpecificClauseNumbers = getSiteSpecificClauses(propertyData.address);
      
      // Special case: Haberfield Heritage Conservation Area (C54) -> Clause 6.20
      if (constraints.heritage && constraints.heritageItemNumber === 'C54') {
        if (!siteSpecificClauseNumbers.includes('6.20')) {
          siteSpecificClauseNumbers.push('6.20');
          console.log('[PropertyDataService] Added Clause 6.20 for Haberfield HCA (C54)');
        }
      }
      
      if (siteSpecificClauseNumbers.length > 0) {
        console.log(`[PropertyDataService] Found ${siteSpecificClauseNumbers.length} site-specific Part 6 clause(s): ${siteSpecificClauseNumbers.join(', ')}`);
        
        // Initialize localProvisions array if not exists
        if (!constraints.localProvisions) {
          constraints.localProvisions = [];
        }
        
        // Add each site-specific clause as a LocalProvision
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
      console.log('[PropertyDataService] Site-specific clause matching failed:', error);
    }

 // Route applicable SEPPs
 const seppRouter = new SeppRouter();
 let applicableSepps = constraints.applicableSepps || [];

 // Add contextual SEPPs based on development characteristics
 applicableSepps = seppRouter.addContextualSepps(
 'residential_low', // TODO: determine from zone and property
 propertyData.zoneDescription || 'R2',
 heritage.isHeritage,
 applicableSepps
 );

 const seppRouting = await seppRouter.routeApplicableSepps(applicableSepps);
 console.log('SEPP Routing Result:', seppRouting);

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
 planningLayers: layers, // Pass through ALL layer data
 roadClassifications, // Road functional hierarchy for setback calculations
 anefData, // Aircraft noise exposure forecast data
 lotDetails: lotGeometry ? {
 cadId: lotGeometry.cadId,
 lotDescription: lotGeometry.lotDescription,
 geometry: lotGeometry.geometry
 } : undefined,
 lotDimensions, // Calculated frontage, depth, area from lot geometry
 cornerLot // Corner lot detection from adjacent road parcels
 };
 
 } catch (error) {
 console.error('Failed to get NSW Planning Portal data:', error);

 // Don't return fallback data - throw error with clear message
 if (error instanceof Error && error.message.includes('abort')) {
   throw new Error('NSW Planning Portal API request timed out after 5 seconds. Please try again.');
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
