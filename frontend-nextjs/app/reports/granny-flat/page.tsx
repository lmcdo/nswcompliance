'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface DetectedStructure {
  index: number;
  area_m2: number | null;
  bbox_pixel: number[];
  matched_prompt: string;
  is_main_dwelling: boolean;
}

interface DetectResult {
  detect_id: string;
  address: string;
  lat: number;
  lng: number;
  prop_id: string;
  lot_area_m2: number | null;
  sepp_eligible: boolean;
  sepp_ineligible_reason: string | null;
  detected_structures: DetectedStructure[];
  samgeo_structure_count: number;
  samgeo_validated: boolean;
  confirmation_required: boolean;
  tile_licence: string;
}

interface ConfirmResult {
  report_id: string;
  address: string;
  granny_flat_buildable: boolean;
  max_floor_area_m2: number;
  estimated_weekly_rent_aud: number | null;
  rental_yield_annual_pct: number | null;
  assumed_build_cost_aud: number | null;
  confidence: string;
  confidence_reason: string;
  data_sources: string[];
  warnings: string[];
}

type PageState = 'idle' | 'detecting' | 'confirming' | 'complete' | 'error';

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence (pre-validation)',
};

export default function GrannyFlatPage() {
  const [address, setAddress] = useState('');
  const [postcode, setPostcode] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [detectResult, setDetectResult] = useState<DetectResult | null>(null);
  const [confirmedCount, setConfirmedCount] = useState(1);
  const [finalResult, setFinalResult] = useState<ConfirmResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleDetect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setState('detecting');
    setDetectResult(null);
    setFinalResult(null);
    setErrorMsg('');

    try {
      // Step 1: enqueue detect job (returns immediately with jobId)
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, action: 'detect' }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Detection failed');

      const jobId: string = json.jobId;

      // Step 2: poll until detect result is written to DB
      const poll = async (): Promise<void> => {
        const pollRes = await fetch(`/api/satellite/granny-flat?jobId=${jobId}`);
        const pollJson = await pollRes.json();

        if (pollJson.status === 'detected') {
          const detectData = pollJson.data;
          setDetectResult(detectData);
          if (detectData.samgeo_validated && detectData.detected_structures?.length > 0) {
            setConfirmedCount(detectData.detected_structures.length);
          } else {
            setConfirmedCount(1);
          }
          setState('confirming');
          return;
        }

        // Still pending — try again in 2s
        await new Promise((r) => setTimeout(r, 2000));
        return poll();
      };

      await poll();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detectResult) return;

    setState('detecting'); // reuse spinner
    setFinalResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: detectResult.address,
          action: 'confirm',
          detect_id: detectResult.detect_id,
          confirmed_structure_count: confirmedCount,
          samgeo_structure_count: detectResult.samgeo_structure_count,
          postcode: postcode.trim() || null,
        }),
      });

      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Calculation failed');

      setFinalResult(json);
      setState('complete');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  const isRunning = state === 'detecting';

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Granny Flat Yield Predictor</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Detect existing structures from aerial imagery, calculate the buildable envelope under SEPP Housing 2021, and estimate weekly rental yield.
        </p>
      </div>

      {/* Step 1: address entry */}
      {(state === 'idle' || state === 'error') && (
        <form onSubmit={handleDetect} className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Property address</label>
            <AddressAutocomplete
              value={address}
              onChange={setAddress}
              onSelect={(addr) => setAddress(addr)}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              disabled={isRunning}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Postcode <span className="text-gray-400 font-normal">(for rent estimate)</span>
            </label>
            <input
              type="text"
              value={postcode}
              onChange={(e) => setPostcode(e.target.value)}
              placeholder="e.g. 2040"
              maxLength={4}
              className="w-40 px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              disabled={isRunning}
            />
          </div>

          {state === 'error' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={isRunning || !address.trim()}
            className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Detect structures
          </button>
        </form>
      )}

      {/* Loading */}
      {state === 'detecting' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Fetching aerial imagery and detecting structures...</p>
          <p className="text-xs text-gray-400 mt-1">This takes 15–30 seconds.</p>
        </div>
      )}

      {/* Step 2: confirmation */}
      {state === 'confirming' && detectResult && (
        <ConfirmationPanel
          detectResult={detectResult}
          confirmedCount={confirmedCount}
          onCountChange={setConfirmedCount}
          onConfirm={handleConfirm}
          onBack={() => { setState('idle'); setDetectResult(null); }}
        />
      )}

      {/* Step 3: result */}
      {state === 'complete' && finalResult && (
        <ResultCard result={finalResult} onReset={() => { setState('idle'); setDetectResult(null); setFinalResult(null); setAddress(''); }} />
      )}
    </div>
  );
}

function ConfirmationPanel({
  detectResult,
  confirmedCount,
  onCountChange,
  onConfirm,
  onBack,
}: {
  detectResult: DetectResult;
  confirmedCount: number;
  onCountChange: (n: number) => void;
  onConfirm: (e: React.FormEvent) => void;
  onBack: () => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div className="p-6">
        <h2 className="font-semibold text-gray-900">{detectResult.address}</h2>
        {detectResult.lot_area_m2 != null && (
          <p className="text-sm text-gray-500 mt-0.5">
            Lot area: {detectResult.lot_area_m2.toLocaleString('en-AU', { maximumFractionDigits: 0 })} m²
          </p>
        )}
        {!detectResult.sepp_eligible && detectResult.sepp_ineligible_reason && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
            {detectResult.sepp_ineligible_reason}
          </div>
        )}
      </div>

      <div className="p-6">
        {!detectResult.samgeo_validated ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 mb-4">
            Aerial detection is in pre-validation mode. Please verify the structure count manually using the SIX Maps viewer before proceeding.
          </div>
        ) : detectResult.detected_structures.length > 0 ? (
          <div className="mb-4">
            <p className="text-sm font-medium text-gray-700 mb-2">
              {detectResult.detected_structures.length} structure{detectResult.detected_structures.length !== 1 ? 's' : ''} detected on lot
            </p>
            <div className="space-y-1">
              {detectResult.detected_structures.map((s) => (
                <div key={s.index} className="flex items-center gap-2 text-xs text-gray-600">
                  <span className="w-2 h-2 rounded-full bg-teal-400 shrink-0" />
                  {s.is_main_dwelling ? 'Main dwelling' : `Structure ${s.index + 1}`}
                  {s.area_m2 != null && ` — ~${s.area_m2} m²`}
                  <span className="text-gray-400 capitalize">({s.matched_prompt})</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500 mb-4">No structures detected — enter count manually.</p>
        )}

        <form onSubmit={onConfirm} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmed number of structures on lot
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={confirmedCount}
              onChange={(e) => onCountChange(parseInt(e.target.value, 10) || 1)}
              className="w-24 px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
            <p className="text-xs text-gray-400 mt-1">
              Count all roofed structures: main dwelling, garage, shed, any secondary dwelling.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
            >
              Calculate yield
            </button>
            <button
              type="button"
              onClick={onBack}
              className="px-5 py-2.5 bg-white text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Back
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ResultCard({ result, onReset }: { result: ConfirmResult; onReset: () => void }) {
  const weeklyRent = result.estimated_weekly_rent_aud;
  const annualRent = weeklyRent ? weeklyRent * 52 : null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{result.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {CONFIDENCE_LABEL[result.confidence] ?? result.confidence}
            </p>
            {result.confidence_reason && (
              <p className="text-xs text-gray-500 mt-1 max-w-sm">{result.confidence_reason}</p>
            )}
          </div>
          <span
            className={`shrink-0 text-xs font-medium px-2 py-1 rounded-full ${
              result.granny_flat_buildable
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {result.granny_flat_buildable ? 'Eligible under SEPP' : 'Not eligible'}
          </span>
        </div>
      </div>

      {result.granny_flat_buildable && (
        <div className="grid grid-cols-3 divide-x divide-gray-100">
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Max floor area</p>
            <p className="text-lg font-semibold text-gray-900">{result.max_floor_area_m2} m²</p>
          </div>
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Est. weekly rent</p>
            <p className="text-lg font-semibold text-gray-900">
              {weeklyRent ? `$${weeklyRent.toLocaleString('en-AU', { maximumFractionDigits: 0 })}/wk` : 'N/A'}
            </p>
          </div>
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Yield on build cost</p>
            <p className="text-lg font-semibold text-gray-900">
              {result.rental_yield_annual_pct ? `${result.rental_yield_annual_pct}%` : 'N/A'}
            </p>
            {result.assumed_build_cost_aud && (
              <p className="text-xs text-gray-400 mt-0.5">
                On ${result.assumed_build_cost_aud.toLocaleString('en-AU')} build cost
              </p>
            )}
          </div>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div className="px-6 py-4 bg-amber-50 space-y-1">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-800">{w}</p>
          ))}
        </div>
      )}

      <div className="px-6 py-4 flex items-center justify-between">
        <p className="text-xs text-gray-400">
          Data: {result.data_sources.join(' · ')}
        </p>
        <button
          onClick={onReset}
          className="text-xs text-teal-600 hover:text-teal-700 underline"
        >
          New address
        </button>
      </div>
    </div>
  );
}
