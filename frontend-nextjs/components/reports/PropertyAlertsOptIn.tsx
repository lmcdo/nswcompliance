'use client';

// prior-art-checked: mirrors the components/reports/PostResultEmailStrip.tsx pattern
// and posts to the existing /api/satellite/threat-radar subscribe route — no
// alerts opt-in component exists (the flagged files are the property API + home
// PropertyProfile, unrelated to email subscription capture).

import { useState } from 'react';

interface Props {
  address: string;
  /** Optional council override — the subscribe route derives it if omitted. */
  councilName?: string;
}

/**
 * Self-contained opt-in strip for development-application alerts.
 * Posts to the existing /api/satellite/threat-radar subscribe route
 * (address -> lat/lng resolve -> threat_radar_subscriptions insert).
 * Renders after a report result; never blocks the result display.
 */
export function PropertyAlertsOptIn({ address, councilName }: Props) {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setState('submitting');
    try {
      const resp = await fetch('/api/satellite/threat-radar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address,
          email: email.trim(),
          ...(councilName ? { council_name: councilName } : {}),
        }),
      });
      if (resp.ok) {
        setState('done');
      } else {
        const data = await resp.json().catch(() => ({}));
        setMessage(data?.error ?? 'Could not set up alerts for this address.');
        setState('error');
      }
    } catch {
      setMessage('Network error — please try again.');
      setState('error');
    }
  };

  if (state === 'done') {
    return (
      <div className="mt-4 p-4 rounded-xl border border-teal-200 bg-teal-50">
        <p className="text-sm text-teal-700 font-medium">
          Done — we&apos;ll email {email} when a new development application is lodged near this address.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-4 p-4 rounded-xl border border-gray-200 bg-gray-50">
      <p className="text-sm font-medium text-gray-700 mb-1">
        Get an email when new development applications are lodged near this property
      </p>
      <p className="text-xs text-gray-500 mb-3">
        Weekly check of the NSW Planning Portal application feeds within 200 m. Unsubscribe any time.
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
        />
        <button
          type="submit"
          disabled={state === 'submitting'}
          className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors whitespace-nowrap disabled:opacity-60"
        >
          {state === 'submitting' ? 'Setting up…' : 'Alert me'}
        </button>
      </form>
      {state === 'error' && <p className="mt-2 text-xs text-red-600">{message}</p>}
    </div>
  );
}
