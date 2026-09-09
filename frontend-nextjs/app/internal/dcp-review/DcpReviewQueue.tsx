'use client';

// prior-art-checked: no existing DCP review-queue UI in the repo (audited 2026-06-20).
import { useCallback, useEffect, useMemo, useState } from 'react';

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
  suspect_reason: string | null;
  fidelity_status: 'grounded' | 'flagged' | null;
  fidelity_detail: string | null;
  source_page_verified: number | null;
  fidelity_source_quote: string | null;
}

interface ChapterGroup {
  council: string;
  chapter_key: string;
  suspect_reason: string | null;
  items: ReviewItem[];
  grounded: number;
  flagged: number;
}

type Action = 'approve' | 'reject' | 'needs-info';

// The fidelity gate records what it could not match as
// "numbers not in source: 15, 2.4". Pull those tokens back out.
function missingNumbers(detail: string | null): string[] {
  if (!detail) return [];
  const m = /numbers not in source:\s*(.*)/i.exec(detail);
  if (!m) return [];
  return m[1]
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

// Every place a flagged number actually appears in the rule text, with the
// words around it. Without this a reviewer is told "15 is not in the PDF" and
// has to search a whole page to find out that the 15 came from the "2.4-15"
// page footer. Showing the context answers that at a glance. Deliberately
// only SHOWS the surrounding text — it makes no judgement about whether the
// number is a real control, which is exactly what the human is here for.
function occurrencesOf(num: string, text: string | null): string[] {
  // new_text arrives from the API as untyped JSON: a non-string (a number, an
  // object) would throw on .indexOf/.slice and blank the whole review panel,
  // which is the one screen the human gate depends on. Guard the type, don't
  // just null-check it.
  if (typeof text !== 'string' || typeof num !== 'string' || !text || !num) return [];
  const out: string[] = [];
  let from = 0;
  while (out.length < 4) {
    const i = text.indexOf(num, from);
    if (i === -1) break;
    from = i + num.length;
    // Skip a match that is part of a longer number ("15" inside "150"), but
    // KEEP one preceded by "." or "-" — "2.4-15" is precisely the page-footer
    // case a reviewer most needs to see.
    const before = text[i - 1] ?? ' ';
    const after = text[i + num.length] ?? ' ';
    if (/\d/.test(before) || /\d/.test(after)) continue;
    const start = Math.max(0, i - 70);
    const end = Math.min(text.length, i + num.length + 70);
    const snippet = text.slice(start, end).replace(/\s+/g, ' ').trim();
    out.push(`${start > 0 ? '…' : ''}${snippet}${end < text.length ? '…' : ''}`);
  }
  return out;
}

export default function DcpReviewQueue() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPdf, setShowPdf] = useState(false);
  const [total, setTotal] = useState(0); // total pending on the server (queue caps loads at 500)
  const [editText, setEditText] = useState(''); // inline correction of the current row's text

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/dcp-review', { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'failed to load');
      const fetched: ReviewItem[] = json.items ?? [];
      setItems(fetched);
      setTotal(json.total ?? fetched.length);
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

  // Reset the inline-correction box to the current row's text whenever the row changes.
  useEffect(() => {
    setEditText(items[idx]?.new_text ?? '');
  }, [idx, items]);

  // Save an inline correction (edited text) and approve the row in one step — for fixing a
  // flagged value (e.g. 2.9m -> 0.9m) without leaving the screen.
  const saveCorrectionAndApprove = useCallback(async () => {
    const cur = items[idx];
    if (!cur || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/dcp-review/${cur.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'approve', edited_text: editText }),
      });
      if (!res.ok && res.status !== 404) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.error || 'save failed');
      }
      setItems((prev) => prev.filter((it) => it.id !== cur.id));
      setIdx((i) => Math.max(0, Math.min(i, items.length - 2)));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'save failed');
    } finally {
      setBusy(false);
    }
  }, [items, idx, busy, editText]);

  // The queue returns at most 500 rows. When the loaded batch is fully resolved but the
  // server still has pending rows, fetch the next batch — so we never falsely report
  // "empty" while thousands remain. Only a fetch that returns 0 shows the empty state.
  useEffect(() => {
    if (!loading && !busy && items.length === 0 && total > 0) load();
  }, [items.length, loading, busy, total, load]);

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
        // 404 = the row was already resolved (double-click / stale list). That's not an
        // error — just drop it and move on. Only other failures surface a banner.
        if (!res.ok && res.status !== 404) {
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
  const actChapterFor = useCallback(
    async (council: string, chapterKey: string, action: Action) => {
      if (busy) return;
      setBusy(true);
      setError(null);
      try {
        const res = await fetch('/api/dcp-review/chapter', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, council, chapter_key: chapterKey }),
        });
        // 404 = the chapter was already resolved (double-click / stale button). Treat it
        // as done rather than an error — just drop the chapter and move on.
        if (!res.ok && res.status !== 404) {
          const json = await res.json().catch(() => ({}));
          throw new Error(json.error || 'chapter action failed');
        }
        // Drop every row of this chapter; reset the cursor.
        setItems((prev) =>
          prev.filter((it) => !(it.council === council && it.chapter_key === chapterKey)),
        );
        setIdx(0);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'chapter action failed');
      } finally {
        setBusy(false);
      }
    },
    [busy],
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

  // Group the flat worklist into chapters; a chapter is "flagged" if the extraction
  // guards left a suspect_reason on it — those are the ones to review, not blind-approve.
  const chapters = useMemo<ChapterGroup[]>(() => {
    const map = new Map<string, ChapterGroup>();
    for (const it of items) {
      const key = `${it.council}/${it.chapter_key}`;
      let g = map.get(key);
      if (!g) {
        g = {
          council: it.council, chapter_key: it.chapter_key, suspect_reason: null,
          items: [], grounded: 0, flagged: 0,
        };
        map.set(key, g);
      }
      g.items.push(it);
      if (it.suspect_reason && !g.suspect_reason) g.suspect_reason = it.suspect_reason;
      if (it.fidelity_status === 'grounded') g.grounded += 1;
      else if (it.fidelity_status === 'flagged') g.flagged += 1;
    }
    return [...map.values()];
  }, [items]);
  const flaggedCount = chapters.filter((c) => c.suspect_reason).length;
  // Source-check totals across the loaded batch (the fidelity gate's verdict).
  const fidFlagged = items.filter((it) => it.fidelity_status === 'flagged').length;
  const fidGrounded = items.filter((it) => it.fidelity_status === 'grounded').length;

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
    // total > 0 means the loaded batch is cleared but more remain — the auto-reload
    // effect is fetching them; don't claim the queue is empty.
    return total > 0 ? (
      <main className="p-8 text-sm text-gray-500">Loading next batch… ({total} still pending)</main>
    ) : (
      <main className="p-8 text-sm text-gray-600">✅ Review queue empty — nothing pending.</main>
    );
  }

  const item = items[idx];
  const chapterCount = items.filter(
    (it) => it.council === item.council && it.chapter_key === item.chapter_key,
  ).length;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-4">
        <h1 className="text-xl font-semibold">
          DCP review — {chapters.length} sections
          {flaggedCount > 0 && (
            <span className="ml-2 rounded bg-amber-100 px-2 py-0.5 text-sm font-semibold text-amber-800">
              ⚠ {flaggedCount} need a careful look
            </span>
          )}
        </h1>
        <p className="text-xs text-gray-500">
          {items.length}{total > items.length ? ` of ${total}` : ''} changes across {chapters.length} sections
          {total > items.length ? ' (loaded 500 at a time — more load as you clear these)' : ''}. Approve a whole clean section
          with its <b>Approve</b> button; ⚠ sections were flagged by the extraction checks — open
          those and review before approving. Keys: <kbd>A</kbd>/<kbd>R</kbd>/<kbd>N</kbd> per row · <kbd>J</kbd>/<kbd>K</kbd> move.
        </p>
        {(fidFlagged > 0 || fidGrounded > 0) && (
          <div className="mt-2 rounded border border-gray-200 bg-gray-50 px-3 py-2 text-xs">
            <b>Source check:</b>{' '}
            <span className="font-semibold text-amber-800">⚠ {fidFlagged} need a look</span>
            {' · '}
            <span className="font-semibold text-green-700">{fidGrounded} matched the source PDF</span>
            . The flagged rows are listed first — review those; the rest matched the source and
            you can approve them in bulk. (A row <b>matched</b> when every number and its key
            words appear in the council&apos;s own PDF; <b>flagged</b> means one did not.)
          </div>
        )}
      </header>

      <div className="grid grid-cols-[20rem_1fr] gap-4">
        {/* Worklist rail — grouped by section, flagged sections highlighted */}
        <ul className="max-h-[70vh] overflow-auto rounded border text-sm">
          {chapters.map((ch) => {
            const active = item.council === ch.council && item.chapter_key === ch.chapter_key;
            return (
              <li key={`${ch.council}/${ch.chapter_key}`} className="border-b last:border-b-0">
                <div
                  className={`flex items-center justify-between gap-2 px-3 py-2 ${
                    ch.suspect_reason ? 'bg-amber-50' : ''
                  }`}
                >
                  <button
                    onClick={() => setIdx(items.indexOf(ch.items[0]))}
                    className="flex-1 truncate text-left"
                    title={ch.suspect_reason ?? undefined}
                  >
                    {ch.suspect_reason && <span aria-label="flagged">⚠ </span>}
                    <span className={active ? 'font-semibold' : ''}>{ch.chapter_key}</span>
                    <span className="text-gray-400"> ({ch.items.length})</span>
                    {ch.flagged > 0 && (
                      <span className="ml-1 text-[10px] text-amber-700">⚠{ch.flagged} to check</span>
                    )}
                  </button>
                  <button
                    onClick={() => actChapterFor(ch.council, ch.chapter_key, 'approve')}
                    disabled={busy}
                    className="shrink-0 rounded border border-green-600 px-2 py-0.5 text-[11px] font-medium text-green-700 disabled:opacity-50"
                    title={`Approve all ${ch.items.length} changes in ${ch.chapter_key}`}
                  >
                    Approve
                  </button>
                </div>
                {ch.suspect_reason && (
                  <div className="px-3 pb-1 text-[10px] text-amber-700">{ch.suspect_reason}</div>
                )}
                {active && (
                  <ul className="bg-gray-50/60">
                    {ch.items.map((it) => (
                      <li key={it.id}>
                        <button
                          onClick={() => setIdx(items.indexOf(it))}
                          className={`flex w-full items-center justify-between gap-2 py-1 pl-6 pr-3 text-left text-xs ${
                            it === item ? 'bg-blue-100 font-medium' : 'hover:bg-gray-100'
                          }`}
                        >
                          <span className="truncate">
                            {it.fidelity_status === 'flagged' && <span title="source check flagged this">⚠ </span>}
                            {it.ref_number ?? '(no ref)'}
                          </span>
                          {it.has_numeric_change && (
                            <span className="shrink-0 rounded bg-amber-100 px-1 text-[9px] font-semibold text-amber-800">
                              NUM
                            </span>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
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

          {item.fidelity_status === 'flagged' && (
            <div className="mb-3 rounded border border-amber-300 bg-amber-50 px-3 py-3 text-sm text-amber-900">
              <p className="font-semibold">⚠ This rule needs a human check.</p>
              <p className="mt-1">
                The source check could not match {item.fidelity_detail?.includes('number') ? 'a number' : 'some wording'} in
                this rule to the council&apos;s PDF
                {item.source_page_verified ? ` (page ${item.source_page_verified})` : ''}.
                {item.fidelity_detail ? ` [${item.fidelity_detail}]` : ''}
              </p>
              {item.fidelity_source_quote && (
                <div className="mt-2 rounded border border-amber-200 bg-white px-3 py-2 text-gray-800">
                  <div className="text-xs font-semibold text-gray-500">What the council&apos;s PDF says here:</div>
                  <div className="mt-1 italic">&ldquo;{item.fidelity_source_quote}&rdquo;</div>
                </div>
              )}

              {missingNumbers(item.fidelity_detail).length > 0 && (
                <div className="mt-2 rounded border border-amber-200 bg-white px-3 py-2 text-gray-800">
                  <div className="text-xs font-semibold text-gray-500">
                    Where each unmatched number sits in this rule:
                  </div>
                  {missingNumbers(item.fidelity_detail).map((num) => {
                    const ctx = occurrencesOf(num, item.new_text);
                    return (
                      <div key={num} className="mt-2">
                        <span className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs font-semibold">
                          {num}
                        </span>
                        {ctx.length === 0 ? (
                          <div className="mt-1 text-xs text-gray-600">
                            Does not appear in the rule text at all — usually means the checker
                            split it out of something else (a section number like 9.13, a date).
                          </div>
                        ) : (
                          ctx.map((c, i) => (
                            <div
                              key={i}
                              className="mt-1 border-l-2 border-amber-300 pl-2 font-mono text-xs leading-relaxed text-gray-700"
                            >
                              {c}
                            </div>
                          ))
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              <p className="mt-2 text-xs">
                Read the snippets above: if the number is a page footer (e.g. <b>2.4-15</b>), a
                section number, or a street address, the rule is fine — just <b>Approve</b>. If it
                is a real control (a setback, height, area, percentage), check it against the PDF
                and, if it is wrong, fix it in the box below and <b>Save correction &amp; approve</b>.
              </p>
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={4}
                className="mt-2 w-full rounded border border-amber-300 p-2 font-mono text-xs text-gray-900"
              />
              <button
                onClick={saveCorrectionAndApprove}
                disabled={busy}
                className="mt-2 rounded bg-amber-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              >
                Save correction &amp; approve
              </button>
            </div>
          )}
          {item.fidelity_status === 'grounded' && (
            <p className="mb-3 rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
              <b>Matched to source:</b> every number and its key words appear in the
              council&apos;s PDF{item.source_page_verified ? ` (page ${item.source_page_verified})` : ''}.
            </p>
          )}

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
              onClick={() => actChapterFor(item.council, item.chapter_key, 'approve')}
              disabled={busy}
              className="rounded bg-green-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              title={`Approve all ${chapterCount} pending changes in ${item.chapter_key}`}
            >
              Approve all {chapterCount} in this chapter
            </button>
            <button
              onClick={() => actChapterFor(item.council, item.chapter_key, 'reject')}
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
