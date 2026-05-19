'use client';

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { WaitlistButton } from '@/components/reports/WaitlistButton';
import { DATA_PROVENANCE } from '@/lib/disclaimers';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TimelineEntry {
  year: number;
  level: 'stable' | 'minor' | 'moderate' | 'major' | 'no_data';
  label: string;
  similarity?: number | null;
  suppressed?: boolean;
  explanation?: string;
  change_type?: string;
  da_events?: string[];
}

interface PipelineResult {
  id?: string;
  address: string;
  lat: number;
  lon: number;
  council: string | null;
  heritage_flag: boolean;
  heritage_note: string | null;
  timeline: TimelineEntry[];
  wayback_ssim?: Record<string, number>;
  run_date: string;
  data_quality_note: string;
}

type PageState = 'idle' | 'submitting' | 'polling' | 'complete' | 'error';

// ---------------------------------------------------------------------------
// Progress steps — purely cosmetic, driven by elapsed time
// ---------------------------------------------------------------------------

const PIPELINE_STEPS = [
  { label: 'Geocoding address with NSW Planning Portal',      ms: 0 },
  { label: 'Loading annual satellite embeddings (2017–2025)', ms: 4000 },
  { label: 'Computing neighbourhood similarity baseline',     ms: 58000 },
  { label: 'Querying vegetation and built-up indices',        ms: 95000 },
  { label: 'Fetching DA events from NSW ePlanning Portal',    ms: 105000 },
  { label: 'Applying flood and bushfire event annotations',   ms: 112000 },
  { label: 'Assembling annotated timeline',                   ms: 116000 },
];

// ---------------------------------------------------------------------------
// Level display helpers
// ---------------------------------------------------------------------------

function levelBg(level: string): string {
  if (level === 'major')    return 'bg-red-50 text-red-700 border border-red-200';
  if (level === 'moderate') return 'bg-orange-50 text-orange-700 border border-orange-200';
  if (level === 'minor')    return 'bg-amber-50 text-amber-700 border border-amber-200';
  if (level === 'no_data')  return 'bg-gray-50 text-gray-400 border border-gray-200';
  return 'bg-green-50 text-green-700 border border-green-200';
}

function levelLabel(level: string): string {
  if (level === 'major')    return 'Major change';
  if (level === 'moderate') return 'Moderate change';
  if (level === 'minor')    return 'Minor change';
  if (level === 'no_data')  return 'No data';
  return 'Stable';
}

function levelTextColor(level: string): string {
  if (level === 'major')    return 'text-red-600';
  if (level === 'moderate') return 'text-orange-600';
  if (level === 'minor')    return 'text-amber-600';
  if (level === 'no_data')  return 'text-gray-400';
  return 'text-green-600';
}

// ---------------------------------------------------------------------------
// Inner component (needs Suspense for useSearchParams)
// ---------------------------------------------------------------------------

function PreDAHistoryToolInner() {
  const searchParams = useSearchParams();

  const [address, setAddress]               = useState('');
  const [state, setState]                   = useState<PageState>('idle');
  const [result, setResult]                 = useState<PipelineResult | null>(null);
  const [reportId, setReportId]             = useState<string | null>(null);
  const [errorMsg, setErrorMsg]             = useState('');
  const [step, setStep]                     = useState(0);
  const [email, setEmail]                   = useState('');

  const [paymentStatus, setPaymentStatus]   = useState<'success' | 'cancelled' | null>(null);

  const stepTimersRef  = useRef<ReturnType<typeof setTimeout>[]>([]);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const handleRunRef = useRef<() => void>(() => {});

  // Listen for hero address input — submit directly after state update flushes
  useEffect(() => {
    const handler = (e: Event) => {
      const addr = (e as CustomEvent).detail?.address;
      if (addr) {
        setAddress(addr);
        setTimeout(() => handleRunRef.current(), 0);
      }
    };
    window.addEventListener('landing-search', handler);
    return () => window.removeEventListener('landing-search', handler);
  }, []);

  // Read URL params: ?address= (auto-run) and ?payment= (callback banner)
  useEffect(() => {
    const payment = searchParams?.get('payment');
    if (payment === 'success')    setPaymentStatus('success');
    if (payment === 'cancelled')  setPaymentStatus('cancelled');
    // Clean URL params after reading
    if (payment) {
      window.history.replaceState({}, '', window.location.pathname);
    }

    const addrParam = searchParams?.get('address')?.trim();
    if (addrParam && !payment) {
      setAddress(addrParam);
      setTimeout(() => handleRunRef.current(), 0);
    }
  }, [searchParams]);

  // Advance cosmetic progress steps while polling
  useEffect(() => {
    if (state === 'polling') {
      setStep(0);
      stepTimersRef.current.forEach(clearTimeout);
      stepTimersRef.current = PIPELINE_STEPS.slice(1).map((s, i) =>
        setTimeout(() => setStep(i + 1), s.ms)
      );
    } else {
      stepTimersRef.current.forEach(clearTimeout);
      stepTimersRef.current = [];
      setStep(0);
    }
    return () => { stepTimersRef.current.forEach(clearTimeout); };
  }, [state]);

  // Start polling a report_id (max 60 polls x 3s = 3 min)
  const pollCountRef = useRef(0);
  const MAX_POLLS = 60;

  const startPolling = useCallback((id: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollCountRef.current = 0;

    const poll = async () => {
      pollCountRef.current += 1;
      if (pollCountRef.current > MAX_POLLS) {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        setErrorMsg('Analysis timed out after 3 minutes — please try again.');
        setState('error');
        return;
      }

      try {
        const res = await fetch(`/api/satellite/pre-da-history?report_id=${id}`);
        const json = await res.json();

        if (json.status === 'error') {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setErrorMsg(json.error ?? 'Pipeline failed — please try again.');
          setState('error');
          return;
        }

        if (json.status === 'complete') {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setResult({ ...json.data, id });
          setState('complete');
          return;
        }
        // status === 'pending' — keep polling
      } catch {
        // network blip — keep polling
      }
    };

    pollIntervalRef.current = setInterval(poll, 3000);
    poll(); // immediate first check
  }, []);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Resume polling from URL param (payment redirect)
  useEffect(() => {
    const rid = searchParams?.get('report_id');
    if (rid && state === 'idle') {
      setReportId(rid);
      setState('polling');
      startPolling(rid);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRun = async () => {
    if (!address.trim()) return;
    setState('submitting');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/pre-da-history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: address.trim() }),
      });

      const json = await res.json();

      if (!res.ok) {
        throw new Error(json?.error ?? `Request failed (${res.status})`);
      }

      const rid = json.report_id as string;
      setReportId(rid);
      setState('polling');
      startPolling(rid);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };
  handleRunRef.current = handleRun;

  // Derived stats
  const validYears    = result ? result.timeline.filter((r) => r.level !== 'no_data') : [];
  const notableYears  = result ? result.timeline.filter((r) =>
    r.level === 'minor' || r.level === 'moderate' || r.level === 'major'
  ) : [];
  const allDaPans = result
    ? Array.from(new Set(result.timeline.flatMap((r) => r.da_events ?? [])))
    : [];

  const isRunning = state === 'submitting' || state === 'polling';

  return (
    <div>
      {/* Payment banners */}
      {paymentStatus === 'success' && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          Payment confirmed — your PDF report will arrive by email shortly.
        </div>
      )}
      {paymentStatus === 'cancelled' && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          Payment cancelled. Your analysis is still saved — enter your email below to purchase.
        </div>
      )}

      {/* Address input */}
      {(state === 'idle' || state === 'error') && (
        <div id="tool-input" className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">NSW property address</label>
          <AddressAutocomplete
            value={address}
            onChange={setAddress}
            onSelect={(addr) => setAddress(addr)}
            placeholder="e.g. 176 Marrickville Road Marrickville NSW 2204"
            className="w-full"
          />
          {state === 'error' && (
            <p className="mt-2 text-sm text-red-600">{errorMsg}</p>
          )}
          <button
            onClick={handleRun}
            disabled={!address.trim()}
            className="mt-4 w-full bg-teal-700 hover:bg-teal-800 disabled:opacity-40 text-white text-sm font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            Run site history analysis
          </button>
          <p className="mt-2 text-xs text-gray-400 text-center">
            Analysis runs in the background — takes 2–4 minutes.
          </p>
        </div>
      )}

      {/* Loading / progress */}
      {isRunning && (
        <div className="mb-6 p-6 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold text-gray-700 mb-4">
            {state === 'submitting' ? 'Starting analysis...' : `Analysing ${address}...`}
          </p>
          <div className="space-y-3">
            {PIPELINE_STEPS.map((s, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`w-4 h-4 rounded-full flex-shrink-0 transition-colors ${
                  i < step  ? 'bg-teal-600' :
                  i === step ? 'bg-teal-400 animate-pulse' :
                  'bg-gray-200'
                }`} />
                <span className={`text-xs ${i <= step ? 'text-gray-700' : 'text-gray-400'}`}>
                  {s.label}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-gray-400">
            First-time analysis for a new area takes ~3 minutes to download satellite tiles.
            Subsequent runs are faster.
          </p>
        </div>
      )}

      {/* Payment success — thank you + PDF download + full results */}
      {paymentStatus === 'success' && (
        <PreDAPaidResults
          reportId={reportId}
          result={result}
          state={state}
          validYears={validYears}
          notableYears={notableYears}
          allDaPans={allDaPans}
          onRunAnother={() => {
            setState('idle');
            setResult(null);
            setAddress('');
            setEmail('');
            setReportId(null);
            setPaymentStatus(null);
          }}
        />
      )}

      {/* Results — free tier (no payment) */}
      {state === 'complete' && result && paymentStatus !== 'success' && (
        <>
          {/* Findings */}
          <SiteHistoryFindings result={result} validYears={validYears} notableYears={notableYears} allDaRefs={allDaPans} />

          <FreePaidComparison
            free={[
              'Satellite change detection (8 years)',
              'DA record cross-reference',
              'Heritage overlay check',
              'Year-by-year timeline table',
            ]}
            paid={[
              'Full annotated timeline with methodology',
              'DA event detail + application numbers',
              'Heritage assessment narrative',
              'Source citations for conveyancer',
              'Disclaimer + limitations section',
              'PDF report for your records',
            ]}
          />

          {/* Timeline table */}
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">Year-by-year satellite timeline</h2>
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-900 text-white">
                    <th className="py-2 px-3 text-left font-medium">Year</th>
                    <th className="py-2 px-3 text-left font-medium">Level</th>
                    <th className="py-2 px-3 text-left font-medium">Similarity</th>
                    <th className="py-2 px-3 text-left font-medium">Notes</th>
                    <th className="py-2 px-3 text-left font-medium">DA refs</th>
                  </tr>
                </thead>
                <tbody>
                  {result.timeline.map((entry, i) => (
                    <tr key={entry.year} className={i % 2 === 1 ? 'bg-gray-50' : 'bg-white'}>
                      <td className="py-2 px-3 font-semibold text-gray-900">{entry.year}</td>
                      <td className="py-2 px-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${levelBg(entry.level)}`}>
                          {levelLabel(entry.level)}
                        </span>
                      </td>
                      <td className={`py-2 px-3 ${levelTextColor(entry.level)}`}>
                        {entry.similarity != null ? entry.similarity.toFixed(3) : '\u2014'}
                      </td>
                      <td className="py-2 px-3 text-gray-600 max-w-xs">
                        {entry.suppressed
                          ? 'No lot-specific change — area-wide variation filtered out'
                          : entry.explanation || entry.label || '\u2014'}
                      </td>
                      <td className="py-2 px-3 text-gray-400">
                        {entry.da_events && entry.da_events.length > 0
                          ? entry.da_events.join(', ')
                          : '\u2014'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Methodology note */}
          <p className="text-xs text-gray-400 mb-6 leading-relaxed">
            Each year is compared to the previous year and to the surrounding neighbourhood. Years marked
            &ldquo;area-wide variation filtered out&rdquo; showed satellite changes consistent with the whole
            neighbourhood (drought, seasonal shift, or sensor variation) rather than lot-specific activity.
            DA events are sourced from the NSW ePlanning Portal — complete from July 2021.
          </p>

          {/* Waitlist CTA */}
          <div className="p-6 bg-teal-50 border border-teal-200 rounded-lg">
            <h2 className="text-sm font-semibold text-gray-900 mb-1">Full PDF report — coming soon</h2>
            <p className="text-xs text-gray-500 mb-4">
              Includes the full annotated timeline, DA event detail, heritage assessment, methodology, and disclaimer.
            </p>
            <WaitlistButton interestType="pre-da-history" address={result?.address} />
          </div>

          {/* Run another */}
          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setState('idle');
                setResult(null);
                setAddress('');
                setEmail('');
                setReportId(null);
              }}
              className="text-sm text-teal-700 hover:underline"
            >
              Run another analysis
            </button>
          </div>

          {/* Data provenance */}
          <p className="text-xs text-gray-400 text-center mt-4">
            {DATA_PROVENANCE.pre_da_history}
          </p>

          {/* Cross-sell */}
          <ToolCrossSell currentTool="pre-da-history" address={result.address} />
        </>
      )}
    </div>
  );
}

function FreePaidComparison({ free, paid }: { free: string[]; paid: string[] }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
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
// SiteHistoryFindings — findings + detail pattern
// ---------------------------------------------------------------------------

const sevColor = { green: 'bg-green-500', amber: 'bg-amber-400', red: 'bg-red-500' };

function SiteHistoryFindings({
  result,
  validYears,
  notableYears,
  allDaRefs,
}: {
  result: PipelineResult;
  validYears: TimelineEntry[];
  notableYears: TimelineEntry[];
  allDaRefs: string[];
}) {
  const findings: { label: string; value: string; detail: string; severity: 'green' | 'amber' | 'red' }[] = [];

  // Satellite change detection
  if (notableYears.length === 0) {
    findings.push({
      label: `Sentinel-2 satellite analysis — ${validYears.length} years (2017–2024)`,
      value: 'No significant physical changes detected',
      detail: 'Across 8 years of satellite imagery, no demolition, construction, or major ground disturbance was detected on this lot. No indicators of undisclosed or unapproved works were found in the data sources checked.',
      severity: 'green',
    });
  } else {
    const majorYears = notableYears.filter(y => y.level === 'major');
    const yearList = notableYears.map(y => y.year).join(', ');
    findings.push({
      label: `Sentinel-2 satellite analysis — ${validYears.length} years (2017–2024)`,
      value: `Physical change detected in ${yearList}`,
      detail: majorYears.length > 0
        ? `Major ground disturbance detected — likely demolition, construction, or significant earthworks. A conveyancer can verify whether these changes were approved and properly certified.`
        : `Minor to moderate changes detected — could be renovations, landscaping, or outbuilding additions. Worth checking whether council approval was obtained, especially if not disclosed in the contract.`,
      severity: majorYears.length > 0 ? 'red' : 'amber',
    });
  }

  // DA events
  if (allDaRefs.length === 0) {
    findings.push({
      label: 'NSW ePlanning Portal — DA records',
      value: 'No development applications found',
      detail: notableYears.length > 0
        ? 'Satellite detected physical changes but no DAs are on record. This could mean unapproved works, works predating the ePlanning Portal (pre-2021), or exempt/complying development that doesn\'t require a DA.'
        : 'No DAs lodged for this property in the ePlanning Portal. This is consistent with the clean satellite result.',
      severity: notableYears.length > 0 ? 'red' : 'green',
    });
  } else {
    findings.push({
      label: 'NSW ePlanning Portal — DA records',
      value: `${allDaRefs.length} development application${allDaRefs.length !== 1 ? 's' : ''} found`,
      detail: notableYears.length > 0
        ? `DA records exist for this property. Cross-reference the satellite timeline below to check whether detected changes align with lodged applications.`
        : `DA records exist but no significant physical changes were detected by satellite. The approved works may have been minor, internal, or not yet constructed.`,
      severity: 'amber',
    });
  }

  // Heritage
  if (result.heritage_flag) {
    findings.push({
      label: 'Heritage overlay',
      value: 'Heritage item or conservation area',
      detail: result.heritage_note
        ? `${result.heritage_note}. Any modifications to this property — past or planned — may require heritage approval under your LEP. Unapproved works on heritage items can result in orders to restore at the owner\'s cost.`
        : 'This property is within a heritage overlay. Any modifications may require heritage approval. If satellite detected changes, verify they were heritage-approved — restoration orders are expensive.',
      severity: 'amber',
    });
  } else {
    findings.push({
      label: 'Heritage overlay',
      value: 'Not heritage listed',
      detail: 'This property is not within a heritage conservation area or individually listed. No heritage-specific approval requirements apply.',
      severity: 'green',
    });
  }

  // Data coverage
  if (validYears.length < 6) {
    findings.push({
      label: 'Satellite data coverage',
      value: `${validYears.length} of 8 years had usable imagery`,
      detail: 'Some years had cloud cover or missing satellite passes. Changes during gaps would not be detected. The timeline table below shows which years have data.',
      severity: 'amber',
    });
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 mb-6">
      <div className="divide-y divide-gray-50">
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
    </div>
  );
}

// ---------------------------------------------------------------------------
// PreDAPaidResults — post-payment thank-you + full results + PDF download
// ---------------------------------------------------------------------------

function PreDAPaidResults({
  reportId,
  result,
  state,
  validYears,
  notableYears,
  allDaPans,
  onRunAnother,
}: {
  reportId: string | null;
  result: PipelineResult | null;
  state: PageState;
  validYears: TimelineEntry[];
  notableYears: TimelineEntry[];
  allDaPans: string[];
  onRunAnother: () => void;
}) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState('');

  const handleDownload = async () => {
    if (!reportId) return;
    setDownloading(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/pre-da-history/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pre-da-history-${reportId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setDlError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div>
      {/* Thank you banner + download */}
      <div className="mb-6 rounded-xl border border-teal-200 bg-teal-50 p-6">
        <p className="text-base font-semibold text-teal-900 mb-1">Payment confirmed — thank you.</p>
        <p className="text-sm text-teal-700 mb-4">
          Your full PDF report is being emailed to you now. You can also download it directly below.
        </p>
        {reportId && (
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="w-full py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {downloading ? 'Preparing download...' : 'Download PDF report'}
          </button>
        )}
        {dlError && <p className="text-xs text-red-600 mt-2">{dlError}</p>}
      </div>

      {/* Loading while polling for results */}
      {state === 'polling' && (
        <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-sm text-gray-600 animate-pulse">Loading your results...</p>
        </div>
      )}

      {/* Full paid results */}
      {result && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Years analysed</p>
              <p className="text-2xl font-bold text-gray-900">{validYears.length}/8</p>
              <p className="text-xs text-gray-400 mt-1">2017–2024</p>
            </div>
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Notable years</p>
              <p className={`text-2xl font-bold ${notableYears.length > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                {notableYears.length}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {notableYears.length === 0 ? 'No changes detected' : 'Year(s) with detected change'}
              </p>
            </div>
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">DA events found</p>
              <p className="text-2xl font-bold text-gray-900">{allDaPans.length}</p>
              <p className="text-xs text-gray-400 mt-1">
                {allDaPans.length > 0 ? allDaPans[0] : 'None matched'}
              </p>
            </div>
          </div>

          {/* Interpretation summary */}
          <div className="mb-4 p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 leading-relaxed">
            <p className="font-semibold text-slate-900 mb-1">What this means</p>
            {notableYears.length === 0 && allDaPans.length === 0 && (
              <p>No significant physical changes detected on this lot between 2017 and 2024. No development applications found on record. No indicators of unapproved works or undisclosed changes were found in the data sources checked.</p>
            )}
            {notableYears.length === 0 && allDaPans.length > 0 && (
              <p>No significant physical changes detected by satellite, but {allDaPans.length} DA event{allDaPans.length !== 1 ? 's' : ''} found on record. The approved works may have been minor or not yet constructed.</p>
            )}
            {notableYears.length > 0 && allDaPans.length > 0 && (
              <p>Physical change detected in {notableYears.map(y => y.year).join(', ')} — and {allDaPans.length} DA event{allDaPans.length !== 1 ? 's' : ''} found on record. Cross-reference the DA details with the satellite timeline to check whether all changes were approved.</p>
            )}
            {notableYears.length > 0 && allDaPans.length === 0 && (
              <p>Physical change detected in {notableYears.map(y => y.year).join(', ')} but no development applications found on record. This may indicate unapproved works, natural events, or works predating the ePlanning Portal (pre-2021).</p>
            )}
          </div>

          {/* Heritage flag */}
          <div className={`mb-4 p-4 rounded-lg text-sm ${
            result.heritage_flag
              ? 'bg-amber-50 border border-amber-200 text-amber-800'
              : 'bg-green-50 border border-green-200 text-green-800'
          }`}>
            <span className="font-semibold">
              {result.heritage_flag ? 'Heritage overlay detected' : 'No heritage overlay detected'}
            </span>
            {result.heritage_note && (
              <p className="mt-1 text-xs">{result.heritage_note}</p>
            )}
          </div>

          {/* Timeline table */}
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">Year-by-year satellite timeline</h2>
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-900 text-white">
                    <th className="py-2 px-3 text-left font-medium">Year</th>
                    <th className="py-2 px-3 text-left font-medium">Level</th>
                    <th className="py-2 px-3 text-left font-medium">Notes</th>
                    <th className="py-2 px-3 text-left font-medium">DA refs</th>
                  </tr>
                </thead>
                <tbody>
                  {result.timeline.map((entry, i) => (
                    <tr key={entry.year} className={i % 2 === 1 ? 'bg-gray-50' : 'bg-white'}>
                      <td className="py-2 px-3 font-semibold text-gray-900">{entry.year}</td>
                      <td className="py-2 px-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${levelBg(entry.level)}`}>
                          {levelLabel(entry.level)}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-gray-600 max-w-xs">
                        {entry.suppressed
                          ? 'Stable — neighbourhood-wide variation, not site-specific'
                          : entry.explanation || entry.label || '\u2014'}
                      </td>
                      <td className="py-2 px-3 text-gray-400">
                        {entry.da_events && entry.da_events.length > 0
                          ? entry.da_events.join(', ')
                          : '\u2014'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Detailed analysis — paid content, always shown after payment */}
          {result.timeline.some(e => !e.suppressed && e.level !== 'no_data') && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-gray-900 mb-3">Detailed analysis</h2>
              <div className="space-y-3">
                {result.timeline
                  .filter(e => !e.suppressed && e.level !== 'no_data')
                  .map(entry => (
                    <div key={entry.year} className="p-4 border border-gray-200 rounded-lg bg-white">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-semibold text-gray-900">{entry.year}</span>
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${levelBg(entry.level)}`}>
                          {levelLabel(entry.level)}
                        </span>
                        {entry.change_type && entry.change_type !== 'unknown' && (
                          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                            {entry.change_type}
                          </span>
                        )}
                      </div>
                      {entry.similarity != null && (
                        <p className="text-xs text-gray-500 mb-1">
                          Similarity score: {entry.similarity.toFixed(3)}
                        </p>
                      )}
                      {entry.explanation && (
                        <p className="text-sm text-gray-700">{entry.explanation}</p>
                      )}
                      {entry.da_events && entry.da_events.length > 0 && (
                        <p className="text-xs text-gray-400 mt-1">
                          DA references: {entry.da_events.join(', ')}
                        </p>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Methodology note */}
          <p className="text-xs text-gray-400 mb-6 leading-relaxed">
            Each year is compared to the previous year and to the surrounding neighbourhood. Years marked
            &ldquo;area-wide variation filtered out&rdquo; showed satellite changes consistent with the whole
            neighbourhood (drought, seasonal shift, or sensor variation) rather than lot-specific activity.
            DA events are sourced from the NSW ePlanning Portal — complete from July 2021.
          </p>

          {/* Run another */}
          <div className="mt-6 text-center">
            <button onClick={onRunAnother} className="text-sm text-teal-700 hover:underline">
              Run another analysis
            </button>
          </div>

          {/* Cross-sell */}
          <ToolCrossSell currentTool="pre-da-history" address={result.address} />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Export wrapped in Suspense for useSearchParams
// ---------------------------------------------------------------------------

export function PreDAHistoryTool() {
  return (
    <Suspense>
      <PreDAHistoryToolInner />
    </Suspense>
  );
}
