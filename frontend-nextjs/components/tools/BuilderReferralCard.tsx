'use client';

// Modelled on components/reports/PostResultEmailStrip.tsx (same lead API,
// same self-contained state pattern); differs by the express consent checkbox
// + referral-fee disclosure required before contact details may be shared
// with a third party (Privacy Act / Spam Act consent basis).

import { useEffect, useState } from 'react';
import posthog from 'posthog-js';
import { trackAdsConversion } from '@/lib/gtag';

type Verdict = 'eligible' | 'needs-checking';

interface Props {
  address: string;
  lgaName: string | null;
  /** Which result this card sits under — changes the copy, never the offer. */
  verdict?: Verdict;
}

/**
 * Referral capture shown under an eligible OR a needs-checking dual-occupancy
 * result. The computed result is never altered by this card; it renders below
 * it. Submissions post to the existing lead API with a distinct interest_type
 * so referral-consented rows are separable from plain email-me rows.
 *
 * The needs-checking variant must NOT imply that a builder review will make the
 * block eligible — it offers a person to look at a property-specific issue the
 * automated map check could not resolve.
 */
export function BuilderReferralCard({ address, lgaName, verdict = 'eligible' }: Props) {
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');

  useEffect(() => {
    posthog.capture('referral_cta_view', { tool: 'upzoning-check', verdict });
  }, [verdict]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (status === 'submitting') return;
    if (!email.trim() || !consent) {
      // Surface the gate instead of a dead disabled button.
      setStatus('error');
      return;
    }
    setStatus('submitting');
    try {
      const res = await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          address,
          eligible: verdict === 'eligible',
          lga_name: lgaName,
          interest_type: 'dual-occ-referral',
        }),
      });
      // A non-2xx must NOT read as success — that silently loses the lead and
      // tells the visitor they're sorted when they aren't.
      if (!res.ok) throw new Error('request failed');
    } catch {
      setStatus('error');
      return;
    }
    posthog.capture('referral_lead_submitted', { tool: 'upzoning-check', lga: lgaName, verdict });
    // Google Ads lead conversion (no-op until the Ads env vars are set).
    trackAdsConversion();
    setStatus('done');
  };

  if (status === 'done') {
    return (
      <div className="rounded-xl border border-teal-200 bg-teal-50 p-5">
        <p className="text-sm text-teal-800 font-medium">
          Thanks — we&apos;ve got your request. We&apos;ll email {email} to
          arrange the builder introduction.
        </p>
      </div>
    );
  }

  const heading =
    verdict === 'eligible'
      ? 'So what would a duplex here actually cost to build?'
      : 'Want a person to check this block properly?';
  const sub =
    verdict === 'eligible'
      ? `Have a free chat with a builder who does dual occupancies${lgaName ? ` in ${lgaName}` : ' in your area'} — real numbers, timelines, and what's involved on a block like yours.`
      : `The automatic map check couldn't give a clear answer here. A duplex specialist${lgaName ? ` in ${lgaName}` : ' in your area'} can look at the property-specific issue — no cost, no obligation. It doesn't change the result above.`;
  const buttonLabel =
    verdict === 'eligible' ? 'Ask about cost & next steps' : 'Ask a specialist to check this block';

  return (
    <div className="rounded-xl border-2 border-teal-500 bg-gradient-to-br from-teal-50 to-white p-5">
      <p className="text-base font-bold text-gray-900">{heading}</p>
      <p className="text-sm text-gray-600 mt-1 mb-3">{sub}</p>
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Consent sits ABOVE the button so the gate is understood before the
            action, and the recipient/use is spelled out. */}
        <label className="flex items-start gap-2 text-xs text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => {
              setConsent(e.target.checked);
              if (e.target.checked && status === 'error') setStatus('idle');
            }}
            className="mt-0.5 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
          />
          <span>
            Share my email, this address and result with a duplex builder so they
            can contact me about this property. PlotDetect may receive a referral
            fee.
          </span>
        </label>
        {/* Fields stack on mobile so the input keeps full width and the button
            never dominates before consent is read. */}
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (status === 'error') setStatus('idle');
            }}
            placeholder="you@email.com"
            className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
          />
          <button
            type="submit"
            disabled={status === 'submitting'}
            className="px-5 py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 transition-colors whitespace-nowrap disabled:opacity-60"
          >
            {status === 'submitting' ? 'Sending…' : buttonLabel}
          </button>
        </div>
        {status === 'error' && (
          <p className="text-xs text-red-600">
            {!consent
              ? 'Please tick the box above so we can pass your details to the builder.'
              : 'Something went wrong sending that — please try again.'}
          </p>
        )}
      </form>
    </div>
  );
}
