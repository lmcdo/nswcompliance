'use client';

import { useState, useEffect, useRef } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface SolarYieldOutputs {
  max_panels: number;
  max_panel_area_m2: number;
  annual_kwh_estimate: number;
  sunshine_hours_per_year: number;
  best_pitch_deg: number;
  best_azimuth_deg: number;
  roof_area_m2: number;
  is_heritage: boolean;
  imagery_date: string;
  coverage_available: boolean;
}

interface ReportData {
  product: string;
  address: string;
  lat: number;
  lng: number;
  run_date: string;
  outputs: SolarYieldOutputs;
  confidence: string;
  data_sources: string[];
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 60_000;

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence',
  pending: 'Processing...',
};

function azimuthLabel(deg: number): string {
  if (deg >= 337.5 || deg < 22.5) return 'N';
  if (deg < 67.5) return 'NE';
  if (deg < 112.5) return 'E';
  if (deg < 157.5) return 'SE';
  if (deg < 202.5) return 'S';
  if (deg < 247.5) return 'SW';
  if (deg < 292.5) return 'W';
  return 'NW';
}

export default function SolarYieldPage() {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [report, setReport] = useState<ReportData | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    pollRef.current = null;
    timeoutRef.current = null;
  };

  useEffect(() => () => stopPolling(), []);

  const poll = (jobId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/satellite/solar-yield?jobId=${jobId}`);
        const json = await res.json();
        if (json.status === 'complete') {
          stopPolling();
          setReport(json.data);
          setState('complete');
        }
      } catch {
        // silently retry
      }
    }, POLL_INTERVAL_MS);

    timeoutRef.current = setTimeout(() => {
      stopPolling();
      setErrorMsg('The report timed out. Try again.');
      setState('error');
    }, POLL_TIMEOUT_MS);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    stopPolling();
    setState('running');
    setReport(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/solar-yield', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });

      const json = await res.json();

      if (!res.ok) {
        throw new Error(json.error || 'Failed to start report');
      }

      poll(json.jobId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(msg);
      setState('error');
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Solar Potential Assessment</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Roof area, orientation, maximum panel capacity, and estimated annual yield for any NSW address.
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
          {state === 'running' ? 'Running...' : 'Run Report'}
        </button>
      </form>

      {state === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Analysing roof geometry...</p>
          <p className="text-xs text-gray-400 mt-1">Usually takes 5–10 seconds.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && report && (
        <ReportCard report={report} />
      )}
    </div>
  );
}

function ReportCard({ report }: { report: ReportData }) {
  const o = report.outputs;

  if (!o.coverage_available) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <p className="font-medium text-gray-800 mb-1">No coverage available</p>
        <p className="text-sm text-gray-500">
          Google Solar data is not yet available for this address. Try a nearby address or check back later.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{report.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Run {report.run_date} &middot; {CONFIDENCE_LABEL[report.confidence] ?? report.confidence}
              {o.imagery_date !== 'unknown' && ` · Imagery ${o.imagery_date}`}
            </p>
          </div>
          {o.is_heritage && (
            <span className="shrink-0 text-xs font-medium px-2 py-1 bg-amber-100 text-amber-800 rounded-full">
              Heritage area
            </span>
          )}
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <Metric
          label="Annual solar potential"
          value={`${o.annual_kwh_estimate.toLocaleString()} kWh/yr`}
          note="Maximum capacity, all usable roof area"
        />
        <Metric
          label="Maximum panel capacity"
          value={`${o.max_panels} panels`}
          note={`${o.max_panel_area_m2} m² usable area`}
        />
      </div>

      {/* Roof details */}
      <div className="p-6 grid grid-cols-4 gap-4 text-sm">
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Total roof area</p>
          <p className="font-medium text-gray-800">{o.roof_area_m2} m²</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Best pitch</p>
          <p className="font-medium text-gray-800">{o.best_pitch_deg}°</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Best orientation</p>
          <p className="font-medium text-gray-800">
            {azimuthLabel(o.best_azimuth_deg)} ({o.best_azimuth_deg}°)
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Sunshine hours</p>
          <p className="font-medium text-gray-800">{o.sunshine_hours_per_year.toLocaleString()} hr/yr</p>
        </div>
      </div>

      {/* Heritage warning */}
      {o.is_heritage && (
        <div className="px-6 py-4 bg-amber-50 text-xs text-amber-800 rounded-b-xl">
          This property is in a Heritage Conservation Area or has a heritage listing. Solar panel installations may require heritage approval. Confirm with your council before proceeding.
        </div>
      )}

      {/* Data sources */}
      <div className="px-6 py-4">
        <p className="text-xs text-gray-400">
          Data sources: {report.data_sources.join(' · ')}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Solar potential only — does not indicate whether panels are currently installed. Not a substitute for a professional energy assessment.
        </p>
      </div>
    </div>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="p-6">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-xl font-semibold text-gray-900">{value}</p>
      <p className="text-xs text-gray-400 mt-1">{note}</p>
    </div>
  );
}
