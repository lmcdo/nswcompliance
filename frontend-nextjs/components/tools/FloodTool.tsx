'use client';

import { useState, useEffect, useCallback } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { WaitlistButton } from '@/components/reports/WaitlistButton';
import { DATA_PROVENANCE } from '@/lib/disclaimers';
import { posthog } from '@/components/providers/PostHogProvider';
import { OperationalTransparency, type TransparencyStep } from '@/components/tools/OperationalTransparency';
import { readFloodZoneVerdict, floodZoneUnavailableMessage } from '@/lib/not-assessed';

const FLOOD_STEPS: TransparencyStep[] = [
  { label: 'Checking EPI flood overlays…',              ms: 0 },
  { label: 'Querying council flood studies…',            ms: 2000 },
  { label: 'Scanning Copernicus EMS satellite history…', ms: 5000 },
  { label: 'Checking JRC 40-year surface water record…', ms: 9000 },
  { label: 'Reading BOM gauge data…',                   ms: 14000 },
  { label: 'Assembling flood screening…',                ms: 20000 },
];

interface EmsActivation {
  activation_id: string;
  event_name: string;
  event_date: string;
  flood_type: string;
}

interface FloodOutputs {
  epi_flood_class: string | null;
  epi_flood_label: string | null;
  sar_flood_detected: boolean | null;
  sar_confidence: string | null;
  sar_analysis_date: string | null;
  ems_flood_detected: boolean | null;
  ems_activations: EmsActivation[] | null;
  jrc_water_occurrence_pct: number | null;
  jrc_data_year: number | null;
  dea_wofs_frequency_pct: number | null;
  ses_in_flood_planning_area: boolean | null;
  ses_flood_class: string | null;
  ses_aep_tiers: string[] | null;
  ses_study_name: string | null;
  ses_study_lga: string | null;
  bom_gauge_name: string | null;
  bom_gauge_distance_km: number | null;
  bom_last_major_flood_date: string | null;
  bom_last_major_flood_peak_m: number | null;
  s1_gap_warning: string | null;
  data_currency: string;
  flood_signal: 'none' | 'low' | 'moderate' | 'elevated' | 'unavailable' | null;
  hawkesbury_flood_level_2aep: number | null;
  hawkesbury_flood_level_5aep: number | null;
  hawkesbury_flood_level_10aep: number | null;
  hawkesbury_flood_level_20aep: number | null;
  hawkesbury_flood_level_50aep: number | null;
  hawkesbury_flood_level_100aep: number | null;
  hawkesbury_flood_level_200aep: number | null;
  hawkesbury_flood_level_500aep: number | null;
  hawkesbury_flood_level_pmf: number | null;
  hawkesbury_flood_study: string | null;
  // Canonical shape for ALL named local flood studies (Hawkesbury, Redbank,
  // Tweed, Wollongong), superseding the flat hawkesbury_flood_level_* fields
  // above for anything generated after those studies were unified onto one
  // schema. Untyped at the element level (unknown, not FloodStudyEntry)
  // because this is a live JSON API response only asserted to be
  // FloodResult by a type cast, never runtime-validated — every read below
  // guards its own shape rather than trusting this declaration.
  flood_studies?: unknown[] | null;
  // Three-state (2026-08-08): true/false are real verdicts, null means the
  // question could not be answered — see lib/not-assessed.ts. Optional here
  // because this interface predates the multi-study contract; older cached
  // rows and the "unavailable" flood_signal path may not carry it.
  in_100yr_flood_zone?: boolean | null;
  // Named studies (e.g. "Redbank Creek flood study") that cover this address's
  // council but could not be consulted for this report — files not on this
  // host, most commonly. Only present when in_100yr_flood_zone is null.
  in_100yr_flood_zone_unconsulted?: string[] | null;
}

interface FloodResult {
  address: string;
  lat: number;
  lng: number;
  run_date: string;
  outputs: FloodOutputs;
  confidence: string;
  data_sources: string[];
  warnings?: string[];
  report_token?: string;
  report_id?: string;
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const FLOOD_SIGNAL_META: Record<string, { label: string; sublabel: string; badge: string; bar: string }> = {
  none:     {
    label:    'No flood indicators detected',
    sublabel: 'No signals across statutory overlay, council flood study, or observed satellite and gauge records',
    badge:    'bg-green-100 text-green-800',
    bar:      'bg-green-500',
  },
  low:      {
    label:    'Low flood signal',
    sublabel: 'Property is within a statutory flood zone — no observed inundation events on record',
    badge:    'bg-yellow-100 text-yellow-800',
    bar:      'bg-yellow-400',
  },
  moderate: {
    label:    'Moderate flood signal',
    sublabel: 'One or more sources indicate flood exposure — review the full data before purchasing or developing',
    badge:    'bg-orange-100 text-orange-800',
    bar:      'bg-orange-500',
  },
  elevated: {
    label:    'Elevated flood signal',
    sublabel: 'Multiple independent sources confirm flood exposure — professional flood study recommended',
    badge:    'bg-red-100 text-red-800',
    bar:      'bg-red-500',
  },
  unavailable: {
    label:    'Flood study coverage not available for this address',
    sublabel: 'Absence of data is not clearance — contact the local council directly to confirm flood status',
    badge:    'bg-gray-100 text-gray-600',
    bar:      'bg-gray-400',
  },
};

const EPI_CLASS_META: Record<string, { label: string; color: string }> = {
  high_flood_risk:     { label: 'High flood risk zone',   color: 'bg-red-50 text-red-700' },
  medium_flood_risk:   { label: 'Medium flood risk zone', color: 'bg-orange-50 text-orange-700' },
  low_flood_risk:      { label: 'Low flood risk zone',    color: 'bg-yellow-50 text-yellow-700' },
  flood_planning_area: { label: 'Flood planning area',    color: 'bg-blue-50 text-blue-700' },
  none:                { label: 'Not in statutory flood overlay', color: 'bg-green-50 text-green-700' },
};

export function FloodTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<FloodResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const [paidReportId, setPaidReportId] = useState<string | null>(null);

  // Listen for hero address input — run the check directly with the address
  // from the event (don't rely on React state flushing before submit)
  const runCheck = useCallback(async (addr: string) => {
    if (!addr.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');
    try {
      const res = await fetch('/api/satellite/flood', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Flood analysis failed');
      setResult(json);
      setState('complete');
      posthog.capture('tool_run', {
        tool: 'flood-truth',
        source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
        embed_ref: embedRef ?? null,
        lga_slug: lgaSlug ?? null,
        result: json.outputs?.flood_signal ?? null,
      });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
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

  // Read URL params on mount: ?address= (auto-run) and ?payment=success (download CTA)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    // Auto-run if address provided via URL (e.g. from property profile page)
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
    setPaidReportId(null);
    window.dispatchEvent(new CustomEvent('landing-reset'));
  };

  return (
    <div className="mb-8">
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
            Run Flood Check
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
        steps={FLOOD_STEPS}
        active={state === 'running'}
        address={address}
        note="Allow 15–30 seconds."
      />

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {/* Payment return — show download CTA even without result in state */}
      {paidReportId && state !== 'complete' && (
        <FloodPaidDownloadCTA reportId={paidReportId} />
      )}

      {state === 'complete' && result && (
        <>
          <FloodCard result={result} />
          <FreePaidComparison
            free={[
              'Government flood overlay (EPI)',
              'Council flood study extent',
              'Satellite water history (DEA WOfS)',
            ]}
            paid={[
              '1-in-100 year flood depth (AHD)',
              'BOM river gauge — last major flood',
              'Copernicus EMS historical events',
              'SAR radar flood detection',
              '40-year water occurrence (JRC)',
              'Full PDF report with source citations',
            ]}
          />
          {result.report_id ? (
            paidReportId ? (
              <FloodPaidDownloadCTA reportId={paidReportId} />
            ) : (
              <FloodLockedPreviewCard result={result} />
            )
          ) : null}
          <ToolCrossSell currentTool="flood-truth" address={result.address} />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FloodLockedPreviewCard — blur-to-reveal with real data from API response
// ---------------------------------------------------------------------------

function formatFloodDate(iso?: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-AU', { month: 'short', year: 'numeric' });
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

function FloodLockedPreviewCard({
  result,
}: {
  result: FloodResult;
}) {
  const o = result.outputs;
  const signal = o.flood_signal ?? 'none';

  const alarmHeadline = signal === 'unavailable'
    ? 'No automated flood data for this address — this is the riskiest result'
    : signal === 'elevated'
    ? 'This property flagged on multiple independent flood sources — your lender has already seen this'
    : signal === 'moderate'
    ? 'Flood exposure detected — your conveyancer will ask for the depths below before settlement'
    : signal === 'low'
    ? 'In a statutory flood zone — insurers price premiums against the depth numbers below'
    : o.epi_flood_class && o.epi_flood_class !== 'none'
    ? 'In a flood planning area — get the depths in writing before exchange'
    : 'No flood indicators detected across checked sources — see limitations below';

  const alarmDetail = signal === 'unavailable'
    ? 'Absence of data is not clearance. If no flood study covers this area, flood status has not been formally assessed. The full report documents exactly what was checked and what was not — giving your solicitor a paper trail.'
    : signal === 'elevated'
    ? 'Banks, mortgage insurers, and conveyancers run the same government flood datasets before settlement. If they find flood risk you haven\'t disclosed, contracts fall over. The 1-in-100 year depth — the number they ask for — is in your report below.'
    : signal === 'moderate'
    ? 'One or more sources show flood exposure. Your lender\'s valuer and your insurer\'s underwriter will both want ARI depths before they commit. Those numbers are below — blurred.'
    : signal === 'low'
    ? 'Being in a flood zone doesn\'t kill a deal, but not knowing your depths does. Insurance underwriters price flood loading directly against the 1-in-100 year level. Your number is below.'
    : 'The full report gives your conveyancer source citations across 6 independent datasets. For properties that come back clean, this replaces a $300+ council certificate.';

  const emsCount = o.ems_activations?.length ?? 0;

  const rows = [
    {
      label: 'BOM last major flood',
      preview: o.bom_last_major_flood_date ? formatFloodDate(o.bom_last_major_flood_date) : '—',
    },
    {
      label: 'Peak river height',
      preview: o.bom_last_major_flood_peak_m != null ? `${o.bom_last_major_flood_peak_m}m above minor flood` : '—',
    },
    {
      label: 'Historical inundation events',
      preview: `${emsCount} event${emsCount !== 1 ? 's' : ''} since 2000`,
    },
    {
      label: '40-year water occurrence',
      preview: o.jrc_water_occurrence_pct != null ? `${o.jrc_water_occurrence_pct}% of satellite observations` : '—',
    },
    {
      label: 'Nearest BOM gauge',
      preview: o.bom_gauge_name && o.bom_gauge_distance_km != null
        ? `${o.bom_gauge_name} · ${o.bom_gauge_distance_km}km`
        : '—',
    },
    {
      label: 'Copernicus EMS — historical flood activations',
      preview: `${emsCount} recorded event${emsCount !== 1 ? 's' : ''} at this location`,
    },
  ];

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-amber-50 border-b border-amber-100 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900 leading-snug">{alarmHeadline}</p>
        <p className="text-xs text-amber-700 mt-1 leading-relaxed">{alarmDetail}</p>
      </div>

      <div className="bg-white px-5 pt-4 pb-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
          Your flood data
        </p>
        <div className="space-y-2">
          {rows.map(({ label, preview }) => (
            <div key={label} className="flex items-center justify-between gap-4 text-sm">
              <span className="text-gray-700">{label}</span>
              <span className="blur-sm select-none pointer-events-none font-medium text-gray-900 tabular-nums text-right">
                {preview}
              </span>
            </div>
          ))}
        </div>
      </div>

      {signal === 'unavailable' && (
        <div className="bg-gray-50 border-t border-gray-100 px-5 py-4">
          <p className="text-xs font-semibold text-gray-700 mb-2">How to get the flood classification for this address</p>
          <ol className="space-y-1.5 text-xs text-gray-600 list-decimal list-inside">
            <li>
              <span className="font-medium">Section 10.7 planning certificate</span> — request from your council (~$53). Includes the statutory flood overlay. Your conveyancer can request it on your behalf.
            </li>
            <li>
              <span className="font-medium">Flood enquiry letter</span> — some councils issue a separate flood certificate. Ask the council&apos;s flood team directly.
            </li>
            <li>
              <span className="font-medium">NSW SES flood portal</span> — flooddata.ses.nsw.gov.au lists available council flood studies. Some are public; others require a data request.
            </li>
          </ol>
          <p className="text-xs text-gray-400 mt-2">We&apos;re expanding coverage to more councils. If this address is in a known flood area, contact us and we&apos;ll prioritise that council.</p>
        </div>
      )}

      <div className="bg-white px-5 pb-5 pt-2">
        <WaitlistButton interestType="flood-truth" address={result.address} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FloodPaidDownloadCTA — shown after Stripe payment=success redirect
// ---------------------------------------------------------------------------

function FloodPaidDownloadCTA({ reportId }: { reportId: string }) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/flood/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `flood-truth-report-${reportId.slice(0, 8)}.pdf`;
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

function FloodCard({ result }: { result: FloodResult }) {
  const o = result.outputs;
  const signal     = o.flood_signal ?? 'none';
  const signalMeta = FLOOD_SIGNAL_META[signal] ?? FLOOD_SIGNAL_META.none;
  const epiClass   = o.epi_flood_class ?? 'none';
  const epiMeta    = EPI_CLASS_META[epiClass] ?? { label: epiClass, color: 'bg-gray-50 text-gray-700' };

  // Build findings with explanations
  const findings: { label: string; value: string; detail: string; severity: 'green' | 'amber' | 'red' }[] = [];

  // 1% AEP (1-in-100-year) verdict — three-state. A named council flood study
  // can exist for this address's area (Hawkesbury, Redbank, Tweed, Wollongong)
  // and still be unreachable on this run; when that happens the verdict is
  // null and unconsulted names the study, so the reader knows a more precise
  // answer exists rather than reading silence as "not in a flood zone".
  const aepVerdict = readFloodZoneVerdict(o.in_100yr_flood_zone);
  // Array.isArray + every-string, not a bare truthy/.length check: `outputs`
  // is a JSON API response only asserted to be FloodResult by a type cast,
  // not runtime-validated, so a contract regression returning a bare string
  // or a malformed element would otherwise pass a `.length > 0` check (a
  // string has .length too) and either throw inside
  // floodZoneUnavailableMessage's array methods or render a bogus name.
  // Mirrors the same guard on the Brief (page.tsx).
  const rawUnconsulted = o.in_100yr_flood_zone_unconsulted;
  const aepUnconsulted =
    Array.isArray(rawUnconsulted) &&
    rawUnconsulted.length > 0 &&
    rawUnconsulted.every((name): name is string => typeof name === 'string')
      ? rawUnconsulted
      : null;
  if (aepVerdict === true) {
    // A positive finding stands on its own regardless of what else was
    // unreachable — matches the backend's own three-state rule (only a
    // NEGATIVE needs every source to have been asked).
    findings.push({
      label: '1% AEP (1-in-100-year) flood extent',
      value: 'At least one source we checked places this location inside the flood extent',
      // Source-neutral on purpose: the backend flags this from the EPI
      // government overlay alone, a council/SES study, or a named flood-study
      // raster (see flood_truth.py's in_100yr check) — naming "a council or
      // statutory flood study" specifically would misattribute an EPI-only
      // positive to evidence that wasn't actually consulted for this address.
      detail: 'At least one of the sources we checked places this location within the 1-in-100-year flood extent.',
      severity: 'red',
    });
  } else if (aepVerdict === false && !aepUnconsulted) {
    // A real negative: every source that could answer was consulted.
    findings.push({
      label: '1% AEP (1-in-100-year) flood extent',
      value: 'None of the sources we checked place this location inside the flood extent',
      // Scoped to "sources we checked" and "this location", not a bare
      // "outside the flood extent" — that would overclaim a guarantee the
      // underlying sources don't give for the whole parcel.
      detail: 'We checked every source that could answer this question, and none of them place this location within the 1-in-100-year flood extent.',
      severity: 'green',
    });
  } else if (aepUnconsulted) {
    // Either the verdict was never established (null), or the backend sent
    // an internally contradictory payload — a False verdict alongside a
    // named unconsulted study, which should never happen given the
    // backend's own rule (in_100yr_flood_zone is only False when unconsulted
    // is empty) but is treated as "not assessed" here rather than trusted,
    // so a future backend regression degrades safely instead of rendering a
    // false-confidence clearance.
    findings.push({
      label: '1% AEP (1-in-100-year) flood extent',
      value: 'Not assessed',
      detail: floodZoneUnavailableMessage(aepUnconsulted),
      severity: 'amber',
    });
  }

  // Government flood overlay
  if (epiClass === 'none' && (signal === 'moderate' || signal === 'elevated')) {
    findings.push({
      label: 'Government flood overlay',
      value: 'Not in statutory flood overlay',
      detail: 'This property is not in a gazetted flood zone, but other data sources in this report indicate flood exposure. The EPI overlay does not cover all flood-affected areas — absence from the overlay is not clearance.',
      severity: 'amber',
    });
  } else if (epiClass === 'none') {
    findings.push({
      label: 'Government flood overlay',
      value: 'Not mapped as flood-prone',
      detail: 'This property is not in a gazetted flood zone under the NSW planning instruments. Lenders and insurers typically don\'t flag properties outside this overlay.',
      severity: 'green',
    });
  } else {
    findings.push({
      label: 'Government flood overlay',
      value: epiMeta.label,
      detail: 'This property is inside a gazetted flood zone. Your lender\'s valuer will note this, and insurers will price flood loading into your premium.',
      severity: 'red',
    });
  }

  // Council flood study
  if (o.ses_in_flood_planning_area === true) {
    const studyLabel = o.ses_flood_class ?? 'In flood extent';
    findings.push({
      label: 'Council flood study',
      value: studyLabel,
      detail: `Council\'s own flood modelling places this property inside the flood extent. This is the data conveyancers reference in Section 10.7 certificates.`,
      severity: 'red',
    });
  } else if (o.ses_in_flood_planning_area === false) {
    findings.push({
      label: 'Council flood study',
      value: 'Outside mapped flood extent',
      detail: 'The council flood model does not show this property within the flood planning area.',
      severity: 'green',
    });
  }

  // Satellite water history
  if (o.dea_wofs_frequency_pct != null) {
    const pct = o.dea_wofs_frequency_pct;
    if (pct === 0) {
      findings.push({
        label: 'Satellite water history',
        value: 'No water detected since 1987',
        detail: 'Across 37 years of Landsat satellite passes, no surface water has been observed at this location.',
        severity: 'green',
      });
    } else if (pct < 5) {
      findings.push({
        label: 'Satellite water history',
        value: `Water detected in ${pct.toFixed(1)}% of satellite passes`,
        detail: 'Satellites have detected surface water here on rare occasions since 1987. This could indicate localised ponding or proximity to a waterway that occasionally overtops.',
        severity: 'amber',
      });
    } else {
      findings.push({
        label: 'Satellite water history',
        value: `Water detected in ${pct.toFixed(1)}% of satellite passes`,
        detail: 'Satellites regularly detect surface water at this location. This is a strong independent signal of recurring flood exposure.',
        severity: 'red',
      });
    }
  }

  // Named local flood study modelling — the canonical flood_studies array
  // covers all four studies (Hawkesbury, Redbank, Tweed, Wollongong)
  // uniformly, each giving a real modelled depth/level specific to this
  // address rather than the category-only EPI overlay everywhere else in
  // NSW gets. Loop first; studiesShown tracks which studies it already
  // covered so the legacy Hawkesbury-only fields below act as a fallback
  // for older stored reports generated before flood_studies existed on the
  // wire, never a duplicate of a study already shown here.
  const studiesShown = new Set<string>();
  if (Array.isArray(o.flood_studies)) {
    for (const raw of o.flood_studies) {
      if (!raw || typeof raw !== 'object') continue;
      const study = raw as Record<string, unknown>;
      const studyKey = typeof study.study_key === 'string' && study.study_key ? study.study_key : null;
      // Fall back to a humanised study_key when study_name is missing so a
      // real, usable figure is never silently dropped just because one
      // string field on the entry didn't validate.
      const displayName = typeof study.study_name === 'string' && study.study_name
        ? study.study_name
        : studyKey
          ? `${studyKey.charAt(0).toUpperCase()}${studyKey.slice(1)} flood study`
          : null;
      const design = study.design && typeof study.design === 'object'
        ? (study.design as Record<string, unknown>)
        : null;
      const onePctRaw = design ? design['1pct'] : null;
      const onePct = onePctRaw && typeof onePctRaw === 'object'
        ? (onePctRaw as { depth_m?: unknown; level_m_ahd?: unknown })
        : null;
      if (!displayName || !onePct) continue;
      const depth = typeof onePct.depth_m === 'number' ? onePct.depth_m : null;
      const level = typeof onePct.level_m_ahd === 'number' ? onePct.level_m_ahd : null;
      if (depth == null && level == null) continue;
      const figure = depth != null
        ? `${depth.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}m deep`
        : `${(level as number).toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}m AHD`;
      findings.push({
        // Label matches whichever measurement is actually shown — depth_m
        // and level_m_ahd are not interchangeable (a depth is height of
        // water above ground; an AHD level is height above a fixed datum),
        // and a study can supply only one of the two.
        label: depth != null ? '1-in-100-year flood depth' : '1-in-100-year flood level',
        value: figure,
        // Source-neutral vs the EPI overlay: naming this "more detailed than
        // the standard overlay used elsewhere in NSW" would be an unqualified
        // statewide comparison this component can't establish (some other
        // area could have its own detailed local study too).
        detail: `Modelled water ${depth != null ? 'depth' : 'level'} at this location from ${displayName}; the EPI overlay separately maps planning categories. Insurers and lenders may use flood information like this in their own assessments — confirm their specific requirements directly.`,
        severity: 'red',
      });
      // Normalized identity, not a bare study_key match: a malformed or
      // differently-cased key on a genuine Hawkesbury entry would otherwise
      // defeat the fallback-suppression below and let the same study render
      // twice (once here, once from the legacy flat fields).
      const normalizedKey = studyKey ? studyKey.toLowerCase() : '';
      if (normalizedKey === 'hawkesbury' || displayName.toLowerCase().includes('hawkesbury')) {
        studiesShown.add('hawkesbury');
      }
    }
  }
  if (!studiesShown.has('hawkesbury') && o.hawkesbury_flood_level_100aep != null) {
    findings.push({
      label: '1-in-100 year flood level',
      value: `${o.hawkesbury_flood_level_100aep.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}m AHD`,
      detail: 'This is the modelled water level at this site during a 1% annual chance flood. Insurers and lenders may use flood information like this in their own assessments — confirm their specific requirements directly.',
      severity: 'red',
    });
  }

  const sevColor = { green: 'bg-green-500', amber: 'bg-amber-400', red: 'bg-red-500' };

  return (
    <div className="bg-white rounded-xl border border-gray-200">
      {/* Header — signal badge + address */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <h2 className="font-semibold text-gray-900 text-base">{result.address}</h2>
          <span className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${signalMeta.badge}`}>
            {signalMeta.label}
          </span>
        </div>
        <p className="text-sm text-gray-600">{signalMeta.sublabel}</p>
        {/* Positioned here, not only in the footer disclaimer, because a
            reader who stops at the badge still sees it: this is a
            screening signal, not a scored risk figure — the calibration
            rerun (2026-09-01) came out statistically indistinguishable from
            its own pass mark, and there is still no measured false-positive
            rate at all. */}
        <p className="text-xs text-amber-700 mt-1.5">
          Screening signal, not a scored risk — the underlying accuracy has not yet been independently established.
        </p>
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

      {/* Warnings — compact */}
      {(o.s1_gap_warning || (result.warnings && result.warnings.length > 0)) && (
        <div className="px-5 py-3 bg-amber-50 border-t border-amber-100">
          {o.s1_gap_warning && <p className="text-xs text-amber-700">{o.s1_gap_warning}</p>}
          {result.warnings?.map((w, i) => (
            <p key={i} className="text-xs text-amber-700">{w}</p>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Screening tool — not a legal flood determination. Obtain a Section 10.7 certificate from council for conveyancing.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          {DATA_PROVENANCE.flood}
        </p>
      </div>
    </div>
  );
}
