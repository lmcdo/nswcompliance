'use client';

// prior-art-checked: posts to the EXISTING /api/dcp-interest route (dcp_interest table
// + off-domain NOTIFY_EMAIL alert). The UX mirrors DcpSnapshotCard's request form, but
// that one posts to /api/canibuildit/lead in the consumer duplex tool; this is the pro
// DCP-gap point-of-pain (Site Report / assessment), so it uses the dedicated
// dcp-interest endpoint. No new endpoint, no new table.

import { useState } from 'react';
import posthog from 'posthog-js';

interface DcpRequestCtaProps {
  /** Council name the request is for (the LGA whose DCP isn't loaded). Required. */
  council: string;
  /** Optional subject address for context in the alert email. */
  address?: string | null;
}

/**
 * Inline email capture shown at the exact point of pain — where the LEP has no
 * mapped FSR/height and the council's DCP is not yet in our dataset. Records the
 * demand (council → interest) and pings the ops inbox so the missing DCP can be
 * prioritised. Fails silent: a capture error never blocks the report.
 */
export function DcpRequestCta({ council, address }: DcpRequestCtaProps) {
  const [email, setEmail] = useState('');
  const [requested, setRequested] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!council) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || submitting) return;
    setSubmitting(true);
    try {
      await fetch('/api/dcp-interest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          council_name: council,
          address: address ?? null,
        }),
      });
    } catch {
      /* silent — never block the report on a capture failure */
    }
    try {
      posthog.capture('dcp_request_submitted', { council, has_address: !!address });
    } catch {
      /* posthog optional */
    }
    setRequested(true);
    setSubmitting(false);
  };

  if (requested) {
    return (
      <div className="mt-3 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-xs text-teal-800">
        Noted — we&rsquo;ll email you when {council}&rsquo;s DCP controls are loaded.
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 border-t border-amber-100 pt-3">
      <label className="block text-xs font-medium text-gray-700 mb-1.5">
        Need {council}&rsquo;s DCP controls for this lot? We&rsquo;ll prioritise loading it and
        email you when it&rsquo;s in.
      </label>
      <div className="flex gap-2">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@email.com"
          aria-label={`Email to request the ${council} DCP`}
          className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
        />
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors whitespace-nowrap"
        >
          {submitting ? 'Sending…' : 'Request this DCP'}
        </button>
      </div>
    </form>
  );
}
