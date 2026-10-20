/**
 * Lists areas of a council's plan whose rules may apply to this property: the property is in the
 * area's suburb, but we cannot tell whether it is inside the area. One collapsed amber section
 * per area; the rules are shown so the reader can check them, not as confirmed for this address.
 *
 * prior-art-checked: extends the council-wide not-covered notice (DcpNotCoveredNotice.tsx) with a
 * per-suburb block; that notice withholds rules, this one shows them with their uncertainty.
 */
import { pageLabel } from '@/lib/page-citation';
import type { Provision } from '@/components/compliance/PageGroupedProvisions';

export interface MayApplyArea {
  area_id: string;
  title: string;
  reason_code: string;
  reason_text: string;
  applies_to_quote: string;
  applies_to_page: number | string;
  suburb: string;
  provisions: Provision[];
}

export function DcpMayApplyBlock({ mayApply }: { mayApply: MayApplyArea[] | null | undefined }) {
  if (!mayApply || mayApply.length === 0) return null;
  return (
    <div data-testid="dcp-may-apply-block" className="mb-3 space-y-2">
      {mayApply.map((area) => {
        const rules = area.provisions ?? [];
        return (
          <details
            key={area.area_id}
            data-testid="dcp-may-apply-area"
            className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5"
          >
            <summary className="cursor-pointer">
              Rules for {area.title} may apply to this property ({rules.length} {rules.length === 1 ? 'rule' : 'rules'})
            </summary>
            <p className="mt-2">
              This property is in {area.suburb}. We can’t tell whether it is inside this area. {area.reason_text} The
              plan says: “{area.applies_to_quote}” (page {area.applies_to_page}). These rules are shown so you can
              check them; they are not confirmed for this address.
            </p>
            <ul className="mt-2 space-y-2">
              {rules.map((p) => {
                const page = pageLabel(p);
                return (
                  <li key={p.id} data-testid="dcp-may-apply-rule" className="bg-white border border-amber-200 rounded p-2 text-gray-800">
                    <p className="whitespace-pre-line">{p.provision_text}</p>
                    {page && <p className="mt-1 text-gray-500">{page}</p>}
                  </li>
                );
              })}
            </ul>
          </details>
        );
      })}
    </div>
  );
}
