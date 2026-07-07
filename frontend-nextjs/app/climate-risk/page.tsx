import type { Metadata } from 'next';
import { Thermometer, Droplets, Flame, Waves, TreePine, Sun, ArrowRight } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { ClimateRiskTool } from '@/components/tools/ClimateRiskTool';

export const metadata: Metadata = {
  title: 'Climate Risk Intelligence — PlotDetect',
  description: 'Government-mapped hazard exposure for any NSW address — flood, bushfire, coastal, fire history — plus heat and rainfall projections from NARCliM 2.0. Factual data, cited to source; not a risk rating or prediction.',
};

export default function ClimateRiskPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex items-center gap-2 mb-4">
          <Thermometer className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            Climate Risk Intelligence
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
          Every hazard on the record for a NSW address, in one place.
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          Government-mapped flood, bushfire, coastal and fire-history exposure, plus climate
          projections from NSW modelling — each cited to its source. Deterministic and factual:
          no AI interpretation, no guesswork, no risk rating.
        </p>
      </section>

      {/* Plain English: what this does and doesn't do */}
      <section className="max-w-3xl mx-auto px-6 pb-10">
        <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 space-y-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900 mb-1.5">
              What this tool does
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Checks whether your property falls within government-mapped hazard
              zones for flood, bushfire, coastal erosion, and fire history, and
              shows projected temperature and rainfall changes from NSW climate
              modelling (NARCliM 2.0), each cited to its government source and date.
            </p>
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-900 mb-1.5">
              What this tool does not do
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              It does not predict whether your property will flood, burn, or be
              damaged. It does not assess your building&apos;s construction,
              resilience, or insurability. It is not an insurance assessment,
              engineering report, or financial advice. It reports exposure to
              mapped hazards &mdash; not probability of loss.
            </p>
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-900 mb-1.5">
              Where the data comes from
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              NSW Planning Portal (flood overlays), NSW Rural Fire Service
              (bushfire prone land), SEPP Resilience &amp; Hazards 2021
              (coastal zones), NPWS (fire history), and NARCliM 2.0 via
              AdaptNSW (heat projections). All government sources, queried
              live.
            </p>
          </div>
        </div>
      </section>

      {/* Interactive tool */}
      <section className="max-w-3xl mx-auto px-6 pb-16">
        <ClimateRiskTool />
      </section>

      {/* Five hazards */}
      <section className="max-w-4xl mx-auto px-6 pb-12">
        <h2 className="text-xl font-bold text-gray-900 mb-6">
          Five hazards assessed independently
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              icon: Droplets,
              iconColor: 'text-blue-600',
              title: 'Flood',
              description: 'EPI flood overlay status, council flood study ARI depths, and satellite water detection.',
              source: 'NSW Planning Portal + SES flood studies',
              dataType: 'Current mapping',
            },
            {
              icon: Flame,
              iconColor: 'text-orange-600',
              title: 'Bushfire',
              description: 'RFS Bush Fire Prone Land classification and estimated BAL band from vegetation proximity.',
              source: 'NSW Rural Fire Service BFPL dataset',
              dataType: 'Current mapping',
            },
            {
              icon: Waves,
              iconColor: 'text-cyan-600',
              title: 'Coastal',
              description: 'SEPP Resilience and Hazards coastal zone mapping. Erosion and inundation exposure.',
              source: 'SEPP (Resilience and Hazards) 2021',
              dataType: 'Current mapping',
            },
            {
              icon: TreePine,
              iconColor: 'text-green-700',
              title: 'Fire History',
              description: 'Historical fire scar records from NPWS. Proximity to burn areas over the past 20 years.',
              source: 'NSW National Parks fire history',
              dataType: 'Historical observed',
            },
            {
              icon: Sun,
              iconColor: 'text-amber-600',
              title: 'Heat Trajectory',
              description: 'Projected temperature change to 2099 under SSP2.45 and SSP3.70 scenarios. 4km grid resolution.',
              source: 'NARCliM 2.0 (ACCESS-ESM1-5 GCM)',
              dataType: 'Climate projection',
            },
          ].map(({ icon: Icon, iconColor, title, description, source, dataType }) => (
            <div key={title} className="rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-2">
                <Icon className={`w-5 h-5 ${iconColor}`} />
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                  dataType === 'Climate projection'
                    ? 'bg-purple-50 text-purple-700'
                    : dataType === 'Historical observed'
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-green-50 text-green-700'
                }`}>
                  {dataType}
                </span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed mb-2">{description}</p>
              <p className="text-xs text-gray-400">{source}</p>
            </div>
          ))}

          {/* Compound card */}
          <div className="rounded-xl border border-teal-200 bg-teal-50 p-5">
            <Thermometer className="w-5 h-5 text-teal-600 mb-2" />
            <h3 className="font-semibold text-gray-900 mb-1">Compound Interactions</h3>
            <p className="text-sm text-gray-600 leading-relaxed mb-2">
              Bushfire + extreme heat. Flood + coastal inundation. Where mapped hazards overlap
              at an address, the report names the overlapping pair and the recognised interaction.
            </p>
            <p className="text-xs text-teal-700">Overlapping hazard categories, flagged factually</p>
          </div>
        </div>
      </section>

      {/* Sample output */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          What you get: sample assessment
        </h2>
        <p className="text-sm text-gray-500 mb-6 max-w-2xl">
          This is a real output for a specific property near Windsor, Hawkesbury LGA
          — one of the most multi-hazard-exposed regions in NSW. Every number comes
          from a government dataset. Nothing is estimated or approximated.
        </p>

        {/* Sample header — neutral, factual, no verdict/traffic-light */}
        <div className="rounded-xl border border-gray-200 overflow-hidden mb-6">
          <div className="bg-gray-50 border-b border-gray-100 px-6 py-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Climate &amp; hazard exposure
              </p>
              <p className="text-lg font-semibold text-gray-900">
                4 of 5 mapped hazard categories present at this address
              </p>
              <p className="text-sm text-gray-500 mt-1">Exposure to published data — not a risk rating or prediction.</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">Near Windsor, Hawkesbury LGA</p>
              <p className="text-xs text-gray-400 mt-0.5">Methodology v1.0</p>
            </div>
          </div>

          {/* Per-hazard breakdown */}
          <div className="divide-y divide-gray-100">
            {/* Flood */}
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Droplets className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-gray-900">Flood</span>
                </div>
                <span className="text-xs px-2 py-0.5 rounded border border-gray-300 bg-gray-100 text-gray-700">
                  Present
                </span>
              </div>
              <p className="text-sm text-gray-500 ml-6">
                Property is within a flood planning area (EPI overlay). The Hawkesbury-Nepean
                is one of the highest flood-risk catchments in Australia — 90,000+ people
                live below the probable maximum flood level.
              </p>
              <p className="text-xs text-gray-400 ml-6 mt-1">
                Source: NSW Planning Portal EPI Flood layers
              </p>
            </div>

            {/* Bushfire */}
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-600" />
                  <span className="text-sm font-medium text-gray-900">Bushfire</span>
                </div>
                <span className="text-xs px-2 py-0.5 rounded border border-gray-300 bg-gray-100 text-gray-700">
                  Present
                </span>
              </div>
              <p className="text-sm text-gray-500 ml-6">
                Bush Fire Prone Land — the property is within an area mapped by the NSW Rural
                Fire Service. Construction must comply with AS 3959 and may require a formal
                BAL assessment before DA lodgement.
              </p>
              <p className="text-xs text-gray-400 ml-6 mt-1">
                Source: NSW RFS Bushfire Prone Land Map
              </p>
            </div>

            {/* Fire History */}
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <TreePine className="w-4 h-4 text-green-700" />
                  <span className="text-sm font-medium text-gray-900">Fire History</span>
                </div>
                <span className="text-xs px-2 py-0.5 rounded border border-gray-300 bg-gray-100 text-gray-700">
                  Present
                </span>
              </div>
              <p className="text-sm text-gray-500 ml-6">
                2 recorded fire events at this location. Areas with repeated burn history face
                higher risk of future fire — vegetation regrowth creates fuel loads that
                accumulate over 5-10 year cycles.
              </p>
              <p className="text-xs text-gray-400 ml-6 mt-1">
                Source: NSW National Parks &amp; Wildlife Service fire history dataset
              </p>
            </div>

            {/* Heat Trajectory */}
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Sun className="w-4 h-4 text-amber-600" />
                  <span className="text-sm font-medium text-gray-900">Heat Trajectory</span>
                </div>
                <span className="text-xs px-2 py-0.5 rounded border border-gray-300 bg-gray-100 text-gray-700">
                  Present
                </span>
              </div>
              <p className="text-sm text-gray-500 ml-6">
                Days over 35°C projected to increase from 14/yr to 52/yr by 2090 under high
                emissions (SSP3-7.0). Western Sydney is one of the fastest-heating regions in
                the country — Penrith already records the highest urban temperatures in Australia.
              </p>
              <div className="ml-6 mt-2 grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-gray-50 rounded-lg px-3 py-2">
                  <p className="text-xs text-gray-400">Baseline</p>
                  <p className="text-sm font-semibold text-gray-900">14 days/yr</p>
                </div>
                <div className="bg-gray-50 rounded-lg px-3 py-2">
                  <p className="text-xs text-gray-400">2050</p>
                  <p className="text-sm font-semibold text-gray-900">28 days/yr</p>
                </div>
                <div className="bg-gray-50 rounded-lg px-3 py-2">
                  <p className="text-xs text-gray-400">2070</p>
                  <p className="text-sm font-semibold text-gray-900">39 days/yr</p>
                </div>
                <div className="bg-gray-50 rounded-lg px-3 py-2">
                  <p className="text-xs text-gray-400">2090</p>
                  <p className="text-sm font-semibold text-gray-900">52 days/yr</p>
                </div>
              </div>
              <p className="text-xs text-gray-400 ml-6 mt-2">
                Source: NARCliM 2.0 (AdaptNSW), ACCESS-ESM1.5, SSP3-7.0, 4km resolution
              </p>
            </div>

            {/* Coastal */}
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Waves className="w-4 h-4 text-cyan-600" />
                  <span className="text-sm font-medium text-gray-900">Coastal</span>
                </div>
                <span className="text-xs px-2 py-0.5 rounded border border-gray-200 bg-white text-gray-400">
                  Not present
                </span>
              </div>
              <p className="text-sm text-gray-500 ml-6">
                Not within any SEPP (Resilience and Hazards) 2021 coastal hazard zone.
                Inland properties are not exposed to coastal erosion or tidal inundation —
                but may still face riverine flood risk (assessed separately above).
              </p>
              <p className="text-xs text-gray-400 ml-6 mt-1">
                Source: SEPP (Resilience and Hazards) 2021 coastal management layers
              </p>
            </div>
          </div>

          {/* Overlapping hazard categories — factual, no scoring */}
          <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Overlapping hazard categories at this address
            </p>
            <div className="space-y-1.5">
              <p className="text-sm text-gray-700">Bushfire + Fire History — repeated burn history in a bushfire-prone area, accumulated fuel loads</p>
              <p className="text-sm text-gray-700">Bushfire + Heat — rising temperatures dry vegetation and extend fire seasons</p>
              <p className="text-sm text-gray-700">Flood + Heat — a warmer atmosphere holds more moisture, driving more intense convective storms</p>
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Climate impacts can cascade and compound across systems (IPCC AR6 WGII, high confidence).
            </p>
          </div>
        </div>

        {/* Additional climate projections */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          <div className="rounded-xl border border-gray-200 p-5">
            <Thermometer className="w-4 h-4 text-gray-500 mb-2" />
            <p className="text-sm font-medium text-gray-900 mb-1">Mean Temperature Change</p>
            <p className="text-2xl font-bold text-gray-900">+2.1°C</p>
            <p className="text-xs text-gray-500 mt-1">
              Projected increase in mean near-surface temperature by 2090 under SSP3-7.0.
              This shifts the entire distribution — what is currently a &ldquo;hot year&rdquo;
              becomes the new average.
            </p>
            <p className="text-xs text-gray-400 mt-2">NARCliM 2.0 · ACCESS-ESM1.5 · 4km grid</p>
          </div>

          <div className="rounded-xl border border-gray-200 p-5">
            <Droplets className="w-4 h-4 text-blue-500 mb-2" />
            <p className="text-sm font-medium text-gray-900 mb-1">Precipitation Trend</p>
            <p className="text-2xl font-bold text-gray-900">-0.3 mm/day</p>
            <p className="text-xs text-gray-500 mt-1">
              A drying trend means less frequent rainfall — but when rain does come, it tends
              to be more intense. This paradox increases both drought and flash flood risk
              simultaneously.
            </p>
            <p className="text-xs text-gray-400 mt-2">NARCliM 2.0 · ACCESS-ESM1.5 · 4km grid</p>
          </div>
        </div>

        {/* How to read this */}
        <div className="rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">How to read this</h3>
          <div className="space-y-2 text-sm text-gray-600">
            <p>
              <strong className="text-gray-900">Exposure, not a rating:</strong> the report lists which
              government-mapped hazards apply to the address and the published climate projections for
              the location. It is not scored, ranked, or colour-coded into a risk verdict — a coastal
              town can face fewer heat days than a hot western suburb, so a single headline number would
              mislead.
            </p>
            <p>
              <strong className="text-gray-900">Deterministic:</strong> the same address always returns
              the same result. No AI interpretation, no machine-learning model, no probabilistic element
              — a direct function of which government spatial layers intersect the property and the
              NARCliM projection at the nearest 4km grid cell.
            </p>
            <p>
              <strong className="text-gray-900">Not a prediction:</strong> it reports hazard
              <em> exposure</em>, not the probability of loss. Property-specific factors (construction
              type, floor height, vegetation management) are not included.
            </p>
          </div>
        </div>
      </section>

      {/* The numbers behind the score */}
      <section className="border-y border-gray-100 bg-gray-50 py-12 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Why these hazards matter — the national picture
          </h2>
          <p className="text-sm text-gray-500 mb-6 max-w-2xl">
            These are not PlotDetect numbers. They are from APRA, the Insurance Council of Australia,
            and the IPCC — the institutions that set prudential standards and measure catastrophe losses.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              {
                stat: '+240%',
                label: 'Projected flood loss increase by 2050',
                detail: 'Flood is the most climate-sensitive weather peril. 50% of all losses are concentrated in just 10% of regions.',
                source: 'APRA Mind the Gap 2026, p.14',
              },
              {
                stat: '1 in 4',
                label: 'Households uninsured by 2050',
                detail: 'Up from 1 in 7 today. That is roughly 40,000 households losing home insurance coverage every year.',
                source: 'APRA Mind the Gap 2026, p.4',
              },
              {
                stat: '$16B',
                label: 'Annual weather losses by 2050',
                detail: 'Up from $7B today under current policies. A 129% increase in national weather-related losses in 26 years.',
                source: 'APRA Mind the Gap 2026, p.4',
              },
              {
                stat: '7.2%',
                label: 'Annual home insurance premium growth',
                detail: 'Versus wage growth of 3.1%. Premiums are rising more than twice as fast as incomes — and NSW levies add ~18% on top.',
                source: 'APRA Mind the Gap 2026, p.7',
              },
              {
                stat: '$164–226B',
                label: 'Coastal infrastructure exposed to 1.1m SLR',
                detail: 'Including 187,000–274,000 residential buildings and 27,000–35,000km of roads.',
                source: 'IPCC AR6 WGII Ch11, Table Box 11.6.2',
              },
              {
                stat: '77%',
                label: 'Severe flood risk properties uninsured',
                detail: '186,000 of the 242,000 highest-risk residential dwellings currently lack flood insurance.',
                source: 'ICA Catastrophe Resilience 2024-25, p.3',
              },
            ].map(({ stat, label, detail, source }) => (
              <div key={label} className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="text-2xl font-bold text-gray-900 mb-1">{stat}</p>
                <p className="text-sm font-medium text-gray-700 mb-2">{label}</p>
                <p className="text-xs text-gray-500 leading-relaxed">{detail}</p>
                <p className="text-xs text-gray-400 mt-2">{source}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why it matters */}
      <section className="bg-slate-900 text-white py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold mb-6">Why hazard exposure matters now</h2>
          <div className="space-y-6">
            {[
              {
                title: 'Insurance repricing',
                description: 'Insurers are repricing property risk based on climate exposure. Properties with unassessed hazards face premium increases or coverage withdrawal.',
              },
              {
                title: 'APRA climate risk self-assessment',
                description: 'APRA requires financial institutions to assess climate risk exposure. Property portfolios need hazard data at the individual address level.',
              },
              {
                title: 'Pre-purchase due diligence',
                description: 'A property in a flood zone that is also on bush fire prone land with projected heat increase has a fundamentally different risk profile. Buyers need to see the compound picture.',
              },
            ].map(({ title, description }) => (
              <div key={title}>
                <h3 className="font-semibold text-white mb-1">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What is available now */}
      <section className="max-w-3xl mx-auto px-6 py-16">
        <h2 className="text-xl font-bold text-gray-900 mb-6">What is available now</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="rounded-xl border-2 border-teal-500 p-6">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-teal-50 text-teal-700 mb-3 inline-block">
              Live now
            </span>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Hazard exposure summary</h3>
            <p className="text-2xl font-bold text-teal-600 mb-2">Free</p>
            <p className="text-sm text-gray-500 leading-relaxed">
              Every government-mapped hazard for any NSW address — flood, bushfire, coastal, fire
              history — plus NARCliM climate projections, each cited to source. Deterministic: the
              same address always returns the same result.
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 p-6">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-600 mb-3 inline-block">
              Coming soon
            </span>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Climate Risk Report</h3>
            <p className="text-2xl font-bold text-gray-900 mb-2">$99</p>
            <p className="text-sm text-gray-500 leading-relaxed mb-3">
              Full NARCliM trajectories, overlapping-hazard detail, and a source-cited PDF
              for pre-purchase and due-diligence research.
            </p>
            <p className="text-xs text-gray-400">
              Available after PlotDetect Pty Ltd incorporation and professional indemnity insurance.
            </p>
            <a
              href="mailto:hello@plotdetect.com.au?subject=Climate%20Risk%20Report%20interest"
              className="inline-block mt-3 text-sm text-teal-600 font-medium hover:text-teal-700 transition-colors"
            >
              Register interest →
            </a>
          </div>
        </div>
      </section>

      {/* Data provenance */}
      <section className="border-y border-gray-100 bg-gray-50 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Data provenance</h2>
          <div className="space-y-3 text-sm text-gray-600">
            <p>
              <strong>NARCliM 2.0</strong> — NSW and ACT Regional Climate Modelling project.
              SSP2.45 (intermediate) and SSP3.70 (high emissions) scenarios.
              ACCESS-ESM1-5 global climate model downscaled to 4km grid resolution.
            </p>
            <p>
              <strong>NSW Rural Fire Service</strong> — Bush Fire Prone Land dataset, updated annually.
            </p>
            <p>
              <strong>NSW Planning Portal</strong> — EPI flood overlay data queried live via layerintersect API.
            </p>
            <p>
              <strong>NPWS</strong> — Historical fire scar polygons from National Parks and Wildlife Service.
            </p>
            <p>
              <strong>SEPP (Resilience and Hazards) 2021</strong> — Coastal management SEPP zones.
            </p>
          </div>
        </div>
      </section>

      {/* CTA — scroll to tool */}
      <section className="max-w-3xl mx-auto px-6 py-12 text-center">
        <a
          href="#tool-input"
          className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          Check any NSW address
          <ArrowRight className="w-4 h-4" />
        </a>
      </section>

      {/* Legal disclaimer */}
      <section className="border-t border-gray-100 bg-gray-50 py-8 px-6">
        <div className="max-w-3xl mx-auto">
          <p className="text-xs text-gray-400 leading-relaxed">
            This hazard-exposure summary is provided for informational purposes only and does not constitute
            financial, insurance, legal, or property advice. It reflects publicly available
            government spatial data and climate projection modelling — it is not a professional
            risk assessment and should not be relied upon as a substitute for independent expert
            advice. Always consult qualified professionals before making property, insurance, or
            investment decisions. PlotDetect does not provide financial product advice within the
            meaning of the Corporations Act 2001 (Cth) s766B. Past hazard exposure does not
            guarantee future outcomes. Climate projections are modelled scenarios, not predictions.
          </p>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
