import { BUSHFIRE_LGAS, describeBfplCoverage } from '@/lib/lga-data/bushfire-lgas'

describe('describeBfplCoverage', () => {
  it('says none for 0, never "about 0%"', () => {
    expect(describeBfplCoverage(0)).toBe('none')
  })
  it('says less than 1% for a small non-zero share, never "about 1%"', () => {
    expect(describeBfplCoverage(0.7)).toBe('less than 1%')
  })
  it('rounds a measured share', () => {
    expect(describeBfplCoverage(65.8)).toBe('about 66%')
  })
})

describe('BUSHFIRE_LGAS coverage', () => {
  it('every council carries a measured share between 0 and 100', () => {
    for (const lga of BUSHFIRE_LGAS) {
      expect(typeof lga.bfplCoveragePct).toBe('number')
      expect(lga.bfplCoveragePct).toBeGreaterThanOrEqual(0)
      expect(lga.bfplCoveragePct).toBeLessThanOrEqual(100)
    }
  })
  it('a council measured at 0% never claims parts are mapped', () => {
    for (const lga of BUSHFIRE_LGAS.filter((l) => l.bfplCoveragePct === 0)) {
      for (const f of lga.faqs) expect(f.a).not.toMatch(/Parts of .* are mapped/)
    }
  })
})
