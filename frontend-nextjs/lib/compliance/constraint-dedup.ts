// prior-art-checked: grepped lib/ and components/ for "deduplicate|dedupe"; the
// only constraint deduplication in the tree was the inner closure in
// ComplianceDashboard.tsx that this file replaces. Extracted to its own module
// rather than exported from the component because importing that component into
// a test pulls in react-markdown, which Jest cannot load as CommonJS, so the
// collision below had no way to be tested where it lived.

import type { ComplianceConstraint } from '@/components/compliance/ComplianceDashboard';

/**
 * Drop constraints that are the same provision seen twice.
 *
 * The constraint's own identity is part of the fallback key. While a missing
 * clause was filled with 'Clause 4.3' for height and 'Clause 4.4' for FSR, those
 * invented values happened to keep the two apart. Removing them (2026-10-06)
 * made both keys '-<EPI name>' whenever the Planning Portal named an instrument
 * but no clause, so FSR collided with height and was dropped from the assessment
 * without a trace. Height and FSR carry no provision_id, so this is the branch
 * they take.
 */
export function deduplicateConstraints(
  constraints: ComplianceConstraint[],
): ComplianceConstraint[] {
  const seen = new Set<string>();
  return constraints.filter(c => {
    const key = c.provision_id
      ? `id-${c.provision_id}`
      : `${c.type}:${c.value}:${c.unit ?? ''}:${c.source.clause ?? ''}-${c.source.document ?? ''}`;

    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
