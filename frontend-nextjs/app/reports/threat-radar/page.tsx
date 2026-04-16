'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface Application {
  PlanningPortalApplicationNumber?: string;
  ApplicationNumber?: string;
  ApplicationType?: string;
  DevelopmentType?: string;
  ApplicationDescription?: string;
  LodgementDate?: string;
  Status?: string;
  _distance_m?: number;
}

interface SearchResult {
  address: string;
  prop_id: string;
  lat: number;
  lng: number;
  council_name: string;
  applications: Application[];
  window_days: number;
  radius_m: number;
}

type PageState = 'idle' | 'searching' | 'results' | 'subscribing' | 'subscribed' | 'error';

export default function ThreatRadarPage() {
  const [address, setAddress] = useState('');
  const [email, setEmail] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setState('searching');
    setSearchResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/threat-radar/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: address.trim() }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Search failed');
      setSearchResult(json);
      setState('results');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !searchResult) return;

    setState('subscribing');
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/threat-radar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: searchResult.address,
          email: email.trim(),
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Subscription failed');
      setState('subscribed');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('results');
    }
  };

  const reset = () => {
    setState('idle');
    setSearchResult(null);
    setAddress('');
    setEmail('');
    setErrorMsg('');
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Neighbour Development Threat Radar</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          See current DA and CDC activity within 200 metres of any NSW property. Subscribe for weekly email alerts when new applications are lodged.
        </p>
      </div>

      {/* Step 1 — address search */}
      {(state === 'idle' || state === 'searching' || state === 'error') && (
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Property address
            </label>
            <AddressAutocomplete
              value={address}
              onChange={setAddress}
              onSelect={(addr) => setAddress(addr)}
              placeholder="e.g. 16 O'Connor St Haberfield NSW 2045"
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              disabled={state === 'searching'}
            />
          </div>

          {state === 'error' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={state === 'searching' || !address.trim()}
            className="w-full py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {state === 'searching' ? 'Searching...' : 'Check nearby applications'}
          </button>

          <p className="text-xs text-gray-400 text-center">
            DA and CDC data sourced from NSW ePlanning Portal. Last 90 days shown.
          </p>
        </form>
      )}

      {/* Step 2 — results + subscription offer */}
      {(state === 'results' || state === 'subscribing') && searchResult && (
        <div className="space-y-6">
          {/* Results header */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">{searchResult.address}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {searchResult.council_name} · within {searchResult.radius_m}m · last {searchResult.window_days} days
              </p>
            </div>
            <button onClick={reset} className="text-xs text-teal-600 hover:text-teal-700 underline">
              New search
            </button>
          </div>

          {/* Applications list */}
          {searchResult.applications.length === 0 ? (
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center">
              <p className="text-sm font-medium text-gray-700">No applications found</p>
              <p className="text-xs text-gray-500 mt-1">
                No DA or CDC applications were lodged within {searchResult.radius_m}m of this address in the last {searchResult.window_days} days.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">
                {searchResult.applications.length} application{searchResult.applications.length !== 1 ? 's' : ''} found nearby
              </p>
              {searchResult.applications.map((app, i) => {
                const appNum = app.PlanningPortalApplicationNumber ?? app.ApplicationNumber ?? '—';
                const type = app.ApplicationType ?? app.DevelopmentType ?? 'DA';
                const desc = app.ApplicationDescription ?? '—';
                const lodged = app.LodgementDate
                  ? new Date(app.LodgementDate).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
                  : '—';
                return (
                  <div key={i} className="border border-gray-200 rounded-xl p-4 bg-white">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{appNum}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{type}</p>
                      </div>
                      {app._distance_m != null && (
                        <span className="shrink-0 text-xs bg-amber-50 text-amber-700 border border-amber-200 rounded-full px-2 py-0.5">
                          {app._distance_m}m away
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 mt-2">{desc}</p>
                    <div className="flex gap-4 mt-2">
                      <span className="text-xs text-gray-400">Lodged {lodged}</span>
                      {app.Status && (
                        <span className="text-xs text-gray-400">{app.Status}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Subscribe offer */}
          <div className="border border-teal-200 bg-teal-50 rounded-xl p-5">
            <p className="text-sm font-medium text-teal-900 mb-1">Get weekly alerts for new applications</p>
            <p className="text-xs text-teal-700 mb-3">
              We check every Monday and email you when new DAs or CDCs are lodged within 200m.
            </p>
            <form onSubmit={handleSubscribe} className="flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="flex-1 px-3 py-2 rounded-lg border border-teal-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent bg-white"
                disabled={state === 'subscribing'}
                required
              />
              <button
                type="submit"
                disabled={state === 'subscribing' || !email.trim()}
                className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {state === 'subscribing' ? 'Subscribing...' : 'Subscribe'}
              </button>
            </form>
            {state === 'results' && errorMsg && (
              <p className="text-xs text-red-600 mt-2">{errorMsg}</p>
            )}
          </div>
        </div>
      )}

      {/* Subscribed confirmation */}
      {state === 'subscribed' && searchResult && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6">
          <p className="font-medium text-green-800 mb-1">Subscribed</p>
          <p className="text-sm text-green-700">
            You will receive weekly alerts at <strong>{email}</strong> for new development activity within 200m of{' '}
            <strong>{searchResult.address}</strong>.
          </p>
          <p className="text-xs text-gray-500 mt-3">
            Checks run every Monday 7:00 am AEST. Data sourced from NSW ePlanning Portal.
          </p>
          <button
            onClick={reset}
            className="mt-4 text-sm text-teal-600 hover:text-teal-700 underline"
          >
            Check another address
          </button>
        </div>
      )}
    </div>
  );
}
