'use client';

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { posthog } from '@/components/providers/PostHogProvider';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';

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

type PageState = 'idle' | 'loading' | 'result' | 'error';

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
// LockedPreviewCard — gates paid analysis with blur-to-reveal pattern
// ---------------------------------------------------------------------------

function LockedPreviewCard({
  lga_name,
  onUnlock,
  unlocking,
  email,
  onEmailChange,
}: {
  lga_name: string | null;
  onUnlock: () => void;
  unlocking: boolean;
  email: string;
  onEmailChange: (v: string) => void;
}) {
  const rows = [
    { label: 'Aerial structure analysis', preview: '1 structure detected' },
    { label: 'Your rental income estimate', preview: '$320/wk' },
    { label: 'Yield on build cost', preview: '8.7% p.a.' },
    { label: `DCP setbacks — ${lga_name ?? 'your council'}`, preview: 'front 6m · side 0.9m · rear 3m' },
    { label: 'Break-even projection', preview: 'Year 7' },
  ];
  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <div className="px-5 pt-5 pb-4 border-b border-gray-100">
        <p className="text-sm font-semibold text-gray-900">Full property analysis</p>
        <p className="text-xs text-gray-400 mt-0.5">AI satellite scan · personalised financials · council planning controls</p>
      </div>
      <div className="px-5 py-4 space-y-3">
        {rows.map(({ label, preview }) => (
          <div key={label} className="flex items-center justify-between gap-4">
            <span className="text-sm text-gray-500 shrink-0">{label}</span>
            <span className="text-sm font-medium text-gray-200 blur-sm select-none pointer-events-none" aria-hidden="true">
              {preview}
            </span>
          </div>
        ))}
      </div>
      <div className="px-5 pb-5 space-y-3">
        <input
          type="email"
          value={email}
          onChange={(e) => onEmailChange(e.target.value)}
          placeholder="your@email.com — results emailed to you"
          className="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
        <button
          onClick={onUnlock}
          disabled={unlocking || !email.trim()}
          className="w-full py-3 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-60 transition-colors"
        >
          {unlocking ? 'Starting analysis…' : 'Unlock full analysis — $49'}
        </button>
        <p className="text-xs text-gray-400 text-center">
          Results shown here and emailed · PDF included
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function GrannyFlatTool({ lgaSlug, lgaName, embedRef }: { lgaSlug?: string; lgaName?: string | null; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [pageState, setPageState] = useState<PageState>('idle');
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [email, setEmail] = useState('');
  const [emailSubmitted, setEmailSubmitted] = useState(false);
  // Yield calculator — ineligible "if this lot qualified" teaser only
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

  // Quick eligibility check (extracted so auto-submit can call it directly)
  const runCheck = async (addr: string) => {
    if (!addr.trim()) return;
    setPageState('loading');
    setEligibility(null);
    setErrorMsg('');
    setUnlocking(false);

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
        source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
        embed_ref: embedRef ?? null,
        lga_slug: lgaSlug ?? null,
        result: result.sepp_eligible ? 'eligible' : 'ineligible',
      });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong');
      setPageState('error');
    }
  };

  const handleCheck = (e: React.FormEvent) => {
    e.preventDefault();
    runCheck(address);
  };

  // Unlock — fire detect job in background, then redirect to Stripe checkout
  const handleUnlock = async () => {
    if (!eligibility || unlocking) return;
    setUnlocking(true);
    setErrorMsg('');
    try {
      const detectRes = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: eligibility.address ?? address,
          action: 'detect',
          ...(email.trim() ? { notification_email: email.trim() } : {}),
        }),
      });
      const detectJson = await detectRes.json();
      if (!detectRes.ok) throw new Error(detectJson.error ?? 'Could not start analysis');
      const jobId: string = detectJson.jobId;

      const checkoutRes = await fetch('/api/stripe/checkout/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jobId,
          address: eligibility.address ?? address,
          ...(email.trim() ? { email: email.trim() } : {}),
        }),
      });
      const checkoutJson = await checkoutRes.json();
      if (!checkoutRes.ok || !checkoutJson.checkout_url) {
        throw new Error(checkoutJson.error ?? 'Checkout failed');
      }
      window.location.href = checkoutJson.checkout_url;
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong — please try again.');
      setUnlocking(false);
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
    setPageState('idle');
    setEligibility(null);
    setErrorMsg('');
    setEmail('');
    setEmailSubmitted(false);
    setLgaEmail('');
    setLgaInterestSubmitted(false);
    setUnlocking(false);
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

      {/* Eligibility result */}
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
                  <p className="text-sm text-teal-700 mt-1 font-medium">
                    Estimated rental income: $280–$340/week
                  </p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  {address && address.toLowerCase() !== eligibility.address?.toLowerCase()
                    ? address
                    : eligibility.address}
                  {address && address.toLowerCase() !== eligibility.address?.toLowerCase() && (
                    <span className="ml-1 text-gray-300">· matched to {eligibility.address}</span>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Check another address — immediately after result */}
          <div className="text-center">
            <button onClick={handleReset} className="px-5 py-2.5 bg-white text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors">
              Check another address
            </button>
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

          {/* Eligible: LockedPreviewCard | Ineligible: yield teaser + "what to change" */}
          {eligibility.sepp_eligible ? (
            <>
              {errorMsg && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
                  <p className="text-sm text-red-700">{errorMsg}</p>
                </div>
              )}
              <LockedPreviewCard
                lga_name={eligibility.lga_name}
                onUnlock={handleUnlock}
                unlocking={unlocking}
                email={email}
                onEmailChange={setEmail}
              />
            </>
          ) : (
            <>
              {/* Interactive yield calculator — ineligible teaser ("if this lot qualified") */}
              {(() => {
                const totalCost = calcBuildCost * 60;
                const annualRent = calcWeeklyRent * 52;
                const grossYield = (annualRent / totalCost * 100).toFixed(1);
                const payback = (totalCost / annualRent).toFixed(1);
                return (
                  <div className="rounded-xl border border-gray-200 bg-white p-5">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
                      If this lot qualified
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

          {/* Share this result */}
          <div className="flex justify-end">
            <button
              onClick={handleShare}
              className="text-xs text-gray-400 hover:text-teal-600 transition-colors px-3 py-1.5 rounded-lg border border-gray-200 hover:border-teal-200"
            >
              {copied ? 'Link copied ✓' : 'Copy shareable link'}
            </button>
          </div>

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
            <p><span className="text-gray-500">Zone</span> — SEPP (Housing) 2021 cl 50, read with definition of &ldquo;residential zone&rdquo; in cl 49: R1, R2, R3, R4, R5/RU5 where dwelling houses are permissible under the applicable LEP.</p>
            <p><span className="text-gray-500">Heritage</span> — CDC pathway: SEPP (Housing) 2021 cl 54(3)(c) excludes heritage items and draft heritage items; DA pathway: {eligibility.epi_name ?? 'applicable LEP'} cl 5.10 (Standard Instrument). Heritage Map sourced from NSW Planning Portal layerintersect.</p>
            <p><span className="text-gray-500">Flood control lot</span> — SEPP (Housing) 2021 cl 58: complying development must not be carried out on flood storage areas, floodways, flow paths, high hazard areas, or high risk areas as certified by council or hydraulic engineer. Spatial data: 12 LGAs — shown as unknown outside coverage.</p>
            <p><span className="text-gray-500">Biodiversity</span> — SEPP (Exempt and Complying Development Codes) 2008 cl 1.19(1) excludes land mapped on the NSW Biodiversity Values Map (Biodiversity Conservation Act 2016). Spatial data: NSW Biodiversity Values Map (DCCEEW).</p>
            <p><span className="text-gray-500">Acid sulfate soils</span> — SEPP (Exempt and Complying Development Codes) 2008 cl 1.19(1) excludes Class 1 and Class 2 acid sulfate soils; DA pathway: {eligibility.epi_name ?? 'applicable LEP'} cl 7.1 (Standard Instrument).</p>
            <p className="pt-1 border-t border-gray-100 mt-2">DCP setback, height, floor space ratio, and landscaping controls not assessed here. This check is indicative only — verify with a qualified town planner before lodging a DA or CDC.</p>
          </div>

        </div>
      )}

      {/* Cross-sell — after result */}
      {pageState === 'result' && eligibility && (
        <ToolCrossSell currentTool="granny-flat" address={eligibility.address ?? address} />
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
