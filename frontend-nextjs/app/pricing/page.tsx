import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { PILOT_COUNCIL_LABELS } from '@/lib/pilot-focus';

export const metadata: Metadata = {
  title: 'Free during the pilot — PlotDetect',
  description: 'Council Rules and Site Facts are free while we test them with chosen professionals in ten councils.',
};

export default function PricingPage() {
  const councils = PILOT_COUNCIL_LABELS;
  return (
    <main className="min-h-screen bg-white">
      <SiteNav maxWidth="max-w-6xl" />

      <section className="pt-16 pb-16 px-6 max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-4 text-center">Free during the pilot</h1>
        <p className="text-gray-600 text-lg leading-relaxed mb-6">
          <Link href="/assessment" className="text-teal-600 hover:text-teal-500">Council Rules</Link> and{' '}
          <Link href="/reports/intelligence-brief" className="text-teal-600 hover:text-teal-500">Site Facts</Link>{' '}
          are free while we test them with chosen professionals in ten councils.
        </p>

        <h2 className="text-xl font-bold text-gray-900 mb-3">The pilot councils</h2>
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-8 text-gray-700">
          {councils.map((name) => (
            <li key={name} className="flex gap-3 text-sm">
              <span className="mt-2 w-1.5 h-1.5 rounded-full bg-teal-500 flex-shrink-0" />
              {name}
            </li>
          ))}
        </ul>

        <h2 className="text-xl font-bold text-gray-900 mb-3">What we ask of pilot users</h2>
        <p className="text-gray-600 leading-relaxed mb-8">
          If a rule shown is wrong, tell us. Every correction helps us fix the reading of the council&apos;s document.
        </p>

        <Link
          href="/contact"
          className="inline-block px-6 py-3 bg-teal-600 text-white text-sm font-semibold rounded-xl hover:bg-teal-700 transition-colors"
        >
          Contact us
        </Link>
      </section>

      <SiteFooter />
    </main>
  );
}
