/**
 * Shared landing section for satellite product pages.
 * Renders above the tool component to build trust and explain features.
 * Deliberately does not name specific APIs, satellites, or data processing methods.
 */

interface CheckItem {
  title: string;
  description: string;
}

interface ComparisonRow {
  feature: string;
  free: boolean;
  paid: boolean;
}

interface ProductLandingProps {
  title: string;
  subtitle: string;
  /** Short paragraph below subtitle — the "why this matters" hook */
  hook: string;
  /** What the report checks — shown as a grid of cards */
  checks: CheckItem[];
  /** Free vs paid comparison rows */
  comparison: ComparisonRow[];
  paidLabel: string;
  /** Trust-building note about methodology — no source names */
  methodology: string;
  /** Optional note about coverage area */
  coverage?: string;
}

export function ProductLanding({
  title,
  subtitle,
  hook,
  checks,
  comparison,
  paidLabel,
  methodology,
  coverage,
}: ProductLandingProps) {
  return (
    <div className="mb-10">
      {/* Hero */}
      <h1 className="text-3xl font-bold text-gray-900 leading-tight">{title}</h1>
      <p className="mt-2 text-lg text-gray-600">{subtitle}</p>
      <p className="mt-3 text-sm text-gray-500 max-w-xl leading-relaxed">{hook}</p>

      {/* What we check */}
      <div className="mt-8">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">What this report checks</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {checks.map((c) => (
            <div key={c.title} className="rounded-lg border border-gray-100 bg-white p-4">
              <p className="text-sm font-medium text-gray-900">{c.title}</p>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">{c.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Free vs Paid */}
      <div className="mt-8">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">Free check vs {paidLabel}</h2>
        <div className="rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="px-4 py-2.5 text-xs font-medium text-gray-500">Feature</th>
                <th className="px-4 py-2.5 text-xs font-medium text-gray-500 text-center w-20">Free</th>
                <th className="px-4 py-2.5 text-xs font-medium text-teal-700 text-center w-20">Paid</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {comparison.map((row) => (
                <tr key={row.feature}>
                  <td className="px-4 py-2.5 text-gray-700">{row.feature}</td>
                  <td className="px-4 py-2.5 text-center">
                    {row.free ? (
                      <span className="text-teal-600 font-medium">Yes</span>
                    ) : (
                      <span className="text-gray-300">&mdash;</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {row.paid ? (
                      <span className="text-teal-600 font-medium">Yes</span>
                    ) : (
                      <span className="text-gray-300">&mdash;</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Methodology + Coverage */}
      <div className="mt-8 space-y-3">
        <div className="rounded-lg bg-gray-50 border border-gray-100 p-4">
          <p className="text-xs font-medium text-gray-500 mb-1">How it works</p>
          <p className="text-xs text-gray-500 leading-relaxed">{methodology}</p>
        </div>
        {coverage && (
          <div className="rounded-lg bg-gray-50 border border-gray-100 p-4">
            <p className="text-xs font-medium text-gray-500 mb-1">Coverage</p>
            <p className="text-xs text-gray-500 leading-relaxed">{coverage}</p>
          </div>
        )}
      </div>

      {/* Divider before tool */}
      <div className="border-t border-gray-200 mt-10 mb-8" />
    </div>
  );
}
