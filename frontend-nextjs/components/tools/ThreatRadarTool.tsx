'use client';

import React, { useState, useMemo } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { PostResultEmailStrip } from '@/components/reports/PostResultEmailStrip';
import { DownloadPdfButton } from '@/components/reports/DownloadPdfButton';
import { posthog } from '@/components/providers/PostHogProvider';

interface Application {
  PlanningPortalApplicationNumber?: string;
  ApplicationNumber?: string;
  ApplicationType?: string;
  DevelopmentType?: string;
  ApplicationDescription?: string;
  LodgementDate?: string;
  DeterminationDate?: string;
  Status?: string;
  PropertyAddress?: string;
  LotDescription?: string;
  CostOfDevelopment?: number | string;
  NumberOfNewDwellings?: number | string;
  CouncilName?: string;
  Latitude?: number | string;
  Longitude?: number | string;
  _distance_m?: number | null;
  NumberOfStoreys?: number | string | null;
  DemolitionDwellings?: number | string | null;
  SubdivisionProposedFlag?: string | null;
  EpiVariationProposedFlag?: string | null;
  AccompaniedByVpaFlag?: string | null;
  DevelopmentSubjectToSicFlag?: string | null;
  DevelopmentCategory?: string | null;
}

interface SearchResult {
  address: string;
  prop_id: string;
  lat: number;
  lng: number;
  run_date?: string;
  council_name: string;
  applications: Application[];
  window_days: number;
  report_token?: string;
}

type SearchState = 'idle' | 'searching' | 'done' | 'error';
type SubscribeState = 'idle' | 'subscribing' | 'subscribed';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso?: string) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatCost(val?: number | string) {
  if (val == null || val === '' || val === 0) return null;
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (!n || isNaN(n)) return null;
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(n);
}

/** NSW ePlanning flags are "Yes"/"No"/null strings, not booleans. "No" is truthy in JS. */
function isYesFlag(val?: string | null): boolean {
  return val?.toString().toLowerCase().startsWith('y') === true;
}

// ---------------------------------------------------------------------------
// Analytics — mirrors threat-radar-report.tsx calcPressureScore/pressureLabel
// ---------------------------------------------------------------------------

interface Stats {
  totalApps: number;
  totalCost: number;
  newDwellings: number;
  demolishedDwellings: number;
  netDwellingChange: number;
  approvedCount: number;
  approvalRate: number;
  epiVariationCount: number;
  devTypeBreakdown: Record<string, number>;
  pressureScore: number;
  pressureLabel: string;
  pressureColor: string;
}

function computeStats(apps: Application[]): Stats {
  let totalCost = 0;
  let newDwellings = 0;
  let demolishedDwellings = 0;
  let approvedCount = 0;
  let epiVariationCount = 0;
  const devTypes: Record<string, number> = {};

  // Pressure score — same algorithm as threat-radar-report.tsx:145-155
  let pressureTotal = 0;

  for (const app of apps) {
    const cost = Number(app.CostOfDevelopment) || 0;
    totalCost += cost;

    const dw = Number(app.NumberOfNewDwellings) || 0;
    newDwellings += dw;
    demolishedDwellings += Number(app.DemolitionDwellings) || 0;

    const status = (app.Status ?? '').toLowerCase();
    if (status.includes('approved') || status.includes('determined')) approvedCount++;

    if (isYesFlag(app.EpiVariationProposedFlag)) epiVariationCount++;

    const devType = app.DevelopmentType || 'Other';
    devTypes[devType] = (devTypes[devType] || 0) + 1;

    // Pressure scoring
    const base = (app._distance_m ?? 999) < 100 ? 3 : (app._distance_m ?? 999) < 250 ? 2 : 1;
    const scale = dw >= 10 ? 2 : dw >= 4 ? 1.5 : 1;
    pressureTotal += base * scale;
  }

  const pressureScore = apps.length === 0 ? 0 : Math.min(10, Math.max(1, Math.round(pressureTotal)));

  let pressureLabel: string;
  let pressureColor: string;
  if (pressureScore >= 8) { pressureLabel = 'Intense'; pressureColor = 'bg-red-500'; }
  else if (pressureScore >= 5) { pressureLabel = 'High'; pressureColor = 'bg-orange-500'; }
  else if (pressureScore >= 3) { pressureLabel = 'Moderate'; pressureColor = 'bg-yellow-500'; }
  else { pressureLabel = 'Low'; pressureColor = 'bg-green-500'; }

  return {
    totalApps: apps.length,
    totalCost,
    newDwellings,
    demolishedDwellings,
    netDwellingChange: newDwellings - demolishedDwellings,
    approvedCount,
    approvalRate: apps.length === 0 ? 0 : Math.round((approvedCount / apps.length) * 100),
    epiVariationCount,
    devTypeBreakdown: devTypes,
    pressureScore,
    pressureLabel,
    pressureColor,
  };
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ThreatRadarTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [email, setEmail] = useState('');
  const [searchState, setSearchState] = useState<SearchState>('idle');
  const [subscribeState, setSubscribeState] = useState<SubscribeState>('idle');
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [searchError, setSearchError] = useState('');
  const [subscribeError, setSubscribeError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setSearchState('searching');
    setSearchResult(null);
    setSearchError('');

    posthog?.capture('threat_radar_search', {
      address,
      lga_slug: lgaSlug,
      source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
      embed_ref: embedRef ?? null,
    });

    try {
      const res = await fetch('/api/satellite/threat-radar/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: address.trim() }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Search failed');
      setSearchResult(json);
      setSearchState('done');
      posthog?.capture('threat_radar_search_complete', {
        address,
        lga_slug: lgaSlug,
        application_count: json.applications?.length ?? 0,
        council_name: json.council_name,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setSearchError(msg);
      setSearchState('error');
      posthog?.capture('threat_radar_search_error', { address, lga_slug: lgaSlug, error: msg });
    }
  };

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !address.trim()) return;

    setSubscribeState('subscribing');
    setSubscribeError('');

    posthog?.capture('threat_radar_subscribe', { address, lga_slug: lgaSlug });

    try {
      const res = await fetch('/api/stripe/checkout/threat-radar-monitor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: address.trim(), email: email.trim() }),
      });
      const json = await res.json();
      if (!res.ok || !json.checkout_url) throw new Error(json.error || 'Checkout failed');
      window.location.href = json.checkout_url;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setSubscribeError(msg);
      setSubscribeState('idle');
    }
  };

  const reset = () => {
    setSearchState('idle');
    setSubscribeState('idle');
    setSearchResult(null);
    setAddress('');
    setEmail('');
    setSearchError('');
    setSubscribeError('');
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Neighbour Development Threat Radar</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          See current DA and CDC activity across your council area. Subscribe for weekly email alerts when new applications are lodged.
        </p>
      </div>

      <div className="space-y-6">
        {/* Address + search — hidden once results are showing */}
        {searchState !== 'done' && (
          <form onSubmit={handleSearch} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Property address</label>
              <AddressAutocomplete
                value={address}
                onChange={setAddress}
                onSelect={(addr) => setAddress(addr)}
                placeholder="e.g. 16 O'Connor St Haberfield NSW 2045"
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                disabled={searchState === 'searching'}
              />
            </div>
            <button
              type="submit"
              disabled={searchState === 'searching' || !address.trim()}
              className="w-full py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {searchState === 'searching' ? 'Searching...' : 'Check nearby applications'}
            </button>
            {searchState === 'error' && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">{searchError}</div>
            )}
          </form>
        )}

        {/* Results */}
        {searchState === 'done' && searchResult && (
          <SearchResults
            result={searchResult}
            onReset={reset}
            email={email}
            onEmailChange={setEmail}
            onSubscribe={handleSubscribe}
            subscribeState={subscribeState}
            subscribeError={subscribeError}
          />
        )}

        {/* Download PDF + email — shown only when results are available */}
        {searchState === 'done' && searchResult && (
          <>
            <DownloadPdfButton
              label="Download PDF report"
              apiPath="/api/reports/threat-radar/generate"
              reportToken={searchResult.report_token}
              data={searchResult}
            />
            <PostResultEmailStrip
              address={searchResult.address}
              product="threat-radar"
              copy="Email me this result →"
            />
          </>
        )}

        {/* Subscribe — always visible */}
        {subscribeState !== 'subscribed' ? (
          <div className="border border-teal-200 bg-teal-50 rounded-xl p-5">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-medium text-teal-900">Weekly DA monitoring — $9.99/month</p>
              <span className="text-xs font-bold text-teal-900">$9.99/mo</span>
            </div>
            <p className="text-xs text-teal-700 mb-3">
              Get emailed every Monday when new DAs or CDCs are lodged within 200m of this address. Cancel anytime.
            </p>
            <form onSubmit={handleSubscribe} className="flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="flex-1 px-3 py-2 rounded-lg border border-teal-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent bg-white"
                disabled={subscribeState === 'subscribing'}
                required
              />
              <button
                type="submit"
                disabled={subscribeState === 'subscribing' || !email.trim() || !address.trim()}
                className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {subscribeState === 'subscribing' ? 'Redirecting...' : 'Subscribe — $9.99/mo →'}
              </button>
            </form>
            {subscribeError && (
              <p className="text-xs text-red-600 mt-2">{subscribeError}</p>
            )}
          </div>
        ) : (
          <div className="bg-green-50 border border-green-200 rounded-xl p-5">
            <p className="font-medium text-green-800 mb-1">Subscribed</p>
            <p className="text-sm text-green-700">
              Weekly alerts will be sent to <strong>{email}</strong> for new applications within 200m of{' '}
              <strong>{address}</strong>.
            </p>
            <p className="text-xs text-gray-500 mt-2">Checks run every Monday 7:00 am AEST.</p>
          </div>
        )}

        <p className="text-xs text-gray-400 text-center">
          DA and CDC data sourced from NSW ePlanning Portal.
        </p>
      </div>
    </div>
  );
}

const FREE_RESULTS_LIMIT = 3;

// ---------------------------------------------------------------------------
// SummaryStatsBanner — aggregate stats above paywall
// ---------------------------------------------------------------------------

function SummaryStatsBanner({ stats }: { stats: Stats }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
      <div className="bg-gray-50 rounded-lg p-3 text-center">
        <p className="text-lg font-bold text-teal-700">{stats.totalApps}</p>
        <p className="text-xs text-gray-500">Applications</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 text-center">
        <p className="text-lg font-bold text-teal-700">{formatCost(stats.totalCost) ?? '$0'}</p>
        <p className="text-xs text-gray-500">Construction value</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 text-center">
        <p className={`text-lg font-bold ${stats.netDwellingChange >= 0 ? 'text-teal-700' : 'text-red-600'}`}>
          {stats.netDwellingChange >= 0 ? '+' : ''}{stats.netDwellingChange}
        </p>
        <p className="text-xs text-gray-500">Net dwellings</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 text-center">
        <p className="text-lg font-bold text-teal-700">{stats.approvalRate}%</p>
        <p className="text-xs text-gray-500">Approved</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 text-center col-span-2 sm:col-span-1">
        <p className="text-lg font-bold text-amber-600">{stats.epiVariationCount}</p>
        <p className="text-xs text-gray-500">EPI variations</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// DevelopmentPressureMeter — gauge bar
// ---------------------------------------------------------------------------

function DevelopmentPressureMeter({ stats }: { stats: Stats }) {
  const pct = Math.min(100, (stats.pressureScore / 10) * 100);
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-gray-700">Development Pressure</p>
        <span className="text-sm font-bold text-gray-900">{stats.pressureScore}/10 — {stats.pressureLabel}</span>
      </div>
      <div className="h-3 rounded-full bg-gray-200 overflow-hidden">
        <div className={`h-full rounded-full ${stats.pressureColor} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-400 mt-1.5">
        Based on application count, proximity, and proposed dwellings
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// NetDwellingCallout
// ---------------------------------------------------------------------------

function NetDwellingCallout({ stats }: { stats: Stats }) {
  if (stats.newDwellings === 0 && stats.demolishedDwellings === 0) return null;
  const sign = stats.netDwellingChange >= 0 ? '+' : '';
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
      <p className="text-sm text-blue-900">
        Your neighbourhood is adding <strong>{stats.newDwellings}</strong> dwelling{stats.newDwellings !== 1 ? 's' : ''}{' '}
        {stats.demolishedDwellings > 0 && (
          <>and demolishing <strong>{stats.demolishedDwellings}</strong></>
        )}{' '}
        — net <strong>{sign}{stats.netDwellingChange}</strong> homes within 500m
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// WhatsBeingBuiltBreakdown
// ---------------------------------------------------------------------------

function WhatsBeingBuiltBreakdown({ breakdown }: { breakdown: Record<string, number> }) {
  const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-medium text-gray-500 mb-1.5">What&apos;s being built</p>
      <div className="flex flex-wrap gap-2">
        {entries.map(([type, count]) => (
          <span key={type} className="bg-gray-100 rounded-full px-3 py-1 text-xs text-gray-700">
            {count} {type}
          </span>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MiniProximityMap — pure SVG, no mapping library
// ---------------------------------------------------------------------------

const MAP_SIZE = 300;
const MAP_PAD = 20;
const MIN_BBOX_SPAN = 0.002; // ~200m, prevents divide-by-zero
const MAX_MAP_DOTS = 50;

function MiniProximityMap({ centerLat, centerLng, apps }: { centerLat: number; centerLng: number; apps: Application[] }) {
  const validApps = apps
    .filter((a) => a.Latitude != null && a.Longitude != null && Number(a.Latitude) !== 0 && Number(a.Longitude) !== 0)
    .slice(0, MAX_MAP_DOTS);

  if (validApps.length === 0) return null;

  const allLats = [centerLat, ...validApps.map((a) => Number(a.Latitude))];
  const allLngs = [centerLng, ...validApps.map((a) => Number(a.Longitude))];

  let minLat = Math.min(...allLats);
  let maxLat = Math.max(...allLats);
  let minLng = Math.min(...allLngs);
  let maxLng = Math.max(...allLngs);

  // Enforce minimum span to prevent degenerate bbox
  if (maxLat - minLat < MIN_BBOX_SPAN) {
    const mid = (maxLat + minLat) / 2;
    minLat = mid - MIN_BBOX_SPAN / 2;
    maxLat = mid + MIN_BBOX_SPAN / 2;
  }
  if (maxLng - minLng < MIN_BBOX_SPAN) {
    const mid = (maxLng + minLng) / 2;
    minLng = mid - MIN_BBOX_SPAN / 2;
    maxLng = mid + MIN_BBOX_SPAN / 2;
  }

  // Add 15% padding
  const latPad = (maxLat - minLat) * 0.15;
  const lngPad = (maxLng - minLng) * 0.15;
  minLat -= latPad; maxLat += latPad;
  minLng -= lngPad; maxLng += lngPad;

  const toX = (lng: number) => MAP_PAD + ((lng - minLng) / (maxLng - minLng)) * (MAP_SIZE - 2 * MAP_PAD);
  const toY = (lat: number) => MAP_PAD + ((maxLat - lat) / (maxLat - minLat)) * (MAP_SIZE - 2 * MAP_PAD);

  const cx = toX(centerLng);
  const cy = toY(centerLat);

  // 500m radius in pixels — approximate 500m as degrees latitude
  const radiusDeg = 500 / 111320;
  const radiusPx = (radiusDeg / (maxLat - minLat)) * (MAP_SIZE - 2 * MAP_PAD);

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="text-xs font-medium text-gray-500 mb-2">Proximity map</p>
      <svg viewBox={`0 0 ${MAP_SIZE} ${MAP_SIZE}`} className="w-full max-w-[300px] mx-auto" role="img" aria-label="Proximity map showing nearby applications">
        {/* 500m radius circle */}
        <circle cx={cx} cy={cy} r={radiusPx} fill="none" stroke="#94a3b8" strokeWidth="1" strokeDasharray="4 3" opacity="0.6" />

        {/* Application dots */}
        {validApps.map((app, i) => {
          const x = toX(Number(app.Longitude));
          const y = toY(Number(app.Latitude));
          const cost = Number(app.CostOfDevelopment) || 0;
          const r = Math.max(4, Math.min(14, Math.sqrt(cost / 100000) * 2));
          const isDA = app.ApplicationType === 'DA';
          const isFree = i < FREE_RESULTS_LIMIT;
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r={r}
              fill={isDA ? '#f59e0b' : '#a855f7'}
              opacity="0.7"
              stroke="white"
              strokeWidth="1"
            >
              {isFree && (
                <title>{app.PlanningPortalApplicationNumber ?? 'App'} — {app._distance_m ?? '?'}m</title>
              )}
            </circle>
          );
        })}

        {/* Center property */}
        <circle cx={cx} cy={cy} r="7" fill="#0d9488" stroke="white" strokeWidth="2" />
        <text x={cx} y={cy - 12} textAnchor="middle" fontSize="10" fill="#0d9488" fontWeight="bold">You</text>

        {/* Legend */}
        <circle cx={MAP_SIZE - 80} cy={MAP_SIZE - 20} r="5" fill="#f59e0b" />
        <text x={MAP_SIZE - 72} y={MAP_SIZE - 16} fontSize="9" fill="#6b7280">DA</text>
        <circle cx={MAP_SIZE - 48} cy={MAP_SIZE - 20} r="5" fill="#a855f7" />
        <text x={MAP_SIZE - 40} y={MAP_SIZE - 16} fontSize="9" fill="#6b7280">CDC</text>
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ThreatBadges — colored pills for each card
// ---------------------------------------------------------------------------

function ThreatBadges({ app }: { app: Application }) {
  const badges: { label: string; cls: string }[] = [];

  if (isYesFlag(app.EpiVariationProposedFlag)) {
    badges.push({ label: 'Seeks EPI variation', cls: 'bg-amber-50 text-amber-700 border-amber-200' });
  }
  if (isYesFlag(app.AccompaniedByVpaFlag)) {
    badges.push({ label: 'VPA attached', cls: 'bg-purple-50 text-purple-700 border-purple-200' });
  }
  if (
    (app.DevelopmentCategory && app.DevelopmentCategory.toLowerCase().includes('state')) ||
    isYesFlag(app.DevelopmentSubjectToSicFlag)
  ) {
    badges.push({ label: 'State significant', cls: 'bg-red-50 text-red-700 border-red-200' });
  }
  if (isYesFlag(app.SubdivisionProposedFlag)) {
    badges.push({ label: 'Subdivision', cls: 'bg-orange-50 text-orange-700 border-orange-200' });
  }
  const storeys = Number(app.NumberOfStoreys);
  if (storeys > 0) {
    badges.push({ label: `${storeys} storey${storeys !== 1 ? 's' : ''}`, cls: 'bg-gray-100 text-gray-600 border-gray-200' });
  }
  const demo = Number(app.DemolitionDwellings);
  if (demo > 0) {
    badges.push({ label: 'Demolition', cls: 'bg-white text-red-600 border-red-300' });
  }

  if (badges.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {badges.map((b) => (
        <span key={b.label} className={`text-xs font-medium px-2 py-0.5 rounded-full border ${b.cls}`}>
          {b.label}
        </span>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MonitorPreviewCard — forward-anxiety subscription gate
// ---------------------------------------------------------------------------

function MonitorPreviewCard({
  hiddenCount,
  email,
  onEmailChange,
  onSubscribe,
  subscribeState,
  subscribeError,
}: {
  hiddenCount: number;
  email: string;
  onEmailChange: (v: string) => void;
  onSubscribe: (e: React.FormEvent) => void;
  subscribeState: SubscribeState;
  subscribeError: string;
}) {
  return (
    <div className="rounded-xl border border-teal-200 bg-teal-50 p-5 space-y-3" data-testid="monitor-preview-card">
      <div>
        <p className="text-sm font-semibold text-teal-900">
          {hiddenCount > 0
            ? `${hiddenCount} more application${hiddenCount !== 1 ? 's' : ''} below — subscribe to see all weekly updates`
            : 'What you\'d miss next week'}
        </p>
        <p className="text-xs text-teal-700 mt-1 leading-relaxed">
          New DAs are lodged every week near most addresses.
          Without alerts, you find out when the excavator arrives.
        </p>
      </div>

      {/* Mock future DA card — visual FOMO */}
      <div className="rounded-lg border border-teal-100 bg-white p-3 space-y-1.5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-gray-900 blur-sm select-none">DA/2026/8821</p>
            <p className="text-xs text-gray-500 blur-sm select-none">Multi-dwelling housing</p>
          </div>
          <span className="shrink-0 text-xs bg-amber-50 text-amber-700 border border-amber-200 rounded-full px-2 py-0.5 blur-sm select-none">
            85m away
          </span>
        </div>
        <p className="text-sm text-gray-700 blur-sm select-none">
          Demolition of existing dwelling and construction of 4-storey residential flat building
        </p>
        <div className="flex gap-4">
          <span className="text-xs text-gray-400 blur-sm select-none">Lodged next week</span>
          <span className="text-xs text-gray-400 blur-sm select-none">Cost $2,400,000</span>
        </div>
      </div>
      <p className="text-xs text-teal-600 italic">
        Example alert — real applications sent every Monday.
      </p>

      {/* Subscribe form */}
      <form onSubmit={onSubscribe} className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => onEmailChange(e.target.value)}
          placeholder="you@example.com"
          className="flex-1 px-3 py-2 rounded-lg border border-teal-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent bg-white"
          disabled={subscribeState === 'subscribing'}
          required
          data-testid="monitor-email-input"
        />
        <button
          type="submit"
          disabled={subscribeState === 'subscribing' || !email.trim()}
          className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          {subscribeState === 'subscribing' ? 'Redirecting...' : 'Subscribe — $9.99/mo →'}
        </button>
      </form>
      {subscribeError && <p className="text-xs text-red-600">{subscribeError}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SearchResults — intelligence dashboard
// ---------------------------------------------------------------------------

function SearchResults({
  result,
  onReset,
  email,
  onEmailChange,
  onSubscribe,
  subscribeState,
  subscribeError,
}: {
  result: SearchResult;
  onReset: () => void;
  email: string;
  onEmailChange: (v: string) => void;
  onSubscribe: (e: React.FormEvent) => void;
  subscribeState: SubscribeState;
  subscribeError: string;
}) {
  const apps = result.applications ?? [];
  const stats = useMemo(() => computeStats(apps), [apps]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          {result.council_name} · last {result.window_days} days
        </p>
        <button onClick={onReset} className="text-xs text-teal-600 hover:text-teal-700 underline">New search</button>
      </div>

      {apps.length === 0 ? (
        <div className="space-y-3">
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 text-center">
            <p className="text-sm font-medium text-gray-700">No applications found</p>
            <p className="text-xs text-gray-500 mt-1">
              No DA or CDC applications lodged within 500m in the last {result.window_days} days.
            </p>
          </div>
          <CrossLinks lat={result.lat} lng={result.lng} councilName={result.council_name} />
        </div>
      ) : (
        <>
          {/* Above-paywall intelligence dashboard */}
          <SummaryStatsBanner stats={stats} />
          <DevelopmentPressureMeter stats={stats} />
          <NetDwellingCallout stats={stats} />
          <WhatsBeingBuiltBreakdown breakdown={stats.devTypeBreakdown} />
          <MiniProximityMap centerLat={result.lat} centerLng={result.lng} apps={apps} />

          <p className="text-sm font-medium text-gray-700">
            {apps.length} application{apps.length !== 1 ? 's' : ''} found nearby
          </p>

          {apps.map((app, i) => {
            const appNum = app.PlanningPortalApplicationNumber ?? app.ApplicationNumber ?? '—';
            const type = app.ApplicationType ?? app.DevelopmentType ?? 'DA';
            const lodged = formatDate(app.LodgementDate);
            const determined = formatDate(app.DeterminationDate);
            const cost = formatCost(app.CostOfDevelopment);
            const dwellings = app.NumberOfNewDwellings != null && Number(app.NumberOfNewDwellings) > 0
              ? Number(app.NumberOfNewDwellings)
              : null;

            const isBlurred = i >= FREE_RESULTS_LIMIT;

            return (
              <React.Fragment key={i}>
                {/* Inject MonitorPreviewCard between result FREE_RESULTS_LIMIT-1 and FREE_RESULTS_LIMIT */}
                {i === FREE_RESULTS_LIMIT && (
                  <MonitorPreviewCard
                    hiddenCount={apps.length - FREE_RESULTS_LIMIT}
                    email={email}
                    onEmailChange={onEmailChange}
                    onSubscribe={onSubscribe}
                    subscribeState={subscribeState}
                    subscribeError={subscribeError}
                  />
                )}
                <div
                  className={`border border-gray-200 rounded-xl p-4 bg-white space-y-2${isBlurred ? ' blur-sm select-none pointer-events-none' : ''}`}
                  aria-hidden={isBlurred}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900">{appNum}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{type}</p>
                    </div>
                    {app._distance_m != null && (
                      <span className="shrink-0 text-xs bg-amber-50 text-amber-700 border border-amber-200 rounded-full px-2 py-0.5">
                        {app._distance_m}m away
                      </span>
                    )}
                  </div>

                  {/* Threat badges */}
                  <ThreatBadges app={app} />

                  {app.PropertyAddress && (
                    <p className="text-sm text-gray-700 font-medium">{app.PropertyAddress}</p>
                  )}

                  {app.ApplicationDescription ? (
                    <p className="text-sm text-gray-600">{app.ApplicationDescription}</p>
                  ) : app.DevelopmentType ? (
                    <p className="text-sm text-gray-500 italic">{app.DevelopmentType}</p>
                  ) : null}

                  <div className="flex flex-wrap gap-x-4 gap-y-1">
                    {app.Status && (
                      <span className="text-xs text-gray-600 font-medium">{app.Status}</span>
                    )}
                    {lodged && (
                      <span className="text-xs text-gray-400">Lodged {lodged}</span>
                    )}
                    {determined && (
                      <span className="text-xs text-gray-400">Determined {determined}</span>
                    )}
                    {cost && (
                      <span className="text-xs text-gray-400">Cost {cost}</span>
                    )}
                    {dwellings && (
                      <span className="text-xs text-gray-400">{dwellings} new dwelling{dwellings !== 1 ? 's' : ''}</span>
                    )}
                    {app.LotDescription && (
                      <span className="text-xs text-gray-400">{app.LotDescription}</span>
                    )}
                  </div>

                  {/* Planning Portal link — free cards only */}
                  {!isBlurred && (
                    <a
                      href="https://www.planningportal.nsw.gov.au/datracking"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block text-xs text-teal-600 hover:text-teal-700 hover:underline"
                    >
                      View on Planning Portal →
                    </a>
                  )}
                </div>
              </React.Fragment>
            );
          })}
          {/* If fewer than FREE_RESULTS_LIMIT results, show card after all results */}
          {apps.length <= FREE_RESULTS_LIMIT && (
            <MonitorPreviewCard
              hiddenCount={0}
              email={email}
              onEmailChange={onEmailChange}
              onSubscribe={onSubscribe}
              subscribeState={subscribeState}
              subscribeError={subscribeError}
            />
          )}
          <CrossLinks lat={result.lat} lng={result.lng} councilName={result.council_name} />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CrossLinks — map + charts
// ---------------------------------------------------------------------------

function CrossLinks({ lat, lng, councilName }: { lat: number; lng: number; councilName: string }) {
  return (
    <div className="space-y-2 mt-2">
      <a
        href={`https://map.plotdetect.com.au?lat=${lat}&lng=${lng}`}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 hover:bg-teal-100 transition-colors"
      >
        <div>
          <p className="text-sm font-medium text-teal-900">
            Explore the full DA map for {councilName}
          </p>
          <p className="text-xs text-teal-700 mt-0.5">
            Filter by cost, keywords, and development type · map.plotdetect.com.au
          </p>
        </div>
        <span className="shrink-0 text-teal-600 text-base">→</span>
      </a>
      <a
        href="https://charts.plotdetect.com.au"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-between gap-3 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3 hover:bg-indigo-100 transition-colors"
      >
        <div>
          <p className="text-sm font-medium text-indigo-900">
            DA analytics for {councilName}
          </p>
          <p className="text-xs text-indigo-700 mt-0.5">
            Cost trends, approval rates, and development type breakdowns · charts.plotdetect.com.au
          </p>
        </div>
        <span className="shrink-0 text-indigo-600 text-base">→</span>
      </a>
    </div>
  );
}
