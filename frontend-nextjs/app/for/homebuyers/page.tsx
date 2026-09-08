import type { Metadata } from 'next';
import Link from 'next/link';
import {
  Droplets, Flame, FileCheck, Building2, Home, Scissors, Sun, Radar,
  Satellite, ArrowRight, ShieldCheck,
} from 'lucide-react';
import { HomeNav } from '@/components/marketing/HomeNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'For Homeowners & Buyers — PlotDetect',
  description:
    'Before you buy or build in NSW, check the address. Flood, bushfire, heritage, what you can build, and what is happening nearby — free instant checks on live government data.',
};

/* ------------------------------------------------------------------ */
/*  Consumer jobs-to-be-done, grouped by the question being asked      */
/* ------------------------------------------------------------------ */

const SECTIONS = [
  {
    heading: 'Before you buy',
    subtitle: 'What are you actually buying — and what could stop your plans?',
    tools: [
      {
        icon: Droplets, iconColor: 'text-blue-600', iconBg: 'bg-blue-500/10',
        title: 'Flood Screening', badge: 'Free + $49',
        question: 'Does it flood — and how deep?',
        answer: 'Flood status plus modelled depth at different return periods, cross-referenced from council flood studies and satellite records — not just a "flood zone" yes/no.',
        href: '/reports/flood',
      },
      {
        icon: Flame, iconColor: 'text-orange-600', iconBg: 'bg-orange-500/10',
        title: 'Bushfire Pre-Screen', badge: 'Free',
        question: 'Is it bushfire-prone, and what does that mean for building?',
        answer: 'Bush Fire Prone Land category, an estimated BAL band, and whether a formal bushfire (BAL) assessment from an accredited practitioner will be needed before you can build.',
        href: '/reports/bushfire',
      },
      {
        icon: FileCheck, iconColor: 'text-emerald-600', iconBg: 'bg-emerald-500/10',
        title: 'Planning Disclosure', badge: 'Free + $49',
        question: 'What planning controls, overlays and heritage apply?',
        answer: 'Zone, height, floor space ratio, heritage, environmental overlays and the SEPPs that apply — the planning picture a section 10.7 certificate leaves out.',
        href: '/reports/conveyancing',
      },
      {
        icon: Satellite, iconColor: 'text-indigo-600', iconBg: 'bg-indigo-500/10',
        title: 'Site History Check', badge: '$49',
        question: 'What has happened on this site before?',
        answer: 'Eight years of satellite change detection cross-referenced with past DA records and heritage overlays — what was built, cleared, or applied for.',
        href: '/reports/pre-da-history',
      },
    ],
  },
  {
    heading: 'Can I build it?',
    subtitle: 'What you are allowed to put on the block — and which approval pathway applies.',
    tools: [
      {
        icon: Building2, iconColor: 'text-teal-600', iconBg: 'bg-teal-500/10',
        title: 'Granny Flat Check', badge: 'Free + $49',
        question: 'Can I put a granny flat here?',
        answer: 'The six SEPP eligibility tests (lot size, zone, heritage, flood, biodiversity, acid sulfate), a check of your yard from aerial imagery, and a rental estimate.',
        href: '/reports/granny-flat',
      },
      {
        icon: Home, iconColor: 'text-amber-600', iconBg: 'bg-amber-500/10',
        title: 'Pre-DA Check', badge: 'Free',
        question: 'Do I even need council approval?',
        answer: 'A plain-English walk through the exempt and complying development rules for your address, so you know whether a full DA is required before you start.',
        href: '/check',
      },
      {
        icon: Scissors, iconColor: 'text-violet-600', iconBg: 'bg-violet-500/10',
        title: 'Subdivision Check', badge: 'Free',
        question: 'Can I subdivide this lot?',
        answer: 'Your lot area against the minimum lot size and the dwelling types permitted in the zone, for both Torrens and strata pathways.',
        href: '/tools/subdivision-check',
      },
    ],
  },
  {
    heading: "What's it worth pursuing?",
    subtitle: 'Whether the plan stacks up before you spend on a consultant.',
    tools: [
      {
        icon: Sun, iconColor: 'text-amber-500', iconBg: 'bg-amber-500/10',
        title: 'Solar Potential', badge: '$39',
        question: 'How much solar could this roof generate?',
        answer: 'Roof geometry and orientation from satellite imagery combined with Bureau of Meteorology irradiance to estimate annual generation.',
        href: '/reports/solar-yield',
      },
      {
        icon: Radar, iconColor: 'text-violet-600', iconBg: 'bg-violet-500/10',
        title: 'Development Monitoring', badge: 'Free + $9/mo',
        question: "What's being built around it?",
        answer: 'Every DA and CDC within 500m, with optional weekly email alerts when a new application is lodged near the property.',
        href: '/reports/threat-radar',
      },
    ],
  },
];

export default function HomebuyersPage() {
  return (
    <main className="min-h-screen bg-white">
      <HomeNav />

      {/* Hero */}
      <section className="relative bg-slate-950 overflow-hidden">
        <div className="absolute inset-0 dot-pattern" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-teal-500/8 rounded-full blur-[100px]" />

        <div className="relative max-w-3xl mx-auto px-6 pt-32 pb-20 text-center">
          <div className="flex items-center justify-center gap-2 mb-6">
            <Home className="w-5 h-5 text-teal-400" />
            <span className="text-xs font-semibold uppercase tracking-widest text-teal-400">
              For homeowners &amp; buyers
            </span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-6 leading-[1.1]">
            Before you buy — or build —{' '}
            <span className="bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
              check the address.
            </span>
          </h1>
          <p className="text-slate-400 text-lg max-w-xl mx-auto leading-relaxed mb-8">
            Does it flood? Is it bushfire-prone? What can you actually build? What is
            being built next door? Ask any NSW address — every answer names the source it
            came from, and where a source could not be consulted it says so rather than
            answering. Free checks; detailed reports from $39.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/reports"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
            >
              Run a free check
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/what-you-get"
              className="inline-flex items-center gap-2 px-6 py-3 text-slate-300 text-sm font-medium rounded-xl border border-slate-700 hover:border-slate-600 hover:text-white transition-all"
            >
              See everything you can check
            </Link>
          </div>
        </div>
      </section>

      {/* Stats strip */}
      <section className="bg-slate-950 border-t border-slate-800/50 py-8 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-6">
          {[
            { value: COVERAGE_DISPLAY.lgasCovered, label: 'LGAs covered' },
            { value: COVERAGE_DISPLAY.riskLayers, label: 'Risk layers' },
            { value: COVERAGE_DISPLAY.govDataSources, label: 'Gov data sources' },
            { value: 'Free', label: 'To start' },
          ].map(({ value, label }) => (
            <div key={label} className="text-center">
              <div className="text-2xl font-bold text-white">{value}</div>
              <div className="text-sm text-slate-500 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Sections */}
      {SECTIONS.map(({ heading, subtitle, tools }, sectionIdx) => (
        <section
          key={heading}
          className={`py-16 px-6 ${sectionIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`}
        >
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-1">{heading}</h2>
            <p className="text-slate-500 mb-8">{subtitle}</p>

            <div className="grid grid-cols-1 gap-4">
              {tools.map(({ icon: Icon, iconColor, iconBg, title, question, answer, href, badge }) => (
                <Link
                  key={title}
                  href={href}
                  className="group flex gap-5 rounded-xl border border-slate-200 bg-white p-6 hover:border-teal-300 hover:shadow-md transition-all"
                >
                  <div className={`shrink-0 w-11 h-11 rounded-xl ${iconBg} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${iconColor}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-slate-900 group-hover:text-teal-700 transition-colors">
                        {title}
                      </h3>
                      <span className="shrink-0 text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                        {badge}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-slate-700 mb-1">{question}</p>
                    <p className="text-sm text-slate-500 leading-relaxed">{answer}</p>
                  </div>
                  <ArrowRight className="shrink-0 w-4 h-4 text-slate-300 mt-1 group-hover:text-teal-500 group-hover:translate-x-0.5 transition-all" />
                </Link>
              ))}
            </div>
          </div>
        </section>
      ))}

      {/* Trust */}
      <section className="relative bg-slate-950 py-16 px-6 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-teal-500/5 rounded-full blur-[100px]" />
        <div className="relative max-w-3xl mx-auto">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-5 h-5 text-teal-400" />
            <span className="text-xs font-semibold uppercase tracking-widest text-teal-400">
              Where the answers come from
            </span>
          </div>
          <h2 className="text-2xl font-bold text-white mb-3">Every figure traced to its source</h2>
          <p className="text-slate-400 leading-relaxed">
            Checks run on live NSW Planning Portal data, council flood studies, the Rural
            Fire Service, Bureau of Meteorology and satellite imagery — combined by a
            deterministic engine, with no AI interpretation of the rules. A free check is a
            screen, not planning advice or a certificate; the detailed report shows every
            source so you and your conveyancer or planner can verify it.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-8 sm:p-10 text-center">
            <h2 className="text-2xl font-bold text-slate-900 mb-3">
              Check the address you are thinking about
            </h2>
            <p className="text-slate-600 mb-6 max-w-lg mx-auto">
              Enter any NSW address and run the free checks — no account, no sales call.
            </p>
            <Link
              href="/reports"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
            >
              Run a free check
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
