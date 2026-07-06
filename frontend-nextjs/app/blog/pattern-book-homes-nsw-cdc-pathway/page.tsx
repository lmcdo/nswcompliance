import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Pattern Book Homes: The 10-Day CDC Pathway That Could Save $330K — PlotDetect',
  description:
    'NSW Pattern Book homes offer pre-approved designs with a 10-day Complying Development Certificate pathway, potentially saving $330K per dwelling in approval costs and construction time. How it works, where it applies, and what the limitations are.',
  keywords: [
    'NSW Pattern Book homes',
    '10 day CDC pathway NSW',
    'pattern book housing NSW 2026',
    'fast track housing approval NSW',
    'complying development certificate NSW',
    'pre-approved housing designs NSW',
    'medium density housing NSW',
    'CDC vs DA NSW',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — DA timeline vs Pattern Book CDC timeline */
function TimelineComparison() {
  const daSteps = [
    { label: 'Pre-DA consultation', weeks: '2-4 weeks' },
    { label: 'Prepare DA documents', weeks: '4-8 weeks' },
    { label: 'Council assessment', weeks: '12-40 weeks' },
    { label: 'Conditions negotiation', weeks: '2-6 weeks' },
    { label: 'Construction certificate', weeks: '2-4 weeks' },
  ];

  const cdcSteps = [
    { label: 'Select Pattern Book design', weeks: '1-2 weeks' },
    { label: 'Site assessment + certifier', weeks: '1-2 weeks' },
    { label: 'CDC determination', weeks: '10 days' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Traditional DA vs Pattern Book CDC — approval timeline
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        {/* DA path */}
        <div className="rounded-xl border-2 border-red-200 bg-white p-5">
          <p className="text-sm font-bold text-red-700 mb-1">
            Traditional DA pathway
          </p>
          <p className="text-xs text-slate-500 mb-4">
            Total: 22-62 weeks typical
          </p>
          <div className="space-y-3">
            {daSteps.map((step) => (
              <div key={step.label} className="flex items-center justify-between">
                <span className="text-sm text-slate-700">{step.label}</span>
                <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                  {step.weeks}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* CDC path */}
        <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
          <p className="text-sm font-bold text-teal-700 mb-1">
            Pattern Book CDC pathway
          </p>
          <p className="text-xs text-slate-500 mb-4">
            Total: 3-5 weeks typical
          </p>
          <div className="space-y-3">
            {cdcSteps.map((step) => (
              <div key={step.label} className="flex items-center justify-between">
                <span className="text-sm text-slate-700">{step.label}</span>
                <span className="text-xs font-medium text-teal-600 bg-teal-50 px-2 py-0.5 rounded-full">
                  {step.weeks}
                </span>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-4 italic">
            Design compliance is pre-verified. The certifier assesses site
            suitability only.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Visual 2 — Cost comparison */
function CostComparison() {
  const rows = [
    {
      item: 'Architectural design fees',
      da: '$30,000-$80,000',
      pb: 'Included in design',
    },
    {
      item: 'DA/CDC lodgement and assessment',
      da: '$15,000-$40,000',
      pb: '$3,000-$8,000',
    },
    {
      item: 'Holding costs during approval',
      da: '$60,000-$150,000',
      pb: '$10,000-$25,000',
    },
    {
      item: 'Consultant reports',
      da: '$10,000-$30,000',
      pb: '$5,000-$10,000',
    },
    {
      item: 'Conditions compliance',
      da: '$5,000-$20,000',
      pb: 'Minimal',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Estimated cost comparison per dwelling
      </p>
      <div className="space-y-0">
        <div className="grid grid-cols-3 gap-4 pb-3 border-b border-slate-200">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Cost item
          </span>
          <span className="text-xs font-bold text-red-600 uppercase tracking-wider">
            Traditional DA
          </span>
          <span className="text-xs font-bold text-teal-600 uppercase tracking-wider">
            Pattern Book CDC
          </span>
        </div>
        {rows.map((row) => (
          <div
            key={row.item}
            className="grid grid-cols-3 gap-4 py-3 border-b border-slate-100 last:border-0"
          >
            <span className="text-sm font-medium text-slate-900">
              {row.item}
            </span>
            <span className="text-sm text-slate-600">{row.da}</span>
            <span className="text-sm text-slate-700 font-medium">{row.pb}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-slate-200 flex justify-between">
        <span className="text-sm font-bold text-slate-900">
          Estimated total pre-construction cost
        </span>
        <div className="text-right">
          <span className="text-sm text-red-600 font-medium">
            $120K-$320K
          </span>
          <span className="text-sm text-slate-400 mx-2">vs</span>
          <span className="text-sm text-teal-600 font-bold">$18K-$43K</span>
        </div>
      </div>
      <p className="text-xs text-slate-400 mt-3 italic">
        Estimates based on medium-density residential in metropolitan Sydney.
        Holding costs assume land value of $1M and 6% carrying cost. Actual
        costs vary by location, scale, and site conditions.
      </p>
    </div>
  );
}

/** Visual 3 — Where it applies vs doesn't */
function ApplicabilityCard() {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Site constraints that override the Pattern Book pathway
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        <div className="rounded-xl bg-white border border-slate-200 p-5">
          <p className="text-sm font-bold text-teal-700 mb-3">
            Pattern Book CDC likely available
          </p>
          <ul className="space-y-2 text-sm text-slate-700">
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5 flex-shrink-0">&#9679;</span>
              R1, R2, R3 residential zones
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5 flex-shrink-0">&#9679;</span>
              No heritage listing or conservation area
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5 flex-shrink-0">&#9679;</span>
              No flood planning area
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5 flex-shrink-0">&#9679;</span>
              Outside bushfire-prone land (or BAL-LOW)
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5 flex-shrink-0">&#9679;</span>
              Meets minimum lot size requirements
            </li>
          </ul>
        </div>
        <div className="rounded-xl bg-white border border-slate-200 p-5">
          <p className="text-sm font-bold text-red-700 mb-3">
            Likely excluded — DA still required
          </p>
          <ul className="space-y-2 text-sm text-slate-700">
            <li className="flex items-start gap-2">
              <span className="text-red-400 mt-0.5 flex-shrink-0">&#9679;</span>
              Heritage-listed property or conservation area
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-400 mt-0.5 flex-shrink-0">&#9679;</span>
              Flood planning area (mapped or council-defined)
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-400 mt-0.5 flex-shrink-0">&#9679;</span>
              Bushfire-prone land (BAL-12.5 and above)
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-400 mt-0.5 flex-shrink-0">&#9679;</span>
              Coastal vulnerability or wetland areas
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-400 mt-0.5 flex-shrink-0">&#9679;</span>
              Environmentally sensitive land
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function PatternBookHomesPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`Pattern Book homes: the 10-day CDC pathway that could save \$330K`}
        description={`Pre-designed Pattern Book homes, a 10-day complying development certificate, and estimated \$330K savings per dwelling. How the Pattern Book pathway works.`}
        slug="pattern-book-homes-nsw-cdc-pathway"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-700">
            Planning Reforms
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          Pattern Book homes: the 10-day CDC pathway that could save $330K
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          A pre-approved residential design. A 10-day Complying Development
          Certificate instead of a 6-12 month DA. An estimated $330,000 saving
          per dwelling from reduced approval time and design costs. The NSW
          Pattern Book pathway is one of the most consequential housing reforms
          in a decade &mdash; if the details hold up.
        </p>
      </div>

      {/* Immediate value — timeline comparison */}
      <TimelineComparison />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#what-are-pattern-book" className="hover:text-teal-600">
              What Pattern Book homes are
            </a>
          </li>
          <li>
            <a href="#how-cdc-works" className="hover:text-teal-600">
              How the 10-day CDC pathway works
            </a>
          </li>
          <li>
            <a href="#cost-savings" className="hover:text-teal-600">
              Where the $330K saving comes from
            </a>
          </li>
          <li>
            <a href="#where-applies" className="hover:text-teal-600">
              Where it applies and where it does not
            </a>
          </li>
          <li>
            <a href="#quality" className="hover:text-teal-600">
              Quality safeguards
            </a>
          </li>
          <li>
            <a href="#existing-cdc" className="hover:text-teal-600">
              How this differs from existing CDC
            </a>
          </li>
          <li>
            <a href="#limitations" className="hover:text-teal-600">
              Limitations and open questions
            </a>
          </li>
        </ul>
      </nav>

      {/* Body */}
      <div className="space-y-10">
        {/* ========== WHAT ARE PATTERN BOOK HOMES ========== */}
        <section id="what-are-pattern-book" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What Pattern Book homes are
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A Pattern Book home is a residential design that has been
            pre-assessed and pre-approved against the National Construction Code
            (NCC), relevant State Environmental Planning Policies (SEPPs), and a
            defined set of development standards. Because the design itself is
            already compliant, it can be approved as Complying Development
            &mdash; a faster, simpler pathway than a full Development
            Application.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The concept is not new. Pattern books were common in Australian
            housing before World War II, when builders selected from catalogues
            of pre-drawn designs. The 2026 version updates this for modern
            building codes, energy standards, and accessibility requirements.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The federal and NSW state governments have both committed to Pattern
            Book schemes as part of the National Housing Accord target of 1.2
            million new dwellings by 2029. The NSW{' '}
            <Link
              href="/blog/nsw-building-bill-2026-certifier-penalties"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Building Bill 2026
            </Link>{' '}
            provides the legislative framework for these designs to enter the
            approval system.
          </p>
        </section>

        {/* ========== HOW THE 10-DAY CDC WORKS ========== */}
        <section id="how-cdc-works" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How the 10-day CDC pathway works
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The standard CDC process already allows a private certifier to
            approve development within 10 days, provided it meets all applicable
            development standards. The Pattern Book pathway simplifies this
            further by removing the design compliance assessment entirely.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Under the Pattern Book CDC pathway, the certifier&apos;s assessment
            is limited to site suitability:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              Does the site meet the minimum lot size and dimensions for the
              selected design?
            </li>
            <li>
              Are there any site-specific exclusions (flood, bushfire, heritage,
              coastal)?
            </li>
            <li>
              Does the proposed siting comply with setback and boundary
              requirements?
            </li>
            <li>
              Are services (sewer, water, power) available to the site?
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            The design itself &mdash; floor plan, materials, structural system,
            energy performance &mdash; has already been assessed. The certifier
            does not re-assess it. This is what makes the 10-day timeframe
            realistic rather than aspirational.
          </p>
        </section>

        {/* ========== COST SAVINGS ========== */}
        <section id="cost-savings" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Where the $330K saving comes from
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The $330,000 figure is an estimate of the total pre-construction cost
            saving per dwelling when comparing a traditional DA pathway with the
            Pattern Book CDC pathway. The saving comes from three sources:
            eliminated design fees, reduced approval costs, and dramatically
            lower holding costs.
          </p>

          <CostComparison />

          <p className="text-slate-700 leading-relaxed">
            The largest component is holding costs. Land purchased for
            development incurs financing costs for every month it sits in the
            approval pipeline. A DA that takes 40 weeks instead of 12 adds
            roughly $40,000-$90,000 in holding costs alone on a $1M land
            parcel. The Pattern Book pathway compresses the approval period from
            months to weeks.
          </p>
          <p className="text-slate-700 leading-relaxed">
            These figures should be treated as indicative. Actual savings depend
            on land value, financing costs, the complexity of the DA that would
            otherwise be required, and the extent of site-specific constraints.
            Not every project will save $330,000. But even half that figure
            changes the economics of medium-density housing substantially.
          </p>
        </section>

        {/* ========== WHERE IT APPLIES ========== */}
        <section id="where-applies" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Where it applies and where it does not
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Pattern Book CDC pathway is expected to apply in residential
            zones where medium-density housing is already permitted &mdash;
            primarily R1 General Residential, R2 Low Density, and R3 Medium
            Density zones. However, site-specific constraints can exclude a
            property regardless of its zoning.
          </p>

          <ApplicabilityCard />

          <p className="text-slate-700 leading-relaxed">
            This is where site-specific compliance checking matters. A property
            may be in the right zone but fall within a flood planning area or
            heritage conservation area that excludes it from the CDC pathway.
            PlotDetect&apos;s{' '}
            <Link
              href="/check"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              address check
            </Link>{' '}
            identifies these overlapping constraints for any NSW address.
          </p>
        </section>

        {/* ========== QUALITY SAFEGUARDS ========== */}
        <section id="quality" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Quality safeguards
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A faster approval pathway does not mean lower building standards.
            Pattern Book homes must still meet:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">
                National Construction Code (NCC)
              </span>{' '}
              &mdash; structural adequacy, fire safety, accessibility,
              weatherproofing, energy efficiency
            </li>
            <li>
              <span className="font-medium">BASIX requirements</span> &mdash;
              NSW energy and water efficiency standards
            </li>
            <li>
              <span className="font-medium">
                Design and Building Practitioners Act
              </span>{' '}
              &mdash; registered practitioners must prepare and certify
              regulated designs
            </li>
            <li>
              <span className="font-medium">Building Bill 2026 provisions</span>{' '}
              &mdash; including the new penalty regime and Building Commission
              oversight
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            The pre-approval process itself acts as a quality filter. Designs
            that make it into the Pattern Book have been assessed more thoroughly
            than many individual DAs. The trade-off is design variety &mdash;
            you get speed and cost savings at the expense of full architectural
            customisation.
          </p>
        </section>

        {/* ========== EXISTING CDC COMPARISON ========== */}
        <section id="existing-cdc" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How this differs from existing CDC
          </h2>
          <p className="text-slate-700 leading-relaxed">
            NSW already has a Complying Development pathway under State
            Environmental Planning Policy (Exempt and Complying Development
            Codes) 2008. It is widely used for single dwellings, alterations,
            and{' '}
            <Link
              href="/blog/can-i-build-a-granny-flat-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              granny flats
            </Link>
            . The Pattern Book pathway extends this concept in two ways:
          </p>
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Pre-approved designs eliminate the design assessment
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Under existing CDC, the certifier still assesses whether your
                specific design meets all development standards. Under the
                Pattern Book pathway, the design has already been assessed. The
                certifier only checks whether the design fits your site.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Medium-density scope
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Existing CDC is primarily used for single dwellings and
                ancillary structures. The Pattern Book pathway is designed to
                include dual occupancies, terraces, and other medium-density
                typologies &mdash; housing types that currently almost always
                require a full DA.
              </p>
            </div>
          </div>
        </section>

        {/* ========== LIMITATIONS ========== */}
        <section id="limitations" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Limitations and open questions
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Pattern Book pathway is promising but not yet operational. Several
            questions remain unanswered:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Which designs will be included?</span>{' '}
              The design catalogue has not been published. The range of
              typologies, lot sizes, and configurations will determine how
              broadly the pathway applies in practice.
            </li>
            <li>
              <span className="font-medium">DCP override provisions</span>{' '}
              &mdash; many council DCPs impose controls (setbacks, landscaping,
              parking rates) that differ from SEPP standards. Whether Pattern
              Book designs override or must comply with local DCP controls is
              not yet settled.
            </li>
            <li>
              <span className="font-medium">Neighbour notification</span>{' '}
              &mdash; CDC currently requires no neighbour notification. For
              medium-density Pattern Book developments, this may face community
              resistance.
            </li>
            <li>
              <span className="font-medium">Architectural homogeneity</span>{' '}
              &mdash; if adoption is high, entire streets could be built from
              the same pattern book. Design variation requirements have not been
              specified.
            </li>
            <li>
              <span className="font-medium">Commencement date</span> &mdash;
              the pathway depends on the Building Bill 2026 and supporting
              regulations, which have not yet commenced.
            </li>
          </ul>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check if your site qualifies for CDC
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect identifies zoning, development standards, and
              site-specific constraints for any NSW address. See whether flood,
              heritage, bushfire, or other overlays would exclude your site from
              the CDC pathway.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/check"
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-500 transition-colors"
                page="pattern-book-homes-nsw-cdc-pathway"
                cta="check_address"
              >
                Check an address
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/blog/nsw-building-bill-2026-certifier-penalties"
                className="inline-flex items-center gap-2 px-6 py-3 border border-slate-200 text-slate-700 text-sm font-medium rounded-xl hover:border-teal-300 hover:text-teal-700 transition-colors"
              >
                Read about the Building Bill
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
