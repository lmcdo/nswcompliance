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
import { CheckCircle2, XCircle, HelpCircle } from 'lucide-react';
import {
  dualOccEligible,
  formLabel,
  type UpzoningResult,
} from '@/lib/upzoning';

export default function DuplexCheckLanding() {
  const [result, setResult] = useState<UpzoningResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const statusRef = useRef<HTMLDivElement>(null);

  // The spinner and the verdict must never sit below the fold unseen —
  // "nothing happened" is the number-one paid-click killer.
  useEffect(() => {
    if (loading || result || error) {
      statusRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [loading, result, error]);

  async function handleAddressSelect(address: string) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch('/api/upzoning', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? 'Could not check that address');
      }
      const data: UpzoningResult = await res.json();
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
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  const eligible = result ? dualOccEligible(result) : false;
  const dualOccForm = result?.forms.find((f) =>
    f.development_type.startsWith('dual_occupancy'),
  );

  return (
    <main className="min-h-screen bg-white flex flex-col">
      {/* Wordmark only — no navigation. Every link on an ad page is a leak. */}
      <header className="px-6 py-4">
        <span className="text-lg font-bold text-gray-900">
          Plot<span className="text-teal-600">Detect</span>
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
            <p className="mt-2 text-xs text-gray-400">
              No signup. No cost. Your answer appears right here.
            </p>
          )}
        </section>

        {/* Status anchor — scrolled into view the moment a check starts */}
        <div ref={statusRef} className="scroll-mt-4" />

        {/* Loading */}
        {loading && (
          <section className="py-8 text-center">
            <div className="animate-spin w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-sm text-gray-500">
              Checking live NSW planning maps for your block...
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
                  Yes — you can apply to build a duplex here.
                </p>
                <p className="mt-2 text-emerald-100 text-sm">
                  {result.address} meets the mapped Housing SEPP lot standards
                  for a dual occupancy — with consent, through a development
                  application.
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
            ) : (
              <div className="rounded-2xl bg-gray-100 border border-gray-200 p-6 text-center">
                <XCircle className="w-10 h-10 mx-auto mb-2 text-gray-400" />
                <p className="text-xl font-bold text-gray-900">
                  Not this block — it doesn&apos;t meet the duplex standard.
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {dualOccForm?.reason ??
                    'The mapped standards for a dual occupancy are not met here.'}
                </p>
                <Link
                  href="/tools/upzoning-check"
                  className="mt-3 inline-block text-sm font-medium text-teal-600 hover:text-teal-500 underline"
                >
                  See what else the rules allow on this block
                </Link>
              </div>
            )}

            {/* The offer — second thing on the page, not the ninth */}
            {eligible && (
              <BuilderReferralCard
                address={result.address}
                lgaName={result.lga_name}
              />
            )}

            {/* Covered council → the DCP numbers a DA is measured against;
                uncovered → capture the request (extraction demand signal). */}
            {eligible && result.lga_name && (
              <DcpSnapshotCard lgaName={result.lga_name} />
            )}

            {/* Trust strip */}
            <p className="text-center text-xs text-gray-400">
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
                    How to read this: ✓ means you can apply to build that
                    housing type here. In 2025 the government drew special
                    zones near town centres and train stations where
                    townhouses and small apartment blocks are newly allowed —
                    &quot;not in a reform area&quot; means this block
                    isn&apos;t inside one of those zones, so those new
                    permissions don&apos;t cover it. You can still seek
                    approval the standard way — a development application
                    (DA) to the council, which decides against its own local
                    rules. Where the map isn&apos;t clear, we say no instead
                    of guessing.
                  </p>
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
                      className="flex items-start gap-2 text-xs text-gray-600"
                    >
                      {f.eligible ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-600 flex-shrink-0 mt-0.5" />
                      ) : f.unconfirmed ? (
                        <HelpCircle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-gray-300 flex-shrink-0 mt-0.5" />
                      )}
                      <span>
                        <span className="font-medium text-gray-800">
                          {formLabel(f.development_type)}:
                        </span>{' '}
                        {f.reason}
                        {f.source_clause ? ` (${f.source_clause})` : ''}
                      </span>
                    </div>
                  ))}
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
        <p className="max-w-2xl mx-auto text-[11px] text-gray-400 text-center leading-relaxed">
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
