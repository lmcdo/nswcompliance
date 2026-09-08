import type { Metadata } from 'next';
import Link from 'next/link';
import { Building2, ArrowRight } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'For Builders & Planners — PlotDetect',
  description: 'Embed free NSW property intelligence tools on your website. Qualified homeowners come to you. Revenue share on paid reports.',
};

const TOOLS = [
  {
    name: 'Granny Flat Eligibility',
    slug: 'granny-flat',
    description: 'Checks SEPP Housing eligibility, lot size, zoning, and existing structures via satellite.',
    audience: 'Builders, display centres, mortgage brokers',
  },
  {
    name: 'Flood Screening',
    slug: 'flood',
    description: 'Modelled flood depth (ARI) and LEP flood control lot status by address.',
    audience: 'Conveyancers, insurance brokers',
  },
  {
    name: 'Solar Yield',
    slug: 'solar-yield',
    description: 'Estimated annual solar yield from roof geometry and orientation.',
    audience: 'Solar installers, energy brokers',
  },
  {
    name: 'Threat Radar',
    slug: 'threat-radar',
    description: 'Active DAs and CDCs lodged within 500m in the last 90 days.',
    audience: 'Property managers, developers',
  },
  {
    name: 'Shadow Detector',
    slug: 'shadow',
    description: 'Shadow path analysis at 9am, noon, and 3pm on the winter solstice.',
    audience: 'Town planners, building certifiers',
  },
];

export default function BuildersPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            For builders & planners
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
          Qualified homeowners from your own website
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          Add any PlotDetect tool to your website for free. Your clients get instant answers.
          You get more time on their site and a referral cut on any paid reports they buy.
        </p>
      </section>

      {/* How it works */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            { step: '1', title: 'Pick a tool', body: 'Choose the tool most relevant to your audience — granny flat for builders, flood for conveyancers, solar for installers.' },
            { step: '2', title: 'Paste one line', body: 'Copy the iframe snippet and paste it anywhere on your website. No login, no API key, no configuration.' },
            { step: '3', title: 'Earn on conversions', body: 'Add your referral ID. Any paid report purchased by a visitor you send earns you 20% of the sale.' },
          ].map(({ step, title, body }) => (
            <div key={step} className="space-y-2">
              <div className="w-8 h-8 rounded-full bg-teal-600 text-white text-sm font-bold flex items-center justify-center">
                {step}
              </div>
              <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
              <p className="text-sm text-gray-500">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Revenue share */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <div className="p-5 border border-teal-200 bg-teal-50 rounded-xl">
          <h2 className="font-semibold text-teal-900 mb-1">Revenue share</h2>
          <p className="text-sm text-teal-800">
            Add <code className="bg-teal-100 px-1 rounded text-xs">?ref=yourname</code> to the
            iframe URL. Any paid report purchased by a visitor from your embed earns you{' '}
            <strong>20% of the sale price</strong>. Paid monthly via bank transfer.
            No minimum threshold.
          </p>
          <p className="text-sm text-teal-700 mt-2">
            To register: email{' '}
            <a href="mailto:partners@plotdetect.com.au" className="underline">
              partners@plotdetect.com.au
            </a>{' '}
            with your website URL and which tool you want to embed.
          </p>
        </div>
      </section>

      {/* Embed snippets */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Embed snippets</h2>
        <div className="space-y-6">
          {TOOLS.map((tool) => (
            <div key={tool.slug} className="border border-gray-200 rounded-xl p-5">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold text-gray-900">{tool.name}</h3>
                  <p className="text-sm text-gray-500 mt-0.5">{tool.description}</p>
                  <p className="text-xs text-gray-400 mt-1">Best for: {tool.audience}</p>
                </div>
                <Link
                  href={`/reports/${tool.slug}`}
                  className="shrink-0 text-xs text-teal-600 hover:text-teal-700 ml-4"
                >
                  Preview →
                </Link>
              </div>
              <div className="mt-3">
                <p className="text-xs font-medium text-gray-500 mb-1.5">Copy this snippet:</p>
                <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs text-gray-700 overflow-x-auto leading-relaxed whitespace-pre-wrap break-all">
{`<iframe
  src="https://verify.plotdetect.com.au/embed/${tool.slug}?ref=YOUR_REF"
  width="100%"
  height="600"
  frameborder="0"
  style="border-radius: 12px; border: 1px solid #e5e7eb;"
  title="${tool.name} — PlotDetect"
></iframe>`}
                </pre>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Verify for planners */}
      <section className="bg-gray-50 border-y border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            For town planners and certifiers
          </h2>
          <p className="text-gray-500 mb-4">
            Site Controls extracts DCP provisions, SEPP standards, and LEP controls for any property
            and development type. Free to use — no account required.
          </p>
          <Link
            href="/assessment"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
          >
            Open Site Controls
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <div className="p-6 border border-gray-200 rounded-xl text-center">
          <h3 className="font-semibold text-gray-900 mb-2">Ready to embed?</h3>
          <p className="text-sm text-gray-500 mb-4">
            Email us your website URL and which tool you want. We will confirm your referral ID
            and you can be live today.
          </p>
          <a
            href="mailto:partners@plotdetect.com.au?subject=Embed%20program%20enquiry"
            className="inline-block px-6 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
          >
            partners@plotdetect.com.au
          </a>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
