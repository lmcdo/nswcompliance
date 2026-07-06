import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'What Can I Build on 5 Acres in NSW? Rural Zoning Explained — PlotDetect',
  description:
    'What NSW rural zones (RU1, RU2, RU4, R5, RU5) allow you to build. Dwelling houses, secondary dwellings, farm buildings, tourist accommodation, and home businesses by zone.',
  keywords: [
    'what can I build on rural land NSW',
    'RU1 zoning what can I build',
    'rural property building rules NSW',
    '5 acres building NSW',
    'rural zoning explained NSW',
    'RU2 zoning NSW',
    'R5 large lot residential NSW',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Comprehensive rural zone comparison table */
function RuralZoneTable() {
  const uses = [
    'Dwelling house',
    'Secondary dwelling',
    'Farm buildings',
    'Tourist accommodation',
    'Home business',
    'Intensive agriculture',
    'Subdivision potential',
  ];

  const zones = [
    {
      code: 'RU1',
      name: 'Primary Production',
      description: 'Broad-acre farming and grazing. The most common rural zone.',
      minLot: '40ha typical (varies widely)',
      values: ['P', 'V', 'P', 'C', 'C', 'C', 'Very limited'],
    },
    {
      code: 'RU2',
      name: 'Rural Landscape',
      description: 'Scenic rural areas. Agriculture with landscape protection.',
      minLot: '10-40ha typical',
      values: ['P', 'V', 'P', 'C', 'C', 'X', 'Limited'],
    },
    {
      code: 'RU4',
      name: 'Primary Production Small Lots',
      description: 'Small-scale rural and hobby farms.',
      minLot: '2-10ha typical',
      values: ['P', 'C', 'P', 'V', 'C', 'V', 'Possible'],
    },
    {
      code: 'R5',
      name: 'Large Lot Residential',
      description: 'Rural-residential lifestyle blocks.',
      minLot: '0.4-4ha typical',
      values: ['P', 'C', 'C', 'X', 'C', 'X', 'Possible'],
    },
    {
      code: 'RU5',
      name: 'Village',
      description: 'Small rural townships. Most flexible rural zone.',
      minLot: '450-2,000sqm typical',
      values: ['P', 'C', 'V', 'C', 'P', 'X', 'Good'],
    },
  ];

  function statusBadge(val: string) {
    if (val === 'P')
      return (
        <span className="inline-flex items-center text-xs font-medium text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
          Permitted
        </span>
      );
    if (val === 'C')
      return (
        <span className="inline-flex items-center text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
          With consent
        </span>
      );
    if (val === 'X')
      return (
        <span className="inline-flex items-center text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded">
          Prohibited
        </span>
      );
    if (val === 'V')
      return (
        <span className="inline-flex items-center text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
          Varies by LEP
        </span>
      );
    return <span className="text-xs text-slate-600">{val}</span>;
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        NSW rural zones — what you can build (quick reference)
      </p>
      <div className="overflow-x-auto -mx-2">
        <table className="w-full text-sm border-collapse min-w-[700px]">
          <thead>
            <tr className="border-b-2 border-slate-200">
              <th className="text-left py-3 pr-3 font-semibold text-slate-900">
                Land use
              </th>
              {zones.map((z) => (
                <th
                  key={z.code}
                  className="text-center py-3 px-2 font-semibold text-slate-900"
                >
                  <div>{z.code}</div>
                  <div className="text-xs font-normal text-slate-400 mt-0.5">
                    {z.name}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {uses.map((use, i) => (
              <tr key={use} className="border-b border-slate-100">
                <td className="py-3 pr-3 font-medium text-slate-800">{use}</td>
                {zones.map((z) => (
                  <td key={z.code} className="py-3 px-2 text-center">
                    {statusBadge(z.values[i])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap gap-4 mt-4 text-xs text-slate-500">
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-teal-500 mr-1" />
          Permitted without consent
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500 mr-1" />
          Permitted with consent (DA required)
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />
          Prohibited
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-slate-400 mr-1" />
          Varies by council LEP
        </span>
      </div>
    </div>
  );
}

/** Visual 2 — Minimum lot size examples by region */
function MinLotSizeExamples() {
  const examples = [
    {
      region: 'Blue Mountains',
      zone: 'RU2',
      minLot: '10ha',
      note: 'Scenic protection limits subdivision',
    },
    {
      region: 'Shoalhaven (coastal)',
      zone: 'R5',
      minLot: '0.4ha (4,000sqm)',
      note: 'Near villages, popular with tree changers',
    },
    {
      region: 'Wingecarribee (Southern Highlands)',
      zone: 'RU1',
      minLot: '40ha',
      note: 'Broad-acre farming — subdivision near impossible',
    },
    {
      region: 'Central Coast (hinterland)',
      zone: 'RU4',
      minLot: '2ha',
      note: 'Small hobby farms, secondary dwelling possible',
    },
    {
      region: 'Clarence Valley',
      zone: 'RU1',
      minLot: '100ha',
      note: 'Very large minimum — common in remote areas',
    },
    {
      region: 'Port Stephens',
      zone: 'R5',
      minLot: '1ha',
      note: 'Rural-residential near coast',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Minimum lot sizes — examples by region
      </p>
      <div className="grid sm:grid-cols-2 gap-3">
        {examples.map((e) => (
          <div
            key={e.region}
            className="bg-white rounded-xl border border-slate-100 p-4"
          >
            <p className="text-sm font-bold text-slate-900">{e.region}</p>
            <p className="text-xs text-slate-500 mt-1">
              {e.zone} &mdash; min lot size: {e.minLot}
            </p>
            <p className="text-xs text-slate-400 mt-1 italic">{e.note}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-3 italic">
        Minimum lot sizes vary by lot, not just by zone. Always check the
        specific lot size map in the applicable LEP.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function WhatCanIBuildRuralPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="What can I build on 5 acres in NSW? Rural zoning explained"
        description="RU1, RU2, RU4, R5 — what each rural zone permits, minimum lot sizes by region, and common misunderstandings about rural land use in NSW."
        slug="what-can-i-build-rural-land-nsw"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-700">
            Planning Rules
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          What can I build on 5 acres in NSW? Rural zoning explained
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          The answer depends entirely on the zone. Five acres (roughly 2
          hectares) in RU1 is a fragment of a farming lot. Five acres in R5 is a
          generous lifestyle block. The same area of land, in different zones,
          permits very different things. Here is what each rural zone allows.
        </p>
      </div>

      {/* ========== IMMEDIATE VALUE: the zone table ========== */}
      <RuralZoneTable />

      {/* Body */}
      <div className="space-y-10">
        {/* How to find your zone */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How to find your zone
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Every lot in NSW has a zone assigned in the Local Environmental Plan
            (LEP). To find yours:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-slate-700 leading-relaxed">
            <li>
              Go to the{' '}
              <a
                href="https://www.planningportal.nsw.gov.au/spatialviewer"
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
              >
                NSW Planning Portal Spatial Viewer
              </a>
            </li>
            <li>Search by address or lot/DP number</li>
            <li>
              The zoning layer shows the zone code (e.g., RU1, R5) and the
              zone name
            </li>
            <li>
              Check the land use table in the LEP for the full list of
              permitted, consent, and prohibited uses
            </li>
          </ol>
          <p className="text-slate-700 leading-relaxed">
            Or run a{' '}
            <Link
              href="/check"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              free compliance check on PlotDetect
            </Link>{' '}
            to see the zone, permitted uses, height limits, floor space ratio,
            and applicable DCP controls for any NSW address.
          </p>
        </section>

        {/* Minimum lot size */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Minimum lot size &mdash; the hidden constraint
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Every lot has a minimum lot size set in the LEP. This is not just
            about subdivision. In some councils, the minimum lot size also
            affects whether you can build a second dwelling, whether your lot
            qualifies for certain land uses, and whether your development
            application will be supported.
          </p>
          <p className="text-slate-700 leading-relaxed">
            If your 5-acre lot is in a zone with a 40-hectare minimum lot size,
            you own less than 5% of the minimum. Subdivision is impossible. A
            secondary dwelling may also be restricted. The minimum lot size is
            the single most important number for rural property feasibility
            after the zone itself.
          </p>

          <MinLotSizeExamples />

          <p className="text-slate-700 leading-relaxed">
            For a full guide to subdivision rules and minimum lot sizes, see{' '}
            <Link
              href="/blog/subdivide-property-nsw-minimum-lot-sizes"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Can I subdivide my property in NSW?
            </Link>
          </p>
        </section>

        {/* Permitted with consent */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What &ldquo;permitted with consent&rdquo; actually means
          </h2>
          <p className="text-slate-700 leading-relaxed">
            When a land use is listed as &ldquo;permitted with consent,&rdquo;
            it means you <em>can</em> apply for development consent (a DA), but
            approval is not guaranteed. Council assesses the DA against the LEP
            objectives, DCP controls, and any applicable SEPPs.
          </p>
          <p className="text-slate-700 leading-relaxed">
            &ldquo;Permitted without consent&rdquo; (also called exempt
            development) means you can proceed without a DA, provided you meet
            the criteria in the State Environmental Planning Policy (Exempt and
            Complying Development Codes) 2008 &mdash; commonly known as the
            Codes SEPP.
          </p>
          <p className="text-slate-700 leading-relaxed">
            &ldquo;Prohibited&rdquo; means the use cannot be approved under
            any circumstances in that zone. No DA will change this. If tourist
            accommodation is prohibited in your zone, that plan for a farm
            stay business will not work on that lot.
          </p>
        </section>

        {/* Common misunderstandings */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Common misunderstandings
          </h2>

          <div className="space-y-4">
            <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
              <p className="text-sm font-semibold text-slate-900 mb-2">
                &ldquo;RU1 means I can do anything agricultural&rdquo;
              </p>
              <p className="text-sm text-slate-700 leading-relaxed">
                Not quite. Extensive agriculture (grazing, cropping) is
                generally permitted without consent in RU1. But intensive
                agriculture &mdash; feedlots, intensive poultry, large-scale
                greenhouses &mdash; typically requires development consent and
                may face significant assessment hurdles around noise, odour,
                and traffic.
              </p>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
              <p className="text-sm font-semibold text-slate-900 mb-2">
                &ldquo;I can put a granny flat on any rural property&rdquo;
              </p>
              <p className="text-sm text-slate-700 leading-relaxed">
                Under SEPP (Housing) 2021, secondary dwellings up to 60sqm are
                permitted as complying development on lots where a dwelling
                house is permitted. But the lot must be in a zone that permits
                secondary dwellings, and some councils further restrict this
                through DCP controls or minimum lot size requirements. In RU1,
                secondary dwellings may not be listed as a permitted use at
                all. Check the specific LEP land use table for your property.
                See our guide on{' '}
                <Link
                  href="/blog/can-i-build-a-granny-flat-nsw"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  granny flats in NSW
                </Link>
                .
              </p>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
              <p className="text-sm font-semibold text-slate-900 mb-2">
                &ldquo;5 acres is plenty of room to subdivide&rdquo;
              </p>
              <p className="text-sm text-slate-700 leading-relaxed">
                Room is not the issue. The minimum lot size is. If the LEP sets
                a 40ha minimum for your zone, your 2ha lot cannot be
                subdivided regardless of how much space it has. Minimum lot
                size is set per lot in the LEP maps and varies enormously
                across NSW.
              </p>
            </div>
          </div>
        </section>

        {/* Farm stay / tourism */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Farm stay and tourism potential
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Farm stay accommodation and tourist cabins are popular income
            strategies for rural properties. In RU1 and RU2, tourist and
            visitor accommodation is generally permitted with consent. In R5
            (Large Lot Residential), it is typically prohibited.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Even where permitted, a DA is required, and council will assess
            traffic, parking, waste management, bushfire access, and amenity
            impacts. Bushfire-prone properties face additional requirements
            under <em>Planning for Bush Fire Protection 2019</em> for
            accommodation of vulnerable users.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Short-term rental accommodation (Airbnb-style) may be subject to
            additional state rules under the SEPP (Housing) 2021 provisions
            for short-term rental accommodation, including day limits in some
            LGAs. Check your council&apos;s specific rules.
          </p>
        </section>

        {/* Other considerations */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Other constraints that affect what you can build
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The zone tells you what is permitted in principle. Other overlays
            and constraints determine what is feasible in practice:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Bushfire Attack Level (BAL)</span>{' '}
              &mdash; determines construction standards and costs. See our{' '}
              <Link
                href="/blog/bushfire-attack-level-bal-property-buyers"
                className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
              >
                BAL guide for buyers
              </Link>
            </li>
            <li>
              <span className="font-medium">Flood planning area</span> &mdash;
              may restrict habitable floor levels and building footprint
            </li>
            <li>
              <span className="font-medium">Biodiversity values</span> &mdash;
              if the Biodiversity Values Map intersects the lot, clearing
              triggers the Biodiversity Offsets Scheme
            </li>
            <li>
              <span className="font-medium">Heritage</span> &mdash; Aboriginal
              or European heritage listings add assessment requirements
            </li>
            <li>
              <span className="font-medium">
                On-site sewage management
              </span>{' '}
              &mdash; no sewer connection means OSSM system required
            </li>
            <li>
              <span className="font-medium">Water supply</span> &mdash;
              bore licence, rainwater tanks, riparian setbacks
            </li>
            <li>
              <span className="font-medium">Road access</span> &mdash;
              legal access required for building approval
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            For a complete pre-purchase checklist covering all seven
            infrastructure and planning checks, see our{' '}
            <Link
              href="/blog/tree-change-checklist-nsw-planning"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              tree change checklist
            </Link>
            .
          </p>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check what your zone permits
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect shows the zone, permitted uses, minimum lot size, and
              applicable planning controls for any NSW property. Enter an
              address to see what the planning rules allow on your lot.
            </p>
            <TrackedLink
              href="/check"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="what-can-i-build-rural-land-nsw"
              cta="check_address"
            >
              Check a property
              <ArrowRight className="w-4 h-4" />
            </TrackedLink>
          </div>
        </section>

        {/* Back link */}
        <div className="pt-8 border-t border-slate-100">
          <Link
            href="/blog"
            className="text-sm text-slate-500 hover:text-teal-600 transition-colors"
          >
            &larr; Back to Insights
          </Link>
        </div>
      </div>
    </article>
  );
}
