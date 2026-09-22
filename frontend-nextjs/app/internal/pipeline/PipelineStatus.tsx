'use client';

import { useCallback, useEffect, useState } from 'react';

// The page answers three questions, in this order, because that is the order they
// matter in: what needs me, is the pipeline running, and is the corpus complete.
// Everything is read from live data -- nothing on this page is hand-maintained, which
// is the failing of /internal (a typed list of routes that has to be edited by hand).

interface Stage {
  id: string;
  label: string;
  last: string | null;
  staleDays: number | null | undefined;
}
interface QueueRow {
  council: string;
  chapter_key: string;
  status: string;
  n: number;
}
interface StuckChapter {
  council: string;
  chapter_key: string;
  changedDaysAgo: number | null | undefined;
}
interface Status {
  generatedAt: string;
  needsYou: { approvedUncommitted: number; pending: number; stuckChapters: number };
  stages: Stage[];
  ruleFormulation: {
    rows: { status: string; n: number }[];
    notProcessed: number;
    totalActionable: number;
    formulatedPct: number | null | undefined;
  };
  corpus: { served: number; council_rows: number } | null;
  queue: QueueRow[];
  stuckChapters: StuckChapter[];
  autoRejected: { council: string; chapter_key: string; n: number }[];
}

const AGE_WARN_DAYS = 3;
const AGE_BAD_DAYS = 14;

function ageTone(days: number | null | undefined): string {
  // `== null` on purpose: a key the API omits arrives as undefined, not null, and an
  // age of 0 ('today') is a real value that must not be swallowed by a truthiness test.
  if (days == null) return 'text-gray-500';
  if (days >= AGE_BAD_DAYS) return 'text-red-600 font-semibold';
  if (days >= AGE_WARN_DAYS) return 'text-amber-600';
  return 'text-green-700';
}

function ago(days: number | null | undefined): string {
  if (days == null) return 'never';
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}

export default function PipelineStatus() {
  const [data, setData] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/internal/pipeline-status', { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? `HTTP ${res.status}`);
      setData(json);
      setError(null);
    } catch (e) {
      // Show the failure. A status page that silently renders nothing is the bug.
      setError(e instanceof Error ? e.message : 'could not load pipeline status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !data) return <main className="p-8">Loading pipeline status…</main>;

  if (error) {
    return (
      <main className="p-8">
        <h1 className="text-2xl font-semibold">Pipeline status</h1>
        <p className="mt-4 rounded border border-red-300 bg-red-50 p-4 text-red-800">
          Could not read the pipeline: {error}
        </p>
        <button onClick={() => void load()} className="mt-4 rounded border px-3 py-1">
          Retry
        </button>
      </main>
    );
  }
  if (!data) return null;

  const { needsYou, stages, ruleFormulation: rf, corpus } = data;
  const nothingWaiting =
    needsYou.approvedUncommitted === 0 && needsYou.pending === 0 && needsYou.stuckChapters === 0;

  return (
    <main className="mx-auto max-w-5xl p-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Pipeline status</h1>
        <button onClick={() => void load()} className="rounded border px-3 py-1 text-sm">
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      <p className="mt-1 text-sm text-gray-500">
        Read live at {new Date(data.generatedAt).toLocaleString()}. Nothing here is
        hand-maintained.
      </p>

      {/* 1. What needs a person, first and largest. */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold">Needs you</h2>
        {nothingWaiting ? (
          <p className="mt-2 rounded border border-green-300 bg-green-50 p-4 text-green-800">
            Nothing is waiting. The pipeline is running unattended.
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {needsYou.approvedUncommitted > 0 && (
              <li className="rounded border border-amber-300 bg-amber-50 p-3">
                <strong>{needsYou.approvedUncommitted}</strong> rules are approved but not
                published yet — the work is done and not live.
              </li>
            )}
            {needsYou.pending > 0 && (
              <li className="rounded border border-amber-300 bg-amber-50 p-3">
                <strong>{needsYou.pending}</strong> rules are waiting for a decision.{' '}
                <a className="underline" href="/internal/dcp-review">
                  Open the review queue
                </a>
              </li>
            )}
            {needsYou.stuckChapters > 0 && (
              <li className="rounded border border-red-300 bg-red-50 p-3">
                <strong>{needsYou.stuckChapters}</strong> chapters changed at the council
                and have not been re-read.
              </li>
            )}
          </ul>
        )}
      </section>

      {/* 2. Is each stage doing anything. */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold">Stages — last time each one did something</h2>
        <p className="text-sm text-gray-500">
          Derived from the data each stage writes, not from a run log: this shows whether a
          stage <em>achieved</em> something. A stage that ran and correctly found nothing
          looks the same as one that did not run — that gap needs the dead-man&apos;s switch.
        </p>
        <table className="mt-3 w-full text-sm">
          <tbody>
            {stages.map((s) => (
              <tr key={s.id} className="border-b">
                <td className="py-2">{s.label}</td>
                <td className={`py-2 text-right ${ageTone(s.staleDays)}`}>{ago(s.staleDays)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* 3. Is the corpus actually finished. */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold">Rule formulation</h2>
        <p className="text-sm text-gray-500">
          Turning rule TEXT into structured numbers a search can use. This is the step that
          makes a planner&apos;s number real.
        </p>
        <p className="mt-2 text-3xl font-semibold">
          {rf.formulatedPct == null ? '—' : `${rf.formulatedPct}%`}
        </p>
        <p className="text-sm text-gray-600">
          of {rf.totalActionable.toLocaleString()} served rules have a structured rule behind
          them. {rf.notProcessed.toLocaleString()} have never been processed.
        </p>
        <table className="mt-3 w-full text-sm">
          <tbody>
            {rf.rows.map((r) => (
              <tr key={r.status} className="border-b">
                <td className="py-1">{r.status}</td>
                <td className="py-1 text-right">{r.n.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {corpus != null && (
          <p className="mt-2 text-sm text-gray-600">
            {corpus.served.toLocaleString()} rules served in total,{' '}
            {corpus.council_rows.toLocaleString()} of them from a council plan (the rest are
            state law).
          </p>
        )}
      </section>

      {data.stuckChapters.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Chapters waiting to be re-read</h2>
          <table className="mt-2 w-full text-sm">
            <tbody>
              {data.stuckChapters.map((c) => (
                <tr key={`${c.council}/${c.chapter_key}`} className="border-b">
                  <td className="py-1">{c.council}</td>
                  <td className="py-1">{c.chapter_key}</td>
                  <td className={`py-1 text-right ${ageTone(c.changedDaysAgo)}`}>
                    changed {ago(c.changedDaysAgo)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {data.autoRejected.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Thrown out automatically</h2>
          <p className="text-sm text-gray-500">
            Rules the pipeline refused because their own text was measurably broken — these
            never reached you. A sudden rise means a source or a reader has changed.
          </p>
          <table className="mt-2 w-full text-sm">
            <tbody>
              {data.autoRejected.map((r) => (
                <tr key={`${r.council}/${r.chapter_key}`} className="border-b">
                  <td className="py-1">{r.council}</td>
                  <td className="py-1">{r.chapter_key}</td>
                  <td className="py-1 text-right">{r.n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
