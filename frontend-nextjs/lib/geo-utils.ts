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

/** A lot boundary as a WGS84 POLYGON WKT for /pipeline/flood-planning and /pipeline/flood,
 *  so the backend tests the whole lot, not only the address point. Web Mercator (3857/102100)
 *  is converted; lat/long systems (4326/4283/7844, within metres of each other) pass through.
 *  null for anything else or a ring under 4 points. The backend still ignores an outline that
 *  does not contain the address point, so a wrong boundary cannot give a wrong answer.
 *  Heddon Greta 2026-10-28: 44.7 m2 of the lot inside Cessnock's 1% AEP extent, address point
 *  6 m outside it -- every surface sent the point only and said "not known" or "none". */
export function lotRingsToWgs84Wkt(rings: number[][][] | null | undefined, wkid: number | null | undefined): string | null {
  if (!rings?.length || !rings.every((r) => Array.isArray(r) && r.length >= 4)) return null;
  let ll: number[][][];
  if (wkid === 3857 || wkid === 102100) ll = esriRingsToGeoJSON(rings).coordinates;
  else if (wkid === 4326 || wkid === 4283 || wkid === 7844) ll = rings;
  else return null;
  const ring = (r: number[][]) => {
    const pts = r.map(([x, y]) => `${x} ${y}`);
    if (pts[0] !== pts[pts.length - 1]) pts.push(pts[0]);
    return `(${pts.join(', ')})`;
  };
  return `POLYGON(${ll.map(ring).join(', ')})`;
}
