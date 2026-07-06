import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'CDC vs DA: Which Approval Pathway Do You Need in NSW? — PlotDetect',
  description:
    'Complying Development Certificates take 10-20 days at lower cost. Development Applications take 40-90+ days. Here is how to know which pathway applies to your project, and what blocks the faster option.',
  keywords: [
    'cdc vs da nsw',
    'complying development certificate',
    'cdc approval nsw',
    'development application nsw',
    'complying development',
    'cdc eligibility',
    'exempt development nsw',
    'do i need council approval',
    'cdc or da',
    'complying development certificate cost',
  ],
};

/* ------------------------------------------------------------------ */
/*  Decision flowchart component                                       */
/* ------------------------------------------------------------------ */

function PathwayDecisionTree() {
  const steps = [
    {
      question: 'Is the work exempt development?',
      detail: 'Minor works like small decks (<25m², <1m above ground), garden sheds (<20m²), fences, painting, minor internal alterations.',
      yes: 'No approval needed. Proceed without council or certifier involvement.',
      no: 'Continue to next check.',
    },
    {
      question: 'Is the property in a heritage conservation area or individually heritage listed?',
      detail: 'Check your LEP Heritage Map or s10.7 certificate.',
      yes: 'CDC pathway is blocked for most work. You need a DA.',
      no: 'Continue to next check.',
    },
    {
      question: 'Is the property on flood prone land?',
      detail: 'Check the LEP Flood Planning map or council flood records.',
      yes: 'CDC pathway is blocked. You need a DA (with flood impact assessment).',
      no: 'Continue to next check.',
    },
    {
      question: 'Is the property in a bushfire prone area?',
      detail: 'Check the RFS Bush Fire Prone Land map.',
      yes: 'CDC may still be possible but requires a BAL assessment and compliance with Planning for Bush Fire Protection.',
      no: 'Continue to next check.',
    },
    {
      question: 'Does the proposed work comply with all standards in the relevant Code?',
      detail: 'Codes SEPP (Exempt & Complying) or Housing SEPP. Check setbacks, height, FSR, lot size requirements.',
      yes: 'CDC pathway is available. Apply to council or a private certifier.',
      no: 'You need a DA. The standards are not negotiable for CDC — any non-compliance means you need the DA pathway.',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Decision flowchart — CDC or DA?
      </p>
      <div className="relative pl-6">
        <div className="absolute left-[11px] top-3 bottom-3 w-0.5 bg-slate-200" />
        {steps.map((step, i) => (
          <div key={i} className="relative pb-8 last:pb-0">
            <div className="absolute left-[-17px] top-1 w-3 h-3 rounded-full bg-white border-2 border-slate-400" />
            <p className="font-semibold text-slate-900 text-sm mb-1">{step.question}</p>
            <p className="text-xs text-slate-500 mb-2">{step.detail}</p>
            <div className="flex gap-3 text-xs">
              <span className="px-2.5 py-1 rounded-full bg-green-50 text-green-700 border border-green-200">
                Yes → {step.yes.length > 60 ? step.yes.slice(0, 57) + '...' : step.yes}
              </span>
            </div>
            {step.no && (
              <div className="mt-1.5 text-xs">
                <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                  No → {step.no}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Comparison table                                                   */
/* ------------------------------------------------------------------ */

function ComparisonTable() {
  const rows = [
    { factor: 'Typical timeframe', cdc: '10–20 business days', da: '40–90+ business days' },
    { factor: 'Who assesses', cdc: 'Private certifier or council', da: 'Council only' },
    { factor: 'Typical cost', cdc: '$2,000–$5,000 (certifier fees)', da: '$3,000–$15,000+ (council fees, reports)' },
    { factor: 'Neighbour notification', cdc: 'Not required', da: 'Required (14–30 days)' },
    { factor: 'Design flexibility', cdc: 'Must meet all standards exactly', da: 'Merit-based — variations possible' },
    { factor: 'Appeal rights', cdc: 'Limited', da: 'Full appeal to Land & Environment Court' },
    { factor: 'Works during assessment', cdc: 'Can start once issued', da: 'Cannot start until consent granted' },
    { factor: 'DCP compliance', cdc: 'Codes SEPP standards apply instead of DCP', da: 'DCP controls apply (s4.15 assessment)' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 overflow-hidden my-6">
      <table className="w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="text-left py-3 px-4 font-semibold text-slate-900">Factor</th>
            <th className="text-left py-3 px-4 font-semibold text-teal-700">CDC</th>
            <th className="text-left py-3 px-4 font-semibold text-blue-700">DA</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ factor, cdc, da }) => (
            <tr key={factor} className="border-t border-slate-100">
              <td className="py-2.5 px-4 text-slate-700 font-medium">{factor}</td>
              <td className="py-2.5 px-4 text-slate-600">{cdc}</td>
              <td className="py-2.5 px-4 text-slate-600">{da}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function CDCvDAPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="CDC vs DA: Which Approval Pathway Do You Need in NSW?"
        description="Complying Development Certificates take 10-20 days at lower cost. Development Applications take 40-90+ days. Here is how to know which pathway applies to your project, and what blocks the faster option."
        slug="cdc-vs-da-which-approval-pathway"
        date="2026-05-20"
      />

      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-700">
            Planning Rules
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          CDC vs DA: which approval pathway do you need?
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          A Complying Development Certificate (CDC) takes 10–20 days and costs less. A Development
          Application (DA) takes 40–90+ days and costs more. The difference comes down to whether
          your project meets every standard in the relevant planning code — and whether your site
          has any blockers like heritage, flooding, or bushfire.
        </p>
      </div>

      <ComparisonTable />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">In this article</p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li><a href="#three-pathways" className="hover:text-teal-600">The three approval pathways</a></li>
          <li><a href="#what-is-cdc" className="hover:text-teal-600">What is a Complying Development Certificate?</a></li>
          <li><a href="#what-blocks-cdc" className="hover:text-teal-600">What blocks the CDC pathway</a></li>
          <li><a href="#when-da" className="hover:text-teal-600">When you need a DA</a></li>
          <li><a href="#housing-sepp" className="hover:text-teal-600">How the Housing SEPP expanded CDC</a></li>
          <li><a href="#common-mistakes" className="hover:text-teal-600">Common mistakes</a></li>
          <li><a href="#check-eligibility" className="hover:text-teal-600">How to check your eligibility</a></li>
        </ul>
      </nav>

      <PathwayDecisionTree />

      {/* Body */}
      <div className="space-y-10">

        <section id="three-pathways" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">The three approval pathways</h2>
          <p className="text-slate-700 leading-relaxed">
            NSW has three tiers of development approval under the Environmental Planning and
            Assessment Act 1979:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-green-200 bg-green-50/30 p-4">
              <p className="font-semibold text-green-800 text-sm mb-1">Exempt development</p>
              <p className="text-xs text-green-700">No approval needed. Minor works that meet prescribed standards — small sheds, fences, painting, internal alterations.</p>
            </div>
            <div className="rounded-xl border border-teal-200 bg-teal-50/30 p-4">
              <p className="font-semibold text-teal-800 text-sm mb-1">Complying development (CDC)</p>
              <p className="text-xs text-teal-700">Fast-track approval. Must meet every standard in the Codes SEPP or Housing SEPP. Assessed by a certifier or council.</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4">
              <p className="font-semibold text-blue-800 text-sm mb-1">Development Application (DA)</p>
              <p className="text-xs text-blue-700">Full merit assessment by council. Required when CDC standards can&apos;t be met, or site has heritage/flood/bushfire constraints.</p>
            </div>
          </div>
        </section>

        <section id="what-is-cdc" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What is a Complying Development Certificate?</h2>
          <p className="text-slate-700 leading-relaxed">
            A CDC is an approval pathway for development that meets all the pre-set standards in a
            State Environmental Planning Policy — primarily the{' '}
            <em>State Environmental Planning Policy (Exempt and Complying Development Codes) 2008</em>{' '}
            (Codes SEPP) and the <em>State Environmental Planning Policy (Housing) 2021</em> (Housing SEPP).
          </p>
          <p className="text-slate-700 leading-relaxed">
            The key difference from a DA: there is no discretion. If your project meets every numerical
            standard — setbacks, height, FSR, lot size, landscaping — the certifier must issue the CDC.
            There is no design review, no neighbour notification, and no merit assessment. This is what
            makes it faster (10–20 days vs 40–90+ days) and cheaper.
          </p>
          <p className="text-slate-700 leading-relaxed">
            CDCs can be issued by council or by a private certifier (registered under the Building and
            Development Certifiers Act 2018). Private certifiers are often faster because they don&apos;t
            have the queue that councils do.
          </p>
        </section>

        <section id="what-blocks-cdc" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What blocks the CDC pathway</h2>
          <p className="text-slate-700 leading-relaxed">
            Even if your project is the right type and meets all the numerical standards, certain site
            characteristics block the CDC pathway entirely:
          </p>
          <ul className="space-y-3 text-slate-700">
            <li className="flex gap-2">
              <span className="text-red-500 font-bold flex-shrink-0">&#10005;</span>
              <span><strong>Heritage conservation area</strong> — most CDC pathways are excluded in HCAs. This is the most common blocker. Check with a{' '}
              <Link href="/tools/zoning-check" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">free zoning check</Link>.</span>
            </li>
            <li className="flex gap-2">
              <span className="text-red-500 font-bold flex-shrink-0">&#10005;</span>
              <span><strong>Heritage item</strong> — individually listed properties cannot use CDC for external works.</span>
            </li>
            <li className="flex gap-2">
              <span className="text-red-500 font-bold flex-shrink-0">&#10005;</span>
              <span><strong>Flood prone land</strong> — properties in flood planning areas are excluded from most CDC codes. The depth and frequency of flooding determines the impact on your project.</span>
            </li>
            <li className="flex gap-2">
              <span className="text-red-500 font-bold flex-shrink-0">&#10005;</span>
              <span><strong>Foreshore building line</strong> — properties within a foreshore building line mapped in the LEP.</span>
            </li>
            <li className="flex gap-2">
              <span className="text-amber-500 font-bold flex-shrink-0">&#9888;</span>
              <span><strong>Bushfire prone land</strong> — CDC is possible but requires a BAL assessment and compliance with the RFS document <em>Planning for Bush Fire Protection</em>. Higher BAL ratings may block CDC for some development types.</span>
            </li>
            <li className="flex gap-2">
              <span className="text-amber-500 font-bold flex-shrink-0">&#9888;</span>
              <span><strong>Critical habitat or environmentally sensitive land</strong> — check the Biodiversity Values Map.</span>
            </li>
          </ul>
        </section>

        <section id="when-da" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">When you need a DA</h2>
          <p className="text-slate-700 leading-relaxed">
            You need a Development Application when:
          </p>
          <ul className="space-y-2 text-slate-700">
            <li className="flex gap-2"><span className="text-blue-600">&#8226;</span> Your site has a CDC blocker (heritage, flood, foreshore)</li>
            <li className="flex gap-2"><span className="text-blue-600">&#8226;</span> Your project doesn&apos;t meet one or more CDC standards (e.g. setback is 4.5m, standard requires 5m)</li>
            <li className="flex gap-2"><span className="text-blue-600">&#8226;</span> Your development type isn&apos;t covered by the Codes SEPP or Housing SEPP (e.g. commercial, industrial, mixed use)</li>
            <li className="flex gap-2"><span className="text-blue-600">&#8226;</span> You want design flexibility — a DA allows merit assessment where a variation can be justified</li>
            <li className="flex gap-2"><span className="text-blue-600">&#8226;</span> Designated development (large scale or high impact) — always requires a DA and environmental assessment</li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            The DA advantage is flexibility. DCP controls apply, but clause 4.15 of the EP&amp;A Act
            allows council to consider variations on merit. If your front setback is 4.8m instead of
            the required 5m, a DA gives you the opportunity to argue the variation is acceptable. A
            CDC does not — it&apos;s pass or fail.
          </p>
        </section>

        <section id="housing-sepp" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">How the Housing SEPP expanded CDC</h2>
          <p className="text-slate-700 leading-relaxed">
            The <em>State Environmental Planning Policy (Housing) 2021</em> — commonly called the
            Housing SEPP — expanded the range of development types that can use the CDC pathway.
            In particular:
          </p>
          <ul className="space-y-2 text-slate-700">
            <li className="flex gap-2"><span className="text-teal-600">&#8226;</span> <strong>Secondary dwellings (granny flats)</strong> — CDC pathway on lots &ge;450m² in R1, R2, R3, R4, RU5 zones (subject to site exclusions)</li>
            <li className="flex gap-2"><span className="text-teal-600">&#8226;</span> <strong>Dual occupancy</strong> — expanded CDC eligibility in some zones</li>
            <li className="flex gap-2"><span className="text-teal-600">&#8226;</span> <strong>Manor houses</strong> (3–4 dwellings) — CDC in R1, R2, R3 zones on lots &ge;600m²</li>
            <li className="flex gap-2"><span className="text-teal-600">&#8226;</span> <strong>Multi-dwelling housing (terraces)</strong> — CDC in some R3 zones</li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            The Housing SEPP is particularly relevant for{' '}
            <Link href="/blog/can-i-build-a-granny-flat-nsw" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              granny flat eligibility
            </Link>
            {' '}— it&apos;s the instrument that made secondary dwellings broadly permissible as complying
            development across most residential zones in NSW.
          </p>
        </section>

        <section id="common-mistakes" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Common mistakes</h2>
          <div className="space-y-4">
            <div className="rounded-xl border border-amber-200 bg-amber-50/30 p-4">
              <p className="font-semibold text-amber-800 text-sm mb-1">Assuming CDC means no rules</p>
              <p className="text-xs text-amber-700">CDC has strict numerical standards. You must comply with every one. The trade-off for speed is zero flexibility.</p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50/30 p-4">
              <p className="font-semibold text-amber-800 text-sm mb-1">Not checking site exclusions first</p>
              <p className="text-xs text-amber-700">Check heritage, flood, and foreshore status before spending money on CDC drawings. These block the pathway entirely.</p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50/30 p-4">
              <p className="font-semibold text-amber-800 text-sm mb-1">Confusing DCP setbacks with CDC setbacks</p>
              <p className="text-xs text-amber-700">CDC uses the Codes SEPP standards, not the DCP. The{' '}
              <Link href="/blog/setback-requirements-nsw" className="text-amber-800 underline underline-offset-2">setback requirements</Link>
              {' '}are often different — sometimes more generous, sometimes stricter.</p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50/30 p-4">
              <p className="font-semibold text-amber-800 text-sm mb-1">Starting with a DA when CDC is available</p>
              <p className="text-xs text-amber-700">If your project meets the CDC standards, there is no benefit to a DA. It will take longer, cost more, and the outcome is less certain.</p>
            </div>
          </div>
        </section>

        <section id="check-eligibility" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">How to check your eligibility</h2>
          <p className="text-slate-700 leading-relaxed">
            Start by checking whether your site has any CDC blockers — heritage, flood, foreshore. Then
            check whether your proposed development type is covered by the Codes SEPP or Housing SEPP.
            Finally, verify that your design meets every numerical standard.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The{' '}
            <Link href="/check" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              PlotDetect Pre-DA Check
            </Link>{' '}
            runs the first two checks for any NSW address — it identifies site exclusions and tells you
            whether the CDC pathway is available for common development types. For the full picture
            including DCP setbacks and SEPP requirements, use the{' '}
            <Link href="/assessment" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              Verify tool
            </Link>.
          </p>
        </section>
      </div>

      <BlogDisclaimer />

      {/* CTA */}
      <section className="mt-4 space-y-6">
        <div className="rounded-2xl border border-violet-200 bg-violet-50/30 p-8">
          <h2 className="text-xl font-bold text-slate-900 mb-3">Check your CDC eligibility</h2>
          <p className="text-slate-600 mb-4 leading-relaxed">
            Enter your address to see whether the CDC pathway is available for your property —
            heritage, flood, bushfire, and zone checks in one step.
          </p>
          <TrackedLink
            href="/check"
            className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-500 transition-colors"
            page="cdc-vs-da-which-approval-pathway"
            cta="check_address"
          >
            Pre-DA Check — free
            <ArrowRight className="w-4 h-4" />
          </TrackedLink>
        </div>
      </section>

      <div className="pt-8 border-t border-slate-100">
        <Link href="/blog" className="text-sm text-slate-500 hover:text-teal-600 transition-colors">
          &larr; Back to Insights
        </Link>
      </div>
    </article>
  );
}
