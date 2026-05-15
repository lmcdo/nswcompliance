import type { Metadata } from 'next';
import Link from 'next/link';
import { Thermometer, Droplets, Flame, Waves, TreePine, Sun, ArrowRight } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'Climate Risk Intelligence — PlotDetect',
  description: 'Composite climate risk scoring for any NSW address. Flood, bushfire, coastal erosion, fire history, and heat projections from NARCliM 2.0.',
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
          Property risk is changing. We measure it.
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          The only NSW property platform combining statutory planning data with
          climate projection modelling. Deterministic composite scoring — no AI interpretation,
          no guesswork.
        </p>
      </section>

      {/* Five hazards */}
      <section className="max-w-4xl mx-auto px-6 pb-12">
        <h2 className="text-xl font-bold text-gray-900 mb-6">
          Five hazards. One composite score.
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              icon: Droplets,
              iconColor: 'text-blue-600',
              title: 'Flood',
              description: 'EPI flood overlay status, council flood study ARI depths, and satellite water detection.',
              source: 'NSW Planning Portal + SES flood studies',
            },
            {
              icon: Flame,
              iconColor: 'text-orange-600',
              title: 'Bushfire',
              description: 'RFS Bush Fire Prone Land classification and estimated BAL band from vegetation proximity.',
              source: 'NSW Rural Fire Service BFPL dataset',
            },
            {
              icon: Waves,
              iconColor: 'text-cyan-600',
              title: 'Coastal',
              description: 'SEPP Resilience and Hazards coastal zone mapping. Erosion and inundation exposure.',
              source: 'SEPP (Resilience and Hazards) 2021',
            },
            {
              icon: TreePine,
              iconColor: 'text-green-700',
              title: 'Fire History',
              description: 'Historical fire scar records from NPWS. Proximity to burn areas over the past 20 years.',
              source: 'NSW National Parks fire history',
            },
            {
              icon: Sun,
              iconColor: 'text-amber-600',
              title: 'Heat Trajectory',
              description: 'Projected temperature change to 2099 under SSP2.45 and SSP3.70 scenarios. 4km grid resolution.',
              source: 'NARCliM 2.0 (ACCESS-ESM1-5 GCM)',
            },
          ].map(({ icon: Icon, iconColor, title, description, source }) => (
            <div key={title} className="rounded-xl border border-gray-200 p-5">
              <Icon className={`w-5 h-5 ${iconColor} mb-2`} />
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
              Bushfire + extreme heat. Flood + coastal inundation. Hazards that overlap
              create disproportionate risk — the composite score captures these interactions.
            </p>
            <p className="text-xs text-teal-700">Interaction bonus scoring model</p>
          </div>
        </div>
      </section>

      {/* Why it matters */}
      <section className="bg-slate-900 text-white py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold mb-6">Why climate risk scoring matters now</h2>
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
            <h3 className="text-lg font-bold text-gray-900 mb-2">Climate Risk Score</h3>
            <p className="text-2xl font-bold text-teal-600 mb-2">Free</p>
            <p className="text-sm text-gray-500 leading-relaxed">
              Composite score out of 10 for any NSW address. Five hazard categories with
              compound interaction analysis. Deterministic — same address always produces
              the same score.
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 p-6">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-600 mb-3 inline-block">
              Coming soon
            </span>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Climate Risk Report</h3>
            <p className="text-2xl font-bold text-gray-900 mb-2">$99</p>
            <p className="text-sm text-gray-500 leading-relaxed mb-3">
              Full NARCliM trajectories, compound hazard analysis, and professional PDF.
              Suitable for insurance assessments and property due diligence.
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

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-12 text-center">
        <Link
          href="/reports"
          className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          Check any NSW address
          <ArrowRight className="w-4 h-4" />
        </Link>
      </section>

      <SiteFooter />
    </main>
  );
}
