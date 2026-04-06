'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface SubscribeResult {
  subscription_id: string;
  address: string;
  message: string;
}

type PageState = 'idle' | 'running' | 'subscribed' | 'error';

export default function ThreatRadarPage() {
  const [address, setAddress] = useState('');
  const [email, setEmail] = useState('');
  const [councilName, setCouncilName] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<SubscribeResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim() || !email.trim() || !councilName.trim()) return;

    setState('running');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/threat-radar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: address.trim(),
          email: email.trim(),
          council_name: councilName.trim(),
        }),
      });

      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Subscription failed');

      setResult(json);
      setState('subscribed');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Neighbour Development Threat Radar</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Monitor nearby DA and CDC activity. Subscribe for weekly email alerts when new applications are lodged within 200 metres of your property.
        </p>
      </div>

      {state === 'subscribed' && result ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6">
          <p className="font-medium text-green-800 mb-1">Subscribed</p>
          <p className="text-sm text-green-700">
            You will receive weekly alerts at <strong>{email}</strong> for development activity within 200m of{' '}
            <strong>{result.address}</strong>.
          </p>
          <p className="text-xs text-gray-500 mt-3">
            Alerts run every Monday 7:00 am AEST. Data sourced from NSW ePlanning Portal.
          </p>
          <button
            onClick={() => { setState('idle'); setResult(null); setAddress(''); setEmail(''); setCouncilName(''); }}
            className="mt-4 text-sm text-teal-600 hover:text-teal-700 underline"
          >
            Subscribe another address
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
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
              disabled={state === 'running'}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Council name
            </label>
            <input
              type="text"
              value={councilName}
              onChange={(e) => setCouncilName(e.target.value)}
              placeholder="e.g. Inner West Council"
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              disabled={state === 'running'}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email for weekly alerts
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              disabled={state === 'running'}
              required
            />
          </div>

          {state === 'error' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={
              state === 'running' ||
              !address.trim() ||
              !email.trim() ||
              !councilName.trim()
            }
            className="w-full py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {state === 'running' ? 'Subscribing...' : 'Subscribe to weekly alerts'}
          </button>

          <p className="text-xs text-gray-400 text-center">
            DA and CDC data sourced from NSW ePlanning Portal. Checks run weekly.
          </p>
        </form>
      )}
    </div>
  );
}
