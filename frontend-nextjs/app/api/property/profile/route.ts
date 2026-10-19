import { NextRequest, NextResponse } from 'next/server';
import { NSWPlanningPortalService } from '@/lib/nsw-planning-portal';
import { calculateLotDimensions } from '@/lib/geometry/lot-dimensions';
import { floodMapStatus } from '@/lib/flood/flood-map';
import { checkRateLimit, getClientIdentifier, searchRateLimiter, createRateLimitHeaders } from '@/lib/rate-limit';

/**
 * GET /api/property/profile?address=...
 *
 * Lightweight property profile using only free NSW Planning Portal data.
 * Returns: zone, height, FSR, heritage, flood, bushfire, lot polygon, coordinates.
 * No expensive satellite pipelines — instant response (~1-2s).
 */
export async function GET(request: NextRequest) {
  const address = request.nextUrl.searchParams.get('address')?.trim();
  if (!address) {
    return NextResponse.json({ error: 'address parameter required' }, { status: 400 });
  }

  // Rate limit
  const clientId = getClientIdentifier(request);
  const rl = await checkRateLimit(`property-profile:${clientId}`, searchRateLimiter, 20, 60_000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again shortly.' },
      { status: 429, headers: createRateLimitHeaders(rl) }
    );
  }

  try {
    const searchResult = await NSWPlanningPortalService.searchProperty(address);
    if (!searchResult) {
      return NextResponse.json({ error: 'Property not found in NSW Planning Portal' }, { status: 404 });
    }

    // Fetch layers, valuation, and lot geometry in parallel
    const [layers, propertyData, lotGeometry] = await Promise.all([
      NSWPlanningPortalService.getPlanningLayers(searchResult.propId),
      NSWPlanningPortalService.getPropertyValuation(searchResult.propId),
      NSWPlanningPortalService.getLotGeometry(searchResult.propId).catch(() => null),
    ]);

    if (!propertyData) {
      return NextResponse.json({ error: 'Property valuation data not available' }, { status: 404 });
    }

    // Extract key fields from layers
    const zoneLayer = layers.find(l => l.layerName === 'Land Zoning Map');
    const heightLayer = layers.find(l => l.layerName === 'Height of Buildings Map');
    const fsrLayer = layers.find(l => l.layerName === 'Floor Space Ratio Map');
    const heritageLayer = layers.find(l => l.layerName === 'Heritage Map');

    const zone = zoneLayer?.results?.[0]?.['Zone'] ?? null;
    const zoneTitle = zoneLayer?.results?.[0]?.['title'] ?? null; // e.g. "E4: General Industrial"
    const zoneDescription = zoneTitle ?? propertyData.zoneDescription ?? null;
    const lga = zoneLayer?.results?.[0]?.['LGA Name'] ?? null;
    const maxHeight = heightLayer?.results?.[0]?.['Maximum Building Height'] ?? null;
    const maxFsr = fsrLayer?.results?.[0]?.['Floor Space Ratio'] ?? null;
    const heritage = heritageLayer?.results != null && heritageLayer.results.length > 0;
    const heritageItemName = heritageLayer?.results?.[0]?.['Heritage Item Name'] ?? null;

    // Coordinates (Web Mercator → WGS84)
    const lon = (propertyData.geometry.x / 20037508.34) * 180;
    const lat = (Math.atan(Math.exp((propertyData.geometry.y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;

    // Lot dimensions
    let lotArea: number | null = null;
    let lotPolygonWgs84: { type: 'Polygon'; coordinates: number[][][] } | null = null;

    if (lotGeometry?.geometry?.rings) {
      const dims = calculateLotDimensions(lotGeometry.geometry);
      lotArea = dims?.area ?? null;

      // Convert rings from Web Mercator to WGS84 for frontend map display
      const wgs84Rings = lotGeometry.geometry.rings.map((ring: number[][]) =>
        ring.map(([x, y]: number[]) => {
          const lng = (x / 20037508.34) * 180;
          const lt = (Math.atan(Math.exp((y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;
          return [lng, lt];
        })
      );
      lotPolygonWgs84 = { type: 'Polygon', coordinates: wgs84Rings };
    }

    // Flood from the council's published Flood Planning Map. layerintersect never returns a
    // 'Flood Planning Area' layer, so the old check answered "No" for every property.
    const lotPlans = (layers.find(l => l.layerName === 'Land Application Map')?.results ?? [])
      .map((r: any) => String(r?.['EPI Name'] ?? r?.title ?? '')).filter(Boolean);
    const flood = await floodMapStatus(lon, lat, lotPlans);
    const floodProne = flood.floodProne;

    return NextResponse.json({
      address: propertyData.address,
      lat,
      lng: lon,
      zone,
      zoneDescription,
      lga,
      maxHeight,
      maxFsr,
      heritage,
      heritageItemName,
      floodProne,
      floodMapNote: flood.note,
      lotArea: lotArea ? Math.round(lotArea) : null,
      lotPolygon: lotPolygonWgs84,
      landValue: propertyData.landValue,
      propertyArea: propertyData.propertyArea,
    });
  } catch (err) {
    console.error('[property/profile] Error:', err);
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
