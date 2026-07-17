'use client';

// prior-art-checked: this file is the EXISTING SeppContextCard extracted verbatim
// from app/reports/intelligence-brief/page.tsx (its only prior home) so its
// zone-family copy can be render-tested; HousingSEPPEligibilityCard /
// ConstraintArithmeticCard render different data (eligibility table / capacity),
// not this "why the SEPP forms don't reach this lot" explainer. No new fetcher.

import { zoneFamily } from '@/lib/regulatory-constants';

// Cross-section planning context the intelligence-brief page assembles — the
// card only needs the zone identity fields.
export interface SeppContextPlanningContext {
  zone?: string;
  zoneFull?: string;
  zoneEpi?: string;
  legislationUrl?: string;
}

// Is this a residential zone where the Housing-SEPP residential forms can apply?
function isResidentialZone(zone?: string): boolean {
  return /^(R1|R2|R3|R4|R5|RU5)\b/.test((zone || '').trim());
}

// When the Housing-SEPP residential forms don't apply, don't say "doesn't apply" —
// explain WHY with the lot's real zone + instrument, and what it means for housing
// on this land. The explanation branches by zone FAMILY: the shop-top sentence is
// true on a centres/business zone and wrong on a conservation or rural one. Never
// assert what a specific council's land-use table permits.
export function SeppContextCard({ ctx }: { ctx: SeppContextPlanningContext }) {
  const zoneLabel = ctx.zone
    ? `${ctx.zone}${ctx.zoneFull ? ` (${ctx.zoneFull})` : ''}`
    : 'this zone';
  const instrument = ctx.zoneEpi || 'the Local Environmental Plan';
  const residential = isResidentialZone(ctx.zone);
  const family = zoneFamily(ctx.zone ?? '');
  const familyTail =
    family === 'rural' ? 'a rural zone'
    : family === 'conservation' ? 'a conservation zone'
    : 'not a residential zone';
  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      <div className="px-5 py-4 border-b border-slate-100">
        <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">Housing SEPP — Low &amp; Mid-Rise</h3>
        <p className="text-xs text-slate-500 mt-0.5">Denser housing forms the policy permits, and whether they reach this lot</p>
      </div>
      <div className="px-5 py-4 text-sm text-slate-700 leading-relaxed space-y-2">
        {residential ? (
          <p>
            This lot sits in <span className="font-medium text-slate-900">{zoneLabel}</span> under{' '}
            {ctx.legislationUrl
              ? <a href={ctx.legislationUrl} target="_blank" rel="noopener noreferrer" className="text-teal-600 underline [overflow-wrap:anywhere]">{instrument}</a>
              : instrument}. It&apos;s a residential zone, but the Low &amp; Mid-Rise Housing standards
            (terraces, townhouses, manor houses and residential flats) couldn&apos;t be loaded for
            it — re-run the brief, or check the standards directly in the instrument above.
          </p>
        ) : (
          <>
            <p>
              This lot is zoned <span className="font-medium text-slate-900">{zoneLabel}</span> under{' '}
              {ctx.legislationUrl
                ? <a href={ctx.legislationUrl} target="_blank" rel="noopener noreferrer" className="text-teal-600 underline [overflow-wrap:anywhere]">{instrument}</a>
                : instrument} — {familyTail}.
            </p>
            {family === 'rural' && (
              <p>
                The Low &amp; Mid-Rise Housing reforms (terraces, townhouses, manor houses, residential
                flats) reach only the residential zones <span className="font-medium">R1–R4</span>, so they
                don&apos;t apply here. What housing is permitted on rural land is set by the zone&apos;s
                land-use table in the LEP.
              </p>
            )}
            {family === 'conservation' && (
              <p>
                The Low &amp; Mid-Rise Housing reforms (terraces, townhouses, manor houses, residential
                flats) reach only the residential zones <span className="font-medium">R1–R4</span>, so they
                don&apos;t apply here. Whether a dwelling house or other housing is permitted on this land
                is set by the zone&apos;s land-use table in the LEP — see the instrument linked above.
              </p>
            )}
            {family === 'centres' && (
              <p>
                The Low &amp; Mid-Rise Housing reforms (terraces, townhouses, manor houses, residential
                flats) reach only the residential zones <span className="font-medium">R1–R4</span>, so they
                don&apos;t apply here. On a centre/business zone like this, housing is delivered through the
                zone&apos;s own permitted uses — typically <span className="font-medium">shop-top housing</span>{' '}
                above ground-floor retail — rather than the low-and-mid-rise pathway.
              </p>
            )}
            {(family === 'other' || family === 'residential') && (
              <p>
                The Low &amp; Mid-Rise Housing reforms (terraces, townhouses, manor houses, residential
                flats) reach only the residential zones <span className="font-medium">R1–R4</span>, so they
                don&apos;t apply here. See the zone&apos;s land-use table in the instrument above for what
                this land permits.
              </p>
            )}
            <p className="text-slate-500">
              See the land use table in the instrument above for what this specific lot permits, and the
              Development Capacity card for the buildable envelope.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
