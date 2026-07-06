import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Heritage Conservation Areas: Why You Can\'t Build a Granny Flat via CDC — PlotDetect',
  description:
    'In NSW Heritage Conservation Areas, the complying development (CDC) pathway is blocked for granny flats and secondary dwellings. You must lodge a DA instead. Here is what that means for your project.',
  keywords: [
    'heritage conservation area renovation NSW',
    'heritage overlay development rules',
    'granny flat heritage area NSW',
    'can I build in heritage conservation area',
    'HCA granny flat NSW',
    'secondary dwelling heritage conservation area',
    'heritage area DA requirements NSW',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — CDC blocked, DA required pathway diagram */
function PathwayDiagram() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Approval pathways: Heritage Conservation Area vs standard residential
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        {/* Left — Standard lot */}
        <div className="rounded-xl border-2 border-green-200 bg-white p-5">
          <p className="text-sm font-bold text-green-700 mb-4">
            Standard residential lot (no HCA)
          </p>
          <div className="space-y-3">
            {[
              { step: 'Meet Housing SEPP criteria', status: 'check' },
              { step: 'Lot 450m2+ without special overlays', status: 'check' },
              { step: 'Lodge CDC with private certifier', status: 'check' },
              { step: 'Approved in ~20 days', status: 'check' },
            ].map((item) => (
              <div key={item.step} className="flex items-center gap-3">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-100 flex items-center justify-center text-xs text-green-600">
                  &#10003;
                </span>
                <span className="text-sm text-slate-700">{item.step}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-lg bg-green-50 p-3">
            <p className="text-xs font-semibold text-green-700">
              CDC pathway available
            </p>
            <p className="text-xs text-green-600 mt-0.5">
              ~$5K&ndash;$10K total assessment costs
            </p>
          </div>
        </div>

        {/* Right — HCA lot */}
        <div className="rounded-xl border-2 border-red-200 bg-white p-5">
          <p className="text-sm font-bold text-red-700 mb-4">
            Lot in Heritage Conservation Area
          </p>
          <div className="space-y-3">
            {[
              {
                step: 'Housing SEPP criteria met',
                status: 'check',
              },
              {
                step: 'CDC pathway: BLOCKED by SEPP exclusion',
                status: 'cross',
              },
              {
                step: 'Must lodge DA with council',
                status: 'arrow',
              },
              {
                step: 'Heritage assessment + design review',
                status: 'arrow',
              },
              {
                step: '3\u20136+ months for determination',
                status: 'arrow',
              },
            ].map((item) => (
              <div key={item.step} className="flex items-center gap-3">
                <span
                  className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                    item.status === 'check'
                      ? 'bg-green-100 text-green-600'
                      : item.status === 'cross'
                        ? 'bg-red-100 text-red-600'
                        : 'bg-amber-100 text-amber-600'
                  }`}
                >
                  {item.status === 'check'
                    ? '\u2713'
                    : item.status === 'cross'
                      ? '\u2717'
                      : '\u2192'}
                </span>
                <span className="text-sm text-slate-700">
                  {item.step}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-lg bg-red-50 p-3">
            <p className="text-xs font-semibold text-red-700">
              DA pathway required
            </p>
            <p className="text-xs text-red-600 mt-0.5">
              ~$15K&ndash;$40K+ total costs (heritage consultant, architect,
              DA fees)
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Visual 2 — What HCA typically requires checklist */
function HcaRequirementsChecklist() {
  const requirements = [
    {
      category: 'Design and form',
      items: [
        'Sympathetic to the streetscape character of the conservation area',
        'Materials compatible with the heritage context (often brick, timber, or rendered masonry)',
        'Roof form consistent with surrounding buildings (pitched, not flat, in many HCAs)',
        'Scale and bulk subordinate to the principal dwelling',
      ],
    },
    {
      category: 'Siting and visibility',
      items: [
        'Typically required behind the front building alignment',
        'Not visible from the street (or minimal visibility with screening)',
        'Setbacks that preserve the spatial pattern of the conservation area',
        'No adverse impact on significant trees or landscape elements',
      ],
    },
    {
      category: 'Documentation',
      items: [
        'Heritage Impact Statement (prepared by a heritage consultant)',
        'Streetscape analysis and photomontage showing the proposal in context',
        'Statement of Heritage Significance addressing the conservation area',
        'Architectural drawings by a qualified designer',
      ],
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Typical council requirements for secondary dwellings in HCAs
      </p>
      <div className="space-y-6">
        {requirements.map((group) => (
          <div key={group.category}>
            <p className="text-sm font-bold text-slate-900 mb-2">
              {group.category}
            </p>
            <div className="space-y-2">
              {group.items.map((item) => (
                <div key={item} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-violet-100 flex items-center justify-center text-xs text-violet-600 mt-0.5">
                    &#9679;
                  </span>
                  <span className="text-sm text-slate-700">{item}</span>
                </div>
              ))}
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

export default function HeritageConservationAreaGrannyFlatPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`Heritage conservation areas: why you can't build a granny flat (and what to do)`}
        description="The SEPP CDC pathway is blocked in heritage conservation areas. What the DA process looks like, what councils require, and what is still possible."
        slug="heritage-conservation-area-granny-flat-nsw"
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
          Heritage Conservation Areas: why you can&apos;t build a granny flat
          via CDC (and what to do instead)
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          If your property is in a Heritage Conservation Area, the fast-track
          complying development certificate (CDC) pathway for granny flats is
          blocked. The Housing SEPP explicitly excludes HCAs from CDC
          eligibility. You must lodge a Development Application with council
          instead &mdash; a process that takes longer, costs more, and requires
          heritage-specific documentation.
        </p>
      </div>

      {/* Immediate value: pathway diagram */}
      <PathwayDiagram />

      {/* Body */}
      <div className="space-y-10">
        {/* ========== SECTION 1: What is an HCA ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What a Heritage Conservation Area actually means for your property
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A Heritage Conservation Area is different from an individual
            heritage listing. An individual heritage item is a specific building
            or structure with assessed significance. An HCA is an area where the
            collective character, streetscape, and pattern of development are
            considered significant &mdash; even if your individual building has
            no heritage value on its own.
          </p>
          <div className="grid sm:grid-cols-2 gap-4 mt-2">
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <p className="text-sm font-bold text-slate-900 mb-2">
                Individual heritage item
              </p>
              <ul className="space-y-1.5 text-sm text-slate-700">
                <li className="flex items-start gap-2">
                  <span className="text-slate-400 mt-0.5">&#9679;</span>
                  Specific building has assessed heritage significance
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-slate-400 mt-0.5">&#9679;</span>
                  Listed in Schedule 5 of the LEP
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-slate-400 mt-0.5">&#9679;</span>
                  Stricter controls on the building itself
                </li>
              </ul>
            </div>
            <div className="rounded-xl border border-violet-200 bg-violet-50/30 p-5">
              <p className="text-sm font-bold text-violet-800 mb-2">
                Heritage Conservation Area
              </p>
              <ul className="space-y-1.5 text-sm text-slate-700">
                <li className="flex items-start gap-2">
                  <span className="text-violet-400 mt-0.5">&#9679;</span>
                  Area-wide designation &mdash; your house may not be heritage
                  itself
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-violet-400 mt-0.5">&#9679;</span>
                  Mapped in the LEP heritage overlay
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-violet-400 mt-0.5">&#9679;</span>
                  Controls focus on streetscape and area character
                </li>
              </ul>
            </div>
          </div>
          <p className="text-slate-700 leading-relaxed">
            Many homeowners in HCAs are unaware of the designation until they
            try to build. Inner-city and inner-ring suburbs in Sydney, Newcastle,
            and Wollongong have extensive HCA coverage. Some LGAs have dozens of
            conservation areas mapped across their territory.
          </p>
        </section>

        {/* ========== SECTION 2: Why CDC is blocked ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why the CDC pathway is blocked in Heritage Conservation Areas
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The State Environmental Planning Policy (Exempt and Complying
            Development Codes) 2008 &mdash; commonly called the Codes SEPP
            &mdash; sets out when development can be approved as complying
            development via a private certifier, without going through council.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The Codes SEPP explicitly lists Heritage Conservation Areas as an
            exclusion. If your property falls within an HCA mapped in the LEP,
            complying development for new dwellings and secondary dwellings
            (granny flats) is not available. The rationale: CDC is a
            standardised approval pathway that cannot assess heritage impact on
            a case-by-case basis. Heritage assessment requires professional
            judgement about context, character, and visual impact that a
            checklist-based CDC process is not designed to provide.
          </p>
          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              The practical impact
            </p>
            <p className="text-sm text-slate-700 leading-relaxed">
              On a standard residential lot outside an HCA, a qualifying granny
              flat can be approved in roughly 20 days via CDC with a private
              certifier. In an HCA, the same granny flat requires a DA that
              typically takes 3&ndash;6 months (longer if council requests
              amendments), costs $15,000&ndash;$40,000+ in consultant and
              application fees, and may be refused on heritage character grounds
              even if it meets all numerical standards.
            </p>
          </div>
        </section>

        {/* ========== SECTION 3: What the DA process looks like ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What the DA process looks like for a granny flat in an HCA
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Building a secondary dwelling in a Heritage Conservation Area is
            not impossible. It requires more work, more money, and more time
            than the CDC pathway. Here is the typical sequence:
          </p>
          <div className="space-y-4 mt-2">
            {[
              {
                num: '1',
                title: 'Pre-DA consultation (optional but recommended)',
                desc: 'Meet with council\'s heritage planner to discuss your concept before investing in full documentation. Some councils offer free or low-cost pre-DA advice. This can save thousands by identifying deal-breakers early.',
              },
              {
                num: '2',
                title: 'Commission a Heritage Impact Statement',
                desc: 'A qualified heritage consultant assesses the significance of the conservation area, analyses the impact of your proposal on that significance, and recommends design responses. Cost: $3,000\u2013$8,000.',
              },
              {
                num: '3',
                title: 'Architectural design to heritage standards',
                desc: 'Your architect or designer must respond to the conservation area character \u2014 materials, form, scale, roof pitch, and visibility from the street. Generic granny flat designs that work elsewhere may be refused here.',
              },
              {
                num: '4',
                title: 'Lodge DA with council',
                desc: 'Submit the DA with Heritage Impact Statement, architectural drawings, streetscape analysis, BASIX certificate, and supporting documentation. DA fees vary by council and estimated cost of works.',
              },
              {
                num: '5',
                title: 'Assessment and notification',
                desc: 'Council assesses the DA against LEP provisions, DCP heritage controls, and the Heritage Impact Statement. Neighbours are typically notified and may make submissions. Council may request design amendments.',
              },
              {
                num: '6',
                title: 'Determination',
                desc: 'Council either approves (potentially with conditions), defers for amendments, or refuses. Approval conditions in HCAs often specify materials, colours, finishes, and landscaping in detail.',
              },
            ].map((step) => (
              <div
                key={step.num}
                className="rounded-xl border border-slate-200 bg-white p-5"
              >
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-7 h-7 rounded-full bg-violet-100 flex items-center justify-center text-xs font-bold text-violet-700">
                    {step.num}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {step.title}
                    </p>
                    <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                      {step.desc}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ========== SECTION 4: What councils look for ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What council heritage planners are looking for
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Heritage assessment in HCAs is not about replicating old buildings.
            It is about ensuring new development does not erode the qualities
            that make the area significant. The following requirements appear
            across most NSW council DCPs for Heritage Conservation Areas:
          </p>
          <HcaRequirementsChecklist />
          <p className="text-slate-700 leading-relaxed">
            The degree of strictness varies by council and by the specific
            conservation area. Some HCAs have detailed character statements and
            design guidelines. Others rely on broader heritage provisions in the
            DCP. Either way, the assessment involves professional judgement
            &mdash; not just numerical compliance.
          </p>
        </section>

        {/* ========== SECTION 5: What IS still possible ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What you can still do as exempt or complying development in an HCA
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Not everything is blocked in Heritage Conservation Areas. Some
            types of work can still proceed as exempt development (no approval
            at all) or complying development (CDC with certifier), even within
            an HCA:
          </p>
          <div className="rounded-2xl border border-green-200 bg-green-50/30 p-6">
            <p className="text-sm font-bold text-green-800 mb-3">
              Generally still available in HCAs (check specific SEPP exclusions)
            </p>
            <ul className="space-y-2 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#10003;</span>
                <span>
                  <span className="font-medium">Internal alterations</span>{' '}
                  &mdash; most internal work to non-heritage-listed buildings is
                  exempt development
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#10003;</span>
                <span>
                  <span className="font-medium">Minor external repairs</span>{' '}
                  &mdash; like-for-like replacement of materials, routine
                  maintenance
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#10003;</span>
                <span>
                  <span className="font-medium">Garden structures</span>{' '}
                  &mdash; small garden sheds, pergolas (subject to size limits
                  and location requirements)
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#10003;</span>
                <span>
                  <span className="font-medium">Solar panels</span> &mdash;
                  generally exempt if not visible from the street (check
                  council-specific rules)
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#10003;</span>
                <span>
                  <span className="font-medium">Fences</span> &mdash; rear and
                  side fences are often exempt, but front fences in HCAs may
                  need DA
                </span>
              </li>
            </ul>
          </div>
          <div className="rounded-2xl border border-red-200 bg-red-50/30 p-6 mt-4">
            <p className="text-sm font-bold text-red-800 mb-3">
              Typically blocked from CDC in HCAs
            </p>
            <ul className="space-y-2 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">&#10007;</span>
                <span>
                  New secondary dwellings / granny flats
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">&#10007;</span>
                <span>
                  New detached dwellings
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">&#10007;</span>
                <span>
                  Additions or alterations visible from the street that change
                  the building&apos;s external appearance
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">&#10007;</span>
                <span>
                  Demolition of buildings in the conservation area
                </span>
              </li>
            </ul>
          </div>
        </section>

        {/* ========== SECTION 6: Strategies ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Strategies to improve your chances of DA approval
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A granny flat DA in an HCA is not a guaranteed refusal. Councils
            approve secondary dwellings in conservation areas regularly &mdash;
            the ones that succeed share common characteristics:
          </p>
          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Design for invisibility from the street
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The most common reason for refusal in HCAs is adverse visual
                impact on the streetscape. Locating the secondary dwelling
                behind the principal building, keeping it single-storey, and
                using screening vegetation significantly reduces this risk.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Use materials that respond to the area character
              </h3>
              <p className="text-slate-700 leading-relaxed">
                This does not mean building a replica. Contemporary design in
                sympathetic materials is generally acceptable. What fails is
                generic off-the-shelf designs that ignore the context entirely
                &mdash; Colorbond walls in a Federation brick precinct, for
                example.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Invest in pre-DA advice
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A pre-DA meeting with council&apos;s heritage planner costs
                little but can save thousands. They will tell you what they are
                looking for in that specific conservation area and flag potential
                refusal grounds before you commission full documentation.
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
                How do I check if my property is in a Heritage Conservation
                Area?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Check the heritage map in your council&apos;s Local
                Environmental Plan. The NSW Planning Portal&apos;s spatial
                viewer also shows heritage overlays. PlotDetect&apos;s{' '}
                <Link
                  href="/check"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  planning check
                </Link>{' '}
                shows HCA status for any NSW address alongside other planning
                constraints.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can I build a granny flat if my property is heritage-listed
                (not just in an HCA)?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Individual heritage items have even stricter controls than
                HCAs. CDC is blocked, and the DA assessment will focus on the
                heritage significance of the specific building and its curtilage.
                A Heritage Impact Statement is mandatory, and the Heritage
                Council or council heritage advisor may be consulted. It is
                possible but requires careful design that respects the
                significance of the listed item.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                How much does a Heritage Impact Statement cost?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Typically $3,000&ndash;$8,000, depending on the complexity of
                the proposal and the heritage consultant. For straightforward
                rear additions or secondary dwellings, expect the lower end.
                For proposals that affect street-facing elements or are near
                individually listed items, expect the higher end.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can council refuse my granny flat even if it meets all the
                numerical standards?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Yes. In HCAs, the DA assessment includes subjective design
                quality and heritage character considerations. A proposal that
                meets all setback, height, and floor space numbers can still be
                refused if the council determines it has an adverse impact on
                the significance of the conservation area. This is the
                fundamental difference between the CDC pathway (purely
                numerical) and the DA pathway (includes merit assessment).
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check if your property is in a Heritage Conservation Area
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect shows heritage overlays, zoning, and DCP controls for
              any NSW address. Find out whether the CDC pathway is available
              for your property before engaging consultants.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/check"
                className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
                page="heritage-conservation-area-granny-flat-nsw"
                cta="check_address"
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
