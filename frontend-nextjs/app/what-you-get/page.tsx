import type { Metadata } from 'next';
import Link from 'next/link';
import { Layers, ArrowRight } from 'lucide-react';
import { HomeNav } from '@/components/marketing/HomeNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { COVERAGE_DISPLAY } from '@/lib/coverage';
import { CapabilityExplorer } from './CapabilityExplorer';

export const metadata: Metadata = {
  title: 'What You Get — Data & Capabilities | PlotDetect',
  description:
    'Everything PlotDetect holds on a NSW address and what you can do with it — planning controls, hazard and climate, satellite imagery and development activity — filtered by your role, with honest coverage for each layer.',
};

/* Coverage is not uniform — this is the honest tiering, from lib/coverage.ts. */
const TIERS = [
  {
    label: 'Statewide',
    scope: 'Every NSW address',
    detail:
      'Zone and LEP controls, SEPP applicability, spatial overlays, bushfire, satellite products and DA activity are resolved live for any address in the state.',
    stat: `${COVERAGE_DISPLAY.totalNswCouncils} councils`,
  },
  {
    label: 'DCP numeric controls',
    scope: 'Structured setbacks, parking, landscaping',
    detail:
      'Council DCP controls extracted into numeric fields with clause citations. Coverage expands as each council is onboarded — everywhere else we surface the source document to check.',
    stat: `${COVERAGE_DISPLAY.dcpNumericCouncils} councils`,
  },
  {
    label: 'Full structured DCP',
    scope: 'Every provision type, precinct-aware',
    detail:
      'The complete Development Control Plan — all provision types, precinct filtering and DA-mode workflow — for the councils with a full structured build.',
    stat: `${COVERAGE_DISPLAY.dcpFullCouncils} councils`,
  },
];

export default function WhatYouGetPage() {
  return (
    <main className="min-h-screen bg-white">
      <HomeNav />

      {/* Hero */}
      <section className="relative bg-slate-950 overflow-hidden">
        <div className="absolute inset-0 dot-pattern" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[500px] bg-teal-500/8 rounded-full blur-[120px]" />

        <div className="relative max-w-3xl mx-auto px-6 pt-32 pb-20 text-center">
          <div className="flex items-center justify-center gap-2 mb-6">
            <Layers className="w-5 h-5 text-teal-400" />
            <span className="text-xs font-semibold uppercase tracking-widest text-teal-400">
              Data &amp; capabilities
            </span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-6 leading-[1.1]">
            Everything on a NSW address —{' '}
            <span className="bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
              and what you can do with it.
            </span>
          </h1>
          <p className="text-slate-400 text-lg max-w-xl mx-auto leading-relaxed mb-8">
            Planning controls, hazard and climate, satellite imagery, and development
            activity — {COVERAGE_DISPLAY.provisionsTotal} indexed provisions across{' '}
            {COVERAGE_DISPLAY.lgasCovered} LGAs and {COVERAGE_DISPLAY.govDataSources} government
            data sources. Pick your role below to see what applies to you.
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
              href="/open-data"
              className="inline-flex items-center gap-2 px-6 py-3 text-slate-300 text-sm font-medium rounded-xl border border-slate-700 hover:border-slate-600 hover:text-white transition-all"
            >
              Data sources &amp; fields
            </Link>
          </div>
        </div>
      </section>

      {/* The interactive, persona-filtered catalogue */}
      <CapabilityExplorer />

      {/* Coverage honesty — what's actually available where */}
      <section className="py-16 px-6 bg-slate-50 border-t border-slate-200">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-2">
            Coverage is not uniform — here is exactly where it stands
          </h2>
          <p className="text-slate-500 max-w-2xl mb-8">
            Most layers resolve for any NSW address. Council DCP controls are the one place
            depth varies, so we state it plainly rather than imply blanket coverage.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TIERS.map(({ label, scope, detail, stat }) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-white p-6">
                <div className="text-2xl font-bold text-teal-700 mb-1">{stat}</div>
                <div className="font-semibold text-slate-900">{label}</div>
                <div className="text-xs text-slate-400 mb-3">{scope}</div>
                <p className="text-sm text-slate-500 leading-relaxed">{detail}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-6">
            Every figure on this page is drawn from a single source of truth and reconciled
            against the live database — see the{' '}
            <Link href="/open-data" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
              data catalogue
            </Link>{' '}
            for record counts, fields and licences, or{' '}
            <Link href="/how-it-works" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
              how it works
            </Link>{' '}
            for each source and its update cadence.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-8 sm:p-10 text-center">
            <h2 className="text-2xl font-bold text-slate-900 mb-3">Put it to work on one address</h2>
            <p className="text-slate-600 mb-6 max-w-lg mx-auto">
              Enter any NSW address and run the free checks — every figure traced to its source.
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
