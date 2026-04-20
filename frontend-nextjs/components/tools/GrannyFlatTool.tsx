'use client';

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { posthog } from '@/components/providers/PostHogProvider';

const AerialTile = dynamic(
  () => import('@/components/reports/AerialTile').then(m => m.AerialTile),
  { ssr: false, loading: () => <div className="w-full rounded-lg bg-gray-100 animate-pulse" style={{ height: 220 }} /> }
);

type CheckResult = 'pass' | 'fail' | 'unknown';

interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

interface EligibilityResult {
  detect_id: string | null;
  address: string;
  lat: number | null;
  lng: number | null;
  lot_polygon: GeoJSONPolygon | null;
  lga_name: string | null;
  epi_name: string | null;
  lot_area_m2: number | null;
  zone?: string | null;
  sepp_eligible: boolean;
  sepp_ineligible_reason: string | null;
  confirmation_required: boolean;
  checks?: {
    lot_area: CheckResult;
    zone: CheckResult;
    heritage: CheckResult;
    flood: CheckResult;
    biodiversity: CheckResult;
    acid_sulfate: CheckResult;
  };
}

interface DetectedStructure {
  index: number;
  area_m2: number | null;
  bbox_pixel: number[];
  matched_prompt: string;
  is_main_dwelling: boolean;
}

interface FullDetectResult {
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
  tile_b64?: string;
  tile_width?: number;
  tile_height?: number;
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

type PageState = 'idle' | 'loading' | 'result' | 'detecting' | 'confirming' | 'complete' | 'error';

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence (pre-validation)',
};

function formatLotArea(m2: number | null): string {
  if (m2 == null) return 'Unknown lot area';
  return `${Math.round(m2).toLocaleString()} m²`;
}

function deriveIneligibleReason(reason: string | null, lotArea: number | null): string {
  if (reason) return reason;
  if (lotArea != null && lotArea < 450) {
    const shortfall = Math.round(450 - lotArea);
    return `Lot area ${Math.round(lotArea).toLocaleString()} m² — ${shortfall} m² short of the 450 m² minimum under SEPP Housing 2021`;
  }
  if (lotArea != null && lotArea >= 450) {
    return `Lot area ${Math.round(lotArea).toLocaleString()} m² meets the size threshold, but the property does not qualify — likely due to zoning, heritage, flood, or biodiversity exclusions`;
  }
  return 'This property does not meet SEPP Housing 2021 eligibility requirements';
}

// ---------------------------------------------------------------------------
// StructureCanvas — aerial tile with SAM detection bboxes
// ---------------------------------------------------------------------------

function StructureCanvas({
  tile_b64,
  tile_width,
  tile_height,
  structures,
  licence,
}: {
  tile_b64: string;
  tile_width: number;
  tile_height: number;
  structures: DetectedStructure[];
  licence: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || imgError) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new window.Image();
    img.onload = () => {
      const cw = canvas.width;
      const ch = canvas.height;
      if (cw <= 0 || ch <= 0) return;
      ctx.clearRect(0, 0, cw, ch);
      ctx.drawImage(img, 0, 0, cw, ch);

      const scaleX = tile_width > 0 ? cw / tile_width : 1;
      const scaleY = tile_height > 0 ? ch / tile_height : 1;

      structures.forEach((s) => {
        const [x0, y0, x1, y1] = s.bbox_pixel;
        const rx = Math.max(0, Math.min(x0 * scaleX, cw - 1));
        const ry = Math.max(0, Math.min(y0 * scaleY, ch - 1));
        const rw = Math.max(1, Math.min((x1 - x0) * scaleX, cw - rx));
        const rh = Math.max(1, Math.min((y1 - y0) * scaleY, ch - ry));
        ctx.strokeStyle = s.is_main_dwelling ? '#ef4444' : '#facc15';
        ctx.lineWidth = 2;
        ctx.strokeRect(rx, ry, rw, rh);
      });
    };
    img.onerror = () => setImgError(true);
    img.src = `data:image/png;base64,${tile_b64}`;
  }, [tile_b64, tile_width, tile_height, structures, imgError]);

  if (imgError) return null;

  return (
    <div className="mb-4">
      <canvas
        ref={canvasRef}
        width={512}
        height={512}
        className="w-full rounded-lg border border-gray-200"
        style={{ aspectRatio: '1 / 1' }}
      />
      <p className="text-xs text-gray-400 mt-1">{licence}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function GrannyFlatTool({ lgaSlug, lgaName }: { lgaSlug?: string; lgaName?: string | null }) {
  const [address, setAddress] = useState('');
  const [postcode, setPostcode] = useState('');
  const [pageState, setPageState] = useState<PageState>('idle');
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [fullDetect, setFullDetect] = useState<FullDetectResult | null>(null);
  const [confirmedCount, setConfirmedCount] = useState(1);
  const [finalResult, setFinalResult] = useState<ConfirmResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [email, setEmail] = useState('');
  const [emailSubmitted, setEmailSubmitted] = useState(false);

  // Step 1 — quick eligibility check
  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setPageState('loading');
    setEligibility(null);
    setFullDetect(null);
    setFinalResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/canibuildit/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Check failed');
      const result = json as EligibilityResult;
      setEligibility(result);
      setPageState('result');

      posthog.capture('tool_run', {
        tool: 'granny-flat',
        source: lgaSlug ? 'lga_page' : 'direct',
        lga_slug: lgaSlug ?? null,
        result: result.sepp_eligible ? 'eligible' : 'ineligible',
      });

      // If eligible, immediately kick off full detect pipeline
      if (result.sepp_eligible) {
        runDetect(address);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong');
      setPageState('error');
    }
  };

  // Step 2 — full ML detect (Railway via satellite API)
  const runDetect = async (addr: string) => {
    setPageState('detecting');
    try {
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, action: 'detect' }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Detection failed');

      const jobId: string = json.jobId;

      // Poll until detect result written to DB
      const poll = async (): Promise<void> => {
        const pollRes = await fetch(`/api/satellite/granny-flat?jobId=${jobId}`);
        const pollJson = await pollRes.json();

        if (pollJson.status === 'detected') {
          const detectData = pollJson.data as FullDetectResult;
          setFullDetect(detectData);
          setConfirmedCount(
            detectData.samgeo_validated && detectData.detected_structures?.length > 0
              ? detectData.detected_structures.length
              : 1
          );
          setPageState('confirming');
          return;
        }

        await new Promise((r) => setTimeout(r, 2000));
        return poll();
      };

      await poll();
    } catch (err: unknown) {
      // Detect failed — fall back to showing just the eligibility result
      setPageState('result');
    }
  };

  // Step 3 — confirm structure count + calculate yield
  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullDetect) return;

    setPageState('detecting');
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: fullDetect.address,
          action: 'confirm',
          detect_id: fullDetect.detect_id,
          confirmed_structure_count: confirmedCount,
          samgeo_structure_count: fullDetect.samgeo_structure_count,
          postcode: postcode.trim() || null,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Calculation failed');
      setFinalResult(json);
      setPageState('complete');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong');
      setPageState('error');
    }
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !eligibility) return;
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          address: eligibility.address,
          eligible: eligibility.sepp_eligible,
        }),
      });
    } catch {
      // Silent
    }
    setEmailSubmitted(true);
  };

  const handleReset = () => {
    setAddress('');
    setPostcode('');
    setPageState('idle');
    setEligibility(null);
    setFullDetect(null);
    setFinalResult(null);
    setErrorMsg('');
    setEmail('');
    setEmailSubmitted(false);
  };

  return (
    <div>
      {/* Hero */}
      <div className="pt-16 pb-10 text-center">
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight leading-tight">
          Can I build a granny flat?
          {lgaName && <span className="block text-2xl font-normal text-gray-500 mt-1">{lgaName}</span>}
        </h1>
        <p className="mt-4 text-lg text-gray-500 max-w-lg mx-auto">
          Instant NSW eligibility check — lot area, zoning, and planning exclusions verified against
          SEPP Housing 2021.
        </p>
        <p className="mt-2 text-sm text-gray-400">Free. No account needed.</p>
      </div>

      {/* Input form */}
      {pageState === 'idle' && (
        <form onSubmit={handleCheck} className="flex flex-col gap-3">
          {lgaName && (
            <div className="text-sm text-teal-700 bg-teal-50 rounded-lg px-4 py-2">
              Checking SEPP Housing 2021 rules for <strong>{lgaName}</strong>
            </div>
          )}
          <AddressAutocomplete
            value={address}
            onChange={setAddress}
            onSelect={(addr) => setAddress(addr)}
            placeholder="Enter a NSW property address"
            className="w-full text-base"
          />
          <button
            type="submit"
            disabled={!address.trim()}
            className="w-full py-3 px-6 bg-teal-600 text-white font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-base"
          >
            Check for free →
          </button>
        </form>
      )}

      {/* Loading — quick check */}
      {pageState === 'loading' && (
        <div className="mt-10 text-center">
          <div className="inline-flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5 text-teal-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            <span className="text-base">Checking planning rules for {address}…</span>
          </div>
          <p className="mt-3 text-sm text-gray-400">Usually takes 2–3 seconds</p>
        </div>
      )}

      {/* Loading — ML detect */}
      {pageState === 'detecting' && (
        <div className="mt-10 text-center">
          <div className="inline-flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5 text-teal-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            <span className="text-base">Fetching aerial imagery and detecting structures…</span>
          </div>
          <p className="mt-3 text-sm text-gray-400">Usually takes 15–30 seconds</p>
        </div>
      )}

      {/* Error */}
      {pageState === 'error' && (
        <div className="mt-10">
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-red-700 font-medium">{errorMsg}</p>
          </div>
          <button onClick={handleReset} className="mt-4 w-full py-2.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
            Try another address
          </button>
        </div>
      )}

      {/* Step 2 — Confirm panel (structure count) */}
      {pageState === 'confirming' && fullDetect && (
        <div className="mt-6 space-y-5">
          {/* Aerial tile with structure bboxes */}
          {fullDetect.tile_b64 && fullDetect.tile_width != null && fullDetect.tile_height != null ? (
            <StructureCanvas
              tile_b64={fullDetect.tile_b64}
              tile_width={fullDetect.tile_width}
              tile_height={fullDetect.tile_height}
              structures={fullDetect.detected_structures}
              licence={fullDetect.tile_licence}
            />
          ) : eligibility?.lat != null && eligibility?.lng != null ? (
            <div className="rounded-xl overflow-hidden border border-gray-200">
              <AerialTile lat={eligibility.lat} lng={eligibility.lng} zoom={19} height={220} lotPolygon={eligibility.lot_polygon ?? undefined} />
            </div>
          ) : null}

          <div className="rounded-xl border border-gray-200 bg-white divide-y divide-gray-100">
            <div className="p-6">
              <h2 className="font-semibold text-gray-900">{fullDetect.address}</h2>
              {fullDetect.lot_area_m2 != null && (
                <p className="text-sm text-gray-500 mt-0.5">
                  Lot area: {fullDetect.lot_area_m2.toLocaleString('en-AU', { maximumFractionDigits: 0 })} m²
                </p>
              )}
            </div>

            <div className="p-6">
              {!fullDetect.samgeo_validated ? (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 mb-4">
                  Aerial detection is in pre-validation mode. Verify the structure count manually on SIX Maps before proceeding.
                </div>
              ) : fullDetect.detected_structures.length > 0 ? (
                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    {fullDetect.detected_structures.length} structure{fullDetect.detected_structures.length !== 1 ? 's' : ''} detected on lot
                  </p>
                  <div className="space-y-1">
                    {fullDetect.detected_structures.map((s) => (
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

              <form onSubmit={handleConfirm} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confirmed number of structures on lot
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={confirmedCount}
                    onChange={(e) => setConfirmedCount(parseInt(e.target.value, 10) || 1)}
                    className="w-24 px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    Count all roofed structures: main dwelling, garage, shed, any secondary dwelling.
                  </p>
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
                    className="w-32 px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
                >
                  Calculate yield →
                </button>
              </form>
            </div>
          </div>

          <button onClick={handleReset} className="w-full py-2.5 text-sm text-gray-400 hover:text-gray-600 transition-colors">
            Check another address
          </button>
        </div>
      )}

      {/* Step 3 — Full result */}
      {pageState === 'complete' && finalResult && (
        <div className="mt-6 space-y-5">
          {eligibility?.lat != null && eligibility?.lng != null && (
            <div className="rounded-xl overflow-hidden border border-gray-200">
              <AerialTile lat={eligibility.lat} lng={eligibility.lng} zoom={19} height={220} lotPolygon={eligibility.lot_polygon ?? undefined} />
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            <div className="p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold text-gray-900">{finalResult.address}</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {CONFIDENCE_LABEL[finalResult.confidence] ?? finalResult.confidence}
                  </p>
                  {finalResult.confidence_reason && (
                    <p className="text-xs text-gray-500 mt-1 max-w-sm">{finalResult.confidence_reason}</p>
                  )}
                </div>
                <span className={`shrink-0 text-xs font-medium px-2 py-1 rounded-full ${
                  finalResult.granny_flat_buildable ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {finalResult.granny_flat_buildable ? 'Eligible under SEPP' : 'Not eligible'}
                </span>
              </div>
            </div>

            {finalResult.granny_flat_buildable && (
              <div className="grid grid-cols-3 divide-x divide-gray-100">
                <div className="p-5">
                  <p className="text-xs text-gray-400 mb-1">Max floor area</p>
                  <p className="text-lg font-semibold text-gray-900">{finalResult.max_floor_area_m2} m²</p>
                </div>
                <div className="p-5">
                  <p className="text-xs text-gray-400 mb-1">Est. weekly rent</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {finalResult.estimated_weekly_rent_aud
                      ? `$${finalResult.estimated_weekly_rent_aud.toLocaleString('en-AU', { maximumFractionDigits: 0 })}/wk`
                      : 'N/A'}
                  </p>
                </div>
                <div className="p-5">
                  <p className="text-xs text-gray-400 mb-1">Yield on build cost</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {finalResult.rental_yield_annual_pct ? `${finalResult.rental_yield_annual_pct}%` : 'N/A'}
                  </p>
                  {finalResult.assumed_build_cost_aud && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      On ${finalResult.assumed_build_cost_aud.toLocaleString('en-AU')} build cost
                    </p>
                  )}
                </div>
              </div>
            )}

            {finalResult.warnings.length > 0 && (
              <div className="px-6 py-4 bg-amber-50 space-y-1">
                {finalResult.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-amber-800">{w}</p>
                ))}
              </div>
            )}

            <div className="px-6 py-4">
              <p className="text-xs text-gray-400">Data: {finalResult.data_sources.join(' · ')}</p>
            </div>
          </div>

          <button onClick={handleReset} className="w-full py-2.5 text-sm text-gray-400 hover:text-gray-600 transition-colors">
            Check another address
          </button>
        </div>
      )}

      {/* Quick eligibility result (shown while detect is loading or if ineligible) */}
      {pageState === 'result' && eligibility && (
        <div className="mt-6 space-y-5">
          {/* Aerial tile */}
          {eligibility.lat != null && eligibility.lng != null && (
            <div className="rounded-xl overflow-hidden border border-gray-200">
              <AerialTile lat={eligibility.lat} lng={eligibility.lng} zoom={19} height={220} lotPolygon={eligibility.lot_polygon ?? undefined} />
            </div>
          )}

          {/* Eligibility card */}
          <div className={`rounded-xl border p-5 ${
            eligibility.sepp_eligible ? 'border-teal-200 bg-teal-50' : 'border-gray-200 bg-white'
          }`}>
            <div className="flex items-start gap-3">
              <span className={`mt-0.5 shrink-0 text-xs font-semibold px-2 py-1 rounded-full ${
                eligibility.sepp_eligible ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600'
              }`}>
                {eligibility.sepp_eligible ? 'Eligible' : 'Not eligible'}
              </span>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${eligibility.sepp_eligible ? 'text-teal-800' : 'text-gray-800'}`}>
                  {eligibility.sepp_eligible
                    ? `${formatLotArea(eligibility.lot_area_m2)} — meets the SEPP Housing 2021 minimum for a secondary dwelling`
                    : deriveIneligibleReason(eligibility.sepp_ineligible_reason, eligibility.lot_area_m2)}
                </p>
                <p className="text-xs text-gray-400 mt-1">{eligibility.address}</p>
              </div>
            </div>
          </div>

          {/* What you'd get — shown for ineligible lots so user understands the value */}
          {!eligibility.sepp_eligible && (
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">If this lot qualified, you&apos;d be entitled to</p>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-white rounded-lg p-3 border border-gray-100">
                  <p className="text-base font-semibold text-gray-900">60 m²</p>
                  <p className="text-xs text-gray-400 mt-0.5">Max granny flat size under SEPP Housing 2021</p>
                </div>
                <div className="bg-white rounded-lg p-3 border border-gray-100">
                  <p className="text-base font-semibold text-gray-900">~$150k</p>
                  <p className="text-xs text-gray-400 mt-0.5">Estimated build cost at $2,500/m²</p>
                </div>
                <div className="bg-white rounded-lg p-3 border border-gray-100">
                  <p className="text-base font-semibold text-gray-900">$350–550/wk</p>
                  <p className="text-xs text-gray-400 mt-0.5">Typical NSW rental range for a 1-bed secondary dwelling</p>
                </div>
              </div>
            </div>
          )}

          {/* Check breakdown */}
          {eligibility.checks && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-baseline justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700">Eligibility checks</h3>
                {eligibility.lga_name && (
                  <span className="text-xs text-gray-400">{eligibility.lga_name}</span>
                )}
              </div>
              <div className="space-y-2.5">
                {(
                  [
                    { key: 'lot_area', label: 'Lot area', detail: eligibility.lot_area_m2 != null ? `${Math.round(eligibility.lot_area_m2).toLocaleString()} m² (min. 450 m²)` : 'Could not determine' },
                    { key: 'zone', label: 'Zoning', detail: eligibility.zone ? `Zone ${eligibility.zone}` : 'Could not determine' },
                    { key: 'heritage', label: 'Heritage exclusion', detail: 'Heritage item or conservation area' },
                    { key: 'flood', label: 'Flood control lot', detail: 'Statutory flood overlay' },
                    { key: 'biodiversity', label: 'Biodiversity values', detail: 'Biodiversity values map' },
                    { key: 'acid_sulfate', label: 'Acid sulfate soils', detail: 'Class 1 & 2 soils' },
                  ] as { key: keyof NonNullable<EligibilityResult['checks']>; label: string; detail: string }[]
                ).map(({ key, label, detail }) => {
                  const status = eligibility.checks![key];
                  return (
                    <div key={key} className="flex items-center gap-3">
                      <div className="w-5 flex-shrink-0 text-center">
                        {status === 'pass' && <span className="text-teal-600 font-bold text-sm">✓</span>}
                        {status === 'fail' && <span className="text-red-500 font-bold text-sm">✗</span>}
                        {status === 'unknown' && <span className="text-gray-400 text-sm">—</span>}
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className={`text-sm font-medium ${status === 'fail' ? 'text-red-700' : status === 'pass' ? 'text-gray-800' : 'text-gray-400'}`}>{label}</span>
                        <span className="text-xs text-gray-400 ml-2">{detail}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* If eligible — note that full analysis is running / lead capture if ineligible */}
          {eligibility.sepp_eligible ? (
            <div className="rounded-xl border border-teal-100 bg-teal-50 p-5 text-center">
              <p className="text-sm text-teal-700 font-medium">Running full structure analysis…</p>
              <p className="text-xs text-teal-600 mt-1">Aerial imagery + SAM detection — this takes 15–30 seconds</p>
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-gray-200 bg-white p-6">
                <h3 className="font-semibold text-gray-900 mb-1">What are your options?</h3>
                <p className="text-sm text-gray-500 mb-4">
                  A full report shows other development options for your lot — CDC, alterations, or subdivision potential.
                </p>
                {!emailSubmitted ? (
                  <form onSubmit={handleEmailSubmit} className="flex gap-2">
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="your@email.com"
                      className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                    />
                    <button
                      type="submit"
                      className="px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors whitespace-nowrap"
                    >
                      Notify me
                    </button>
                  </form>
                ) : (
                  <p className="text-sm text-teal-700 font-medium">
                    Got it — we&apos;ll be in touch when the full report is ready.
                  </p>
                )}
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Other things to check on this property</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[
                    { href: '/reports/threat-radar', label: 'Nearby development activity', detail: 'See DAs and CDCs lodged within 200m' },
                    { href: '/reports/shadow', label: 'Shadow risk from neighbours', detail: 'Model future shadow from a max-height northern build' },
                    { href: '/reports/solar-yield', label: 'Rooftop solar potential', detail: 'Estimate annual kWh yield from aerial imagery' },
                    { href: '/reports/flood', label: 'Flood history', detail: 'SAR satellite flood detection + NSW statutory overlays' },
                  ].map(({ href, label, detail }) => (
                    <a key={href} href={href} className="group flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 group-hover:text-teal-700 transition-colors">{label}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{detail}</p>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            </>
          )}

          <div className="text-xs text-gray-400 px-2 space-y-1.5">
            <p className="font-medium text-gray-500">Legislative basis</p>
            <p><span className="text-gray-500">Lot area</span> — SEPP (Housing) 2021 cl 53(2)(a): detached secondary dwelling minimum site area 450 m² [complying development]; cl 52 [development consent].</p>
            <p><span className="text-gray-500">Zone</span> — SEPP (Housing) 2021 cl 50, read with definition of "residential zone" in cl 49: R1, R2, R3, R4, R5/RU5 where dwelling houses are permissible under the applicable LEP.</p>
            <p><span className="text-gray-500">Heritage</span> — CDC pathway: SEPP (Housing) 2021 cl 54(3)(c) excludes heritage items and draft heritage items; DA pathway: {eligibility.epi_name ?? 'applicable LEP'} cl 5.10 (Standard Instrument). Heritage Map sourced from NSW Planning Portal layerintersect.</p>
            <p><span className="text-gray-500">Flood control lot</span> — SEPP (Housing) 2021 cl 58: complying development must not be carried out on flood storage areas, floodways, flow paths, high hazard areas, or high risk areas as certified by council or hydraulic engineer. Spatial data: 12 LGAs — shown as unknown outside coverage.</p>
            <p><span className="text-gray-500">Biodiversity</span> — SEPP (Exempt and Complying Development Codes) 2008 cl 1.19(1) excludes land mapped on the NSW Biodiversity Values Map (Biodiversity Conservation Act 2016). Spatial data: NSW Biodiversity Values Map (DCCEEW).</p>
            <p><span className="text-gray-500">Acid sulfate soils</span> — SEPP (Exempt and Complying Development Codes) 2008 cl 1.19(1) excludes Class 1 and Class 2 acid sulfate soils; DA pathway: {eligibility.epi_name ?? 'applicable LEP'} cl 7.1 (Standard Instrument).</p>
            <p className="pt-1 border-t border-gray-100 mt-2">DCP setback, height, floor space ratio, and landscaping controls not assessed here. This check is indicative only — verify with a qualified town planner before lodging a DA or CDC.</p>
          </div>

          <button onClick={handleReset} className="w-full py-2.5 text-sm text-gray-400 hover:text-gray-600 transition-colors">
            Check another address
          </button>
        </div>
      )}

      {/* Social proof — idle only */}
      {pageState === 'idle' && (
        <div className="mt-12 pt-10 border-t border-gray-100">
          <p className="text-center text-sm text-gray-400 mb-6">What we check</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {[
              { label: 'Lot area', detail: 'Min. 450 m² under SEPP Housing 2021' },
              { label: 'Zoning', detail: 'R1, R2, R3, R4, R5/RU5 under SEPP Housing 2021 cl 49' },
              { label: 'Heritage exclusion', detail: 'Heritage items and conservation areas' },
              { label: 'Flood control lots', detail: 'Statutory flood overlay check' },
              { label: 'Biodiversity', detail: 'Biodiversity values map exclusions' },
              { label: 'Acid sulfate soils', detail: 'Class 1 & 2 soil exclusions' },
            ].map(({ label, detail }) => (
              <div key={label} className="rounded-lg bg-gray-50 p-4">
                <p className="text-sm font-medium text-gray-700">{label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
