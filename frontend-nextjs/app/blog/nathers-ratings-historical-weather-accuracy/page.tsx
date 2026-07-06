import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'NatHERS Ratings Use Historical Weather: 7-Star Might Perform Like 5-Star by 2050 — PlotDetect',
  description:
    'NatHERS energy ratings are based on weather data from 1990-2015. A 7-star home today may perform like 5-star by 2050. Here is why the gap matters and what buyers and builders can do.',
  keywords: [
    'NatHERS energy rating accuracy',
    'energy efficiency rating future climate',
    'NatHERS weather data outdated',
    'home energy rating climate change',
    '7 star energy rating Australia',
    'NatHERS climate zones outdated',
    'building energy performance gap',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual components                                                  */
/* ------------------------------------------------------------------ */

/** Visual 1 — Star rating vs actual performance degradation */
function PerformanceDegradationDiagram() {
  const decades = [
    { year: '2025', rated: 7.0, actual: 6.8, bar: 97 },
    { year: '2030', rated: 7.0, actual: 6.3, bar: 90 },
    { year: '2040', rated: 7.0, actual: 5.6, bar: 80 },
    { year: '2050', rated: 7.0, actual: 5.0, bar: 71 },
    { year: '2060', rated: 7.0, actual: 4.5, bar: 64 },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
        The performance gap over time
      </p>
      <p className="text-xs text-slate-400 mb-5">
        A 7-star rated home under current NatHERS weather files vs estimated
        actual thermal performance under SSP3-7.0 (regional rivalry) scenario
      </p>
      <div className="space-y-3">
        {decades.map((d) => (
          <div key={d.year} className="flex items-center gap-4">
            <span className="text-xs font-bold text-slate-500 w-10 flex-shrink-0">
              {d.year}
            </span>
            <div className="flex-1 relative h-8 rounded-lg bg-slate-100 overflow-hidden">
              {/* Rated bar (background) */}
              <div className="absolute inset-0 rounded-lg bg-teal-100" />
              {/* Actual performance bar */}
              <div
                className="absolute inset-y-0 left-0 rounded-lg bg-teal-500 transition-all"
                style={{ width: `${d.bar}%` }}
              />
              <div className="absolute inset-0 flex items-center justify-between px-3">
                <span className="text-xs font-medium text-white z-10">
                  {d.actual}-star actual
                </span>
                <span className="text-xs text-teal-700">
                  7-star rated
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4 italic">
        Indicative estimates based on CSIRO research into future weather files
        for NatHERS. Actual degradation varies by climate zone, orientation,
        and construction. These are not predictions of specific outcomes.
      </p>
    </div>
  );
}

/** Visual 2 — Climate zone impact comparison */
function ClimateZoneImpact() {
  const zones = [
    {
      zone: 'Western Sydney',
      nathers: 'Zone 28 (Penrith)',
      impact: 'High',
      reason:
        'Projected +2-4\u00b0C summer maximums by 2070. Cooling load increase overwhelms insulation benefits. Urban heat island amplifies warming.',
      impactColor: 'text-red-600 bg-red-50',
    },
    {
      zone: 'Tropical North',
      nathers: 'Zones 1-3 (Cairns, Darwin)',
      impact: 'High',
      reason:
        'Year-round cooling demand increases. Humidity projections not captured in historical weather files. Condensation risk rises.',
      impactColor: 'text-red-600 bg-red-50',
    },
    {
      zone: 'Coastal Sydney',
      nathers: 'Zone 56 (Sydney)',
      impact: 'Medium',
      reason:
        'Ocean moderates temperature extremes but heatwave frequency is projected to double. Coastal humidity increases condensation risk.',
      impactColor: 'text-amber-600 bg-amber-50',
    },
    {
      zone: 'Southern Highlands',
      nathers: 'Zone 24 (Canberra/Queanbeyan)',
      impact: 'Low-Medium',
      reason:
        'Reduced heating load partially offsets increased cooling. Net energy impact is smaller but direction is still negative.',
      impactColor: 'text-teal-600 bg-teal-50',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Which climate zones are most affected
      </p>
      <div className="space-y-4">
        {zones.map((z) => (
          <div key={z.zone} className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-sm font-bold text-slate-900">{z.zone}</p>
                <p className="text-xs text-slate-500">{z.nathers}</p>
              </div>
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full ${z.impactColor}`}
              >
                {z.impact} impact
              </span>
            </div>
            <p className="text-sm text-slate-700">{z.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function NatHERSHistoricalWeatherPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="NatHERS ratings use historical weather: 7-star might perform like 5-star by 2050"
        description="NatHERS simulates energy performance using 1990-2015 weather data. Buildings last 50+ years. The gap between rated and actual performance is growing."
        slug="nathers-ratings-historical-weather-accuracy"
        date="2026-05-20"
      />
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-700">
            Climate Risk
          </span>
          <span className="text-xs text-slate-400">May 2026</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          NatHERS ratings use historical weather: 7-star might perform like 5-star by 2050
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Every new home in Australia needs a minimum 7-star NatHERS energy
          rating. But that rating is calculated using weather data from
          1990&ndash;2015. Buildings are designed to last 50+ years. The climate
          they will operate in is not the climate they were rated for.
        </p>
      </div>

      {/* Immediate value — the performance gap */}
      <PerformanceDegradationDiagram />

      {/* Body */}
      <div className="space-y-10">
        {/* How NatHERS works */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            How NatHERS works
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The Nationwide House Energy Rating Scheme simulates how much energy
            a home needs for heating and cooling to maintain thermal comfort.
            The simulation uses a Reference Meteorological Year (RMY) &mdash; a
            synthetic year of weather data assembled from historical
            observations for each of NatHERS&apos; 69 climate zones across
            Australia.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The RMY represents &ldquo;typical&rdquo; weather conditions based on
            Bureau of Meteorology records from approximately 1990 to 2015. The
            higher the star rating, the less energy the building needs to heat
            and cool under those historical conditions. Since NCC 2022, the
            mandatory minimum for new residential buildings is 7 stars.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The problem: the RMY data describes a climate that no longer exists
            and will increasingly diverge from reality over the building&apos;s
            lifespan. A building rated under 1990&ndash;2015 weather conditions
            will experience hotter summers, more frequent heatwaves, higher
            humidity, and different seasonal patterns than the conditions it was
            designed for.
          </p>
        </section>

        {/* The research */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What the research shows
          </h2>
          <p className="text-slate-700 leading-relaxed">
            CSIRO has been developing future weather files for NatHERS since
            the mid-2010s, modelling how Reference Meteorological Year data
            would change under various warming scenarios. Their findings are
            consistent: buildings rated 7 stars under current weather files
            perform progressively worse as actual weather diverges from
            historical patterns.
          </p>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              Key findings from climate-adjusted NatHERS research
            </p>
            <ul className="space-y-1.5 text-sm text-slate-700">
              <li>
                Cooling energy demand increases by 20&ndash;80% by 2050 in
                most Australian climate zones under SSP3-7.0
              </li>
              <li>
                Western Sydney and tropical northern zones show the largest
                performance degradation due to extreme heat amplification
              </li>
              <li>
                Heating demand decreases in southern zones, partially offsetting
                cooling increases &mdash; but net energy demand still rises
              </li>
              <li>
                A 7-star home designed for Penrith&apos;s current RMY may
                require 40&ndash;60% more cooling energy by 2050 than the
                rating suggests
              </li>
              <li>
                Humidity projections (not well captured in current RMY files)
                could further degrade performance in coastal and tropical zones
              </li>
            </ul>
          </div>

          <p className="text-slate-700 leading-relaxed">
            The &ldquo;5-star by 2050&rdquo; headline is an approximation. The
            actual gap depends on climate zone, scenario, orientation,
            construction materials, and occupant behaviour. But the direction
            is clear: the gap between rated and actual performance widens every
            year.
          </p>
        </section>

        {/* Climate zone impacts */}
        <ClimateZoneImpact />

        {/* What this means for buyers */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What this means for buyers
          </h2>
          <p className="text-slate-700 leading-relaxed">
            If you are buying a new home with a 7-star NatHERS rating, the
            rating accurately describes the building&apos;s thermal performance
            under the historical weather conditions used for the simulation. It
            does not describe how the building will perform in 2040 or 2060.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The practical consequences include:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Higher energy costs</span> &mdash;
              cooling costs will likely exceed what the star rating implies,
              particularly in Western Sydney, North Queensland, and other
              heat-exposed areas.
            </li>
            <li>
              <span className="font-medium">Comfort gaps</span> &mdash; a
              building designed to maintain comfort under 35&deg;C peak days may
              struggle with 40&deg;C+ days that become more frequent.
            </li>
            <li>
              <span className="font-medium">Retrofit costs</span> &mdash;
              upgrading insulation, glazing, or shading after construction is
              significantly more expensive than designing for future climate
              upfront.
            </li>
            <li>
              <span className="font-medium">Resale implications</span> &mdash;
              as climate-adjusted ratings become available, homes rated under
              outdated weather files may need re-assessment.
            </li>
          </ul>
        </section>

        {/* What's being done */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What is being done about it
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The gap is acknowledged. Several initiatives are in progress:
          </p>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                CSIRO future weather files
              </h3>
              <p className="text-slate-700 leading-relaxed">
                CSIRO has developed prototype future weather files for NatHERS
                that incorporate climate projections. These files model how the
                Reference Meteorological Year would change under SSP2-4.5 and
                SSP3-7.0 scenarios at 2030, 2050, and 2070 timeframes. They
                are not yet adopted into the NatHERS framework but represent
                the most likely path to addressing the gap.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                NCC 2025 review
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The National Construction Code 2025, adoptable from May 2026,
                includes updated energy efficiency provisions. However, the
                underlying climate data for NatHERS zones has not been updated
                to reflect future warming. The NCC 2025 retains the existing
                climate zone structure and historical weather files. A separate
                ABCB-led review of climate zone boundaries and weather data
                methodology is underway but has no published timeline for
                completion.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                CC&NH SEPP (NSW)
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The draft Climate Change and Natural Hazards SEPP for NSW would
                prescribe NARCliM 2.0 climate scenarios for development
                assessment. While this does not directly change NatHERS ratings,
                it creates a regulatory environment where forward-looking
                climate data is required for development approval &mdash;
                setting the stage for climate-adjusted building performance
                standards.
              </p>
            </div>
          </div>
        </section>

        {/* What buyers and builders can do */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What buyers and builders can do now
          </h2>
          <p className="text-slate-700 leading-relaxed">
            You do not need to wait for regulatory reform. Several strategies
            help close the performance gap:
          </p>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. Design above minimum
              </h3>
              <p className="text-slate-700 leading-relaxed">
                A home rated 8 stars under current weather files will degrade
                to roughly 6&ndash;6.5 stars by 2050, still above today&apos;s
                mandatory minimum. Building to 8 or 9 stars now provides a
                buffer against future climate divergence.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Prioritise passive cooling
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The biggest performance gap is in cooling, not heating.
                Cross-ventilation, eave depth, external shading, light-coloured
                roofing, and thermal mass positioning have a disproportionate
                impact on maintaining comfort during hotter-than-rated
                conditions.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Check your climate zone&apos;s trajectory
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Some climate zones will shift categories under projected
                warming. Western Sydney, currently classified as a temperate
                zone, is projected to experience conditions more consistent
                with subtropical zones by mid-century. PlotDetect&apos;s{' '}
                <Link
                  href="/climate-risk"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  climate risk assessment
                </Link>{' '}
                shows projected temperature and hazard changes for any NSW
                address.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                4. Ask for future-adjusted modelling
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Some energy assessors can run NatHERS simulations using CSIRO
                future weather files as an unofficial supplementary assessment.
                This is not a replacement for the mandatory rating (which uses
                standard RMY files) but gives a clearer picture of how the
                building will actually perform.
              </p>
            </div>
          </div>
        </section>

        {/* Broader context */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The broader picture
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The NatHERS weather file gap is part of a wider pattern: Australian
            planning and building regulations are calibrated to historical
            climate data while the actual climate is changing. The{' '}
            <Link
              href="/blog/aasb-s2-mandatory-climate-reporting-property"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              AASB S2 mandatory climate reporting
            </Link>{' '}
            standard explicitly requires forward-looking scenario analysis for
            property portfolios. Building ratings, by contrast, remain
            backward-looking.
          </p>
          <p className="text-slate-700 leading-relaxed">
            This creates an asymmetry: investors and lenders will soon be
            required to assess future climate risk on properties, while the
            building code rates those same properties using past weather data.
            The gap between regulatory intent and building performance standards
            is widening.
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
                Does this mean 7-star homes are poorly built?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                No. A 7-star home performs well under the conditions it was
                designed for. The issue is that those conditions are based on
                historical weather data that is progressively diverging from
                actual and projected weather patterns.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Will my NatHERS rating be downgraded?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Existing ratings remain valid under the current framework. If
                future weather files are adopted into NatHERS, it is possible
                that re-assessment under updated conditions would produce a
                different rating. No retrospective downgrade mechanism exists
                or is proposed.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Which zones are least affected?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Southern highland and alpine zones are least affected because
                warming reduces their heating demand, partially offsetting
                increased cooling. Coastal zones with strong ocean moderation
                (such as parts of Sydney, Wollongong, and the Mid North Coast)
                are moderately affected. Inland and tropical zones face the
                largest gap.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              See how climate projections affect your property
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s climate risk assessment shows projected
              temperature changes and hazard exposure for any NSW address,
              using NARCliM 2.0 climate projections.
            </p>
            <TrackedLink
              href="/climate-risk"
              page="nathers-ratings-historical-weather-accuracy"
              cta="climate_check"
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
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
