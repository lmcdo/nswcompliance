/**
 * The climate card must render THREE hazard states, not two.
 *
 * `_normalize_heat` returns `present: false, available: false` when NARCliM has
 * no value for the point — the source could not be reached. The card used to
 * branch only on `present`, so that rendered as "Not present": a failed lookup
 * served as a confident negative about the property. That is the DQ-36 class,
 * and it is the same defect #885 fixed for shadow.
 *
 * Raised by cross-review on PR #889 and confirmed on the evidence.
 */
import { render, screen } from '@testing-library/react'
import { ClimateRiskResultCard, type ClimateRiskResult } from '@/components/tools/ClimateRiskResultCard'

function makeResult(overrides: Partial<ClimateRiskResult['outputs']> = {}): ClimateRiskResult {
  return {
    address: '1 Test St, Sydney NSW 2000',
    lat: -33.87,
    lng: 151.21,
    run_date: '2026-08-07',
    confidence: 'medium',
    data_sources: ['spatial_overlays'],
    outputs: {
      methodology_version: '1.1',
      data_date: '2026-05-18',
      disclaimer: 'Climate Risk Awareness Score v1.1.',
      narclim_summary: null,
      hazards: [
        {
          hazard: 'flood', present: true, detail: 'Flood planning layer: Yes',
          confidence: 'high', confidence_reason: 'intersects', data_source: 'EPI', available: true,
        },
        {
          hazard: 'bushfire', present: false, detail: 'Bushfire Prone Land: No',
          confidence: 'high', confidence_reason: 'queried, clear', data_source: 'RFS', available: true,
        },
        {
          hazard: 'heat', present: false, detail: 'NARCliM data not available for this location',
          confidence: 'low', confidence_reason: 'outside model domain',
          data_source: 'NARCliM 2.0 — unavailable', available: false,
        },
      ],
      ...overrides,
    },
  }
}

describe('ClimateRiskResultCard — unavailable is not absent', () => {
  it('renders an unavailable hazard as "Not checked", never "Not present"', () => {
    render(<ClimateRiskResultCard result={makeResult()} />)

    // One genuine negative (bushfire) — so "Not present" must appear exactly once,
    // not twice. Before the fix, heat produced a second one.
    expect(screen.getAllByText('Not present')).toHaveLength(1)
    expect(screen.getByText('Not checked')).toBeInTheDocument()
  })

  it('excludes unavailable hazards from the denominator', () => {
    render(<ClimateRiskResultCard result={makeResult()} />)
    // 3 hazards, 1 unavailable => 2 checked, 1 present. Saying "1 of 3" would
    // claim three categories were checked when only two were.
    expect(
      screen.getByText(/1 of 2 mapped hazard categories present/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/1 of 3 mapped hazard categories/i)).not.toBeInTheDocument()
  })

  it('states plainly that an unchecked category is not a finding of no hazard', () => {
    render(<ClimateRiskResultCard result={makeResult()} />)
    expect(screen.getByText(/could not be\s+checked/i)).toBeInTheDocument()
    expect(screen.getByText(/not a finding of no hazard/i)).toBeInTheDocument()
  })

  it('does not render the composite score or band even if a stale payload carries them', () => {
    // Belt and braces: the API no longer returns these, but a cached or replayed
    // payload must not resurrect a rendered composite.
    const stale = makeResult()
    ;(stale.outputs as unknown as Record<string, unknown>).score = 62
    ;(stale.outputs as unknown as Record<string, unknown>).band = 'High'
    const { container } = render(<ClimateRiskResultCard result={stale} />)
    expect(container.textContent).not.toMatch(/\b62\b/)
    expect(container.textContent).not.toMatch(/\bHigh\b/)
  })

  it('when every hazard is available the denominator is the full list', () => {
    const allAvailable = makeResult({
      hazards: makeResult().outputs.hazards.map(h => ({ ...h, available: true })),
    })
    render(<ClimateRiskResultCard result={allAvailable} />)
    expect(screen.getByText(/1 of 3 mapped hazard categories present/i)).toBeInTheDocument()
    expect(screen.queryByText('Not checked')).not.toBeInTheDocument()
  })
})
