import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { COUNCIL_STATS } from '@/lib/lga-data/secondary-dwelling-stats';

/* ------------------------------------------------------------------ */
/*  Article metadata                                                   */
/* ------------------------------------------------------------------ */

const ARTICLES: {
  slug: string;
  title: string;
  description: string;
  category: 'Climate Risk' | 'Planning' | 'Property Research';
  date: string;
}[] = [
  {
    slug: 'aasb-s2-property-climate-data',
    title: 'AASB S2 and property-level climate data: what fund managers need',
    description: 'How AASB S2 climate disclosure requirements affect property portfolio reporting, and where to source location-specific physical risk data in Australia.',
    category: 'Climate Risk',
    date: '2026-05-17',
  },
  {
    slug: 'apra-cpg-229-property-assessment',
    title: 'APRA CPG 229: climate risk assessment for property lending',
    description: 'A practical guide to meeting APRA CPG 229 requirements for property-secured lending, including physical risk data, scenario analysis, and portfolio screening.',
    category: 'Climate Risk',
    date: '2026-05-17',
  },
  {
    slug: 'climate-risk-data-provider-australia',
    title: 'Climate risk data providers in Australia: a comparison',
    description: 'Comparing Australian climate risk data sources — government, commercial, and open-source — for flood, bushfire, coastal, and heat stress assessment.',
    category: 'Climate Risk',
    date: '2026-05-17',
  },
  {
    slug: 'uninsurable-property-climate-risk',
    title: 'Uninsurable properties: how climate risk is repricing Australian real estate',
    description: 'Insurance withdrawal, premium spikes, and the emerging data infrastructure that buyers need to assess property-level climate exposure before purchase.',
    category: 'Climate Risk',
    date: '2026-05-17',
  },
  {
    slug: 'is-my-house-in-a-flood-zone-nsw',
    title: 'Is my house in a flood zone? How to check in NSW',
    description: 'Step-by-step guide to checking flood zone status for any NSW property — free government sources, what the data actually means, and what it misses.',
    category: 'Property Research',
    date: '2026-05-17',
  },
];

const CATEGORY_COLORS: Record<string, string> = {
  'Climate Risk': 'bg-teal-500/10 text-teal-700',
  'Planning': 'bg-blue-500/10 text-blue-700',
  'Property Research': 'bg-amber-500/10 text-amber-700',
};

/* Top councils by volume for the featured section */
const TOP_COUNCILS = [...COUNCIL_STATS]
  .sort((a, b) => b.totalApplications - a.totalApplications)
  .slice(0, 12);

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function BlogIndexPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      <div className="mb-12">
        <h1 className="text-4xl font-bold text-slate-900 tracking-tight mb-3">
          Insights
        </h1>
        <p className="text-slate-500 text-lg max-w-xl">
          Property intelligence, climate risk analysis, and planning compliance
          research for professionals.
        </p>
      </div>

      {/* Council data section */}
      <div className="mb-10">
        <Link
          href="/blog/granny-flat"
          className="group block rounded-2xl border border-teal-200 bg-teal-50/30 p-6 hover:border-teal-400 hover:shadow-lg hover:shadow-teal-500/5 transition-all"
        >
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-700">
              Council Data
            </span>
            <span className="text-xs text-slate-400">{COUNCIL_STATS.length} councils</span>
          </div>
          <h2 className="text-lg font-semibold text-slate-900 mb-2 group-hover:text-teal-700 transition-colors">
            Granny flat applications by council — CDC and DA statistics
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed mb-3">
            Secondary dwelling application volumes, CDC pathway rates, processing
            times, and build costs for {COUNCIL_STATS.length} NSW councils. NSW
            Planning Portal open data.
          </p>
          <div className="flex flex-wrap gap-2 mb-4">
            {TOP_COUNCILS.slice(0, 6).map(c => (
              <span key={c.slug} className="text-xs px-2 py-1 rounded-md bg-white border border-slate-200 text-slate-600">
                {c.shortName} ({c.totalApplications})
              </span>
            ))}
            <span className="text-xs px-2 py-1 text-slate-400">
              +{COUNCIL_STATS.length - 6} more
            </span>
          </div>
          <span className="inline-flex items-center gap-1 text-sm text-teal-600 font-medium group-hover:text-teal-500 transition-colors">
            View all councils
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </span>
        </Link>
      </div>

      {/* Articles */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {ARTICLES.map((article) => (
          <Link
            key={article.slug}
            href={`/blog/${article.slug}`}
            className="group rounded-2xl border border-slate-200 p-6 hover:border-teal-500/40 hover:shadow-lg hover:shadow-teal-500/5 transition-all"
          >
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${CATEGORY_COLORS[article.category]}`}>
                {article.category}
              </span>
              <span className="text-xs text-slate-400">{article.date}</span>
            </div>
            <h2 className="text-lg font-semibold text-slate-900 mb-2 group-hover:text-teal-700 transition-colors">
              {article.title}
            </h2>
            <p className="text-sm text-slate-500 leading-relaxed mb-4">
              {article.description}
            </p>
            <span className="inline-flex items-center gap-1 text-sm text-teal-600 font-medium group-hover:text-teal-500 transition-colors">
              Read more
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
