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

interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

/**
 * Compute a bbox from a GeoJSON polygon's extent, with padding.
 * Returns [minLng, minLat, maxLng, maxLat].
 */
function bboxFromPolygon(polygon: GeoJSONPolygon, paddingFraction = 0.3): { minX: number; minY: number; maxX: number; maxY: number } {
  const coords = polygon.coordinates[0];
  const lngs = coords.map(c => c[0]);
  const lats = coords.map(c => c[1]);
  const rawMinX = Math.min(...lngs);
  const rawMaxX = Math.max(...lngs);
  const rawMinY = Math.min(...lats);
  const rawMaxY = Math.max(...lats);
  const padX = (rawMaxX - rawMinX) * paddingFraction;
  const padY = (rawMaxY - rawMinY) * paddingFraction;
  return {
    minX: rawMinX - padX,
    minY: rawMinY - padY,
    maxX: rawMaxX + padX,
    maxY: rawMaxY + padY,
  };
}

export async function fetchAerialTileBase64(
  lat: number,
  lng: number,
  zoom: 'property' | 'neighbourhood' = 'neighbourhood',
  lotPolygon?: GeoJSONPolygon | null,
): Promise<string | null> {
  if (
    !isFinite(lat) || !isFinite(lng) ||
    lat < NSW_LAT.min || lat > NSW_LAT.max ||
    lng < NSW_LNG.min || lng > NSW_LNG.max
  ) return null;

  let minX: string, minY: string, maxX: string, maxY: string;
  let w: number, h: number;

  if (lotPolygon && lotPolygon.coordinates?.[0]?.length >= 3) {
    // Zoom to lot boundary with padding
    const bbox = bboxFromPolygon(lotPolygon);
    minX = bbox.minX.toFixed(6);
    minY = bbox.minY.toFixed(6);
    maxX = bbox.maxX.toFixed(6);
    maxY = bbox.maxY.toFixed(6);
    // Use square-ish output sized to the lot's aspect ratio
    const dLng = bbox.maxX - bbox.minX;
    const dLat = bbox.maxY - bbox.minY;
    const aspect = dLng / dLat;
    h = 512;
    w = Math.round(h * aspect);
    // Clamp width to reasonable range
    w = Math.max(256, Math.min(1024, w));
  } else {
    // Fallback to fixed preset centred on lat/lng
    const preset = ZOOM_PRESETS[zoom];
    minX = (lng - preset.d_lng).toFixed(6);
    minY = (lat - preset.d_lat).toFixed(6);
    maxX = (lng + preset.d_lng).toFixed(6);
    maxY = (lat + preset.d_lat).toFixed(6);
    w = preset.w;
    h = preset.h;
  }

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
    // Reject very small images (< 5KB) — these are typically blank/checkerboard
    // "no data" tiles from the MapServer when imagery isn't available
    if (buf.byteLength < 5000) return null;
    return Buffer.from(buf).toString('base64');
  } catch {
    return null;
  }
}
