-- Migration 028: precinct_amenity_cache
-- Pre-computed amenity walkability per DCP precinct.
-- Avoids live Overpass API calls (10-15s) for supported LGAs.
-- Populated by enrichment/precompute_amenity.py at LGA onboarding time.

create table if not exists precinct_amenity_cache (
  precinct_id    text        primary key,
  former_council text        not null,
  amenity_jsonb  jsonb       not null,
  centroid_lat   float       not null,
  centroid_lng   float       not null,
  computed_at    timestamptz not null default now()
);

comment on table precinct_amenity_cache is
  'Pre-computed amenity walkability (schools, parks, shops, transport, medical) per DCP precinct. '
  'Keyed by v2_precinct_id. Refreshed at LGA onboarding or on demand via precompute_amenity.py.';

comment on column precinct_amenity_cache.amenity_jsonb is
  'Raw response from city2graph /amenity endpoint. Schema: {schools, parks, shops, transport, '
  'medical, walkability_score, walkability_score_label, radius_searched_m}.';
