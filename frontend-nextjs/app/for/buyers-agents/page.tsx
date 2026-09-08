import type { Metadata } from 'next';
import Link from 'next/link';
import {
  Radar, Droplets, Flame, Building2, ArrowRight, Moon, Sun, Satellite,
  FileCheck, ShieldCheck, Map, BarChart3, Thermometer,
} from 'lucide-react';
import { HomeNav } from '@/components/marketing/HomeNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'For Buyers Agents — PlotDetect',
  description:
    'Every property check in one place. Flood depth, bushfire BAL, zone/FSR/height, heritage, DAs within 500m, granny flat eligibility, shadow risk, climate projections, and more — free for any NSW address.',
};

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const WORKFLOW_SECTIONS = [
  {
    heading: 'Risk screening',
    subtitle: 'The "should my client avoid this?" questions',
    tools: [
      {
        icon: Droplets,
        iconColor: 'text-blue-600',
        iconBg: 'bg-blue-500/10',
        title: 'Flood Screening',
        question: 'Does it flood? How deep?',
        answer:
          'ARI return period depths from council flood studies — not just whether the overlay exists. Know the difference between ankle-deep and ground-floor-underwater.',
        href: '/reports/flood',
        badge: 'Free + $49 report',
      },
      {
        icon: Flame,
        iconColor: 'text-orange-600',
        iconBg: 'bg-orange-500/10',
        title: 'Bushfire Pre-Screen',
        question: 'Is it bushfire-prone? What does that cost?',
        answer:
          'Bush Fire Prone Land status, estimated BAL band, 10/50 vegetation clearing obligations, and CDC pathway impact. Directly affects insurance premiums and building constraints.',
        href: '/reports/bushfire',
        badge: 'Free + $39 report',
      },
      {
        icon: Thermometer,
        iconColor: 'text-red-600',
        iconBg: 'bg-red-500/10',
        title: 'Climate Risk Intelligence',
        question: 'What is the long-term risk trajectory?',
        answer:
          'Five-hazard compound scoring — flood, bushfire, heat stress, precipitation change, and coastal risk. NARCliM 2.0 projections to 2099. The "should I buy in this suburb long-term" answer.',
        href: '/climate-risk',
        badge: 'Free check',
      },
      {
        icon: Moon,
        iconColor: 'text-slate-500',
        iconBg: 'bg-slate-500/10',
        title: 'Shadow Risk Analyser',
        question: 'Will this property get overshadowed?',
        answer:
          'Shadow modelled from a maximum-height building envelope placed immediately north of the lot, calculated on ADG solar access test dates. Know before your client loses their north-facing light.',
        href: '/reports/shadow',
        badge: '$39',
      },
    ],
  },
  {
    heading: 'Planning intelligence',
    subtitle: 'The "what can be built here?" questions',
    tools: [
      {
        icon: ShieldCheck,
        iconColor: 'text-teal-600',
        iconBg: 'bg-teal-500/10',
        title: 'Site Controls — Planning Provisions',
        question: 'What are the zone, FSR, height, heritage, and SEPP requirements?',
        answer:
          `Zone permissibility, floor space ratio, height of buildings, minimum lot size, heritage status, all spatial overlays, and every applicable SEPP requirement — for any NSW address. Full DCP provisions for Inner West, structured numeric controls for ${COVERAGE_DISPLAY.dcpNumericCouncils} councils.`,
        href: '/assessment',
        badge: 'Free',
      },
      {
        icon: FileCheck,
        iconColor: 'text-emerald-600',
        iconBg: 'bg-emerald-500/10',
        title: 'Conveyancing Disclosure',
        question: 'What should the conveyancer check before exchange?',
        answer:
          'LEP controls, spatial overlays, heritage listings, and SEPP compliance in one report. The planning check that should happen pre-exchange — whether your client has a conveyancer yet or not.',
        href: '/reports/conveyancing',
        badge: 'Free + $49 report',
      },
    ],
  },
  {
    heading: 'Investment potential',
    subtitle: 'The "what is the opportunity?" questions',
    tools: [
      {
        icon: Building2,
        iconColor: 'text-teal-600',
        iconBg: 'bg-teal-500/10',
        title: 'Granny Flat Yield Predictor',
        question: 'Can my client add a granny flat?',
        answer:
          'SEPP Housing eligibility, satellite structure detection for existing secondary dwellings, and rental yield estimate. Filters investment properties fast.',
        href: '/reports/granny-flat',
        badge: 'Free + $49 report',
      },
      {
        icon: Sun,
        iconColor: 'text-amber-500',
        iconBg: 'bg-amber-500/10',
        title: 'Rooftop Solar Yield',
        question: 'What solar output could this property generate?',
        answer:
          'Roof geometry, orientation, and estimated annual generation from satellite imagery and Bureau of Meteorology irradiance data. Useful for sustainability-conscious buyers and cost-of-living conversations.',
        href: '/reports/solar-yield',
        badge: '$39',
      },
      {
        icon: Satellite,
        iconColor: 'text-indigo-600',
        iconBg: 'bg-indigo-500/10',
        title: 'Pre-DA Site History',
        question: 'What has happened on this site before?',
        answer:
          'Eight years of satellite change detection cross-referenced with DA records and heritage overlays. Spots undisclosed work, previous refusals, and neighbourhood trajectory.',
        href: '/reports/pre-da-history',
        badge: '$49',
      },
    ],
  },
  {
    heading: 'Monitoring and analytics',
    subtitle: 'The "what is changing nearby?" questions',
    tools: [
      {
        icon: Radar,
        iconColor: 'text-violet-600',
        iconBg: 'bg-violet-500/10',
        title: 'Neighbour Threat Radar',
        question: 'What is being built near this property?',
        answer:
          'Every DA and CDC within 500m — with weekly email alerts when new applications are lodged. Know before your client\'s neighbour breaks ground on something that affects their view, parking, or value.',
        href: '/reports/threat-radar',
        badge: 'Free + $9/mo',
      },
      {
        icon: Map,
        iconColor: 'text-blue-600',
        iconBg: 'bg-blue-500/10',
        title: 'Scout — Interactive Map',
        question: 'What does the area look like on a planning map?',
        answer:
          'Zone overlays, lot boundaries, heritage items, and planning controls rendered on an interactive map. Click any property in NSW to see its planning context.',
        href: '/scout',
        badge: 'Free',
      },
      {
        icon: BarChart3,
        iconColor: 'text-violet-600',
        iconBg: 'bg-violet-500/10',
        title: 'Validate — DA Analytics',
        question: 'What are the approval rates for this council?',
        answer:
          `DA analytics across ${COVERAGE_DISPLAY.totalNswCouncils} NSW councils — approval rates, processing times, common refusal reasons, and trend analysis. Context for advising clients on what to expect.`,
        href: '/validate',
        badge: 'Free',
      },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function BuyersAgentsPage() {
  return (
    <main className="min-h-screen bg-white">
      <HomeNav />

      {/* Hero */}
      <section className="relative bg-slate-950 overflow-hidden">
        <div className="absolute inset-0 dot-pattern" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-violet-500/8 rounded-full blur-[100px]" />

        <div className="relative max-w-3xl mx-auto px-6 pt-32 pb-20 text-center">
          <div className="flex items-center justify-center gap-2 mb-6">
            <Radar className="w-5 h-5 text-violet-400" />
            <span className="text-xs font-semibold uppercase tracking-widest text-violet-400">
              For buyers agents
            </span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-6 leading-[1.1]">
            Every property check.{' '}
            <span className="bg-gradient-to-r from-violet-400 to-teal-400 bg-clip-text text-transparent">
              One address.
            </span>
          </h1>
          <p className="text-slate-400 text-lg max-w-xl mx-auto leading-relaxed mb-8">
            Flood depth, bushfire BAL, zone and FSR, heritage, nearby DAs, granny flat
            eligibility, shadow risk, climate projections, and DA analytics — 12 checks
            that replace 7 government portals. Free, no account required.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/reports"
              className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-500 transition-colors"
            >
              Try any tool free
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/assessment"
              className="inline-flex items-center gap-2 px-6 py-3 text-slate-300 text-sm font-medium rounded-xl border border-slate-700 hover:border-slate-600 hover:text-white transition-all"
            >
              Open Site Controls
            </Link>
          </div>
        </div>
      </section>

      {/* Stats strip */}
      <section className="bg-slate-950 border-t border-slate-800/50 py-8 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-6">
          {[
            { value: '12', label: 'Property checks' },
            { value: COVERAGE_DISPLAY.lgasCovered, label: 'LGAs covered' },
            { value: COVERAGE_DISPLAY.riskLayers, label: 'Risk layers' },
            { value: COVERAGE_DISPLAY.govDataSources, label: 'Gov data sources' },
          ].map(({ value, label }) => (
            <div key={label} className="text-center">
              <div className="text-2xl font-bold text-white">{value}</div>
              <div className="text-sm text-slate-500 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Workflow sections */}
      {WORKFLOW_SECTIONS.map(({ heading, subtitle, tools }, sectionIdx) => (
        <section
          key={heading}
          className={`py-16 px-6 ${sectionIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`}
        >
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-1">
              {heading}
            </h2>
            <p className="text-slate-500 mb-8">{subtitle}</p>

            <div className="grid grid-cols-1 gap-4">
              {tools.map(({ icon: Icon, iconColor, iconBg, title, question, answer, href, badge }) => (
                <Link
                  key={title}
                  href={href}
                  className="group flex gap-5 rounded-xl border border-slate-200 bg-white p-6 hover:border-violet-300 hover:shadow-md transition-all"
                >
                  <div className={`shrink-0 w-11 h-11 rounded-xl ${iconBg} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${iconColor}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-slate-900 group-hover:text-violet-700 transition-colors">
                        {title}
                      </h3>
                      <span className="shrink-0 text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                        {badge}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-slate-700 mb-1">{question}</p>
                    <p className="text-sm text-slate-500 leading-relaxed">{answer}</p>
                  </div>
                  <ArrowRight className="shrink-0 w-4 h-4 text-slate-300 mt-1 group-hover:text-violet-500 group-hover:translate-x-0.5 transition-all" />
                </Link>
              ))}
            </div>
          </div>
        </section>
      ))}

      {/* Pricing */}
      <section className="relative bg-slate-950 py-16 px-6 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-violet-500/5 rounded-full blur-[100px]" />
        <div className="relative max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-2">Pricing</h2>
          <p className="text-slate-400 mb-8">
            Most checks are free. Reports and monitoring are priced per property.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
              <p className="text-2xl font-bold text-white">Free</p>
              <p className="text-sm text-slate-400 mt-1">Instant checks</p>
              <p className="text-xs text-slate-500 mt-3">
                Flood, bushfire, granny flat, conveyancing, threat radar, climate risk,
                Site Controls planning data, Scout map, Validate DA analytics.
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
              <p className="text-2xl font-bold text-white">$39 &#8211; $49</p>
              <p className="text-sm text-slate-400 mt-1">Per property report</p>
              <p className="text-xs text-slate-500 mt-3">
                Professional PDF with satellite imagery, data citations, and full analysis.
                Pass through as a disbursement.
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
              <p className="text-2xl font-bold text-white">$9/mo</p>
              <p className="text-sm text-slate-400 mt-1">Per property monitoring</p>
              <p className="text-xs text-slate-500 mt-3">
                Weekly DA alerts within 500m. Monthly digest email. Cancel anytime.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <div className="rounded-2xl border border-violet-200 bg-violet-50/50 p-8 sm:p-10 text-center">
            <h2 className="text-2xl font-bold text-slate-900 mb-3">
              Try it on a property you are evaluating right now
            </h2>
            <p className="text-slate-600 mb-6 max-w-lg mx-auto">
              Enter any NSW address and run every check — free, no account, no sales call.
              If it saves you time, we would like to hear about it.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link
                href="/reports"
                className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-500 transition-colors"
              >
                Start with any tool
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="mailto:hello@plotdetect.com.au?subject=Buyers%20agent%20enquiry"
                className="inline-flex items-center gap-2 px-6 py-3 text-slate-700 text-sm font-medium rounded-xl border border-slate-200 hover:border-slate-300 transition-all"
              >
                hello@plotdetect.com.au
              </a>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
