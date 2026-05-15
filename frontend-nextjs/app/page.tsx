import Link from 'next/link';
import {
  Droplets, Flame, FileCheck, Building2, Radar, Sun, Moon, Satellite,
  ShieldCheck, Map, BarChart3, Thermometer, ArrowRight,
} from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

/* ------------------------------------------------------------------ */
/*  Tool card data                                                     */
/* ------------------------------------------------------------------ */

const TOOLS = [
  {
    href: '/reports/flood',
    title: 'Flood Risk Check',
    tagline: 'How deep does it flood — not just whether it floods.',
    badge: 'Free + $49',
    icon: Droplets,
    iconColor: 'text-blue-600',
  },
  {
    href: '/reports/bushfire',
    title: 'Bushfire Pre-Screen',
    tagline: 'Bush Fire Prone Land status, BAL band estimate, and CDC pathway.',
    badge: 'Free + $29',
    icon: Flame,
    iconColor: 'text-orange-600',
  },
  {
    href: '/reports/conveyancing',
    title: 'Conveyancing Disclosure',
    tagline: 'LEP controls, overlays, heritage, SEPP — the planning check your conveyancer should do.',
    badge: 'Free + $49',
    icon: FileCheck,
    iconColor: 'text-emerald-600',
  },
  {
    href: '/reports/granny-flat',
    title: 'Granny Flat Yield Predictor',
    tagline: 'SEPP eligibility, satellite structure detection, and rental yield estimate.',
    badge: 'Free + $49',
    icon: Building2,
    iconColor: 'text-teal-600',
  },
  {
    href: '/reports/threat-radar',
    title: 'Neighbour Threat Radar',
    tagline: 'Every DA and CDC within 500m — with weekly email alerts for new lodgements.',
    badge: 'Free + $9/mo',
    icon: Radar,
    iconColor: 'text-violet-600',
  },
  {
    href: '/reports/shadow',
    title: 'Shadow Risk Analyser',
    tagline: 'Shadow modelled from the maximum-height building envelope on ADG solar access test dates.',
    badge: '$29',
    icon: Moon,
    iconColor: 'text-slate-600',
  },
  {
    href: '/reports/solar-yield',
    title: 'Rooftop Solar Yield',
    tagline: 'Roof geometry, orientation, and estimated annual generation from satellite and BoM data.',
    badge: '$19',
    icon: Sun,
    iconColor: 'text-amber-500',
  },
  {
    href: '/reports/pre-da-history',
    title: 'Pre-DA Site History',
    tagline: 'Eight years of satellite change detection cross-referenced with DA records and heritage overlays.',
    badge: '$49',
    icon: Satellite,
    iconColor: 'text-indigo-600',
  },
];

/* ------------------------------------------------------------------ */
/*  Data sources                                                       */
/* ------------------------------------------------------------------ */

const DATA_SOURCES = [
  'NSW Planning Portal',
  'Bureau of Meteorology',
  'European Space Agency',
  'NSW Rural Fire Service',
  'Copernicus EMS',
  'NARCliM 2.0',
  'Spatial Services NSW',
];

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function HomePage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav maxWidth="max-w-6xl" />

      {/* ── Hero ── */}
      <section className="px-6 pt-20 pb-16 max-w-3xl mx-auto text-center">
        <h1 className="text-4xl sm:text-5xl font-bold leading-tight text-gray-900 mb-4">
          Stop guessing.{' '}
          <span className="text-teal-600">Start with the data.</span>
        </h1>
        <p className="text-gray-500 text-lg mb-10 max-w-xl mx-auto">
          Flood depth, bushfire risk, planning controls, and climate projections
          for any NSW address. Free instant checks. Professional reports from $19.
        </p>
        <div className="flex flex-wrap justify-center gap-2.5">
          {TOOLS.slice(0, 5).map(({ href, title, icon: Icon, iconColor }) => (
            <Link
              key={href}
              href={href}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:border-gray-300 hover:shadow-sm transition-all"
            >
              <Icon className={`w-4 h-4 ${iconColor}`} />
              {title}
            </Link>
          ))}
          <Link
            href="/reports"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-teal-700 bg-teal-50 border border-teal-200 rounded-lg hover:bg-teal-100 transition-colors"
          >
            All tools
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </section>

      {/* ── Verify — full-width showcase ── */}
      <section className="bg-gray-50 border-y border-gray-100 py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-5 h-5 text-teal-600" />
            <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
              Verify — Compliance Engine
            </span>
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Every provision. Every clause. Every PDF page.
          </h2>
          <p className="text-gray-500 max-w-2xl mb-8">
            Design compliant from the start. Verify extracts the exact DCP provisions,
            SEPP standards, and LEP controls that apply to your property and development type
            — with clause citations and PDF page references.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Inner West tier */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-teal-50 text-teal-700">
                  Full DCP coverage
                </span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Inner West Council</h3>
              <ul className="space-y-1.5 text-sm text-gray-600">
                <li>~11,000 provisions across 3 former councils</li>
                <li>Precinct-specific filtering</li>
                <li>DA Mode with triage and annotation</li>
                <li>SEE scaffold export</li>
                <li>Development type filtering</li>
                <li>PDF page citations for every clause</li>
              </ul>
            </div>

            {/* 28 LGA tier */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                  Numeric controls
                </span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">28 NSW councils</h3>
              <ul className="space-y-1.5 text-sm text-gray-600">
                <li>Setbacks, parking rates, landscaping standards</li>
                <li>Clause citations from source DCP</li>
                <li>Useful for pre-DA checks and CDC screening</li>
                <li>Coverage expanding with each LGA onboarding</li>
              </ul>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/assessment"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
            >
              Try Verify — free
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/how-it-works"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-gray-600 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all"
            >
              How the data works
            </Link>
          </div>
        </div>
      </section>

      {/* ── Property intelligence tools (8 cards) ── */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Property intelligence tools
          </h2>
          <p className="text-gray-500 mb-8 max-w-xl">
            Free instant checks reveal risk. Professional reports resolve it.
            No account required.
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {TOOLS.map(({ href, title, tagline, badge, icon: Icon, iconColor }) => (
              <Link
                key={href}
                href={href}
                className="group block bg-white rounded-xl border border-gray-200 p-5 hover:border-gray-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <Icon className={`w-5 h-5 ${iconColor} shrink-0 mt-0.5`} />
                  <span className={`shrink-0 text-[11px] font-medium px-2 py-0.5 rounded-full ${
                    badge.startsWith('Free')
                      ? 'bg-teal-50 text-teal-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {badge}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 text-sm mb-1 group-hover:text-teal-700 transition-colors">
                  {title}
                </h3>
                <p className="text-xs text-gray-500 leading-relaxed">{tagline}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Climate intelligence ── */}
      <section className="bg-slate-900 text-white py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-2 mb-3">
            <Thermometer className="w-5 h-5 text-teal-400" />
            <span className="text-xs font-semibold uppercase tracking-widest text-teal-400">
              Climate Risk Intelligence
            </span>
          </div>
          <h2 className="text-3xl font-bold mb-3">
            Property risk is changing. We measure it.
          </h2>
          <p className="text-slate-400 max-w-2xl mb-10">
            NARCliM 2.0 climate projections combined with statutory planning overlays
            and satellite hazard detection. Deterministic composite scoring — no AI interpretation.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                title: 'Flood',
                description: 'Modelled depth at ARI return periods — not just "flood zone."',
                source: 'NSW SES + council flood studies',
              },
              {
                title: 'Bushfire',
                description: 'BAL band estimation, CDC pathway assessment, and 10/50 vegetation clearing.',
                source: 'NSW Rural Fire Service',
              },
              {
                title: 'Climate Projections',
                description: 'Heat stress and precipitation change trajectories to 2099.',
                source: 'NARCliM 2.0 (SSP2.45 + SSP3.70)',
              },
              {
                title: 'Compound Hazards',
                description: 'Bushfire + heat, flood + coastal — interaction scoring for combined risk.',
                source: 'Composite hazard model',
              },
            ].map(({ title, description, source }) => (
              <div key={title} className="border border-slate-700 rounded-xl p-5">
                <h3 className="font-semibold text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed mb-3">{description}</p>
                <p className="text-xs text-slate-500">{source}</p>
              </div>
            ))}
          </div>

          <p className="text-xs text-slate-500 mt-8">
            Climate Risk Score — free composite assessment for any NSW address.
            Climate Risk Report ($99) available after PlotDetect Pty Ltd incorporation and professional indemnity insurance.
          </p>
        </div>
      </section>

      {/* ── Scout + Validate ── */}
      <section className="py-16 px-6 border-b border-gray-100">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-3">
              <Map className="w-5 h-5 text-blue-600" />
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                Scout
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Click any property in NSW
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed mb-4">
              Interactive map explorer with zone overlays, lot boundaries, heritage overlays,
              and planning controls. Free, no account required.
            </p>
            <Link
              href="/scout"
              className="text-sm text-blue-600 font-medium hover:text-blue-700 transition-colors"
            >
              Open Scout →
            </Link>
          </div>

          <div className="rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-5 h-5 text-violet-600" />
              <span className="text-xs font-semibold uppercase tracking-widest text-violet-600">
                Validate
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Track DA patterns and approval rates
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed mb-4">
              DA analytics across 128 NSW councils — approval rates, processing times,
              common refusal reasons, and trend analysis.
            </p>
            <Link
              href="/validate"
              className="text-sm text-violet-600 font-medium hover:text-violet-700 transition-colors"
            >
              Open Validate →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Who uses PlotDetect ── */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">
            Built for how you actually work
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                title: 'Homebuyers',
                description: 'Check hazards before you bid. Free instant checks, detailed reports for shortlisted properties.',
                href: '/reports',
                cta: 'Run a free check',
              },
              {
                title: 'Conveyancers',
                description: 'Pre-exchange planning disclosure in 30 seconds. LEP, DCP, heritage, flood, bushfire — one report.',
                href: '/for/conveyancers',
                cta: 'See conveyancing tools',
              },
              {
                title: 'Buyers Agents',
                description: 'Satellite hazard screening for shortlists. Threat Radar monitoring for your portfolio.',
                href: '/for/buyers-agents',
                cta: 'Professional tools',
              },
              {
                title: 'Builders & Planners',
                description: 'Compliance checking with Verify. Free embed program for your website.',
                href: '/partner',
                cta: 'Embed program',
              },
            ].map(({ title, description, href, cta }) => (
              <Link
                key={title}
                href={href}
                className="group block rounded-xl border border-gray-200 p-5 hover:border-gray-300 hover:shadow-sm transition-all"
              >
                <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed mb-3">{description}</p>
                <span className="text-sm text-teal-600 font-medium group-hover:text-teal-700 transition-colors">
                  {cta} →
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Data sources strip ── */}
      <section className="border-y border-gray-100 bg-gray-50 py-8 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-xs text-gray-400 uppercase tracking-widest mb-4 font-medium">
            Live government and scientific data sources
          </p>
          <p className="text-sm text-gray-500">
            {DATA_SOURCES.join(' \u00B7 ')}
          </p>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
