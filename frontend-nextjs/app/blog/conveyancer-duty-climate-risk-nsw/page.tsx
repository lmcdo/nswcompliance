import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { ArrowRight } from 'lucide-react';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    "Conveyancers and climate risk: the duty of care in NSW property transactions — PlotDetect",
  description:
    "NSW is a buyer-beware state, but the duty of care sitting behind a property adviser is widening as flood and climate data becomes public. Here is what the standard searches leave out and what prudent practice looks like now.",
  keywords: [
    'conveyancer duty of care climate risk',
    'solicitor duty property disclosure NSW',
    'Shaddock duty of care conveyancing',
    'climate risk conveyancing NSW',
    'section 10.7 certificate limitations',
    'flood disclosure NSW property',
    'due diligence property hazard NSW',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual components                                                  */
/* ------------------------------------------------------------------ */

/** Visual 1 — what the standard searches surface vs what a buyer needs */
function SearchGapTable() {
  const rows = [
    {
      matter: 'Flood',
      standard: 'A yes/no flag on the s10.7 certificate',
      fuller:
        'The mapped extent, the return period, and a prompt to price insurance before exchange',
    },
    {
      matter: 'Bushfire',
      standard: 'Bushfire-prone land flag (a prescribed s10.7(2) matter)',
      fuller: 'The vegetation category and what a BAL assessment would involve',
    },
    {
      matter: 'Forward-looking climate',
      standard: 'Not shown at all — the certificate is a point-in-time snapshot',
      fuller:
        'Government climate projections (heat, rainfall) for the location, cited and dated',
    },
    {
      matter: 'Estuarine tidal inundation',
      standard: 'Not a prescribed certificate matter',
      fuller:
        'Whether the lot intersects the NSW Government 2025 mapped extent — a newly published dataset',
    },
    {
      matter: 'Contaminated land',
      standard: 'Only if the land is on a specific notified register',
      fuller: 'A prompt to make further enquiry where the history warrants it',
    },
  ];

  return (
    <div className="my-8 overflow-x-auto rounded-2xl border border-slate-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-50 text-left text-slate-600">
            <th className="px-4 py-3 font-semibold">Matter</th>
            <th className="px-4 py-3 font-semibold">
              What the standard s10.7 search surfaces
            </th>
            <th className="px-4 py-3 font-semibold">
              What a buyer actually needs to weigh the risk
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={r.matter} className="align-top">
              <td className="px-4 py-3 font-medium text-slate-900 whitespace-nowrap">
                {r.matter}
              </td>
              <td className="px-4 py-3 text-slate-600">{r.standard}</td>
              <td className="px-4 py-3 text-slate-700">{r.fuller}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-4 py-3 text-xs text-slate-400">
        The s10.7 planning certificate remains the authoritative statutory
        disclosure. The right-hand column is context a buyer weighs alongside
        it, not a replacement for it.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function ConveyancerDutyClimateRiskPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Conveyancers and climate risk: the duty of care in NSW property transactions"
        description="NSW is a buyer-beware state, but the duty of care behind a property adviser is widening as flood and climate data becomes public. What the standard searches leave out, and what prudent practice looks like now."
        slug="conveyancer-duty-climate-risk-nsw"
        date="2026-07-09"
      />

      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-700">
            Climate Risk
          </span>
          <span className="text-xs text-slate-400">July 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          Conveyancers and climate risk: the duty of care in NSW property
          transactions
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          NSW is a buyer-beware state, and the s10.7 certificate is the
          authoritative statutory disclosure. But the duty of care that sits
          behind anyone who provides property information is not static &mdash;
          and it is widening as flood, bushfire, and climate data moves into the
          public domain. This is a plain-language look at where the standard
          searches stop, what has changed around them, and what a careful
          practice looks like now &mdash; without overstating a legal position
          that is still settling.
        </p>
      </div>

      <SearchGapTable />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#duty" className="hover:text-teal-600">
              The duty of care behind a property certificate
            </a>
          </li>
          <li>
            <a href="#gap" className="hover:text-teal-600">
              Where the standard searches stop
            </a>
          </li>
          <li>
            <a href="#direction" className="hover:text-teal-600">
              The direction of travel: disclosure is widening
            </a>
          </li>
          <li>
            <a href="#practice" className="hover:text-teal-600">
              What careful practice looks like now
            </a>
          </li>
        </ul>
      </nav>

      <div className="prose prose-slate max-w-none">
        {/* Section 1 */}
        <section id="duty" className="scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mt-12 mb-4">
            The duty of care behind a property certificate
          </h2>
          <p className="text-slate-600 leading-relaxed mb-4">
            The foundational case is <em>Shaddock &amp; Associates v Parramatta
            City Council</em> (1981). A council issued a certificate that failed
            to mention a road-widening proposal affecting the land. The High
            Court held that a body which supplies information others are expected
            to rely on can owe a duty of care, and can be liable where a
            negligent omission causes loss. The principle is not limited to
            councils: it runs to anyone in the transaction whose information a
            client relies on.
          </p>
          <p className="text-slate-600 leading-relaxed mb-4">
            For a conveyancer or solicitor, the duty to the client already
            exists in contract and in tort. What is moving is its{' '}
            <em>scope</em> &mdash; the set of risks a reasonable practitioner is
            expected to have in view. As hazard data that was once specialist
            becomes public and searchable, the line between &ldquo;not our
            job&rdquo; and &ldquo;a foreseeable matter we passed over&rdquo;
            shifts with it. None of this makes a conveyancer a climate
            scientist. It does raise the question of whether a knowable, mapped
            hazard was surfaced, or quietly left for the buyer to discover after
            exchange.
          </p>
        </section>

        {/* Section 2 */}
        <section id="gap" className="scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mt-12 mb-4">
            Where the standard searches stop
          </h2>
          <p className="text-slate-600 leading-relaxed mb-4">
            The s10.7 planning certificate is a point-in-time yes/no instrument.
            It flags whether flood-related development controls or bushfire-prone
            land apply. It does not tell a buyer how deep a flood reaches, how
            often, what it costs to insure, or how the exposure changes over a
            30-year mortgage. It says nothing about forward-looking climate
            projections, and it does not cover estuarine tidal inundation, which
            the NSW Government only published as a state-wide mapped dataset in
            late 2025. The table above sets out the gap matter by matter.
          </p>
          <p className="text-slate-600 leading-relaxed mb-4">
            The gap is not a defect in the certificate &mdash; it was never
            designed to carry that detail. It is simply the space a buyer (and
            the practitioner advising them) now has to fill from other sources.
            See also{' '}
            <Link
              href="/blog/section-10-7-flood-risk-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              the s10.7 flood data gap
            </Link>
            .
          </p>
        </section>

        {/* Section 3 */}
        <section id="direction" className="scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mt-12 mb-4">
            The direction of travel: disclosure is widening
          </h2>
          <p className="text-slate-600 leading-relaxed mb-4">
            NSW has not legislated a vendor climate-disclosure duty, and this
            article does not suggest it has. But the surrounding movement is one
            way. Queensland introduced a mandatory seller disclosure regime.
            Victoria treats a history of flooding or bushfire as a material fact
            a vendor must disclose. At the corporate level, Australia&apos;s
            mandatory climate-disclosure standard now requires large entities to
            assess physical climate risk to their assets &mdash; a signal of
            where public expectation is heading, even though it does not bind a
            residential transaction.
          </p>
          <p className="text-slate-600 leading-relaxed mb-4">
            The practical read for a NSW practitioner is not &ldquo;a new rule
            applies tomorrow.&rdquo; It is that buyer expectation and the
            standard of a careful search are drifting toward fuller hazard
            transparency, and the data to meet that expectation is increasingly
            free and per-address. See{' '}
            <Link
              href="/blog/qld-seller-disclosure-nsw-comparison"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              how the states compare on seller disclosure
            </Link>
            .
          </p>
        </section>

        {/* Section 4 */}
        <section id="practice" className="scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mt-12 mb-4">
            What careful practice looks like now
          </h2>
          <p className="text-slate-600 leading-relaxed mb-4">
            None of the following is legal advice, and none of it turns a
            conveyancer into a hazard consultant. It is simply what surfacing a
            foreseeable, knowable risk tends to involve:
          </p>
          <ul className="list-disc pl-6 space-y-2 text-slate-600 mb-4">
            <li>
              Surface the mapped hazards that public data already shows &mdash;
              flood and bushfire &mdash; rather than leaving them at a bare
              yes/no.
            </li>
            <li>
              Where government climate projection data exists for the location,
              note it as cited, dated context &mdash; not as a score or a
              verdict, which can mislead.
            </li>
            <li>
              Prompt the insurance question before exchange, since hazard
              exposure and premium cost are what actually move a buyer&apos;s
              decision.
            </li>
            <li>
              Record that these matters were put in front of the client. A short
              note that a hazard was raised is the difference between a matter
              disclosed and a matter passed over.
            </li>
          </ul>
          <p className="text-slate-600 leading-relaxed mb-4">
            A single consolidated disclosure that gathers the mapped hazards and
            the cited climate context into one document is one way to do this
            consistently across a matter list &mdash; so completeness does not
            depend on remembering to run a separate search each time.
          </p>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              One document that surfaces the hazard picture
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s Conveyancing Planning Disclosure report
              consolidates LEP, SEPP, and DCP controls with flood and bushfire
              mapping and cited government climate projections into a single
              per-address document &mdash; the context that sits alongside the
              s10.7 certificate. See our{' '}
              <Link
                href="/for/conveyancers"
                className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
              >
                tools for conveyancers
              </Link>{' '}
              page for the full capability.
            </p>
            <TrackedLink
              href="/reports/conveyancing"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-500 transition-colors"
              page="conveyancer-duty-climate-risk-nsw"
              cta="check_conveyancing"
            >
              View Conveyancing Report
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
