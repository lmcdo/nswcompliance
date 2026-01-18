'use client';

/**
 * CdcComplianceCalculator Component
 *
 * Main container combining CDC development form and results display.
 * Collapsible section to be placed within StateLevelControls under
 * the SEPP Housing 2021 content.
 */

import { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Calculator,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCdcComplianceCalculator } from '@/hooks/useCdcComplianceCalculator';
import { useCdcEligibility, type CdcCheckResult } from '@/hooks/useCdcEligibility';
import { CdcDevelopmentForm } from './CdcDevelopmentForm';
import { CdcComplianceResults } from './CdcComplianceResults';

interface LotDimensions {
  area: number;
  frontage: number;
  depth: number;
  confidence?: number;
}

interface CdcComplianceCalculatorProps {
  /** Property address for eligibility check */
  address: string | null;
  /** Initial collapsed state */
  initialCollapsed?: boolean;
  /** Lot dimensions from cadastre/geometry calculations */
  lotDimensions?: LotDimensions | null;
  /** Lot size from property data */
  lotSize?: number | null;
}

/**
 * Auto-checks display from CDC eligibility check
 */
function AutoChecksDisplay({ data }: { data: CdcCheckResult | null }) {
  if (!data) return null;

  const getStatusIcon = (passed: boolean, uncertain: boolean = false) => {
    if (uncertain) return <AlertTriangle className="w-4 h-4 text-amber-500" />;
    if (passed) return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    return <XCircle className="w-4 h-4 text-red-500" />;
  };

  // Map checks performed to pass/fail based on exclusions
  const checkResults = data.checksPerformed.map((check) => {
    const relatedExclusion = data.exclusions.find((e) =>
      e.constraint.toLowerCase().includes(check.toLowerCase().split(' ')[0])
    );
    return {
      name: check,
      passed: !relatedExclusion,
      exclusion: relatedExclusion?.reason,
    };
  });

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
      <div className="text-sm font-semibold text-blue-900 mb-2">
        Auto-Checks (from property data)
      </div>
      <div className="flex flex-wrap gap-2">
        {checkResults.slice(0, 6).map((check, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs ${
              check.passed
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {getStatusIcon(check.passed)}
            <span>{check.name}</span>
          </div>
        ))}
      </div>
      {data.exclusions.length > 0 && (
        <div className="mt-2 space-y-1">
          {data.exclusions.map((exc, idx) => (
            <div
              key={idx}
              className="text-xs text-red-700 flex items-start gap-1"
            >
              <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
              <span>{exc.reason}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CdcComplianceCalculator({
  address,
  initialCollapsed = true,
  lotDimensions,
  lotSize,
}: CdcComplianceCalculatorProps) {
  const [isCollapsed, setIsCollapsed] = useState(initialCollapsed);
  const [showResults, setShowResults] = useState(false);

  // CDC eligibility auto-check
  const {
    data: eligibilityData,
    isLoading: eligibilityLoading,
  } = useCdcEligibility(address);

  // Build initial values from lot dimensions (auto-populate from cadastre)
  const initialValues = useMemo(() => {
    if (!lotDimensions && !lotSize) return undefined;

    const area = lotDimensions?.area || lotSize || 0;
    const frontage = lotDimensions?.frontage || 0;
    const depth = lotDimensions?.depth || 0;

    // If we have dimensions, we can estimate reasonable site coverage starting point
    // Default building footprint: leave 6m front + 3m rear + 0.9m each side
    const usableWidth = Math.max(0, frontage - 1.8); // 0.9m each side
    const usableDepth = Math.max(0, depth - 9); // 6m front + 3m rear
    const maxFootprint = usableWidth * usableDepth;
    const estimatedCoverage = area > 0 ? Math.min(50, Math.round((maxFootprint / area) * 100)) : 45;

    return {
      // Don't auto-populate setbacks - user should input their design
      // But show the lot info in the UI
      siteCoveragePercent: estimatedCoverage > 0 ? estimatedCoverage : 45,
      landscapedAreaPercent: 100 - estimatedCoverage > 30 ? 100 - estimatedCoverage : 35,
    };
  }, [lotDimensions, lotSize]);

  // Compliance calculator state
  const {
    form,
    updateField,
    updateSetback,
    validation,
    passCount,
    totalChecks,
    isFullyCompliant,
    reset,
  } = useCdcComplianceCalculator({ initialValues });

  // Check if property is excluded from CDC
  const isExcluded = eligibilityData?.eligible === 'no';

  const handleCheckCompliance = () => {
    setShowResults(true);
  };

  const handleReset = () => {
    reset();
    setShowResults(false);
  };

  // Summary badge for header
  const getSummaryBadge = () => {
    if (!showResults) return null;

    if (isFullyCompliant) {
      return (
        <Badge className="bg-green-100 text-green-800 border-green-300">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          All Pass
        </Badge>
      );
    }
    if (passCount >= totalChecks - 2) {
      return (
        <Badge className="bg-amber-100 text-amber-800 border-amber-300">
          <AlertTriangle className="w-3 h-3 mr-1" />
          {passCount}/{totalChecks}
        </Badge>
      );
    }
    return (
      <Badge className="bg-red-100 text-red-800 border-red-300">
        <XCircle className="w-3 h-3 mr-1" />
        {passCount}/{totalChecks}
      </Badge>
    );
  };

  return (
    <Card className="border-indigo-200 bg-indigo-50/30">
      <CardHeader
        className="cursor-pointer hover:bg-indigo-100/50 transition-colors py-3"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isCollapsed ? (
              <ChevronRight className="h-5 w-5 text-indigo-600" />
            ) : (
              <ChevronDown className="h-5 w-5 text-indigo-600" />
            )}
            <Calculator className="h-5 w-5 text-indigo-600" />
            <CardTitle className="text-base text-indigo-900">
              CDC Compliance Calculator
            </CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {getSummaryBadge()}
            <Badge className="bg-indigo-100 text-indigo-800">SEPP Housing</Badge>
          </div>
        </div>
      </CardHeader>

      {!isCollapsed && (
        <CardContent className="pt-0 space-y-4">
          {/* Disclaimer Header */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-amber-800">
                <strong>Preliminary guidance only.</strong> This calculator provides
                estimates based on SEPP Housing 2021 default standards. It does not
                replace a formal CDC assessment by a registered certifier.
              </p>
            </div>
          </div>

          {/* Auto-Checks from Property Data */}
          {eligibilityLoading ? (
            <div className="bg-gray-100 rounded-lg p-3 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            </div>
          ) : (
            <AutoChecksDisplay data={eligibilityData} />
          )}

          {/* Lot Dimensions from Cadastre */}
          {lotDimensions && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
              <div className="text-sm font-semibold text-indigo-900 mb-2">
                Lot Dimensions (from cadastre)
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Area:</span>{' '}
                  <span className="font-medium text-indigo-900">
                    {lotDimensions.area.toFixed(0)} m²
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Frontage:</span>{' '}
                  <span className="font-medium text-indigo-900">
                    {lotDimensions.frontage.toFixed(1)} m
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Depth:</span>{' '}
                  <span className="font-medium text-indigo-900">
                    {lotDimensions.depth.toFixed(1)} m
                  </span>
                </div>
              </div>
              {lotDimensions.confidence && lotDimensions.confidence < 0.8 && (
                <p className="text-xs text-amber-600 mt-2">
                  Note: Irregular lot shape - dimensions are estimates
                </p>
              )}
            </div>
          )}

          {/* Exclusion Warning */}
          {isExcluded && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="flex items-start gap-2 text-red-800">
                <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium">CDC Pathway Not Available</div>
                  <p className="text-sm mt-1">
                    This property has been identified as excluded from the CDC pathway.
                    A Development Application may be required instead.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Form Section */}
          {!isExcluded && (
            <>
              <div className="border-t border-indigo-200 pt-4">
                <div className="text-sm font-semibold text-indigo-900 mb-3">
                  PROPOSED DEVELOPMENT
                </div>
                <CdcDevelopmentForm
                  form={form}
                  validation={validation}
                  updateField={updateField}
                  updateSetback={updateSetback}
                  passCount={passCount}
                  totalChecks={totalChecks}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-center gap-3 pt-2">
                <Button
                  onClick={handleCheckCompliance}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  <Calculator className="w-4 h-4 mr-2" />
                  Check Compliance
                </Button>
                {showResults && (
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    className="border-indigo-300 text-indigo-700 hover:bg-indigo-50"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Reset
                  </Button>
                )}
              </div>

              {/* Results Section */}
              {showResults && (
                <div className="border-t border-indigo-200 pt-4">
                  <CdcComplianceResults
                    validation={validation}
                    passCount={passCount}
                    totalChecks={totalChecks}
                    bedrooms={form.bedrooms}
                  />
                </div>
              )}
            </>
          )}

          {/* External Links */}
          <div className="border-t border-indigo-200 pt-4 flex flex-wrap gap-2">
            <a
              href="https://www.planningportal.nsw.gov.au/publications/environmental-planning-instruments/state-environmental-planning-policy-housing-2021"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
            >
              <ExternalLink className="w-3 h-3" />
              SEPP Housing 2021
            </a>
            <a
              href="https://www.planning.nsw.gov.au/assess-and-regulate/development-assessment/planning-approval-pathways/complying-development"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
            >
              <ExternalLink className="w-3 h-3" />
              CDC Information
            </a>
            <a
              href="https://www.fairtrading.nsw.gov.au/trades-and-businesses/construction-and-trade-essentials/certifiers"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
            >
              <ExternalLink className="w-3 h-3" />
              Find a Certifier
            </a>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

export default CdcComplianceCalculator;
