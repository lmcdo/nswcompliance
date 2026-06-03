'use client';

import { useState, useEffect } from 'react';

const STORAGE_KEY = 'plotdetect_email';

interface Props {
  /** Address being analysed — sent to lead API */
  address: string;
  /** Product identifier for interest_type */
  product: string;
  /** Content shown only after email is provided */
  children: React.ReactNode;
}

/**
 * EmailGate — sits between the free verdict and the paid locked content.
 * Asks for email before revealing the children (LockedPreviewCard, FreePaidComparison, etc).
 * Remembers email in localStorage so the gate opens automatically on return visits.
 */
export function EmailGate({ address, product, children }: Props) {
  const [email, setEmail] = useState('');
  const [unlocked, setUnlocked] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  // Check localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setEmail(stored);
      setUnlocked(true);
    }
    setHydrated(true);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    const trimmed = email.trim();
    localStorage.setItem(STORAGE_KEY, trimmed);
    setUnlocked(true);
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: trimmed,
          address,
          eligible: null,
          interest_type: product,
        }),
      });
    } catch { /* silent */ }
  };

  // Prevent hydration mismatch — render nothing until client-side check is done
  if (!hydrated) return null;

  if (unlocked) {
    return <>{children}</>;
  }

  return (
    <div className="mt-6 p-5 rounded-xl border border-teal-200 bg-teal-50">
      <p className="text-sm font-semibold text-gray-800 mb-1">
        See the detailed breakdown
      </p>
      <p className="text-sm text-gray-500 mb-3">
        Enter your email to view the full analysis and purchase options.
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
          className="px-5 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors whitespace-nowrap"
        >
          Continue
        </button>
      </form>
    </div>
  );
}
