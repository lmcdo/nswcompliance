/**
 * Points to the built-form figures that show upper-level setbacks on some street frontages
 * of a centre (Ku-ring-gai). The figure legends are not served as rules; the figure is the source.
 * Same amber one-line style as DcpNotCoveredNotice.
 *
 * prior-art-checked: DcpNotCoveredNotice is council-wide and names chapters, not figure pages;
 * no other component links into a chapter PDF page.
 */
import type { FrontageFigureItem } from '@/lib/frontage-setback-figures';

export function DcpFrontageFigureNotice({ items, failed }: {
  items: FrontageFigureItem[] | null | undefined;
  failed?: boolean | null;
}) {
  if (failed) {
    return (
      <p
        data-testid="dcp-frontage-figure-notice"
        className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5 mb-3"
      >
        The built-form figures for this centre could not be loaded. Upper-level setbacks may apply to some
        street frontages: check the centre&apos;s built-form figures in the council&apos;s plan.
      </p>
    );
  }
  if (!items || items.length === 0) return null;
  return (
    <p
      data-testid="dcp-frontage-figure-notice"
      className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5 mb-3"
    >
      Upper-level setbacks apply to some street frontages in this centre:{' '}
      {items.map((i, idx) => (
        <span key={`${i.chapter_key}-${i.page}`}>
          {idx > 0 ? '; ' : ''}
          <a
            href={i.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            {i.figure ? `see Figure ${i.figure}, page ${i.page}` : `see page ${i.page}`}
          </a>
        </span>
      ))}
    </p>
  );
}
