'use client';

/**
 * DuplexCheckWidget — the white-label, embeddable variant of the duplex
 * eligibility check.
 *
 * prior-art-checked: same engine + API as app/duplex-check/page.tsx (the ads
 * landing) and app/tools/upzoning-check/page.tsx (the SEO surface) — this is
 * the third, partner-skinned surface those pages cannot be: compact enough
 * for an iframe, carries the PARTNER's name, and on an eligible result the
 * call-to-action routes to the PARTNER's own contact page instead of
 * BuilderReferralCard (the whole point of the white-label product is that
 * the enquiry belongs to the partner, not to our referral pool). Types and
 * verdict helpers imported from lib/upzoning.ts; eligibility logic stays in
 * services/upzoning_check.py. The computed verdict is never conditioned on
 * partner presence (hard rule: the answer never bends toward a partner).
 *
 * CTA policy (user decision 2026-07-19): the partner button shows on
 * ELIGIBLE ("Ask X about a duplex...") and INDETERMINATE ("Ask X to take a
 * closer look") — never on a clear no, not_residential, or outage. Clicks
 * are tagged with the verdict so yes-leads and maybe-leads report
 * separately from day one.
 */

import React, { useEffect, useRef, useState } from 'react';
import posthog from 'posthog-js';
import { PropertySearch } from '@/components/property/PropertySearch';
import { CheckCircle2, XCircle, HelpCircle, ArrowRight } from 'lucide-react';
import {
  dualOccEligible,
  formLabel,
  plainReason,
  type UpzoningResult,
} from '@/lib/upzoning';

interface DuplexCheckWidgetProps {
  /** Partner display name — renders in the heading and the enquiry button */
  partnerName?: string | null;
  /** Partner's own contact page (https) — target of the enquiry button */
  ctaUrl?: string | null;
  /** Registered partner slug (or demo-<slug>) for usage analytics */
  refSlug?: string | null;
}

export function DuplexCheckWidget({ partnerName, ctaUrl, refSlug }: DuplexCheckWidgetProps) {
  const [result, setResult] = useState<UpzoningResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  // Guards the check-A-then-quickly-check-B race: only the latest selection's
  // response may write state, else a slow first response silently replaces
  // the verdict for the address the visitor is actually looking at.
  const requestIdRef = useRef(0);

  // Inside a ~700px iframe the verdict can render off-screen — same
  // "nothing happened" failure the ads landing guards against.
  useEffect(() => {
    if (loading || result || error) {
      statusRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
        source: 'widget',
        partner: refSlug ?? null,
        zone: data.zone,
        status: data.status,
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
  // one. "The maps couldn't answer" must never render as a definitive no.
  const dualOccForms =
    result?.forms.filter((f) => f.development_type.startsWith('dual_occupancy')) ?? [];
  const unconfirmedDualOcc = dualOccForms.find((f) => f.unconfirmed);
  const dualOccForm = dualOccForms[0];
  const indeterminate = !eligible && unconfirmedDualOcc !== undefined;

  return (
    <div className="w-full max-w-xl mx-auto">
      {/* Heading — carries the partner's name; the answer machinery is ours */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-extrabold text-gray-900 leading-tight">
          Can your block take a <span className="text-teal-600">duplex?</span>
        </h2>
        {partnerName && (
          <p className="mt-1 text-sm text-gray-500">
            A free eligibility check from {partnerName}
          </p>
        )}
      </div>

      <div className="bg-white rounded-xl border-2 border-teal-500 shadow-md p-4 text-left">
        <PropertySearch onAddressSelect={handleAddressSelect} />
      </div>
      <p className="mt-2 text-center text-xs text-gray-500">
        Free 10-second check against the 2025 NSW housing reforms — live NSW
        Government planning maps.
      </p>

      <div ref={statusRef} className="scroll-mt-2" />

      {loading && (
        <div className="py-8 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="animate-pulse text-lg font-bold text-teal-600">Checking your block...</p>
        </div>
      )}

      {error && (
        <div className="mt-4 bg-red-50 rounded-xl border border-red-200 p-4 text-center">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          {eligible ? (
            <div className="rounded-xl bg-emerald-600 text-white p-5 text-center">
              <CheckCircle2 className="w-8 h-8 mx-auto mb-2" />
              <p className="text-xl font-extrabold leading-tight">
                Yes — eligible for a duplex here.
              </p>
              <p className="mt-1.5 text-emerald-50 text-xs">
                {result.address} meets the mapped Housing SEPP lot standards for
                a dual occupancy. Any duplex still needs council consent through
                a development application.
              </p>
            </div>
          ) : result.status === 'unavailable' ? (
            <div className="rounded-xl bg-amber-50 border border-amber-200 p-5 text-center">
              <HelpCircle className="w-7 h-7 mx-auto mb-1.5 text-amber-500" />
              <p className="text-base font-bold text-gray-900">
                We couldn&apos;t reach the standards service just now.
              </p>
              <p className="mt-1 text-xs text-gray-600">
                That&apos;s a data outage, not an answer about your block — try
                again in a minute.
              </p>
            </div>
          ) : indeterminate ? (
            <div className="rounded-xl bg-amber-50 border border-amber-200 p-5 text-center">
              <HelpCircle className="w-7 h-7 mx-auto mb-1.5 text-amber-500" />
              <p className="text-base font-bold text-gray-900">
                Needs checking — the maps alone can&apos;t answer this one.
              </p>
              <p className="mt-1 text-xs text-gray-600">
                {unconfirmedDualOcc
                  ? plainReason(unconfirmedDualOcc)
                  : 'The government map data did not give a clear answer for this block.'}
              </p>
              <p className="mt-1.5 text-xs font-medium text-gray-700">
                This is not a no. It means an automatic map check isn&apos;t
                enough here — this block needs a person to look at it.
              </p>
              {ctaUrl ? (
                <a
                  href={ctaUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() =>
                    posthog.capture('widget_cta_click', {
                      partner: refSlug ?? null,
                      verdict: 'indeterminate',
                    })
                  }
                  className="mt-3 flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl bg-gray-900 text-white text-sm font-semibold hover:bg-gray-800 transition-colors"
                >
                  {partnerName
                    ? `Ask ${partnerName} to take a closer look`
                    : 'Ask a builder to take a closer look'}
                  <ArrowRight className="w-4 h-4" />
                </a>
              ) : (
                <a
                  href="https://verify.plotdetect.com.au/tools/upzoning-check"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-xs font-medium text-teal-700 hover:text-teal-600 underline"
                >
                  Run the full free check for this address
                </a>
              )}
            </div>
          ) : (
            <div className="rounded-xl bg-gray-100 border border-gray-200 p-5 text-center">
              <XCircle className="w-7 h-7 mx-auto mb-1.5 text-gray-400" />
              <p className="text-base font-bold text-gray-900">
                Not eligible — this block doesn&apos;t meet the mapped duplex
                standard.
              </p>
              <p className="mt-1 text-xs text-gray-600">
                {dualOccForm
                  ? plainReason(dualOccForm)
                  : 'The mapped standards for a dual occupancy are not met here.'}
              </p>
            </div>
          )}

          {/* Partner enquiry — the widget's job. Rendered on the verdict only
              when a CTA target exists; the verdict itself never changes. */}
          {eligible && ctaUrl && (
            <a
              href={ctaUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() =>
                posthog.capture('widget_cta_click', {
                  partner: refSlug ?? null,
                  verdict: 'eligible',
                })
              }
              className="flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl bg-gray-900 text-white text-sm font-semibold hover:bg-gray-800 transition-colors"
            >
              {partnerName
                ? `Ask ${partnerName} about a duplex on this block`
                : 'Enquire about a duplex on this block'}
              <ArrowRight className="w-4 h-4" />
            </a>
          )}

          {result.status === 'ok' && (
            <details className="rounded-xl border border-gray-200 p-3">
              <summary className="text-xs font-medium text-gray-700 cursor-pointer">
                See the full planning detail for this block
              </summary>
              <div className="mt-2 space-y-1.5">
                <p className="text-xs text-gray-500">
                  Zone {result.zone ?? 'not mapped'}
                  {result.zone_full ? ` — ${result.zone_full}` : ''} · Lot{' '}
                  {result.lot_area_m2 != null
                    ? `${Math.round(result.lot_area_m2)} m²`
                    : 'not mapped'}
                  {result.heritage.flag ? ' · Heritage mapping applies' : ''}
                </p>
                {result.forms.map((f) => (
                  <div key={f.development_type} className="flex items-start gap-2 text-xs">
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
                    </span>
                  </div>
                ))}
              </div>
            </details>
          )}

          <p className="text-xs text-gray-500 leading-relaxed">
            Mapped planning data and extracted Housing SEPP standards with their
            source clauses — not planning advice. Development consent depends on
            a development application and site-specific assessment by the
            consent authority. We never read an unclear map as a yes — a block
            the maps can&apos;t confirm shows as needs-checking or not eligible.
          </p>
        </div>
      )}
    </div>
  );
}
