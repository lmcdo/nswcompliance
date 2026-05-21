'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { PostResultEmailStrip } from '@/components/reports/PostResultEmailStrip';
import { WaitlistButton } from '@/components/reports/WaitlistButton';
import { DATA_PROVENANCE } from '@/lib/disclaimers';
import { DownloadPdfButton } from '@/components/reports/DownloadPdfButton';
import { posthog } from '@/components/providers/PostHogProvider';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';

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

interface LgaStats {
  total_applications: number;
  approval_rate: number | null;
  avg_determination_days: number | null;
  total_construction_value: number;
  top_development_types: { type: string; count: number }[];
  period_months: number;
}

interface SearchResult {
  address: string;
  prop_id: string;
  lat: number;
  lng: number;
  run_date?: string;
  council_name: string | null;
  applications: Application[];
  window_days: number;
  report_token?: string;
  lga_stats?: LgaStats | null;
}

type SearchState = 'idle' | 'searching' | 'done' | 'error';


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
    if (status.includes('approved') || (status.includes('determined') && !status.includes('undetermined'))) approvedCount++;

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

  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [searchError, setSearchError] = useState('');


  const runCheck = useCallback(async (addr: string) => {
    if (!addr.trim()) return;
    setSearchState('searching');
    setSearchResult(null);
    setSearchError('');

    posthog?.capture('threat_radar_search', {
      address: addr,
      lga_slug: lgaSlug,
      source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
      embed_ref: embedRef ?? null,
    });

    try {
      const res = await fetch('/api/satellite/threat-radar/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr.trim() }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Search failed');
      setSearchResult(json);
      setSearchState('done');
      posthog?.capture('threat_radar_search_complete', {
        address: addr,
        lga_slug: lgaSlug,
        application_count: json.applications?.length ?? 0,
        council_name: json.council_name,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setSearchError(msg);
      setSearchState('error');
      posthog?.capture('threat_radar_search_error', { address: addr, lga_slug: lgaSlug, error: msg });
    }
  }, [embedRef, lgaSlug]);

  useEffect(() => {
    const handler = (e: Event) => {
      const addr = (e as CustomEvent).detail?.address;
      if (addr) {
        setAddress(addr);
        runCheck(addr);
      }
    };
    window.addEventListener('landing-search', handler);
    return () => window.removeEventListener('landing-search', handler);
  }, [runCheck]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const addrParam = params.get('address')?.trim();
    if (addrParam) {
      setAddress(addrParam);
      runCheck(addrParam);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [runCheck]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    runCheck(address);
  };

  const reset = () => {
    setSearchState('idle');
    setSearchResult(null);
    setAddress('');
    setEmail('');
    setSearchError('');
    window.dispatchEvent(new CustomEvent('landing-reset'));
  };

  return (
    <div>
      <div className="space-y-6">
        {/* Address + search */}
        {searchState === 'idle' || searchState === 'error' ? (
          <form id="tool-input" onSubmit={handleSearch} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Property address</label>
              <AddressAutocomplete
                value={address}
                onChange={setAddress}
                onSelect={(addr) => setAddress(addr)}
                placeholder="e.g. 16 O'Connor St Haberfield NSW 2045"
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>
            <button
              type="submit"
              disabled={!address.trim()}
              className="w-full py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Check nearby applications
            </button>
            {searchState === 'error' && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">{searchError}</div>
            )}
          </form>
        ) : (
          <div className="mb-2">
            <p className="text-sm text-gray-500">{address}</p>
            <button
              type="button"
              onClick={reset}
              className="text-sm text-teal-600 hover:text-teal-700 font-medium mt-1"
            >
              Search new address
            </button>
          </div>
        )}

        {/* Results */}
        {searchState === 'done' && searchResult && (
          <SearchResults
            result={searchResult}
            onReset={reset}
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
            <ToolCrossSell currentTool="threat-radar" address={address} />
          </>
        )}

        {/* Waitlist — payments not yet available */}
        <div className="border border-teal-200 bg-teal-50 rounded-xl p-5">
          <p className="text-sm font-medium text-teal-900 mb-1">Weekly DA monitoring — coming soon</p>
          <p className="text-xs text-teal-700 mb-3">
            Get emailed every Monday when new DAs or CDCs are lodged within 200m of this address. Join the waitlist to be first in line.
          </p>
          <WaitlistButton interestType="threat-radar" address={address} label="Join waitlist" />
        </div>

        <p className="text-xs text-gray-400 text-center">
          {DATA_PROVENANCE.threat_radar}
        </p>
      </div>
    </div>
  );
}


const sevColor = { green: 'bg-green-500', amber: 'bg-amber-400', red: 'bg-red-500' };

// ---------------------------------------------------------------------------
// ThreatFindings — findings + detail pattern
// ---------------------------------------------------------------------------

function ThreatFindings({ stats, apps }: { stats: Stats; apps: Application[] }) {
  const findings: { label: string; value: string; detail: string; severity: 'green' | 'amber' | 'red' }[] = [];

  // Development pressure
  if (stats.pressureScore >= 8) {
    findings.push({
      label: 'Development pressure index',
      value: `${stats.pressureLabel} pressure — ${stats.pressureScore}/10`,
      detail: 'Very high development activity near your property. Multiple applications close by with significant dwelling numbers. Construction noise, traffic disruption, and changes to street character are common in areas with this level of activity.',
      severity: 'red',
    });
  } else if (stats.pressureScore >= 5) {
    findings.push({
      label: 'Development pressure index',
      value: `${stats.pressureLabel} pressure — ${stats.pressureScore}/10`,
      detail: 'Significant development activity in your area. Several applications are in progress nearby. Worth monitoring — new buildings can affect parking, sunlight, and street amenity.',
      severity: 'amber',
    });
  } else if (stats.pressureScore >= 3) {
    findings.push({
      label: 'Development pressure index',
      value: `${stats.pressureLabel} pressure — ${stats.pressureScore}/10`,
      detail: 'Some development activity nearby, but nothing unusual for a suburban area. Keep an eye on any applications within 100m of your property.',
      severity: 'amber',
    });
  } else {
    findings.push({
      label: 'Development pressure index',
      value: `${stats.pressureLabel} pressure — ${stats.pressureScore}/10`,
      detail: 'Minimal development activity near your property. Your neighbourhood is relatively quiet right now.',
      severity: 'green',
    });
  }

  // Application count + value
  findings.push({
    label: 'NSW ePlanning Portal — DA/CDC search (500m radius)',
    value: `${stats.totalApps} application${stats.totalApps !== 1 ? 's' : ''} — ${formatCost(stats.totalCost) ?? '$0'} total construction value`,
    detail: stats.totalCost > 5000000
      ? 'Substantial construction investment near you. High-value applications often mean larger buildings, longer construction timelines, and more impact on neighbours.'
      : stats.totalCost > 1000000
      ? 'Moderate construction investment. A mix of residential and commercial works is typical for this level of activity.'
      : 'Relatively low construction value. Most applications are likely minor renovations or additions.',
    severity: stats.totalCost > 5000000 ? 'red' : stats.totalCost > 1000000 ? 'amber' : 'green',
  });

  // Net dwelling change
  if (stats.newDwellings > 0 || stats.demolishedDwellings > 0) {
    const sign = stats.netDwellingChange >= 0 ? '+' : '';
    findings.push({
      label: 'Dwelling density analysis',
      value: `${sign}${stats.netDwellingChange} net dwellings within 500m`,
      detail: stats.netDwellingChange > 10
        ? `${stats.newDwellings} new dwellings proposed${stats.demolishedDwellings > 0 ? `, ${stats.demolishedDwellings} being demolished` : ''}. Your neighbourhood is densifying significantly. Areas with this level of new housing typically experience increased traffic, parking pressure, and shadow/privacy impacts.`
        : stats.netDwellingChange > 0
        ? `${stats.newDwellings} new dwellings proposed${stats.demolishedDwellings > 0 ? `, ${stats.demolishedDwellings} being demolished` : ''}. Moderate densification — typical for established suburbs with good transport links.`
        : `${stats.demolishedDwellings} dwellings being demolished, ${stats.newDwellings} being built. The neighbourhood composition is changing.`,
      severity: stats.netDwellingChange > 10 ? 'red' : stats.netDwellingChange > 0 ? 'amber' : 'green',
    });
  }

  // EPI variations
  if (stats.epiVariationCount > 0) {
    findings.push({
      label: 'Environmental Planning Instrument variations',
      value: `${stats.epiVariationCount} application${stats.epiVariationCount !== 1 ? 's' : ''} seeking to vary planning rules`,
      detail: 'These applications request exceptions to height limits, setbacks, or floor space ratios. If approved, they may set precedents that future applicants can cite. Affected neighbours have a right to make submissions during the public notification period.',
      severity: 'red',
    });
  }

  // What's being built
  const devEntries = Object.entries(stats.devTypeBreakdown).sort((a, b) => b[1] - a[1]);
  if (devEntries.length > 0) {
    const topTypes = devEntries.slice(0, 3).map(([type, count]) => `${count} ${type}`).join(', ');
    const hasMultiDwelling = devEntries.some(([type]) =>
      type.toLowerCase().includes('multi') || type.toLowerCase().includes('residential flat')
    );
    findings.push({
      label: 'Development type breakdown',
      value: topTypes,
      detail: hasMultiDwelling
        ? 'Multi-dwelling and apartment projects are in the mix. These tend to have the biggest impact on neighbours — shadow, overlooking, traffic, and parking.'
        : 'Mostly single-dwelling or minor works. Impact on your property is likely to be limited unless an application is directly adjacent.',
      severity: hasMultiDwelling ? 'amber' : 'green',
    });
  }

  // Close applications
  const closeApps = apps.filter(a => (a._distance_m ?? 999) < 100);
  if (closeApps.length > 0) {
    findings.push({
      label: 'Proximity alert',
      value: `${closeApps.length} application${closeApps.length !== 1 ? 's' : ''} within 100m of your property`,
      detail: 'Applications this close can directly affect your sunlight, privacy, noise levels, and street parking. You have the right to lodge an objection during the public exhibition period — check the individual DA details below.',
      severity: 'red',
    });
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 mb-3">
      <div className="divide-y divide-gray-50">
        {findings.map(({ label, value, detail, severity }) => (
          <div key={label} className="px-5 py-4">
            <div className="flex items-center gap-2.5 mb-1">
              <span className={`shrink-0 w-2.5 h-2.5 rounded-full ${sevColor[severity]}`} />
              <span className="text-sm font-medium text-gray-900">{value}</span>
            </div>
            <p className="text-xs text-gray-500 ml-5 leading-relaxed">{detail}</p>
            <p className="text-[11px] text-gray-400 ml-5 mt-1">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function FreePaidComparison({ free, paid }: { free: string[]; paid: string[] }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Included free</p>
          <ul className="space-y-2">
            {free.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-gray-700">
                <span className="shrink-0 mt-0.5 w-4 h-4 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-[10px] font-bold">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">In paid report</p>
          <ul className="space-y-2">
            {paid.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-gray-500">
                <span className="shrink-0 mt-0.5 w-4 h-4 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center text-[10px]">🔒</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
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
              <title>{app.PlanningPortalApplicationNumber ?? 'App'} — {app._distance_m ?? '?'}m</title>
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

function MonitorPreviewCard() {
  return (
    <div className="rounded-xl border border-teal-200 bg-teal-50 p-5 space-y-3" data-testid="monitor-preview-card">
      <div>
        <p className="text-sm font-semibold text-teal-900">
          Weekly DA monitoring — coming soon
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

      <WaitlistButton interestType="threat-radar" label="Join waitlist" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// SearchResults — intelligence dashboard
// ---------------------------------------------------------------------------

function SearchResults({
  result,
  onReset,
}: {
  result: SearchResult;
  onReset: () => void;
}) {
  const apps = result.applications ?? [];
  const stats = useMemo(() => computeStats(apps), [apps]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          {result.council_name ?? 'Unknown LGA'} · last {result.window_days} days
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
          {/* Findings */}
          <ThreatFindings stats={stats} apps={apps} />

          {/* LGA-wide stats */}
          {result.lga_stats && (
            <LgaStatsPanel stats={result.lga_stats} councilName={result.council_name} />
          )}

          {/* Interactive map + analytics links — prominent placement */}
          <CrossLinks lat={result.lat} lng={result.lng} councilName={result.council_name} />

          <FreePaidComparison
            free={[
              'Development pressure score',
              'Application count + construction value',
              'Net dwelling change analysis',
              'EPI variation warnings',
              'All DA and CDC details',
              'Proximity map',
              'LGA-wide approval rate and trends',
            ]}
            paid={[
              'Weekly new DA/CDC email alerts',
              'Monitoring within 200m of your address',
              'Notified when new applications lodge nearby',
              'Cancel anytime — $9.99/month',
            ]}
          />
          <MiniProximityMap centerLat={result.lat} centerLng={result.lng} apps={apps} />

          {apps.map((app, i) => {
            const appNum = app.PlanningPortalApplicationNumber ?? app.ApplicationNumber ?? '—';
            const type = app.ApplicationType ?? app.DevelopmentType ?? 'DA';
            const lodged = formatDate(app.LodgementDate);
            const determined = formatDate(app.DeterminationDate);
            const cost = formatCost(app.CostOfDevelopment);
            const dwellings = app.NumberOfNewDwellings != null && Number(app.NumberOfNewDwellings) > 0
              ? Number(app.NumberOfNewDwellings)
              : null;

            return (
              <div
                key={i}
                className="border border-gray-200 rounded-xl p-4 bg-white space-y-2"
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

                {app.ApplicationDescription && (
                  <p className="text-sm text-gray-700">{app.ApplicationDescription}</p>
                )}

                {app.PropertyAddress && (
                  <p className="text-xs text-gray-500">{app.PropertyAddress}</p>
                )}

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

                {appNum !== '—' && (
                  <a
                    href={`https://www.planningportal.nsw.gov.au/map?search=${encodeURIComponent(appNum)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block text-xs text-teal-600 hover:text-teal-700 hover:underline"
                  >
                    View on Planning Portal →
                  </a>
                )}
              </div>
            );
          })}
          {/* Subscribe CTA after all results */}
          <MonitorPreviewCard />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// LgaStatsPanel — LGA-wide aggregate stats
// ---------------------------------------------------------------------------

function LgaStatsPanel({ stats, councilName }: { stats: LgaStats; councilName: string | null }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        {councilName ?? 'LGA'} — last {stats.period_months} months (DAs only)
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-400">Total applications</p>
          <p className="text-lg font-semibold text-gray-900">{stats.total_applications.toLocaleString('en-AU')}</p>
        </div>
        {stats.approval_rate != null && (
          <div>
            <p className="text-xs text-gray-400">Approval rate</p>
            <p className="text-lg font-semibold text-gray-900">{stats.approval_rate}%</p>
          </div>
        )}
        {stats.avg_determination_days != null && (
          <div>
            <p className="text-xs text-gray-400">Avg determination</p>
            <p className="text-lg font-semibold text-gray-900">{stats.avg_determination_days} days</p>
          </div>
        )}
        {stats.total_construction_value > 0 && (
          <div>
            <p className="text-xs text-gray-400">Total construction</p>
            <p className="text-lg font-semibold text-gray-900">
              {stats.total_construction_value >= 1_000_000
                ? `$${(stats.total_construction_value / 1_000_000).toFixed(1)}M`
                : `$${Math.round(stats.total_construction_value / 1_000).toLocaleString('en-AU')}K`}
            </p>
          </div>
        )}
      </div>
      {stats.top_development_types.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 mb-2">Most common development types</p>
          <div className="flex flex-wrap gap-1.5">
            {stats.top_development_types.map(({ type, count }) => (
              <span key={type} className="text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">
                {type} ({count})
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CrossLinks — map + charts
// ---------------------------------------------------------------------------

function CrossLinks({ lat, lng, councilName }: { lat: number; lng: number; councilName: string | null }) {
  return (
    <div className="space-y-2">
      <a
        href={`https://map.plotdetect.com.au?lat=${lat}&lng=${lng}&zoom=16`}
        target="_blank"
        rel="noopener noreferrer"
        className="block rounded-xl border-2 border-teal-300 bg-teal-50 px-5 py-4 hover:bg-teal-100 hover:border-teal-400 transition-colors"
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-teal-900">
              Explore on interactive map
            </p>
            <p className="text-xs text-teal-700 mt-0.5">
              Pan, zoom, filter by cost, keywords, and development type — every DA and CDC in {councilName ?? 'your area'}
            </p>
          </div>
          <span className="shrink-0 text-teal-600 text-lg font-bold">→</span>
        </div>
      </a>
      <a
        href="https://charts.plotdetect.com.au"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-between gap-3 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3 hover:bg-indigo-100 transition-colors"
      >
        <div>
          <p className="text-sm font-medium text-indigo-900">
            See LGA trends and analytics
          </p>
          <p className="text-xs text-indigo-700 mt-0.5">
            Cost trends, approval rates, and development type breakdowns for {councilName ?? 'your area'}
          </p>
        </div>
        <span className="shrink-0 text-indigo-600 text-base">→</span>
      </a>
    </div>
  );
}
