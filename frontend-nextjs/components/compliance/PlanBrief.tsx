'use client';

// prior-art-checked: YourProjectSummary shows proven figures only and says "not found" for an empty row; DcpMayApplyBlock
// lists withheld areas. No component showed the plan's own best clauses for an empty row.

/**
 * PlanBrief — under the "Your project" table: for each row WITHOUT a proven figure, the plan's own best clauses
 * (up to 3, "show more" to 5), the council's words and the page. Indicative only; the full plan stays one click away.
 * Pure view + a connected wrapper; the wrapper renders nothing while the API flag is off.
 */

import React, { useState } from 'react';
import useSWR from 'swr';
import {
  BRIEF_EMPTY_TEXT, BRIEF_FIRST_SHOWN, BRIEF_NOTE, BRIEF_TAG_APPLIES, BRIEF_TAG_MAY,
  shapeBriefRows, tableRows, BRIEF_TEXT_LIMIT, type BriefItem, type BriefRow, type StoredBriefRow,
} from '@/lib/plan-brief';

function TextView({ text }: { text: string }) {
  const rows = tableRows(text);
  if (rows) {
    return (
      <div className="overflow-x-auto" data-testid="brief-table">
        <table className="text-xs text-slate-800 border-collapse">
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-slate-200 first:border-t-0">
                {r.map((c, j) => <td key={j} className="pr-3 py-0.5 align-top break-words">{c}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return <p className="text-sm text-slate-800 break-words whitespace-pre-line">{text}{text.length >= BRIEF_TEXT_LIMIT ? '…' : ''}</p>;
}

function ItemView({ item }: { item: BriefItem }) {
  const place = [item.clauseLabel ? `clause ${item.clauseLabel}` : null, item.page ? `page ${item.pageLabel || item.page}` : null].filter(Boolean).join(', ');
  return (
    <li className="py-2 border-t border-slate-100 first:border-t-0" data-testid="brief-item">
      <TextView text={item.text} />
      {item.continues && item.continues.length > 0 && (
        <div className="mt-1 border-l-2 border-slate-200 pl-2 text-xs text-slate-600 space-y-1" data-testid="brief-continues">
          {item.continues.map((c, i) => <TextView key={i} text={c} />)}
        </div>
      )}
      <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span className={`rounded px-1.5 py-0.5 font-medium ${item.verdict === 'APPLIES' ? 'bg-teal-50 text-teal-800' : 'bg-amber-50 text-amber-800'}`} data-testid="brief-tag">
          {item.verdict === 'APPLIES' ? BRIEF_TAG_APPLIES : BRIEF_TAG_MAY}
        </span>
        {place && (item.url
          ? <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-teal-700 hover:underline" data-testid="brief-place">{place}{item.urlPage ? ' · open the plan at this page' : ' · open the plan'}</a>
          : <span data-testid="brief-place">{place}</span>)}
      </p>
    </li>
  );
}

function RowView({ row, planUrl }: { row: BriefRow; planUrl?: string | null }) {
  const [more, setMore] = useState(false);
  const first = row.items.slice(0, BRIEF_FIRST_SHOWN);
  const rest = row.items.slice(BRIEF_FIRST_SHOWN);
  return (
    <section className="rounded border border-slate-200 bg-white p-3" data-testid={`brief-row-${row.key}`}>
      <h4 className="text-sm font-semibold text-slate-900">{row.label}</h4>
      {row.items.length === 0 ? (
        <p className="mt-1 text-xs text-slate-500" data-testid="brief-empty">
          {BRIEF_EMPTY_TEXT}
          {planUrl && <>{' '}<a href={planUrl} target="_blank" rel="noopener noreferrer" className="text-teal-700 hover:underline">Open the plan</a></>}
        </p>
      ) : (
        <>
          <ul>{first.map((it) => <ItemView key={it.id} item={it} />)}</ul>
          {rest.length > 0 && (
            <>
              {more && <ul>{rest.map((it) => <ItemView key={it.id} item={it} />)}</ul>}
              <button type="button" onClick={() => setMore(!more)} aria-expanded={more}
                className="mt-1 text-xs font-semibold text-teal-700 hover:underline" data-testid="brief-more">
                {more ? 'Show fewer' : `Show ${rest.length} more`}
              </button>
            </>
          )}
        </>
      )}
    </section>
  );
}

export interface PlanBriefViewProps { rows: BriefRow[]; planUrl?: string | null }

export function PlanBriefView({ rows, planUrl }: PlanBriefViewProps) {
  if (rows.length === 0) return null;
  return (
    <div className="space-y-2" data-testid="plan-brief">
      <h3 className="text-sm font-semibold text-slate-900">From the plan (indicative)</h3>
      <p className="text-xs text-slate-600" data-testid="brief-note">{BRIEF_NOTE}</p>
      {rows.map((r) => <RowView key={r.key} row={r} planUrl={planUrl} />)}
    </div>
  );
}

interface BriefPayload { enabled: boolean; rows: StoredBriefRow[] }
const fetcher = async (url: string): Promise<BriefPayload> => {
  const res = await fetch(url);
  if (!res.ok) throw new Error('brief unavailable');
  return res.json();
};

export interface PlanBriefProps {
  council: string;
  devType: string | null;
  zone?: string | null;
  /** Row keys (front, side, rear, coverage, landscape, pos, parking, ...) that already have a proven figure. */
  provenKeys: ReadonlySet<string>;
  planUrl?: string | null;
}

export function PlanBrief({ council, devType, zone, provenKeys, planUrl }: PlanBriefProps) {
  const url = council && devType
    ? `/api/brief/for-property?council=${encodeURIComponent(council)}&dev_type=${encodeURIComponent(devType)}${zone ? `&zone=${encodeURIComponent(zone)}` : ''}`
    : null;
  const { data } = useSWR<BriefPayload>(url, fetcher, { revalidateOnFocus: false });
  if (!data?.enabled || !data.rows.length) return null;          // off, failed, or nothing built for this council: show nothing
  return <PlanBriefView rows={shapeBriefRows(data.rows, provenKeys)} planUrl={planUrl} />;
}
