import type { Metadata } from 'next';
import Link from 'next/link';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { BlogPostingJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title:
    'How We Validate Property Data Before It Reaches You — PlotDetect',
  description:
    'Every property screening result on PlotDetect goes through a 5-pass validation process — data source verification, algorithm checks, edge case hardening, connection safety, and output defensibility. Here is exactly how it works.',
  keywords: [
    'property data validation',
    'data provenance property',
    'NSW planning data accuracy',
    'property screening methodology',
    'satellite data validation',
    'flood data verification NSW',
    'solar yield data accuracy',
    'property report quality assurance',
  ],
};

/* ------------------------------------------------------------------ */
/*  Visual: 5-pass validation pipeline                                 */
/* ------------------------------------------------------------------ */

function ValidationPipeline() {
  const passes = [
    {
      number: 1,
      name: 'Data source verification',
      question: 'Are we querying the right source, with the right parameters?',
      detail: 'Every external data source — government APIs, satellite imagery providers, spatial databases — is traced from endpoint URL to the value that appears in your report. Newly generated reports record which sources were queried, with parameters and timestamps. This pass is what caught the problem described below, and it did not catch all of it first time: see the August 2026 update.',
    },
    {
      number: 2,
      name: 'Algorithm correctness',
      question: 'Does the logic produce the right answer for known inputs?',
      detail: 'Scoring algorithms, signal computations, and derived fields are checked against expected outputs. Test suites cover normal cases, boundary conditions, and adversarial inputs — around 5,000 automated tests across the platform. Note what this does and does not show: a test proves the code does what we expect, not that what we expect matches the physical world. Only one of our tools has been compared against an independent external reference.',
    },
    {
      number: 3,
      name: 'Null and edge case hardening',
      question: 'What happens when data is missing, malformed, or unexpected?',
      detail: 'Government APIs return null fields, empty arrays, and unexpected formats more often than you would think. Every field that comes from an external source is null-checked before use, and missing data is intended to produce a clear "unavailable" indicator rather than a result. In August 2026 we found three cases where that intent was not met and a failure was rendered as a negative finding — see the update below.',
    },
    {
      number: 4,
      name: 'Connection and resource safety',
      question: 'Are database connections and API handles properly released?',
      detail: 'A leaked database connection under load can take down an entire service. Every connection follows a strict open-try-finally-close pattern. External API calls have timeouts. Long-running queries have statement-level time limits.',
    },
    {
      number: 5,
      name: 'Output defensibility',
      question: 'Does the language in the report stay within what the data supports?',
      detail: 'Every word of user-facing text is audited against a substitution ruleset. "Qualifies" becomes "meets criteria based on data sources checked". "Risk assessment" becomes "screening". No statement crosses the line from factual information into advice, recommendation, or assurance.',
    },
  ];

  return (
    <div className="my-8 space-y-4">
      {passes.map((pass) => (
        <div key={pass.number} className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="shrink-0 w-7 h-7 rounded-full bg-teal-100 text-teal-700 text-xs font-bold flex items-center justify-center">
              {pass.number}
            </span>
            <h3 className="font-semibold text-slate-900 text-sm">{pass.name}</h3>
          </div>
          <p className="text-sm font-medium text-slate-600 mb-1 ml-10">{pass.question}</p>
          <p className="text-sm text-slate-500 leading-relaxed ml-10">{pass.detail}</p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Visual: audit trail itemised checks                                */
/* ------------------------------------------------------------------ */

function AuditTrailChecks() {
  const checks = [
    {
      check: 'Every data source queried',
      recorded: 'Source name, endpoint URL, query parameters',
      proves: 'Which government APIs and datasets were actually consulted for this specific address',
    },
    {
      check: 'Query timestamp',
      recorded: 'UTC timestamp for each data source query',
      proves: 'Exactly when each source was checked — not a cached result from weeks ago',
    },
    {
      check: 'Response time',
      recorded: 'Milliseconds from request to response for each source',
      proves: 'The query actually executed (not a timeout or silent failure)',
    },
    {
      check: 'Response hash',
      recorded: 'SHA-256 cryptographic hash of each API response body',
      proves: 'The raw data has not been altered after receipt — tamper-evident',
    },
    {
      check: 'Features returned',
      recorded: 'Count of records/features returned by each source',
      proves: 'Whether the source returned data or came back empty for this location',
    },
    {
      check: 'Error tracking',
      recorded: 'Error message and stack trace if a source query failed',
      proves: 'Failures are recorded, not silently swallowed — you see what was not available',
    },
    {
      check: 'Pipeline version',
      recorded: 'Git commit SHA of the deployed code',
      proves: 'Which exact version of the analysis logic produced the result',
    },
    {
      check: 'Disclaimer version',
      recorded: 'Version ID of the disclaimer active at report generation time',
      proves: 'What the user was told about limitations when they received the report',
    },
  ];

  return (
    <div className="not-prose my-8 grid gap-3 sm:grid-cols-2">
      {checks.map((c) => (
        <div key={c.check} className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="shrink-0 w-5 h-5 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center text-xs font-bold">
              &#10003;
            </span>
            <p className="text-sm font-semibold text-slate-900">{c.check}</p>
          </div>
          <p className="text-xs text-slate-500 mb-1"><span className="font-medium text-slate-600">Recorded:</span> {c.recorded}</p>
          <p className="text-xs text-slate-500"><span className="font-medium text-slate-600">Proves:</span> {c.proves}</p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Visual: bug pattern summary                                        */
/* ------------------------------------------------------------------ */

function RecurringPatterns() {
  const patterns = [
    {
      name: 'False data source attribution',
      description: 'Reports listing data sources the pipeline did not actually query. Found across 5 of 7 pipelines in May 2026 — and found again, in a form the May fix did not reach, in August 2026.',
      fix: 'Newly generated reports record the sources actually queried, with parameters, timestamps and a response hash. This did not reach reports already sitting in the cache: see the August 2026 update.',
    },
    {
      name: 'Connection leaks',
      description: 'Database connections closed inside the success path but not on the error path — meaning an API failure would leak a connection.',
      fix: 'All connections now follow an open-try-finally-close pattern. Connections are released regardless of whether the query succeeds or fails.',
    },
    {
      name: 'Liability-creating language',
      description: 'Words like "qualifies", "passes all checks", "risk assessment", and "will require" that imply a formal professional determination.',
      fix: 'Systematic replacement with factual alternatives: "meets criteria", "meets", "screening", "may require". Automated grep patterns enforce this in code review.',
    },
  ];

  return (
    <div className="my-8 rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-5">
        Recurring patterns found across all pipelines
      </p>
      <div className="space-y-5">
        {patterns.map((p) => (
          <div key={p.name}>
            <p className="text-sm font-semibold text-slate-900">{p.name}</p>
            <p className="text-sm text-slate-500 mt-1">{p.description}</p>
            <p className="text-sm text-teal-700 mt-1"><span className="font-medium">Fix:</span> {p.fix}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function HowWeValidatePage() {
  return (
    <article className="prose prose-slate max-w-none">
      <BlogPostingJsonLd
        title="How we validate property data before it reaches you"
        description="Every property screening result goes through a 5-pass validation: data source verification, algorithm checks, edge case hardening, connection safety, and output defensibility."
        slug="how-we-validate-property-data-nsw"
        date="2026-05-21"
      />
      {/* ---- Lead (inverted pyramid: most important info first) ---- */}
      <p className="text-lg text-slate-700 leading-relaxed">
        Every property screening result on this platform goes through a 5-pass
        validation process before it reaches you. Across 7 pipelines and tens of
        thousands of lines of code, this process has found and fixed 40 bugs —
        including false data source attributions, database connection leaks, and
        language that overstated what the data could support.
      </p>

      <p className="text-base text-slate-600">
        This page explains what those 5 passes are, why they matter for property
        data specifically, and what we found when we applied them.
      </p>

      {/* ---- Why this matters ---- */}
      <h2>Why property data needs more than unit tests</h2>

      <p>
        Property screening tools sit in a specific legal position under Australian
        law. Under the{' '}
        <a href="https://www.legislation.gov.au/Details/C2014C00004" target="_blank" rel="noopener noreferrer">
          Australian Consumer Law
        </a>{' '}
        (section 18), conduct that is misleading or deceptive — or likely to mislead
        or deceive — is prohibited. Under the principle established in{' '}
        <em>Shaddock &amp; Associates Pty Ltd v Parramatta City Council</em>{' '}
        (1981), a party that provides information knowing it will be relied upon
        owes a duty of care in how that information is presented.
      </p>

      <p>
        What this means in practice: if a property screening report says a lot
        &ldquo;qualifies&rdquo; for a secondary dwelling, and the buyer relies on
        that to purchase, and it turns out the data was wrong or the language
        overstated, there is a liability chain. Unit tests catch code bugs.
        They do not catch false data attributions, misleading language, or
        silent failures where wrong data is served without any error.
      </p>

      <p>
        The 5-pass framework addresses all of these.
      </p>

      {/* ---- The 5 passes ---- */}
      <h2>The 5-pass validation framework</h2>

      <ValidationPipeline />

      {/* ---- What we found ---- */}
      <h2>What we found</h2>

      <p>
        When we applied this framework systematically across all 7 property
        screening pipelines, we found 40 bugs. None of them would have been
        caught by standard unit tests alone.
      </p>

      <RecurringPatterns />

      <p>
        The single most common issue was <strong>false data source attribution</strong> —
        PDF reports claiming data came from a source that the pipeline never
        actually queried. This is exactly the kind of issue that creates legal
        exposure: a user sees &ldquo;source: NSW Building Footprints&rdquo; in their
        report, assumes the data came from that dataset, and makes a decision
        based on that assumption. In reality, the data came from a different
        source entirely.
      </p>

      {/* ---- August 2026 correction ---- */}
      <h2>Update, August 2026: what this page got wrong</h2>

      <div className="not-prose my-6 rounded-2xl border border-amber-200 bg-amber-50/60 p-6">
        <p className="text-sm text-slate-700 leading-relaxed">
          When this page was published in May 2026 it made several promises in
          absolute terms — that a listed source had always been queried, and that
          missing data would <em>never</em> read as a result. In August 2026 we ran
          a deeper review of our own outputs and found that those promises were
          stronger than the evidence behind them. Rather than quietly soften the
          wording, here is what we found.
        </p>
      </div>

      <ul>
        <li>
          <strong>Cached reports kept naming a source we never queried.</strong>{' '}
          The May fix corrected how new reports record their sources, but reports
          already stored in the cache kept their original text. We found 143 flood
          screening results still naming a satellite source the code had stopped
          using, 131 of them recent enough to still be served. The original claim
          — &ldquo;if a source is listed, it was queried&rdquo; — was true of the
          code path and false of the cache.
        </li>
        <li>
          <strong>A failed calculation was displayed as a negative finding.</strong>{' '}
          In shadow analysis, a geometry failure and a genuine &ldquo;no
          overshadowing&rdquo; result returned the same value, so a crash could be
          shown as 0% overshadowed. This is exactly the false &ldquo;all
          clear&rdquo; this page said could not happen. It is fixed: the three
          outcomes — a real result, no result, and a failure — are now distinct,
          and a failure renders as an explicit &ldquo;not assessed&rdquo;.
        </li>
        <li>
          <strong>A confidence label was shown for a scan that produced nothing.</strong>{' '}
          Secondary dwelling reports could display &ldquo;high confidence&rdquo;
          where the imagery scan had returned no result at all. The confidence
          grade has been removed entirely and replaced with plain statements of
          what actually happened — for example &ldquo;scan ran, nothing found&rdquo;
          or &ldquo;not assessed&rdquo;.
        </li>
        <li>
          <strong>A feature reported a result it had never once produced.</strong>{' '}
          A surface-change check on neighbouring land returned no usable reading in
          any of 538 attempts, while every one of those reports still displayed a
          confident negative. The check has been removed from the product rather
          than repaired, because at the resolution of the imagery involved it could
          not have answered the question reliably even when working.
        </li>
        <li>
          <strong>We named a calculation method we were not using.</strong>{' '}
          Our disclaimer and marketing named a specific astronomical library as our
          shadow method. The running code used a different one. The wording now
          describes what the code actually does. Separately, the calculation itself
          was then tested against an independent model and passed — the method claim
          was wrong, the maths was not.
        </li>
      </ul>

      <p>
        Two things are worth saying plainly about that list. First, most of these
        are <em>description</em> failures rather than calculation failures — the
        numbers were largely right and the words around them were not. Second, the
        checks described on this page are what surfaced them, but only once we
        went looking specifically for claims that could not be supported. A
        validation process that runs green is evidence that the checks passed, not
        proof that the output is true.
      </p>

      {/* ---- Audit trail ---- */}
      <h2>What every report records</h2>

      <p>
        Every report generated on this platform creates an append-only audit
        trail record. Here is exactly what is captured:
      </p>

      <AuditTrailChecks />

      <p>
        If a data source is later questioned — &ldquo;did you actually check
        the flood overlay for this address?&rdquo; — we can show which source was
        queried, with what parameters, and when. <strong>What we cannot do is
        reproduce the response body.</strong> We store a cryptographic hash of it,
        not the response itself, so the record can confirm that a copy of the
        response you already hold is unaltered, but it cannot recreate one from
        nothing. That is a real limit of this audit trail and it is worth stating
        rather than implying otherwise.
      </p>

      {/* ---- Disclaimer architecture ---- */}
      <h2>Versioned disclaimers</h2>

      <p>
        Each product has its own disclaimer text, stored in a versioned database
        table. Disclaimers are never deleted — when the text changes, a new
        version is inserted and the old version is marked as superseded. Every
        audit trail record captures which disclaimer version was active when the
        report was generated.
      </p>

      <p>
        This matters because the legal question is not &ldquo;what does the
        disclaimer say today?&rdquo; — it is &ldquo;what did the user see when
        they received their report?&rdquo; Versioned disclaimers answer that
        question definitively.
      </p>

      {/* ---- Ongoing monitoring ---- */}
      <h2>Ongoing data source monitoring</h2>

      <p>
        Government APIs go down, change their schema, or return stale data without
        warning. An automated monitor probes external data sources — 15 of them at
        the last run — and records the result. Each probe checks:
      </p>

      <ul>
        <li>Is the endpoint reachable?</li>
        <li>Does the response match the expected format?</li>
        <li>Has the response structure changed since the last check?</li>
        <li>Is the response time within acceptable limits?</li>
      </ul>

      <p>
        <strong>Honest note on cadence, August 2026:</strong> this page previously
        described the monitor as running daily and said we would know about a
        failure within 24 hours. Checking the actual run history, it does not run
        every day — at the time of writing the most recent round was five days old.
        The monitor is real and its results are recorded; the
        24-hour promise was not something the schedule supported, so it has been
        removed rather than restated. Putting it on a dependable schedule is
        outstanding work, not a solved problem.
      </p>

      <p>
        The same daily check also looks for two types of silent failure that
        are harder to catch:
      </p>

      <ul>
        <li>
          <strong>Missing audit trails</strong> — if a report was generated
          but the audit record was not written, the gap is flagged. A report
          without an audit trail cannot be defended if questioned.
        </li>
        <li>
          <strong>Empty or incomplete outputs</strong> — if a screening tool
          ran but produced no results, no confidence rating, or recorded no
          data sources, it is flagged. This catches the case where a tool
          appears to succeed but actually returned nothing useful.
        </li>
      </ul>

      <p>
        This is not a one-off validation — it runs every day, automatically.
        The results are recorded so we can show, for any given day, which
        sources were checked and what their status was.
      </p>

      {/* ---- What this means for you ---- */}
      <h2>What this means for you</h2>

      <p>
        When you receive a property screening report from this platform:
      </p>

      <ul>
        <li>
          The sources listed are recorded at the time the report runs, with
          their parameters and timestamps — not copied from a template
        </li>
        <li>
          Missing data is intended to read as &ldquo;unavailable&rdquo; rather
          than as a result. We have found and fixed cases where it did not, and
          we cannot promise there are none left
        </li>
        <li>
          The language describes what the data shows — it does not make
          compliance determinations, recommendations, or assurances
        </li>
        <li>
          An audit record exists for the report, linking the output to the data
          that produced it
        </li>
        <li>
          <strong>What has and has not been checked against the real world:</strong>{' '}
          our shadow calculations have been compared against an independent
          astronomical model and agreed to within 0.21 degrees. No other tool
          here has been compared against an external reference. That is a
          statement of fact about our evidence, not a claim that the others are
          wrong
        </li>
      </ul>

      <p>
        These are screening tools, not formal planning certificates. They are
        designed to surface the right questions early — before you are committed
        — so you can get qualified professional advice where it matters.
      </p>

      <div className="not-prose mt-8 flex flex-col sm:flex-row gap-3">
        <Link
          href="/how-it-works"
          className="inline-flex items-center justify-center px-5 py-2.5 rounded-lg bg-teal-600 text-white text-sm font-medium hover:bg-teal-700 transition-colors"
        >
          See data sources per tool
        </Link>
      </div>

      <BlogDisclaimer />
    </article>
  );
}
