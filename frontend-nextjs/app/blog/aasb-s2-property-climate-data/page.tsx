import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { ArrowRight } from 'lucide-react';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title: 'AASB S2 and Property-Level Climate Data: What Fund Managers Need — PlotDetect',
  description:
    'How AASB S2 climate disclosure requirements affect property portfolio reporting, and where to source location-specific physical risk data in Australia.',
  keywords: [
    'AASB S2 property climate data',
    'AASB S2 physical risk',
    'climate disclosure property portfolio',
    'climate risk reporting australia',
    'property climate risk data',
    'ISSB S2 australia',
    'physical risk assessment property',
  ],
};

export default function AasbS2PropertyDataPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="AASB S2 and property-level climate data: what fund managers need"
        description="How AASB S2 climate disclosure requirements affect property portfolio reporting, and where to source location-specific physical risk data in Australia."
        slug="aasb-s2-property-climate-data"
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
          AASB S2 and property-level climate data: what fund managers need
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          AASB S2 requires Australian entities to disclose climate-related risks using
          scenario analysis. For property-exposed portfolios, that means sourcing
          asset-level physical risk data that most organisations don&apos;t have yet.
        </p>
      </div>

      {/* Body */}
      <div className="space-y-8">
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What AASB S2 requires</h2>
          <p className="text-slate-700 leading-relaxed">
            AASB S2 (Climate-related Disclosures) mirrors ISSB S2 and applies to reporting periods
            beginning on or after 1 January 2025 for Group 1 entities, with Group 2 and Group 3
            following in subsequent years. The standard requires disclosure across four pillars:
            governance, strategy, risk management, and metrics &amp; targets.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For property portfolios, the critical requirement is in the Strategy pillar: entities must
            assess the current and anticipated effects of climate-related risks on their business model,
            strategy, and financial position. This explicitly includes physical risks — the acute and
            chronic hazards that affect property assets.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Paragraph 22 of AASB S2 requires the use of <span className="font-medium">climate-related
            scenario analysis</span> to assess resilience. For property, this means modelling how assets
            perform under different warming pathways (e.g. SSP2.45 at +2&deg;C and SSP3.70 at +3.5&deg;C).
            A statement that &ldquo;we consider climate risk in our investment process&rdquo; is insufficient.
            The standard demands scenario-specific, quantified analysis.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Why property portfolios are uniquely exposed</h2>
          <p className="text-slate-700 leading-relaxed">
            Property is inherently location-specific. Unlike a diversified equity portfolio, a property
            portfolio&apos;s physical risk profile is determined by the geographic coordinates of each asset.
            A fund with $500 million in residential mortgage-backed securities has exposure to thousands
            of individual locations, each with distinct flood, bushfire, heat, and coastal risk profiles.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The physical risks relevant to Australian property portfolios include:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Riverine and flash flooding</span> — modelled depth at
              different return periods. The Hawkesbury-Nepean floodplain alone contains an estimated
              $8 billion in residential property.
            </li>
            <li>
              <span className="font-medium">Bushfire</span> — proximity to vegetation, BAL rating
              under AS 3959, and projected changes to fire weather under warming scenarios.
            </li>
            <li>
              <span className="font-medium">Coastal erosion and inundation</span> — sea level rise
              projections, storm surge modelling, and coastal recession rates that affect properties
              within identified coastal vulnerability areas.
            </li>
            <li>
              <span className="font-medium">Extreme heat</span> — increased cooling costs, reduced
              liveability, and potential impacts on property values in Western Sydney and other
              heat-stressed regions.
            </li>
            <li>
              <span className="font-medium">Compound events</span> — concurrent flooding and storm
              damage, or bushfire followed by erosion, where the combined impact exceeds the sum
              of individual hazards.
            </li>
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">The data gap</h2>
          <p className="text-slate-700 leading-relaxed">
            Most Australian property fund managers currently lack the granular data needed for
            AASB S2 compliance. The typical situation is:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>Climate risk is assessed at the postcode or suburb level, not the property level</li>
            <li>Only one or two hazards are considered (usually flood), not the full multi-hazard profile</li>
            <li>Assessment is based on current conditions, not forward-looking scenarios</li>
            <li>Data comes from a single source (e.g. CoreLogic flood flag) without cross-referencing statutory overlays</li>
            <li>Results are qualitative (&ldquo;high/medium/low&rdquo;) rather than quantified</li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            AASB S2 demands more. The scenario analysis requirement means you need data that can be
            projected forward under different climate pathways. The strategy disclosure requires
            quantification of financial impact. A traffic-light rating doesn&apos;t satisfy either requirement.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Government vs commercial data</h2>
          <p className="text-slate-700 leading-relaxed">
            Australian climate hazard data exists in both government and commercial sources.
            Understanding the difference is essential for building a compliant data stack.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse mt-4">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">Dimension</th>
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">Government sources</th>
                  <th className="text-left py-3 font-semibold text-slate-900">Commercial providers</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Resolution</td>
                  <td className="py-3 pr-4">Varies: property-level (flood overlays) to 4km grid (NARCliM)</td>
                  <td className="py-3">Typically postcode to SA2; some offer property-level</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Hazard coverage</td>
                  <td className="py-3 pr-4">Individual hazards from separate agencies</td>
                  <td className="py-3">Multi-hazard (but Australian coverage varies)</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Scenarios</td>
                  <td className="py-3 pr-4">NARCliM: SSP2.45, SSP3.70. BoM: CMIP6 projections</td>
                  <td className="py-3">Global models (MSCI, S&amp;P) or Australian-specific (XDI)</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Cost</td>
                  <td className="py-3 pr-4">Free but integration-heavy</td>
                  <td className="py-3">$50K-$500K+ per year for institutional access</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Auditability</td>
                  <td className="py-3 pr-4">Public, transparent methodology</td>
                  <td className="py-3">Often proprietary/black-box models</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium">Planning integration</td>
                  <td className="py-3 pr-4">Source of statutory overlays (LEP, BFPL)</td>
                  <td className="py-3">Rarely includes planning constraint data</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-slate-700 leading-relaxed mt-4">
            The optimal approach for AASB S2 is to combine both: government statutory data
            (which auditors can verify against public sources) with forward-looking scenario
            projections. An assessment that shows &ldquo;this property is in the LEP flood planning
            area AND has projected flood depth increase under SSP3.70&rdquo; is significantly more
            defensible than either data source alone.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What a compliant data stack looks like</h2>
          <p className="text-slate-700 leading-relaxed">
            For property-exposed entities preparing for AASB S2 disclosure, the data stack should include:
          </p>
          <ol className="space-y-3 text-slate-700 leading-relaxed list-decimal list-inside">
            <li>
              <span className="font-medium">Asset-level hazard data</span> — flood depth at ARI
              return periods, bushfire BAL classification, coastal vulnerability status, and heat
              stress metrics for each property location.
            </li>
            <li>
              <span className="font-medium">Scenario projections</span> — how each hazard changes
              under at least two climate pathways (AASB S2 requires consideration of a scenario
              consistent with &lt;2&deg;C and a higher-warming scenario).
            </li>
            <li>
              <span className="font-medium">Statutory overlay integration</span> — LEP flood
              planning areas, Bush Fire Prone Land, heritage zones, and other planning constraints
              that affect development potential and adaptation options.
            </li>
            <li>
              <span className="font-medium">Financial impact quantification</span> — translation
              of physical hazard exposure into financial metrics: insurance cost uplift, capital
              expenditure for adaptation, potential value impairment, and portfolio concentration risk.
            </li>
            <li>
              <span className="font-medium">Audit trail</span> — clear provenance for all data
              sources, methodology documentation, and the ability to explain results to auditors
              and board members.
            </li>
          </ol>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Practical steps for fund managers</h2>
          <p className="text-slate-700 leading-relaxed">
            If you&apos;re a Group 2 or Group 3 entity preparing for AASB S2, the time to start building
            your climate risk data capability is now. The first reporting periods are approaching,
            and the data collection and validation process takes longer than most organisations expect.
          </p>
          <ol className="space-y-3 text-slate-700 leading-relaxed list-decimal list-inside">
            <li>
              <span className="font-medium">Inventory your property exposure.</span> Build a complete
              register of directly held properties, mortgage-secured properties, and indirect property
              exposure (through funds, trusts, or securitisations). You need addresses, not just postcodes.
            </li>
            <li>
              <span className="font-medium">Screen for multi-hazard exposure.</span> Run the full
              portfolio through property-level hazard assessment covering flood, bushfire, coastal,
              and heat stress. Identify concentration risk — clusters of assets exposed to the same hazard.
            </li>
            <li>
              <span className="font-medium">Apply scenario analysis.</span> Project forward under at
              least two climate pathways. How does the portfolio&apos;s risk profile change by 2040 and 2060?
              Which assets transition from &ldquo;marginal&rdquo; to &ldquo;high risk&rdquo;?
            </li>
            <li>
              <span className="font-medium">Quantify financial impact.</span> Translate physical risk
              into financial metrics: expected annual loss, insurance cost trajectory, potential capital
              expenditure for mitigation, and portfolio-level Value at Risk under each scenario.
            </li>
            <li>
              <span className="font-medium">Document methodology.</span> Auditors will want to
              understand your data sources, the spatial resolution of your analysis, and any
              assumptions or limitations. Deterministic, transparent methodologies are easier to
              audit than proprietary AI/ML models.
            </li>
          </ol>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">The role of deterministic scoring</h2>
          <p className="text-slate-700 leading-relaxed">
            A key decision in climate risk assessment is methodology: deterministic models vs
            machine learning. For AASB S2 compliance, deterministic approaches have a significant
            advantage — they produce auditable, explainable results.
          </p>
          <p className="text-slate-700 leading-relaxed">
            A deterministic model says: &ldquo;This property is 12m from a mapped watercourse, inside
            the LEP flood planning area, with modelled flood depth of 0.8m at 1% AEP based on
            the 2019 council flood study.&rdquo; Every element is traceable to a public data source.
          </p>
          <p className="text-slate-700 leading-relaxed">
            An ML model says: &ldquo;This property has a flood risk score of 73/100.&rdquo; An auditor
            asking &ldquo;why 73?&rdquo; gets a statistical answer about feature weights and training data,
            not a traceable chain of evidence. For disclosure purposes, the deterministic approach
            is almost always more defensible.
          </p>
        </section>

        {/* CTA */}
        <section className="mt-12 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check the climate risk profile for any NSW property
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect provides deterministic, property-level climate risk assessment using
              NSW government data sources, NARCliM 2.0 projections, and statutory planning overlays.
              Free instant checks for any NSW address. Portfolio screening available for
              institutional clients.
            </p>
            <TrackedLink
              href="/climate-risk"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="aasb-s2-property-climate-data"
              cta="climate_check"
            >
              Try the free climate risk check
              <ArrowRight className="w-4 h-4" />
            </TrackedLink>
          </div>

          <div className="rounded-2xl border border-slate-200 p-8 text-center">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">
              Request the full AASB S2 property data whitepaper
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              Detailed guidance on sourcing, validating, and presenting property-level climate risk
              data for AASB S2 disclosure, including worked examples and auditor Q&amp;A preparation.
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
