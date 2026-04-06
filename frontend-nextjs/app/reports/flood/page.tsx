'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface FloodOutputs {
  epi_flood_class: string | null;
  epi_flood_label: string | null;
  sar_flood_detected: boolean | null;
  sar_confidence: string | null;
  sar_analysis_date: string | null;
  s1_gap_warning: string | null;
  data_currency: string;
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
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const EPI_CLASS_LABELS: Record<string, { label: string; color: string }> = {
  high_flood_risk: { label: 'High flood risk', color: 'bg-red-100 text-red-800' },
  medium_flood_risk: { label: 'Medium flood risk', color: 'bg-orange-100 text-orange-800' },
  low_flood_risk: { label: 'Low flood risk', color: 'bg-yellow-100 text-yellow-800' },
  flood_planning_area: { label: 'Flood planning area', color: 'bg-blue-100 text-blue-800' },
  none: { label: 'No EPI flood overlay', color: 'bg-green-100 text-green-800' },
};

export default function FloodPage() {
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
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Wet Season Flood Truth Engine</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Cross-reference Sentinel-1 SAR flood detection with NSW EPI statutory flood overlays for any NSW parcel.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3 mb-8">
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
          {state === 'running' ? 'Checking...' : 'Check Flood Risk'}
        </button>
      </form>

      {state === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Querying EPI flood overlays...</p>
          <p className="text-xs text-gray-400 mt-1">This takes 5–15 seconds.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && result && <FloodCard result={result} />}
    </div>
  );
}

function FloodCard({ result }: { result: FloodResult }) {
  const o = result.outputs;
  const epiClass = o.epi_flood_class ?? 'none';
  const epiMeta = EPI_CLASS_LABELS[epiClass] ?? { label: epiClass, color: 'bg-gray-100 text-gray-700' };

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{result.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">Run {result.run_date}</p>
          </div>
          <span className={`shrink-0 text-xs font-medium px-2 py-1 rounded-full ${epiMeta.color}`}>
            {epiMeta.label}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">EPI statutory overlay</p>
          <p className="text-lg font-semibold text-gray-900">
            {o.epi_flood_label ?? (epiClass === 'none' ? 'Not in flood overlay' : epiClass)}
          </p>
          <p className="text-xs text-gray-400 mt-1">NSW EPI Flood WFS</p>
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">SAR flood event detected</p>
          <p className="text-lg font-semibold text-gray-900">
            {o.sar_flood_detected == null
              ? 'Not available'
              : o.sar_flood_detected
              ? 'Yes'
              : 'No'}
          </p>
          {o.sar_confidence && (
            <p className="text-xs text-gray-400 mt-1">
              Confidence: {o.sar_confidence}
            </p>
          )}
        </div>
      </div>

      {(o.s1_gap_warning || (result.warnings && result.warnings.length > 0)) && (
        <div className="px-6 py-4 bg-amber-50 space-y-1">
          {o.s1_gap_warning && (
            <p className="text-xs text-amber-800">{o.s1_gap_warning}</p>
          )}
          {result.warnings?.map((w, i) => (
            <p key={i} className="text-xs text-amber-800">{w}</p>
          ))}
        </div>
      )}

      <div className="px-6 py-4">
        <p className="text-xs text-gray-400">
          Data sources: {result.data_sources.join(' · ')}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Indicative only. Not a substitute for a formal Section 10.7 flood certificate.
        </p>
      </div>
    </div>
  );
}
