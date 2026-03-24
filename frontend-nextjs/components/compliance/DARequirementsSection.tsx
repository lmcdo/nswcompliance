'use client';

import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, FileText, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { PdfPageButton, PdfPageFooter } from './PdfPageButton';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { canSubdivide, isSubdivisionRequirement, hasHeritage, isHeritageRequirement } from '@/lib/requirement-prioritization';

interface DARequirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;
  verbatim_source_text?: string;
  has_conditionals: boolean;
  conditional_text?: string;
  confidence: string;
  pdf_page?: number;
  pdf_page_image_url?: string;
  pdf_path?: string;
  part_name?: string;
  part_number?: string;
  user_category?: string;
  section_type?: string;
  priority_level?: number | null;
}

interface DARequirementsSectionProps {
  requirements: DARequirement[];
  defaultExpanded?: boolean;
  zone?: string;
  developmentType?: string;
  formerCouncil?: string;
  lotArea?: number;  // For subdivision filtering (cadastre area in m²)
  heritage?: any;  // For heritage filtering
  showSubdivisionOverride?: boolean;  // Override state from parent
  showHeritageOverride?: boolean;  // Override state from parent
}

type RequirementCategory = 'standard' | 'councilSpecific' | 'conditional' | 'excluded';

/**
 * Extract council and DCP info from requirement
 */
const getCouncilInfo = (requirement: DARequirement) => {
  const pdfPath = requirement.pdf_path || '';

  // Extract council from PDF path
  let council = 'Inner West';
  let dcp = '';

  if (pdfPath.includes('Ashfield')) {
    council = 'Ashfield';
    dcp = 'Ashfield DCP 2016';
  } else if (pdfPath.includes('Marrickville')) {
    council = 'Marrickville';
    dcp = 'Marrickville DCP 2011';
  } else if (pdfPath.includes('Leichhardt')) {
    council = 'Leichhardt';
    dcp = 'Leichhardt DCP 2013';
  }

  return { council, dcp };
};

/**
 * Ashfield filtering: Strict (Zone + Development Type)
 * Ashfield DCP Chapter F is organized by development type (F.1, F.2, etc.)
 */
const filterAshfield = (requirement: DARequirement, devType: string, zone: string): RequirementCategory => {
  const text = requirement.requirement_text.toLowerCase();
  const partName = (requirement.part_name || '').toLowerCase();

  // Map dev types to Ashfield chapter sections
  const devTypeMap: Record<string, string[]> = {
    'dwelling_house': ['dwelling house', 'single dwelling', 'f.1', 'f1'],
    'secondary_dwelling': ['secondary dwelling', 'granny flat', 'f.2', 'f2'],
    'multi_dwelling': ['multi dwelling', 'f.3', 'f3'],
    'residential_flat': ['residential flat building', 'rfb', 'f.4', 'f4'],
    'boarding_house': ['boarding house', 'f.5', 'f5'],
    'child_care': ['child care', 'childcare', 'f.6', 'f6'],
    'shop_top_housing': ['shop top housing', 'f.7', 'f7'],
  };

  const relevantTerms = devTypeMap[devType] || [];

  // Check if requirement matches this dev type
  const isRelevant = relevantTerms.some(term => text.includes(term) || partName.includes(term));

  // Check if it's explicitly for a DIFFERENT dev type
  const otherDevTypes = Object.entries(devTypeMap)
    .filter(([key]) => key !== devType)
    .flatMap(([, terms]) => terms);

  const isOtherDevType = otherDevTypes.some(term => text.includes(term) || partName.includes(term));

  if (isOtherDevType) return 'excluded';
  if (isRelevant) return 'standard';

  // General Ashfield requirements (not dev-type specific)
  if (partName.includes('general') || text.includes('all development')) return 'councilSpecific';

  return 'standard'; // Default: show (conservative)
};

/**
 * Marrickville filtering: Partial (Development Type for Part 4.x, keep all Part 2.x)
 * Part 2.x = universal, Part 4.x = dev type specific
 */
const filterMarrickville = (requirement: DARequirement, devType: string): RequirementCategory => {
  const text = requirement.requirement_text.toLowerCase();
  const partName = (requirement.part_name || '').toLowerCase();

  // Part 2.x is universal - always show
  if (partName.includes('part 2')) return 'standard';

  // Part 4.x filtering
  if (partName.includes('part 4')) {
    const devTypeMap: Record<string, string[]> = {
      'dwelling_house': ['4.1', 'dwelling house', 'single dwelling'],
      'multi_dwelling': ['4.2', 'multi dwelling'],
      'residential_flat': ['4.3', 'residential flat building', 'rfb'],
      'secondary_dwelling': ['4.1.8', 'secondary dwelling', 'granny flat'],
    };

    const relevantTerms = devTypeMap[devType] || [];
    const isRelevant = relevantTerms.some(term => text.includes(term) || partName.includes(term));

    // Check for other dev types in Part 4.x
    const otherDevTypes = Object.entries(devTypeMap)
      .filter(([key]) => key !== devType)
      .flatMap(([, terms]) => terms);

    const isOtherDevType = otherDevTypes.some(term => text.includes(term) || partName.includes(term));

    if (isOtherDevType) return 'excluded';
    if (isRelevant) return 'standard';
  }

  return 'councilSpecific'; // Other Marrickville requirements
};

/**
 * Leichhardt filtering: Very conservative (Parts A-E are universal)
 * Only filter obviously wrong requirements
 */
const filterLeichhardtConservative = (requirement: DARequirement, devType: string): RequirementCategory => {
  const text = requirement.requirement_text.toLowerCase();

  // Special events/Callan Park - clearly not for residential development
  const specialEventKeywords = [
    'special event',
    'callan park',
    'booking form',
    'event application',
    'public art',
    'community event'
  ];

  if (specialEventKeywords.some(kw => text.includes(kw))) {
    return 'excluded';
  }

  // Explicitly for other dev types
  if (devType === 'dwelling_house') {
    const wrongTypes = [
      'multi dwelling housing',
      'residential flat building',
      'boarding house',
      'childcare centre',
      'other than single dwelling',
      'except for dwelling houses'
    ];

    if (wrongTypes.some(type => text.includes(type))) {
      return 'excluded';
    }
  }

  // Check for conditional requirements
  if (requirement.has_conditionals) {
    return 'conditional';
  }

  return 'standard'; // Default: SHOW (Leichhardt Parts A-E are mostly universal)
};

/**
 * Main categorization function - routes to council-specific logic
 */
const categorizeRequirement = (
  requirement: DARequirement,
  devType: string = 'dwelling_house',
  zone: string = '',
  formerCouncil: string = ''
): RequirementCategory => {
  const { council } = getCouncilInfo(requirement);

  if (council === 'Ashfield') {
    return filterAshfield(requirement, devType, zone);
  } else if (council === 'Marrickville') {
    return filterMarrickville(requirement, devType);
  } else if (council === 'Leichhardt') {
    return filterLeichhardtConservative(requirement, devType);
  }

  // Fallback for other councils
  return 'standard';
};

/**
 * Group requirements by CATEGORY first, then by page number within each category
 * Display with single PDF link per category
 */
const RequirementGroup: React.FC<{ requirements: DARequirement[] }> = ({ requirements }) => {
  const [viewingPdfImage, setViewingPdfImage] = useState<string | null>(null);

  // Group ONLY by part_name (not page - multiple pages can be in same part)
  const groupedByPart: { [partName: string]: DARequirement[] } = {};

  requirements.forEach(req => {
    const partName = req.part_name || 'General';
    if (!groupedByPart[partName]) {
      groupedByPart[partName] = [];
    }
    groupedByPart[partName].push(req);
  });

  // Sort parts alphabetically
  const sortedParts = Object.entries(groupedByPart).sort(([a], [b]) => a.localeCompare(b));

  return (
    <>
      <div className="space-y-3">
        {sortedParts.map(([partName, partReqs]) => {
          const { council, dcp } = getCouncilInfo(partReqs[0]);

          // Group requirements within this part by page number
          const pageGroups: { [page: number]: DARequirement[] } = {};
          partReqs.forEach(req => {
            const page = req.pdf_page || 0;
            if (!pageGroups[page]) pageGroups[page] = [];
            pageGroups[page].push(req);
          });

          const sortedPageGroups = Object.entries(pageGroups).sort(([a], [b]) => parseInt(a) - parseInt(b));

          return (
            <div key={partName} className="border border-purple-200 rounded-lg overflow-hidden">
              {/* Part header with council and part number */}
              <div className="bg-purple-100 px-3 py-2 border-b border-purple-200">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-purple-900">{partName}</span>
                  <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-300">
                    {council}
                  </Badge>
                  {partReqs[0].part_number && (
                    <span className="text-xs text-gray-600">({partReqs[0].part_number})</span>
                  )}
                  {dcp && !partReqs[0].part_number && (
                    <span className="text-xs text-gray-600">({dcp})</span>
                  )}
                </div>
              </div>

              {/* Requirements grouped by page within this part */}
              <div>
                {sortedPageGroups.map(([pageStr, pageReqs]) => {
                  const page = parseInt(pageStr);
                  const pdfUrl = pageReqs[0]?.pdf_page_image_url;

                  return (
                    <div key={`${partName}-${page}`}>
                      {/* Requirements from this page */}
                      <div className="divide-y divide-purple-100">
                        {pageReqs.map((req) => (
                          <div key={req.id} className="px-3 py-2">
                            <DARequirementItemSimple requirement={req} />
                          </div>
                        ))}
                      </div>

                      {/* PDF Page Footer for this page group */}
                      {page > 0 && pdfUrl && (
                        <PdfPageFooter
                          pageNumber={page}
                          requirementCount={pageReqs.length}
                          pdfUrl={pdfUrl}
                          onViewPdf={() => setViewingPdfImage(pdfUrl)}
                          accentColor="slate"
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* PDF Viewer Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        imageUrl={viewingPdfImage}
        title="DCP Source Document"
      />
    </>
  );
};

/**
 * Simple DA requirement item (for use within page groups)
 * Doesn't include PDF viewing button (shown at group level instead)
 */
const DARequirementItemSimple: React.FC<{ requirement: DARequirement }> = ({ requirement }) => {
  const isHighPriority = requirement.priority_level && requirement.priority_level <= 2;

  return (
    <div>
      {/* Just badges and text - council/part info is in the group header */}
      <div className="flex items-start gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            {isHighPriority && (
              <Badge variant="outline" className="text-xs bg-slate-100 text-slate-700 border-slate-300">
                Required
              </Badge>
            )}
            {requirement.has_conditionals && (
              <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-300">
                Conditional
              </Badge>
            )}
          </div>

          <p className="text-sm text-gray-800">{requirement.requirement_text}</p>

          {requirement.has_conditionals && requirement.conditional_text && (
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
              <strong>Condition:</strong> {requirement.conditional_text}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Full DA requirement item (for standalone use, with individual PDF viewing)
 * Used for requirements without page numbers
 */
const DARequirementItem: React.FC<{ requirement: DARequirement }> = ({ requirement }) => {
  const [expanded, setExpanded] = useState(false);
  const [showVerbatim, setShowVerbatim] = useState(false);

  const hasPdfAccess = requirement.pdf_page_image_url;
  const isHighPriority = requirement.priority_level && requirement.priority_level <= 2;
  const { council, dcp } = getCouncilInfo(requirement);

  return (
    <div
      className="border-l-4 border-l-purple-400 bg-purple-50 p-3 mb-2 rounded cursor-pointer hover:shadow-sm transition-shadow"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <FileText className="w-4 h-4 text-purple-600" />

            {/* Council Badge */}
            <Badge variant="outline" className="text-xs bg-purple-100 text-purple-800 border-purple-300">
              {council}
            </Badge>

            {/* Part Name */}
            <span className="text-xs font-medium text-purple-700">
              {requirement.part_name || 'General'}
            </span>

            {/* DCP Reference */}
            {dcp && (
              <span className="text-xs text-gray-500">
                ({dcp})
              </span>
            )}

            {isHighPriority && (
              <Badge variant="outline" className="text-xs bg-slate-100 text-slate-700 border-slate-300">
                Required
              </Badge>
            )}
            {requirement.has_conditionals && (
              <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-300">
                Conditional
              </Badge>
            )}
          </div>

          <p className="text-sm text-gray-800 mt-1">{requirement.requirement_text}</p>

          {/* Verbatim Text Toggle */}
          {requirement.verbatim_source_text && requirement.verbatim_source_text !== requirement.requirement_text && (
            <div className="mt-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowVerbatim(!showVerbatim);
                }}
                className="text-xs text-purple-600 hover:text-purple-700 hover:underline flex items-center gap-1"
              >
                {showVerbatim ? '▲ Hide' : '▼ View'} {requirement.pdf_page ? `PDF page ${requirement.pdf_page}` : 'PDF source'}
              </button>
              {showVerbatim && (
                <div className="mt-2 p-3 bg-white border border-purple-300 rounded-lg">
                  <div className="text-xs font-medium text-purple-700 mb-1">📄 Exact text from PDF:</div>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {requirement.verbatim_source_text}
                  </p>
                </div>
              )}
            </div>
          )}

          {expanded && requirement.has_conditionals && requirement.conditional_text && (
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
              <strong>Condition:</strong> {requirement.conditional_text}
            </div>
          )}
        </div>

        <div className="ml-2 p-1.5 rounded-full hover:bg-purple-200 transition-colors">
          {expanded ? <ChevronDown className="w-5 h-5 text-purple-600" /> : <ChevronRight className="w-5 h-5 text-purple-600" />}
        </div>
      </div>
    </div>
  );
};

/**
 * DARequirementsSection: Displays Development Application documentation requirements
 *
 * Features:
 * - Purple theme to distinguish from technical DCP controls
 * - Collapsible section with requirement count
 * - Priority badges for required vs optional documentation
 * - Grouped display of all documentation/process requirements
 */
const DARequirementsSection: React.FC<DARequirementsSectionProps> = ({
  requirements,
  defaultExpanded = true,
  zone = '',
  developmentType = 'dwelling_house',
  formerCouncil = '',
  lotArea,
  heritage,
  showSubdivisionOverride = false,
  showHeritageOverride = false
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [showExcluded, setShowExcluded] = useState(false);

  const propertyCanSubdivide = canSubdivide(lotArea);
  const propertyHasHeritage = hasHeritage(heritage);

  // Apply smart filters to requirements (using parent's override state)
  const filteredRequirements = useMemo(() => {
    let filtered = requirements;

    // Apply subdivision filter
    if (!showSubdivisionOverride && !propertyCanSubdivide) {
      filtered = filtered.filter(req => !isSubdivisionRequirement(req));
    }

    // Apply heritage filter
    if (!showHeritageOverride && !propertyHasHeritage) {
      filtered = filtered.filter(req => !isHeritageRequirement(req));
    }

    return filtered;
  }, [requirements, showSubdivisionOverride, propertyCanSubdivide, showHeritageOverride, propertyHasHeritage]);

  // Categorize filtered requirements
  const categorized = filteredRequirements.reduce((acc, req) => {
    const category = categorizeRequirement(req, developmentType, zone, formerCouncil);
    if (!acc[category]) acc[category] = [];
    acc[category].push(req);
    return acc;
  }, {} as Record<RequirementCategory, DARequirement[]>);

  const standardReqs = categorized.standard || [];
  const councilSpecificReqs = categorized.councilSpecific || [];
  const conditionalReqs = categorized.conditional || [];
  const excludedReqs = categorized.excluded || [];

  // Count stats
  const visibleCount = standardReqs.length + councilSpecificReqs.length + conditionalReqs.length;
  const excludedCount = excludedReqs.length;
  const requiredCount = requirements.filter(r => r.priority_level && r.priority_level <= 2).length;

  return (
    <div className="border-2 border-purple-300 rounded-lg overflow-hidden shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-4 bg-purple-100 hover:bg-purple-200 transition-colors flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          {/* Large Chevron Icon */}
          {expanded ? (
            <ChevronDown className="w-12 h-12 text-purple-600 flex-shrink-0" />
          ) : (
            <ChevronRight className="w-12 h-12 text-purple-600 flex-shrink-0" />
          )}

          {/* Title */}
          <div className="flex flex-col items-start">
            <div className="flex items-center gap-2">
              <FileText className="w-6 h-6 text-purple-700" />
              <span className="font-bold text-purple-900 text-lg">
                Development Application Requirements
              </span>
            </div>
            <span className="text-sm text-purple-700">
              Documentation and process requirements for your DA
            </span>
          </div>
        </div>

        {/* Count Badge */}
        <div className="flex items-center gap-2">
          <div className="px-3 py-1 rounded-full bg-purple-200 text-purple-800 text-sm font-medium border border-purple-400 flex items-center gap-1">
            <CheckCircle2 className="w-4 h-4" />
            {visibleCount} relevant
          </div>
          {excludedCount > 0 && (
            <div className="px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-sm font-medium border border-gray-300 flex items-center gap-1">
              {excludedCount} filtered
            </div>
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="p-4 bg-white">
          {/* Explainer Box */}
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900 mb-2">
              <strong>📋 What to submit:</strong> These requirements specify what documentation
              and supporting materials you need to include with your Development Application.
              Required items must be provided; additional items may be requested based on your
              specific proposal.
            </p>
            <p className="text-xs text-blue-800 mt-2 border-t border-blue-200 pt-2">
              <strong>ℹ️ About Inner West Council:</strong> Inner West was formed in 2016 by merging
              Ashfield, Marrickville, and Leichhardt councils. Each area maintains its own DCP
              (Development Control Plan) with specific requirements. The requirements below are drawn
              from the relevant DCP for your property's location.
            </p>
          </div>

          {/* Standard Requirements */}
          {standardReqs.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2 px-2">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <h4 className="font-semibold text-gray-900">Standard Documentation ({standardReqs.length})</h4>
              </div>
              <RequirementGroup requirements={standardReqs} />
            </div>
          )}

          {/* Council-Specific Requirements */}
          {councilSpecificReqs.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2 px-2">
                <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-300">
                  Council-Specific
                </Badge>
                <h4 className="font-semibold text-gray-900">Additional Local Requirements ({councilSpecificReqs.length})</h4>
              </div>
              <p className="text-xs text-gray-600 mb-2 px-2">
                These are specific to {formerCouncil || 'this council area'}'s DCP and may not apply to all development types
              </p>
              <RequirementGroup requirements={councilSpecificReqs} />
            </div>
          )}

          {/* Conditional Requirements */}
          {conditionalReqs.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2 px-2">
                <AlertCircle className="w-5 h-5 text-yellow-600" />
                <h4 className="font-semibold text-gray-900">May Be Required ({conditionalReqs.length})</h4>
              </div>
              <p className="text-xs text-gray-600 mb-2 px-2">
                These requirements apply in specific circumstances - check each condition
              </p>
              <RequirementGroup requirements={conditionalReqs} />
            </div>
          )}

          {/* Excluded Requirements (Collapsible) */}
          {excludedReqs.length > 0 && (
            <div className="mb-4 border-t pt-4">
              <button
                onClick={() => setShowExcluded(!showExcluded)}
                className="flex items-center gap-2 mb-2 px-2 text-gray-600 hover:text-gray-800 w-full"
              >
                {showExcluded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                <h4 className="font-semibold">Filtered Out ({excludedCount})</h4>
                <span className="text-xs text-gray-500">- Not relevant to {developmentType.replace('_', ' ')}</span>
              </button>
              {showExcluded && (
                <div className="opacity-60">
                  <RequirementGroup requirements={excludedReqs} />
                </div>
              )}
            </div>
          )}

          {/* Empty State */}
          {requirements.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No DA requirements found for this development type
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DARequirementsSection;
