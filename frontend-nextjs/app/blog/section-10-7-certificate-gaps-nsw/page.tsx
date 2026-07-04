import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'What a Section 10.7 Certificate Doesn\u2019t Tell You — PlotDetect',
  description:
    'The NSW s10.7 planning certificate covers zoning, heritage, and flood status. It does not cover flood depth, DCP controls, development potential, insurance costs, or contamination history. Here are the gaps and what to check instead.',
  keywords: [
    'section 10.7 certificate what it covers',
    'property planning certificate NSW gaps',
    's10.7 limitations',
    'planning certificate NSW what to check',
    'section 10.7 vs section 149',
    's10.7(2) vs s10.7(5)',
    'planning certificate flood risk',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual: What s10.7 covers vs what it misses                        */
/* ------------------------------------------------------------------ */

function CertificateCoversVsGaps() {
  const covers = [
    'Zoning (land use zone under the LEP)',
    'Heritage listing (local or state)',
    'Acid sulfate soil class',
    'Bush Fire Prone Land status (yes/no)',
    'Flood planning area notation (binary)',
    'Contamination notation (if council has listed it)',
    'Road widening or land acquisition reservations',
    'Building line setbacks (LEP-level only)',
  ];

  const misses = [
    'Flood depth, frequency, or overland flow risk',
    'Insurance cost implications',
    'DCP controls (setbacks, FSR bonuses, parking, landscaping)',
    'Development potential (granny flat, subdivision, dual occ)',
    'Biodiversity Values Map / BDAR trigger status',
    'Neighbour DA activity or recent approvals',
    'Contamination history (only current notations)',
    'Infrastructure contribution levies (s7.11/s7.12)',
    'Climate risk projections (coastal, heat, future flood)',
    'Strata scheme details or company title status',
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Section 10.7 planning certificate &mdash; what you get vs what you
        don&apos;t
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        <div className="rounded-xl border-2 border-emerald-200 bg-white p-5">
          <p className="text-sm font-bold text-emerald-700 mb-3">
            What the certificate covers
          </p>
          {covers.map((item) => (
            <div
              key={item}
              className="flex items-start gap-2.5 py-1.5 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center text-xs text-emerald-600 mt-0.5">
                &#10003;
              </span>
              <span className="text-sm text-slate-700">{item}</span>
            </div>
          ))}
        </div>

        <div className="rounded-xl border-2 border-red-200 bg-white p-5">
          <p className="text-sm font-bold text-red-700 mb-3">
            What the certificate does not cover
          </p>
          {misses.map((item) => (
            <div
              key={item}
              className="flex items-start gap-2.5 py-1.5 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-4 h-4 rounded-full bg-red-100 flex items-center justify-center text-xs text-red-600 mt-0.5">
                &times;
              </span>
              <span className="text-sm text-slate-700">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Visual: Beyond the certificate checklist                           */
/* ------------------------------------------------------------------ */

function BeyondCertificateChecklist() {
  const checks = [
    {
      label: 'Get an insurance quote',
      detail:
        'Reveals the insurer\u2019s risk model for the address \u2014 flood, bushfire, storm. Free and more informative than any certificate.',
      source: 'Any insurer (free)',
    },
    {
      label: 'Check flood depth and frequency',
      detail:
        'The certificate says flood controls apply. It does not say how deep the water gets. Check council flood studies or the SES Flood Data Portal.',
      source: 'SES Flood Data Portal / council',
    },
    {
      label: 'Check the Biodiversity Values Map',
      detail:
        'If your land intersects, any clearing triggers the Biodiversity Offsets Scheme. Costs: $50K\u2013$500K. Not disclosed on s10.7.',
      source: 'NSW SEED Portal (free)',
    },
    {
      label: 'Review the DCP for specific controls',
      detail:
        'DCPs contain setbacks, FSR, height, parking, landscaping \u2014 none of which appear on the certificate. These controls determine what you can actually build.',
      source: 'Council website or PlotDetect',
    },
    {
      label: 'Check for nearby DAs',
      detail:
        'An approved DA next door \u2014 a boarding house, a 6-storey building, a childcare centre \u2014 will not appear on your certificate.',
      source: 'NSW Planning Portal / council',
    },
    {
      label: 'Check infrastructure contribution rates',
      detail:
        'Section 7.11 and 7.12 contribution levies can add $20K\u2013$80K+ to any development. Not on the s10.7.',
      source: 'Council contributions plan',
    },
    {
      label: 'Check contamination history',
      detail:
        'The certificate shows current contamination notations. It does not show former uses (petrol station, dry cleaner, industrial) or remediation status.',
      source: 'NSW EPA CLR (free)',
    },
    {
      label: 'Check climate risk exposure',
      detail:
        'Coastal erosion, urban heat, future flood mapping under climate projections. None of this is on the certificate today.',
      source: 'PlotDetect Climate Risk Score',
    },
  ];

  return (
    <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        What else to check beyond the s10.7
      </p>
      <div className="space-y-3">
        {checks.map((c, i) => (
          <div
            key={c.label}
            className="rounded-xl bg-white border border-slate-200 p-4"
          >
            <div className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 flex items-center justify-center text-xs font-bold text-teal-700">
                {i + 1}
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  {c.label}
                </p>
                <p className="text-sm text-slate-600 mt-0.5">{c.detail}</p>
                <p className="text-xs text-slate-400 mt-1">
                  Source: {c.source}
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

export default function Section107CertificateGapsPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`What a section 10.7 certificate doesn't tell you`}
        description="The planning certificate covers zoning, heritage, and hazard overlays. It misses flood depth, insurance costs, DCP controls, development potential, and more."
        slug="section-10-7-certificate-gaps-nsw"
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
          What a Section 10.7 certificate doesn&apos;t tell you
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          The s10.7 planning certificate is a legal requirement in every NSW
          property transaction. It covers zoning, heritage, and basic hazard
          overlays. But it does not cover flood depth, DCP controls, development
          potential, insurance costs, contamination history, or biodiversity
          offset triggers. Here are the gaps &mdash; and what to check instead.
        </p>
      </div>

      {/* Immediate value: covers vs gaps */}
      <CertificateCoversVsGaps />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#what-it-contains" className="hover:text-teal-600">
              What the certificate actually contains
            </a>
          </li>
          <li>
            <a href="#what-it-misses" className="hover:text-teal-600">
              What it misses &mdash; and why it matters
            </a>
          </li>
          <li>
            <a href="#s107-2-vs-5" className="hover:text-teal-600">
              The difference between s10.7(2) and s10.7(5)
            </a>
          </li>
          <li>
            <a href="#beyond-certificate" className="hover:text-teal-600">
              What to check beyond the certificate
            </a>
          </li>
          <li>
            <a href="#conveyancers" className="hover:text-teal-600">
              Why conveyancers should go further
            </a>
          </li>
          <li>
            <a href="#faq" className="hover:text-teal-600">
              Frequently asked questions
            </a>
          </li>
        </ul>
      </nav>

      {/* Body */}
      <div className="space-y-10">
        {/* SECTION 1: What it contains */}
        <section id="what-it-contains" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What the certificate actually contains
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A Section 10.7 planning certificate is issued by the local council
            under Part 10.7 of the{' '}
            <span className="font-medium">
              Environmental Planning and Assessment Act 1979
            </span>
            . It discloses information prescribed by regulation, drawn from the
            council&apos;s records about planning instruments that apply to the
            land. The standard s10.7(2) certificate includes:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              The zoning of the land under the Local Environmental Plan
            </li>
            <li>
              Whether the land is heritage-listed (local or state significance)
            </li>
            <li>
              Whether the land is in a flood planning area (binary yes/no)
            </li>
            <li>
              Bush Fire Prone Land status
            </li>
            <li>Acid sulfate soil classification</li>
            <li>
              Contamination notations (only if council has recorded them)
            </li>
            <li>
              Road widening, road realignment, or land acquisition proposals
            </li>
            <li>
              Whether any SEPP, REP, or deemed SEPP provisions apply
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            This information is drawn from planning instruments &mdash; the LEP,
            SEPPs, and any relevant state policies. It is factual. It is
            limited. And it is exactly the same for a $400,000 unit in
            Campbelltown and a $4,000,000 house in Mosman.
          </p>
        </section>

        {/* SECTION 2: What it misses */}
        <section id="what-it-misses" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What it misses &mdash; and why it matters
          </h2>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Flood depth and frequency
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The certificate tells you flood controls apply. It does not tell
                you whether the property floods to 0.3m or 3m, whether it is a
                1-in-20-year or 1-in-100-year flood, or whether there is
                overland flow risk. After the{' '}
                <Link
                  href="/blog/section-10-7-flood-risk-nsw"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  2021 and 2023 legislative changes
                </Link>
                , the certificate may now show less flood information than it
                used to.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                DCP controls
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Development Control Plans contain the specific rules that govern
                what you can build: setbacks, floor space ratios, height
                controls, parking requirements, landscaping minimums, lot width
                requirements. None of this appears on the s10.7 certificate.
                The certificate confirms a DCP exists. It does not tell you what
                it says.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Development potential
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Can you build a granny flat? Is the lot large enough for
                subdivision? Does the zoning permit dual occupancy? These are the
                questions buyers care about most, and the certificate answers
                none of them. Determining development potential requires
                cross-referencing the LEP zone, SEPP Housing 2021,
                the DCP, and site-specific constraints.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Biodiversity offset triggers
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The NSW Government has explicitly confirmed that the s10.7
                certificate does not disclose whether land is on the Biodiversity
                Values Map. If it is, any vegetation clearing triggers the
                Biodiversity Offsets Scheme &mdash; a process that costs $50,000
                to $500,000 and takes 4 to 12 months. Discovering this after
                exchange is a significant financial risk.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Insurance cost implications
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The certificate tells you hazard overlays apply. It does not tell
                you what that means for insurance. A property in a flood planning
                area may face $1,000 to $5,000 higher annual premiums. A
                property on Bush Fire Prone Land at{' '}
                <Link
                  href="/blog/bushfire-attack-level-bal-property-buyers"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  BAL-40 or BAL-FZ
                </Link>{' '}
                may be uninsurable. None of this is on the certificate.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Neighbour development activity
              </h3>
              <p className="text-slate-700 leading-relaxed">
                An approved DA next door &mdash; a boarding house, a multi-storey
                residential flat building, a childcare centre &mdash; does not
                appear anywhere on your planning certificate. Neither does a
                recently lodged DA that has not yet been determined.
              </p>
            </div>
          </div>
        </section>

        {/* SECTION 3: s10.7(2) vs s10.7(5) */}
        <section id="s107-2-vs-5" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The difference between s10.7(2) and s10.7(5)
          </h2>
          <div className="grid sm:grid-cols-2 gap-6 mt-2">
            <div className="rounded-xl border-2 border-slate-200 bg-white p-5">
              <p className="text-sm font-bold text-slate-900 mb-3">
                s10.7(2) &mdash; standard certificate
              </p>
              <ul className="space-y-2 text-sm text-slate-700">
                <li className="flex items-start gap-2">
                  <span className="text-slate-400 mt-0.5">&#9679;</span>
                  Costs $53 (2026 rate)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-slate-400 mt-0.5">&#9679;</span>
                  Includes only information prescribed by regulation
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-slate-400 mt-0.5">&#9679;</span>
                  Required for every property transaction
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-slate-400 mt-0.5">&#9679;</span>
                  Covers: zoning, heritage, hazard overlays, road proposals
                </li>
              </ul>
            </div>
            <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
              <p className="text-sm font-bold text-teal-700 mb-3">
                s10.7(5) &mdash; additional information
              </p>
              <ul className="space-y-2 text-sm text-slate-700">
                <li className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#9679;</span>
                  Costs $153 (2026 rate)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#9679;</span>
                  Council may include any additional information it considers
                  relevant
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#9679;</span>
                  Content varies significantly between councils
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#9679;</span>
                  May include: flooding detail, contamination notes, drainage,
                  road classification
                </li>
              </ul>
            </div>
          </div>
          <p className="text-slate-700 leading-relaxed">
            The s10.7(5) certificate can include more detail, but councils are
            not obligated to include specific information. What you get depends
            entirely on the council. Some councils provide substantial
            additional detail. Others provide almost nothing beyond the
            standard s10.7(2) content.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Neither version tells you what the DCP says, what you can build,
            or what insurance will cost. They are regulatory disclosure
            documents, not property intelligence reports.
          </p>
        </section>

        {/* SECTION 4: Beyond the certificate */}
        <section id="beyond-certificate" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What to check beyond the certificate
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The s10.7 is a starting point. Here are eight checks that fill the
            gaps:
          </p>
          <BeyondCertificateChecklist />
          <p className="text-slate-700 leading-relaxed">
            PlotDetect&apos;s{' '}
            <Link
              href="/reports/conveyancing"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Conveyancing Planning Disclosure report
            </Link>{' '}
            consolidates many of these checks into a single document &mdash;
            covering LEP, SEPP, DCP constraints, environmental overlays, and
            development potential for any NSW address.
          </p>
        </section>

        {/* SECTION 5: Why conveyancers should go further */}
        <section id="conveyancers" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why conveyancers should go further
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The s10.7 certificate meets the minimum legal requirement for
            property transaction disclosure. But minimum disclosure is not the
            same as adequate due diligence. A buyer who discovers a $50,000
            biodiversity offset requirement after exchange &mdash; information
            the certificate does not disclose &mdash; has a legitimate
            grievance.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Conveyancers who supplement the certificate with planning
            intelligence reports, flood checks, and environmental overlay
            verification are providing genuine risk protection. It is also a
            professional liability argument: documenting that you checked
            beyond the minimum is stronger than documenting that you only
            checked the minimum.
          </p>
          <p className="text-slate-700 leading-relaxed">
            PlotDetect provides{' '}
            <Link
              href="/for/conveyancers"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              planning disclosure tools for conveyancers
            </Link>{' '}
            that can be added as a disbursement to the client&apos;s settlement
            statement.
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
                Is a s10.7 certificate the same as a s149 certificate?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Yes. Section 149 certificates were renamed to Section 10.7
                certificates when the Environmental Planning and Assessment Act
                was amended in 2018. They are the same document. Older
                references to &ldquo;s149&rdquo; mean the same thing.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Should I get a s10.7(2) or s10.7(5)?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Most conveyancers order the s10.7(2) as standard. The s10.7(5)
                costs $100 more and may contain additional council-specific
                information, but the content varies. For properties with
                potential environmental or flood issues, the s10.7(5) can
                provide useful additional detail &mdash; but check with the
                specific council what they typically include.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does the certificate show what I can build?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                No. The certificate shows the zoning, which determines
                broad land use permissibility. It does not show DCP controls,
                lot-specific constraints, or development feasibility. To
                understand what you can build, you need to cross-reference the
                LEP, DCP, and applicable SEPPs with the site dimensions and
                constraints.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can I check if my house is in a{' '}
                <Link
                  href="/blog/is-my-house-in-a-flood-zone-nsw"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  flood zone
                </Link>{' '}
                without a s10.7?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Yes. The NSW Planning Portal, the SES Flood Data Portal, and
                council websites provide flood information without ordering a
                certificate. PlotDetect&apos;s flood check also provides
                depth and frequency data &mdash; information the certificate
                does not include.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                How long is a s10.7 certificate valid?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                There is no formal expiry period. However, the information
                reflects planning instruments at the date of issue. LEP
                amendments, new SEPPs, or flood mapping updates can change what
                applies. In practice, most conveyancers order a fresh
                certificate for each transaction.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              See what the certificate doesn&apos;t show
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s Conveyancing Planning Disclosure report covers
              LEP, SEPP, and DCP constraints, environmental overlays,
              development potential, and hazard exposure &mdash; the information
              the s10.7 leaves out.
            </p>
            <TrackedLink
              href="/reports/conveyancing"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-500 transition-colors"
              page="section-10-7-certificate-gaps-nsw"
              cta="check_conveyancing"
            >
              Run a planning disclosure report
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
