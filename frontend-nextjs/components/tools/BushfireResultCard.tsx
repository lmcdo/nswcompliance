'use client'

import { DATA_PROVENANCE } from '@/lib/disclaimers'

interface BushfireCompliance {
  state_legislation: string | null
  rfs_referral_required: boolean | null
  rfs_referral_note?: string | null
  rfs_referral_triggers: string[] | null
  cdc_pathway_available: boolean | null
  clearing_10_50_entitled: boolean | null
  clearing_10_50_exceptions: string | null
  cross_overlays: Array<{ type: string; value: string; source: string }> | null
  estimated_consultant_costs: string | null
  zone: string | null
  compliance_depth: string
  legislation_url: string | null
}

interface BushfireOutputs {
  is_bushfire_prone: boolean | null
  designation_source: string | null
  designation_category: string | null
  designation_guideline: string | null
  estimated_bal_band: string | null
  bal_assessment_likely_required: boolean | null
  bal_formal_assessment_cost_range: string | null
  bal_assessor_directory_url: string | null
  fire_signal: 'none' | 'low' | 'moderate' | 'elevated' | 'unavailable'
  compliance: BushfireCompliance
  data_currency: string
}

export interface BushfireResult {
  address: string
  lat: number
  lng: number
  run_date: string
  outputs: BushfireOutputs
  confidence: 'high' | 'medium' | 'low'
  data_sources: string[]
  report_id?: string
  report_token?: string
}

const FIRE_SIGNAL_META: Record<string, { label: string; sublabel: string; badge: string }> = {
  none: {
    label: 'Not bushfire prone',
    sublabel: 'This property is not on the NSW RFS Bush Fire Prone Land Map. No bushfire construction requirements apply.',
    badge: 'bg-green-100 text-green-800',
  },
  low: {
    label: 'Bushfire prone — lower category',
    sublabel: 'This property is on the RFS Bush Fire Prone Land Map in a lower designation category. A BAL assessment is required before building.',
    badge: 'bg-yellow-100 text-yellow-800',
  },
  moderate: {
    label: 'Bushfire prone — moderate category',
    sublabel: 'This property is mapped in a moderate bushfire designation category. Bushfire-rated construction under AS 3959 applies, and a Rural Fire Service referral applies to trigger developments such as subdivision or special fire protection purposes.',
    badge: 'bg-orange-100 text-orange-800',
  },
  elevated: {
    label: 'Bushfire prone — highest category',
    sublabel: 'This property is in the highest bushfire designation category on the RFS map. AS 3959 construction standards apply, and the fast-track CDC approval pathway is not available.',
    badge: 'bg-red-100 text-red-800',
  },
  unavailable: {
    label: 'Data unavailable',
    sublabel: 'We couldn\'t query the NSW RFS Bush Fire Prone Land Map for this address. Check the RFS portal directly or contact your council.',
    badge: 'bg-gray-100 text-gray-600',
  },
}

export function BushfireResultCard({ result }: { result: BushfireResult }) {
  const o = result.outputs
  const signal = o.fire_signal ?? 'unavailable'
  const signalMeta = FIRE_SIGNAL_META[signal] ?? FIRE_SIGNAL_META.unavailable
  const c = o.compliance

  const findings: { label: string; value: string; detail: string; severity: 'green' | 'amber' | 'red' }[] = []

  // BFPL designation
  if (o.is_bushfire_prone === null) {
    findings.push({
      label: 'NSW RFS Bush Fire Prone Land Map',
      value: 'Data unavailable',
      detail: 'Could not determine bushfire prone land status. This does not indicate absence of risk — contact the local council or check the RFS Bush Fire Prone Land Map directly.',
      severity: 'amber',
    })
  } else if (o.is_bushfire_prone) {
    findings.push({
      label: 'NSW RFS Bush Fire Prone Land Map',
      value: o.designation_category ?? 'Bushfire prone land',
      detail: 'This property is officially mapped as bushfire prone. Your insurer will load your premium, and any building work must comply with bushfire construction standards (AS 3959).',
      severity: signal === 'elevated' ? 'red' : 'amber',
    })
  } else {
    findings.push({
      label: 'NSW RFS Bush Fire Prone Land Map',
      value: 'Not bushfire prone',
      detail: 'This property is not mapped as bushfire prone land. No bushfire-specific construction standards or RFS referrals are required.',
      severity: 'green',
    })
  }

  // BAL band
  if (o.estimated_bal_band) {
    const isHigh = o.estimated_bal_band === 'BAL-40 to BAL-FZ'
    const isMid = o.estimated_bal_band === 'BAL-29'
    const isLow = o.estimated_bal_band === 'BAL-LOW'

    let balDetail: string
    if (isHigh) {
      balDetail = 'At this BAL level, construction costs increase substantially — fire-rated windows, non-combustible cladding, and ember protection are all mandatory. You cannot use the fast-track CDC pathway; a full DA with RFS referral is required.'
    } else if (isMid) {
      balDetail = 'Your builder will need to use bushfire-rated materials and construction methods under AS 3959. Budget for 10–20% higher build costs compared to a non-bushfire site. A formal BAL assessment is required before approval.'
    } else if (isLow) {
      balDetail = 'BAL-LOW means no special bushfire construction requirements apply. Standard building materials and methods are acceptable.'
    } else {
      balDetail = 'A formal BAL assessment by a qualified practitioner will confirm the exact rating. Your builder and certifier both need this before construction can start.'
    }

    findings.push({
      label: 'Estimated Bushfire Attack Level (BAL)',
      value: o.estimated_bal_band,
      detail: balDetail,
      severity: isHigh ? 'red' : isLow ? 'green' : 'amber',
    })
  }

  // RFS referral — three-state. On bushfire prone land the answer depends on
  // the proposal (null), so render the conditional note + the s4.14 triggers
  // rather than a bare Yes/No.
  if (c?.rfs_referral_required === true) {
    findings.push({
      label: 'RFS referral (s4.14 EP&A Act)',
      value: 'Required for any new development',
      detail: 'The Rural Fire Service must be consulted on any DA for this property. This typically adds 4–6 weeks to the approval timeline. Factor this into the project schedule.',
      severity: 'red',
    })
  } else if (c?.rfs_referral_required === false) {
    findings.push({
      label: 'RFS referral',
      value: 'Not required',
      detail: 'No Rural Fire Service consultation needed for development at this property.',
      severity: 'green',
    })
  } else if (o.is_bushfire_prone === true) {
    const note = c?.rfs_referral_note
      ?? 'Referral to the NSW Rural Fire Service applies only if the proposal matches a trigger below. Other development on bush fire prone land is assessed by the council against Planning for Bush Fire Protection.'
    const triggers = c?.rfs_referral_triggers?.length
      ? ` Triggers: ${c.rfs_referral_triggers.join('; ')}.`
      : ''
    findings.push({
      label: 'RFS referral (s4.14 EP&A Act)',
      value: 'Depends on the proposal',
      detail: `${note}${triggers}`,
      severity: 'amber',
    })
  }

  // CDC pathway
  if (c?.cdc_pathway_available === true) {
    findings.push({
      label: 'Fast-track approval (CDC)',
      value: 'Available',
      detail: 'You can use the Complying Development Certificate pathway for standard builds — faster and cheaper than a full DA. Your private certifier can issue approval without council involvement.',
      severity: 'green',
    })
  } else if (c?.cdc_pathway_available === false) {
    findings.push({
      label: 'Fast-track approval (CDC)',
      value: 'Not available — DA required',
      detail: 'The bushfire risk level at this site means you must go through the full Development Application process with council. CDCs are only available for properties at BAL-29 or below.',
      severity: 'red',
    })
  }

  // 10/50 clearing — three-state. On bushfire prone land the entitlement
  // depends on the RFS 10/50 entitlement area map (null), so render the
  // conditional wording rather than a bare Yes.
  if (c?.clearing_10_50_entitled === true) {
    findings.push({
      label: '10/50 vegetation clearing',
      value: 'Entitled to clear',
      detail: 'You can clear trees within 10m and managed vegetation within 50m of your home without council approval. This is a significant maintenance benefit on bushfire prone land.',
      severity: 'green',
    })
  } else if (c?.clearing_10_50_entitled === false) {
    findings.push({
      label: '10/50 vegetation clearing',
      value: 'Does not apply',
      detail: c?.clearing_10_50_exceptions
        ? `Clearing entitlement is excluded at this site. ${c.clearing_10_50_exceptions}`
        : 'The 10/50 clearing entitlement does not apply to this property. You\'ll need separate approval to clear vegetation near the dwelling.',
      severity: 'amber',
    })
  } else if (o.is_bushfire_prone === true) {
    findings.push({
      label: '10/50 vegetation clearing',
      value: 'Depends on the RFS entitlement area map',
      detail: c?.clearing_10_50_exceptions
        ?? 'Whether the 10/50 vegetation clearing scheme applies here depends on the RFS 10/50 entitlement area map — check the address in the RFS online 10/50 tool. Entitlements do not apply within threatened species habitat or 40m of a waterway.',
      severity: 'amber',
    })
  }

  // Cross-overlays
  if (c?.cross_overlays && c.cross_overlays.length > 0) {
    for (const overlay of c.cross_overlays) {
      findings.push({
        label: `${overlay.source}`,
        value: `${overlay.type.charAt(0).toUpperCase() + overlay.type.slice(1)} overlay — ${overlay.value}`,
        detail: 'Additional planning overlay at this site. This may affect what you can build and how approvals are assessed — check with your planner.',
        severity: 'amber',
      })
    }
  }

  const sevColor = { green: 'bg-green-500', amber: 'bg-amber-400', red: 'bg-red-500' }

  return (
    <div className="bg-white rounded-xl border border-gray-200 mb-6">
      {/* Header — signal badge + address */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <h2 className="font-semibold text-gray-900 text-base">{result.address}</h2>
          <span className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${signalMeta.badge}`}>
            {signalMeta.label}
          </span>
        </div>
        <p className="text-sm text-gray-600">{signalMeta.sublabel}</p>
      </div>

      {/* Findings — value + explanation */}
      <div className="border-t border-gray-100 divide-y divide-gray-50">
        {findings.map(({ label, value, detail, severity }) => (
          <div key={label} className="px-5 py-4">
            <div className="flex items-center gap-2.5 mb-1">
              <span className={`shrink-0 w-2.5 h-2.5 rounded-full ${sevColor[severity]}`} />
              <span className="text-sm font-medium text-gray-900">{value}</span>
            </div>
            <p className="text-xs text-gray-500 ml-5 leading-relaxed">{detail}</p>
            <p className="text-[11px] text-gray-400 ml-5 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Consultant costs + BAL assessor link */}
      {o.is_bushfire_prone && (c?.estimated_consultant_costs || o.bal_assessor_directory_url) && (
        <div className="px-5 py-4 bg-gray-50 border-t border-gray-100">
          {c?.estimated_consultant_costs && (
            <p className="text-xs text-gray-600 mb-2">
              <span className="font-medium">Estimated consultant costs:</span> {c.estimated_consultant_costs}
            </p>
          )}
          {o.bal_assessor_directory_url && (
            <a
              href={o.bal_assessor_directory_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-teal-600 hover:text-teal-700 underline"
            >
              Find a qualified BAL assessor (RFS directory) &rarr;
            </a>
          )}
        </div>
      )}

      {/* Legislation link */}
      {c?.legislation_url && (
        <div className="px-5 py-3 border-t border-gray-100">
          <a
            href={c.legislation_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-teal-600 hover:text-teal-700 underline"
          >
            {c.state_legislation ?? 'View applicable legislation'} &rarr;
          </a>
        </div>
      )}

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Screening tool — not a formal BAL assessment. Obtain a bushfire assessment from a practitioner
          listed in the RFS directory before development on bushfire prone land.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          {DATA_PROVENANCE.bushfire}
        </p>
      </div>
    </div>
  )
}
