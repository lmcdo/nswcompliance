import { NextRequest, NextResponse } from 'next/server';

// Sample transport data for NSW (would be from database in production)
const TRANSPORT_STATIONS = [
 // Heavy Rail
 { id: 'chatswood', name: 'Chatswood Station', type: 'heavy_rail', lat: -33.7969, lng: 151.1846, frequency: 'high' },
 { id: 'north_sydney', name: 'North Sydney Station', type: 'heavy_rail', lat: -33.8416, lng: 151.2067, frequency: 'high' },
 { id: 'burwood', name: 'Burwood Station', type: 'heavy_rail', lat: -33.8777, lng: 151.1044, frequency: 'high' },
 { id: 'strathfield', name: 'Strathfield Station', type: 'heavy_rail', lat: -33.8716, lng: 151.0935, frequency: 'high' },
 { id: 'parramatta', name: 'Parramatta Station', type: 'heavy_rail', lat: -33.8151, lng: 151.0041, frequency: 'high' },
 { id: 'central', name: 'Central Station', type: 'heavy_rail', lat: -33.8823, lng: 151.2062, frequency: 'high' },
 { id: 'town_hall', name: 'Town Hall Station', type: 'heavy_rail', lat: -33.8736, lng: 151.2070, frequency: 'high' },
 { id: 'wynyard', name: 'Wynyard Station', type: 'heavy_rail', lat: -33.8657, lng: 151.2061, frequency: 'high' },
 { id: 'circular_quay', name: 'Circular Quay Station', type: 'heavy_rail', lat: -33.8616, lng: 151.2111, frequency: 'high' },

 // Light Rail
 { id: 'dulwich_hill_lr', name: 'Dulwich Hill Light Rail', type: 'light_rail', lat: -33.9111, lng: 151.1403, frequency: 'medium' },
 { id: 'central_lr', name: 'Central Light Rail', type: 'light_rail', lat: -33.8823, lng: 151.2062, frequency: 'high' },
 { id: 'circular_quay_lr', name: 'Circular Quay Light Rail', type: 'light_rail', lat: -33.8616, lng: 151.2111, frequency: 'high' },
 { id: 'moore_park_lr', name: 'Moore Park Light Rail', type: 'light_rail', lat: -33.8928, lng: 151.2234, frequency: 'medium' },

 // Bus Interchanges
 { id: 'chatswood_bus', name: 'Chatswood Bus Interchange', type: 'bus', lat: -33.7969, lng: 151.1846, frequency: 'high' },
 { id: 'bondi_junction_bus', name: 'Bondi Junction Bus Interchange', type: 'bus', lat: -33.8920, lng: 151.2469, frequency: 'high' },
 { id: 'wynyard_bus', name: 'Wynyard Bus Terminal', type: 'bus', lat: -33.8657, lng: 151.2061, frequency: 'high' },
 { id: 'qvb_bus', name: 'QVB Bus Stop', type: 'bus', lat: -33.8717, lng: 151.2067, frequency: 'high' },

 // Ferry
 { id: 'circular_quay_ferry', name: 'Circular Quay Ferry Terminal', type: 'ferry', lat: -33.8616, lng: 151.2111, frequency: 'high' },
 { id: 'manly_ferry', name: 'Manly Ferry Wharf', type: 'ferry', lat: -33.7981, lng: 151.2845, frequency: 'high' },
 { id: 'parramatta_ferry', name: 'Parramatta Ferry Wharf', type: 'ferry', lat: -33.8151, lng: 151.0041, frequency: 'medium' },
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
 const query = searchParams.get('query')?.toLowerCase() || '';
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