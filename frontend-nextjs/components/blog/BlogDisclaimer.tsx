/**
 * Standard disclaimer for all blog posts.
 * Required on every published article — YMYL content under ACL s18.
 */
export function BlogDisclaimer() {
  return (
    <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-xs text-slate-500 leading-relaxed mt-10">
      This content is general information about NSW planning and property
      matters. It is not planning advice, legal advice, financial advice, or
      insurance advice, and should not be relied upon as a substitute for
      professional assessment. Planning controls and regulatory instruments
      change &mdash; verify current provisions at{' '}
      <a
        href="https://www.planning.nsw.gov.au"
        target="_blank"
        rel="noopener noreferrer"
        className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
      >
        planning.nsw.gov.au
      </a>{' '}
      and{' '}
      <a
        href="https://legislation.nsw.gov.au"
        target="_blank"
        rel="noopener noreferrer"
        className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
      >
        legislation.nsw.gov.au
      </a>
      .
    </div>
  );
}
