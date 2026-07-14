'use client';

/**
 * CdcComplianceCalculator Component
 *
 * Main container combining CDC development form and results display.
 * Uses neutral styling to avoid competing with app's color-coded sections.
 */

import { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Calculator,
  Check,
  X,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  Info,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCdcComplianceCalculator } from '@/hooks/useCdcComplianceCalculator';
import { useCdcEligibility, type CdcCheckResult } from '@/hooks/useCdcEligibility';
import { battleaxeAwareLotWidth, battleaxeAwareLotDepth } from '@/lib/geometry/effective-lot-width';
import { CdcDevelopmentForm } from './CdcDevelopmentForm';
import { CdcComplianceResults } from './CdcComplianceResults';

interface LotDimensions {
  area: number;
  frontage: number;
  depth: number;
  confidence?: number;
  lotType?: 'rectangular' | 'battleaxe' | 'irregular';
  battleaxe?: { isBattleaxe?: boolean; mainLotWidth?: number | null; mainLotArea?: number | null } | null;
}

interface CdcComplianceCalculatorProps {
  address: string | null;
  initialCollapsed?: boolean;
  lotDimensions?: LotDimensions | null;
  lotSize?: number | null;
}

/**
 * Compact auto-checks display - minimal color, icon-driven
 */
function AutoChecksDisplay({ data }: { data: CdcCheckResult | null }) {
  if (!data) return null;

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
    <div className="space-y-2">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        Auto-Checks
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {checkResults.slice(0, 6).map((check, idx) => (
          <div key={idx} className="flex items-center gap-1.5 text-sm">
            {check.passed ? (
              <Check className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <X className="w-3.5 h-3.5 text-red-600" />
            )}
            <span className={check.passed ? 'text-gray-700' : 'text-gray-500 line-through'}>
              {check.name}
            </span>
          </div>
        ))}
      </div>
      {data.exclusions.length > 0 && (
        <div className="text-xs text-red-600 mt-1">
          {data.exclusions.map((exc, idx) => (
            <span key={idx}>
              {idx > 0 && ' · '}
              {exc.reason}
            </span>
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

  const {
    data: eligibilityData,
    isLoading: eligibilityLoading,
  } = useCdcEligibility(address);

  const initialValues = useMemo(() => {
    if (!lotDimensions && !lotSize) return undefined;

    const area = lotDimensions?.area || lotSize || 0;
    // For a battleaxe, lotDimensions.frontage/depth describe the access handle;
    // the buildable-footprint estimate must use the head (mainLotWidth and the
    // derived head depth), or coverage is badly understated. Non-battleaxe lots
    // return the raw frontage/depth unchanged.
    const frontage = battleaxeAwareLotWidth(lotDimensions) ?? 0;
    const depth = battleaxeAwareLotDepth(lotDimensions) ?? 0;

    const usableWidth = Math.max(0, frontage - 1.8);
    const usableDepth = Math.max(0, depth - 9);
    const maxFootprint = usableWidth * usableDepth;
    const estimatedCoverage = area > 0 ? Math.min(50, Math.round((maxFootprint / area) * 100)) : 45;

    return {
      siteCoveragePercent: estimatedCoverage > 0 ? estimatedCoverage : 45,
      landscapedAreaPercent: 100 - estimatedCoverage > 30 ? 100 - estimatedCoverage : 35,
    };
  }, [lotDimensions, lotSize]);

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

  const isExcluded = eligibilityData?.eligible === 'no';

  const handleCheckCompliance = () => setShowResults(true);
  const handleReset = () => {
    reset();
    setShowResults(false);
  };

  // Minimal summary indicator
  const getSummaryIndicator = () => {
    if (!showResults) return null;

    if (isFullyCompliant) {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-green-700 font-medium">
          <Check className="w-3.5 h-3.5" />
          {passCount}/{totalChecks}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs text-gray-600 font-medium">
        {passCount}/{totalChecks}
      </span>
    );
  };

  return (
    <Card className="border-gray-200 bg-white shadow-sm">
      <CardHeader
        className="cursor-pointer hover:bg-gray-50 transition-colors py-3 px-4"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            )}
            <Calculator className="h-4 w-4 text-gray-500" />
            <CardTitle className="text-sm font-medium text-gray-900">
              CDC Compliance Calculator
            </CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {getSummaryIndicator()}
            <Badge variant="outline" className="text-xs text-gray-500 border-gray-300 font-normal">
              SEPP Housing
            </Badge>
          </div>
        </div>
      </CardHeader>

      {!isCollapsed && (
        <CardContent className="pt-0 px-4 pb-4 space-y-4">
          {/* Disclaimer - subtle */}
          <div className="flex items-start gap-2 text-xs text-gray-500 bg-gray-50 rounded p-2">
            <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <span>
              Preliminary guidance only. Does not replace assessment by a registered certifier.
            </span>
          </div>

          {/* Auto-Checks */}
          {eligibilityLoading ? (
            <div className="h-8 bg-gray-100 rounded animate-pulse" />
          ) : (
            <AutoChecksDisplay data={eligibilityData} />
          )}

          {/* Lot Dimensions - clean, minimal. For a battleaxe the raw
              frontage/depth classify arbitrary edges of the L (the main
              property card suppresses them for the same reason) — show the
              main-lot width/depth the calculator itself uses instead. */}
          {lotDimensions && (
            <div className="border-t border-gray-100 pt-3">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Lot Dimensions
              </div>
              <div className="flex gap-6 text-sm">
                <div>
                  <span className="text-gray-500">Area</span>{' '}
                  <span className="font-medium text-gray-900">{lotDimensions.area.toFixed(0)}m²</span>
                </div>
                {lotDimensions.lotType === 'battleaxe' ? (
                  <>
                    {(battleaxeAwareLotWidth(lotDimensions) ?? 0) > 0 && (
                      <div>
                        <span className="text-gray-500">Main lot width</span>{' '}
                        <span className="font-medium text-gray-900">
                          {(battleaxeAwareLotWidth(lotDimensions) as number).toFixed(1)}m
                        </span>
                      </div>
                    )}
                    {(battleaxeAwareLotDepth(lotDimensions) ?? 0) > 0 && (
                      <div>
                        <span className="text-gray-500">Main lot depth</span>{' '}
                        <span className="font-medium text-gray-900">
                          {(battleaxeAwareLotDepth(lotDimensions) as number).toFixed(1)}m
                        </span>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div>
                      <span className="text-gray-500">Frontage</span>{' '}
                      <span className="font-medium text-gray-900">{lotDimensions.frontage.toFixed(1)}m</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Depth</span>{' '}
                      <span className="font-medium text-gray-900">{lotDimensions.depth.toFixed(1)}m</span>
                    </div>
                  </>
                )}
              </div>
              {lotDimensions.lotType === 'battleaxe' && (
                <p className="text-xs text-gray-400 mt-1 italic">
                  Battleaxe (flag) lot — width and depth describe the main lot, excluding the access way
                </p>
              )}
              {lotDimensions.confidence && lotDimensions.confidence < 0.8 && lotDimensions.lotType !== 'battleaxe' && (
                <p className="text-xs text-gray-400 mt-1 italic">
                  Irregular lot - dimensions estimated
                </p>
              )}
            </div>
          )}

          {/* Exclusion Warning */}
          {isExcluded && (
            <div className="border border-gray-200 rounded p-3 bg-gray-50">
              <div className="flex items-start gap-2">
                <X className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-sm font-medium text-gray-900">CDC Pathway Not Available</div>
                  <p className="text-xs text-gray-600 mt-0.5">
                    This property requires a Development Application.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Form Section */}
          {!isExcluded && (
            <>
              <div className="border-t border-gray-100 pt-4">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
                  Proposed Development
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
                  size="sm"
                  className="bg-gray-900 hover:bg-gray-800 text-white"
                >
                  <Calculator className="w-3.5 h-3.5 mr-1.5" />
                  Check Compliance
                </Button>
                {showResults && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleReset}
                    className="border-gray-300 text-gray-600 hover:bg-gray-50"
                  >
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                    Reset
                  </Button>
                )}
              </div>

              {/* Results Section */}
              {showResults && (
                <div className="border-t border-gray-100 pt-4">
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

          {/* External Links - subtle */}
          <div className="border-t border-gray-100 pt-3 flex flex-wrap gap-4">
            <a
              href="https://www.planningportal.nsw.gov.au/publications/environmental-planning-instruments/state-environmental-planning-policy-housing-2021"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
            >
              <ExternalLink className="w-3 h-3" />
              SEPP Housing 2021
            </a>
            <a
              href="https://www.planning.nsw.gov.au/assess-and-regulate/development-assessment/planning-approval-pathways/complying-development"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
            >
              <ExternalLink className="w-3 h-3" />
              CDC Information
            </a>
            <a
              href="https://www.fairtrading.nsw.gov.au/trades-and-businesses/construction-and-trade-essentials/certifiers"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
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
