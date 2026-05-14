import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { VERIFY_LGAS, VERIFY_LGA_SLUG_MAP } from '@/lib/lga-data/verify-lgas'
import { sanitizeHTML } from '@/lib/sanitize'

export const revalidate = 86400

export function generateStaticParams() {
  return VERIFY_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = VERIFY_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  return {
    title: `Planning Controls for ${lga.name}, NSW — Setbacks, Parking, Height, Landscaping`,
    description: `Full SEPP, LEP, and DCP controls for any ${lga.name} property — setbacks, parking, height, landscaping, heritage with clause citations. Free. No signup.`,
  }
}

export default function PlanningControlsLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = VERIFY_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  return (
    <div className="max-w-2xl mx-auto px-6">

      {/* SEO content — above the tool */}
      <div className="pt-12 pb-6">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Planning controls for {lga.name}
        </h1>
        <p className="mt-3 text-base text-gray-500">
          Full SEPP, LEP, and DCP controls for any {lga.name} address — setbacks, parking, height,
          floor space ratio, landscaping, and heritage with clause citations. Free. Also check{' '}
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
          <p className="text-sm font-semibold text-gray-900 mt-1">SEPP + LEP + DCP</p>
          <p className="text-xs text-gray-400 mt-0.5">Three tiers of controls</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">DCP controls</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.hasDcpData ? 'Available' : 'Coming soon'}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">Structured provisions</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Coverage</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">All NSW</p>
          <p className="text-xs text-gray-400 mt-0.5">LEP + SEPP for every address</p>
        </div>
      </div>

      {/* CTA to assessment page */}
      <div className="rounded-xl border-2 border-teal-100 bg-teal-50/50 p-6 text-center">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Check planning controls for your {lga.name} property
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Enter any {lga.name} address to see the full SEPP, LEP, and DCP controls with clause citations.
        </p>
        <Link
          href="/assessment"
          className="inline-block px-6 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          Open Planning Controls Tool
        </Link>
      </div>

      {/* What's included */}
      <div className="mt-10 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">
          What the planning controls assessment covers
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { title: 'SEPP controls', desc: 'State-level policies including Housing SEPP 2021, Transport & Infrastructure, and Coastal Management.' },
            { title: 'LEP controls', desc: 'Zoning, height of buildings, floor space ratio, minimum lot size, heritage, and additional permitted uses.' },
            { title: 'DCP controls', desc: 'Council-specific setbacks, parking rates, landscaping requirements, private open space, and design controls.' },
            { title: 'Spatial overlays', desc: 'Flood, bushfire, heritage, acid sulfate soils, biodiversity, and other mapped constraints from the NSW Planning Portal.' },
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
          Planning controls in {lga.name} — common questions
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
          <a
            href={`/bushfire/${lga.slug}`}
            className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Bushfire pre-screen</p>
              <p className="text-xs text-gray-400 mt-0.5">BFPL status and BAL estimate</p>
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
              const related = VERIFY_LGA_SLUG_MAP[slug]
              if (!related) return null
              return (
                <Link
                  key={slug}
                  href={`/planning-controls/${slug}`}
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
        Planning controls are sourced live from the NSW Planning Portal, PostGIS spatial overlays,
        and structured DCP provisions. Controls shown are indicative — always verify with the
        relevant council or a registered town planner before making development decisions.
      </p>

    </div>
  )
}
