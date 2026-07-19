'use client';

/**
 * /duplex-check — ads landing page for the duplex eligibility check.
 *
 * prior-art-checked: same engine + API as app/tools/upzoning-check/page.tsx
 * (which stays as the SEO surface with nav/footer/full detail). This page is
 * the conversion-optimised shell that page cannot be: no navigation (1:1
 * attention ratio), verdict as the hero, referral capture directly under the
 * verdict, planning detail collapsed. Shared types/labels imported from
 * lib/upzoning.ts; eligibility logic stays in services/upzoning_check.py.
 *
 * Funnel: paid click → address (zero-PII micro-commitment) → computed verdict
 * → builder-chat capture (BuilderReferralCard) → collapsed detail for the few.
 */

import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import posthog from 'posthog-js';
import { PropertySearch } from '@/components/property/PropertySearch';
import { BuilderReferralCard } from '@/components/tools/BuilderReferralCard';
import { DcpSnapshotCard } from '@/components/tools/DcpSnapshotCard';
import { loadGoogleAds } from '@/lib/gtag';
import { PostResultEmailStrip } from '@/components/reports/PostResultEmailStrip';
import { CheckCircle2, XCircle, HelpCircle } from 'lucide-react';
import {
  dualOccEligible,
  formLabel,
  plainReason,
  type UpzoningResult,
} from '@/lib/upzoning';

export default function DuplexCheckLanding() {
  const [result, setResult] = useState<UpzoningResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  // Guards a check-A-then-quickly-B race: only the latest selection may write
  // state, else a slow first response overwrites the address actually shown —
  // unusually damaging on a per-address legal-info tool (matches the widget).
  const requestIdRef = useRef(0);

  // Load the Google Ads tag on this ads landing only (no-op until the Ads env
  // vars are set) so the $100 test can register lead conversions.
  useEffect(() => {
    loadGoogleAds();
  }, []);

  // The spinner and the verdict must never sit below the fold unseen —
  // "nothing happened" is the number-one paid-click killer.
  useEffect(() => {
    if (loading || result || error) {
      statusRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [loading, result, error]);

  async function handleAddressSelect(address: string) {
    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch('/api/upzoning', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });
      if (requestId !== requestIdRef.current) return;
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? 'Could not check that address');
      }
      const data: UpzoningResult = await res.json();
      if (requestId !== requestIdRef.current) return;
      setResult(data);
      posthog.capture('tool_run', {
        tool: 'upzoning-check',
        source: 'ads_landing',
        zone: data.zone,
        status: data.status,
        eligible_count: data.forms.filter((f) => f.eligible).length,
        dual_occ_eligible: dualOccEligible(data),
      });
    } catch (e) {
      if (requestId !== requestIdRef.current) return;
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }

  const eligible = result ? dualOccEligible(result) : false;
  // ALL dual-occ variants (attached/detached), not .find()'s first match —
  // a confirmed-ineligible first variant must not mask an unconfirmed later
  // one. "The maps couldn't answer" must never render as a definitive no —
  // the engine's three-state semantics survive to the headline (same fix as
  // DuplexCheckWidget; found in PR #790 cross-review).
  const dualOccForms = result
    ? result.forms.filter((f) => f.development_type.startsWith('dual_occupancy'))
    : [];
  const unconfirmedDualOcc = dualOccForms.find((f) => f.unconfirmed);
  const dualOccForm = dualOccForms[0];
  const indeterminate = !eligible && unconfirmedDualOcc !== undefined;

  return (
    <main className="min-h-screen bg-white flex flex-col">
      {/* Wordmark only — no navigation. Every link on an ad page is a leak.
          Lead with the domain's brand (canibuildit.com.au) so a paid visitor
          isn't left wondering whether they were redirected. */}
      <header className="px-6 py-4 flex items-baseline gap-2">
        <span className="text-lg font-bold text-gray-900">Can I Build It</span>
        <span className="text-xs text-gray-400">
          by Plot<span className="text-teal-600">Detect</span>
        </span>
      </header>

      <div className="flex-1 w-full max-w-2xl mx-auto px-6 pb-16">
        {/* Hero: headline → address box → supporting line. The input is the
            page; everything else supports it. */}
        <section className="pt-6 sm:pt-10 pb-6 text-center">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 leading-tight">
            Can your block take a{' '}
            <span className="text-teal-600">duplex?</span>
          </h1>
          <div className="mt-6 bg-white rounded-2xl border-2 border-teal-500 shadow-lg p-5 text-left">
            <PropertySearch onAddressSelect={handleAddressSelect} />
          </div>
          <p className="mt-3 text-base text-gray-600 max-w-lg mx-auto">
            Free 10-second check against the 2025 NSW housing reforms —
            straight from live NSW Government planning maps.
          </p>
          {!result && !loading && (
            <p className="mt-2 text-xs text-gray-500 max-w-md mx-auto">
              Independent planning-data check. No signup, no cost — entering an
              address doesn&apos;t send it to a builder. Your answer appears right
              here.
            </p>
          )}
        </section>

        {/* Status anchor — scrolled into view the moment a check starts */}
        <div ref={statusRef} className="scroll-mt-4" />

        {/* Loading — loud on purpose: a paid click must never wonder whether
            anything is happening */}
        {loading && (
          <section className="py-10 text-center">
            <div className="animate-spin w-12 h-12 border-4 border-teal-600 border-t-transparent rounded-full mx-auto mb-5" />
            <p className="animate-pulse text-2xl sm:text-3xl font-extrabold text-teal-600">
              Checking your block...
            </p>
            <p className="mt-2 text-sm text-gray-500">
              Reading live NSW Government planning maps — zone, heritage and
              lot standards.
            </p>
          </section>
        )}

        {/* Error */}
        {error && (
          <section className="py-4">
            <div className="bg-red-50 rounded-xl border border-red-200 p-5 text-center">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </section>
        )}

        {/* Verdict — the hero moment */}
        {result && (
          <section className="space-y-5">
            {eligible ? (
              <div className="rounded-2xl bg-emerald-600 text-white p-6 sm:p-8 text-center shadow-lg">
                <CheckCircle2 className="w-12 h-12 mx-auto mb-3" />
                <p className="text-2xl sm:text-3xl font-extrabold leading-tight">
                  Yes — eligible for a duplex
                </p>
                <p className="mt-1.5 text-lg sm:text-xl font-bold leading-snug">
                  {result.address}
                </p>
                <p className="mt-2 text-emerald-50 text-sm">
                  Meets the mapped Housing SEPP lot standards for a dual
                  occupancy. Any duplex still needs council consent through a
                  development application.
                </p>
              </div>
            ) : result.status === 'unavailable' ? (
              <div className="rounded-2xl bg-amber-50 border border-amber-200 p-6 text-center">
                <HelpCircle className="w-10 h-10 mx-auto mb-2 text-amber-500" />
                <p className="text-xl font-bold text-gray-900">
                  We couldn&apos;t reach the standards service just now.
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  That&apos;s a data outage, not an answer about your block —
                  try again in a minute.
                </p>
              </div>
            ) : indeterminate ? (
              <div className="rounded-2xl bg-amber-50 border border-amber-200 p-6 text-center">
                <HelpCircle className="w-10 h-10 mx-auto mb-2 text-amber-500" />
                <p className="text-xl font-bold text-gray-900">
                  Needs checking — the maps alone can&apos;t answer this one.
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {unconfirmedDualOcc
                    ? plainReason(unconfirmedDualOcc)
                    : 'The government map data did not give a clear answer for this block.'}
                </p>
                <p className="mt-2 text-sm font-medium text-gray-700">
                  This is not a no. It means an automatic map check isn&apos;t
                  enough here — this block needs a person to look at it.
                </p>
              </div>
            ) : (
              <div className="rounded-2xl bg-gray-100 border border-gray-200 p-6 text-center">
                <XCircle className="w-10 h-10 mx-auto mb-2 text-gray-400" />
                <p className="text-xl font-bold text-gray-900">
                  Not eligible — this block doesn&apos;t meet the mapped duplex
                  standard.
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {dualOccForm
                    ? plainReason(dualOccForm)
                    : 'The mapped standards for a dual occupancy are not met here.'}
                </p>
                <Link
                  href="/tools/upzoning-check"
                  className="mt-3 inline-block text-sm font-medium text-teal-600 hover:text-teal-500 underline"
                >
                  See what else the rules allow on this block
                </Link>
              </div>
            )}

            {/* The offer — second thing on the page, not the ninth. Shown on an
                eligible result AND a needs-checking one (the maybe-lead the
                builder pitch calls valuable); copy differs per verdict and never
                implies a specialist will make the block eligible. */}
            {(eligible || indeterminate) && (
              <BuilderReferralCard
                address={result.address}
                lgaName={result.lga_name}
                verdict={eligible ? 'eligible' : 'needs-checking'}
              />
            )}

            {/* Covered council → the DCP numbers a DA is measured against;
                uncovered → capture the request (extraction demand signal). */}
            {eligible && result.lga_name && (
              <DcpSnapshotCard
                lgaName={result.lga_name}
                councilSlug={result.former_council}
              />
            )}

            {/* The keepable result — the one thing a search engine can't give
                them. Both verdicts: everyone wants their own answer saved. */}
            {result.status === 'ok' && (
              <PostResultEmailStrip
                address={result.address}
                product="duplex-result"
                eligible={eligible}
                lgaName={result.lga_name}
                copy="Email me this result — keep it, or forward it to your builder or agent"
              />
            )}

            {/* Trust strip */}
            <p className="text-center text-xs text-gray-500">
              Live NSW Planning Portal data · every standard cited to its
              source clause · Data: NSW Planning Portal, Spatial Services NSW
            </p>

            {/* Detail collapsed — credibility asset, not the interface */}
            {result.status === 'ok' && (
              <details className="rounded-xl border border-gray-200 p-4">
                <summary className="text-sm font-medium text-gray-700 cursor-pointer">
                  See the full planning detail for this block
                </summary>
                <div className="mt-3 space-y-2">
                  <p className="text-xs text-gray-500">
                    Zone {result.zone ?? 'not mapped'}
                    {result.zone_full ? ` — ${result.zone_full}` : ''} · Lot{' '}
                    {result.lot_area_m2 != null
                      ? `${Math.round(result.lot_area_m2)} m²`
                      : 'not mapped'}
                    {result.heritage.flag ? ' · Heritage mapping applies' : ''}
                  </p>
                  {result.forms.map((f) => (
                    <div
                      key={f.development_type}
                      className="flex items-start gap-2 text-xs"
                    >
                      {f.eligible ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-600 flex-shrink-0 mt-0.5" />
                      ) : f.unconfirmed ? (
                        <HelpCircle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-gray-300 flex-shrink-0 mt-0.5" />
                      )}
                      <span className="flex-1 text-gray-600">
                        <span className="font-medium text-gray-800">
                          {formLabel(f.development_type)}:
                        </span>{' '}
                        {plainReason(f)}
                        {f.legislation_url && (
                          <>
                            {' '}
                            <a
                              href={f.legislation_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-teal-600/70 hover:text-teal-600 underline whitespace-nowrap"
                            >
                              official rule ↗
                            </a>
                          </>
                        )}
                      </span>
                    </div>
                  ))}
                  <p className="text-xs text-gray-500 pt-1">
                    The 2025 reforms opened extra housing types in mapped zones
                    near town centres and stations; outside those zones the
                    standard council pathway (a development application) still
                    applies. We never read an unclear map as a yes — a block the
                    maps can&apos;t confirm shows as needs-checking or not
                    eligible, never as eligible.
                  </p>
                  <Link
                    href="/tools/upzoning-check"
                    className="inline-block text-xs text-teal-600 hover:text-teal-500 underline"
                  >
                    Open the full checker with the council land-use table
                  </Link>
                </div>
              </details>
            )}
          </section>
        )}
      </div>

      {/* One legal line — no footer menus */}
      <footer className="px-6 py-4 border-t border-gray-100">
        <p className="max-w-2xl mx-auto text-[11px] text-gray-500 text-center leading-relaxed">
          This tool reports mapped planning data and extracted Housing SEPP
          standards with their source clauses. It is not planning advice —
          development consent depends on a development application and
          site-specific assessment by the consent authority. ©{' '}
          {new Date().getFullYear()} PlotDetect
        </p>
      </footer>
    </main>
  );
}
