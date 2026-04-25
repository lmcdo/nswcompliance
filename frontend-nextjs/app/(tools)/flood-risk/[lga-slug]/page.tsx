import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { FloodTool } from '@/components/tools/FloodTool'
import { FLOOD_LGAS, FLOOD_LGA_SLUG_MAP } from '@/lib/lga-data/flood-lgas'
import { sanitizeHTML } from '@/lib/sanitize'

export const revalidate = 86400

export function generateStaticParams() {
  return FLOOD_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = FLOOD_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  const ariDesc = lga.ariScenarios.length > 0
    ? ` ARI flood data (${lga.ariScenarios.slice(0, 3).join(', ')} and more).`
    : ' Statutory flood planning area check.'
  return {
    title: `Flood Risk in ${lga.name} NSW — Check Your Property Address`,
    description: `Is your ${lga.name} property in a flood zone? Instant check against NSW statutory flood overlays.${ariDesc} Free.`,
  }
}

export default function FloodRiskLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = FLOOD_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  const hasAri = lga.ariScenarios.length > 0

  return (
    <div className="max-w-2xl mx-auto px-6">

      {/* SEO content — above the tool */}
      <div className="pt-12 pb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Flood Risk in {lga.name}, NSW
        </h1>
        <p className="mt-3 text-base text-gray-500">
          Check whether a {lga.name} property address falls within a flood planning area.
          {hasAri
            ? ` ${lga.name} has ARI-quantified flood data from the ${lga.floodStudyName} — ${lga.ariScenarios.length} scenarios mapped (${lga.ariScenarios.join(', ')}).`
            : ` Data sourced from the ${lga.floodStudyName} and NSW EPI statutory overlays.`}
        </p>
      </div>

      {/* Data summary */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Flood data</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {hasAri ? `${lga.ariScenarios.length} AEP scenarios` : 'Flood planning area'}
          </p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Flood features</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.floodFeatureCount.toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Heritage items</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.heritageCount > 0 ? lga.heritageCount.toLocaleString() : 'See address check'}
          </p>
        </div>
      </div>

      {/* THE TOOL — renders inline */}
      <FloodTool lgaSlug={lga.slug} />

      {/* FAQ */}
      <div className="mt-12 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Flood planning in {lga.name} — common questions
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

      {/* Verify CTA */}
      <div className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="font-semibold text-gray-900">Need the full planning picture?</h3>
        <p className="text-sm text-gray-500 mt-1 mb-4">
          Flood is one layer. A full report covers heritage, CDC eligibility, DCP setbacks,
          and nearby DA activity.
        </p>
        <a
          href="/canibuildit"
          className="inline-block px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          Check granny flat eligibility →
        </a>
        <p className="text-xs text-gray-400 mt-3">
          Also check:{' '}
          <a href={`/granny-flat/${lga.slug}`} className="text-teal-600 hover:underline">
            granny flat eligibility in {lga.name}
          </a>
        </p>
      </div>

      {/* Disclaimer */}
      <p className="mt-8 text-xs text-gray-400 text-center px-4 pb-12">
        Flood data for {lga.name} sourced from the {lga.floodStudyName} and NSW Planning
        Portal EPI statutory overlay.
        {hasAri && ` ARI scenarios: ${lga.ariScenarios.join(', ')}.`}
        {' '}Not a Section 10.7 flood certificate. Not legal advice. Confirm with{' '}
        {lga.name} Council or a licensed flood consultant before making property or
        development decisions.
      </p>

    </div>
  )
}
