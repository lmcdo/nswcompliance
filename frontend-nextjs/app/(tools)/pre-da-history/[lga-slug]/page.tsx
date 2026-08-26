import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { PreDAHistoryTool } from '@/components/tools/PreDAHistoryTool'
import { PRE_DA_HISTORY_LGAS, PRE_DA_HISTORY_LGA_SLUG_MAP } from '@/lib/lga-data/pre-da-history-lgas'
import { GRANNY_FLAT_LGA_SLUG_MAP } from '@/lib/lga-data/granny-flat-lgas'
import { sanitizeHTML } from '@/lib/sanitize'
import { BreadcrumbJsonLd } from '@/lib/json-ld'

export const revalidate = 86400
// Only slugs from generateStaticParams render; unknown slugs 404 (not 500).
export const dynamicParams = false

export function generateStaticParams() {
  return PRE_DA_HISTORY_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = PRE_DA_HISTORY_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  return {
    title: `Site History for ${lga.name} NSW — Pre-DA Satellite & DA Check`,
    description: `What happened on this ${lga.name} property before you got here? Eight years of satellite change detection, DA history, heritage overlays, and natural disaster events. Free.`,
    openGraph: {
      title: `Pre-DA Site History in ${lga.name} — Free NSW Property Check`,
      description: `Satellite change detection + DA history for any ${lga.name} address. Unapproved works, vegetation clearing, flood/fire events. No login required.`,
      url: `https://verify.plotdetect.com.au/pre-da-history/${lga.slug}`,
      siteName: 'plotdetect.com.au',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: `Pre-DA Site History in ${lga.name} — PlotDetect`,
      description: `Satellite change detection + DA history for any ${lga.name} address. Free, instant.`,
    },
  }
}

export default function PreDaHistoryLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = PRE_DA_HISTORY_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  const hasGrannyFlat = !!GRANNY_FLAT_LGA_SLUG_MAP[lga.slug]

  return (
    <div className="max-w-2xl mx-auto px-6">
      <BreadcrumbJsonLd items={[
        { name: 'Home', href: '/' },
        { name: 'Pre-DA Site History', href: '/reports/pre-da-history' },
        { name: lga.name, href: `/pre-da-history/${lga.slug}` },
      ]} />

      {/* SEO content — above the tool */}
      <div className="pt-12 pb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Pre-DA Site History in {lga.name}, NSW
        </h1>
        <p className="mt-3 text-base text-gray-500">
          What happened on this {lga.name} property before you got here?
          This report analyses eight years of satellite imagery and cross-references
          DA records, heritage overlays, and natural disaster events for any address.
        </p>
      </div>

      {/* Risk factors summary */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        {lga.riskFactors.slice(0, 3).map((factor, i) => (
          <div key={i} className="rounded-lg bg-gray-50 p-4">
            <p className="text-xs text-gray-500">Key risk factor</p>
            <p className="text-sm font-semibold text-gray-900 mt-1">{factor}</p>
          </div>
        ))}
      </div>

      {/* THE TOOL — renders inline */}
      <PreDAHistoryTool />

      {/* FAQ */}
      <div className="mt-12 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Site history in {lga.name} — common questions
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

      {/* Cross-tool CTA */}
      <div className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="font-semibold text-gray-900">Need the full planning picture?</h3>
        <p className="text-sm text-gray-500 mt-1 mb-4">
          Site history is one layer. Check flood risk, bushfire status, granny flat eligibility,
          shadow impact, and nearby development activity for the same address.
        </p>
        <a
          href="/reports"
          className="inline-block px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          See all property checks →
        </a>
        <p className="text-xs text-gray-400 mt-3">
          Also check:{' '}
          <a href={`/bushfire/${lga.slug}`} className="text-orange-600 hover:underline mr-2">
            bushfire risk in {lga.name}
          </a>
          {hasGrannyFlat && (
            <a href={`/granny-flat/${lga.slug}`} className="text-teal-600 hover:underline">
              granny flat eligibility in {lga.name}
            </a>
          )}
        </p>
      </div>

      {/* Related areas */}
      {lga.relatedSlugs.length > 0 && (
        <div className="mt-8">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">Also check nearby councils</p>
          <div className="flex flex-wrap gap-2">
            {lga.relatedSlugs.map(slug => {
              const related = PRE_DA_HISTORY_LGA_SLUG_MAP[slug]
              if (!related) return null
              return (
                <Link
                  key={slug}
                  href={`/pre-da-history/${slug}`}
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
        Satellite imagery sourced from ESA Sentinel-2 via Google Earth Engine.
        DA records from the NSW ePlanning Portal. Heritage data from the NSW Heritage Register.
        This report is not a formal site investigation and does not replace a Section 10.7
        planning certificate, contamination assessment, or professional planning advice.
      </p>

    </div>
  )
}
