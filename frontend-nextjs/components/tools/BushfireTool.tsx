'use client';

import { useState, useEffect } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { posthog } from '@/components/providers/PostHogProvider';

interface BushfireCompliance {
  state_legislation: string | null;
  rfs_referral_required: boolean | null;
  rfs_referral_triggers: string[] | null;
  cdc_pathway_available: boolean | null;
  clearing_10_50_entitled: boolean | null;
  clearing_10_50_exceptions: string | null;
  cross_overlays: Array<{ type: string; value: string; source: string }> | null;
  estimated_consultant_costs: string | null;
  zone: string | null;
  compliance_depth: string;
  legislation_url: string | null;
}

interface BushfireOutputs {
  is_bushfire_prone: boolean | null;
  designation_source: string | null;
  designation_category: string | null;
  designation_guideline: string | null;
  estimated_bal_band: string | null;
  bal_assessment_likely_required: boolean | null;
  bal_formal_assessment_cost_range: string | null;
  bal_assessor_directory_url: string | null;
  fire_signal: 'none' | 'low' | 'moderate' | 'elevated' | 'unavailable';
  compliance: BushfireCompliance;
  data_currency: string;
}

interface BushfireResult {
  address: string;
  lat: number;
  lng: number;
  run_date: string;
  outputs: BushfireOutputs;
  confidence: 'high' | 'medium' | 'low';
  data_sources: string[];
  report_id?: string;
  report_token?: string;
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const FIRE_SIGNAL_META: Record<string, { label: string; sublabel: string; badge: string }> = {
  none: {
    label: 'Not bushfire prone',
    sublabel: 'This property is not mapped as bushfire prone land under the NSW RFS Bush Fire Prone Land Map',
    badge: 'bg-green-100 text-green-800',
  },
  low: {
    label: 'Low fire signal',
    sublabel: 'Bushfire prone — Vegetation Buffer or Category 3. BAL assessment required before development.',
    badge: 'bg-yellow-100 text-yellow-800',
  },
  moderate: {
    label: 'Moderate fire signal',
    sublabel: 'Vegetation Category 2. Estimated BAL-29. RFS referral required for new development.',
    badge: 'bg-orange-100 text-orange-800',
  },
  elevated: {
    label: 'Elevated fire signal',
    sublabel: 'Vegetation Category 1 — highest risk. Estimated BAL-40 to BAL-FZ. DA pathway mandatory.',
    badge: 'bg-red-100 text-red-800',
  },
  unavailable: {
    label: 'RFS data unavailable',
    sublabel: 'Could not query the NSW RFS Bush Fire Prone Land Map. Check the RFS portal directly.',
    badge: 'bg-gray-100 text-gray-600',
  },
};

const BAL_COLOR: Record<string, string> = {
  'BAL-LOW':           'bg-green-50 text-green-700',
  'BAL-12.5':          'bg-yellow-50 text-yellow-700',
  'BAL-19':            'bg-yellow-50 text-yellow-700',
  'BAL-29':            'bg-orange-50 text-orange-700',
  'BAL-40 to BAL-FZ':  'bg-red-50 text-red-700',
};

export function BushfireTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<BushfireResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState('');
  const [paidReportId, setPaidReportId] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('payment') === 'success') {
      const rid = params.get('report_id')?.trim();
      if (rid) setPaidReportId(rid);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const handleUnlock = async (reportId: string, addr: string) => {
    setUnlocking(true);
    setUnlockError('');
    try {
      const res = await fetch('/api/stripe/checkout/bushfire', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId, address: addr }),
      });
      const json = await res.json();
      if (!res.ok || !json.checkout_url) throw new Error(json.error || 'Checkout failed');
      window.location.href = json.checkout_url;
    } catch (err: unknown) {
      setUnlockError(err instanceof Error ? err.message : 'Something went wrong');
      setUnlocking(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/bushfire', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Bushfire check failed');
      setResult(json);
      setState('complete');
      posthog.capture('tool_run', {
        tool: 'bushfire',
        source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
        embed_ref: embedRef ?? null,
        lga_slug: lgaSlug ?? null,
        result: json.outputs?.fire_signal ?? null,
      });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  return (
    <div className="mb-8">
      <h1 className="text-2xl font-bold text-gray-900">Bushfire Pre-Screen</h1>
      <p className="mt-1.5 text-sm text-gray-500">
        Check if an NSW property is on bushfire prone land and understand the development
        implications. Uses the live NSW RFS Bush Fire Prone Land Map — state-wide coverage,
        no login required.
      </p>
      <p className="mt-2 text-sm text-gray-400">
        BFPL category, estimated BAL band, RFS referral requirement, and 10/50 vegetation
        clearing entitlements. Full report includes AS 3959 construction standards,
        referral triggers, cross-overlays, and consultant cost estimates.
      </p>

      <form onSubmit={handleSubmit} className="flex gap-3 mt-6 mb-8">
        <AddressAutocomplete
          value={address}
          onChange={setAddress}
          onSelect={(addr) => setAddress(addr)}
          className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          disabled={state === 'running'}
        />
        <button
          type="submit"
          disabled={state === 'running' || !address.trim()}
          className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {state === 'running' ? 'Checking...' : 'Run Bushfire Check'}
        </button>
      </form>

      {state === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Querying NSW RFS bushfire prone land data...</p>
          <p className="text-xs text-gray-400 mt-1">RFS BFPL map &middot; PostGIS zone overlays. Allow 5&ndash;15 seconds.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && result && (
        <>
          <BushfireCard result={result} />
          {result.report_id ? (
            paidReportId ? (
              <BushfirePaidDownloadCTA reportId={paidReportId} />
            ) : (
              <BushfireLockedPreviewCard
                result={result}
                onUnlock={() => handleUnlock(result.report_id!, result.address)}
                unlocking={unlocking}
                error={unlockError}
              />
            )
          ) : null}
          <ToolCrossSell currentTool="bushfire" address={result.address} />
        </>
      )}
    </div>
  );
}

function BushfireCard({ result }: { result: BushfireResult }) {
  const o = result.outputs;
  const signal = o.fire_signal ?? 'unavailable';
  const signalMeta = FIRE_SIGNAL_META[signal] ?? FIRE_SIGNAL_META.unavailable;
  const c = o.compliance;
  const sourceCount = (result.data_sources ?? []).length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 mb-6">

      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="font-semibold text-gray-900">{result.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Run {result.run_date} &middot; {sourceCount} data source{sourceCount !== 1 ? 's' : ''} &middot; {result.confidence} confidence
            </p>
          </div>
          <span className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full ${signalMeta.badge}`}>
            {signalMeta.label}
          </span>
        </div>
        <p className="text-xs text-gray-500">{signalMeta.sublabel}</p>
        <p className="text-xs text-gray-400 mt-1">
          Indicative pre-screen only. A formal BAL assessment by a qualified practitioner is
          required before development on bushfire prone land.
        </p>
      </div>

      {/* BFPL designation + BAL band */}
      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">BFPL category</p>
          {o.is_bushfire_prone === null ? (
            <p className="text-sm text-gray-400">Unavailable</p>
          ) : o.is_bushfire_prone ? (
            <>
              <p className="text-sm font-medium text-gray-900">
                {o.designation_category ?? 'Bushfire prone'}
              </p>
              {o.designation_guideline && (
                <p className="text-xs text-gray-400 mt-0.5">{o.designation_guideline}</p>
              )}
            </>
          ) : (
            <p className="text-sm font-medium text-green-700">Not bushfire prone</p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            NSW RFS &middot;{' '}
            {o.data_currency !== 'unknown' && o.data_currency !== 'query_failed'
              ? `as at ${o.data_currency}`
              : 'date unavailable'}
          </p>
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Estimated BAL band</p>
          {o.estimated_bal_band ? (
            <>
              <span className={`inline-block text-sm font-medium px-2 py-0.5 rounded mb-1 ${BAL_COLOR[o.estimated_bal_band] ?? 'bg-gray-50 text-gray-700'}`}>
                {o.estimated_bal_band}
              </span>
              <p className="text-xs text-gray-400">
                {o.bal_assessment_likely_required
                  ? 'Formal BAL assessment required before development'
                  : 'No bushfire construction standards apply'}
              </p>
            </>
          ) : (
            <p className="text-sm text-gray-400">Not applicable</p>
          )}
        </div>
      </div>

      {/* Development implications — shown only when bushfire prone */}
      {o.is_bushfire_prone && c && (
        <div className="p-6 space-y-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Development implications
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">RFS referral required</p>
              <p className={`text-sm font-medium ${c.rfs_referral_required ? 'text-red-700' : c.rfs_referral_required === false ? 'text-green-700' : 'text-gray-500'}`}>
                {c.rfs_referral_required === null
                  ? '—'
                  : c.rfs_referral_required
                  ? 'Yes — s4.14 EP&A Act'
                  : 'No'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">CDC pathway</p>
              <p className={`text-sm font-medium ${c.cdc_pathway_available === false ? 'text-red-700' : c.cdc_pathway_available ? 'text-green-700' : 'text-gray-500'}`}>
                {c.cdc_pathway_available === null
                  ? '—'
                  : c.cdc_pathway_available
                  ? 'Available (BAL \u2264 29)'
                  : 'DA required'}
              </p>
            </div>
          </div>

          {c.rfs_referral_triggers && c.rfs_referral_triggers.length > 0 && (
            <div>
              <p className="text-xs text-gray-400 mb-1">s4.14 referral triggers</p>
              <ul className="space-y-1">
                {c.rfs_referral_triggers.map((trigger, i) => (
                  <li key={i} className="text-xs text-gray-600 flex gap-2">
                    <span className="shrink-0 text-gray-300">&middot;</span>
                    <span>{trigger}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {c.clearing_10_50_entitled !== null && (
            <div>
              <p className="text-xs text-gray-400 mb-1">10/50 vegetation clearing</p>
              <p className="text-sm font-medium text-gray-900">
                {c.clearing_10_50_entitled ? 'Entitlement applies' : 'Does not apply'}
              </p>
              {c.clearing_10_50_exceptions && (
                <p className="text-xs text-gray-500 mt-0.5">{c.clearing_10_50_exceptions}</p>
              )}
            </div>
          )}

          {c.estimated_consultant_costs && (
            <div>
              <p className="text-xs text-gray-400 mb-1">Estimated consultant costs</p>
              <p className="text-sm text-gray-700">{c.estimated_consultant_costs}</p>
            </div>
          )}

          {o.bal_assessor_directory_url && (
            <a
              href={o.bal_assessor_directory_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block text-xs text-teal-600 hover:text-teal-700 underline"
            >
              Find a qualified BAL assessor (RFS directory) &rarr;
            </a>
          )}
        </div>
      )}

      {/* Cross-overlays */}
      {c?.cross_overlays && c.cross_overlays.length > 0 && (
        <div className="p-6">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
            Additional overlays at this site
          </p>
          <div className="space-y-2">
            {c.cross_overlays.map((overlay, i) => (
              <div key={i} className="flex items-center justify-between gap-4 text-sm">
                <span className="capitalize text-gray-700">{overlay.type} overlay</span>
                <span className="text-xs text-gray-500">{overlay.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Legislation link */}
      {c?.legislation_url && (
        <div className="px-6 py-4 bg-gray-50">
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
      <div className="px-6 py-4">
        <p className="text-xs text-gray-400">
          Sources: {(result.data_sources ?? []).join(' \u00b7 ')}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Indicative pre-screen only. Not a formal BAL assessment. For development applications:
          obtain a bushfire assessment from a practitioner listed in the RFS directory.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BushfireLockedPreviewCard — blur-to-reveal paywall
// ---------------------------------------------------------------------------

function BushfireLockedPreviewCard({
  result,
  onUnlock,
  unlocking,
  error,
}: {
  result: BushfireResult;
  onUnlock: () => void;
  unlocking: boolean;
  error: string;
}) {
  const o = result.outputs;
  const c = o.compliance;
  const triggerCount = c.rfs_referral_triggers?.length ?? 0;
  const overlayCount = c.cross_overlays?.length ?? 0;

  const rows = [
    { label: 'AS 3959 construction standards', preview: 'BAL-specific requirements' },
    ...(triggerCount > 0 ? [{ label: 's4.14 referral triggers', preview: `${triggerCount} trigger${triggerCount !== 1 ? 's' : ''} identified` }] : []),
    ...(overlayCount > 0 ? [{ label: 'Cross-overlay analysis', preview: `${overlayCount} overlay${overlayCount !== 1 ? 's' : ''} detected` }] : []),
    ...(c.estimated_consultant_costs ? [{ label: 'Consultant cost estimate', preview: c.estimated_consultant_costs }] : []),
    { label: 'Plain-English interpretation', preview: 'What this means for your project' },
    { label: 'Full PDF report', preview: 'bushfire-report.pdf' },
  ];

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-amber-50 border-b border-amber-100 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900 leading-snug">
          {o.is_bushfire_prone
            ? `${o.designation_category ?? 'Bushfire prone'} — see the full compliance breakdown`
            : 'Full bushfire compliance report'}
        </p>
        <p className="text-xs text-amber-700 mt-1 leading-relaxed">
          AS 3959 construction requirements for your BAL rating, referral triggers,
          cross-overlays, and consultant cost estimates.
        </p>
      </div>

      <div className="bg-white px-5 pt-4 pb-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
          Included in paid report
        </p>
        <div className="space-y-2">
          {rows.map(({ label, preview }) => (
            <div key={label} className="flex items-center justify-between gap-4 text-sm">
              <span className="text-gray-700">{label}</span>
              <span className="blur-sm select-none pointer-events-none font-medium text-gray-900 tabular-nums">
                {preview}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white px-5 pb-5 pt-2">
        <button
          onClick={onUnlock}
          disabled={unlocking}
          className="w-full py-2.5 px-4 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {unlocking ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Starting checkout...
            </>
          ) : (
            'Unlock full report — $29'
          )}
        </button>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
        <p className="text-xs text-gray-400 text-center mt-2">
          Paid once. PDF delivered to your email after checkout.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BushfirePaidDownloadCTA — shown after Stripe payment success
// ---------------------------------------------------------------------------

function BushfirePaidDownloadCTA({ reportId }: { reportId: string }) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/bushfire/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bushfire-report-${reportId.slice(0, 8)}.pdf`;
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
        {downloading ? 'Preparing download...' : 'Download PDF report \u2192'}
      </button>
      {dlError && <p className="text-xs text-red-600 mt-2">{dlError}</p>}
    </div>
  );
}
