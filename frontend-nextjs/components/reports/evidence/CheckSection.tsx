// prior-art-checked: 2026-11-23. The old page printed these paragraphs in one table and a "to check by hand" list (app/reports/evidence-statement/EvidenceStatement.tsx); this replaces both with cards
// that put the plain topic, what was found, the distance behind it and the law's own words together. Figures come from the payload's `facts`; the only typed text is wording.
import React from 'react';
import { gapCrossChecked, type Evidence, type EvidenceExclusion, type ExclusionFacts } from '@/lib/evidence-statement';
import { cardRows, distanceWords, fmtNum, rowTitle, sentence, statusOf, tally } from '@/lib/evidence-summary';

const SPATIAL_VIEWER_STEP = 'Check the lot on the NSW Planning Portal Spatial Viewer, or ask the council for a planning certificate.';

/** The lines of fact a card shows under "What we found", built from the payload's figures. A field that is absent adds no line, never a guess. */
export function factLines(f: ExclusionFacts | null | undefined, detail?: string | null): string[] {
  if (!f) return [];
  const out: string[] = [];
  const has = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
  if (f.flood_state === 'outside' && has(f.nearest_m) && !(detail ?? '').includes(distanceWords(f.nearest_m))) out.push(`Nearest flooded land: ${distanceWords(f.nearest_m)} away.`);
  if (f.flood_state === 'outside' && f.nearest_m === null) out.push('No flood area is within the search distance.');
  if (f.flood_state === 'edge' && has(f.edge_m) && has(f.margin_m)) out.push(`The lot is ${distanceWords(f.edge_m)} from the edge of the flood area, inside the ${fmtNum(f.margin_m)} m margin for map detail: the map cannot say which side of the edge it is on.`);
  if (f.flood_state === 'inside') out.push('The lot is on the flood area of the study.');
  if (f.flood_state && has(f.nearest_500_year_m)) out.push(`1-in-500 year flood: ${distanceWords(f.nearest_500_year_m)} away.`);
  if (f.flood_state && has(f.nearest_100_year_m)) out.push(`1-in-100 year flood: ${distanceWords(f.nearest_100_year_m)} away.`);
  if (f.flood_state && f.copy_as_of) out.push(`Our copy of the flood study was read on ${f.copy_as_of}${f.study ? ` (${f.study})` : ''}. It is not a council flood certificate.`);
  if (f.map) {   // the pipeline paragraph
    if (f.hit === true) out.push(`A pipeline on the ${f.map} is within the law's distance${has(f.limit_m) ? ` of ${fmtNum(f.limit_m)} m` : ''}.`);
    else if (has(f.nearest_m)) out.push(`Nearest mapped gas pipeline: ${distanceWords(f.nearest_m)}${f.nearest_name ? ` (${f.nearest_name})` : ''}${has(f.limit_m) ? `; the law's distance is ${fmtNum(f.limit_m)} m` : ''}.`);
    else if (has(f.searched_m)) out.push(`No mapped gas pipeline within ${distanceWords(f.searched_m)}.`);
    if (f.gap) out.push(`${f.gap.no_route_count} of the ${f.gap.named_in_law} pipelines the law names have no published route we could find, so this paragraph cannot be cleared from the map alone (checked ${f.gap.checked_on}${gapCrossChecked(f.gap) ? '' : ', not yet cross-checked'}).`);
  }
  return out;
}

function Card({ r }: { r: EvidenceExclusion }) {
  const s = statusOf(r.result);
  const lines = factLines(r.facts, r.detail);
  const showDetail = !(r.result === 'not_checked' && lines.length > 0);   // for a paragraph this tool could not check, the detail only restates the law: the figures below say what we know
  return (
    <div className="flex min-w-0 flex-1 basis-72 flex-col gap-3 rounded-3xl border border-gray-200 bg-white p-6 break-inside-avoid">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold text-gray-600">{r.clause} · page {r.page}</span>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${r.result === 'clear' ? 'bg-gray-100 text-gray-900' : 'border-2 border-gray-900 text-gray-900'}`}><span aria-hidden="true">{s.symbol}</span>{r.result_words}</span>
      </div>
      <h3 className="text-xl font-bold leading-snug tracking-tight">{rowTitle(r)}</h3>
      {showDetail ? <p className="text-sm leading-relaxed"><strong>What we found:</strong> {sentence(r.detail ?? r.result_words)}{r.not_seen ? ` Not seen: ${r.not_seen}.` : ''}</p> : null}
      {lines.map((l, i) => <p key={i} className="text-sm leading-relaxed text-gray-800">{l}</p>)}
      <blockquote className="border-l-4 border-gray-200 pl-3 text-sm italic leading-relaxed text-gray-700">The law says: &ldquo;{r.law_words}&rdquo;</blockquote>
      {r.result !== 'clear' ? <p className="text-sm leading-relaxed"><strong>Next step:</strong> {SPATIAL_VIEWER_STEP}</p> : null}
    </div>
  );
}

/** Section 2: the paragraphs that need a person first, and any clear paragraph with a distance, as cards; the rest as one line each in a fold. */
export default function CheckSection({ data }: { data: Evidence }) {
  const t = tally(data.exclusions);
  const cards = cardRows(data.exclusions).sort((a, b) => Number(a.result === 'clear') - Number(b.result === 'clear'));
  const shown = new Set(cards.map((c) => c.para));
  const rest = t.clearRows.filter((r) => !shown.has(r.para));
  const instrument = data.law_instrument ? ` of ${data.law_instrument}` : '';
  return (
    <section id="check" aria-labelledby="check-h" className="flex flex-col gap-5 scroll-mt-6">
      <h2 id="check-h" className="text-2xl font-bold tracking-tight">2 · Excluded land (section 164)</h2>
      <p className="max-w-3xl text-base leading-relaxed text-gray-600">
        Whatever the walk, the Low and Mid Rise housing rules leave out some land, such as flood-prone land. The law lists {t.total} kinds, in section 164(1){instrument}. {t.clear} did not apply to this lot.
        {t.excludes > 0 ? ` ${t.excludes === 1 ? 'One' : t.excludes} ${t.excludes === 1 ? 'was' : 'were'} found to apply to this lot.` : ''}{t.other.length - t.excludes > 0 ? ` ${t.other.length - t.excludes === 1 ? 'One' : t.other.length - t.excludes} could not be settled by this tool and ${t.other.length - t.excludes === 1 ? 'needs' : 'need'} a person.` : ''} Law wording for all {t.total}: see The proof section below.
      </p>
      {data.summary?.line ? <p className="text-sm font-semibold">{data.summary.line}</p> : null}
      <div className="flex flex-wrap gap-4">{cards.map((r) => <Card key={r.para} r={r} />)}</div>
      {rest.length > 0 ? (
        <details className="rounded-2xl border border-gray-200 bg-white">
          <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-5 py-4"><span><span className="block text-base font-semibold">{rest.length === 1 ? 'The other check, clear' : `The other ${rest.length} checks, all clear`}</span><span className="block text-sm text-gray-600">One line each. The law&apos;s wording and the map checked are in The proof below.</span></span><span aria-hidden="true" className="text-xl text-gray-600">›</span></summary>
          <ul className="grid gap-x-6 gap-y-2 border-t border-gray-200 px-5 py-4 text-sm sm:grid-cols-2">{rest.map((r) => <li key={r.para}>✓ {rowTitle(r)} <span className="text-gray-600">({r.para})</span></li>)}</ul>
        </details>
      ) : null}
    </section>
  );
}
