import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { ArrowRight } from 'lucide-react';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'Why Your Section 10.7 Certificate Might Not Show Flood Risk — PlotDetect',
  description:
    'NSW flood overlays were removed from LEPs in 2021 and 2023. Your s10.7 planning certificate now shows less flood information than it used to. Here is what changed and what to do about it.',
  keywords: [
    'section 10.7 flood risk nsw',
    'flood planning certificate nsw',
    'is my property in a flood zone nsw',
    's10.7 certificate flood',
    'flood planning area removed lep',
    'nsw flood overlay changes',
    'epi flood data revocation',
  ],
};

/* ------------------------------------------------------------------ */
/*  Inline SVG visual components                                      */
/* ------------------------------------------------------------------ */

/** Visual 1 — s10.7 vs what you actually need (side-by-side) */
function CertificateGapDiagram() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        What your planning certificate tells you vs what you need
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        {/* Left — what you get */}
        <div className="rounded-xl border-2 border-red-200 bg-white p-5">
          <p className="text-sm font-bold text-red-700 mb-3">
            Section 10.7 certificate
          </p>
          <div className="flex items-center gap-3 py-2.5 border-b border-slate-100">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-100 flex items-center justify-center text-xs text-red-600">
              ?
            </span>
            <span className="text-sm text-slate-700">
              Flood controls apply: <strong>Yes / No</strong>
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-3 italic">
            That&apos;s it. One binary answer.
          </p>
        </div>

        {/* Right — what you need */}
        <div className="rounded-xl border-2 border-teal-200 bg-white p-5">
          <p className="text-sm font-bold text-teal-700 mb-3">
            What you actually need to know
          </p>
          {[
            'How deep does the water get?',
            'How often does it flood (1-in-20? 1-in-100?)',
            'Has the property flooded before?',
            'What will insurance cost?',
            'Is there overland flow risk?',
            'Have the flood boundaries changed?',
          ].map((item) => (
            <div
              key={item}
              className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-teal-100 flex items-center justify-center text-xs text-teal-600">
                &times;
              </span>
              <span className="text-sm text-slate-700">{item}</span>
            </div>
          ))}
          <p className="text-xs text-slate-400 mt-3 italic">
            None of this appears on the certificate.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Visual 2 — Timeline of flood data removal */
function FloodDataTimeline() {
  const events = [
    {
      year: 'Pre-2021',
      label: 'Flood maps in LEPs',
      desc: 'Councils included flood planning maps directly in their LEP. Certificates referenced those maps.',
      color: 'bg-teal-500',
    },
    {
      year: 'Jul 2021',
      label: 'Maps removed from LEPs',
      desc: 'Flood Prone Land Package replaced specific maps with generic clauses 5.21 and 5.22.',
      color: 'bg-amber-500',
    },
    {
      year: 'Nov 2023',
      label: 'EPI flood areas revoked',
      desc: 'EPI 2023-609 revoked most remaining EPI Flood Planning Areas. The data layer went blank.',
      color: 'bg-red-500',
    },
    {
      year: '2026-27',
      label: 'CC&NH SEPP (proposed)',
      desc: 'Would centralise flood provisions in one state instrument. Under consideration.',
      color: 'bg-slate-300',
    },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        How NSW flood disclosure changed
      </p>
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-slate-200" />
        <div className="space-y-6">
          {events.map((e) => (
            <div key={e.year} className="relative pl-10">
              <div
                className={`absolute left-1.5 top-1.5 w-3.5 h-3.5 rounded-full ${e.color} ring-4 ring-white`}
              />
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                {e.year}
              </p>
              <p className="text-sm font-semibold text-slate-900 mt-0.5">
                {e.label}
              </p>
              <p className="text-sm text-slate-600 mt-0.5">{e.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Visual 3 — Information asymmetry */
function InsuranceAsymmetryDiagram() {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6 sm:p-8 my-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        The information gap between insurers and buyers
      </p>
      <div className="grid sm:grid-cols-2 gap-6">
        <div className="rounded-xl bg-white border border-slate-200 p-5">
          <p className="text-sm font-bold text-slate-900 mb-2">
            What the insurer knows
          </p>
          <ul className="space-y-1.5 text-sm text-slate-700">
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5">&#9679;</span>
              NFID: 13.7 million addresses mapped
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5">&#9679;</span>
              Proprietary flood depth models
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5">&#9679;</span>
              Historical claims data by address
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-500 mt-0.5">&#9679;</span>
              Climate projection scenarios
            </li>
          </ul>
        </div>
        <div className="rounded-xl bg-white border border-slate-200 p-5">
          <p className="text-sm font-bold text-slate-900 mb-2">
            What the buyer gets
          </p>
          <ul className="space-y-1.5 text-sm text-slate-700">
            <li className="flex items-start gap-2">
              <span className="text-red-400 mt-0.5">&#9679;</span>
              s10.7 certificate: &ldquo;Yes&rdquo; or &ldquo;No&rdquo;
            </li>
          </ul>
          <p className="text-xs text-slate-400 mt-4 italic">
            The premium you&apos;re quoted reflects everything above. The
            certificate you hold reflects one binary flag.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function Section107FloodRiskPage() {
  return (
    <article className="max-w-3xl mx-auto px-6 py-16">
      <BlogPostingJsonLd
        title={`The s10.7 flood data gap: what NSW buyers aren't told`}
        description={`Your planning certificate says yes or no to flood risk. It doesn't say how deep, how often, or what it costs to insure. Here's what's missing and why.`}
        slug="section-10-7-flood-risk-nsw"
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
          Why your Section 10.7 certificate might not show flood risk
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          A s10.7 planning certificate gives you a single yes/no answer about
          flood controls. It does not tell you how deep the water gets, how
          often it floods, or what your insurance will cost. And after two
          legislative changes in 2021 and 2023, the certificate may now show{' '}
          <strong>less</strong> flood information than it used to.
        </p>
      </div>

      {/* ========== IMMEDIATE VALUE: the gap ========== */}
      <CertificateGapDiagram />

      {/* TOC */}
      <nav className="mb-10 rounded-2xl border border-slate-200 p-6">
        <p className="text-sm font-semibold text-slate-900 mb-3">
          In this article
        </p>
        <ul className="space-y-1.5 text-sm text-slate-600">
          <li>
            <a href="#what-to-do" className="hover:text-teal-600">
              What you can do about it
            </a>
          </li>
          <li>
            <a href="#insurance-gap" className="hover:text-teal-600">
              The insurance information gap
            </a>
          </li>
          <li>
            <a href="#what-changed" className="hover:text-teal-600">
              What changed in 2021 and 2023
            </a>
          </li>
          <li>
            <a href="#why-data-missing" className="hover:text-teal-600">
              Why flood data is missing from many councils
            </a>
          </li>
          <li>
            <a href="#council-differences" className="hover:text-teal-600">
              Council-by-council differences
            </a>
          </li>
          <li>
            <a href="#whats-coming" className="hover:text-teal-600">
              What&apos;s coming: the CC&NH SEPP and mandatory climate reporting
            </a>
          </li>
          <li>
            <a href="#faq" className="hover:text-teal-600">
              Frequently asked questions
            </a>
          </li>
        </ul>
      </nav>

      {/* Body */}
      <div className="space-y-10">
        {/* ========== SECTION 1: ACTION (what to do) ========== */}
        <section id="what-to-do" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What you can do about it
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The s10.7 certificate is a starting point, not an endpoint. Five
            ways to get a fuller picture before you commit:
          </p>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                1. Get an insurance quote before you buy
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Call at least two insurers with the specific address and ask for
                a quote including flood cover. The premium reflects the
                insurer&apos;s flood model &mdash; data you cannot access any
                other way. This is the single most informative step a buyer can
                take, and it costs nothing.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                2. Run a flood risk check that goes beyond the binary
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Tools that cross-reference multiple data sources &mdash; LEP
                overlays, flood study modelling, and historical event data
                &mdash; can show depth and frequency information the s10.7 does
                not include. PlotDetect&apos;s{' '}
                <Link
                  href="/reports/flood"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  free Flood Screening
                </Link>{' '}
                does this for any NSW address. For the broader picture
                &mdash; flood, bushfire, coastal, and heat exposure combined
                &mdash; PlotDetect&apos;s{' '}
                <Link
                  href="/climate-risk"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  climate risk score
                </Link>{' '}
                checks five government-mapped hazard layers in one view. It
                shows which hazards overlap your property &mdash; it does not
                predict whether damage will occur.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                3. Check the SES Flood Data Portal
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The NSW SES Flood Data Portal (flooddata.ses.nsw.gov.au) hosts
                1% AEP and historical flood extent layers for some councils.
                Coverage is patchy &mdash; each council decides what to upload
                &mdash; but where data exists, it shows mapped flood extents
                rather than a yes/no flag.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                4. Ask council for flood study data directly
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Some councils will provide flood study information for specific
                properties on request, even where the full dataset is not
                publicly available. Ask for the 1% AEP flood level at your
                address and the flood planning level (FPL). Not all councils
                respond, but it costs nothing to ask.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                5. Look beyond the flood planning area boundary
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Flood planning areas are based on the 1% AEP flood plus a
                freeboard (usually 0.5m). Properties just outside the boundary
                are not necessarily flood-free &mdash; boundaries represent a
                modelling output with inherent uncertainty. Overland flow,
                stormwater flooding, and flash flooding are typically not
                captured in the statutory flood planning area at all.
              </p>
            </div>
          </div>

          <p className="text-slate-700 leading-relaxed">
            If you&apos;re a conveyancer, a{' '}
            <Link
              href="/reports/conveyancing"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Conveyancing Planning Disclosure report
            </Link>{' '}
            consolidates LEP, SEPP, and DCP constraints &mdash; including flood
            overlays &mdash; into a single document. See our{' '}
            <Link
              href="/for/conveyancers"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              planning disclosure tools for conveyancers
            </Link>
            .
          </p>
        </section>

        {/* ========== SECTION 2: CONSEQUENCE (insurance gap) ========== */}
        <section id="insurance-gap" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            The insurance information gap
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Insurers do not rely on s10.7 certificates or LEP flood maps. They
            use proprietary flood models informed by data sources that consumers
            cannot access. The National Flood Information Database (NFID),
            maintained by the Insurance Council of Australia, covers 13.7
            million addresses. It is used for insurance pricing. It is not
            available to the public.
          </p>

          <InsuranceAsymmetryDiagram />

          <p className="text-slate-700 leading-relaxed">
            Properties in flood planning areas typically face $1,000&ndash;$5,000
            higher annual premiums, with flood excess sometimes set at $10,000
            or more. In severe cases, flood cover is excluded entirely. These
            costs are invisible until you ask for a quote &mdash; and by then,
            you may have already exchanged contracts.
          </p>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6 mt-2">
            <p className="text-sm font-semibold text-slate-900 mb-2">
              Key figures from APRA&apos;s March 2026 Insurance Climate
              Vulnerability Assessment
            </p>
            <ul className="space-y-1.5 text-sm text-slate-700">
              <li>1 in 7 Australian households are currently uninsured</li>
              <li>1 in 4 projected to be uninsured by 2050</li>
              <li>
                NSW and QLD together account for 60% of all uninsured homes
              </li>
              <li>
                Annual weather losses: $7 billion (2024), projected above $16
                billion by 2050
              </li>
              <li>Flood losses projected to increase by 240% by 2050</li>
            </ul>
            <p className="text-xs text-slate-500 mt-3">
              Source: APRA &ldquo;Mind the Gap&rdquo; Insurance Climate
              Vulnerability Assessment, March 2026
            </p>
          </div>

          <p className="text-slate-700 leading-relaxed mt-2">
            For a deeper look at how{' '}
            <Link
              href="/blog/uninsurable-property-climate-risk"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              climate risk is repricing Australian property insurance
            </Link>
            , see our analysis of the APRA findings.
          </p>
        </section>

        {/* ========== SECTION 3: STORY (what changed) ========== */}
        <section id="what-changed" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What changed in 2021 and 2023
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Before 2021, most NSW councils included flood planning maps directly
            in their Local Environmental Plans. When you ordered a s10.7
            planning certificate, the certificate referenced those maps. Two
            legislative changes altered this.
          </p>

          <FloodDataTimeline />

          <div className="rounded-2xl border border-slate-200 p-6 space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                July 2021: Flood Prone Land Package
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The{' '}
                <span className="font-medium">
                  Standard Instrument Amendment (Flood Planning) Order 2021
                </span>{' '}
                replaced the old map-referencing flood clauses in LEPs with
                generic clauses 5.21 and 5.22. Instead of pointing to a
                specific flood map, the new clauses reference a broader
                &ldquo;Flood Planning Area&rdquo; defined by council. The
                government framed this as modernisation. The practical effect:
                the statutory link between the LEP and a specific, publicly
                visible flood map was broken.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                November 2023: EPI flood area revocations
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The{' '}
                <span className="font-medium">
                  Environmental Planning Instrument (EPI) 2023-609
                </span>{' '}
                revoked most remaining EPI Flood Planning Areas from LEPs. The
                state-level EPI flood data layer &mdash; the dataset the NSW
                Planning Portal used to show flood status &mdash; now returns no
                data for many addresses where it previously showed flood
                information. The data was not corrected or updated. It was
                removed.
              </p>
            </div>
          </div>

          <p className="text-slate-700 leading-relaxed">
            A s10.7 certificate issued today may show{' '}
            <span className="font-medium">less</span> flood information than
            one issued for the same property in 2019. The absence of flood data
            on the certificate is not evidence that the property has no flood
            risk. It may simply mean the data is no longer there.
          </p>
        </section>

        {/* ========== SECTION 4: DEEP CONTEXT (why data is missing) ========== */}
        <section id="why-data-missing" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Why flood data is missing from many councils
          </h2>
          <p className="text-slate-700 leading-relaxed">
            There is no single source of truth for flood risk in NSW. Flood data
            is fragmented across at least five systems, none of which talk to
            each other:
          </p>
          <ul className="space-y-2 text-slate-700 leading-relaxed list-disc list-inside">
            <li>
              <span className="font-medium">LEP flood overlays</span> &mdash;
              now partly revoked
            </li>
            <li>
              <span className="font-medium">Council flood studies</span>{' '}
              &mdash; detailed modelling, but often not publicly accessible
            </li>
            <li>
              <span className="font-medium">SES Flood Data Portal</span>{' '}
              &mdash; patchy coverage, council-controlled uploads
            </li>
            <li>
              <span className="font-medium">State EPI flood layers</span>{' '}
              &mdash; only cover a fraction of NSW councils
            </li>
            <li>
              <span className="font-medium">Insurer flood models</span> &mdash;
              private, not shared with consumers
            </li>
          </ul>

          <h3 className="text-lg font-semibold text-slate-900 mt-6">
            The copyright problem nobody talks about
          </h3>
          <p className="text-slate-700 leading-relaxed">
            Many councils commissioned engineering consultants to produce flood
            studies. Under the{' '}
            <span className="font-medium">Copyright Act 1968 (Cth)</span>,
            unless copyright was explicitly assigned in the contract,
            consultant-created works are owned by the consultant &mdash; not the
            council that paid for them.
          </p>
          <p className="text-slate-700 leading-relaxed">
            The result: councils that spent hundreds of thousands of dollars on
            flood modelling cannot legally share the spatial data with the
            public. Some councils have stated this explicitly when asked. The
            data exists. It is locked behind a copyright wall.
          </p>
          <p className="text-slate-700 leading-relaxed">
            This is a structural problem, not an oversight. The most detailed
            flood information for your property may exist in a consultant&apos;s
            archive and never appear on any publicly available map or
            certificate.
          </p>
        </section>

        {/* ========== SECTION 5: DETAIL (council differences) ========== */}
        <section id="council-differences" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Council-by-council differences
          </h2>
          <p className="text-slate-700 leading-relaxed">
            Flood data availability varies dramatically across NSW. The
            state-level EPI flood layer only covers a handful of councils. The
            rest rely on their own flood studies, which may or may not be
            published.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse mt-2">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 pr-4 font-semibold text-slate-900">
                    Data situation
                  </th>
                  <th className="text-left py-3 font-semibold text-slate-900">
                    Example councils
                  </th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4">
                    Detailed flood study data publicly accessible via council
                    GIS
                  </td>
                  <td className="py-3">
                    Byron, Tweed, Port Macquarie-Hastings
                  </td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4">
                    Data on state EPI layer (limited)
                  </td>
                  <td className="py-3">Wollongong, Wingecarribee</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-3 pr-4">
                    Partial data on SES Flood Portal (may require login)
                  </td>
                  <td className="py-3">Penrith, Campbelltown</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4">
                    No publicly accessible digital flood data
                  </td>
                  <td className="py-3">
                    Many regional LGAs, including some of the most
                    flood-affected areas in NSW
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-slate-700 leading-relaxed">
            The irony is hard to miss. Some of the most flood-affected areas in
            NSW &mdash; places that have made national headlines &mdash; have
            the least accessible flood data for property buyers. The{' '}
            <Link
              href="/flood-risk/hawkesbury"
              className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
            >
              Hawkesbury
            </Link>{' '}
            experienced two major floods within three years (2021 and 2022), yet
            the state EPI layer returns nothing for most addresses in the
            valley.
          </p>
        </section>

        {/* ========== SECTION 6: FUTURE (what's coming) ========== */}
        <section id="whats-coming" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            What&apos;s coming: the CC&NH SEPP and mandatory climate reporting
          </h2>
          <p className="text-slate-700 leading-relaxed">
            The NSW Government has acknowledged the flood data transparency
            problem, at least in part. Two regulatory changes are in progress:
          </p>

          <div className="space-y-4 mt-2">
            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Climate Change and Natural Hazards SEPP
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Exhibited between 17 February and 16 March 2026, the CC&NH SEPP
                will replace SEPP (Resilience & Hazards) 2021. It proposes
                centralising flood provisions from individual LEPs into a single
                state instrument, prescribing NARCliM 2.0 climate scenarios, and
                introducing all-hazards assessment covering flood, bushfire,
                coastal erosion, and urban heat. Expected to commence late 2026
                or 2027.
              </p>
              <p className="text-slate-700 leading-relaxed mt-2">
                If implemented as exhibited, this would re-establish a
                consistent state-level flood framework &mdash; addressing part
                of the fragmentation created by the 2021 and 2023 changes.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                AASB S2: mandatory climate-related financial disclosures
              </h3>
              <p className="text-slate-700 leading-relaxed">
                From 2025, large Australian companies must report climate risk
                under{' '}
                <Link
                  href="/blog/aasb-s2-property-climate-data"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  AASB S2
                </Link>
                , including address-level exposure to physical hazards like
                flooding. Group 1 entities (revenue over $500M) are reporting
                now. Group 2 ($200M+) starts from mid-2026. By 2029,
                approximately 10,000 entities will need property-level flood
                data for their portfolios.
              </p>
              <p className="text-slate-700 leading-relaxed mt-2">
                Banks are also required under{' '}
                <Link
                  href="/blog/apra-cpg-229-property-assessment"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  APRA CPG 229
                </Link>{' '}
                to assess address-level flood exposure across mortgage
                portfolios. The demand for granular flood data is growing from
                the institutional side, even as consumer-facing data has become
                harder to access.
              </p>
            </div>
          </div>
        </section>

        {/* ========== FAQ ========== */}
        <section id="faq" className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-900">
            Frequently asked questions
          </h2>

          {/* TODO: Add FAQPage JSON-LD schema via layout-level script */}

          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Does a clear s10.7 certificate mean my property has no flood
                risk?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                No. The certificate only tells you whether LEP flood-related
                development controls currently apply. After the 2021 and 2023
                changes, some properties with real flood exposure may show no
                flood controls because the underlying data layer was removed.
                Absence of data is not absence of risk.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Why was flood data removed from LEPs?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The Flood Prone Land Package (2021) replaced LEP-specific flood
                maps with generic clauses 5.21 and 5.22. The EPI 2023-609 then
                revoked most remaining flood planning areas. The stated purpose
                was to let councils update mapping without amending the LEP. The
                practical effect was less flood information on certificates.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Where can I find detailed flood data for my property?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The SES Flood Data Portal (flooddata.ses.nsw.gov.au) hosts
                flood extent layers for some councils. Your council&apos;s
                website may have flood study maps. For depth and frequency data,
                see our guide on{' '}
                <Link
                  href="/blog/is-my-house-in-a-flood-zone-nsw"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  how to check if your house is in a flood zone in NSW
                </Link>
                .
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Can I rely on the s10.7 for conveyancing due diligence?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The certificate is a legal requirement, but it provides only
                binary flood status. Conveyancers and buyers increasingly need
                to go beyond the certificate &mdash; checking flood study data,
                insurance quotes, and overland flow exposure &mdash; to
                understand actual flood risk.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                Will the new CC&NH SEPP fix this?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                The Climate Change and Natural Hazards SEPP proposes
                centralising flood provisions into one state instrument. If
                implemented as exhibited, it would re-establish a consistent
                framework. But the underlying data access problem &mdash;
                consultant copyright over flood studies &mdash; would remain.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                How does flood risk affect property insurance?
              </h3>
              <p className="text-slate-700 leading-relaxed">
                Insurers use proprietary flood models not available to
                consumers. Properties in flood areas typically face
                $1,000&ndash;$5,000 higher annual premiums. According to
                APRA&apos;s March 2026 assessment, 1 in 4 Australian households
                could be{' '}
                <Link
                  href="/blog/uninsurable-property-climate-risk"
                  className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
                >
                  uninsurable by 2050
                </Link>{' '}
                due to rising climate risk costs.
              </p>
            </div>
          </div>
        </section>

        <BlogDisclaimer />

        {/* CTA */}
        <section className="mt-4 space-y-6">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              See what your Section 10.7 certificate does not show
            </h2>
            <p className="text-slate-600 mb-4 leading-relaxed">
              PlotDetect&apos;s free Flood Screening shows modelled flood depth
              at multiple return intervals &mdash; not just the binary yes/no
              from the planning certificate. Enter any NSW address for instant
              results. No account required.
            </p>
            <TrackedLink
              href="/reports/flood"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-500 transition-colors"
              page="section-10-7-flood-risk-nsw"
              cta="check_flood"
            >
              Check flood risk &mdash; free
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
