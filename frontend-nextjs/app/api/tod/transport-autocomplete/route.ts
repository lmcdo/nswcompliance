import { NextRequest, NextResponse } from 'next/server';
import { AutocompleteSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

export const dynamic = 'force-dynamic';

// Transport stations for NSW - focused on Inner West + major hubs
// Coordinates verified from TfNSW and Google Maps
const TRANSPORT_STATIONS = [
  // Heavy Rail - Inner West Line (T2 Inner West)
  { id: 'petersham', name: 'Petersham Station', type: 'heavy_rail', lat: -33.8896, lng: 151.1551, frequency: 'high' },
  { id: 'lewisham', name: 'Lewisham Station', type: 'heavy_rail', lat: -33.8929, lng: 151.1482, frequency: 'high' },
  { id: 'summer_hill', name: 'Summer Hill Station', type: 'heavy_rail', lat: -33.8913, lng: 151.1389, frequency: 'high' },
  { id: 'ashfield', name: 'Ashfield Station', type: 'heavy_rail', lat: -33.8876, lng: 151.1244, frequency: 'high' },
  { id: 'croydon', name: 'Croydon Station', type: 'heavy_rail', lat: -33.8836, lng: 151.1163, frequency: 'high' },
  { id: 'burwood', name: 'Burwood Station', type: 'heavy_rail', lat: -33.8777, lng: 151.1044, frequency: 'high' },
  { id: 'strathfield', name: 'Strathfield Station', type: 'heavy_rail', lat: -33.8716, lng: 151.0935, frequency: 'high' },

  // Heavy Rail - Bankstown Line (T3 via Sydenham)
  { id: 'stanmore', name: 'Stanmore Station', type: 'heavy_rail', lat: -33.8938, lng: 151.1641, frequency: 'high' },
  { id: 'newtown', name: 'Newtown Station', type: 'heavy_rail', lat: -33.8976, lng: 151.1789, frequency: 'high' },
  { id: 'macdonaldtown', name: 'Macdonaldtown Station', type: 'heavy_rail', lat: -33.8936, lng: 151.1862, frequency: 'medium' },
  { id: 'st_peters', name: 'St Peters Station', type: 'heavy_rail', lat: -33.9103, lng: 151.1808, frequency: 'high' },
  { id: 'sydenham', name: 'Sydenham Station', type: 'heavy_rail', lat: -33.9168, lng: 151.1693, frequency: 'high' },
  { id: 'marrickville', name: 'Marrickville Station', type: 'heavy_rail', lat: -33.9112, lng: 151.1557, frequency: 'high' },
  { id: 'dulwich_hill', name: 'Dulwich Hill Station', type: 'heavy_rail', lat: -33.9066, lng: 151.1394, frequency: 'high' },

  // Heavy Rail - Major Interchange Stations
  { id: 'central', name: 'Central Station', type: 'heavy_rail', lat: -33.8823, lng: 151.2062, frequency: 'high' },
  { id: 'redfern', name: 'Redfern Station', type: 'heavy_rail', lat: -33.8923, lng: 151.1984, frequency: 'high' },
  { id: 'town_hall', name: 'Town Hall Station', type: 'heavy_rail', lat: -33.8736, lng: 151.2070, frequency: 'high' },
  { id: 'wynyard', name: 'Wynyard Station', type: 'heavy_rail', lat: -33.8657, lng: 151.2061, frequency: 'high' },
  { id: 'parramatta', name: 'Parramatta Station', type: 'heavy_rail', lat: -33.8151, lng: 151.0041, frequency: 'high' },

  // Light Rail - L1 Dulwich Hill Line (Inner West)
  { id: 'dulwich_hill_lr', name: 'Dulwich Hill Light Rail', type: 'light_rail', lat: -33.9111, lng: 151.1403, frequency: 'medium' },
  { id: 'dulwich_grove_lr', name: 'Dulwich Grove Light Rail', type: 'light_rail', lat: -33.9082, lng: 151.1442, frequency: 'medium' },
  { id: 'arlington_lr', name: 'Arlington Light Rail', type: 'light_rail', lat: -33.9034, lng: 151.1486, frequency: 'medium' },
  { id: 'waratah_mills_lr', name: 'Waratah Mills Light Rail', type: 'light_rail', lat: -33.8994, lng: 151.1518, frequency: 'medium' },
  { id: 'lewisham_west_lr', name: 'Lewisham West Light Rail', type: 'light_rail', lat: -33.8962, lng: 151.1477, frequency: 'medium' },
  { id: 'taverners_hill_lr', name: 'Taverners Hill Light Rail', type: 'light_rail', lat: -33.8912, lng: 151.1519, frequency: 'medium' },
  { id: 'marion_lr', name: 'Marion Light Rail', type: 'light_rail', lat: -33.8907, lng: 151.1579, frequency: 'medium' },
  { id: 'hawthorne_lr', name: 'Hawthorne Light Rail', type: 'light_rail', lat: -33.8909, lng: 151.1659, frequency: 'medium' },
  { id: 'leichhardt_nth_lr', name: 'Leichhardt North Light Rail', type: 'light_rail', lat: -33.8842, lng: 151.1607, frequency: 'medium' },
  { id: 'lilyfield_lr', name: 'Lilyfield Light Rail', type: 'light_rail', lat: -33.8763, lng: 151.1657, frequency: 'medium' },
  { id: 'rozelle_bay_lr', name: 'Rozelle Bay Light Rail', type: 'light_rail', lat: -33.8685, lng: 151.1717, frequency: 'medium' },
  { id: 'jubilee_park_lr', name: 'Jubilee Park Light Rail', type: 'light_rail', lat: -33.8710, lng: 151.1825, frequency: 'medium' },
  { id: 'glebe_lr', name: 'Glebe Light Rail', type: 'light_rail', lat: -33.8734, lng: 151.1880, frequency: 'medium' },
  { id: 'wentworth_park_lr', name: 'Wentworth Park Light Rail', type: 'light_rail', lat: -33.8752, lng: 151.1917, frequency: 'medium' },
  { id: 'fish_market_lr', name: 'Fish Market Light Rail', type: 'light_rail', lat: -33.8719, lng: 151.1915, frequency: 'medium' },
  { id: 'central_lr', name: 'Central Chalmers St Light Rail', type: 'light_rail', lat: -33.8823, lng: 151.2062, frequency: 'high' },

  // Bus - High Frequency Routes (Inner West corridors)
  { id: 'leichhardt_bus', name: 'Leichhardt Marketplace Bus Stop', type: 'bus', lat: -33.8832, lng: 151.1559, frequency: 'high' },
  { id: 'parramatta_rd_petersham', name: 'Parramatta Rd Petersham Bus', type: 'bus', lat: -33.8866, lng: 151.1551, frequency: 'high' },
  { id: 'marrickville_metro', name: 'Marrickville Metro Bus Stop', type: 'bus', lat: -33.9112, lng: 151.1557, frequency: 'high' },
  { id: 'norton_st_bus', name: 'Norton St Leichhardt Bus', type: 'bus', lat: -33.8857, lng: 151.1568, frequency: 'high' },
  { id: 'ashfield_mall_bus', name: 'Ashfield Mall Bus Stop', type: 'bus', lat: -33.8876, lng: 151.1244, frequency: 'high' },

  // Ferry - Balmain/Rozelle
  { id: 'balmain_east_ferry', name: 'Balmain East Ferry Wharf', type: 'ferry', lat: -33.8577, lng: 151.1920, frequency: 'medium' },
  { id: 'balmain_ferry', name: 'Balmain Ferry Wharf', type: 'ferry', lat: -33.8564, lng: 151.1783, frequency: 'medium' },
  { id: 'circular_quay_ferry', name: 'Circular Quay Ferry Terminal', type: 'ferry', lat: -33.8616, lng: 151.2111, frequency: 'high' },
];

function calculateDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
 const R = 6371e3; // Earth's radius in meters
 const φ1 = lat1 * Math.PI / 180;
 const φ2 = lat2 * Math.PI / 180;
 const Δφ = (lat2 - lat1) * Math.PI / 180;
 const Δλ = (lng2 - lng1) * Math.PI / 180;

 const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
 Math.cos(φ1) * Math.cos(φ2) *
 Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
 const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

 return R * c;
}

export async function GET(request: NextRequest) {
 try {
 const searchParams = request.nextUrl.searchParams;

 // Validate query params using AutocompleteSchema (only if query is provided)
 const queryParam = searchParams.get('query');
 if (queryParam) {
 const validation = validateRequest(AutocompleteSchema, {
 query: queryParam,
 limit: parseInt(searchParams.get('limit') || '10'),
 });

 if (!validation.success) {
 return NextResponse.json(
 {
 error: 'Invalid query parameters',
 details: formatValidationErrors(validation.details),
 },
 { status: 400 }
 );
 }
 }

 const query = queryParam?.toLowerCase() || '';
 const lat = parseFloat(searchParams.get('lat') || '-33.8688');
 const lng = parseFloat(searchParams.get('lng') || '151.2093');
 const limit = parseInt(searchParams.get('limit') || '10');

 // Filter stations based on query
 let filtered = TRANSPORT_STATIONS;
 if (query) {
 filtered = TRANSPORT_STATIONS.filter(station =>
 station.name.toLowerCase().includes(query) ||
 station.type.toLowerCase().includes(query)
 );
 }

 // Calculate distances and sort by proximity
 const withDistances = filtered.map(station => ({
 ...station,
 distance: Math.round(calculateDistance(lat, lng, station.lat, station.lng))
 }));

 // Sort by distance
 withDistances.sort((a, b) => a.distance - b.distance);

 // Format as suggestions
 const suggestions = withDistances.slice(0, limit).map(station => ({
 id: station.id,
 name: station.name,
 type: station.type,
 distance: station.distance,
 frequency: station.frequency,
 lat: station.lat,
 lng: station.lng,
 label: `${station.name} (${Math.round(station.distance)}m)`,
 value: station.name
 }));

 return NextResponse.json({
 suggestions,
 count: suggestions.length,
 query,
 location: { lat, lng }
 });

 } catch (error) {
 console.error('Transport autocomplete error:', error);
 return NextResponse.json(
 { error: 'Failed to get transport suggestions' },
 { status: 500 }
 );
 }
}