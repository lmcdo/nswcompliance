import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { ArrowRight } from 'lucide-react';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    '1 in 4 Australian Households Could Be Uninsurable by 2050 — PlotDetect',
  description:
    'Actuaries Institute, ICA, and Treasury data projects that 25% of Australian households will face unaffordable or unavailable insurance by 2050. Here is the trajectory, the regions most affected, and what property owners can do now.',
  keywords: [
    'property insurance risk Australia',
    'uninsurable property Australia 2050',
    'climate risk property value projection',
    'insurance affordability crisis Australia',
    'climate risk property assessment',
    'flood insurance withdrawal Australia',
    'reinsurance Australia natural catastrophe',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual components                                                  */
/* ------------------------------------------------------------------ */

/** Visual 1 — Insurance affordability trajectory 2024-2050 */
function AffordabilityTrajectory() {
  const milestones = [
    {
      year: '2024',
      households: '520,000',
      pct: '4%',
      bar: 'w-[16%]',
      color: 'bg-amber-400',
      note: 'Actuaries Institute affordability stress threshold',
    },
    {
      year: '2030',
      households: '~900,000',
      pct: '7%',
      bar: 'w-[28%]',
      color: 'bg-amber-500',
      note: 'APRA CVA mid-range projection',
    },
    {
      year: '2040',
      households: '~1.8M',
      pct: '14%',
      bar: 'w-[56%]',
      color: 'bg-red-400',
      note: 'Compound premium growth under SSP2-4.5',
    },
    {
      year: '2050',
      households: '~2.7M',
      pct: '25%',
      bar: 'w-full',
      color: 'bg-red-600',
      note: 'APRA "Mind the Gap" headline scenario',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
        Projected insurance affordability crisis
      </p>
      <p className="text-xs text-slate-400 mb-6">
        Households facing unaffordable or unavailable home insurance
      </p>
      <div className="space-y-5">
        {milestones.map((m) => (
          <div key={m.year}>
            <div className="flex items-baseline justify-between mb-1.5">
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-bold text-slate-900">
                  {m.year}
                </span>
                <span className="text-sm text-slate-600">
                  {m.households} households
                </span>
              </div>
              <span className="text-sm font-semibold text-slate-900">
                {m.pct}
              </span>
            </div>
            <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
              <div className={`h-full ${m.bar} ${m.color} rounded-full`} />
            </div>
            <p className="text-xs text-slate-400 mt-1">{m.note}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-5 border-t border-slate-200 pt-3">
        Sources: Actuaries Institute (2024), APRA Insurance CVA &ldquo;Mind the
        Gap&rdquo; (March 2026), ICA analysis. 2030 and 2040 figures are
        interpolated from APRA scenario modelling under SSP2-4.5.
      </p>
    </div>
  );
}

/** Visual 2 — Regional impact map (text-based) */
function RegionalImpactDiagram() {
  const regions = [
    {
      name: 'Northern Rivers NSW',
      hazard: 'Riverine flood',
      severity: 'Extreme',
      dotColor: 'bg-red-600',
      detail:
        'Lismore, Ballina, Byron. 30-40% of households already dropped coverage post-2022.',
    },
    {
      name: 'Far North Queensland',
      hazard: 'Cyclone + flood',
      severity: 'Extreme',
      dotColor: 'bg-red-600',
      detail:
        'Cairns, Townsville, Mackay. Cyclone reinsurance costs driving 15-20% annual premium increases.',
    },
    {
      name: 'Western Sydney',
      hazard: 'Extreme heat + flood',
      severity: 'High',
      dotColor: 'bg-red-400',
      detail:
        'Penrith, Hawkesbury-Nepean. Days above 35C projected to triple by 2060. Flash flood exposure.',
    },
    {
      name: 'Hunter Valley NSW',
      hazard: 'Riverine flood',
      severity: 'High',
      dotColor: 'bg-red-400',
      detail:
        'Maitland, Cessnock, Singleton. Repeated flood events in 2022 and 2024 triggered repricing.',
    },
    {
      name: 'NSW South Coast',
      hazard: 'Coastal erosion + bushfire',
      severity: 'Moderate-High',
      dotColor: 'bg-amber-500',
      detail:
        'Wamberal, Collaroy, Lake Conjola. Dual hazard from coastal recession and peri-urban fire.',
    },
    {
      name: 'SE Queensland',
      hazard: 'Flood + severe storm',
      severity: 'High',
      dotColor: 'bg-red-400',
      detail:
        'Logan, Ipswich, Gold Coast hinterland. 2022 floods expanded the insurer risk maps significantly.',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
        Regions most affected by insurance withdrawal
      </p>
      <p className="text-xs text-slate-400 mb-5">
        Ranked by current premium stress and projected trajectory
      </p>
      <div className="space-y-4">
        {regions.map((r) => (
          <div
            key={r.name}
            className="rounded-xl bg-white border border-slate-200 p-4"
          >
            <div className="flex items-center gap-3 mb-1.5">
              <span
                className={`flex-shrink-0 w-2.5 h-2.5 rounded-full ${r.dotColor}`}
              />
              <span className="text-sm font-semibold text-slate-900">
                {r.name}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {r.hazard}
              </span>
            </div>
            <p className="text-sm text-slate-600 pl-5.5 ml-[0.625rem]">
              {r.detail}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Visual 3 — Reinsurance withdrawal pattern */
function ReinsuranceDiagram() {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
        How reinsurance withdrawal reaches your premium
      </p>
      <div className="grid sm:grid-cols-4 gap-3">
        {[
          {
            step: '1',
            title: 'Global reinsurers reprice',
            desc: 'Munich Re, Swiss Re increase nat-cat premiums or pull capacity from Australian market.',
          },
          {
            step: '2',
            title: 'Domestic insurers absorb costs',
            desc: 'IAG, Suncorp, QBE pass reinsurance cost through to premium structures.',
          },
          {
            step: '3',
            title: 'Address-level repricing',
            desc: 'Insurers recalibrate risk models. High-exposure addresses see 15-30% annual increases.',
          },
          {
            step: '4',
            title: 'Affordability threshold crossed',
            desc: 'Premiums exceed 4 weeks gross income. Household drops coverage or reduces scope.',
          },
        ].map((s) => (
          <div key={s.step} className="rounded-xl bg-white border border-slate-200 p-4">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold mb-2">
              {s.step}
            </span>
            <p className="text-sm font-semibold text-slate-900 mb-1">
              {s.title}
            </p>
            <p className="text-xs text-slate-600">{s.desc}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4">
        This cycle has already completed in parts of the Northern Rivers and FNQ.
        APRA projects it will reach approximately 2.7 million households
        nationally by 2050.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function UninsurableHouseholds2050Page() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="1 in 4 Australian households could be uninsurable by 2050"
        description={`The trajectory from 520,000 households in affordability stress today to projected 2.7 million by 2050. Which regions, why it's accelerating, and what to check.`}
        slug="uninsurable-households-australia-2050"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-700">
            Climate Risk
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          1 in 4 Australian households could be uninsurable by 2050
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          APRA&apos;s March 2026 Insurance Climate Vulnerability Assessment
          projected that approximately 2.7 million Australian households will
          face unaffordable or unavailable home insurance by 2050. That is not a
          worst-case scenario. It is the mid-range projection under current
          emissions trajectories. Here is the data behind the headline, the
          regions on the steepest trajectory, and what the numbers mean for
          property values and mortgage lending.
        </p>
      </div>

      {/* Immediate value: the trajectory */}
      <AffordabilityTrajectory />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#trajectory" className="hover:text-teal-600">
              The trajectory: 520,000 to 2.7 million
            </a>
          </li>
          <li>
            <a href="#regions" className="hover:text-teal-600">
              Which regions are on the steepest curve
            </a>
          </li>
          <li>
            <a href="#reinsurance" className="hover:text-teal-600">
              The reinsurance withdrawal pattern
            </a>
          </li>
          <li>
            <a href="#climate-projections" className="hover:text-teal-600">
              How climate projections feed insurance pricing
            </a>
          </li>
          <li>
            <a href="#property-values" className="hover:text-teal-600">
              What this means for property values and mortgages
            </a>
          </li>
          <li>
            <a href="#government-response" className="hover:text-teal-600">
              Government responses: the Hazards Insurance Partnership
            </a>
          </li>
          <li>
            <a href="#assess-trajectory" className="hover:text-teal-600">
              How to assess your property&apos;s trajectory
            </a>
          </li>
        </ul>
      </nav>

      {/* Body */}
      <div className="space-y-10">
        {/* Section 1 */}
        <section id="trajectory" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The trajectory: 520,000 to 2.7 million
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Actuaries Institute&apos;s 2024 Home Insurance Affordability
            Update identified approximately 520,000 Australian households in
            insurance affordability stress &mdash; defined as premiums exceeding
            one month&apos;s gross household income. That figure represented
            roughly 4% of all households.
          </p>
          <p className="text-slate-700 leading-relaxed">
            APRA&apos;s March 2026 Insurance Climate Vulnerability Assessment
            extended the analysis forward. Under SSP2-4.5 (the
            &ldquo;middle-of-the-road&rdquo; emissions pathway), the number of
            households crossing the affordability threshold rises to
            approximately 2.7 million by 2050 &mdash; one in four Australian
            households. Annual insured weather losses increase from $7 billion
            (2024) to above $16 billion. Flood losses alone increase by 240%.
          </p>
          <p className="text-slate-700 leading-relaxed">
            These projections come from stress testing the five largest general
            insurers in Australia &mdash; IAG, Suncorp, QBE, Allianz, and
            Hollard &mdash; which together cover approximately 90% of the
            residential market. The data reflects actual pricing models, not
            academic estimates.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For context on how this repricing is already affecting property
            markets, see our analysis of{' '}
            <Link
              href="/blog/uninsurable-property-climate-risk"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              how climate risk is repricing Australian real estate
            </Link>
            .
          </p>
        </section>

        {/* Section 2 */}
        <section id="regions" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Which regions are on the steepest curve
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The insurance affordability crisis is not uniform. It is
            concentrated in six corridors where natural hazard exposure,
            population growth, and climate trajectory intersect. NSW and
            Queensland together account for 60% of all uninsured homes
            nationally.
          </p>

          <RegionalImpactDiagram />

          <p className="text-slate-700 leading-relaxed">
            The common thread is compounding frequency. Properties that
            experienced one major event per decade are now experiencing events
            every two to three years. Each event triggers insurer repricing.
            Each repricing pushes more households past the affordability
            threshold. The cycle accelerates.
          </p>
        </section>

        {/* Section 3 */}
        <section id="reinsurance" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The reinsurance withdrawal pattern
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Most property owners never think about reinsurance &mdash; the
            insurance that insurers themselves buy to cover catastrophic losses.
            But reinsurance pricing is the primary driver of what you pay. When
            global reinsurers reprice Australian natural catastrophe risk, every
            domestic insurer must either absorb the cost or pass it through to
            premiums.
          </p>

          <ReinsuranceDiagram />

          <p className="text-slate-700 leading-relaxed">
            Munich Re and Swiss Re &mdash; the two largest global reinsurers
            &mdash; have publicly flagged Australia as one of the most
            climate-exposed insurance markets globally. Munich Re&apos;s 2025
            NatCat Review noted that Australian flood and cyclone losses have
            exceeded actuarial expectations in four of the last five years.
            Swiss Re&apos;s Sigma Institute estimated that Australia&apos;s
            insured natural catastrophe losses will grow 5-7% annually through
            2050, well above premium growth.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The practical consequence: reinsurance capacity for Australian
            nat-cat is contracting. Domestic insurers face higher reinsurance
            costs, larger retained losses, and pressure from shareholders to
            exit unprofitable geographies. This is already happening. ICA data
            shows that the number of insurers offering flood cover in the
            Northern Rivers dropped from seven in 2020 to three in 2025.
          </p>
        </section>

        {/* Section 4 */}
        <section id="climate-projections" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How climate projections feed insurance pricing
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Insurers are no longer pricing risk from historical claims data
            alone. The major insurers now incorporate forward-looking climate
            projections into their pricing models. The data infrastructure
            behind this is more sophisticated than most property owners realise.
          </p>
          <div className="rounded-2xl border border-slate-200 p-6 space-y-3">
            <h3 className="text-lg font-semibold text-slate-900">
              The projection stack insurers use
            </h3>
            <ul className="space-y-2 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-teal-500 mt-0.5 flex-shrink-0">
                  &#9679;
                </span>
                <span>
                  <strong>IPCC AR6 scenarios</strong> (SSP1-2.6 through
                  SSP5-8.5) provide the global emissions pathway.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-teal-500 mt-0.5 flex-shrink-0">
                  &#9679;
                </span>
                <span>
                  <strong>NARCliM 2.0</strong> downscales global models to 4km
                  resolution for NSW, providing temperature, rainfall intensity,
                  and wind projections at local scale.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-teal-500 mt-0.5 flex-shrink-0">
                  &#9679;
                </span>
                <span>
                  <strong>Risk Frontiers catastrophe models</strong> (FloodAUS,
                  CyclAUS, FireAUS) translate climate projections into
                  address-level damage estimates used by Australian insurers.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-teal-500 mt-0.5 flex-shrink-0">
                  &#9679;
                </span>
                <span>
                  <strong>NFID</strong> (National Flood Information Database)
                  covers 13.4 million Australian addresses with flood risk
                  ratings that feed directly into underwriting.
                </span>
              </li>
            </ul>
          </div>
          <p className="text-slate-700 leading-relaxed">
            Under SSP2-4.5, NARCliM 2.0 projects that Western Sydney will
            experience approximately 30 days above 35&deg;C per year by 2060,
            up from roughly 10 today. Rainfall intensity during extreme events
            increases 15-25%, meaning the same catchment produces more water in
            shorter periods. Extended fire seasons push the Forest Fire Danger
            Index into &ldquo;catastrophic&rdquo; territory more frequently.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For insurers, these projections translate directly into higher
            expected annual losses. For property owners, they mean that
            today&apos;s premium is almost certainly the lowest it will ever be
            for a climate-exposed property. A home that is marginally affordable
            to insure in 2026 may become genuinely unaffordable by 2035 &mdash;
            well within most mortgage terms.
          </p>
        </section>

        {/* Section 5 */}
        <section id="property-values" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What this means for property values and mortgages
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The insurance affordability crisis has a direct transmission
            mechanism to property values. APRA now requires banks to consider
            climate risk in their mortgage lending under CPG 229. When a
            property&apos;s insurance becomes unaffordable or unavailable, the
            collateral that backs the mortgage is impaired.
          </p>
          <div className="rounded-2xl border border-slate-200 p-6 space-y-3">
            <h3 className="text-lg font-semibold text-slate-900">
              The lending feedback loop
            </h3>
            <ol className="space-y-2 text-sm text-slate-700 list-decimal list-inside">
              <li>
                Insurance premiums rise above affordability for borrower
              </li>
              <li>
                Borrower drops or reduces coverage
              </li>
              <li>
                Lender&apos;s collateral is now uninsured or underinsured
              </li>
              <li>
                Lender tightens lending criteria for that postcode or address
              </li>
              <li>
                Reduced credit availability depresses property values
              </li>
              <li>
                Lower values reduce equity, triggering LMI recalculation
              </li>
            </ol>
          </div>
          <p className="text-slate-700 leading-relaxed">
            This feedback loop has not yet triggered widespread lending
            restrictions. But APRA&apos;s CVA explicitly modelled collateral
            impairment scenarios, and the major banks are building
            address-level climate risk into their mortgage origination
            systems. The transition from portfolio-level to address-level risk
            assessment will, when it completes, create postcode-specific
            lending restrictions that compound the insurance problem.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Companies with property portfolios face a parallel obligation.
            Under{' '}
            <Link
              href="/blog/aasb-s2-property-climate-data"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              AASB S2 mandatory climate reporting
            </Link>
            , approximately 10,000 entities must now disclose the percentage
            of their assets exposed to physical climate risks. Property
            holdings with deteriorating insurance trajectories become material
            disclosable risks.
          </p>
        </section>

        {/* Section 6 */}
        <section id="government-response" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Government responses: the Hazards Insurance Partnership
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The federal government established the Hazards Insurance
            Partnership (HIP) in 2024 as a joint initiative between Treasury,
            APRA, and the ICA. Its stated goals are improving hazard data
            transparency, exploring reinsurance pool expansion beyond
            cyclones (the existing Australian Reinsurance Pool Corporation
            covers cyclone only), and developing mitigation investment
            frameworks.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Progress has been incremental. The ARPC cyclone reinsurance pool,
            established in 2022, has reduced cyclone premiums by an estimated
            $180 on average in northern Australia. But there is no equivalent
            pool for flood &mdash; the hazard driving the largest share of
            premium stress. Expanding the pool to cover flood would require
            substantially more government capital and is politically
            contentious.
          </p>
          <p className="text-slate-700 leading-relaxed">
            At the state level, the NSW Climate Change and Natural Hazards
            SEPP (exhibited February-March 2026) proposes prescribing NARCliM
            2.0 climate scenarios for all development assessment. If
            implemented, every DA in NSW would need to account for projected
            climate conditions &mdash; effectively building the insurance
            industry&apos;s forward-looking approach into the planning system.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The Productivity Commission&apos;s 2024 report on natural disaster
            funding recommended standardised hazard disclosure at the point
            of property sale. No state has yet implemented this, though
            Queensland&apos;s existing seller disclosure regime provides a
            partial model.
          </p>
        </section>

        {/* Section 7 */}
        <section id="assess-trajectory" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How to assess your property&apos;s trajectory
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The gap between what insurers know about your property and what
            you know is the core problem. Five steps to narrow it:
          </p>
          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. Get a multi-hazard risk assessment
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A suburb-level view is not enough. Two properties 200 metres
                apart can have completely different flood, bushfire, and heat
                exposure. PlotDetect&apos;s{' '}
                <Link
                  href="/climate-risk"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  climate risk assessment
                </Link>{' '}
                checks five government-mapped hazard layers at the property
                level. It shows which hazards overlap your address &mdash; it
                does not predict whether damage will occur.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Get an insurance quote before you commit
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Call at least two insurers with the specific address. Ask for
                a full quote including flood, storm, and bushfire cover. The
                premium reflects the insurer&apos;s proprietary risk model
                &mdash; data you cannot access any other way. A quote that
                seems high today will only increase.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Check the flood exposure specifically
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Flood is responsible for the largest share of the
                affordability crisis. PlotDetect&apos;s{' '}
                <Link
                  href="/reports/flood"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  Flood Screening
                </Link>{' '}
                cross-references LEP overlays, flood study modelling, and
                state data to show depth and frequency information that
                planning certificates do not include.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                4. Consider the 2040 scenario, not just today
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A 30-year mortgage taken out in 2026 matures in 2056. If the
                property is in a region where climate projections show
                worsening hazard exposure, insurance costs will compound over
                the life of the loan. The question is not whether you can
                afford the premium today, but whether you can afford it in
                2040.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                5. Factor insurance into purchase price
              </h3>
              <p className="text-slate-700 leading-relaxed">
                At a 5% discount rate, $5,000 per year in additional
                insurance costs equates to $100,000 in lost property value.
                If you are comparing two properties and one has materially
                higher climate exposure, the price should reflect that
                liability &mdash; even if the market has not yet adjusted.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check your property&apos;s climate risk trajectory
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect provides free, instant climate risk assessment for any
              NSW address &mdash; flood, bushfire, coastal, and heat exposure
              from government data sources. See which hazards overlap your
              property before you buy.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/climate-risk"
                className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
                page="uninsurable-households-australia-2050"
                cta="climate_check"
              >
                Check climate risk
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/reports/flood"
                className="inline-flex items-center gap-2 px-6 py-3 text-slate-700 text-sm font-medium rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all"
              >
                Check flood risk
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
