/**
 * GeneralDCPSection.tsx (Fixed page grouping v2)
 * Unified DCP display component that adapts to each LGA's structure
 *
 * Displays:
 * - General Controls (Chapter F / Part 4.x / Part C.1) - filtered by zone/devtype where available
 * - Precinct Controls (Marrickville/Ashfield) or Distinctive Neighbourhood (Leichhardt) when applicable
 *
 * Adapts to different filtering levels:
 * - Ashfield: Zone + Dev Type filtering
 * - Marrickville: Dev Type filtering
 * - Leichhardt: Universal (no filtering)
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, FileText, FileImage, Info, X } from 'lucide-react';
import { PdfPageButton } from './PdfPageButton';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { prioritizeRequirements, getPriorityStats, canSubdivide, isSubdivisionRequirement, hasHeritage, isHeritageRequirement, groupByCategory } from '@/lib/requirement-prioritization';

interface GeneralProvision {
  id: number;
  section_header: string;
  provision_text: string;
  ref_number: string;
  part_name?: string;
}

interface GeneralRequirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;  // Summary (prescriptive/actionable parts only)
  verbatim_source_text?: string;  // Exact text from PDF (for user verification)
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  unit?: string;
  has_conditionals: boolean;
  conditional_text?: string;
  confidence: string;
  pdf_page?: number;
  pdf_page_image_url?: string;
  pdf_path?: string;
}

interface PrecinctProvision {
  id: number;
  precinct_id: string;
  precinct_name: string;
  section_header: string;
  provision_text: string;
  ref_number: string;
}

interface PrecinctRequirement {
  id: number;
  precinct_id: string;
  precinct_name: string;
  category: string;
  subcategory?: string;
  requirement_text: string;  // Summary (prescriptive/actionable parts only)
  verbatim_source_text?: string;  // Exact text from PDF (for user verification)
  value_numeric?: number;
  unit?: string;
  has_conditionals: boolean;
  conditional_text?: string;
  confidence: string;
  pdf_page?: number;
  pdf_page_image_url?: string;
  pdf_path?: string;
}

interface CategorySummary {
  category: string;
  general_count: number;
  precinct_count: number;
  total_count: number;
  general_requirements: GeneralRequirement[];
  precinct_requirements: PrecinctRequirement[];
}

interface GeneralDCPSectionProps {
  generalData: {
    source: string;
    applicable_to: string;
    count: number;
    requirements_count: number;
    provisions: GeneralProvision[];
    requirements: GeneralRequirement[];
    by_category: Record<string, GeneralRequirement[]>;
  };
  precinctData?: {
    source: string;
    precinct_id: string;
    precinct_name: string;
    applicable_to: string;
    count: number;
    requirements_count: number;
    provisions: PrecinctProvision[];
    requirements: PrecinctRequirement[];
    by_category: Record<string, PrecinctRequirement[]>;
  } | null;
  combinedCategories: CategorySummary[];
  zone: string;
  developmentType: string;
  filteringLevel?: 'zone+devtype' | 'devtype' | 'universal';
  formerCouncil?: string;
  lotArea?: number;  // For subdivision filtering (cadastre area in m²)
  heritage?: any;  // For heritage filtering
  daRequirementsCount?: number;  // For DA requirements display
  displayModeSetterRef?: React.MutableRefObject<((mode: 'separated' | 'combined') => void) | null>;
}

const CategoryIcon: React.FC<{ category: string }> = ({ category }) => {
  const iconMap: Record<string, string> = {
    setback_front: '📏',
    setback_side: '📐',
    setback_rear: '📊',
    parking: '🅿️',
    landscaping: '🌳',
    building_height: '📈',
    building_form: '🏛️',
    character: '🎨',
    privacy: '👁️',
    solar_access: '☀️',
    open_space: '🌿',
    deep_soil: '🌱',
    fencing: '🚧',
    other: '📋'
  };

  return <span className="mr-2">{iconMap[category] || '📋'}</span>;
};

// Format category names with proper capitalization
const formatCategoryName = (category: string): string => {
  const formatted = category.replace(/_/g, ' ');

  // Special cases that need specific capitalization
  const specialCases: Record<string, string> = {
    'da requirements': 'DA Requirements',
    'basix': 'BASIX',
    'sepp': 'SEPP',
    'lep': 'LEP',
    'dcp': 'DCP',
    'hca': 'HCA',
  };

  // Check if the full string matches a special case
  const lowerFormatted = formatted.toLowerCase();
  if (specialCases[lowerFormatted]) {
    return specialCases[lowerFormatted];
  }

  // Otherwise, capitalize each word normally
  return formatted
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

const FilteringLevelBadge: React.FC<{ level?: string; formerCouncil?: string }> = ({ level, formerCouncil }) => {
  const badgeConfig = {
    'zone+devtype': { color: 'bg-green-100 text-green-800 border-green-300', label: 'Zone + Type Filtered' },
    'devtype': { color: 'bg-blue-100 text-blue-800 border-blue-300', label: 'Type Filtered' },
    'universal': { color: 'bg-gray-100 text-gray-800 border-gray-300', label: formerCouncil ? `${formerCouncil} DCP ${formerCouncil === 'Ashfield' ? '2016' : formerCouncil === 'Marrickville' ? '2011' : '2013'}` : 'Universal' }
  };

  const config = badgeConfig[level as keyof typeof badgeConfig] || badgeConfig.universal;

  return (
    <Badge variant="outline" className={`${config.color} text-xs`}>
      {config.label}
    </Badge>
  );
};

const RequirementCard: React.FC<{
  requirement: GeneralRequirement | PrecinctRequirement;
  source: 'general' | 'precinct';
  hideIndividualPdf?: boolean;
}> = ({ requirement, source, hideIndividualPdf = false }) => {
  const [expanded, setExpanded] = useState(false);
  const [showVerbatim, setShowVerbatim] = useState(false);
  const [showingPdf, setShowingPdf] = useState(false);

  const sourceColor = source === 'general'
    ? 'border-l-blue-400 bg-blue-50'
    : 'border-l-green-400 bg-green-50';

  // Show PDF button if we have the image URL (page number is optional)
  const hasPdfAccess = requirement.pdf_page_image_url;

  return (
    <>
      {requirement.confidence === 'medium' ? (
        // Descriptive provision (character description)
        <div className="border-l-4 border-yellow-400 bg-yellow-50 p-4 mb-2 rounded">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-yellow-600 text-lg">⚠️</span>
            <span className="font-semibold text-yellow-800 text-xs uppercase tracking-wide">Character Description</span>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-600">
              {formatCategoryName(requirement.category)}
            </span>
            {requirement.has_conditionals && (
              <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-300">
                Conditional
              </Badge>
            )}
          </div>
          <p className="text-sm text-gray-800">{requirement.requirement_text}</p>
          <p className="text-xs text-gray-600 mt-2 italic">
            ℹ️ This describes typical character, not minimum requirements
          </p>
        </div>
      ) : (
        // Prescriptive requirement (high/low confidence)
        <div
          className={`border-l-4 ${sourceColor} p-3 mb-2 rounded cursor-pointer hover:shadow-sm transition-shadow`}
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-gray-600">
                  {formatCategoryName(requirement.category)}
                </span>
                {requirement.has_conditionals && (
                  <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-300">
                    Conditional
                  </Badge>
                )}
              </div>
              <p className="text-sm text-gray-800">{requirement.requirement_text}</p>

            {/* Verbatim Text Toggle - Hidden when PDF grouping is active */}
            {!hideIndividualPdf && requirement.verbatim_source_text && requirement.verbatim_source_text !== requirement.requirement_text && (
              <div className="mt-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowVerbatim(!showVerbatim);
                  }}
                  className="text-xs text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1"
                >
                  {showVerbatim ? '▲ Hide verbatim text' : '▼ View verbatim text'}
                </button>
                {showVerbatim && (
                  <div className="mt-2 p-3 bg-gray-100 border border-gray-300 rounded-lg">
                    <div className="text-xs font-medium text-gray-700 mb-1">📄 Exact text from PDF:</div>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                      {requirement.verbatim_source_text}
                    </p>
                    {/* Standardized PDF button - right-aligned below verbatim */}
                    {hasPdfAccess && (
                      <PdfPageButton
                        pageNumber={requirement.pdf_page}
                        pdfUrl={requirement.pdf_page_image_url!}
                        onClick={() => setShowingPdf(true)}
                        variant="inline"
                      />
                    )}
                  </div>
                )}
              </div>
            )}

            {expanded && requirement.has_conditionals && requirement.conditional_text && (
              <div className="mt-2">
                <div className="p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                  <strong>Condition:</strong> {requirement.conditional_text}
                </div>
              </div>
            )}
          </div>
          <div className="ml-2 p-1.5 rounded-full hover:bg-gray-200 transition-colors">
            {expanded ? <ChevronDown className="w-5 h-5 text-gray-600" /> : <ChevronRight className="w-5 h-5 text-gray-600" />}
          </div>
        </div>
      </div>
      )}

      {/* PDF Viewer Modal */}
      {showingPdf && hasPdfAccess && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
          onClick={() => setShowingPdf(false)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-auto relative"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between">
              <h3 className="font-semibold">{requirement.pdf_page ? `DCP Page ${requirement.pdf_page}` : 'DCP Source Document'}</h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowingPdf(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="p-4">
              <img
                src={requirement.pdf_page_image_url}
                alt={requirement.pdf_page ? `PDF Page ${requirement.pdf_page}` : 'DCP Source Document'}
                className="w-full h-auto"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
};

const CategorySection: React.FC<{
  category: CategorySummary;
  defaultExpanded?: boolean;
  setViewingPdfImage: (value: { url: string; page: number } | null) => void;
  showOnly?: 'general' | 'precinct' | 'both';
}> = ({ category, defaultExpanded = false, setViewingPdfImage, showOnly = 'both' }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="border rounded-lg mb-4 overflow-hidden">
      <div
        className="bg-gray-50 p-4 cursor-pointer hover:bg-gray-100 transition-colors flex items-center justify-between"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-700 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-700 flex-shrink-0" />}
        <div className="flex items-center gap-3 flex-1">
          <CategoryIcon category={category.category} />
          <div>
            <h4 className="font-semibold text-gray-900">
              {formatCategoryName(category.category)}
            </h4>
            <p className="text-xs text-gray-600">
              {showOnly === 'general' && category.general_count > 0 && (
                `${category.general_count} requirement${category.general_count !== 1 ? 's' : ''}`
              )}
              {showOnly === 'precinct' && category.precinct_count > 0 && (
                `${category.precinct_count} requirement${category.precinct_count !== 1 ? 's' : ''}`
              )}
              {showOnly === 'both' && (
                <>
                  {category.total_count} requirement{category.total_count !== 1 ? 's' : ''}
                  {category.general_count > 0 && category.precinct_count > 0 &&
                    ` (${category.general_count} general + ${category.precinct_count} precinct)`}
                </>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {(showOnly === 'general' || showOnly === 'both') && category.general_count > 0 && (
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300 text-xs">
              {category.general_count} General
            </Badge>
          )}
          {(showOnly === 'precinct' || showOnly === 'both') && category.precinct_count > 0 && (
            <Badge variant="outline" className="bg-teal-50 text-teal-700 border-teal-300 text-xs">
              {category.precinct_count} Precinct
            </Badge>
          )}
        </div>
      </div>

      {expanded && (
        <div className="p-4 bg-white">
          {(showOnly === 'general' || showOnly === 'both') && category.general_requirements.length > 0 && (
            <div className="mb-4">
              <h5 className="text-sm font-medium text-blue-700 mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                General Controls
              </h5>
              <div className="border-l-4 border-l-blue-400 bg-blue-50 rounded">
                {(() => {
                  // Group by PDF page number (simple and reliable)
                  // Within a category, all requirements are from the same document
                  const groupedByPage: { [page: number]: GeneralRequirement[] } = {};
                  const requirementsWithoutPage: GeneralRequirement[] = [];

                  category.general_requirements.forEach(req => {
                    const pageNum = req.pdf_page;
                    if (pageNum) {
                      if (!groupedByPage[pageNum]) {
                        groupedByPage[pageNum] = [];
                      }
                      groupedByPage[pageNum].push(req);
                    } else {
                      requirementsWithoutPage.push(req);
                    }
                  });

                  // Sort page groups by page number (ascending order)
                  const sortedPageGroups = Object.entries(groupedByPage)
                    .sort(([pageA], [pageB]) => parseInt(pageA) - parseInt(pageB));

                  return sortedPageGroups.map(([pageNumStr, requirements], groupIdx) => {
                    const pdfPage = parseInt(pageNumStr);
                    const pdfUrl = requirements[0]?.pdf_page_image_url;
                    const hasMultiple = requirements.length > 1;

                    return (
                      <div key={`page-${pdfPage}`} className={groupIdx > 0 ? 'border-t border-blue-200' : ''}>
                        {/* Requirements list */}
                        <div className="divide-y divide-blue-100">
                          {requirements.map((req) => (
                            <div key={req.id} className="p-3">
                              {req.confidence === 'medium' ? (
                                // Descriptive provision (character description)
                                <div className="border-l-4 border-yellow-400 bg-yellow-50 p-3 rounded">
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="text-yellow-600 text-lg">⚠️</span>
                                    <span className="font-semibold text-yellow-800 text-xs uppercase tracking-wide">Character Description</span>
                                  </div>
                                  <p className="text-sm text-gray-800">{req.requirement_text}</p>
                                  <p className="text-xs text-gray-600 mt-2 italic">
                                    ℹ️ This describes typical character, not minimum requirements
                                  </p>
                                </div>
                              ) : (
                                // Prescriptive requirement (high/low confidence)
                                <div className="flex items-start gap-2">
                                  <span className="text-blue-600 font-bold">✓</span>
                                  <p className="text-sm text-gray-800">{req.requirement_text}</p>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                        {/* PDF button at bottom of page group */}
                        {pdfPage && pdfUrl && (
                          <div className="px-3 py-2 bg-blue-100 border-t border-blue-200 flex items-center justify-between">
                            <div className="text-xs text-blue-800">
                              <span className="font-semibold">{hasMultiple ? `${requirements.length} requirements` : '1 requirement'}</span> from page {pdfPage}
                            </div>
                            <button
                              className="p-1.5 rounded hover:bg-blue-200 transition-colors"
                              title={`View PDF Page ${pdfPage}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                setViewingPdfImage({ url: pdfUrl, page: pdfPage });
                              }}
                            >
                              <FileImage className="w-5 h-5 text-blue-600 hover:text-blue-800" />
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          )}

          {(showOnly === 'precinct' || showOnly === 'both') && category.precinct_requirements.length > 0 && (
            <div>
              <h5 className="text-sm font-medium text-green-700 mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                Precinct-Specific Controls
              </h5>
              <div className="border-l-4 border-l-green-400 bg-green-50 rounded">
                {(() => {
                  // Group by PDF page number (simple and reliable)
                  // Within a category, all requirements are from the same document
                  const groupedByPage: { [page: number]: PrecinctRequirement[] } = {};
                  const requirementsWithoutPage: PrecinctRequirement[] = [];

                  category.precinct_requirements.forEach(req => {
                    const pageNum = req.pdf_page;
                    if (pageNum) {
                      if (!groupedByPage[pageNum]) {
                        groupedByPage[pageNum] = [];
                      }
                      groupedByPage[pageNum].push(req);
                    } else {
                      requirementsWithoutPage.push(req);
                    }
                  });

                  // Sort page groups by page number (ascending order)
                  const sortedPageGroups = Object.entries(groupedByPage)
                    .sort(([pageA], [pageB]) => parseInt(pageA) - parseInt(pageB));

                  return sortedPageGroups.map(([pageNumStr, requirements], groupIdx) => {
                    const pdfPage = parseInt(pageNumStr);
                    const pdfUrl = requirements[0]?.pdf_page_image_url;
                    const hasMultiple = requirements.length > 1;

                    return (
                      <div key={`precinct-page-${pdfPage}`} className={groupIdx > 0 ? 'border-t border-green-200' : ''}>
                        {/* Requirements list */}
                        <div className="divide-y divide-green-100">
                          {requirements.map((req) => (
                            <div key={req.id} className="p-3">
                              {req.confidence === 'medium' ? (
                                // Descriptive provision (character description)
                                <div className="border-l-4 border-yellow-400 bg-yellow-50 p-3 rounded">
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="text-yellow-600 text-lg">⚠️</span>
                                    <span className="font-semibold text-yellow-800 text-xs uppercase tracking-wide">Character Description</span>
                                  </div>
                                  <p className="text-sm text-gray-800">{req.requirement_text}</p>
                                  <p className="text-xs text-gray-600 mt-2 italic">
                                    ℹ️ This describes typical character, not minimum requirements
                                  </p>
                                </div>
                              ) : (
                                // Prescriptive requirement (high/low confidence)
                                <div className="flex items-start gap-2">
                                  <span className="text-green-600 font-bold">✓</span>
                                  <p className="text-sm text-gray-800">{req.requirement_text}</p>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                        {/* PDF button at bottom of page group */}
                        {pdfPage && pdfUrl && (
                          <div className="px-3 py-2 bg-green-100 border-t border-green-200 flex items-center justify-between">
                            <div className="text-xs text-green-800">
                              <span className="font-semibold">{hasMultiple ? `${requirements.length} requirements` : '1 requirement'}</span> from page {pdfPage}
                            </div>
                            <button
                              className="p-1.5 rounded hover:bg-green-200 transition-colors"
                              title={`View PDF Page ${pdfPage}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                setViewingPdfImage({ url: pdfUrl, page: pdfPage });
                              }}
                            >
                              <FileImage className="w-5 h-5 text-green-600 hover:text-green-800" />
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const GeneralDCPSection: React.FC<GeneralDCPSectionProps> = ({
  generalData,
  precinctData,
  combinedCategories,
  zone,
  developmentType,
  filteringLevel = 'universal',
  formerCouncil,
  lotArea,
  heritage,
  daRequirementsCount = 0,
  displayModeSetterRef
}) => {
  // Modal state for PDF viewer (page group footers)
  const [viewingPdfImage, setViewingPdfImage] = useState<{ url: string; page: number } | null>(null);

  // Display mode: 'separated' (default) or 'combined'
  const [displayMode, setDisplayMode] = useState<'separated' | 'combined'>('separated');

  // Track which category should be expanded
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  // Subdivision filter state
  const [showSubdivisionOverride, setShowSubdivisionOverride] = useState(false);
  const propertyCanSubdivide = canSubdivide(lotArea);

  // Heritage filter state
  const [showHeritageOverride, setShowHeritageOverride] = useState(false);
  const propertyHasHeritage = hasHeritage(heritage);

  // Debug logging
  useEffect(() => {
    console.log('[Smart Filters] Debug:', {
      lotArea,
      propertyCanSubdivide,
      heritage: propertyHasHeritage,
      totalRequirements: generalData.requirements.length,
      subdivisionCount: generalData.requirements.filter(isSubdivisionRequirement).length,
      heritageCount: generalData.requirements.filter(isHeritageRequirement).length
    });
  }, [lotArea, propertyCanSubdivide, propertyHasHeritage, generalData.requirements]);

  // Expose setDisplayMode and helper functions to parent via ref
  useEffect(() => {
    if (displayModeSetterRef) {
      displayModeSetterRef.current = (mode: 'separated' | 'combined', options?: { expandCategory?: string }) => {
        setDisplayMode(mode);
        if (options?.expandCategory) {
          setGeneralExpanded(true);
          setExpandedCategory(options.expandCategory);
        }
      };
    }
  }, [displayModeSetterRef]);

  // Apply smart filters to requirements
  const filteredRequirements = React.useMemo(() => {
    let filtered = generalData.requirements;

    // Apply subdivision filter
    if (!showSubdivisionOverride && !propertyCanSubdivide) {
      filtered = filtered.filter(req => !isSubdivisionRequirement(req));
      console.log('[Smart Filters] Filtered out subdivision requirements:', {
        removed: generalData.requirements.length - filtered.length
      });
    }

    // Apply heritage filter
    if (!showHeritageOverride && !propertyHasHeritage) {
      const beforeHeritage = filtered.length;
      filtered = filtered.filter(req => !isHeritageRequirement(req));
      console.log('[Smart Filters] Filtered out heritage requirements:', {
        removed: beforeHeritage - filtered.length
      });
    }

    console.log('[Smart Filters] Final filtered count:', {
      before: generalData.requirements.length,
      after: filtered.length,
      totalRemoved: generalData.requirements.length - filtered.length
    });

    return filtered;
  }, [generalData.requirements, showSubdivisionOverride, propertyCanSubdivide, showHeritageOverride, propertyHasHeritage]);

  // Count requirements for display
  const subdivisionCount = React.useMemo(() => {
    return generalData.requirements.filter(isSubdivisionRequirement).length;
  }, [generalData.requirements]);

  const heritageCount = React.useMemo(() => {
    return generalData.requirements.filter(isHeritageRequirement).length;
  }, [generalData.requirements]);

  const subdivisionFiltered = !propertyCanSubdivide && !showSubdivisionOverride && subdivisionCount > 0;
  const heritageFiltered = !propertyHasHeritage && !showHeritageOverride && heritageCount > 0;

  // Prioritize requirements (numeric vs qualitative) - using filtered list
  const prioritized = prioritizeRequirements(filteredRequirements);

  // Collapsible sections
  const [generalExpanded, setGeneralExpanded] = useState(false);
  const [precinctExpanded, setPrecinctExpanded] = useState(true);

  const totalProvisions = generalData.count + (precinctData?.count || 0);
  const totalRequirements = generalData.requirements_count + (precinctData?.requirements_count || 0);

  // Determine filtering level from data if not provided
  const detectedFilteringLevel = filteringLevel || (() => {
    if (generalData.source.includes('Chapter F')) return 'zone+devtype';
    if (generalData.source.includes('Part 4')) return 'devtype';
    return 'universal';
  })();

  // State for showing filter details
  const [showFilterDetails, setShowFilterDetails] = useState(false);

  // Create filtered combined categories (apply subdivision filter to general requirements)
  const filteredCombinedCategories = React.useMemo(() => {
    return combinedCategories.map(cat => ({
      ...cat,
      general_requirements: filteredRequirements.filter(req => req.category === cat.category),
      general_count: filteredRequirements.filter(req => req.category === cat.category).length,
      total_count: filteredRequirements.filter(req => req.category === cat.category).length + cat.precinct_count
    }));
  }, [combinedCategories, filteredRequirements]);

  // Get council-specific setback approach info
  const getSetbackApproach = (council: string) => {
    if (council === 'Ashfield') return { approach: 'Prescriptive Minimums', color: 'bg-blue-100 text-blue-800 border-blue-300' };
    return { approach: 'Character-Based', color: 'bg-purple-100 text-purple-800 border-purple-300' };
  };

  const setbackInfo = formerCouncil ? getSetbackApproach(formerCouncil) : null;

  return (
    <div className="w-full">
      {/* Smart Filter Summary */}
      <div className="bg-blue-50 border-l-4 border-blue-500 p-3 mb-6 text-sm">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-700 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-medium text-blue-900 mb-1">
                Showing {prioritized.numeric.length} numeric requirements + {prioritized.qualitative.length} qualitative requirements
                {(subdivisionFiltered || heritageFiltered) && ` (${(subdivisionFiltered ? subdivisionCount : 0) + (heritageFiltered ? heritageCount : 0)} hidden)`}
              </p>
              <p className="text-blue-800 text-xs mb-2">
                Automatically organized based on your property:
              </p>
              <ul className="text-blue-800 text-xs space-y-1">
                <li>• <strong>Numeric requirements</strong> ({prioritized.numeric.length}): Setbacks, heights, areas - actionable measurements</li>
                <li>• <strong>Qualitative requirements</strong> ({prioritized.qualitative.length}): Design principles, character, context - important but less prescriptive</li>
                {subdivisionFiltered && (
                  <li className="flex items-center justify-between">
                    <span>• <strong>Subdivision requirements hidden</strong> ({subdivisionCount}): Property is {lotArea ? `${Math.round(lotArea)}m²` : 'unknown size'} - too small to subdivide (450m² minimum)</span>
                    <button
                      onClick={() => setShowSubdivisionOverride(true)}
                      className="ml-2 text-xs text-blue-700 hover:text-blue-900 underline whitespace-nowrap"
                    >
                      Show anyway
                    </button>
                  </li>
                )}
                {heritageFiltered && (
                  <li className="flex items-center justify-between">
                    <span>• <strong>Heritage requirements hidden</strong> ({heritageCount}): Property not in Heritage Conservation Area</span>
                    <button
                      onClick={() => setShowHeritageOverride(true)}
                      className="ml-2 text-xs text-blue-700 hover:text-blue-900 underline whitespace-nowrap"
                    >
                      Show anyway
                    </button>
                  </li>
                )}
                {prioritized.objectives.length > 0 && (
                  <li>• <strong>Design objectives auto-collapsed</strong> ({prioritized.objectives.length}): Informational only, not compliance requirements</li>
                )}
                <li>• <strong>Development type filter</strong>: Auto-detected from {zone} zone → {developmentType.replace(/_/g, ' ')} controls</li>
              </ul>
              <button
                onClick={() => setShowFilterDetails(!showFilterDetails)}
                className="text-xs text-blue-700 underline mt-2 hover:text-blue-900"
              >
                {showFilterDetails ? 'Hide' : 'Show'} filtering details
              </button>
            </div>
          </div>

          {showFilterDetails && (
            <div className="mt-3 pt-3 border-t border-blue-200 text-xs text-blue-800 space-y-2">
              <div>
                <strong>How numeric/qualitative split works:</strong> Requirements with specific measurements (value_numeric, value_min, value_max) are shown first as "numeric requirements" - these are directly actionable. Requirements without measurements are "qualitative" - equally important for DA approval but focus on design principles, character compatibility, and contextual considerations.
              </div>
              {subdivisionFiltered && (
                <div>
                  <strong>Subdivision filtering:</strong> Properties under 450m² cannot legally be subdivided under Inner West LEP. Since your property is {lotArea ? `${Math.round(lotArea)}m²` : 'unknown size'}, {subdivisionCount} subdivision {subdivisionCount === 1 ? 'control' : 'controls'} {subdivisionCount === 1 ? 'has' : 'have'} been automatically hidden. Click "Show anyway" above to view if needed.
                </div>
              )}
              {heritageFiltered && (
                <div>
                  <strong>Heritage filtering:</strong> Heritage Conservation Area (HCA) requirements only apply if your property is within a designated HCA. Since this property is not in an HCA, {heritageCount} heritage {heritageCount === 1 ? 'control' : 'controls'} {heritageCount === 1 ? 'has' : 'have'} been automatically hidden. Click "Show anyway" above to view if needed.
                </div>
              )}
              <div>
                <strong>Development type filtering:</strong> Based on your {zone} zone, clearly irrelevant requirements (e.g., commercial signage for residential developments) have been filtered out. This is conservative filtering - when uncertain, requirements are shown.
              </div>
              {prioritized.objectives.length > 0 && (
                <div>
                  <strong>Objectives:</strong> Design objectives describe council's intent and desired outcomes. They're important context but aren't compliance requirements with specific measurements or standards. They're auto-collapsed to reduce cognitive load while remaining accessible.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Display Mode Toggle - Above DCP General Controls */}
        {precinctData && (
          <div className="mb-6 flex items-center justify-end gap-2">
            <Button
              size="sm"
              variant={displayMode === 'separated' ? 'default' : 'outline'}
              onClick={() => setDisplayMode('separated')}
              className="text-xs h-8"
            >
              Separated
            </Button>
            <Button
              size="sm"
              variant={displayMode === 'combined' ? 'default' : 'outline'}
              onClick={() => setDisplayMode('combined')}
              className="text-xs h-8"
            >
              Combined
            </Button>
          </div>
        )}
        {/* General Controls Section */}
        <div className="mb-8">
          <div
            className="flex items-center gap-3 mb-4 cursor-pointer"
            onClick={() => setGeneralExpanded(!generalExpanded)}
          >
            {generalExpanded ? <ChevronDown className="w-4 h-4 text-gray-700 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-700 flex-shrink-0" />}
            <div className="w-1 h-8 bg-teal-500 rounded"></div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                DCP General Controls
                <Badge variant="outline" className="text-xs bg-teal-50 text-teal-700 border-teal-300">
                  {generalData.requirements_count} Requirements
                </Badge>
              </h3>
              <p className="text-sm text-gray-600">
                {formerCouncil ? `${formerCouncil} DCP ${formerCouncil === 'Ashfield' ? '2016' : formerCouncil === 'Marrickville' ? '2011' : '2013'} ${generalData.source}` : generalData.source}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {developmentType.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ')}{formerCouncil && ` · Former council area: ${formerCouncil} Council`}
              </p>
            </div>
          </div>

          {generalExpanded && (
            <>
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-green-800 flex items-center gap-2">
                  <Badge className="bg-green-500 hover:bg-green-500 text-white text-xs px-2 py-0.5">
                    Council-wide
                  </Badge>
                  <span><strong>Applies to:</strong> {formerCouncil ? `All properties in the former area of ${formerCouncil} council` : generalData.applicable_to}</span>
                </p>
              </div>

              {filteredCombinedCategories.filter(cat => cat.general_count > 0).length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No general provisions for this zone and development type
                </div>
              ) : (
                filteredCombinedCategories
                  .filter(cat => cat.general_count > 0)
                  .map((cat, idx) => (
                    <CategorySection
                      key={cat.category}
                      category={cat}
                      defaultExpanded={cat.category === expandedCategory}
                      setViewingPdfImage={setViewingPdfImage}
                      showOnly={displayMode === 'separated' ? 'general' : 'both'}
                    />
                  ))
              )}
            </>
          )}
        </div>

        {/* Precinct Controls Section */}
        {precinctData && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-1 h-8 bg-green-400 rounded"></div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  {formerCouncil === 'Leichhardt' ? 'Distinctive Neighbourhood Controls' : 'Precinct Controls'}
                  <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-300">
                    {precinctData.requirements_count} Requirements
                  </Badge>
                </h3>
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">
                    {formerCouncil === 'Leichhardt' ? 'Leichhardt Distinctive Neighbourhood name:' :
                     formerCouncil === 'Marrickville' ? 'Marrickville Precinct name:' :
                     formerCouncil === 'Ashfield' ? 'Ashfield Precinct name:' :
                     'Precinct name:'}
                  </span>
                  {' '}{precinctData.precinct_name}
                </p>
              </div>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-green-800 flex items-center gap-2">
                <Badge className="bg-green-500 hover:bg-green-500 text-white text-xs px-2 py-0.5">
                  {formerCouncil === 'Leichhardt' ? 'Neighbourhood' : 'Precinct'}
                </Badge>
                <span><strong>Applies to:</strong> {precinctData.applicable_to}</span>
              </p>
              <p className="text-xs text-green-700 mt-1">
                These controls apply <strong>in addition to</strong> the general controls above
              </p>
            </div>

            {filteredCombinedCategories
              .filter(cat => cat.precinct_count > 0)
              .map((cat) => (
                <CategorySection
                  key={cat.category}
                  category={cat}
                  defaultExpanded={false}
                  setViewingPdfImage={setViewingPdfImage}
                  showOnly={displayMode === 'separated' ? 'precinct' : 'both'}
                />
              ))}
          </div>
        )}

        {/* No precinct message - only show for Ashfield (Marrickville/Leichhardt all have precincts/neighbourhoods) */}
        {!precinctData && formerCouncil === 'Ashfield' && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
            <p className="text-sm text-gray-600">
              This property is not within a specific precinct area.
              Only general DCP controls apply.
            </p>
          </div>
        )}

      {/* PDF Viewer Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        imageUrl={viewingPdfImage?.url}
        pageNumber={viewingPdfImage?.page}
        title="DCP Source Document"
      />
    </div>
  );
};

export default GeneralDCPSection;
