import type { Metadata } from 'next';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'Contact — PlotDetect',
  description: 'Get in touch with PlotDetect — questions or feedback.',
};

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <div className="max-w-2xl mx-auto px-6 py-14">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Get in touch</h1>
        <p className="text-gray-500 mb-10">
          Questions or feedback about Council Rules and Site Facts.
        </p>

        <div className="space-y-6">
          <div className="rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-1">General enquiries</h2>
            <p className="text-sm text-gray-500 mb-3">
              Questions about data sources or how the tools work.
            </p>
            <a
              href="mailto:hello@plotdetect.com.au"
              className="text-teal-600 font-medium hover:text-teal-700 transition-colors"
            >
              hello@plotdetect.com.au
            </a>
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

        <p className="text-sm text-gray-500 mt-10">
          Pilot users: if a rule looks wrong, tell us at{' '}
          <a
            href="mailto:hello@plotdetect.com.au?subject=Wrong rule"
            className="text-teal-600 font-medium hover:text-teal-700 transition-colors"
          >
            hello@plotdetect.com.au
          </a>
          .
        </p>
      </div>

      <SiteFooter />
    </main>
  );
}
