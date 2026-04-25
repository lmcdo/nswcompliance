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

// Width/height of the exported image in pixels
const IMG_W = 600;
const IMG_H = 300;

// Bounding box half-extents in degrees around the subject point
// At Sydney's latitude (~34°S): 0.003° lng ≈ 283m, 0.0015° lat ≈ 167m
const D_LNG = 0.003;
const D_LAT = 0.0015;

const NSW_LAT = { min: -38.0, max: -28.0 };
const NSW_LNG = { min: 140.5, max: 154.0 };

export async function fetchAerialTileBase64(lat: number, lng: number): Promise<string | null> {
  if (
    !isFinite(lat) || !isFinite(lng) ||
    lat < NSW_LAT.min || lat > NSW_LAT.max ||
    lng < NSW_LNG.min || lng > NSW_LNG.max
  ) return null;

  const minX = (lng - D_LNG).toFixed(6);
  const minY = (lat - D_LAT).toFixed(6);
  const maxX = (lng + D_LNG).toFixed(6);
  const maxY = (lat + D_LAT).toFixed(6);

  const params = new URLSearchParams({
    bbox: `${minX},${minY},${maxX},${maxY}`,
    bboxSR: '4326',
    imageSR: '4326',
    size: `${IMG_W},${IMG_H}`,
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
