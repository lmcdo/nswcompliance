'use client';

// prior-art-checked: no existing extracted-value trust-review UI in the repo
// (audited 2026-07-02). Distinct from DcpReviewQueue (DCP change-detection).
// Shows each flagged setback VALUE next to the clause it cites, with three
// reversible decisions: keep, correct (with a required source), or remove.
import { useCallback, useEffect, useState } from 'react';

interface FlaggedControl {
  id: number;
  lga: string;
  dev_type: string;
  control_type: string;
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  condition: string | null;
  section_ref: string | null;
  source_text: string | null;
  review_reason: string | null;
  source_chapter_key: string | null;
}

function formatValue(c: FlaggedControl): string {
  const unit = c.unit ?? '';
  if (c.value_min !== null && c.value_max !== null && c.value_min !== c.value_max) {
    return `${c.value_min}–${c.value_max} ${unit}`.trim();
  }
  const v = c.value_min ?? c.value_max;
  return v === null ? '—' : `${v} ${unit}`.trim();
}

export default function SetbackReviewQueue() {
  const [items, setItems] = useState<FlaggedControl[]>([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fix form state (only used for the "correct" action).
  const [fixing, setFixing] = useState(false);
  const [fixMin, setFixMin] = useState('');
  const [fixMax, setFixMax] = useState('');
  const [fixRef, setFixRef] = useState('');
  const [fixSource, setFixSource] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/internal/setback-review', { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'failed to load');
      setItems(json.items ?? []);
      setIdx(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetFixForm = () => {
    setFixing(false);
    setFixMin('');
    setFixMax('');
    setFixRef('');
    setFixSource('');
  };

  const act = useCallback(
    async (action: 'confirm' | 'remove' | 'fix', extra?: Record<string, unknown>) => {
      const item = items[idx];
      if (!item || busy) return;
      setBusy(true);
      setError(null);
      try {
        const res = await fetch(`/api/internal/setback-review/${item.id}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, ...(extra ?? {}) }),
        });
        const json = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(json.error || 'action failed');
        // Drop the resolved row and keep the cursor in range.
        setItems((prev) => prev.filter((it) => it.id !== item.id));
        setIdx((i) => Math.max(0, Math.min(i, items.length - 2)));
        resetFixForm();
      } catch (e) {
        setError(e instanceof Error ? e.message : 'action failed');
      } finally {
        setBusy(false);
      }
    },
    [items, idx, busy],
  );

  const submitFix = () => {
    if (!fixMin && !fixMax) {
      setError('Enter a corrected value (min and/or max).');
      return;
    }
    if (!fixRef.trim()) {
      setError('A corrected value needs a source citation (clause / section reference).');
      return;
    }
    act('fix', {
      value_min: fixMin || null,
      value_max: fixMax || null,
      section_ref: fixRef.trim(),
      source_text: fixSource.trim() || null,
    });
  };

  if (loading) {
    return <main className="p-8 text-sm text-gray-500">Loading review queue…</main>;
  }
  if (error && items.length === 0) {
    return (
      <main className="p-8 text-sm">
        <p className="text-red-600">Error: {error}</p>
        <button onClick={load} className="mt-2 rounded border px-3 py-1">Retry</button>
      </main>
    );
  }
  if (items.length === 0) {
    return <main className="p-8 text-sm text-gray-600">Review queue empty — no setback values are flagged.</main>;
  }

  const item = items[idx];

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-4">
        <h1 className="text-xl font-semibold">Setback value review — {items.length} flagged</h1>
        <p className="text-xs text-gray-500">
          Each value below was flagged as possibly not traceable to its cited clause. Keep it, correct it (with a source), or remove it. All actions are reversible.
        </p>
      </header>

      <div className="grid grid-cols-[20rem_1fr] gap-4">
        {/* Worklist rail */}
        <ul className="max-h-[70vh] overflow-auto rounded border text-sm">
          {items.map((it, i) => (
            <li key={it.id}>
              <button
                onClick={() => { setIdx(i); resetFixForm(); }}
                className={`flex w-full flex-col gap-0.5 px-3 py-2 text-left ${
                  i === idx ? 'bg-blue-50 font-medium' : 'hover:bg-gray-50'
                }`}
              >
                <span className="truncate">{it.lga} · {it.control_type}</span>
                <span className="text-[11px] text-gray-500">{it.dev_type} · {formatValue(it)}</span>
              </button>
            </li>
          ))}
        </ul>

        {/* Detail */}
        <section className="rounded border p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded bg-gray-100 px-2 py-0.5 font-mono">{item.control_type}</span>
            <span className="text-gray-500">{item.lga} · {item.dev_type}</span>
            {item.section_ref && (
              <span className="rounded bg-gray-100 px-2 py-0.5 text-xs">ref {item.section_ref}</span>
            )}
          </div>

          <div className="mb-3">
            <div className="text-xs font-semibold text-gray-500">Stored value</div>
            <div className="text-2xl font-semibold">{formatValue(item)}</div>
            {item.condition && <div className="text-xs text-gray-500">condition: {item.condition}</div>}
          </div>

          <div className="mb-3">
            <div className="mb-1 text-xs font-semibold text-gray-500">Cited clause text</div>
            <pre className="min-h-[6rem] whitespace-pre-wrap rounded border bg-gray-50 p-3 text-sm">
              {item.source_text ?? '— no clause text stored —'}
            </pre>
          </div>

          {item.review_reason && (
            <p className="mb-3 rounded bg-amber-50 px-3 py-2 text-xs text-amber-900">
              Flagged: {item.review_reason}
            </p>
          )}

          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

          {!fixing ? (
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={() => act('confirm')}
                disabled={busy}
                className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Keep — value matches the clause
              </button>
              <button
                onClick={() => { setError(null); setFixing(true); }}
                disabled={busy}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Correct the value…
              </button>
              <button
                onClick={() => act('remove')}
                disabled={busy}
                className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Remove — not in the clause
              </button>
            </div>
          ) : (
            <div className="mt-4 rounded border bg-blue-50/40 p-3">
              <div className="mb-2 text-sm font-medium">Corrected value (must cite a source)</div>
              <div className="flex flex-wrap gap-2">
                <label className="text-xs">
                  min
                  <input value={fixMin} onChange={(e) => setFixMin(e.target.value)} inputMode="decimal"
                    className="mt-0.5 block w-24 rounded border px-2 py-1 text-sm" placeholder="e.g. 6" />
                </label>
                <label className="text-xs">
                  max
                  <input value={fixMax} onChange={(e) => setFixMax(e.target.value)} inputMode="decimal"
                    className="mt-0.5 block w-24 rounded border px-2 py-1 text-sm" placeholder="optional" />
                </label>
                <label className="flex-1 text-xs">
                  source citation (clause / section ref) — required
                  <input value={fixRef} onChange={(e) => setFixRef(e.target.value)}
                    className="mt-0.5 block w-full rounded border px-2 py-1 text-sm" placeholder="e.g. Part C 4.2.1" />
                </label>
              </div>
              <label className="mt-2 block text-xs">
                clause text (optional)
                <textarea value={fixSource} onChange={(e) => setFixSource(e.target.value)}
                  className="mt-0.5 block w-full rounded border px-2 py-1 text-sm" rows={2} />
              </label>
              <div className="mt-2 flex gap-2">
                <button onClick={submitFix} disabled={busy}
                  className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                  Save correction
                </button>
                <button onClick={() => { resetFixForm(); setError(null); }} disabled={busy}
                  className="rounded border px-4 py-2 text-sm font-medium disabled:opacity-50">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
