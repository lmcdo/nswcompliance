'use client';

/**
 * Week 3: Categorized Requirements Display Component
 * Shows LLM-categorized precinct requirements grouped by category
 * FORCE RELOAD v2
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, ExternalLink, CheckCircle, AlertTriangle, FileImage } from 'lucide-react';

interface CategorizedRequirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;  // Summary (prescriptive/actionable parts only)
  verbatim_source_text?: string;  // Exact text from PDF (for user verification)
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  unit?: string;
  confidence: 'high' | 'medium' | 'low';
  has_conditionals: boolean;
  conditional_text?: string;
  validated: boolean;
  source_provision_ids: number[];
  source_document_ids: string[];
  pdf_page_image_url?: string;
  pdf_pages?: number[];  // Array of page numbers where text may appear
}

interface CategoryGroup {
  category: string;
  display_name: string;
  requirements: CategorizedRequirement[];
  total_count: number;
  high_confidence_count: number;
  validated_count: number;
}

interface CategorizedRequirementsCardProps {
  categories: CategoryGroup[];
  precinctName?: string;
  className?: string;
}

export function CategorizedRequirementsCard({
  categories,
  precinctName,
  className = ''
}: CategorizedRequirementsCardProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(categories.slice(0, 3).map(c => c.category)) // Expand first 3 by default
  );
  const [expandedRequirementId, setExpandedRequirementId] = useState<number | null>(null);
  const [expandedVerbatimIds, setExpandedVerbatimIds] = useState<Set<number>>(new Set());
  const [sourceProvisions, setSourceProvisions] = useState<any[]>([]);
  const [loadingSource, setLoadingSource] = useState(false);
  const [viewingPdfPages, setViewingPdfPages] = useState<{pageNumber: number, url: string}[] | null>(null);

  const toggleVerbatimText = (requirementId: number) => {
    const newExpanded = new Set(expandedVerbatimIds);
    if (newExpanded.has(requirementId)) {
      newExpanded.delete(requirementId);
    } else {
      newExpanded.add(requirementId);
    }
    setExpandedVerbatimIds(newExpanded);
  };

  // DEBUG: Check if PDF URLs are present
  console.log('[CategorizedRequirementsCard] Received categories:', categories.length);
  if (categories.length > 0) {
    const firstCat = categories[0];
    console.log('[CategorizedRequirementsCard] First category:', firstCat.category, 'Requirements:', firstCat.requirements.length);
    if (firstCat.requirements.length > 0) {
      const firstReq = firstCat.requirements[0];
      console.log('[CategorizedRequirementsCard] First requirement has pdf_page_image_url:', !!firstReq.pdf_page_image_url);
      console.log('[CategorizedRequirementsCard] PDF URL:', firstReq.pdf_page_image_url);
    }
  }

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const toggleRequirementSource = async (requirementId: number, provisionIds: number[]) => {
    console.log('[toggleRequirementSource] Clicked! Requirement ID:', requirementId, 'Provision IDs:', provisionIds);

    if (expandedRequirementId === requirementId) {
      // Collapse if already expanded
      console.log('[toggleRequirementSource] Collapsing already expanded requirement');
      setExpandedRequirementId(null);
      setSourceProvisions([]);
      return;
    }

    // Expand and fetch source provisions
    console.log('[toggleRequirementSource] Fetching source provisions...');
    setExpandedRequirementId(requirementId);
    setLoadingSource(true);

    try {
      console.log('[toggleRequirementSource] Making fetch request to /api/provisions/by-ids');
      const response = await fetch('/api/provisions/by-ids', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: provisionIds })
      });
      console.log('[toggleRequirementSource] Fetch response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.provisions) {
          setSourceProvisions(data.provisions);
        }
      }
    } catch (error) {
      console.error('Failed to fetch source provisions:', error);
    } finally {
      setLoadingSource(false);
    }
  };

  const getConfidenceBadge = (confidence: 'high' | 'medium' | 'low') => {
    const variants = {
      high: 'default',
      medium: 'secondary',
      low: 'outline'
    };

    const colors = {
      high: 'bg-green-100 text-green-800 border-green-200',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      low: 'bg-gray-100 text-gray-800 border-gray-200'
    };

    return (
      <Badge className={`text-xs ${colors[confidence]}`}>
        {confidence.toUpperCase()}
      </Badge>
    );
  };

  const formatValue = (req: CategorizedRequirement) => {
    if (req.value_min && req.value_max) {
      return `${req.value_min}-${req.value_max} ${req.unit || ''}`;
    } else if (req.value_numeric) {
      return `${req.value_numeric} ${req.unit || ''}`;
    }
    return null;
  };

  if (!categories || categories.length === 0) {
    return null;
  }

  const totalRequirements = categories.reduce((sum, cat) => sum + cat.total_count, 0);
  const totalHighConfidence = categories.reduce((sum, cat) => sum + cat.high_confidence_count, 0);
  const highConfidencePercent = Math.round((totalHighConfidence / totalRequirements) * 100);

  return (
    <Card id="precinct-requirements-card" className={`${className} border-purple-200 bg-purple-50/30 transition-all`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <span className="text-purple-700">📍 Precinct Requirements</span>
            </CardTitle>
            {precinctName && (
              <p className="text-sm text-gray-600 mt-1">{precinctName}</p>
            )}
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-gray-700">
              {totalRequirements} Requirements
            </div>
            <div className="text-xs text-gray-500">
              {highConfidencePercent}% High Confidence
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Info Box: How Precinct Controls Work */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
          <div className="flex items-start gap-2">
            <span className="text-blue-600 text-lg flex-shrink-0">💡</span>
            <div className="text-sm text-gray-700">
              <strong className="text-blue-900">How Precinct Controls Work:</strong>
              <p className="mt-1">
                These location-specific requirements <strong>supplement or override</strong> the general DCP controls shown above.
              </p>
              <ul className="mt-2 ml-4 space-y-1 text-xs">
                <li className="flex items-start gap-1">
                  <span className="text-blue-600 flex-shrink-0">•</span>
                  <span>If a precinct control conflicts with a general control (e.g., different setback distances), the <strong>precinct control takes precedence</strong>.</span>
                </li>
                <li className="flex items-start gap-1">
                  <span className="text-blue-600 flex-shrink-0">•</span>
                  <span>Precinct controls may also add <strong>additional requirements</strong> not found in general controls (e.g., heritage character considerations).</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {categories.map(category => {
          const isExpanded = expandedCategories.has(category.category);
          const confidencePercent = Math.round(
            (category.high_confidence_count / category.total_count) * 100
          );

          return (
            <div key={category.category} className="border border-purple-100 rounded-lg overflow-hidden bg-white">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.category)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-purple-50/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-purple-600" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-purple-600" />
                  )}
                  <div className="text-left">
                    <div className="font-medium text-gray-900">
                      {category.display_name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {category.total_count} requirement{category.total_count !== 1 ? 's' : ''}
                      {' · '}
                      {confidencePercent}% high confidence
                    </div>
                  </div>
                </div>
                {category.validated_count > 0 && (
                  <Badge className="bg-blue-100 text-blue-800 text-xs">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    {category.validated_count} Validated
                  </Badge>
                )}
              </button>

              {/* Category Requirements */}
              {isExpanded && (
                <div className="border-t border-purple-100 divide-y divide-purple-50">
                  {category.requirements.map((req, idx) => (
                    <div key={req.id} className="px-4 py-3 hover:bg-purple-50/30 transition-colors">
                      {/* Requirement Header */}
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex-1">
                          <p className="text-sm text-gray-900 leading-relaxed">
                            {req.requirement_text}
                          </p>

                          {/* Verbatim Text (Expandable) */}
                          {req.verbatim_source_text && req.verbatim_source_text !== req.requirement_text && (
                            <div className="mt-2">
                              <button
                                onClick={() => toggleVerbatimText(req.id)}
                                className="text-xs text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1"
                              >
                                {expandedVerbatimIds.has(req.id) ? '▲ Hide' : '▼ View'} exact text from PDF
                              </button>
                              {expandedVerbatimIds.has(req.id) && (
                                <div className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                                  <div className="text-xs font-medium text-gray-700 mb-1">📄 Exact text from PDF:</div>
                                  <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                                    {req.verbatim_source_text}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {getConfidenceBadge(req.confidence)}
                          {req.validated && (
                            <Badge className="bg-blue-100 text-blue-800 text-xs">
                              <CheckCircle className="w-3 h-3" />
                            </Badge>
                          )}
                          {req.pdf_pages && req.pdf_pages.length > 0 && req.pdf_page_image_url && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const pages = req.pdf_pages!.map(pageNum => ({
                                  pageNumber: pageNum,
                                  url: req.pdf_page_image_url!.replace(/_page_\d+\.png$/, `_page_${pageNum}.png`)
                                }));
                                setViewingPdfPages(pages);
                              }}
                              className="p-1.5 rounded hover:bg-blue-100 transition-colors"
                              title={`View PDF Page${req.pdf_pages.length > 1 ? 's ' + req.pdf_pages.join('-') : ' ' + req.pdf_pages[0]}`}
                            >
                              <FileImage className="w-5 h-5 text-blue-500 hover:text-blue-700" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Value Display */}
                      {formatValue(req) && (
                        <div className="mb-2 inline-block">
                          <Badge className="bg-purple-100 text-purple-800 text-sm font-mono">
                            {formatValue(req)}
                          </Badge>
                        </div>
                      )}

                      {/* Conditional Warning */}
                      {req.has_conditionals && (
                        <div className="flex items-start gap-2 mb-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                          <AlertTriangle className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="font-medium text-yellow-900">Contains Conditions</div>
                            {req.conditional_text && (
                              <div className="text-yellow-700 mt-1">{req.conditional_text}</div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Source Link */}
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <div>
                          Source: {req.source_provision_ids.length} provision{req.source_provision_ids.length !== 1 ? 's' : ''}
                        </div>
                        <button
                          onClick={() => toggleRequirementSource(req.id, req.source_provision_ids)}
                          className="flex items-center gap-1 text-purple-600 hover:text-purple-700 hover:underline"
                        >
                          {expandedRequirementId === req.id ? 'Hide Source ▲' : 'View Source ▼'}
                        </button>
                      </div>

                      {/* Expanded Source Provisions - Inline */}
                      {expandedRequirementId === req.id && (
                        <div className="mt-3 border-t border-purple-100 pt-3">
                          {loadingSource ? (
                            <div className="text-sm text-gray-500 italic">Loading source provisions...</div>
                          ) : sourceProvisions.length === 0 ? (
                            <div className="text-sm text-gray-500 italic">No source provisions found</div>
                          ) : (
                            <div className="space-y-3">
                              <div className="text-xs font-medium text-gray-700 mb-2">
                                Source Provisions ({sourceProvisions.length})
                              </div>
                              {sourceProvisions.map((provision, provIdx) => (
                                <div key={provision.id} className="border border-gray-200 rounded-lg bg-gray-50 p-3">
                                  {/* Provision Header */}
                                  <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-200">
                                    {provision.ref_number && (
                                      <Badge variant="outline" className="text-xs">
                                        {provision.ref_number}
                                      </Badge>
                                    )}
                                    {provision.section_header && (
                                      <span className="text-xs font-semibold text-gray-700">
                                        {provision.section_header}
                                      </span>
                                    )}
                                  </div>

                                  {/* Provision Text */}
                                  <div className="text-sm text-gray-700 whitespace-pre-wrap">
                                    {provision.provision_text}
                                  </div>

                                  {/* Provision Footer */}
                                  <div className="flex items-center justify-between gap-3 mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
                                    <div className="flex items-center gap-3">
                                      {provision.pdf_name && (
                                        <span>📄 {provision.pdf_name}</span>
                                      )}
                                      {provision.page_number && (
                                        <span>Page {provision.page_number}</span>
                                      )}
                                    </div>
                                    {provision.pdf_page_image_url && (
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          setViewingPdfPages([{pageNumber: provision.page_number, url: provision.pdf_page_image_url}]);
                                        }}
                                        className="p-1.5 rounded hover:bg-blue-100 transition-colors"
                                        title={`View PDF Page ${provision.page_number}`}
                                      >
                                        <FileImage className="w-5 h-5 text-blue-500 hover:text-blue-700" />
                                      </button>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {/* Help Text */}
        <div className="mt-4 p-3 bg-purple-50 border border-purple-100 rounded-lg text-xs text-gray-600">
          <div className="font-medium text-gray-900 mb-1">About these requirements</div>
          <p>
            These requirements are specific to the {precinctName || 'precinct'} and supplement the base DCP requirements.
            They have been extracted and categorized using AI. High confidence requirements have been validated for accuracy.
          </p>
        </div>
      </CardContent>

      {/* PDF Pages Viewer Modal */}
      {viewingPdfPages && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4"
          onClick={() => setViewingPdfPages(null)}
        >
          <div className="relative max-w-6xl max-h-[90vh] bg-white rounded-lg shadow-xl overflow-y-auto">
            <button
              onClick={() => setViewingPdfPages(null)}
              className="sticky top-2 right-2 float-right bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 z-10 mr-2"
            >
              Close
            </button>
            <div className="p-4 space-y-4" onClick={(e) => e.stopPropagation()}>
              {viewingPdfPages.map((page) => (
                <div key={page.pageNumber} className="border-b border-gray-300 pb-4 last:border-0">
                  <div className="text-sm font-medium text-gray-700 mb-2">Page {page.pageNumber}</div>
                  <img
                    src={page.url}
                    alt={`PDF Page ${page.pageNumber}`}
                    className="w-full object-contain"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
