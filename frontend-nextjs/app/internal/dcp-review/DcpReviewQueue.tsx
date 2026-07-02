'use client';

// prior-art-checked: no existing DCP review-queue UI in the repo (audited 2026-06-20).
import { useCallback, useEffect, useState } from 'react';

interface ReviewItem {
  id: number;
  council: string;
  chapter_key: string;
  document_id: string | null;
  ref_number: string | null;
  change_type: 'changed' | 'added' | 'removed' | 'restructure';
  old_text: string | null;
  new_text: string | null;
  old_page: number | null;
  new_page: number | null;
  has_numeric_change: boolean;
  summary: string | null;
  pdf_url: string | null;
}

type Action = 'approve' | 'reject' | 'needs-info';

export default function DcpReviewQueue() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPdf, setShowPdf] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/dcp-review', { cache: 'no-store' });
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

  const act = useCallback(
    async (action: Action) => {
      const item = items[idx];
      if (!item || busy) return;
      setBusy(true);
      setError(null);
      try {
        const res = await fetch(`/api/dcp-review/${item.id}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action }),
        });
        if (!res.ok) {
          const json = await res.json().catch(() => ({}));
          throw new Error(json.error || 'action failed');
        }
        // Remove the resolved item; keep the cursor in range.
        setItems((prev) => prev.filter((it) => it.id !== item.id));
        setIdx((i) => Math.max(0, Math.min(i, items.length - 2)));
      } catch (e) {
        setError(e instanceof Error ? e.message : 'action failed');
      } finally {
        setBusy(false);
      }
    },
    [items, idx, busy],
  );

  // Approve/reject EVERY pending row of the current chapter in one call — for
  // accepting a whole clean re-extraction (e.g. a baseline swap) without clicking
  // through hundreds of rows. Still human-initiated: the reviewer clicks the button.
  const actChapter = useCallback(
    async (action: Action) => {
      const item = items[idx];
      if (!item || busy) return;
      setBusy(true);
      setError(null);
      try {
        const res = await fetch('/api/dcp-review/chapter', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action,
            council: item.council,
            chapter_key: item.chapter_key,
          }),
        });
        if (!res.ok) {
          const json = await res.json().catch(() => ({}));
          throw new Error(json.error || 'chapter action failed');
        }
        // Drop every row of this chapter; reset the cursor.
        setItems((prev) =>
          prev.filter(
            (it) => !(it.council === item.council && it.chapter_key === item.chapter_key),
          ),
        );
        setIdx(0);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'chapter action failed');
      } finally {
        setBusy(false);
      }
    },
    [items, idx, busy],
  );

  // Keyboard: A approve · R reject · N needs-info · J/K next/prev.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const k = e.key.toLowerCase();
      if (k === 'a') act('approve');
      else if (k === 'r') act('reject');
      else if (k === 'n') act('needs-info');
      else if (k === 'j' || e.key === 'ArrowDown') setIdx((i) => Math.min(i + 1, items.length - 1));
      else if (k === 'k' || e.key === 'ArrowUp') setIdx((i) => Math.max(i - 1, 0));
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [act, items.length]);

  if (loading) {
    return <main className="p-8 text-sm text-gray-500">Loading review queue…</main>;
  }
  if (error) {
    return (
      <main className="p-8 text-sm">
        <p className="text-red-600">Error: {error}</p>
        <button onClick={load} className="mt-2 rounded border px-3 py-1">Retry</button>
      </main>
    );
  }
  if (items.length === 0) {
    return <main className="p-8 text-sm text-gray-600">✅ Review queue empty — nothing pending.</main>;
  }

  const item = items[idx];
  const chapterCount = items.filter(
    (it) => it.council === item.council && it.chapter_key === item.chapter_key,
  ).length;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-4">
        <h1 className="text-xl font-semibold">DCP review queue — {items.length} pending</h1>
        <p className="text-xs text-gray-500">
          Keys: <kbd>A</kbd> approve · <kbd>R</kbd> reject · <kbd>N</kbd> needs-info · <kbd>J</kbd>/<kbd>K</kbd> next/prev
        </p>
      </header>

      <div className="grid grid-cols-[18rem_1fr] gap-4">
        {/* Worklist rail */}
        <ul className="max-h-[70vh] overflow-auto rounded border text-sm">
          {items.map((it, i) => (
            <li key={it.id}>
              <button
                onClick={() => setIdx(i)}
                className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left ${
                  i === idx ? 'bg-blue-50 font-medium' : 'hover:bg-gray-50'
                }`}
              >
                <span className="truncate">
                  {it.council} / {it.chapter_key} {it.ref_number ? `· ${it.ref_number}` : ''}
                </span>
                {it.has_numeric_change && (
                  <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">
                    NUM
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>

        {/* Detail + diff */}
        <section className="rounded border p-4">
          <div className="mb-3 flex items-center gap-2 text-sm">
            <span className="rounded bg-gray-100 px-2 py-0.5 font-mono">{item.change_type}</span>
            {item.has_numeric_change && (
              <span className="rounded bg-amber-100 px-2 py-0.5 font-semibold text-amber-800">
                numeric change — always human
              </span>
            )}
            <span className="text-gray-500">
              {item.council} / {item.chapter_key}
              {item.ref_number ? ` · ${item.ref_number}` : ''}
            </span>
          </div>

          {item.summary && (
            <p className="mb-3 rounded bg-blue-50 px-3 py-2 text-sm">{item.summary}</p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="mb-1 text-xs font-semibold text-gray-500">
                OLD {item.old_page ? `(p.${item.old_page})` : ''}
              </div>
              <pre className="min-h-[8rem] whitespace-pre-wrap rounded border bg-red-50/40 p-3 text-sm">
                {item.old_text ?? '—'}
              </pre>
            </div>
            <div>
              <div className="mb-1 text-xs font-semibold text-gray-500">
                NEW {item.new_page ? `(p.${item.new_page})` : ''}
              </div>
              <pre className="min-h-[8rem] whitespace-pre-wrap rounded border bg-green-50/40 p-3 text-sm">
                {item.new_text ?? '—'}
              </pre>
            </div>
          </div>

          {/* Source PDF — verify the NEW text against the actual council page.
              The page is approximate (extraction records the chunk's first page). */}
          {item.pdf_url && (
            <div className="mt-4 border-t pt-4">
              <button
                onClick={() => setShowPdf((v) => !v)}
                className="rounded border px-3 py-1.5 text-sm font-medium"
              >
                {showPdf ? 'Hide' : 'Show'} source PDF (near p.{item.new_page ?? item.old_page ?? 1})
              </button>
              {showPdf && (
                <iframe
                  title="source PDF page"
                  src={`${item.pdf_url}#page=${item.new_page ?? item.old_page ?? 1}&view=FitH`}
                  className="mt-3 h-[70vh] w-full rounded border"
                />
              )}
            </div>
          )}

          <div className="mt-4 flex gap-2">
            <button
              onClick={() => act('approve')}
              disabled={busy}
              className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Approve (A)
            </button>
            <button
              onClick={() => act('reject')}
              disabled={busy}
              className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Reject (R)
            </button>
            <button
              onClick={() => act('needs-info')}
              disabled={busy}
              className="rounded border px-4 py-2 text-sm font-medium disabled:opacity-50"
            >
              Needs info (N)
            </button>
          </div>

          {/* Chapter-level actions — accept/reject the whole current chapter at once. */}
          <div className="mt-4 flex items-center gap-2 border-t pt-4">
            <span className="text-xs text-gray-500">
              Whole chapter ({chapterCount} pending in {item.chapter_key}):
            </span>
            <button
              onClick={() => actChapter('approve')}
              disabled={busy}
              className="rounded bg-green-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              title={`Approve all ${chapterCount} pending changes in ${item.chapter_key}`}
            >
              Approve all {chapterCount} in this chapter
            </button>
            <button
              onClick={() => actChapter('reject')}
              disabled={busy}
              className="rounded border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 disabled:opacity-50"
              title={`Reject all ${chapterCount} pending changes in ${item.chapter_key}`}
            >
              Reject all in this chapter
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
