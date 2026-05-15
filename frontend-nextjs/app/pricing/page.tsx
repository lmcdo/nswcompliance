import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'Pricing — PlotDetect',
  description: 'Free NSW property intelligence tools. Professional reports from $19. Monitoring from $9/month.',
};

function Check() {
  return (
    <svg className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav maxWidth="max-w-6xl" />

      {/* Header */}
      <section className="pt-16 pb-12 px-6 text-center max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">Simple pricing</h1>
        <p className="text-gray-500 text-lg">
          Free checks reveal risk. Paid reports resolve it.
        </p>
      </section>

      {/* Three columns */}
      <section className="px-6 pb-16 max-w-5xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Free tools */}
          <div className="rounded-2xl border border-gray-200 p-8 flex flex-col">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">Everyone</p>
              <h2 className="text-2xl font-bold text-gray-900">Free tools</h2>
              <p className="text-gray-500 text-sm mt-2">
                No account, no credit card. Run any check as many times as you like.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">$0</div>
            <p className="text-sm text-gray-400 mb-8">Always free</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                'Flood risk check (LEP overlay + depth where available)',
                'Bushfire pre-screen (BFPL + BAL band)',
                'Conveyancing planning disclosure',
                'Granny flat eligibility check',
                'Neighbour Threat Radar (DAs within 500m)',
                'Shadow path analysis',
                'Solar yield estimate',
                'Pre-DA site history (changes detected)',
                'Verify — full compliance engine (SEPP/LEP/DCP)',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <Check />
                  {item}
                </li>
              ))}
            </ul>
            <Link
              href="/reports"
              className="block text-center py-3 px-6 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Start checking
            </Link>
          </div>

          {/* Reports — highlighted */}
          <div className="rounded-2xl border-2 border-teal-500 p-8 flex flex-col relative shadow-lg">
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
              <span className="bg-teal-500 text-white text-xs font-semibold px-4 py-1 rounded-full">
                Most popular
              </span>
            </div>
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-teal-600 mb-2">One-off purchase</p>
              <h2 className="text-2xl font-bold text-gray-900">Reports</h2>
              <p className="text-gray-500 text-sm mt-2">
                Professional PDF with full analysis and actionable next steps. One address, one purchase.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">$19–$49</div>
            <p className="text-sm text-gray-400 mb-8">Per property</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                { text: 'Solar Yield — $19', sub: 'System sizing, payback, monthly kWh' },
                { text: 'Shadow Analysis — $29', sub: 'Seasonal diagrams, ADG compliance' },
                { text: 'Bushfire — $29', sub: 'BAL band, AS 3959, RFS referral guidance' },
                { text: 'Flood Risk — $49', sub: 'Depth modelling, ARI bands, BoM history' },
                { text: 'Granny Flat — $49', sub: 'CDC checklist, setbacks, yield analysis' },
                { text: 'Site History — $49', sub: 'Satellite change detection, DA search' },
                { text: 'Conveyancing — $49', sub: 'LEP, overlays, DCP setbacks, heritage' },
              ].map(({ text, sub }) => (
                <li key={text} className="flex items-start gap-2">
                  <Check />
                  <span>
                    <span className="font-medium">{text}</span>
                    <span className="block text-xs text-gray-400 mt-0.5">{sub}</span>
                  </span>
                </li>
              ))}
            </ul>
            <Link
              href="/reports"
              className="block text-center py-3 px-6 bg-teal-600 text-white rounded-xl text-sm font-semibold hover:bg-teal-700 transition-colors"
            >
              Run free check first →
            </Link>
          </div>

          {/* Monitoring + Bundle */}
          <div className="rounded-2xl border border-gray-200 p-8 flex flex-col">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">Ongoing</p>
              <h2 className="text-2xl font-bold text-gray-900">Monitoring</h2>
              <p className="text-gray-500 text-sm mt-2">
                Weekly DA alerts for properties you care about. Cancel anytime.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">$9/mo</div>
            <p className="text-sm text-gray-400 mb-8">Per property</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                'Weekly email alerts for new DAs within 200m',
                'Monthly digest summary',
                'Cancel anytime via Stripe portal',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <Check />
                  {item}
                </li>
              ))}
            </ul>

            <div className="border-t border-gray-100 pt-6 mt-auto">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">Save with a bundle</p>
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="font-bold text-gray-900">$149</p>
                <p className="text-sm text-gray-500 mt-1">
                  All 7 standard reports for one address. Save up to $145.
                </p>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* Climate Risk — coming */}
      <section className="px-6 pb-16 max-w-5xl mx-auto">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">Coming soon</p>
              <h3 className="text-lg font-bold text-gray-900">Climate Risk Report — $99</h3>
              <p className="text-sm text-gray-500 mt-1 max-w-lg">
                NARCliM 2.0 climate projections, compound hazard scoring, and trajectory analysis.
                Available after PlotDetect Pty Ltd incorporation and professional indemnity insurance.
              </p>
              <p className="text-xs text-gray-400 mt-2">
                The free Climate Risk Score (composite rating) is available now for any NSW address.
              </p>
            </div>
            <a
              href="mailto:hello@plotdetect.com.au?subject=Climate%20Risk%20Report%20interest"
              className="shrink-0 inline-block px-5 py-2.5 border border-slate-300 text-sm font-medium text-slate-700 rounded-lg hover:bg-white transition-colors"
            >
              Register interest
            </a>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-slate-50 border-t border-slate-100 py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-8 text-center">Common questions</h2>
          <dl className="space-y-6">
            {[
              {
                q: 'Are the free tools really free?',
                a: 'Yes. Every check runs live against NSW Government data and costs you nothing. No account, no credit card. Free forever.',
              },
              {
                q: 'What do the paid reports add?',
                a: 'The free check gives you the verdict. The paid report gives you the depth — full compliance checklists, setback calculations, yield analysis, and a shareable PDF you can send to a builder, certifier, or conveyancer.',
              },
              {
                q: 'Can I use this as a conveyancer or buyers agent?',
                a: 'Yes. Reports are one-off purchases — pass them through as a disbursement. For professional pricing and volume discounts, contact us.',
              },
              {
                q: 'What is the bundle?',
                a: 'All 7 standard reports (solar, shadow, bushfire, flood, granny flat, site history, conveyancing) for one address at $149 instead of $293. Useful for pre-auction due diligence.',
              },
              {
                q: 'Is this planning advice?',
                a: 'No. Results are indicative and based on publicly available planning data. Always consult a registered town planner or certifier before making decisions.',
              },
            ].map(({ q, a }) => (
              <div key={q}>
                <dt className="font-semibold text-gray-900 mb-1">{q}</dt>
                <dd className="text-sm text-gray-600 leading-relaxed">{a}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
