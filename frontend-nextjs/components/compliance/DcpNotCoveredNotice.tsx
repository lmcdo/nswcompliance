/**
 * Says so when rules for particular areas are held back for this council (OC-21).
 * The areas have no outline yet, so this shows for every address in the council.
 * Same amber one-line style as the precinct warning in ProvisionsByTocStructure.tsx.
 *
 * prior-art-checked: DcpLandApplicationNotice is a per-property LEP gate and
 * RegulatoryCurrencyNotice is about plan dates; neither carries a council-wide withheld list.
 */
import { chapterLabel, type NotCovered } from '@/lib/not-covered';

export function DcpNotCoveredNotice({ notCovered }: { notCovered: NotCovered | null | undefined }) {
  if (!notCovered || notCovered.chapters.length === 0) return null;
  const names = notCovered.chapters.map((c) => c.title || chapterLabel(c.chapter_key)).join('; ');
  return (
    <p
      data-testid="dcp-not-covered-notice"
      className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5 mb-3"
    >
      Some rules in this council’s plan apply only to particular areas that we have not mapped
      yet. Those rules are not shown here. Check the council’s plan for: {names}.
    </p>
  );
}
