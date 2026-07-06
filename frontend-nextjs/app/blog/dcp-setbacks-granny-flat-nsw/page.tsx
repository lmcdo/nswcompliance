import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Why Your Council\'s DCP Setbacks for Granny Flats Are Different — PlotDetect',
  description:
    'The SEPP Housing 2021 sets statewide granny flat standards, but council DCPs add their own setback, landscaping, and parking controls. The same lot can have different buildable areas depending on which council it falls under.',
  keywords: [
    'granny flat setback requirements NSW',
    'DCP secondary dwelling controls',
    'council setback rules granny flat',
    'rear setback granny flat NSW',
    'granny flat DCP controls',
    'secondary dwelling setbacks by council',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — Same lot, different buildable envelopes under 3 councils */
function BuildableEnvelopeDiagram() {
  const councils = [
    {
      name: 'SEPP minimum (statewide)',
      rear: '3 m',
      side: '0.9 m',
      separation: 'None specified',
      buildable: '~42 m\u00B2 footprint',
      color: 'border-teal-300 bg-teal-50',
      barWidth: 'w-4/5',
      barColor: 'bg-teal-500',
    },
    {
      name: 'Council A (topic-based DCP)',
      rear: '5 m',
      side: '1.5 m',
      separation: '3 m from main dwelling',
      buildable: '~30 m\u00B2 footprint',
      color: 'border-amber-300 bg-amber-50',
      barWidth: 'w-3/5',
      barColor: 'bg-amber-500',
    },
    {
      name: 'Council B (dev-type DCP)',
      rear: '6 m',
      side: '1.5 m',
      separation: '4 m from main dwelling',
      buildable: '~24 m\u00B2 footprint',
      color: 'border-red-300 bg-red-50',
      barWidth: 'w-2/5',
      barColor: 'bg-red-400',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
        Same 600 m&sup2; lot, different buildable footprints
      </p>
      <p className="text-xs text-slate-400 mb-5">
        Assumes 15 m wide &times; 40 m deep lot, existing dwelling 12 m from front boundary. Footprints are illustrative.
      </p>

      <div className="space-y-4">
        {councils.map((c) => (
          <div key={c.name} className={`rounded-xl border ${c.color} p-4`}>
            <p className="text-sm font-semibold text-slate-900 mb-2">{c.name}</p>
            <div className="grid grid-cols-3 gap-3 text-xs text-slate-600 mb-3">
              <div>
                <span className="font-medium text-slate-700">Rear:</span> {c.rear}
              </div>
              <div>
                <span className="font-medium text-slate-700">Side:</span> {c.side}
              </div>
              <div>
                <span className="font-medium text-slate-700">Separation:</span> {c.separation}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-slate-100 rounded-full h-4">
                <div className={`${c.barColor} h-4 rounded-full ${c.barWidth}`} />
              </div>
              <span className="text-xs font-medium text-slate-700 whitespace-nowrap">{c.buildable}</span>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-400 mt-4 italic">
        These are simplified examples to show how DCP setbacks reduce buildable
        area. Actual controls vary by council, precinct, and lot characteristics.
        Two-storey builds have different side setback requirements.
      </p>
    </div>
  );
}

/** Visual 2 — SEPP standards vs typical DCP additions */
function SEPPvsDCPTable() {
  const rows = [
    {
      control: 'Rear setback',
      sepp: '3 m',
      typical_dcp: '3\u20136 m',
      note: 'Some DCPs specify different values for single vs two storey',
    },
    {
      control: 'Side setback',
      sepp: '0.9 m (single storey)',
      typical_dcp: '0.9\u20131.5 m',
      note: 'Two-storey SEPP minimum is 1.5 m; some DCPs go higher',
    },
    {
      control: 'Separation from main dwelling',
      sepp: 'Not specified in SEPP',
      typical_dcp: '3\u20134 m',
      note: 'Common DCP addition; affects siting on narrow lots',
    },
    {
      control: 'Landscaped area',
      sepp: 'Minimum % (varies by lot size)',
      typical_dcp: '30\u201350% of site area',
      note: 'DCPs often specify deep soil zones, not just soft landscaping',
    },
    {
      control: 'Private open space',
      sepp: '24 m\u00B2 minimum',
      typical_dcp: '24\u201335 m\u00B2',
      note: 'Some DCPs require minimum dimensions (e.g. 4 m width)',
    },
    {
      control: 'Car parking',
      sepp: '1 additional space',
      typical_dcp: '1\u20132 spaces',
      note: 'Some DCPs prohibit tandem parking; others allow it',
    },
    {
      control: 'Maximum height',
      sepp: '8.5 m',
      typical_dcp: '7\u20138.5 m',
      note: 'Some DCPs set lower maximums in low-density character areas',
    },
    {
      control: 'Design / materials',
      sepp: 'Not specified',
      typical_dcp: 'Varies widely',
      note: 'Heritage areas may require specific materials, colours, roof pitch',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        SEPP Housing 2021 standards vs typical DCP additions
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-3 pr-3 font-semibold text-slate-900">Control</th>
              <th className="text-left py-3 pr-3 font-semibold text-teal-700">SEPP standard</th>
              <th className="text-left py-3 pr-3 font-semibold text-amber-700">Typical DCP range</th>
              <th className="text-left py-3 font-semibold text-slate-500">Notes</th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {rows.map((r) => (
              <tr key={r.control} className="border-b border-slate-100">
                <td className="py-2.5 pr-3 font-medium text-slate-900">{r.control}</td>
                <td className="py-2.5 pr-3">{r.sepp}</td>
                <td className="py-2.5 pr-3">{r.typical_dcp}</td>
                <td className="py-2.5 text-xs text-slate-500">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function DCPSetbacksGrannyFlatPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`Why your council's DCP setbacks for granny flats are different`}
        description="The SEPP gives one set of standards, but council DCPs often impose stricter controls. How to find your actual setback, landscaping, and parking rules."
        slug="dcp-setbacks-granny-flat-nsw"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-700">
            Planning Rules
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          Why your council&apos;s DCP setbacks for granny flats are different
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          The SEPP Housing 2021 sets statewide minimums for granny flat
          setbacks: 3 m rear, 0.9 m side. But your council&apos;s Development
          Control Plan can add stricter requirements &mdash; larger setbacks,
          separation distances, landscaping rules &mdash; that reduce what you
          can actually build. The same 600 m&sup2; lot can have a very different
          buildable envelope depending on which council it falls under.
        </p>
      </div>

      {/* Immediate value: buildable envelope comparison */}
      <BuildableEnvelopeDiagram />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">In this article</p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li><a href="#sepp-vs-dcp" className="hover:text-teal-600">What the SEPP says vs what DCPs add</a></li>
          <li><a href="#why-different" className="hover:text-teal-600">Why councils have different controls</a></li>
          <li><a href="#merged-councils" className="hover:text-teal-600">Merged councils: the 3-DCP problem</a></li>
          <li><a href="#sepp-dcp-conflict" className="hover:text-teal-600">What happens when SEPP and DCP conflict</a></li>
          <li><a href="#find-your-controls" className="hover:text-teal-600">How to find your specific DCP controls</a></li>
          <li><a href="#faq" className="hover:text-teal-600">Frequently asked questions</a></li>
        </ul>
      </nav>

      <div className="space-y-10">
        {/* SECTION 1: SEPP vs DCP */}
        <section id="sepp-vs-dcp" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What the SEPP says vs what DCPs add
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The SEPP Housing 2021 sets minimum standards for secondary dwellings
            approved as complying development. These are statewide &mdash; every
            council in NSW applies the same SEPP. But councils also adopt their
            own DCPs, which can impose additional controls for secondary
            dwellings assessed through the DA pathway.
          </p>

          <SEPPvsDCPTable />

          <p className="text-slate-700 leading-relaxed">
            The most impactful DCP addition is usually the{' '}
            <span className="font-medium">separation distance</span> between
            the main dwelling and the granny flat. The SEPP does not specify a
            separation distance. When a DCP requires 3 to 4 metres of
            separation, combined with the rear setback, the buildable area
            shrinks significantly &mdash; especially on lots under 700 m&sup2;.
          </p>
        </section>

        {/* SECTION 2: Why different */}
        <section id="why-different" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why councils have different controls
          </h2>
          <p className="text-slate-700 leading-relaxed">
            DCPs are adopted by individual councils to reflect local character,
            built form priorities, and environmental context. Councils with
            predominantly low-density, large-lot suburbs may set generous
            setbacks and landscaping requirements. Councils with tighter
            inner-city lots may accept smaller setbacks to make secondary
            dwellings feasible.
          </p>
          <p className="text-slate-700 leading-relaxed">
            There is no statewide standard for DCP content. Each council writes
            its own, and they are structured differently. Some councils organise
            DCP controls by development type (a dedicated &ldquo;secondary
            dwellings&rdquo; chapter). Others use topic-based organisation
            where setback controls apply universally to all residential
            development, including secondary dwellings.
          </p>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              Three DCP structural types in NSW
            </p>
            <div className="space-y-3 text-sm text-slate-700">
              <div>
                <span className="font-medium">Development-type organised:</span>{' '}
                Separate chapters per development category. Secondary dwellings
                get their own chapter with specific setback tables. Easy to
                find, but may not capture universal provisions that also apply.
              </div>
              <div>
                <span className="font-medium">Zone organised:</span>{' '}
                Controls grouped by zone or density area. Secondary dwelling
                standards sit within the low-density residential zone chapter,
                sometimes with cross-references to other sections.
              </div>
              <div>
                <span className="font-medium">Topic / universal:</span>{' '}
                All provisions apply to all development types. There is no
                dedicated secondary dwelling chapter &mdash; setback, height,
                and landscaping rules apply to granny flats the same way they
                apply to any other residential addition.
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 italic">
              The structural type determines how you find the controls that
              apply to your build. Topic-based DCPs are the hardest to navigate
              because the relevant provisions are scattered across multiple
              sections.
            </p>
          </div>
        </section>

        {/* SECTION 3: Merged councils */}
        <section id="merged-councils" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Merged councils: the 3-DCP problem
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The 2016 NSW council amalgamations created a particular challenge
            for DCP navigation. Merged councils often still operate under the
            former council&apos;s DCP for each geographic area. The controls
            that apply to your property depend on which former council area your
            lot falls within &mdash; not the current council name.
          </p>

          <div className="rounded-2xl border border-slate-200 p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">
              Example: Inner West Council
            </h3>
            <p className="text-slate-700 leading-relaxed mb-3">
              Inner West Council was formed from three former councils. Each
              former area still operates under its own DCP:
            </p>
            <div className="space-y-2">
              {[
                {
                  former: 'Former Ashfield',
                  dcp: 'Ashfield DCP 2007',
                  type: 'Development-type organised',
                  note: 'Dedicated secondary dwelling chapter with specific setback tables',
                },
                {
                  former: 'Former Leichhardt',
                  dcp: 'Leichhardt DCP 2013',
                  type: 'Topic / universal',
                  note: 'No dedicated secondary dwelling chapter; universal residential setbacks apply',
                },
                {
                  former: 'Former Marrickville',
                  dcp: 'Marrickville DCP 2011',
                  type: 'Zone organised',
                  note: 'Secondary dwelling controls within low-density residential section',
                },
              ].map((c) => (
                <div key={c.former} className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                  <p className="text-sm font-medium text-slate-900">{c.former}</p>
                  <p className="text-xs text-slate-500">
                    {c.dcp} &mdash; {c.type}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">{c.note}</p>
                </div>
              ))}
            </div>
            <p className="text-sm text-slate-700 mt-3">
              A property on one side of a street may be under a completely
              different DCP than the property across the road, even though both
              are in the same council area.
            </p>
          </div>
        </section>

        {/* SECTION 4: SEPP/DCP conflict */}
        <section id="sepp-dcp-conflict" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What happens when SEPP and DCP conflict
          </h2>
          <p className="text-slate-700 leading-relaxed">
            This is a common point of confusion. The answer depends on which
            approval pathway you use:
          </p>

          <div className="grid sm:grid-cols-2 gap-4 mt-2">
            <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
              <p className="text-sm font-bold text-teal-700 mb-2">
                CDC pathway (complying development)
              </p>
              <p className="text-sm text-slate-700">
                The SEPP standards apply. DCP controls are not relevant for
                CDC assessment. If your build meets every SEPP standard and
                your property is not excluded, the certifier issues the CDC
                based on the SEPP alone. This is one of the main advantages of
                the CDC pathway.
              </p>
            </div>
            <div className="rounded-xl border-2 border-amber-200 bg-white p-5">
              <p className="text-sm font-bold text-amber-700 mb-2">
                DA pathway (development application)
              </p>
              <p className="text-sm text-slate-700">
                Both the LEP and the DCP apply. Council assesses the application
                against their DCP controls, which may require larger setbacks,
                more landscaping, or additional parking. Council has discretion
                to vary DCP controls, but this is not guaranteed &mdash; the
                DCP is the starting point for assessment.
              </p>
            </div>
          </div>

          <p className="text-slate-700 leading-relaxed">
            In practice, this means homeowners whose properties qualify for
            CDC get a more predictable outcome: the statewide SEPP standards
            apply, and council DCP variations are irrelevant. Homeowners who
            must go through DA &mdash; because of heritage, flood, or other
            exclusions &mdash; face council-specific DCP requirements on top
            of the SEPP framework.
          </p>
        </section>

        {/* SECTION 5: Find your controls */}
        <section id="find-your-controls" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How to find your specific DCP controls
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Finding the secondary dwelling controls in your council&apos;s DCP
            is not always straightforward. Depending on the DCP structure, the
            relevant provisions may be in a dedicated chapter, scattered across
            topic-based sections, or embedded in zone-specific controls.
          </p>
          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. Check your council&apos;s website
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Most councils publish their DCP as a PDF or web document. Search
                for &ldquo;secondary dwelling&rdquo; or &ldquo;ancillary
                dwelling&rdquo; in the document. If your council was created
                from a merger, make sure you are reading the correct
                former-council DCP for your property&apos;s location.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Use PlotDetect&apos;s DCP browser
              </h3>
              <p className="text-slate-700 leading-relaxed">
                PlotDetect&apos;s{' '}
                <Link
                  href="/dcp-browse"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  DCP browser
                </Link>{' '}
                shows extracted DCP provisions by council, precinct, and
                development type. For supported councils, you can filter directly
                to secondary dwelling controls and see the specific setback,
                height, and landscaping requirements that apply.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Speak to a town planner or your certifier
              </h3>
              <p className="text-slate-700 leading-relaxed">
                For complex sites (heritage areas, merged council boundaries,
                precinct-specific controls), a planning consultant can confirm
                which DCP applies and how the controls interact with the SEPP
                standards. If you are going through the CDC pathway, your
                certifier will assess against the SEPP, but understanding the
                DCP context is still useful for design decisions.
              </p>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Frequently asked questions
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Do DCP setbacks apply if I use the CDC pathway?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                No. For complying development, only the SEPP Housing 2021
                standards apply. DCP controls are assessed under the DA pathway.
                This is a key advantage of CDC &mdash; the statewide SEPP
                standards are fixed and predictable, regardless of which council
                you are in.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                What is the minimum rear setback for a granny flat in NSW?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The SEPP Housing 2021 minimum rear setback for a secondary
                dwelling is 3 metres. Council DCPs may require larger rear
                setbacks (commonly 5 to 6 metres) for DAs, but cannot reduce
                below the SEPP minimum.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Why does my council require a separation distance the SEPP
                does not mention?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The SEPP does not specify a minimum separation distance between
                the main dwelling and the secondary dwelling. Councils include
                separation controls in their DCPs to address privacy, access,
                and fire safety. This is one of the most common DCP additions
                and can significantly reduce buildable area on smaller lots.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                I am in a merged council area. Which DCP applies?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The DCP of the former council area your property falls within.
                For example, Inner West Council operates under Ashfield DCP
                2007, Leichhardt DCP 2013, and Marrickville DCP 2011 depending
                on location. Check your property&apos;s address against the
                former council boundaries to determine which DCP applies.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can council vary DCP controls for my DA?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Yes. DCPs are guidelines, not legally binding standards (unlike
                LEPs and SEPPs). Council can approve a DA that does not fully
                comply with DCP controls if they are satisfied the
                development achieves the objectives of the control. However,
                this is discretionary and should not be assumed.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-violet-200 bg-violet-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Find your council&apos;s DCP controls
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s DCP browser shows extracted provisions by council,
              precinct, and development type. See the specific setback, height,
              and landscaping controls that apply to secondary dwellings in your
              area.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/dcp-browse"
                className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-500 transition-colors"
                page="dcp-setbacks-granny-flat-nsw"
                cta="browse_dcp"
              >
                Browse DCP controls
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/check"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-violet-700 text-sm font-medium rounded-xl border border-violet-200 hover:bg-violet-50 transition-colors"
              >
                Check your property
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
