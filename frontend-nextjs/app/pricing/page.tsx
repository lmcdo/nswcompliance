import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'Pricing — PlotDetect',
  description: 'Free property risk checks for any NSW address. Professional reports from $39. Site Controls Pro for planning professionals at $49/month.',
};

function Check() {
  return (
    <svg className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}

function Dash() {
  return <span className="w-4 text-gray-300 shrink-0 mt-0.5 text-center">—</span>;
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
      <section className="px-6 pb-16 max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Free checks */}
          <div className="rounded-2xl border border-gray-200 p-8 flex flex-col">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">Everyone</p>
              <h2 className="text-2xl font-bold text-gray-900">Free checks</h2>
              <p className="text-gray-500 text-sm mt-2">
                Instant risk verdicts for any NSW address. No account, no credit card.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">$0</div>
            <p className="text-sm text-gray-400 mb-8">Always free</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                { text: 'Flood risk verdict', sub: 'In flood zone or not — LEP overlay check' },
                { text: 'Bushfire prone land check', sub: 'BFPL category — on the map or not' },
                { text: 'Granny flat eligibility', sub: 'Eligible or not, with reason' },
                { text: 'Solar yield indicator', sub: 'Estimated annual kWh — no system sizing' },
                { text: 'Shadow path verdict', sub: 'Impact or no impact from adjacent sites' },
                { text: 'Threat Radar summary', sub: 'DA count within 500m — no detail' },
                { text: 'Site history changes detected', sub: 'Change count — no timeline' },
                { text: 'Climate Risk Score', sub: 'Composite score out of 100 — 5 hazards' },
                { text: 'Site Controls — planning provisions', sub: '3 lookups per day — SEPP, LEP, DCP' },
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
                Full analysis with quantified outputs, compliance checklists, and a shareable PDF.
                One address, one purchase.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">$39–$49</div>
            <p className="text-sm text-gray-400 mb-8">Per property</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                { text: 'Solar Yield — $39', sub: 'System sizing, payback period, monthly kWh breakdown' },
                { text: 'Shadow Analysis — $39', sub: 'Seasonal diagrams, ADG compliance, objection evidence' },
                { text: 'Bushfire — $39', sub: 'BAL band estimation, AS 3959 requirements, RFS referral guidance' },
                { text: 'Flood Screening — $49', sub: 'Depth modelling, ARI return periods, BoM history, mitigation' },
                { text: 'Granny Flat — $49', sub: 'CDC compliance checklist, setbacks, rental yield analysis' },
                { text: 'Site History — $49', sub: '8-year satellite change detection, DA cross-reference' },
                { text: 'Conveyancing — $49', sub: 'LEP controls, overlays, DCP setbacks, heritage, feasibility' },
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
            <p className="text-xs text-gray-400 mb-4 border-t border-gray-100 pt-4">
              Pass through as a disbursement — same model as title searches.
              Volume pricing available for firms doing 8+ reports/month.
            </p>
            <Link
              href="/reports"
              className="block text-center py-3 px-6 bg-teal-600 text-white rounded-xl text-sm font-semibold hover:bg-teal-700 transition-colors"
            >
              Run free check first →
            </Link>
          </div>

          {/* Professional */}
          <div className="rounded-2xl border border-gray-200 p-8 flex flex-col">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">For planning professionals</p>
              <h2 className="text-2xl font-bold text-gray-900">Professional</h2>
              <p className="text-gray-500 text-sm mt-2">
                Unlimited Site Controls access, report credits, and property monitoring in one plan.
              </p>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-1">$149<span className="text-lg font-normal text-gray-400">/mo</span></div>
            <p className="text-sm text-gray-400 mb-8">Cancel anytime</p>
            <ul className="space-y-3 text-sm text-gray-700 mb-8 flex-1">
              {[
                'Site Controls Pro — unlimited lookups, all LGAs',
                'DA Mode — triage + annotation',
                'SEE scaffold export',
                'Development type filtering',
                '20 report credits/month (= $980 value)',
                '5 properties monitored (= $45 value)',
                'Priority LGA expansion requests',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <Check />
                  {item}
                </li>
              ))}
            </ul>

            <div className="border-t border-gray-100 pt-4 mb-4">
              <p className="text-xs text-gray-400">
                Annual billing: $119/mo ($1,428/year — save $360).
              </p>
            </div>

            <a
              href="mailto:hello@plotdetect.com.au?subject=Professional%20plan%20—%2014-day%20trial"
              className="block text-center py-3 px-6 border border-teal-500 text-teal-600 rounded-xl text-sm font-semibold hover:bg-teal-50 transition-colors"
            >
              Start 14-day free trial
            </a>
          </div>

        </div>
      </section>

      {/* Founding 50 */}
      <section className="px-6 pb-12 max-w-6xl mx-auto">
        <div className="rounded-2xl border-2 border-amber-400 bg-amber-50/50 p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="bg-amber-400 text-amber-900 text-xs font-bold px-3 py-0.5 rounded-full uppercase tracking-wider">
                  Limited
                </span>
                <p className="text-xs font-semibold uppercase tracking-widest text-amber-700">Founding 50 program</p>
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">$75/mo — 50% off Professional for Year 1</h3>
              <p className="text-sm text-gray-600 leading-relaxed max-w-lg">
                50 spots for planning professionals who want to shape the product.
                Full Professional access at half price for 12 months.
                In exchange: monthly feedback, case study rights, and a LinkedIn testimonial.
              </p>
              <p className="text-xs text-gray-400 mt-2">
                After Year 1, locked in at $119/mo (annual rate) for as long as you stay.
              </p>
            </div>
            <a
              href="mailto:hello@plotdetect.com.au?subject=Founding%2050%20—%20interested"
              className="shrink-0 inline-block px-6 py-3 bg-amber-500 text-white text-sm font-semibold rounded-xl hover:bg-amber-600 transition-colors"
            >
              Apply for a spot
            </a>
          </div>
        </div>
      </section>

      {/* Site Controls Pro standalone */}
      <section className="px-6 pb-12 max-w-6xl mx-auto">
        <div className="rounded-2xl border border-gray-200 bg-gray-50 p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">Site Controls Pro — $49/mo</h3>
              <p className="text-sm text-gray-500 max-w-lg">
                Unlimited compliance lookups across all LGAs. DA Mode, SEE scaffold export, development type filtering.
                For planners who need Site Controls daily but buy reports individually.
              </p>
              <p className="text-xs text-gray-400 mt-2">
                Annual: $39/mo ($468/year). Free tier: 3 lookups/day, no DA Mode.
              </p>
            </div>
            <a
              href="mailto:hello@plotdetect.com.au?subject=Site%20Controls%20Pro%20—%2014-day%20trial"
              className="shrink-0 inline-block px-5 py-2.5 border border-gray-300 text-sm font-medium text-gray-700 rounded-lg hover:bg-white transition-colors"
            >
              Start 14-day trial
            </a>
          </div>
        </div>
      </section>

      {/* Monitoring */}
      <section className="px-6 pb-12 max-w-6xl mx-auto">
        <div className="rounded-2xl border border-gray-200 bg-gray-50 p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">Property monitoring — $9/mo per property</h3>
              <p className="text-sm text-gray-500 max-w-lg">
                Weekly DA alerts for properties you care about — new applications within 200m, monthly digest summary.
                Cancel anytime via Stripe portal.
              </p>
            </div>
            <Link
              href="/reports/threat-radar"
              className="shrink-0 inline-block px-5 py-2.5 border border-gray-300 text-sm font-medium text-gray-700 rounded-lg hover:bg-white transition-colors"
            >
              Set up monitoring
            </Link>
          </div>
        </div>
      </section>

      {/* Bundle */}
      <section className="px-6 pb-12 max-w-6xl mx-auto">
        <div className="rounded-2xl border border-gray-200 bg-gray-50 p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">Pre-auction bundle — $149</h3>
              <p className="text-sm text-gray-500 max-w-lg">
                All 7 standard reports for one address. Flood, bushfire, solar, shadow, granny flat,
                site history, and conveyancing disclosure. Save up to $145.
              </p>
            </div>
            <Link
              href="/reports"
              className="shrink-0 inline-block px-5 py-2.5 border border-gray-300 text-sm font-medium text-gray-700 rounded-lg hover:bg-white transition-colors"
            >
              Run free checks first
            </Link>
          </div>
        </div>
      </section>

      {/* Climate Risk — coming */}
      <section className="px-6 pb-16 max-w-6xl mx-auto">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">Coming soon</p>
              <h3 className="text-lg font-bold text-gray-900">Climate Risk Report — $99</h3>
              <p className="text-sm text-gray-500 mt-1 max-w-lg">
                NARCliM 2.0 climate projections, compound hazard scoring, and trajectory analysis to 2090.
                Available after PlotDetect Pty Ltd incorporation and professional indemnity insurance.
              </p>
              <p className="text-xs text-gray-400 mt-2">
                The free Climate Risk Score (composite rating out of 100) is available now for any NSW address.
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

      {/* Comparison table */}
      <section className="px-6 pb-16 max-w-6xl mx-auto">
        <h2 className="text-xl font-bold text-gray-900 mb-6 text-center">What you get at each level</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-500 w-1/3">Feature</th>
                <th className="text-center py-3 px-4 font-medium text-gray-500">Free</th>
                <th className="text-center py-3 px-4 font-medium text-teal-600">Report</th>
                <th className="text-center py-3 px-4 font-medium text-gray-500">Professional</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[
                { feature: 'Risk verdict (yes/no)', free: true, report: true, pro: true },
                { feature: 'Quantified analysis (depths, BAL, kWh)', free: false, report: true, pro: true },
                { feature: 'Compliance checklist', free: false, report: true, pro: true },
                { feature: 'Shareable PDF report', free: false, report: true, pro: true },
                { feature: 'Site Controls lookups', free: '3/day', report: '3/day', pro: 'Unlimited' },
                { feature: 'DA Mode + SEE scaffold', free: false, report: false, pro: true },
                { feature: 'Report credits', free: false, report: 'Pay per report', pro: '20/month' },
                { feature: 'Property monitoring', free: false, report: '$9/mo add-on', pro: '5 included' },
                { feature: 'Volume pricing', free: false, report: false, pro: true },
              ].map(({ feature, free, report, pro }) => (
                <tr key={feature}>
                  <td className="py-3 px-4 text-gray-700">{feature}</td>
                  {[free, report, pro].map((val, i) => (
                    <td key={i} className="py-3 px-4 text-center">
                      {val === true ? (
                        <svg className="w-4 h-4 text-teal-500 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      ) : val === false ? (
                        <span className="text-gray-300">—</span>
                      ) : (
                        <span className="text-xs text-gray-600">{val}</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-slate-50 border-t border-slate-100 py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-8 text-center">Common questions</h2>
          <dl className="space-y-6">
            {[
              {
                q: 'What do the free checks actually show?',
                a: 'Each free check gives you the verdict — flood zone or not, bushfire prone or not, granny flat eligible or not. Enough to know if there\'s a risk. The paid report gives you the depth: how deep, which BAL band, what the CDC checklist requires, and a professional PDF you can send to a builder or conveyancer.',
              },
              {
                q: 'Why $39 minimum for reports?',
                a: 'A Section 10.7 planning certificate from council costs $53–$178. Our reports provide more detail (hazard analysis, compliance checklists, actionable recommendations) at a lower price. Pricing below $39 would signal hobby-grade work — this is professional infrastructure.',
              },
              {
                q: 'Can I use this as a conveyancer or buyers agent?',
                a: 'Yes. Individual reports are one-off purchases — pass them through as a disbursement, same model as title searches. For 8+ reports per month, contact us for volume pricing or consider the Professional plan.',
              },
              {
                q: 'What is the Founding 50 program?',
                a: 'We\'re offering 50 planning professionals full Professional access at half price ($75/mo) for Year 1. In exchange: monthly feedback call, case study rights, and a LinkedIn testimonial. It\'s how we build a product that actually fits your workflow.',
              },
              {
                q: 'What does Site Controls Pro add over the free tier?',
                a: 'The free Site Controls tier gives you 3 lookups per day — enough to try it. Site Controls Pro removes the limit and adds DA Mode (triage + annotation), SEE scaffold export, and development type filtering. PropCode charges $49.95 per individual report for less coverage.',
              },
              {
                q: 'What is the pre-auction bundle?',
                a: 'All 7 standard reports (solar, shadow, bushfire, flood, granny flat, site history, conveyancing) for one address at $149 instead of $313. Covers every hazard and planning dimension before you bid.',
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
