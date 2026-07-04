import type { Metadata } from 'next'
import Link from 'next/link'
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react'
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer'
import { COUNCIL_STATS, DATA_AS_OF } from '@/lib/lga-data/secondary-dwelling-stats'
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title: 'Granny Flat Statistics by Council — NSW Secondary Dwelling Data | PlotDetect',
  description:
    'Secondary dwelling DA and CDC statistics for 102 NSW councils. Application volumes, CDC pathway rates, processing times, and build costs from NSW Planning Portal data.',
  keywords: [
    'granny flat statistics NSW',
    'secondary dwelling data by council',
    'CDC approval rates NSW',
    'granny flat council comparison',
    'NSW granny flat data',
  ],
}

/* Sort councils by total applications descending */
const SORTED_BY_VOLUME = [...COUNCIL_STATS].sort(
  (a, b) => b.totalApplications - a.totalApplications,
)

/* Aggregate totals for headline */
const TOTALS = {
  councils: COUNCIL_STATS.length,
  applications: COUNCIL_STATS.reduce((s, c) => s + c.totalApplications, 0),
  cdcs: COUNCIL_STATS.reduce((s, c) => s + c.cdcTotal, 0),
  das: COUNCIL_STATS.reduce((s, c) => s + c.daTotal, 0),
}

/* --- Ranking tables (top 10 each, filtered for data quality) --- */
const MIN_APPS_FOR_RANKING = 10

const TOP_CDC_SPEED = [...COUNCIL_STATS]
  .filter(c => c.cdcMedianDays != null && c.cdcTotal >= MIN_APPS_FOR_RANKING)
  .sort((a, b) => a.cdcMedianDays! - b.cdcMedianDays!)
  .slice(0, 10)

const TOP_CDC_RATIO = [...COUNCIL_STATS]
  .filter(c => c.cdcRatioPct != null && c.totalApplications >= MIN_APPS_FOR_RANKING)
  .sort((a, b) => b.cdcRatioPct! - a.cdcRatioPct!)
  .slice(0, 10)

const TOP_LOWEST_CDC_COST = [...COUNCIL_STATS]
  .filter(c => c.cdcMedianCost != null && c.cdcTotal >= MIN_APPS_FOR_RANKING)
  .sort((a, b) => a.cdcMedianCost! - b.cdcMedianCost!)
  .slice(0, 10)

const TOP_HIGHEST_VOLUME = SORTED_BY_VOLUME.slice(0, 10)

function formatPct(value: number | null): string {
  if (value == null) return 'N/A'
  return `${value}%`
}

function formatDays(value: number | null): string {
  if (value == null) return '-'
  return `${value}d`
}

function formatCostShort(value: number | null): string {
  if (value == null) return '-'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K`
  return `$${value}`
}

export default function GrannyFlatBlogIndexPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Granny Flat Statistics by Council — NSW Secondary Dwelling Data"
        description="Secondary dwelling DA and CDC statistics for 102 NSW councils. Application volumes, CDC pathway rates, processing times, and build costs from NSW Planning Portal data."
        slug="granny-flat"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <Link
            href="/blog"
            className="text-xs text-slate-400 hover:text-teal-600 transition-colors"
          >
            Insights
          </Link>
          <span className="text-xs text-slate-300">/</span>
          <span className="text-xs text-slate-500">Council Data</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          Granny flat applications by council
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed max-w-2xl">
          Secondary dwelling DA and CDC statistics for {TOTALS.councils} NSW
          councils. {TOTALS.applications.toLocaleString()} applications recorded
          in the NSW Planning Portal open dataset. Data generated on {DATA_AS_OF}.
        </p>
      </div>

      {/* Headline stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">Councils</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{TOTALS.councils}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">Total applications</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{TOTALS.applications.toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">CDCs issued</p>
          <p className="text-2xl font-bold text-teal-700 mt-1">{TOTALS.cdcs.toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">DAs lodged</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">{TOTALS.das.toLocaleString()}</p>
        </div>
      </div>

      {/* --- Ranking leaderboards --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        {/* Fastest CDC processing */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">
            Fastest CDC processing
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Councils with the shortest median CDC turnaround (minimum {MIN_APPS_FOR_RANKING} CDCs)
          </p>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 pr-2 font-semibold text-slate-700">#</th>
                <th className="text-left py-2 pr-2 font-semibold text-slate-700">Council</th>
                <th className="text-right py-2 px-2 font-semibold text-teal-700">Median days</th>
                <th className="text-right py-2 pl-2 font-semibold text-slate-500">CDCs</th>
              </tr>
            </thead>
            <tbody className="text-slate-700">
              {TOP_CDC_SPEED.map((c, i) => (
                <tr key={c.slug} className="border-b border-slate-50">
                  <td className="py-2 pr-2 text-slate-400 font-medium">{i + 1}</td>
                  <td className="py-2 pr-2">
                    <Link href={`/blog/granny-flat/${c.slug}`} className="font-medium text-slate-900 hover:text-teal-600 transition-colors">
                      {c.shortName}
                    </Link>
                  </td>
                  <td className="py-2 px-2 text-right font-bold text-teal-700">{c.cdcMedianDays}d</td>
                  <td className="py-2 pl-2 text-right text-slate-500">{c.cdcTotal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Highest CDC ratio */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">
            Highest CDC pathway usage
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Councils where the largest share of granny flat applications use the CDC pathway (minimum {MIN_APPS_FOR_RANKING} applications)
          </p>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 pr-2 font-semibold text-slate-700">#</th>
                <th className="text-left py-2 pr-2 font-semibold text-slate-700">Council</th>
                <th className="text-right py-2 px-2 font-semibold text-teal-700">CDC %</th>
                <th className="text-right py-2 pl-2 font-semibold text-slate-500">Total</th>
              </tr>
            </thead>
            <tbody className="text-slate-700">
              {TOP_CDC_RATIO.map((c, i) => (
                <tr key={c.slug} className="border-b border-slate-50">
                  <td className="py-2 pr-2 text-slate-400 font-medium">{i + 1}</td>
                  <td className="py-2 pr-2">
                    <Link href={`/blog/granny-flat/${c.slug}`} className="font-medium text-slate-900 hover:text-teal-600 transition-colors">
                      {c.shortName}
                    </Link>
                  </td>
                  <td className="py-2 px-2 text-right font-bold text-teal-700">{c.cdcRatioPct}%</td>
                  <td className="py-2 pl-2 text-right text-slate-500">{c.totalApplications}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Lowest CDC cost */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">
            Lowest median CDC cost
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Councils with the lowest self-reported median CDC build cost (minimum {MIN_APPS_FOR_RANKING} CDCs)
          </p>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 pr-2 font-semibold text-slate-700">#</th>
                <th className="text-left py-2 pr-2 font-semibold text-slate-700">Council</th>
                <th className="text-right py-2 px-2 font-semibold text-teal-700">Median cost</th>
                <th className="text-right py-2 pl-2 font-semibold text-slate-500">CDCs</th>
              </tr>
            </thead>
            <tbody className="text-slate-700">
              {TOP_LOWEST_CDC_COST.map((c, i) => (
                <tr key={c.slug} className="border-b border-slate-50">
                  <td className="py-2 pr-2 text-slate-400 font-medium">{i + 1}</td>
                  <td className="py-2 pr-2">
                    <Link href={`/blog/granny-flat/${c.slug}`} className="font-medium text-slate-900 hover:text-teal-600 transition-colors">
                      {c.shortName}
                    </Link>
                  </td>
                  <td className="py-2 px-2 text-right font-bold text-teal-700">{formatCostShort(c.cdcMedianCost)}</td>
                  <td className="py-2 pl-2 text-right text-slate-500">{c.cdcTotal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Highest volume */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">
            Most granny flat applications
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Councils with the highest total secondary dwelling application volume
          </p>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 pr-2 font-semibold text-slate-700">#</th>
                <th className="text-left py-2 pr-2 font-semibold text-slate-700">Council</th>
                <th className="text-right py-2 px-2 font-semibold text-teal-700">Applications</th>
                <th className="text-right py-2 pl-2 font-semibold text-slate-500">CDC %</th>
              </tr>
            </thead>
            <tbody className="text-slate-700">
              {TOP_HIGHEST_VOLUME.map((c, i) => (
                <tr key={c.slug} className="border-b border-slate-50">
                  <td className="py-2 pr-2 text-slate-400 font-medium">{i + 1}</td>
                  <td className="py-2 pr-2">
                    <Link href={`/blog/granny-flat/${c.slug}`} className="font-medium text-slate-900 hover:text-teal-600 transition-colors">
                      {c.shortName}
                    </Link>
                  </td>
                  <td className="py-2 px-2 text-right font-bold text-teal-700">{c.totalApplications}</td>
                  <td className="py-2 pl-2 text-right text-slate-500">{formatPct(c.cdcRatioPct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-slate-400 mb-10">
        Rankings derived from NSW Planning Portal open data as of {DATA_AS_OF}. Cost is self-reported at lodgement.
        CDC time is median calendar days from submission to determination. Minimum sample size of {MIN_APPS_FOR_RANKING} applications for ranking inclusion.
      </p>

      {/* Council table */}
      <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4 sm:p-6 mb-10">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
          All councils — sorted by application volume
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2.5 pr-3 font-semibold text-slate-900">Council</th>
                <th className="text-right py-2.5 px-3 font-semibold text-slate-900">Total</th>
                <th className="text-right py-2.5 px-3 font-semibold text-teal-700">CDCs</th>
                <th className="text-right py-2.5 px-3 font-semibold text-amber-700">DAs</th>
                <th className="text-right py-2.5 px-3 font-semibold text-slate-900 hidden sm:table-cell">CDC %</th>
                <th className="text-right py-2.5 px-3 font-semibold text-slate-900 hidden md:table-cell">CDC time</th>
                <th className="text-right py-2.5 pl-3 font-semibold text-slate-900 hidden md:table-cell">Median cost</th>
              </tr>
            </thead>
            <tbody className="text-slate-700">
              {SORTED_BY_VOLUME.map(c => (
                <tr key={c.slug} className="border-b border-slate-100 hover:bg-white transition-colors">
                  <td className="py-2.5 pr-3">
                    <Link
                      href={`/blog/granny-flat/${c.slug}`}
                      className="font-medium text-slate-900 hover:text-teal-600 transition-colors"
                    >
                      {c.shortName}
                    </Link>
                  </td>
                  <td className="py-2.5 px-3 text-right font-medium">{c.totalApplications}</td>
                  <td className="py-2.5 px-3 text-right text-teal-700">{c.cdcTotal}</td>
                  <td className="py-2.5 px-3 text-right text-amber-700">{c.daTotal}</td>
                  <td className="py-2.5 px-3 text-right hidden sm:table-cell">
                    {c.totalApplications >= 10 ? formatPct(c.cdcRatioPct) : '-'}
                  </td>
                  <td className="py-2.5 px-3 text-right hidden md:table-cell">{formatDays(c.cdcMedianDays)}</td>
                  <td className="py-2.5 pl-3 text-right hidden md:table-cell">{formatCostShort(c.cdcMedianCost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-slate-400 mt-4">
          Source: NSW Planning Portal open data as of {DATA_AS_OF}. CDC % only
          shown for councils with 10+ applications. Cost is self-reported at
          lodgement. CDC time is median calendar days from submission to determination.
        </p>
      </div>

      {/* CTA */}
      <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-6 sm:p-8 mb-6">
        <h2 className="text-lg font-bold text-slate-900 mb-2">
          Check if your property qualifies for a granny flat
        </h2>
        <p className="text-sm text-slate-600 mb-4">
          Enter an address to check lot size, zoning, heritage, flood, and
          environmental overlays against SEPP Housing 2021 requirements.
        </p>
        <TrackedLink
          href="/reports/granny-flat"
          page="granny-flat"
          cta="check_granny_flat"
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
        >
          Run free eligibility check
          <ArrowRight className="h-4 w-4" />
        </TrackedLink>
      </div>

      {/* Related articles */}
      <div className="mt-8">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-3">
          Related articles
        </p>
        <div className="flex flex-wrap gap-2">
          <Link href="/blog/can-i-build-a-granny-flat-nsw" className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors">
            Eligibility guide
          </Link>
          <Link href="/blog/dcp-setbacks-granny-flat-nsw" className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors">
            DCP setback differences
          </Link>
          <Link href="/blog/granny-flat-rental-income-roi" className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors">
            Rental income & ROI
          </Link>
          <Link href="/blog/heritage-conservation-area-granny-flat-nsw" className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors">
            Heritage blockers
          </Link>
        </div>
      </div>

      <BlogDisclaimer />
    </div>
  )
}
