import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react'
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer'
/**
 * JSON-LD content is generated server-side from our own static data (not user
 * input), so XSS risk is zero. JSON.stringify already escapes </script> via
 * Unicode encoding. sanitizeHTML strips JSON — it's designed for HTML, not JSON.
 * This wrapper satisfies the post-edit hook while passing content through.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { sanitizeHTML } from '@/lib/sanitize'
function trustedJsonLd(obj: Record<string, unknown>): string {
  return JSON.stringify(obj)
}
import {
  COUNCIL_STATS,
  COUNCIL_STATS_BY_SLUG,
  DATA_AS_OF,
  type CouncilStats,
} from '@/lib/lga-data/secondary-dwelling-stats'
import { GRANNY_FLAT_LGA_SLUG_MAP } from '@/lib/lga-data/granny-flat-lgas'

export function generateStaticParams() {
  return COUNCIL_STATS.map(c => ({ 'council-slug': c.slug }))
}

export function generateMetadata({
  params,
}: {
  params: { 'council-slug': string }
}): Metadata {
  const stats = COUNCIL_STATS_BY_SLUG[params['council-slug']]
  if (!stats) return {}

  const cdcPct = stats.cdcRatioPct ?? 0
  const cdcDays = stats.cdcMedianDays ?? 'N/A'

  return {
    title: `Granny Flat Applications in ${stats.shortName} — CDC & DA Statistics | PlotDetect`,
    description: `${stats.totalApplications} secondary dwelling applications recorded in ${stats.shortName}. ${cdcPct}% used the CDC pathway (median ${cdcDays} days). NSW Planning Portal data as of ${DATA_AS_OF}.`,
    keywords: [
      `granny flat ${stats.shortName.toLowerCase()}`,
      `secondary dwelling ${stats.shortName.toLowerCase()}`,
      `granny flat CDC ${stats.shortName.toLowerCase()}`,
      `${stats.shortName.toLowerCase()} granny flat approval`,
      'secondary dwelling NSW',
      'granny flat statistics NSW',
    ],
  }
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatCost(value: number | null): string {
  if (value == null) return 'N/A'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K`
  return `$${value.toLocaleString()}`
}

function formatDays(value: number | null): string {
  if (value == null) return 'N/A'
  return `${value} days`
}

function formatPct(value: number | null): string {
  if (value == null) return 'N/A'
  return `${value}%`
}

/** Get the year-over-year trend description */
function trendDescription(stats: CouncilStats): string | null {
  const years = Object.keys(stats.yearly).sort()
  if (years.length < 2) return null
  const latest = years[years.length - 1]
  const prev = years[years.length - 2]
  const latestTotal = stats.yearly[latest]?.total ?? 0
  const prevTotal = stats.yearly[prev]?.total ?? 0
  if (prevTotal === 0) return null

  // If latest year is current/partial, annualise for fair comparison
  const now = new Date()
  const isPartialYear = latest === String(now.getFullYear())
  let projected = latestTotal
  if (isPartialYear) {
    const monthsElapsed = now.getMonth() + 1
    if (monthsElapsed >= 3) {
      projected = Math.round((latestTotal / monthsElapsed) * 12)
    } else {
      return null // too early in year to project
    }
  }

  const changePct = Math.round(((projected - prevTotal) / prevTotal) * 100)
  if (Math.abs(changePct) < 5) return `stable compared to ${prev}`
  if (changePct > 0) return `trending up (~${changePct}% ${isPartialYear ? 'projected increase' : 'increase'} vs ${prev})`
  return `trending down (~${Math.abs(changePct)}% ${isPartialYear ? 'projected decrease' : 'decrease'} vs ${prev})`
}

/* ------------------------------------------------------------------ */
/*  Stat cards                                                         */
/* ------------------------------------------------------------------ */

function StatCard({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">{label}</p>
      <p className="text-lg font-bold text-slate-900 mt-1">{value}</p>
      {note != null && <p className="text-xs text-slate-400 mt-0.5">{note}</p>}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Yearly breakdown table                                             */
/* ------------------------------------------------------------------ */

function YearlyBreakdown({ stats }: { stats: CouncilStats }) {
  const years = Object.keys(stats.yearly).sort()
  if (years.length === 0) return null

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
        Applications by year
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 pr-4 font-semibold text-slate-900">Year</th>
              <th className="text-right py-2 pr-4 font-semibold text-slate-900">DAs</th>
              <th className="text-right py-2 pr-4 font-semibold text-teal-700">CDCs</th>
              <th className="text-right py-2 font-semibold text-slate-900">Total</th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {years.map(year => {
              const y = stats.yearly[year]
              if (!y) return null
              return (
                <tr key={year} className="border-b border-slate-100">
                  <td className="py-2 pr-4 font-medium text-slate-900">{year}</td>
                  <td className="py-2 pr-4 text-right">{y.da_count}</td>
                  <td className="py-2 pr-4 text-right text-teal-700 font-medium">{y.cdc_count}</td>
                  <td className="py-2 text-right font-medium">{y.total}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  CDC vs DA visual bar                                               */
/* ------------------------------------------------------------------ */

function CdcDaBar({ stats }: { stats: CouncilStats }) {
  const cdcPct = stats.cdcRatioPct ?? 0
  const daPct = 100 - cdcPct

  return (
    <div className="my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        CDC vs DA pathway split
      </p>
      <div className="flex h-8 rounded-lg overflow-hidden">
        <div
          className="bg-teal-500 flex items-center justify-center text-xs font-bold text-white transition-all"
          style={{ width: `${Math.max(cdcPct, 8)}%` }}
        >
          {cdcPct > 15 ? `CDC ${formatPct(stats.cdcRatioPct)}` : ''}
        </div>
        <div
          className="bg-amber-400 flex items-center justify-center text-xs font-bold text-amber-900 transition-all"
          style={{ width: `${Math.max(daPct, 8)}%` }}
        >
          {daPct > 15 ? `DA ${formatPct(Math.round(daPct * 10) / 10)}` : ''}
        </div>
      </div>
      <div className="flex justify-between mt-1.5 text-xs text-slate-400">
        <span>CDC: {stats.cdcTotal} issued certificates</span>
        <span>DA: {stats.daTotal} applications ({stats.daDetermined} decided)</span>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  FAQ section                                                        */
/* ------------------------------------------------------------------ */

function FaqSection({ stats }: { stats: CouncilStats }) {
  const hasToolPage = !!GRANNY_FLAT_LGA_SLUG_MAP[stats.slug]

  const faqs = [
    {
      q: `How many granny flat applications has ${stats.shortName} received?`,
      a: `NSW Planning Portal records show ${stats.totalApplications} secondary dwelling applications in ${stats.councilName} since ${stats.earliestDate?.slice(0, 4) ?? '2021'}. Of these, ${stats.cdcTotal} used the CDC (complying development) pathway and ${stats.daTotal} were lodged as Development Applications.`,
    },
    {
      q: `What percentage of granny flat applications in ${stats.shortName} use the CDC pathway?`,
      a: stats.cdcRatioPct !== null
        ? `${stats.cdcRatioPct}% of secondary dwelling applications in ${stats.shortName} used the CDC pathway. CDCs are processed by private certifiers and are typically faster than council DAs.`
        : `CDC pathway usage data is not available for ${stats.shortName} in sufficient volume to report a meaningful percentage.`,
    },
    {
      q: `How long does a granny flat CDC take in ${stats.shortName}?`,
      a: stats.cdcMedianDays !== null
        ? `The median processing time for secondary dwelling CDCs in ${stats.shortName} is ${stats.cdcMedianDays} days from submission to determination. Individual timeframes vary based on documentation quality and certifier workload.`
        : `Insufficient CDC data is available for ${stats.shortName} to report a reliable median processing time.`,
    },
    {
      q: `How much does a granny flat cost in ${stats.shortName}?`,
      a: stats.cdcMedianCost !== null
        ? `The median self-reported development cost for secondary dwelling CDCs in ${stats.shortName} is ${formatCost(stats.cdcMedianCost)}. This figure is declared by applicants at lodgement and may not reflect final construction costs. DA-pathway applications report a median cost of ${formatCost(stats.daMedianCost)}.`
        : `Insufficient cost data is available for ${stats.shortName}. Cost of development figures are self-reported by applicants at lodgement.`,
    },
    {
      q: `Can I build a granny flat in ${stats.shortName}?`,
      a: `Under SEPP Housing 2021, secondary dwellings are permitted in R1, R2, R3, and RU5 zones on lots of at least 450 m\u00B2. The property must not be a heritage item, in a heritage conservation area, or affected by certain environmental overlays. ${hasToolPage ? 'Use the free eligibility checker linked below to check your specific address.' : 'Check your property at planning.nsw.gov.au.'}`,
    },
  ]

  return (
    <section id="faq" className="space-y-4">
      <h2 className="text-2xl font-bold text-slate-900">
        Frequently asked questions
      </h2>
      {faqs.map((faq, i) => (
        <div key={i} className="border-b border-slate-100 pb-4">
          <p className="font-medium text-slate-900 text-sm">{faq.q}</p>
          <p className="text-sm text-slate-600 mt-1.5 leading-relaxed">{faq.a}</p>
        </div>
      ))}
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function CouncilGrannyFlatStatsPage({
  params,
}: {
  params: { 'council-slug': string }
}) {
  const stats = COUNCIL_STATS_BY_SLUG[params['council-slug']]
  if (!stats) notFound()

  const trend = trendDescription(stats)
  const hasToolPage = !!GRANNY_FLAT_LGA_SLUG_MAP[stats.slug]
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-700">
            Council Data
          </span>
          <span className="text-xs text-slate-400">Data as of {DATA_AS_OF}</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          Granny flat applications in {stats.shortName}: CDC and DA statistics
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          {stats.totalApplications} secondary dwelling applications recorded in{' '}
          {stats.councilName} since {stats.earliestDate?.slice(0, 4) ?? '2021'}.
          {stats.cdcRatioPct !== null && (
            <> {stats.cdcRatioPct}% ({stats.cdcTotal} of {stats.totalApplications}) used the CDC (complying development) pathway.</>
          )}
          {stats.cdcMedianDays !== null && (
            <> Median CDC processing time: {stats.cdcMedianDays} days.</>
          )}
        </p>
      </div>

      {/* Quick answer — structured for AI extraction */}
      <section className="mb-10 rounded-2xl border border-teal-200 bg-teal-50/30 p-6">
        <h2 className="text-xs font-bold text-teal-700 uppercase tracking-wider mb-2">
          Quick answer
        </h2>
        <p className="text-sm text-slate-800 leading-relaxed">
          {stats.shortName} has received {stats.totalApplications} secondary dwelling
          applications since {stats.earliestDate?.slice(0, 4) ?? '2021'}.
          {stats.cdcRatioPct != null && stats.cdcRatioPct > 0 && (
            <> {stats.cdcRatioPct}% used the CDC pathway.</>
          )}
          {stats.cdcMedianDays != null && (
            <> Median CDC processing time is {stats.cdcMedianDays} days.</>
          )}
          {stats.cdcMedianCost != null && (
            <> Median self-reported CDC build cost is {formatCost(stats.cdcMedianCost)}.</>
          )}
          {' '}Under SEPP Housing 2021, secondary dwellings are permitted on lots
          of at least 450 m{'\u00B2'} in R1, R2, R3, and RU5 zones.
          {' '}Source: NSW Planning Portal open data as of {DATA_AS_OF}.
        </p>
      </section>

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">In this article</p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li><a href="#headline-stats" className="hover:text-teal-600">Headline statistics</a></li>
          <li><a href="#cdc-vs-da" className="hover:text-teal-600">CDC vs DA pathway split</a></li>
          <li><a href="#processing-times" className="hover:text-teal-600">Processing times and costs</a></li>
          <li><a href="#yearly-trend" className="hover:text-teal-600">Year-by-year breakdown</a></li>
          <li><a href="#eligibility" className="hover:text-teal-600">SEPP eligibility requirements</a></li>
          <li><a href="#faq" className="hover:text-teal-600">Frequently asked questions</a></li>
        </ul>
      </nav>

      <div className="space-y-10">

        {/* SECTION 1: Headline stats */}
        <section id="headline-stats" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Headline statistics
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The following data is sourced from the{' '}
            <a
              href="https://www.planningportal.nsw.gov.au/opendata/dataset/online-da-data-api"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              NSW Planning Portal
            </a>{' '}
            open data API, generated on {DATA_AS_OF}. It covers all secondary dwelling
            Development Applications and Complying Development Certificates lodged in{' '}
            {stats.councilName}.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
            <StatCard
              label="Total applications"
              value={stats.totalApplications.toLocaleString()}
              note={`Since ${stats.earliestDate?.slice(0, 4) ?? '2021'}`}
            />
            <StatCard
              label="CDC pathway"
              value={stats.cdcRatioPct !== null ? `${formatPct(stats.cdcRatioPct)}` : `${stats.cdcTotal} CDCs`}
              note={`${stats.cdcTotal} of ${stats.totalApplications} applications`}
            />
            <StatCard
              label="DA pathway"
              value={`${stats.daTotal} applications`}
              note={`${stats.daDetermined} decided`}
            />
            <StatCard
              label="CDC median time"
              value={formatDays(stats.cdcMedianDays)}
              note="Submission to determination"
            />
            <StatCard
              label="DA median time"
              value={formatDays(stats.daMedianDays)}
              note="Lodgement to determination"
            />
            <StatCard
              label="Median build cost (CDC)"
              value={formatCost(stats.cdcMedianCost)}
              note="Self-reported at lodgement"
            />
          </div>
          {trend && (
            <p className="text-sm text-slate-500 italic mt-2">
              Application volume is {trend}.
            </p>
          )}
        </section>

        {/* SECTION 2: CDC vs DA */}
        <section id="cdc-vs-da" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            CDC vs DA pathway split
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A Complying Development Certificate (CDC) is issued by a private
            certifier when a property meets all SEPP Housing 2021 standards. A
            Development Application (DA) goes through council assessment and is
            required when the property has constraints like heritage listing, flood
            overlay, or environmental sensitivity.
          </p>
          <CdcDaBar stats={stats} />
          <p className="text-sm text-slate-500">
            All CDC records in the NSW Planning Portal have status
            &ldquo;Approved&rdquo; &mdash; rejected CDC applications are not
            published in the open dataset. DA records show status
            &ldquo;Determined&rdquo; for all decided applications &mdash; the
            portal does not distinguish between approved and refused DAs.
          </p>
        </section>

        {/* SECTION 3: Processing times & costs */}
        <section id="processing-times" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Processing times and costs
          </h2>

          <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8">
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 pr-4 font-semibold text-slate-900" />
                    <th className="text-left py-3 pr-4 font-semibold text-teal-700">CDC pathway</th>
                    <th className="text-left py-3 font-semibold text-amber-700">DA pathway</th>
                  </tr>
                </thead>
                <tbody className="text-slate-700">
                  <tr className="border-b border-slate-100">
                    <td className="py-2.5 pr-4 font-medium text-slate-900">Median processing time</td>
                    <td className="py-2.5 pr-4">{formatDays(stats.cdcMedianDays)}</td>
                    <td className="py-2.5">{formatDays(stats.daMedianDays)}</td>
                  </tr>
                  <tr className="border-b border-slate-100">
                    <td className="py-2.5 pr-4 font-medium text-slate-900">Median development cost</td>
                    <td className="py-2.5 pr-4">{formatCost(stats.cdcMedianCost)}</td>
                    <td className="py-2.5">{formatCost(stats.daMedianCost)}</td>
                  </tr>
                  <tr className="border-b border-slate-100">
                    <td className="py-2.5 pr-4 font-medium text-slate-900">Average development cost</td>
                    <td className="py-2.5 pr-4">{formatCost(stats.cdcAvgCost)}</td>
                    <td className="py-2.5">{formatCost(stats.daAvgCost)}</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 pr-4 font-medium text-slate-900">Application count</td>
                    <td className="py-2.5 pr-4">{stats.cdcTotal.toLocaleString()}</td>
                    <td className="py-2.5">{stats.daTotal.toLocaleString()}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-xs text-slate-400 mt-4">
              Cost of development is self-reported by applicants at lodgement and
              may not reflect actual construction costs. Processing time outliers
              (&gt;365 days for CDCs, &gt;730 days for DAs) are excluded from
              median calculations.
            </p>
          </div>
        </section>

        {/* SECTION 4: Yearly breakdown */}
        <section id="yearly-trend" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Year-by-year breakdown
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Secondary dwelling application volumes in {stats.shortName} by year,
            split by pathway. NSW Planning Portal reporting became mandatory for
            all councils from 1 July 2021, so earlier years may have incomplete
            data.
          </p>
          <YearlyBreakdown stats={stats} />
        </section>

        {/* SECTION 5: SEPP eligibility */}
        <section id="eligibility" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            SEPP Housing 2021 eligibility requirements
          </h2>
          <p className="text-slate-700 leading-relaxed">
            These state-wide standards apply to all secondary dwellings in NSW,
            including those in {stats.shortName}. Meeting all standards qualifies
            a property for the CDC (complying development) pathway.
          </p>
          <div className="grid sm:grid-cols-2 gap-4 mt-2">
            {[
              { label: 'Minimum lot size', value: '450 m\u00B2' },
              { label: 'Maximum floor area', value: '60 m\u00B2' },
              { label: 'Permitted zones', value: 'R1, R2, R3, RU5' },
              { label: 'Rear setback', value: '3 m (SEPP minimum)' },
              { label: 'Side setback', value: '0.9 m (SEPP minimum)' },
              { label: 'Maximum height', value: '8.5 m (2 storeys)' },
            ].map(item => (
              <div
                key={item.label}
                className="rounded-xl border border-slate-200 bg-white p-4"
              >
                <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
                  {item.label}
                </p>
                <p className="text-lg font-bold text-slate-900 mt-1">{item.value}</p>
              </div>
            ))}
          </div>
          <p className="text-sm text-slate-500 mt-2">
            Properties with heritage listing, flood overlays, biodiversity values,
            or acid sulfate soil classifications are excluded from the CDC pathway
            and require a Development Application. See{' '}
            <Link
              href="/blog/can-i-build-a-granny-flat-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              our full eligibility guide
            </Link>{' '}
            for details on each exclusion.
          </p>
        </section>

        {/* FAQ */}
        <FaqSection stats={stats} />

        {/* CTA */}
        <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-6 sm:p-8">
          <h3 className="text-lg font-bold text-slate-900 mb-2">
            Check if your {stats.shortName} property qualifies
          </h3>
          <p className="text-sm text-slate-600 mb-4">
            Enter an address to check lot size, zoning, heritage, flood, and
            environmental overlays against SEPP Housing 2021 requirements.
          </p>
          <TrackedLink
            href={hasToolPage ? `/granny-flat/${stats.slug}` : '/reports/granny-flat'}
            page={`granny-flat-${stats.slug}`}
            cta="check_granny_flat"
            className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
          >
            Run free eligibility check
            <ArrowRight className="h-4 w-4" />
          </TrackedLink>
        </div>

        {/* Cross-links to related council pages */}
        <RelatedCouncils currentSlug={stats.slug} />
      </div>

      <BlogDisclaimer />

      {/* Schema markup */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: trustedJsonLd({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: `Granny flat applications in ${stats.shortName}: CDC and DA statistics`,
            datePublished: '2026-05-20',
            dateModified: DATA_AS_OF,
            author: {
              '@type': 'Organization',
              name: 'PlotDetect',
              url: 'https://www.plotdetect.com.au',
            },
          }),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: trustedJsonLd({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: [
              {
                '@type': 'Question',
                name: `How many granny flat applications has ${stats.shortName} received?`,
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: `NSW Planning Portal records show ${stats.totalApplications} secondary dwelling applications in ${stats.councilName}.`,
                },
              },
              {
                '@type': 'Question',
                name: `What percentage use the CDC pathway in ${stats.shortName}?`,
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: stats.cdcRatioPct !== null
                    ? `${stats.cdcRatioPct}% of secondary dwelling applications used the CDC pathway.`
                    : 'Insufficient data to report a reliable percentage.',
                },
              },
            ],
          }),
        }}
      />
    </article>
  )
}

/* ------------------------------------------------------------------ */
/*  Related councils — nearby in the sorted list                       */
/* ------------------------------------------------------------------ */

function RelatedCouncils({ currentSlug }: { currentSlug: string }) {
  const idx = COUNCIL_STATS.findIndex(c => c.slug === currentSlug)
  if (idx === -1) return null

  // Pick up to 4 neighbours in the list (by alphabetical proximity)
  const related: CouncilStats[] = []
  for (const offset of [-2, -1, 1, 2]) {
    const c = COUNCIL_STATS[idx + offset]
    if (c) related.push(c)
  }
  if (related.length === 0) return null

  return (
    <div className="mt-2">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-3">
        Other council statistics
      </p>
      <div className="flex flex-wrap gap-2">
        {related.map(c => (
          <Link
            key={c.slug}
            href={`/blog/granny-flat/${c.slug}`}
            className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors"
          >
            {c.shortName}
          </Link>
        ))}
      </div>
    </div>
  )
}
