'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface SolarYieldOutputs {
  has_panels: boolean;
  panel_area_m2: number;
  roof_material: string;
  tilt_deg: number;
  azimuth_deg: number;
  annual_kwh_estimate: number;
  is_heritage: boolean;
  tile_date: string;
  panel_count: number;
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

const MATERIAL_LABELS: Record<string, string> = {
  colorbond_dark: 'Colorbond (dark)',
  colorbond_light: 'Colorbond (light)',
  terracotta: 'Terracotta tile',
  concrete_tile: 'Concrete tile',
  flat: 'Flat membrane',
  unknown: 'Unknown',
};

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence (pre-validation)',
  pending: 'Processing...',
};

export default function SolarYieldPage() {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [report, setReport] = useState<ReportData | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

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
        throw new Error(json.error || 'Failed to run report');
      }

      setReport(json);
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
        <h1 className="text-2xl font-bold text-gray-900">Rooftop Solar Yield Underwriter</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Detect existing panels, estimate usable roof area, and calculate annual kWh yield from NSW SIX Maps 10cm aerial imagery.
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
          <p className="text-sm font-medium text-gray-700">Fetching aerial imagery and running analysis...</p>
          <p className="text-xs text-gray-400 mt-1">This takes 30–60 seconds.</p>
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

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{report.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Run {report.run_date} &middot; {CONFIDENCE_LABEL[report.confidence] ?? report.confidence}
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
          label="Annual yield estimate"
          value={o.annual_kwh_estimate > 0 ? `${o.annual_kwh_estimate.toLocaleString()} kWh/yr` : 'N/A'}
          note={o.annual_kwh_estimate > 0 ? 'Based on detected panel area and PVGIS irradiance data' : 'No panels detected'}
        />
        <Metric
          label="Existing solar panels"
          value={o.has_panels ? `${o.panel_count} detected` : 'None detected'}
          note={o.has_panels ? `~${o.panel_area_m2} m² total area` : 'Based on 10cm aerial imagery'}
        />
      </div>

      {/* Roof details */}
      <div className="p-6 grid grid-cols-3 gap-4 text-sm">
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Roof material</p>
          <p className="font-medium text-gray-800">{MATERIAL_LABELS[o.roof_material] ?? o.roof_material}</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Est. tilt</p>
          <p className="font-medium text-gray-800">{o.tilt_deg}°</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Est. azimuth</p>
          <p className="font-medium text-gray-800">{o.azimuth_deg}° {o.azimuth_deg === 0 ? '(N)' : ''}</p>
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
          Indicative only. Not a substitute for a professional energy assessment.
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
