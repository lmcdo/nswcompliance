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
  lot_width_m: number | null;
  lot_depth_m: number | null;
  zone?: string | null;
  height_of_buildings: string | null;
  fsr: string | null;
  min_lot_size_m2: number | null;
  nearby_secondary_dwelling_count: number | null;
  dcp_available: boolean;
  sepp_eligible: boolean;
  sepp_ineligible_reason: string | null;
  dcp_setbacks?: Array<{
    control_type: string;
    value_min: number | null;
    value_max: number | null;
    unit: string | null;
    condition: string | null;
    applicability: string;
    source_text: string | null;
    section_ref: string | null;
  }>;
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

function deriveWhatToChange(reason: string | null, lotArea: number | null): string {
  if (lotArea != null && lotArea < 450) {
    const shortfall = Math.round(450 - lotArea);
    return `A boundary adjustment of ${shortfall} m² could unlock CDC eligibility. A DA pathway may also be available at council's discretion — a certifier or town planner can advise.`;
  }
  if (reason?.toLowerCase().includes('heritage')) {
    return 'Heritage exclusions apply to the CDC pathway only. A DA pathway remains available — contact a heritage-experienced town planner.';
  }
  if (reason?.toLowerCase().includes('flood')) {
    return 'Flood control lot exclusions apply to the CDC pathway only. A DA with a flood risk management report may still be available — consult a hydraulic engineer.';
  }
  if (reason?.toLowerCase().includes('zone') || reason?.toLowerCase().includes('zoning')) {
    return 'Zoning restrictions may be fixed unless a planning proposal is lodged. Check the applicable LEP with a town planner.';
  }
  return "A DA pathway may still be available at council's discretion — a town planner or certifier can advise on your options.";
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
// SEPP Housing 2021 — secondary dwelling CDC design standards
// Source: SEPP Housing 2021 Part 4 + Schedule 3 Subdivision 4
// These are state-wide minimums; council DCP may impose stricter controls.
// ---------------------------------------------------------------------------

const SEPP_CDC_STANDARDS = [
  { label: 'Min. lot area',    value: '450 m²',          clause: 'cl. 4.17' },
  { label: 'Max. floor area',  value: '60 m²',           clause: 'cl. 4.18' },
  { label: 'Rear setback',     value: '3 m minimum',     clause: 'Sch. 3 Subdiv. 4' },
  { label: 'Side setback',     value: '0.9 m – 1.5 m',  clause: 'Sch. 3 Subdiv. 4' },
  { label: 'Max. height',      value: '8.5 m',           clause: 'Sch. 3 Subdiv. 4' },
  { label: 'From principal dwelling', value: '3 m',      clause: 'Sch. 3 Subdiv. 4' },
] as const;

const SEPP_LEGISLATION_URL =
  'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0649';

// ---------------------------------------------------------------------------
// DCP setback control formatting helpers
// ---------------------------------------------------------------------------

function formatControlLabel(controlType: string): string {
  const labels: Record<string, string> = {
    rear_setback: 'Rear setback',
    side_setback: 'Side setback',
    front_setback: 'Front setback',
    separation_from_dwelling: 'From principal dwelling',
    height_max: 'Max. height',
    height_storeys_max: 'Max. storeys',
    floor_area_max: 'Max. floor area',
    site_coverage_max: 'Max. site coverage',
    landscaping_min: 'Min. landscaping',
    car_parking: 'Car parking',
    private_open_space: 'Private open space',
  };
  return labels[controlType] ?? controlType.replace(/_/g, ' ');
}

function formatControlValue(ctrl: {
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  applicability: string;
}): string {
  const u = ctrl.unit ?? '';
  const unitSuffix = u === 'm2' ? ' m²' : u === '%' ? '%' : u ? ` ${u}` : '';
  if (ctrl.value_min !== null && ctrl.value_max !== null) {
    return `${ctrl.value_min}${unitSuffix} – ${ctrl.value_max}${unitSuffix}`;
  }
  if (ctrl.value_min !== null) return `${ctrl.value_min}${unitSuffix} min.`;
  if (ctrl.value_max !== null) return `${ctrl.value_max}${unitSuffix} max.`;
  return 'Check with council';
}

function formatSectionRef(ref: string): string {
  // Trim to last segment after __ for display
  const parts = ref.split('__');
  const last = parts[parts.length - 1] ?? ref;
  return last.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
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
  // Yield calculator
  const [calcBuildCost, setCalcBuildCost] = useState(2500); // $/m²
  const [calcWeeklyRent, setCalcWeeklyRent] = useState(450); // $/wk
  // Share
  const [copied, setCopied] = useState(false);
  // LGA DCP interest form
  const [lgaEmail, setLgaEmail] = useState('');
  const [lgaInterestSubmitted, setLgaInterestSubmitted] = useState(false);
  const autoSubmittedRef = useRef(false);

  // Auto-submit from ?address= query param (share URL)
  useEffect(() => {
    if (autoSubmittedRef.current || typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const addrParam = params.get('address');
    if (addrParam?.trim()) {
      autoSubmittedRef.current = true;
      setAddress(addrParam.trim());
      runCheck(addrParam.trim());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleShare = () => {
    if (!eligibility || typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    url.searchParams.set('address', eligibility.address ?? address);
    url.hash = '';
    navigator.clipboard.writeText(url.toString()).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  // Step 1 — quick eligibility check (extracted so auto-submit can call it directly)
  const runCheck = async (addr: string) => {
    if (!addr.trim()) return;
    setPageState('loading');
    setEligibility(null);
    setFullDetect(null);
    setFinalResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/canibuildit/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Check failed');
      const result = json as EligibilityResult;
      setEligibility(result);
      setPageState('result');

      // Update URL so result can be shared from the address bar
      const url = new URL(window.location.href);
      url.searchParams.set('address', result.address ?? addr);
      window.history.replaceState({}, '', url.toString());

      posthog.capture('tool_run', {
        tool: 'granny-flat',
        source: lgaSlug ? 'lga_page' : 'direct',
        lga_slug: lgaSlug ?? null,
        result: result.sepp_eligible ? 'eligible' : 'ineligible',
      });

      if (result.sepp_eligible) {
        runDetect(addr);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong');
      setPageState('error');
    }
  };

  const handleCheck = (e: React.FormEvent) => {
    e.preventDefault();
    runCheck(address);
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

  const handleLgaInterest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lgaEmail.trim() || !eligibility?.lga_name) return;
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: lgaEmail.trim(),
          address: eligibility.address,
          lga_name: eligibility.lga_name,
          interest_type: 'dcp_inclusion',
        }),
      });
    } catch {
      // Silent
    }
    setLgaInterestSubmitted(true);
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
    setLgaEmail('');
    setLgaInterestSubmitted(false);
    autoSubmittedRef.current = false;
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.delete('address');
      window.history.replaceState({}, '', url.toString());
    }
  };

  return (
    <div>
      {/* Hero — only shown on standalone /canibuildit page, not LGA pages */}
      {!lgaName && (
        <div className="pt-16 pb-10 text-center">
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight leading-tight">
            Could this property earn an extra $280–$340/week?
          </h1>
          <p className="mt-4 text-lg text-gray-500 max-w-lg mx-auto">
            Free granny flat eligibility check for any NSW address — lot size, zoning, heritage, flood — plus a rental yield estimate. Takes 15 seconds.
          </p>
          <p className="mt-2 text-sm text-gray-400">Free. No account needed.</p>
        </div>
      )}

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
            Check my property →
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
                {eligibility.sepp_eligible && (
                  <p className="text-sm text-teal-700 mt-1 font-medium">Estimated rental income: $280–$340/week</p>
                )}
                <p className="text-xs text-gray-400 mt-1">{eligibility.address}</p>
              </div>
            </div>
          </div>

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
                    {
                      key: 'lot_area',
                      label: 'Lot area',
                      detail: eligibility.lot_area_m2 != null
                        ? `${Math.round(eligibility.lot_area_m2).toLocaleString()} m² (min. 450 m²)${eligibility.lot_width_m != null && eligibility.lot_depth_m != null ? ` · approx. ${eligibility.lot_width_m}m × ${eligibility.lot_depth_m}m` : ''}`
                        : 'Could not determine',
                    },
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

                {/* Nearby secondary dwelling approvals — social proof */}
                {eligibility.nearby_secondary_dwelling_count != null && eligibility.nearby_secondary_dwelling_count > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-2">
                    <span className="text-teal-600 text-sm">✓</span>
                    <p className="text-xs text-teal-700">
                      {eligibility.nearby_secondary_dwelling_count} secondary {eligibility.nearby_secondary_dwelling_count === 1 ? 'dwelling' : 'dwellings'} approved within 500m in the last 2 years
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SEPP Housing 2021 — CDC design standards */}
          {eligibility.sepp_eligible && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-baseline justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700">SEPP Housing 2021 — CDC standards</h3>
                <a
                  href={SEPP_LEGISLATION_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-teal-600 hover:underline"
                >
                  View legislation ↗
                </a>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
                {SEPP_CDC_STANDARDS.map(({ label, value, clause }) => (
                  <div key={label}>
                    <p className="text-xs text-gray-400">{label}</p>
                    <p className="text-sm font-medium text-gray-900">{value}</p>
                    <p className="text-xs text-gray-400">{clause}</p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-3">
                State-wide CDC minimums. Your council&apos;s DCP may impose stricter setback or height controls.
              </p>
            </div>
          )}

          {/* DCP setback controls — council-specific, shown when data exists */}
          {eligibility.dcp_setbacks && eligibility.dcp_setbacks.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
              <div className="flex items-baseline justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700">
                  {eligibility.lga_name ?? 'Council'} DCP controls
                </h3>
                <span className="text-xs text-amber-700 font-medium">Council-specific</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
                {eligibility.dcp_setbacks.map((ctrl, i) => (
                  <div key={i}>
                    <p className="text-xs text-gray-400">{formatControlLabel(ctrl.control_type)}</p>
                    <p className="text-sm font-medium text-gray-900">
                      {formatControlValue(ctrl)}
                    </p>
                    {ctrl.condition && (
                      <p className="text-xs text-amber-700">{ctrl.condition}</p>
                    )}
                    {ctrl.section_ref && (
                      <p className="text-xs text-gray-400 truncate" title={ctrl.section_ref}>
                        {formatSectionRef(ctrl.section_ref)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
              {eligibility.dcp_setbacks.some(c => c.applicability === 'universal_residential') && (
                <p className="text-xs text-gray-500 mt-3 border-t border-amber-200 pt-2">
                  * Universal residential controls — apply to secondary dwellings in this LGA.
                </p>
              )}
            </div>
          )}

          {/* LEP planning controls — HOB, FSR, min lot size */}
          {(eligibility.height_of_buildings || eligibility.fsr || eligibility.min_lot_size_m2) && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">LEP planning controls</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {eligibility.height_of_buildings && (
                  <div>
                    <p className="text-xs text-gray-400">Height of buildings</p>
                    <p className="text-sm font-medium text-gray-900">{eligibility.height_of_buildings}</p>
                  </div>
                )}
                {eligibility.fsr && (
                  <div>
                    <p className="text-xs text-gray-400">Floor space ratio</p>
                    <p className="text-sm font-medium text-gray-900">{eligibility.fsr}</p>
                  </div>
                )}
                {eligibility.min_lot_size_m2 && (
                  <div>
                    <p className="text-xs text-gray-400">Min. lot size (LEP)</p>
                    <p className="text-sm font-medium text-gray-900">{eligibility.min_lot_size_m2.toLocaleString()} m²</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Interactive yield calculator */}
          {(() => {
            const totalCost = calcBuildCost * 60;
            const annualRent = calcWeeklyRent * 52;
            const grossYield = (annualRent / totalCost * 100).toFixed(1);
            const payback = (totalCost / annualRent).toFixed(1);
            return (
              <div className="rounded-xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
                  {eligibility.sepp_eligible ? 'Estimated return' : 'If this lot qualified'}
                </p>
                <div className="grid grid-cols-2 gap-5 mb-5">
                  <div>
                    <label className="block text-xs text-gray-500 mb-2">Build cost per m²</label>
                    <input
                      type="range" min={1800} max={4500} step={100}
                      value={calcBuildCost}
                      onChange={(e) => setCalcBuildCost(Number(e.target.value))}
                      className="w-full accent-teal-600"
                    />
                    <span className="text-sm font-medium text-gray-700">${calcBuildCost.toLocaleString()}/m²</span>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-2">Weekly rent</label>
                    <input
                      type="range" min={250} max={750} step={25}
                      value={calcWeeklyRent}
                      onChange={(e) => setCalcWeeklyRent(Number(e.target.value))}
                      className="w-full accent-teal-600"
                    />
                    <span className="text-sm font-medium text-gray-700">${calcWeeklyRent}/wk</span>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-3 bg-gray-50 rounded-lg p-4">
                  <div>
                    <p className="text-xs text-gray-400 mb-0.5">Build cost</p>
                    <p className="text-base font-semibold text-gray-900">${(totalCost / 1000).toFixed(0)}k</p>
                    <p className="text-xs text-gray-400">60 m² CDC max</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 mb-0.5">Annual rent</p>
                    <p className="text-base font-semibold text-gray-900">${annualRent.toLocaleString()}</p>
                    <p className="text-xs text-gray-400">gross</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 mb-0.5">Gross yield</p>
                    <p className="text-base font-semibold text-teal-700">{grossYield}%</p>
                    <p className="text-xs text-gray-400">p.a.</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 mb-0.5">Payback</p>
                    <p className="text-base font-semibold text-gray-900">{payback} yrs</p>
                    <p className="text-xs text-gray-400">undiscounted</p>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-3">Illustrative only. Excludes DA/CDC fees, finance, vacancy, maintenance. Verify rent against NSW Fair Trading bond data.</p>
              </div>
            );
          })()}

          {/* Share this result */}
          <div className="flex justify-end">
            <button
              onClick={handleShare}
              className="text-xs text-gray-400 hover:text-teal-600 transition-colors px-3 py-1.5 rounded-lg border border-gray-200 hover:border-teal-200"
            >
              {copied ? 'Link copied ✓' : 'Copy shareable link'}
            </button>
          </div>

          {/* If eligible — note that full analysis is running / lead capture if ineligible */}
          {eligibility.sepp_eligible ? (
            <div className="rounded-xl border border-teal-100 bg-teal-50 p-5 text-center">
              <p className="text-sm text-teal-700 font-medium">Running full structure analysis…</p>
              <p className="text-xs text-teal-600 mt-1">Aerial imagery + SAM detection — this takes 15–30 seconds</p>
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-gray-200 bg-white p-6">
                <h3 className="font-semibold text-gray-900 mb-1">What could change this?</h3>
                <p className="text-sm text-gray-500 mb-4">
                  {deriveWhatToChange(eligibility.sepp_ineligible_reason, eligibility.lot_area_m2)}
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

          {/* LGA DCP interest — shown when this council's DCP is not yet in the database */}
          {!eligibility.dcp_available && eligibility.lga_name && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <p className="text-sm font-semibold text-gray-800 mb-1">
                DCP controls for {eligibility.lga_name} not yet available
              </p>
              <p className="text-xs text-gray-500 mb-4">
                Setback, height, and floor space controls from the local DCP are not yet in our database for this council. We&apos;re expanding coverage — register to be notified when {eligibility.lga_name} is added.
              </p>
              {!lgaInterestSubmitted ? (
                <form onSubmit={handleLgaInterest} className="flex gap-2">
                  <input
                    type="email"
                    required
                    value={lgaEmail}
                    onChange={(e) => setLgaEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors whitespace-nowrap"
                  >
                    Notify me
                  </button>
                </form>
              ) : (
                <p className="text-sm text-teal-700 font-medium">
                  Registered — we&apos;ll notify you when {eligibility.lga_name} is added.
                </p>
              )}
            </div>
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
