'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface DetectResult {
  detect_id: string;
  address: string;
  lot_area_m2: number | null;
  sepp_eligible: boolean;
  sepp_ineligible_reason: string | null;
  confirmation_required: boolean;
}

type PageState = 'idle' | 'loading' | 'result' | 'error';

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

export default function CanIBuildItPage() {
  const [address, setAddress] = useState('');
  const [pageState, setPageState] = useState<PageState>('idle');
  const [result, setResult] = useState<DetectResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [email, setEmail] = useState('');
  const [emailSubmitted, setEmailSubmitted] = useState(false);

  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setPageState('loading');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/canibuildit/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Check failed');
      setResult(json as DetectResult);
      setPageState('result');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong');
      setPageState('error');
    }
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !result) return;
    // Store lead — table will be created before launch
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          address: result.address,
          eligible: result.sepp_eligible,
        }),
      });
    } catch {
      // Silent — don't block UX on lead capture failure
    }
    setEmailSubmitted(true);
  };

  const handleReset = () => {
    setAddress('');
    setPageState('idle');
    setResult(null);
    setErrorMsg('');
    setEmail('');
    setEmailSubmitted(false);
  };

  return (
    <div className="max-w-2xl mx-auto px-6">
      {/* Hero */}
      <div className="pt-16 pb-10 text-center">
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight leading-tight">
          Can I build a granny flat?
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

      {/* Loading */}
      {pageState === 'loading' && (
        <div className="mt-10 text-center">
          <div className="inline-flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5 text-teal-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            <span className="text-base">Checking planning rules for {address}…</span>
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

      {/* Result */}
      {pageState === 'result' && result && (
        <div className="mt-6 space-y-5">
          {/* Eligibility card */}
          <div
            className={`rounded-2xl border-2 p-8 text-center ${
              result.sepp_eligible
                ? 'border-teal-200 bg-teal-50'
                : 'border-amber-200 bg-amber-50'
            }`}
          >
            <div className={`text-5xl mb-4`}>{result.sepp_eligible ? '✓' : '✗'}</div>
            <h2
              className={`text-2xl font-bold mb-2 ${
                result.sepp_eligible ? 'text-teal-800' : 'text-amber-800'
              }`}
            >
              {result.sepp_eligible
                ? 'Your lot qualifies'
                : 'Your lot does not qualify'}
            </h2>
            <p className={`text-base ${result.sepp_eligible ? 'text-teal-700' : 'text-amber-700'}`}>
              {result.sepp_eligible
                ? `${formatLotArea(result.lot_area_m2)} — meets the SEPP Housing 2021 minimum lot area for a secondary dwelling`
                : deriveIneligibleReason(result.sepp_ineligible_reason, result.lot_area_m2)}
            </p>
            {result.lot_area_m2 != null && (
              <p className="mt-2 text-sm font-medium text-gray-500">
                Lot area: {formatLotArea(result.lot_area_m2)}
                {!result.sepp_eligible && result.lot_area_m2 < 450 && (
                  <span className="ml-2 text-amber-600">(min. 450 m² required)</span>
                )}
              </p>
            )}
            <p className="mt-3 text-xs text-gray-400">{result.address}</p>
          </div>

          {/* What next */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="font-semibold text-gray-900 mb-1">
              {result.sepp_eligible ? 'Get the full feasibility report' : 'What are your options?'}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              {result.sepp_eligible
                ? 'Includes buildable envelope, estimated weekly rent, build cost estimate, and CDC pathway assessment.'
                : 'A full report shows other development options for your lot — CDC, alterations, or subdivision potential.'}
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
                Got it — we'll be in touch when the full report is ready.
              </p>
            )}
          </div>

          {/* What else to check — ineligible only */}
          {!result.sepp_eligible && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Other things to check on this property</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <a
                  href="/reports/threat-radar"
                  className="group flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 group-hover:text-teal-700 transition-colors">Nearby development activity</p>
                    <p className="text-xs text-gray-400 mt-0.5">See DAs and CDCs lodged within 200m</p>
                  </div>
                </a>
                <a
                  href="/reports/shadow"
                  className="group flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 group-hover:text-teal-700 transition-colors">Shadow risk from neighbours</p>
                    <p className="text-xs text-gray-400 mt-0.5">Model future shadow from a max-height northern build</p>
                  </div>
                </a>
                <a
                  href="/reports/solar-yield"
                  className="group flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 group-hover:text-teal-700 transition-colors">Rooftop solar potential</p>
                    <p className="text-xs text-gray-400 mt-0.5">Estimate annual kWh yield from aerial imagery</p>
                  </div>
                </a>
                <a
                  href="/reports/flood"
                  className="group flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 group-hover:text-teal-700 transition-colors">Flood history</p>
                    <p className="text-xs text-gray-400 mt-0.5">SAR satellite flood detection + NSW statutory overlays</p>
                  </div>
                </a>
              </div>
            </div>
          )}

          {/* Disclaimer */}
          <p className="text-xs text-gray-400 text-center px-4">
            This check covers SEPP Housing 2021 lot area eligibility only. Additional DCP setback,
            heritage, and flood controls may apply. Not legal advice.
          </p>

          <button onClick={handleReset} className="w-full py-2.5 text-sm text-gray-400 hover:text-gray-600 transition-colors">
            Check another address
          </button>
        </div>
      )}

      {/* Social proof / trust signals */}
      {pageState === 'idle' && (
        <div className="mt-12 pt-10 border-t border-gray-100">
          <p className="text-center text-sm text-gray-400 mb-6">What we check</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {[
              { label: 'Lot area', detail: 'Min. 450 m² under SEPP Housing 2021' },
              { label: 'Zoning', detail: 'R1, R2, R3, RU5 and permitted residential' },
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
