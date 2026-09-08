import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'Embed Program — PlotDetect',
  description: 'Add free NSW property intelligence tools to your website. Granny flat, flood, solar, and DA activity checks for your clients.',
};

const TOOLS = [
  {
    name: 'Granny Flat Eligibility',
    slug: 'granny-flat',
    description: 'Checks SEPP Housing eligibility, lot size, zoning, and existing structures via satellite.',
    audience: 'Builders, display centres, mortgage brokers, buyer\'s agents',
    color: 'teal',
  },
  {
    name: 'Flood Screening',
    slug: 'flood',
    description: 'Modelled flood depth (ARI) and LEP flood control lot status by address.',
    audience: 'Conveyancers, buyer\'s agents, insurance brokers',
    color: 'blue',
  },
  {
    name: 'Solar Yield',
    slug: 'solar-yield',
    description: 'Estimated annual solar yield from roof geometry and orientation.',
    audience: 'Solar installers, builders, energy brokers',
    color: 'amber',
  },
  {
    name: 'Shadow Detector',
    slug: 'shadow',
    description: 'Shadow path analysis at 9am, noon, and 3pm on the winter solstice.',
    audience: 'Town planners, building certifiers, objectors',
    color: 'slate',
  },
  {
    name: 'Threat Radar',
    slug: 'threat-radar',
    description: 'Active DAs and CDCs lodged within 500m in the last 90 days.',
    audience: 'Buyer\'s agents, property managers, developers',
    color: 'violet',
  },
];

const BORDER: Record<string, string> = {
  teal: 'border-teal-200 bg-teal-50',
  blue: 'border-blue-200 bg-blue-50',
  amber: 'border-amber-200 bg-amber-50',
  slate: 'border-slate-200 bg-slate-50',
  violet: 'border-violet-200 bg-violet-50',
};

export default function PartnerPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <div className="max-w-3xl mx-auto px-6 py-14">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">Embed program</h1>
          <p className="text-gray-500 text-base max-w-xl">
            Add any of our NSW property intelligence tools to your website for free.
            Your clients get instant answers. You get more time on their site and a referral cut
            on any paid reports they buy.
          </p>
        </div>

        {/* How it works */}
        <div className="mb-12 grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            { step: '1', title: 'Pick a tool', body: 'Choose the tool most relevant to your audience — granny flat for builders, flood for conveyancers, solar for installers.' },
            { step: '2', title: 'Paste one line', body: 'Copy the iframe snippet below and paste it anywhere on your website. No login, no API key, no configuration.' },
            { step: '3', title: 'Earn on conversions', body: 'Add your referral ID to the snippet. Any paid report purchased by a visitor you send earns you 20% of the sale.' },
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

        {/* Revenue share */}
        <div className="mb-12 p-5 border border-teal-200 bg-teal-50 rounded-xl">
          <h2 className="font-semibold text-teal-900 mb-1">Revenue share</h2>
          <p className="text-sm text-teal-800">
            Add <code className="bg-teal-100 px-1 rounded text-xs">?ref=yourname</code> to the
            iframe URL. Any paid report purchased by a visitor from your embed earns you{' '}
            <strong>20% of the sale price</strong>. Paid monthly via bank transfer.
            No minimum threshold.
          </p>
          <p className="text-sm text-teal-700 mt-2">
            To register for revenue share: email{' '}
            <a href="mailto:partners@plotdetect.com.au" className="underline">
              partners@plotdetect.com.au
            </a>{' '}
            with your website URL and which tool you want to embed.
          </p>
        </div>

        {/* Tool snippets */}
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Embed snippets</h2>
        <div className="space-y-8">
          {TOOLS.map((tool) => (
            <div key={tool.slug} className={`border rounded-xl p-5 ${BORDER[tool.color]}`}>
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
                <pre className="bg-white border border-gray-200 rounded-lg p-3 text-xs text-gray-700 overflow-x-auto leading-relaxed whitespace-pre-wrap break-all">
{`<iframe
  src="https://verify.plotdetect.com.au/embed/${tool.slug}?ref=YOUR_REF"
  width="100%"
  height="600"
  frameborder="0"
  style="border-radius: 12px; border: 1px solid #e5e7eb;"
  title="${tool.name} — PlotDetect"
></iframe>`}
                </pre>
                <p className="text-xs text-gray-400 mt-1.5">
                  Replace <code className="bg-gray-100 px-1 rounded">YOUR_REF</code> with your referral ID (or remove <code className="bg-gray-100 px-1 rounded">?ref=</code> entirely if not participating in revenue share).
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div className="mt-16 space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">Common questions</h2>
          {[
            {
              q: 'Is the embed free?',
              a: 'Yes. All five tools are free to embed. You pay nothing. Your visitors pay nothing for the basic check. Paid reports ($39–$49) are optional upgrades.',
            },
            {
              q: 'Do I need a developer?',
              a: 'No. Paste the iframe code anywhere on your page — a text block in WordPress, a page section in Squarespace or Webflow, or a custom HTML element. No backend required.',
            },
            {
              q: 'Can I embed on multiple pages?',
              a: 'Yes. Embed any combination of tools on any pages. Each can have the same or different referral ID.',
            },
            {
              q: 'How is revenue share tracked?',
              a: 'Via the ?ref= parameter in the iframe URL. When a visitor pays for a report, we match the referral ID to your account and pay you 20% of the report price monthly.',
            },
            {
              q: 'What does it look like on mobile?',
              a: 'The tools are responsive and work on all screen sizes. Set height to 700px on mobile or use a CSS media query to adjust.',
            },
          ].map(({ q, a }) => (
            <div key={q}>
              <p className="font-medium text-gray-800 text-sm mb-1">{q}</p>
              <p className="text-sm text-gray-500">{a}</p>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="mt-12 p-6 border border-gray-200 rounded-xl text-center">
          <h3 className="font-semibold text-gray-900 mb-2">Ready to embed?</h3>
          <p className="text-sm text-gray-500 mb-4">
            Email us your website URL and which tool you want. We&apos;ll confirm your referral ID and you can be live today.
          </p>
          <a
            href="mailto:partners@plotdetect.com.au?subject=Embed program enquiry"
            className="inline-block px-6 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
          >
            partners@plotdetect.com.au →
          </a>
        </div>
      </div>

      <SiteFooter />
    </main>
  );
}
