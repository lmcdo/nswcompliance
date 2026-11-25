// prior-art-checked: 2026-11-23. No summary component exists for the evidence page (grep components/reports for "At a glance": none). Every number, name and sentence here comes from lib/evidence-summary
// helpers or the payload; there is no verdict colour: status is a symbol plus words.
import React from 'react';
import type { Evidence } from '@/lib/evidence-statement';
import { fmtNum, lgaName, rowTitle, statusOf, tally, verdictWords, walkVerdict } from '@/lib/evidence-summary';

const TILE = 'flex min-w-0 flex-1 basis-60 flex-col gap-2 rounded-2xl border border-gray-200 bg-gray-50 p-5 no-underline text-gray-900 hover:border-gray-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600';
const LABEL = 'text-xs font-semibold tracking-wider text-gray-600';
const BIG = 'text-3xl font-bold leading-none tracking-tight';
const PILL = 'inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold';

/** The summary box: three tiles (the walk, the checks for land where the rules don't apply, the council's own rules) and one bottom line, each tile a link to its section. */
export default function AtAGlance({ data }: { data: Evidence }) {
  const v = walkVerdict(data.walk);
  const words = verdictWords(v, data.walk.detail);
  const t = tally(data.exclusions);
  const cc = data.council_controls;
  const ccLabels = cc.status === 'ok' ? cc.controls.map((c) => c.label ?? c.control_type ?? 'Control not named') : [];
  const excluded = t.excludes;
  const anyOpen = t.other.length;
  const needPerson = anyOpen - excluded;   // rows still open; an excluded row is a finding, not an open question
  return (
    <section aria-labelledby="glance-h" className="flex flex-col gap-5 rounded-3xl border border-gray-300 bg-white p-5 shadow-sm sm:p-8">
      <h2 id="glance-h" className="text-xl font-bold tracking-tight">At a glance</h2>
      <div className="flex flex-wrap gap-4">
        <a href="#walk" className={TILE}>
          <span className={LABEL}>1 · THE WALK</span>
          {v.best !== null ? <span className={BIG}>{fmtNum(v.best)} m</span> : <span className={BIG}>No walk measured</span>}
          <span className="text-sm text-gray-600">shortest walk to the nearest station or town centre</span>
          <span className={`${PILL} ${v.kind === 'over' ? 'bg-gray-900 text-white' : 'border-2 border-gray-900 text-gray-900'}`}><span aria-hidden="true">{v.kind === 'over' ? '▲' : v.kind === 'within' ? '▼' : '◐'}</span>{words.pill}</span>
          <span className="text-sm leading-snug text-gray-800">{words.margin ?? ''}</span>
        </a>
        <a href="#check" className={TILE}>
          <span className={LABEL}>2 · IS THIS LOT EXCLUDED?</span>
          <span className={BIG}>{t.clear} of {t.total} checks clear</span>
          <span className="text-sm text-gray-600">Flood, bushfire, heritage, pipelines and other land the housing law excludes, whatever the walk.</span>
          {t.total === 0 ? <span className={`${PILL} border-2 border-gray-900 text-gray-900`}><span aria-hidden="true">◐</span>No checks were returned</span>
            : anyOpen === 0 ? <span className={`${PILL} bg-gray-200 text-gray-900`}><span aria-hidden="true">✓</span>All clear</span>
            : <span className={`${PILL} border-2 border-gray-900 text-gray-900`}><span aria-hidden="true">{statusOf(excluded > 0 ? 'excludes' : 'warn').symbol}</span>{excluded > 0 ? `${excluded} excluded` : `${anyOpen} to check`}</span>}
          {anyOpen > 0 ? <span className="text-sm leading-snug text-gray-800">{t.other.map(rowTitle).join('; ')}.</span> : null}
        </a>
      </div>
      <div className="flex flex-col gap-3 border-t border-gray-200 pt-4">
        <p className="text-base leading-relaxed"><strong>Bottom line.</strong> {words.bottom}{excluded > 0 ? ` ${excluded === 1 ? 'One check' : `${excluded} checks`} found land where the rules don't apply.` : ''}{needPerson > 0 ? ` ${needPerson === 1 ? 'One check' : `${needPerson} checks`} for land where the rules don't apply still ${needPerson === 1 ? 'needs' : 'need'} a person.` : ''} This tool shows what it checked; the planner or the council decides.</p>
        <p className="text-sm text-gray-700">{cc.status === 'ok' && cc.controls.length > 0 ? `${lgaName(data.lga) ? `${lgaName(data.lga)}'s` : 'The council\'s'} own house rules (${ccLabels.join('; ')}) are further down. They are not part of the walking test.` : cc.status === 'none' || cc.status === 'ok' ? 'No current house rules are held for this council. They would not be part of the walking test.' : 'The council\'s own house rules could not be read. They are not part of the walking test.'}</p>
        <nav aria-label="Jump to" className="flex flex-wrap gap-x-5 gap-y-2 text-sm"><span className="text-gray-600">Jump to:</span>
          <a className="text-blue-700 underline" href="#walk">The walk</a><a className="text-blue-700 underline" href="#check">Is this lot excluded?</a>
          <a className="text-blue-700 underline" href="#controls">Council rules</a><a className="text-blue-700 underline" href="#method">How it was measured</a><a className="text-blue-700 underline" href="#proof">Law wording</a>
        </nav>
      </div>
    </section>
  );
}
