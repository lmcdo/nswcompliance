'use client';

/**
 * Small shared pieces for showing one CDC check:
 * a status icon (pass / fail / not checked) and a hint line that shows the
 * stored figure with its clause and, on request, the verbatim law text.
 *
 * prior-art-checked: new presentational helper; the old components each hard-coded "Min 6.0m" style hints.
 */

import { Check, X, Minus } from 'lucide-react';
import type { CdcCheck } from '@/lib/cdc/housing-code-checks';
import { clauseLabel } from '@/lib/cdc/housing-code-checks';

export function StatusIcon({ status, small = false }: { status: CdcCheck['status']; small?: boolean }) {
  const size = small ? 'w-3 h-3' : 'w-3.5 h-3.5';
  if (status === 'pass') return <Check className={`${size} text-green-600`} aria-label="Met" />;
  if (status === 'fail') return <X className={`${size} text-red-500`} aria-label="Not met" />;
  return <Minus className={`${size} text-gray-400`} aria-label="Not checked" />;
}

/** "Min 4.5 m (clause)" for a decided check, "Not checked" otherwise. */
export function hintText(check: CdcCheck): string {
  if (check.status === 'not_checked' || check.required === null) return 'Not checked';
  const word = check.comparison === 'min' ? 'Min' : 'Max';
  const unit = check.unit === '' ? '' : ` ${check.unit}`;
  return `${word} ${check.required}${unit}`;
}

export function StandardHint({ check, className = 'text-xs text-gray-400' }: { check: CdcCheck; className?: string }) {
  return (
    <span className={className} title={check.reason ?? undefined}>
      {hintText(check)}
      {check.clause && <span> · {check.clause}</span>}
    </span>
  );
}

/** Expander with the verbatim law text (decided checks) or the reason (not checked). */
export function CheckDetail({ check }: { check: CdcCheck }) {
  if (check.status === 'not_checked') {
    return (
      <div className="text-xs text-gray-500">
        {check.reason ?? 'Not checked'}
        {check.storedClauses.length > 0 && (
          <span> Stored clauses: {check.storedClauses.join(', ')}.</span>
        )}
      </div>
    );
  }
  return (
    <details className="text-xs text-gray-500">
      <summary className="cursor-pointer">{clauseLabel(check.clause)}</summary>
      <blockquote className="mt-1 border-l-2 border-gray-200 pl-2 text-gray-600">{check.quote}</blockquote>
      {check.unmodelledClauses.length > 0 && (
        <p className="mt-1">
          Other stored rows for this standard that were not applied: {check.unmodelledClauses.join(', ')}.
        </p>
      )}
    </details>
  );
}
