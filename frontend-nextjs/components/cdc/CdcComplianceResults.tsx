'use client';

/**
 * CdcComplianceResults Component
 *
 * Shows one row per check. Each row is Met, Not met, or Not checked. A decided
 * row shows the stored figure and its clause, with the verbatim law text one
 * click away. A Not checked row shows the reason and the stored clauses and no
 * number.
 */

import { ArrowRight, FileText } from 'lucide-react';
import { FormValidation, CdcCheck } from './types';
import { StatusIcon, CheckDetail } from './CdcCheckBits';
import { shortfallText } from '@/lib/cdc/housing-code-checks';

interface CdcComplianceResultsProps {
  validation: FormValidation;
  passCount: number;
  totalChecks: number;
  failCount?: number;
  notCheckedCount?: number;
}

const ORDER: (keyof FormValidation)[] = [
  'front', 'sideLeft', 'sideRight', 'rear', 'siteCoverage', 'landscapedArea',
  'buildingHeight', 'storeys', 'parking',
];

function ResultRow({ check }: { check: CdcCheck }) {
  const decided = check.status !== 'not_checked' && check.required !== null;
  const comparison = check.comparison === 'max' ? '≤' : '≥';
  const unit = check.unit;
  const margin = check.margin;
  return (
    <div className="py-1.5 border-b border-gray-100 last:border-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusIcon status={check.status} />
          <span className="text-sm text-gray-700">{check.label}</span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {decided ? (
            <>
              <span className={check.status === 'pass' ? 'text-gray-600' : 'text-red-600 font-medium'}>
                {check.proposed}{unit} {comparison} {check.required}{unit}
              </span>
              <span className="text-xs text-gray-400 w-12 text-right">
                [{margin !== null && margin >= 0 ? '+' : '-'}{Math.abs(margin ?? 0).toFixed(1)}{unit}]
              </span>
            </>
          ) : (
            <span className="text-gray-500">Not checked</span>
          )}
        </div>
      </div>
      <div className="pl-6 pt-0.5">
        <CheckDetail check={check} />
      </div>
    </div>
  );
}

export function CdcComplianceResults({
  validation,
  passCount,
  totalChecks,
  failCount = 0,
  notCheckedCount = 0,
}: CdcComplianceResultsProps) {
  const allPass = passCount === totalChecks;
  const checks = ORDER.map((k) => validation[k]).filter(Boolean);
  const failed = checks.filter((c) => c.status === 'fail');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Results</span>
        <span className="text-sm font-medium text-gray-600">
          {passCount} met, {failCount} not met, {notCheckedCount} not checked
        </span>
      </div>

      <div className="bg-gray-50 rounded p-3">
        {checks.map((c) => (
          <ResultRow key={c.key} check={c} />
        ))}
      </div>

      {failed.length > 0 && (
        <div className="text-sm space-y-1.5">
          <div className="text-gray-600 font-medium">Not met:</div>
          {failed.map((c) => (
            <div key={c.key} className="flex items-start gap-2 text-gray-600">
              <ArrowRight className="w-3 h-3 mt-1 flex-shrink-0 text-gray-400" />
              <span>
                {c.label}: {shortfallText(c)} ({c.clause})
              </span>
            </div>
          ))}
        </div>
      )}

      {allPass && (
        <div className="text-sm text-gray-600 bg-gray-50 rounded p-3">
          Every check met its stored standard. Other controls can also apply; confirm with a registered certifier.
        </div>
      )}

      <div className="text-xs text-gray-400 space-y-1 pt-2 border-t border-gray-100">
        <div className="flex items-center gap-1.5">
          <FileText className="w-3 h-3" />
          <span className="font-medium">Disclaimer</span>
        </div>
        <p className="leading-relaxed">
          Uses only the Housing Code standards stored from the Codes SEPP (Part 3). A check marked
          Not checked was not assessed. Site conditions, easements and council controls can also apply.
        </p>
      </div>
    </div>
  );
}

export default CdcComplianceResults;
