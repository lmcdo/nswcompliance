'use client';

import { useState } from 'react';
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
  _distance_m?: number | null;
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
        {/* Address + search */}
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

        {/* Results */}
        {searchState === 'done' && searchResult && (
          <SearchResults result={searchResult} onReset={reset} />
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

function SearchResults({ result, onReset }: { result: SearchResult; onReset: () => void }) {
  const apps = result.applications ?? [];

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
          <a
            href={`https://map.plotdetect.com.au?lat=${result.lat}&lng=${result.lng}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 hover:bg-teal-100 transition-colors"
          >
            <div>
              <p className="text-sm font-medium text-teal-900">
                Explore the full DA map for {result.council_name}
              </p>
              <p className="text-xs text-teal-700 mt-0.5">
                See all applications across the LGA · map.plotdetect.com.au
              </p>
            </div>
            <span className="shrink-0 text-teal-600 text-base">→</span>
          </a>
        </div>
      ) : (
        <>
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

            return (
              <div key={i} className="border border-gray-200 rounded-xl p-4 bg-white space-y-2">
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
              </div>
            );
          })}
          <a
            href={`https://map.plotdetect.com.au?lat=${result.lat}&lng=${result.lng}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 hover:bg-teal-100 transition-colors mt-2"
          >
            <div>
              <p className="text-sm font-medium text-teal-900">
                Explore the full DA map for {result.council_name}
              </p>
              <p className="text-xs text-teal-700 mt-0.5">
                Filter by cost, keywords, and development type · map.plotdetect.com.au
              </p>
            </div>
            <span className="shrink-0 text-teal-600 text-base">→</span>
          </a>
        </>
      )}
    </div>
  );
}
