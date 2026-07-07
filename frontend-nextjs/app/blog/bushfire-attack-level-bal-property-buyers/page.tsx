import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Understanding Bushfire Attack Levels (BAL) for Property Buyers — PlotDetect',
  description:
    'What BAL ratings mean for building costs, insurance premiums, and property value in NSW. How to check if a property is on Bush Fire Prone Land before you buy.',
  keywords: [
    'bushfire attack level check',
    'BAL assessment cost NSW',
    'bushfire prone land property NSW',
    'BAL rating meaning',
    'AS 3959 bushfire assessment',
    'bushfire prone land map NSW',
    'BAL-FZ building cost',
    'bushfire insurance premium',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual: BAL rating scale with cost/insurance impact                */
/* ------------------------------------------------------------------ */

function BALRatingScale() {
  const levels = [
    {
      bal: 'BAL-LOW',
      heat: 'Negligible',
      buildCost: '$0 extra',
      insurance: 'Standard premiums',
      color: 'bg-emerald-500',
      barWidth: 'w-1/12',
      desc: 'No special construction requirements under AS 3959.',
    },
    {
      bal: 'BAL-12.5',
      heat: '12.5 kW/m\u00B2',
      buildCost: '$5K\u201315K extra',
      insurance: 'Minor loading',
      color: 'bg-lime-500',
      barWidth: 'w-3/12',
      desc: 'Ember protection required. Non-combustible gutters, ember guards on vents.',
    },
    {
      bal: 'BAL-19',
      heat: '19 kW/m\u00B2',
      buildCost: '$15K\u201340K extra',
      insurance: '+20\u201350% loading',
      color: 'bg-yellow-500',
      barWidth: 'w-5/12',
      desc: 'Higher-rated windows, non-combustible external walls, restricted timber use.',
    },
    {
      bal: 'BAL-29',
      heat: '29 kW/m\u00B2',
      buildCost: '$40K\u201380K extra',
      insurance: '+50\u2013100% loading',
      color: 'bg-orange-500',
      barWidth: 'w-7/12',
      desc: 'Full ember/radiant heat protection. BAL-rated windows, restricted decking materials.',
    },
    {
      bal: 'BAL-40',
      heat: '40 kW/m\u00B2',
      buildCost: '$80K\u2013150K extra',
      insurance: '+100\u2013200% loading',
      color: 'bg-red-500',
      barWidth: 'w-9/12',
      desc: 'Substantial construction upgrades. Non-combustible everything. Metal shutters.',
    },
    {
      bal: 'BAL-FZ',
      heat: 'Flame Zone (direct flame contact)',
      buildCost: '$150K\u2013250K+ extra',
      insurance: 'Often unavailable',
      color: 'bg-red-800',
      barWidth: 'w-full',
      desc: 'Most restrictive. Full non-combustible construction. Some insurers will not cover.',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        BAL rating scale &mdash; what each level means for your build and
        insurance
      </p>
      <div className="space-y-4">
        {levels.map((l) => (
          <div
            key={l.bal}
            className="rounded-xl bg-white border border-slate-200 p-4"
          >
            <div className="flex items-center gap-3 mb-2">
              <span
                className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold text-white ${l.color}`}
              >
                {l.bal}
              </span>
              <span className="text-xs text-slate-500">{l.heat}</span>
            </div>
            <div className="mb-2">
              <div className="w-full bg-slate-100 rounded-full h-1.5">
                <div
                  className={`${l.color} h-1.5 rounded-full ${l.barWidth}`}
                />
              </div>
            </div>
            <p className="text-sm text-slate-700 mb-1.5">{l.desc}</p>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
              <span>
                Build cost impact:{' '}
                <span className="font-medium text-slate-700">
                  {l.buildCost}
                </span>
              </span>
              <span>
                Insurance:{' '}
                <span className="font-medium text-slate-700">
                  {l.insurance}
                </span>
              </span>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4 italic">
        Cost estimates are indicative ranges for a standard residential dwelling
        in NSW. Actual costs depend on site conditions, building design, and
        materials. Insurance loadings vary by insurer and location.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Visual: Decision diagram — "Do I need a BAL assessment?"           */
/* ------------------------------------------------------------------ */

function BALDecisionDiagram() {
  const steps = [
    {
      question: 'Is the property on the RFS Bush Fire Prone Land map?',
      yes: 'Continue to next step',
      no: 'No BAL assessment required. Standard construction.',
      noColor: 'text-emerald-600',
    },
    {
      question: 'Are you planning to build, renovate, or subdivide?',
      yes: 'Continue to next step',
      no: 'No BAL assessment required for purchase only. But check insurance costs before exchange.',
      noColor: 'text-amber-600',
    },
    {
      question:
        'Is the development within 100m of classified vegetation or within the mapped BFPL boundary?',
      yes: 'A formal BAL assessment under AS 3959 will be required before construction.',
      no: 'May still require a BAL assessment depending on council and certifier interpretation.',
      noColor: 'text-amber-600',
      yesColor: 'text-red-600',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Do you need a BAL assessment?
      </p>
      <div className="space-y-4">
        {steps.map((s, i) => (
          <div key={i} className="rounded-xl bg-white border border-slate-200 p-5">
            <p className="text-sm font-semibold text-slate-900 mb-3">
              Step {i + 1}: {s.question}
            </p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center text-xs font-bold text-emerald-700">
                  Y
                </span>
                <p
                  className={`text-sm ${s.yesColor ?? 'text-slate-600'}`}
                >
                  {s.yes}
                </p>
              </div>
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-100 flex items-center justify-center text-xs font-bold text-red-700">
                  N
                </span>
                <p className={`text-sm ${s.noColor}`}>{s.no}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4">
        A formal BAL assessment costs $500&ndash;$2,000 in NSW depending on site
        complexity. It must be conducted by an accredited assessor under AS 3959.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function BushfireBALPropertyBuyersPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Understanding Bushfire Attack Levels (BAL) for property buyers"
        description={`What BAL ratings mean for building costs and insurance, how they're determined, and how to check before you buy.`}
        slug="bushfire-attack-level-bal-property-buyers"
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
          Understanding Bushfire Attack Levels (BAL) for property buyers
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          A BAL rating determines what you can build, how much it will cost, and
          whether you can insure it. At BAL-LOW, there is no impact. At BAL-FZ,
          construction costs can increase by $150,000 or more, and some insurers
          will not offer cover at all. Here is how to check before you buy.
        </p>
      </div>

      {/* Immediate value: BAL scale */}
      <BALRatingScale />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#what-bal-means" className="hover:text-teal-600">
              What BAL actually means for your purchase
            </a>
          </li>
          <li>
            <a href="#how-bal-determined" className="hover:text-teal-600">
              How BAL is determined
            </a>
          </li>
          <li>
            <a href="#bfpl-vs-bal" className="hover:text-teal-600">
              Bush Fire Prone Land status vs BAL rating
            </a>
          </li>
          <li>
            <a href="#do-i-need" className="hover:text-teal-600">
              Do I need a BAL assessment?
            </a>
          </li>
          <li>
            <a href="#insurance" className="hover:text-teal-600">
              Insurance implications
            </a>
          </li>
          <li>
            <a href="#how-to-check" className="hover:text-teal-600">
              How to check before buying
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
        {/* SECTION 1: What BAL means */}
        <section id="what-bal-means" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What BAL actually means for your purchase
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Bushfire Attack Level is a classification under{' '}
            <span className="font-medium">
              Australian Standard AS 3959-2018
            </span>{' '}
            that measures the severity of a building&apos;s potential exposure to
            bushfire attack. It ranges from BAL-LOW (negligible risk) to BAL-FZ
            (direct flame contact). The rating dictates minimum construction
            standards for any new building or major renovation.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For property buyers, the BAL rating affects three things directly:
          </p>
          <div className="space-y-3 mt-2">
            <div className="rounded-2xl border border-slate-200 p-5">
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                1. Construction costs
              </h3>
              <p className="text-sm text-slate-700 leading-relaxed">
                Every step up in BAL rating adds mandatory construction
                requirements &mdash; from ember guards at BAL-12.5 to full
                non-combustible construction at BAL-FZ. These are not optional
                upgrades. They are legal minimums for a Construction Certificate.
                The cost difference between BAL-LOW and BAL-FZ on a standard
                residential build can exceed $200,000.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-5">
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                2. Insurance premiums
              </h3>
              <p className="text-sm text-slate-700 leading-relaxed">
                Insurers use their own bushfire risk models, which often align
                with but do not directly reference BAL ratings. Properties at
                BAL-29 and above typically face significant premium loadings.
                At BAL-FZ, some insurers will decline cover entirely or exclude
                bushfire from the policy.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 p-5">
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                3. Resale value and buyer pool
              </h3>
              <p className="text-sm text-slate-700 leading-relaxed">
                Properties with high BAL ratings have a smaller buyer pool.
                Anyone planning to renovate or rebuild faces the additional
                construction costs. Lenders may also require evidence of adequate
                insurance &mdash; which is harder to obtain at higher BAL levels.
              </p>
            </div>
          </div>
        </section>

        {/* SECTION 2: How BAL is determined */}
        <section id="how-bal-determined" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How BAL is determined
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A formal BAL assessment under AS 3959 considers three primary
            factors:
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse mt-2">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                    Factor
                  </th>
                  <th className="text-left py-3 font-semibold text-slate-900">
                    What it means
                  </th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Vegetation type</td>
                  <td className="py-3">
                    Classified into groups: forest, woodland, scrub, grassland,
                    rainforest, etc. Dense eucalypt forest produces far higher
                    radiant heat than grassland.
                  </td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">
                    Slope under the vegetation
                  </td>
                  <td className="py-3">
                    Fire travels faster uphill. Downslope vegetation relative to
                    the building increases BAL significantly. A property at the
                    top of a vegetated slope faces higher BAL than the same
                    property on flat ground.
                  </td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium">
                    Distance from classified vegetation
                  </td>
                  <td className="py-3">
                    Measured in metres from the building to the nearest
                    classified vegetation. The closer the vegetation, the higher
                    the BAL. Beyond 100m from most vegetation types, BAL drops to
                    BAL-LOW.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-slate-700 leading-relaxed">
            The assessor also considers the Fire Danger Index (FDI) for the
            region, which is set by the NSW Rural Fire Service. Higher FDI
            regions (such as parts of the Blue Mountains and Hawkesbury) start
            at a higher baseline, meaning the same vegetation at the same
            distance produces a higher BAL.
          </p>
        </section>

        {/* SECTION 3: BFPL vs BAL */}
        <section id="bfpl-vs-bal" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Bush Fire Prone Land status vs BAL rating
          </h2>
          <p className="text-slate-700 leading-relaxed">
            These are different things, and confusing them is one of the most
            common mistakes buyers make.
          </p>
          <div className="grid sm:grid-cols-2 gap-6 mt-2">
            <div className="rounded-xl border-2 border-amber-200 bg-white p-5">
              <p className="text-sm font-bold text-amber-700 mb-3">
                Bush Fire Prone Land (BFPL)
              </p>
              <ul className="space-y-2 text-sm text-slate-700">
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">&#9679;</span>
                  A mapped designation by the NSW RFS
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">&#9679;</span>
                  Shows up on your Section 10.7 planning certificate
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">&#9679;</span>
                  Three categories: Category 1, Category 2, Category 3
                  (vegetation buffer)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">&#9679;</span>
                  Triggers the requirement for a BAL assessment &mdash; but does
                  not tell you the BAL rating itself
                </li>
              </ul>
            </div>
            <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
              <p className="text-sm font-bold text-teal-700 mb-3">
                BAL rating
              </p>
              <ul className="space-y-2 text-sm text-slate-700">
                <li className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#9679;</span>
                  Determined by a site-specific assessment under AS 3959
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#9679;</span>
                  Considers vegetation, slope, and distance for the specific
                  building location
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#9679;</span>
                  Ranges from BAL-LOW to BAL-FZ
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#9679;</span>
                  Dictates exact construction requirements and cost
                </li>
              </ul>
            </div>
          </div>
          <p className="text-slate-700 leading-relaxed">
            A property can be on Bush Fire Prone Land (Category 2) and still
            receive a BAL-LOW rating if the classified vegetation is far enough
            away. Conversely, being outside the mapped BFPL boundary does not
            guarantee safety &mdash; maps are updated periodically and may not
            reflect recent vegetation growth.
          </p>
        </section>

        {/* SECTION 4: Decision diagram */}
        <section id="do-i-need" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Do I need a BAL assessment?
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Not every property on Bush Fire Prone Land requires a formal BAL
            assessment. But any new dwelling, addition, or alteration in a
            BFPL area will trigger one. Here is a simplified decision path:
          </p>
          <BALDecisionDiagram />
          <p className="text-slate-700 leading-relaxed">
            Even if you are buying an existing dwelling with no plans to build,
            knowing the BAL rating tells you what construction standard the
            existing building was built to &mdash; and what any future
            renovation would require. For properties built before the current
            AS 3959 standards, upgrading to comply can be a significant cost.
          </p>
        </section>

        {/* SECTION 5: Insurance */}
        <section id="insurance" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Insurance implications
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Insurers do not use BAL ratings directly &mdash; they use their own
            proprietary bushfire risk models. But the two correlate. Properties
            in high-BAL areas consistently face higher premiums, higher
            excesses, and in some cases, coverage exclusions.
          </p>
          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6 mt-2">
            <p className="text-sm font-semibold text-slate-900 mb-3">
              What buyers should do before exchange
            </p>
            <ul className="space-y-2 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">1.</span>
                Get an insurance quote for the specific address before you
                exchange contracts. This is free and tells you more about actual
                risk than any map.
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">2.</span>
                Ask whether bushfire cover is included or excluded. Some policies
                cover &ldquo;fire&rdquo; but not &ldquo;bushfire&rdquo; as a
                named peril.
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">3.</span>
                Check the bushfire excess separately from the general excess. It
                can be $5,000&ndash;$10,000 or more on high-risk properties.
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">4.</span>
                If the property is BAL-40 or BAL-FZ, check whether you can
                obtain cover at all. Lenders require insurance as a condition of
                the mortgage.
              </li>
            </ul>
          </div>
          <p className="text-slate-700 leading-relaxed">
            For a broader analysis of how climate risk is affecting property
            insurance in Australia, see our guide on{' '}
            <Link
              href="/blog/uninsurable-property-climate-risk"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              uninsurable properties and climate risk
            </Link>
            .
          </p>
        </section>

        {/* SECTION 6: How to check */}
        <section id="how-to-check" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How to check before buying
          </h2>
          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. Check the RFS Bush Fire Prone Land map
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The NSW Rural Fire Service publishes the Bush Fire Prone Land
                map at{' '}
                <a
                  href="https://www.rfs.nsw.gov.au/plan-and-prepare/building-in-a-bush-fire-area/planning-for-bush-fire-protection/bush-fire-prone-land"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  rfs.nsw.gov.au
                </a>
                . This tells you whether the property is in a BFPL category but
                does not tell you the BAL rating.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Run a bushfire risk check
              </h3>
              <p className="text-slate-700 leading-relaxed">
                PlotDetect&apos;s{' '}
                <Link
                  href="/reports/bushfire"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  Bushfire Risk Report
                </Link>{' '}
                cross-references the RFS BFPL map with satellite vegetation
                data to provide an indicative BAL risk band before you pay for a
                formal assessment. It is not a substitute for a certified BAL
                assessment, but it tells you what to expect. For a combined view
                of bushfire, flood, coastal, and heat exposure, see the{' '}
                <Link
                  href="/climate-risk"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  climate risk score
                </Link>
                .
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Order a Section 10.7 planning certificate
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The{' '}
                <Link
                  href="/blog/section-10-7-certificate-gaps-nsw"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  Section 10.7 certificate
                </Link>{' '}
                will confirm BFPL status. But note that it will not include the
                BAL rating, construction cost implications, or insurance impact.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                4. Commission a formal BAL assessment if needed
              </h3>
              <p className="text-slate-700 leading-relaxed">
                If the property is on BFPL and you plan to build, you will need
                a formal assessment by an accredited assessor. Costs range from
                $500 to $2,000 depending on site complexity. The assessment is
                valid for the life of the development application &mdash; but
                may need updating if vegetation or mapping changes.
              </p>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Frequently asked questions
          </h2>

          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                How much does a BAL assessment cost in NSW?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Between $500 and $2,000, depending on site complexity. Steep
                vegetated sites with multiple aspects cost more. The assessment
                must be conducted by an accredited practitioner under AS 3959.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can I reduce my BAL rating?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Yes, in some cases. Creating a larger Asset Protection Zone
                (APZ) by clearing vegetation between the building and classified
                vegetation can reduce the BAL. However, clearing may require
                approval under the Biodiversity Conservation Act, especially in
                E-zones or areas mapped on the Biodiversity Values Map. Clearing
                without approval carries significant penalties.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does BAL affect existing buildings or only new construction?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                BAL construction standards apply to new buildings, additions,
                and alterations. Existing dwellings are not required to be
                upgraded retroactively. However, any future renovation or
                extension must meet the current BAL standard, which may be
                higher than when the original dwelling was built.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                What is the difference between BFPL Category 1 and Category 2?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Category 1 is higher risk &mdash; typically areas of dense
                forest or woodland with higher fire potential. Category 2 covers
                lower-risk vegetation such as grassland. Category 3 is a buffer
                zone (usually 100m) around Category 1 and 2 areas. All three
                trigger the requirement for a BAL assessment for new
                development.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can I do a BAL assessment myself?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                For a Development Application or Construction Certificate, the
                assessment must be done by an accredited practitioner. For your
                own pre-purchase due diligence, you can use indicative tools
                like the{' '}
                <Link
                  href="/reports/bushfire"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  PlotDetect Bushfire Risk Report
                </Link>{' '}
                to understand the likely BAL band before commissioning a formal
                assessment.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-orange-200 bg-orange-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check bushfire risk before you buy
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s Bushfire Risk Report shows whether a property is
              on Bush Fire Prone Land, the vegetation density around it, and an
              indicative BAL risk band &mdash; before you pay $500+ for a formal
              assessment.
            </p>
            <TrackedLink
              href="/reports/bushfire"
              className="inline-flex items-center gap-2 px-6 py-3 bg-orange-600 text-white text-sm font-medium rounded-xl hover:bg-orange-500 transition-colors"
              page="bushfire-attack-level-bal-property-buyers"
              cta="check_bushfire"
            >
              Check bushfire risk
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
