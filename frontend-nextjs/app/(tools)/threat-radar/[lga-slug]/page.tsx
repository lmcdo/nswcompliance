import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { ThreatRadarTool } from '@/components/tools/ThreatRadarTool'
import { THREAT_RADAR_LGAS, THREAT_RADAR_LGA_SLUG_MAP } from '@/lib/lga-data/threat-radar-lgas'
import { sanitizeHTML } from '@/lib/sanitize'

export const revalidate = 86400

export function generateStaticParams() {
  return THREAT_RADAR_LGAS.map(lga => ({ 'lga-slug': lga.slug }))
}

export function generateMetadata(
  { params }: { params: { 'lga-slug': string } }
): Metadata {
  const lga = THREAT_RADAR_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) return {}
  return {
    title: `Neighbour Development Alerts in ${lga.name} NSW — Weekly DA & CDC Monitor`,
    description: `See DA and CDC applications lodged within 200m of any ${lga.name} address. ${lga.activityDescription}. Subscribe for free weekly email alerts. No signup required to search.`,
  }
}

export default function ThreatRadarLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = THREAT_RADAR_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  return (
    <div className="max-w-2xl mx-auto px-6">

      {/* SEO content — above the tool */}
      <div className="pt-12 pb-6">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Neighbour Development Alerts in {lga.name}, NSW
        </h1>
        <p className="mt-3 text-base text-gray-500">
          See DA and CDC applications lodged near any {lga.name} address — updated weekly from the
          NSW ePlanning Portal. {lga.activityDescription}. Subscribe to get emailed
          every Monday when new applications are lodged within 200m of your property.
        </p>
      </div>

      {/* Data summary */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Alert radius</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">200m</p>
          <p className="text-xs text-gray-400 mt-0.5">from your address</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Check frequency</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">Weekly</p>
          <p className="text-xs text-gray-400 mt-0.5">Monday 7:00 am AEST</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs text-gray-500">Activity level</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">{lga.activityLevel}</p>
          <p className="text-xs text-gray-400 mt-0.5">in {lga.name}</p>
        </div>
      </div>

      {/* THE TOOL — renders inline */}
      <ThreatRadarTool lgaSlug={lga.slug} />

      {/* FAQ */}
      <div className="mt-12 space-y-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Development monitoring in {lga.name} — common questions
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
          {lga.hasGrannyFlatPage && (
            <a
              href={`/granny-flat/${lga.slug}`}
              className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Granny flat eligibility</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  SEPP Housing 2021 check — lot area, zoning, heritage, flood
                </p>
              </div>
            </a>
          )}
          {lga.hasFloodPage && (
            <a
              href={`/flood-risk/${lga.slug}`}
              className="flex items-start gap-3 rounded-lg border border-gray-100 p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Flood risk</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Statutory flood overlay and ARI flood data
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

      {/* Disclaimer */}
      <p className="mt-8 text-xs text-gray-400 text-center px-4 pb-12">
        DA and CDC data sourced from the NSW ePlanning Portal. Applications typically appear
        within 24–48 hours of lodgement. Weekly alert checks run every Monday at 7:00 am AEST.
        Not all development types require DA or CDC lodgement on the ePlanning Portal — minor
        exempt development may not appear. Not legal advice.
      </p>

    </div>
  )
}
