import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'What the NSW Planning Portal Doesn\'t Tell You — PlotDetect',
  description:
    'The NSW Planning Portal shows your zone and LEP maps. It does not show DCP setbacks, flood depth, parking rates, or development potential. Here are the 7 gaps and where to find the missing data.',
  keywords: [
    'nsw planning portal',
    'planning portal nsw',
    'nsw planning portal limitations',
    'planning portal property search',
    'what does the planning portal show',
    'nsw property zoning check',
    'planning portal alternative',
    'planning portal missing data',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual: what the portal shows vs doesn't                          */
/* ------------------------------------------------------------------ */

function PortalGapsTable() {
  const rows = [
    { item: 'Zone code and name', portal: true, detail: 'e.g. R2 Low Density Residential' },
    { item: 'LEP height limit', portal: true, detail: 'From the Height of Buildings Map' },
    { item: 'LEP floor space ratio', portal: true, detail: 'From the FSR Map' },
    { item: 'LEP minimum lot size', portal: true, detail: 'From the Lot Size Map' },
    { item: 'Heritage item listing', portal: true, detail: 'If the property is individually listed' },
    { item: 'Permitted / prohibited land uses', portal: false, detail: 'Zone table exists in the LEP text, not returned by the portal property search' },
    { item: 'DCP front setback', portal: false, detail: 'Only in the council\'s DCP document (PDF)' },
    { item: 'DCP side and rear setbacks', portal: false, detail: 'Only in the council\'s DCP document (PDF)' },
    { item: 'DCP parking rates', portal: false, detail: 'Only in the council\'s DCP document (PDF)' },
    { item: 'DCP landscaping requirements', portal: false, detail: 'Only in the council\'s DCP document (PDF)' },
    { item: 'Flood depth at return periods', portal: false, detail: 'Council flood studies — most councils don\'t publish this online' },
    { item: 'Bushfire Attack Level (BAL)', portal: false, detail: 'RFS BFPL map shows prone/not prone, not the BAL band' },
    { item: 'Heritage conservation area status', portal: false, detail: 'The Heritage Map shows items but not always HCA boundaries clearly' },
    { item: 'SEPP-specific requirements', portal: false, detail: 'Which SEPPs apply and what they require for this address' },
    { item: 'Development potential assessment', portal: false, detail: 'What you can actually build given all controls combined' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6 overflow-x-auto">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
        NSW Planning Portal property search — what it returns
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-2 pr-4 font-semibold text-slate-900">Data point</th>
            <th className="text-center py-2 px-3 font-semibold text-slate-900 w-24">On portal?</th>
            <th className="text-left py-2 pl-4 font-semibold text-slate-900">Detail</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ item, portal, detail }) => (
            <tr key={item} className="border-b border-slate-100 last:border-0">
              <td className="py-2.5 pr-4 text-slate-700">{item}</td>
              <td className="py-2.5 px-3 text-center">
                {portal ? (
                  <span className="text-green-600 font-medium">Yes</span>
                ) : (
                  <span className="text-red-500 font-medium">No</span>
                )}
              </td>
              <td className="py-2.5 pl-4 text-slate-500">{detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function PlanningPortalGapsPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`What the NSW Planning Portal Doesn't Tell You`}
        description="The NSW Planning Portal shows your zone and LEP maps. It does not show DCP setbacks, flood depth, parking rates, or development potential. Here are the 7 gaps and where to find the missing data."
        slug="nsw-planning-portal-gaps"
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
          What the NSW Planning Portal doesn&apos;t tell you
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Over 33,000 people search for the NSW Planning Portal every month. Most find their zone,
          see some maps, and leave more confused than when they arrived. That&apos;s because the portal
          was built to publish LEP maps — not to answer the question you actually have: &quot;what can
          I do with my property?&quot;
        </p>
      </div>

      <PortalGapsTable />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">In this article</p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li><a href="#what-it-shows" className="hover:text-teal-600">What the Planning Portal actually shows</a></li>
          <li><a href="#gap-1-dcp" className="hover:text-teal-600">Gap 1: No DCP controls (setbacks, parking, landscaping)</a></li>
          <li><a href="#gap-2-flood" className="hover:text-teal-600">Gap 2: Flood zone yes/no — but no depth</a></li>
          <li><a href="#gap-3-permissibility" className="hover:text-teal-600">Gap 3: No permitted use table for your zone</a></li>
          <li><a href="#gap-4-sepp" className="hover:text-teal-600">Gap 4: No SEPP-specific requirements</a></li>
          <li><a href="#gap-5-heritage" className="hover:text-teal-600">Gap 5: Heritage conservation areas are unclear</a></li>
          <li><a href="#gap-6-bushfire" className="hover:text-teal-600">Gap 6: Bushfire prone but no BAL estimate</a></li>
          <li><a href="#gap-7-potential" className="hover:text-teal-600">Gap 7: No development potential assessment</a></li>
          <li><a href="#where-to-find" className="hover:text-teal-600">Where to find the missing data</a></li>
        </ul>
      </nav>

      {/* Body */}
      <div className="space-y-10">

        <section id="what-it-shows" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What the Planning Portal actually shows</h2>
          <p className="text-slate-700 leading-relaxed">
            The NSW Planning Portal (planningportal.nsw.gov.au) is operated by the Department of Planning,
            Housing and Infrastructure. Its property search returns data from the Local Environmental Plan
            (LEP) for your council area. This includes:
          </p>
          <ul className="space-y-2 text-slate-700">
            <li className="flex gap-2"><span className="text-green-600 font-bold">&#10003;</span> Zone code and name (e.g. R2 Low Density Residential)</li>
            <li className="flex gap-2"><span className="text-green-600 font-bold">&#10003;</span> Height of buildings limit (metres)</li>
            <li className="flex gap-2"><span className="text-green-600 font-bold">&#10003;</span> Floor space ratio (FSR)</li>
            <li className="flex gap-2"><span className="text-green-600 font-bold">&#10003;</span> Minimum lot size</li>
            <li className="flex gap-2"><span className="text-green-600 font-bold">&#10003;</span> Heritage item listings</li>
            <li className="flex gap-2"><span className="text-green-600 font-bold">&#10003;</span> Lot boundary and area</li>
            <li className="flex gap-2"><span className="text-green-600 font-bold">&#10003;</span> Acid sulfate soil class</li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            This is useful — but it&apos;s only the LEP layer. The LEP sets the broad parameters. The
            detailed controls that determine what you can actually build come from the Development
            Control Plan (DCP), State Environmental Planning Policies (SEPPs), and council-held data
            like flood studies. None of that is on the portal.
          </p>
        </section>

        <section id="gap-1-dcp" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Gap 1: No DCP controls</h2>
          <p className="text-slate-700 leading-relaxed">
            The{' '}
            <Link href="/blog/development-control-plans-explained" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              Development Control Plan
            </Link>{' '}
            is where the real detail lives. Front setback, side setback, rear setback, parking rates, landscaping
            area, site coverage, building separation, private open space — all of these come from the DCP,
            and none are available on the Planning Portal.
          </p>
          <p className="text-slate-700 leading-relaxed">
            There are 128 councils in NSW, each with its own DCP published as a PDF on the council&apos;s
            website. Some councils have multiple DCPs inherited from pre-merger council areas. There is no
            standardised format and no API. Finding the right setback for your address means identifying
            which DCP applies, which precinct you&apos;re in, and which section covers your development type.
          </p>
          <p className="text-slate-700 leading-relaxed">
            This matters because setback requirements directly determine the{' '}
            <Link href="/blog/building-height-limits-nsw" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              building envelope
            </Link>
            {' '}— the three-dimensional space you can build within. A 6-metre front setback vs a 4-metre
            setback on a 15-metre-deep lot is the difference between a viable extension and a rejected DA.
          </p>
        </section>

        <section id="gap-2-flood" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Gap 2: Flood zone yes/no — but no depth</h2>
          <p className="text-slate-700 leading-relaxed">
            The Planning Portal can tell you whether a property is on &quot;flood prone land.&quot; It cannot tell
            you how deep the water gets, at what return period, or from which flood study the data was
            sourced. For a property buyer or developer, the difference between 10cm of ankle-deep water in
            a 1-in-100-year event and 1.5m of ground-floor flooding is everything — for insurance,
            for building design, and for the ability to get a{' '}
            <Link href="/blog/cdc-vs-da-which-approval-pathway" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              Complying Development Certificate
            </Link>.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Flood depth data comes from council flood studies — engineering models that estimate water
            behaviour at different rainfall intensities. Most councils commission these studies but don&apos;t
            publish the results in a format the public can access. Some make them available on request.
            Others require a formal application.
          </p>
        </section>

        <section id="gap-3-permissibility" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Gap 3: No permitted use table</h2>
          <p className="text-slate-700 leading-relaxed">
            You find out your property is zoned &quot;R2 Low Density Residential.&quot; The portal does not
            then tell you what R2 permits. Can you build a dual occupancy? A boarding house? A secondary
            dwelling? The zone permissibility table is in the LEP text (the legal instrument), but the
            portal&apos;s property search doesn&apos;t surface it. You have to navigate to the LEP, find the
            land use table, and cross-reference your zone — a process that assumes you know how to read
            planning legislation.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The{' '}
            <Link href="/tools/zoning-check" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              free zoning check tool
            </Link>{' '}
            on PlotDetect shows the zone, the key numbers, and the permitted/prohibited land uses in plain
            English — because that&apos;s what people actually want to know when they search for their zone.
          </p>
        </section>

        <section id="gap-4-sepp" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Gap 4: No SEPP-specific requirements</h2>
          <p className="text-slate-700 leading-relaxed">
            State Environmental Planning Policies (SEPPs) override or supplement local controls.
            The Housing SEPP determines whether you can build a secondary dwelling as complying
            development. The Exempt and Complying Development Codes SEPP determines whether your
            extension, deck, or garage can skip the DA process. The Resilience and Hazards SEPP
            governs development on flood-prone and bushfire-prone land.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The portal doesn&apos;t tell you which SEPPs apply to your address or what they require.
            This is a significant gap because SEPP provisions often determine the approval pathway
            — whether you need a full Development Application or can use the faster{' '}
            <Link href="/blog/cdc-vs-da-which-approval-pathway" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              CDC pathway
            </Link>.
          </p>
        </section>

        <section id="gap-5-heritage" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Gap 5: Heritage conservation areas are unclear</h2>
          <p className="text-slate-700 leading-relaxed">
            The portal&apos;s Heritage Map shows heritage items — individually listed properties. But many
            properties sit within a{' '}
            <Link href="/blog/heritage-conservation-area-granny-flat-nsw" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              heritage conservation area
            </Link>{' '}
            (HCA) without being individually listed. Being in an HCA blocks the CDC pathway for most
            development types, including granny flats. The distinction between &quot;heritage item&quot; and
            &quot;in a heritage conservation area&quot; is critical, and the portal doesn&apos;t always make it clear.
          </p>
        </section>

        <section id="gap-6-bushfire" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Gap 6: Bushfire prone but no BAL estimate</h2>
          <p className="text-slate-700 leading-relaxed">
            The RFS Bush Fire Prone Land map shows whether your property is in a bushfire-prone area and
            the vegetation category. It does not show the{' '}
            <Link href="/blog/bushfire-attack-level-bal-property-buyers" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              Bushfire Attack Level (BAL)
            </Link>
            {' '}— the rating that determines building construction requirements and insurance premiums.
            BAL ranges from BAL-LOW (no special requirements) to BAL-FZ (Flame Zone — extreme construction
            requirements). A formal BAL assessment requires a site visit, but a screening estimate based
            on vegetation category and distance to bushland is possible from spatial data.
          </p>
        </section>

        <section id="gap-7-potential" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Gap 7: No development potential assessment</h2>
          <p className="text-slate-700 leading-relaxed">
            This is the biggest gap. After checking all the controls — zone, FSR, height, setbacks, overlays,
            SEPPs, heritage, flood, bushfire — the question most people actually want answered is: &quot;what
            can I build here?&quot; The portal gives you raw data points. It does not combine them into
            an assessment of what is and isn&apos;t possible on your specific lot.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Answering that question requires understanding how all the controls interact — how the
            setback envelope intersects with the height limit, how the FSR constrains the gross floor
            area, whether the lot is large enough for{' '}
            <Link href="/tools/subdivision-check" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              subdivision
            </Link>, and which approval pathway applies. This is what planning consultants do — and
            what the portal was never designed to automate.
          </p>
        </section>

        <section id="where-to-find" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Where to find the missing data</h2>
          <p className="text-slate-700 leading-relaxed">
            The data exists — it&apos;s just scattered across different sources:
          </p>
          <div className="rounded-xl border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left py-3 px-4 font-semibold text-slate-900">Data</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-900">Source</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['DCP setbacks, parking, landscaping', 'Council DCP document (PDF on council website)'],
                  ['Permitted land uses', 'LEP Land Use Table (legislation.nsw.gov.au)'],
                  ['Flood depth at return periods', 'Council flood studies (request from council)'],
                  ['Bushfire Attack Level', 'Formal BAL assessment (accredited assessor)'],
                  ['Heritage conservation area', 'Council heritage maps or s10.7 certificate'],
                  ['SEPP applicability', 'Read the relevant SEPP (legislation.nsw.gov.au)'],
                  ['Development potential', 'Planning consultant or site analysis'],
                ].map(([data, source]) => (
                  <tr key={data} className="border-t border-slate-100">
                    <td className="py-2.5 px-4 text-slate-700">{data}</td>
                    <td className="py-2.5 px-4 text-slate-500">{source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-slate-700 leading-relaxed">
            Or you can check most of these in one place. The{' '}
            <Link href="/assessment" className="text-teal-600 hover:text-teal-700 underline underline-offset-2">
              PlotDetect Verify tool
            </Link>{' '}
            pulls zone, LEP controls, DCP numeric controls, SEPP requirements, spatial overlays,
            flood data, and bushfire status for any NSW address — from the same government data
            sources, structured and cross-referenced.
          </p>
        </section>
      </div>

      <BlogDisclaimer />

      {/* CTA */}
      <section className="mt-4 space-y-6">
        <div className="rounded-2xl border border-violet-200 bg-violet-50/30 p-8">
          <h2 className="text-xl font-bold text-slate-900 mb-3">Check your property now</h2>
          <p className="text-slate-600 mb-4 leading-relaxed">
            See what the portal misses — zone, LEP controls, DCP setbacks, SEPP requirements, flood
            risk, and spatial overlays for any NSW address. Free, instant.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/tools/zoning-check"
              className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-500 transition-colors"
            >
              Free zoning check
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/assessment"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white text-violet-700 text-sm font-medium rounded-xl border border-violet-200 hover:bg-violet-50 transition-colors"
            >
              Full planning controls
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      <div className="pt-8 border-t border-slate-100">
        <Link href="/blog" className="text-sm text-slate-500 hover:text-teal-600 transition-colors">
          &larr; Back to Insights
        </Link>
      </div>
    </article>
  );
}
