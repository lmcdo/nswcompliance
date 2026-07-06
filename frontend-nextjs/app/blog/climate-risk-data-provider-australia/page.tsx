import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { ArrowRight } from 'lucide-react';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title: 'Climate Risk Data Providers in Australia: A Comparison — PlotDetect',
  description:
    'Comparing Australian climate risk data sources — government, commercial, and open-source — for flood, bushfire, coastal, and heat stress assessment at the property level.',
  keywords: [
    'climate risk data australia',
    'climate risk data provider',
    'property climate risk assessment',
    'flood data australia',
    'bushfire risk data',
    'NARCliM climate projections',
    'physical climate risk data',
  ],
};

export default function ClimateRiskDataProviderPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Climate risk data providers in Australia: a comparison"
        description="Comparing Australian climate risk data sources — government, commercial, and open-source — for flood, bushfire, coastal, and heat stress assessment."
        slug="climate-risk-data-provider-australia"
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
          Climate risk data providers in Australia: a comparison
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          As AASB S2 disclosure requirements take effect and insurance costs climb,
          Australian organisations need property-level climate risk data. But the landscape
          of available data is fragmented, inconsistent, and often poorly understood.
          This guide maps what&apos;s available, what it costs, and what it actually tells you.
        </p>
      </div>

      {/* Body */}
      <div className="space-y-8">
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Why property-level data matters</h2>
          <p className="text-slate-700 leading-relaxed">
            Most climate risk assessments in Australia still operate at the LGA or postcode level. A fund
            manager with a $2 billion mortgage book might know that &ldquo;Western Sydney has high heat stress
            exposure&rdquo; — but that tells them nothing about whether a specific property at 14 Smith Street,
            Penrith is on a flood plain, in a bushfire-prone corridor, or exposed to coastal recession.
          </p>
          <p className="text-slate-700 leading-relaxed">
            AASB S2 and APRA CPG 229 both require scenario-based physical risk assessment. The scenario
            models exist (NARCliM 2.0 provides SSP2.45 and SSP3.70 projections to 2099). The gap is in
            translating those projections to individual property locations — and combining them with
            statutory hazard overlays that affect property use, insurance, and development potential.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Government data sources</h2>
          <p className="text-slate-700 leading-relaxed">
            The Australian government (federal, state, and local) publishes substantial climate hazard data,
            but it&apos;s scattered across dozens of agencies with different formats, update cycles, and access methods.
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Flood</h3>
          <p className="text-slate-700 leading-relaxed">
            NSW SES and individual councils publish flood study data. The quality varies dramatically by LGA.
            Some councils (Hawkesbury-Nepean, Parramatta) have detailed ARI depth modelling at 1-in-20, 1-in-50,
            1-in-100, and 1-in-500 year return intervals. Others publish only a binary &ldquo;flood planning area&rdquo;
            boundary derived from the LEP. The NSW Planning Portal exposes flood control lot status via its
            layerintersect API, but this tells you whether a property is in a flood overlay — not how deep
            the water gets.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Victoria&apos;s Melbourne Water and regional CMAs publish flood extent data through the Victorian Floodplain
            Management Strategy. Queensland has the QRA flood mapping program. None of these are interoperable
            or accessed through a common API.
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Bushfire</h3>
          <p className="text-slate-700 leading-relaxed">
            NSW Rural Fire Service publishes Bush Fire Prone Land (BFPL) maps as spatial datasets. These are the
            statutory basis for bushfire compliance — any development on BFPL land requires a Bush Fire Attack Level
            (BAL) assessment under AS 3959. The RFS data is publicly available and updated periodically, but BAL
            estimation requires site-specific analysis of vegetation type, slope, and distance that the raw spatial
            layer doesn&apos;t provide.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Victoria&apos;s CFA publishes equivalent Bushfire Management Overlay (BMO) data. South Australia uses
            the Country Fire Service hazard mapping. Each state has different classification systems and
            assessment frameworks.
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Climate projections</h3>
          <p className="text-slate-700 leading-relaxed">
            NARCliM 2.0 (NSW/ACT Regional Climate Modelling) provides downscaled climate projections for
            southeast Australia. It offers variables including temperature, precipitation, wind, humidity,
            and derived fire weather indices under SSP2.45 and SSP3.70 scenarios. The spatial resolution
            is approximately 4km — adequate for regional analysis but requiring interpolation for property-level use.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The Bureau of Meteorology publishes historical climate data and CMIP6-based projections through
            the Climate Change in Australia portal. CSIRO provides similar data through the Australian Climate
            Service. Both are research-grade datasets designed for scientists, not for integration into
            property assessment workflows.
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Coastal</h3>
          <p className="text-slate-700 leading-relaxed">
            Coastal hazard data is primarily held by state governments. NSW publishes coastal vulnerability
            areas under the Coastal Management Act 2016, covering erosion, recession, and inundation.
            Geoscience Australia publishes national coastal exposure data at a coarser resolution. The
            granularity and currency of these datasets varies significantly by state and coastal segment.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Commercial data providers</h2>
          <p className="text-slate-700 leading-relaxed">
            Several commercial providers operate in the Australian property climate risk space. Their
            offerings differ significantly in methodology, coverage, and pricing.
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Global platforms</h3>
          <p className="text-slate-700 leading-relaxed">
            Companies like MSCI (Climate Value at Risk), Moody&apos;s (Four Twenty Seven), and S&amp;P (Trucost)
            provide global physical risk scores. These typically operate at postcode or SA2 resolution in
            Australia, using global climate models rather than regional downscaling. They&apos;re designed for
            portfolio-level screening of large institutional investors, not for property-specific assessment.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The advantage is global coverage and standardised methodology. The disadvantage is that they
            miss Australia-specific hazard nuances — particularly bushfire (a uniquely Australian risk
            profile) and the interaction between statutory planning overlays and physical hazard exposure.
            A property might score &ldquo;low flood risk&rdquo; globally but sit inside an LEP flood planning area
            that affects development potential and insurance cost.
          </p>

          <h3 className="text-xl font-semibold text-slate-900 mt-6">Australian specialists</h3>
          <p className="text-slate-700 leading-relaxed">
            Climate Valuation (XDI) provides asset-level physical risk analysis for Australian properties,
            using engineering-grade models for specific perils. Their approach is methodologically rigorous
            but typically priced for institutional clients — individual property checks are not available
            as a self-serve product.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Risk Frontiers (now part of Aon) offers catastrophe modelling for the insurance industry,
            with strong flood and cyclone models. Their data is primarily available through insurance
            industry channels rather than directly to property buyers or fund managers.
          </p>
          <p className="text-slate-700 leading-relaxed">
            CoreLogic provides some climate hazard overlays within its property data platform, primarily
            flood zone and bushfire-prone status. These are binary indicators derived from the same
            government sources described above — they don&apos;t include depth modelling, BAL estimation,
            or climate projections.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What to look for in a data provider</h2>
          <p className="text-slate-700 leading-relaxed">
            Not all climate risk data is created equal. When evaluating providers for property assessment,
            consider these dimensions:
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse mt-4">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">Dimension</th>
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">What to ask</th>
                  <th className="text-left py-3 font-semibold text-slate-900">Why it matters</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Spatial resolution</td>
                  <td className="py-3 pr-4">Property-level, SA2, or postcode?</td>
                  <td className="py-3">Two properties 500m apart can have completely different flood exposure</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Hazard coverage</td>
                  <td className="py-3 pr-4">Which perils? Flood, bushfire, heat, coastal, wind?</td>
                  <td className="py-3">Single-peril assessments miss compound risks</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Scenario basis</td>
                  <td className="py-3 pr-4">Which SSP pathways? What time horizons?</td>
                  <td className="py-3">AASB S2 requires scenario analysis, not just current state</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Methodology</td>
                  <td className="py-3 pr-4">Deterministic or AI/ML-generated?</td>
                  <td className="py-3">Deterministic models are auditable; ML models can be black boxes</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">Data currency</td>
                  <td className="py-3 pr-4">When was the underlying data last updated?</td>
                  <td className="py-3">Flood studies can be 10+ years old; LEP amendments happen quarterly</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium">Statutory integration</td>
                  <td className="py-3 pr-4">Does it include planning overlays?</td>
                  <td className="py-3">Physical risk alone misses regulatory constraints that affect property value</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">The integration gap</h2>
          <p className="text-slate-700 leading-relaxed">
            The biggest gap in the Australian market isn&apos;t the absence of data — it&apos;s the absence
            of integration. Government flood studies exist but aren&apos;t linked to bushfire maps. Climate
            projections exist but aren&apos;t spatially joined to property boundaries. Statutory planning
            overlays exist but aren&apos;t combined with physical hazard data.
          </p>
          <p className="text-slate-700 leading-relaxed">
            A property buyer checking flood risk on the NSW Planning Portal gets a binary yes/no.
            A bushfire check on the RFS website gives a separate yes/no. A NARCliM query gives
            temperature projections at 4km grid cells. None of these tell you what the compound
            risk profile is for a specific address.
          </p>
          <p className="text-slate-700 leading-relaxed">
            This is where the next generation of property intelligence platforms is emerging — combining
            these disparate sources into a single, property-level assessment that covers multiple hazards,
            includes scenario analysis, and integrates with statutory planning constraints.
          </p>
        </section>

        {/* CTA */}
        <section className="mt-12 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check the climate risk profile for any NSW property
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect combines NSW SES flood studies, RFS bushfire data, NARCliM 2.0 climate projections,
              and statutory planning overlays into a single deterministic climate risk score for any NSW address.
              Free instant assessment — no account required.
            </p>
            <TrackedLink
              href="/climate-risk"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="climate-risk-data-provider-australia"
              cta="climate_check"
            >
              Try the free climate risk check
              <ArrowRight className="w-4 h-4" />
            </TrackedLink>
          </div>

          <div className="rounded-2xl border border-slate-200 p-8 text-center">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">
              Request the climate risk data provider comparison guide
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              Detailed methodology comparison across 8 providers, with scoring framework for enterprise evaluation.
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
