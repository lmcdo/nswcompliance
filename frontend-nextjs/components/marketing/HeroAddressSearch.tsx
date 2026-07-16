'use client';

// prior-art-checked: reuses the AddressAutocomplete primitive (components/reports).
// No existing island renders a dark homepage hero search that routes to /reports —
// HomeHero routes to /property (light theme) and LandingHero is the reports-landing
// card. This is the thin client wrapper that replaces the fake <TrackedLink> CTA on
// the marketing homepage so the hero box is a real, typeable address search.

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, ArrowRight } from 'lucide-react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { trackFunnelCta } from '@/lib/analytics';

/**
 * Homepage hero address search. Carries the typed address to the reports hub as
 * `?address=`, which every tool card then threads into its tool (each tool page
 * reads `params.address` and auto-runs). Fires the same PostHog funnel event the
 * old TrackedLink CTA did, so home→reports funnel tracking is preserved.
 */
export function HeroAddressSearch() {
  const [address, setAddress] = useState('');
  const router = useRouter();

  const go = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    const href = `/reports?address=${encodeURIComponent(trimmed)}`;
    trackFunnelCta('home', 'hero_search', href);
    router.push(href);
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        go(address);
      }}
      className="group flex items-center gap-3 w-full max-w-lg mx-auto bg-slate-900/80 border border-slate-700/50 rounded-xl px-5 py-4 hover:border-teal-500/50 focus-within:border-teal-500/50 hover:shadow-lg hover:shadow-teal-500/10 transition-all mb-10"
    >
      <Search className="w-5 h-5 flex-shrink-0 text-slate-500 group-focus-within:text-teal-400 transition-colors" />
      <AddressAutocomplete
        value={address}
        onChange={setAddress}
        onSelect={(selected) => go(selected)}
        placeholder="Enter any NSW address..."
        className="bg-transparent text-left text-white placeholder:text-slate-500 focus:outline-none"
      />
      <button
        type="submit"
        aria-label="Search this address"
        disabled={!address.trim()}
        className="flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <ArrowRight className="w-4 h-4 text-slate-600 group-focus-within:text-teal-400 group-hover:translate-x-0.5 transition-all" />
      </button>
    </form>
  );
}
