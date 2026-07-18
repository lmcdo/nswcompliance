'use client';

// Modelled on components/reports/PostResultEmailStrip.tsx (same lead API,
// same self-contained state pattern); differs by the express consent checkbox
// + referral-fee disclosure required before contact details may be shared
// with a third party (Privacy Act / Spam Act consent basis).

import { useEffect, useState } from 'react';
import posthog from 'posthog-js';

interface Props {
  address: string;
  lgaName: string | null;
}

/**
 * Referral capture shown ONLY after an eligible dual-occupancy result.
 * The computed result is never altered by this card; it renders below it.
 * Submissions post to the existing lead API with a distinct interest_type so
 * referral-consented rows are separable from plain email-me rows.
 */
export function BuilderReferralCard({ address, lgaName }: Props) {
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    posthog.capture('referral_cta_view', { tool: 'upzoning-check' });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !consent) return;
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          address,
          eligible: true,
          lga_name: lgaName,
          interest_type: 'dual-occ-referral',
        }),
      });
    } catch {
      /* silent — never block the result display */
    }
    posthog.capture('referral_lead_submitted', {
      tool: 'upzoning-check',
      lga: lgaName,
    });
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="rounded-xl border border-teal-200 bg-teal-50 p-5">
        <p className="text-sm text-teal-800 font-medium">
          Done — your builder chat is being set up. Watch {email} for the
          introduction.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-teal-500 bg-gradient-to-br from-teal-50 to-white p-5">
      <p className="text-base font-bold text-gray-900">
        You can apply to build a duplex here. What would it actually cost?
      </p>
      <p className="text-sm text-gray-600 mt-1 mb-3">
        Have a free, no-pressure chat with a builder who does dual occupancies
        {lgaName ? ` in ${lgaName}` : ' in your area'} — real numbers, timelines,
        and what&apos;s involved on a block like yours.
      </p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@email.com"
            className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
          />
          <button
            type="submit"
            disabled={!consent}
            className="px-5 py-2 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 transition-colors whitespace-nowrap disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Talk to a builder
          </button>
        </div>
        <label className="flex items-start gap-2 text-xs text-gray-500 cursor-pointer">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-0.5 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
          />
          <span>
            Share my email and this address with the builder so they can
            contact me. PlotDetect may receive a referral fee.
          </span>
        </label>
      </form>
    </div>
  );
}
