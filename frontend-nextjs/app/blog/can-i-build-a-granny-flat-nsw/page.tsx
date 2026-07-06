import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Can I Build a Granny Flat on My Property in NSW? — PlotDetect',
  description:
    'Check if your NSW property is eligible for a granny flat (secondary dwelling). Covers SEPP Housing 2021 requirements, lot size, zone, heritage, flood, and CDC vs DA pathways.',
  keywords: [
    'can I build a granny flat NSW',
    'granny flat eligibility check',
    'secondary dwelling NSW rules',
    'granny flat SEPP',
    'affordable rental housing SEPP',
    'SEPP Housing 2021 granny flat',
    'granny flat CDC vs DA',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Eligibility decision tree */
function EligibilityDecisionTree() {
  const gates = [
    {
      question: 'Is your lot zoned R1, R2, R3, or RU5?',
      yes: 'Continue',
      no: 'Not eligible under SEPP Housing 2021',
      note: 'Check your zoning at planning.nsw.gov.au or via PlotDetect',
    },
    {
      question: 'Is your lot at least 450 m\u00B2?',
      yes: 'Continue',
      no: 'Not eligible — minimum lot size for CDC pathway',
      note: 'Some councils accept smaller lots via DA, but CDC requires 450 m\u00B2',
    },
    {
      question: 'Is the property free of heritage listing or heritage conservation area?',
      yes: 'Continue',
      no: 'Not eligible for CDC — may still be possible via DA with heritage assessment',
      note: 'Both individual heritage items and HCAs are excluded under Cl 37(1)(d)',
    },
    {
      question: 'Is the property outside a flood planning area?',
      yes: 'Continue',
      no: 'Not eligible for CDC — DA pathway may still be available',
      note: 'Flood planning areas are mapped by council, not always on planning certificates',
    },
    {
      question: 'Is the property free of biodiversity / acid sulfate constraints?',
      yes: 'Eligible for CDC pathway',
      no: 'Not eligible for CDC — DA pathway may still apply',
      note: null,
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Granny flat eligibility — key gates (SEPP Housing 2021)
      </p>
      <div className="relative">
        <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-slate-200" />
        <div className="space-y-5">
          {gates.map((g, i) => (
            <div key={i} className="relative pl-10">
              <div className="absolute left-1.5 top-1.5 w-3.5 h-3.5 rounded-full bg-teal-500 ring-4 ring-white" />
              <p className="text-sm font-semibold text-slate-900">{g.question}</p>
              <div className="mt-2 grid sm:grid-cols-2 gap-2">
                <div className="flex items-start gap-2 rounded-lg bg-teal-50 border border-teal-100 px-3 py-2">
                  <span className="text-teal-600 font-bold text-xs mt-0.5">YES</span>
                  <span className="text-sm text-slate-700">{g.yes}</span>
                </div>
                <div className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-100 px-3 py-2">
                  <span className="text-red-600 font-bold text-xs mt-0.5">NO</span>
                  <span className="text-sm text-slate-700">{g.no}</span>
                </div>
              </div>
              {g.note && (
                <p className="text-xs text-slate-400 mt-1.5 italic">{g.note}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Visual 2 — CDC vs DA pathway comparison */
function PathwayComparison() {
  const rows = [
    { label: 'Approval body', cdc: 'Private certifier', da: 'Council' },
    { label: 'Typical timeframe', cdc: '10\u201320 business days', da: '45\u201390+ days' },
    { label: 'Neighbour notification', cdc: 'Not required', da: 'Required' },
    { label: 'Typical cost (approval fees)', cdc: '$3,000\u2013$6,000', da: '$5,000\u2013$15,000+' },
    { label: 'Heritage properties', cdc: 'Not available', da: 'Available with heritage assessment' },
    { label: 'Flood-affected land', cdc: 'Not available', da: 'May be available with flood study' },
    { label: 'Floor area cap', cdc: '60 m\u00B2', da: '60 m\u00B2 (same cap applies)' },
    { label: 'Design flexibility', cdc: 'Must meet all SEPP standards', da: 'Council can vary standards' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        CDC pathway vs DA pathway
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-3 pr-4 font-semibold text-slate-900 w-1/3" />
              <th className="text-left py-3 pr-4 font-semibold text-teal-700">
                Complying Development (CDC)
              </th>
              <th className="text-left py-3 font-semibold text-amber-700">
                Development Application (DA)
              </th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {rows.map((r) => (
              <tr key={r.label} className="border-b border-slate-100">
                <td className="py-2.5 pr-4 font-medium text-slate-900">{r.label}</td>
                <td className="py-2.5 pr-4">{r.cdc}</td>
                <td className="py-2.5">{r.da}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function CanIBuildGrannyFlatPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Can I build a granny flat on my property in NSW?"
        description="Quick eligibility check, CDC vs DA pathways, SEPP requirements, and common blockers — heritage, flood, bushfire, strata, and lot size."
        slug="can-i-build-a-granny-flat-nsw"
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
          Can I build a granny flat on my property in NSW?
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Five questions determine whether your property qualifies for a
          secondary dwelling under the SEPP Housing 2021 complying development
          pathway. Most properties in residential zones pass. Here is how to
          check yours.
        </p>
      </div>

      {/* Immediate value: decision tree */}
      <EligibilityDecisionTree />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">In this article</p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li><a href="#key-requirements" className="hover:text-teal-600">Key requirements at a glance</a></li>
          <li><a href="#cdc-vs-da" className="hover:text-teal-600">CDC vs DA: which pathway do you need?</a></li>
          <li><a href="#common-blockers" className="hover:text-teal-600">Common blockers that catch people out</a></li>
          <li><a href="#sepp-standards" className="hover:text-teal-600">What the SEPP actually requires</a></li>
          <li><a href="#dcp-layer" className="hover:text-teal-600">Your council&apos;s DCP may add more</a></li>
          <li><a href="#faq" className="hover:text-teal-600">Frequently asked questions</a></li>
        </ul>
      </nav>

      <div className="space-y-10">
        {/* SECTION 1: Key requirements */}
        <section id="key-requirements" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Key requirements at a glance
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Under{' '}
            <span className="font-medium">
              State Environmental Planning Policy (Housing) 2021
            </span>
            , a secondary dwelling (granny flat) can be approved as complying
            development if the property meets these minimum standards:
          </p>
          <div className="grid sm:grid-cols-2 gap-4 mt-2">
            {[
              { label: 'Minimum lot size', value: '450 m\u00B2' },
              { label: 'Maximum floor area', value: '60 m\u00B2' },
              { label: 'Maximum height', value: '8.5 m (2 storeys)' },
              { label: 'Permitted zones', value: 'R1, R2, R3, RU5' },
              { label: 'Rear setback (SEPP minimum)', value: '3 m' },
              { label: 'Side setback (SEPP minimum)', value: '0.9 m' },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-xl border border-slate-200 bg-white p-4"
              >
                <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
                  {item.label}
                </p>
                <p className="text-lg font-bold text-slate-900 mt-1">{item.value}</p>
              </div>
            ))}
          </div>
          <p className="text-slate-700 leading-relaxed">
            The 60 m&sup2; floor area cap is a hard limit under the SEPP. It
            applies regardless of lot size &mdash; a 2,000 m&sup2; lot still
            gets a maximum 60 m&sup2; granny flat under complying development.
            Councils cannot increase this cap.
          </p>
        </section>

        {/* SECTION 2: CDC vs DA */}
        <section id="cdc-vs-da" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            CDC vs DA: which pathway do you need?
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A Complying Development Certificate (CDC) is faster and cheaper, but
            only available when the property and the proposed building both meet
            every SEPP standard. If any standard is not met &mdash; or if the
            property has a constraint that excludes it from CDC &mdash; you need
            a Development Application (DA) through council.
          </p>

          <PathwayComparison />

          <p className="text-slate-700 leading-relaxed">
            In practice, most standard granny flat builds on unconstrained
            residential lots can use the CDC pathway. The DA pathway exists for
            properties that are heritage-listed, flood-affected, or otherwise
            excluded from complying development. DA gives council discretion to
            approve developments that do not meet every prescriptive standard,
            but the process is slower and less predictable.
          </p>
        </section>

        {/* SECTION 3: Common blockers */}
        <section id="common-blockers" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Common blockers that catch people out
          </h2>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Heritage listing or heritage conservation area
              </h3>
              <p className="text-slate-700 leading-relaxed">
                If the property is individually heritage-listed or within a
                heritage conservation area (HCA), complying development is not
                available under Cl 37(1)(d). Many inner-Sydney suburbs have
                extensive HCA coverage. A property does not need to be a
                heritage building itself &mdash; being within the HCA boundary
                is enough to exclude CDC. DA with a heritage impact assessment
                is the alternative.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Flood planning area
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Properties within a flood planning area cannot use the CDC
                pathway for a secondary dwelling. Flood status is not always
                obvious from a planning certificate &mdash; after{' '}
                <Link
                  href="/blog/section-10-7-flood-risk-nsw"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  legislative changes in 2021 and 2023
                </Link>
                , some certificates show less flood information than they
                previously did. Check with your council or use a tool that
                cross-references multiple flood data sources.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Bushfire prone land
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Properties on bushfire-prone land may still be eligible for CDC,
                but additional construction standards apply under the{' '}
                <span className="font-medium">Planning for Bush Fire Protection</span>{' '}
                guidelines. Asset protection zones and BAL ratings affect siting
                and construction cost. Properties rated BAL-40 or BAL-FZ face
                significantly higher build costs.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Strata title
              </h3>
              <p className="text-slate-700 leading-relaxed">
                If your property is on a strata lot, you cannot build a granny
                flat as complying development. The SEPP Housing 2021 CDC
                pathway requires the lot to be Torrens title. Some strata
                schemes may allow it via DA with owners corporation consent, but
                this is uncommon and complex.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Lot too small or too narrow
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The 450 m&sup2; minimum is the SEPP threshold. Below this, CDC
                is not available. Some older inner-city lots are under 450 m&sup2;
                &mdash; these may still be eligible via DA if council supports
                secondary dwellings at merit assessment, but there is no
                guarantee of approval.
              </p>
            </div>
          </div>
        </section>

        {/* SECTION 4: SEPP standards */}
        <section id="sepp-standards" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What the SEPP actually requires
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The SEPP Housing 2021 (formerly the Affordable Rental Housing SEPP)
            sets out the CDC standards for secondary dwellings in Division 2,
            Subdivision 6. Key provisions:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Floor area:</span> maximum 60 m&sup2;
              (Cl 39(1))
            </li>
            <li>
              <span className="font-medium">Height:</span> maximum 8.5 m
              (Cl 39(2)(a))
            </li>
            <li>
              <span className="font-medium">Rear setback:</span> minimum 3 m
              (Cl 39(2)(b))
            </li>
            <li>
              <span className="font-medium">Side setback:</span> minimum 0.9 m
              (single storey) or 1.5 m (two storey)
            </li>
            <li>
              <span className="font-medium">Landscaped area:</span> minimum
              percentage of the lot must remain landscaped (varies by lot size)
            </li>
            <li>
              <span className="font-medium">Private open space:</span> minimum
              24 m&sup2; accessible from the secondary dwelling
            </li>
            <li>
              <span className="font-medium">Car parking:</span> one additional
              space required (may be tandem or stacked with existing)
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            These are the SEPP minimums. Your council&apos;s Development Control
            Plan (DCP) may impose additional or stricter requirements on top of
            these. See our guide on{' '}
            <Link
              href="/blog/dcp-setbacks-granny-flat-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              why DCP setbacks for granny flats differ by council
            </Link>
            .
          </p>
        </section>

        {/* SECTION 5: DCP layer */}
        <section id="dcp-layer" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Your council&apos;s DCP may add more
          </h2>
          <p className="text-slate-700 leading-relaxed">
            While the SEPP sets statewide baseline standards, each council&apos;s
            DCP can add controls for secondary dwellings. Common DCP additions
            include:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>Larger rear setbacks than the SEPP 3 m minimum</li>
            <li>Separation distances between the main dwelling and the granny flat</li>
            <li>Additional landscaping or deep soil planting requirements</li>
            <li>Materials and finishes to match the streetscape character</li>
            <li>Specific waste storage and collection arrangements</li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            DCP controls apply to the DA pathway. For the CDC pathway, the SEPP
            standards take precedence &mdash; but understanding DCP requirements
            matters if you need to go through DA, or if you want your build to
            align with council expectations.
          </p>
          <p className="text-slate-700 leading-relaxed">
            You can browse your council&apos;s DCP controls using{' '}
            <Link
              href="/dcp-browse"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              PlotDetect&apos;s DCP browser
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
                Can I build a granny flat bigger than 60 m&sup2;?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Not under the SEPP Housing 2021 complying development pathway.
                The 60 m&sup2; cap applies regardless of lot size. Some councils
                may consider larger secondary dwellings via DA in specific
                circumstances, but this is council-dependent and not guaranteed.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can I rent out a granny flat?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Yes. Secondary dwellings approved under the SEPP can be rented
                out. The previous 10-year moratorium on separate sale of
                secondary dwellings has been lifted for some lot configurations,
                but most granny flats remain tied to the primary lot title.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Do I need council approval for a granny flat?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                You always need either a CDC (issued by a private certifier) or
                a DA (issued by council). You cannot build a granny flat without
                one or the other. The CDC pathway is faster and does not require
                council assessment, but requires meeting every SEPP standard.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                What zones allow granny flats in NSW?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                R1 General Residential, R2 Low Density Residential, R3 Medium
                Density Residential, and RU5 Village. R4 High Density
                Residential does not permit secondary dwellings under the SEPP
                Housing 2021.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                How do I check if my property is eligible?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                You need to verify your zone, lot size, and check for exclusion
                constraints (heritage, flood, biodiversity, acid sulfate,
                strata). PlotDetect&apos;s{' '}
                <Link
                  href="/check"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  eligibility checker
                </Link>{' '}
                runs these checks automatically for any NSW address.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check your property in 30 seconds
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect checks zone, lot size, heritage, flood, and
              environmental constraints for any NSW address. Enter your address
              to see whether your property qualifies for a granny flat under
              the SEPP Housing 2021 CDC pathway.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/check"
                className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
                page="can-i-build-a-granny-flat-nsw"
                cta="check_address"
              >
                Check eligibility
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/reports/granny-flat"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-teal-700 text-sm font-medium rounded-xl border border-teal-200 hover:bg-teal-50 transition-colors"
              >
                Granny flat report
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
