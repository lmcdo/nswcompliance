'use client';

import { useState } from 'react';

type InterestType =
  | 'flood-truth'
  | 'solar-yield'
  | 'solar'
  | 'shadow'
  | 'threat-radar'
  | 'granny-flat'
  | 'conveyancing'
  | 'pre-da-history';

interface WaitlistButtonProps {
  /** Which product the user is interested in. */
  interestType: InterestType;
  /** Address context if available. */
  address?: string;
  /** Override the default CTA label. */
  label?: string;
  /** Additional CSS classes on the outer container. */
  className?: string;
}

/**
 * Replaces Stripe checkout buttons while payments are disabled (pre-incorporation).
 * Captures email + interest via /api/canibuildit/lead (existing endpoint with
 * rate limiting, honeypot, MX check, and duplicate detection).
 */
export function WaitlistButton({
  interestType,
  address,
  label,
  className = '',
}: WaitlistButtonProps) {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed || !trimmed.includes('@')) {
      setErrorMsg('Enter a valid email address.');
      return;
    }
    setState('submitting');
    setErrorMsg('');
    try {
      const res = await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: trimmed,
          ...(address ? { address } : {}),
          interest_type: interestType,
        }),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.error || 'Something went wrong');
      }
      setState('done');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong');
      setState('error');
    }
  };

  if (state === 'done') {
    return (
      <div className={`rounded-lg bg-teal-50 border border-teal-200 px-4 py-3 ${className}`}>
        <p className="text-sm font-medium text-teal-800">
          You're on the list. We'll email you when this report is available for purchase.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className={`space-y-2 ${className}`}>
      <div className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          disabled={state === 'submitting'}
          autoComplete="email"
        />
        <button
          type="submit"
          disabled={state === 'submitting' || !email.trim()}
          className="px-5 py-2 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          {state === 'submitting' ? 'Joining...' : (label ?? 'Join waitlist')}
        </button>
      </div>
      {errorMsg && <p className="text-xs text-red-600">{errorMsg}</p>}
      <p className="text-xs text-gray-400">
        Paid reports launching soon. Join the waitlist to be notified.
      </p>
    </form>
  );
}
