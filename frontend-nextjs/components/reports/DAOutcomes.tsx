'use client';

// prior-art-checked: extracted verbatim from app/reports/intelligence-brief/page.tsx
// (DAOutcomesDisplay + the da_refusal_stats sentence) so the window-honesty
// rewrite is jest-testable; page.tsx now imports from here.

// Determined DA outcomes near the lot + LGA determination counts, from the NSW
// DA tracking layer. That layer is a point-in-time extract (frozen at 2023-04
// as of 2026-07), so every sentence here states the window the data actually
// covers — derived from the payload (`window_start`/`window_end`/`data_currency`),
// NEVER "last N years" arithmetic from `years_back`/`period_years`. If the
// window fields are absent, the temporal claim is suppressed, not defaulted.

export interface DAOutcomeRowFE {
  planning_portal_number?: string; da_number?: string | null; status?: string;
  outcome?: string | null; dev_type?: string | null; cost?: string | null;
  address?: string; lodgement_date?: string | null; determined_date?: string | null;
}
export interface DAOutcomesPayload {
  outcomes?: DAOutcomeRowFE[]; radius_m?: number; years_back?: number;
  data_currency?: string | null; window_start?: string | null; window_end?: string | null;
}
export interface RefusalStatsRow {
  lga?: string; period_years?: number; total_determined?: number;
  approved?: number; refused?: number; deferred_commencement?: number; refusal_rate?: number | null;
  data_currency?: string | null; window_start?: string | null;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

/** "2023-04-29" → "April 2023". Returns null for anything not YYYY-MM-DD. */
export function formatMonthYear(iso: string | null | undefined): string | null {
  if (!iso || typeof iso !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
  const month = Number(iso?.slice(5, 7));
  if (month < 1 || month > 12) return null;
  return `${MONTH_NAMES[month - 1]} ${iso?.slice(0, 4)}`;
}

/** " lodged between March 2019 and February 2023" — or '' when either end is
 * missing/unparseable, so no temporal claim is rendered without data. */
function lodgedWindowPhrase(start: string | null | undefined, end: string | null | undefined): string {
  const s = formatMonthYear(start);
  const e = formatMonthYear(end);
  if (!s || !e) return '';
  if (s === e) return ` lodged in ${s}`;
  return ` lodged between ${s} and ${e}`;
}

/** The coverage-extent note; null when the payload carries no currency value. */
function extentNote(dataCurrency: string | null | undefined): string | null {
  const c = formatMonthYear(dataCurrency);
  return c ? `The published tracking data extends to applications lodged up to ${c}.` : null;
}

const DA_OUTCOMES_PREVIEW_COUNT = 6;

function daOutcomeRow(d: DAOutcomeRowFE, i: number, formatLabel: (s: string) => string) {
  const costNum = d.cost != null && d.cost !== '' ? Number(d.cost) : null;
  return (
    <tr key={d.planning_portal_number ?? i} className="border-t border-slate-100 align-top">
      <td className="py-1 pr-3 text-slate-700">
        {d.dev_type ? formatLabel(String(d.dev_type)) : (d.da_number ?? d.planning_portal_number ?? '—')}
        {d.address ? <span className="block text-[11px] text-slate-400">{d.address}</span> : null}
      </td>
      <td className="py-1 pr-3">
        {d.outcome
          ? <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium ring-1 ${d.outcome === 'Refused' ? 'bg-amber-50 text-amber-700 ring-amber-200' : 'bg-slate-50 text-slate-600 ring-slate-200'}`}>{d.outcome}</span>
          : <span className="text-slate-400 text-xs">{d.status ?? '—'}</span>}
      </td>
      <td className="py-1 pr-3 tabular-nums text-slate-700">{costNum != null && Number.isFinite(costNum) ? `$${Math.round(costNum).toLocaleString()}` : '—'}</td>
      <td className="py-1 tabular-nums text-slate-500">{d.determined_date ?? d.lodgement_date ?? '—'}</td>
    </tr>
  );
}

export function DAOutcomesDisplay({ data, formatLabel }: { data: DAOutcomesPayload; formatLabel: (s: string) => string }) {
  const rows = data.outcomes ?? [];
  const radius = data.radius_m ?? 200;
  const extent = extentNote(data.data_currency);
  if (rows.length === 0) {
    return (
      <span className="text-sm text-slate-500">
        No applications with a determination within {radius} m appear in the published tracking data.
        {extent ? ` ${extent}` : ''}
      </span>
    );
  }
  const sorted = [...rows].sort((a, b) => String(b.determined_date ?? b.lodgement_date ?? '').localeCompare(String(a.determined_date ?? a.lodgement_date ?? '')));
  const preview = sorted.slice(0, DA_OUTCOMES_PREVIEW_COUNT);
  const rest = sorted.slice(DA_OUTCOMES_PREVIEW_COUNT);
  const refused = rows.filter((r) => r.outcome === 'Refused').length;
  const determined = rows.filter((r) => r.outcome != null).length;
  return (
    <div>
      <p className="text-sm text-slate-700 mb-1.5">
        {rows.length.toLocaleString()} application{rows.length === 1 ? '' : 's'} within {radius} m
        {lodgedWindowPhrase(data.window_start, data.window_end)}
        {determined > 0 ? <> — {determined.toLocaleString()} with a recorded result ({refused.toLocaleString()} refused)</> : null}.
      </p>
      {extent ? <p className="text-xs text-slate-500 mb-1.5">{extent}</p> : null}
      <table className="w-full text-[13px]">
        <thead>
          <tr className="text-xs text-slate-500 text-left">
            <th className="font-medium pb-1 pr-3">Application</th>
            <th className="font-medium pb-1 pr-3">Result</th>
            <th className="font-medium pb-1 pr-3">Stated cost</th>
            <th className="font-medium pb-1">Determined</th>
          </tr>
        </thead>
        <tbody>{preview.map((d, i) => daOutcomeRow(d, i, formatLabel))}</tbody>
      </table>
      {rest.length > 0 && (
        <details className="mt-1">
          <summary className="cursor-pointer select-none text-xs text-slate-500">Show {rest.length} more applications</summary>
          <table className="w-full text-[13px] mt-1"><tbody>{rest.map((d, i) => daOutcomeRow(d, i, formatLabel))}</tbody></table>
        </details>
      )}
    </div>
  );
}

export function RefusalStatsSentence({ stats, formatLabel }: { stats: RefusalStatsRow; formatLabel: (s: string) => string }) {
  const granted: number | null = stats.approved ?? null;
  const windowStart = formatMonthYear(stats.window_start);
  const windowEnd = formatMonthYear(stats.data_currency);
  if (!windowStart || !windowEnd) {
    // No data-derived window: suppress the counts rather than serve them with
    // an undated (implied-current) framing — the defect this component fixes.
    return (
      <span className="text-sm text-slate-500">
        Determination counts are not shown — the data window of the tracking layer could not be established for this council.
      </span>
    );
  }
  return (
    <>
      Of {stats.total_determined?.toLocaleString()} applications determined in {formatLabel(String(stats.lga ?? 'this council'))},
      lodged between {windowStart} and {windowEnd} (the extent of the published tracking data):{' '}
      {granted?.toLocaleString()} granted development consent, {stats.refused?.toLocaleString()} refused
      {stats.deferred_commencement ? <>, {stats.deferred_commencement.toLocaleString()} deferred commencement</> : null}
      {stats.refusal_rate != null ? <> ({(stats.refusal_rate * 100).toFixed(1)}% refused)</> : null}.
    </>
  );
}
