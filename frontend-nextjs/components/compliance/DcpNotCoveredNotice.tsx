/**
 * Says so when rules for particular areas are held back for this council (OC-21).
 * The areas have no outline yet, so this shows for every address in the council. For each part of
 * the plan it gives the plan's name for it, why we cannot place it, and a link to the plan page.
 * Same amber style as DcpMayApplyBlock.tsx (collapsed list when there are more than three).
 *
 * prior-art-checked: DcpLandApplicationNotice is a per-property LEP gate and
 * RegulatoryCurrencyNotice is about plan dates; neither carries a council-wide withheld list.
 */
import { chapterLabel, type NotCovered } from '@/lib/not-covered';

const COLLAPSE_AFTER = 3;

/** The link to the plan at the page: only a PDF address can take a #page anchor. */
function planHref(url: string | undefined, page: number | null | undefined): string | null {
  if (!url) return null;
  const isPdf = /\.pdf(\?|#|$)/i.test(url);
  return isPdf && typeof page === 'number' && page > 0 && !url.includes('#') ? `${url}#page=${page}` : url;
}

export function DcpNotCoveredNotice({
  notCovered,
  chapterPdfUrls,
}: {
  notCovered: NotCovered | null | undefined;
  chapterPdfUrls?: Record<string, string> | null;
}) {
  if (!notCovered || notCovered.chapters.length === 0) return null;
  const lines = (
    <ul className="mt-2 space-y-2">
      {notCovered.chapters.map((c) => {
        const href = planHref(chapterPdfUrls?.[c.chapter_key], c.page);
        return (
          <li key={c.chapter_key} data-testid="dcp-not-covered-chapter" className="bg-white border border-amber-200 rounded p-2 text-gray-800">
            <p className="font-medium">{c.title || chapterLabel(c.chapter_key)}</p>
            {c.reason_text && <p className="mt-1">{c.reason_text}</p>}
            {href && (
              <p className="mt-1">
                <a href={href} target="_blank" rel="noopener noreferrer" className="underline text-sky-800">
                  Read it in the plan{typeof c.page === 'number' ? ` (page ${c.page})` : ''}
                </a>
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
  const heading = 'Rules for particular areas we could not place on the map';
  const lead =
    'These parts of the council’s plan apply only to certain land. We could not tell from the map whether this property is in that land, so their rules are not listed below. Read them in the plan if they may apply to you.';
  const box = 'text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5 mb-3';
  if (notCovered.chapters.length > COLLAPSE_AFTER) {
    return (
      <details data-testid="dcp-not-covered-notice" className={box}>
        <summary className="cursor-pointer">{heading} ({notCovered.chapters.length})</summary>
        <p className="mt-2">{lead}</p>
        {lines}
      </details>
    );
  }
  return (
    <div data-testid="dcp-not-covered-notice" className={box}>
      <p className="font-medium">{heading}</p>
      <p className="mt-1">{lead}</p>
      {lines}
    </div>
  );
}
