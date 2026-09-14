/**
 * These two tiles are public claims about a whole council, on an indexed page.
 *
 * The middle one used to say "Available" whenever a flag was set, and on
 * 2026-09-10 eight councils were found asserting DCP data with zero rows behind
 * it. A count cannot drift away from the truth the way a vague word can, but a
 * count rendered from a failed query can still lie — so the rule under test is:
 * an unknown must never render as a claim.
 */
import fs from 'fs'
import path from 'path'
import { profileTile, dcpControlsTile, type CouncilProfile } from './council-profile-tile'

const p = (o: Partial<CouncilProfile> = {}): CouncilProfile => ({
  controls: 0,
  precincts: 0,
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

  it('shows the precinct count when the served provisions carry precincts', () => {
    const t = profileTile(p({ precincts: 158 }))
    expect(t.label).toBe('Precincts')
    expect(t.value).toBe('158 precincts')
  })

  it('shows the generic copy when a council has no precincts', () => {
    expect(profileTile(p()).value).toBe('All NSW')
  })

  it('never names a "main constraint"', () => {
    // Removed before merge: the share was of overlay ROWS, not land area, so many
    // small heritage polygons could outrank one flood polygon covering most of a
    // council. No branch may make that claim.
    for (const t of [profileTile(null), profileTile(p()), profileTile(p({ precincts: 62, controls: 9 }))]) {
      expect(t.label).not.toMatch(/constraint/i)
    }
    const page = fs.readFileSync(
      path.join(__dirname, '../app/(tools)/planning-controls/[lga-slug]/page.tsx'),
      'utf8',
    )
    expect(page).not.toMatch(/spatial_overlays/)
    expect(page).not.toMatch(/Main constraint/)
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
    // Burwood: structured controls, zero provisions. A count is true; "Available" was not.
    expect(dcpControlsTile(p({ controls: 24 }), 0, false).value).toBe('24 structured controls')
  })

  it('says Coming soon when the council genuinely has nothing', () => {
    expect(dcpControlsTile(p({ controls: 0 }), 0, false).value).toBe('Coming soon')
  })

  it('does not claim "Not yet published" when the count could not be read', () => {
    // A failed query is an unknown, not an absence: "Not yet published" would be a
    // false statement about a council that may have controls.
    const t = dcpControlsTile(null, 0, false)
    expect(t.value).toBe('Not counted')
    expect(t.sub).not.toMatch(/published/i)
    expect(t.value).not.toMatch(/coming soon/i)
  })

  it('does not claim provisions when showTopics is set but the total is zero', () => {
    // Guard against a caller passing showTopics with nothing behind it — the
    // tile would otherwise read "0 provisions", which looks like a measurement
    // rather than an absence.
    expect(dcpControlsTile(p({ controls: 24 }), 0, true).value).toBe('24 structured controls')
  })
})

describe('the control count reads the served set', () => {
  it('excludes rows held for review, as fetch_dcp_setbacks does', () => {
    // A row held for review (e.g. a repealed plan's number) is not served, so it must
    // not be counted in a public "N structured controls" claim.
    const page = fs.readFileSync(
      path.join(__dirname, '../app/(tools)/planning-controls/[lga-slug]/page.tsx'),
      'utf8',
    )
    // The SQL template literal: from its FROM clause to the closing backtick.
    const start = page.indexOf('FROM dcp_setback_controls')
    expect(start).toBeGreaterThan(-1)
    const q = page.slice(start, page.indexOf('`', start))
    expect(q).toMatch(/is_current = TRUE/)
    expect(q).toMatch(/needs_review IS NULL OR needs_review = FALSE/)
  })
})
