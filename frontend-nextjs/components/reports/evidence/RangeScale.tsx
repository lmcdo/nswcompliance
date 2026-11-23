// prior-art-checked: 2026-11-23. Replaces the range-band version in this file (grep components/ for "limit" scales: none other). Plain divs and percentages from lib/evidence-summary.buildScale, no chart
// library: a labelled number line with the limit as a line and the measured walk as a dot; every label carries its number so colour is never the only carrier.
import React from 'react';
import { buildScale, fmtNum, type WalkVerdict } from '@/lib/evidence-summary';

/** The measured walk against the limit on a labelled number line: the limit as a line, the measured walk as a dot, and which side is over the limit. */
export default function RangeScale({ verdict }: { verdict: WalkVerdict }) {
  const best = verdict.best;
  const m = buildScale(verdict.limit, best, best, best);
  if (!m || verdict.limit === null || best === null || m.bestPct === null) return null;
  const at = (pct: number): React.CSSProperties => ({ left: `${pct}%` });
  const label = `Scale from ${fmtNum(m.min)} to ${fmtNum(m.max)} metres. The ${fmtNum(verdict.limit)} metre limit is marked. The shortest walk is ${fmtNum(best)} metres.`;
  const nearLimit = (pct: number) => Math.abs(pct - m.limitPct) < 6;   // a tick label this close to the limit label would overlap it
  const nearBest = (pct: number) => Math.abs(pct - m.bestPct!) < 6;
  return (
    <div className="mx-3 sm:mx-4">
      <div role="img" aria-label={label} className="relative h-28 select-none">
        <div className="absolute top-7 h-12 rounded-l-xl border border-r-0 border-gray-200 bg-white" style={{ left: 0, width: `${m.limitPct}%` }} />
        <div className="absolute top-7 h-12 rounded-r-xl bg-gray-100" style={{ left: `${m.limitPct}%`, right: 0 }} />
        <div className="absolute top-1 hidden whitespace-nowrap text-xs text-gray-600 sm:block" style={{ left: 0 }}>Within the limit</div>
        <div className="absolute top-1 whitespace-nowrap pl-2 text-xs text-gray-600" style={at(m.limitPct)}>Over the limit</div>
        <div className="absolute top-6 h-14 w-0.5 bg-gray-900" style={at(m.limitPct)} />
        <div className="absolute top-[2.1rem] -ml-2.5 h-5 w-5 rounded-full border-[3px] border-white bg-gray-900 shadow" style={at(m.bestPct)} />
        <div className="absolute top-[3.6rem] -translate-x-1/2 whitespace-nowrap text-xs font-semibold" style={at(m.bestPct)}>Shortest walk {fmtNum(best)} m</div>
        {m.ticks.map((t, i) => {
          const pct = ((t - m.min) / (m.max - m.min)) * 100;
          if (nearLimit(pct) || nearBest(pct)) return null;
          return <div key={t} className="absolute top-[5.2rem] -translate-x-1/2 whitespace-nowrap text-xs text-gray-600" style={at(pct)}>{fmtNum(t)}{i === m.ticks.length - 1 ? ' m' : ''}</div>;
        })}
        <div className="absolute top-[5.2rem] -translate-x-1/2 whitespace-nowrap text-xs font-bold text-gray-900" style={at(m.limitPct)}>{fmtNum(verdict.limit)} m limit</div>
      </div>
    </div>
  );
}
