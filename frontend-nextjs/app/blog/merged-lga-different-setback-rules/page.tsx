import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Why Different Setback Rules in the Same Merged LGA — PlotDetect',
  description:
    'NSW council amalgamations in 2016 created LGAs where neighbouring properties follow completely different setback rules. Here is why, and how to find which DCP applies to your site.',
  keywords: [
    'council setback rules NSW',
    'DCP development controls explained',
    'merged council different rules NSW',
    'inner west council DCP',
    'council amalgamation planning rules',
    'canterbury bankstown DCP',
    'cumberland council DCP',
    'rear setback NSW',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual components                                                  */
/* ------------------------------------------------------------------ */

/** Visual 1 — Merged LGA with different DCP zones */
function MergedLGADiagram() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        One LGA, three sets of rules
      </p>
      <div className="relative rounded-xl border-2 border-violet-200 bg-white p-6 overflow-hidden">
        <p className="text-sm font-bold text-violet-700 mb-4 text-center">
          Inner West Council (merged 2016)
        </p>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border-2 border-dashed border-rose-300 bg-rose-50/50 p-4 text-center">
            <p className="text-xs font-bold text-rose-700 mb-1">
              Former Ashfield
            </p>
            <p className="text-xs text-slate-600">Ashfield DCP 2007</p>
            <p className="text-xs text-slate-500 mt-2">Rear setback: 8m</p>
            <p className="text-xs text-slate-500">Side setback: 0.9m</p>
          </div>
          <div className="rounded-lg border-2 border-dashed border-amber-300 bg-amber-50/50 p-4 text-center">
            <p className="text-xs font-bold text-amber-700 mb-1">
              Former Leichhardt
            </p>
            <p className="text-xs text-slate-600">Leichhardt DCP 2013</p>
            <p className="text-xs text-slate-500 mt-2">Rear setback: 6m</p>
            <p className="text-xs text-slate-500">Side setback: 1.2m</p>
          </div>
          <div className="rounded-lg border-2 border-dashed border-teal-300 bg-teal-50/50 p-4 text-center">
            <p className="text-xs font-bold text-teal-700 mb-1">
              Former Marrickville
            </p>
            <p className="text-xs text-slate-600">Marrickville DCP 2011</p>
            <p className="text-xs text-slate-500 mt-2">Rear setback: 5m</p>
            <p className="text-xs text-slate-500">Side setback: 0.9m</p>
          </div>
        </div>
        <div className="mt-4 text-center">
          <p className="text-xs text-slate-400 italic">
            Three former councils. Three DCPs. One merged LGA.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Visual 2 — Comparison table of setback differences across merged councils */
function SetbackComparisonTable() {
  const rows = [
    {
      lga: 'Inner West',
      former: 'Ashfield / Leichhardt / Marrickville',
      rear: '5m–8m',
      side: '0.9m–1.2m',
      landscape: '30%–50%',
    },
    {
      lga: 'Canterbury-Bankstown',
      former: 'Canterbury / Bankstown',
      rear: '3m–6m',
      side: '0.9m–1.5m',
      landscape: '40%–50%',
    },
    {
      lga: 'Cumberland',
      former: 'Auburn / Holroyd / Parramatta (part)',
      rear: '3m–6m',
      side: '0.9m–1.2m',
      landscape: '30%–40%',
    },
    {
      lga: 'Georges River',
      former: 'Kogarah / Hurstville',
      rear: '6m–8m',
      side: '0.9m–1.5m',
      landscape: '40%–55%',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        How setback rules vary within merged LGAs
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                Merged LGA
              </th>
              <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                Former councils
              </th>
              <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                Rear setback range
              </th>
              <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                Side setback range
              </th>
              <th className="text-left py-3 font-semibold text-slate-900">
                Landscaped area
              </th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {rows.map((r) => (
              <tr key={r.lga} className="border-b border-slate-100">
                <td className="py-3 pr-4 font-medium">{r.lga}</td>
                <td className="py-3 pr-4">{r.former}</td>
                <td className="py-3 pr-4">{r.rear}</td>
                <td className="py-3 pr-4">{r.side}</td>
                <td className="py-3">{r.landscape}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400 mt-3 italic">
        Ranges reflect variation between former council DCPs within the same
        merged LGA. Actual requirements depend on zone, lot size, and building
        type. Verify current provisions with council.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function MergedLGASetbackRulesPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Why different setback rules in the same merged LGA"
        description="NSW council amalgamations left merged LGAs with multiple inherited DCPs. Your neighbour in the same council area can have completely different rules."
        slug="merged-lga-different-setback-rules"
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
          Why different setback rules apply in the same merged LGA
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          You and your neighbour are in the same council area. You share a
          fence. But your rear setback is 8 metres, and theirs is 5 metres.
          This is not an error &mdash; it is a consequence of NSW council
          amalgamations and the way development control plans were inherited,
          not unified.
        </p>
      </div>

      {/* Immediate value — the diagram */}
      <MergedLGADiagram />

      {/* Body */}
      <div className="space-y-10">
        {/* What happened */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What happened in 2016
          </h2>
          <p className="text-slate-700 leading-relaxed">
            In 2016, the NSW Government merged 43 councils into 20 new entities.
            Each former council had its own Development Control Plan &mdash; a
            detailed document specifying setbacks, building heights, landscaping
            requirements, parking rates, and dozens of other site-specific
            controls. When councils merged, these DCPs were not consolidated.
            They were inherited.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The merged council now administers multiple DCPs simultaneously.
            Which one applies to your property depends entirely on which former
            council area your lot falls within &mdash; not on any unified
            standard.
          </p>
          <p className="text-slate-700 leading-relaxed">
            This was intended to be temporary. Ten years later, most merged
            councils still operate under their inherited DCPs. Harmonisation is
            a multi-year process that requires extensive community consultation,
            technical studies, and political will. Some councils have begun the
            process. Most have not finished it.
          </p>
        </section>

        {/* Why it matters */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why this matters for your build
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The practical impact goes well beyond setbacks. Different former
            council DCPs within the same LGA can specify different requirements
            for:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Rear setbacks</span> &mdash; the
              distance between your building and the rear boundary. This
              directly affects how much of your lot is buildable.
            </li>
            <li>
              <span className="font-medium">Side setbacks</span> &mdash;
              clearance to side boundaries. Affects building width, light, and
              privacy.
            </li>
            <li>
              <span className="font-medium">Landscaped area</span> &mdash;
              minimum percentage of the lot that must remain soft landscaping.
              Ranges from 30% to 55% across different former council areas.
            </li>
            <li>
              <span className="font-medium">Car parking rates</span> &mdash;
              different minimums for the same dwelling type depending on which
              DCP applies.
            </li>
            <li>
              <span className="font-medium">
                Granny flat and secondary dwelling controls
              </span>{' '}
              &mdash; floor area limits, setback requirements, and private open
              space differ between former councils. See our guide on{' '}
              <Link
                href="/blog/can-i-build-a-granny-flat-nsw"
                className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
              >
                granny flat rules in NSW
              </Link>
              .
            </li>
            <li>
              <span className="font-medium">Heritage and character controls</span>{' '}
              &mdash; different precincts, different character statements,
              different DCP heritage provisions.
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            If you are comparing properties across a merged LGA, the controls
            applicable to each lot may be fundamentally different &mdash; even
            if the LEP zoning is identical.
          </p>
        </section>

        {/* The big examples */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Where this plays out in practice
          </h2>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Inner West Council
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Formed from the merger of Ashfield, Leichhardt, and Marrickville
                councils. Three distinct DCPs remain in force. The Ashfield DCP
                2007 applies to the northern part of the LGA; the Leichhardt DCP
                2013 to the central area; and the Marrickville DCP 2011 to the
                south. Rear setbacks, landscaped area requirements, and
                character precinct controls all differ between the three.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Canterbury-Bankstown Council
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Formed from Canterbury and Bankstown. The two former council
                areas had substantially different approaches to medium-density
                housing controls, parking rates, and landscaping. A townhouse
                project in the former Canterbury area operates under different
                setback and open space provisions than an equivalent project in
                the former Bankstown area, despite both being in the same LGA
                under the same LEP.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Cumberland Council
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Formed from Auburn, Holroyd, and part of Parramatta. Three sets
                of inherited DCP controls apply across the LGA. Parking rates,
                setbacks, and building envelope controls differ between the
                former council areas. Properties near the boundaries between
                former councils can be subject to noticeably different controls
                from properties just one street away.
              </p>
            </div>
          </div>
        </section>

        {/* Setback comparison */}
        <SetbackComparisonTable />

        {/* How to find your DCP */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How to find which rules apply to your property
          </h2>
          <p className="text-slate-700 leading-relaxed">
            There are three ways to determine which former council area your
            property is in, and therefore which DCP applies:
          </p>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. Check PlotDetect&apos;s DCP browser
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Enter your address on PlotDetect&apos;s{' '}
                <Link
                  href="/dcp-browse"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  DCP browser
                </Link>{' '}
                to see which DCP provisions apply to your specific lot. The
                system identifies the relevant former council area and shows the
                applicable controls for setbacks, landscaping, parking, and
                other site-specific requirements.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Check with council directly
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The merged council&apos;s planning department can confirm which
                DCP applies to a specific address. Most councils have a duty
                planner available by phone or in person. Ask specifically which
                former council DCP applies, not just the LGA-wide DCP number.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Check the council website
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Most merged councils publish maps showing former council
                boundaries. Cross-reference your address against these maps to
                determine which former council area you are in, then locate the
                relevant DCP on the council website.
              </p>
            </div>
          </div>
        </section>

        {/* When will this change */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            When will councils harmonise their DCPs?
          </h2>
          <p className="text-slate-700 leading-relaxed">
            There is no state-mandated deadline for DCP harmonisation. Each
            merged council is proceeding at its own pace. Inner West Council
            began work on a comprehensive DCP in 2020, with parts still being
            exhibited in 2026. Canterbury-Bankstown adopted a consolidated DCP
            in 2023 but retained area-specific variations for some controls.
            Cumberland Council is progressing a new comprehensive DCP.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Full harmonisation is likely to take several more years across most
            merged LGAs. In the meantime, checking the applicable former council
            DCP remains necessary for any development proposal.
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
                Can I vary a DCP setback?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                DCPs are not legally binding in the same way LEPs are. Consent
                authorities can approve variations to DCP controls if justified.
                However, departure from DCP setbacks requires demonstrating that
                the variation achieves the objectives of the control, and
                councils vary in their willingness to approve variations.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Why does the LEP apply uniformly but the DCP does not?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                When councils merged, the NSW Government created new LEPs that
                apply across the entire merged LGA. LEPs are state
                environmental planning instruments gazetted under the EP&A Act.
                DCPs are council-adopted documents that sit below the LEP. There
                was no equivalent state process to force DCP unification, so the
                old DCPs persisted.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does this affect complying development?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Complying development under the Codes SEPP has its own setback
                standards that override local DCPs. If your project qualifies as
                complying development, the Codes SEPP setbacks apply regardless
                of which former council area you are in. But if your project
                requires a DA, the local DCP setbacks are relevant.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-violet-200 bg-violet-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Find the DCP controls that apply to your property
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s compliance check identifies your former council
              area and shows the specific DCP setbacks, landscaping, and parking
              controls for your lot. Enter any NSW address.
            </p>
            <TrackedLink
              href="/check"
              page="merged-lga-different-setback-rules"
              cta="check_address"
              className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-500 transition-colors"
            >
              Check your property
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
