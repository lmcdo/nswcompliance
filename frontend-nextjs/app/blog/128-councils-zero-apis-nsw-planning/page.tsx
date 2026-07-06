import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    '128 Councils, Zero APIs: Why NSW Planning Compliance Is So Hard — PlotDetect',
  description:
    'NSW has 128 councils, each with its own Development Control Plan published in different formats with no standardised data or APIs. The Planning Portal covers LEP and SEPP but not DCP. Here is why planning compliance automation is so difficult.',
  keywords: [
    'NSW planning system digital',
    'DCP automation NSW',
    'planning compliance technology NSW',
    'council development controls digital',
    'NSW planning portal limitations',
    'development control plan NSW',
    'planning data fragmentation',
    'NSW ePlanning',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Fragmentation diagram */
function FragmentationDiagram() {
  const layers = [
    {
      name: 'LEP (Local Environmental Plan)',
      source: 'NSW Planning Portal',
      format: 'Standardised (Standard Instrument)',
      digital: true,
      desc: 'Zoning, lot sizes, height limits, FSR',
    },
    {
      name: 'SEPP (State Environmental Planning Policies)',
      source: 'NSW Planning Portal',
      format: 'Standardised (state-level)',
      digital: true,
      desc: 'Housing Code, exempt/complying, transport corridors',
    },
    {
      name: 'DCP (Development Control Plan)',
      source: '128 individual councils',
      format: 'No standard — varies by council',
      digital: false,
      desc: 'Setbacks, landscaping, parking, design, precinct controls',
    },
    {
      name: 'Section 7.11/7.12 contributions',
      source: 'Individual councils',
      format: 'PDF schedules, some with calculators',
      digital: false,
      desc: 'Infrastructure contributions, rates, thresholds',
    },
    {
      name: 'Council-specific overlays',
      source: 'Council GIS (where available)',
      format: 'ArcGIS, MapInfo, or none',
      digital: false,
      desc: 'Heritage, flood, DCP precinct maps, character areas',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        NSW planning data — what is digital vs what is not
      </p>
      <div className="space-y-0">
        {layers.map((layer) => (
          <div
            key={layer.name}
            className={`flex items-start gap-4 py-4 border-b border-slate-100 last:border-0 ${
              layer.digital ? '' : 'bg-red-50/30 -mx-3 px-3 rounded-lg'
            }`}
          >
            <div
              className={`flex-shrink-0 mt-1 w-3 h-3 rounded-full ${
                layer.digital ? 'bg-teal-500' : 'bg-red-400'
              }`}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-900">
                {layer.name}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Source: {layer.source} &mdash; Format: {layer.format}
              </p>
              <p className="text-sm text-slate-600 mt-1">{layer.desc}</p>
            </div>
            <span
              className={`flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
                layer.digital
                  ? 'bg-teal-100 text-teal-700'
                  : 'bg-red-100 text-red-700'
              }`}
            >
              {layer.digital ? 'API available' : 'No API'}
            </span>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4 italic">
        The two layers with APIs (LEP and SEPP) cover zoning and state-level
        rules. The three layers without APIs (DCP, contributions, overlays)
        contain the site-specific controls that drive most compliance decisions.
      </p>
    </div>
  );
}

/** Visual 2 — What the Planning Portal covers vs doesn't */
function PortalCoverage() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        NSW Planning Portal — what it covers vs what it does not
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
          <p className="text-sm font-bold text-teal-700 mb-3">
            Available via Planning Portal
          </p>
          {[
            'Zoning (land use zone for any lot)',
            'LEP development standards (height, FSR, lot size)',
            'SEPP provisions (housing code, exempt/complying)',
            'Heritage listings (state and local)',
            'Acid sulfate soils classification',
            'Section 10.7 certificate data',
          ].map((item) => (
            <div
              key={item}
              className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-teal-100 flex items-center justify-center text-xs text-teal-600">
                &#10003;
              </span>
              <span className="text-sm text-slate-700">{item}</span>
            </div>
          ))}
        </div>
        <div className="rounded-xl border-2 border-red-200 bg-white p-5">
          <p className="text-sm font-bold text-red-700 mb-3">
            Not available — must check each council
          </p>
          {[
            'DCP setbacks (front, side, rear)',
            'DCP landscaping and tree canopy requirements',
            'DCP parking rates and bicycle storage',
            'DCP building design controls (materials, colours)',
            'Precinct-specific DCP rules',
            'DCP FSR bonuses and incentive provisions',
            'Section 7.11/7.12 contribution rates',
            'Council-specific flood mapping',
          ].map((item) => (
            <div
              key={item}
              className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-100 flex items-center justify-center text-xs text-red-600">
                &times;
              </span>
              <span className="text-sm text-slate-700">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Visual 3 — DCP format variety across councils */
function DCPFormatVariety() {
  const formats = [
    {
      format: 'Monolithic PDF',
      example: 'Single 400-page document, no internal hyperlinking',
      councils: 'Common in regional councils',
    },
    {
      format: 'Sectioned PDFs',
      example: 'Separate PDFs per section (residential, commercial, precinct)',
      councils: 'Inner West, Canterbury-Bankstown',
    },
    {
      format: 'Web-based with PDF maps',
      example: 'HTML provisions with linked PDF precinct maps',
      councils: 'City of Sydney, North Sydney',
    },
    {
      format: 'Interactive GIS + PDF',
      example: 'Council GIS links spatial precincts to DCP provisions',
      councils: 'Northern Beaches, Wollongong',
    },
    {
      format: 'Multiple concurrent DCPs',
      example: 'Pre-merger councils each retain separate DCPs',
      councils: 'Inner West (3 former DCPs), Cumberland (2)',
    },
  ];

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        How councils publish DCPs — five different approaches
      </p>
      <div className="space-y-0">
        {formats.map((f) => (
          <div
            key={f.format}
            className="py-3 border-b border-amber-100 last:border-0"
          >
            <p className="text-sm font-semibold text-slate-900">{f.format}</p>
            <p className="text-sm text-slate-600 mt-0.5">{f.example}</p>
            <p className="text-xs text-slate-400 mt-0.5">
              Examples: {f.councils}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function CouncilsZeroApisPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="128 councils, zero APIs: why NSW planning compliance is so hard"
        description={`Every council has different DCP formats, no standardised data, and no APIs. What the Planning Portal covers, what it doesn't, and what digital planning could look like.`}
        slug="128-councils-zero-apis-nsw-planning"
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
          128 councils, zero APIs: why NSW planning compliance is so hard
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          The NSW Planning Portal gives you zoning and LEP standards for any
          address in the state. But the controls that drive most compliance
          decisions &mdash; DCP setbacks, parking rates, landscaping
          requirements, precinct-specific rules &mdash; are published by 128
          individual councils in formats ranging from 400-page PDFs to
          unstandardised web pages. There are no APIs. There is no common
          schema. And every council updates on its own schedule.
        </p>
      </div>

      {/* Immediate value — fragmentation diagram */}
      <FragmentationDiagram />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#portal-does-well" className="hover:text-teal-600">
              What the Planning Portal does well
            </a>
          </li>
          <li>
            <a href="#portal-gap" className="hover:text-teal-600">
              What it does not cover
            </a>
          </li>
          <li>
            <a href="#dcp-formats" className="hover:text-teal-600">
              How councils publish DCPs
            </a>
          </li>
          <li>
            <a href="#cost-of-manual" className="hover:text-teal-600">
              The cost of manual compliance checking
            </a>
          </li>
          <li>
            <a href="#progress" className="hover:text-teal-600">
              Progress so far
            </a>
          </li>
          <li>
            <a href="#what-digital-could-look-like" className="hover:text-teal-600">
              What digital planning could look like
            </a>
          </li>
        </ul>
      </nav>

      {/* Body */}
      <div className="space-y-10">
        {/* ========== WHAT PORTAL DOES WELL ========== */}
        <section id="portal-does-well" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What the Planning Portal does well
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Credit where it is due. The NSW Planning Portal is one of the better
            state-level planning systems in Australia. It provides:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Zoning data</span> for every lot in
              the state, with permitted and prohibited uses derived from the
              Standard Instrument LEP
            </li>
            <li>
              <span className="font-medium">LEP development standards</span>{' '}
              &mdash; maximum building height, floor space ratio, minimum lot
              size &mdash; as mapped spatial layers
            </li>
            <li>
              <span className="font-medium">SEPP provisions</span> including the
              Housing Code, exempt and complying development criteria, and
              transport corridor overlays
            </li>
            <li>
              <span className="font-medium">
                Heritage and environmental overlays
              </span>{' '}
              &mdash; state and local heritage listings, acid sulfate soils,
              some biodiversity layers
            </li>
            <li>
              <span className="font-medium">Section 10.7 data</span> for
              planning certificates, referenced by conveyancers across the state
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            The Portal&apos;s spatial API (layerintersect) allows programmatic
            queries against these layers. For LEP-level compliance questions
            &mdash; &ldquo;what zone is this lot in?&rdquo; or &ldquo;what is the
            maximum height?&rdquo; &mdash; the data is comprehensive, current,
            and machine-readable. This is genuinely good infrastructure.
          </p>
        </section>

        {/* ========== WHAT IT DOESN'T COVER ========== */}
        <section id="portal-gap" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What it does not cover
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The gap is the Development Control Plan. Every council in NSW has a
            DCP (some have multiple), and the DCP is where most of the
            site-specific development controls live. The Planning Portal does
            not include DCP data. There is no state-level API, no common schema,
            and no requirement for councils to publish DCPs in any particular
            format.
          </p>

          <PortalCoverage />

          <p className="text-slate-700 leading-relaxed">
            The practical consequence: a planner checking compliance for a
            residential development needs the Planning Portal for zoning and LEP
            standards, then must separately find, download, and manually read the
            relevant council&apos;s DCP to determine setbacks, parking, landscaping,
            and design requirements. If the site falls within a DCP precinct,
            they need to identify the correct precinct &mdash; often from a PDF
            map &mdash; and find the precinct-specific controls, which may
            override the general DCP provisions.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For professionals who work across multiple councils, this is a daily
            frustration. For property buyers trying to understand what they can
            build, it is often an impenetrable barrier. PlotDetect&apos;s{' '}
            <Link
              href="/dcp-browse"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              DCP browser
            </Link>{' '}
            and{' '}
            <Link
              href="/assessment"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              compliance assessment
            </Link>{' '}
            are built specifically to bridge this gap.
          </p>
        </section>

        {/* ========== HOW COUNCILS PUBLISH DCPs ========== */}
        <section id="dcp-formats" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How councils publish DCPs
          </h2>
          <p className="text-slate-700 leading-relaxed">
            There is no standard format for a DCP. Each council chooses how to
            structure, publish, and update its development controls. The result
            is a landscape that resists automation at every turn.
          </p>

          <DCPFormatVariety />

          <p className="text-slate-700 leading-relaxed">
            The merger problem compounds this. When NSW councils were
            amalgamated in 2016, many merged councils retained their pre-merger
            DCPs. Inner West Council, for example, operates under three former
            DCPs (Ashfield, Leichhardt, Marrickville) with different structures,
            numbering systems, and precinct definitions. A single property
            lookup requires knowing which former council area the address falls
            in before you can identify the correct DCP.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Updates add another dimension. Councils amend DCPs periodically, but
            there is no central notification system. A setback rule that was
            correct six months ago may have been amended without any
            programmatic way to detect the change.
          </p>
        </section>

        {/* ========== COST OF MANUAL CHECKING ========== */}
        <section id="cost-of-manual" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The cost of manual compliance checking
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Manual DCP compliance checking is slow, expensive, and error-prone.
            The costs are borne across the entire development pipeline:
          </p>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Time
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A planner checking DCP compliance for a medium-density
                residential project typically spends 4-8 hours on the DCP alone
                &mdash; finding the document, identifying the correct precinct,
                cross-referencing general and precinct-specific controls, and
                documenting the applicable standards. Across hundreds of DAs per
                council per year, this adds up to thousands of professional
                hours spent reading PDFs.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Errors
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Manual processes produce inconsistent results. Two planners
                reading the same DCP for the same site may identify different
                applicable controls &mdash; especially where precinct boundaries
                are ambiguous or where general provisions interact with
                precinct-specific overrides. These errors surface as assessment
                delays, requests for additional information, or incorrect
                compliance advice.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Inconsistency across councils
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A developer working across three councils must learn three
                different DCP structures, three different precinct systems, and
                three different sets of terminology for equivalent controls. Side
                setbacks might be called &ldquo;side boundary setbacks,&rdquo;
                &ldquo;side setbacks,&rdquo; &ldquo;lateral setbacks,&rdquo; or
                &ldquo;building separation&rdquo; depending on the council.
                There is no common vocabulary.
              </p>
            </div>
          </div>
        </section>

        {/* ========== PROGRESS SO FAR ========== */}
        <section id="progress" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Progress so far
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The situation is not entirely static. Two developments are moving in
            the right direction:
          </p>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                ePlanning spatial layers
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The NSW ePlanning program has published ArcGIS MapServer
                endpoints for various planning spatial layers, including some
                development control overlays. These are publicly accessible
                without authentication. Coverage is growing, but the data is
                primarily spatial (boundaries, zones) rather than the textual
                development controls within those boundaries.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Council GIS portals
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Some councils have invested in interactive GIS portals that link
                spatial precincts to DCP provisions. Northern Beaches and
                Wollongong offer relatively good spatial interfaces. But these
                are council-by-council investments with no common standard, and
                many councils &mdash; particularly in regional NSW &mdash; have
                no GIS portal at all.
              </p>
            </div>
          </div>

          <p className="text-slate-700 leading-relaxed">
            The gap between what is digitally available and what is needed for
            automated compliance remains large. LEP and SEPP data is well
            served. DCP data &mdash; the layer that contains the controls most
            relevant to actual building design &mdash; remains overwhelmingly
            analogue.
          </p>
        </section>

        {/* ========== WHAT DIGITAL PLANNING COULD LOOK LIKE ========== */}
        <section id="what-digital-could-look-like" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What digital planning could look like
          </h2>
          <p className="text-slate-700 leading-relaxed">
            A fully digital planning system would mean a planner, developer, or
            property buyer could enter an address and receive every applicable
            development control &mdash; LEP, SEPP, and DCP &mdash; in a
            structured, machine-readable format. The controls would be
            spatially linked to the correct precinct, current as of the latest
            amendment, and consistent in terminology across councils.
          </p>
          <p className="text-slate-700 leading-relaxed">
            This is not a technology problem. The technology to extract, structure,
            and serve this data exists today. The barriers are institutional:
            128 councils with independent publishing practices, no mandate for
            digital-first DCP publication, and no common data standard for
            development controls.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Until the institutional barriers are resolved, the gap between
            state-level digital planning infrastructure and local-level
            development controls will persist. Bridging that gap &mdash; making
            DCP controls as accessible as LEP zoning data &mdash; is one of the
            most consequential challenges in NSW planning technology.
          </p>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              See what applies to your address
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect brings LEP, SEPP, and DCP controls together for NSW
              addresses. Browse DCP provisions by council, or run a compliance
              check for a specific site.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/check"
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-500 transition-colors"
                page="128-councils-zero-apis-nsw-planning"
                cta="check_address"
              >
                Check an address
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/dcp-browse"
                className="inline-flex items-center gap-2 px-6 py-3 border border-slate-200 text-slate-700 text-sm font-medium rounded-xl hover:border-teal-300 hover:text-teal-700 transition-colors"
              >
                Browse DCP provisions
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
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
