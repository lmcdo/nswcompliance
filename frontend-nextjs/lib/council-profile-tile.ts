// prior-art-checked: reuse not viable — every flagged neighbour renders a
// PROPERTY-level constraint for one address (ServicingTile: Sydney Water at a
// point; LepControls / StateLevelControls / ConstraintArithmeticCard: the
// controls hitting one parcel; api/dcp/structured-controls: structured controls
// for a lot). This is the opposite scope: a fact computed across a whole LGA,
// with no address involved. The only true home would be
// planning-controls/[lga-slug]/page.tsx, where this logic currently sits inline
// — and moving it out is the entire point, because a server component cannot be
// unit-tested and these strings are public claims about a council. No lib helper
// for tile copy exists (grepped lib/*.ts for TileContent, tileCopy, profileTile).

/**
 * What the two data tiles on /planning-controls/<council> should say.
 *
 * These tiles make claims about a whole council on a public, indexed page. The
 * middle one used to say "Available" — the vague word that let eight councils
 * assert DCP data they did not have (found and corrected 2026-09-10, PR #1075).
 *
 * The governing principle: an unknown must never render as a claim. Every
 * branch below either states something measured, or falls back to wording that
 * is true of every council in NSW.
 */

export type CouncilProfile = {
  /** rows in dcp_setback_controls for this council */
  controls: number
  /** distinct v2_precinct_id on its served provisions */
  precincts: number
  /** the overlay layer that defines this LGA, if one does */
  dominant: { layer: string; pct: number } | null
}

export type TileContent = {
  label: string
  value: string
  sub: string
}

/**
 * Overlay layer -> the words a reader uses.
 *
 * Only layers that constrain what can be built are listed. A layer absent from
 * this map is never surfaced: naming one we cannot explain in three words is
 * worse than naming none, and it would put an unexplained technical term on a
 * public page.
 */
export const CONSTRAINT_LABEL: Record<string, string> = {
  heritage: 'Heritage',
  flood: 'Flood',
  bushfire: 'Bushfire',
  biodiversity: 'Biodiversity',
  acid_sulfate: 'Acid sulfate soils',
  riparian: 'Riparian land',
  coastal: 'Coastal management',
  landslide: 'Landslide risk',
}

/**
 * Below this share, the layer is not the defining feature of the LGA and
 * calling it the main constraint would overstate it.
 *
 * 20% is read off the measured spread on 2026-09-10 rather than chosen:
 * Campbelltown flood 89%, Burwood heritage 47%, Hornsby heritage 25%,
 * Northern Beaches biodiversity 15%, then a long tail in single digits. The
 * gap between 25 and 15 is where "this defines the council" stops being true.
 */
export const DOMINANT_MIN_PCT = 20

/**
 * Third tile. Was "Coverage / All NSW / LEP + SEPP for every address" on every
 * council page — true, identical everywhere, and therefore worth nothing to a
 * reader. Falls back to exactly that when nothing specific is known.
 */
export function profileTile(profile: CouncilProfile | null): TileContent {
  const generic: TileContent = {
    label: 'Coverage',
    value: 'All NSW',
    sub: 'LEP + SEPP for every address',
  }
  if (!profile) return generic

  if (profile.dominant && profile.dominant.pct >= DOMINANT_MIN_PCT) {
    return {
      label: 'Main constraint',
      value: `${profile.dominant.layer} ${Math.round(profile.dominant.pct)}%`,
      sub: 'Share of mapped overlays in this LGA',
    }
  }
  if (profile.precincts > 0) {
    return {
      label: 'Precincts',
      value: `${profile.precincts} precincts`,
      sub: 'Controls vary by precinct',
    }
  }
  return generic
}

/**
 * Middle tile. Prefers the provision count, then the structured-control count,
 * then says the plain truth. Never the word "Available".
 */
export function dcpControlsTile(
  profile: CouncilProfile | null,
  provisionTotal: number,
  showTopics: boolean
): TileContent {
  if (showTopics && provisionTotal > 0) {
    return {
      label: 'DCP controls',
      value: `${provisionTotal.toLocaleString()} provisions`,
      sub: 'Full provision text',
    }
  }
  if (profile && profile.controls > 0) {
    return {
      label: 'DCP controls',
      value: `${profile.controls} structured controls`,
      sub: 'Setbacks, parking, height',
    }
  }
  return { label: 'DCP controls', value: 'Coming soon', sub: 'Not yet published' }
}
