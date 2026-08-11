'use client';

/**
 * /tools/upzoning-check — Free Upzoning Check Tool
 *
 * "What do the 2025 NSW housing reforms allow on this block?" — per-address
 * Housing-SEPP form eligibility (dual occupancy, terraces, manor houses,
 * low-rise apartments, TOD) from the fail-closed backend engine.
 *
 * prior-art-checked: page structure mirrors app/tools/zoning-check/page.tsx
 * (SiteNav/SiteFooter, PropertySearch, posthog tool_run); ALL eligibility logic
 * lives in services/upzoning_check.py -> housing_sepp_eligibility (live
 * 776/752/759/452 gates + heritage suppression). This page renders engine
 * output verbatim and adds no planning logic.
 *
 * Funnel: free instant result → /reports/intelligence-brief for capacity analysis
 */

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import posthog from 'posthog-js';
import { PropertySearch } from '@/components/property/PropertySearch';
import { BuilderReferralCard } from '@/components/tools/BuilderReferralCard';
import { TrendingUp, ArrowRight, CheckCircle2, XCircle, AlertTriangle, HelpCircle } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { formLabel, type UpzoningResult } from '@/lib/upzoning';

function deslug(devType: string): string {
  const words = devType.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

interface LepEntry {
  development_type: string;
  permissibility: 'exempt' | 'permitted' | 'prohibited';
}

/**
 * What the council's OWN plan lists for this zone — verbatim land-use table
 * entries from our scraped legislation data (coverage-gated server side; the
 * panel simply does not render for councils we have not loaded). This is the
 * ordinary development-application pathway, separate from the 2025 reforms.
 */
function LepLandUsePanel({ zone, lga, zoneEpi }: { zone: string; lga: string; zoneEpi: string | null }) {
  const [entries, setEntries] = useState<LepEntry[] | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEntries(null);
    fetch(`/api/lep/permissibility?zone=${encodeURIComponent(zone)}&lga=${encodeURIComponent(lga)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled || !data?.covered) return;
        setEntries(data.entries ?? []);
        setSourceUrl(data.source_url ?? null);
      })
      .catch(() => {
        // Panel is additive context — absence is the fail state, never an error box.
      });
    return () => {
      cancelled = true;
    };
  }, [zone, lga]);

  if (!entries || entries.length === 0) return null;

  const withConsent = entries.filter((e) => e.permissibility === 'permitted');
  const prohibited = entries.filter((e) => e.permissibility === 'prohibited');

  return (
    <div className="rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-1">
        What {zoneEpi ?? `the ${lga} local plan`} lists for zone {zone}
      </h3>
      <p className="text-xs text-gray-400 mb-3">
        The ordinary council pathway, separate from the 2025 reforms: uses listed as
        permitted here can be applied for through a standard development application.
        Entries are reproduced from the plan&apos;s land-use table.
      </p>
      {withConsent.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-gray-500 mb-1.5">Permitted with consent</p>
          <div className="flex flex-wrap gap-1.5">
            {withConsent.map((e) => (
              <span key={e.development_type} className="px-2 py-0.5 text-[11px] bg-green-50 text-green-700 rounded-full border border-green-200">
                {deslug(e.development_type)}
              </span>
            ))}
          </div>
        </div>
      )}
      {prohibited.length > 0 && (
        <details>
          <summary className="text-xs font-medium text-gray-500 cursor-pointer">
            Prohibited ({prohibited.length} uses)
          </summary>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {prohibited.map((e) => (
              <span key={e.development_type} className="px-2 py-0.5 text-[11px] bg-gray-50 text-gray-500 rounded-full border border-gray-200">
                {deslug(e.development_type)}
              </span>
            ))}
          </div>
        </details>
      )}
      {sourceUrl && (
        <p className="text-[11px] text-gray-400 mt-3">
          Source:{' '}
          <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="underline hover:text-gray-600">
            land-use table on NSW legislation
          </a>
        </p>
      )}
    </div>
  );
}

export default function UpzoningCheckPage() {
  const [result, setResult] = useState<UpzoningResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        source: 'seo_page',
        zone: data.zone,
        status: data.status,
        eligible_count: data.forms.filter((f) => f.eligible).length,
        in_tod: data.gates?.in_tod ?? null,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  const eligibleForms = result?.forms.filter((f) => f.eligible) ?? [];
  const otherForms = result?.forms.filter((f) => !f.eligible) ?? [];

  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero + Search */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-8">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            Free tool
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">
          Upzoning check: what do the 2025 housing reforms allow on your block?
        </h1>
        <p className="text-gray-500 text-lg max-w-xl mb-8">
          Check dual occupancy, terraces, manor houses and low-rise apartments against the
          NSW Low and Mid-Rise housing reforms and Transport Oriented Development precincts —
          from live NSW Government planning maps, with the source clause for every standard.
        </p>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Enter a NSW address
          </label>
          <PropertySearch onAddressSelect={handleAddressSelect} />
        </div>
      </section>

      {/* Loading */}
      {loading && (
        <section className="max-w-3xl mx-auto px-6 pb-8">
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
            <div className="animate-spin w-6 h-6 border-2 border-teal-600 border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-sm text-gray-500">Checking live planning maps — zone, heritage, TOD and reform-area layers...</p>
          </div>
        </section>
      )}

      {/* Error */}
      {error && (
        <section className="max-w-3xl mx-auto px-6 pb-8">
          <div className="bg-red-50 rounded-xl border border-red-200 p-6">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </section>
      )}

      {/* Result */}
      {result && (
        <section className="max-w-3xl mx-auto px-6 pb-12 space-y-4">
          {/* Address + Zone header */}
          <div className="bg-teal-50 rounded-xl border border-teal-200 p-6">
            {result.zone_epi && (
              <p className="text-xs text-teal-600 font-medium mb-1">{result.zone_epi}</p>
            )}
            <p className="text-sm text-gray-700 mb-3">{result.address}</p>
            <div className="flex items-baseline gap-3 flex-wrap">
              <span className="text-2xl font-bold text-gray-900">{result.zone ?? 'Zone not mapped'}</span>
              {result.zone_full && result.zone && (
                <span className="text-lg text-gray-600">{result.zone_full.replace(result.zone, '').trim()}</span>
              )}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
              <span>Lot area: {result.lot_area_m2 != null ? `${Math.round(result.lot_area_m2)} m²` : 'not mapped'}</span>
              <span>
                {result.lot_type === 'battleaxe'
                  ? `Width (main lot, battleaxe): ${result.lot_width_m != null ? `${Math.round(result.lot_width_m)} m` : 'not mapped'}`
                  : `Frontage: ${result.lot_width_m != null ? `${Math.round(result.lot_width_m)} m` : 'not mapped'}`}
              </span>
            </div>
          </div>

          {/* Mapped status chips */}
          <div className="rounded-xl border border-gray-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
              Mapped status for this lot (live NSW planning layers)
            </p>
            <div className="flex flex-wrap gap-2 text-xs">
              <span className={`px-2.5 py-1 rounded-full border ${result.gates.in_tod ? 'bg-teal-50 text-teal-700 border-teal-200' : 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                {result.gates.in_tod ? 'In a TOD precinct' : 'Not in a TOD precinct'}
              </span>
              <span className={`px-2.5 py-1 rounded-full border ${result.gates.in_lmr_area ? 'bg-teal-50 text-teal-700 border-teal-200' : 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                {result.gates.in_lmr_area ? 'In a Low & Mid-Rise reform area' : 'Not a Low & Mid-Rise reform area'}
              </span>
              <span className={`px-2.5 py-1 rounded-full border ${result.gates.dual_occ_prohibited ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                {result.gates.dual_occ_prohibited ? 'Dual occupancy prohibited on this lot' : 'No dual-occupancy prohibition'}
              </span>
              <span className={`px-2.5 py-1 rounded-full border ${result.heritage.flag ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                {result.heritage.flag ? 'Heritage listed' : 'No heritage listing'}
              </span>
            </div>
          </div>

          {/* Heritage banner */}
          {result.heritage.flag && (
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-amber-800 font-medium">
                  Heritage mapping applies to this lot
                </p>
                <p className="text-xs text-amber-700 mt-1">
                  {[...result.heritage.hca, ...result.heritage.items.filter((i) => !result.heritage.hca.includes(i))].slice(0, 3).join(' · ')}
                </p>
                <p className="text-xs text-amber-600 mt-1">
                  The Low and Mid-Rise reforms do not apply on heritage land — the results below reflect that.
                </p>
              </div>
            </div>
          )}

          {/* Status: unavailable — a data outage is NOT "nothing possible" */}
          {result.status === 'unavailable' && (
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-6">
              <p className="text-sm text-amber-800 font-medium">
                Eligibility standards are temporarily unavailable for this address.
              </p>
              <p className="text-xs text-amber-700 mt-1">
                The standards service did not respond. This is a data outage, not a planning
                result — try again shortly.
              </p>
            </div>
          )}

          {/* Status: not residential */}
          {result.status === 'not_residential' && (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
              <p className="text-sm text-gray-700 font-medium">
                {result.zone ? `Zone ${result.zone}` : 'This zone'} is not a residential zone.
              </p>
              <p className="text-xs text-gray-500 mt-1">
                The Low and Mid-Rise housing reforms apply in R1, R2, R3 and R4 zones. For other
                zones, check the permitted uses in the zoning tables for this property&apos;s LEP.
              </p>
              <Link
                href="/tools/zoning-check"
                className="mt-3 inline-flex items-center gap-1 text-sm text-teal-600 hover:text-teal-500 font-medium"
              >
                Run a zoning check instead <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}

          {/* Forms */}
          {result.status === 'ok' && (
            <>
              {/* Lead with the confident answer: name the forms that meet the mapped
                  standards up front, so the result reads as a finding, not a hedge.
                  The "with consent / subject to a DA" caveat lives once, below. */}
              {eligibleForms.length > 0 && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-emerald-900">
                      On this block you can apply to build:{' '}
                      {eligibleForms.map((f) => formLabel(f.development_type)).join(', ')}
                    </p>
                    <p className="text-xs text-emerald-700 mt-1">
                      Each meets the mapped Housing SEPP standards for this lot — with consent,
                      through a development application. Detail and source clauses below.
                    </p>
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-gray-200 p-5">
                <h3 className="text-sm font-semibold text-gray-900 mb-1">
                  Housing types checked against mapped standards
                </h3>
                <p className="text-xs text-gray-400 mb-4">
                  Every result below is subject to a development application and site-specific
                  council assessment — this is a mapped-standards screen, not an approval outcome.
                </p>
                <div className="space-y-3">
                  {[...eligibleForms, ...otherForms].map((f) => (
                    <div
                      key={f.development_type}
                      className={`rounded-lg border p-4 ${
                        f.eligible
                          ? 'border-green-200 bg-green-50'
                          : f.unconfirmed
                            ? 'border-amber-200 bg-amber-50'
                            : 'border-gray-200 bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-gray-900">{formLabel(f.development_type)}</p>
                          <p className={`text-xs mt-1 ${f.eligible ? 'text-green-700' : f.unconfirmed ? 'text-amber-700' : 'text-gray-600'}`}>
                            {/* Drop the inline "(subject to a development application)" on the
                                eligible cards — the section note above states it once, and
                                repeating it per row is what made a clear "meets" read as a hedge. */}
                            {f.eligible
                              ? f.reason.replace(/\s*\(subject to a development application\)/i, '')
                              : f.reason}
                          </p>
                          {/* A "no" on the reform pathway is NOT "cannot build" — the
                              council's own plan may permit this type via a standard DA.
                              Without this line, a Bowral owner reads "townhouses: no"
                              while standing next to townhouses consented under that pathway. */}
                          {!f.eligible && !f.unconfirmed && f.requires_lmr_area && f.reason.includes('Low and Mid-Rise reform area') && (
                            <p className="text-[11px] text-gray-500 mt-1">
                              This result covers the 2025 Low and Mid-Rise reforms only. This
                              housing type may still be permitted under the council&apos;s own
                              Local Environmental Plan through a standard development
                              application — see the council&apos;s land-use table below.
                            </p>
                          )}
                          {(f.source_clause || f.legislation_url) && (
                            <p className="text-[11px] text-gray-400 mt-1.5">
                              {f.source_clause && <span>Source: {f.source_clause}</span>}
                              {f.legislation_url && (
                                <>
                                  {f.source_clause && ' · '}
                                  <a href={f.legislation_url} target="_blank" rel="noopener noreferrer" className="underline hover:text-gray-600">
                                    legislation
                                  </a>
                                </>
                              )}
                              {f.effective_date && ` · in force ${f.effective_date}`}
                            </p>
                          )}
                        </div>
                        <span className="flex-shrink-0 mt-0.5">
                          {f.eligible ? (
                            <CheckCircle2 className="w-5 h-5 text-green-600" aria-label="Meets mapped standards" />
                          ) : f.unconfirmed ? (
                            <HelpCircle className="w-5 h-5 text-amber-500" aria-label="Not determinable from mapped data" />
                          ) : (
                            <XCircle className="w-5 h-5 text-gray-400" aria-label="Does not meet mapped standards" />
                          )}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {result.zone && result.lga_name && (
                <LepLandUsePanel zone={result.zone} lga={result.lga_name} zoneEpi={result.zone_epi} />
              )}

              {/* Builder referral — ONLY on an eligible dual-occ result; the
                  computed result above is never conditioned on this card. */}
              {eligibleForms.some((f) => f.development_type.startsWith('dual_occupancy')) && (
                <BuilderReferralCard address={result.address} lgaName={result.lga_name} />
              )}

              {/* CTA */}
              <div className="bg-slate-950 rounded-xl p-6 flex items-center justify-between gap-4">
                <div>
                  <p className="text-white font-semibold text-sm">What would it actually yield?</p>
                  <p className="text-slate-400 text-xs mt-1">
                    The free property brief adds development capacity arithmetic, constraints,
                    nearby DA outcomes and land value context for this address.
                  </p>
                </div>
                <Link
                  href={`/reports/intelligence-brief?address=${encodeURIComponent(result.address)}`}
                  className="flex-shrink-0 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
                >
                  Full property brief <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </>
          )}

          {/* Disclaimer */}
          <p className="text-[11px] text-gray-400 leading-relaxed">
            This tool reports mapped planning data and extracted Housing SEPP standards with
            their source clauses. It is not planning advice. Results are a screen against
            mapped standards only — development consent depends on a development application
            and site-specific assessment by the consent authority. Where a layer or standard
            is not mapped, the result says so rather than assuming an answer.
          </p>
        </section>
      )}

      {/* SEO content (always visible before a result) */}
      {!result && !loading && (
        <section className="max-w-3xl mx-auto px-6 pb-12">
          <div className="bg-gray-50 rounded-xl border border-gray-100 p-8">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              What changed under the 2025 NSW housing reforms?
            </h2>
            <div className="space-y-4 text-sm text-gray-600 leading-relaxed">
              <p>
                From early 2025, the NSW <strong>Low and Mid-Rise housing reforms</strong> under
                SEPP (Housing) 2021 made dual occupancies, terraces, manor houses and low-rise
                apartment buildings permissible with consent across many R1, R2 and R3 zoned
                lots that previously could not host them — subject to lot standards, exclusion
                mapping and heritage.
              </p>
              <p>
                Separately, <strong>Transport Oriented Development (TOD) precincts</strong> around
                designated stations carry their own uplift for mid-rise apartment forms, mapped
                as precinct polygons on the NSW planning maps.
              </p>
              <p>
                Whether any of this applies to a specific block depends on live mapping: the
                zone, the Low and Mid-Rise exclusion map, TOD precinct boundaries, dual-occupancy
                prohibition mapping, heritage items and conservation areas, and the lot&apos;s own
                area and frontage. This tool queries those layers for one address and shows each
                housing type&apos;s result with the clause it comes from.
              </p>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/tools/zoning-check"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                What zone is my property? <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              <Link
                href="/tools/subdivision-check"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                Can I subdivide? <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              <Link
                href="/reports/intelligence-brief"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                Full property brief <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </section>
      )}

      <SiteFooter />
    </main>
  );
}
