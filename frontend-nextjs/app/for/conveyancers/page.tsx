import type { Metadata } from 'next';
import Link from 'next/link';
import { FileCheck, Droplets, Flame, ShieldCheck, ArrowRight } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'For Conveyancers — PlotDetect',
  description: 'Pre-exchange planning disclosure in 30 seconds. LEP controls, environmental overlays, heritage, flood depth, bushfire — from live government data.',
};

export default function ConveyancersPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex items-center gap-2 mb-4">
          <FileCheck className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            For conveyancers
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
          Pre-exchange planning disclosure in 30 seconds
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          Your client is about to exchange. The s10.7 certificate covers zoning and overlays,
          but not flood depth, not DCP setbacks, not heritage conservation area boundaries,
          not bushfire BAL. PlotDetect checks all of it — from live government data, instantly.
        </p>
      </section>

      {/* What it surfaces that s10.7 misses */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <h2 className="text-xl font-bold text-gray-900 mb-6">
          What PlotDetect surfaces that s10.7 misses
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            {
              icon: Droplets,
              iconColor: 'text-blue-600',
              title: 'Flood depth modelling',
              description: `Not just "flood zone" — modelled depth at ARI return periods where a council flood study has been ingested (${COVERAGE_DISPLAY.floodStudies} studies: Hawkesbury, Tweed, Wollongong, Redbank). Elsewhere, the mapped flood planning area.`,
            },
            {
              icon: Flame,
              iconColor: 'text-orange-600',
              title: 'Bushfire BAL estimation',
              description: 'Bush Fire Prone Land status and estimated BAL band. Required for any new dwelling in a bushfire-prone area.',
            },
            {
              icon: ShieldCheck,
              iconColor: 'text-teal-600',
              title: 'DCP setback controls',
              description: `Front, side, and rear setbacks from the applicable DCP — with clause citations. ${COVERAGE_DISPLAY.dcpSetbackTripleCouncils} councils hold all three.`,
            },
            {
              icon: FileCheck,
              iconColor: 'text-emerald-600',
              title: 'Heritage and overlays',
              description: 'Heritage conservation area boundaries, environmental overlays, acid sulfate soils, and SEPP provisions.',
            },
          ].map(({ icon: Icon, iconColor, title, description }) => (
            <div key={title} className="rounded-xl border border-gray-200 p-5">
              <Icon className={`w-5 h-5 ${iconColor} mb-2`} />
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Trust — can you stand behind it */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-6">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-5 h-5 text-teal-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Can you put this in front of a client?
            </h2>
          </div>
          <p className="text-sm text-gray-600 leading-relaxed">
            Every figure in the report names where it came from &mdash; a council
            planning control carries the clause it was read from, and a mapping result
            names its dataset: zoning and SEPP from the NSW Planning Portal, flood
            and hazard mapping from Spatial Services NSW and council flood studies,
            bushfire from the NSW Rural Fire Service. Figures are indicative and
            computed from published planning controls, not advice &mdash; the report
            sits alongside the s10.7 certificate and a qualified town planner, not in
            place of them.{' '}
            <Link
              href="/how-it-works"
              className="text-teal-700 hover:text-teal-800 underline underline-offset-2"
            >
              See how each check is sourced
            </Link>
            .
          </p>
        </div>
      </section>

      {/* Pricing as disbursement */}
      <section className="bg-gray-50 border-y border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Pricing</h2>
          <p className="text-gray-500 mb-6">
            Reports are one-off purchases, passed through as a disbursement.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-2xl font-bold text-gray-900">Free</p>
              <p className="text-sm text-gray-500 mt-1">Instant planning check</p>
              <p className="text-xs text-gray-400 mt-2">
                Zone, height, FSR, overlays, flood zone status, heritage — the quick check.
              </p>
            </div>
            <div className="bg-white rounded-xl border-2 border-teal-500 p-5">
              <p className="text-2xl font-bold text-gray-900">$49</p>
              <p className="text-sm text-gray-500 mt-1">Conveyancing report</p>
              <p className="text-xs text-gray-400 mt-2">
                Full planning disclosure PDF. LEP controls, DCP setbacks, environmental overlays, heritage, flood depth, bushfire.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-2xl font-bold text-gray-900">$149</p>
              <p className="text-sm text-gray-500 mt-1">Full property bundle</p>
              <p className="text-xs text-gray-400 mt-2">
                All standard reports for one address — conveyancing, flood, bushfire, granny flat, shadow, solar, site history.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <div className="rounded-xl border border-teal-200 bg-teal-50 p-8 text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Run 5 free reports on your current pipeline
          </h2>
          <p className="text-sm text-gray-600 mb-6 max-w-md mx-auto">
            Enter any NSW address and get the instant planning check — free, no account required.
            See what your clients should know before they exchange.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/reports/conveyancing"
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
            >
              Try the conveyancing check
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="mailto:hello@plotdetect.com.au?subject=Conveyancing%20enquiry"
              className="inline-flex items-center gap-2 px-6 py-2.5 text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 transition-all"
            >
              hello@plotdetect.com.au
            </a>
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-6 text-center">
          Data sourced from NSW Planning Portal, Spatial Services NSW, Bureau of Meteorology,
          NSW Rural Fire Service, and council flood studies. Results are indicative — always
          confirm with a section 10.7 certificate and qualified town planner.
        </p>
      </section>

      <SiteFooter />
    </main>
  );
}
