'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { evidenceUrl, isEvidence, type Evidence } from '@/lib/evidence-statement';
import { fmtNum, lgaName, verdictWords, walkVerdict } from '@/lib/evidence-summary';
import RouteMapFigure from '@/components/reports/RouteMapFigure';
import AtAGlance from '@/components/reports/evidence/AtAGlance';
import CheckSection from '@/components/reports/evidence/CheckSection';
import ControlsSection from '@/components/reports/evidence/ControlsSection';
import ProofSection from '@/components/reports/evidence/ProofSection';
import RangeScale from '@/components/reports/evidence/RangeScale';

// header, nav and footer are the SITE's (and this page's jump links); the page's own title block and record line are divs so they print.
const PRINT_CSS = '@media print { header, nav, footer, .no-print { display: none !important; } .evidence-statement { max-width: none; padding: 0; } figure, svg { break-inside: avoid; } }';

/** Opens every folded section while the page prints, and puts each back as it was afterwards, so the printed record carries the proof. */
function useOpenFoldsForPrint() {
  useEffect(() => {
    const was = new Map<HTMLDetailsElement, boolean>();
    const open = () => document.querySelectorAll<HTMLDetailsElement>('.evidence-statement details').forEach((d) => { was.set(d, d.open); d.open = true; });
    const restore = () => { was.forEach((v, d) => { d.open = v; }); was.clear(); };
    window.addEventListener('beforeprint', open);
    window.addEventListener('afterprint', restore);
    return () => { window.removeEventListener('beforeprint', open); window.removeEventListener('afterprint', restore); };
  }, []);
}

export default function EvidenceStatement() {
  const sp = useSearchParams();
  const lat = sp?.get('lat') ?? null;
  const lng = sp?.get('lng') ?? null;
  const address = sp?.get('address') ?? null;
  const [data, setData] = useState<Evidence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<'idle' | 'done' | 'failed'>('idle');
  useOpenFoldsForPrint();

  useEffect(() => {
    const url = evidenceUrl(lat, lng);
    if (!url) { setError('This page needs a latitude and longitude in the address bar.'); return; }
    let live = true;
    setData(null);
    setError(null);
    fetch(url, { cache: 'no-store' })
      .then(async (r) => {
        const j = await r.json().catch(() => null);
        if (!r.ok || !isEvidence(j)) throw new Error('The evidence data could not be loaded.');
        return j;
      })
      .then((j) => { if (live) setData(j); })
      .catch((e: Error) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [lat, lng]);

  const copyLink = useCallback(() => {
    if (!navigator.clipboard) { setCopied('failed'); return; }
    navigator.clipboard.writeText(window.location.href).then(() => setCopied('done'), () => setCopied('failed'));
  }, []);

  if (error) return <p className="p-6 text-sm" role="alert">{error}</p>;
  if (!data) return <p className="p-6 text-sm">Loading the evidence for this lot...</p>;

  const w = data.walk;
  const v = walkVerdict(w);
  const words = verdictWords(v, w.detail);
  const hasCrossings = !!(w.crossings_only_note || w.crossings_only_walk_m != null);
  const limitText = v.limit !== null ? ` ${fmtNum(v.limit)} m` : '';
  return (
    <main className="evidence-statement mx-auto flex max-w-4xl flex-col gap-10 px-4 py-8 text-sm text-gray-900 sm:px-8">
      <style>{PRINT_CSS}</style>
      <div className="no-print flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => window.print()} className="min-h-11 rounded-full bg-blue-700 px-5 text-sm font-medium text-white">Print or save as PDF</button>
        <button type="button" onClick={copyLink} className="min-h-11 rounded-full border border-gray-300 bg-white px-5 text-sm font-medium">Copy link</button>
        {copied !== 'idle' ? <span role="status" className="text-sm text-gray-600">{copied === 'done' ? 'Link copied.' : 'The link could not be copied: copy it from the address bar.'}</span> : null}
      </div>

      <div className="flex flex-col gap-3">
        <h1 className="text-4xl font-bold leading-tight tracking-tight">Low and Mid Rise housing: walking-distance check</h1>
        <p className="max-w-3xl text-lg leading-snug">
          {`Is this lot within${limitText || ' a set'} walking distance of a station or town centre, and is any of it on land where the housing rules don't apply?`} What this tool found, and the law&apos;s words behind it.
        </p>
        <p className="text-2xl font-semibold tracking-tight">{address ?? `Point ${lat}, ${lng}`}</p>
        <p className="flex flex-wrap gap-2 text-xs text-gray-700">
          {lgaName(data.lga) ? <span className="rounded-full bg-gray-100 px-3 py-1.5">{lgaName(data.lga)}</span> : null}
          <span className="rounded-full bg-gray-100 px-3 py-1.5">Law as at {data.law_version_date ?? 'not given'}</span>
          <span className="rounded-full bg-gray-100 px-3 py-1.5">Point {lat}, {lng}</span>
        </p>
        {address ? <p className="text-xs text-gray-600">Reference typed in the link, not checked against the point: {address}.</p> : null}
      </div>

      <AtAGlance data={data} />

      <section id="walk" aria-labelledby="walk-h" className="flex flex-col gap-5 scroll-mt-6">
        <h2 id="walk-h" className="text-2xl font-bold tracking-tight">1 · The walk</h2>
        <p className="max-w-3xl text-base leading-relaxed text-gray-600">
          {data.law_instrument || w.clause ? `The law (${[data.law_instrument, w.clause, w.page != null ? `page ${w.page}` : null].filter(Boolean).join(', ')}) counts` : 'The law counts'} land within{limitText || ' a set'} walking distance of a station or town centre. The walk is measured from the nearest part of the lot. Law wording: see The proof section below.
        </p>
        <div className="flex flex-col gap-4 rounded-3xl border border-gray-200 bg-white p-6 sm:p-8">
          {v.best !== null && v.limit !== null ? (
            <>
              <p className="text-base font-semibold">The shortest walk against the limit</p>
              <p className="text-lg leading-snug">{words.sentence}</p>
              <RangeScale verdict={v} />
              <p className="text-sm leading-relaxed text-gray-700">
                <strong>How it is measured:</strong> the shortest walk along public footpaths and crossings, in metres, from the nearest part of the lot to the station or town centre entrance. The law counts the lot if any part of it is within the distance.
              </p>
            </>
          ) : <p>{`No walk was measured. ${w.detail ?? ''}`}</p>}
          {hasCrossings ? (
            <p className="text-sm leading-relaxed"><strong>Crossings-only walk, for information.</strong> {w.crossings_only_note ?? `Crossing busy roads only at traffic lights, zebra or marked crossings, the walk is about ${w.crossings_only_walk_m} m.`} It does not change the result above.</p>
          ) : null}
        </div>
        {data.route_map ? <RouteMapFigure routeMap={data.route_map} /> : null}
      </section>

      <CheckSection data={data} />
      <ControlsSection data={data} />
      <ProofSection data={data} showRoadRules={hasCrossings} />

      <div className="flex flex-col gap-3 border-t border-gray-200 pt-5 text-xs leading-relaxed text-gray-600">
        <p>Record: law as at {data.law_version_date ?? 'not given'}{lgaName(data.lga) ? ` · ${lgaName(data.lga)}` : ''}. This page shows what this tool checked and what it did not. It is not a planning certificate and it does not decide whether a lot is inside or outside a housing area. The planner or the council decides.</p>
      </div>
    </main>
  );
}
