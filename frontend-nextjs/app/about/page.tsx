import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { PILOT_COUNCIL_LABELS } from '@/lib/pilot-focus';

export const metadata: Metadata = {
  title: 'About — PlotDetect',
  description: "PlotDetect is a small NSW project that reads councils' own planning documents and shows the clause and the page each rule comes from.",
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <article className="max-w-2xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">About PlotDetect</h1>

        <div className="prose prose-sm prose-gray max-w-none">
          <p className="text-gray-600 leading-relaxed">
            PlotDetect is a small NSW project. It reads councils&apos; own planning documents and shows the
            clause and the page each rule comes from.
          </p>

          <h2 className="text-lg font-semibold text-gray-900 mt-8 mb-3">Private pilot</h2>
          <p className="text-gray-600 leading-relaxed">
            It is in a private pilot for these councils: {PILOT_COUNCIL_LABELS.join(', ')}. See{' '}
            <Link href="/how-it-works" className="text-teal-600 hover:text-teal-700 transition-colors">how it works</Link>.
          </p>

          <h2 className="text-lg font-semibold text-gray-900 mt-8 mb-3">Data sources</h2>
          <ul className="text-gray-600 space-y-1">
            <li>NSW Planning Portal</li>
            <li>NSW legislation</li>
            <li>Councils&apos; own planning documents</li>
          </ul>

          <h2 className="text-lg font-semibold text-gray-900 mt-8 mb-3">Contact</h2>
          <p className="text-gray-600 leading-relaxed">
            Get in touch through the{' '}
            <Link href="/contact" className="text-teal-600 hover:text-teal-700 transition-colors">contact page</Link>.
          </p>
        </div>
      </article>

      <SiteFooter />
    </main>
  );
}
