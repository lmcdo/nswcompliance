'use client';

/**
 * Pathway Summary Card
 *
 * Shows comprehensive pathway triage at a glance - all approval pathways
 * analyzed for the property (Pattern Book CDC, Exempt & Complying, Housing SEPP, Standard DA).
 *
 * Positioned at top of SEPP tab to give users immediate overview of fastest pathway.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface PathwaySummaryCardProps {
  propertyData: any;
  patternBookStatus?: 'ELIGIBLE' | 'INELIGIBLE' | 'CONDITIONAL';
  exemptComplyingCount?: number;
  housingLmrApplicable?: boolean;
  zoneCode?: string;
}

export function PathwaySummaryCard({
  propertyData,
  patternBookStatus,
  exemptComplyingCount = 0,
  housingLmrApplicable = false,
  zoneCode
}: PathwaySummaryCardProps) {

  // Determine fastest pathway
  const getFastestPathway = (): string => {
    if (patternBookStatus === 'ELIGIBLE') {
      return 'Pattern Book CDC (10-day approval)';
    }
    if (exemptComplyingCount > 0) {
      return `Exempt & Complying Development (${exemptComplyingCount} work types available)`;
    }
    if (housingLmrApplicable) {
      return 'Housing SEPP (Low-Mid Rise) streamlined assessment';
    }
    return 'Standard Development Application (50+ days)';
  };

  const fastestPathway = getFastestPathway();

  return (
    <Card className="border-blue-200 bg-blue-50/30 mb-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Approval Pathways for This Property</CardTitle>
          <Badge className="bg-blue-100 text-blue-800">Automated Triage</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Fastest Pathway Highlight */}
        {(patternBookStatus === 'ELIGIBLE' || exemptComplyingCount > 0) && (
          <div className="bg-green-50 border-2 border-green-500 rounded-lg p-4 mb-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold text-green-900 text-base mb-1">
                  ✓ Fast-Track Available
                </div>
                <div className="text-sm text-green-800">
                  {fastestPathway}
                </div>
                <div className="text-xs text-green-700 mt-1">
                  {patternBookStatus === 'ELIGIBLE'
                    ? 'Pre-approved designs with 10-day processing'
                    : `${exemptComplyingCount} work ${exemptComplyingCount === 1 ? 'type' : 'types'} eligible for streamlined approval`
                  }
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">

          {/* Pattern Book CDC */}
          <div className="flex items-center gap-2">
            {patternBookStatus === 'ELIGIBLE' ? (
              <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
            ) : patternBookStatus === 'CONDITIONAL' ? (
              <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
            )}
            <span>
              Pattern Book CDC (10 days): <strong>
                {patternBookStatus === 'ELIGIBLE' ? 'Eligible' :
                 patternBookStatus === 'CONDITIONAL' ? 'Conditional' :
                 'Ineligible'}
              </strong>
            </span>
          </div>

          {/* Exempt & Complying */}
          <div className="flex items-center gap-2">
            {exemptComplyingCount > 0 ? (
              <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 text-gray-400 flex-shrink-0" />
            )}
            <span>
              Exempt & Complying: <strong>
                {exemptComplyingCount > 0
                  ? `${exemptComplyingCount} work types available`
                  : 'Not applicable'}
              </strong>
            </span>
          </div>

          {/* Housing SEPP (LMR) */}
          <div className="flex items-center gap-2">
            {housingLmrApplicable ? (
              <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 text-gray-400 flex-shrink-0" />
            )}
            <span>
              Housing SEPP (LMR): <strong>
                {housingLmrApplicable ? 'Applicable' : 'Not applicable'}
              </strong>
              {!housingLmrApplicable && zoneCode && (
                <span className="text-xs text-gray-500 ml-1"> ({zoneCode} zone)</span>
              )}
            </span>
          </div>

          {/* Standard DA - Always available */}
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-blue-600 flex-shrink-0" />
            <span>
              Standard DA (50+ days): <strong>Available</strong>
            </span>
          </div>

        </div>

        {/* Summary */}
        <div className="mt-3 pt-3 border-t border-blue-100">
          <p className="text-xs text-gray-500">
            PlotDetect analyzed all approval pathways and compliance requirements for this property
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
