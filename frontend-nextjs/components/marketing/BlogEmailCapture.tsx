'use client';

import { useState } from 'react';

/**
 * Email capture CTA for blog pages.
 * Renders at the bottom of every blog post (injected via blog layout).
 * POSTs to the lead API so we capture blog readers who never reach a tool page.
 */
export function BlogEmailCapture() {
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
          address: '',
          eligible: null,
          interest_type: 'blog-subscriber',
        }),
      });
    } catch { /* silent — never block the page */ }
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="mt-12 mb-8 p-6 rounded-xl border border-teal-200 bg-teal-50 text-center">
        <p className="text-sm text-teal-700 font-medium">
          Thanks — you&apos;re on the list.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-12 mb-8 p-6 rounded-xl border border-gray-200 bg-gray-50">
      <p className="text-base font-semibold text-gray-800 mb-1">
        Get property intelligence updates
      </p>
      <p className="text-sm text-gray-500 mb-4">
        Free tools, data insights, and NSW planning updates — no spam.
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2 max-w-md">
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
          className="px-5 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors whitespace-nowrap"
        >
          Subscribe
        </button>
      </form>
    </div>
  );
}
