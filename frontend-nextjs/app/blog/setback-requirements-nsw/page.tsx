import type { Metadata } from 'next';
import Link from 'next/link';
import { COVERAGE_DISPLAY } from '@/lib/coverage';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Setback Requirements in NSW: Front, Side & Rear Setbacks Explained — PlotDetect',
  description:
    'NSW setback requirements vary by council, zone, lot width, and development type. This guide covers how front, side, and rear setbacks work under DCPs, what triggers different rules, and where to find the controls for your property.',
  keywords: [
    'setback requirements nsw',
    'front setback nsw',
    'side setback nsw',
    'rear setback nsw',
    'building setback requirements',
    'dcp setback controls',
    'setback from boundary nsw',
    'setback rules residential nsw',
    'building envelope nsw',
    'setback distance from boundary',
  ],
};

/* ------------------------------------------------------------------ */
/*  Setback types table                                                */
/* ------------------------------------------------------------------ */

function SetbackTypesTable() {
  const types = [
    {
      type: 'Front setback',
      typical: '4.5–6.5 m',
      source: 'DCP — varies by zone, street hierarchy, and prevailing setback',
      notes: 'Often the most prescriptive. Many councils require averaging with neighbours.',
    },
    {
      type: 'Side setback',
      typical: '0.9–1.5 m',
      source: 'DCP — varies by wall height, lot width, and building length',
      notes: 'BCA also imposes fire separation requirements that may override DCP.',
    },
    {
      type: 'Rear setback',
      typical: '6–8 m',
      source: 'DCP — varies by zone, storey count, and whether rear boundary adjoins a lane',
      notes: 'Some councils allow reduced rear setbacks for laneway lots.',
    },
    {
      type: 'Secondary street setback',
      typical: '3–4 m',
      source: 'DCP — applies to corner lots',
      notes: 'Measured from the secondary street boundary.',
    },
    {
      type: 'Building separation',
      typical: '6–24 m',
      source: 'ADG (Apartment Design Guide) — varies by building height',
      notes: 'Applies to residential flat buildings. Not the same as side setback.',
    },
    {
      type: 'Foreshore building line',
      typical: 'Varies',
      source: 'LEP map + DCP',
      notes: 'Mapped on the LEP. No development seaward of the line without consent.',
    },
  ];

  return (
    <div className="overflow-x-auto my-6">
      <table className="w-full text-sm border border-slate-200 rounded-xl overflow-hidden">
        <thead>
          <tr className="bg-slate-50 text-left">
            <th className="px-4 py-3 font-semibold text-slate-900">Setback type</th>
            <th className="px-4 py-3 font-semibold text-slate-900">Typical range</th>
            <th className="px-4 py-3 font-semibold text-slate-900 hidden sm:table-cell">Source</th>
            <th className="px-4 py-3 font-semibold text-slate-900 hidden md:table-cell">Notes</th>
          </tr>
        </thead>
        <tbody>
          {types.map(({ type, typical, source, notes }) => (
            <tr key={type} className="border-t border-slate-100">
              <td className="px-4 py-3 font-medium text-slate-900">{type}</td>
              <td className="px-4 py-3 text-slate-600">{typical}</td>
              <td className="px-4 py-3 text-slate-500 hidden sm:table-cell">{source}</td>
              <td className="px-4 py-3 text-slate-400 hidden md:table-cell">{notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  What affects setback values                                        */
/* ------------------------------------------------------------------ */

function SetbackFactorsGrid() {
  const factors = [
    {
      factor: 'Zone',
      detail: 'R2 Low Density typically has larger front setbacks than R3 Medium Density or B zones.',
    },
    {
      factor: 'Lot width',
      detail: 'Narrow lots (under 12 m) often get reduced side setbacks. Some DCPs specify 0.9 m for lots under 10 m wide.',
    },
    {
      factor: 'Building height / storeys',
      detail: 'Upper-storey side setbacks are often larger than ground-floor setbacks to reduce overshadowing.',
    },
    {
      factor: 'Development type',
      detail: 'A dual occupancy may have different setbacks than a dwelling house on the same lot in the same zone.',
    },
    {
      factor: 'Street hierarchy',
      detail: 'Properties fronting classified roads or arterials may have larger front setbacks than those on local streets.',
    },
    {
      factor: 'Precinct / character area',
      detail: 'Many councils have precinct-specific controls that override the general DCP setback.',
    },
    {
      factor: 'Prevailing setback',
      detail: 'Some councils require the front setback to match the average of neighbouring buildings within a certain distance.',
    },
    {
      factor: 'Corner lots',
      detail: 'Corner lots have both a primary and secondary street setback. The secondary is typically smaller.',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-6">
      {factors.map(({ factor, detail }) => (
        <div key={factor} className="rounded-xl border border-slate-200 p-4">
          <p className="font-semibold text-slate-900 text-sm mb-1">{factor}</p>
          <p className="text-sm text-slate-500">{detail}</p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function SetbackRequirementsNSWPage() {
  return (
    <article className="max-w-2xl mx-auto px-6 py-12">
      <BlogPostingJsonLd
        title={`Setback Requirements in NSW: Front, Side & Rear Setbacks Explained`}
        description="NSW setback requirements vary by council, zone, lot width, and development type. This guide covers how front, side, and rear setbacks work under DCPs, what triggers different rules, and where to find the controls for your property."
        slug="setback-requirements-nsw"
        date="2026-05-20"
      />
      {/* Reverse pyramid — answer first */}
      <h1 className="text-3xl font-bold text-slate-900 mb-4">
        Setback Requirements in NSW: Front, Side &amp; Rear Setbacks Explained
      </h1>

      <p className="text-lg text-slate-600 mb-6 leading-relaxed">
        Setback requirements in NSW are set by each council&apos;s Development Control Plan
        (DCP), not by the LEP. They vary by zone, lot width, building height, development
        type, and sometimes by precinct or street. There is no single statewide setback
        rule — you need to check the DCP that applies to your specific property.
      </p>

      <div className="rounded-xl bg-teal-50 border border-teal-200 p-4 text-sm text-teal-800 mb-8">
        <strong>Quick lookup:</strong>{' '}
        <Link href="/assessment" className="text-teal-700 underline underline-offset-2 hover:text-teal-600">
          Enter your address in Verify
        </Link>{' '}
        to see the DCP setback controls that apply to your property — front, side, rear,
        and secondary street — with clause citations.
      </div>

      {/* TOC */}
      <nav className="rounded-xl border border-slate-200 p-5 mb-10">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Contents</p>
        <ul className="space-y-1.5 text-sm">
          {[
            ['what-is-a-setback', 'What is a setback?'],
            ['types-of-setbacks', 'Types of setbacks'],
            ['what-affects-setbacks', 'What affects the setback distance'],
            ['dcp-vs-lep', 'DCP vs LEP — where setbacks come from'],
            ['front-setbacks', 'Front setbacks in detail'],
            ['side-setbacks', 'Side setbacks in detail'],
            ['rear-setbacks', 'Rear setbacks in detail'],
            ['apartment-design-guide', 'Apartment Design Guide building separation'],
            ['variations', 'Can you vary a setback?'],
            ['how-to-find', 'How to find the setback for your property'],
          ].map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} className="text-teal-600 hover:text-teal-500">{label}</a>
            </li>
          ))}
        </ul>
      </nav>

      {/* ---- What is a setback ---- */}
      <section id="what-is-a-setback" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">What is a setback?</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A setback is the minimum distance a building (or part of a building) must be from a
          property boundary. Setbacks control the building envelope — the 3D space within
          which development can occur on a lot.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Setbacks serve several planning purposes: they preserve streetscape character, provide
          separation between buildings for privacy and ventilation, reduce overshadowing of
          adjoining properties, and maintain space for landscaping and tree canopy.
        </p>
        <p className="text-slate-600 leading-relaxed">
          In NSW, setback requirements are almost always found in the council&apos;s DCP, not in
          the LEP. The LEP sets the zone, floor space ratio (FSR), and{' '}
          <Link href="/blog/building-height-limits-nsw" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            building height limits
          </Link>
          . The DCP adds the finer-grained controls including setbacks, landscaping, parking
          rates, and site coverage.
        </p>
      </section>

      {/* ---- Types of setbacks ---- */}
      <section id="types-of-setbacks" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Types of setbacks</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Every lot has at least three setback requirements: front, side, and rear. Corner
          lots add a secondary street setback. Multi-storey residential flat buildings add
          building separation distances under the Apartment Design Guide (ADG).
        </p>
        <SetbackTypesTable />
        <p className="text-sm text-slate-500 leading-relaxed">
          These ranges are indicative. Actual values vary by council. For example, front
          setbacks in the Inner West DCP range from 3 m to 6.5 m depending on the
          precinct and street type, while in Penrith DCP they may be 4.5 m to 10 m
          depending on the character area.
        </p>
      </section>

      {/* ---- What affects setbacks ---- */}
      <section id="what-affects-setbacks" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          What affects the setback distance
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The setback that applies to your property depends on multiple factors. This is why
          a simple &ldquo;what&apos;s the setback in NSW?&rdquo; question has no single answer — it
          depends on where the lot is and what you want to build.
        </p>
        <SetbackFactorsGrid />
      </section>

      {/* ---- DCP vs LEP ---- */}
      <section id="dcp-vs-lep" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          DCP vs LEP — where setbacks come from
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          This distinction matters because it affects how flexible setback requirements are.
          LEP controls are statutory — they&apos;re part of a legal instrument made under the
          Environmental Planning and Assessment Act 1979. DCP controls are not statutory in the
          same sense. A council must &ldquo;take into consideration&rdquo; a DCP when assessing a DA,
          but DCP controls can be varied if the applicant demonstrates the variation achieves the
          objectives of the control.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          In practice, most councils treat setback non-compliance seriously, particularly front
          setbacks. But the legal weight of a DCP setback is different from the legal weight of an
          LEP height limit or FSR. Read more about the{' '}
          <Link href="/blog/development-control-plans-explained" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            full DCP hierarchy and how provisions work
          </Link>.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Some setback-like controls <em>do</em> sit in the LEP: the foreshore building line
          (mapped on the LEP) and occasionally specific setbacks for heritage items. Check your{' '}
          <Link href="/blog/nsw-planning-portal-gaps" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            planning certificate and spatial overlays
          </Link>{' '}
          to confirm whether any LEP-level building lines apply to your lot.
        </p>
      </section>

      {/* ---- Front setbacks ---- */}
      <section id="front-setbacks" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Front setbacks in detail</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The front setback is measured from the front boundary of the lot to the nearest part
          of the building facade (excluding minor projections like eaves, awnings, or porches,
          which typically have separate allowances).
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Front setback controls serve two primary objectives: maintaining a consistent
          streetscape, and providing space for deep soil planting in the front yard.
        </p>
        <h3 className="text-lg font-semibold text-slate-900 mb-2">Prevailing setback</h3>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Many councils use a &ldquo;prevailing setback&rdquo; approach rather than a fixed number.
          This means the required front setback is the average of the front setbacks of the
          buildings on either side of your lot, or within a specified distance along the street.
          The logic is that new development sits in line with existing buildings.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Where the DCP specifies both a minimum setback <em>and</em> a prevailing setback rule,
          the prevailing setback typically overrides — but only if it is greater than the minimum.
          Some councils apply the prevailing setback only in certain character areas.
        </p>
      </section>

      {/* ---- Side setbacks ---- */}
      <section id="side-setbacks" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Side setbacks in detail</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Side setbacks are typically the smallest setback on a lot. They exist to provide
          separation between buildings for fire safety, privacy, ventilation, and maintenance
          access.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A common structure in DCPs is to specify a minimum ground-floor side setback
          (e.g., 0.9 m) and a larger upper-floor side setback (e.g., 1.5 m) to reduce
          the visual bulk of upper storeys and limit overshadowing.
        </p>
        <h3 className="text-lg font-semibold text-slate-900 mb-2">Zero lot line / nil setback</h3>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Some zones and development types allow building to the side boundary (zero setback)
          on one side. This is common in terrace-house precincts and some medium-density zones.
          Where a DCP permits nil setback on one side, it typically requires a larger setback on
          the other side — often 1.5 m or more.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Note that even where the DCP permits a nil side setback, the Building Code of Australia
          (BCA) fire separation requirements still apply. A wall on the boundary typically needs
          to be a fire-rated wall with no openings.
        </p>
      </section>

      {/* ---- Rear setbacks ---- */}
      <section id="rear-setbacks" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Rear setbacks in detail</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Rear setbacks are typically the largest setback on a residential lot. They exist
          to preserve private open space and deep soil areas at the rear of properties.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Many DCPs tie the rear setback to the concept of &ldquo;rear building line&rdquo; or
          &ldquo;private open space&rdquo; — a zone at the rear of the lot where no built form is
          permitted. This area often overlaps with minimum landscaped area and deep soil
          requirements.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Rear setbacks for corner lots or lots that back onto a laneway may be reduced,
          because the rear condition is different — there is no adjoining residential
          property directly behind. Check your specific DCP for laneway provisions.
        </p>
      </section>

      {/* ---- ADG building separation ---- */}
      <section id="apartment-design-guide" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Apartment Design Guide building separation
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          For residential flat buildings and mixed-use developments containing apartments,
          the Apartment Design Guide (ADG) — which is incorporated into SEPP (Housing) 2021 —
          sets building separation distances that are separate from (and often greater than) DCP
          side setbacks.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          ADG separation distances increase with building height: 12 m between habitable rooms
          up to 4 storeys, 18 m for 5&ndash;8 storeys, and 24 m for 9+ storeys. These are
          measured between facing walls of separate buildings, not from the boundary.
        </p>
        <p className="text-slate-600 leading-relaxed">
          The practical effect is that a setback from the side boundary of half the separation
          distance is needed (e.g., 6 m for a 4-storey apartment building, 9 m for a 5&ndash;8
          storey building). This is significantly larger than the 0.9&ndash;1.5 m side setback
          typical for dwelling houses. Read more about{' '}
          <Link href="/blog/building-height-limits-nsw" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            how building height limits interact with these controls
          </Link>.
        </p>
      </section>

      {/* ---- Variations ---- */}
      <section id="variations" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Can you vary a setback?</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Because setbacks are DCP controls (not LEP), they can technically be varied through the
          DA process. The test is whether the variation achieves the objectives of the control —
          not whether it complies with the number.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Common grounds for setback variations include: irregular lot shapes where strict
          compliance produces an unreasonable result, existing buildings on the lot that
          already encroach into the setback, or design solutions that achieve the DCP
          objective through alternative means (e.g., an angled facade that reduces overlooking
          despite a reduced side setback).
        </p>
        <p className="text-slate-600 leading-relaxed">
          Complying Development Certificates (CDCs) have less flexibility — if the{' '}
          <Link href="/blog/cdc-vs-da-which-approval-pathway" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            CDC pathway
          </Link>{' '}
          applies, you must meet the setback in the Housing SEPP exactly. There is no
          &ldquo;variation clause&rdquo; for CDCs.
        </p>
      </section>

      {/* ---- How to find ---- */}
      <section id="how-to-find" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          How to find the setback for your property
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Finding the correct setback requires identifying which DCP applies, which part of the
          DCP covers your zone and development type, and whether any precinct-specific controls
          override the general provisions.
        </p>
        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5 my-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Manual process</p>
          <ol className="space-y-2 text-sm text-slate-600 list-decimal list-inside">
            <li>Identify your LGA and the applicable DCP on council&apos;s website</li>
            <li>Find the residential development section (often Part B or Part C)</li>
            <li>Look up the controls for your zone (e.g., R2 Low Density Residential)</li>
            <li>Check if your property is in a character area or precinct with specific controls</li>
            <li>Cross-reference the development type (dwelling house, dual occupancy, etc.)</li>
            <li>Check for any LEP-level building lines (foreshore, heritage)</li>
          </ol>
          <p className="text-xs text-slate-400 mt-3">
            This typically takes 30&ndash;60 minutes per property across council PDF documents.
          </p>
        </div>
        <p className="text-slate-600 leading-relaxed">
          PlotDetect extracts DCP setback controls into structured numeric fields with clause
          citations — front, side, rear, and secondary street setbacks — for{' '}
          <Link href="/assessment" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            {COVERAGE_DISPLAY.dcpNumericCouncils} LGAs covering numeric controls and {COVERAGE_DISPLAY.dcpFullCouncils} councils with full structured provisions
          </Link>.
          Enter your address to see which setbacks apply.
        </p>
      </section>

      {/* CTA */}
      <div className="rounded-2xl bg-slate-50 border border-slate-200 p-6 text-center mt-10 mb-6">
        <p className="font-bold text-slate-900 mb-2">Check setback controls for your property</p>
        <p className="text-sm text-slate-500 mb-4">
          Enter any NSW address. See DCP setbacks, zone, LEP controls, and spatial overlays.
        </p>
        <TrackedLink
          href="/assessment"
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          page="setback-requirements-nsw"
          cta="run_verify"
        >
          Open Verify <ArrowRight className="w-4 h-4" />
        </TrackedLink>
      </div>

      <BlogDisclaimer />
    </article>
  );
}
