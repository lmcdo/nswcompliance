'use client';

import { useState } from 'react';

interface PaywallGateProps {
  tool: 'flood-truth' | 'shadow' | 'solar-yield';
  reportId: string;
  address: string;
  /** Price in AUD, displayed on the CTA. */
  price: number;
  /** Short alarming headline driven by actual result data. */
  alarmHeadline: string;
  /** Supporting detail sentence. */
  alarmDetail: string;
  /** Bullet list of what the paid report contains. */
  previewItems: string[];
}

const TOOL_LABELS: Record<PaywallGateProps['tool'], string> = {
  'flood-truth':  'Flood Truth Report',
  'shadow':       'Shadow Analysis Report',
  'solar-yield':  'Solar Yield Report',
};

const CHECKOUT_PATHS: Record<PaywallGateProps['tool'], string> = {
  'flood-truth': '/api/stripe/checkout/flood-truth',
  'shadow':      '/api/stripe/checkout/shadow',
  'solar-yield': '/api/stripe/checkout/solar-yield',
};

export function PaywallGate({
  tool,
  reportId,
  address,
  price,
  alarmHeadline,
  alarmDetail,
  previewItems,
}: PaywallGateProps) {
  const [email, setEmail]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed || !trimmed.includes('@')) {
      setError('Enter a valid email address.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch(CHECKOUT_PATHS[tool], {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId, email: trimmed }),
      });
      const json = await res.json();
      if (!res.ok || !json.checkout_url) {
        throw new Error(json.error || 'Could not start checkout');
      }
      window.location.href = json.checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoading(false);
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">

      {/* Alarm band */}
      <div className="bg-amber-50 border-b border-amber-100 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900 leading-snug">{alarmHeadline}</p>
        <p className="text-xs text-amber-700 mt-1 leading-relaxed">{alarmDetail}</p>
      </div>

      {/* Blurred preview */}
      <div className="relative bg-white px-5 pt-4 pb-0">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
          What&rsquo;s in the {TOOL_LABELS[tool]}
        </p>
        <ul className="space-y-2">
          {previewItems.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
              <svg className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              {item}
            </li>
          ))}
        </ul>
        {/* Blur overlay on bottom half */}
        <div
          className="absolute bottom-0 left-0 right-0 h-20 pointer-events-none"
          style={{ background: 'linear-gradient(to bottom, transparent, white)' }}
        />
      </div>

      {/* CTA */}
      <div className="bg-white px-5 pb-5 pt-3">
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="Your email — report delivered here"
            className="w-full px-3.5 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            disabled={loading}
            autoComplete="email"
          />
          <button
            type="submit"
            disabled={loading || !email.trim()}
            className="w-full py-2.5 px-4 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Starting checkout…
              </>
            ) : (
              <>
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                </svg>
                Get full report &mdash; ${price}
              </>
            )}
          </button>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <p className="text-xs text-gray-400 text-center">
            Paid once. PDF delivered to your email. {address && `For: ${address}`}
          </p>
        </form>
      </div>
    </div>
  );
}
