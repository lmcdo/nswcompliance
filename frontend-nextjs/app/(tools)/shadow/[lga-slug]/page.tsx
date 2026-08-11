import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { ShadowTool } from '@/components/tools/ShadowTool'
import { SHADOW_LGAS, SHADOW_LGA_SLUG_MAP } from '@/lib/lga-data/shadow-lgas'
import { GRANNY_FLAT_LGA_SLUG_MAP } from '@/lib/lga-data/granny-flat-lgas'
import { sanitizeHTML } from '@/lib/sanitize'
import { BreadcrumbJsonLd } from '@/lib/json-ld'

export const revalidate = 86400
// Only slugs from generateStaticParams render; unknown slugs 404 (not 500).
export const dynamicParams = false

export function generateStaticParams() {
  return SHADOW_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = SHADOW_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  return {
    title: `Shadow Check in ${lga.name} NSW — Will Neighbours Block Your Sunlight?`,
    description: `See how much shadow neighbouring buildings cast on any ${lga.name} property — summer and winter solstice. ${lga.densityNote} Free instant check.`,
  }
}

export default function ShadowLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = SHADOW_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  const grannyFlatData = GRANNY_FLAT_LGA_SLUG_MAP[lga.slug]

  return (
    <div className="max-w-2xl mx-auto px-6">
      <BreadcrumbJsonLd items={[
        { name: 'Home', href: '/' },
        { name: 'Shadow Check', href: '/reports/shadow' },
        { name: lga.name, href: `/shadow/${lga.slug}` },
      ]} />

      {/* SEO content — above the tool */}
      <div className="pt-12 pb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Shadow Check in {lga.name}, NSW
        </h1>
        <p className="mt-3 text-base text-gray-500">
          See how much shadow neighbouring buildings cast on your {lga.name} property
          at the summer and winter solstice. {lga.densityNote}
          {lga.heritageCount > 200 && ` ${lga.name} has ${lga.heritageCount.toLocaleString()} heritage items — character buildings can cast unexpected shadows.`}
          {' '}Shadow analysis works best alongside a{' '}
          <Link href={`/solar-potential/${lga.slug}`} className="text-amber-600 hover:underline">solar yield estimate</Link>
          {' '}— shading directly reduces panel output. If you are planning a granny flat, check{' '}
          <Link href={`/granny-flat/${lga.slug}`} className="text-teal-600 hover:underline">SEPP eligibility</Link>
          {' '}and{' '}
          <Link href={`/threat-radar/${lga.slug}`} className="text-violet-600 hover:underline">nearby development activity</Link>
          {' '}in {lga.name}.
        </p>
      </div>

      {/* Data summary */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Analysis points</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">Summer + Winter</p>
          <p className="text-xs text-gray-400 mt-0.5">solstice comparison</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">ADG check</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">3hrs direct sun</p>
          <p className="text-xs text-gray-400 mt-0.5">NSW min. standard</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Heritage items</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.heritageCount.toLocaleString()}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">in {lga.name}</p>
        </div>
      </div>

      {/* THE TOOL — renders inline */}
      <ShadowTool lgaSlug={lga.slug} />

      {/* FAQ */}
      <div className="mt-12 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Shadow and overshadowing in {lga.name} — common questions
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
        <h3 className="font-semibold text-gray-900">More property checks for {lga.name}</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
          <a
            href={`/granny-flat/${lga.slug}`}
            className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Granny flat eligibility</p>
              <p className="text-xs text-gray-400 mt-0.5">SEPP Housing 2021 instant check</p>
            </div>
          </a>
          <a
            href={`/solar-potential/${lga.slug}`}
            className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Solar potential</p>
              <p className="text-xs text-gray-400 mt-0.5">Roof yield estimate</p>
            </div>
          </a>
        </div>
      </div>

      {/* Related areas */}
      {grannyFlatData && grannyFlatData.relatedSlugs.length > 0 && (
        <div className="mt-8">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">Also check nearby councils</p>
          <div className="flex flex-wrap gap-2">
            {grannyFlatData.relatedSlugs.map(slug => {
              const related = GRANNY_FLAT_LGA_SLUG_MAP[slug]
              if (!related) return null
              return (
                <Link
                  key={slug}
                  href={`/shadow/${slug}`}
                  className="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-slate-400 hover:text-slate-700 transition-colors"
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
        Shadow analysis uses building footprints and height data from NSW Spatial Services aerial
        imagery. The ADG 3-hour minimum applies to habitable rooms in new residential development
        assessed under the Apartment Design Guide. Results are indicative only -- actual shadow
        impact depends on exact roof pitch, vegetation, and neighbouring building heights.
        Not planning advice.
      </p>

    </div>
  )
}
