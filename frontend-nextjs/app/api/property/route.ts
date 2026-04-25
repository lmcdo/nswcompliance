import { NextRequest, NextResponse } from 'next/server';
import { PropertyDataService } from '../../../lib/property-data';
import { PropertySearchSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';
import { query } from '@/lib/db';

/**
 * General NSW Property Data API Endpoint
 *
 * Returns comprehensive property data for any NSW property address
 * Fixed to use real data instead of N/A values
 */
export async function GET(req: NextRequest) {
 const { searchParams } = new URL(req.url);

 // Build object from query parameters for validation
 const params = {
   address: searchParams.get('address') || '',
   lga: searchParams.get('lga') || undefined,
   includeConstraints: searchParams.get('includeConstraints') === 'true' || undefined
 };

 // Validate request data with Zod
 const validation = validateRequest(PropertySearchSchema, params);

 if (!validation.success) {
   return NextResponse.json(
     {
       success: false,
       error: 'Invalid request data',
       details: formatValidationErrors(validation.details),
       example: '/api/property?address=3 Wilkinson Ln, Telopea NSW 2117'
     },
     { status: 400 }
   );
 }

 const { address, lga, includeConstraints } = validation.data;
 
 try {
 // Get comprehensive property data
 const propertyData = await PropertyDataService.getPropertyComplianceData(address);

 // Transform Web Mercator geometry (EPSG:3857) to WGS84 coordinates (EPSG:4326)
 // ComplianceDashboard needs coordinates for geographic neighbourhood detection
 if (propertyData.geometry && !propertyData.coordinates) {
 const { x, y } = propertyData.geometry;

 // Web Mercator to WGS84 transformation
 const lon = (x / 20037508.34) * 180;
 const lat = (Math.atan(Math.exp((y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;

 propertyData.coordinates = { lat, lon };

 console.log(`[Property API] Transformed coordinates: Web Mercator (${x.toFixed(2)}, ${y.toFixed(2)}) → WGS84 (${lat.toFixed(6)}, ${lon.toFixed(6)})`);
 }

 // Enrich constraints with spatial overlay data from PostGIS.
 // Runs whenever coordinates are available — decoupled from the geometry
 // transformation block so properties with pre-existing coordinates are also covered.
 const spatialCoords = propertyData.coordinates;
 if (spatialCoords) {
 const { lon: spatialLon, lat: spatialLat } = spatialCoords;
 try {
   const spatialResult = await query(
     `SELECT layer_type, value
      FROM spatial_overlays
      WHERE ST_Contains(geom, ST_SetSRID(ST_Point($1, $2), 4326))
      AND layer_type IN (
        'additional_permitted_uses', 'foreshore_building_line', 'land_reservation',
        'riparian', 'wetlands', 'key_sites', 'active_street_frontages', 'flood',
        'sep', 'tod_precinct', 'tod_accelerated', 'tod_deferred',
        'biodiversity', 'landslide', 'fsr', 'acid_sulfate', 'lot_size'
      )`,
     [spatialLon, spatialLat]
   );
   const rows = spatialResult.rows;
   const apuRows = rows.filter(r => r.layer_type === 'additional_permitted_uses');
   const foreshorRows = rows.filter(r => r.layer_type === 'foreshore_building_line');
   const reservRows = rows.filter(r => r.layer_type === 'land_reservation');
   const riparianRows = rows.filter(r => r.layer_type === 'riparian');
   const wetlandsRows = rows.filter(r => r.layer_type === 'wetlands');
   const keySiteRows = rows.filter(r => r.layer_type === 'key_sites');
   const asfRows = rows.filter(r => r.layer_type === 'active_street_frontages');
   const dcpFloodRows = rows.filter(r => r.layer_type === 'flood');

   if (apuRows.length > 0) {
     propertyData.constraints.additionalPermittedUses = {
       hasAPU: true,
       schedules: [...new Set(apuRows.map(r => r.value).filter(Boolean))],
     };
   }
   if (foreshorRows.length > 0) {
     propertyData.constraints.foreshoreBuildingLine = {
       hasLine: true,
       layClass: foreshorRows[0].value,
     };
   }
   if (reservRows.length > 0) {
     propertyData.constraints.landReservation = {
       hasReservation: true,
       purpose: reservRows[0].value,
     };
   }
   if (riparianRows.length > 0) {
     const val = riparianRows[0].value as string;
     // Shorten verbose values: "Protected-Riparian Land" → "Protected", "10m" → "10m"
     const category = val?.startsWith('Protected') ? 'Protected' : val;
     propertyData.constraints.riparianLand = { inRiparianArea: true, category };
   }
   if (wetlandsRows.length > 0) {
     propertyData.constraints.wetlands = { inWetlandsArea: true };
   }
   if (keySiteRows.length > 0) {
     const clauseRow = keySiteRows.find(r => (r.value as string)?.startsWith('Clause'));
     propertyData.constraints.keySite = {
       isKeySite: true,
       clause: clauseRow?.value ?? undefined,
     };
   }
   if (asfRows.length > 0) {
     const clauseRow = asfRows.find(r => (r.value as string)?.includes('Clause'));
     propertyData.constraints.activeStreetFrontage = {
       required: true,
       clause: clauseRow?.value ?? undefined,
     };
   }
   if (dcpFloodRows.length > 0) {
     propertyData.constraints.dcpFloodMap = {
       inFloodArea: true,
       classification: dcpFloodRows[0].value,
     };
   }

   const biodiversityRows = rows.filter(r => r.layer_type === 'biodiversity');
   if (biodiversityRows.length > 0) {
     propertyData.constraints.terrestrialBiodiversity = { inBiodiversityArea: true };
   }

   const landslideRows = rows.filter(r => r.layer_type === 'landslide');
   if (landslideRows.length > 0) {
     propertyData.constraints.landslideRisk = {
       hasRisk: true,
       layClass: landslideRows[0].value ?? undefined,
     };
   }

   // PostGIS fallbacks — only set if Planning Portal didn't return a value
   const fsrRows = rows.filter(r => r.layer_type === 'fsr');
   if (fsrRows.length > 0 && !propertyData.constraints.maxFsr) {
     const fsrVal = parseFloat(fsrRows[0].value as string);
     if (!isNaN(fsrVal)) propertyData.constraints.maxFsr = fsrVal;
   }

   const acidRows = rows.filter(r => r.layer_type === 'acid_sulfate');
   if (acidRows.length > 0 && !propertyData.constraints.acidSulfateSoils) {
     propertyData.constraints.acidSulfateSoils = acidRows[0].value as string ?? 'Present';
   }

   const lotSizeRows = rows.filter(r => r.layer_type === 'lot_size');
   if (lotSizeRows.length > 0 && propertyData.constraints.minLotSize === null) {
     const parsed = parseFloat(lotSizeRows[0].value as string);
     if (!isNaN(parsed)) propertyData.constraints.minLotSize = parsed;
   }

   const sepRows = rows.filter(r => r.layer_type === 'sep');
   if (sepRows.length > 0) {
     const isDraft = (sepRows[0].value as string)?.toLowerCase().includes('draft');
     propertyData.constraints.specialEntertainmentPrecinct = {
       inSEP: true,
       name: sepRows[0].value,
       isDraft,
     };
   }

   const todRows = rows.filter(r => r.layer_type === 'tod_precinct');
   const todAccRows = rows.filter(r => r.layer_type === 'tod_accelerated');
   const todDefRows = rows.filter(r => r.layer_type === 'tod_deferred');
   if (todRows.length > 0) {
     propertyData.constraints.todPrecinctSpatial = {
       inTODPrecinct: true,
       classification: todRows[0].value,
       isAccelerated: false,
       isDeferred: false,
     };
   }
   if (todAccRows.length > 0) {
     const existing = propertyData.constraints.todPrecinctSpatial;
     propertyData.constraints.todPrecinctSpatial = {
       inTODPrecinct: true,
       classification: todAccRows[0].value,
       isAccelerated: true,
       isDeferred: false,
       ...(existing || {}),
     };
   }
   if (todDefRows.length > 0) {
     propertyData.constraints.todPrecinctSpatial = {
       inTODPrecinct: true,
       classification: todDefRows[0].value,
       isAccelerated: false,
       isDeferred: true,
     };
   }
 } catch (spatialErr) {
   console.warn('[Property API] Spatial overlay query failed (non-fatal):', spatialErr);
 }
 }

 return NextResponse.json({
 success: true,
 data: propertyData,
 metadata: {
 timestamp: new Date().toISOString(),
 source: 'NSW Planning Portal',
 api_version: 'current'
 }
 });
 
 } catch (error) {
 console.error('Property data fetch failed:', error);
 
 return NextResponse.json(
 { 
 error: 'Failed to retrieve property data',
 details: error instanceof Error ? error.message : 'Unknown error'
 },
 { status: 500 }
 );
 }
}