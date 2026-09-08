import 'maplibre-gl/dist/maplibre-gl.css';
// ^ must be imported in a server component to avoid dynamic chunk 404 (see AerialTile.tsx)
import type { Metadata } from 'next'
import Link from 'next/link'
import { GrannyFlatTool } from '@/components/tools/GrannyFlatTool'
import { sanitizeHTML } from '@/lib/sanitize'
import { SoftwareAppJsonLd } from '@/lib/json-ld'

export const metadata: Metadata = {
  title: 'Granny Flat Eligibility Check NSW — Free Instant SEPP Housing 2021 Check',
  description: 'Can you build a granny flat on your NSW property? Free instant check — lot size, zoning, heritage, flood, and biodiversity under SEPP Housing 2021. Any NSW address, no signup.',
}

const FAQS = [
  {
    q: 'What is the minimum lot size for a granny flat in NSW?',
    a: 'Under SEPP Housing 2021 (the state-wide policy that overrides local council rules), the minimum lot size for a secondary dwelling approved as complying development is 450 m². If your lot is below this threshold, a DA through your local council is required and approval is not guaranteed.',
  },
  {
    q: 'What zones allow granny flats in NSW?',
    a: 'SEPP Housing 2021 permits secondary dwellings as complying development in R1 General Residential, R2 Low Density Residential, R3 Medium Density Residential, and RU5 Village zones. Commercial, industrial, rural, and environmental protection zones do not qualify for the CDC pathway.',
  },
  {
    q: 'What is the difference between a CDC and a DA for a granny flat?',
    a: 'A Complying Development Certificate (CDC) is a fast-track approval from a private certifier — no council involvement, typically 10–20 business days. A Development Application (DA) goes through your local council, takes 40–100+ days, and can be refused. SEPP Housing 2021 only allows CDC if all eligibility checks pass. If any check fails — heritage, flood, lot size, zone — a DA is required.',
  },
  {
    q: 'Does heritage listing affect granny flat eligibility?',
    a: 'Yes. Properties that are individually heritage-listed under the LEP, or within a heritage conservation area, are excluded from SEPP Housing 2021 complying development. A DA with a heritage impact assessment is required. Heritage exclusions are most common in inner-city LGAs (Inner West, Woollahra, Randwick) and regional towns with colonial history.',
  },
  {
    q: 'Does flood risk affect granny flat eligibility?',
    a: 'Yes. Properties on a flood control lot — defined as land within a flood planning area under the LEP — are excluded from the CDC pathway. A DA with a flood risk management report is required. Flood exclusions are most significant in Hawkesbury, Campbelltown, Clarence Valley, and coastal LGAs.',
  },
  {
    q: 'How large can a granny flat be in NSW?',
    a: 'Under SEPP Housing 2021, a secondary dwelling is limited to 60 m² internal floor area. On lots over 900 m², an attached secondary dwelling may have different sizing provisions. DCP setback and height controls from your local council also apply regardless of SEPP eligibility.',
  },
  {
    q: 'Can a granny flat earn rental income?',
    a: 'Yes. Secondary dwellings approved under SEPP Housing 2021 can be independently tenanted. Current market rents for granny flats in Greater Sydney range from $280–$500/week depending on size, location, and fit-out. Regional NSW rents are typically $180–$320/week.',
  },
]

export default function GrannyFlatHubPage() {
  return (
    <div className="max-w-2xl mx-auto px-6">
      <SoftwareAppJsonLd
        name="Granny Flat Eligibility Check NSW"
        description="Can you build a granny flat on your NSW property? Free instant check — lot size, zoning, heritage, flood, and biodiversity under SEPP Housing 2021. Any NSW address, no signup."
        url="/granny-flat"
      />

      {/* THE TOOL */}
      <GrannyFlatTool />

      {/* How it works */}
      <div className="mt-12 border-t border-gray-100 pt-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">How the eligibility check works</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { step: '1', label: 'Enter address', detail: 'Any NSW residential address. We geocode it and look up your lot boundary.' },
            { step: '2', label: 'Check 6 criteria', detail: 'Lot area, zone, heritage items and conservation areas, flood control lots, biodiversity values, acid sulfate soils.' },
            { step: '3', label: 'Instant result', detail: 'Pass all six: CDC pathway is available. Fail any one: DA required. We show exactly which criterion failed.' },
          ].map(({ step, label, detail }) => (
            <div key={step} className="rounded-lg bg-gray-50 p-4">
              <div className="w-6 h-6 rounded-full bg-teal-100 text-teal-700 text-xs font-bold flex items-center justify-center mb-2">{step}</div>
              <p className="text-sm font-medium text-gray-900">{label}</p>
              <p className="text-xs text-gray-500 mt-1">{detail}</p>
            </div>
          ))}
        </div>
      </div>

      {/* SEPP rules summary */}
      <div className="mt-10 border-t border-gray-100 pt-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">SEPP Housing 2021 — key rules</h2>
        <p className="text-sm text-gray-500 mb-4">
          SEPP (State Environmental Planning Policy) Housing 2021 is the state-wide policy that
          gives property owners the right to build a secondary dwelling as complying development —
          bypassing council DA — if all criteria are met. Local councils cannot override SEPP Housing 2021
          for eligible properties.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { label: 'Min. lot area', value: '450 m²' },
            { label: 'Max. floor area', value: '60 m²' },
            { label: 'Approval path', value: 'CDC (private certifier)' },
            { label: 'Zones permitted', value: 'R1, R2, R3, RU5' },
            { label: 'Heritage items', value: 'Excluded' },
            { label: 'Flood control lots', value: 'Excluded' },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-gray-100 p-3">
              <p className="text-xs text-gray-400">{label}</p>
              <p className="text-sm font-medium text-gray-900 mt-0.5">{value}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-3">
          Source:{' '}
          <a
            href="https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0649"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline"
          >
            SEPP (Housing) 2021
          </a>
          {' '}— Cl 53. DCP setbacks and height controls from your local council also apply.
        </p>
      </div>

      {/* FAQ */}
      <div className="mt-10 border-t border-gray-100 pt-8 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">Common questions</h2>
        {FAQS.map((faq, i) => (
          <div key={i} className="border-b border-gray-100 pb-4">
            <p className="font-medium text-gray-900 text-sm">{faq.q}</p>
            <p className="text-sm text-gray-500 mt-1">{faq.a}</p>
          </div>
        ))}
      </div>

      {/* FAQ schema */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: sanitizeHTML(JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: FAQS.map(faq => ({
              '@type': 'Question',
              name: faq.q,
              acceptedAnswer: { '@type': 'Answer', text: faq.a },
            })),
          })),
        }}
      />

      {/* Cross-tool CTA */}
      <div className="mt-10 rounded-xl border border-gray-200 bg-gray-50 p-6 mb-4">
        <h3 className="font-semibold text-gray-900 mb-3">Other checks for your property</h3>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Flood Screening', desc: 'Statutory overlay + ARI data', href: '/flood-risk', color: 'text-blue-600' },
            { label: 'Solar Yield', desc: 'Roof yield estimate', href: '/solar-potential', color: 'text-amber-600' },
            { label: 'Shadow Check', desc: 'Summer + winter solstice', href: '/shadow', color: 'text-slate-600' },
            { label: 'Threat Radar', desc: 'Nearby DA + CDC activity', href: '/threat-radar', color: 'text-violet-600' },
          ].map(({ label, desc, href, color }) => (
            <Link key={href} href={href} className="rounded-lg border border-gray-200 bg-white p-4 hover:border-gray-300 transition-colors">
              <p className={`text-sm font-medium ${color}`}>{label}</p>
              <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <p className="mt-6 text-xs text-gray-400 text-center px-4 pb-12">
        Eligibility checks use live data from the NSW Planning Portal, Spatial Services NSW, and
        NSW Heritage Register. Results are indicative only — lot area, zone, and heritage status
        are checked against statutory data but DCP setbacks, height limits, and site-specific
        constraints are not included. Not planning advice. Confirm with a registered certifier or town planner.
      </p>

    </div>
  )
}
