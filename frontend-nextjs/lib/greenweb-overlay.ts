/**
 * Ku-ring-gai DCP Part 18R.1 Greenweb: is this property on it?
 *
 * prior-art-checked: reuse not viable. The spatial_overlays enrichment in app/api/property/route.ts
 * tests the ADDRESS POINT (ST_Contains); Greenweb patches are small and a point test hides binding
 * rules for a lot that only partly overlaps. No existing lib reads nsw_cadastre_lots against an
 * overlay layer (grep of frontend-nextjs/lib and app/api, 2026-10-20).
 *
 * The council's words: Part 18 applies to "areas identified as Greenweb, mapped in this DCP". So a lot
 * is flagged when ANY PART of it overlaps a Greenweb category. The lot is the cadastre polygon
 * containing the address point. Only when no lot polygon is found does the point decide, and the
 * result says so (basis: 'point').
 */

export type GreenwebBasis = 'lot' | 'point';

export interface GreenwebConstraint {
  onGreenweb: true;
  categories: string[];
  basis: GreenwebBasis;
}

type QueryFn = (
  sql: string,
  params?: unknown[]
) => Promise<{ rows: Array<Record<string, unknown>> }>;

/** The lot polygons holding the point, and the Greenweb categories any part of them overlaps. */
export const GREENWEB_LOT_SQL = `
  WITH pt AS (SELECT ST_SetSRID(ST_Point($1, $2), 4326) AS g),
  lot AS (
    SELECT l.geom FROM nsw_cadastre_lots l, pt
    WHERE ST_Contains(l.geom, pt.g)
  )
  SELECT
    (SELECT count(*) FROM lot)::int AS lot_count,
    COALESCE(
      (SELECT array_agg(DISTINCT o.value ORDER BY o.value)
       FROM spatial_overlays o, lot
       WHERE o.layer_type = 'greenweb' AND ST_Intersects(o.geom, lot.geom)),
      ARRAY[]::text[]
    ) AS categories
`;

/** Fallback when the cadastre has no polygon for the point. */
export const GREENWEB_POINT_SQL = `
  SELECT COALESCE(array_agg(DISTINCT o.value ORDER BY o.value), ARRAY[]::text[]) AS categories
  FROM spatial_overlays o
  WHERE o.layer_type = 'greenweb'
    AND ST_Contains(o.geom, ST_SetSRID(ST_Point($1, $2), 4326))
`;

function toCategories(raw: unknown): string[] {
  return Array.isArray(raw) ? raw.filter((v): v is string => typeof v === 'string' && v.length > 0) : [];
}

/**
 * Returns the constraint, or null when the property is not on Greenweb. Throws on a database error:
 * the caller decides whether that is fatal (the property route logs it and leaves the flag unset, which
 * the rules route reads as "not on Greenweb" -- visible only in the log, so the caller must log it).
 */
export async function greenwebForPoint(
  query: QueryFn,
  lon: number,
  lat: number
): Promise<GreenwebConstraint | null> {
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;

  const lotResult = await query(GREENWEB_LOT_SQL, [lon, lat]);
  const row = lotResult.rows[0];
  const lotCount = Number(row?.lot_count ?? 0);

  if (lotCount > 0) {
    const categories = toCategories(row?.categories);
    return categories.length > 0 ? { onGreenweb: true, categories, basis: 'lot' } : null;
  }

  const pointResult = await query(GREENWEB_POINT_SQL, [lon, lat]);
  const categories = toCategories(pointResult.rows[0]?.categories);
  return categories.length > 0 ? { onGreenweb: true, categories, basis: 'point' } : null;
}
