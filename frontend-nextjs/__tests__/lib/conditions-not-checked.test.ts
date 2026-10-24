import { readFileSync } from 'fs'
import { join } from 'path'
import { conditionsNotChecked, whyFromError } from '@/lib/conditions-not-checked'

const ALL_ANSWERED = { notChecked: [] as string[], bushfireProne: false }

describe('conditionsNotChecked: a failed check is named, never silent', () => {
  it('every check answered: nothing to report', () => {
    expect(conditionsNotChecked(ALL_ANSWERED)).toEqual([])
  })

  it('flood map timed out: says what, why and where', () => {
    const [m] = conditionsNotChecked({ ...ALL_ANSWERED, notChecked: ['flood'], notCheckedWhy: { flood: 'no_reply' } })
    expect(m.what).toBe('Flood')
    expect(m.why).toBe('the flood planning map did not reply in time')
    expect(m.whereUrl).toMatch(/^https:\/\//)
  })

  it('server busy (429) is said as busy, not as a fact', () => {
    const [m] = conditionsNotChecked({ ...ALL_ANSWERED, notChecked: ['spatial_overlays'], notCheckedWhy: { spatial_overlays: 'busy' } })
    expect(m.why).toMatch(/busy/)
  })

  it('bush fire unknown (null) is listed; a definite No is not', () => {
    expect(conditionsNotChecked({ ...ALL_ANSWERED, bushfireProne: null }).map((m) => m.what)).toContain('Bush fire')
    expect(conditionsNotChecked({ ...ALL_ANSWERED, bushfireProne: false })).toEqual([])
  })

  it('precinct lookup failed: listed, so an empty precinct section is not read as "no precinct"', () => {
    expect(conditionsNotChecked({ ...ALL_ANSWERED, notChecked: ['precinct'] }).map((m) => m.what)).toContain('Precinct (area-specific council rules)')
  })

  it('an existing plain-words note is reused without a doubled full stop', () => {
    const [m] = conditionsNotChecked({ ...ALL_ANSWERED, greenwebUnchecked: 'The Greenweb map did not answer.' })
    expect(m.why).toBe('The Greenweb map did not answer')
  })
})

describe('every lookup check is covered', () => {
  it('a failed acid sulfate check is listed (any LookupCheck that fails is named)', () => {
    expect(conditionsNotChecked({ ...ALL_ANSWERED, notChecked: ['acid_sulfate'] }).map((m) => m.what)).toContain('Acid sulfate soils')
  })
})

describe('whyFromError', () => {
  it('reads 429 as busy, abort/timeout as no reply, anything else as error', () => {
    expect(whyFromError(new Error('HTTP 429 Rate limit is exceeded'))).toBe('busy')
    expect(whyFromError(Object.assign(new Error('The operation was aborted'), { name: 'AbortError' }))).toBe('no_reply')
    expect(whyFromError(new Error('connection refused'))).toBe('error')
  })
})

describe('the rules page uses it', () => {
  const src = readFileSync(join(__dirname, '../../components/compliance/ProvisionsByTocStructure.tsx'), 'utf8')
  it('lists not-checked conditions above the rules', () => {
    expect(src).toMatch(/conditionsNotChecked\(propertyData\?\.constraints\)/)
  })
  it('a failed council lookup is not shown as "council not covered"', () => {
    expect(src).toMatch(/council-not-checked/)
  })
  it('the precinct lookup on the property path throws on error instead of returning null', () => {
    const pd = readFileSync(join(__dirname, '../../lib/property-data.ts'), 'utf8')
    expect(pd).toMatch(/throwOnError: true/)
    expect(pd).toMatch(/'precinct'\]/)
  })
})
