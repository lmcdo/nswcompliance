import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Pricing — canibuildit.com.au',
  description: 'Free NSW planning tools for everyone. Detailed reports for homeowners. Embed program for builders.',
};

function Check() {
  return (
    <svg className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}

function Cross() {
  return (
    <svg className="w-4 h-4 text-slate-300 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto border-b border-gray-100">
        <Link href="/" className="text-lg font-bold tracking-tight text-gray-900">
          canibuildit<span className="text-teal-600">.com.au</span>
        </Link>
        <Link href="/granny-flat" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
          Try the tools →
        </Link>
      </nav>

      {/* Header */}
      <section className="pt-16 pb-12 px-6 text-center max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">Simple pricing</h1>
        <p className="text-gray-500 text-lg">
          The tools are free. Pay only when you want more depth.
        </p>
      </section>

      {/* Three columns */}
      <section className="px-6 pb-20 max-w-5xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Homeowner */}
          <div className="rounded-2xl border border-gray-200 p-8 flex flex-col">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">Homeowner</p>
              <h2 className="text-2xl font-bold text-gray-900">Free tools</h2>
              <p className="text-gray-500 text-sm mt-2">
                Run any check as many times as you like. No account required.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">$0</div>
            <p className="text-sm text-gray-400 mb-8">Always free</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                'Granny Flat eligibility check',
                'Flood risk (LEP flood control lot)',
                'Solar yield estimate',
                'Shadow path analysis',
                'Nearby development radar',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <Check />
                  {item}
                </li>
              ))}
            </ul>
            <Link
              href="/granny-flat"
              className="block text-center py-3 px-6 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Start checking
            </Link>
          </div>

          {/* Detailed reports — highlighted */}
          <div className="rounded-2xl border-2 border-teal-500 p-8 flex flex-col relative shadow-lg">
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
              <span className="bg-teal-500 text-white text-xs font-semibold px-4 py-1 rounded-full">
                Most popular
              </span>
            </div>
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-teal-600 mb-2">Homeowner — report</p>
              <h2 className="text-2xl font-bold text-gray-900">Detailed reports</h2>
              <p className="text-gray-500 text-sm mt-2">
                Professional PDF with full analysis, compliance checklist, and actionable next steps.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">$19–$49</div>
            <p className="text-sm text-gray-400 mb-8">Per property, one-off</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                { text: 'Solar Yield — $19', sub: 'System sizing, payback, monthly kWh' },
                { text: 'Shadow Analysis — $29', sub: 'Seasonal diagrams, ADG compliance' },
                { text: 'Bushfire Pre-Screen — $29', sub: 'BAL band, AS 3959, RFS referral' },
                { text: 'Flood Risk — $49', sub: 'Depth modelling, ARI bands, BOM history' },
                { text: 'Granny Flat — $49', sub: 'CDC checklist, setbacks, yield analysis' },
                { text: 'Site History — $49', sub: 'Satellite change detection, DA search' },
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
              href="/granny-flat"
              className="block text-center py-3 px-6 bg-teal-600 text-white rounded-xl text-sm font-semibold hover:bg-teal-700 transition-colors"
            >
              Run free check first →
            </Link>
          </div>

          {/* Builder embed */}
          <div className="rounded-2xl border border-gray-200 p-8 flex flex-col">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">Builder / Agent</p>
              <h2 className="text-2xl font-bold text-gray-900">Embed program</h2>
              <p className="text-gray-500 text-sm mt-2">
                Add any tool to your own website. Qualified homeowners come to you.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">Free</div>
            <p className="text-sm text-gray-400 mb-8">to start — Partner plan $99/mo</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                { text: 'Embed any tool on your site', included: true },
                { text: 'Unbranded widget (white-label)', included: false },
                { text: 'Lead capture for eligible results', included: false },
                { text: 'Monthly lead report', included: false },
                { text: 'Priority support', included: false },
              ].map(({ text, included }) => (
                <li key={text} className="flex items-start gap-2">
                  {included ? <Check /> : <Cross />}
                  <span className={included ? '' : 'text-gray-400'}>{text}</span>
                </li>
              ))}
              <li className="text-xs text-gray-400 pt-2 italic">
                Cross/tick shows free vs Partner plan
              </li>
            </ul>
            <a
              href="mailto:hello@canibuildit.com.au?subject=Embed%20program%20enquiry"
              className="block text-center py-3 px-6 bg-gray-900 text-white rounded-xl text-sm font-semibold hover:bg-gray-800 transition-colors"
            >
              Get the embed code
            </a>
          </div>

        </div>
      </section>

      {/* FAQ strip */}
      <section className="bg-slate-50 border-t border-slate-100 py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-8 text-center">Common questions</h2>
          <dl className="space-y-6">
            {[
              {
                q: 'Are the free tools really free?',
                a: 'Yes. Every check runs live against the NSW Planning Portal and costs you nothing. No account, no credit card.',
              },
              {
                q: 'What do the paid reports add?',
                a: 'The free tool gives you the verdict. The paid report gives you the depth — full compliance checklists, setback calculations, yield sensitivity analysis, insurer checklists, and a shareable PDF you can send to a builder, certifier, or conveyancer. Prices range from $19 to $49 depending on the tool.',
              },
              {
                q: 'How does the builder embed work?',
                a: 'You paste one line of HTML onto your website. Visitors can check their address without leaving your site. Eligible results show your contact details. Free to start — the Partner plan adds lead capture and white-labelling.',
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

      {/* Footer */}
      <footer className="bg-[#0b1628] py-8 px-6 text-center">
        <p className="text-sm text-slate-600">
          © 2026 canibuildit.com.au — NSW planning intelligence for property owners and builders.
        </p>
      </footer>
    </main>
  );
}
