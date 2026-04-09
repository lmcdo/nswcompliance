'use client';

export type FeatureFlag =
  | 'spatial_context_card'   // SpatialContextCard visible in left panel
  | 'spatial_context_full'   // full amenity breakdown (vs teaser for free tier)
  | 'see_section2_autofill'; // DA mode SEE Section 2 auto-population

const FLAG_ENV: Record<FeatureFlag, string> = {
  spatial_context_card:   'NEXT_PUBLIC_FEATURE_SPATIAL_CONTEXT_CARD',
  spatial_context_full:   'NEXT_PUBLIC_FEATURE_SPATIAL_CONTEXT_FULL',
  see_section2_autofill:  'NEXT_PUBLIC_FEATURE_SEE_SECTION2_AUTOFILL',
};

/**
 * Returns whether a feature flag is enabled.
 * Phase 1: reads NEXT_PUBLIC_FEATURE_* env vars.
 * Phase 2: will read from user session plan tier.
 */
export function useFeatureFlag(flag: FeatureFlag): boolean {
  return process.env[FLAG_ENV[flag]] === 'true';
}
