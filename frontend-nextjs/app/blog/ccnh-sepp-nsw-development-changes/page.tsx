import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'What Is the CC&NH SEPP? How It Changes NSW Development — PlotDetect',
  description:
    'The draft Climate Change and Natural Hazards SEPP will consolidate flood, bushfire, coastal, and heat planning rules into one NSW instrument. Here is what it means for developers, planners, and conveyancers.',
  keywords: [
    'climate change natural hazards SEPP NSW',
    'NSW flood planning SEPP 2026',
    'CC&NH SEPP explained',
    'natural hazards development NSW',
    'SEPP resilience hazards replacement',
    'NARCliM planning assessment NSW',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual components                                                  */
/* ------------------------------------------------------------------ */

/** Visual 1 — Current fragmented system vs proposed consolidated SEPP */
function FragmentedVsConsolidatedDiagram() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Current system vs proposed CC&NH SEPP
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        {/* Current — fragmented */}
        <div className="rounded-xl border-2 border-red-200 bg-white p-5">
          <p className="text-sm font-bold text-red-700 mb-3">
            Current: fragmented across instruments
          </p>
          {[
            {
              label: 'Flood',
              source: 'LEP clauses 5.21/5.22 + council flood studies',
            },
            {
              label: 'Bushfire',
              source: 'Planning for Bush Fire Protection 2019 + BFPL maps',
            },
            {
              label: 'Coastal',
              source:
                'SEPP (Resilience & Hazards) 2021 Chapter 2 + Coastal SEMP',
            },
            {
              label: 'Heat',
              source: 'No statutory instrument (ad hoc council DCPs)',
            },
          ].map((item) => (
            <div
              key={item.label}
              className="flex items-start gap-3 py-2.5 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-100 flex items-center justify-center text-xs text-red-600 mt-0.5">
                !
              </span>
              <div>
                <p className="text-sm font-medium text-slate-900">
                  {item.label}
                </p>
                <p className="text-xs text-slate-500">{item.source}</p>
              </div>
            </div>
          ))}
          <p className="text-xs text-slate-400 mt-3 italic">
            Four hazards, four different regulatory pathways, inconsistent data
            sources.
          </p>
        </div>

        {/* Proposed — consolidated */}
        <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
          <p className="text-sm font-bold text-teal-700 mb-3">
            Proposed: one instrument, all hazards
          </p>
          {[
            {
              label: 'Flood',
              source: 'Centralised from LEPs, standardised assessment',
            },
            {
              label: 'Bushfire',
              source:
                'Landscape-level assessment with cumulative community impact',
            },
            {
              label: 'Coastal',
              source:
                'Updated coastal hazard provisions with NARCliM projections',
            },
            {
              label: 'Heat',
              source:
                'NEW: urban heat policy for development assessment',
            },
          ].map((item) => (
            <div
              key={item.label}
              className="flex items-start gap-3 py-2.5 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-teal-100 flex items-center justify-center text-xs text-teal-600 mt-0.5">
                &#10003;
              </span>
              <div>
                <p className="text-sm font-medium text-slate-900">
                  {item.label}
                </p>
                <p className="text-xs text-slate-500">{item.source}</p>
              </div>
            </div>
          ))}
          <p className="text-xs text-slate-400 mt-3 italic">
            Prescribed NARCliM 2.0 + ARR4 data sources. Statewide application.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Visual 2 — Key changes summary */
function KeyChangesSummary() {
  const changes = [
    {
      change: 'Prescribed climate scenarios',
      current: 'Councils choose their own data sources and scenarios',
      proposed:
        'NARCliM 2.0 and ARR4 prescribed for all assessments. Consistent statewide baseline.',
      impact: 'High',
      impactColor: 'text-red-600 bg-red-50',
    },
    {
      change: 'Flood provisions centralised',
      current:
        'LEP clauses 5.21/5.22 reference council-defined flood planning areas',
      proposed:
        'Flood provisions move from individual LEPs into the SEPP. One framework replaces 128 local variations.',
      impact: 'High',
      impactColor: 'text-red-600 bg-red-50',
    },
    {
      change: 'Urban heat policy',
      current: 'No statewide requirement. Some councils have DCP provisions.',
      proposed:
        'Development must consider and mitigate urban heat impact. First time heat is in a NSW planning instrument.',
      impact: 'Medium',
      impactColor: 'text-amber-600 bg-amber-50',
    },
    {
      change: 'Landscape-level bushfire assessment',
      current:
        'Site-specific BAL assessment under Planning for Bush Fire Protection',
      proposed:
        'Cumulative community-level impact considered. Assessments look beyond the individual lot.',
      impact: 'Medium',
      impactColor: 'text-amber-600 bg-amber-50',
    },
    {
      change: 'Post-disaster rebuilding',
      current: 'No specific planning pathway for post-disaster reconstruction',
      proposed:
        'Streamlined rebuilding pathways for properties damaged by natural hazards.',
      impact: 'Low-Medium',
      impactColor: 'text-teal-600 bg-teal-50',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        What changes and how much it matters
      </p>
      <div className="space-y-4">
        {changes.map((c) => (
          <div
            key={c.change}
            className="rounded-xl border border-slate-200 bg-white p-5"
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-bold text-slate-900">{c.change}</p>
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full ${c.impactColor}`}
              >
                {c.impact} impact
              </span>
            </div>
            <div className="grid sm:grid-cols-2 gap-3 mt-3">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Current
                </p>
                <p className="text-sm text-slate-600">{c.current}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Proposed
                </p>
                <p className="text-sm text-slate-700">{c.proposed}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function CCNHSEPPPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`What is the CC&NH SEPP? How it changes NSW development`}
        description="The draft Climate Change and Natural Hazards SEPP consolidates flood, bushfire, and coastal planning into one instrument. What it means for development."
        slug="ccnh-sepp-nsw-development-changes"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-700">
            Planning Reforms
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          What is the CC&NH SEPP? How it changes NSW development
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          The draft Climate Change and Natural Hazards SEPP will replace SEPP
          (Resilience & Hazards) 2021 and consolidate how NSW handles flood,
          bushfire, coastal, and heat risk in development assessment. It is the
          most significant structural change to hazard-based planning rules in
          a decade.
        </p>
      </div>

      {/* Immediate value — the diagram */}
      <FragmentedVsConsolidatedDiagram />

      {/* Body */}
      <div className="space-y-10">
        {/* What it is */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What the CC&NH SEPP is
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Climate Change and Natural Hazards SEPP is a draft State
            Environmental Planning Policy developed by the NSW Department of
            Planning, Housing and Infrastructure (DPHI). It was publicly
            exhibited between 17 February and 16 March 2026, with finalisation
            expected late 2026 or 2027.
          </p>
          <p className="text-slate-700 leading-relaxed">
            SEPPs are the highest-tier planning instruments in NSW, overriding
            local LEP and DCP provisions where there is inconsistency. The
            CC&NH SEPP would apply statewide to all local development, state
            significant development (SSD), and state significant
            infrastructure (SSI).
          </p>
          <p className="text-slate-700 leading-relaxed">
            It replaces SEPP (Resilience & Hazards) 2021, which primarily
            addressed coastal hazards. The new instrument expands scope to
            cover all four major natural hazard types in a single framework:
            flooding, bushfire, coastal erosion and inundation, and urban heat.
          </p>
        </section>

        {/* What it consolidates */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What it consolidates
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Currently, hazard assessment for NSW development is scattered
            across multiple instruments and data sources. The CC&NH SEPP
            proposes to bring these under one roof:
          </p>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Flood provisions
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Flood planning provisions currently sit within individual LEPs
                (clauses 5.21 and 5.22), established by the Flood Prone Land
                Package of 2021. Each council defines its own flood planning
                area based on its own flood studies, with no consistent
                statewide standard. The CC&NH SEPP would centralise these
                provisions and standardise the data and methodology used for
                flood assessment.
              </p>
              <p className="text-slate-700 leading-relaxed mt-2">
                This addresses a significant gap created by the{' '}
                <Link
                  href="/blog/section-10-7-flood-risk-nsw"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  2021 and 2023 changes to flood data in LEPs
                </Link>{' '}
                &mdash; where flood planning maps were removed from LEPs
                without a consistent replacement.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Coastal hazards
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Coastal erosion and inundation provisions from Chapter 2 of
                SEPP (Resilience & Hazards) 2021 carry into the new instrument,
                updated to reference NARCliM 2.0 climate projections rather
                than earlier models. Councils with certified Coastal Management
                Programs would continue to apply local provisions, but within
                the standardised SEPP framework.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Bushfire
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The SEPP introduces landscape-level bushfire assessment that
                considers cumulative community impact, not just site-specific
                BAL ratings. This is a significant shift from the current model
                where bushfire assessment is largely confined to the individual
                lot under Planning for Bush Fire Protection 2019. The RFS
                remains the referral authority for bushfire-affected
                development.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Urban heat (new)
              </h3>
              <p className="text-slate-700 leading-relaxed">
                For the first time, a NSW planning instrument would require
                development to consider and mitigate urban heat impact. No
                formal urban heat policy has existed at the SEPP level before.
                The exhibited draft proposes that larger developments assess
                their contribution to the urban heat island effect and
                incorporate mitigation measures such as canopy cover,
                permeable surfaces, and building material reflectivity.
              </p>
            </div>
          </div>
        </section>

        {/* Key changes */}
        <KeyChangesSummary />

        {/* What it means for existing properties */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What it means for existing properties
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The CC&NH SEPP primarily affects new development and modifications,
            not existing buildings. However, several indirect effects are
            significant for property owners:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Hazard reclassification</span>{' '}
              &mdash; properties not currently identified as flood or bushfire
              affected may be reclassified under standardised NARCliM-based
              mapping. This could affect{' '}
              <Link
                href="/blog/is-my-house-in-a-flood-zone-nsw"
                className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
              >
                flood zone status
              </Link>
              , s10.7 certificate notations, and insurance pricing.
            </li>
            <li>
              <span className="font-medium">
                Development potential changes
              </span>{' '}
              &mdash; properties in newly identified hazard areas may face
              additional development requirements or constraints, potentially
              reducing development potential.
            </li>
            <li>
              <span className="font-medium">Disclosure implications</span>{' '}
              &mdash; conveyancers and vendors may need to disclose new hazard
              classifications. Section 10.7 certificates would reflect the SEPP
              framework, potentially showing hazard information that was
              previously absent.
            </li>
            <li>
              <span className="font-medium">Insurance impact</span> &mdash;
              standardised hazard mapping provides insurers with more consistent
              data for pricing. Properties reclassified into higher-risk
              categories may see premium increases.
            </li>
          </ul>
        </section>

        {/* How it interacts with existing framework */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How it fits with existing planning rules
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The CC&NH SEPP does not replace LEPs or DCPs entirely. It operates
            as a layer above them for hazard-related matters:
          </p>

          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-6">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="flex-shrink-0 text-xs font-bold bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full">
                  SEPP
                </span>
                <span className="text-sm text-slate-700">
                  CC&NH SEPP sets the statewide hazard assessment framework.
                  Overrides LEP provisions where inconsistent.
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="flex-shrink-0 text-xs font-bold bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full">
                  LEP
                </span>
                <span className="text-sm text-slate-700">
                  Local Environmental Plans retain zoning, building height, and
                  FSR. Flood clauses 5.21/5.22 would be superseded by SEPP
                  provisions.
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="flex-shrink-0 text-xs font-bold bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full">
                  DCP
                </span>
                <span className="text-sm text-slate-700">
                  Council DCPs retain local controls for setbacks, parking,
                  character. Hazard-specific DCP provisions may need to align
                  with the SEPP framework.
                </span>
              </div>
            </div>
          </div>

          <p className="text-slate-700 leading-relaxed">
            The Flood Prone Land Package of 2021, which introduced LEP clauses
            5.21 and 5.22, would be effectively superseded. The SEPP creates a
            single source of truth for hazard-based development controls rather
            than relying on 128 separate council implementations.
          </p>
        </section>

        {/* Timeline */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Timeline and status
          </h2>
          <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6">
            <div className="space-y-4">
              {[
                {
                  date: 'Feb-Mar 2026',
                  event: 'Public exhibition',
                  detail:
                    'Draft CC&NH SEPP exhibited for public comment from 17 February to 16 March 2026.',
                  status: 'Complete',
                  statusColor: 'bg-teal-50 text-teal-700',
                },
                {
                  date: 'Mid 2026',
                  event: 'Response to submissions',
                  detail:
                    'DPHI reviews submissions and prepares final instrument. May include amendments based on feedback.',
                  status: 'In progress',
                  statusColor: 'bg-amber-50 text-amber-700',
                },
                {
                  date: 'Late 2026',
                  event: 'Expected commencement',
                  detail:
                    'Earliest expected date for the SEPP to commence. Could extend into 2027 depending on the scale of amendments.',
                  status: 'Projected',
                  statusColor: 'bg-slate-100 text-slate-600',
                },
              ].map((item) => (
                <div
                  key={item.date}
                  className="flex gap-4 items-start border-b border-slate-100 last:border-0 pb-3 last:pb-0"
                >
                  <span className="flex-shrink-0 text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full min-w-[110px] text-center">
                    {item.date}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-slate-900">
                        {item.event}
                      </p>
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${item.statusColor}`}
                      >
                        {item.status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600">{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* What to prepare */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What to prepare for now
          </h2>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                For developers
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Projects currently in pre-DA should consider the incoming
                framework. If your site is near a flood planning area, coastal
                hazard zone, or bushfire prone land, the CC&NH SEPP may impose
                additional assessment requirements. Engaging hazard consultants
                now using NARCliM 2.0 data positions you ahead of the
                transition.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                For planners
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Familiarise yourself with NARCliM 2.0 and ARR4 data sources.
                The SEPP will prescribe these as the standard climate data
                inputs for development assessment. Council planners will need to
                assess DAs against a statewide hazard framework rather than
                local flood studies alone.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                For conveyancers
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The SEPP will change what appears on s10.7 planning certificates
                for hazard-affected properties. Properties that currently show
                no flood or hazard notation may receive new notations under the
                standardised framework. Building this into due diligence
                processes early is prudent. PlotDetect&apos;s{' '}
                <Link
                  href="/reports/flood"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  flood risk reports
                </Link>{' '}
                already incorporate multiple data sources beyond the s10.7
                certificate.
              </p>
            </div>
          </div>
        </section>

        {/* Connection to AASB S2 */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Connection to mandatory climate reporting
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The CC&NH SEPP creates demand for climate hazard data from the
            planning side. Simultaneously,{' '}
            <Link
              href="/blog/aasb-s2-mandatory-climate-reporting-property"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              AASB S2 mandatory climate reporting
            </Link>{' '}
            creates demand from the financial side. Both require property-level
            hazard data. Both reference forward-looking climate scenarios. The
            convergence means that the same underlying data &mdash; flood maps,
            bushfire layers, coastal hazard assessments, climate projections
            &mdash; is needed by planning consultants, developers,
            conveyancers, fund managers, banks, and insurers.
          </p>
        </section>

        {/* FAQ */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Frequently asked questions
          </h2>

          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Is the CC&NH SEPP already in force?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                No. The SEPP was publicly exhibited in February-March 2026 and
                is still being finalised. It is expected to commence late 2026
                or 2027. Current development assessment continues under the
                existing framework.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Will it affect existing development approvals?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                No. Existing development consents remain valid. The SEPP
                applies to new DAs and modification applications lodged after
                commencement. Transition provisions are expected for
                applications already in the pipeline.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                What happens to council flood studies?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Council flood studies are not replaced. The SEPP provides a
                standardised framework for how flood risk is assessed in
                development applications, including prescribed climate scenarios
                and data sources. Councils retain their flood data but apply it
                within the SEPP framework.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does this apply to complying development?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The exhibited SEPP applies to local development, SSD, and SSI.
                Complying development under the Codes SEPP has its own hazard
                provisions. The interaction between the CC&NH SEPP and
                complying development pathways will depend on the final
                instrument.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check hazard exposure for any NSW property
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s climate risk assessment checks five
              government-mapped hazard layers &mdash; flood, bushfire, coastal,
              heat, and subsidence &mdash; for any NSW address. See what the
              CC&NH SEPP framework will assess.
            </p>
            <TrackedLink
              href="/climate-risk"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-500 transition-colors"
              page="ccnh-sepp-nsw-development-changes"
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
