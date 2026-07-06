import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Modular and Prefab Homes in NSW: How the 2026 Building Bill Changes Everything — PlotDetect',
  description:
    'The NSW Building Bill 2026 formally recognises modular and off-site construction for the first time. New compliance pathways, Pattern Book CDC, and certifier penalties reshape how prefab homes get approved.',
  keywords: [
    'modular homes NSW planning approval',
    'prefab housing NSW rules 2026',
    'NSW Building Bill 2026 modular',
    'off-site construction NSW regulations',
    'pattern book CDC NSW',
    'modular construction compliance NSW',
    'prefabricated building NSW law',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Before vs after the Building Bill */
function BeforeAfterDiagram() {
  const rows = [
    {
      aspect: 'Legal recognition',
      before: 'No statutory definition of modular/prefab. Falls through gaps between EPA Act and LG Act.',
      after: '"Prefabricated buildings" formally defined in legislation. NSW is first Australian jurisdiction to do this.',
    },
    {
      aspect: 'Approval pathway',
      before: 'Triple consent: DA (EPA Act) + s68 installation (LG Act) + building certification. Three separate applications, fees, consultants.',
      after: 'Consolidated Building Approval replaces Construction Certificates. Fewer separate applications for recognised prefab.',
    },
    {
      aspect: 'Fastest pathway',
      before: 'CDC (~20 days) on qualifying lots. Not available for many modular types.',
      after: 'Pattern Book designs eligible for 10-day CDC. Pre-approved designs skip design assessment entirely.',
    },
    {
      aspect: 'Interstate recognition',
      before: 'Factory-certified modules in one state not recognised in another. Re-certification required on arrival.',
      after: 'Building Commission oversight creates framework for interstate recognition of factory certification.',
    },
    {
      aspect: 'Manufacturer liability',
      before: 'Unclear chain of responsibility. Site certifiers held liable for factory defects.',
      after: 'Chain of responsibility established. Off-site manufacturers legally accountable. Certifier penalties up to $1.1M.',
    },
    {
      aspect: 'BCA compliance',
      before: 'Ambiguous for structures in the "caravan or building?" grey zone. Some avoided BCA via classification arbitrage.',
      after: 'Full BCA/NCC compliance required for all prefabricated buildings. No more classification arbitrage.',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Before and after the Building Bill 2026
      </p>
      <div className="space-y-4">
        {rows.map((row) => (
          <div
            key={row.aspect}
            className="rounded-xl border border-slate-200 bg-white overflow-hidden"
          >
            <div className="px-4 py-2 bg-slate-100 border-b border-slate-200">
              <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                {row.aspect}
              </p>
            </div>
            <div className="grid sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-slate-100">
              <div className="p-4">
                <p className="text-xs font-semibold text-red-600 uppercase tracking-wider mb-1">
                  Before (current)
                </p>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {row.before}
                </p>
              </div>
              <div className="p-4">
                <p className="text-xs font-semibold text-green-600 uppercase tracking-wider mb-1">
                  After (2027+)
                </p>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {row.after}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Visual 2 — Key changes summary card */
function KeyChangesSummary() {
  const changes = [
    {
      title: 'Pattern Book 10-day CDC',
      desc: 'Pre-approved designs can be approved in 10 days via complying development certificate, down from 20+ days for standard CDC or months for DA.',
      icon: '10d',
      color: 'bg-green-100 text-green-700',
    },
    {
      title: '$1.1M certifier penalties',
      desc: 'Maximum penalties for building certifiers increase to $1.1M (individuals) and higher for corporations. Aimed at eliminating non-compliance in certification.',
      icon: '$1.1M',
      color: 'bg-red-100 text-red-700',
    },
    {
      title: 'Building Commission NSW',
      desc: 'New regulatory body with powers to audit, investigate, and enforce across the building lifecycle. Oversight of both on-site and off-site construction.',
      icon: 'BC',
      color: 'bg-blue-100 text-blue-700',
    },
    {
      title: '20% cost reduction (est.)',
      desc: 'Productivity Commission estimates modular methods reduce construction costs by 20% and build times by 50% compared to traditional on-site construction.',
      icon: '-20%',
      color: 'bg-teal-100 text-teal-700',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Key changes at a glance
      </p>
      <div className="grid sm:grid-cols-2 gap-4">
        {changes.map((change) => (
          <div
            key={change.title}
            className="rounded-xl border border-slate-200 bg-white p-5"
          >
            <div className="flex items-start gap-3">
              <span
                className={`flex-shrink-0 px-2 py-1 rounded-lg text-xs font-bold ${change.color}`}
              >
                {change.icon}
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  {change.title}
                </p>
                <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                  {change.desc}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function ModularPrefabBuildingBillPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Modular and prefab homes in NSW: how the 2026 Building Bill changes everything"
        description="The Building Bill formally recognises modular construction and creates a new compliance pathway. Before vs after, who benefits, and implementation timeline."
        slug="modular-prefab-homes-nsw-building-bill-2026"
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
          Modular and prefab homes in NSW: how the 2026 Building Bill changes
          everything
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          The Building (Approvals and Practitioners) Bill 2026 formally
          recognises modular and off-site construction in NSW law for the first
          time. It creates a clearer compliance pathway, introduces pre-approved
          Pattern Book designs eligible for 10-day CDC, and establishes
          manufacturer accountability with certifier penalties up to $1.1M.
          Implementation begins 2027.
        </p>
      </div>

      {/* Immediate value: key changes card */}
      <KeyChangesSummary />

      {/* Body */}
      <div className="space-y-10">
        {/* ========== SECTION 1: Current problems ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What is broken in the current system
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Modular and prefabricated housing has been possible in NSW for
            decades, but the regulatory framework was never designed for it.
            The result is a series of structural barriers that add cost, time,
            and uncertainty:
          </p>
          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                No legal definition of modular construction
              </h3>
              <p className="text-slate-700 leading-relaxed">
                NSW planning law has no category for &ldquo;modular&rdquo; or
                &ldquo;prefabricated&rdquo; buildings. A factory-built home is
                classified as either a caravan (LG Act), a manufactured home
                (LG Act + Housing SEPP), or a building (EPA Act) &mdash;
                depending on physical characteristics the court assesses after
                installation. This creates uncertainty for manufacturers,
                builders, and owners before a single module leaves the factory.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Site-specific certification
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A module certified for compliance in a factory must be
                re-certified on site. The site certifier is held liable for
                defects in factory construction they did not supervise. This
                discourages certifiers from taking on modular projects and adds
                redundant assessment costs.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Interstate non-recognition
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A modular home factory-certified in Victoria or Queensland is
                not automatically recognised in NSW. Modules must be
                re-assessed against NSW requirements on arrival, adding weeks
                and thousands of dollars. This fragments the national market
                and prevents manufacturers from achieving the scale that drives
                cost reductions.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Triple-consent problem
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Manufactured homes on individual lots (not estates) require
                three separate approvals: a DA under the EPA Act, s68
                installation approval under the LG Act, and building
                certification. Each has its own fees, consultants, and timeline.
                For more detail on how this affects smaller structures, see our
                guide to{' '}
                <Link
                  href="/blog/tiny-houses-nsw-planning-rules"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  tiny house planning rules in NSW
                </Link>
                .
              </p>
            </div>
          </div>
        </section>

        {/* ========== SECTION 2: Before/after ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What the Building Bill 2026 changes
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Bill addresses each of these barriers. Some changes are
            immediate when the Act commences (expected 2027). Others depend on
            regulations being drafted throughout 2026&ndash;2027. Here is the
            full before-and-after comparison:
          </p>
          <BeforeAfterDiagram />
        </section>

        {/* ========== SECTION 3: Pattern Book ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The Pattern Book: pre-approved designs in 10 days
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Bill introduces a Pattern Book of pre-approved building designs
            that qualify for a 10-day complying development certificate. The NSW
            Government Architect is developing the initial designs.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For modular manufacturers and granny flat builders, this is
            potentially the most significant change. If a design matches a
            Pattern Book template and the lot meets CDC eligibility criteria
            (correct zoning, adequate size, no excluding overlays like Heritage
            Conservation Areas or flood), the approval process reduces to a
            spatial and overlay check rather than a full design assessment.
          </p>
          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              What to watch
            </p>
            <p className="text-sm text-slate-700 leading-relaxed">
              The Pattern Book&apos;s impact depends entirely on what designs
              are included. If secondary dwellings and small modular homes
              receive Pattern Book templates, this will be the most significant
              improvement to small housing approvals in NSW history. If the
              initial Pattern Book focuses on larger housing types, the benefit
              for granny flats and tiny homes will be limited. The design list
              has not been published yet.
            </p>
          </div>
          <p className="text-slate-700 leading-relaxed">
            Even with Pattern Book eligibility, certain overlays still exclude
            properties from the CDC pathway &mdash; including Heritage
            Conservation Areas. For properties in HCAs, see our guide on{' '}
            <Link
              href="/blog/heritage-conservation-area-granny-flat-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              why CDC is blocked in heritage areas and what to do instead
            </Link>
            .
          </p>
        </section>

        {/* ========== SECTION 4: Who benefits ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Who benefits and who faces higher costs
          </h2>
          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-green-200 bg-green-50/30 p-6">
              <p className="text-sm font-bold text-green-800 mb-3">
                Clear winners
              </p>
              <ul className="space-y-2 text-sm text-slate-700">
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">&#9679;</span>
                  <span>
                    <span className="font-medium">
                      Established modular manufacturers
                    </span>{' '}
                    &mdash; formal recognition legitimises the sector, Pattern
                    Book inclusion creates demand, interstate recognition opens
                    markets
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">&#9679;</span>
                  <span>
                    <span className="font-medium">
                      Granny flat builders (compliant)
                    </span>{' '}
                    &mdash; 10-day CDC via Pattern Book dramatically reduces
                    approval time and cost for qualifying lots
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">&#9679;</span>
                  <span>
                    <span className="font-medium">
                      Regional housing projects
                    </span>{' '}
                    &mdash; modular construction is 50% faster than traditional
                    building (Productivity Commission estimate), critical for
                    areas with trade shortages
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">&#9679;</span>
                  <span>
                    <span className="font-medium">Homeowners</span> &mdash;
                    clearer pathways reduce consultant costs and approval
                    uncertainty
                  </span>
                </li>
              </ul>
            </div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
              <p className="text-sm font-bold text-amber-800 mb-3">
                Mixed impact
              </p>
              <ul className="space-y-2 text-sm text-slate-700">
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">&#9679;</span>
                  <span>
                    <span className="font-medium">
                      Small-scale / artisan tiny home builders
                    </span>{' '}
                    &mdash; chain of responsibility requirements and full BCA
                    compliance increase the compliance floor. DIY builds that
                    previously avoided BCA through classification ambiguity are
                    now explicitly required to comply.
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">&#9679;</span>
                  <span>
                    <span className="font-medium">Building certifiers</span>{' '}
                    &mdash; clearer liability framework but penalties up to
                    $1.1M raise the stakes. Factory-to-site handover
                    responsibilities will need to be carefully managed.
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* ========== SECTION 5: The numbers ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The cost and productivity context
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Bill responds to well-documented problems in Australian housing
            construction. The Productivity Commission&apos;s February 2026
            report found:
          </p>
          <div className="rounded-2xl border border-slate-200 p-6">
            <div className="grid sm:grid-cols-2 gap-6">
              <div>
                <p className="text-3xl font-bold text-slate-900">$320K</p>
                <p className="text-sm text-slate-600 mt-1">
                  Regulatory cost currently added to a detached house
                  (Productivity Commission finding)
                </p>
              </div>
              <div>
                <p className="text-3xl font-bold text-slate-900">$330K</p>
                <p className="text-sm text-slate-600 mt-1">
                  Estimated savings per apartment block from Pattern Book
                  standardisation
                </p>
              </div>
              <div>
                <p className="text-3xl font-bold text-slate-900">50%</p>
                <p className="text-sm text-slate-600 mt-1">
                  Faster build times for modular vs traditional construction
                  (Productivity Commission)
                </p>
              </div>
              <div>
                <p className="text-3xl font-bold text-slate-900">77,662</p>
                <p className="text-sm text-slate-600 mt-1">
                  Homes behind target under the National Housing Accord as of
                  mid-2026
                </p>
              </div>
            </div>
          </div>
          <p className="text-slate-700 leading-relaxed">
            Housing construction productivity in Australia has halved since
            1995. The Accord shortfall creates sustained federal pressure on
            states to remove supply barriers. Modular construction and secondary
            dwellings are politically straightforward wins &mdash; small
            footprint, low infrastructure cost, fast build times.
          </p>
        </section>

        {/* ========== SECTION 6: Timeline ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Timeline and implementation
          </h2>
          <div className="relative rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8">
            <div className="absolute left-8 top-10 bottom-10 w-0.5 bg-slate-200 hidden sm:block" />
            <div className="space-y-6">
              {[
                {
                  date: '2026 (now)',
                  label: 'Bill passed',
                  desc: 'Building (Approvals and Practitioners) Bill 2026 enacted. Regulations being drafted.',
                  color: 'bg-blue-500',
                },
                {
                  date: '2026 H2',
                  label: 'Draft regulations',
                  desc: 'Building Commission NSW to publish draft regulations including prefabricated building definitions and Pattern Book criteria.',
                  color: 'bg-blue-400',
                },
                {
                  date: '2027',
                  label: 'Commencement',
                  desc: 'Act commences. New Building Approval pathway replaces Construction Certificates. Building Commission operational.',
                  color: 'bg-teal-500',
                },
                {
                  date: '2027+',
                  label: 'Pattern Book rollout',
                  desc: 'NSW Government Architect publishes Pattern Book designs. Eligible designs qualify for 10-day CDC.',
                  color: 'bg-green-500',
                },
              ].map((event) => (
                <div key={event.date} className="relative pl-0 sm:pl-10">
                  <div
                    className={`hidden sm:block absolute left-6 top-1.5 w-3.5 h-3.5 rounded-full ${event.color} ring-4 ring-white`}
                  />
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                    {event.date}
                  </p>
                  <p className="text-sm font-semibold text-slate-900 mt-0.5">
                    {event.label}
                  </p>
                  <p className="text-sm text-slate-600 mt-0.5">
                    {event.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ========== SECTION 7: What to do now ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What to do now
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Bill is law but the regulations are not yet finalised. Until
            commencement in 2027, the current approval pathways still apply.
            That said, there are steps worth taking now:
          </p>
          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                For modular manufacturers
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Monitor Building Commission NSW for draft regulation
                consultation. The prefabricated building definition details
                will determine exactly which products benefit. Consider
                submitting to the Pattern Book design process if the Government
                Architect opens consultation.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                For homeowners planning a granny flat
              </h3>
              <p className="text-slate-700 leading-relaxed">
                If your lot qualifies for CDC today, there is no reason to wait
                &mdash; the current pathway works. If you are considering a
                modular granny flat on a lot that currently requires DA (heritage
                overlay, bushfire, flood), the Bill may simplify the process but
                will not remove overlay-based exclusions. Check your lot&apos;s
                planning constraints first.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                For builders and developers
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The chain of responsibility provisions will require
                documentation of factory quality assurance. Start establishing
                QA documentation frameworks now. When Pattern Book designs are
                published, integrating them into your product line will give you
                a competitive advantage in approval speed.
              </p>
            </div>
          </div>
        </section>

        {/* ========== FAQ ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Frequently asked questions
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                When does the Building Bill 2026 take effect?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The Bill has been enacted but commencement depends on
                supporting regulations being finalised. Expected commencement
                is 2027. Regulations are being drafted throughout 2026&ndash;2027.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does the Bill make modular homes cheaper?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Indirectly, yes. By reducing approval steps (consolidated
                Building Approval), enabling faster approval (10-day Pattern
                Book CDC), and removing interstate re-certification, the Bill
                reduces the regulatory cost component. The Productivity
                Commission estimates modular methods reduce overall
                construction costs by 20%. However, full BCA compliance
                requirements may increase costs for the cheapest DIY builds
                that previously avoided compliance.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does this affect tiny houses on wheels?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Registered tiny houses on wheels that meet caravan dimensions
                remain governed by LG Act Regulation 77 exemptions. The Bill
                does not change this category. However, for tiny homes that
                are permanently installed and don&apos;t qualify as caravans,
                the new &ldquo;prefabricated building&rdquo; pathway creates
                a clearer route. See our{' '}
                <Link
                  href="/blog/tiny-houses-nsw-planning-rules"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  guide to tiny house planning rules
                </Link>{' '}
                for the full classification spectrum.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Will the Pattern Book include granny flat designs?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The Pattern Book design list has not been published yet. The
                NSW Government Architect is developing the initial designs. If
                secondary dwellings are included, it would be the most
                significant practical improvement to granny flat approvals in
                NSW. We will update this article when the design list is
                available.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check if your lot qualifies for CDC today
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              While the Building Bill&apos;s new pathways are coming in 2027,
              many lots already qualify for the existing CDC pathway for granny
              flats and secondary dwellings. Check your address to see what
              zoning, overlays, and DCP controls apply.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/check"
                page="modular-prefab-homes-nsw-building-bill-2026"
                cta="check_address"
                className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              >
                Check your address
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/reports/granny-flat"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-teal-700 text-sm font-medium rounded-xl border border-teal-200 hover:bg-teal-50 transition-colors"
              >
                Granny flat feasibility report
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
