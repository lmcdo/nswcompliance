import 'maplibre-gl/dist/maplibre-gl.css';
// ^ must be imported in a server component to avoid dynamic chunk 404 (see AerialTile.tsx)
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { GrannyFlatTool } from '@/components/tools/GrannyFlatTool'
import { GRANNY_FLAT_LGAS, GRANNY_FLAT_LGA_SLUG_MAP } from '@/lib/lga-data/granny-flat-lgas'
import { sanitizeHTML } from '@/lib/sanitize'
import { BreadcrumbJsonLd, DatasetJsonLd } from '@/lib/json-ld'

export const revalidate = 86400
// Only slugs from generateStaticParams render; unknown slugs 404 (not 500).
export const dynamicParams = false

export function generateStaticParams() {
  return GRANNY_FLAT_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = GRANNY_FLAT_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  return {
    title: `Granny Flat Rules & Eligibility in ${lga.name}, NSW — Free Check`,
    description: `Could your ${lga.name} property earn $280–$340/week with a granny flat? Free eligibility check — lot size, zoning, heritage (${lga.heritageCount.toLocaleString()} items), flood${lga.hasFloodData ? ' (ARI data)' : ''}, biodiversity. No signup.`,
  }
}

export default function GrannyFlatLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = GRANNY_FLAT_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  return (
    <div className="max-w-2xl mx-auto px-6">
      <BreadcrumbJsonLd items={[
        { name: 'Home', href: '/' },
        { name: 'Granny Flat Eligibility', href: '/granny-flat' },
        { name: lga.name, href: `/granny-flat/${lga.slug}` },
      ]} />

      {/* SEO content — above the tool */}
      <div className="pt-12 pb-6">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Can I build a granny flat in {lga.name}?
        </h1>
        <p className="mt-3 text-base text-gray-500">
          Instant SEPP Housing 2021 eligibility check for any {lga.name} address — lot area, zoning,
          heritage exclusions
          {lga.heritageCount > 0 && ` (${lga.heritageCount.toLocaleString()} items in ${lga.name})`},
          {lga.hasFloodData
            ? <>{' '}<Link href={`/flood-risk/${lga.slug}`} className="text-blue-600 hover:underline">flood control lots</Link>,</>
            : ''}
          {' '}biodiversity values, and acid sulfate soils. Free. Also check{' '}
          <Link href={`/solar-potential/${lga.slug}`} className="text-amber-600 hover:underline">solar yield</Link>
          {' '}and{' '}
          <Link href={`/shadow/${lga.slug}`} className="text-slate-600 hover:underline">shadow impact</Link>
          {' '}for any {lga.name} address.
        </p>
      </div>

      {/* Data summary */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Min. lot area</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">450 m²</p>
          <p className="text-xs text-gray-400 mt-0.5">SEPP Housing 2021</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Heritage items</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.heritageCount.toLocaleString()}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">in {lga.name}</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Flood data</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.hasAriData ? 'ARI scenarios' : lga.hasFloodData ? 'FPA mapped' : 'EPI overlay'}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">checked per address</p>
        </div>
      </div>

      {/* THE TOOL — renders inline */}
      <GrannyFlatTool lgaSlug={lga.slug} lgaName={lga.name} />

      {/* FAQ */}
      <div className="mt-12 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Granny flats in {lga.name} — common questions
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
        name={`Granny Flat Eligibility Data — ${lga.name}, NSW`}
        description={`Secondary dwelling (granny flat) eligibility data for ${lga.name} including zoning, minimum lot size, heritage items, flood overlays, and biodiversity constraints. Sourced from NSW Planning Portal and SEPP Housing 2021.`}
        url={`/granny-flat/${lga.slug}`}
        spatialCoverage={`${lga.name}, New South Wales, Australia`}
        variableMeasured={['Zoning', 'Lot size', 'Heritage items', 'Flood planning area', 'Biodiversity', 'Acid sulfate soils']}
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

      {/* Cross-link CTA */}
      <div className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="font-semibold text-gray-900">Check other property risks in {lga.name}</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
          {lga.hasFloodData && (
            <a
              href={`/flood-risk/${lga.slug}`}
              className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Flood risk</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {lga.hasAriData ? 'ARI flood data available' : 'Flood planning area check'}
                </p>
              </div>
            </a>
          )}
          <a
            href={`/solar-potential/${lga.slug}`}
            className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Solar potential</p>
              <p className="text-xs text-gray-400 mt-0.5">Roof yield estimate for any address</p>
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
              const related = GRANNY_FLAT_LGA_SLUG_MAP[slug]
              if (!related) return null
              return (
                <Link
                  key={slug}
                  href={`/granny-flat/${slug}`}
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
        Checks lot area, zoning, heritage items and conservation areas, flood control lots,
        biodiversity values, and acid sulfate soils against SEPP Housing 2021.
        {lga.hasFloodData
          ? ` Flood check uses ${lga.hasAriData ? 'ARI-quantified data' : 'statutory flood planning area boundaries'} for ${lga.name}.`
          : ' Flood check uses NSW EPI statutory overlay — shown as unknown outside coverage.'}
        {' '}DCP setback and height controls not included. Not legal advice.
      </p>

    </div>
  )
}
