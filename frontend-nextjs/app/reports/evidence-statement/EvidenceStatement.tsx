'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { evidenceUrl, isEvidence, type Evidence } from '@/lib/evidence-statement';

const PRINT_CSS = '@media print { header, nav, footer, .no-print { display: none !important; } .evidence-statement { max-width: none; padding: 0; } tr { break-inside: avoid; } }';

export default function EvidenceStatement() {
  const sp = useSearchParams();
  const lat = sp?.get('lat') ?? null;
  const lng = sp?.get('lng') ?? null;
  const address = sp?.get('address') ?? null;
  const [data, setData] = useState<Evidence | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  if (error) return <p className="p-6 text-sm" role="alert">{error}</p>;
  if (!data) return <p className="p-6 text-sm">Loading the evidence for this lot...</p>;

  const w = data.walk;
  const cc = data.council_controls;
  const cf = data.council_files;
  // The earliest "held from" among the files listed below (ISO dates sort as text). Read from the same list, and only when EVERY file
  // has a date: a file with no date could be older, so "we hold nothing earlier" could not be said.
  const heldDates = cf.status === 'ok' ? cf.files.map((f) => f.held_from?.slice(0, 10)) : [];
  const earliestHeld = heldDates.length > 0 && heldDates.every((d) => !!d) ? (heldDates as string[]).slice().sort()[0] : null;
  return (
    <main className="mx-auto max-w-4xl p-6 text-sm text-gray-900 evidence-statement">
      <style>{PRINT_CSS}</style>
      <div className="no-print mb-4">
        <button type="button" onClick={() => window.print()} className="rounded border px-3 py-1">Print or save as PDF</button>
      </div>
      <h1 className="text-xl font-semibold">Site evidence statement</h1>
      <p className="text-gray-600">
        Point {lat}, {lng}{data.lga ? ` (${data.lga})` : ''}.{address ? ` Reference typed in the link, not checked against the point: ${address}.` : ''} Law version dated {data.law_version_date ?? 'not given'}.
      </p>
      {data.headline && <p className="mt-2">{data.headline}</p>}
      {data.summary?.line ? <p className="mt-2 font-semibold">{data.summary.line}</p> : null}

      {data.notes.length > 0 && (
        <>
          <h2 className="mt-6 text-lg font-semibold">Notes on how to read this</h2>
          <ul className="list-disc pl-5">{data.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
        </>
      )}

      <h2 className="mt-6 text-lg font-semibold">Walking range</h2>
      <p>
        {w.walk_low_m != null && w.walk_high_m != null
          ? `Measured walk from ${w.anchor ?? 'the nearest anchor'}: ${w.walk_low_m} to ${w.walk_high_m} m. Limit in the law: ${w.limit_m ?? 'not given'} m${w.clause ? ` (${w.clause}, page ${w.page})` : ''}.`
          : `No walking range was measured. ${w.detail ?? ''}`}
      </p>
      {w.walk_low_m != null && w.walk_high_m != null && w.margin_low_m != null && w.margin_high_m != null && (
        <p className="text-gray-600">
          {`The walk is a range because the measurement can be off: the range runs from the measured walk less ${w.margin_low_m} m to the measured walk plus ${w.margin_high_m} m${w.entrance_unmapped_extra_m ? `, plus up to ${w.entrance_unmapped_extra_m} m because the station entrance is not mapped` : ''}.`}
        </p>
      )}
      {w.heuristic && <p className="text-gray-600">{w.heuristic}</p>}
      {w.crossings_only_note || w.crossings_only_walk_m != null ? (
        <p className="mt-2">
          <strong>Crossings-only walk, for information.</strong> {w.crossings_only_note ?? `Crossing busy roads only at traffic lights, zebra or marked crossings, the walk is about ${w.crossings_only_walk_m} m.`} It does not change the result above.
        </p>
      ) : null}

      <h2 className="mt-6 text-lg font-semibold">Section 164 exclusions (law version dated {data.law_version_date ?? 'not given'})</h2>
      <table className="w-full border-collapse">
        <thead>
          <tr className="text-left">
            <th className="border p-1">Clause</th><th className="border p-1">Law wording</th>
            <th className="border p-1">Source checked</th><th className="border p-1">Result</th>
          </tr>
        </thead>
        <tbody>
          {data.exclusions.map((x) => (
            <tr key={x.para} className="align-top">
              <td className="border p-1 whitespace-nowrap">{x.clause}<br />page {x.page}</td>
              <td className="border p-1">{x.law_words}</td>
              <td className="border p-1">{x.source_checked}</td>
              <td className="border p-1">
                <strong>{x.result_words}</strong><br />{x.detail}
                {x.not_seen ? <><br />Not seen: {x.not_seen}</> : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.manual_checks && data.manual_checks.length > 0 && (
        <>
          <h2 className="mt-6 text-lg font-semibold">To check by hand</h2>
          <p>This tool did not clear these paragraphs. Check the lot on the NSW Planning Portal Spatial Viewer or ask the council for a planning certificate.</p>
          <ul className="list-disc pl-5">
            {data.manual_checks.map((m, i) => (
              <li key={i}>{m.clause ?? 'Paragraph not named'}{m.page != null ? ` (page ${m.page})` : ''}: {m.law_words ?? 'law wording not held'}. {m.result_words ?? ''}{m.not_seen ? ` Not seen: ${m.not_seen}.` : ''}</li>
            ))}
          </ul>
        </>
      )}

      <h2 className="mt-6 text-lg font-semibold">Council controls (dwelling house)</h2>
      <p className="text-gray-600">Controls for other kinds of development, and controls that apply only to part of a council area, are not shown here.</p>
      {cc.status !== 'ok' ? (
        <p>{cc.status === 'none' ? 'No current controls are held for this council.' : `Could not be read: ${cc.reason ?? 'no reason given'}.`}</p>
      ) : (
        <>
          {cc.as_at_line && <p className="text-gray-600">{cc.as_at_line}</p>}
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left">
                <th className="border p-1">Control</th><th className="border p-1">Council wording</th><th className="border p-1">Clause and page</th><th className="border p-1">Quote on the cited page, by file version</th>
              </tr>
            </thead>
            <tbody>
              {cc.controls.map((c, i) => (
                <tr key={i} className="align-top">
                  <td className="border p-1">{c.label ?? c.control_type ?? 'Control not named'}<br />{c.requirement ?? 'No requirement text'}</td>
                  <td className="border p-1">{c.council_words ?? 'Council wording not held'}</td>
                  <td className="border p-1">
                    {c.clause ? `${c.clause}${c.clause_shown ? '' : ' (label not checked against the page)'}, ` : ''}page {c.page ?? 'not given'}
                  </td>
                  <td className="border p-1">
                    {c.version_checks?.status === 'ok' ? c.version_checks.versions.map((v) => (
                      <div key={v.version}>{v.version}: {v.result_words}{v.stale ? ' (check made on an older wording of this quote)' : ''}</div>
                    )) : c.version_checks?.status === 'unreadable' ? 'Could not be read.' : 'Not checked.'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <h2 className="mt-6 text-lg font-semibold">Council files held</h2>
      {cf.status !== 'ok' ? (
        <p>{cf.status === 'none' ? 'No council files are held.' : `Could not be read: ${cf.reason ?? 'no reason given'}.`}</p>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left">
              <th className="border p-1">Chapter</th><th className="border p-1">Version</th><th className="border p-1">Held from</th>
              <th className="border p-1">Replaced on</th><th className="border p-1">Council file date</th>
            </tr>
          </thead>
          <tbody>
            {cf.files.map((f, i) => (
              <tr key={i}>
                <td className="border p-1">{f.chapter}</td>
                <td className="border p-1">{f.version}</td>
                <td className="border p-1">{f.held_from?.slice(0, 10) ?? 'not recorded'}</td>
                <td className="border p-1">{f.current ? 'current' : (f.replaced_on?.slice(0, 10) ?? 'not recorded')}</td>
                <td className="border p-1">{f.council_file_date ?? f.council_file_date_note ?? 'not recorded'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {earliestHeld && (
        <p className="mt-2 text-gray-600">The earliest file we hold for this council is held from {earliestHeld}. We hold no earlier copy, so a version replaced before that date is not on this page.</p>
      )}
      <p className="mt-2 text-gray-600">
        These are the files we hold. A plan date shown above is the date the plan document states; this page does not say which file is in force. Each version is checked against the page the current plan cites; an older file can be paginated differently, so "different page" does not mean the control is wrong.
      </p>

      <p className="mt-6 border-t pt-2 text-gray-600">
        This page shows what this tool checked and what it did not. It is not a planning certificate and it does not decide whether a lot is inside or outside a housing area. The planner or the council decides.
      </p>
    </main>
  );
}
