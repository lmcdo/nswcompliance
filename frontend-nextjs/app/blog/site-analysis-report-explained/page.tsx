import type { Metadata } from 'next';
import Link from 'next/link';
import { COVERAGE_DISPLAY } from '@/lib/coverage';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Site Analysis Reports Explained: What They Cover and Why They Matter — PlotDetect',
  description:
    'A site analysis report collates planning controls, spatial constraints, and environmental factors for a specific property. This guide explains what a site analysis includes, who needs one, and what data sources feed into it.',
  keywords: [
    'site analysis report nsw',
    'site analysis property development',
    'planning site analysis',
    'site analysis checklist',
    'property site assessment',
    'site constraints report',
    'pre-purchase site analysis',
    'development site assessment',
    'site analysis planning consultant',
    'site due diligence property',
  ],
};

/* ------------------------------------------------------------------ */
/*  What a site analysis covers                                        */
/* ------------------------------------------------------------------ */

function SiteAnalysisChecklist() {
  const categories = [
    {
      category: 'Planning controls',
      items: [
        { item: 'Zone and land use permissibility', source: 'LEP / Planning Portal' },
        { item: 'Floor space ratio (FSR)', source: 'LEP Height/FSR Map' },
        { item: 'Building height limit', source: 'LEP HOB Map' },
        { item: 'Minimum lot size', source: 'LEP Lot Size Map' },
        { item: 'Heritage listing or conservation area', source: 'LEP Heritage Map / s10.7' },
        { item: 'DCP setbacks, parking, landscaping, site coverage', source: 'Council DCP (PDF)' },
        { item: 'Precinct-specific DCP controls', source: 'Council DCP precinct maps' },
      ],
    },
    {
      category: 'Spatial overlays',
      items: [
        { item: 'Flood prone land', source: 'LEP Flood Planning Map / council records' },
        { item: 'Bushfire prone land', source: 'RFS BFPL Map' },
        { item: 'Acid sulfate soils', source: 'LEP ASS Map' },
        { item: 'Riparian corridor / waterway', source: 'LEP / DCP' },
        { item: 'Foreshore building line', source: 'LEP' },
        { item: 'ANEF noise contours (near airports)', source: 'LEP' },
        { item: 'Contaminated land', source: 'EPA CLM register / s10.7' },
      ],
    },
    {
      category: 'SEPP applicability',
      items: [
        { item: 'Housing SEPP (secondary dwellings, in-fill affordable)', source: 'SEPP (Housing) 2021' },
        { item: 'Exempt & Complying development', source: 'SEPP (Exempt & Complying) 2008' },
        { item: 'Transport & Infrastructure', source: 'SEPP (T&I) 2021' },
        { item: 'Resilience & Hazards (coastal, flooding)', source: 'SEPP (R&H) 2021' },
      ],
    },
    {
      category: 'Environmental & physical',
      items: [
        { item: 'Flood depth at key return periods (1% AEP etc.)', source: 'Council flood study / modelling' },
        { item: 'Bushfire Attack Level (BAL) estimate', source: 'AS 3959 / RFS assessment' },
        { item: 'Topography and slope', source: 'Survey / LiDAR' },
        { item: 'Tree canopy and vegetation', source: 'Aerial imagery / council TPO' },
        { item: 'Solar access and overshadowing', source: 'Shadow analysis' },
      ],
    },
  ];

  return (
    <div className="space-y-6 my-6">
      {categories.map(({ category, items }) => (
        <div key={category}>
          <h3 className="font-semibold text-slate-900 text-sm mb-3">{category}</h3>
          <div className="rounded-xl border border-slate-200 overflow-hidden">
            {items.map(({ item, source }, i) => (
              <div
                key={item}
                className={`flex items-start justify-between gap-4 px-4 py-2.5 text-sm ${
                  i > 0 ? 'border-t border-slate-100' : ''
                }`}
              >
                <span className="text-slate-700">{item}</span>
                <span className="text-xs text-slate-400 flex-shrink-0 text-right">{source}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Who needs a site analysis                                          */
/* ------------------------------------------------------------------ */

function WhoNeedsGrid() {
  const audiences = [
    {
      who: 'Property buyers',
      why: 'Understand what can be built before purchasing. Identify constraints that affect property value or intended use.',
    },
    {
      who: 'Planning consultants',
      why: 'Data gathering phase for pre-lodgement advice, DA preparation, or feasibility assessment. The site analysis informs the planning report.',
    },
    {
      who: 'Architects',
      why: 'Define the building envelope before design begins. Height, setbacks, FSR, and site coverage set the 3D constraints for the design.',
    },
    {
      who: 'Developers',
      why: 'Feasibility assessment before acquiring a site. FSR × lot area = maximum GFA. Height and setbacks define yield.',
    },
    {
      who: 'Conveyancers',
      why: 'Due diligence beyond the s10.7 certificate. Flood depth, DCP constraints, and spatial overlays that certificates do not include.',
    },
    {
      who: 'Investors',
      why: 'Development potential assessment. Is subdivision possible? Is the site under-developed relative to its zoning? Are there constraints that limit future development?',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-6">
      {audiences.map(({ who, why }) => (
        <div key={who} className="rounded-xl border border-slate-200 p-4">
          <p className="font-semibold text-slate-900 text-sm mb-1">{who}</p>
          <p className="text-sm text-slate-500">{why}</p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function SiteAnalysisReportPage() {
  return (
    <article className="max-w-2xl mx-auto px-6 py-12">
      <BlogPostingJsonLd
        title="Site Analysis Reports Explained: What They Cover and Why They Matter"
        description="A site analysis report collates planning controls, spatial constraints, and environmental factors for a specific property. This guide explains what a site analysis includes, who needs one, and what data sources feed into it."
        slug="site-analysis-report-explained"
        date="2026-05-20"
      />
      {/* Reverse pyramid — answer first */}
      <h1 className="text-3xl font-bold text-slate-900 mb-4">
        Site Analysis Reports Explained: What They Cover and Why They Matter
      </h1>

      <p className="text-lg text-slate-600 mb-6 leading-relaxed">
        A site analysis report brings together planning controls, spatial constraints, and
        environmental factors for a specific property — zone, FSR, height, setbacks, flood,
        bushfire, heritage, and more. It is the data-gathering step that precedes design,
        feasibility, or purchase decisions. Getting it wrong (or incomplete) means the
        project starts from bad assumptions.
      </p>

      <div className="rounded-xl bg-teal-50 border border-teal-200 p-4 text-sm text-teal-800 mb-8">
        <strong>Quick lookup:</strong>{' '}
        <Link href="/assessment" className="text-teal-700 underline underline-offset-2 hover:text-teal-600">
          Enter your address in Verify
        </Link>{' '}
        to generate a structured site analysis — zone, LEP controls, DCP provisions, SEPP
        applicability, flood, bushfire, and spatial overlays.
      </div>

      {/* TOC */}
      <nav className="rounded-xl border border-slate-200 p-5 mb-10">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Contents</p>
        <ul className="space-y-1.5 text-sm">
          {[
            ['what-is-site-analysis', 'What is a site analysis report?'],
            ['who-needs', 'Who needs a site analysis?'],
            ['what-it-covers', 'What a site analysis covers'],
            ['data-sources', 'Where the data comes from'],
            ['s107-vs-site-analysis', 'Section 10.7 certificate vs site analysis'],
            ['common-gaps', 'Common gaps in site analysis'],
            ['how-long', 'How long does a manual site analysis take?'],
            ['automated-analysis', 'Automated site analysis'],
          ].map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} className="text-teal-600 hover:text-teal-500">{label}</a>
            </li>
          ))}
        </ul>
      </nav>

      {/* ---- What is a site analysis ---- */}
      <section id="what-is-site-analysis" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">What is a site analysis report?</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A site analysis report compiles all the planning controls, environmental constraints,
          and physical characteristics that apply to a specific property. It answers the
          question: &ldquo;What are the rules and constraints for this site?&rdquo;
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The site analysis is the foundation of every planning assessment. Before a planner
          writes a Statement of Environmental Effects (SEE), before an architect starts
          sketching, and before a developer runs a feasibility model — someone needs to know
          what the controls are.
        </p>
        <p className="text-slate-600 leading-relaxed">
          A site analysis is not a planning assessment. It does not interpret whether a proposed
          development is likely to receive consent. It gathers the raw data — the controls, overlays,
          and constraints — that a professional then interprets in context.
        </p>
      </section>

      {/* ---- Who needs ---- */}
      <section id="who-needs" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Who needs a site analysis?</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Anyone making a decision about a property — buying, building, investing, or advising —
          needs to understand what applies to the site.
        </p>
        <WhoNeedsGrid />
        <p className="text-sm text-slate-500 leading-relaxed">
          For{' '}
          <Link href="/for/planners" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            planning professionals
          </Link>
          , the site analysis is a daily task — often repeated multiple times per week across
          different properties.
        </p>
      </section>

      {/* ---- What it covers ---- */}
      <section id="what-it-covers" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">What a site analysis covers</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A thorough site analysis covers four categories of data: planning controls (LEP + DCP),
          spatial overlays, SEPP applicability, and environmental/physical characteristics.
        </p>
        <SiteAnalysisChecklist />
        <p className="text-sm text-slate-500 leading-relaxed">
          Not every property requires every item. A flat suburban lot in an established area
          may only need the planning controls section. A waterfront lot with flood risk, heritage
          constraints, and acid sulfate soils needs the full analysis.
        </p>
      </section>

      {/* ---- Data sources ---- */}
      <section id="data-sources" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Where the data comes from</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Site analysis data comes from multiple disconnected sources:
        </p>
        <ul className="list-disc list-inside space-y-2 text-sm text-slate-600 mb-4 ml-2">
          <li>
            <strong>NSW Planning Portal</strong> — zone, LEP numeric controls (FSR, height, lot size),
            heritage listings, and some spatial layers
          </li>
          <li>
            <strong>Council websites</strong> — DCP documents (PDF), local flood maps, development
            contribution plans
          </li>
          <li>
            <strong>NSW Legislation</strong> — LEP and SEPP full text
          </li>
          <li>
            <strong>RFS (Rural Fire Service)</strong> — Bush Fire Prone Land mapping
          </li>
          <li>
            <strong>EPA (Environment Protection Authority)</strong> — Contaminated Land Management
            register
          </li>
          <li>
            <strong>Council flood studies</strong> — modelled flood depths at various return periods
          </li>
          <li>
            <strong>Survey and LiDAR</strong> — topography and existing site conditions
          </li>
        </ul>
        <p className="text-slate-600 leading-relaxed">
          The fragmentation of data sources is the primary reason manual site analysis is
          time-consuming. Each source has its own interface, format, and level of detail. The{' '}
          <Link href="/blog/nsw-planning-portal-gaps" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            NSW Planning Portal covers some of this but has significant gaps
          </Link>
          , particularly around DCP controls, flood depth, and SEPP applicability.
        </p>
      </section>

      {/* ---- s10.7 vs site analysis ---- */}
      <section id="s107-vs-site-analysis" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Section 10.7 certificate vs site analysis
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A section 10.7 planning certificate (formerly s149 certificate) is a formal document
          issued by the council that lists prescribed matters affecting a property. It is a
          required part of the conveyancing process.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          However, a s10.7 certificate is not a site analysis. It confirms zone, height, FSR,
          heritage listing, and some spatial constraints — but it does not include:
        </p>
        <ul className="list-disc list-inside space-y-1 text-sm text-slate-600 mb-4 ml-2">
          <li>DCP setbacks, parking rates, landscaping, or site coverage</li>
          <li>Modelled flood depth at specific return periods</li>
          <li>Bushfire Attack Level (BAL) estimate</li>
          <li>Land use permissibility (what you can build in the zone)</li>
          <li>SEPP applicability or which clauses apply</li>
          <li>Development potential or feasibility indicators</li>
        </ul>
        <p className="text-slate-600 leading-relaxed">
          A site analysis fills these gaps. It is the complement to the s10.7 certificate — the
          certificate gives you the statutory baseline; the site analysis gives you the
          operational detail needed for design, feasibility, or purchase decisions.
        </p>
      </section>

      {/* ---- Common gaps ---- */}
      <section id="common-gaps" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Common gaps in site analysis
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Even experienced professionals sometimes miss data that affects the project later:
        </p>
        <div className="space-y-3 my-4">
          {[
            {
              gap: 'Missing the precinct-specific DCP controls',
              impact: 'General setbacks assumed, but precinct controls are stricter. Design needs to be revised after DA feedback.',
            },
            {
              gap: 'Not checking flood depth (only flood prone yes/no)',
              impact: 'Knowing a property is flood prone is step one. The flood depth determines floor level, insurance, and whether certain development types are viable.',
            },
            {
              gap: 'Heritage conservation area vs individual heritage item',
              impact: 'These have different implications. An HCA affects CDC eligibility and design controls. An individual heritage item has additional assessment requirements.',
            },
            {
              gap: 'Not checking SEPP provisions',
              impact: 'SEPP clauses can override LEP controls — both expanding and restricting what is permitted. Missing a SEPP provision can invalidate an entire DA strategy.',
            },
            {
              gap: 'Relying solely on the s10.7 certificate',
              impact: 'The certificate is necessary but incomplete. DCP controls, flood depth, and development potential are not included.',
            },
          ].map(({ gap, impact }) => (
            <div key={gap} className="rounded-xl border border-slate-200 p-4">
              <p className="font-semibold text-slate-900 text-sm mb-1">{gap}</p>
              <p className="text-sm text-slate-500">{impact}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---- How long ---- */}
      <section id="how-long" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          How long does a manual site analysis take?
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A thorough manual site analysis for a single NSW property typically takes
          1.5&ndash;2.5 hours, depending on the complexity of the site and the council area.
          The time breaks down roughly as:
        </p>
        <ul className="list-disc list-inside space-y-1 text-sm text-slate-600 mb-4 ml-2">
          <li>Zone and LEP controls lookup: 10&ndash;15 minutes</li>
          <li>DCP controls extraction (finding the right section, precinct, dev type): 30&ndash;60 minutes</li>
          <li>SEPP applicability check: 15&ndash;20 minutes</li>
          <li>Spatial overlay check (flood, bushfire, heritage, riparian): 10&ndash;15 minutes</li>
          <li>Flood depth / bushfire BAL (if available and applicable): 20&ndash;30 minutes</li>
        </ul>
        <p className="text-slate-600 leading-relaxed">
          For{' '}
          <Link href="/for/planners" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            planning professionals doing 3&ndash;5 sites per week
          </Link>
          , this is 5&ndash;12 hours of data gathering — time that could be spent on analysis
          and advice.
        </p>
      </section>

      {/* ---- Automated analysis ---- */}
      <section id="automated-analysis" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Automated site analysis</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          PlotDetect automates the data-gathering phase of site analysis. Enter any NSW address
          and see zone permissibility, LEP controls, DCP provisions (for covered LGAs), SEPP
          applicability, flood depth, bushfire status, and spatial overlays — all on one screen
          with source citations.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The data comes from the NSW Planning Portal API, council flood studies, RFS bushfire
          layers, and extracted DCP provisions. Coverage: {COVERAGE_DISPLAY.totalNswCouncils} councils for zone and LEP controls,
          {' '}{COVERAGE_DISPLAY.dcpNumericCouncils} LGAs for DCP numeric controls (with full structured provisions for {COVERAGE_DISPLAY.dcpFullCouncils} councils), and
          {' '}{COVERAGE_DISPLAY.floodStudies} ingested council flood studies for modelled flood depth.
        </p>
        <p className="text-slate-600 leading-relaxed">
          This does not replace professional judgement — it replaces the manual data lookup. The
          interpretation, design decisions, and assessment are still done by the professional.
          The tool gives you the data faster so you can spend more time on the parts that require
          expertise.
        </p>
      </section>

      {/* CTA */}
      <div className="rounded-2xl bg-slate-50 border border-slate-200 p-6 text-center mt-10 mb-6">
        <p className="font-bold text-slate-900 mb-2">Run a site analysis for your property</p>
        <p className="text-sm text-slate-500 mb-4">
          Enter any NSW address. See planning controls, spatial overlays, and environmental
          data — with source citations.
        </p>
        <TrackedLink
          href="/assessment"
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          page="site-analysis-report-explained"
          cta="run_verify"
        >
          Open Verify <ArrowRight className="w-4 h-4" />
        </TrackedLink>
      </div>

      <BlogDisclaimer />
    </article>
  );
}
