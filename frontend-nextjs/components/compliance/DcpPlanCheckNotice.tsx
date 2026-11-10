/**
 * One line under the report when we have not been able to look at the council's
 * plan for over 14 days, have never looked, or the council's website is blocking
 * our check (DQ-153 -- the same rule as the red number). The facts come from the
 * API (meta.plan_check); no council is named here.
 *
 * prior-art-checked: reuse not viable because the nearest notice,
 * DcpLandApplicationNotice, words a land-application decision, not a check date.
 * Same amber one-line style.
 */
import { planNotice, type PlanCheck } from '@/lib/plan-confirmed';

interface Props {
  check: PlanCheck | null | undefined;
  now?: Date;
}

export function DcpPlanCheckNotice({ check, now }: Props) {
  const kind = planNotice(check, now ?? new Date());
  if (!kind || !check) return null;
  let text: string;
  if (kind === 'never') {
    text = "We have not yet checked this council's plan against the council's website. The council may have changed it.";
  } else {
    const date = check.checked_on
      ? new Date(check.checked_on).toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Australia/Sydney' })
      : null;
    const lead = kind === 'blocked'
      ? "The council's website is not letting our check reach its plan."
      : '';
    text = `${lead}${lead ? ' ' : ''}${date ? `Council plan last checked against the council's website on ${date}.` : "We have no date for our last check of this council's plan."} The council may have changed it since.`;
  }
  return (
    <p
      data-testid="plan-check-notice"
      className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5 mb-3"
    >
      {text}
    </p>
  );
}
