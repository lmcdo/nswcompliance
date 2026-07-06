import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { ArrowRight } from 'lucide-react';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'QLD Seller Disclosure Regime: What NSW Can Learn (and What\'s Coming) — PlotDetect',
  description:
    'Queensland requires sellers to disclose known defects, flooding history, and contamination before sale. NSW relies on buyer beware. Here is how every state compares and what conveyancers should do now.',
  keywords: [
    'QLD seller disclosure property',
    'property disclosure laws Australia',
    'seller disclosure form Queensland',
    'NSW property disclosure requirements comparison',
    'Form 24a Queensland',
    'vendor disclosure Australia',
    'section 10.7 certificate limitations',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual components                                                  */
/* ------------------------------------------------------------------ */

/** Visual 1 — State-by-state disclosure comparison */
function StateComparisonTable() {
  const states = [
    {
      state: 'QLD',
      instrument: 'Form 24a + Property Sustainability Declaration',
      defects: true,
      flooding: true,
      contamination: true,
      encumbrances: true,
      bodyCorp: true,
      hazards: false,
      rating: 'Strong',
      ratingColor: 'text-teal-700 bg-teal-50',
    },
    {
      state: 'VIC',
      instrument: 'Section 32 Vendor Statement',
      defects: false,
      flooding: false,
      contamination: false,
      encumbrances: true,
      bodyCorp: true,
      hazards: false,
      rating: 'Moderate',
      ratingColor: 'text-amber-700 bg-amber-50',
    },
    {
      state: 'SA',
      instrument: 'Form 1 Vendor Statement',
      defects: false,
      flooding: true,
      contamination: true,
      encumbrances: true,
      bodyCorp: true,
      hazards: false,
      rating: 'Moderate',
      ratingColor: 'text-amber-700 bg-amber-50',
    },
    {
      state: 'NSW',
      instrument: 's10.7 Certificate + Contract for Sale',
      defects: false,
      flooding: false,
      contamination: false,
      encumbrances: true,
      bodyCorp: false,
      hazards: false,
      rating: 'Weak',
      ratingColor: 'text-red-700 bg-red-50',
    },
    {
      state: 'WA',
      instrument: 'Joint Form of General Conditions',
      defects: false,
      flooding: false,
      contamination: false,
      encumbrances: true,
      bodyCorp: false,
      hazards: false,
      rating: 'Weak',
      ratingColor: 'text-red-700 bg-red-50',
    },
  ];

  const Check = () => (
    <span className="text-teal-600 font-bold">&#10003;</span>
  );
  const Cross = () => (
    <span className="text-slate-300 font-bold">&mdash;</span>
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
        What sellers must disclose, by state
      </p>
      <p className="text-xs text-slate-400 mb-5">
        Mandatory vendor disclosure obligations at point of residential sale
      </p>
      <div className="overflow-x-auto -mx-2 px-2">
        <table className="w-full text-sm border-collapse min-w-[600px]">
          <thead>
            <tr className="border-b-2 border-slate-200">
              <th className="text-left py-3 pr-3 font-semibold text-slate-900">
                State
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Known defects
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Flooding
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Contamination
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Encumbrances
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Body corp
              </th>
              <th className="text-center py-3 pl-3 font-semibold text-slate-900">
                Strength
              </th>
            </tr>
          </thead>
          <tbody>
            {states.map((s) => (
              <tr key={s.state} className="border-b border-slate-100">
                <td className="py-3 pr-3">
                  <span className="font-semibold text-slate-900">
                    {s.state}
                  </span>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {s.instrument}
                  </p>
                </td>
                <td className="text-center py-3 px-2">
                  {s.defects ? <Check /> : <Cross />}
                </td>
                <td className="text-center py-3 px-2">
                  {s.flooding ? <Check /> : <Cross />}
                </td>
                <td className="text-center py-3 px-2">
                  {s.contamination ? <Check /> : <Cross />}
                </td>
                <td className="text-center py-3 px-2">
                  {s.encumbrances ? <Check /> : <Cross />}
                </td>
                <td className="text-center py-3 px-2">
                  {s.bodyCorp ? <Check /> : <Cross />}
                </td>
                <td className="text-center py-3 pl-3">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${s.ratingColor}`}
                  >
                    {s.rating}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400 mt-4">
        &ldquo;Flooding&rdquo; and &ldquo;Contamination&rdquo; refer to
        mandatory vendor disclosure of known history or risk, not planning
        certificate flags. NSW&apos;s s10.7 discloses planning controls, not
        property condition.
      </p>
    </div>
  );
}

/** Visual 2 — What's disclosed vs what's hidden in NSW */
function DisclosureGapDiagram() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        NSW property sale: what the buyer gets vs what stays hidden
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
          <p className="text-sm font-bold text-teal-700 mb-3">
            Disclosed to buyer
          </p>
          {[
            's10.7 planning certificate (zoning, LEP controls)',
            'Title search (easements, covenants, caveats)',
            'Strata report (if applicable, at buyer cost)',
            'Contract for sale (special conditions)',
          ].map((item) => (
            <div
              key={item}
              className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-teal-100 flex items-center justify-center text-xs text-teal-600">
                &#10003;
              </span>
              <span className="text-sm text-slate-700">{item}</span>
            </div>
          ))}
        </div>

        <div className="rounded-xl border-2 border-red-200 bg-white p-5">
          <p className="text-sm font-bold text-red-700 mb-3">
            Not required from vendor
          </p>
          {[
            'Known structural defects',
            'Flooding history at the property',
            'Contamination or asbestos presence',
            'Previous insurance claims',
            'Neighbourhood disputes or nuisances',
            'Bushfire or climate risk exposure',
            'Insurance affordability for the address',
            'DCP constraints affecting future development',
          ].map((item) => (
            <div
              key={item}
              className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-100 flex items-center justify-center text-xs text-red-600">
                &times;
              </span>
              <span className="text-sm text-slate-700">{item}</span>
            </div>
          ))}
          <p className="text-xs text-slate-400 mt-3 italic">
            In NSW, the buyer bears the cost of discovering all of the above.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Visual 3 — QLD Form 24a breakdown */
function Form24aBreakdown() {
  const sections = [
    {
      section: 'Part 1',
      title: 'Title and encumbrances',
      items: 'Registered interests, unregistered dealings, boundary disputes, access issues',
    },
    {
      section: 'Part 2',
      title: 'Environmental matters',
      items: 'Contaminated land notices, environmental management registers, notifiable activities',
    },
    {
      section: 'Part 3',
      title: 'Statutory notices and orders',
      items: 'Building orders, show cause notices, compliance notices, local government orders',
    },
    {
      section: 'Part 4',
      title: 'Neighbourhood and property matters',
      items: 'Known defects, flooding history, asbestos, termite damage, neighbourhood nuisances',
    },
    {
      section: 'Part 5',
      title: 'Body corporate (if applicable)',
      items: 'Contributions, special levies, disputes, building defects, insurance adequacy',
    },
    {
      section: 'Sustainability',
      title: 'Property Sustainability Declaration',
      items: 'Energy efficiency, solar, insulation, water tanks — separate form, mandatory since 2010',
    },
  ];

  return (
    <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
        What QLD Form 24a requires sellers to disclose
      </p>
      <p className="text-xs text-slate-400 mb-5">
        Under the Property Law Act 1974 (Qld) and Property Occupations
        Act 2014 (Qld)
      </p>
      <div className="space-y-3">
        {sections.map((s) => (
          <div
            key={s.section}
            className="rounded-xl bg-white border border-slate-200 p-4"
          >
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-xs font-bold text-blue-600 uppercase">
                {s.section}
              </span>
              <span className="text-sm font-semibold text-slate-900">
                {s.title}
              </span>
            </div>
            <p className="text-xs text-slate-600">{s.items}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4">
        False or misleading statements on Form 24a can give the buyer the
        right to terminate the contract. This creates a genuine incentive for
        vendor honesty that does not exist in NSW.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function QldSellerDisclosureComparisonPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`QLD seller disclosure regime: what NSW can learn (and what's coming)`}
        description="Queensland requires sellers to disclose known defects. NSW relies on buyer beware. A state-by-state comparison and what the Productivity Commission recommends."
        slug="qld-seller-disclosure-nsw-comparison"
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
          QLD seller disclosure regime: what NSW can learn (and what&apos;s
          coming)
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Queensland requires property sellers to disclose known defects,
          flooding history, contamination, and body corporate issues before
          sale. NSW requires almost none of this. The buyer bears the cost
          of discovering material risks after exchange. Here is how every
          state compares, why this matters for conveyancers, and what the
          Productivity Commission has recommended.
        </p>
      </div>

      {/* Immediate value: comparison table */}
      <StateComparisonTable />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#qld-model" className="hover:text-teal-600">
              What Queensland&apos;s Form 24a actually requires
            </a>
          </li>
          <li>
            <a href="#nsw-gap" className="hover:text-teal-600">
              What NSW does (and doesn&apos;t) require
            </a>
          </li>
          <li>
            <a href="#other-states" className="hover:text-teal-600">
              Victoria, South Australia, and Western Australia
            </a>
          </li>
          <li>
            <a href="#productivity-commission" className="hover:text-teal-600">
              The Productivity Commission&apos;s recommendation
            </a>
          </li>
          <li>
            <a href="#climate-disclosure" className="hover:text-teal-600">
              The case for mandatory hazard disclosure at sale
            </a>
          </li>
          <li>
            <a href="#conveyancers-now" className="hover:text-teal-600">
              What conveyancers should do now
            </a>
          </li>
        </ul>
      </nav>

      {/* Body */}
      <div className="space-y-10">
        {/* Section 1 */}
        <section id="qld-model" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What Queensland&apos;s Form 24a actually requires
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Under the Property Law Act 1974 (Qld), sellers of residential
            property must provide a completed Form 24a (Seller&apos;s
            Disclosure Statement) before the buyer signs the contract. The
            form is not optional. If the seller fails to provide it, or
            provides false or materially incomplete information, the buyer
            may terminate the contract and recover costs.
          </p>

          <Form24aBreakdown />

          <p className="text-slate-700 leading-relaxed">
            The critical difference from NSW is the &ldquo;known
            defects&rdquo; obligation. Queensland sellers must disclose
            structural problems, water ingress, termite damage, asbestos,
            and past flooding &mdash; anything they are or should reasonably
            be aware of. The standard is not perfect; sellers can and do
            claim ignorance. But the existence of a statutory obligation
            with termination rights creates accountability that NSW&apos;s
            buyer-beware model lacks entirely.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Since 2010, Queensland also requires a Property Sustainability
            Declaration &mdash; a separate form disclosing energy efficiency
            features, solar installations, insulation, and water tanks. This
            was novel when introduced and remains the only mandatory
            sustainability disclosure at point of sale in Australia.
          </p>
        </section>

        {/* Section 2 */}
        <section id="nsw-gap" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What NSW does (and doesn&apos;t) require
          </h2>
          <p className="text-slate-700 leading-relaxed">
            NSW property sales rely on three documents: the contract for
            sale, the title search, and the Section 10.7 planning
            certificate. None of these require the seller to disclose known
            property defects, flooding history, contamination, insurance
            claims, or climate risk exposure.
          </p>

          <DisclosureGapDiagram />

          <div className="rounded-2xl border border-slate-200 p-6 space-y-3">
            <h3 className="text-lg font-semibold text-slate-900">
              What the s10.7 certificate covers
            </h3>
            <p className="text-slate-700 leading-relaxed">
              The{' '}
              <Link
                href="/blog/section-10-7-flood-risk-nsw"
                className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
              >
                Section 10.7 planning certificate
              </Link>{' '}
              discloses planning controls that apply to the land &mdash;
              zoning, heritage listings, acid sulfate soils, and flood
              planning area status. It answers the question &ldquo;what are
              you allowed to build here?&rdquo; It does not answer &ldquo;what
              is wrong with what&apos;s already built?&rdquo; or &ldquo;what
              has happened here before?&rdquo;
            </p>
            <p className="text-slate-700 leading-relaxed">
              As we detailed in our analysis of{' '}
              <Link
                href="/blog/section-10-7-flood-risk-nsw"
                className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
              >
                s10.7 certificate gaps for flood risk
              </Link>
              , the certificate now shows less flood information than it did
              before 2021 due to legislative changes that removed flood
              planning maps from LEPs.
            </p>
          </div>
          <p className="text-slate-700 leading-relaxed">
            The legal doctrine underpinning NSW property sales is caveat
            emptor &mdash; buyer beware. The seller&apos;s primary obligation
            is not to make actively misleading statements. Silence about
            known problems is, in most cases, legally permissible. This
            places the entire burden of due diligence on the buyer, who
            typically has five business days (the cooling-off period) to
            discover issues that may take weeks to investigate.
          </p>
        </section>

        {/* Section 3 */}
        <section id="other-states" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Victoria, South Australia, and Western Australia
          </h2>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Victoria: Section 32 Vendor Statement
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Under Section 32 of the Sale of Land Act 1962 (Vic), vendors
                must provide a statement covering title details, easements,
                covenants, owner-builder warranties, and planning information.
                The statement is comprehensive for title and encumbrance
                matters but does not require disclosure of property condition,
                flooding history, or environmental contamination. Victoria
                falls between NSW and QLD &mdash; more structured than NSW
                but without the defect disclosure obligation.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                South Australia: Form 1 Vendor Statement
              </h3>
              <p className="text-slate-700 leading-relaxed">
                SA&apos;s Form 1 under the Land and Business (Sale and
                Conveyancing) Act 1994 requires disclosure of title details,
                encumbrances, and &mdash; notably &mdash; environmental
                matters including contamination and flooding designations.
                SA is the only state besides QLD that requires vendors to
                disclose environmental risk information. The form must be
                served on the buyer before the contract is formed.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Western Australia: minimal requirements
              </h3>
              <p className="text-slate-700 leading-relaxed">
                WA has no mandatory vendor disclosure statement equivalent to
                the other states. The Joint Form of General Conditions
                (used in most residential contracts) includes basic
                representations but no obligation to disclose defects,
                flooding, or environmental issues. Like NSW, WA operates
                largely on buyer beware.
              </p>
            </div>
          </div>
        </section>

        {/* Section 4 */}
        <section id="productivity-commission" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The Productivity Commission&apos;s recommendation
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Productivity Commission&apos;s 2024 inquiry into National
            Natural Disaster Arrangements recommended that state and
            territory governments &ldquo;require standardised, mandatory
            disclosure of natural hazard risks at the point of property
            sale.&rdquo; The recommendation specifically cited flood,
            bushfire, and coastal hazard exposure.
          </p>
          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              Key points from the Productivity Commission report
            </p>
            <ul className="space-y-2 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-amber-500 mt-0.5 flex-shrink-0">
                  &#9679;
                </span>
                Information asymmetry between sellers and buyers is a market
                failure that depresses investment in mitigation
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-500 mt-0.5 flex-shrink-0">
                  &#9679;
                </span>
                Buyers who discover hazard exposure post-purchase have fewer
                resources for mitigation than informed pre-purchase buyers
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-500 mt-0.5 flex-shrink-0">
                  &#9679;
                </span>
                Disclosure should be standardised nationally to avoid
                regulatory fragmentation across states
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-500 mt-0.5 flex-shrink-0">
                  &#9679;
                </span>
                The existing patchwork (QLD Form 24a, VIC s32, SA Form 1,
                NSW s10.7) creates inconsistent consumer protection
              </li>
            </ul>
          </div>
          <p className="text-slate-700 leading-relaxed">
            No state has yet implemented the recommendation. But the
            direction of travel is clear: the combination of the insurance
            affordability crisis, the APRA stress test findings, and
            increasing climate litigation makes expanded vendor disclosure
            a question of when, not whether.
          </p>
        </section>

        {/* Section 5 */}
        <section id="climate-disclosure" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The case for mandatory hazard disclosure at sale
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The argument for requiring vendors to disclose flood, bushfire,
            and climate risk at point of sale is straightforward: buyers
            cannot price risk they cannot see. When material hazard
            information is hidden &mdash; either by omission or by the
            structural limitations of instruments like the s10.7 &mdash;
            buyers overpay for high-risk properties and underinvest in
            mitigation.
          </p>
          <p className="text-slate-700 leading-relaxed">
            APRA&apos;s Insurance CVA found that 1 in 4 Australian
            households will face unaffordable or unavailable insurance by
            2050. A significant portion of those households purchased their
            properties without adequate information about climate exposure.
            For the detailed projection data, see our analysis of{' '}
            <Link
              href="/blog/uninsurable-households-australia-2050"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              the trajectory to 2.7 million uninsurable households
            </Link>
            .
          </p>
          <p className="text-slate-700 leading-relaxed">
            The counter-argument &mdash; that mandatory disclosure would
            depress property values in hazard-affected areas &mdash; is
            economically backwards. Prices in those areas are already
            mispriced upward because buyers lack information. A correction
            is not a loss; it is an alignment of price with reality. The
            loss occurs when an uninformed buyer pays too much and discovers
            the true cost of ownership after settlement.
          </p>
        </section>

        {/* Section 6 */}
        <section id="conveyancers-now" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What conveyancers should do now
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Mandatory vendor disclosure may be coming, but conveyancers
            acting for buyers do not need to wait. The information is
            available &mdash; it is just not yet required.
          </p>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. Go beyond the s10.7
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The planning certificate is a starting point, not the
                endpoint. Cross-reference with council flood studies, Bush
                Fire Prone Land mapping, and the SES Flood Data Portal. A{' '}
                <Link
                  href="/reports/conveyancing"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  Conveyancing Planning Disclosure report
                </Link>{' '}
                consolidates LEP, SEPP, and DCP constraints into a single
                document that supplements the standard certificate.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Recommend pre-purchase insurance quotes
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Advise buyers to obtain insurance quotes before exchange, not
                after. The premium reflects hazard data that is not available
                through any public channel. A quote that reveals $4,000+ in
                annual flood premium is material information for purchase
                decisions.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Include climate risk in due diligence advice
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Professional obligations are evolving. Failing to advise a
                client about material flood or bushfire exposure creates
                professional liability risk, particularly where the
                information was readily available. PlotDetect&apos;s{' '}
                <Link
                  href="/climate-risk"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  climate risk assessment
                </Link>{' '}
                checks five government-mapped hazard layers at the property
                level and takes under a minute to run.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                4. Document what you checked
              </h3>
              <p className="text-slate-700 leading-relaxed">
                In a future where mandatory disclosure becomes standard,
                conveyancers who can demonstrate they were already
                incorporating hazard checks into their pre-purchase advice
                will be ahead of the profession. Document the searches you
                ran, the data sources you checked, and the advice you gave.
                It protects you and your client.
              </p>
            </div>
          </div>

          <p className="text-slate-700 leading-relaxed">
            For more on how the s10.7 certificate specifically falls short
            on flood risk, see our detailed analysis:{' '}
            <Link
              href="/blog/section-10-7-flood-risk-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Why your Section 10.7 certificate might not show flood risk
            </Link>
            .
          </p>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Planning disclosure tools for conveyancers
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s Conveyancing Planning Disclosure report
              consolidates LEP, SEPP, DCP, and flood overlays into a single
              document &mdash; filling the gaps that the s10.7 certificate
              leaves. See our{' '}
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
              page="qld-seller-disclosure-nsw-comparison"
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
