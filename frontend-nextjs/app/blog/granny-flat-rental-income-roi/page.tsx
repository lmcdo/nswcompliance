import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Granny Flat Rental Income vs Build Cost: Is It Worth It? — PlotDetect',
  description:
    'Typical granny flat build costs in NSW range from $120K to $200K. Weekly rental income ranges from $350 to $550 in Sydney metro. Here is how the numbers break down and what affects your return.',
  keywords: [
    'granny flat rental income NSW',
    'granny flat ROI calculator',
    'granny flat build cost 2026',
    'secondary dwelling investment return',
    'granny flat cost vs rental income',
    'is a granny flat worth it',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Cost vs income breakdown */
function CostIncomeBreakdown() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Indicative cost vs income — Sydney metro granny flat (60 m&sup2;)
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        {/* Cost side */}
        <div className="rounded-xl border-2 border-red-200 bg-white p-5">
          <p className="text-sm font-bold text-red-700 mb-3">Build costs</p>
          <div className="space-y-2">
            {[
              { item: 'Construction (turnkey)', range: '$120K\u2013$180K' },
              { item: 'Council DA fees or CDC fees', range: '$3K\u2013$15K' },
              { item: 'Site costs (access, slope, services)', range: '$5K\u2013$30K' },
              { item: 'Connection to sewer/water/power', range: '$5K\u2013$15K' },
              { item: 'Landscaping and fencing', range: '$3K\u2013$10K' },
            ].map((c) => (
              <div key={c.item} className="flex justify-between items-center py-1.5 border-b border-slate-50 last:border-0">
                <span className="text-sm text-slate-700">{c.item}</span>
                <span className="text-sm font-medium text-slate-900 whitespace-nowrap ml-3">{c.range}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-slate-200 flex justify-between">
            <span className="text-sm font-bold text-slate-900">Typical total</span>
            <span className="text-sm font-bold text-red-700">$140K\u2013$250K</span>
          </div>
        </div>

        {/* Income side */}
        <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
          <p className="text-sm font-bold text-teal-700 mb-3">Rental income</p>
          <div className="space-y-2">
            {[
              { area: 'Inner Sydney (5\u201310 km)', range: '$450\u2013$550/week' },
              { area: 'Middle ring (10\u201325 km)', range: '$380\u2013$480/week' },
              { area: 'Outer Sydney (25\u201340 km)', range: '$350\u2013$420/week' },
              { area: 'Regional NSW (major centres)', range: '$280\u2013$380/week' },
            ].map((r) => (
              <div key={r.area} className="flex justify-between items-center py-1.5 border-b border-slate-50 last:border-0">
                <span className="text-sm text-slate-700">{r.area}</span>
                <span className="text-sm font-medium text-slate-900 whitespace-nowrap ml-3">{r.range}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-3 italic">
            Ranges are indicative for a well-finished 50\u201360 m&sup2; dwelling.
            Actual rents depend on location, finish, and market conditions.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Visual 2 — Payback period range */
function PaybackPeriodVisual() {
  const scenarios = [
    {
      label: 'Best case',
      cost: '$140K',
      weekly: '$500',
      annual: '$26,000',
      payback: '5.4 years',
      color: 'bg-teal-500',
      width: 'w-1/3',
    },
    {
      label: 'Mid case',
      cost: '$180K',
      weekly: '$420',
      annual: '$21,800',
      payback: '8.3 years',
      color: 'bg-amber-500',
      width: 'w-1/2',
    },
    {
      label: 'Conservative',
      cost: '$220K',
      weekly: '$370',
      annual: '$19,200',
      payback: '11.5 years',
      color: 'bg-red-400',
      width: 'w-3/4',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Indicative payback period (gross, before expenses)
      </p>
      <div className="space-y-5">
        {scenarios.map((s) => (
          <div key={s.label}>
            <div className="flex justify-between items-baseline mb-1.5">
              <div>
                <span className="text-sm font-semibold text-slate-900">{s.label}</span>
                <span className="text-xs text-slate-400 ml-2">
                  {s.cost} build, {s.weekly}/wk rent
                </span>
              </div>
              <span className="text-sm font-bold text-slate-900">{s.payback}</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-3">
              <div className={`${s.color} h-3 rounded-full ${s.width}`} />
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Gross annual: {s.annual} (assumes 50 weeks occupancy)
            </p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4 italic">
        These are gross payback estimates. Actual returns will be lower after
        accounting for maintenance, insurance, property management fees (typically
        5\u20138% of rent), vacancy periods, and depreciation. These figures do
        not constitute financial advice.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function GrannyFlatRentalIncomeROIPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Granny flat rental income vs build cost: is it worth it?"
        description="Typical build costs, rental yields by location, payback periods, and the hidden cost drivers that affect your return on a secondary dwelling."
        slug="granny-flat-rental-income-roi"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-700">
            Property Research
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          Granny flat rental income vs build cost: is it worth it?
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          A well-located granny flat in Sydney metro typically rents for $350 to
          $550 per week. Build costs range from $120K to $200K for a standard
          turnkey build, before site costs and approvals. The payback period
          depends on five variables &mdash; most of which you can assess before
          committing.
        </p>
      </div>

      {/* Immediate value: cost vs income */}
      <CostIncomeBreakdown />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">In this article</p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li><a href="#payback" className="hover:text-teal-600">Payback period scenarios</a></li>
          <li><a href="#cost-factors" className="hover:text-teal-600">What drives build cost up</a></li>
          <li><a href="#income-factors" className="hover:text-teal-600">What drives rental income</a></li>
          <li><a href="#hidden-costs" className="hover:text-teal-600">Hidden costs to budget for</a></li>
          <li><a href="#60sqm-constraint" className="hover:text-teal-600">The 60 m&sup2; cap and what it means for ROI</a></li>
          <li><a href="#dcp-costs" className="hover:text-teal-600">Council DCP variations that affect cost</a></li>
          <li><a href="#faq" className="hover:text-teal-600">Frequently asked questions</a></li>
        </ul>
      </nav>

      <div className="space-y-10">
        {/* SECTION 1: Payback */}
        <section id="payback" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Payback period scenarios
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Gross payback &mdash; total build cost divided by annual rent &mdash;
            ranges from roughly 5 to 12 years depending on location and build
            cost. Net payback is longer after accounting for ongoing expenses.
            Three indicative scenarios:
          </p>

          <PaybackPeriodVisual />

          <p className="text-slate-700 leading-relaxed">
            The single biggest factor is rental location. A $150K build in inner
            Sydney returning $500/week will always outperform a $150K build in
            outer suburbs returning $370/week. Build cost matters, but location
            is the multiplier.
          </p>
        </section>

        {/* SECTION 2: Cost factors */}
        <section id="cost-factors" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What drives build cost up
          </h2>
          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Site access
              </h3>
              <p className="text-slate-700 leading-relaxed">
                If machinery cannot access the rear yard &mdash; narrow side
                passages, no rear lane, fences to remove &mdash; materials must
                be craned or hand-carried. This alone can add $10,000 to $25,000
                to a build. Some builders quote a flat &ldquo;restricted access
                fee&rdquo;; others price it into the per-square-metre rate.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Slope and site preparation
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A flat, cleared site is the cheapest to build on. Slopes
                requiring cut-and-fill, retaining walls, or pier foundations add
                cost. Rock excavation can double earthworks costs. A
                geotechnical report ($1,500 to $3,000) is worth getting before
                committing to a builder.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Services connection
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Connecting sewer, water, and electricity to the granny flat is a
                separate cost from construction. If the existing sewer main runs
                under the proposed building footprint, you may need to divert
                it. Sydney Water connection fees, Ausgrid fees, and council
                contributions are in addition to the builder&apos;s quote.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                DA vs CDC approval costs
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A CDC through a private certifier typically costs $3,000 to
                $6,000. A DA through council can cost $5,000 to $15,000 or more,
                including application fees, consultant reports (heritage,
                arborist, flooding), and potentially a section 7.12 levy. If
                your property{' '}
                <Link
                  href="/blog/can-i-build-a-granny-flat-nsw"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  qualifies for CDC
                </Link>
                , the approval cost saving is meaningful.
              </p>
            </div>
          </div>
        </section>

        {/* SECTION 3: Income factors */}
        <section id="income-factors" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What drives rental income
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Four factors have the most impact on what a granny flat will rent for:
          </p>
          <ul className="space-y-3 text-slate-700 leading-relaxed">
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 flex items-center justify-center text-xs font-bold text-teal-700 mt-0.5">1</span>
              <div>
                <span className="font-medium">Location and transport access.</span>{' '}
                Proximity to train stations, employment centres, and amenities
                is the dominant factor. A 1-bedroom granny flat 500 m from a
                train station will rent for significantly more than an identical
                build 5 km from one.
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 flex items-center justify-center text-xs font-bold text-teal-700 mt-0.5">2</span>
              <div>
                <span className="font-medium">Floor area and layout.</span>{' '}
                A 60 m&sup2; one-bedroom with a separate living area rents for
                more than a studio layout of the same size. An enclosed
                bedroom &mdash; even in a compact layout &mdash; is important
                for the rental market.
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 flex items-center justify-center text-xs font-bold text-teal-700 mt-0.5">3</span>
              <div>
                <span className="font-medium">Finish quality and separate entry.</span>{' '}
                A private entrance, own outdoor space, and reasonable finishes
                (not builder-grade) command a premium. Split systems, dishwasher,
                and internal laundry are now expected by renters at market rate.
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 flex items-center justify-center text-xs font-bold text-teal-700 mt-0.5">4</span>
              <div>
                <span className="font-medium">Privacy from the main dwelling.</span>{' '}
                Granny flats that share outdoor space, have overlooking windows,
                or share a driveway entrance rent for less. Separation &mdash;
                both physical and visual &mdash; matters to tenants.
              </div>
            </li>
          </ul>
        </section>

        {/* SECTION 4: Hidden costs */}
        <section id="hidden-costs" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Hidden costs to budget for
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse mt-2">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                    Cost
                  </th>
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                    Typical range
                  </th>
                  <th className="text-left py-3 font-semibold text-slate-900">
                    Notes
                  </th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                <tr className="border-b border-slate-100">
                  <td className="py-2.5 pr-4">Increased council rates</td>
                  <td className="py-2.5 pr-4 whitespace-nowrap">$300\u2013$800/year</td>
                  <td className="py-2.5">Varies by council; some reassess after completion</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2.5 pr-4">Insurance (landlord)</td>
                  <td className="py-2.5 pr-4 whitespace-nowrap">$500\u2013$1,200/year</td>
                  <td className="py-2.5">Building + landlord contents + public liability</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2.5 pr-4">Property management fees</td>
                  <td className="py-2.5 pr-4 whitespace-nowrap">5\u20138% of rent</td>
                  <td className="py-2.5">Plus letting fees (1\u20132 weeks rent per new tenancy)</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2.5 pr-4">Maintenance allowance</td>
                  <td className="py-2.5 pr-4 whitespace-nowrap">1\u20132% of build cost/year</td>
                  <td className="py-2.5">Hot water, appliances, painting, general wear</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2.5 pr-4">Water usage (if not separately metered)</td>
                  <td className="py-2.5 pr-4 whitespace-nowrap">$400\u2013$800/year</td>
                  <td className="py-2.5">Separate metering costs ~$2K to install but saves long-term</td>
                </tr>
                <tr>
                  <td className="py-2.5 pr-4">Vacancy periods</td>
                  <td className="py-2.5 pr-4 whitespace-nowrap">2\u20134 weeks/year</td>
                  <td className="py-2.5">Budget for 50 weeks occupancy, not 52</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* SECTION 5: 60sqm constraint */}
        <section id="60sqm-constraint" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The 60 m&sup2; cap and what it means for ROI
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The SEPP Housing 2021 caps secondary dwelling floor area at
            60 m&sup2; for CDC. This creates an interesting dynamic: the cap
            limits your total rental income, but also limits your build cost.
            A 60 m&sup2; granny flat is not trying to compete with a 2-bedroom
            apartment &mdash; it occupies a specific market niche.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The per-square-metre build cost is typically higher for a granny
            flat than for a larger dwelling because fixed costs (kitchen,
            bathroom, services connection) are spread over fewer square metres.
            A 60 m&sup2; build at $2,000 to $3,000 per square metre is typical
            for a standard finish.
          </p>
          <p className="text-slate-700 leading-relaxed">
            From an investment perspective, the cap also means rental yield per
            square metre is comparatively high. A 60 m&sup2; dwelling renting
            at $450/week yields $7.50 per m&sup2; per week &mdash; significantly
            more than most 2-bedroom apartments on a per-area basis.
          </p>
        </section>

        {/* SECTION 6: DCP costs */}
        <section id="dcp-costs" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Council DCP variations that affect cost
          </h2>
          <p className="text-slate-700 leading-relaxed">
            If you go through the DA pathway, your council&apos;s DCP controls
            directly affect what you can build and what it costs. Common
            variations between councils:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Larger setbacks</span> reduce the
              buildable footprint on smaller lots, potentially forcing a smaller
              or two-storey design
            </li>
            <li>
              <span className="font-medium">Deep soil landscaping requirements</span>{' '}
              can reduce the area available for both the building and outdoor
              space
            </li>
            <li>
              <span className="font-medium">Parking requirements</span> vary
              &mdash; some councils require a dedicated space; others accept
              tandem parking with the main dwelling
            </li>
            <li>
              <span className="font-medium">Materials and design controls</span>{' '}
              in heritage-sensitive areas can add cost through brick rather than
              cladding, specific roofing materials, or colour palette restrictions
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            These variations are one of the reasons the CDC pathway is more
            cost-predictable &mdash; the SEPP standards are statewide and
            fixed. For a detailed comparison of how DCP controls differ by
            council, see{' '}
            <Link
              href="/blog/dcp-setbacks-granny-flat-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              why your council&apos;s DCP setbacks for granny flats are different
            </Link>
            .
          </p>
        </section>

        {/* FAQ */}
        <section id="faq" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Frequently asked questions
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                How much does a granny flat cost to build in NSW in 2026?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A standard 50 to 60 m&sup2; turnkey build ranges from $120,000
                to $180,000 before site costs and approvals. Total project cost
                including connections, approvals, and landscaping typically
                falls between $140,000 and $250,000. High-end finishes, steep
                sites, or restricted access push costs higher.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                What rental income can I expect from a granny flat in Sydney?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                In Sydney metro, a well-finished 1-bedroom granny flat
                typically rents for $350 to $550 per week depending on location
                and proximity to transport. Inner Sydney commands the highest
                rents. Check current market rates for your specific suburb
                before committing.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Is a granny flat a good investment?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Gross payback periods of 5 to 12 years are common. Whether this
                represents a good return depends on your cost of capital,
                alternative investment options, and the value of the property
                uplift (granny flat potential adds value to the main property
                at resale). This is a financial decision that should be assessed
                against your specific circumstances.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does a granny flat increase property value?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                An approved and tenanted granny flat typically adds value to a
                property beyond its build cost, particularly in areas with
                strong rental demand. The value uplift varies by market and is
                not guaranteed. Properties with CDC-eligible granny flat
                potential (but no granny flat yet built) also trade at a
                premium in some markets.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can I claim depreciation on a granny flat?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                New granny flat construction is eligible for capital works
                deductions and plant and equipment depreciation. A quantity
                surveyor can prepare a depreciation schedule for the build.
                This is a tax matter &mdash; consult a registered tax agent for
                advice specific to your situation.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check if your property qualifies
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              Before running the numbers, check whether your property is
              eligible for a granny flat under the SEPP Housing 2021 CDC
              pathway. PlotDetect checks zone, lot size, heritage, flood, and
              environmental constraints for any NSW address.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/reports/granny-flat"
                className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
                page="granny-flat-rental-income-roi"
                cta="check_granny_flat"
              >
                Granny flat report
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/blog/can-i-build-a-granny-flat-nsw"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-teal-700 text-sm font-medium rounded-xl border border-teal-200 hover:bg-teal-50 transition-colors"
              >
                Full eligibility guide
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
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
