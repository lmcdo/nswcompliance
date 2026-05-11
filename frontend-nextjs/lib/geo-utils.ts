/**
 * Shared geo utilities for converting between ESRI and GeoJSON formats.
 */

/** Convert Esri Web Mercator rings → GeoJSON Polygon (WGS84). */
export function esriRingsToGeoJSON(rings: number[][][]): { type: 'Polygon'; coordinates: number[][][] } {
  const R = 20037508.342789244;
  const coords = rings.map(ring =>
    ring.map(([x, y]) => [
      (x / R) * 180.0,
      (Math.atan(Math.exp((y * Math.PI) / R)) * 2 - Math.PI / 2) * (180.0 / Math.PI),
    ])
  );
  return { type: 'Polygon', coordinates: coords };
}
