import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'The Tree Change Checklist: 7 Planning Checks Before You Buy Rural — PlotDetect',
  description:
    '7 planning and infrastructure checks every city-to-regional buyer should complete before purchasing rural property in NSW. Zoning, bushfire, flood, sewage, water, and access.',
  keywords: [
    'buying rural property NSW checklist',
    'tree change property due diligence',
    'regional property planning checks NSW',
    'moving to the country NSW planning',
    'tree change checklist NSW',
    'rural property due diligence',
    'regional NSW property buying',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline visual components                                          */
/* ------------------------------------------------------------------ */

/** Visual 1 — The 7-item checklist as a prominent card */
function SevenCheckChecklist() {
  const checks = [
    {
      num: 1,
      title: 'Zoning',
      summary: 'What your zone actually permits',
      risk: 'RU1, RU2, RU4, and R5 allow very different things',
      color: 'bg-teal-500',
    },
    {
      num: 2,
      title: 'Minimum Lot Size',
      summary: 'Can you subdivide or add a second dwelling?',
      risk: 'May be 40ha in RU1 — blocking subdivision entirely',
      color: 'bg-blue-500',
    },
    {
      num: 3,
      title: 'Bushfire',
      summary: 'Most regional properties are on Bush Fire Prone Land',
      risk: 'BAL-40/FZ adds $30K-$80K+ to construction costs',
      color: 'bg-red-500',
    },
    {
      num: 4,
      title: 'Flood',
      summary: 'Check flood studies, not just the LEP overlay',
      risk: 'Insurance premiums $1K-$5K higher; may be uninsurable',
      color: 'bg-amber-500',
    },
    {
      num: 5,
      title: 'On-Site Sewage',
      summary: 'No sewer means an on-site sewage management system',
      risk: 'OSSM installation costs $15K-$50K',
      color: 'bg-violet-500',
    },
    {
      num: 6,
      title: 'Water',
      summary: 'Bore licences, riparian buffers, water sharing plans',
      risk: 'No mains water = rainwater tanks + bore (if licensed)',
      color: 'bg-cyan-500',
    },
    {
      num: 7,
      title: 'Access',
      summary: 'Unsealed roads, Crown roads, right-of-way',
      risk: 'No legal road access = no building approval',
      color: 'bg-slate-500',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        7 planning checks before you buy rural
      </p>
      <div className="space-y-4">
        {checks.map((c) => (
          <div
            key={c.num}
            className="flex gap-4 items-start bg-white rounded-xl border border-slate-100 p-4"
          >
            <div
              className={`flex-shrink-0 w-8 h-8 rounded-full ${c.color} text-white text-sm font-bold flex items-center justify-center`}
            >
              {c.num}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-slate-900">{c.title}</p>
              <p className="text-sm text-slate-600 mt-0.5">{c.summary}</p>
              <p className="text-xs text-slate-400 mt-1 italic">{c.risk}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Visual 2 — Rural zone comparison table */
function RuralZoneComparisonTable() {
  const zones = [
    {
      code: 'RU1',
      name: 'Primary Production',
      dwelling: true,
      secondary: false,
      farm: true,
      tourism: true,
      minLot: '40ha typical',
      character: 'Broad-acre farming, grazing',
    },
    {
      code: 'RU2',
      name: 'Rural Landscape',
      dwelling: true,
      secondary: false,
      farm: true,
      tourism: true,
      minLot: '10-40ha typical',
      character: 'Scenic rural, some agriculture',
    },
    {
      code: 'RU4',
      name: 'Primary Production Small Lots',
      dwelling: true,
      secondary: true,
      farm: true,
      tourism: false,
      minLot: '2-10ha typical',
      character: 'Hobby farms, small-scale rural',
    },
    {
      code: 'R5',
      name: 'Large Lot Residential',
      dwelling: true,
      secondary: true,
      farm: false,
      tourism: false,
      minLot: '0.4-4ha typical',
      character: 'Rural-residential, lifestyle blocks',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Rural zone comparison — what each zone typically allows
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-3 pr-3 font-semibold text-slate-900">
                Zone
              </th>
              <th className="text-left py-3 pr-3 font-semibold text-slate-900">
                Character
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Dwelling
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Secondary
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Farm bldgs
              </th>
              <th className="text-center py-3 px-2 font-semibold text-slate-900">
                Tourism
              </th>
              <th className="text-left py-3 font-semibold text-slate-900">
                Min lot size
              </th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {zones.map((z) => (
              <tr key={z.code} className="border-b border-slate-100">
                <td className="py-3 pr-3 font-medium whitespace-nowrap">
                  {z.code}
                </td>
                <td className="py-3 pr-3 text-xs text-slate-500">
                  {z.character}
                </td>
                <td className="py-3 px-2 text-center">
                  {z.dwelling ? (
                    <span className="text-teal-600 font-bold">Yes</span>
                  ) : (
                    <span className="text-red-400">No</span>
                  )}
                </td>
                <td className="py-3 px-2 text-center">
                  {z.secondary ? (
                    <span className="text-teal-600 font-bold">Yes</span>
                  ) : (
                    <span className="text-slate-400">Varies</span>
                  )}
                </td>
                <td className="py-3 px-2 text-center">
                  {z.farm ? (
                    <span className="text-teal-600 font-bold">Yes</span>
                  ) : (
                    <span className="text-slate-400">Limited</span>
                  )}
                </td>
                <td className="py-3 px-2 text-center">
                  {z.tourism ? (
                    <span className="text-teal-600 font-bold">With DA</span>
                  ) : (
                    <span className="text-slate-400">Unlikely</span>
                  )}
                </td>
                <td className="py-3 text-xs">{z.minLot}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400 mt-3 italic">
        Permissibility varies by council LEP. &ldquo;Secondary&rdquo; = secondary
        dwelling / granny flat. Always verify against the specific LEP land use
        table for your property.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function TreeChangeChecklistPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="The tree change checklist: 7 planning checks before you buy rural"
        description="Zoning, minimum lot size, bushfire, flood, on-site sewage, water rights, and access — the 7 checks before buying regional property in NSW."
        slug="tree-change-checklist-nsw-planning"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-700">
            Property Research
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          The tree change checklist: 7 planning checks before you buy rural
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Around 30,000 Australians move from cities to regional areas every
          year. Roughly 1 in 5 move back. The failures are almost always
          information failures &mdash; things that could have been checked before
          exchange. Here are the 7 planning and infrastructure checks that
          matter most.
        </p>
      </div>

      {/* ========== IMMEDIATE VALUE: the checklist ========== */}
      <SevenCheckChecklist />

      {/* Body */}
      <div className="space-y-10">
        {/* CHECK 1: Zoning */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            1. Zoning &mdash; what your zone actually permits
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Not all rural land is equal. RU1 (Primary Production) is for
            broad-acre farming. R5 (Large Lot Residential) is for lifestyle
            blocks. RU4 (Primary Production Small Lots) sits somewhere in
            between. Each zone has a different land use table in the Local
            Environmental Plan, and the differences are significant.
          </p>
          <p className="text-slate-700 leading-relaxed">
            A property zoned RU1 may not permit a secondary dwelling. An R5
            property may not allow farm buildings beyond a certain scale.
            Tourist accommodation typically requires development consent in RU1
            and RU2, and may be prohibited in R5. Before you fall in love with
            the view, check what the zone actually lets you do.
          </p>

          <RuralZoneComparisonTable />

          <p className="text-slate-700 leading-relaxed">
            <strong>How to check:</strong> Search your property on the{' '}
            <a
              href="https://www.planningportal.nsw.gov.au/spatialviewer"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              NSW Planning Portal
            </a>{' '}
            to find the zoning, or run a{' '}
            <Link
              href="/check"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              free compliance check on PlotDetect
            </Link>{' '}
            to see the zone, permitted uses, and applicable planning controls
            in one view.
          </p>
        </section>

        {/* CHECK 2: Minimum Lot Size */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            2. Minimum lot size &mdash; subdivision and dual occupancy
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Every lot in NSW has a minimum lot size set in the LEP. In rural
            zones, this can range from 2 hectares to 100 hectares or more. The
            minimum lot size determines whether you can subdivide the property
            and, in some cases, whether you can build a second dwelling.
          </p>
          <p className="text-slate-700 leading-relaxed">
            If you are buying 5 acres (about 2ha) in an area where the minimum
            lot size is 40ha, you cannot subdivide. Some councils also tie
            secondary dwelling permissibility to minimum lot size thresholds.
            This is one of the most common surprises for tree changers who
            planned to subdivide or build a granny flat for income.
          </p>
          <p className="text-slate-700 leading-relaxed">
            <strong>How to check:</strong> The minimum lot size map is in the
            LEP. Search the property on the Planning Portal and look at the
            &ldquo;Lot Size Map&rdquo; layer. For a deeper analysis of
            subdivision potential, see our guide on{' '}
            <Link
              href="/blog/subdivide-property-nsw-minimum-lot-sizes"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              subdivision and minimum lot sizes in NSW
            </Link>
            .
          </p>
        </section>

        {/* CHECK 3: Bushfire */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            3. Bushfire &mdash; BAL ratings and construction costs
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Most regional properties in NSW are on Bush Fire Prone Land (BFPL).
            If the property is on the BFPL map, any new dwelling or addition
            requires a Bushfire Attack Level (BAL) assessment under{' '}
            <em>Planning for Bush Fire Protection 2019</em>. The BAL rating
            determines construction requirements under AS 3959.
          </p>
          <p className="text-slate-700 leading-relaxed">
            At BAL-LOW, standard construction applies. At BAL-29, expect
            $15,000&ndash;$30,000 in additional construction costs for ember
            guards, non-combustible materials, and radiant heat protection. At
            BAL-40 or Flame Zone (FZ), costs can exceed $50,000&ndash;$80,000,
            and some builders will not quote at all.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Asset Protection Zones (APZs) also matter. You may need to maintain
            cleared or managed vegetation around any dwelling &mdash; sometimes
            for 30 metres or more &mdash; which affects where you can build on
            the lot.
          </p>
          <p className="text-slate-700 leading-relaxed">
            <strong>How to check:</strong> Use PlotDetect&apos;s{' '}
            <Link
              href="/reports/bushfire"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              free bushfire check
            </Link>{' '}
            or read our detailed guide on{' '}
            <Link
              href="/blog/bushfire-attack-level-bal-property-buyers"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              BAL ratings and what they mean for property buyers
            </Link>
            .
          </p>
        </section>

        {/* CHECK 4: Flood */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            4. Flood &mdash; look beyond the LEP overlay
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The LEP flood overlay is a starting point, not the full picture.
            After legislative changes in 2021 and 2023, many NSW councils have
            reduced or removed flood data from their LEPs. A clean planning
            certificate does not mean the property has no flood risk &mdash; it
            may mean the data layer was revoked.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Regional properties near rivers, creeks, or low-lying areas may
            have flood risk that only shows up in detailed flood studies held by
            council, or on the SES Flood Data Portal. Overland flow and flash
            flooding are almost never captured in statutory flood maps.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Insurance is the forcing function. Properties in flood planning
            areas typically face $1,000&ndash;$5,000 higher annual premiums,
            with flood excess sometimes set at $10,000 or more. Get an
            insurance quote before you buy, not after.
          </p>
          <p className="text-slate-700 leading-relaxed">
            <strong>How to check:</strong> Run a{' '}
            <Link
              href="/reports/flood"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              free flood risk check
            </Link>{' '}
            on PlotDetect, and read our explainer on{' '}
            <Link
              href="/blog/is-my-house-in-a-flood-zone-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              how to check if your property is in a flood zone
            </Link>
            .
          </p>
        </section>

        {/* CHECK 5: On-Site Sewage */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            5. On-site sewage &mdash; no sewer means real costs
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Most regional and rural properties are not connected to reticulated
            sewer. If there is no sewer connection, you need an on-site sewage
            management system (OSSM) &mdash; typically a septic system or
            aerated wastewater treatment system (AWTS).
          </p>
          <p className="text-slate-700 leading-relaxed">
            Installation costs range from $15,000 for a basic septic system to
            $50,000 or more for an AWTS on difficult terrain. The system needs
            council approval under the Local Government Act, and the lot must
            have sufficient area for the absorption field. Steep slopes, high
            water tables, flood-prone land, and proximity to waterways can all
            make on-site sewage difficult or expensive.
          </p>
          <p className="text-slate-700 leading-relaxed">
            If the property has an existing OSSM, check when it was last
            inspected. Councils require periodic inspections, and a failing
            system can cost $20,000&ndash;$40,000 to replace.
          </p>
          <p className="text-slate-700 leading-relaxed">
            <strong>How to check:</strong> Ask the vendor or agent whether the
            property is connected to sewer. If not, request details of the
            existing OSSM system and its last inspection report. Check with
            council whether the system is registered and compliant.
          </p>
        </section>

        {/* CHECK 6: Water */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            6. Water &mdash; supply, licences, and riparian buffers
          </h2>
          <p className="text-slate-700 leading-relaxed">
            No mains water means rainwater tanks, a bore, or surface water
            extraction. Each comes with conditions. Bore licences are issued
            under WaterNSW and may be restricted under a Water Sharing Plan.
            Not every property can get a bore licence, and existing licences
            may have conditions on extraction volume.
          </p>
          <p className="text-slate-700 leading-relaxed">
            If the property adjoins a creek or river, riparian buffer
            requirements apply. Under the Water Management Act 2000 and
            council DCP controls, you may need to maintain a vegetated buffer
            of 10&ndash;40 metres from the watercourse &mdash; reducing your
            buildable area.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Water availability is not just about drinking water. It affects
            whether you can irrigate, keep livestock, or run a farm stay
            business.
          </p>
          <p className="text-slate-700 leading-relaxed">
            <strong>How to check:</strong> Search the{' '}
            <a
              href="https://waterregister.waternsw.com.au"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              WaterNSW Public Register
            </a>{' '}
            for bore licences on the property. Ask the vendor about water
            supply and whether the property has a registered bore or dam.
          </p>
        </section>

        {/* CHECK 7: Access */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            7. Access &mdash; road status and legal access
          </h2>
          <p className="text-slate-700 leading-relaxed">
            In regional NSW, not every road on the map is a council-maintained
            road. Some are Crown roads (owned by the state, often unmaintained),
            some are private access tracks, and some require a right-of-way
            over a neighbour&apos;s property.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Building approval generally requires legal road access to the lot.
            If the only access is via a Crown road or private track, you may
            need to purchase the Crown road reserve or negotiate a formal
            right-of-way &mdash; both of which take time and money.
          </p>
          <p className="text-slate-700 leading-relaxed">
            In bushfire-prone areas, access roads must meet{' '}
            <em>Planning for Bush Fire Protection 2019</em> standards: minimum
            4-metre carriageway width, passing bays, turning circles for fire
            trucks. An existing narrow dirt track may not qualify, which blocks
            building approval.
          </p>
          <p className="text-slate-700 leading-relaxed">
            <strong>How to check:</strong> Review the title to confirm legal
            road access. Check whether the access road is a council road, Crown
            road, or private easement. For bushfire-prone properties, check
            whether the access meets RFS standards.
          </p>
        </section>

        {/* Closing */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The pattern behind the failures
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The 1-in-5 tree changers who move back share common stories:
            insurance was unaffordable, the sewage system failed, the
            subdivision they planned was blocked by minimum lot size, or they
            could not get approval to build because the access road did not
            meet standards. Every one of these problems was discoverable before
            exchange.
          </p>
          <p className="text-slate-700 leading-relaxed">
            A property in the regions can be a transformative move. But the
            planning framework in rural NSW is different from metro Sydney in
            ways that are not obvious until you are already committed. Running
            these seven checks before you exchange does not guarantee a
            successful tree change. But skipping them is how the failures
            happen.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For more on what rural zoning allows, see our guide on{' '}
            <Link
              href="/blog/what-can-i-build-rural-land-nsw"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              what you can build on rural land in NSW
            </Link>
            .
          </p>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check planning controls for any NSW property
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect shows zoning, permitted uses, bushfire status, flood
              overlays, and applicable DCP controls for any NSW address.
              Enter a property to see what the planning rules allow.
            </p>
            <TrackedLink
              href="/check"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="tree-change-checklist-nsw-planning"
              cta="check_address"
            >
              Check a property
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
