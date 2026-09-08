import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    '5 Things City Conveyancers Miss on Regional Property Transactions — PlotDetect',
  description:
    'Regional NSW property transactions involve on-site sewage, bushfire BAL requirements, rural minimum lot sizes, Crown road access, and water rights. Here are 5 issues city conveyancers commonly overlook.',
  keywords: [
    'regional property conveyancing NSW',
    'buying rural property NSW checks',
    'rural property due diligence NSW',
    'country property conveyancing pitfalls',
    'regional NSW property purchase',
    'on-site sewage management NSW',
    'rural subdivision NSW minimum lot size',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual: The 5 items as a checklist                                 */
/* ------------------------------------------------------------------ */

function FiveItemsChecklist() {
  const items = [
    {
      number: 1,
      title: 'On-site sewage management',
      summary: 'No sewer connection means OSSM compliance under the LG Act',
      icon: '!',
      color: 'bg-red-500',
    },
    {
      number: 2,
      title: 'Bushfire BAL requirements',
      summary:
        'Regional properties are often BAL-29 or higher \u2014 $40K\u2013$200K+ in extra build costs',
      icon: '!',
      color: 'bg-orange-500',
    },
    {
      number: 3,
      title: 'Minimum lot sizes for subdivision',
      summary:
        'Rural zone minimums range from 2ha to 100ha+ \u2014 not the 450m\u00B2 city conveyancers expect',
      icon: '!',
      color: 'bg-amber-500',
    },
    {
      number: 4,
      title: 'Access and road classification',
      summary:
        'Crown roads, paper roads, and right-of-way issues can block legal access entirely',
      icon: '!',
      color: 'bg-yellow-600',
    },
    {
      number: 5,
      title: 'Water rights and bore licences',
      summary:
        'Water access licences do not automatically transfer with land title',
      icon: '!',
      color: 'bg-blue-500',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        5 issues city conveyancers commonly miss on regional transactions
      </p>
      <div className="space-y-3">
        {items.map((item) => (
          <a
            key={item.number}
            href={`#item-${item.number}`}
            className="block rounded-xl bg-white border border-slate-200 p-4 hover:border-teal-300 transition-colors"
          >
            <div className="flex items-start gap-3">
              <span
                className={`flex-shrink-0 w-7 h-7 rounded-full ${item.color} flex items-center justify-center text-xs font-bold text-white`}
              >
                {item.number}
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  {item.title}
                </p>
                <p className="text-sm text-slate-600 mt-0.5">{item.summary}</p>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Visual: Metro vs regional comparison                               */
/* ------------------------------------------------------------------ */

function MetroVsRegionalComparison() {
  const rows = [
    {
      aspect: 'Sewerage',
      metro: 'Town sewer \u2014 automatic connection',
      regional: 'On-site system \u2014 council approval required',
    },
    {
      aspect: 'Bushfire',
      metro: 'Rarely above BAL-12.5',
      regional: 'Often BAL-29, BAL-40, or BAL-FZ',
    },
    {
      aspect: 'Subdivision minimum',
      metro: '150\u2013600m\u00B2 typical',
      regional: '2ha\u2013100ha+ depending on zone',
    },
    {
      aspect: 'Road access',
      metro: 'Dedicated public road, council-maintained',
      regional: 'Crown roads, paper roads, private right-of-way',
    },
    {
      aspect: 'Water supply',
      metro: 'Town water \u2014 metered connection',
      regional: 'Bore, dam, tank, or river \u2014 licences required',
    },
    {
      aspect: 'Flood data',
      metro: 'Usually available from council or state layer',
      regional: 'Often no publicly accessible digital data',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Metro vs regional \u2014 what changes
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                Aspect
              </th>
              <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                Metro Sydney
              </th>
              <th className="text-left py-3 font-semibold text-slate-900">
                Regional NSW
              </th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {rows.map((r) => (
              <tr key={r.aspect} className="border-b border-slate-100">
                <td className="py-3 pr-4 font-medium">{r.aspect}</td>
                <td className="py-3 pr-4">{r.metro}</td>
                <td className="py-3">{r.regional}</td>
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

export default function RegionalPropertyConveyancingPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="5 things city conveyancers miss on regional property transactions"
        description="On-site sewage, bushfire BAL, minimum lot sizes, Crown roads, and water rights — the checks that trip up metro-trained conveyancers."
        slug="regional-property-conveyancing-nsw"
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
          5 things city conveyancers miss on regional property transactions
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Regional NSW property transactions involve infrastructure, hazards,
          and legal considerations that rarely come up in metro settlements.
          On-site sewage, high BAL ratings, rural minimum lot sizes, Crown road
          access, and water licensing all require specific checks that a city
          conveyancer may not think to make.
        </p>
      </div>

      {/* Immediate value: the 5 items */}
      <FiveItemsChecklist />

      {/* Comparison table */}
      <MetroVsRegionalComparison />

      {/* Body */}
      <div className="space-y-10">
        {/* ITEM 1: On-site sewage */}
        <section id="item-1" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            1. On-site sewage management
          </h2>
          <p className="text-slate-700 leading-relaxed">
            In metro Sydney, virtually every property connects to the town
            sewer system operated by Sydney Water. In regional NSW, many
            properties rely on on-site sewage management systems (OSSMS)
            &mdash; septic tanks, aerated wastewater treatment systems (AWTS),
            or composting toilets.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Under the{' '}
            <span className="font-medium">Local Government Act 1993</span> and
            the{' '}
            <span className="font-medium">
              Local Government (General) Regulation 2021
            </span>
            , all on-site sewage systems require council approval to install and
            operate. When a property changes hands, the new owner inherits the
            obligation to maintain a compliant system. If the existing system
            is non-compliant &mdash; or if there is no system at all &mdash;
            the cost to install or upgrade can range from $10,000 to $40,000.
          </p>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              What to check
            </p>
            <ul className="space-y-1.5 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Request the OSSM approval from council &mdash; confirm a valid
                approval exists for the installed system
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Ask when the last compliance inspection was conducted (councils
                inspect on a 1&ndash;5 year cycle)
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Check the buffer distances &mdash; OSSMS must be minimum
                distances from waterways, property boundaries, and bores
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                If the property has no town sewer and no approved OSSM, factor in
                $15K&ndash;$40K for a new system
              </li>
            </ul>
          </div>
        </section>

        {/* ITEM 2: Bushfire */}
        <section id="item-2" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            2. Bushfire BAL requirements
          </h2>
          <p className="text-slate-700 leading-relaxed">
            In metro Sydney, most residential properties are BAL-LOW or not on
            Bush Fire Prone Land at all. In regional NSW, especially in
            timbered areas like the Blue Mountains, Hawkesbury, Shoalhaven,
            Wingecarribee, and Cessnock, properties commonly attract BAL-29,
            BAL-40, or even BAL-FZ (Flame Zone) ratings.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The cost implications are significant. At BAL-29, construction
            costs increase by $40,000 to $80,000 for a standard residential
            build. At BAL-FZ, the increase can exceed $200,000. Insurance
            premiums are also substantially higher, and at BAL-FZ, some
            insurers will not offer cover at all. See our full guide on{' '}
            <Link
              href="/blog/bushfire-attack-level-bal-property-buyers"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              understanding BAL ratings for property buyers
            </Link>
            .
          </p>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              What to check
            </p>
            <ul className="space-y-1.5 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Check the RFS Bush Fire Prone Land map for BFPL category (1, 2,
                or 3)
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                If the buyer plans any construction, budget for a formal BAL
                assessment ($500&ndash;$2,000)
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Get an insurance quote before exchange &mdash; bushfire loading
                can add $2,000&ndash;$5,000+ to annual premiums
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Check Asset Protection Zone (APZ) maintenance obligations
                &mdash; these are ongoing requirements under{' '}
                <span className="font-medium italic">
                  Planning for Bush Fire Protection 2019
                </span>
              </li>
            </ul>
          </div>
          <p className="text-slate-700 leading-relaxed">
            PlotDetect&apos;s{' '}
            <Link
              href="/reports/bushfire"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Bushfire Risk Report
            </Link>{' '}
            provides an indicative BAL risk band for any NSW address using
            satellite vegetation data and the RFS fire register.
          </p>
        </section>

        {/* ITEM 3: Minimum lot sizes */}
        <section id="item-3" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            3. Minimum lot sizes for subdivision and dual occupancy
          </h2>
          <p className="text-slate-700 leading-relaxed">
            In metro zones (R1, R2, R3), minimum lot sizes for subdivision
            typically range from 150m&sup2; to 600m&sup2;. City conveyancers
            who work exclusively with metro properties develop an intuition
            that a &ldquo;large block&rdquo; means subdivision potential.
          </p>
          <p className="text-slate-700 leading-relaxed">
            In rural zones (RU1, RU2, RU4, RU5), minimum lot sizes in the LEP
            can range from 2 hectares to 100 hectares or more. A 10-acre
            (4ha) property that looks enormous to a city buyer may be well
            below the minimum for subdivision in an RU1 Primary Production
            zone.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Dual occupancy permissibility also varies. SEPP (Housing) 2021
            permits secondary dwellings in most residential zones, but rural
            zones have different thresholds and some councils impose additional
            DCP controls. A buyer who assumes they can add a granny flat to
            a rural lot without checking the specific LEP minimum lot size
            and DCP provisions may face a costly surprise.
          </p>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              What to check
            </p>
            <ul className="space-y-1.5 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Check the LEP Lot Size Map for the specific minimum lot size
                applicable to the zone
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Verify dual occupancy and secondary dwelling permissibility
                in the land use table for that zone
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Check whether the lot is &ldquo;battle-axe&rdquo; shaped
                &mdash; some councils prohibit subdivision of battle-axe lots
                in rural zones
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                If the buyer mentions &ldquo;subdivision potential,&rdquo;
                verify it against the LEP before any value is attributed to it
              </li>
            </ul>
          </div>
        </section>

        {/* ITEM 4: Access and roads */}
        <section id="item-4" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            4. Access and road classification
          </h2>
          <p className="text-slate-700 leading-relaxed">
            In metro areas, virtually every residential property fronts a
            council-maintained public road. In regional NSW, road access is
            significantly more complex:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Crown roads</span> &mdash; roads
              that appear on old parish maps but have never been formed or
              maintained. The land is still Crown land. They may cross private
              property. They can affect boundary surveys and create access
              ambiguity.
            </li>
            <li>
              <span className="font-medium">Paper roads</span> &mdash;
              surveyed road reserves that exist on plan but have no physical
              road. The property may appear to have legal road frontage on the
              title plan, but no actual formed access.
            </li>
            <li>
              <span className="font-medium">Right-of-way access</span> &mdash;
              some rural properties are accessed via easements over neighbouring
              land. The terms of the easement (maintenance responsibilities,
              permitted use, width) matter significantly.
            </li>
            <li>
              <span className="font-medium">Private roads and fire trails</span>{' '}
              &mdash; some properties are accessed via private roads maintained
              by a group of landowners, or via RFS fire trails that may not
              have public access rights.
            </li>
          </ul>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              What to check
            </p>
            <ul className="space-y-1.5 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Verify the property has legal access via a formed, publicly
                maintained road &mdash; not just road frontage on the plan
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Check for Crown road reservations on the title or parish map
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                If access is via easement, review the easement terms for
                maintenance obligations and permitted use
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                For properties accessed via private roads, confirm whether a
                road maintenance agreement exists between landowners
              </li>
            </ul>
          </div>
        </section>

        {/* ITEM 5: Water rights */}
        <section id="item-5" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            5. Water rights and bore licences
          </h2>
          <p className="text-slate-700 leading-relaxed">
            In metro areas, water supply is a metered connection to the town
            water main. In regional NSW, properties may rely on bores, dams,
            river pumping, or rainwater tanks. Each has a different legal
            framework:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Bore licences</span> &mdash;
              extracting groundwater requires a Water Access Licence (WAL) and
              a Water Supply Work Approval under the{' '}
              <span className="font-medium">Water Management Act 2000</span>.
              These are separate instruments from the land title and do not
              automatically transfer with the sale.
            </li>
            <li>
              <span className="font-medium">Water sharing plans</span> &mdash;
              most of NSW is covered by water sharing plans that cap total
              extraction. A bore licence does not guarantee unlimited water
              &mdash; allocations can be reduced in drought years.
            </li>
            <li>
              <span className="font-medium">Riparian setbacks</span> &mdash;
              properties adjacent to rivers, creeks, or wetlands have mandatory
              setbacks under the{' '}
              <span className="font-medium">Water Management Act</span> and
              often under the council&apos;s DCP. Building within the riparian
              corridor triggers additional approvals and may be prohibited
              entirely.
            </li>
            <li>
              <span className="font-medium">Dam licences</span> &mdash; farm
              dams above a certain capacity require licensing. A property
              advertised with &ldquo;a large dam&rdquo; may have an unlicensed
              dam that the new owner would need to either licence or
              decommission.
            </li>
          </ul>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              What to check
            </p>
            <ul className="space-y-1.5 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Search the WaterNSW Public Register for any Water Access
                Licences associated with the property
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Confirm whether WALs are included in the sale contract &mdash;
                they must be transferred separately
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Check the applicable water sharing plan for allocation limits
                and any temporary restrictions
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                If the property borders a waterway, check riparian setback
                requirements in both the LEP and DCP
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">&bull;</span>
                Verify dam licences if any dams are present on the property
              </li>
            </ul>
          </div>
        </section>

        {/* CLOSING: Why this matters now */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why this matters now
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Around 30,000 Australians move from capital cities to regional areas
            each year, roughly 50% above pre-COVID levels. Many are buying
            their first regional property. They rely on their conveyancer to
            surface issues that are not visible from a Domain listing or a
            weekend inspection.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The five issues above are not edge cases. On-site sewage affects
            most rural properties without town sewer. Bushfire BAL requirements
            affect large areas of coastal and hinterland NSW. Water rights are
            relevant to any property with a bore or dam. These are standard
            considerations for regional conveyancing &mdash; but they are easy
            to miss if your practice predominantly handles metro transactions.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For buyers doing their own research, PlotDetect&apos;s{' '}
            <Link
              href="/check"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              free property check
            </Link>{' '}
            covers zoning, hazard overlays, and LEP constraints for any NSW
            address. For a more detailed view of flood and bushfire exposure,
            see the{' '}
            <Link
              href="/reports/flood"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Flood Screening Report
            </Link>{' '}
            and{' '}
            <Link
              href="/reports/bushfire"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Bushfire Risk Report
            </Link>
            .
          </p>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check regional property constraints before you buy
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect covers zoning, bushfire, flood, environmental overlays,
              and DCP controls for any NSW address. Run a free check to see what
              planning constraints apply to a regional property.
            </p>
            <TrackedLink
              href="/check"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              page="regional-property-conveyancing-nsw"
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
