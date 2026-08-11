import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { VERIFY_LGAS, VERIFY_LGA_SLUG_MAP } from '@/lib/lga-data/verify-lgas'
import { sanitizeHTML } from '@/lib/sanitize'
import { BreadcrumbJsonLd, DatasetJsonLd } from '@/lib/json-ld'
import { query } from '@/lib/database/pool-manager'

export const revalidate = 86400
// Only slugs from generateStaticParams render; unknown slugs 404 (not 500).
export const dynamicParams = false

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

/* ------------------------------------------------------------------ */
/*  Slug → document_id regex pattern mapping                           */
/* ------------------------------------------------------------------ */

const SLUG_TO_DOC_PATTERN: Record<string, string> = {
  'inner-west': '(Marrickville|Inner_West_Ashfield|Leichhardt)',
  'city-of-sydney': 'Sydney',
  'the-hills-shire': 'Hills_Shire',
  'ku-ring-gai': 'Ku-ring-gai',
  'northern-beaches': 'Northern_Beaches',
  'canterbury-bankstown': 'Canterbury-Bankstown',
  'sutherland-shire': 'Sutherland_Shire',
  'georges-river': 'Georges_River',
  'canada-bay': 'Canada_Bay',
  'lane-cove': 'Lane_Cove',
  'bathurst-regional': 'Bathurst',
  'tamworth-regional': 'Tamworth',
  'clarence-valley': 'Clarence_Valley',
  'yass-valley': 'Yass_Valley',
}

function slugToDocPattern(slug: string, name: string): string {
  if (SLUG_TO_DOC_PATTERN[slug]) return SLUG_TO_DOC_PATTERN[slug]
  // Default: use the council name with spaces → underscores
  return name.replace(/\s+/g, '_')
}

/* ------------------------------------------------------------------ */
/*  Topic label normalization                                          */
/* ------------------------------------------------------------------ */

const TOPIC_LABELS: Record<string, string> = {
  heritage: 'Heritage',
  residential: 'Residential development',
  signage: 'Signage',
  parking: 'Parking',
  height: 'Height',
  building_form: 'Building form',
  access: 'Access',
  waste: 'Waste management',
  landscaping: 'Landscaping',
  setbacks: 'Setbacks',
  setback: 'Setbacks',
  stormwater: 'Stormwater',
  trees: 'Trees and vegetation',
  fencing: 'Fencing',
  fence: 'Fencing',
  general: 'General controls',
  building_design: 'Building design',
  safety: 'Safety',
  commercial: 'Commercial',
  open_space: 'Open space',
  roofing: 'Roofing',
  roof: 'Roofing',
  flooding: 'Flooding',
  solar: 'Solar access',
  sustainability: 'Sustainability',
  privacy: 'Privacy',
  environmental: 'Environmental',
  contamination: 'Contamination',
  precinct: 'Precinct-specific',
  transport: 'Transport',
  industrial: 'Industrial',
  biodiversity: 'Biodiversity',
  views: 'Views',
  public_domain: 'Public domain',
  density: 'Density',
  demolition: 'Demolition',
  bushfire: 'Bushfire',
  acoustic: 'Acoustic',
  subdivision: 'Subdivision',
  water: 'Water',
  accessibility: 'Accessibility',
  design_excellence: 'Design excellence',
  materials: 'Materials',
  carport: 'Carport',
  retail: 'Retail',
  deck: 'Deck',
  pool: 'Pool',
  verandah: 'Verandah',
  additions: 'Additions',
  character: 'Character',
  archaeological: 'Archaeological',
  energy: 'Energy',
  site_analysis: 'Site analysis',
  urban_character: 'Urban character',
  public_art: 'Public art',
  site_specific: 'Site-specific',
  excavation: 'Excavation',
  inter_war_buildings: 'Inter-war buildings',
  social_impact: 'Social impact',
  vehicle_access: 'Vehicle access',
  bicycle_parking: 'Bicycle parking',
  mixed_use: 'Mixed use',
  coastal: 'Coastal',
  food_premises: 'Food premises',
  alterations: 'Alterations',
}

function topicLabel(raw: string): string {
  const key = raw.toLowerCase()
  return TOPIC_LABELS[key] ?? raw.charAt(0).toUpperCase() + raw.slice(1).replace(/_/g, ' ')
}

/* ------------------------------------------------------------------ */
/*  Data fetching                                                      */
/* ------------------------------------------------------------------ */

interface TopicSummary {
  topic: string
  label: string
  count: number
  sample: string
}

const MIN_PROVISIONS_FOR_TOPICS = 30

async function fetchTopicSummary(slug: string, name: string): Promise<{ topics: TopicSummary[]; total: number }> {
  const pattern = slugToDocPattern(slug, name)

  try {
    const result = await query(
      `SELECT
        LOWER(v2_topic) as topic,
        COUNT(*) as cnt,
        (array_agg(provision_text ORDER BY LENGTH(provision_text) ASC))[1] as sample_text
      FROM regulatory_provisions
      WHERE v2_is_actionable = true
        AND document_id ~* $1
        AND v2_topic IS NOT NULL
        AND document_id !~* 'SEPP|LEP'
      GROUP BY LOWER(v2_topic)
      HAVING COUNT(*) >= 3
      ORDER BY cnt DESC`,
      [pattern]
    )

    const rows = result.rows as Array<{ topic: string; cnt: string; sample_text: string | null }>

    // Merge topics that normalize to the same label
    const merged = new Map<string, { count: number; sample: string; topic: string }>()
    for (const row of rows) {
      const label = topicLabel(row.topic)
      const existing = merged.get(label)
      const count = parseInt(row.cnt, 10)
      if (existing) {
        existing.count += count
        // Keep the shorter sample
        if (row.sample_text && row.sample_text.length < existing.sample.length) {
          existing.sample = row.sample_text
        }
      } else {
        merged.set(label, {
          count,
          sample: row.sample_text ?? '',
          topic: row.topic,
        })
      }
    }

    const topics: TopicSummary[] = Array.from(merged.entries())
      .map(([label, data]) => ({
        topic: data.topic,
        label,
        count: data.count,
        sample: data.sample.length > 200 ? data.sample.slice(0, 197) + '...' : data.sample,
      }))
      .sort((a, b) => b.count - a.count)

    const total = topics.reduce((sum, t) => sum + t.count, 0)
    return { topics, total }
  } catch (err) {
    console.error(`[planning-controls] Topic query failed for ${slug}:`, err)
    return { topics: [], total: 0 }
  }
}

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */

export default async function PlanningControlsLgaPage(
  { params }: { params: { 'lga-slug': string } }
) {
  const lga = VERIFY_LGA_SLUG_MAP[params['lga-slug']]
  if (!lga) notFound()

  const { topics, total } = lga.hasDcpData
    ? await fetchTopicSummary(lga.slug, lga.name)
    : { topics: [], total: 0 }

  const showTopics = total >= MIN_PROVISIONS_FOR_TOPICS && topics.length >= 3

  return (
    <div className="max-w-2xl mx-auto px-6">
      <BreadcrumbJsonLd items={[
        { name: 'Home', href: '/' },
        { name: 'Planning Controls', href: '/assessment' },
        { name: lga.name, href: `/planning-controls/${lga.slug}` },
      ]} />

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
            {showTopics ? `${total.toLocaleString()} provisions` : lga.hasDcpData ? 'Available' : 'Coming soon'}
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

      {/* DCP Topic Summary — only for councils with enough data */}
      {showTopics && (
        <div className="mt-10 space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">
            DCP controls in {lga.name} by topic
          </h2>
          <p className="text-sm text-gray-500">
            {lga.name} Council&apos;s Development Control Plan contains {total.toLocaleString()} structured
            provisions across {topics.length} topics. Enter an address above to see which controls
            apply to a specific property.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {topics.slice(0, 16).map(t => (
              <div key={t.label} className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex items-baseline justify-between mb-1">
                  <p className="text-sm font-medium text-gray-900">{t.label}</p>
                  <span className="text-xs text-gray-400 tabular-nums">{t.count}</span>
                </div>
                {t.sample && (
                  <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">
                    {t.sample}
                  </p>
                )}
              </div>
            ))}
          </div>
          {topics.length > 16 && (
            <p className="text-xs text-gray-400 text-center">
              Plus {topics.length - 16} more topic{topics.length - 16 > 1 ? 's' : ''}. Enter an address to see all controls.
            </p>
          )}
        </div>
      )}

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
      <DatasetJsonLd
        name={`Planning Controls — ${lga.name}, NSW`}
        description={`SEPP, LEP, and DCP planning controls for ${lga.name} including setbacks, height limits, floor space ratio, parking rates, landscaping, and heritage constraints. Sourced from NSW Planning Portal and council DCPs.`}
        url={`/planning-controls/${lga.slug}`}
        spatialCoverage={`${lga.name}, New South Wales, Australia`}
        variableMeasured={showTopics
          ? topics.slice(0, 10).map(t => t.label)
          : ['Setbacks', 'Height of buildings', 'Floor space ratio', 'Minimum lot size', 'Parking rates', 'Landscaping area', 'Heritage items']
        }
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
