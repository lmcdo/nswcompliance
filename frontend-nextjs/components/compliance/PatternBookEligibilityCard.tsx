'use client';

/**
 * Pattern Book CDC Eligibility Card
 *
 * Displays Pattern Book Complying Development eligibility assessment
 * Positioned in SEPP & LEP tab (StateLevelControls) ABOVE Housing SEPP card
 *
 * Features:
 * - Status badge (ELIGIBLE, CONDITIONAL, INELIGIBLE)
 * - Exclusion blockers with SEPP references + DCP cross-references
 * - Numeric standard failures
 * - Alternative pathway recommendations
 * - Navigation to DCP tab for heritage/other blockers
 * - CDC Compliance Calculator (shown only when ELIGIBLE) for buildable capacity
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileImage,
  FileText,
  Shield,
  ArrowRight,
  Clock
} from 'lucide-react';
import { AuthorityColors } from '@/lib/design-tokens';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { CdcComplianceCalculator } from '../cdc/CdcComplianceCalculator';

interface LotDimensions {
  area: number;
  frontage: number;
  depth: number;
  confidence?: number;
}

interface StrataInfo {
  isStrata: boolean;
  source: string | null;
  strataUnit: string | null;
}

interface PatternBookEligibilityCardProps {
  propertyData: any;
  onNavigateToDcp?: (topic: string, hcaSlug?: string) => void;
  lotDimensions?: LotDimensions | null;
  lotSize?: number | null;
  address?: string | null;
  strataInfo?: StrataInfo;
}

interface Exclusion {
  exclusionType: string;
  title: string; // Transformed from exclusionType
  description: string; // From API 'reason'
  sepp_provision: string; // Extracted from sourceClause
  sepp_pdf_page: number | null; // Extracted from sourceClause text
  sepp_pdf_path: string; // PDF folder path (e.g., 'sepp-housing', 'sepp-transport-infrastructure')
  override_available: boolean; // Merged from overrideCheck
  override_condition?: string; // From overrideCheck
  override_notes?: string; // From overrideCheck
}

interface NumericFailure {
  metricName: string;
  required: number;
  actual: number;
  unit: string;
  operator: 'min' | 'max';
  gap: number;
}

interface EligibilityResult {
  status: 'ELIGIBLE' | 'INELIGIBLE' | 'CONDITIONAL';
  pathway: string;
  exclusions?: Exclusion[];
  numeric_failures?: NumericFailure[];
  numeric_standards_met?: boolean;
  lot_size?: number;
  frontage?: number;
  professional_guidance?: {
    alternative_pathways: string[];
    next_steps: string[];
    estimated_complexity: 'low' | 'medium' | 'high';
  };
  reasons?: string[];
  numericCheck?: any;
  nextSteps?: string[];
}

// Helper: Transform exclusionType to human-readable title
function getExclusionTitle(exclusionType: string): string {
  const titles: Record<string, string> = {
    heritage: 'Heritage Conservation Area',
    flood_planning_area: 'Flood Planning Area',
    bushfire_prone: 'Bushfire Prone Land',
    acid_sulfate_soils: 'Acid Sulfate Soils',
    aircraft_noise: 'Aircraft Noise Exposure',
    threatened_species: 'Threatened Species Habitat',
    coastal_erosion: 'Coastal Erosion Risk',
    protected_area: 'Protected Environmental Area',
    unsewered: 'Unsewered Land'
  };
  return titles[exclusionType] || exclusionType.replace(/_/g, ' ');
}

// Helper: Extract page number from sourceClause text
function extractPageNumber(sourceClause: string): number | null {
  const match = sourceClause.match(/Page (\d+)/i);
  return match ? parseInt(match[1], 10) : null;
}

// Helper: Extract clause reference from sourceClause
function extractClauseReference(sourceClause: string): string {
  // Remove the " - Page X" suffix if present
  return sourceClause.replace(/ - Page \d+$/i, '').trim();
}

// Helper: Extract SEPP PDF folder path from sourceClause
function extractSeppPdfPath(sourceClause: string): string {
  // Map SEPP names to PDF folder paths (must match R2 bucket structure)
  const lowerClause = sourceClause.toLowerCase();

  // Biodiversity & Conservation (heritage exclusions)
  if (lowerClause.includes('biodiversity') || lowerClause.includes('conservation')) {
    return 'sepp-biodiversity-conservation-2021';
  }
  // Housing SEPP (2021 version)
  if (lowerClause.includes('housing') || lowerClause.includes('sepp housing')) {
    return 'sepp-housing-2021';
  }
  // Transport & Infrastructure (2021 version)
  if (lowerClause.includes('transport') && lowerClause.includes('infrastructure')) {
    return 'sepp-transport-infrastructure-2021';
  }
  // Exempt & Complying Development Codes
  if (lowerClause.includes('exempt and complying') || lowerClause.includes('codes sepp')) {
    return 'sepp-exempt-complying';
  }
  // Resilience & Hazards
  if (lowerClause.includes('resilience') || lowerClause.includes('hazards')) {
    return 'sepp-resilience-hazards';
  }
  // Sustainable Buildings (BASIX)
  if (lowerClause.includes('sustainable buildings') || lowerClause.includes('basix')) {
    return 'sepp-sustainable-buildings';
  }

  // Default fallback to Housing 2021
  console.warn('Unknown SEPP in sourceClause, defaulting to sepp-housing-2021:', sourceClause);
  return 'sepp-housing-2021';
}

// Helper: Transform API response to component format
function transformExclusions(
  exclusionCheck: any,
  overrideCheck: any
): Exclusion[] {
  if (!exclusionCheck?.details || exclusionCheck.details.length === 0) {
    return [];
  }

  // Create a map of override data by exclusionType
  const overrideMap = new Map<string, any>();
  if (overrideCheck?.details) {
    overrideCheck.details.forEach((override: any) => {
      overrideMap.set(override.exclusionType, override);
    });
  }

  // Transform and merge
  return exclusionCheck.details.map((exc: any) => {
    const override = overrideMap.get(exc.exclusionType);

    return {
      exclusionType: exc.exclusionType,
      title: getExclusionTitle(exc.exclusionType),
      description: exc.reason,
      sepp_provision: extractClauseReference(exc.sourceClause || ''),
      sepp_pdf_page: extractPageNumber(exc.sourceClause || ''),
      sepp_pdf_path: extractSeppPdfPath(exc.sourceClause || ''),
      override_available: override?.canOverride || false,
      override_condition: override?.condition,
      override_notes: override?.notes
    };
  });
}

export function PatternBookEligibilityCard({
  propertyData,
  onNavigateToDcp,
  lotDimensions,
  lotSize,
  address,
  strataInfo,
}: PatternBookEligibilityCardProps) {
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [viewingPdf, setViewingPdf] = useState<{ pageNumber: number; url: string; label: string } | null>(null);
  const [transformedExclusions, setTransformedExclusions] = useState<Exclusion[]>([]);

  // Fetch eligibility from API
  useEffect(() => {
    if (!propertyData) {
      setLoading(false);
      return;
    }

    const fetchEligibility = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch('/api/pathway/pattern-book-eligibility', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            propertyData: propertyData
          })
        });

        if (!response.ok) {
          throw new Error('Failed to check Pattern Book eligibility');
        }

        const data = await response.json();
        const eligibilityData = data.data?.eligibility || data;
        setEligibility(eligibilityData);

        // Transform exclusions to component format
        const transformed = transformExclusions(
          eligibilityData.exclusionCheck,
          eligibilityData.overrideCheck
        );
        setTransformedExclusions(transformed);

        // Auto-collapse when INELIGIBLE to reduce visual clutter (users can expand if needed)
        // Auto-expand if CONDITIONAL (needs user attention) or ELIGIBLE (celebrate!)
        setExpanded(eligibilityData.status === 'CONDITIONAL' || eligibilityData.status === 'ELIGIBLE');
      } catch (err) {
        console.error('Pattern Book eligibility check failed:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchEligibility();
  }, [propertyData]);

  if (loading) {
    return (
      <Card className="border-l-4 border-l-gray-300 bg-gray-50 animate-pulse">
        <CardHeader>
          <div className="h-6 bg-gray-200 rounded w-1/2"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-l-4 border-l-red-500 bg-red-50">
        <CardHeader>
          <CardTitle className="text-red-900">Pattern Book Eligibility Check Failed</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-700">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!eligibility) return null;

  const isEligible = eligibility.status === 'ELIGIBLE';
  const isConditional = eligibility.status === 'CONDITIONAL';
  const isIneligible = eligibility.status === 'INELIGIBLE';

  return (
    <>
      {strataInfo?.isStrata && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg px-4 py-3 flex items-start gap-2 text-sm">
          <AlertTriangle className="h-4 w-4 text-orange-500 flex-shrink-0 mt-0.5" />
          <span className="text-orange-800">
            <span className="font-semibold">Strata unit — </span>
            Pattern Book CDC applies to new buildings on the parent lot, not individual unit alterations. The result below describes what could be built on this lot as a scheme. Unit works require strata by-laws and owners corporation consent.
          </span>
        </div>
      )}
      <Card className={`border-l-4 ${
        isEligible ? 'border-l-green-500 bg-green-50' :
        isConditional ? 'border-l-amber-500 bg-amber-50' :
        'border-l-red-500 bg-red-50'
      }`}>
        <CardHeader
          className="cursor-pointer hover:bg-white/50 transition-colors"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className="bg-purple-100 text-purple-800">
                SEPP Housing 2021
              </Badge>
              <Badge variant="outline" className="text-xs">
                Pattern Book CDC Pathway
              </Badge>
              <Badge variant="outline" className="text-xs text-gray-500 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated Feb 2026
              </Badge>
            </div>

            <div className="flex items-center gap-3">
              {expanded ?
                <ChevronDown className="h-5 w-5 text-gray-500" /> :
                <ChevronRight className="h-5 w-5 text-gray-500" />
              }
              <CardTitle className="text-lg">
                Pattern Book CDC Eligibility
              </CardTitle>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                isEligible ? 'bg-green-600 text-white' :
                isConditional ? 'bg-amber-600 text-white' :
                'bg-red-600 text-white'
              }`}>
                {eligibility.status}
              </span>
            </div>

            <p className="text-sm text-gray-600">
              {isEligible ?
                'Property may be eligible for Pattern Book Complying Development Certificate (10-day approval pathway)' :
              isConditional ?
                'Property may be eligible subject to additional assessments and override provisions' :
                'Property is not eligible for Pattern Book CDC pathway - Development Application (DA) required'
              }
            </p>

            {/* Show primary reason when collapsed and ineligible */}
            {!expanded && isIneligible && eligibility.reasons && eligibility.reasons.length > 0 && (
              <div className="text-xs text-red-700 ml-8 flex items-center gap-2">
                <span className="font-medium">Reason:</span>
                <span>{eligibility.reasons[0]}</span>
                {eligibility.reasons.length > 1 && (
                  <span className="text-red-600">+{eligibility.reasons.length - 1} more</span>
                )}
              </div>
            )}
          </div>
        </CardHeader>

        {expanded && (
          <CardContent className="space-y-6">
            {/* Pathway analysis statistics */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-xs font-medium text-blue-900 mb-2">Comprehensive Pathway Analysis</p>
              <div className="text-xs text-blue-800 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">32</span>
                  <span>exclusion triggers checked</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">37</span>
                  <span>numeric standards verified</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">68</span>
                  <span>override rules evaluated</span>
                </div>
              </div>
              <p className="text-[10px] text-blue-600 mt-2 italic">
                Exclusion triggers: SEPP (Exempt &amp; Complying) Codes 2008 Schedule 1 — Pattern Book CDC standards: SEPP (Housing) 2021 Part 3
              </p>
            </div>

            {/* ELIGIBLE: Show summary and next steps */}
            {isEligible && (
              <div className="bg-white rounded-lg p-4 space-y-4">
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="font-medium text-green-900">No Exclusions Apply</h4>
                    <p className="text-sm text-green-700 mt-1">
                      Property does not trigger any Pattern Book exclusions. Proceed with Pattern Book design standards.
                    </p>
                  </div>
                </div>

                {/* Numeric standards summary */}
                {eligibility.numeric_standards_met && (
                  <div className="border-t pt-3">
                    <h5 className="text-sm font-medium text-gray-700 mb-2">Numeric Standards</h5>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      {eligibility.lot_size && (
                        <div>
                          <span className="text-gray-500">Lot size:</span>
                          <span className="ml-2 font-medium text-green-600">✓ {eligibility.lot_size}m²</span>
                        </div>
                      )}
                      {eligibility.frontage && (
                        <div>
                          <span className="text-gray-500">Frontage:</span>
                          <span className="ml-2 font-medium text-green-600">✓ {eligibility.frontage}m</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Next steps */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <h5 className="text-sm font-semibold text-blue-900 mb-2">Next Steps</h5>
                  <ul className="text-sm text-blue-800 space-y-1">
                    <li>• Apply Pattern Book design standards from SEPP Housing 2021 Part 3A</li>
                    <li className="flex items-center gap-1.5">
                      <span>• Check DCP provisions for any additional local controls</span>
                      {onNavigateToDcp && (
                        <button
                          onClick={() => onNavigateToDcp('general')}
                          className="inline-flex items-center gap-1 text-xs text-teal-700 hover:text-teal-900 font-medium underline underline-offset-2"
                        >
                          Go to DCP
                          <ArrowRight className="h-3 w-3" />
                        </button>
                      )}
                    </li>
                    <li>• Prepare CDC application with accredited certifier</li>
                  </ul>
                </div>

                {/* CDC Compliance Calculator - Only show when ELIGIBLE */}
                <div className="border-t pt-4 mt-4">
                  <div className="mb-3">
                    <h5 className="text-sm font-semibold text-gray-900">Calculate Your Buildable Capacity</h5>
                    <p className="text-xs text-gray-600 mt-1">
                      Use this calculator to check if your design meets Pattern Book numeric standards
                    </p>
                  </div>
                  <CdcComplianceCalculator
                    address={address || null}
                    initialCollapsed={false}
                    lotDimensions={lotDimensions || null}
                    lotSize={lotSize || null}
                  />
                </div>
              </div>
            )}

            {/* INELIGIBLE/CONDITIONAL: Show blockers */}
            {(isIneligible || isConditional) && transformedExclusions.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-gray-900">
                    Exclusion Triggers ({transformedExclusions.length})
                  </h4>
                </div>

                {transformedExclusions.map((exclusion, idx) => (
                  <ExclusionBlockerCard
                    key={idx}
                    exclusion={exclusion}
                    onViewPdf={(page, pdfPath) => setViewingPdf({
                      pageNumber: page,
                      url: `/pdf-pages/${pdfPath}/${pdfPath}_page_${page}.png`,
                      label: `SEPP - Page ${page}`
                    })}
                    onNavigateToDcp={onNavigateToDcp}
                  />
                ))}
              </div>
            )}

            {/* Numeric failures */}
            {eligibility.numericCheck?.details && eligibility.numericCheck.details.length > 0 && (
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold text-gray-900">Lot Size Requirements Not Met</h4>
                  <p className="text-sm text-gray-600 mt-1">
                    Pattern Book designs have different minimum lot sizes depending on the housing type.
                    Your lot is <strong>{propertyData?.lotDimensions?.area?.toFixed(1) || 'unknown'}m²</strong> —
                    the standards below show minimums for each design type.
                  </p>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-amber-900">
                      <p className="font-medium mb-2">What This Means:</p>
                      <ul className="space-y-1 ml-4 list-disc">
                        <li>Pattern Book designs range from studio apartments (300m² min) to manor houses (1500m² min)</li>
                        <li>If your lot is below the smallest minimum, Pattern Book CDC pathway is not available</li>
                        <li>You'll need to pursue a standard Development Application (DA) instead</li>
                        <li>DA pathway uses Housing SEPP standards but requires council/certifier assessment (50+ days)</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h5 className="text-sm font-medium text-gray-700">Standards by Design Type:</h5>
                  {eligibility.numericCheck.details.map((failure: any, idx: number) => (
                    <NumericFailureCard
                      key={idx}
                      failure={failure}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Alternative pathways - show next steps */}
            {(isIneligible || isConditional) && eligibility.nextSteps && eligibility.nextSteps.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3 mb-3">
                  <Shield className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h5 className="font-semibold text-blue-900">Your Alternative Pathways</h5>
                    <p className="text-sm text-blue-700 mt-1">
                      Pattern Book CDC is not available, but you can still develop this property through standard pathways.
                    </p>
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  {eligibility.nextSteps.map((step: any, idx: number) => (
                    <div key={idx} className="flex items-start gap-2">
                      <ArrowRight className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                      <p className="text-blue-800">{step}</p>
                    </div>
                  ))}
                </div>

              </div>
            )}

            {/* Compliance-grade guarantee badge */}
            <div className="flex items-center gap-2 text-xs text-gray-600 border-t border-gray-200 pt-3 mt-4">
              <Shield className="h-4 w-4 text-green-600 flex-shrink-0" />
              <span>Exclusion triggers and numeric standards extracted from SEPP (Housing) 2021. Verify property-specific constraints before lodging a Pattern Book application.</span>
            </div>
          </CardContent>
        )}
      </Card>

      {/* PDF Modal */}
      {viewingPdf && (
        <PdfImageModal
          isOpen={true}
          onClose={() => setViewingPdf(null)}
          pageNumber={viewingPdf.pageNumber}
          imageUrl={viewingPdf.url}
          {...({ label: viewingPdf.label } as any)}
        />
      )}
    </>
  );
}

// Exclusion blocker card with SEPP reference
function ExclusionBlockerCard({
  exclusion,
  onViewPdf,
  onNavigateToDcp,
}: {
  exclusion: Exclusion;
  onViewPdf: (page: number, pdfPath: string) => void;
  onNavigateToDcp?: (topic: string, hcaSlug?: string) => void;
}) {
  return (
    <div className="bg-white border-2 border-red-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1">
          <XCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <h5 className="font-semibold text-red-900">{exclusion.title}</h5>
            <p className="text-sm text-red-700 mt-1">{exclusion.description}</p>
          </div>
        </div>

        {exclusion.override_available && (
          <Badge className="bg-amber-100 text-amber-800 border-amber-300 flex-shrink-0 ml-2">
            Override Available
          </Badge>
        )}
      </div>

      {/* SEPP reference */}
      <div className="bg-gray-50 rounded p-3 mb-3 text-sm">
        <div className="flex items-center justify-between mb-1">
          <span className="font-medium text-gray-700">SEPP Reference:</span>
          {exclusion.sepp_pdf_page && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewPdf(exclusion.sepp_pdf_page!, exclusion.sepp_pdf_path)}
              className="h-8"
            >
              <FileImage className="h-4 w-4 mr-1" />
              View Page {exclusion.sepp_pdf_page}
            </Button>
          )}
        </div>
        <p className="text-gray-600">{exclusion.sepp_provision}</p>
      </div>

      {/* Override condition - show if override is available */}
      {exclusion.override_available && exclusion.override_condition && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3">
          <h6 className="text-sm font-semibold text-amber-900 mb-1">
            Override Requirements
          </h6>
          <p className="text-sm text-amber-800">
            <span className="font-medium">Required:</span> {exclusion.override_condition}
          </p>
          {exclusion.override_notes && (
            <p className="text-xs text-amber-700 mt-2">
              {exclusion.override_notes}
            </p>
          )}
        </div>
      )}

      {/* Heritage-specific DCP cross-reference */}
      {exclusion.exclusionType === 'heritage' && onNavigateToDcp && (
        <button
          onClick={() => onNavigateToDcp('heritage')}
          className="mt-3 flex items-center gap-1.5 text-xs text-teal-700 hover:text-teal-900 font-medium"
        >
          <FileText className="h-3.5 w-3.5" />
          Review DCP heritage controls
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

// Numeric failure card
function NumericFailureCard({ failure }: { failure: NumericFailure }) {
  // Map lot size minimums to likely Pattern Book design types
  const getDesignTypeLabel = (required: number | string): string => {
    const reqNum = typeof required === 'string' ? parseFloat(required) : required;

    if (reqNum <= 300) return 'Studio/1-bed designs';
    if (reqNum <= 450) return '2-bed designs (duplex)';
    if (reqNum <= 600) return '3-bed designs (multi-dwelling)';
    if (reqNum <= 900) return '4-bed designs (townhouses)';
    if (reqNum <= 1500) return 'Manor houses';
    return 'Large configurations';
  };

  const designType = failure.metricName === 'lot_size_min'
    ? getDesignTypeLabel(failure.required)
    : null;

  return (
    <div className="bg-white border border-gray-300 rounded-lg p-3">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="outline" className="text-xs">
              {failure.operator === 'min' ? 'minimum ' : 'maximum '}{failure.required}{failure.unit}
            </Badge>
            {designType && (
              <span className="text-xs text-gray-600">— {designType}</span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Your lot:</span>
              <span className="ml-2 font-medium text-amber-700">
                {failure.actual}{failure.unit}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Short by:</span>
              <span className="ml-2 font-medium text-red-600">
                {Math.abs(failure.gap).toFixed(1)}{failure.unit}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
