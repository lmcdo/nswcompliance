// prior-art-checked: 2026-11-23. The exclusions table and the road-rules quotations moved here unchanged from app/reports/evidence-statement/EvidenceStatement.tsx; they are now folded (opened for printing by the page),
// and the "how this was measured" notes sit beside them. Quotations stay word for word and keep their clause and source.
import React from 'react';
import type { Evidence } from '@/lib/evidence-statement';

const SUMMARY = 'flex min-h-11 cursor-pointer items-center justify-between gap-4 px-6 py-5';

/** Section 4 (how it was measured) and section 5 (sources): the notes the check returned, then the law's own wording folded away. */
export default function ProofSection({ data, showRoadRules }: { data: Evidence; showRoadRules: boolean }) {
  const date = data.law_version_date ?? 'not given';
  return (
    <>
      <section id="method" aria-labelledby="method-h" className="flex flex-col gap-3 scroll-mt-6">
        <h2 id="method-h" className="text-2xl font-bold tracking-tight">How this was measured</h2>
        <div className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-6 text-sm leading-relaxed">
          {data.headline ? <p><strong>The result under the law.</strong> {data.headline}</p> : null}
          {data.notes.map((n, i) => <p key={i}>{n}</p>)}
          <p><strong>The walk.</strong> The shortest route along mapped footpaths from the nearest part of the lot to the nearest station entrance or town-centre edge. Footpath data: OpenStreetMap contributors.</p>
          <p><strong>What this page does not do.</strong> It is not a planning certificate and does not decide whether a lot is inside or outside a housing area. It shows what this tool checked and what it did not.</p>
        </div>
      </section>

      <section id="proof" aria-labelledby="proof-h" className="flex flex-col gap-3 scroll-mt-6">
        <div className="flex flex-col gap-1">
          <h2 id="proof-h" className="text-2xl font-bold tracking-tight">Sources</h2>
          <p className="max-w-3xl text-base text-gray-600">The law&apos;s own words for each line above. Open any section.</p>
        </div>
        <div className="divide-y divide-gray-200 overflow-hidden rounded-2xl border border-gray-200 bg-white">
          <details>
            <summary className={SUMMARY}><span><span className="block text-lg font-semibold">Is this lot excluded? Section 164 (law version dated {date})</span>
              <span className="block text-sm text-gray-600">{data.law_instrument ? `${data.law_instrument}. ` : ''}Each paragraph with the law&apos;s words, the map or list checked and the result.</span></span><span aria-hidden="true" className="text-xl text-gray-600">›</span></summary>
            <div className="overflow-x-auto px-6 pb-6">
              <table className="w-full border-collapse text-sm">
                <thead><tr className="text-left"><th className="border p-1">Clause</th><th className="border p-1">Law wording</th><th className="border p-1">Source checked</th><th className="border p-1">Result</th></tr></thead>
                <tbody>
                  {data.exclusions.map((x) => (
                    <tr key={x.para} className="align-top">
                      <td className="border p-1 whitespace-nowrap">{x.clause}<br />page {x.page}</td>
                      <td className="border p-1">{x.law_words}</td>
                      <td className="border p-1">{x.source_checked}</td>
                      <td className="border p-1"><strong>{x.result_words}</strong><br />{x.detail}{x.not_seen ? <><br />Not seen: {x.not_seen}</> : null}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          {showRoadRules && data.road_rules ? (
            <details>
              <summary className={SUMMARY}><span><span className="block text-lg font-semibold">NSW road rules for pedestrians at lights and near crossings</span>
                <span className="block text-sm text-gray-600">Word for word. For reference; this tool does not decide whether a walk is lawful.</span></span><span aria-hidden="true" className="text-xl text-gray-600">›</span></summary>
              <div className="px-6 pb-6">
                {data.road_rules.status === 'ok' && data.road_rules.rules ? (
                  <>
                    <p className="text-sm text-gray-600">The exact wording of the {data.road_rules.instrument ?? 'NSW Road Rules'}, copied from AustLII on {data.road_rules.copied_on ?? 'a date not recorded'}. Shown for reference. This tool does not decide whether a walk is lawful.</p>
                    {data.road_rules.rules.map((rr) => (
                      <figure key={rr.clause} className="mt-3">
                        <blockquote className="whitespace-pre-wrap border-l-2 pl-2 text-sm">{rr.quote}</blockquote>
                        <figcaption className="text-xs text-gray-600">{rr.clause}{rr.heading ? `, ${rr.heading}` : ''}. Source: {rr.source_url}</figcaption>
                      </figure>
                    ))}
                  </>
                ) : <p className="text-sm">The road rules wording could not be shown: {data.road_rules.reason ?? 'no reason given'}.</p>}
              </div>
            </details>
          ) : null}
        </div>
      </section>
    </>
  );
}
