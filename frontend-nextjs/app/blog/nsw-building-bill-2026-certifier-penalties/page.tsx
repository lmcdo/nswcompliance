import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'The NSW Building Bill 2026: $1.1M Certifier Penalties and What It Means for the Industry — PlotDetect',
  description:
    'The NSW Building Bill 2026 introduces $1.1M penalties for certifiers, a Building Commission with investigative powers, and mandatory professional standards. What builders, certifiers, and developers need to prepare for.',
  keywords: [
    'NSW Building Bill 2026',
    'building certifier penalties NSW',
    'NSW building reform 2026',
    'building compliance NSW changes',
    'Building Commission NSW',
    'Opal Tower building defects',
    'certifier registration NSW',
    'building insurance NSW',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Before vs After comparison card */
function BeforeAfterComparison() {
  const rows = [
    {
      area: 'Maximum certifier penalty',
      before: 'Up to $110,000',
      after: 'Up to $1.1 million',
    },
    {
      area: 'Regulatory body',
      before: 'NSW Fair Trading (limited scope)',
      after: 'Building Commission (dedicated, investigative)',
    },
    {
      area: 'Certifier registration',
      before: 'Accreditation via BPB',
      after: 'Mandatory registration + CPD requirements',
    },
    {
      area: 'Personal liability',
      before: 'Corporate entity shields common',
      after: 'Individual practitioner accountability',
    },
    {
      area: 'Builder insurance',
      before: 'Home Building Compensation Fund',
      after: 'Expanded mandatory insurance obligations',
    },
    {
      area: 'Defect rectification',
      before: 'Civil dispute process',
      after: 'Statutory rectification orders with enforcement',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        What changes under the Building Bill 2026
      </p>
      <div className="space-y-0">
        {/* Header */}
        <div className="grid grid-cols-3 gap-4 pb-3 border-b border-slate-200">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Area
          </span>
          <span className="text-xs font-bold text-red-600 uppercase tracking-wider">
            Current regime
          </span>
          <span className="text-xs font-bold text-teal-600 uppercase tracking-wider">
            Under the Bill
          </span>
        </div>
        {rows.map((row) => (
          <div
            key={row.area}
            className="grid grid-cols-3 gap-4 py-3 border-b border-slate-100 last:border-0"
          >
            <span className="text-sm font-medium text-slate-900">
              {row.area}
            </span>
            <span className="text-sm text-slate-600">{row.before}</span>
            <span className="text-sm text-slate-700 font-medium">
              {row.after}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Visual 2 — Implementation timeline */
function ImplementationTimeline() {
  const phases = [
    {
      period: '2017-2019',
      label: 'Defects crisis emerges',
      desc: 'Opal Tower evacuation (2018), Mascot Towers cracking (2019). Public confidence in building certification collapses.',
      color: 'bg-red-500',
    },
    {
      period: '2019-2020',
      label: 'Shergold-Weir + Lambert reports',
      desc: 'Independent reviews find systemic failures in certification, compliance, and accountability across the building sector.',
      color: 'bg-amber-500',
    },
    {
      period: '2020-2023',
      label: 'Design & Building Practitioners Act',
      desc: 'Interim reforms: design practitioner registration, duty of care provisions. First step toward broader reform.',
      color: 'bg-amber-500',
    },
    {
      period: '2025-2026',
      label: 'Building Bill introduced',
      desc: 'Comprehensive overhaul: Building Commission, tenfold penalty increase, mandatory registration, expanded insurance.',
      color: 'bg-teal-500',
    },
    {
      period: '2026-2027',
      label: 'Staged commencement (expected)',
      desc: 'Building Commission establishment, new registration requirements, penalty regime commencement. Transition periods for existing practitioners.',
      color: 'bg-slate-300',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        From defects crisis to legislative overhaul
      </p>
      <div className="relative">
        <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-slate-200" />
        <div className="space-y-6">
          {phases.map((e) => (
            <div key={e.period} className="relative pl-10">
              <div
                className={`absolute left-1.5 top-1.5 w-3.5 h-3.5 rounded-full ${e.color} ring-4 ring-white`}
              />
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                {e.period}
              </p>
              <p className="text-sm font-semibold text-slate-900 mt-0.5">
                {e.label}
              </p>
              <p className="text-sm text-slate-600 mt-0.5">{e.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Visual 3 — Building Commission powers summary */
function CommissionPowers() {
  const powers = [
    {
      title: 'Investigation',
      items: [
        'Enter premises and inspect building work',
        'Require production of documents and records',
        'Examine practitioners under oath',
      ],
    },
    {
      title: 'Enforcement',
      items: [
        'Issue stop-work orders',
        'Issue rectification orders for defective work',
        'Impose conditions on practitioner registration',
      ],
    },
    {
      title: 'Discipline',
      items: [
        'Suspend or cancel registration',
        'Impose fines up to $1.1M (individuals)',
        'Publish disciplinary findings',
      ],
    },
  ];

  return (
    <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Building Commission — proposed powers
      </p>
      <div className="grid sm:grid-cols-3 gap-4">
        {powers.map((group) => (
          <div
            key={group.title}
            className="rounded-xl bg-white border border-slate-200 p-5"
          >
            <p className="text-sm font-bold text-slate-900 mb-3">
              {group.title}
            </p>
            <ul className="space-y-2">
              {group.items.map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="text-blue-500 mt-0.5 flex-shrink-0">&#9679;</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function BuildingBillCertifierPenaltiesPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`The NSW Building Bill 2026: \$1.1M certifier penalties and what it means`}
        description={`Maximum penalties up to \$1.1M, a Building Commission with investigative powers, and mandatory professional standards. What builders and certifiers need to know.`}
        slug="nsw-building-bill-2026-certifier-penalties"
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
          The NSW Building Bill 2026: $1.1M certifier penalties and what it means
          for the industry
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Maximum penalties for building certifiers jump from $110,000 to $1.1
          million. A new Building Commission gets investigative powers modelled on
          a royal commission. Mandatory registration, continuous professional
          development, and personal liability become non-negotiable. Here is what
          is changing and who needs to act.
        </p>
      </div>

      {/* Immediate value — before/after comparison */}
      <BeforeAfterComparison />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#why-this-bill" className="hover:text-teal-600">
              Why this Bill exists
            </a>
          </li>
          <li>
            <a href="#certifiers" className="hover:text-teal-600">
              What changes for certifiers
            </a>
          </li>
          <li>
            <a href="#builders" className="hover:text-teal-600">
              What changes for builders
            </a>
          </li>
          <li>
            <a href="#building-commission" className="hover:text-teal-600">
              The Building Commission
            </a>
          </li>
          <li>
            <a href="#timeline" className="hover:text-teal-600">
              Implementation timeline
            </a>
          </li>
          <li>
            <a href="#prepare" className="hover:text-teal-600">
              How to prepare
            </a>
          </li>
        </ul>
      </nav>

      {/* Body */}
      <div className="space-y-10">
        {/* ========== WHY THIS BILL EXISTS ========== */}
        <section id="why-this-bill" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why this Bill exists
          </h2>
          <p className="text-slate-700 leading-relaxed">
            On Christmas Eve 2018, residents of Opal Tower in Sydney Olympic Park
            were evacuated after cracking was discovered in pre-stressed concrete
            beams. Six months later, Mascot Towers was evacuated due to cracking
            in the primary support structure and the transfer slab of the adjacent
            building. Neither building has been fully reoccupied.
          </p>
          <p className="text-slate-700 leading-relaxed">
            These were not isolated incidents. They were the most visible symptoms
            of systemic failures identified in the Shergold-Weir report (2018) and
            the Lambert review (2020): inadequate certification, conflicted
            interests between builders and certifiers, weak enforcement powers,
            and penalties too low to deter non-compliance.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The Design and Building Practitioners Act 2020 was the first
            legislative response, introducing design practitioner registration and
            a statutory duty of care. The Building Bill 2026 is the comprehensive
            overhaul &mdash; restructuring how building work is regulated,
            certified, and enforced across NSW.
          </p>
        </section>

        {/* ========== WHAT CHANGES FOR CERTIFIERS ========== */}
        <section id="certifiers" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What changes for certifiers
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Bill redefines the certification profession. Five changes matter
            most:
          </p>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. Mandatory registration replaces accreditation
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The current Building Professionals Board accreditation system is
                replaced by a mandatory registration scheme administered by the
                Building Commission. Registration carries explicit conditions,
                ongoing obligations, and can be suspended or cancelled for
                non-compliance.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Tenfold penalty increase
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Maximum penalties for individuals increase from approximately
                $110,000 to $1.1 million. For corporations, penalties scale
                higher. The increase is designed to make the cost of
                non-compliance genuinely punitive rather than a cost of doing
                business.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Continuous professional development
              </h3>
              <p className="text-slate-700 leading-relaxed">
                CPD becomes a condition of maintaining registration. Certifiers
                will need to demonstrate ongoing competency, not just meet a
                one-time qualification threshold. The specifics of CPD
                requirements are expected to be set by regulation.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                4. Personal liability
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The Bill strengthens personal accountability for individual
                certifiers, making it harder to shelter behind a corporate entity.
                Directors and officers of certification companies face specific
                obligations that cannot be delegated.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                5. Conflict of interest provisions
              </h3>
              <p className="text-slate-700 leading-relaxed">
                New provisions address the long-standing concern that certifiers
                appointed and paid by developers have a financial incentive to
                approve work. The Bill introduces stricter independence
                requirements and disclosure obligations.
              </p>
            </div>
          </div>
        </section>

        {/* ========== WHAT CHANGES FOR BUILDERS ========== */}
        <section id="builders" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What changes for builders
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Builders face three substantial shifts:
          </p>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Expanded insurance obligations
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The Bill expands mandatory insurance requirements for building
                work, extending coverage obligations and addressing gaps in the
                current Home Building Compensation Fund. The aim is to ensure
                homeowners have genuine recourse when defective work is
                discovered.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Statutory defect rectification
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Currently, homeowners with defective building work must pursue
                civil remedies &mdash; a process that can take years and cost tens
                of thousands in legal fees. The Bill introduces statutory
                rectification orders, giving the Building Commission power to
                compel builders to fix defective work directly.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Documentation and record-keeping
              </h3>
              <p className="text-slate-700 leading-relaxed">
                New record-keeping obligations require builders to maintain and
                provide documentation throughout the construction process. This
                creates an audit trail that did not previously exist in many
                residential projects.
              </p>
            </div>
          </div>

          <p className="text-slate-700 leading-relaxed">
            The Bill also creates a pathway for{' '}
            <Link
              href="/blog/modular-prefab-homes-nsw-building-bill-2026"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              modular and prefabricated construction
            </Link>{' '}
            to be mainstreamed, with quality assurance provisions tailored to
            factory-built components.
          </p>
        </section>

        {/* ========== BUILDING COMMISSION ========== */}
        <section id="building-commission" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The Building Commission
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The centrepiece of the Bill is a dedicated Building Commission with
            powers that go well beyond the current regulatory framework. The
            Commission replaces the fragmented oversight currently split between
            NSW Fair Trading, the Building Professionals Board, and local councils.
          </p>

          <CommissionPowers />

          <p className="text-slate-700 leading-relaxed">
            The investigative powers are notable. The Commission can require
            practitioners to produce documents, enter premises to inspect work,
            and examine witnesses. These are closer to the powers of a standing
            commission of inquiry than a licensing body.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For industry participants accustomed to a largely self-regulated
            environment, this represents a fundamental shift. The Commission is
            designed to be proactive &mdash; identifying systemic issues before
            they become Opal Tower-scale failures &mdash; rather than reactive.
          </p>
        </section>

        {/* ========== TIMELINE ========== */}
        <section id="timeline" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Implementation timeline
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Bill is expected to commence in stages. Not all provisions will
            take effect simultaneously &mdash; transition periods allow existing
            practitioners and businesses to adjust.
          </p>

          <ImplementationTimeline />

          <p className="text-slate-700 leading-relaxed">
            The staged approach is deliberate. The building certification
            workforce cannot absorb a sudden regulatory shift without transition
            periods. But the direction is unambiguous: higher standards, stronger
            enforcement, and personal accountability are coming.
          </p>
        </section>

        {/* ========== HOW TO PREPARE ========== */}
        <section id="prepare" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How to prepare
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Bill has not commenced yet, but preparation should not wait for
            gazette notices. Three steps for each group:
          </p>

          <div className="rounded-2xl border border-slate-200 p-6 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Certifiers
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Review your current insurance coverage against the expanded
                liability exposure. Start documenting CPD activities now &mdash;
                retroactive compliance is harder than ongoing compliance. Audit
                your client relationships for potential conflict of interest
                issues under the new provisions.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Builders
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Establish systematic documentation practices for all building
                work. Review your insurance arrangements and understand the gap
                between current cover and likely new requirements. For defect
                rectification exposure, consider whether your current contracts
                adequately address the Bill&apos;s statutory rectification
                framework.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Developers
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Budget for increased certification costs &mdash; the penalty
                regime will be reflected in certification fees. Factor in longer
                inspection timeframes as certifiers adopt more thorough
                documentation requirements. Ensure your building contracts
                allocate defect rectification obligations clearly.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check compliance requirements for your next project
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect identifies LEP, SEPP, and DCP controls that apply to any
              NSW address &mdash; zoning, development standards, and site-specific
              constraints. Enter an address to see what applies.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/check"
                page="nsw-building-bill-2026-certifier-penalties"
                cta="check_address"
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-500 transition-colors"
              >
                Check an address
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/for/builders"
                className="inline-flex items-center gap-2 px-6 py-3 border border-slate-200 text-slate-700 text-sm font-medium rounded-xl hover:border-teal-300 hover:text-teal-700 transition-colors"
              >
                Tools for builders
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
