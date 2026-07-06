import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'AASB S2: What Mandatory Climate Reporting Means for Property — PlotDetect',
  description:
    'AASB S2 mandatory climate disclosure is rolling out from 2025. Property investors, REITs, and super funds need property-level hazard data for their portfolios. Here is what you need to know.',
  keywords: [
    'AASB S2 property climate risk',
    'mandatory climate reporting property Australia',
    'climate disclosure property investors',
    'AASB S2 explained simply',
    'climate risk property portfolio',
    'AASB S2 REIT disclosure',
    'mandatory climate reporting Australia 2025',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual components                                                  */
/* ------------------------------------------------------------------ */

/** Visual 1 — Reporting timeline by entity group */
function ReportingTimeline() {
  const groups = [
    {
      group: 'Group 1',
      criteria: '$500M+ revenue, $1B+ assets, or 500+ employees',
      starts: 'FY from Jan 2025',
      firstReport: 'H1 2026',
      color: 'bg-red-500',
      borderColor: 'border-red-200',
      bgColor: 'bg-red-50/50',
      textColor: 'text-red-700',
      status: 'Reporting now',
    },
    {
      group: 'Group 2',
      criteria: '$200M+ revenue, $500M+ assets, or 250+ employees',
      starts: 'FY from Jul 2026',
      firstReport: 'H1 2028',
      color: 'bg-amber-500',
      borderColor: 'border-amber-200',
      bgColor: 'bg-amber-50/50',
      textColor: 'text-amber-700',
      status: 'Preparing now',
    },
    {
      group: 'Group 3',
      criteria: '$50M+ revenue, $25M+ assets, or 100+ employees',
      starts: 'FY from Jul 2027',
      firstReport: 'H1 2029',
      color: 'bg-teal-500',
      borderColor: 'border-teal-200',
      bgColor: 'bg-teal-50/50',
      textColor: 'text-teal-700',
      status: '12 months to prepare',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Who reports, and when
      </p>
      <div className="space-y-4">
        {groups.map((g) => (
          <div
            key={g.group}
            className={`rounded-xl border-2 ${g.borderColor} ${g.bgColor} p-5`}
          >
            <div className="flex items-center justify-between mb-2">
              <p className={`text-sm font-bold ${g.textColor}`}>{g.group}</p>
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full ${g.bgColor} ${g.textColor}`}
              >
                {g.status}
              </span>
            </div>
            <p className="text-sm text-slate-700 mb-2">{g.criteria}</p>
            <div className="flex gap-6 text-xs text-slate-500">
              <span>
                Starts: <strong className="text-slate-700">{g.starts}</strong>
              </span>
              <span>
                First report:{' '}
                <strong className="text-slate-700">{g.firstReport}</strong>
              </span>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4 italic">
        Also applies to NGER reporters and asset owners with $5B+ AUM.
        Entities must meet 2 of 3 criteria (revenue, assets, employees).
      </p>
    </div>
  );
}

/** Visual 2 — The 4 pillars with property-specific requirements */
function FourPillarsDiagram() {
  const pillars = [
    {
      name: 'Governance',
      desc: 'How does your board oversee climate risk?',
      property:
        'Board must demonstrate oversight of property portfolio exposure. Document who reviews hazard data and how often.',
      color: 'border-blue-200',
    },
    {
      name: 'Strategy',
      desc: 'How does climate risk affect your business model?',
      property:
        'Identify which properties are exposed to physical risks (flood, bushfire, heat, coastal erosion). Run scenario analysis under at least 1.5\u00b0C and >2\u00b0C pathways.',
      color: 'border-teal-200',
    },
    {
      name: 'Risk Management',
      desc: 'How do you identify and manage climate risks?',
      property:
        'Describe the process for assessing property-level hazard exposure. Include data sources, frequency of review, and integration with investment decisions.',
      color: 'border-violet-200',
    },
    {
      name: 'Metrics & Targets',
      desc: 'What do you measure and disclose?',
      property:
        'Report percentage of assets exposed by hazard type, geographic concentration, and projected financial impact under each scenario.',
      color: 'border-amber-200',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        AASB S2&apos;s four pillars &mdash; what they mean for property
      </p>
      <div className="grid sm:grid-cols-2 gap-4">
        {pillars.map((p) => (
          <div
            key={p.name}
            className={`rounded-xl border-2 ${p.color} bg-white p-5`}
          >
            <p className="text-sm font-bold text-slate-900 mb-1">{p.name}</p>
            <p className="text-xs text-slate-500 mb-3 italic">{p.desc}</p>
            <p className="text-sm text-slate-700">{p.property}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function AABS2MandatoryClimateReportingPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="AASB S2: what mandatory climate reporting means for property"
        description={`Who reports when, what the four pillars require for property portfolios, and where to source the climate risk data you'll need.`}
        slug="aasb-s2-mandatory-climate-reporting-property"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-700">
            Climate Risk
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          AASB S2: what mandatory climate reporting means for property
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          From January 2025, large Australian companies must publicly disclose
          their exposure to climate-related physical risks &mdash; including
          flood, bushfire, coastal erosion, and extreme heat &mdash; at the
          property level. By 2029, approximately 10,000 entities will be
          covered. If you hold property assets in a portfolio, fund, or REIT,
          this affects you.
        </p>
      </div>

      {/* Immediate value — the timeline */}
      <ReportingTimeline />

      {/* Body */}
      <div className="space-y-10">
        {/* What AASB S2 actually requires */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What AASB S2 actually requires, in plain English
          </h2>
          <p className="text-slate-700 leading-relaxed">
            AASB S2 is the Australian implementation of the global IFRS S2
            climate disclosure standard. It replaced the voluntary TCFD
            framework with a mandatory reporting obligation backed by law
            &mdash; the Treasury Laws Amendment Act 2024, passed in September
            2024.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The standard requires entities to disclose climate-related risks
            and opportunities across four pillars: governance, strategy, risk
            management, and metrics and targets. For property holders, the most
            consequential requirements are:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Scenario analysis</span> &mdash;
              model the impact of climate change on your property portfolio under
              at least two scenarios: one aligned with 1.5&deg;C warming, and
              one above 2&deg;C. This is not optional.
            </li>
            <li>
              <span className="font-medium">
                Physical risk identification
              </span>{' '}
              &mdash; identify which properties in your portfolio are exposed to
              physical hazards such as flooding, bushfire, coastal inundation,
              or extreme heat. This requires address-level hazard data.
            </li>
            <li>
              <span className="font-medium">Concentration disclosure</span>{' '}
              &mdash; report the geographic concentration of climate-exposed
              assets. A portfolio concentrated in Western Sydney flood zones or
              coastal erosion areas must say so.
            </li>
            <li>
              <span className="font-medium">
                Projected financial impact
              </span>{' '}
              &mdash; estimate the financial effect of physical climate risk on
              asset values, insurance costs, and operating expenses under each
              scenario.
            </li>
          </ul>
        </section>

        {/* Four pillars */}
        <FourPillarsDiagram />

        {/* Why property is uniquely exposed */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why property portfolios are uniquely exposed
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Property is the asset class where physical climate risk is most
            directly measurable. Unlike equities or bonds, where climate
            exposure is estimated through sectoral proxies, every property has a
            specific location. That location either floods or it does not. It is
            either in a bushfire zone or it is not. The data exists. The
            question is whether you have it.
          </p>
          <p className="text-slate-700 leading-relaxed">
            This makes AASB S2 compliance simultaneously harder and more
            straightforward for property holders. Harder, because you cannot
            rely on sector-average estimates &mdash; auditors will expect
            address-level evidence. More straightforward, because the data
            sources exist: government flood maps, bushfire prone land mapping,
            coastal hazard assessments, and climate projection datasets.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The challenge is assembling these sources at scale. A REIT with 200
            properties needs hazard data for 200 addresses, across multiple
            councils, each with different data formats and access methods. A
            super fund with mortgage exposure needs it for thousands.
          </p>
        </section>

        {/* What's different from voluntary ESG */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How this differs from voluntary ESG reporting
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Many property companies have published voluntary sustainability
            reports for years. AASB S2 is fundamentally different in three
            ways:
          </p>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                It is mandatory and audited
              </h3>
              <p className="text-slate-700 leading-relaxed">
                AASB S2 disclosures are part of the annual financial report,
                subject to assurance. From FY 2030, reasonable assurance
                (auditor-verified) will apply to all climate disclosures. If
                your data is wrong, ASIC can prosecute. Greenwashing or
                understatement carries the same legal risk as misleading
                financial statements.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                It requires scenario analysis, not just current state
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Voluntary reports typically describe current emissions. AASB S2
                requires forward-looking analysis: what happens to your
                portfolio under different warming scenarios? This requires
                climate projection data (such as NARCliM or CMIP6 outputs), not
                just historical observations.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                It requires property-level granularity
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The standard&apos;s Real Estate Appendix B prescribes
                industry-specific metrics including percentage of assets
                vulnerable to physical risks by hazard type and geographic
                concentration. Portfolio-level averages are not sufficient. You
                need to know which specific properties are exposed, and to what.
              </p>
            </div>
          </div>
        </section>

        {/* What data you need */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What data you need for compliance
          </h2>
          <p className="text-slate-700 leading-relaxed">
            At minimum, AASB S2 property disclosure requires:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Flood hazard data</span> &mdash;
              flood planning area status, 1% AEP extent, and ideally depth and
              frequency data for each property address.
            </li>
            <li>
              <span className="font-medium">Bushfire exposure</span> &mdash;
              bush fire prone land mapping, BAL (Bushfire Attack Level) where
              available.
            </li>
            <li>
              <span className="font-medium">Coastal hazard</span> &mdash;
              coastal erosion and inundation mapping for properties in coastal
              LGAs.
            </li>
            <li>
              <span className="font-medium">Extreme heat exposure</span>{' '}
              &mdash; urban heat island data, projected temperature increases
              under warming scenarios.
            </li>
            <li>
              <span className="font-medium">Climate projections</span> &mdash;
              future hazard exposure under at least a 1.5&deg;C and a &gt;2&deg;C
              scenario, with timeframes aligned to asset holding periods.
            </li>
            <li>
              <span className="font-medium">Planning overlays</span> &mdash;
              what statutory constraints (LEP, SEPP) apply to each property,
              including any development restrictions triggered by hazard
              classification.
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            For fund managers wanting deeper technical detail on data sources and
            integration, see our{' '}
            <Link
              href="/blog/aasb-s2-property-climate-data"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              AASB S2 property data guide
            </Link>
            .
          </p>
        </section>

        {/* APRA angle */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The APRA overlay: banks and insurers
          </h2>
          <p className="text-slate-700 leading-relaxed">
            AASB S2 applies to reporting entities directly. But{' '}
            <Link
              href="/blog/apra-cpg-229-property-assessment"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              APRA&apos;s CPG 229
            </Link>{' '}
            separately requires banks and insurers to assess climate risk
            across their mortgage and underwriting portfolios. APRA&apos;s March
            2026 Insurance Climate Vulnerability Assessment found that 1 in 4
            Australian households could be effectively uninsurable by 2050.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For property investors, the APRA requirements create a secondary
            pressure. Even if your entity is not directly subject to AASB S2
            (for example, a small REIT below Group 3 thresholds), your bank may
            ask for property-level climate data as part of refinancing. Your
            insurer is already pricing it. The data demand flows down.
          </p>
        </section>

        {/* What's coming */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Key dates ahead
          </h2>
          <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6">
            <div className="space-y-4">
              {[
                {
                  date: 'H1 2026',
                  event: 'Group 1 first reports due',
                  detail:
                    'Largest entities publish their first AASB S2 disclosures.',
                },
                {
                  date: 'Jul 2026',
                  event: 'Group 2 reporting begins',
                  detail:
                    'Approximately 3,000 additional entities start their first reporting period.',
                },
                {
                  date: 'Late 2026',
                  event: 'CC&NH SEPP expected',
                  detail:
                    'NSW Climate Change and Natural Hazards SEPP would prescribe NARCliM climate scenarios for all development assessment.',
                },
                {
                  date: 'Jul 2027',
                  event: 'Group 3 reporting begins',
                  detail:
                    'Approximately 6,000+ entities start. Total coverage reaches ~10,000 entities.',
                },
                {
                  date: 'FY 2030',
                  event: 'Reasonable assurance required',
                  detail:
                    'All climate disclosures must be auditor-verified to reasonable assurance standard. Data quality becomes legally consequential.',
                },
              ].map((item) => (
                <div
                  key={item.date}
                  className="flex gap-4 items-start border-b border-slate-100 last:border-0 pb-3 last:pb-0"
                >
                  <span className="flex-shrink-0 text-xs font-bold text-teal-700 bg-teal-50 px-2.5 py-1 rounded-full min-w-[80px] text-center">
                    {item.date}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {item.event}
                    </p>
                    <p className="text-sm text-slate-600">{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Frequently asked questions
          </h2>

          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does AASB S2 apply to private property investors?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                AASB S2 applies to entities meeting the size thresholds (revenue,
                assets, employees). A private investor holding properties in
                their own name is not directly captured. However, if you hold
                properties through an entity above the thresholds, or if your
                lender or insurer requires climate data, the requirements flow
                through to you indirectly.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                What scenarios do I need to model?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                AASB S2 requires at least two scenarios: one consistent with
                limiting warming to 1.5&deg;C, and one above 2&deg;C. Most
                entities use SSP1-2.6 and SSP3-7.0 (or the older RCP 2.6 and
                RCP 8.5). APRA additionally references NGFS scenarios for
                financial sector entities.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                What happens if I get the disclosure wrong?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Misleading climate disclosures carry the same legal
                consequences as misleading financial disclosures. ASIC has
                flagged greenwashing and climate misstatement as enforcement
                priorities. From FY 2030, reasonable assurance will apply,
                meaning auditors must verify the data, not just review it.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Where can I get property-level climate hazard data?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Government sources include NSW bushfire prone land maps, SES
                flood data, coastal hazard assessments, and NARCliM climate
                projections. PlotDetect&apos;s{' '}
                <Link
                  href="/climate-risk"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  climate risk assessment
                </Link>{' '}
                consolidates multiple government hazard layers at the
                property level.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Assess climate risk across your property portfolio
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s climate risk assessment checks five government-
              mapped hazard layers for any NSW address. See which physical risks
              overlap your properties &mdash; flood, bushfire, coastal erosion,
              heat, and subsidence.
            </p>
            <TrackedLink
              href="/climate-risk"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="aasb-s2-mandatory-climate-reporting-property"
              cta="climate_check"
            >
              Check climate risk
              <ArrowRight className="w-4 h-4" />
            </TrackedLink>
          </div>
        </section>

        {/* Back link */}
        <div className="pt-8 border-t border-slate-100">
          <Link
            href="/blog"
            className="text-sm text-slate-500 hover:text-teal-600 transition-colors"
          >
            &larr; Back to Insights
          </Link>
        </div>
      </div>
    </article>
  );
}
