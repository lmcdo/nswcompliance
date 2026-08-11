'use client';

import { useState, useMemo, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { WaitlistButton } from '@/components/reports/WaitlistButton';
import { DATA_PROVENANCE } from '@/lib/disclaimers';
import {
  SCENARIO_NOT_ASSESSED_LABEL, isScenarioUnavailable, scenarioUnavailableMessage,
} from '@/lib/not-assessed';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { posthog } from '@/components/providers/PostHogProvider';
import { OperationalTransparency, type TransparencyStep } from '@/components/tools/OperationalTransparency';

const SHADOW_STEPS: TransparencyStep[] = [
  { label: 'Calculating sun angles across 5 ADG scenarios…', ms: 0 },
  { label: 'Modelling shadow envelopes for each scenario…',  ms: 3000 },
  { label: 'Measuring shadow impact on neighbouring lots…',   ms: 8000 },
  { label: 'Checking ADG solar access test…',                 ms: 14000 },
  { label: 'Generating shadow diagrams…',                    ms: 20000 },
];

const ShadowMap = dynamic(
  () => import('@/components/reports/ShadowMap').then(m => m.ShadowMap),
  { ssr: false, loading: () => <div className="w-full h-full bg-gray-100 animate-pulse rounded" /> }
);


interface GeoJSONGeometry {
  type: string;
  coordinates: unknown[];
}

interface GeoJSONCollection {
  type: 'FeatureCollection';
  features: { type: 'Feature'; geometry: GeoJSONGeometry; properties?: Record<string, unknown> }[];
}

interface ShadowScenario {
  scenario: string;
  label: string;
  date: string;
  time_local: string;
  status?: 'computed' | 'unavailable';  // absent on pre-fix cached rows = computed
  error_note?: string | null;           // why a scenario has no measurements
  shadow_length_m: number | null;       // null when the scenario computation errored
  shadow_overlap_fraction: number | null;
  // null when the bearing is not meaningful: sun below the horizon, or so near
  // the zenith that a direction says nothing about a centimetres-long shadow.
  shadow_direction_deg: number | null;
  overlaps_subject_lot: boolean | null;
  shadow_on_lot: GeoJSONCollection | null;
  shadow_polygon: GeoJSONCollection | null;
}

interface ShadowOutputs {
  height_m: number;
  height_source: 'planning_portal' | 'spatial_overlays' | 'regulatory_provisions' | 'default' | null;
  lep_name: string | null;
  lot_polygon: GeoJSONGeometry | null;
  north_proxy_polygon: GeoJSONGeometry | null;
  scenarios: ShadowScenario[];
  adg_compliant: boolean | null;  // null = not assessed (noon scenario missing/errored)
  worst_case_scenario: string;
}

interface ShadowResult {
  address: string;
  lat: number;
  lng: number;
  run_date: string;
  outputs: ShadowOutputs;
  confidence: string;
  data_sources: string[];
  zone: string | null;
  warnings?: string[];
  report_token?: string;
  report_id?: string;
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const NON_RESIDENTIAL_ZONE_PREFIXES = ['B', 'E', 'IN', 'SP', 'W'];

const SCENARIO_LABELS: Record<string, string> = {
  jun21_9am: '21 Jun — 9:00 am',
  jun21_12pm: '21 Jun — 12:00 pm',
  jun21_3pm: '21 Jun — 3:00 pm',
  sep21_12pm: '21 Sep — 12:00 pm',
  dec21_12pm: '21 Dec — 12:00 pm',
};

function formatAustralianDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' });
}

function bearingToCompass(deg: number): string {
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return dirs[Math.round(deg / 45) % 8];
}

export function ShadowTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<ShadowResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const [paidReportId, setPaidReportId] = useState<string | null>(null);

  const runCheck = useCallback(async (addr: string) => {
    if (!addr.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');

    posthog?.capture('shadow_tool_run', {
      address: addr,
      lga_slug: lgaSlug,
      source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
      embed_ref: embedRef ?? null,
    });

    try {
      const res = await fetch('/api/satellite/shadow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Shadow analysis failed');
      setResult(json);
      setState('complete');
      posthog?.capture('shadow_tool_complete', {
        address: addr,
        lga_slug: lgaSlug,
        adg_compliant: json.outputs?.adg_compliant,
        confidence: json.confidence,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(msg);
      setState('error');
      posthog?.capture('shadow_tool_error', { address: addr, lga_slug: lgaSlug, error: msg });
    }
  }, [embedRef, lgaSlug]);

  useEffect(() => {
    const handler = (e: Event) => {
      const addr = (e as CustomEvent).detail?.address;
      if (addr) {
        setAddress(addr);
        runCheck(addr);
      }
    };
    window.addEventListener('landing-search', handler);
    return () => window.removeEventListener('landing-search', handler);
  }, [runCheck]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const addrParam = params.get('address')?.trim();
    if (addrParam && !params.get('payment')) {
      setAddress(addrParam);
      runCheck(addrParam);
      window.history.replaceState({}, '', window.location.pathname);
    }

    if (params.get('payment') === 'success') {
      const rid = params.get('report_id')?.trim();
      if (rid) setPaidReportId(rid);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [runCheck]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runCheck(address);
  };

  const handleReset = () => {
    setAddress('');
    setState('idle');
    setResult(null);
    setErrorMsg('');
    window.dispatchEvent(new CustomEvent('landing-reset'));
  };

  return (
    <div>
      {state === 'idle' || state === 'error' ? (
        <form id="tool-input" onSubmit={handleSubmit} className="flex gap-3 mb-8">
          <AddressAutocomplete
            value={address}
            onChange={setAddress}
            onSelect={(addr) => setAddress(addr)}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!address.trim()}
            className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Analyse
          </button>
        </form>
      ) : (
        <div className="mb-6">
          <p className="text-sm text-gray-500">{address}</p>
          <button
            type="button"
            onClick={handleReset}
            className="text-sm text-teal-600 hover:text-teal-700 font-medium mt-1"
          >
            Search new address
          </button>
        </div>
      )}

      <OperationalTransparency
        steps={SHADOW_STEPS}
        active={state === 'running'}
        address={address}
        note="This takes 15–30 seconds."
      />

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {paidReportId && state !== 'complete' && (
        <ShadowPaidDownloadCTA reportId={paidReportId} />
      )}

      {state === 'complete' && result && (
        <>
          <ShadowCard result={result} />
          <FreePaidComparison
            free={[
              'ADG solar access compliance check',
              'Shadow overlap across 5 scenarios',
              'Worst-case shadow length + direction',
              'Construction activity detection',
              'Shadow map with lot boundary',
            ]}
            paid={[
              'All 5 scenario shadow diagrams',
              'Shadow overlap percentages per scenario',
              'Objection-ready paragraph for council',
              'Construction change detection detail',
              'Full PDF report for DA submission',
            ]}
          />
          {result.report_id ? (
            paidReportId ? (
              <ShadowPaidDownloadCTA reportId={paidReportId} />
            ) : (
              <ShadowLockedPreviewCard result={result} />
            )
          ) : null}
          <ToolCrossSell currentTool="shadow-detector" address={result.address} />
        </>
      )}
    </div>
  );
}

function FreePaidComparison({ free, paid }: { free: string[]; paid: string[] }) {
  return (
    <div className="mt-4 bg-white rounded-xl border border-gray-200 p-5">
      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Included free</p>
          <ul className="space-y-2">
            {free.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-gray-700">
                <span className="shrink-0 mt-0.5 w-4 h-4 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-[10px] font-bold">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">In paid report</p>
          <ul className="space-y-2">
            {paid.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-gray-500">
                <span className="shrink-0 mt-0.5 w-4 h-4 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center text-[10px]">🔒</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ShadowLockedPreviewCard — gate documentation value, not the verdict
// Free: ADG verdict + map. Paid: scenario data, construction detection, objection para.
// ---------------------------------------------------------------------------

const SCENARIO_ORDER = ['jun21_9am', 'jun21_12pm', 'jun21_3pm', 'sep21_12pm', 'dec21_12pm'];

function ShadowLockedPreviewCard({
  result,
}: {
  result: ShadowResult;
}) {
  const o = result.outputs;
  const overlapCount = o.scenarios.filter(s => s.overlaps_subject_lot).length;
  // Unavailable scenarios must not be silently absorbed into an all-clear
  // aggregate (Sol pre-push round); absence of status = legacy computed row.
  const lockedUnavailable = o.scenarios.filter(s => s.status === 'unavailable').length;
  const lockedComputed = o.scenarios.length - lockedUnavailable;
  const lockedDenominator = lockedUnavailable > 0 ? `${lockedComputed} computed` : '5';

  // Find worst-case overlap fraction for blurred preview
  const worstScenario = o.scenarios.find(s => s.scenario === o.worst_case_scenario);
  const worstOverlapPct = worstScenario?.shadow_overlap_fraction != null
    ? `${Math.round(worstScenario.shadow_overlap_fraction * 100)}% of lot`
    : `${overlapCount} of ${lockedDenominator} scenarios`;

  // Sort scenarios in standard order for consistent display
  const sortedScenarios = [...o.scenarios].sort(
    (a, b) => SCENARIO_ORDER.indexOf(a.scenario) - SCENARIO_ORDER.indexOf(b.scenario)
  );
  const teaserScenarios = sortedScenarios.slice(0, 2);
  // Three-state (output-grounding fix 1): null = not assessed. The old
  // `!o.adg_compliant` rendered an "ADG concern" verdict from a failed run.
  const alarmHeadline = o.adg_compliant == null
    ? 'Shadow analysis incomplete — the ADG solar access test could not be run for this lot'
    : o.adg_compliant === false
    ? `ADG concern — shadow impact on ${overlapCount} of ${lockedDenominator} test scenarios`
    : overlapCount > 0
    ? `Shadow impact on ${overlapCount} of ${lockedDenominator} scenarios — get the diagrams for your records`
    : lockedUnavailable > 0
    ? `No shadow concern in the ${lockedComputed} computed scenarios — ${lockedUnavailable} of 5 could not be assessed`
    : 'No shadow concern detected — save the full analysis for your records';

  const alarmDetail = o.adg_compliant == null
    ? 'The shadow model could not compute the 21 June noon scenario, so no shadow verdict is made. Re-run the analysis, or treat shadow as unassessed for this property.'
    : o.adg_compliant === false
    ? 'This property may not meet the ADG 2-hour solar access requirement on 21 June. The full report has the scenario diagrams and objection paragraph you need.'
    : overlapCount > 0
    ? 'The full report includes hourly shadow diagrams and a ready-to-paste objection paragraph for your council submission.'
    : 'The full report documents that no shadow impact was found — useful evidence if a future DA is lodged nearby.';

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-amber-50 border-b border-amber-100 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900 leading-snug">{alarmHeadline}</p>
        <p className="text-xs text-amber-700 mt-1 leading-relaxed">{alarmDetail}</p>
      </div>

      <div className="bg-white px-5 pt-4 pb-3 space-y-4">
        {/* Worst-case overlap — blurred */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Shadow overlap — worst case
          </p>
          <span className="blur-sm select-none pointer-events-none text-sm font-medium text-gray-900">
            {worstOverlapPct}
          </span>
        </div>

        {/* Scenario table — 2 teasers + blurred rows */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Scenario breakdown
          </p>
          <div className="space-y-1.5">
            {teaserScenarios.map((s) => (
              isScenarioUnavailable(s) ? (
                // "not computed" is operator shorthand, and sitting in the
                // value column it reads as a value. A scenario with no result
                // gets its own amber block that says why and says it is
                // neither a pass nor a fail.
                <div key={s.scenario} className="text-sm py-1.5 px-2 border-b border-gray-50 bg-amber-50 rounded">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">{SCENARIO_LABELS[s.scenario] ?? s.scenario}</span>
                    <span className="font-medium text-amber-900">{SCENARIO_NOT_ASSESSED_LABEL}</span>
                  </div>
                  <p className="text-xs text-amber-800 leading-snug mt-0.5">
                    {scenarioUnavailableMessage(s.error_note)}
                  </p>
                </div>
              ) : (
                <div key={s.scenario} className="flex items-center justify-between gap-4 text-sm py-1 border-b border-gray-50">
                  <span className="text-gray-600">{SCENARIO_LABELS[s.scenario] ?? s.scenario}</span>
                  <span className="font-medium text-gray-900 tabular-nums">
                    {s.shadow_length_m != null
                      ? `${s.shadow_length_m.toFixed(0)}m shadow${s.overlaps_subject_lot ? ' · overlaps lot' : ''}`
                      : '—'}
                  </span>
                </div>
              )
            ))}
            {/* Blurred remaining rows — use real scenario labels, blur real values */}
            {sortedScenarios.slice(2).map((s) => (
              <div key={s.scenario} className="flex items-center justify-between gap-4 text-sm py-1 border-b border-gray-50">
                <span className="blur-sm select-none pointer-events-none text-gray-600">
                  {SCENARIO_LABELS[s.scenario] ?? s.scenario}
                </span>
                <span className="blur-sm select-none pointer-events-none font-medium text-gray-900 tabular-nums">
                  {s.shadow_length_m != null
                    ? `${s.shadow_length_m.toFixed(0)}m shadow${s.overlaps_subject_lot ? ' · overlaps lot' : ''}`
                    : 'not computed'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Objection paragraph — blurred, only shown when there's actual shadow impact */}
        {overlapCount > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Objection-ready paragraph
            </p>
            <p className="blur-sm select-none pointer-events-none text-sm text-gray-700 leading-relaxed">
              Shadow modelling conducted in accordance with NSW Apartment Design Guide Part 3F
              indicates that a maximum-height building on the northern boundary would cast a shadow
              over {Math.round((worstScenario?.shadow_overlap_fraction ?? 0) * 100)}% of the subject
              lot at 21 June 12pm, which {o.adg_compliant ? 'is within' : 'does not comply with'} the 2-hour solar access requirement.
            </p>
          </div>
        )}
      </div>

      <div className="bg-white px-5 pb-5 pt-2">
        <WaitlistButton interestType="shadow" address={result.address} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ShadowPaidDownloadCTA — shown after Stripe payment=success redirect
// ---------------------------------------------------------------------------

function ShadowPaidDownloadCTA({ reportId }: { reportId: string }) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/shadow/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `shadow-report-${reportId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setDlError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mt-4 rounded-xl border border-teal-200 bg-teal-50 p-5">
      <p className="text-sm font-semibold text-teal-900 mb-1">Payment confirmed — your report is ready.</p>
      <p className="text-xs text-teal-700 mb-3">A copy is also on its way to your email.</p>
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="w-full py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {downloading ? 'Preparing download...' : 'Download PDF report →'}
      </button>
      {dlError && <p className="text-xs text-red-600 mt-2">{dlError}</p>}
    </div>
  );
}

function ShadowCard({ result }: { result: ShadowResult }) {
  const o = result.outputs;
  const scenarios = o.scenarios ?? [];

  const [activeScenario] = useState<string>(
    o.worst_case_scenario ?? 'jun21_12pm'
  );

  const activeShadowOnLot = useMemo(() => {
    const match = scenarios.find(s => s.scenario === activeScenario);
    return match?.shadow_on_lot ?? null;
  }, [activeScenario, scenarios]);

  const overlapCount = scenarios.filter(s => s.overlaps_subject_lot).length;
  // Same rule as the PDF findings: a scenario the model could not compute is
  // excluded from every aggregate claim, and its exclusion is stated.
  const unavailableCount = scenarios.filter(s => s.status === 'unavailable').length;
  const computedCount = scenarios.length - unavailableCount;
  const worstScenario = scenarios.find(s => s.scenario === o.worst_case_scenario);

  const isNonResidential =
    result.zone != null &&
    NON_RESIDENTIAL_ZONE_PREFIXES.some(p => result.zone!.toUpperCase().startsWith(p));

  const badgeColor = isNonResidential
    ? 'bg-gray-100 text-gray-600'
    : o.adg_compliant
    ? 'bg-green-100 text-green-800'
    : 'bg-red-100 text-red-800';

  const badgeLabel = isNonResidential
    ? 'Indicative only'
    : o.adg_compliant
    ? 'Meets ADG solar access test'
    : 'ADG solar access concern';

  const summaryText = isNonResidential
    ? 'ADG solar access requirements apply to residential apartment buildings only. This result is indicative for non-residential zones.'
    : o.adg_compliant
    ? 'Based on the modelled worst-case scenario, this property appears to meet the ADG 2-hour solar access test on 21 June (winter solstice). This is an indicative analysis, not a formal compliance assessment.'
    : 'Based on the modelled scenario, this property may not meet the ADG 2-hour solar access test on 21 June. If a neighbour lodges a DA for a tall building, this analysis may support an objection submission.';

  // Build findings
  const findings: { label: string; value: string; detail: string; severity: 'green' | 'amber' | 'red' }[] = [];

  // ADG compliance
  if (isNonResidential) {
    findings.push({
      label: 'NSW Apartment Design Guide — Part 3F',
      value: 'Non-residential zone — ADG not applicable',
      detail: 'The ADG solar access test applies to residential apartment development. This zone is non-residential, so this result is informational only.',
      severity: 'green',
    });
  } else if (o.adg_compliant) {
    findings.push({
      label: 'NSW Apartment Design Guide — Part 3F',
      value: 'Meets 2-hour solar access requirement',
      detail: 'Even if your neighbour builds to the maximum permitted height, the model indicates your property would receive at least 2 hours of direct sunlight between 9 am and 3 pm on 21 June (the worst day of the year for shadows).',
      severity: 'green',
    });
  } else {
    findings.push({
      label: 'NSW Apartment Design Guide — Part 3F',
      value: 'May not meet 2-hour solar access requirement',
      detail: 'If a neighbour builds to maximum permitted height, your property could lose the 2 hours of winter sunlight required under the ADG. This is grounds for objection if a DA is lodged.',
      severity: 'red',
    });
  }

  // Shadow overlap count
  if (overlapCount === 0) {
    findings.push({
      label: 'Shadow overlap analysis (5 ADG scenarios)',
      value: unavailableCount > 0
        ? `No shadow reaches your lot in the ${computedCount} computed scenarios`
        : 'No shadow reaches your lot',
      detail: unavailableCount > 0
        ? `Across the ${computedCount} test scenarios that could be computed, a maximum-height building to the north would not cast shadow onto your property. ${unavailableCount} of the 5 scenarios could not be assessed, so this is not a result across all 5.`
        : 'Across all 5 test scenarios (winter solstice morning, midday, afternoon + equinox + summer), a maximum-height building to the north would not cast shadow onto your property.',
      severity: unavailableCount > 0 ? 'amber' : 'green',
    });
  } else {
    findings.push({
      label: 'Shadow overlap analysis (5 ADG scenarios)',
      value: `Shadow overlaps your lot in ${overlapCount} of ${unavailableCount > 0 ? `${computedCount} computed` : '5'} scenarios`,
      detail: overlapCount >= 3
        ? 'Shadow reaches your property in the majority of test scenarios. This would affect winter sunlight, garden usability, and potentially solar panel output.'
        : 'Shadow reaches your property in some test scenarios. The map below shows the worst case.',
      severity: overlapCount >= 3 ? 'red' : 'amber',
    });
  }

  // Worst-case shadow length
  if (worstScenario) {
    // null when the worst-case scenario itself errored (typed absence, fix 1).
    // Never coalesce to 0 — a zero-metre "measurement" from a failed
    // computation is the exact collapse this fix removes (Sol round 1).
    if (worstScenario.shadow_length_m == null) {
      findings.push({
        label: `Worst case — ${SCENARIO_LABELS[worstScenario.scenario] ?? worstScenario.scenario}`,
        value: 'Not computed — this scenario could not be modelled',
        detail: 'The shadow computation for this scenario did not complete, so no length or coverage figure is reported for it.',
        severity: 'amber',
      });
    } else {
    const len = worstScenario.shadow_length_m;
    // Guarded: shadow_direction_deg is nullable now. Math.round(null/45) is 0,
    // so an unguarded call would silently render "N" — a fabricated direction —
    // and Math.round(undefined/45) indexes the array with NaN and renders
    // "undefined". Absent direction must read as absent.
    const dir = worstScenario.shadow_direction_deg != null
      ? bearingToCompass(worstScenario.shadow_direction_deg)
      : null;
    const overlapPct = worstScenario.shadow_overlap_fraction != null
      ? Math.round(worstScenario.shadow_overlap_fraction * 100)
      : null;

    findings.push({
      label: `Worst case — ${SCENARIO_LABELS[worstScenario.scenario] ?? worstScenario.scenario}`,
      value: `${len.toFixed(0)}m shadow${dir ? ` cast ${dir}` : ''}${overlapPct != null ? ` — ${overlapPct}% of lot covered` : ''}`,
      detail: len > 20
        ? 'At this length, the shadow would extend well beyond your immediate boundary. This is the scenario to reference if objecting to a neighbour\'s DA.'
        : 'A relatively short shadow. The impact on your property would be limited to the area nearest the boundary.',
      severity: len > 20 ? 'red' : len > 10 ? 'amber' : 'green',
    });
    }
  }

  // Building height used
  findings.push({
    label: o.height_source === 'planning_portal' ? 'NSW Planning Portal — LEP height of building map'
      : o.height_source === 'spatial_overlays' ? 'Spatial overlays — height of building'
      : o.height_source === 'regulatory_provisions' ? 'DCP regulatory provisions'
      : 'Default assumption',
    value: `${o.height_m}m maximum building height modelled`,
    detail: o.height_source === 'default'
      ? 'No specific height control found for this site — the model used a default assumption. The actual permitted height may differ; check your local LEP.'
      : 'This is the maximum building height permitted under the planning controls. The shadow model assumes a building at this full height on the neighbouring lot.',
    severity: o.height_source === 'default' ? 'amber' : 'green',
  });

  const sevColor = { green: 'bg-green-500', amber: 'bg-amber-400', red: 'bg-red-500' };

  return (
    <div className="bg-white rounded-xl border border-gray-200">

      {/* Header */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <h2 className="font-semibold text-gray-900 text-base">{result.address}</h2>
          <span className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${badgeColor}`}>
            {badgeLabel}
          </span>
        </div>
        <p className="text-sm text-gray-600">{summaryText}</p>
        <p className="text-xs text-gray-400 mt-2">
          The Apartment Design Guide (ADG) Part 3F requires residential apartments to receive at least 2 hours of direct sunlight between 9 am and 3 pm on 21 June — the worst day of the year for overshadowing.
        </p>
      </div>

      {/* Findings */}
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

      {/* Map */}
      <div className="relative border-t border-gray-100" style={{ height: 280 }}>
        <ShadowMap
          center={[result.lng, result.lat]}
          lotPolygon={o.lot_polygon ?? null}
          shadowOnLot={activeShadowOnLot}
        />
        <div className="absolute bottom-3 left-3 bg-black/60 text-white rounded-full w-8 h-8 flex flex-col items-center justify-center gap-0 select-none">
          <svg width="10" height="12" viewBox="0 0 10 12" fill="none">
            <path d="M5 1 L5 11" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M5 1 L2 5 M5 1 L8 5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <span className="text-[9px] font-bold leading-none">N</span>
        </div>
        <div className="absolute bottom-3 left-12 bg-black/60 text-white text-xs px-2.5 py-1 rounded-full">
          {SCENARIO_LABELS[activeScenario] ?? activeScenario}
        </div>
        <div className="absolute top-3 right-3 bg-white/90 text-xs rounded-lg px-3 py-2 space-y-1.5 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm bg-teal-500 opacity-70 shrink-0" />
            <span className="text-gray-700">Your lot</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm bg-orange-400 opacity-80 shrink-0" />
            <span className="text-gray-700">Shadow on your lot</span>
          </div>
        </div>
      </div>
      <p className="px-5 py-2 text-xs text-gray-400 border-t border-gray-100">
        Worst-case shadow from a maximum-height building on the northern boundary. Geometric model — not satellite imagery.
      </p>


      {/* ADG zone note */}
      {isNonResidential && (
        <div className="px-5 py-3 bg-blue-50 border-t border-blue-100">
          <p className="text-xs text-blue-700">
            ADG solar access requirements apply to residential apartment buildings only. This property is zoned {result.zone} — the ADG result is indicative only.
          </p>
        </div>
      )}

      {/* Warnings */}
      {result.warnings && result.warnings.length > 0 && (
        <div className="px-5 py-3 bg-amber-50 border-t border-amber-100">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-700">{w}</p>
          ))}
        </div>
      )}

      {/* How this works — transparency */}
      <details className="border-t border-gray-100 group">
        <summary className="px-5 py-3 text-xs text-gray-400 cursor-pointer hover:text-gray-600 select-none">
          How this model works
        </summary>
        <div className="px-5 pb-4 text-xs text-gray-400 space-y-1.5">
          <p>1. We find your lot boundary from the NSW Planning Portal cadastre.</p>
          <p>2. A hypothetical building is modelled immediately north of your lot, at the maximum height mapped at your location ({o.height_m}m). Its outline is a rectangle offset north of your own boundary — we do not fetch the neighbouring parcel, so its real shape, position and height control are not known to this model.</p>
          <p>3. Shadow is computed geometrically from the sun&apos;s position at each of the 5 ADG test scenarios (winter solstice 9am/12pm/3pm, equinox noon, summer noon). Times are NSW local wall-clock, with daylight saving applied where it applies — 21 December is AEDT.</p>
          <p>4. We check whether the shadow polygon overlaps your lot boundary.</p>
          <p className="pt-1 text-gray-500 font-medium">This model considers a hypothetical new building only — it does not account for shadow from existing structures, trees, or infrastructure (e.g. overpasses, bridges).</p>
        </div>
      </details>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Screening tool — not a formal shadow impact assessment. A qualified town planner or architect must prepare shadow diagrams for DA submission.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          {DATA_PROVENANCE.shadow}
        </p>
      </div>
    </div>
  );
}
