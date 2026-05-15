'use client'

import { DATA_PROVENANCE } from '@/lib/disclaimers'

interface HazardScore {
  hazard: string
  raw_score: number
  weight: number
  weighted_score: number
  present: boolean
  detail: string
  confidence: string
  data_source: string
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

interface ClimateRiskOutputs {
  score: number
  band: string
  hazards: HazardScore[]
  interaction_bonus: number
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

const BAND_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  Low:       { bg: 'bg-green-50',  text: 'text-green-700',  border: 'border-green-100' },
  Moderate:  { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-100' },
  High:      { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-100' },
  'Very High': { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-100' },
  Extreme:   { bg: 'bg-red-100',  text: 'text-red-900',   border: 'border-red-200' },
}

const HAZARD_META: Record<string, { label: string; icon: string; explanation: string }> = {
  flood: {
    label: 'Flood',
    icon: '💧',
    explanation: 'Whether the property is within a flood planning area under the local environmental plan. Properties in flood zones face insurance loading, construction constraints, and disclosure obligations on sale.',
  },
  bushfire: {
    label: 'Bushfire',
    icon: '🔥',
    explanation: 'Whether the property is on the NSW RFS Bush Fire Prone Land Map. Mapped properties must comply with AS 3959 construction standards and may require a formal BAL assessment before building.',
  },
  coastal: {
    label: 'Coastal Hazard',
    icon: '🌊',
    explanation: 'Exposure to SEPP (Resilience and Hazards) 2021 coastal management zones — wetlands, littoral rainforest, coastal environment areas, and coastal use areas. These overlays trigger additional assessment requirements for development.',
  },
  fire_history: {
    label: 'Fire History',
    icon: '🌲',
    explanation: 'Number of recorded fire events at this location from the NPWS fire history dataset. Repeated burn history indicates higher ongoing risk — vegetation regrows and fuel loads accumulate over 5–10 year cycles.',
  },
  heat: {
    label: 'Heat Trajectory',
    icon: '☀️',
    explanation: 'Projected increase in days over 35°C from baseline to 2090, from NARCliM 2.0 regional climate projections. Western Sydney is one of the fastest-heating urban regions in Australia.',
  },
}

const INTERACTION_EXPLANATIONS: Record<string, string> = {
  'bushfire+fire_history': 'Repeated burn history in a bushfire-prone area — fuel loads accumulate over 5–10 year cycles, increasing structural risk with each regrowth period.',
  'flood+coastal': 'Riverine flood + tidal inundation can occur simultaneously during coastal storms — compound inundation events produce water levels higher than either hazard alone.',
  'bushfire+heat': 'Rising temperatures dry vegetation and extend fire seasons. By 2090, Western Sydney fire danger days could increase 20–30% under high emissions.',
  'flood+heat': 'Extreme heat drives more intense convective storms. A warming atmosphere holds ~7% more moisture per degree — flash flood intensity increases even as average rainfall decreases.',
}

function formatInteractionKey(h1: string, h2: string): string {
  return [h1, h2].sort().join('+')
}

export function ClimateRiskResultCard({ result }: { result: ClimateRiskResult }) {
  const o = result.outputs
  const bandStyle = BAND_STYLES[o.band] ?? BAND_STYLES.Moderate
  const narclim = o.narclim_summary

  // Identify active interaction pairs
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
        explanation: INTERACTION_EXPLANATIONS[key] ?? 'Compound hazard interaction detected.',
      })
    }
  }

  return (
    <div className="space-y-4">
      {/* Score header */}
      <div className={`rounded-xl border ${bandStyle.border} ${bandStyle.bg} p-6`}>
        <div className="flex items-center justify-between">
          <div>
            <p className={`text-xs font-medium uppercase tracking-wide mb-1 ${bandStyle.text}`}>
              Climate Risk Score
            </p>
            <p className={`text-4xl font-bold ${bandStyle.text}`}>
              {o.score} <span className="text-lg font-semibold opacity-60">/ 100</span>
            </p>
            <p className={`text-sm mt-1 font-medium ${bandStyle.text}`}>{o.band}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">{result.address}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              v{o.methodology_version} · {result.run_date}
            </p>
          </div>
        </div>
      </div>

      {/* Per-hazard breakdown */}
      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Hazard breakdown — 5 categories, 20 points each
          </p>
        </div>
        <div className="divide-y divide-gray-100">
          {o.hazards.map((h) => {
            const meta = HAZARD_META[h.hazard] ?? { label: h.hazard, icon: '·', explanation: '' }
            const points = Math.round(h.weighted_score * 100)
            const maxPoints = Math.round(h.weight * 100)
            const pctFill = h.raw_score * 100

            return (
              <div key={h.hazard} className="px-5 py-4">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{meta.icon}</span>
                    <span className="text-sm font-medium text-gray-900">{meta.label}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${h.present ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
                      {h.present ? 'Exposed' : 'Not exposed'}
                    </span>
                  </div>
                  <span className="text-xs font-mono text-gray-600">
                    {points} / {maxPoints}
                  </span>
                </div>

                {/* Score bar */}
                <div className="w-full h-1.5 bg-gray-100 rounded-full mb-2">
                  <div
                    className={`h-1.5 rounded-full transition-all ${
                      pctFill > 60 ? 'bg-red-400' : pctFill > 30 ? 'bg-amber-400' : pctFill > 0 ? 'bg-yellow-300' : 'bg-green-300'
                    }`}
                    style={{ width: `${Math.max(pctFill, pctFill > 0 ? 3 : 0)}%` }}
                  />
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

      {/* NARCliM trajectory data */}
      {narclim && (narclim.hot_days_baseline != null || narclim.temp_baseline != null) && (
        <div className="rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Climate projections — NARCliM 2.0 (AdaptNSW)
            </p>
          </div>
          <div className="p-5 space-y-4">
            {/* Hot days trajectory */}
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
                      <p className="text-sm font-semibold text-amber-700">
                        {Math.round(narclim.hot_days_mid_century_high)} days
                      </p>
                    </div>
                  )}
                  {narclim.hot_days_late_century_mid != null && (
                    <div className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs text-gray-400">2090 (SSP2-4.5)</p>
                      <p className="text-sm font-semibold text-orange-700">
                        {Math.round(narclim.hot_days_late_century_mid)} days
                      </p>
                    </div>
                  )}
                  {narclim.hot_days_late_century_high != null && (
                    <div className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs text-gray-400">2090 (SSP3-7.0)</p>
                      <p className="text-sm font-semibold text-red-700">
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

            {/* Temperature + precipitation */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {narclim.temp_delta_2090 != null && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Mean temperature change by 2090</p>
                  <p className="text-xl font-bold text-red-600">
                    {narclim.temp_delta_2090 > 0 ? '+' : ''}{narclim.temp_delta_2090.toFixed(1)}°C
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    This shifts the entire distribution — what is currently
                    a &ldquo;hot year&rdquo; becomes the new average.
                  </p>
                </div>
              )}
              {narclim.precip_delta_2090 != null && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Precipitation trend by 2090</p>
                  <p className="text-xl font-bold text-amber-600">
                    {narclim.precip_delta_2090 > 0 ? '+' : ''}{narclim.precip_delta_2090.toFixed(1)} mm/day
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {narclim.precip_delta_2090 < 0
                      ? 'A drying trend means less frequent rainfall — but when rain comes, it tends to be more intense. This increases both drought and flash flood risk.'
                      : 'Increasing average rainfall raises baseline flood risk and soil saturation levels.'}
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

      {/* Compound interactions */}
      {interactionPairs.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
          <p className="text-xs font-medium text-amber-700 uppercase tracking-wide mb-3">
            Compound hazard interactions detected (+{Math.round(o.interaction_bonus * 100)} points)
          </p>
          <div className="space-y-3">
            {interactionPairs.map(({ key, label, explanation }) => (
              <div key={key}>
                <p className="text-sm font-medium text-gray-900">{label}</p>
                <p className="text-xs text-gray-600 mt-0.5">{explanation}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-amber-600 mt-4">
            Climate impacts are cascading and compounding across systems (IPCC AR6 WGII, high confidence).
          </p>
        </div>
      )}

      {/* How to read the score */}
      <div className="rounded-xl border border-gray-200 p-5">
        <p className="text-sm font-semibold text-gray-900 mb-3">How to read this score</p>
        <div className="grid grid-cols-5 gap-1.5 mb-4">
          {[
            { band: 'Low', range: '1–20', bg: 'bg-green-100 text-green-800' },
            { band: 'Moderate', range: '21–40', bg: 'bg-yellow-100 text-yellow-800' },
            { band: 'High', range: '41–60', bg: 'bg-orange-100 text-orange-800' },
            { band: 'V. High', range: '61–80', bg: 'bg-red-100 text-red-800' },
            { band: 'Extreme', range: '81–100', bg: 'bg-red-200 text-red-900' },
          ].map(({ band, range, bg }) => (
            <div key={band} className={`rounded-lg px-2 py-1.5 text-center ${bg}`}>
              <p className="text-xs font-semibold">{band}</p>
              <p className="text-xs">{range}</p>
            </div>
          ))}
        </div>
        <div className="space-y-2 text-xs text-gray-500">
          <p>
            <strong className="text-gray-700">Equal weighting (V1):</strong> each hazard
            contributes up to 20 points. This is a simplifying assumption — V2 will weight
            by projected loss severity.
          </p>
          <p>
            <strong className="text-gray-700">Deterministic:</strong> same address always
            produces the same score. No AI interpretation, no machine learning, no probabilistic
            element.
          </p>
          <p>
            <strong className="text-gray-700">Exposure, not prediction:</strong> the score
            measures hazard exposure — not the probability of damage. Property-specific factors
            (construction type, floor height, vegetation management) are not included.
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
        {o.disclaimer}
      </p>
    </div>
  )
}
