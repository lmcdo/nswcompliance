'use client';

// prior-art-checked: PathwaySummaryCard and the other *Summary* files are unrelated
// (pathway, water, ADG, prospector); no component shows LEP + DCP key controls in one
// table. DcpStructuredControls' helpers (formatValue, noNumberLabel, shortCitation) are reused.

/**
 * YourProjectSummary — a short table above the SEPP / LEP / DCP tabs.
 *
 * Every figure is passed through unchanged from an existing source (Planning Portal
 * constraints, /api/dcp/structured-controls). It holds no planning number of its own,
 * does not interpret the plan, and never fills a gap: a value that is not in our data
 * says so and links to the plan.
 */

import React, { useState } from 'react';
import useSWR from 'swr';
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';
import {
  DEFAULT_PROJECT_TYPE,
  resolveControlsDevType,
  setSharedProjectType,
  useSharedProjectTypeRaw,
} from '@/lib/project-type';
import {
  NOT_FOUND_TEXT,
  NO_CONTROLS_FOR_TYPE_TEXT,
  buildDcpRows,
  buildLepRows,
  buildSiteFlags,
  compareFigure,
  limitSentence,
  type ControlsPayload,
  type FlagConstraints,
  type LepInputs,
  type SummaryEntry,
  type SummaryRow,
} from '@/lib/project-summary';

const fetcher = async (url: string): Promise<ControlsPayload> => {
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch structured controls');
  return res.json();
};

// ── Pure view (props in, markup out; tested with fixtures) ───────────────────

export interface YourProjectSummaryViewProps {
  projectType: string;
  onProjectTypeChange: (value: string) => void;
  lepRows: SummaryRow[];
  /** null while loading. */
  dcpRows: SummaryRow[] | null;
  dcpLoadError?: boolean;
  /** True when the picked project type has no mapping to a controls type. */
  unmapped: boolean;
  flags: ReturnType<typeof buildSiteFlags>;
  defaultOpen?: boolean;
}

function EntryCells({ entry }: { entry: SummaryEntry }) {
  const place = [entry.document, entry.clause, entry.page ? `p. ${entry.page}` : null].filter(Boolean).join(', ');
  return (
    <>
      <td className="px-2 py-2 align-top font-mono text-sm text-slate-900" data-testid="figure">
        {entry.label && <span className="block text-xs font-sans text-slate-500">{entry.label}</span>}
        {entry.figure}
        {entry.condition && <span className="block text-xs font-sans text-slate-500" data-testid="condition">{entry.condition}</span>}
        {limitSentence(entry.limit) && <span className="block text-xs font-sans text-slate-500">{limitSentence(entry.limit)}</span>}
      </td>
      <td className="px-2 py-2 align-top text-xs text-slate-600" data-testid="source">
        {place && <span data-testid="place">{place}</span>}{' '}
        {entry.url ? (
          <a href={entry.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-teal-700 hover:underline" data-testid="link">
            {entry.citation}<ExternalLink className="w-2.5 h-2.5" aria-hidden />
          </a>
        ) : (
          <span className="text-slate-500" data-testid="no-link">{entry.citation}</span>
        )}
      </td>
      <td className="px-2 py-2 align-top text-xs text-slate-600">
        {entry.words ? (
          <details>
            <summary className="cursor-pointer text-slate-500">The plan&apos;s words</summary>
            <p className="mt-1 italic" data-testid="words">{entry.words}</p>
          </details>
        ) : (
          <span className="text-slate-400">Not in our data</span>
        )}
      </td>
    </>
  );
}

function YourProposal({ row }: { row: SummaryRow }) {
  const [value, setValue] = useState('');
  // One comparison per row, and only when the row holds exactly one entry with a single number.
  const entry = row.entries.length === 1 ? row.entries[0] : null;
  if (!entry || entry.number === null) {
    return <td className="px-2 py-2 align-top text-xs text-slate-400">No number to compare with</td>;
  }
  const result = compareFigure(entry.number, value);
  return (
    <td className="px-2 py-2 align-top text-xs">
      <label className="block">
        <span className="sr-only">{`Your proposal: ${row.label}${entry.unit ? ` (${entry.unit})` : ''}`}</span>
        <input
          type="text"
          inputMode="decimal"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={entry.unit ? `Your figure (${entry.unit})` : 'Your figure'}
          className="w-28 rounded border border-slate-300 px-1.5 py-1 text-sm"
          data-testid={`proposal-${row.key}`}
        />
      </label>
      {result.kind === 'result' && <p className="mt-1 text-slate-700" data-testid={`result-${row.key}`}>{result.text}</p>}
      {result.kind === 'invalid' && <p className="mt-1 text-slate-500">Enter a number.</p>}
    </td>
  );
}

function RowView({ row }: { row: SummaryRow }) {
  if (row.entries.length === 0) {
    return (
      <tr className="border-t border-slate-100" data-testid={`row-${row.key}`}>
        <th scope="row" className="px-2 py-2 align-top text-left text-sm font-medium text-slate-800">{row.label}</th>
        <td colSpan={4} className="px-2 py-2 text-xs text-slate-600" data-testid="not-found">
          {NOT_FOUND_TEXT}
          {row.planUrl && (
            <>{' '}<a href={row.planUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-teal-700 hover:underline" data-testid="plan-link">
              Open the plan<ExternalLink className="w-2.5 h-2.5" aria-hidden />
            </a></>
          )}
        </td>
      </tr>
    );
  }
  return (
    <>
      {row.entries.map((entry, i) => (
        <tr key={`${row.key}-${i}`} className="border-t border-slate-100" data-testid={`row-${row.key}`}>
          <th scope="row" className="px-2 py-2 align-top text-left text-sm font-medium text-slate-800">{i === 0 ? row.label : ''}</th>
          <EntryCells entry={entry} />
          {i === 0 ? <YourProposal row={row} /> : <td />}
        </tr>
      ))}
    </>
  );
}

export function YourProjectSummaryView(p: YourProjectSummaryViewProps) {
  const [open, setOpen] = useState(p.defaultOpen ?? true);
  return (
    <section className="mb-4 rounded-lg border border-slate-200 bg-white shadow-sm" aria-label="Your project" data-testid="your-project-summary">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
        className="flex w-full items-center justify-between px-4 py-3 text-left">
        <span className="text-sm font-semibold text-slate-900">Your project</span>
        {open ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
      </button>
      {open && (
        <div className="space-y-3 px-4 pb-4">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <span>Project type</span>
            <select value={p.projectType} onChange={(e) => p.onProjectTypeChange(e.target.value)}
              className="rounded border border-slate-300 px-2 py-1 text-sm" data-testid="project-type">
              {DEV_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse">
              <thead>
                <tr className="text-left text-xs text-slate-500">
                  <th className="px-2 py-1 font-medium">Control</th>
                  <th className="px-2 py-1 font-medium">Plan figure</th>
                  <th className="px-2 py-1 font-medium">Document, clause and page</th>
                  <th className="px-2 py-1 font-medium">The plan&apos;s words</th>
                  <th className="px-2 py-1 font-medium">Your proposal</th>
                </tr>
              </thead>
              <tbody>
                {p.lepRows.map((r) => <RowView key={r.key} row={r} />)}
                {p.unmapped ? (
                  <tr className="border-t border-slate-100"><td colSpan={5} className="px-2 py-2 text-xs text-slate-600" data-testid="unmapped">{NO_CONTROLS_FOR_TYPE_TEXT}</td></tr>
                ) : p.dcpRows === null ? (
                  <tr className="border-t border-slate-100"><td colSpan={5} className="px-2 py-2 text-xs text-slate-500">Loading council plan controls…</td></tr>
                ) : (
                  p.dcpRows.map((r) => <RowView key={r.key} row={r} />)
                )}
              </tbody>
            </table>
          </div>
          {p.dcpLoadError && <p className="text-xs text-slate-600" data-testid="load-error">The council plan controls could not be loaded. {NOT_FOUND_TEXT}.</p>}

          {(p.flags.flags.length > 0 || p.flags.unchecked.length > 0) && (
            <div data-testid="site-flags">
              <h3 className="mb-1 text-sm font-semibold text-slate-900">Triggered by your site</h3>
              <ul className="space-y-1 text-xs text-slate-700">
                {p.flags.flags.map((f) => (
                  <li key={f.key} data-testid={`flag-${f.key}`}>
                    <span className="font-medium">{f.label}</span>
                    {f.detail && <span>{`: ${f.detail}`}</span>}
                    <span className="text-slate-500">{` (Source: ${f.source}`}
                      {f.url && <>{', '}<a href={f.url} target="_blank" rel="noopener noreferrer" className="text-teal-700 hover:underline">link</a></>}
                      {')'}</span>
                  </li>
                ))}
                {p.flags.unchecked.map((u, i) => <li key={`u${i}`} className="text-slate-500" data-testid="flag-unchecked">{u}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ── Connected component ──────────────────────────────────────────────────────

export interface YourProjectSummaryProps {
  formerCouncil: string;
  constraints: (FlagConstraints & {
    maxHeight?: number | null; maxFsr?: number | null; minLotSize?: number | null;
  }) | null | undefined;
  planningLayers?: Array<{ layerName?: string; results?: Array<Record<string, any>> }>;
}

export function YourProjectSummary({ formerCouncil, constraints, planningLayers }: YourProjectSummaryProps) {
  const shared = useSharedProjectTypeRaw();
  const projectType = shared ?? DEFAULT_PROJECT_TYPE;
  const controlsType = resolveControlsDevType(shared);

  const url = controlsType && formerCouncil
    ? `/api/dcp/structured-controls?council=${encodeURIComponent(formerCouncil)}&dev_type=${encodeURIComponent(controlsType)}`
    : null;
  const { data, error, isLoading } = useSWR<ControlsPayload>(url, fetcher, { revalidateOnFocus: false });

  const zone = planningLayers?.find((l) => l.layerName === 'Land Zoning Map')?.results?.[0];
  const lep: LepInputs = {
    maxHeight: constraints?.maxHeight,
    maxFsr: constraints?.maxFsr,
    minLotSize: constraints?.minLotSize,
    lepName: zone?.['EPI Name'] ?? null,
    legislationUrl: zone?.['legislationUrl'] ?? null,
  };

  return (
    <YourProjectSummaryView
      projectType={projectType}
      onProjectTypeChange={setSharedProjectType}
      lepRows={buildLepRows(lep)}
      dcpRows={url && isLoading ? null : buildDcpRows(data)}
      dcpLoadError={!!error}
      unmapped={controlsType === null}
      flags={buildSiteFlags(constraints)}
    />
  );
}
