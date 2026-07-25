import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { CONVEYANCING_LGAS, CONVEYANCING_LGA_SLUG_MAP } from '@/lib/lga-data/conveyancing-lgas'
import { sanitizeHTML } from '@/lib/sanitize'
import { BreadcrumbJsonLd } from '@/lib/json-ld'

export const revalidate = 86400
// Only slugs from generateStaticParams render; unknown slugs 404 (not 500).
export const dynamicParams = false

export function generateStaticParams() {
  return CONVEYANCING_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = CONVEYANCING_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  return {
    title: `Conveyancing Planning Disclosure for ${lga.name}, NSW — $49 PDF Report`,
    description: `Instant planning disclosure for any ${lga.name} property. LEP controls, heritage, flood, bushfire, SEPP overlays, DCP setbacks, nearby DAs — from live NSW government data. Free summary, $49 full PDF.`,
  }
}

export default function ConveyancingLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = CONVEYANCING_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  return (
    <div className="max-w-2xl mx-auto px-6">
      <BreadcrumbJsonLd items={[
        { name: 'Home', href: '/' },
        { name: 'Conveyancing Disclosure', href: '/reports/conveyancing' },
        { name: lga.name, href: `/conveyancing/${lga.slug}` },
      ]} />

      {/* SEO content — above the CTA */}
      <div className="pt-12 pb-6">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Conveyancing planning disclosure for {lga.name}
        </h1>
        <p className="mt-3 text-base text-gray-500">
          Instant planning intelligence for any {lga.name} property — LEP zoning, height, FSR,
          heritage, environmental overlays, SEPP controls, DCP setbacks, and nearby DA activity.
          Free summary online, $49 for the full PDF report with data citations.
          Also check{' '}
          <Link href={`/granny-flat/${lga.slug}`} className="text-teal-600 hover:underline">granny flat eligibility</Link>
          {' '}and{' '}
          <Link href={`/flood-risk/${lga.slug}`} className="text-blue-600 hover:underline">flood risk</Link>
          {' '}for any {lga.name} address.
        </p>
      </div>

      {/* Data summary */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Data sources</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">9 layers</p>
          <p className="text-xs text-gray-400 mt-0.5">LEP + SEPP + DCP + spatial</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Coverage</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">All NSW</p>
          <p className="text-xs text-gray-400 mt-0.5">Any address in {lga.name}</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Full report</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">$49</p>
          <p className="text-xs text-gray-400 mt-0.5">PDF emailed instantly</p>
        </div>
      </div>

      {/* CTA to conveyancing tool */}
      <div className="rounded-xl border-2 border-teal-100 bg-teal-50/50 p-6 text-center">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Generate a planning disclosure for your {lga.name} property
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Enter any {lga.name} address to get a free summary. Upgrade to the full PDF report for $49.
        </p>
        <Link
          href="/reports/conveyancing"
          className="inline-block px-6 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          Start Planning Disclosure
        </Link>
      </div>

      {/* What's included */}
      <div className="mt-10 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">
          What the planning disclosure report covers
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { title: 'LEP controls', desc: 'Zoning, height of buildings, floor space ratio, minimum lot size, heritage, and additional permitted uses under the Local Environmental Plan.' },
            { title: 'SEPP overlays', desc: 'State Environmental Planning Policies including Housing SEPP 2021, Transport & Infrastructure, Coastal Management, and exempt/complying provisions.' },
            { title: 'Environmental overlays', desc: 'Flood planning areas, bushfire prone land, acid sulfate soils, contaminated land, biodiversity, and other mapped constraints.' },
            { title: 'DCP setback controls', desc: 'Council-specific front, side, and rear setbacks, parking rates, landscaping requirements, and site coverage controls.' },
            { title: 'Heritage status', desc: 'Heritage items, heritage conservation areas, and Aboriginal heritage mapping from the LEP and NSW Heritage Register.' },
            { title: 'Nearby DA activity', desc: 'Recent development applications and CDCs lodged within proximity — showing what neighbours are building and approval patterns.' },
          ].map(item => (
            <div key={item.title} className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-sm font-medium text-gray-900">{item.title}</p>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ */}
      <div className="mt-12 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Conveyancing planning disclosure for {lga.name} — common questions
        </h2>
        {lga.faqs.map((faq, i) => (
          <div key={i} className="border-b border-gray-100 pb-4">
            <p className="font-medium text-gray-900 text-sm">{faq.q}</p>
            <p className="text-sm text-gray-500 mt-1">{faq.a}</p>
          </div>
        ))}
      </div>

      {/* Schema markup */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: sanitizeHTML(JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: lga.faqs.map(faq => ({
              '@type': 'Question',
              name: faq.q,
              acceptedAnswer: { '@type': 'Answer', text: faq.a },
            })),
          })),
        }}
      />

      {/* Cross-link CTA */}
      <div className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="font-semibold text-gray-900">Other property checks for {lga.name}</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
          <a
            href={`/planning-controls/${lga.slug}`}
            className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Planning controls</p>
              <p className="text-xs text-gray-400 mt-0.5">SEPP + LEP + DCP assessment</p>
            </div>
          </a>
          <a
            href={`/granny-flat/${lga.slug}`}
            className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Granny flat eligibility</p>
              <p className="text-xs text-gray-400 mt-0.5">SEPP Housing 2021 check</p>
            </div>
          </a>
          <a
            href={`/flood-risk/${lga.slug}`}
            className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Flood risk</p>
              <p className="text-xs text-gray-400 mt-0.5">Statutory + satellite flood data</p>
            </div>
          </a>
          <a
            href={`/threat-radar/${lga.slug}`}
            className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Threat radar</p>
              <p className="text-xs text-gray-400 mt-0.5">Nearby DAs and CDCs</p>
            </div>
          </a>
        </div>
      </div>

      {/* Related areas */}
      {lga.relatedSlugs.length > 0 && (
        <div className="mt-8">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">Also check nearby councils</p>
          <div className="flex flex-wrap gap-2">
            {lga.relatedSlugs.map(slug => {
              const related = CONVEYANCING_LGA_SLUG_MAP[slug]
              if (!related) return null
              return (
                <Link
                  key={slug}
                  href={`/conveyancing/${slug}`}
                  className="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-teal-400 hover:text-teal-700 transition-colors"
                >
                  {related.name}
                </Link>
              )
            })}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <p className="mt-8 text-xs text-gray-400 text-center px-4 pb-12">
        Planning data is sourced live from the NSW Planning Portal, PostGIS spatial overlays,
        and structured DCP provisions. This report is not a Section 10.7 planning certificate
        and does not constitute legal advice. Confirm all findings with the relevant council
        or a licensed conveyancer before making property decisions.
      </p>

    </div>
  )
}
