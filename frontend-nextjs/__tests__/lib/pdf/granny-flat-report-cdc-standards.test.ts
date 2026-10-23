import { readFileSync } from 'fs'
import { join } from 'path'

// The granny flat PDF once cited an older instrument ("cl 4.18", "Sch 3 Subdiv 4") and
// stated standards Schedule 1 does not set (3 m separation, 5 m wall height). The
// standards now come from one list naming SEPP (Housing) 2021 Schedule 1 sections.
const SRC = readFileSync(join(__dirname, '../../../lib/pdf/granny-flat-report.tsx'), 'utf8')
const PAGE = readFileSync(join(__dirname, '../../../app/reports/granny-flat/page.tsx'), 'utf8')

describe('granny flat report CDC standards', () => {
  it.each(['cl 4.18', 'Sch 3 Subdiv 4', "'Min 3 m'", "cdc: '5 m'", '1.5 m above 8 m', '3 m dimension'])(
    'no longer contains %s',
    (old) => {
      expect(SRC).not.toContain(old)
      expect(PAGE).not.toContain(old)
    },
  )

  it('every standard row names a Schedule 1 section', () => {
    const block = SRC.slice(SRC.indexOf('const CDC_SCHEDULE_1'), SRC.indexOf('];', SRC.indexOf('const CDC_SCHEDULE_1')))
    const rows = block.split('\n').filter((l) => l.includes('{ std:'))
    expect(rows.length).toBeGreaterThanOrEqual(8)
    for (const r of rows) expect(r).toMatch(/clause: 'SEPP \(Housing\) 2021 Schedule 1( s\d+(\(\d+\))?)?'/)
  })

  it('separation is stated as not set, never a distance', () => {
    expect(SRC).toMatch(/std: 'Separation from dwelling', req: 'Not set by Schedule 1'/)
  })
})
