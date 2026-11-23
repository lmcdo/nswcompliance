// prior-art-checked: 2026-11-23. No component in frontend-nextjs draws a range against a limit (grep components/ for "limit" scales: none; RouteMapFigure draws routes, not a number line). Plain divs and
// percentages from lib/evidence-summary.buildScale, no chart library: it is a labelled number line, and every label carries its number so colour is never the only carrier.
import React from 'react';
import { buildScale, fmtNum, type WalkVerdict } from '@/lib/evidence-summary';

/** The walk against the limit on a labelled number line: the limit as a line, the measured walk as a dot, the possible range as a band, and which side is over the limit. */
export default function RangeScale({ verdict }: { verdict: WalkVerdict }) {
  const m = buildScale(verdict.limit, verdict.low, verdict.high, verdict.best);
  if (!m || verdict.limit == null || verdict.low == null || verdict.high == null) return null;
  const at = (pct: number): React.CSSProperties => ({ left: `${pct}%` });
  const label = `Scale from ${fmtNum(m.min)} to ${fmtNum(m.max)} metres. The ${fmtNum(verdict.limit)} metre limit is marked. `
    + `${verdict.best !== null ? `The measured walk is ${fmtNum(verdict.best)} metres. ` : ''}The possible range is ${fmtNum(verdict.low)} to ${fmtNum(verdict.high)} metres.`;
  const nearLimit = (pct: number) => Math.abs(pct - m.limitPct) < 6;   // a tick label this close to the limit label would overlap it
  return (
    <div className="mx-3 sm:mx-4">
      <div role="img" aria-label={label} className="relative h-36 select-none">
        <div className="absolute top-7 h-16 rounded-l-xl border border-r-0 border-gray-200 bg-white" style={{ left: 0, width: `${m.limitPct}%` }} />
        <div className="absolute top-7 h-16 rounded-r-xl bg-gray-100" style={{ left: `${m.limitPct}%`, right: 0 }} />
        <div className="absolute top-1 hidden whitespace-nowrap text-xs text-gray-600 sm:block" style={{ left: 0 }}>Within the limit</div>
        <div className="absolute top-1 whitespace-nowrap pl-2 text-xs text-gray-600" style={at(m.limitPct)}>Over the limit</div>
        <div className="absolute top-11 flex h-7 items-center justify-end whitespace-nowrap rounded-full bg-blue-600 pr-3 text-xs font-semibold text-white" style={{ left: `${m.bandLeftPct}%`, width: `${m.bandWidthPct}%` }}>
          <span className="truncate pl-2"><span className="hidden sm:inline">Possible range: </span>{fmtNum(verdict.low)} to {fmtNum(verdict.high)} m</span>
        </div>
        <div className="absolute top-6 h-20 w-0.5 bg-gray-900" style={at(m.limitPct)} />
        {m.bestPct !== null && verdict.best !== null ? (
          <>
            <div className="absolute top-12 -ml-2.5 h-5 w-5 rounded-full border-[3px] border-white bg-gray-900" style={at(m.bestPct)} />
            <div className="absolute top-[4.6rem] -translate-x-1/2 whitespace-nowrap text-xs font-semibold" style={at(m.bestPct)}><span className="hidden sm:inline">Measured walk </span>{fmtNum(verdict.best)} m</div>
          </>
        ) : null}
        {m.ticks.map((t, i) => {
          const pct = ((t - m.min) / (m.max - m.min)) * 100;
          if (nearLimit(pct)) return null;
          return <div key={t} className="absolute top-[6.6rem] -translate-x-1/2 whitespace-nowrap text-xs text-gray-600" style={at(pct)}>{fmtNum(t)}{i === m.ticks.length - 1 ? ' m' : ''}</div>;
        })}
        <div className="absolute top-[6.6rem] -translate-x-1/2 whitespace-nowrap text-xs font-bold text-gray-900" style={at(m.limitPct)}>{fmtNum(verdict.limit)} m limit</div>
      </div>
    </div>
  );
}
