'use client';

import { useState } from 'react';

interface Props {
  address: string;
  product: string; // passed as interest_type to lead API
  copy?: string;
  /** Verdict context for result-style emails (null = not applicable). */
  eligible?: boolean | null;
  lgaName?: string | null;
}

/**
 * Generic post-result email capture strip.
 * Self-contained: manages its own email state and API call.
 * Renders after a result card to capture the user's email without blocking result display.
 */
export function PostResultEmailStrip({
  address,
  product,
  copy = 'Get this result emailed to you',
  eligible = null,
  lgaName = null,
}: Props) {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          address,
          eligible,
          ...(lgaName ? { lga_name: lgaName } : {}),
          interest_type: product,
        }),
      });
    } catch { /* silent — never block the result */ }
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="mt-4 p-4 rounded-xl border border-teal-200 bg-teal-50">
        <p className="text-sm text-teal-700 font-medium">
          Thanks — we&apos;ll be in touch at {email}.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-4 p-4 rounded-xl border border-gray-200 bg-gray-50">
      <p className="text-sm font-medium text-gray-700 mb-3">{copy}</p>
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
          className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors whitespace-nowrap"
        >
          Email me
        </button>
      </form>
    </div>
  );
}
