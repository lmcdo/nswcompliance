/**
 * Fetches an aerial tile for a given lat/lng using the NSW SIX Maps ArcGIS export API.
 * No API key required. Licence: CC-BY 4.0 NSW Government.
 *
 * Returns a base64-encoded PNG string, or null on failure.
 *
 * Using the ArcGIS MapServer export endpoint (returns a pre-composed image at any bbox):
 * https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/export
 */

const EXPORT_URL =
  'https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/export';

const NSW_LAT = { min: -38.0, max: -28.0 };
const NSW_LNG = { min: 140.5, max: 154.0 };

// 'property': ~90m × 90m — lot-level, individual property visible clearly
// 'neighbourhood': ~550m × 330m — street context, used by flood/shadow/solar/threat-radar
// Exported so map-overlay.tsx can compute matching SVG viewports.
export const ZOOM_PRESETS = {
  property:     { d_lng: 0.0005, d_lat: 0.0005, w: 512, h: 512 },
  neighbourhood:{ d_lng: 0.003,  d_lat: 0.0015, w: 600, h: 300 },
};

export async function fetchAerialTileBase64(
  lat: number,
  lng: number,
  zoom: 'property' | 'neighbourhood' = 'neighbourhood',
): Promise<string | null> {
  if (
    !isFinite(lat) || !isFinite(lng) ||
    lat < NSW_LAT.min || lat > NSW_LAT.max ||
    lng < NSW_LNG.min || lng > NSW_LNG.max
  ) return null;

  const { d_lng, d_lat, w, h } = ZOOM_PRESETS[zoom];
  const minX = (lng - d_lng).toFixed(6);
  const minY = (lat - d_lat).toFixed(6);
  const maxX = (lng + d_lng).toFixed(6);
  const maxY = (lat + d_lat).toFixed(6);

  const params = new URLSearchParams({
    bbox: `${minX},${minY},${maxX},${maxY}`,
    bboxSR: '4326',
    imageSR: '4326',
    size: `${w},${h}`,
    format: 'png',
    f: 'image',
  });

  try {
    const res = await fetch(`${EXPORT_URL}?${params}`, {
      signal: AbortSignal.timeout(15_000),
    });
    if (!res.ok) return null;
    const ct = res.headers.get('content-type') ?? '';
    if (!ct.includes('image')) return null;
    const buf = await res.arrayBuffer();
    return Buffer.from(buf).toString('base64');
  } catch {
    return null;
  }
}
