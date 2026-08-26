import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { BushfireTool } from '@/components/tools/BushfireTool'
import { BUSHFIRE_LGAS, BUSHFIRE_LGA_SLUG_MAP } from '@/lib/lga-data/bushfire-lgas'
import { FLOOD_LGA_SLUG_MAP } from '@/lib/lga-data/flood-lgas'
import { sanitizeHTML } from '@/lib/sanitize'
import { BreadcrumbJsonLd, DatasetJsonLd } from '@/lib/json-ld'

export const revalidate = 86400
// Only slugs from generateStaticParams render; unknown slugs 404 (not 500).
export const dynamicParams = false

export function generateStaticParams() {
  return BUSHFIRE_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = BUSHFIRE_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  return {
    title: `Bushfire Risk in ${lga.name} NSW — Check Your Property Address`,
    description: `Is your ${lga.name} property on bush fire prone land? Instant BFPL check, estimated BAL band, RFS referral requirements, and 10/50 clearing entitlements. Free.`,
    openGraph: {
      title: `Bushfire Risk in ${lga.name} — Free NSW Property Check`,
      description: `Check bush fire prone land status, BAL band, and RFS referral requirements for any ${lga.name} address. No login required.`,
      url: `https://verify.plotdetect.com.au/bushfire/${lga.slug}`,
      siteName: 'plotdetect.com.au',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: `Bushfire Risk in ${lga.name} — PlotDetect`,
      description: `BFPL category and BAL band for any ${lga.name} address. Free, instant.`,
    },
  }
}

export default function BushfireLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = BUSHFIRE_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  const hasFlood = !!FLOOD_LGA_SLUG_MAP[lga.slug]

  return (
    <div className="max-w-2xl mx-auto px-6">
      <BreadcrumbJsonLd items={[
        { name: 'Home', href: '/' },
        { name: 'Bushfire Pre-Screen', href: '/reports/bushfire' },
        { name: lga.name, href: `/bushfire/${lga.slug}` },
      ]} />

      {/* SEO content — above the tool */}
      <div className="pt-12 pb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Bushfire Risk in {lga.name}, NSW
        </h1>
        <p className="mt-3 text-base text-gray-500">
          Check whether a {lga.name} property address is on bush fire prone land.
          {` Approximately ${lga.bfplCoveragePct}% of ${lga.name} is mapped as bush fire prone land by the NSW RFS.`}
          {' '}Bushfire status affects{' '}
          <Link href={`/granny-flat/${lga.slug}`} className="text-teal-600 hover:underline">granny flat eligibility</Link>
          , insurance premiums, and construction costs.
        </p>
      </div>

      {/* Data summary */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">BFPL coverage</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            ~{lga.bfplCoveragePct}% of LGA
          </p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Dominant vegetation</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.dominantVegetation[0]}
          </p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Data source</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            NSW RFS BFPL Map
          </p>
        </div>
      </div>

      {/* THE TOOL — renders inline */}
      <BushfireTool lgaSlug={lga.slug} />

      {/* FAQ */}
      <div className="mt-12 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Bushfire planning in {lga.name} — common questions
        </h2>
        {lga.faqs.map((faq, i) => (
          <div key={i} className="border-b border-gray-100 pb-4">
            <p className="font-medium text-gray-900 text-sm">{faq.q}</p>
            <p className="text-sm text-gray-500 mt-1">{faq.a}</p>
          </div>
        ))}
      </div>

      {/* Schema markup */}
      <DatasetJsonLd
        name={`Bushfire Risk Data — ${lga.name}, NSW`}
        description={`Bushfire risk assessment data for ${lga.name} including bush fire prone land mapping, estimated BAL bands, RFS referral requirements, and 10/50 vegetation clearing entitlements. Sourced from NSW RFS and Planning Portal.`}
        url={`/bushfire/${lga.slug}`}
        spatialCoverage={`${lga.name}, New South Wales, Australia`}
        variableMeasured={['Bush fire prone land', 'BAL band', 'Vegetation category', 'RFS referral requirement']}
      />
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

      {/* Cross-tool CTA */}
      <div className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="font-semibold text-gray-900">Need the full planning picture?</h3>
        <p className="text-sm text-gray-500 mt-1 mb-4">
          Bushfire is one layer. Check flood risk, granny flat eligibility, shadow impact,
          and nearby development activity for the same address.
        </p>
        <a
          href="/reports"
          className="inline-block px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          See all property checks →
        </a>
        <p className="text-xs text-gray-400 mt-3">
          Also check:{' '}
          {hasFlood && (
            <a href={`/flood-risk/${lga.slug}`} className="text-blue-600 hover:underline mr-2">
              flood risk in {lga.name}
            </a>
          )}
          <a href={`/granny-flat/${lga.slug}`} className="text-teal-600 hover:underline">
            granny flat eligibility in {lga.name}
          </a>
        </p>
      </div>

      {/* Related areas */}
      {lga.relatedSlugs.length > 0 && (
        <div className="mt-8">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">Also check nearby councils</p>
          <div className="flex flex-wrap gap-2">
            {lga.relatedSlugs.map(slug => {
              const related = BUSHFIRE_LGA_SLUG_MAP[slug]
              if (!related) return null
              return (
                <Link
                  key={slug}
                  href={`/bushfire/${slug}`}
                  className="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-orange-400 hover:text-orange-700 transition-colors"
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
        Bush fire prone land data for {lga.name} sourced from the NSW Rural Fire Service
        Bush Fire Prone Land Map via the NSW Planning Portal.
        Not a formal BAL assessment. Not planning advice. A qualified BAL assessor accredited
        under the RFS scheme must assess your site before any development application or
        construction on bush fire prone land.
      </p>

    </div>
  )
}
