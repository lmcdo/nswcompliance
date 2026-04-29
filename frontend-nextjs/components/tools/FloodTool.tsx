'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { PaywallGate } from '@/components/reports/PaywallGate';
import { posthog } from '@/components/providers/PostHogProvider';

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
  bom_gauge_name: string | null;
  bom_gauge_distance_km: number | null;
  bom_last_major_flood_date: string | null;
  bom_last_major_flood_peak_m: number | null;
  s1_gap_warning: string | null;
  data_currency: string;
  flood_signal: 'none' | 'low' | 'moderate' | 'elevated' | null;
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
    sublabel: 'No signals across any data source',
    badge:    'bg-green-100 text-green-800',
    bar:      'bg-green-500',
  },
  low:      {
    label:    'Low flood signal',
    sublabel: 'Statutory overlay only — no observed events on record',
    badge:    'bg-yellow-100 text-yellow-800',
    bar:      'bg-yellow-400',
  },
  moderate: {
    label:    'Moderate flood signal',
    sublabel: 'One or more data sources indicate past or potential inundation',
    badge:    'bg-orange-100 text-orange-800',
    bar:      'bg-orange-500',
  },
  elevated: {
    label:    'Elevated flood signal',
    sublabel: 'Multiple independent sources converge on flood exposure',
    badge:    'bg-red-100 text-red-800',
    bar:      'bg-red-500',
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/flood', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
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
  };

  return (
    <div className="mb-8">
      <h1 className="text-2xl font-bold text-gray-900">Flood Data Summary</h1>
      <p className="mt-1.5 text-sm text-gray-500">
        Cross-references NSW EPI statutory flood overlays, Copernicus EMS observed events,
        40-year Landsat water history, and BOM river gauge data for any NSW address.
        Indicative only — not a substitute for a formal Section 10.7 flood certificate.
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
          {state === 'running' ? 'Checking...' : 'Run Flood Check'}
        </button>
      </form>

      {state === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Querying flood data sources...</p>
          <p className="text-xs text-gray-400 mt-1">EPI overlay · Copernicus EMS · JRC 40yr history · BOM gauge. Allow 15–30 seconds.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && result && (
        <>
          <FloodCard result={result} />
          {result.report_id ? (
            <PaywallGate
              tool="flood-truth"
              reportId={result.report_id}
              address={result.address}
              price={49}
              alarmHeadline={
                result.outputs.flood_signal && result.outputs.flood_signal !== 'none'
                  ? `${FLOOD_SIGNAL_META[result.outputs.flood_signal]?.label ?? 'Flood signal'} detected at this address`
                  : result.outputs.epi_flood_class && result.outputs.epi_flood_class !== 'none'
                  ? `${EPI_CLASS_META[result.outputs.epi_flood_class]?.label ?? 'Flood planning area'} confirmed at this address`
                  : 'Flood check complete — get the verified PDF for your records'
              }
              alarmDetail={
                result.outputs.flood_signal && result.outputs.flood_signal !== 'none'
                  ? `Your lender, insurer, and conveyancer will ask for exact ARI flood depths — 1-in-20, 1-in-100, and 1-in-500 year. This report answers that question.`
                  : `The full report includes ARI depths, historical flood events, BOM gauge data, and source citations — ready to share with your conveyancer.`
              }
              previewItems={[
                'ARI flood depths at 1-in-20, 1-in-100, and 1-in-500 year return periods',
                'Access risk — whether the access road is also affected',
                'Historical flood events at this address (2011–2025)',
                'Comparison to LGA average flood depth at same ARI band',
                'Nearest flood study reference + DPIE source link',
                'Printable PDF with full data source citations and dates',
              ]}
            />
          ) : null}
          <ToolCrossSell currentTool="flood-truth" address={result.address} />
        </>
      )}
    </div>
  );
}

function FloodCard({ result }: { result: FloodResult }) {
  const o = result.outputs;
  const signal     = o.flood_signal ?? 'none';
  const signalMeta = FLOOD_SIGNAL_META[signal] ?? FLOOD_SIGNAL_META.none;
  const epiClass   = o.epi_flood_class ?? 'none';
  const epiMeta    = EPI_CLASS_META[epiClass] ?? { label: epiClass, color: 'bg-gray-50 text-gray-700' };
  const sourceCount = (result.data_sources ?? []).length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">

      {/* Header — flood signal as primary indicator */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="font-semibold text-gray-900">{result.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">Run {result.run_date} · {sourceCount} data sources</p>
          </div>
          <span className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full ${signalMeta.badge}`}>
            {signalMeta.label}
          </span>
        </div>
        <p className="text-xs text-gray-500">{signalMeta.sublabel}</p>
        <p className="text-xs text-gray-400 mt-1">
          Data convergence indicator across {sourceCount} independent sources.
          A formal Section 10.7 certificate from council is required for legal flood status.
        </p>
      </div>

      {/* Free tier: council overlay badge only — depth, history, gauge hidden behind paywall */}
      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Council flood overlay</p>
          <p className={`inline-block text-sm font-medium px-2 py-0.5 rounded ${epiMeta.color} mb-1`}>
            {epiMeta.label}
          </p>
          <p className="text-xs text-gray-400">
            NSW EPI Flood WFS · data as at {o.data_currency !== 'unknown' ? o.data_currency : 'date unavailable'}
          </p>
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Data sources checked</p>
          <p className="text-sm font-medium text-gray-900">{sourceCount} independent sources</p>
          <p className="text-xs text-gray-400 mt-1">EPI overlay · Copernicus EMS · JRC 40yr history · BOM gauge · Sentinel-1 SAR</p>
        </div>
      </div>

      {/* Warnings — always shown */}
      {(o.s1_gap_warning || result.warnings?.length) && (
        <div className="px-6 py-4 bg-amber-50 space-y-1">
          {o.s1_gap_warning && <p className="text-xs text-amber-800">{o.s1_gap_warning}</p>}
          {result.warnings?.map((w, i) => (
            <p key={i} className="text-xs text-amber-800">{w}</p>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-4">
        <p className="text-xs text-gray-400">
          Sources: {(result.data_sources ?? []).join(' · ')}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Indicative only. Not a substitute for a formal Section 10.7 flood certificate.
          Consult council or a qualified flood engineer for development or conveyancing decisions.
        </p>
      </div>
    </div>
  );
}
