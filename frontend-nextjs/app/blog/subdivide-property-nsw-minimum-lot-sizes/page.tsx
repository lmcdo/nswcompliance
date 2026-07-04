import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Can I Subdivide My Property in NSW? Minimum Lot Sizes Explained — PlotDetect',
  description:
    'How to determine if your NSW property can be subdivided. Minimum lot sizes, subdivision types, the DA process, common blockers, and indicative costs.',
  keywords: [
    'can I subdivide my property NSW',
    'minimum lot size NSW',
    'subdivision rules NSW',
    'Torrens title subdivision NSW',
    'strata subdivision NSW',
    'how to subdivide land NSW',
    'subdivision costs NSW',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Subdivision decision tree */
function SubdivisionDecisionTree() {
  const steps = [
    {
      question: 'What zone is your property in?',
      detail:
        'Find the zone code (e.g., R2, R3, R5, RU1, RU4) on the Planning Portal or PlotDetect.',
      outcomes: null,
    },
    {
      question: 'What is the minimum lot size for your zone?',
      detail:
        'Check the Lot Size Map in the LEP. This varies by lot, not just by zone.',
      outcomes: null,
    },
    {
      question: 'Does your lot meet the minimum for two lots?',
      detail:
        'Both resulting lots must meet or exceed the minimum lot size. A 700sqm lot with a 300sqm minimum can create two 350sqm lots.',
      outcomes: [
        { label: 'Yes', result: 'Subdivision may be possible', ok: true },
        {
          label: 'No',
          result: 'Subdivision cannot be approved',
          ok: false,
        },
      ],
    },
    {
      question: 'Are there constraints or overlays?',
      detail:
        'Heritage, flooding, bushfire, biodiversity, easements, and access can all block or complicate subdivision.',
      outcomes: [
        {
          label: 'No major constraints',
          result: 'Proceed with DA or CDC application',
          ok: true,
        },
        {
          label: 'Constraints present',
          result: 'May still be possible — assess each constraint',
          ok: null,
        },
      ],
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Can you subdivide? Decision pathway
      </p>
      <div className="relative">
        <div className="absolute left-4 top-4 bottom-4 w-0.5 bg-slate-200" />
        <div className="space-y-6">
          {steps.map((s, i) => (
            <div key={i} className="relative pl-12">
              <div className="absolute left-2 top-1 w-5 h-5 rounded-full bg-violet-500 text-white text-xs font-bold flex items-center justify-center ring-4 ring-white">
                {i + 1}
              </div>
              <p className="text-sm font-bold text-slate-900">{s.question}</p>
              <p className="text-sm text-slate-600 mt-1">{s.detail}</p>
              {s.outcomes && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {s.outcomes.map((o) => (
                    <div
                      key={o.label}
                      className={`text-xs px-3 py-1.5 rounded-lg border ${
                        o.ok === true
                          ? 'border-teal-200 bg-teal-50 text-teal-700'
                          : o.ok === false
                            ? 'border-red-200 bg-red-50 text-red-700'
                            : 'border-amber-200 bg-amber-50 text-amber-700'
                      }`}
                    >
                      <span className="font-semibold">{o.label}:</span>{' '}
                      {o.result}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Visual 2 — Cost breakdown */
function SubdivisionCostBreakdown() {
  const costs = [
    {
      item: 'Development application (DA) fees',
      range: '$2,000 — $10,000',
      note: 'Council fees based on estimated development cost',
    },
    {
      item: 'Surveyor (subdivision plan)',
      range: '$5,000 — $15,000',
      note: 'Registered surveyor to prepare subdivision plan',
    },
    {
      item: 'Section 7.12 / s94 contributions',
      range: '$20,000 — $80,000+',
      note: 'Infrastructure contributions to council. Varies enormously by LGA',
    },
    {
      item: 'Service connections (sewer, water, power)',
      range: '$10,000 — $50,000',
      note: 'Per lot. Rural lots without reticulated services cost more',
    },
    {
      item: 'Stormwater drainage',
      range: '$5,000 — $30,000',
      note: 'On-site detention may be required',
    },
    {
      item: 'Road / driveway works',
      range: '$5,000 — $40,000',
      note: 'New crossover, kerb and gutter, road widening',
    },
    {
      item: 'Legal and registration fees',
      range: '$2,000 — $5,000',
      note: 'Solicitor + NSW Land Registry Services registration',
    },
    {
      item: 'Consultant reports (if required)',
      range: '$2,000 — $15,000',
      note: 'Bushfire, flood, geotech, arborist, heritage, traffic',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Indicative subdivision costs (two-lot Torrens title)
      </p>
      <div className="space-y-3">
        {costs.map((c) => (
          <div
            key={c.item}
            className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4 bg-white rounded-xl border border-slate-100 p-4"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900">{c.item}</p>
              <p className="text-xs text-slate-400 mt-0.5">{c.note}</p>
            </div>
            <p className="text-sm font-bold text-slate-700 whitespace-nowrap">
              {c.range}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-xl bg-violet-50 border border-violet-200 p-4">
        <p className="text-sm font-bold text-violet-900">
          Typical total: $50,000 — $200,000+
        </p>
        <p className="text-xs text-violet-700 mt-1">
          Costs vary enormously by location, lot size, and site constraints.
          Section 7.12 contributions alone can exceed $80,000 in some metro
          councils.
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function SubdividePropertyPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Can I subdivide my property in NSW? Minimum lot sizes explained"
        description="How to find your minimum lot size, the three types of subdivision, common blockers, costs, and the dual occupancy pathway."
        slug="subdivide-property-nsw-minimum-lot-sizes"
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
          Can I subdivide my property in NSW? Minimum lot sizes explained
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Whether you can subdivide depends on three things: your zone, your
          minimum lot size, and site constraints. If both resulting lots meet
          the minimum lot size and no overlay blocks the proposal, subdivision
          is generally possible. Here is how to work through the decision.
        </p>
      </div>

      {/* ========== IMMEDIATE VALUE: the decision tree ========== */}
      <SubdivisionDecisionTree />

      {/* Body */}
      <div className="space-y-10">
        {/* What minimum lot size means */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What minimum lot size means
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Every lot in NSW has a minimum lot size set in the Local
            Environmental Plan (LEP). This number defines the smallest lot that
            can be created through subdivision. It is not a suggestion &mdash;
            it is a legal constraint. A subdivision that produces a lot smaller
            than the minimum cannot be approved.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Minimum lot sizes vary by zone and by location within the zone. In
            an R2 (Low Density Residential) zone, the minimum might be 300sqm
            in one council and 600sqm in another. In RU1 (Primary Production),
            it can be 40 hectares, 100 hectares, or even larger. The number is
            set per lot in the LEP&apos;s Lot Size Map &mdash; not just per
            zone.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For a simple two-lot subdivision, both resulting lots must meet the
            minimum. If your lot is 800sqm and the minimum is 450sqm, you
            cannot create two lots because neither would be 450sqm. If the
            minimum is 300sqm, you could create a 400sqm and a 400sqm lot, or
            a 500sqm and a 300sqm lot.
          </p>
        </section>

        {/* How to find your minimum lot size */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How to find your minimum lot size
          </h2>
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
              Turn on the &ldquo;Lot Size Map&rdquo; layer under the LEP
              section
            </li>
            <li>
              The minimum lot size for your specific lot is shown on the map
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
            &mdash; the minimum lot size is included alongside zoning, height,
            FSR, and all other LEP controls.
          </p>
        </section>

        {/* Types of subdivision */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Types of subdivision
          </h2>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Torrens title subdivision
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The most common type. Creates separate freehold lots, each with
                its own title. Each lot is independently owned, has its own
                street address, and can be sold separately. Requires a
                subdivision plan prepared by a registered surveyor, DA approval
                (or CDC in some cases), and registration with NSW Land Registry
                Services.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Strata subdivision
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Creates separate lots within a shared structure or shared land.
                Commonly used for apartments and townhouses, but also used for
                duplexes and dual occupancies. Each lot has its own strata
                title. A strata scheme is created with by-laws governing common
                areas. Strata levies apply even for two-lot schemes.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Community title subdivision
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A hybrid between Torrens and strata. Creates individual lots
                with shared community facilities (driveways, open space,
                services). More complex than Torrens title and less common for
                small subdivisions. Typically used for larger estates,
                eco-villages, and rural-residential developments.
              </p>
            </div>
          </div>
        </section>

        {/* The subdivision process */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The subdivision process
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A standard Torrens title subdivision follows this sequence:
          </p>
          <ol className="list-decimal list-inside space-y-3 text-slate-700 leading-relaxed">
            <li>
              <span className="font-medium">Pre-DA check:</span> Confirm
              zoning, minimum lot size, and any overlays. This is where most
              subdivisions are killed &mdash; before they start.
            </li>
            <li>
              <span className="font-medium">
                Engage a surveyor and planner:
              </span>{' '}
              The surveyor prepares the subdivision plan. A planner may be
              needed for the Statement of Environmental Effects and any
              consultant reports.
            </li>
            <li>
              <span className="font-medium">
                Lodge DA (or CDC application):
              </span>{' '}
              Some simple two-lot subdivisions can go through the Complying
              Development Certificate (CDC) pathway via a private certifier,
              which is faster. Most require a DA to council.
            </li>
            <li>
              <span className="font-medium">Assessment and approval:</span>{' '}
              Council assesses against the LEP, DCP, and any applicable SEPPs.
              Conditions of consent may require infrastructure upgrades,
              service connections, stormwater works, and s7.12 contributions.
            </li>
            <li>
              <span className="font-medium">
                Complete conditions and construct:
              </span>{' '}
              Satisfy all conditions of consent &mdash; service connections,
              road works, drainage, landscaping.
            </li>
            <li>
              <span className="font-medium">Subdivision certificate:</span>{' '}
              Council (or a certifier) issues a subdivision certificate
              confirming all conditions are met.
            </li>
            <li>
              <span className="font-medium">Registration:</span> Lodge the
              subdivision plan and certificate with NSW Land Registry Services.
              New titles are created.
            </li>
          </ol>
          <p className="text-slate-700 leading-relaxed">
            Timeline: 6&ndash;18 months from DA lodgement to registration is
            typical. Complex sites with constraints can take longer.
          </p>
        </section>

        {/* Common blockers */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Common blockers
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Even where the lot size arithmetic works, other factors can block
            or significantly complicate subdivision:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Heritage listing</span> &mdash;
              heritage items or heritage conservation areas add assessment
              requirements and may restrict the form of subdivision
            </li>
            <li>
              <span className="font-medium">Flood planning area</span> &mdash;
              may restrict habitable floor levels, building footprint, or
              prevent subdivision of flood-affected portions entirely
            </li>
            <li>
              <span className="font-medium">Bush Fire Prone Land</span>{' '}
              &mdash; both resulting lots must have compliant access roads and
              Asset Protection Zones. This can be the silent killer for rural
              subdivision
            </li>
            <li>
              <span className="font-medium">Service availability</span>{' '}
              &mdash; each lot must be capable of being serviced (sewer, water,
              power, road access). Extending services to a new rear lot can
              cost $30,000&ndash;$50,000+
            </li>
            <li>
              <span className="font-medium">Access</span> &mdash; the new lot
              must have legal road access. Battle-axe handles must meet minimum
              width requirements (typically 3&ndash;4 metres)
            </li>
            <li>
              <span className="font-medium">Easements</span> &mdash; existing
              drainage or services easements may constrain the subdivision
              layout
            </li>
            <li>
              <span className="font-medium">Tree preservation</span> &mdash;
              significant trees may limit where boundaries can be drawn or
              where buildings can be located on the new lots
            </li>
          </ul>
        </section>

        {/* Dual occupancy + subdivision pathway */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The dual occupancy + subdivision pathway
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A common strategy: build a dual occupancy (attached or detached
            duplex), then subdivide the land into two Torrens title lots, each
            containing one dwelling. This creates two independently sellable
            properties from one lot.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Whether this works depends on the zone, the minimum lot size, and
            the DCP. Not every zone that permits dual occupancy also permits
            subdivision. Some councils allow dual occupancy but restrict
            Torrens title subdivision to strata only. Some require a minimum
            lot area for dual occupancy that is larger than the minimum lot
            size for subdivision.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Check both the LEP (permitted uses + minimum lot size) and the DCP
            (dual occupancy controls, subdivision controls) before committing.
            For rural properties, see our guide on{' '}
            <Link
              href="/blog/what-can-i-build-rural-land-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              what you can build on rural land in NSW
            </Link>
            .
          </p>
        </section>

        {/* Costs */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What subdivision costs
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Subdivision costs vary enormously depending on location, site
            conditions, and the infrastructure requirements set by council.
            Section 7.12 (formerly s94) contributions are often the largest
            single cost and are set by council &mdash; they can range from
            $10,000 to $80,000+ per additional lot in metro Sydney.
          </p>

          <SubdivisionCostBreakdown />
        </section>

        {/* Granny flat alternative */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            When subdivision is not the answer
          </h2>
          <p className="text-slate-700 leading-relaxed">
            If subdivision is blocked by minimum lot size, a secondary dwelling
            (granny flat) may still be possible. Under SEPP (Housing) 2021,
            secondary dwellings up to 60sqm can be approved as complying
            development on eligible lots. The secondary dwelling cannot be
            separately subdivided &mdash; it stays on the same title &mdash;
            but it can generate rental income.
          </p>
          <p className="text-slate-700 leading-relaxed">
            See our guides on{' '}
            <Link
              href="/blog/can-i-build-a-granny-flat-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              granny flats in NSW
            </Link>{' '}
            and{' '}
            <Link
              href="/reports/granny-flat"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              PlotDetect&apos;s granny flat feasibility check
            </Link>{' '}
            for more on this pathway.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For rural properties, also consider whether your zone permits
            tourist accommodation or home business uses &mdash; these may be
            more viable than subdivision for generating returns. See our guide
            on{' '}
            <Link
              href="/blog/tree-change-checklist-nsw-planning"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              planning checks for rural property buyers
            </Link>
            .
          </p>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check your minimum lot size and zoning
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect shows the minimum lot size, zone, permitted uses, and
              applicable DCP controls for any NSW property. Enter an address to
              see whether subdivision is feasible for your lot.
            </p>
            <TrackedLink
              href="/check"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="subdivide-property-nsw-minimum-lot-sizes"
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
