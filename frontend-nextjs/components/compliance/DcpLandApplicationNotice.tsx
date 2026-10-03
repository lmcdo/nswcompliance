/**
 * What the report says when a council DCP does not apply, or may only partly
 * apply, to this property (DQ-120). The decision is made server-side by
 * lib/dcp-land-application.ts; this only words it.
 *
 * prior-art-checked: the nearest existing surfaces are the precinct warning in
 * ProvisionsByTocStructure.tsx (a one-line amber note, reused here for
 * 'partial') and DCPInterestForm (a "council not processed yet" form, which is
 * the wrong message — this council IS processed, its plan just does not cover
 * this land).
 */

import { Card, CardContent } from '@/components/ui/card';
import type { LandApplicationDecision } from '@/lib/dcp-land-application';

interface Props {
  decision: LandApplicationDecision;
}

export function DcpLandApplicationNotice({ decision }: Props) {
  const dcp = decision.dcp ?? 'This council’s development control plan';
  const others = decision.other_instruments.map((i) => i.name);

  if (decision.status === 'partial') {
    return (
      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5 mb-3">
        The NSW Planning Portal maps this property under {decision.required_lep} and also under{' '}
        {others.join(', ')}. {dcp} covers only the {decision.required_lep} land, so some of the
        controls below may not apply to part of this lot.
      </p>
    );
  }

  if (!decision.withhold) return null;

  return (
    <Card>
      <CardContent className="p-6 space-y-2 text-sm text-gray-800">
        <p className="font-semibold">{dcp} controls are not shown for this property.</p>
        {decision.status === 'excluded' ? (
          <p>
            {dcp} applies only to land covered by {decision.required_lep}. The NSW Planning
            Portal maps this property under {others.join(', ')}, which has its own planning
            controls. Those controls are not yet included here.
          </p>
        ) : (
          <p>
            {dcp} applies only to land covered by {decision.required_lep}, and the NSW Planning
            Portal did not return which plan covers this property. Rather than show controls that
            may not apply, none are shown.
          </p>
        )}
        {decision.source && <p className="text-xs text-gray-500">Source: {decision.source}.</p>}
      </CardContent>
    </Card>
  );
}
