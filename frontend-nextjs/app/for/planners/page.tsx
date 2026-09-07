import type { Metadata } from 'next';
import Link from 'next/link';
import { Clock, FileText, Search, CheckSquare, ArrowRight, Layers, BarChart3 } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'For Town Planners & Planning Consultants — PlotDetect',
  description:
    'Cut site analysis from 2 hours to 10 minutes. Zone permissibility, LEP/DCP controls, SEPP requirements, spatial overlays, and flood/bushfire status — for any NSW address. Built for planning professionals.',
  keywords: [
    'planning consultant tools',
    'town planner software',
    'planning consultant nsw',
    'site analysis tool',
    'planning advice tools',
    'pre-lodgement assessment tool',
    'development control plan lookup',
    'planning assessment software',
  ],
};

const TIME_SAVINGS = [
  {
    task: 'Zone + permitted uses lookup',
    before: '10–15 min',
    after: 'Instant',
    description: 'Zone code, full permitted/prohibited table, and legislation URL — from the Planning Portal API, not a PDF.',
  },
  {
    task: 'LEP numeric controls',
    before: '5–10 min',
    after: 'Instant',
    description: 'FSR, height, minimum lot size, heritage listing, acid sulfate soil class — per lot, not per map sheet.',
  },
  {
    task: 'DCP controls extraction',
    before: '30–60 min',
    after: '10 seconds',
    description: `Setbacks, parking rates, landscaping, site coverage — numeric fields with clause citations. ${COVERAGE_DISPLAY.dcpNumericCouncils} LGAs, ${COVERAGE_DISPLAY.dcpSetbackRows} rows. Full structured provisions for ${COVERAGE_DISPLAY.dcpFullCouncils} councils.`,
  },
  {
    task: 'SEPP applicability check',
    before: '15–20 min',
    after: 'Instant',
    description: 'Housing SEPP, Exempt & Complying, Transport & Infrastructure, Resilience & Hazards — which clauses apply to this address.',
  },
  {
    task: 'Spatial overlay check',
    before: '10–15 min',
    after: 'Instant',
    description: 'Flood prone land, bushfire prone land, heritage conservation area, riparian corridor, foreshore building line, ANEF contours.',
  },
  {
    task: 'Flood depth + bushfire BAL',
    before: '20–30 min (if available)',
    after: 'Instant',
    description: `Modelled flood depth at ARI return periods where a council flood study has been ingested (${COVERAGE_DISPLAY.floodStudies} studies); the mapped flood planning area elsewhere. Bush Fire Prone Land category and estimated BAL band.`,
  },
];

const WORKFLOW_STEPS = [
  {
    icon: Search,
    title: 'Enter the address',
    description: 'Type any NSW address. We resolve it against the Planning Portal lot boundary.',
  },
  {
    icon: Layers,
    title: 'Review the controls',
    description: 'Zone, LEP, DCP, SEPP, spatial overlays — all on one screen with clause citations.',
  },
  {
    icon: FileText,
    title: 'Export or continue',
    description: 'Use the data for your site analysis. Link directly to the legislation for each control.',
  },
];

export default function PlannersPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            For planning professionals
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
          Site analysis in 10 minutes, not 2 hours
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          You already know the planning system. You don&apos;t need it explained — you need the data
          pulled together faster. PlotDetect gives you zone permissibility, LEP/DCP controls, SEPP
          applicability, and spatial overlays for any NSW address, instantly.
        </p>
        <div className="flex flex-wrap gap-3 mt-8">
          <TrackedLink
            href="/assessment"
            page="planners"
            cta="hero_try_free"
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          >
            Try it now <ArrowRight className="w-4 h-4" />
          </TrackedLink>
        </div>
      </section>

      {/* Time savings table */}
      <section className="bg-gray-50 border-y border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-2">What it replaces</h2>
          <p className="text-sm text-gray-500 mb-6">
            Time estimates based on manual lookups across Planning Portal, council DCP PDFs, and spatial viewers.
          </p>
          <div className="space-y-3">
            {TIME_SAVINGS.map(({ task, before, after, description }) => (
              <div key={task} className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-baseline justify-between mb-1">
                  <h3 className="font-semibold text-gray-900 text-sm">{task}</h3>
                  <div className="flex items-center gap-2 text-xs flex-shrink-0">
                    <span className="text-gray-400 line-through">{before}</span>
                    <ArrowRight className="w-3 h-3 text-gray-300" />
                    <span className="text-teal-600 font-semibold">{after}</span>
                  </div>
                </div>
                <p className="text-xs text-gray-500">{description}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 bg-teal-50 rounded-xl border border-teal-200 p-4">
            <div className="flex items-baseline justify-between">
              <p className="font-bold text-teal-800 text-sm">Total time saved per site</p>
              <p className="text-teal-600 font-bold text-sm">~90 minutes</p>
            </div>
            <p className="text-xs text-teal-600 mt-1">
              At 3 sites/week, that&apos;s 4.5 hours back — or 2 extra billable assessments.
            </p>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <h2 className="text-xl font-bold text-gray-900 mb-6">How it works</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {WORKFLOW_STEPS.map(({ icon: Icon, title, description }, i) => (
            <div key={title} className="relative">
              <div className="flex items-center gap-3 mb-2">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-teal-100 flex items-center justify-center text-xs font-bold text-teal-700">
                  {i + 1}
                </span>
                <Icon className="w-4 h-4 text-gray-400" />
              </div>
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* What it is NOT */}
      <section className="bg-gray-50 border-y border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-4">What PlotDetect is not</h2>
          <p className="text-sm text-gray-500 mb-4">
            This tool does not replace your professional judgement. It accelerates the data
            gathering phase so you can spend more time on analysis and advice.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              'Not a planning assessment — it gathers data, you interpret it',
              'Not a DA preparation tool — it shows controls, not application forms',
              'Not a replacement for council pre-lodgement — it saves time before the meeting',
              'Not legal advice — all data links to the source instrument',
            ].map((item) => (
              <div key={item} className="flex items-start gap-2">
                <CheckSquare className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-gray-600">{item}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Coverage */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Data coverage</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { stat: 'NSW-wide', label: 'Any address', sub: 'Zone, LEP + SEPP, live from the Planning Portal' },
            { stat: '24', label: 'Sydney councils', sub: 'Structured numeric DCP controls' },
            { stat: 'Clause + page', label: 'Every control cited', sub: 'Check any value against the source document' },
            { stat: 'Inner West', label: 'Deepest coverage', sub: 'Full DCP browser, expanding' },
          ].map(({ stat, label, sub }) => (
            <div key={label + sub} className="text-center p-4 rounded-xl border border-gray-200">
              <p className="text-2xl font-bold text-gray-900">{stat}</p>
              <p className="text-sm text-gray-600">{label}</p>
              <p className="text-xs text-gray-400">{sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-12 text-center">
        <h2 className="text-xl font-bold text-gray-900 mb-3">Try it on your next site</h2>
        <p className="text-gray-500 text-sm mb-6 max-w-md mx-auto">
          Enter any NSW address. See the controls. Decide if it saves you time.
        </p>
        <TrackedLink
          href="/assessment"
          page="planners"
          cta="bottom_open_verify"
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
        >
          Open Site Controls <ArrowRight className="w-4 h-4" />
        </TrackedLink>
      </section>

      <SiteFooter />
    </main>
  );
}
