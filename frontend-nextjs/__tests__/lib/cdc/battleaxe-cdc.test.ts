import { readFileSync } from 'fs'
import { join } from 'path'
import { applyBattleaxeLimits, NEAR_LIMIT_M, type BattleaxeLimits } from '@/lib/cdc/battleaxe-cdc'
import type { BattleaxeDetectionResult } from '@/lib/geometry/lot-shape-analysis'

// Stands in for the stored rows; a different value than the law proves the code reads it.
const LIMITS: BattleaxeLimits = { accessMinWidth: 3, lotMinDimension: 12, ref: 'Sch 1 s2(1)(c)', quote: 'q', pdfPage: 88 }

function lot(access: number, width = 15, area = 300): BattleaxeDetectionResult {
  return {
    isBattleaxe: true, confidence: 0.9, accessWayWidth: access, accessWayLength: 20,
    mainLotWidth: width, mainLotArea: area, meetsMinimumRequirements: null, complianceIssues: [],
  }
}

describe('applyBattleaxeLimits', () => {
  it('no stored limits: not checked, never a pass', () => {
    const r = applyBattleaxeLimits(lot(5), null)
    expect(r.meetsMinimumRequirements).toBeNull()
    expect(r.cdcStatus).toBe('not_checked')
    expect(r.complianceIssues[0]).toMatch(/could not be read, so this was not checked/)
  })

  it('below the stored width: fails, names the route, the measurement, the clause and the next step', () => {
    const r = applyBattleaxeLimits(lot(2.4), LIMITS)
    expect(r.meetsMinimumRequirements).toBe(false)
    const m = r.complianceIssues.join(' ')
    expect(m).toContain('2.4 m wide')
    expect(m).toContain('complying development (CDC)')
    expect(m).toContain('SEPP (Housing) 2021 Sch 1 s2(1)(c)')
    expect(m).toContain('cadastre map')
    expect(m).toContain('a DA is assessed against the council')
    expect(r.cdcPdfPage).toBe(88)
  })

  it('the limit comes from the rows: a different stored width changes the answer', () => {
    expect(applyBattleaxeLimits(lot(4), LIMITS).meetsMinimumRequirements).toBe(true)
    expect(applyBattleaxeLimits(lot(4), { ...LIMITS, accessMinWidth: 5 }).meetsMinimumRequirements).toBe(false)
  })

  it('within the near band: close, not pass or fail', () => {
    const r = applyBattleaxeLimits(lot(3 - NEAR_LIMIT_M / 2), LIMITS)
    expect(r.meetsMinimumRequirements).toBeNull()
    expect(r.cdcStatus).toBe('near')
    expect(r.complianceIssues[0]).toMatch(/close to the 3 m/)
  })

  it('main lot too small fails on the 12 m by 12 m test', () => {
    const r = applyBattleaxeLimits(lot(4, 10, 100), LIMITS)
    expect(r.meetsMinimumRequirements).toBe(false)
    expect(r.complianceIssues.join(' ')).toContain('12 m by 12 m')
  })

  it('the geometry module carries no typed CDC limits', () => {
    const src = readFileSync(join(__dirname, '../../../lib/geometry/lot-shape-analysis.ts'), 'utf8')
    expect(src).not.toMatch(/MIN_ACCESS_WAY_WIDTH|MIN_MAIN_LOT_DIMENSION|MIN_MAIN_LOT_AREA/)
    expect(src).not.toMatch(/below minimum/)
  })
})
