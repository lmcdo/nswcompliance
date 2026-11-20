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

      <h2 className="mt-6 text-lg font-semibold">Walking range</h2>
      <p>
        {w.walk_low_m != null && w.walk_high_m != null
          ? `Measured walk from ${w.anchor ?? 'the nearest anchor'}: ${w.walk_low_m} to ${w.walk_high_m} m. Limit in the law: ${w.limit_m ?? 'not given'} m${w.clause ? ` (${w.clause}, page ${w.page})` : ''}.`
          : `No walking range was measured. ${w.detail ?? ''}`}
      </p>
      {w.heuristic && <p className="text-gray-600">{w.heuristic}</p>}

      <h2 className="mt-6 text-lg font-semibold">Section 164 exclusions</h2>
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

      <h2 className="mt-6 text-lg font-semibold">Council controls (dwelling house)</h2>
      {cc.status !== 'ok' ? (
        <p>{cc.status === 'none' ? 'No current controls are held for this council.' : `Could not be read: ${cc.reason ?? 'no reason given'}.`}</p>
      ) : (
        <>
          {cc.as_at_line && <p className="text-gray-600">{cc.as_at_line}</p>}
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left">
                <th className="border p-1">Control</th><th className="border p-1">Council wording</th><th className="border p-1">Clause and page</th>
              </tr>
            </thead>
            <tbody>
              {cc.controls.map((c, i) => (
                <tr key={i} className="align-top">
                  <td className="border p-1">{c.control_type ?? 'Control not named'}<br />{c.requirement ?? 'No requirement text'}</td>
                  <td className="border p-1">{c.council_words ?? 'Council wording not held'}</td>
                  <td className="border p-1">
                    {c.clause ? `${c.clause}${c.clause_shown ? '' : ' (label not checked against the page)'}, ` : ''}page {c.page ?? 'not given'}
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
      <p className="mt-2 text-gray-600">
        These are the files held, not a statement of which file is in force. Whether each quote is on its cited page, for earlier versions, is not checked here.
      </p>

      {data.notes.length > 0 && (
        <>
          <h2 className="mt-6 text-lg font-semibold">Notes</h2>
          <ul className="list-disc pl-5">{data.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
        </>
      )}
    </main>
  );
}
