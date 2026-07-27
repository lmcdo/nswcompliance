import 'maplibre-gl/dist/maplibre-gl.css';
// ^ must be imported in a server component to avoid dynamic chunk 404 (see AerialTile.tsx)
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { SolarYieldTool } from '@/components/tools/SolarYieldTool'
import { SOLAR_LGAS, SOLAR_LGA_SLUG_MAP } from '@/lib/lga-data/solar-lgas'
import { GRANNY_FLAT_LGA_SLUG_MAP } from '@/lib/lga-data/granny-flat-lgas'
import { sanitizeHTML } from '@/lib/sanitize'
import { BreadcrumbJsonLd } from '@/lib/json-ld'

export const revalidate = 86400
// Only slugs from generateStaticParams render; unknown slugs 404 (not 500).
export const dynamicParams = false

export function generateStaticParams() {
  return SOLAR_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = SOLAR_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  return {
    title: `Solar Potential in ${lga.name} NSW — Rooftop Yield Estimate`,
    description: `Estimate rooftop solar yield for any ${lga.name} NSW address. Annual kWh, payback period, A–F suitability grade based on aerial imagery. Free.`,
  }
}

export default function SolarPotentialLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = SOLAR_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  const grannyFlatData = GRANNY_FLAT_LGA_SLUG_MAP[lga.slug]

  return (
    <div className="max-w-2xl mx-auto px-6">
      <BreadcrumbJsonLd items={[
        { name: 'Home', href: '/' },
        { name: 'Solar Potential', href: '/reports/solar-yield' },
        { name: lga.name, href: `/solar-potential/${lga.slug}` },
      ]} />

      {/* SEO content — above the tool */}
      <div className="pt-12 pb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Solar Potential in {lga.name}, NSW
        </h1>
        <p className="mt-3 text-base text-gray-500">
          Estimate the rooftop solar yield for any {lga.name} address — panel count, annual kWh,
          and payback period based on aerial imagery analysis of your actual roof.
          {lga.heritageCount > 200 && ` ${lga.name} has ${lga.heritageCount.toLocaleString()} heritage items — check your address for heritage constraints.`}
          {' '}Combine with a{' '}
          <Link href={`/shadow/${lga.slug}`} className="text-slate-600 hover:underline">shadow check</Link>
          {' '}to see if neighbouring buildings will reduce your yield, or check{' '}
          <Link href={`/granny-flat/${lga.slug}`} className="text-teal-600 hover:underline">granny flat eligibility</Link>
          {' '}if you are planning a secondary dwelling.
        </p>
      </div>

      {/* Data summary */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Sunshine hours/yr</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.sunshineHoursPerYear.toLocaleString()} hrs
          </p>
          <p className="text-xs text-gray-400 mt-0.5">BOM {lga.bomStation}</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Ref. payback (6.6 kW)</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.refPaybackYears} years
          </p>
          <p className="text-xs text-gray-400 mt-0.5">at current NSW tariffs</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Heritage items</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {lga.heritageCount.toLocaleString()}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">check address above</p>
        </div>
      </div>

      {/* THE TOOL — renders inline */}
      <SolarYieldTool lgaSlug={lga.slug} />

      {/* FAQ */}
      <div className="mt-12 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Solar in {lga.name} — common questions
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
        <h3 className="font-semibold text-gray-900">Planning a granny flat in {lga.name}?</h3>
        <p className="text-sm text-gray-500 mt-1 mb-4">
          Check SEPP Housing 2021 eligibility — lot area, zoning, heritage, and flood exclusions — in 15 seconds.
        </p>
        <a
          href={`/granny-flat/${lga.slug}`}
          className="inline-block px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          Check granny flat eligibility →
        </a>
        <p className="text-xs text-gray-400 mt-3">
          Also check:{' '}
          <a href={`/flood-risk/${lga.slug}`} className="text-teal-600 hover:underline">
            flood risk in {lga.name}
          </a>
        </p>
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
                  href={`/solar-potential/${slug}`}
                  className="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-amber-400 hover:text-amber-700 transition-colors"
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
        Solar yield estimates based on aerial imagery analysis and BOM sunshine hours for {lga.bomStation} station.
        Financial figures use AER DMO 2025–26 tariff benchmarks and SolarQuotes NSW 2026 install cost data.
        Indicative only — actual yield depends on shading, panel degradation, and household consumption patterns.
        Not financial advice.
      </p>

    </div>
  )
}
