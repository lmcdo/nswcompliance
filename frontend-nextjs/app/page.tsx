import Link from 'next/link';
import {
  FileCheck, Building2, Radar, Satellite,
  MapPin, Scale, FileText, ArrowRight,
} from 'lucide-react';
import { HomeNav } from '@/components/marketing/HomeNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { HeroAddressSearch } from '@/components/marketing/HeroAddressSearch';

// The plan-brief rows under "Your project" are off until NEXT_PUBLIC_PLAN_BRIEF=on
// (components/compliance/YourProjectSummary.tsx). The council-plan column below
// describes only what is live, so the copy follows the same flag.
const PLAN_BRIEF_ON = process.env.NEXT_PUBLIC_PLAN_BRIEF === 'on';

/* ------------------------------------------------------------------ */
/*  What a Site Report holds                                           */
/* ------------------------------------------------------------------ */

const REPORT_PARTS = [
  {
    icon: MapPin,
    label: 'The lot',
    title: 'What the government maps say about this lot',
    body: 'Zone, height, floor space ratio, minimum lot size, heritage, flood, bushfire and other mapped overlays. Read from the NSW Planning Portal and other public sources, each with the date of the layer.',
  },
  {
    icon: Scale,
    label: 'Statewide law',
    title: 'The state rules, set against your lot',
    body: 'Housing SEPP, low and mid-rise housing and complying development gates, shown as a fact beside its threshold with a link to the clause. No pass or fail banner.',
  },
  {
    icon: FileText,
    label: 'The council plan',
    title: PLAN_BRIEF_ON
      ? "The council plan's own rules for your project"
      : 'The council chapters that apply to this lot',
    body: PLAN_BRIEF_ON
      ? "The plan's closest clauses for each rule type, quoted in the council's words with the page number. Where we could not find one, the row says so and points to the plan."
      : "Each chapter of the council's development control plan that applies to this lot, with a link to the council's own page. The full plan stays below.",
  },
];

const STEPS = [
  { n: '1', title: 'Enter an address', body: 'Any NSW address. No account needed.' },
  { n: '2', title: 'Say what you want to build', body: 'Dwelling, secondary dwelling, subdivision and so on. A corner lot, main road or heritage item changes the rules, so you can say so.' },
  { n: '3', title: 'Read your Site Report', body: 'A table for your project, every row linked to its source.' },
  { n: '4', title: 'Open the full plan if you want it', body: 'Nothing is hidden. The whole council plan sits below the report.' },
];

const LIMITS = [
  'It is not a verdict. It does not predict the outcome of a development application.',
  'It is not a section 10.7 planning certificate and not legal advice.',
  "It shows the council's published words. It does not interpret them.",
  'When a figure or clause cannot be found, the row says "not found" and links to the source. It never fills the gap with a guess.',
  'Figures are indicative. Check the linked clause and the council before you rely on one.',
];

/* ------------------------------------------------------------------ */
/*  Other checks (secondary)                                           */
/* ------------------------------------------------------------------ */

const TOOLS = [
  {
    href: '/reports/conveyancing',
    title: 'Conveyancing Disclosure',
    tagline: 'LEP controls, overlays, heritage and SEPP, set out for a conveyancer.',
    badge: 'Free + $49',
    icon: FileCheck,
    iconColor: 'text-emerald-600',
    iconBg: 'bg-emerald-500/10',
  },
  {
    href: '/reports/granny-flat',
    title: 'Granny Flat Check',
    tagline: 'SEPP eligibility, structure detection from imagery, and a rental estimate.',
    badge: 'Free + $49',
    icon: Building2,
    iconColor: 'text-teal-600',
    iconBg: 'bg-teal-500/10',
  },
  {
    href: '/reports/threat-radar',
    title: 'Development Monitoring',
    tagline: 'Every DA and CDC within 500m, with weekly email alerts for new lodgements.',
    badge: 'Free + $9/mo',
    icon: Radar,
    iconColor: 'text-violet-600',
    iconBg: 'bg-violet-500/10',
  },
  {
    href: '/reports/pre-da-history',
    title: 'Site History Check',
    tagline: 'Eight years of satellite change detection beside DA records and heritage overlays.',
    badge: '$49',
    icon: Satellite,
    iconColor: 'text-indigo-600',
    iconBg: 'bg-indigo-500/10',
  },
];

/* ------------------------------------------------------------------ */
/*  Personas                                                           */
/* ------------------------------------------------------------------ */

const PERSONAS = [
  {
    title: 'Homeowners & buyers',
    description: 'See what the maps and the council plan say about a lot before you bid or plan.',
    href: '/for/homebuyers',
    cta: 'For homeowners',
  },
  {
    title: 'Conveyancers',
    description: 'A planning pre-check with every line linked to its source, ahead of the section 10.7 certificate.',
    href: '/for/conveyancers',
    cta: 'For conveyancers',
  },
  {
    title: 'Buyers Agents',
    description: 'Screen a shortlist against the facts that decide a project, then monitor nearby development.',
    href: '/for/buyers-agents',
    cta: 'For buyers agents',
  },
  {
    title: 'Builders & Planners',
    description: "Find the clause and the page fast. Each rule is in the council's own words.",
    href: '/for/builders',
    cta: 'For builders and planners',
  },
];

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <HomeNav />

      {/* ── Hero ── */}
      <section className="relative bg-slate-950 overflow-hidden">
        <div className="absolute inset-0 dot-pattern" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-teal-500/8 rounded-full blur-[120px]" />

        <div className="relative px-6 pt-32 pb-24 max-w-3xl mx-auto text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-teal-400 mb-4">
            Site Report
          </p>
          <h1 className="text-5xl sm:text-6xl font-bold leading-[1.08] text-white mb-6 tracking-tight">
            Your address. Your project.{' '}
            <span className="bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
              The rules that apply.
            </span>
          </h1>
          <p className="text-slate-400 text-lg mb-10 max-w-xl mx-auto leading-relaxed">
            A Site Report for any NSW address: what the government maps and state law say
            about that lot, and what the council plan says about your project. Each line
            links to its source and, for council rules, gives the council&apos;s own words and the page.
            Where we cannot find something, it says so.
          </p>

          <HeroAddressSearch />

          <div className="flex flex-wrap justify-center gap-3">
            <TrackedLink
              href="/assessment"
              page="home"
              cta="hero_open_site_report"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
            >
              Open a Site Report
              <ArrowRight className="w-3.5 h-3.5" />
            </TrackedLink>
            <Link
              href="/how-it-works"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-slate-300 bg-slate-800/50 border border-slate-700/50 rounded-lg hover:border-slate-600 hover:text-white transition-all"
            >
              How it works
            </Link>
          </div>
        </div>
      </section>

      {/* ── What a Site Report holds ── */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-2">
            What is in a Site Report
          </h2>
          <p className="text-slate-500 max-w-xl mb-10">
            Three layers, each tied to where it came from. Only the rules for your lot and your project come first.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {REPORT_PARTS.map(({ icon: Icon, label, title, body }) => (
              <div key={label} className="rounded-2xl border border-slate-200 p-6">
                <div className="w-10 h-10 rounded-xl bg-teal-500/10 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-teal-600" />
                </div>
                <span className="text-xs font-semibold uppercase tracking-widest text-teal-600 mb-2 block">
                  {label}
                </span>
                <h3 className="font-semibold text-slate-900 mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it reads ── */}
      <section className="py-20 px-6 bg-slate-50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-10">
            From address to report
          </h2>
          <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {STEPS.map(({ n, title, body }) => (
              <li key={n} className="rounded-2xl bg-white border border-slate-200 p-6">
                <span className="text-sm font-bold text-teal-600">Step {n}</span>
                <h3 className="font-semibold text-slate-900 mt-1 mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ── What it does not do ── */}
      <section className="py-20 px-6 bg-slate-950">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-white tracking-tight mb-3">
            What a Site Report does not do
          </h2>
          <p className="text-slate-400 mb-8">
            It is a fast first look at how far a lot is from the rules that decide a project.
          </p>
          <ul className="space-y-3">
            {LIMITS.map((line) => (
              <li key={line} className="flex gap-3 text-slate-300 text-sm leading-relaxed">
                <span className="mt-2 w-1.5 h-1.5 rounded-full bg-teal-400 flex-shrink-0" />
                {line}
              </li>
            ))}
          </ul>
          <div className="mt-10">
            <TrackedLink
              href="/assessment"
              page="home"
              cta="limits_open_site_report"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
            >
              Open a Site Report
              <ArrowRight className="w-4 h-4" />
            </TrackedLink>
          </div>
        </div>
      </section>

      {/* ── More checks ── */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-2">
                More checks for one address
              </h2>
              <p className="text-slate-500 max-w-lg text-sm">
                Separate reports for a single question. Free checks first, no account needed.
              </p>
            </div>
            <Link
              href="/reports"
              className="hidden sm:inline-flex text-sm text-teal-600 font-medium hover:text-teal-500 transition-colors"
            >
              All checks →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {TOOLS.map((tool) => {
              const Icon = tool.icon;
              return (
                <Link
                  key={tool.href}
                  href={tool.href}
                  className="group rounded-2xl border border-slate-200 p-6 hover:border-teal-500/40 hover:shadow-lg hover:shadow-teal-500/5 transition-all"
                >
                  <div className={`w-10 h-10 rounded-xl ${tool.iconBg} flex items-center justify-center mb-4`}>
                    <Icon className={`w-5 h-5 ${tool.iconColor}`} />
                  </div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <h3 className="font-semibold text-slate-900 group-hover:text-teal-700 transition-colors">
                      {tool.title}
                    </h3>
                    <span
                      className={`shrink-0 text-[11px] font-medium px-2 py-0.5 rounded-full ${
                        tool.badge.startsWith('Free')
                          ? 'bg-teal-50 text-teal-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {tool.badge}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500 leading-relaxed">{tool.tagline}</p>
                </Link>
              );
            })}
          </div>
          <p className="mt-6 text-sm text-slate-500">
            Also:{' '}
            <Link href="/scout" className="text-teal-600 hover:text-teal-500">Scout</Link>
            {' '}(map explorer),{' '}
            <Link href="/validate" className="text-teal-600 hover:text-teal-500">Validate</Link>
            {' '}(DA approval patterns) and{' '}
            <Link href="/climate-risk" className="text-teal-600 hover:text-teal-500">climate risk</Link>.
          </p>
        </div>
      </section>

      {/* ── Personas ── */}
      <section className="py-20 px-6 bg-slate-50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-10 text-center">
            Built for how you actually work
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {PERSONAS.map(({ title, description, href, cta }) => (
              <Link
                key={title}
                href={href}
                className="group rounded-2xl bg-white border border-slate-200 p-6 hover:shadow-lg hover:border-teal-500/30 transition-all"
              >
                <h3 className="font-semibold text-slate-900 mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed mb-4">{description}</p>
                <span className="inline-flex items-center gap-1 text-sm text-teal-600 font-medium group-hover:text-teal-500 transition-colors">
                  {cta}
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
