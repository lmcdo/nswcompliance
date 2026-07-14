'use client';

/**
 * /tools/zoning-check — Free Zoning Check Tool
 *
 * Target keywords: "zoning check" (880/mo), "what zone is my property" (1,000/mo),
 * "what is my property zoned for" (110/mo), "property zoning nsw" (40/mo)
 * Combined: ~2,030/mo
 *
 * Funnel: Free instant result → /assessment for full planning controls
 */

import React, { useState } from 'react';
import Link from 'next/link';
import posthog from 'posthog-js';
import { PropertySearch } from '@/components/property/PropertySearch';
import { MapPin, ArrowRight, CheckCircle2, XCircle, AlertTriangle, Building2 } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

interface ZoneResult {
  address: string;
  zone_code: string;
  zone_name: string;
  lga: string;
  permitted: string[];
  prohibited: string[];
  fsr: number | null;
  height_m: number | null;
  min_lot_size_sqm: number | null;
  heritage_item: boolean;
  heritage_conservation_area: boolean;
}

function deslug(devType: string): string {
  const words = devType.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export default function ZoningCheckPage() {
  const [result, setResult] = useState<ZoneResult | null>(null);
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

      // Extract zone code from zoneDescription (e.g. "R2 Low Density Residential" → "R2")
      const zoneDesc: string = prop.zoneDescription ?? '';
      const zoneCodeMatch = zoneDesc.match(/^([A-Z][A-Z0-9]*(?:\.\d+)?)\b/);
      const zone_code = zoneCodeMatch?.[1] ?? zoneDesc.split(' ')[0] ?? 'Unknown';
      const zone_name = zoneCodeMatch ? zoneDesc.slice(zoneCodeMatch[0].length).trim() : zoneDesc;
      const lga = constraints.lga ?? '';

      // Fetch permissibility using zone + lga params (the endpoint requires both)
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
                .filter((e: { permissibility: string }) => e.permissibility === 'permitted')
                .map((e: { development_type: string }) => e.development_type);
              prohibited = lepData.entries
                .filter((e: { permissibility: string }) => e.permissibility === 'prohibited')
                .map((e: { development_type: string }) => e.development_type);
            }
          }
        } catch {
          // Non-fatal — permissibility section just won't render
        }
      }

      setResult({
        address: prop.address ?? address,
        zone_code,
        zone_name,
        lga,
        permitted,
        prohibited,
        fsr: constraints.maxFsr ?? null,
        height_m: constraints.maxHeight ?? null,
        min_lot_size_sqm: constraints.minLotSize ?? null,
        heritage_item: prop.heritage?.isHeritage ?? false,
        heritage_conservation_area: (prop.heritage?.heritageType ?? '').toLowerCase().includes('conservation'),
      });

      posthog.capture('tool_run', {
        tool: 'zoning-check',
        source: 'seo_page',
        zone: zone_code,
        lga,
        has_permissibility: permitted.length > 0,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero + Search */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-8">
        <div className="flex items-center gap-2 mb-4">
          <MapPin className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            Free tool
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">
          What zone is my property?
        </h1>
        <p className="text-gray-500 text-lg max-w-xl mb-8">
          Check the zoning, permitted land uses, height limit, floor space ratio, and heritage
          status for any NSW address. Free, instant, from live government data.
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
            <p className="text-sm text-gray-500">Checking zoning data...</p>
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
          {/* Address + Zone */}
          <div className="bg-teal-50 rounded-xl border border-teal-200 p-6">
            <p className="text-xs text-teal-600 font-medium mb-1">{result.lga} Council</p>
            <p className="text-sm text-gray-700 mb-3">{result.address}</p>
            <div className="flex items-baseline gap-3">
              <span className="text-2xl font-bold text-gray-900">{result.zone_code}</span>
              <span className="text-lg text-gray-600">{result.zone_name}</span>
            </div>
          </div>

          {/* Key numbers */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-xs text-gray-400 mb-1">Max height</p>
              {result.height_m != null ? (
                <p className="text-xl font-bold text-gray-900">{result.height_m}m</p>
              ) : (
                <>
                  <p className="text-lg font-bold text-gray-900">Not mapped</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">Check DCP for height controls</p>
                </>
              )}
            </div>
            <div className="rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-xs text-gray-400 mb-1">FSR</p>
              {result.fsr != null ? (
                <p className="text-xl font-bold text-gray-900">{result.fsr}:1</p>
              ) : (
                <>
                  <p className="text-lg font-bold text-gray-900">Not mapped</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">Check DCP for FSR controls</p>
                </>
              )}
            </div>
            <div className="rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-xs text-gray-400 mb-1">Min lot size</p>
              {result.min_lot_size_sqm != null ? (
                <p className="text-xl font-bold text-gray-900">{result.min_lot_size_sqm}m²</p>
              ) : (
                <>
                  <p className="text-lg font-bold text-gray-900">Not mapped</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">Check DCP for lot size controls</p>
                </>
              )}
            </div>
          </div>

          {/* Heritage flags */}
          {(result.heritage_item || result.heritage_conservation_area) && (
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                {result.heritage_item && (
                  <p className="text-sm text-amber-800 font-medium">Heritage item</p>
                )}
                {result.heritage_conservation_area && (
                  <p className="text-sm text-amber-800 font-medium">Heritage conservation area</p>
                )}
                <p className="text-xs text-amber-600 mt-1">
                  Additional controls apply. Check the full assessment for details.
                </p>
              </div>
            </div>
          )}

          {/* Permitted uses */}
          {result.permitted.length > 0 && (
            <div className="rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Permitted with consent
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.permitted.slice(0, 12).map((use) => (
                  <span
                    key={use}
                    className="px-2.5 py-1 text-xs bg-green-50 text-green-700 rounded-full border border-green-200"
                  >
                    {deslug(use)}
                  </span>
                ))}
                {result.permitted.length > 12 && (
                  <span className="px-2.5 py-1 text-xs bg-gray-50 text-gray-500 rounded-full border border-gray-200">
                    +{result.permitted.length - 12} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Prohibited uses */}
          {result.prohibited.length > 0 && (
            <div className="rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <XCircle className="w-4 h-4 text-red-500" />
                Prohibited
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.prohibited.slice(0, 8).map((use) => (
                  <span
                    key={use}
                    className="px-2.5 py-1 text-xs bg-red-50 text-red-600 rounded-full border border-red-200"
                  >
                    {deslug(use)}
                  </span>
                ))}
                {result.prohibited.length > 8 && (
                  <span className="px-2.5 py-1 text-xs bg-gray-50 text-gray-500 rounded-full border border-gray-200">
                    +{result.prohibited.length - 8} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* CTA: See full controls */}
          <div className="bg-slate-950 rounded-xl p-6 flex items-center justify-between">
            <div>
              <p className="text-white font-semibold text-sm">Want the full picture?</p>
              <p className="text-slate-400 text-xs mt-1">
                DCP setbacks, parking rates, SEPP requirements, flood depth, bushfire status, and more.
              </p>
            </div>
            <Link
              href={`/assessment?address=${encodeURIComponent(result.address)}`}
              className="flex-shrink-0 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
            >
              Full assessment <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      )}

      {/* SEO content (always visible) */}
      {!result && !loading && (
        <section className="max-w-3xl mx-auto px-6 pb-12">
          <div className="bg-gray-50 rounded-xl border border-gray-100 p-8">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              How zoning works in NSW
            </h2>
            <div className="space-y-4 text-sm text-gray-600 leading-relaxed">
              <p>
                Every property in NSW is assigned a zone under the Local Environmental Plan (LEP)
                for its council area. The zone determines what you can and cannot build —
                from dwelling houses and granny flats to shops and industrial uses.
              </p>
              <p>
                Common residential zones include <strong>R1 General Residential</strong> (widest
                range of housing types), <strong>R2 Low Density Residential</strong> (detached
                houses, secondary dwellings), and <strong>R3 Medium Density Residential</strong>
                (townhouses, apartments up to 3 storeys).
              </p>
              <p>
                Beyond the zone, your property&apos;s development potential depends on numeric controls
                like <strong>floor space ratio</strong> (how much you can build relative to lot size),
                <strong> building height</strong> (maximum height in metres), and
                <strong> minimum lot size</strong> (for subdivision or dual occupancy).
              </p>
              <p>
                The NSW Planning Portal shows your zone, but it doesn&apos;t explain what it means
                for your specific plans. This tool gives you the zone, the key numbers, and
                the permitted uses — so you know what&apos;s possible before talking to a planner.
              </p>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/assessment"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                Full planning controls check <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              <Link
                href="/tools/subdivision-check"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                Can I subdivide? <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              <Link
                href="/check"
                className="text-sm text-teal-600 hover:text-teal-500 font-medium flex items-center gap-1"
              >
                CDC eligibility check <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </section>
      )}

      <SiteFooter />
    </main>
  );
}
