import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Building Height Limits in NSW: How Height of Buildings Controls Work — PlotDetect',
  description:
    'Building height limits in NSW are set by the LEP as a mapped numeric control. This guide explains how height is measured, what the height map shows, how height interacts with FSR and setbacks, and where to find the height limit for your property.',
  keywords: [
    'building height limits nsw',
    'height of buildings nsw',
    'lep height limit',
    'maximum building height nsw',
    'height of buildings map',
    'how is building height measured nsw',
    'height limit residential nsw',
    'lep height map',
    'building height controls',
    'storey limit nsw',
  ],
};

/* ------------------------------------------------------------------ */
/*  Common height limits table                                         */
/* ------------------------------------------------------------------ */

function HeightLimitsExamples() {
  const examples = [
    {
      zone: 'R2 Low Density Residential',
      typicalHeight: '8.5–9 m',
      typicalStoreys: '2 storeys',
      notes: 'Most common residential zone. Height limits vary by council — some set 8.5 m, others 9 m.',
    },
    {
      zone: 'R3 Medium Density Residential',
      typicalHeight: '9–12 m',
      typicalStoreys: '2–3 storeys',
      notes: 'Allows attached dwellings, multi dwelling housing, and some residential flat buildings.',
    },
    {
      zone: 'R4 High Density Residential',
      typicalHeight: '15–45+ m',
      typicalStoreys: '4–15+ storeys',
      notes: 'Highly variable. Height limits in R4 zones depend heavily on the specific area and council strategy.',
    },
    {
      zone: 'B1/B2 Commercial',
      typicalHeight: '10–25 m',
      typicalStoreys: '2–6 storeys',
      notes: 'Town centres and local centres. Often have bonus height provisions for active ground floor uses.',
    },
    {
      zone: 'E1/E2 (formerly RU)',
      typicalHeight: '8–10 m',
      typicalStoreys: '2 storeys',
      notes: 'Environmental and rural zones. Low height limits to protect landscape character.',
    },
    {
      zone: 'IN1/IN2 Industrial',
      typicalHeight: '12–15 m',
      typicalStoreys: 'N/A (measured in metres)',
      notes: 'Industrial buildings are typically measured by overall height, not storeys.',
    },
  ];

  return (
    <div className="overflow-x-auto my-6">
      <table className="w-full text-sm border border-slate-200 rounded-xl overflow-hidden">
        <thead>
          <tr className="bg-slate-50 text-left">
            <th className="px-4 py-3 font-semibold text-slate-900">Zone</th>
            <th className="px-4 py-3 font-semibold text-slate-900">Typical height</th>
            <th className="px-4 py-3 font-semibold text-slate-900 hidden sm:table-cell">Typical storeys</th>
            <th className="px-4 py-3 font-semibold text-slate-900 hidden md:table-cell">Notes</th>
          </tr>
        </thead>
        <tbody>
          {examples.map(({ zone, typicalHeight, typicalStoreys, notes }) => (
            <tr key={zone} className="border-t border-slate-100">
              <td className="px-4 py-3 font-medium text-slate-900">{zone}</td>
              <td className="px-4 py-3 text-slate-600">{typicalHeight}</td>
              <td className="px-4 py-3 text-slate-500 hidden sm:table-cell">{typicalStoreys}</td>
              <td className="px-4 py-3 text-slate-400 hidden md:table-cell">{notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-slate-400 mt-2">
        These are indicative ranges across NSW councils. The actual height limit for a specific
        lot is shown on the LEP Height of Buildings Map for that council area.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function BuildingHeightLimitsPage() {
  return (
    <article className="max-w-2xl mx-auto px-6 py-12">
      <BlogPostingJsonLd
        title="Building Height Limits in NSW: How Height of Buildings Controls Work"
        description="Building height limits in NSW are set by the LEP as a mapped numeric control. This guide explains how height is measured, what the height map shows, how height interacts with FSR and setbacks, and where to find the height limit for your property."
        slug="building-height-limits-nsw"
        date="2026-05-20"
      />
      {/* Reverse pyramid — answer first */}
      <h1 className="text-3xl font-bold text-slate-900 mb-4">
        Building Height Limits in NSW: How Height of Buildings Controls Work
      </h1>

      <p className="text-lg text-slate-600 mb-6 leading-relaxed">
        Building height limits in NSW are set by the Local Environmental Plan (LEP) as a mapped
        numeric control — Clause 4.3 &ldquo;Height of buildings&rdquo; in the Standard
        Instrument LEP. The height limit for a property is shown on the LEP Height of Buildings
        Map, measured in metres from existing ground level to the highest point of the building.
      </p>

      <div className="rounded-xl bg-teal-50 border border-teal-200 p-4 text-sm text-teal-800 mb-8">
        <strong>Quick lookup:</strong>{' '}
        <Link href="/assessment" className="text-teal-700 underline underline-offset-2 hover:text-teal-600">
          Enter your address in Verify
        </Link>{' '}
        to see the LEP height limit, FSR, zone, and other controls for your property.
      </div>

      {/* TOC */}
      <nav className="rounded-xl border border-slate-200 p-5 mb-10">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Contents</p>
        <ul className="space-y-1.5 text-sm">
          {[
            ['how-height-measured', 'How building height is measured'],
            ['height-map', 'The LEP Height of Buildings Map'],
            ['common-limits', 'Common height limits by zone'],
            ['height-vs-storeys', 'Height in metres vs storeys'],
            ['height-and-fsr', 'How height interacts with FSR'],
            ['height-and-setbacks', 'How height affects setbacks'],
            ['height-planes', 'Building height planes in DCPs'],
            ['clause-46', 'Cl 4.6 variations — exceeding the height limit'],
            ['sepp-heights', 'SEPP height provisions'],
            ['how-to-check', 'How to check the height limit for your property'],
          ].map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} className="text-teal-600 hover:text-teal-500">{label}</a>
            </li>
          ))}
        </ul>
      </nav>

      {/* ---- How height is measured ---- */}
      <section id="how-height-measured" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">How building height is measured</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Under the Standard Instrument LEP, &ldquo;building height&rdquo; (also called
          &ldquo;height of building&rdquo;) is the vertical distance from existing ground level
          to the highest point of the building. This includes the roof ridge, parapet, or any
          rooftop structure — but typically excludes certain elements like aerials, chimneys,
          flagpoles, and some plant rooms.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          &ldquo;Existing ground level&rdquo; is the ground level at the time of the DA
          lodgement, before any earthworks associated with the proposed development. This is an
          important distinction — you cannot excavate the site and then measure height from the
          new, lower ground level.
        </p>
        <p className="text-slate-600 leading-relaxed">
          For sloping sites, height is typically measured at any point along the building
          perimeter. The building must not exceed the height limit at any point — not just at
          the tallest part. This means sloping sites effectively lose developable height on the
          uphill side.
        </p>
      </section>

      {/* ---- Height map ---- */}
      <section id="height-map" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          The LEP Height of Buildings Map
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Every LEP in NSW has a Height of Buildings Map (HOB Map) that assigns a maximum
          building height in metres to each parcel of land. The map uses letter codes
          (e.g., &ldquo;I&rdquo; = 9 m, &ldquo;J&rdquo; = 10 m) which correspond to heights
          in the map legend.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The height map is available on the{' '}
          <Link href="/blog/nsw-planning-portal-gaps" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            NSW Planning Portal
          </Link>{' '}
          as a spatial layer. You can also access it through the council&apos;s own mapping
          system or through the formal s10.7 planning certificate process.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Be aware that some lots sit across multiple height bands on the map — this is common
          at zone boundaries or at transitions between low-density and medium-density areas. In
          these cases, the height limit may differ across the lot, which affects what can be built
          in different parts of the site.
        </p>
      </section>

      {/* ---- Common limits ---- */}
      <section id="common-limits" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Common height limits by zone</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Height limits vary by council and zone. The table below shows typical ranges seen
          across NSW councils. The actual height for your property may differ — always check the
          LEP map.
        </p>
        <HeightLimitsExamples />
      </section>

      {/* ---- Height vs storeys ---- */}
      <section id="height-vs-storeys" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Height in metres vs storeys
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The LEP sets height limits in metres, not storeys. However, you will often see
          storey limits mentioned in DCPs, the Apartment Design Guide (ADG), and SEPP provisions.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A rough conversion: residential floor-to-floor height is approximately 3 m, so an 8.5 m
          height limit accommodates 2 storeys plus a pitched roof. A 12 m limit accommodates
          3 storeys. But these are approximations — roof form, floor-to-ceiling height, and
          structural depth all affect whether a given number of storeys fits within the
          height limit.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Where both a metre height limit (LEP) and a storey limit (DCP or SEPP) apply, both
          must be satisfied. A building must not exceed the metre limit and must not exceed the
          storey limit.
        </p>
      </section>

      {/* ---- Height and FSR ---- */}
      <section id="height-and-fsr" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          How height interacts with FSR
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Height and FSR are the two primary LEP development standards that define what can
          be built on a lot. They interact but control different things:
        </p>
        <ul className="list-disc list-inside space-y-2 text-sm text-slate-600 mb-4 ml-2">
          <li>
            <strong>Height</strong> limits the vertical extent — how tall the building can be
          </li>
          <li>
            <strong>FSR</strong> limits the total floor area — how much floor space relative to
            the site area
          </li>
        </ul>
        <p className="text-slate-600 mb-3 leading-relaxed">
          A tall, slender building might comply with height but exceed FSR. A low, sprawling
          building might comply with FSR but have insufficient setbacks. The building envelope
          is defined by the intersection of all applicable controls: height, FSR,{' '}
          <Link href="/blog/setback-requirements-nsw" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            setbacks
          </Link>
          , site coverage, and landscaped area.
        </p>
        <p className="text-slate-600 leading-relaxed">
          In some areas — particularly where councils have recently upzoned — the height and FSR
          controls may not align perfectly. For example, a zone might have a height limit that
          would permit 6 storeys but an FSR that can only be achieved in 4 storeys. The more
          restrictive control governs.
        </p>
      </section>

      {/* ---- Height and setbacks ---- */}
      <section id="height-and-setbacks" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          How height affects setbacks
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Many DCP setback controls increase with building height. Upper-storey side setbacks
          are often larger than ground-floor setbacks. This creates a stepped building form
          that reduces visual bulk and overshadowing.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The Apartment Design Guide (ADG) takes this further with building separation distances
          that scale with height: 12 m for buildings up to 4 storeys, 18 m for 5&ndash;8
          storeys, 24 m for 9+ storeys. These are measured between facing habitable rooms and
          translate into side setback requirements of half the separation distance from each
          boundary.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Some DCPs also use &ldquo;building height planes&rdquo; — angled planes from
          boundaries that limit how high a building can be at a given distance from the boundary.
          These create a 3D envelope that is more nuanced than a flat height limit.
        </p>
      </section>

      {/* ---- Height planes ---- */}
      <section id="height-planes" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Building height planes in DCPs
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Some councils use building height planes (also called building envelope planes or
          recession planes) in their DCPs. These are imaginary angled planes that start at a
          point on the boundary and slope inward at a specified angle.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          For example, a DCP might specify a height plane that starts at 3.5 m on the side
          boundary and rises at 45 degrees. This means the building can be 3.5 m at the
          boundary, 5 m at 1.5 m from the boundary, 6.5 m at 3 m from the boundary, and so on —
          up to the LEP height limit.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Height planes are a DCP control, not an LEP control. They sit below the LEP height
          limit in the hierarchy — a building that complies with the height plane may still be
          below the maximum LEP height. Read more about the{' '}
          <Link href="/blog/development-control-plans-explained" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            DCP hierarchy and how these controls work
          </Link>.
        </p>
      </section>

      {/* ---- Cl 4.6 ---- */}
      <section id="clause-46" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          Cl 4.6 variations — exceeding the height limit
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Clause 4.6 of the Standard Instrument LEP provides a mechanism to vary development
          standards (including height). An applicant must demonstrate that compliance with the
          standard is &ldquo;unreasonable or unnecessary in the circumstances&rdquo; and that
          there are environmental planning grounds that justify the variation.
        </p>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The test was clarified by the Court of Appeal in <em>Wehbe v Pittwater Council</em>
          {' '}[2007] NSWLEC 827, which established five ways to demonstrate that compliance is
          unreasonable or unnecessary. In practice, the most commonly relied upon test is that
          the objectives of the development standard are achieved despite the non-compliance.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Height variations above certain thresholds require concurrence from the Department of
          Planning. Variations above 10% of a mapped LEP height limit are scrutinised more
          closely. Variations of 40% or more are very rarely granted.
        </p>
      </section>

      {/* ---- SEPP heights ---- */}
      <section id="sepp-heights" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">SEPP height provisions</h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          Some SEPPs set their own height limits that override or supplement the LEP:
        </p>
        <ul className="list-disc list-inside space-y-2 text-sm text-slate-600 mb-4 ml-2">
          <li>
            <strong>SEPP (Housing) 2021</strong> — sets maximum heights for in-fill affordable
            housing and build-to-rent development that may exceed the LEP height limit
          </li>
          <li>
            <strong>SEPP (Transport and Infrastructure) 2021</strong> — certain infrastructure
            may be exempt from height limits
          </li>
          <li>
            <strong>SEPP (Precincts — Eastern Harbour City) 2021</strong> — site-specific height
            controls for identified precincts that replace the LEP
          </li>
        </ul>
        <p className="text-slate-600 leading-relaxed">
          Where a SEPP sets a height limit, it overrides the LEP. Check which SEPPs apply to
          your property — the{' '}
          <Link href="/blog/cdc-vs-da-which-approval-pathway" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            CDC vs DA pathway analysis
          </Link>{' '}
          covers how SEPP provisions interact with local controls.
        </p>
      </section>

      {/* ---- How to check ---- */}
      <section id="how-to-check" className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">
          How to check the height limit for your property
        </h2>
        <p className="text-slate-600 mb-3 leading-relaxed">
          The height limit for a specific property can be found through:
        </p>
        <ol className="space-y-2 text-sm text-slate-600 list-decimal list-inside mb-4">
          <li>
            The NSW Planning Portal — select the lot and check the &ldquo;Height of buildings&rdquo;
            layer
          </li>
          <li>
            A s10.7 planning certificate — ordered from the council (the height limit is a
            standard inclusion)
          </li>
          <li>
            The council&apos;s own online mapping system (where available)
          </li>
        </ol>
        <p className="text-slate-600 leading-relaxed">
          PlotDetect pulls the LEP height limit directly from the Planning Portal for all 128
          NSW councils. Enter your address in{' '}
          <Link href="/assessment" className="text-teal-600 underline underline-offset-2 hover:text-teal-500">
            Verify
          </Link>{' '}
          to see the height limit alongside FSR, zone, minimum lot size, heritage status, and
          DCP controls.
        </p>
      </section>

      {/* CTA */}
      <div className="rounded-2xl bg-slate-50 border border-slate-200 p-6 text-center mt-10 mb-6">
        <p className="font-bold text-slate-900 mb-2">Check the height limit for your property</p>
        <p className="text-sm text-slate-500 mb-4">
          Enter any NSW address. See LEP height, FSR, zone, and DCP controls.
        </p>
        <TrackedLink
          href="/assessment"
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          page="building-height-limits-nsw"
          cta="run_verify"
        >
          Open Verify <ArrowRight className="w-4 h-4" />
        </TrackedLink>
      </div>

      <BlogDisclaimer />
    </article>
  );
}
