'use client';

/**
 * /tools/subdivision-check — Free Subdivision Eligibility Check
 *
 * Target keywords: "can i subdivide my property" (480/mo), "dual occupancy nsw" (50/mo),
 * "subdivision rules nsw" (10/mo)
 * Combined: ~540/mo
 *
 * Funnel: Free instant result → /assessment or /reports/conveyancing
 */

import React, { useState } from 'react';
import Link from 'next/link';
import posthog from 'posthog-js';
import { PropertySearch } from '@/components/property/PropertySearch';
import { Scissors, ArrowRight, CheckCircle2, XCircle, AlertTriangle, Info } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

interface SubdivisionResult {
  address: string;
  lga: string;
  zone_code: string;
  zone_name: string;
  lot_area_sqm: number | null;
  min_lot_size_sqm: number | null;
  fsr: number | null;
  height_m: number | null;
  permitted_dwelling_types: string[];
  subdivision_likely: 'yes' | 'no' | 'maybe';
  reason: string;
  heritage_item: boolean;
  heritage_conservation_area: boolean;
}

function assessSubdivision(data: {
  zone_code: string;
  lot_area_sqm: number | null;
  min_lot_size_sqm: number | null;
  permitted: string[];
  prohibited: string[];
}): { likely: 'yes' | 'no' | 'maybe'; reason: string } {
  const { zone_code, lot_area_sqm, min_lot_size_sqm, permitted, prohibited } = data;

  // Industrial/environmental zones
  if (typeof zone_code === 'string' && (zone_code.startsWith('IN') || zone_code.startsWith('E') || zone_code.startsWith('W') || zone_code.startsWith('C1') || zone_code === 'SP1' || zone_code === 'SP2')) {
    return { likely: 'no', reason: `Zone ${zone_code} does not typically permit residential subdivision.` };
  }

  const hasDualOcc = permitted.some(u => u.toLowerCase().includes('dual occupancy'));
  const hasMultiDwelling = permitted.some(u => u.toLowerCase().includes('multi dwelling'));
  const dualOccProhibited = prohibited.some(u => u.toLowerCase().includes('dual occupancy'));

  // "hasDensity" = either dual occ or multi dwelling is permitted
  const hasDensity = hasDualOcc || hasMultiDwelling;

  if (!lot_area_sqm || !min_lot_size_sqm) {
    if (hasDensity) {
      const types = [hasDualOcc && 'dual occupancy', hasMultiDwelling && 'multi dwelling housing'].filter(Boolean).join(' and ');
      return { likely: 'maybe', reason: `This zone permits ${types}, but lot area data is not available to confirm minimum lot size compliance. Check with council.` };
    }
    return { likely: 'maybe', reason: 'Insufficient data to determine subdivision eligibility. Check your LEP minimum lot size against your actual lot area.' };
  }

  const canFitTwo = lot_area_sqm >= min_lot_size_sqm * 2;

  if (canFitTwo && hasDualOcc) {
    return { likely: 'yes', reason: `Your lot (${lot_area_sqm.toLocaleString()}m²) is at least twice the minimum lot size (${min_lot_size_sqm}m²), and dual occupancy is permitted in zone ${zone_code}. Torrens title subdivision may be possible.` };
  }

  if (canFitTwo && hasMultiDwelling && !hasDualOcc) {
    const prohibitedNote = dualOccProhibited
      ? `Dual occupancy is prohibited in zone ${zone_code}, but multi dwelling housing is permitted.`
      : `Dual occupancy is not listed as permitted in zone ${zone_code}, but multi dwelling housing is permitted.`;
    return { likely: 'maybe', reason: `Your lot (${lot_area_sqm.toLocaleString()}m²) is at least twice the minimum lot size (${min_lot_size_sqm}m²). ${prohibitedNote} A multi dwelling housing development with strata subdivision may be possible. Consult a planner.` };
  }

  if (canFitTwo && !hasDensity) {
    const prohibitedNote = dualOccProhibited
      ? `Dual occupancy is prohibited in zone ${zone_code}.`
      : `Dual occupancy does not appear as a permitted use in zone ${zone_code}.`;
    return { likely: 'maybe', reason: `Your lot is large enough (${lot_area_sqm.toLocaleString()}m²), but ${prohibitedNote.toLowerCase()} Strata subdivision for an attached dual occupancy may still be possible. Check with a planner.` };
  }

  if (!canFitTwo && hasDualOcc) {
    return { likely: 'maybe', reason: `Dual occupancy is permitted, but your lot (${lot_area_sqm.toLocaleString()}m²) is below twice the minimum lot size (${min_lot_size_sqm * 2}m²). Strata subdivision (attached dual occupancy) may be possible, but Torrens title is unlikely.` };
  }

  if (!canFitTwo && hasMultiDwelling && !hasDualOcc) {
    const prohibitedNote = dualOccProhibited
      ? `Dual occupancy is prohibited in zone ${zone_code}, but multi dwelling housing is permitted.`
      : `Dual occupancy is not listed as permitted in zone ${zone_code}, but multi dwelling housing is permitted.`;
    return { likely: 'maybe', reason: `Your lot (${lot_area_sqm.toLocaleString()}m²) is below twice the minimum lot size (${min_lot_size_sqm * 2}m²) for Torrens title. ${prohibitedNote} A multi dwelling housing development with strata subdivision may still be possible. Consult a planner.` };
  }

  // Neither dual occ nor multi dwelling permitted, lot too small
  const prohibitedNote = dualOccProhibited
    ? `dual occupancy is prohibited in zone ${zone_code}`
    : `dual occupancy does not appear permitted in zone ${zone_code}`;
  return { likely: 'no', reason: `Your lot (${lot_area_sqm.toLocaleString()}m²) is below twice the minimum lot size (${min_lot_size_sqm * 2}m²), and ${prohibitedNote}.` };
}

export default function SubdivisionCheckPage() {
  const [result, setResult] = useState<SubdivisionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAddressSelect(address: string) {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`/api/property?address=${encodeURIComponent(address)}`);
      if (!res.ok) throw new Error('Could not look up that address');
      const json = await res.json();
      const prop = json.data ?? json;
      const constraints = prop.constraints ?? {};

      // Extract zone code from zoneDescription
      const zoneDesc: string = prop.zoneDescription ?? '';
      const zoneCodeMatch = zoneDesc.match(/^([A-Z][A-Z0-9]*(?:\.\d+)?)\b/);
      const zone_code = zoneCodeMatch?.[1] ?? zoneDesc.split(' ')[0] ?? 'Unknown';
      const zone_name = zoneCodeMatch ? zoneDesc.slice(zoneCodeMatch[0].length).trim() : zoneDesc;
      const lga = constraints.lga ?? '';

      // Extract lot area from propertyArea string (e.g. "450 m²")
      const areaMatch = (prop.propertyArea ?? '').match(/([\d.]+)/);
      const lot_area_sqm = areaMatch ? parseFloat(areaMatch[1]) : null;
      const min_lot_size_sqm = constraints.minLotSize ?? null;

      // Fetch permissibility for dwelling type check
      let permitted: string[] = [];
      let prohibited: string[] = [];
      if (zone_code !== 'Unknown' && lga) {
        try {
          const lepRes = await fetch(
            `/api/lep/permissibility?zone=${encodeURIComponent(zone_code)}&lga=${encodeURIComponent(lga)}`
          );
          if (lepRes.ok) {
            const lepData = await lepRes.json();
            if (lepData.covered && lepData.entries) {
              permitted = lepData.entries
                .filter((e: { permissibility: string }) => e.permissibility === 'Permitted')
                .map((e: { development_type: string }) => e.development_type);
              prohibited = lepData.entries
                .filter((e: { permissibility: string }) => e.permissibility === 'Prohibited')
                .map((e: { development_type: string }) => e.development_type);
            }
          }
        } catch {
          // Non-fatal
        }
      }

      const assessment = assessSubdivision({ zone_code, lot_area_sqm, min_lot_size_sqm, permitted, prohibited });

      setResult({
        address: prop.address ?? address,
        lga,
        zone_code,
        zone_name,
        lot_area_sqm,
        min_lot_size_sqm,
        fsr: constraints.maxFsr ?? null,
        height_m: constraints.maxHeight ?? null,
        permitted_dwelling_types: permitted.filter((u: string) =>
          ['dwelling', 'dual', 'multi', 'secondary', 'semi', 'attached', 'boarding', 'group'].some(k => u.toLowerCase().includes(k))
        ),
        subdivision_likely: assessment.likely,
        reason: assessment.reason,
        heritage_item: prop.heritage?.isHeritage ?? false,
        heritage_conservation_area: (prop.heritage?.heritageType ?? '').toLowerCase().includes('conservation'),
      });

      posthog.capture('tool_run', {
        tool: 'subdivision-check',
        source: 'seo_page',
        zone: zone_code,
        lga,
        verdict: assessment.likely,
        lot_area_sqm,
        min_lot_size_sqm,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  const verdictConfig = {
    yes: { icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200', label: 'Subdivision looks possible' },
    no: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50', border: 'border-red-200', label: 'Subdivision unlikely' },
    maybe: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Further investigation needed' },
  };

  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero + Search */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-8">
        <div className="flex items-center gap-2 mb-4">
          <Scissors className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            Free tool
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">
          Can I subdivide my property?
        </h1>
        <p className="text-gray-500 text-lg max-w-xl mb-8">
          Check your lot size against the minimum subdivision requirements for your zone.
          Find out if dual occupancy, Torrens title, or strata subdivision is possible —
          free, instant, for any NSW address.
        </p>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Enter a NSW address
          </label>
          <PropertySearch
            onAddressSelect={handleAddressSelect}
          />
        </div>
      </section>

      {/* Loading */}
      {loading && (
        <section className="max-w-3xl mx-auto px-6 pb-8">
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
            <div className="animate-spin w-6 h-6 border-2 border-teal-600 border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-sm text-gray-500">Checking subdivision eligibility...</p>
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
      {result && (() => {
        const verdict = verdictConfig[result.subdivision_likely];
        const VerdictIcon = verdict.icon;
        return (
          <section className="max-w-3xl mx-auto px-6 pb-12 space-y-4">
            {/* Verdict */}
            <div className={`${verdict.bg} rounded-xl border ${verdict.border} p-6`}>
              <div className="flex items-start gap-3">
                <VerdictIcon className={`w-6 h-6 ${verdict.color} flex-shrink-0 mt-0.5`} />
                <div>
                  <p className={`font-bold ${verdict.color} text-lg`}>{verdict.label}</p>
                  <p className="text-sm text-gray-700 mt-2 leading-relaxed">{result.reason}</p>
                </div>
              </div>
            </div>

            {/* Property details */}
            <div className="rounded-xl border border-gray-200 p-5">
              <p className="text-xs text-gray-400 mb-1">{result.lga} Council</p>
              <p className="text-sm text-gray-700 mb-3">{result.address}</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <p className="text-xs text-gray-400">Zone</p>
                  <p className="text-sm font-semibold text-gray-900">{result.zone_code}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Lot area</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {result.lot_area_sqm != null ? `${result.lot_area_sqm.toLocaleString()}m²` : 'Unknown'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Min lot size</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {result.min_lot_size_sqm != null ? `${result.min_lot_size_sqm}m²` : 'Unknown'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Max height</p>
                  {result.height_m != null ? (
                    <p className="text-sm font-semibold text-gray-900">{result.height_m}m</p>
                  ) : (
                    <p className="text-sm font-semibold text-gray-400">Not mapped</p>
                  )}
                </div>
              </div>
            </div>

            {/* Permitted dwelling types */}
            {result.permitted_dwelling_types.length > 0 && (
              <div className="rounded-xl border border-gray-200 p-5">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">
                  Permitted dwelling types in zone {result.zone_code}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {result.permitted_dwelling_types.map((use) => (
                    <span
                      key={use}
                      className="px-2.5 py-1 text-xs bg-teal-50 text-teal-700 rounded-full border border-teal-200"
                    >
                      {use}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Heritage warning */}
            {(result.heritage_item || result.heritage_conservation_area) && (
              <div className="bg-amber-50 rounded-xl border border-amber-200 p-4 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-amber-800 font-medium">Heritage constraints apply</p>
                  <p className="text-xs text-amber-600 mt-1">
                    {result.heritage_item ? 'This property is a heritage item. ' : ''}
                    {result.heritage_conservation_area ? 'This property is in a heritage conservation area. ' : ''}
                    Subdivision may require heritage impact assessment.
                  </p>
                </div>
              </div>
            )}

            {/* Disclaimer */}
            <div className="flex items-start gap-2 px-1">
              <Info className="w-4 h-4 text-gray-300 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-gray-400 leading-relaxed">
                This is a preliminary check based on LEP zoning and lot size data from the NSW Planning Portal.
                Actual subdivision eligibility depends on DCP controls, council policies, site geometry, access,
                and services. Consult a qualified town planner before proceeding.
              </p>
            </div>

            {/* CTAs */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Link
                href={`/assessment?address=${encodeURIComponent(result.address)}`}
                className="bg-slate-950 rounded-xl p-5 flex items-center justify-between hover:bg-slate-900 transition-colors"
              >
                <div>
                  <p className="text-white font-semibold text-sm">Full planning controls</p>
                  <p className="text-slate-400 text-xs mt-0.5">DCP setbacks, SEPP, overlays</p>
                </div>
                <ArrowRight className="w-4 h-4 text-teal-400" />
              </Link>
              <Link
                href={`/reports/conveyancing?address=${encodeURIComponent(result.address)}`}
                className="bg-slate-950 rounded-xl p-5 flex items-center justify-between hover:bg-slate-900 transition-colors"
              >
                <div>
                  <p className="text-white font-semibold text-sm">Property report</p>
                  <p className="text-slate-400 text-xs mt-0.5">Full disclosure PDF — $49</p>
                </div>
                <ArrowRight className="w-4 h-4 text-teal-400" />
              </Link>
            </div>
          </section>
        );
      })()}

      {/* SEO content (always visible when no result) */}
      {!result && !loading && (
        <section className="max-w-3xl mx-auto px-6 pb-12">
          <div className="bg-gray-50 rounded-xl border border-gray-100 p-8">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              Subdivision rules in NSW
            </h2>
            <div className="space-y-4 text-sm text-gray-600 leading-relaxed">
              <p>
                Whether you can subdivide your property in NSW depends on three things:
                your <strong>zone</strong> (does it permit dual occupancy or multi-dwelling housing?),
                your <strong>lot size</strong> (is it at least twice the LEP minimum lot size for Torrens title?),
                and your <strong>council&apos;s DCP</strong> (setbacks, access requirements, landscaping).
              </p>
              <p>
                <strong>Torrens title subdivision</strong> creates two fully independent lots with
                separate titles. This typically requires your lot to be at least twice the minimum
                lot size — e.g. 900m² if the minimum is 450m².
              </p>
              <p>
                <strong>Strata subdivision</strong> creates separate titles within the same lot
                boundary — common for attached dual occupancies or townhouses. Strata may be possible
                on lots smaller than the Torrens title threshold.
              </p>
              <p>
                <strong>Community title</strong> is used for larger developments (3+ lots) and
                includes shared areas managed by a community association.
              </p>
              <p>
                This tool checks your zone&apos;s permitted uses and compares your lot size to the
                LEP minimum. For a complete picture including DCP requirements, use the full
                planning controls check.
              </p>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/tools/zoning-check"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                Zoning check <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              <Link
                href="/check"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                CDC eligibility check <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              <Link
                href="/blog/can-i-build-a-granny-flat-nsw"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                Granny flat rules NSW <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </section>
      )}

      <SiteFooter />
    </main>
  );
}
