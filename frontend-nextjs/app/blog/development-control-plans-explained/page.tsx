import type { Metadata } from 'next';
import Link from 'next/link';
import { COVERAGE_DISPLAY } from '@/lib/coverage';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Development Control Plans (DCPs) Explained: What They Are and Why They Matter — PlotDetect',
  description:
    'A DCP is the document that sets the fine-grained rules for development in each NSW council area — setbacks, parking, landscaping, building height planes, and more. This guide explains how DCPs work, their legal status, and how to read them.',
  keywords: [
    'development control plan nsw',
    'dcp nsw',
    'what is a dcp',
    'development control plan explained',
    'dcp vs lep',
    'how to read a dcp',
    'council development controls',
    'dcp setbacks parking landscaping',
    'nsw planning controls',
    'development control plan guide',
  ],
};

/* ------------------------------------------------------------------ */
/*  DCP hierarchy visual                                               */
/* ------------------------------------------------------------------ */

function PlanningHierarchy() {
  const layers = [
    {
      name: 'Environmental Planning & Assessment Act 1979',
      scope: 'State legislation',
      detail: 'The Act that gives all planning instruments their legal authority.',
      color: 'bg-slate-900 text-white',
    },
    {
      name: 'State Environmental Planning Policies (SEPPs)',
      scope: 'State-wide',
      detail: 'Override LEPs and DCPs where they apply. Examples: SEPP (Housing) 2021, SEPP (Transport & Infrastructure) 2021.',
      color: 'bg-slate-700 text-white',
    },
    {
      name: 'Local Environmental Plan (LEP)',
      scope: 'Per council area',
      detail: 'Statutory instrument. Sets zones, FSR, height limits, heritage listings, minimum lot sizes. Cannot be varied by a DA.',
      color: 'bg-teal-600 text-white',
    },
    {
      name: 'Development Control Plan (DCP)',
      scope: 'Per council area',
      detail: 'Non-statutory guidance. Sets setbacks, parking, landscaping, building design, tree preservation, and precinct-specific rules.',
      color: 'bg-teal-100 text-teal-900',
    },
  ];

  return (
    <div className="my-6 space-y-2">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
        NSW planning hierarchy (top overrides bottom)
      </p>
      {layers.map(({ name, scope, detail, color }, i) => (
        <div key={name} className={`rounded-xl p-4 ${color}`} style={{ marginLeft: `${i * 12}px` }}>
          <div className="flex items-baseline justify-between gap-2 mb-1">
            <p className="font-semibold text-sm">{name}</p>
            <span className="text-xs opacity-75 flex-shrink-0">{scope}</span>
          </div>
          <p className="text-xs opacity-80">{detail}</p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  What a DCP typically covers                                        */
/* ------------------------------------------------------------------ */

function DCPContentsGrid() {
  const sections = [
    {
      title: 'Setbacks',
      detail: 'Front, side, rear, and secondary street setbacks — often by zone, lot width, and precinct.',
    },
    {
      title: 'Car parking',
      detail: 'Number of spaces required by dwelling count, GFA, or land use. Bicycle parking minimums.',
    },
    {
      title: 'Landscaping',
      detail: 'Minimum landscaped area, deep soil zones, tree canopy targets, permeable surface ratios.',
    },
    {
      title: 'Site coverage',
      detail: 'Maximum percentage of the lot that can be covered by buildings (footprint).',
    },
    {
      title: 'Private open space',
      detail: 'Minimum area and dimensions for private outdoor space — ground floor and balconies.',
    },
    {
      title: 'Solar access',
      detail: 'Hours of sunlight that neighbouring properties must retain (typically 2–3 hours mid-winter).',
    },
    {
      title: 'Privacy',
      detail: 'Overlooking controls for windows, balconies, and roof terraces — screening and offset distances.',
    },
    {
      title: 'Building design',
      detail: 'Facade articulation, materials, roof pitch, garage dominance, fencing, and heritage character.',
    },
    {
      title: 'Stormwater',
      detail: 'On-site detention, water-sensitive urban design (WSUD), rainwater tanks.',
    },
    {
      title: 'Precinct controls',
      detail: 'Many DCPs have area-specific provisions that override the general controls for particular suburbs or character areas.',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-6">
      {sections.map(({ title, detail }) => (
        <div key={title} className="rounded-xl border border-slate-200 p-4">
          <p className="font-semibold text-slate-900 text-sm mb-1">{title}</p>
          <p className="text-sm text-slate-500">{detail}</p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function DCPExplainedPage() {
  return (
    <article className="max-w-2xl mx-auto px-6 py-12">
      <BlogPostingJsonLd
        title="Development Control Plans (DCPs) Explained: What They Are and Why They Matter"
        description="A DCP is the document that sets the fine-grained rules for development in each NSW council area — setbacks, parking, landscaping, building height planes, and more. This guide explains how DCPs work, their legal status, and how to read them."
        slug="development-control-plans-explained"
        date="2026-05-20"
      />
      {/* Reverse pyramid — answer first */}
      <h1 className="text-3xl font-bold text-slate-900 mb-4">
        Development Control Plans (DCPs) Explained
      </h1>

      <p className="text-lg text-slate-600 mb-6 leading-relaxed">
        A Development Control Plan (DCP) is the document that sets the fine-grained rules for
        development in each NSW council area. It covers setbacks, parking, landscaping,
        building design, and much more. Unlike the LEP, a DCP is not a statutory instrument —
        but non-compliance typically requires justification through the DA process.
      </p>

      <div className="rounded-xl bg-teal-50 border border-teal-200 p-4 text-sm text-teal-800 mb-8">
        <strong>Quick lookup:</strong>{' '}
        <Link href="/assessment" className="text-teal-700 underline underline-offset-2 hover:text-teal-600">
          Enter your address in Verify
        </Link>{' '}
        to see the DCP controls that apply to your property — numeric values with clause citations
        from your council&apos;s DCP.
      </div>

      {/* TOC */}
      <nav className="rounded-xl border border-slate-200 p-5 mb-10">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Contents</p>
        <ul className="space-y-1.5 text-sm">
          {[
            ['what-is-a-dcp', 'What is a DCP?'],
            ['hierarchy', 'Where DCPs sit in the planning hierarchy'],
            ['what-dcps-cover', 'What a DCP typically covers'],
            ['dcp-vs-lep', 'DCP vs LEP — what is the difference?'],
            ['legal-status', 'The legal status of DCP controls'],
            ['how-to-read', 'How to read a DCP'],
            ['precinct-controls', 'Precinct-specific controls'],
            ['common-mistakes', 'Common mistakes when reading DCPs'],
            ['structured-lookup', 'Looking up DCP controls without the PDF'],
          ].map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} className="text-teal-600 hover:text-teal-500">{label}</a>
            </li>
          ))}
        </ul>
      </nav>

      {/* ---- What is a DCP ---- */}
      <section id="what-is-a-dcp" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">What is a DCP?</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A Development Control Plan is a document prepared by a council under section 72 of the
          Environmental Planning and Assessment Act 1979 (EP&amp;A Act). It provides detailed
          planning and design guidelines for development within the council area.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Every council in NSW has at least one DCP. Larger councils may have multiple — sometimes
          inherited from former councils that were merged. For example, the Inner West Council
          inherited DCPs from the former Ashfield, Leichhardt, and Marrickville councils, which
          were later consolidated into a single Inner West DCP.
        </p>
        <p className="text-slate-600 leading-relaxed">
          DCPs are typically structured as large PDF documents organised into parts. A common
          structure is: Part A (general provisions), Part B (residential development), Part C
          (commercial and industrial), Part D (special areas or precincts). The numbering and
          structure varies significantly between councils.
        </p>
      </section>

      {/* ---- Hierarchy ---- */}
      <section id="hierarchy" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Where DCPs sit in the planning hierarchy
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          NSW planning operates in a hierarchy. The EP&amp;A Act sits at the top. Below that are
          SEPPs (state-level policies), then LEPs (local zoning and development standards), then
          DCPs (council-level design guidance).
        </p>
        <PlanningHierarchy />
        <p className="text-slate-600 leading-relaxed">
          The critical point: if a SEPP and a DCP conflict, the SEPP wins. If an LEP and a DCP
          conflict, the LEP wins. DCPs can add detail to LEP provisions, but they cannot
          contradict them. For example, a DCP cannot set a maximum height lower than the LEP
          height limit.
        </p>
      </section>

      {/* ---- What DCPs cover ---- */}
      <section id="what-dcps-cover" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">What a DCP typically covers</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          DCPs are wide-ranging. A single DCP can run to hundreds of pages covering every aspect
          of development design and assessment. The most commonly referenced controls are:
        </p>
        <DCPContentsGrid />
        <p className="text-sm text-slate-500 leading-relaxed">
          Not every DCP covers every topic above. Smaller rural councils may have short, simple
          DCPs. Inner-city councils with complex built environments tend to have very detailed
          provisions across multiple precincts.
        </p>
      </section>

      {/* ---- DCP vs LEP ---- */}
      <section id="dcp-vs-lep" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          DCP vs LEP — what is the difference?
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The LEP and DCP work together but serve different roles:
        </p>
        <div className="overflow-x-auto my-4">
          <table className="w-full text-sm border border-slate-200 rounded-xl overflow-hidden">
            <thead>
              <tr className="bg-slate-50 text-left">
                <th className="px-4 py-3 font-semibold text-slate-900">Aspect</th>
                <th className="px-4 py-3 font-semibold text-slate-900">LEP</th>
                <th className="px-4 py-3 font-semibold text-slate-900">DCP</th>
              </tr>
            </thead>
            <tbody className="text-slate-600">
              <tr className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">Legal status</td>
                <td className="px-4 py-3">Statutory — an Environmental Planning Instrument</td>
                <td className="px-4 py-3">Non-statutory — guidance the council must consider</td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">What it sets</td>
                <td className="px-4 py-3">Zones, FSR, height, lot size, heritage, land use permissibility</td>
                <td className="px-4 py-3">Setbacks, parking, landscaping, design, site coverage, precinct rules</td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">Can it be varied?</td>
                <td className="px-4 py-3">Only via Cl 4.6 variation request (a high bar)</td>
                <td className="px-4 py-3">Yes — if the variation achieves the control&apos;s objectives</td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">Where to find it</td>
                <td className="px-4 py-3">NSW Legislation website (legislation.nsw.gov.au)</td>
                <td className="px-4 py-3">Council website (usually as PDF documents)</td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">Applies to CDCs?</td>
                <td className="px-4 py-3">Yes</td>
                <td className="px-4 py-3">No — CDCs follow the Housing SEPP, not the DCP</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-slate-600 leading-relaxed">
          Read more about{' '}
          <Link href="/blog/cdc-vs-da-which-approval-pathway" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            the CDC vs DA pathways
          </Link>{' '}
          to understand when DCP controls apply and when they don&apos;t.
        </p>
      </section>

      {/* ---- Legal status ---- */}
      <section id="legal-status" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">The legal status of DCP controls</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Section 4.15(1)(a)(iii) of the EP&amp;A Act requires a consent authority to
          &ldquo;take into consideration&rdquo; a DCP when determining a DA. This is a lower
          threshold than &ldquo;comply with&rdquo;.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          In practice, this means a council can approve a DA that does not comply with a DCP
          control, provided the applicant demonstrates that the variation meets the objectives of
          the control. Conversely, a council can refuse a DA for DCP non-compliance if the
          variation does not meet the objectives.
        </p>
        <p className="text-slate-600 leading-relaxed">
          The Land and Environment Court has consistently held that DCP non-compliance is a
          relevant consideration but not an automatic ground for refusal. The weight given to
          DCP non-compliance depends on the degree of non-compliance, the nature of the control,
          and whether the development achieves the control&apos;s stated objectives.
        </p>
      </section>

      {/* ---- How to read a DCP ---- */}
      <section id="how-to-read" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">How to read a DCP</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          DCPs can be intimidating — some run to hundreds of pages. The key is knowing which
          sections apply to your specific situation:
        </p>
        <ol className="space-y-3 text-sm text-slate-600 list-decimal list-inside mb-4">
          <li>
            <strong>Start with the zone.</strong> Most DCPs have separate sections for low density
            residential, medium density, commercial, and industrial zones.
          </li>
          <li>
            <strong>Identify the development type.</strong> A dwelling house, dual occupancy, and
            residential flat building may each have different controls within the same zone section.
          </li>
          <li>
            <strong>Check for precinct-specific controls.</strong> Many DCPs have precinct or
            character area sections that override the general controls. If your property is in a
            named precinct, those controls take precedence.
          </li>
          <li>
            <strong>Read both objectives and controls.</strong> The objectives explain what the
            council is trying to achieve. The numeric controls (setbacks, parking rates) are the
            default way to meet those objectives — but the objectives are what matters for any
            variation request.
          </li>
          <li>
            <strong>Check the definitions.</strong> DCP definitions of terms like &ldquo;site
            coverage&rdquo;, &ldquo;landscaped area&rdquo;, or &ldquo;private open space&rdquo;
            may differ from the standard dictionary meaning or from other councils&apos; definitions.
          </li>
        </ol>
      </section>

      {/* ---- Precinct controls ---- */}
      <section id="precinct-controls" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Precinct-specific controls</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Many councils divide their area into precincts, character areas, or localities — each
          with distinct controls that override the general DCP provisions. Missing the precinct
          controls is one of the most common errors in site analysis.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          For example, a property in the Inner West LGA might fall within the &ldquo;Haberfield
          Heritage Conservation Area&rdquo; precinct, which has stricter setback, height, and
          design controls than the general R2 residential provisions.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Precinct boundaries are mapped in the DCP — typically as a map within the DCP PDF
          document or as a separate spatial layer on council&apos;s mapping system. The{' '}
          <Link href="/blog/nsw-planning-portal-gaps" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            NSW Planning Portal does not include precinct mapping
          </Link>
          , which is one of the gaps in the state-level planning data.
        </p>
      </section>

      {/* ---- Common mistakes ---- */}
      <section id="common-mistakes" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Common mistakes when reading DCPs
        </h2>
        <div className="space-y-3 my-4">
          {[
            {
              mistake: 'Using the wrong former council DCP',
              detail: 'Merged councils often maintain separate DCPs for each former area until consolidation. Check which former council area your property falls in.',
            },
            {
              mistake: 'Missing precinct-specific overrides',
              detail: 'The general residential controls may say "6 m front setback" but the precinct section may say "4.5 m". The precinct control takes precedence.',
            },
            {
              mistake: 'Applying DCP controls to a CDC application',
              detail: 'CDCs follow the Housing SEPP (or other applicable SEPP), not the DCP. If you are doing complying development, the DCP setbacks do not apply.',
            },
            {
              mistake: 'Confusing FSR with site coverage',
              detail: 'FSR (LEP) is total floor area divided by site area. Site coverage (DCP) is building footprint divided by site area. They are different numbers with different limits.',
            },
            {
              mistake: 'Ignoring the objectives',
              detail: 'If you need to vary a DCP control, the objectives are your justification. Read them carefully — they tell you what the council actually cares about.',
            },
          ].map(({ mistake, detail }) => (
            <div key={mistake} className="rounded-xl border border-slate-200 p-4">
              <p className="font-semibold text-slate-900 text-sm mb-1">{mistake}</p>
              <p className="text-sm text-slate-500">{detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---- Structured lookup ---- */}
      <section id="structured-lookup" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Looking up DCP controls without the PDF
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          DCPs are published as PDF documents — often hundreds of pages long, with controls
          embedded in prose paragraphs, tables, and appendices. Finding the specific numbers that
          apply to your property means reading through the right sections and cross-referencing
          with precinct maps.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          PlotDetect extracts DCP controls into structured, queryable fields with clause citations.
          For{' '}
          <Link href="/assessment" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            {COVERAGE_DISPLAY.dcpNumericCouncils} LGAs with numeric controls and {COVERAGE_DISPLAY.dcpFullCouncils} councils with full structured provisions
          </Link>
          , you can enter an address and see{' '}
          <Link href="/blog/setback-requirements-nsw" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            setbacks
          </Link>
          , parking rates, landscaping requirements, site coverage limits, and more — each linked
          to the source DCP clause.
        </p>
      </section>

      {/* CTA */}
      <div className="rounded-2xl bg-slate-50 border border-slate-200 p-6 text-center mt-10 mb-6">
        <p className="font-bold text-slate-900 mb-2">See DCP controls for your property</p>
        <p className="text-sm text-slate-500 mb-4">
          Enter any NSW address. Get setbacks, parking, landscaping, and site coverage with
          clause citations.
        </p>
        <TrackedLink
          href="/assessment"
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          page="development-control-plans-explained"
          cta="run_verify"
        >
          Open Verify <ArrowRight className="w-4 h-4" />
        </TrackedLink>
      </div>

      <BlogDisclaimer />
    </article>
  );
}
