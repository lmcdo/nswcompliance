'use client'

// Legal posture (ce-climate-risk-score-legal-assessment): never present the
// composite score as a headline verdict, and DO NOT use traffic-light
// (green/amber/red) colour coding — it implies a safety/danger rating the data
// does not support (a coastal town can out-score a far hotter western suburb).
// This card leads with the factual per-hazard exposure + NARCliM projection
// metrics, each with source and date; the composite index is retired from the
// headline, matching the brief's Climate Disclosure Profile.

// raw_score / weight / weighted_score are NOT in the API response — they are the
// composite model's arithmetic and nothing renders them. See
// services/climate_risk_score.py → to_dict.
interface HazardScore {
  hazard: string
  present: boolean
  detail: string
  confidence: string
  confidence_reason?: string
  data_source: string
  // Required, not optional: the API emits it on every hazard. false means the
  // source could not be reached for this point — which is NOT the same as the
  // hazard being absent, and must never render as "Not present".
  available: boolean
}

interface NARCliMSummary {
  grid_distance_km?: number
  hot_days_baseline?: number
  hot_days_delta_2050?: number
  hot_days_delta_2090?: number
  hot_days_mid_century_mid?: number
  hot_days_mid_century_high?: number
  hot_days_late_century_mid?: number
  hot_days_late_century_high?: number
  temp_baseline?: number
  temp_delta_2050?: number
  temp_delta_2090?: number
  precip_baseline?: number
  precip_delta_2050?: number
  precip_delta_2090?: number
  [key: string]: number | undefined
}

// The composite score, its band and the interaction bonus are deliberately not
// part of this contract. The card never rendered them (see the legal posture note
// at the top of this file) and they are no longer served at all.
interface ClimateRiskOutputs {
  hazards: HazardScore[]
  methodology_version: string
  data_date: string
  disclaimer: string
  narclim_summary: NARCliMSummary | null
}

export interface ClimateRiskResult {
  address: string
  lat: number
  lng: number
  run_date: string
  outputs: ClimateRiskOutputs
  confidence: string
  data_sources: string[]
}

const HAZARD_META: Record<string, { label: string; explanation: string }> = {
  flood: {
    label: 'Flood',
    explanation: 'Whether the property is within a flood planning area under the local environmental plan. Properties in flood zones face insurance loading, construction constraints, and disclosure obligations on sale.',
  },
  bushfire: {
    label: 'Bushfire',
    explanation: 'Whether the property is on the NSW RFS Bush Fire Prone Land Map. Mapped properties must comply with AS 3959 construction standards and may require a formal BAL assessment before building.',
  },
  coastal: {
    label: 'Coastal Hazard',
    explanation: 'Exposure to SEPP (Resilience and Hazards) 2021 coastal management zones — wetlands, littoral rainforest, coastal environment areas, and coastal use areas. These overlays trigger additional assessment requirements for development.',
  },
  fire_history: {
    label: 'Fire History',
    explanation: 'Number of recorded fire events at this location from the NPWS fire history dataset. Repeated burn history reflects accumulated fuel loads over 5–10 year regrowth cycles.',
  },
  heat: {
    label: 'Heat Trajectory',
    explanation: 'Projected increase in days over 35°C from baseline to 2090, from NARCliM 2.0 regional climate projections. Western Sydney is one of the fastest-heating urban regions in Australia.',
  },
}

const INTERACTION_EXPLANATIONS: Record<string, string> = {
  'bushfire+fire_history': 'Repeated burn history in a bushfire-prone area — fuel loads accumulate over 5–10 year cycles.',
  'flood+coastal': 'Riverine flood + tidal inundation can occur simultaneously during coastal storms — compound inundation events produce water levels higher than either hazard alone.',
  'bushfire+heat': 'Rising temperatures dry vegetation and extend fire seasons. By 2090, Western Sydney fire danger days could increase 20–30% under high emissions.',
  'flood+heat': 'Extreme heat drives more intense convective storms. A warming atmosphere holds ~7% more moisture per degree — flash flood intensity increases even as average rainfall decreases.',
}

function formatInteractionKey(h1: string, h2: string): string {
  return [h1, h2].sort().join('+')
}

export function ClimateRiskResultCard({ result }: { result: ClimateRiskResult }) {
  const o = result.outputs
  const narclim = o.narclim_summary

  const presentHazards = new Set(o.hazards.filter(h => h.present).map(h => h.hazard))
  const interactionPairs: { key: string; label: string; explanation: string }[] = []
  const PAIRS: [string, string][] = [
    ['bushfire', 'fire_history'],
    ['flood', 'coastal'],
    ['bushfire', 'heat'],
    ['flood', 'heat'],
  ]
  for (const [h1, h2] of PAIRS) {
    if (presentHazards.has(h1) && presentHazards.has(h2)) {
      const key = formatInteractionKey(h1, h2)
      const label1 = HAZARD_META[h1]?.label ?? h1
      const label2 = HAZARD_META[h2]?.label ?? h2
      interactionPairs.push({
        key,
        label: `${label1} + ${label2}`,
        explanation: INTERACTION_EXPLANATIONS[key] ?? 'Compound hazard interaction present.',
      })
    }
  }

  // Three states, not two. A hazard whose data source could not be reached is
  // NOT a hazard that is absent: _normalize_heat returns present=false with
  // available=false when NARCliM has no value for the point. Rendering that as
  // "Not present" turns a failed lookup into a confident negative (the DQ-36
  // class). Unavailable hazards are also excluded from the denominator — saying
  // "1 of 6" implies six were checked when only five were.
  const unavailable = o.hazards.filter(h => h.available === false)
  const checkedCount = o.hazards.length - unavailable.length
  const exposedCount = presentHazards.size

  return (
    <div className="space-y-4">
      {/* Neutral header — factual framing, no verdict, no traffic-light */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">
              Climate &amp; hazard exposure
            </p>
            <p className="text-lg font-semibold text-gray-900">
              {exposedCount} of {checkedCount} mapped hazard categories present at this address
            </p>
            {unavailable.length > 0 && (
              <p className="text-sm text-amber-800 mt-1">
                {unavailable.length} further{' '}
                {unavailable.length === 1 ? 'category' : 'categories'} could not be
                checked — {unavailable.map(h => HAZARD_META[h.hazard]?.label ?? h.hazard).join(', ')}.
                This is not a finding of no hazard; the data source returned nothing
                for this location. See the category list below for what was attempted.
              </p>
            )}
            <p className="text-sm text-gray-500 mt-1">
              A summary of the government hazard overlays and climate projections for this location.
              It reports exposure to published data — it is not a risk rating, a prediction, or a
              statement about safety, insurability, or value.
            </p>
          </div>
          <div className="text-right shrink-0 ml-4">
            <p className="text-xs text-gray-500">{result.address}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              v{o.methodology_version} · {result.run_date}
            </p>
          </div>
        </div>
      </div>

      {/* Per-hazard breakdown — each with its source */}
      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Hazard categories
          </p>
        </div>
        <div className="divide-y divide-gray-100">
          {o.hazards.map((h) => {
            const meta = HAZARD_META[h.hazard] ?? { label: h.hazard, explanation: '' }
            return (
              <div key={h.hazard} className="px-5 py-4">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-gray-900">{meta.label}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded border ${
                      h.available === false
                        ? 'border-amber-300 bg-amber-50 text-amber-800'
                        : h.present
                        ? 'border-gray-300 bg-gray-100 text-gray-700'
                        : 'border-gray-200 bg-white text-gray-400'
                    }`}
                  >
                    {h.available === false
                      ? 'Not checked'
                      : h.present
                      ? 'Present'
                      : 'Not present'}
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-1">{h.detail}</p>
                <p className="text-xs text-gray-400">{meta.explanation}</p>
                <p className="text-xs text-gray-400 mt-1">
                  Source: {h.data_source} · Confidence: {h.confidence}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      {/* NARCliM projections — factual metrics, scenario/epoch labelled, no danger colours */}
      {narclim && (narclim.hot_days_baseline != null || narclim.temp_baseline != null) && (
        <div className="rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Climate projections — NARCliM 2.0 (AdaptNSW)
            </p>
          </div>
          <div className="p-5 space-y-4">
            {narclim.hot_days_baseline != null && (
              <div>
                <p className="text-sm font-medium text-gray-900 mb-2">
                  Days over 35°C per year
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-gray-50 rounded-lg px-3 py-2">
                    <p className="text-xs text-gray-400">Baseline</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {Math.round(narclim.hot_days_baseline)} days
                    </p>
                  </div>
                  {narclim.hot_days_mid_century_high != null && (
                    <div className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs text-gray-400">2050 (SSP3-7.0)</p>
                      <p className="text-sm font-semibold text-gray-900">
                        {Math.round(narclim.hot_days_mid_century_high)} days
                      </p>
                    </div>
                  )}
                  {narclim.hot_days_late_century_mid != null && (
                    <div className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs text-gray-400">2090 (SSP2-4.5)</p>
                      <p className="text-sm font-semibold text-gray-900">
                        {Math.round(narclim.hot_days_late_century_mid)} days
                      </p>
                    </div>
                  )}
                  {narclim.hot_days_late_century_high != null && (
                    <div className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs text-gray-400">2090 (SSP3-7.0)</p>
                      <p className="text-sm font-semibold text-gray-900">
                        {Math.round(narclim.hot_days_late_century_high)} days
                      </p>
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  SSP2-4.5 = intermediate emissions · SSP3-7.0 = high emissions.
                  Each scenario represents a different global policy pathway — not a best/worst case.
                </p>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {narclim.temp_delta_2090 != null && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Mean temperature change by 2090 (SSP3-7.0)</p>
                  <p className="text-xl font-bold text-gray-900">
                    {narclim.temp_delta_2090 > 0 ? '+' : ''}{narclim.temp_delta_2090.toFixed(1)}°C
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    A shift in the mean moves the whole distribution — what is currently
                    a &ldquo;hot year&rdquo; sits closer to the new average.
                  </p>
                </div>
              )}
              {narclim.precip_delta_2090 != null && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Precipitation change by 2090 (SSP3-7.0)</p>
                  <p className="text-xl font-bold text-gray-900">
                    {narclim.precip_delta_2090 > 0 ? '+' : ''}{narclim.precip_delta_2090.toFixed(1)} mm/day
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {narclim.precip_delta_2090 < 0
                      ? 'A drying trend in the average; individual rainfall events can still be more intense in a warmer atmosphere.'
                      : 'An increase in average rainfall raises baseline soil saturation.'}
                  </p>
                </div>
              )}
            </div>

            {narclim.grid_distance_km != null && (
              <p className="text-xs text-gray-400">
                NARCliM grid cell {narclim.grid_distance_km.toFixed(1)}km from property.
                Resolution: 4km × 4km. Model: ACCESS-ESM1.5 downscaled by WRF.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Compound interactions — factual, no scoring language */}
      {interactionPairs.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
            Overlapping hazard categories at this address
          </p>
          <div className="space-y-3">
            {interactionPairs.map(({ key, label, explanation }) => (
              <div key={key}>
                <p className="text-sm font-medium text-gray-900">{label}</p>
                <p className="text-xs text-gray-600 mt-0.5">{explanation}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-4">
            Climate impacts can cascade and compound across systems (IPCC AR6 WGII, high confidence).
          </p>
        </div>
      )}

      {/* How to read this */}
      <div className="rounded-xl border border-gray-200 p-5">
        <p className="text-sm font-semibold text-gray-900 mb-3">How to read this</p>
        <div className="space-y-2 text-xs text-gray-500">
          <p>
            <strong className="text-gray-700">Exposure, not prediction:</strong> this reports which
            mapped hazards apply to the address and the published climate projections for the
            location — not the probability of damage. Property-specific factors (construction type,
            floor height, vegetation management) are not included.
          </p>
          <p>
            <strong className="text-gray-700">Deterministic:</strong> the same address always
            returns the same result. No AI interpretation, no machine learning, no probabilistic element.
          </p>
          <p>
            <strong className="text-gray-700">Each item is sourced:</strong> every hazard and
            projection carries the government dataset it came from and the currency date, so it can be
            checked against the original.
          </p>
        </div>
      </div>

      {/* Data sources */}
      <div className="rounded-xl border border-gray-200 p-5">
        <p className="text-sm font-semibold text-gray-900 mb-2">Data sources</p>
        <ul className="space-y-1">
          {result.data_sources.map((src) => (
            <li key={src} className="text-xs text-gray-500">• {src}</li>
          ))}
        </ul>
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-gray-400 leading-relaxed px-1">
        This summary reflects currently available government spatial data and modelled climate
        projections. It does not predict future events or substitute for site-specific professional
        assessment. It is factual information, not financial product advice, and is not a basis for
        a financial decision.
        {o.disclaimer ? ` ${o.disclaimer}` : ''}
      </p>
    </div>
  )
}
