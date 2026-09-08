import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { ArrowRight } from 'lucide-react';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title: 'Is My House in a Flood Zone? How to Check in NSW — PlotDetect',
  description:
    'Step-by-step guide to checking flood zone status for any NSW property — free government sources, what the data actually means, and what it misses.',
  keywords: [
    'is my house in a flood zone nsw',
    'flood zone check nsw',
    'nsw flood map',
    'flood planning area nsw',
    's10.7 certificate flood',
    'flood risk check nsw',
    'flood zone property nsw',
  ],
};

export default function FloodZoneCheckPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title="Is my house in a flood zone? How to check in NSW"
        description="Step-by-step guide to checking flood zone status for any NSW property — free government sources, what the data actually means, and what it misses."
        slug="is-my-house-in-a-flood-zone-nsw"
        date="2026-05-17"
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
          Is my house in a flood zone? How to check in NSW
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          Whether you&apos;re buying, building, or just curious, knowing your flood risk
          matters. Here&apos;s how to check for free using government data — and what
          the results actually tell you.
        </p>
      </div>

      {/* Body */}
      <div className="space-y-8">
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What &ldquo;flood zone&rdquo; means in NSW</h2>
          <p className="text-slate-700 leading-relaxed">
            In NSW, there&apos;s no single official &ldquo;flood zone&rdquo; designation. Instead, there
            are several overlapping layers of flood information, each with a different purpose:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">Flood Planning Area (FPA)</span> — defined in the
              Local Environmental Plan (LEP). This is the statutory boundary that triggers planning
              controls. If your property is inside the FPA, development applications will need to
              address flood-related clauses.
            </li>
            <li>
              <span className="font-medium">Flood Control Lot</span> — a property that the Planning
              Portal identifies as affected by flood-related LEP provisions. You can check this via
              the NSW Planning Portal&apos;s property search.
            </li>
            <li>
              <span className="font-medium">Flood study extent</span> — the area modelled in a
              council flood study. These studies calculate how deep water gets at different flood
              frequencies (e.g. 1-in-100 year event). Not all areas have detailed flood studies.
            </li>
            <li>
              <span className="font-medium">Flood prone land</span> — a broader category used in
              the NSW Flood Prone Land Policy. Land is &ldquo;flood prone&rdquo; if it can be inundated
              by the Probable Maximum Flood (PMF) — an extreme theoretical event.
            </li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            A property can be &ldquo;flood prone&rdquo; without being in the Flood Planning Area, and
            vice versa. The FPA is the one that matters most for planning approvals and is typically
            based on the 1% AEP (1-in-100 year) flood plus a freeboard allowance (usually 0.5m).
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">How to check: step by step</h2>
          <p className="text-slate-700 leading-relaxed">
            There are three free ways to check flood status for any NSW property. Each gives you
            different information.
          </p>

          <div className="space-y-6 mt-4">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. NSW Planning Portal — property search
              </h3>
              <p className="text-slate-700 leading-relaxed mb-3">
                Go to the <span className="font-medium">NSW Planning Portal</span> (planningportal.nsw.gov.au)
                and use the property search tool. Enter any NSW address. The portal returns a list of
                planning constraints, including whether the property is a &ldquo;Flood Control Lot&rdquo; under the LEP.
              </p>
              <p className="text-slate-700 leading-relaxed">
                <span className="font-medium">What it tells you:</span> Whether the LEP applies flood-related
                clauses to this property. This is a yes/no answer — it doesn&apos;t tell you how deep the
                water gets or how often it floods.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Section 10.7 Planning Certificate
              </h3>
              <p className="text-slate-700 leading-relaxed mb-3">
                When buying property, your conveyancer will order a s10.7 certificate from the local
                council. This is a legal document that lists all planning controls affecting the property.
                Clause 7 covers &ldquo;flood related development controls.&rdquo;
              </p>
              <p className="text-slate-700 leading-relaxed">
                <span className="font-medium">What it tells you:</span> The same binary flood status as
                the Planning Portal, but in a legally binding document. If flood controls apply, the
                certificate says so. If they don&apos;t, it says &ldquo;no&rdquo; — and the council is liable for
                that statement.
              </p>
              <p className="text-slate-700 leading-relaxed mt-2">
                <span className="font-medium">What it doesn&apos;t tell you:</span> Flood depth, frequency,
                historical flood events, insurance implications, or whether the property flooded in
                past events. Many buyers assume the s10.7 gives a complete picture. It doesn&apos;t.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Council flood maps and flood studies
              </h3>
              <p className="text-slate-700 leading-relaxed mb-3">
                Some councils publish flood study data on their websites or through the NSW SES.
                These studies model flood behaviour for specific catchments — how deep the water gets,
                how fast it flows, and how often flooding of different severity occurs.
              </p>
              <p className="text-slate-700 leading-relaxed">
                <span className="font-medium">What it tells you:</span> Actual flood depth and extent
                at different return intervals. For example, in a 1-in-100 year flood, this property
                would experience 0.3m of water. In a 1-in-500 year flood, 1.2m. This is the most
                useful information for understanding real flood risk.
              </p>
              <p className="text-slate-700 leading-relaxed mt-2">
                <span className="font-medium">The catch:</span> Not all councils have detailed flood
                studies. Where they exist, they can be hard to find and interpret. Studies are often
                published as PDF reports with GIS layers that require specialist software to read.
              </p>
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Understanding ARI return periods
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Flood studies describe flood severity using Average Recurrence Intervals (ARI) — sometimes
            called Annual Exceedance Probability (AEP). These are statistical measures, not predictions.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse mt-4">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">ARI</th>
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">AEP</th>
                  <th className="text-left py-3 font-semibold text-slate-900">What it means</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">1-in-20 year</td>
                  <td className="py-3 pr-4">5%</td>
                  <td className="py-3">5% chance of this level happening in any given year. Common enough that you&apos;d likely experience it during a 30-year mortgage.</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">1-in-50 year</td>
                  <td className="py-3 pr-4">2%</td>
                  <td className="py-3">Less frequent, but a 45% chance of occurring at least once in 30 years.</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">1-in-100 year</td>
                  <td className="py-3 pr-4">1%</td>
                  <td className="py-3">The standard used for flood planning areas in NSW. Still a 26% chance over 30 years.</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium">1-in-500 year</td>
                  <td className="py-3 pr-4">0.2%</td>
                  <td className="py-3">Rare but catastrophic. Used for emergency planning. The Hawkesbury-Nepean has had events near this magnitude.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-slate-700 leading-relaxed mt-4">
            A common misconception: &ldquo;1-in-100 year flood&rdquo; does not mean it only happens once
            every 100 years. It means there&apos;s a 1% chance in any given year. Over a 30-year
            mortgage, there&apos;s roughly a 1-in-4 chance it happens at least once. The Hawkesbury-Nepean
            experienced two major floods within three years (2021 and 2022).
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What flood status means for insurance</h2>
          <p className="text-slate-700 leading-relaxed">
            Insurance companies use their own flood models — they don&apos;t simply rely on the LEP
            flood planning area. An insurer might consider a property &ldquo;flood exposed&rdquo; even if
            the council doesn&apos;t, or vice versa.
          </p>
          <p className="text-slate-700 leading-relaxed">
            That said, if your property is in an LEP flood planning area, you should expect:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>Higher insurance premiums — typically $1,000-$5,000 more than comparable non-flood properties</li>
            <li>Higher excess for flood claims — some policies set flood excess at $10,000+</li>
            <li>In severe cases, flood cover may be excluded from your policy entirely</li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            The most important thing you can do is get an insurance quote <span className="font-medium">before</span> you
            buy. Call at least two insurers with the specific address and ask for a quote including flood cover.
            The premium will tell you more about real flood risk than any planning certificate.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">What flood status means for building</h2>
          <p className="text-slate-700 leading-relaxed">
            If your property is in a flood planning area, any development application will need to address
            the flood-related clauses in the LEP and DCP. Typically, this means:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>Minimum floor levels — habitable floors must be above the 1% AEP flood level plus freeboard</li>
            <li>Building materials — below the flood planning level, materials must be flood-compatible (no plasterboard, carpet, etc.)</li>
            <li>Structural design — buildings must withstand flood forces (hydrostatic and hydrodynamic loads)</li>
            <li>Evacuation — the site must have a viable evacuation route that doesn&apos;t require crossing floodwater</li>
            <li>Storage — no storage of hazardous materials below the flood planning level</li>
          </ul>
          <p className="text-slate-700 leading-relaxed">
            These requirements can add $50,000-$200,000 to construction costs depending on the
            flood depth and the type of development. For renovations, they can make otherwise
            straightforward projects significantly more complex.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">The gap between &ldquo;flood zone&rdquo; and actual risk</h2>
          <p className="text-slate-700 leading-relaxed">
            The biggest limitation of the standard flood zone check is that it&apos;s binary — yes or no.
            But flood risk is a spectrum. A property with 0.1m of water in a 1-in-100 year flood has
            a very different risk profile from one with 2m of water. Both would show as &ldquo;flood zone: yes&rdquo;
            on a s10.7 certificate.
          </p>
          <p className="text-slate-700 leading-relaxed">
            Equally, a property just outside the flood planning area boundary isn&apos;t necessarily safe.
            The boundary is drawn at a specific flood level (usually 1% AEP + freeboard), and it
            represents a modelling output with inherent uncertainty. Climate change is also shifting
            these boundaries — the current flood planning level was calculated using historical rainfall
            data that may not reflect future conditions.
          </p>
          <p className="text-slate-700 leading-relaxed">
            What you actually want to know is: <span className="font-medium">how deep does the water
            get at my specific address, and how often?</span> That requires flood study data — the
            modelled depth at different ARI return periods — not just the binary overlay.
          </p>
        </section>

        {/* CTA */}
        <section className="mt-12 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              Check flood risk for any NSW address — free instant results
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s free Flood Screening goes beyond the binary yes/no. Where flood study
              data is available, it shows modelled depth at 1-in-20 through 1-in-500 year return
              intervals — plus LEP flood overlay status from the NSW Planning Portal. No account required.
            </p>
            <TrackedLink
              href="/reports/flood"
              page="is-my-house-in-a-flood-zone-nsw"
              cta="check_flood"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-500 transition-colors"
            >
              Check flood risk — free
              <ArrowRight className="w-4 h-4" />
            </TrackedLink>
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
