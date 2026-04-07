'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

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

const EPI_CLASS_META: Record<string, { label: string; color: string }> = {
  high_flood_risk:    { label: 'High flood risk',    color: 'bg-red-100 text-red-800' },
  medium_flood_risk:  { label: 'Medium flood risk',  color: 'bg-orange-100 text-orange-800' },
  low_flood_risk:     { label: 'Low flood risk',     color: 'bg-yellow-100 text-yellow-800' },
  flood_planning_area:{ label: 'Flood planning area',color: 'bg-blue-100 text-blue-800' },
  none:               { label: 'No EPI flood overlay',color: 'bg-green-100 text-green-800' },
};

const CONFIDENCE_META: Record<string, { label: string; color: string }> = {
  high:   { label: 'High confidence',   color: 'text-green-700' },
  medium: { label: 'Medium confidence', color: 'text-amber-700' },
  low:    { label: 'Low confidence',    color: 'text-gray-400' },
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
          Cross-reference Sentinel-1 SAR, Copernicus EMS, JRC 40-year water history, and BOM gauge
          data with NSW EPI statutory flood overlays for any NSW parcel.
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
          <p className="text-sm font-medium text-gray-700">Querying flood data sources...</p>
          <p className="text-xs text-gray-400 mt-1">EPI overlay · Copernicus EMS · JRC 40yr history · BOM gauge. Allow 15–30 seconds.</p>
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
  const epiMeta  = EPI_CLASS_META[epiClass] ?? { label: epiClass, color: 'bg-gray-100 text-gray-700' };
  const confMeta = CONFIDENCE_META[result.confidence] ?? { label: result.confidence, color: 'text-gray-400' };

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">

      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{result.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">Run {result.run_date}</p>
          </div>
          <div className="flex flex-col items-end gap-1.5 shrink-0">
            <span className={`text-xs font-medium px-2 py-1 rounded-full ${epiMeta.color}`}>
              {epiMeta.label}
            </span>
            <span className={`text-xs ${confMeta.color}`}>{confMeta.label}</span>
          </div>
        </div>
      </div>

      {/* Row 1: EPI + SAR */}
      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">EPI statutory overlay</p>
          <p className="text-lg font-semibold text-gray-900">
            {o.epi_flood_label ?? (epiClass === 'none' ? 'Not in flood overlay' : epiClass)}
          </p>
          <p className="text-xs text-gray-400 mt-1">NSW EPI Flood WFS</p>
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">SAR flood detection</p>
          <p className="text-lg font-semibold text-gray-900">
            {o.sar_flood_detected == null ? 'Pending' : o.sar_flood_detected ? 'Detected' : 'None detected'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {o.sar_flood_detected == null ? 'Batch analysis — check back later' : `Confidence: ${o.sar_confidence ?? 'n/a'}`}
          </p>
        </div>
      </div>

      {/* Row 2: JRC + BOM gauge */}
      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Water history (Landsat 1984–{o.jrc_data_year ?? 2021})</p>
          {o.jrc_water_occurrence_pct != null ? (
            <>
              <p className="text-lg font-semibold text-gray-900">
                {o.jrc_water_occurrence_pct.toFixed(0)}
                <span className="text-sm font-normal text-gray-500">% of months</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {o.jrc_water_occurrence_pct === 0
                  ? 'No surface water observed at this site since 1984'
                  : o.jrc_water_occurrence_pct < 5
                  ? 'Rare surface water — episodic flood events only'
                  : o.jrc_water_occurrence_pct < 25
                  ? 'Seasonal or periodic inundation'
                  : 'Frequent or permanent surface water'}
              </p>
            </>
          ) : (
            <p className="text-sm text-gray-400">Not available</p>
          )}
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Nearest river gauge</p>
          {o.bom_gauge_name ? (
            <>
              <p className="text-sm font-semibold text-gray-900 leading-snug">{o.bom_gauge_name}</p>
              <p className="text-xs text-gray-400 mt-0.5">{o.bom_gauge_distance_km} km away</p>
              {o.bom_last_major_flood_date ? (
                <p className="text-xs text-red-700 mt-2 font-medium">
                  Last major flood: {o.bom_last_major_flood_date} — {o.bom_last_major_flood_peak_m}m peak
                </p>
              ) : (
                <p className="text-xs text-gray-400 mt-2">No major flood recorded since 2020</p>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-400">No gauge within {75} km</p>
          )}
        </div>
      </div>

      {/* Copernicus EMS historical events */}
      {o.ems_flood_detected !== null && (
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-2">Recorded flood events (Copernicus EMS activations)</p>
          {!o.ems_flood_detected || !o.ems_activations?.length ? (
            <p className="text-sm text-gray-600">No recorded EMS flood events at this location</p>
          ) : (
            <ul className="space-y-2">
              {o.ems_activations.map((act) => (
                <li key={act.activation_id} className="flex items-start gap-3">
                  <span className="mt-1.5 shrink-0 w-2 h-2 rounded-full bg-red-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{act.event_name}</p>
                    <p className="text-xs text-gray-400">
                      {act.activation_id} · {act.event_date}
                      {act.flood_type === 'estimated' && ' · estimated extent'}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Warnings */}
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
          Data sources: {(result.data_sources ?? []).join(' · ')}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Indicative only. Not a substitute for a formal Section 10.7 flood certificate.
        </p>
      </div>
    </div>
  );
}
