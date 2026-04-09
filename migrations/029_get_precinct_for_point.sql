-- Migration 029: get_precinct_for_point
-- Spatial lookup: given a lat/lng, return the precinct_id whose boundary contains the point.
-- Used by /api/spatial/brief to resolve precinct_id when the caller doesn't supply one.
-- Falls back gracefully when no precinct contains the point (returns NULL).

create or replace function get_precinct_for_point(p_lat float8, p_lng float8)
returns text
language sql stable
as $$
  select precinct_id
  from dcp_precinct_boundaries
  where boundary is not null
    and ST_Contains(
      boundary,
      ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)
    )
  limit 1;
$$;
