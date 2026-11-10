/**
 * One line under the report when we have not been able to look at the council's
 * plan for over 30 days (DQ-153: the council's website blocks our monitor).
 * The date comes from the API (meta.plan_confirmed); no council is named here.
 *
 * prior-art-checked: reuse not viable because the nearest notice,
 * DcpLandApplicationNotice, words a land-application decision, not a check date.
 * Same amber one-line style.
 */
import { planCheckIsOld } from '@/lib/plan-confirmed';

interface Props {
  /** ISO date of the oldest check of this council's plan chapters, from the API. */
  checkedOn: string | null | undefined;
  now?: Date;
}

export function DcpPlanCheckNotice({ checkedOn, now }: Props) {
  if (!checkedOn || !planCheckIsOld(checkedOn, now ?? new Date())) return null;
  const date = new Date(checkedOn).toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Australia/Sydney' });
  return (
    <p
      data-testid="plan-check-notice"
      className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5 mb-3"
    >
      Council plan last checked against the council&apos;s website on {date}. The council may have changed it since.
    </p>
  );
}
