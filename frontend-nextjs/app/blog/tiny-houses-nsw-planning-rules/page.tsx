import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Tiny Houses in NSW: What the Planning System Actually Says — PlotDetect',
  description:
    'NSW has no statutory definition of "tiny house." Whether yours needs council approval depends on what it physically is — caravan, manufactured home, or dwelling. Here is how the classification works and what approval you need.',
  keywords: [
    'tiny house NSW planning rules',
    'can I put a tiny house on my property NSW',
    'tiny home council approval NSW',
    'moveable dwelling NSW',
    'tiny house on wheels legal NSW',
    'tiny home DA approval NSW',
    'manufactured home NSW regulations',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Legal classification spectrum */
function ClassificationSpectrum() {
  const categories = [
    {
      label: 'Registered caravan / THOW',
      examples: 'Trailer-registered, towable, self-contained, under 2.5m wide',
      approval: 'No DA required (Reg 77 exemption)',
      risk: 'Low',
      color: 'border-green-300 bg-green-50/50',
      dotColor: 'bg-green-500',
      caseRef: 'Russell v Camden [2018]',
    },
    {
      label: 'Mid-range: semi-permanent tiny home',
      examples:
        'On stumps, partial utility connections, skid-mounted, no registration',
      approval: 'Grey zone — fact-dependent',
      risk: 'Medium',
      color: 'border-amber-300 bg-amber-50/50',
      dotColor: 'bg-amber-500',
      caseRef: 'No definitive case law',
    },
    {
      label: 'Manufactured home on individual lot',
      examples:
        'Prefabricated off-site, transported in sections, permanently installed',
      approval: 'DA + s68 LG Act + building certification',
      risk: 'High complexity',
      color: 'border-orange-300 bg-orange-50/50',
      dotColor: 'bg-orange-500',
      caseRef: 'LG Act 1993 + Housing SEPP',
    },
    {
      label: 'Permanent modular / secondary dwelling',
      examples:
        'Fixed to foundations, full utility connections, verandah/deck attached',
      approval: 'Full DA required (or CDC if qualifying)',
      risk: 'High',
      color: 'border-red-300 bg-red-50/50',
      dotColor: 'bg-red-500',
      caseRef: 'Ogilvie v Rovest [2023]',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
        Legal classification spectrum
      </p>
      <p className="text-sm text-slate-600 mb-5">
        The same physical structure can fall anywhere on this spectrum depending
        on its characteristics. NSW courts use a &ldquo;substance over
        characterisation&rdquo; test.
      </p>
      <div className="space-y-4">
        {categories.map((cat) => (
          <div
            key={cat.label}
            className={`rounded-xl border-2 ${cat.color} p-4 sm:p-5`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`flex-shrink-0 w-3 h-3 rounded-full ${cat.dotColor} mt-1.5`}
              />
              <div className="flex-1">
                <p className="text-sm font-bold text-slate-900">{cat.label}</p>
                <p className="text-sm text-slate-600 mt-1">{cat.examples}</p>
                <div className="flex flex-wrap gap-x-6 gap-y-1 mt-2">
                  <p className="text-xs text-slate-500">
                    <span className="font-semibold">Approval:</span>{' '}
                    {cat.approval}
                  </p>
                  <p className="text-xs text-slate-400 italic">
                    {cat.caseRef}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Visual 2 — Decision tree: what approval pathway */
function ApprovalDecisionTree() {
  const steps = [
    {
      question: 'Is it trailer-registered and genuinely towable?',
      yes: 'Likely a caravan. Reg 77 exemption may apply — no DA needed if occupied by household members on owner-occupied land.',
      no: 'Continue below.',
      yesColor: 'text-green-700 bg-green-50',
      noColor: 'text-slate-600 bg-slate-50',
    },
    {
      question: 'Is it permanently fixed to the ground with full utility connections?',
      yes: 'Likely a building or secondary dwelling. Needs DA (or CDC if it meets Housing SEPP criteria on a 450m2+ lot without special overlays).',
      no: 'Continue below.',
      yesColor: 'text-red-700 bg-red-50',
      noColor: 'text-slate-600 bg-slate-50',
    },
    {
      question: 'Was it constructed mostly off-site and transported in sections?',
      yes: 'Likely a manufactured home. On individual lots: needs DA + s68 LG Act approval + building certification (triple consent). On manufactured home estates: streamlined consent under Housing SEPP Part 8.',
      no: 'Continue below.',
      yesColor: 'text-orange-700 bg-orange-50',
      noColor: 'text-slate-600 bg-slate-50',
    },
    {
      question: 'Does it sit in the grey zone — skid-mounted, partial connections, no registration?',
      yes: 'Fact-dependent. Council will apply the Ogilvie four-factor test: site attachments, portability, dimensions vs caravan limits, stated intent. Seek professional advice before installing.',
      no: 'Your structure may not fit NSW planning categories. Contact council before proceeding.',
      yesColor: 'text-amber-700 bg-amber-50',
      noColor: 'text-slate-600 bg-slate-50',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Decision tree: what approval does your tiny home need?
      </p>
      <div className="space-y-5">
        {steps.map((step, i) => (
          <div key={step.question} className="relative">
            <div className="flex items-start gap-3 mb-3">
              <span className="flex-shrink-0 w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-700">
                {i + 1}
              </span>
              <p className="text-sm font-semibold text-slate-900 pt-0.5">
                {step.question}
              </p>
            </div>
            <div className="grid sm:grid-cols-2 gap-3 ml-10">
              <div className={`rounded-lg p-3 ${step.yesColor}`}>
                <p className="text-xs font-bold uppercase tracking-wider mb-1">
                  Yes
                </p>
                <p className="text-sm leading-relaxed">{step.yes}</p>
              </div>
              <div className={`rounded-lg p-3 ${step.noColor}`}>
                <p className="text-xs font-bold uppercase tracking-wider mb-1">
                  No
                </p>
                <p className="text-sm leading-relaxed">{step.no}</p>
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

export default function TinyHousesNswPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Tiny houses in NSW: what the planning system actually says"
        description="NSW has no statutory definition of a tiny house. Where yours falls — caravan, manufactured home, or dwelling — determines your entire approval pathway."
        slug="tiny-houses-nsw-planning-rules"
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
          Tiny houses in NSW: what the planning system actually says
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          NSW has no statutory definition of &ldquo;tiny house.&rdquo; Whether
          you need council approval &mdash; and what kind &mdash; depends
          entirely on what your structure physically is and how it connects to
          the land. The same object can be a caravan, a manufactured home, or a
          building depending on four factors a court will assess.
        </p>
      </div>

      {/* Immediate value: classification spectrum */}
      <ClassificationSpectrum />

      {/* Body */}
      <div className="space-y-10">
        {/* ========== SECTION 1: The core problem ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why &ldquo;tiny house&rdquo; means nothing in NSW planning law
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The NSW planning system classifies structures by their physical
            characteristics and relationship to the land &mdash; not by what the
            owner calls them. There is no &ldquo;tiny house&rdquo; category in
            the Environmental Planning and Assessment Act 1979, the Local
            Government Act 1993, or the Housing SEPP 2021. Your tiny home will
            be treated as one of the following:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">A caravan</span> &mdash; max 2.5m
              wide, 4.3m high, 12.5m long, 4.5 tonnes. Governed by the LG Act,
              not the EPA Act. Exempt from DA under Regulation 77 in specific
              circumstances.
            </li>
            <li>
              <span className="font-medium">A manufactured home</span> &mdash;
              self-contained dwelling constructed mostly off-site, not
              registrable as a vehicle. Governed by LG Act 1993 and Housing SEPP
              Parts 8-9.
            </li>
            <li>
              <span className="font-medium">A secondary dwelling</span> &mdash;
              max 60m2 internal floor area, ancillary to a principal dwelling.
              Governed by Housing SEPP 2021. CDC pathway available on qualifying
              lots.
            </li>
            <li>
              <span className="font-medium">A building</span> &mdash; anything
              permanently attached to land that doesn&apos;t fit the above
              categories. Full DA required.
            </li>
          </ul>
        </section>

        {/* ========== SECTION 2: Decision tree ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What approval pathway does your tiny home need?
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Work through this from top to bottom. The first &ldquo;yes&rdquo;
            that matches your situation is your most likely pathway &mdash; but
            council interpretation varies, and the grey zone cases are genuinely
            uncertain.
          </p>
          <ApprovalDecisionTree />
        </section>

        {/* ========== SECTION 3: Case law ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The two court cases that define the boundaries
          </h2>

          <div className="space-y-4">
            <div className="rounded-2xl border border-green-200 bg-green-50/30 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Russell v Camden Council [2018] NSWLEC 1159
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A family installed a renovated caravan in their backyard for
                their daughter. Connected to water, electricity, and sewer.
                Council issued a removal order, calling it an unlicensed
                structure requiring DA.
              </p>
              <p className="text-slate-700 leading-relaxed mt-2">
                <span className="font-medium">
                  The Land and Environment Court ruled for the homeowner.
                </span>{' '}
                The court held that trailer registration and physical capability
                of being towed were determinative &mdash; not appearance,
                stationary placement, or utility connections. A registered
                caravan occupied by household members on owner-occupied land is
                exempt under Regulation 77.
              </p>
            </div>

            <div className="rounded-2xl border border-red-200 bg-red-50/30 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Ogilvie v Rovest Holdings [2023] NSWLEC 17
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A developer installed prefabricated modular units (14.4m x 3.4m)
                on piers, connected to utilities, with attached verandahs.
              </p>
              <p className="text-slate-700 leading-relaxed mt-2">
                <span className="font-medium">
                  The court ruled against the developer.
                </span>{' '}
                Applying &ldquo;substance over characterisation,&rdquo; the
                court established a four-factor test: (1) site attachments,
                (2) portability, (3) dimensions compared to caravan limits,
                (4) stated intent for relocation. Permanent installation plus
                service connections plus no genuine portability equals a
                building, regardless of labelling.
              </p>
            </div>
          </div>

          <p className="text-slate-700 leading-relaxed">
            Most tiny homes sit somewhere between these two poles. The closer
            your structure is to the Russell end (registered, towable, compact),
            the stronger your position. The closer to the Ogilvie end
            (permanent, large, connected), the more likely you need DA.
          </p>
        </section>

        {/* ========== SECTION 4: Reg 77 exemptions ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            When no council approval is needed: Regulation 77
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Local Government (General) Regulation 2021, Regulation 77,
            exempts certain moveable dwelling placements from council approval:
          </p>
          <div className="rounded-2xl border border-slate-200 p-6">
            <ul className="space-y-3 text-slate-700 leading-relaxed">
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-100 flex items-center justify-center text-xs text-green-600 mt-0.5">
                  1
                </span>
                <span>
                  <span className="font-medium">
                    One caravan on owner-occupied land
                  </span>{' '}
                  for household members &mdash; indefinite duration, no approval
                  needed
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-100 flex items-center justify-center text-xs text-green-600 mt-0.5">
                  2
                </span>
                <span>
                  <span className="font-medium">Up to 2 caravans</span> on any
                  land if occupied no more than 2 consecutive days and 60
                  days/year total
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-100 flex items-center justify-center text-xs text-green-600 mt-0.5">
                  3
                </span>
                <span>
                  <span className="font-medium">Farm stay:</span> up to 6
                  caravans on rural properties over 15 hectares
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-100 flex items-center justify-center text-xs text-green-600 mt-0.5">
                  4
                </span>
                <span>
                  <span className="font-medium">Disaster displacement:</span>{' '}
                  temporary housing for approximately 2 years
                </span>
              </li>
            </ul>
          </div>
          <p className="text-slate-700 leading-relaxed">
            The critical requirement for exemption 1: the caravan must meet the
            dimensional limits (2.5m wide, 4.3m high, 12.5m long, 4.5 tonnes)
            and be genuinely capable of road towing. Removing axles, building
            over the hitch, or connecting permanently to services weakens the
            exemption.
          </p>
        </section>

        {/* ========== SECTION 5: Triple consent problem ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The triple consent problem for manufactured homes
          </h2>
          <p className="text-slate-700 leading-relaxed">
            If your tiny home is classified as a manufactured home on an
            individual lot (not a manufactured home estate), you face three
            separate approval processes:
          </p>
          <div className="grid sm:grid-cols-3 gap-4 mt-2">
            {[
              {
                num: '1',
                title: 'Development Application',
                body: 'Under the EPA Act for the use of land',
              },
              {
                num: '2',
                title: 'S68 Approval',
                body: 'Under the LG Act for installation of the structure',
              },
              {
                num: '3',
                title: 'Building Certification',
                body: 'Construction/Occupation Certificate for the structure itself',
              },
            ].map((item) => (
              <div
                key={item.num}
                className="rounded-xl border border-slate-200 bg-white p-4"
              >
                <span className="text-xs font-bold text-slate-400">
                  Step {item.num}
                </span>
                <p className="text-sm font-semibold text-slate-900 mt-1">
                  {item.title}
                </p>
                <p className="text-sm text-slate-600 mt-1">{item.body}</p>
              </div>
            ))}
          </div>
          <p className="text-slate-700 leading-relaxed">
            Each step has separate fees, separate consultants, and separate
            timelines. Combined costs for engineering, stormwater, geotechnical,
            and bushfire assessments can reach $5,000&ndash;$20,000 before
            construction begins. On-site sewage management alone (where no mains
            sewer is available) adds $5,000&ndash;$15,000.
          </p>
        </section>

        {/* ========== SECTION 6: Council differences ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How different councils interpret the rules
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Because the legislation doesn&apos;t define &ldquo;tiny house,&rdquo;
            council interpretation varies dramatically. Metro and suburban
            councils tend to interpret more restrictively. Regional councils are
            more varied &mdash; some block, some actively innovate.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse mt-2">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                    Council
                  </th>
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                    Approach
                  </th>
                  <th className="text-left py-3 font-semibold text-slate-900">
                    Detail
                  </th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Shellharbour</td>
                  <td className="py-3 pr-4">Innovating</td>
                  <td className="py-3">
                    Two-year pilot to amend LEP to permit mobile tiny homes on
                    residential land without DA
                  </td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Lismore</td>
                  <td className="py-3 pr-4">Incentivising</td>
                  <td className="py-3">
                    $15K grants for small housing including tiny homes
                    (post-flood recovery)
                  </td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Byron Shire</td>
                  <td className="py-3 pr-4">Permissive</td>
                  <td className="py-3">
                    Secondary dwellings in R2 without strict time limits for
                    household use
                  </td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Eurobodalla</td>
                  <td className="py-3 pr-4">Restrictive</td>
                  <td className="py-3">
                    THOWs only as secondary to existing dwelling, never as
                    primary residence
                  </td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium">Camden</td>
                  <td className="py-3 pr-4">Enforcement-first</td>
                  <td className="py-3">
                    Issued removal order for backyard caravan (lost in court
                    &mdash; Russell case)
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* ========== SECTION 7: DCP blockers ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            DCP controls that effectively block tiny homes
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Even where the LEP and Housing SEPP technically permit a secondary
            dwelling, council Development Control Plans can impose controls that
            make tiny homes impractical. The Housing SEPP prevents councils from
            imposing stricter <em>numerical</em> standards than the state
            baseline for secondary dwellings &mdash; but councils exercise
            discretion through design quality and neighbourhood character
            assessment in the DA process.
          </p>
          <div className="rounded-2xl border border-slate-200 p-6">
            <ul className="space-y-2 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-slate-400 mt-0.5">&#9679;</span>
                <span>
                  <span className="font-medium">Site coverage maximums</span>{' '}
                  &mdash; 50% combined for all structures leaves little room on
                  small lots
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-slate-400 mt-0.5">&#9679;</span>
                <span>
                  <span className="font-medium">Single-level requirements</span>{' '}
                  &mdash; eliminates loft-style designs
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-slate-400 mt-0.5">&#9679;</span>
                <span>
                  <span className="font-medium">
                    &ldquo;Subservient&rdquo; design requirements
                  </span>{' '}
                  &mdash; subjective assessment that secondary dwelling must be
                  visually subordinate
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-slate-400 mt-0.5">&#9679;</span>
                <span>
                  <span className="font-medium">Placement restrictions</span>{' '}
                  &mdash; must be behind front building alignment, rear yard only
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-slate-400 mt-0.5">&#9679;</span>
                <span>
                  <span className="font-medium">Heritage / character overlays</span>{' '}
                  &mdash; wide discretion to refuse non-traditional designs in
                  Heritage Conservation Areas
                </span>
              </li>
            </ul>
          </div>
          <p className="text-slate-700 leading-relaxed">
            You can check which overlays and DCP controls apply to a specific
            address using PlotDetect&apos;s{' '}
            <Link
              href="/check"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              free planning check
            </Link>
            .
          </p>
        </section>

        {/* ========== SECTION 8: Building Bill 2026 ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What changes under the Building Bill 2026
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Building (Approvals and Practitioners) Bill 2026 is the most
            significant legislative change affecting tiny home classification
            since the LG Act 1993. NSW is the first Australian jurisdiction to
            formally define &ldquo;prefabricated buildings&rdquo; in legislation.
            Implementation begins 2027.
          </p>
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-6 space-y-3">
            <p className="text-sm font-semibold text-slate-900">
              Key changes for tiny home owners:
            </p>
            <ul className="space-y-2 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">&#9679;</span>
                Modular/prefab construction formally recognised &mdash; ends the
                &ldquo;is it a caravan or a building?&rdquo; ambiguity for
                qualifying structures
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">&#9679;</span>
                Triple consent partially resolved &mdash; Building Approvals
                replace Construction Certificates, consolidating part of the
                pathway
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">&#9679;</span>
                Pattern Book pre-approved designs eligible for 10-day CDC
                &mdash; if secondary dwelling designs are included, this
                dramatically simplifies approval
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-500 mt-0.5">&#9679;</span>
                Full BCA/NCC compliance now required for modular &mdash;
                eliminates the regulatory arbitrage some tiny home owners relied
                on
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-500 mt-0.5">&#9679;</span>
                Broader &ldquo;building work&rdquo; definition &mdash; site
                preparation on undeveloped land now triggers the approval system
                sooner
              </li>
            </ul>
          </div>
          <p className="text-slate-700 leading-relaxed">
            Registered tiny houses on wheels (THOWs) remain governed by LG Act
            caravan provisions and Reg 77 exemptions. The Bill does not touch
            this category. For more on the Building Bill, see our detailed
            analysis of{' '}
            <Link
              href="/blog/modular-prefab-homes-nsw-building-bill-2026"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              how the 2026 Building Bill changes modular and prefab housing
            </Link>
            .
          </p>
        </section>

        {/* ========== FAQ ========== */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Frequently asked questions
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can I put a tiny house on wheels in my backyard in NSW?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                If it meets caravan dimensions (under 2.5m wide, 4.3m high,
                12.5m long, 4.5 tonnes), is trailer-registered, genuinely
                towable, and occupied by household members on owner-occupied
                land, Regulation 77 exempts it from council approval. This was
                confirmed in Russell v Camden [2018]. Connecting to utilities
                does not automatically disqualify you, but removing wheels or
                making it immovable weakens the exemption.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Do I need DA for a tiny house in NSW?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                It depends on classification. Registered caravans under Reg 77
                do not need DA. Secondary dwellings under 60m2 on lots over
                450m2 without special overlays can use the CDC pathway (no DA).
                Manufactured homes on individual lots need DA plus s68 approval.
                Anything permanently installed that doesn&apos;t fit these
                categories needs full DA.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                What happens if a neighbour complains about my tiny home?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Even where Regulation 77 applies, a complaint can trigger a
                council investigation, an order to remove, and potentially a Land
                and Environment Court appeal. The Russell case took this exact
                path &mdash; the homeowner won, but only after legal
                proceedings. Having registration documents and maintaining
                genuine towability strengthens your position.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check what planning controls apply to your property
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              Before installing a tiny home, check the zoning, overlays, and DCP
              controls for your address. PlotDetect shows LEP permissibility,
              heritage and bushfire overlays, and setback requirements &mdash;
              the factors that determine which approval pathway applies to your
              lot.
            </p>
            <TrackedLink
              href="/check"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="tiny-houses-nsw-planning-rules"
              cta="check_address"
            >
              Check your address
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
