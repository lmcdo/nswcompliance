'use client';

/**
 * ADG Summary Card Component
 * Displays key NSW Apartment Design Guide Design Criteria
 * for multi-dwelling developments (Residential Flat Buildings, etc.)
 */

import { useState, useEffect } from 'react';
import { ExternalLink, ChevronDown, ChevronUp, Building2, Info, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface SummaryMetric {
  criteriaId: string;
  label: string;
  summary: string;
  numericValue: number | null;
  numericUnit: string | null;
  secondaryValue: number | null;
  secondaryUnit: string | null;
  sectionCode: string;
  sourcePage: number;
  sourceUrl: string;
}

interface DocumentInfo {
  name: string;
  version: string;
  authority: string;
  legalStatus: string;
  parts: Array<{ number: number; name: string; pages: string }>;
}

interface ADGSummaryData {
  keyMetrics: SummaryMetric[];
  totalCriteria: number;
  appliesTo: string[];
  documentInfo: DocumentInfo;
}

interface ADGSummaryCardProps {
  developmentType: string;
  zoneCode?: string;
  onViewAllCriteria?: () => void;
}

// Zones that typically prohibit or restrict apartment developments
const APARTMENT_RESTRICTED_ZONES = [
  'R2',   // Low Density Residential - usually prohibits RFB
  'RU1', 'RU2', 'RU3', 'RU4', 'RU5', 'RU6',  // Rural zones
  'E1', 'E2', 'E3', 'E4',  // Environment zones (new)
  'C1', 'C2', 'C3', 'C4',  // Conservation zones (old)
  'W1', 'W2', 'W3',  // Waterway zones
  'SP1', 'SP2',  // Special Purpose (varies)
  'RE1', 'RE2',  // Recreation
  'IN1', 'IN2', 'IN3', 'IN4',  // Industrial
];

// Development types that trigger ADG requirements
const ADG_APPLICABLE_TYPES = [
  'residential_flat',
  'residential_flat_building',
  'multi_dwelling',
  'multi_dwelling_housing',
  'shop_top_housing',
  'boarding_house',
  'seniors_housing',
  'build_to_rent',
  'mixed_use'
];

export function ADGSummaryCard({ developmentType, zoneCode, onViewAllCriteria }: ADGSummaryCardProps) {
  const [data, setData] = useState<ADGSummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  // Check if zone might restrict apartments (for warning display)
  const zonePrefix = zoneCode?.split(' ')[0]?.toUpperCase();
  const isZoneRestricted = zonePrefix ? APARTMENT_RESTRICTED_ZONES.includes(zonePrefix) : false;

  useEffect(() => {
    // Always fetch - parent component controls visibility
    const fetchSummary = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/adg/summary');
        if (!response.ok) {
          throw new Error('Failed to fetch ADG summary');
        }
        const result = await response.json();
        if (result.success) {
          setData(result.data);
        } else {
          throw new Error(result.error || 'Unknown error');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load ADG requirements');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, []);

  // Loading state
  if (loading) {
    return (
      <Card className="border-purple-200 bg-purple-50/50">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-purple-600" />
            <CardTitle className="text-base font-semibold text-purple-900">
              NSW Apartment Design Guide
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            <div className="h-4 bg-purple-200 rounded w-3/4"></div>
            <div className="h-4 bg-purple-200 rounded w-1/2"></div>
            <div className="h-4 bg-purple-200 rounded w-2/3"></div>
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

  // No data
  if (!data) {
    return null;
  }

  const visibleMetrics = expanded ? data.keyMetrics : data.keyMetrics.slice(0, 5);

  return (
    <Card className="border-purple-200 bg-gradient-to-br from-purple-50/80 to-white">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-purple-600" />
            <CardTitle className="text-base font-semibold text-purple-900">
              {data.documentInfo.name}
            </CardTitle>
          </div>
          <Badge variant="outline" className="text-purple-700 border-purple-300 bg-purple-100/50">
            STATUTORY
          </Badge>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {data.documentInfo.version} | Authority: {data.documentInfo.authority}
        </p>
      </CardHeader>

      <CardContent className="pt-2">
        {/* Zone Restriction Warning */}
        {isZoneRestricted && (
          <div className="mb-3 p-2 bg-amber-50 border border-amber-200 rounded-md flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-amber-800">
              <span className="font-medium">Zone {zoneCode}</span> may prohibit or restrict apartment developments.
              Check LEP permissibility before proceeding.
            </div>
          </div>
        )}

        {/* Key Metrics */}
        <div className="space-y-2">
          {visibleMetrics.map((metric) => (
            <MetricRow key={metric.criteriaId} metric={metric} />
          ))}
        </div>

        {/* Expand/Collapse Button */}
        {data.keyMetrics.length > 5 && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-2 text-purple-600 hover:text-purple-800 hover:bg-purple-100"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>
                <ChevronUp className="w-4 h-4 mr-1" />
                Show Less
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4 mr-1" />
                Show {data.keyMetrics.length - 5} More
              </>
            )}
          </Button>
        )}

        {/* Building Separation Table (Section 3F) */}
        <div className="mt-4 pt-3 border-t border-purple-100">
          <h4 className="text-xs font-semibold text-purple-800 mb-2">
            Side/Rear Setbacks to Boundaries (3F-1)
          </h4>
          <p className="text-xs text-gray-500 mb-2">
            Min distance from windows/balconies to boundary
          </p>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="pb-1">Building</th>
                <th className="pb-1">Living/Bed</th>
                <th className="pb-1">Bath/Store</th>
              </tr>
            </thead>
            <tbody className="text-gray-700">
              <tr>
                <td className="py-0.5">Up to 12m</td>
                <td className="py-0.5 font-medium">6m</td>
                <td className="py-0.5">3m</td>
              </tr>
              <tr>
                <td className="py-0.5">12-25m</td>
                <td className="py-0.5 font-medium">9m</td>
                <td className="py-0.5">4.5m</td>
              </tr>
              <tr>
                <td className="py-0.5">Over 25m</td>
                <td className="py-0.5 font-medium">12m</td>
                <td className="py-0.5">6m</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="mt-3 pt-2 border-t border-purple-100 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {data.totalCriteria} Design Criteria | ADG March 2023
          </span>
          {onViewAllCriteria && (
            <Button
              variant="link"
              size="sm"
              className="text-purple-600 p-0 h-auto"
              onClick={onViewAllCriteria}
            >
              View All
              <ExternalLink className="w-3 h-3 ml-1" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface MetricRowProps {
  metric: SummaryMetric;
}

function MetricRow({ metric }: MetricRowProps) {
  const formatValue = () => {
    if (!metric.numericValue) return '';

    let value = '';
    switch (metric.numericUnit) {
      case 'percent':
        value = `${metric.numericValue}%`;
        break;
      case 'metres':
        value = `${metric.numericValue}m`;
        break;
      case 'sqm':
        value = `${metric.numericValue}m\u00B2`;
        break;
      case 'cubic_m':
        value = `${metric.numericValue}m\u00B3`;
        break;
      case 'hours':
        value = `${metric.numericValue}hrs`;
        break;
      case 'units':
        value = `${metric.numericValue}`;
        break;
      default:
        value = `${metric.numericValue} ${metric.numericUnit || ''}`;
    }

    // Add secondary value if exists
    if (metric.secondaryValue && metric.secondaryUnit) {
      switch (metric.secondaryUnit) {
        case 'hours':
          value += ` @ ${metric.secondaryValue}hrs`;
          break;
        case 'metres':
          value += ` @ ${metric.secondaryValue}m`;
          break;
        case 'sqm':
          value += ` to ${metric.secondaryValue}m\u00B2`;
          break;
        case 'cubic_m':
          value += ` to ${metric.secondaryValue}m\u00B3`;
          break;
        default:
          value += ` / ${metric.secondaryValue}${metric.secondaryUnit}`;
      }
    }

    return value;
  };

  return (
    <div className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-purple-50/50 group">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-700 truncate">
          {metric.label}
        </span>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="w-3.5 h-3.5 text-gray-400 hover:text-purple-500 cursor-help flex-shrink-0" />
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs">
              <p className="text-xs">{metric.summary}</p>
              <p className="text-xs text-gray-400 mt-1">
                Section {metric.sectionCode} | Page {metric.sourcePage}
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-purple-700 font-mono">
          {formatValue()}
        </span>
        <span className="text-xs text-gray-400 font-mono">
          {metric.criteriaId}
        </span>
      </div>
    </div>
  );
}
