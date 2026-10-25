import { NextRequest, NextResponse } from 'next/server';
import { PropertyDataService } from '../../../lib/property-data';
import { PropertySearchSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';
import { query as dbQuery } from '@/lib/db';
import { greenwebConstraints } from '@/lib/greenweb-overlay';
import { railOrBusyRoadConstraints } from '@/lib/rail-busy-road';
import { classifiedRoadConstraints } from '@/lib/classified-road';
import { withLookupBudget, withinLookupBudget, LOOKUP_OUT_OF_TIME } from '@/lib/fetch-timeout';
import { SPATIAL_OVERLAYS_SQL, LOT_FOUND_MARKER } from '@/lib/spatial-overlays-sql';
import { LOOKUP_BUDGET_MS, type LookupCheck } from '@/lib/lookup-not-checked';
import { ADDRESS_SEARCH_UNAVAILABLE, VALUATION_UNAVAILABLE, LOCATION_NOT_FOUND } from '@/lib/nsw-planning-portal';

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
 // One time limit for the whole lookup: anything unfinished when it runs out is "Not checked".
 const propertyData = await withLookupBudget(LOOKUP_BUDGET_MS, async () => {
 const propertyData = await PropertyDataService.getPropertyComplianceData(address);
 // Database calls cannot take the time limit's signal, so each is cut off by it instead.
 const query: typeof dbQuery = (text, params) => withinLookupBudget(dbQuery(text, params));
 const notChecked = (check: LookupCheck) => {
   propertyData.constraints.notChecked = [...(propertyData.constraints.notChecked ?? []), check];
 };

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
 // Does the LOT front a State or classified road (any council)? Started now so it runs alongside the overlay queries.
 // Never throws: a failed check comes back as a plain-words classifiedRoadUnchecked note (lib/classified-road.ts).
 const classifiedRoadCheck = classifiedRoadConstraints(query, fetch, spatialLon, spatialLat);
 try {
   const spatialResult = await query(
     SPATIAL_OVERLAYS_SQL,
     [spatialLon, spatialLat]
   );
   const lotFound = spatialResult.rows.find(r => r.layer_type === LOT_FOUND_MARKER)?.value === 'true';
   const rows = spatialResult.rows.filter(r => r.layer_type !== LOT_FOUND_MARKER);
   // Hazard layers need the whole lot; with no lot only the point was checked, which cannot say "No".
   if (!lotFound) notChecked('spatial_overlays');
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
   if (acidRows.length > 0 && !propertyData.constraints.acidSulfateSoils) { // unknown-ok: fills the class only when the layers gave none
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
   // Flood, TOD, acid sulfate, key sites, ... all unknown: never "not in any overlay".
   console.warn('[Property API] Spatial overlay query failed:', spatialErr);
   notChecked('spatial_overlays');
   // The overlay is the acid sulfate fallback: with no class from the layers either, it is unknown.
   if (!propertyData.constraints.acidSulfateSoils) notChecked('acid_sulfate'); // unknown-ok: this IS the not-checked marking
 }
 // Ku-ring-gai Greenweb is flagged by the LOT, not the address point: Part 18 applies to areas
 // identified as Greenweb, and a lot that only partly overlaps a patch is still bound. Separate
 // query so a failure here cannot hide the point-based overlays above, and vice versa.
 // greenwebConstraints never throws: a failed check comes back as a plain-words greenwebUnchecked note.
 // Ku-ring-gai only: Greenweb is that council's own DCP map, so no other council gets a Greenweb note (Sol, 2026-10-20).
 if (/ku-?ring-?gai/i.test(String(propertyData.constraints?.lga ?? ''))) {
   // Part 20 (rail corridor and busy roads) is also a property of the LOT: it adjoins the corridor or it does not.
   // Never throws: a failed check comes back as a plain-words railOrBusyRoadUnchecked note.
   const [greenweb, railOrBusyRoad] = await Promise.all([
     greenwebConstraints(query, spatialLon, spatialLat),
     railOrBusyRoadConstraints(query, fetch, spatialLon, spatialLat),
   ]);
   Object.assign(propertyData.constraints, greenweb, railOrBusyRoad);
 }
 const classifiedRoad = await classifiedRoadCheck;
 if (propertyData.constraints) Object.assign(propertyData.constraints, classifiedRoad);
 if (classifiedRoad.classifiedRoadUnchecked) notChecked('classified_road');
 }
 return propertyData;
 });

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

 // DQ-122: no candidate carried the asked street number and street. Say so plainly (404), so a
 // caller can tell "no such property" from "the service is down" -- never serve a neighbour.
 const message = error instanceof Error ? error.message : '';
 // The record answered but has no location: the maps cannot be checked. Not an outage, not "no such property".
 if (message.startsWith(LOCATION_NOT_FOUND)) {
   return NextResponse.json(
     { success: false, error: 'The NSW property record for this address has no location, so the map checks could not be done.', details: message },
     { status: 422 }
   );
 }
 // A source that did not answer is an outage (503), never "no such property".
 if ([ADDRESS_SEARCH_UNAVAILABLE, VALUATION_UNAVAILABLE, LOOKUP_OUT_OF_TIME].some((m) => message.startsWith(m))) {
   return NextResponse.json(
     { success: false, error: 'The NSW property services did not answer, so this property could not be looked up. Please try again.', details: message },
     { status: 503 }
   );
 }
 if (message.includes('Property not found')) {
   return NextResponse.json(
     {
       success: false,
       error: `No property matching "${address}" was found in the NSW Planning Portal. Check the street number and street name.`,
       notFound: true,
     },
     { status: 404 }
   );
 }

 return NextResponse.json(
 { 
 error: 'Failed to retrieve property data',
 details: error instanceof Error ? error.message : 'Unknown error'
 },
 { status: 500 }
 );
 }
}