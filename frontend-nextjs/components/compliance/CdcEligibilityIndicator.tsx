'use client';

/**
 * CdcEligibilityIndicator Component
 *
 * Phase 5 of Rule-Based Provision Enrichment Plan.
 *
 * Displays a preliminary CDC (Complying Development Certificate) eligibility
 * indicator for a property. Shows:
 * - Green: "CDC pathway may be available" (no definite exclusions)
 * - Red: "CDC excluded" with reason (definite exclusion found)
 * - Yellow: "Verify with certifier" (uncertain status)
 *
 * Always includes disclaimer that this is preliminary only.
 */

import { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  useCdcEligibility,
  getCdcStatusLabel,
  getPrimaryExclusion,
  type CdcCheckResult,
  type CdcExclusion,
} from '@/hooks/useCdcEligibility';

interface CdcEligibilityIndicatorProps {
  /** Property address to check */
  address: string | null;
  /** Whether to show in compact mode (badge only) */
  compact?: boolean;
  /** Whether to show in expanded mode with all details */
  expanded?: boolean;
  /** Callback when more info is requested */
  onLearnMore?: () => void;
}

/**
 * Get icon for eligibility status
 */
function getStatusIcon(eligible: 'yes' | 'no' | 'maybe', className: string = 'w-5 h-5') {
  switch (eligible) {
    case 'no':
      return <XCircle className={`${className} text-red-500`} />;
    case 'maybe':
      return <AlertTriangle className={`${className} text-amber-500`} />;
    case 'yes':
      return <CheckCircle2 className={`${className} text-green-500`} />;
    default:
      return <HelpCircle className={`${className} text-gray-400`} />;
  }
}

/**
 * Get background color class for status
 */
function getStatusBgClass(eligible: 'yes' | 'no' | 'maybe'): string {
  switch (eligible) {
    case 'no':
      return 'bg-red-50 border-red-200';
    case 'maybe':
      return 'bg-amber-50 border-amber-200';
    case 'yes':
      return 'bg-green-50 border-green-200';
    default:
      return 'bg-gray-50 border-gray-200';
  }
}

/**
 * Get text color class for status
 */
function getStatusTextClass(eligible: 'yes' | 'no' | 'maybe'): string {
  switch (eligible) {
    case 'no':
      return 'text-red-700';
    case 'maybe':
      return 'text-amber-700';
    case 'yes':
      return 'text-green-700';
    default:
      return 'text-gray-700';
  }
}

/**
 * Compact badge-only view
 */
function CompactIndicator({
  data,
  isLoading,
}: {
  data: CdcCheckResult | null;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <Badge variant="outline" className="bg-gray-50">
        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
        Checking CDC...
      </Badge>
    );
  }

  if (!data) {
    return null;
  }

  const primaryExclusion = getPrimaryExclusion(data.exclusions);

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={`cursor-help ${getStatusBgClass(data.eligible)} ${getStatusTextClass(data.eligible)}`}
          >
            {getStatusIcon(data.eligible, 'w-3 h-3 mr-1')}
            {getCdcStatusLabel(data.eligible)}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <div className="text-xs space-y-1">
            <div className="font-medium">
              {data.eligible === 'no'
                ? 'CDC pathway not available'
                : 'CDC pathway may be available'}
            </div>
            {primaryExclusion && (
              <div className="text-red-600">{primaryExclusion}</div>
            )}
            <div className="text-gray-500 text-[10px] mt-1">
              Preliminary only - verify with certifier
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Full card view with details
 */
function FullIndicator({
  data,
  isLoading,
  error,
  expanded: initialExpanded,
  onLearnMore,
}: {
  data: CdcCheckResult | null;
  isLoading: boolean;
  error: string | null;
  expanded?: boolean;
  onLearnMore?: () => void;
}) {
  const [showDetails, setShowDetails] = useState(initialExpanded || false);

  if (isLoading) {
    return (
      <Card className="border-gray-200">
        <CardContent className="py-4">
          <div className="flex items-center gap-2 text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Checking CDC eligibility...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-amber-200 bg-amber-50">
        <CardContent className="py-4">
          <div className="flex items-center gap-2 text-amber-700">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm">Could not check CDC eligibility</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return null;
  }

  const primaryExclusion = getPrimaryExclusion(data.exclusions);
  const definiteExclusions = data.exclusions.filter(e => e.severity === 'definite');

  return (
    <Card className={`border ${getStatusBgClass(data.eligible)}`}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          <div className="flex items-center gap-2">
            {getStatusIcon(data.eligible)}
            <span className={getStatusTextClass(data.eligible)}>
              CDC Preliminary Eligibility
            </span>
          </div>
          <Badge
            variant="outline"
            className={`${getStatusBgClass(data.eligible)} ${getStatusTextClass(data.eligible)}`}
          >
            {getCdcStatusLabel(data.eligible)}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Primary message */}
        <div className={`text-sm ${getStatusTextClass(data.eligible)}`}>
          {data.eligible === 'no' ? (
            <div className="font-medium">
              This property appears to be excluded from the CDC pathway.
            </div>
          ) : (
            <div className="font-medium">
              CDC pathway may be available for this property.
            </div>
          )}
        </div>

        {/* Exclusions */}
        {definiteExclusions.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-xs font-medium text-gray-600">Exclusion Reasons:</div>
            {definiteExclusions.map((exc, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 text-sm text-red-700 bg-red-100 px-2 py-1.5 rounded"
              >
                <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{exc.reason}</span>
              </div>
            ))}
          </div>
        )}

        {/* Expandable details */}
        <button
          type="button"
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? (
            <ChevronUp className="w-3 h-3" />
          ) : (
            <ChevronDown className="w-3 h-3" />
          )}
          {showDetails ? 'Hide details' : 'Show checks performed'}
        </button>

        {showDetails && (
          <div className="space-y-3 pt-2 border-t border-gray-200">
            {/* Checks performed */}
            <div>
              <div className="text-xs font-medium text-gray-600 mb-1">
                Checks Performed ({data.checksPerformed.length}):
              </div>
              <div className="flex flex-wrap gap-1">
                {data.checksPerformed.map((check, idx) => (
                  <Badge key={idx} variant="outline" className="text-[10px] bg-white">
                    {check}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Warnings */}
            {data.warnings.length > 0 && (
              <div>
                <div className="text-xs font-medium text-amber-600 mb-1">
                  Limitations ({data.warnings.length}):
                </div>
                <ul className="text-xs text-gray-600 space-y-0.5 list-disc pl-4">
                  {data.warnings.slice(0, 5).map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Disclaimer */}
        <div className="text-[10px] text-gray-500 bg-gray-100 px-2 py-1.5 rounded">
          <strong>Disclaimer:</strong> {data.disclaimer}
        </div>

        {/* Learn more link */}
        {onLearnMore && (
          <button
            type="button"
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
            onClick={onLearnMore}
          >
            <ExternalLink className="w-3 h-3" />
            Learn more about CDC requirements
          </button>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Main component
 */
export function CdcEligibilityIndicator({
  address,
  compact = false,
  expanded = false,
  onLearnMore,
}: CdcEligibilityIndicatorProps) {
  const { data, isLoading, error } = useCdcEligibility(address);

  if (compact) {
    return <CompactIndicator data={data} isLoading={isLoading} />;
  }

  return (
    <FullIndicator
      data={data}
      isLoading={isLoading}
      error={error}
      expanded={expanded}
      onLearnMore={onLearnMore}
    />
  );
}

export default CdcEligibilityIndicator;
