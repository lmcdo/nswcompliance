/**
 * prior-art-checked: reuse not viable -- lib/citation-display.ts holds the logic and wording
 * (reused here); no component renders it. This is the one shared presentational mark, extracted
 * from the inline markup in PageGroupedProvisions so every citation surface uses the same badge.
 *
 * The one "Citation not yet checked" mark (OC-20). Every surface that shows a rule's citation
 * renders this; __tests__/components/compliance/citation-badge-inventory.test.ts fails if one does not.
 * `checked` is the server's citation_checked (lib/citation-display isCitationChecked). Anything
 * other than `true` -- false, null, undefined -- shows the mark (fail closed).
 */
import React from 'react';
import { CITATION_UNCHECKED_LABEL, CITATION_UNCHECKED_TOOLTIP } from '@/lib/citation-display';

export function CitationUncheckedBadge({ checked, className = '' }: { checked?: boolean | null; className?: string }) {
  if (checked === true) return null;
  return (
    <span
      data-testid="citation-unchecked"
      title={CITATION_UNCHECKED_TOOLTIP}
      className={`inline-block rounded bg-amber-50 text-amber-800 border border-amber-200 px-1.5 py-0.5 text-[11px] font-normal ${className}`}
    >
      {CITATION_UNCHECKED_LABEL}
      <span className="sr-only"> {CITATION_UNCHECKED_TOOLTIP}</span>
    </span>
  );
}
