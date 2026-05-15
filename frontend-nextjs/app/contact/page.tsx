import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'Contact — PlotDetect',
  description: 'Get in touch with PlotDetect — questions, embed partnerships, or feedback.',
};

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <div className="max-w-2xl mx-auto px-6 py-14">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Get in touch</h1>
        <p className="text-gray-500 mb-10">
          Questions, feedback, or interested in embedding our tools on your website?
        </p>

        <div className="space-y-6">
          <div className="rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-1">General enquiries</h2>
            <p className="text-sm text-gray-500 mb-3">
              Questions about reports, data sources, or how the tools work.
            </p>
            <a
              href="mailto:hello@plotdetect.com.au"
              className="text-teal-600 font-medium hover:text-teal-700 transition-colors"
            >
              hello@plotdetect.com.au
            </a>
          </div>

          <div className="rounded-xl border border-teal-200 bg-teal-50 p-6">
            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-1">Embed program</h2>
            <p className="text-sm text-gray-600 mb-3">
              Add the Granny Flat Check or other tools to your website — free for buyer&apos;s agents,
              builders, and property professionals. Takes about 10 minutes to set up.
            </p>
            <div className="flex flex-wrap gap-4 items-center">
              <a
                href="mailto:hello@plotdetect.com.au?subject=Embed%20program%20enquiry"
                className="text-teal-600 font-medium hover:text-teal-700 transition-colors text-sm"
              >
                hello@plotdetect.com.au
              </a>
              <Link
                href="/for/builders"
                className="text-sm text-teal-700 underline underline-offset-2 hover:text-teal-900 transition-colors"
              >
                See embed details →
              </Link>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-1">Privacy &amp; data requests</h2>
            <p className="text-sm text-gray-500 mb-3">
              To request deletion of your data or ask about how we handle personal information.
            </p>
            <a
              href="mailto:hello@plotdetect.com.au?subject=Privacy%20request"
              className="text-teal-600 font-medium hover:text-teal-700 transition-colors"
            >
              hello@plotdetect.com.au
            </a>
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-10">
          We typically respond within 1 business day.
        </p>
      </div>

      <SiteFooter />
    </main>
  );
}
