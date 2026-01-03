'use client';

/**
 * Housing SEPP Eligibility Card Component
 * Displays eligibility for Low/Mid-Rise housing types under SEPP (Housing) 2021
 * with full provenance to legislation clauses
 */

import { useState, useEffect } from 'react';
import {
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Home,
  CheckCircle2,
  XCircle,
  Info,
  Building
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

interface DevelopmentStandard {
  standardType: string;
  numericValue: number;
  unit: string;
  sourceClause: string;
  sourceProvisionId: number | null;
  effectiveDate: string;
}

interface EligibilityResult {
  developmentType: string;
  displayName: string;
  description: string;
  isEligible: boolean;
  eligibilityReason: string;
  standards: DevelopmentStandard[];
  effectiveDate: string;
  legislationUrl: string;
}

interface HousingSEPPEligibilityCardProps {
  zoneCode: string;
  lotSize: number;
  lotWidth: number;
  stationDistance?: number;
  isLMRArea?: boolean;
}

// Format standard type for display
function formatStandardType(standardType: string): string {
  const labels: Record<string, string> = {
    min_lot_size: 'Min Lot Size',
    min_lot_width: 'Min Lot Width',
    max_fsr: 'Max FSR',
    max_height: 'Max Building Height',
    parking_per_dwelling: 'Parking per Dwelling',
    min_subdivision_lot: 'Min Subdivision Lot',
    min_subdivision_width: 'Min Subdivision Width',
    max_storeys: 'Max Storeys',
    min_landscaped_area_percent: 'Min Landscaped Area',
    min_deep_soil_percent: 'Min Deep Soil Zone'
  };
  return labels[standardType] || standardType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// Format value with unit
function formatValue(value: number, unit: string): string {
  switch (unit) {
    case 'm²':
      return `${value}m²`;
    case 'm':
      return `${value}m`;
    case ':1':
      return `${value}:1`;
    case '%':
      return `${value}%`;
    case 'spaces':
      return value === 1 ? '1 space' : `${value} spaces`;
    case 'storeys':
      return value === 1 ? '1 storey' : `${value} storeys`;
    default:
      return `${value}${unit}`;
  }
}

function EligibilityRow({ result }: { result: EligibilityResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <div className={`rounded-lg border ${result.isEligible
        ? 'border-green-200 bg-green-50/50'
        : 'border-gray-200 bg-gray-50/50'
        }`}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full p-3 h-auto justify-between hover:bg-transparent"
          >
            <div className="flex items-center gap-3">
              {result.isEligible ? (
                <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
              ) : (
                <XCircle className="w-5 h-5 text-gray-400 flex-shrink-0" />
              )}
              <div className="text-left">
                <div className="font-medium text-sm text-gray-900">
                  {result.displayName}
                </div>
                <div className="text-xs text-gray-500">
                  {result.description}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {result.isEligible ? (
                <Badge className="bg-green-100 text-green-800 border-green-200">
                  Eligible
                </Badge>
              ) : (
                <Badge variant="secondary" className="bg-gray-100 text-gray-600">
                  Not Eligible
                </Badge>
              )}
              {expanded ? (
                <ChevronUp className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              )}
            </div>
          </Button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="px-3 pb-3 pt-0">
            {/* Eligibility reason */}
            <div className={`text-xs p-2 rounded mb-2 ${result.isEligible
              ? 'bg-green-100 text-green-800'
              : 'bg-amber-50 text-amber-800'
              }`}>
              {result.eligibilityReason}
            </div>

            {/* Standards table */}
            <div className="space-y-1">
              <div className="text-xs font-medium text-gray-500 mb-1">
                Development Standards (Clause references)
              </div>
              {result.standards.map((std, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between py-1 px-2 rounded hover:bg-white/50"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-700">
                      {formatStandardType(std.standardType)}
                    </span>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="w-3 h-3 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top">
                          <p className="text-xs">
                            Clause {std.sourceClause}
                            {std.sourceProvisionId && (
                              <span className="text-gray-400"> (ID: {std.sourceProvisionId})</span>
                            )}
                          </p>
                          <p className="text-xs text-gray-400">
                            Effective: {std.effectiveDate}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-gray-900 font-mono">
                      {formatValue(std.numericValue, std.unit)}
                    </span>
                    <span className="text-xs text-gray-400 font-mono">
                      §{std.sourceClause}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Legislation link */}
            <a
              href={result.legislationUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 mt-2"
            >
              View SEPP (Housing) 2021
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

export function HousingSEPPEligibilityCard({
  zoneCode,
  lotSize,
  lotWidth,
  stationDistance,
  isLMRArea
}: HousingSEPPEligibilityCardProps) {
  const [data, setData] = useState<{
    eligibleTypes: EligibilityResult[];
    propertyInfo: Record<string, unknown>;
    totalChecked: number;
    eligibleCount: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    const fetchEligibility = async () => {
      // Skip if missing required data
      if (!zoneCode || !lotSize || !lotWidth) {
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await fetch('/api/housing-sepp/eligibility', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            zoneCode,
            lotSize,
            lotWidth,
            stationDistance,
            isLMRArea
          })
        });

        if (!response.ok) {
          throw new Error('Failed to fetch eligibility');
        }

        const result = await response.json();
        if (result.success) {
          setData(result.data);
        } else {
          throw new Error(result.error || 'Unknown error');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to check eligibility');
      } finally {
        setLoading(false);
      }
    };

    fetchEligibility();
  }, [zoneCode, lotSize, lotWidth, stationDistance, isLMRArea]);

  // Loading state
  if (loading) {
    return (
      <Card className="border-emerald-200 bg-emerald-50/50">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Home className="w-5 h-5 text-emerald-600" />
            <CardTitle className="text-base font-semibold text-emerald-900">
              Multiple Occupancy Options
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            <div className="h-12 bg-emerald-200 rounded"></div>
            <div className="h-12 bg-emerald-200 rounded"></div>
            <div className="h-12 bg-emerald-200 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className="border-red-200 bg-red-50/50">
        <CardContent className="py-4">
          <p className="text-sm text-red-600">{error}</p>
        </CardContent>
      </Card>
    );
  }

  // No data or missing inputs
  if (!data || !data.eligibleTypes.length) {
    return (
      <Card className="border-gray-200 bg-gray-50/50">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Home className="w-5 h-5 text-gray-400" />
            <CardTitle className="text-base font-semibold text-gray-600">
              Multiple Occupancy Options
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            {!zoneCode || !lotSize || !lotWidth
              ? 'Lot size and frontage width are needed to check what housing types your property may be eligible for'
              : 'No multiple occupancy housing types are available in this zone under current NSW reforms'}
          </p>
        </CardContent>
      </Card>
    );
  }

  const eligibleCount = data.eligibleCount;
  const totalCount = data.totalChecked;
  const visibleResults = showAll ? data.eligibleTypes : data.eligibleTypes.slice(0, 4);

  return (
    <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50/80 to-white">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building className="w-5 h-5 text-emerald-600" />
            <CardTitle className="text-base font-semibold text-emerald-900">
              Multiple Occupancy Options
            </CardTitle>
          </div>
          <Badge
            variant="outline"
            className={eligibleCount > 0
              ? "text-green-700 border-green-300 bg-green-100/50"
              : "text-gray-600 border-gray-300 bg-gray-100/50"
            }
          >
            {eligibleCount} of {totalCount} options available
          </Badge>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Check what housing types you can build under NSW Low and Mid-Rise Housing reforms
        </p>
      </CardHeader>

      <CardContent className="pt-2">
        {/* Property summary */}
        <div className="mb-3 p-2 bg-white rounded border border-gray-100">
          <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600">
            <span>Your zone: <strong className="text-gray-900">{zoneCode}</strong></span>
            <span>Lot area: <strong className="text-gray-900">{lotSize}m²</strong></span>
            <span>Frontage: <strong className="text-gray-900">{lotWidth}m</strong></span>
            {stationDistance && (
              <span>To station: <strong className="text-gray-900">{stationDistance}m</strong></span>
            )}
          </div>
        </div>

        {/* Eligibility results */}
        <div className="space-y-2">
          {visibleResults.map((result) => (
            <EligibilityRow key={result.developmentType} result={result} />
          ))}
        </div>

        {/* Show more button */}
        {data.eligibleTypes.length > 4 && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-2 text-emerald-600 hover:text-emerald-800 hover:bg-emerald-100"
            onClick={() => setShowAll(!showAll)}
          >
            {showAll ? (
              <>
                <ChevronUp className="w-4 h-4 mr-1" />
                Show Less
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4 mr-1" />
                Show {data.eligibleTypes.length - 4} More
              </>
            )}
          </Button>
        )}

        {/* Footer with explanation */}
        <div className="mt-3 pt-2 border-t border-emerald-100">
          <p className="text-xs text-gray-500 mb-2">
            These options are based on NSW Low and Mid-Rise Housing reforms (July 2024 &amp; Feb 2025).
            Development standards override local council controls for eligible properties.
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">
              Source: SEPP (Housing) 2021
            </span>
            <a
              href="https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-emerald-600 hover:text-emerald-800 flex items-center gap-1"
            >
              View official legislation
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
