/**
 * The PostGIS overlay lookup behind the property route's LEP map answers (flood, riparian, FSR, ...).
 * $1 = longitude, $2 = latitude (WGS84). Kept here so tests/test_spatial_overlays_whole_lot.py can run
 * the exact text the route runs against a real database.
 *
 * Value layers (FSR, lot size, acid sulfate, TOD, ...) are read at the address point: they give one
 * value and a neighbour's must not join in. Hazard / presence layers are ALSO tested against the whole
 * cadastre lot holding the point: a lot whose back half is flood mapped must not read "No" because
 * the address point is outside the flood polygon. A lot hit needs more than 1 m2 of real overlap, so a
 * polygon that only shares the lot's edge does not count. Point hits sort first (by_lot = 0), so
 * `rows[0].value` is still the address point's value when it has one. No lot found = point only.
 */
export const SPATIAL_OVERLAYS_SQL = `WITH pt AS (SELECT ST_SetSRID(ST_Point($1, $2), 4326) AS g),
lot AS (SELECT ST_Union(l.geom) AS g FROM nsw_cadastre_lots l, pt WHERE ST_Covers(l.geom, pt.g))
SELECT layer_type, value FROM (
  SELECT o.layer_type, o.value, 0 AS by_lot
  FROM spatial_overlays o, pt
  WHERE ST_Contains(o.geom, pt.g)
    AND o.layer_type IN (
      'additional_permitted_uses', 'foreshore_building_line', 'land_reservation',
      'riparian', 'wetlands', 'key_sites', 'active_street_frontages', 'flood',
      'sep', 'tod_precinct', 'tod_accelerated', 'tod_deferred',
      'biodiversity', 'landslide', 'fsr', 'acid_sulfate', 'lot_size'
    )
  UNION ALL
  SELECT o.layer_type, o.value, 1 AS by_lot
  FROM spatial_overlays o, lot
  WHERE lot.g IS NOT NULL
    AND ST_Intersects(o.geom, lot.g)
    AND o.layer_type IN (
      'flood', 'riparian', 'wetlands', 'biodiversity', 'landslide',
      'foreshore_building_line', 'land_reservation'
    )
    AND ST_Area(ST_Intersection(o.geom, lot.g)::geography) > 1
) hits
ORDER BY by_lot`;
