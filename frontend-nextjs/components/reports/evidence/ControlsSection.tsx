// prior-art-checked: 2026-11-23. This replaces the council-controls table in app/reports/evidence-statement/EvidenceStatement.tsx with cards; the data (payload council_controls) and every word it shows are unchanged.
import React from 'react';
import type { Evidence } from '@/lib/evidence-statement';
import { lgaName } from '@/lib/evidence-summary';

/** Section 3: the council's own rules for a house, each with its page and the check of its wording against the cited page, by file version. */
export default function ControlsSection({ data }: { data: Evidence }) {
  const cc = data.council_controls;
  return (
    <section id="controls" aria-labelledby="controls-h" className="flex flex-col gap-4 scroll-mt-6">
      <h2 id="controls-h" className="text-2xl font-bold tracking-tight">3 · {lgaName(data.lga) ? `${lgaName(data.lga)}'s` : 'The council\'s'} own rules for building a house</h2>
      <p className="max-w-3xl text-base leading-relaxed text-gray-600">Controls for other kinds of development, and controls that apply only to part of a council area, are not shown here.</p>
      {cc.status !== 'ok' ? (
        <p className="text-sm">{cc.status === 'none' ? 'No current controls are held for this council.' : `Could not be read: ${cc.reason ?? 'no reason given'}.`}</p>
      ) : (
        <>
          {cc.as_at_line ? <p className="text-sm text-gray-600">{cc.as_at_line}</p> : null}
          <div className="flex flex-wrap gap-4">
            {cc.controls.map((c, i) => (
              <div key={i} className="flex min-w-0 flex-1 basis-72 flex-col gap-2 rounded-2xl border border-gray-200 bg-white p-5 break-inside-avoid">
                <span className="text-xs font-semibold text-gray-600">
                  {c.clause && c.clause_shown ? `${c.clause}, ` : ''}page {c.page ?? 'not given'}
                </span>
                <h3 className="text-lg font-bold">{c.label ?? c.control_type ?? 'Control not named'}</h3>
                {c.requirement && c.requirement !== c.council_words ? <p className="text-sm font-semibold leading-relaxed text-gray-800">{c.requirement}</p> : null}
                <p className="text-sm leading-relaxed">{c.council_words ?? c.requirement ?? 'Council wording not held'}</p>
                {c.clause && !c.clause_shown ? <p className="text-xs text-gray-600">Clause {c.clause}: label not checked against the page.</p> : null}
                <div className="text-xs leading-relaxed text-gray-600">
                  {c.version_checks?.status === 'ok' ? c.version_checks.versions.map((v) => (
                    <div key={v.version}>{v.version}: {v.result_words}{v.stale ? ' (check made on an older wording of this quote)' : ''}</div>
                  )) : c.version_checks?.status === 'unreadable' ? 'Could not be read.' : 'Not checked.'}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
