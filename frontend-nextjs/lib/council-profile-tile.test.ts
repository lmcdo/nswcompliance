/**
 * These two tiles are public claims about a whole council, on an indexed page.
 *
 * The middle one used to say "Available" whenever a flag was set, and on
 * 2026-09-10 eight councils were found asserting DCP data with zero rows behind
 * it. A count cannot drift away from the truth the way a vague word can, but a
 * count rendered from a failed query can still lie — so the rule under test is:
 * an unknown must never render as a claim.
 */
import {
  profileTile,
  dcpControlsTile,
  CONSTRAINT_LABEL,
  DOMINANT_MIN_PCT,
  type CouncilProfile,
} from './council-profile-tile'

const p = (o: Partial<CouncilProfile> = {}): CouncilProfile => ({
  controls: 0,
  precincts: 0,
  dominant: null,
  ...o,
})

describe('profileTile — the third tile', () => {
  it('falls back to the generic copy when the profile is unknown', () => {
    // The failure that matters: a dropped query must not produce an empty or
    // half-built claim about a council. It must produce the sentence that is
    // true of every council in NSW.
    expect(profileTile(null)).toEqual({
      label: 'Coverage',
      value: 'All NSW',
      sub: 'LEP + SEPP for every address',
    })
  })

  it('names the dominant constraint when one defines the LGA', () => {
    // Burwood, measured 2026-09-10: heritage is 47% of its mapped overlays.
    const t = profileTile(p({ dominant: { layer: 'Heritage', pct: 47 } }))
    expect(t.label).toBe('Main constraint')
    expect(t.value).toBe('Heritage 47%')
    expect(t.sub).toContain('mapped overlays')
  })

  it('does NOT name a constraint that sits below the threshold', () => {
    // The confusable negative. Northern Beaches biodiversity is 15%: real, but
    // not what defines the council. Calling it the main constraint would be an
    // overstatement of exactly the kind this page has already had to correct.
    const t = profileTile(p({ dominant: { layer: 'Biodiversity', pct: 15 } }))
    expect(t.label).not.toBe('Main constraint')
    expect(t.value).toBe('All NSW')
  })

  it('treats the threshold as inclusive at its stated value', () => {
    expect(profileTile(p({ dominant: { layer: 'Flood', pct: DOMINANT_MIN_PCT } })).label)
      .toBe('Main constraint')
    expect(profileTile(p({ dominant: { layer: 'Flood', pct: DOMINANT_MIN_PCT - 1 } })).label)
      .not.toBe('Main constraint')
  })

  it('falls back to precincts when no single constraint dominates', () => {
    // City of Sydney: 158 precincts and no overlay above the threshold. The
    // precinct count is the honest headline for that council.
    const t = profileTile(p({ precincts: 158 }))
    expect(t.label).toBe('Precincts')
    expect(t.value).toBe('158 precincts')
  })

  it('prefers a dominant constraint over a precinct count when both exist', () => {
    // Woollahra has 62 precincts AND heritage at 22%. Only one can head the
    // tile; the constraint is the thing that stops a development, so it wins.
    const t = profileTile(p({ precincts: 62, dominant: { layer: 'Heritage', pct: 22 } }))
    expect(t.label).toBe('Main constraint')
  })

  it('shows the generic copy when a council has neither', () => {
    expect(profileTile(p()).value).toBe('All NSW')
  })
})

describe('dcpControlsTile — the middle tile', () => {
  it('NEVER says "Available"', () => {
    // The whole reason this file exists. Every reachable branch, checked.
    const cases = [
      dcpControlsTile(null, 0, false),
      dcpControlsTile(null, 0, true),
      dcpControlsTile(p(), 0, false),
      dcpControlsTile(p({ controls: 24 }), 0, false),
      dcpControlsTile(p({ controls: 24 }), 500, true),
      dcpControlsTile(p({ controls: 0 }), 500, true),
    ]
    for (const c of cases) {
      expect(c.value).not.toBe('Available')
      expect(c.value.toLowerCase()).not.toContain('available')
    }
  })

  it('shows the provision count when full text is displayed', () => {
    expect(dcpControlsTile(p({ controls: 57 }), 2892, true).value).toBe('2,892 provisions')
  })

  it('shows the structured-control count when there is no provision text', () => {
    // Burwood: 24 structured controls, zero provisions. "24 structured
    // controls" is true; "Available" was not.
    expect(dcpControlsTile(p({ controls: 24 }), 0, false).value).toBe('24 structured controls')
  })

  it('says Coming soon when the council genuinely has nothing', () => {
    expect(dcpControlsTile(p({ controls: 0 }), 0, false).value).toBe('Coming soon')
  })

  it('says Coming soon rather than guessing when the profile is unknown', () => {
    // A failed query must not invent a count.
    expect(dcpControlsTile(null, 0, false).value).toBe('Coming soon')
  })

  it('does not claim provisions when showTopics is set but the total is zero', () => {
    // Guard against a caller passing showTopics with nothing behind it — the
    // tile would otherwise read "0 provisions", which looks like a measurement
    // rather than an absence.
    expect(dcpControlsTile(p({ controls: 24 }), 0, true).value).toBe('24 structured controls')
  })
})

describe('CONSTRAINT_LABEL', () => {
  it('only maps layers a reader can act on, in plain words', () => {
    for (const [key, label] of Object.entries(CONSTRAINT_LABEL)) {
      expect(key).toMatch(/^[a-z_]+$/)
      expect(label[0]).toBe(label[0].toUpperCase())
      expect(label.split(' ').length).toBeLessThanOrEqual(3)
    }
  })
})
