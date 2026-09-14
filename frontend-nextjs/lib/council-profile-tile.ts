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
 *
 * A "Main constraint" tile (the overlay layer with the largest share of mapped
 * overlay ROWS) was removed before merge: a row count is not an area. Heritage
 * mapped as many small polygons outnumbers one flood polygon covering most of a
 * council, so the tile could name heritage the main constraint where flood
 * covers far more land. Nothing measured supports that claim, so it is not made.
 */

export type CouncilProfile = {
  /** served rows in dcp_setback_controls for this council (current, not held for review) */
  controls: number
  /** distinct v2_precinct_id on its served provisions */
  precincts: number
}

export type TileContent = {
  label: string
  value: string
  sub: string
}

/**
 * Third tile. Was "Coverage / All NSW / LEP + SEPP for every address" on every
 * council page — true, identical everywhere. Shows the precinct count when the
 * council's served provisions carry precincts; otherwise exactly that copy.
 */
export function profileTile(profile: CouncilProfile | null): TileContent {
  const generic: TileContent = {
    label: 'Coverage',
    value: 'All NSW',
    sub: 'LEP + SEPP for every address',
  }
  if (!profile) return generic

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
 *
 * An unknown profile (the count query failed) is not the same as a council with
 * nothing: saying "Not yet published" for it would be a false claim about that
 * council, so it says the count could not be read instead.
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
  if (!profile) {
    return { label: 'DCP controls', value: 'Not counted', sub: 'Could not be read just now' }
  }
  if (profile.controls > 0) {
    return {
      label: 'DCP controls',
      value: `${profile.controls} structured controls`,
      sub: 'Setbacks, parking, height',
    }
  }
  return { label: 'DCP controls', value: 'Coming soon', sub: 'Not yet published' }
}
