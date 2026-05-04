'use client';

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
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
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [paymentStatus, setPaymentStatus]   = useState<'success' | 'cancelled' | null>(null);

  const stepTimersRef  = useRef<ReturnType<typeof setTimeout>[]>([]);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Payment callback banner
  useEffect(() => {
    const payment = searchParams?.get('payment');
    if (payment === 'success')    setPaymentStatus('success');
    if (payment === 'cancelled')  setPaymentStatus('cancelled');
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

  // Start polling a report_id (max 100 polls x 3s = 5 min)
  const pollCountRef = useRef(0);
  const MAX_POLLS = 100;

  const startPolling = useCallback((id: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollCountRef.current = 0;

    const poll = async () => {
      pollCountRef.current += 1;
      if (pollCountRef.current > MAX_POLLS) {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        setErrorMsg('Analysis timed out after 5 minutes — please try again.');
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

  const handleCheckout = async () => {
    const rid = result?.id ?? reportId;
    if (!email.trim() || !rid) return;
    setCheckoutLoading(true);
    try {
      const res = await fetch('/api/stripe/checkout/pre-da-history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: rid, email: email.trim() }),
      });
      const json = await res.json();
      if (json?.checkout_url) {
        window.location.href = json.checkout_url;
      } else {
        throw new Error(json?.error ?? 'Checkout failed');
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Checkout failed');
    } finally {
      setCheckoutLoading(false);
    }
  };

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
        <div className="mb-6">
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
            Analysis runs in the background — takes 3–5 minutes.
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

      {/* Results */}
      {state === 'complete' && result && (
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
              <p>No significant physical changes detected on this lot between 2017 and 2024. No development applications found on record. This is a clean site history — low risk of unapproved works or undisclosed changes.</p>
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

          {/* Stripe CTA */}
          <div className="p-6 bg-teal-50 border border-teal-200 rounded-lg">
            <h2 className="text-sm font-semibold text-gray-900 mb-1">Get the full PDF report — $49</h2>
            <p className="text-xs text-gray-500 mb-4">
              Includes the full annotated timeline, DA event detail, heritage assessment, methodology, and disclaimer.
              Delivered to your email immediately after payment.
            </p>
            <div className="flex gap-3">
              <input
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
              <button
                onClick={handleCheckout}
                disabled={!email.trim() || !(result?.id ?? reportId) || checkoutLoading}
                className="bg-teal-700 hover:bg-teal-800 disabled:opacity-40 text-white text-sm font-semibold py-2 px-5 rounded-lg transition-colors whitespace-nowrap"
              >
                {checkoutLoading ? 'Loading...' : 'Buy PDF — $49'}
              </button>
            </div>
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
