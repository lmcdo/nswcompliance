import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { ArrowRight } from 'lucide-react';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title: 'Uninsurable Properties: How Climate Risk Is Repricing Australian Real Estate — PlotDetect',
  description:
    'Insurance withdrawal, premium spikes, and the emerging data infrastructure that buyers need to assess property-level climate exposure before purchase.',
  keywords: [
    'uninsurable property australia',
    'climate risk property value',
    'flood insurance nsw',
    'bushfire insurance cost',
    'property climate risk',
    'insurance affordability australia',
    'northern rivers flood insurance',
  ],
};

export default function UninsurablePropertyPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Uninsurable properties: how climate risk is repricing Australian real estate"
        description="Insurance withdrawal, premium spikes, and the emerging data infrastructure that buyers need to assess property-level climate exposure before purchase."
        slug="uninsurable-property-climate-risk"
        date="2026-05-17"
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
          Uninsurable properties: how climate risk is repricing Australian real estate
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          One in 25 Australian addresses now faces insurance premiums above $5,000 per year.
          In some flood- and cyclone-exposed areas, insurers have withdrawn entirely.
          The property market is slowly pricing in what the insurance industry already knows —
          and most buyers are finding out too late.
        </p>
      </div>

      {/* Body */}
      <div className="space-y-8">
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">The affordability crisis is a data problem</h2>
          <p className="text-slate-700 leading-relaxed">
            The Actuaries Institute estimated in 2024 that approximately 520,000 Australian households
            face insurance affordability stress — defined as premiums exceeding one month&apos;s household
            income. In northern NSW, parts of southeast Queensland, and far north Queensland, the
            numbers are worse. Some communities report that 30-40% of households have dropped
            insurance coverage entirely.
          </p>
          <p className="text-slate-700 leading-relaxed">
            This isn&apos;t happening uniformly. Two properties on the same street can have dramatically
            different premiums based on floor height, proximity to waterways, vegetation setback,
            or building construction. The insurer knows this — they use address-level risk models
            built from decades of claims data, engineering assessments, and catastrophe modelling.
            The buyer, typically, does not.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The information asymmetry is the core problem. Insurers have property-level risk data.
            Buyers have a suburb-level reputation and whatever the real estate agent chooses to disclose.
            By the time the buyer gets an insurance quote, they&apos;ve already exchanged contracts.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What &ldquo;uninsurable&rdquo; actually means</h2>
          <p className="text-slate-700 leading-relaxed">
            Strictly speaking, very few Australian properties are technically uninsurable. What happens
            in practice is a sequence of escalation:
          </p>
          <ol className="space-y-3 text-slate-700 leading-relaxed list-decimal list-inside">
            <li>
              <span className="font-medium">Premium loading.</span> The insurer adds a risk premium
              based on hazard exposure. A property in a 1-in-100 year flood zone might see premiums
              2-5x higher than a comparable property outside the zone.
            </li>
            <li>
              <span className="font-medium">Excess loading.</span> The insurer increases the flood
              or storm excess to $10,000-$25,000, making claims economically unviable for all but
              catastrophic events.
            </li>
            <li>
              <span className="font-medium">Product withdrawal.</span> The insurer stops offering
              flood cover entirely for that address, while still offering fire and theft. The
              property is technically insurable — just not for its primary risk.
            </li>
            <li>
              <span className="font-medium">Full withdrawal.</span> In extreme cases, all major
              insurers decline to offer any policy. This is rare but documented in parts of the
              Northern Rivers and far north Queensland.
            </li>
          </ol>
          <p className="text-slate-700 leading-relaxed">
            The ACCC&apos;s Northern Australia Insurance Inquiry (2020) documented this progression in
            detail. Since then, the 2022 floods and subsequent events have accelerated the trend
            southward into the Hunter Valley, Hawkesbury-Nepean, and parts of Western Sydney.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">How this affects property values</h2>
          <p className="text-slate-700 leading-relaxed">
            Academic research is beginning to quantify the impact. A 2023 study by the University of
            NSW found that properties in high-flood-risk areas in the Hawkesbury-Nepean experienced
            a price discount of 5-12% relative to comparable properties outside flood zones, with the
            discount widening after the 2022 floods.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The mechanism is straightforward: if annual insurance costs add $3,000-$8,000 to the
            cost of ownership, the capitalised value of that liability reduces what a rational buyer
            should pay. At a 5% discount rate, $5,000 per year in additional insurance costs equates
            to $100,000 in property value destruction.
          </p>
          <p className="text-slate-700 leading-relaxed">
            But the market doesn&apos;t adjust smoothly. Most buyers don&apos;t check insurance costs before
            purchase. Vendor disclosure requirements in NSW (s10.7 certificates) indicate flood
            planning area status but don&apos;t quantify the financial exposure. The price adjustment
            happens after purchase, when the buyer discovers the true cost of ownership — and by
            then, the loss is locked in.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">The bushfire dimension</h2>
          <p className="text-slate-700 leading-relaxed">
            Flood gets most of the attention, but bushfire insurance stress is equally significant
            in peri-urban areas. Properties assessed at BAL-40 or BAL-Flame Zone under AS 3959
            face substantial premium loadings. More critically, the cost of building to BAL
            standards adds $50,000-$200,000 to construction costs — a factor that affects
            development feasibility and renovation economics.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The Black Summer fires (2019-20) and subsequent events triggered a recalibration of
            bushfire risk models across the insurance industry. Properties that were previously
            assessed as moderate risk have been reclassified. The NSW Bush Fire Prone Land map
            is updated periodically, and each update can shift the risk profile of thousands of
            properties.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Unlike flood, where mitigation infrastructure (levees, detention basins) can reduce
            risk, bushfire mitigation is primarily about vegetation management and building
            construction — both of which are the property owner&apos;s responsibility and ongoing cost.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">Climate projections compound the problem</h2>
          <p className="text-slate-700 leading-relaxed">
            Current insurance pricing reflects historical claims experience with some forward-looking
            adjustment. But climate projections suggest that the current hazard profile is a floor,
            not a ceiling. NARCliM 2.0 projections for NSW show:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>Increased intensity of rainfall events (more water in shorter periods)</li>
            <li>More days above 35&deg;C in Western Sydney (from ~10/year to ~30/year by 2060 under SSP3.70)</li>
            <li>Extended fire seasons with higher Forest Fire Danger Index values</li>
            <li>Sea level rise affecting coastal erosion and tidal inundation</li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            For property buyers, this means that today&apos;s insurance premium is likely the cheapest
            it will ever be. A property that&apos;s marginally affordable to insure today may become
            genuinely unaffordable within 10-15 years — well within the typical mortgage term.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What buyers can do</h2>
          <p className="text-slate-700 leading-relaxed">
            The most effective protection is pre-purchase due diligence. Before exchanging contracts:
          </p>
          <ol className="space-y-3 text-slate-700 leading-relaxed list-decimal list-inside">
            <li>
              <span className="font-medium">Get an insurance quote before you bid.</span> Call
              at least two insurers with the address and ask for a full quote including flood,
              storm, and bushfire cover. The quote tells you more than any flood map.
            </li>
            <li>
              <span className="font-medium">Check the flood planning status.</span> Request the
              s10.7 certificate (your conveyancer should do this) and check whether the property
              is in a flood planning area. If it is, ask for the flood study data to understand
              depth and frequency.
            </li>
            <li>
              <span className="font-medium">Check Bush Fire Prone Land status.</span> The NSW
              RFS publishes these maps. If the property is on BFPL land, a BAL assessment will
              be required for any future development — and the BAL rating affects insurance.
            </li>
            <li>
              <span className="font-medium">Look at climate projections.</span> What does the
              hazard profile look like in 2040 or 2060? Properties in areas with worsening
              projections face compounding insurance costs over the life of a mortgage.
            </li>
            <li>
              <span className="font-medium">Use property-level risk data.</span> Suburb-level
              assessments are insufficient. Two properties 200 metres apart can have completely
              different flood, bushfire, and heat exposure depending on elevation, vegetation,
              and watercourse proximity.
            </li>
          </ol>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">The role of disclosure</h2>
          <p className="text-slate-700 leading-relaxed">
            There is growing momentum for mandatory climate risk disclosure at the point of property
            sale. The Productivity Commission&apos;s 2024 report on natural disaster funding recommended
            that state governments require standardised hazard disclosure in vendor statements.
            Several states are reviewing their disclosure frameworks.
          </p>
          <p className="text-slate-700 leading-relaxed">
            In the interim, the information gap creates both risk and opportunity. Buyers who do
            their due diligence can avoid properties with hidden climate liabilities. Vendors who
            can demonstrate low climate exposure may achieve price premiums as the market becomes
            more risk-aware.
          </p>
          <p className="text-slate-700 leading-relaxed">
            For conveyancers and buyer&apos;s agents, climate risk assessment is becoming a professional
            obligation. Failing to advise a client about material flood or bushfire risk exposure
            creates professional liability. The tools to check are now available — the question is
            whether the profession integrates them into standard pre-purchase workflows.
          </p>
        </section>

        {/* CTA */}
        <section className="mt-12 space-y-6">
          <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check the climate risk profile before you buy
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect provides free, instant climate risk assessment for any NSW address —
              flood depth, bushfire BAL estimation, heat stress projections, and coastal hazard
              data from government sources. No account required.
            </p>
            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/reports/flood"
                className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
                page="uninsurable-property-climate-risk"
                cta="check_flood"
              >
                Check flood risk
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/reports/bushfire"
                className="inline-flex items-center gap-2 px-6 py-3 text-slate-700 text-sm font-medium rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all"
              >
                Check bushfire risk
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* Back link */}
        <div className="pt-8 border-t border-slate-100">
          <Link href="/blog" className="text-sm text-slate-500 hover:text-teal-600 transition-colors">
            &larr; Back to Insights
          </Link>
        </div>
      </div>
    </article>
  );
}
