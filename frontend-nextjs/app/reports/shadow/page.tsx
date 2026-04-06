'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface ShadowScenario {
  scenario: string;
  label: string;
  date: string;
  time_local: string;
  shadow_length_m: number;
  shadow_direction_deg: number;
  overlaps_subject_lot: boolean;
}

interface ShadowOutputs {
  height_m: number;
  scenarios: ShadowScenario[];
  construction_change_score: number | null;
  construction_change_detected: boolean;
  adg_compliant: boolean;
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
  warnings?: string[];
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const SCENARIO_LABELS: Record<string, string> = {
  jun21_9am: '21 Jun — 9:00 am',
  jun21_12pm: '21 Jun — 12:00 pm',
  jun21_3pm: '21 Jun — 3:00 pm',
  sep21_12pm: '21 Sep — 12:00 pm',
  dec21_12pm: '21 Dec — 12:00 pm',
};

export default function ShadowPage() {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<ShadowResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setState('running');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/shadow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });

      const json = await res.json();

      if (!res.ok) {
        throw new Error(json.error || 'Shadow analysis failed');
      }

      setResult(json);
      setState('complete');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(msg);
      setState('error');
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Construction Shadow Detector</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Model shadow cast by a maximum-permissible building on an adjacent lot across the five ADG solar access scenarios.
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
          {state === 'running' ? 'Analysing...' : 'Analyse'}
        </button>
      </form>

      {state === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Running shadow model across 5 ADG scenarios...</p>
          <p className="text-xs text-gray-400 mt-1">This takes 15–30 seconds.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && result && <ShadowCard result={result} />}
    </div>
  );
}

function ShadowCard({ result }: { result: ShadowResult }) {
  const o = result.outputs;
  const adgColor = o.adg_compliant ? 'text-green-700 bg-green-100' : 'text-red-700 bg-red-100';

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{result.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">Run {result.run_date}</p>
          </div>
          <span className={`shrink-0 text-xs font-medium px-2 py-1 rounded-full ${adgColor}`}>
            {o.adg_compliant ? 'ADG compliant' : 'ADG concern'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Max building height assumed</p>
          <p className="text-xl font-semibold text-gray-900">{o.height_m} m</p>
          <p className="text-xs text-gray-400 mt-1">From LEP height limit</p>
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Construction activity</p>
          <p className="text-xl font-semibold text-gray-900">
            {o.construction_change_detected ? 'Detected' : 'None detected'}
          </p>
          {o.construction_change_score != null && (
            <p className="text-xs text-gray-400 mt-1">
              Change score: {o.construction_change_score.toFixed(3)}
            </p>
          )}
        </div>
      </div>

      <div className="p-6">
        <p className="text-sm font-medium text-gray-700 mb-4">ADG Solar Access Scenarios</p>
        <div className="space-y-2">
          {o.scenarios.map((s) => (
            <div
              key={s.scenario}
              className="flex items-center justify-between text-sm py-2 border-b border-gray-50 last:border-0"
            >
              <span className="text-gray-600">{SCENARIO_LABELS[s.scenario] ?? s.scenario}</span>
              <div className="flex items-center gap-3 text-right">
                <span className="text-gray-500 text-xs">{s.shadow_length_m.toFixed(1)} m</span>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    s.overlaps_subject_lot
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {s.overlaps_subject_lot ? 'Overlaps lot' : 'Clear'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="px-6 py-4">
        <p className="text-xs text-gray-400">
          Data sources: {result.data_sources.join(' · ')}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Shadow direction verified for Southern Hemisphere (Sydney lat). Indicative only.
        </p>
      </div>
    </div>
  );
}
