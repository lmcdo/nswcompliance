import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { ArrowRight } from 'lucide-react';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title: 'APRA CPG 229: Climate Risk Assessment for Property Lending — PlotDetect',
  description:
    'A practical guide to meeting APRA CPG 229 requirements for property-secured lending, including physical risk data, scenario analysis, and portfolio screening.',
  keywords: [
    'APRA CPG 229 property',
    'climate risk property lending',
    'APRA climate risk assessment',
    'mortgage climate risk',
    'physical risk property portfolio',
    'ADI climate risk',
    'property lending climate data',
  ],
};

export default function ApraCpg229Page() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="APRA CPG 229: climate risk assessment for property lending"
        description="A practical guide to meeting APRA CPG 229 requirements for property-secured lending, including physical risk data, scenario analysis, and portfolio screening."
        slug="apra-cpg-229-property-assessment"
        date="2026-05-17"
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
          APRA CPG 229: climate risk assessment for property lending
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          APRA expects regulated entities to identify, assess, and manage climate-related
          financial risks. For ADIs with property-secured lending, that means understanding
          physical hazard exposure at the asset level — not the postcode level.
        </p>
      </div>

      {/* Body */}
      <div className="space-y-8">
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What CPG 229 requires</h2>
          <p className="text-slate-700 leading-relaxed">
            APRA&apos;s Prudential Practice Guide CPG 229 (Climate Change Financial Risks) was
            published in November 2021 and sets out APRA&apos;s expectations for how regulated
            entities — banks, insurers, and superannuation trustees — should manage climate-related
            financial risks. While technically guidance rather than a binding prudential standard,
            APRA has made clear that it expects entities to demonstrate compliance.
          </p>
          <p className="text-slate-700 leading-relaxed">
            CPG 229 distinguishes between physical risks (direct damage from climate hazards) and
            transition risks (financial impacts from the shift to a low-carbon economy). For
            property lending, physical risk is the dominant concern. An ADI with a $50 billion
            residential mortgage book needs to understand which of those properties are exposed
            to flood, bushfire, coastal erosion, or extreme heat — and how that exposure changes
            under different climate scenarios.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The guide explicitly states that entities should use scenario analysis as a tool for
            understanding potential climate impacts. This isn&apos;t a box-ticking exercise. APRA
            expects entities to use scenarios that are relevant to their specific risk profile,
            consider multiple time horizons, and integrate the results into risk management
            and strategic planning.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Physical risk in mortgage portfolios</h2>
          <p className="text-slate-700 leading-relaxed">
            A residential mortgage is ultimately secured by a physical asset at a specific
            location. If that location is exposed to increasing climate hazards, the security
            value is at risk. The mechanisms are both direct and indirect:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Direct damage.</span> Flooding, bushfire, or storm
              damage reduces the value of the security. Even with insurance, there may be
              underinsurance, policy exclusions, or delays in repair that affect the borrower&apos;s
              financial position and the bank&apos;s recovery prospects.
            </li>
            <li>
              <span className="font-medium">Insurance withdrawal.</span> As premiums rise in
              high-risk areas, some borrowers drop coverage or face exclusions for specific
              perils. An uninsured loss can trigger default. An uninsurable property has
              reduced market value regardless of whether a loss event occurs.
            </li>
            <li>
              <span className="font-medium">Value impairment.</span> Properties in areas with
              increasing hazard exposure may experience price discounts as the market becomes
              more risk-aware. Research suggests 5-12% discounts for flood-exposed properties
              in NSW, with the discount widening after major events.
            </li>
            <li>
              <span className="font-medium">Concentration risk.</span> A bank with significant
              exposure to a single geographic area faces correlated losses from a single event.
              The 2022 Northern Rivers floods affected thousands of properties simultaneously
              within a concentrated lending area.
            </li>
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What data banks need</h2>
          <p className="text-slate-700 leading-relaxed">
            To meet APRA&apos;s expectations, an ADI&apos;s climate risk assessment for property lending
            should include:
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Asset-level hazard exposure</h3>
          <p className="text-slate-700 leading-relaxed">
            Each property in the portfolio needs to be assessed against multiple hazards at
            its specific coordinates. Postcode-level assessment is insufficient — two properties
            in the same postcode can have completely different flood, bushfire, and coastal
            exposure depending on elevation, proximity to waterways, and vegetation.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The minimum hazard set for Australian property should include: riverine and flash
            flooding (with depth at multiple return periods), bushfire (BAL classification),
            coastal erosion and inundation (for coastal properties), and extreme heat stress
            (for properties in heat-affected regions).
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Scenario-based projections</h3>
          <p className="text-slate-700 leading-relaxed">
            CPG 229 expects scenario analysis across multiple time horizons. For property lending,
            relevant scenarios should include at least a &ldquo;Paris-aligned&rdquo; pathway (SSP1.26 or
            SSP2.45) and a &ldquo;high warming&rdquo; pathway (SSP3.70 or SSP5.85). The time horizons
            should align with the bank&apos;s lending book — typically 5-year, 15-year, and 30-year
            windows to match mortgage terms.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Australia&apos;s primary source for regional climate projections is NARCliM 2.0, which
            provides downscaled CMIP6 projections for southeast Australia at approximately 4km
            resolution under SSP2.45 and SSP3.70. This data includes temperature, precipitation,
            wind, humidity, and derived indices including fire weather.
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Statutory planning context</h3>
          <p className="text-slate-700 leading-relaxed">
            Physical hazard data alone is incomplete without understanding the statutory planning
            framework. A property in an LEP flood planning area faces development constraints that
            affect its long-term value and adaptability. A property on Bush Fire Prone Land faces
            additional construction costs under AS 3959. A property in a heritage conservation area
            may have limited options for climate adaptation upgrades.
          </p>
          <p className="text-slate-700 leading-relaxed">
            These planning constraints are material to credit risk because they affect the
            borrower&apos;s ability to adapt the property, the cost of any future development, and
            the property&apos;s market value to future buyers. A comprehensive assessment integrates
            physical hazard data with statutory overlay data.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Stress testing approaches</h2>
          <p className="text-slate-700 leading-relaxed">
            APRA&apos;s climate vulnerability assessment (CVA) exercises have given ADIs practice in
            climate stress testing. The key lesson from early CVA rounds is that the quality of
            results is entirely dependent on the quality of input data. Banks that used postcode-level
            proxies got postcode-level results — insufficient for identifying specific at-risk
            exposures or for making portfolio-level decisions.
          </p>
          <p className="text-slate-700 leading-relaxed">
            A property-level stress test should model:
          </p>
          <ol className="space-y-3 text-slate-700 leading-relaxed list-decimal list-inside">
            <li>
              <span className="font-medium">Event-based scenarios.</span> What happens to the
              portfolio if a 1-in-100 year flood event occurs in each major catchment? Which
              loans are directly affected? What is the total exposure at risk?
            </li>
            <li>
              <span className="font-medium">Chronic degradation.</span> Under a high-warming
              scenario, which properties transition from &ldquo;insurable&rdquo; to &ldquo;marginally insurable&rdquo;
              to &ldquo;uninsurable&rdquo; over the next 20 years? What is the cumulative value impairment?
            </li>
            <li>
              <span className="font-medium">Correlated default.</span> In a major climate event,
              multiple borrowers are affected simultaneously. If 500 borrowers in the Hawkesbury-Nepean
              experience a 1-in-100 year flood, what proportion are likely to default, and what is the
              recovery rate on water-damaged security?
            </li>
            <li>
              <span className="font-medium">Insurance discontinuity.</span> If insurers withdraw
              flood cover from a catchment (as has occurred in parts of the Northern Rivers),
              what happens to property values and borrower behaviour?
            </li>
          </ol>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What good property climate data looks like</h2>
          <p className="text-slate-700 leading-relaxed">
            For CPG 229 compliance, the data used for physical risk assessment should meet several
            criteria:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Asset-level granularity.</span> Risk assessment at the
              individual property coordinate, not aggregated to postcode or suburb. Flood depth
              varies by metres within a single street.
            </li>
            <li>
              <span className="font-medium">Multi-hazard coverage.</span> Assessment across flood,
              bushfire, coastal, and heat hazards. Single-peril assessment misses compound risks
              and creates blind spots.
            </li>
            <li>
              <span className="font-medium">Scenario-based.</span> Forward-looking under at least
              two SSP pathways with defined time horizons. Current-state-only assessment doesn&apos;t
              satisfy the scenario analysis requirement.
            </li>
            <li>
              <span className="font-medium">Deterministic methodology.</span> Results should be
              traceable to source data and explainable to auditors, board risk committees, and
              regulators. Proprietary ML models that produce a &ldquo;score&rdquo; without transparent
              methodology create audit risk.
            </li>
            <li>
              <span className="font-medium">Statutory integration.</span> Physical hazard data
              combined with planning overlay data (LEP flood areas, Bush Fire Prone Land, coastal
              vulnerability areas) provides the full picture of regulatory and physical constraint.
            </li>
            <li>
              <span className="font-medium">Data provenance.</span> Clear documentation of
              underlying data sources, update frequency, and known limitations. Auditors will
              ask where the data comes from.
            </li>
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Getting started</h2>
          <p className="text-slate-700 leading-relaxed">
            For ADIs early in their climate risk data journey, the practical starting point is:
          </p>
          <ol className="space-y-3 text-slate-700 leading-relaxed list-decimal list-inside">
            <li>
              <span className="font-medium">Geocode your mortgage book.</span> Ensure every
              property in the portfolio has accurate coordinates, not just addresses. Address-level
              geocoding is the foundation for property-level hazard assessment.
            </li>
            <li>
              <span className="font-medium">Run a multi-hazard screen.</span> Identify which
              properties fall within statutory hazard overlays (flood planning area, Bush Fire
              Prone Land, coastal vulnerability area). This uses publicly available government
              data and gives an immediate view of regulatory exposure.
            </li>
            <li>
              <span className="font-medium">Prioritise detailed assessment.</span> For the
              highest-exposure properties, obtain detailed hazard data: flood depth at multiple
              ARI, BAL classification, and projected changes under climate scenarios.
            </li>
            <li>
              <span className="font-medium">Build the reporting framework.</span> Structure
              the results to map to CPG 229&apos;s framework: risk identification (which hazards,
              which assets), measurement (quantified exposure), monitoring (ongoing tracking),
              and management (mitigation actions and limits).
            </li>
          </ol>
        </section>

        {/* CTA */}
        <section className="mt-12 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check the climate risk profile for any NSW property
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect provides free, deterministic climate risk assessment for any NSW address.
              Flood depth at ARI return periods, bushfire BAL estimation, heat stress projections
              (NARCliM 2.0), and statutory planning overlays — all from authoritative government sources.
            </p>
            <TrackedLink
              href="/climate-risk"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="apra-cpg-229-property-assessment"
              cta="climate_check"
            >
              Try the free climate risk check
              <ArrowRight className="w-4 h-4" />
            </TrackedLink>
          </div>

          <div className="rounded-2xl border border-slate-200 p-8 text-center">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">
              Request the CPG 229 property climate data guide
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              Practical guidance for ADIs: data sourcing, portfolio screening methodology,
              stress testing frameworks, and board reporting templates for climate risk
              in property-secured lending.
            </p>
            <div className="flex items-center gap-3 max-w-md mx-auto">
              <input
                type="email"
                placeholder="work@company.com"
                className="flex-1 px-4 py-2.5 rounded-lg border border-slate-200 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                disabled
              />
              <button
                className="px-5 py-2.5 bg-slate-900 text-white text-sm font-medium rounded-lg hover:bg-slate-800 transition-colors"
                disabled
              >
                Send
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-2">Coming soon</p>
          </div>
        </section>

        <BlogDisclaimer />

        {/* Back link */}
        <div className="pt-8 border-t border-slate-100">
          <Link href="/blog" className="text-sm text-slate-500 hover:text-teal-600 transition-colors">
            &larr; Back to Insights
          </Link>
        </div>
      </div>
    </article>
  );
}
