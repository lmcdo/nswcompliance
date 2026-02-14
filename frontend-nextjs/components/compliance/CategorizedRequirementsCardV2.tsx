'use client';

/**
 * Week 3: Categorized Requirements Display Component
 * Shows LLM-categorized precinct requirements grouped by category
 * With PDF page grouping feature
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, ExternalLink, CheckCircle, AlertTriangle } from 'lucide-react';
import { PdfPageButton, PdfPageFooter } from './PdfPageButton';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { FormattedProvisionText } from './FormattedProvisionText';
import { stripSectionHeader } from '@/lib/provision-text-formatter';

interface CategorizedRequirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;
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
  pdf_page?: number;  // Page number from matched source provision
  pdf_page_image_url?: string;
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
  developmentType?: string;  // For frontend filtering
  className?: string;
  // NEW: Separated HCA and precinct categories for heritage properties
  hcaCategories?: CategoryGroup[];
  precinctCategories?: CategoryGroup[];
  isHeritage?: boolean;
}

export function CategorizedRequirementsCard({
  categories,
  precinctName,
  developmentType,
  className = '',
  hcaCategories,
  precinctCategories,
  isHeritage = false
}: CategorizedRequirementsCardProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set() // Start with all categories collapsed
  );
  const [expandedRequirementId, setExpandedRequirementId] = useState<number | null>(null);
  const [sourceProvisions, setSourceProvisions] = useState<any[]>([]);
  const [loadingSource, setLoadingSource] = useState(false);
  const [viewingPdfImage, setViewingPdfImage] = useState<string | null>(null);

  // Frontend filtering by development type
  const filteredCategories = developmentType ? categories.map(cat => {
    // Filter requirements based on development type keywords
    const devTypeKeywords = developmentType.replace(/_/g, ' ').toLowerCase();

    const filtered = cat.requirements.filter(req => {
      const text = req.requirement_text.toLowerCase();
      const verbatim = (req as any).verbatim_source_text?.toLowerCase() || '';
      const fullText = text + ' ' + verbatim;

      // Universal requirements (apply to all dev types)
      if (fullText.includes('all development') || fullText.includes('any development') ||
          fullText.includes('all properties') || fullText.includes('any building')) {
        console.log(`[Filter] ✅ KEEP (universal): "${text.substring(0, 80)}..."`);
        return true;
      }

      // Dwelling house filtering
      if (devTypeKeywords.includes('dwelling house') || devTypeKeywords.includes('dwelling_house')) {
        const isDwellingHouse = fullText.includes('dwelling house') ||
                                fullText.includes('single dwelling') ||
                                fullText.includes('detached dwelling') ||
                                (fullText.includes('dwelling') && !fullText.includes('multi'));

        if (isDwellingHouse) {
          console.log(`[Filter] ✅ KEEP (dwelling house): "${text.substring(0, 80)}..."`);
          return true;
        }

        // Hide multi-dwelling requirements when in dwelling_house mode
        if (fullText.includes('multi dwelling') ||
            fullText.includes('multi-dwelling') ||
            fullText.includes('residential flat') ||
            fullText.includes('apartment')) {
          console.log(`[Filter] ❌ HIDE (multi-dwelling for dwelling_house): "${text.substring(0, 80)}..."`);
          return false;
        }
      }

      // Multi dwelling filtering
      if (devTypeKeywords.includes('multi dwelling') || devTypeKeywords.includes('multi_dwelling')) {
        const isMultiDwelling = fullText.includes('multi dwelling') ||
                                fullText.includes('multi-dwelling') ||
                                fullText.includes('dual occupancy') ||
                                fullText.includes('residential flat') ||
                                fullText.includes('apartment');

        if (isMultiDwelling) {
          console.log(`[Filter] ✅ KEEP (multi-dwelling): "${text.substring(0, 80)}..."`);
          return true;
        }
      }

      // Character/streetscape controls (usually universal)
      if (fullText.includes('streetscape') || fullText.includes('character') ||
          fullText.includes('heritage') || fullText.includes('setback') ||
          fullText.includes('parking')) {
        console.log(`[Filter] ✅ KEEP (character/universal): "${text.substring(0, 80)}..."`);
        return true;
      }

      // Default: show all (precinct controls are usually geography-based, not dev-type specific)
      console.log(`[Filter] ✅ KEEP (default/no match): "${text.substring(0, 80)}..."`);
      return true;
    });

    const beforeCount = cat.requirements.length;
    const afterCount = filtered.length;
    if (beforeCount !== afterCount) {
      console.log(`[Filter] Category "${cat.category}": ${beforeCount} → ${afterCount} requirements (removed ${beforeCount - afterCount})`);
    }

    return {
      ...cat,
      requirements: filtered,
      total_count: filtered.length,
      high_confidence_count: filtered.filter(r => r.confidence === 'high').length,
      validated_count: filtered.filter(r => r.validated).length
    };
  }).filter(cat => cat.requirements.length > 0) : categories;

  // DEBUG: Check if PDF URLs are present
  console.log('[CategorizedRequirementsCard] Received categories:', categories.length);
  console.log('[CategorizedRequirementsCard] Filtered categories:', filteredCategories.length);
  console.log('[CategorizedRequirementsCard] Development type:', developmentType);
  if (filteredCategories.length > 0) {
    const firstCat = filteredCategories[0];
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

  const formatValue = (req: CategorizedRequirement) => {
    if (req.value_min && req.value_max) {
      return `${req.value_min}-${req.value_max} ${req.unit || ''}`;
    } else if (req.value_numeric) {
      return `${req.value_numeric} ${req.unit || ''}`;
    }
    return null;
  };

  if (!filteredCategories || filteredCategories.length === 0) {
    return null;
  }

  const totalRequirements = filteredCategories.reduce((sum, cat) => sum + cat.total_count, 0);
  const totalHighConfidence = filteredCategories.reduce((sum, cat) => sum + cat.high_confidence_count, 0);
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

        {/* HCA Universal Heritage Controls - shown first for heritage properties */}
        {isHeritage && hcaCategories && hcaCategories.length > 0 && (
          <div id="dcp-hca-section" className="border border-blue-200 rounded-lg overflow-hidden bg-blue-50/30 mb-4">
            <div className="px-4 py-3 bg-blue-100/50 border-b border-blue-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-blue-700 text-lg">🏛️</span>
                  <div>
                    <h3 className="font-semibold text-blue-900">Heritage Conservation Areas</h3>
                    <p className="text-xs text-blue-700">
                      {hcaCategories.reduce((sum, cat) => sum + cat.total_count, 0)} controls
                    </p>
                  </div>
                </div>
              </div>
              {/* Contextual note */}
              <p className="text-xs text-blue-800 mt-2 bg-blue-100 rounded px-2 py-1">
                These controls apply to all Heritage Conservation Areas in Inner West (former Leichhardt).
              </p>
            </div>
            <div className="p-3 space-y-2">
              {hcaCategories.map(category => (
                <div key={`hca-${category.category}`} className="border border-blue-100 rounded bg-white">
                  <button
                    onClick={() => toggleCategory(`hca-${category.category}`)}
                    className="w-full px-3 py-2 flex items-center justify-between hover:bg-blue-50/50 transition-colors text-sm"
                  >
                    <div className="flex items-center gap-2">
                      {expandedCategories.has(`hca-${category.category}`) ? (
                        <ChevronDown className="w-4 h-4 text-blue-600" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-blue-600" />
                      )}
                      <span className="font-medium text-gray-800">{category.display_name}</span>
                      <span className="text-xs text-gray-500">({category.total_count})</span>
                    </div>
                  </button>
                  {expandedCategories.has(`hca-${category.category}`) && (
                    <div className="px-3 pb-3 space-y-2 border-t border-blue-100">
                      {category.requirements.map(req => (
                        <div key={req.id} className="text-sm text-gray-700 py-2 border-b border-gray-100 last:border-0">
                          {req.requirement_text}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Precinct-specific requirements */}
        {filteredCategories.map(category => {
          const isExpanded = expandedCategories.has(category.category);
          const confidencePercent = Math.round(
            (category.high_confidence_count / category.total_count) * 100
          );

          // Group requirements by PDF page number (simple and reliable)
          // Within a category, all requirements are from the same document, so page number alone is sufficient
          const groupedByPage: { [page: number]: CategorizedRequirement[] } = {};
          const requirementsWithoutPage: CategorizedRequirement[] = [];

          category.requirements.forEach(req => {
            const pageNum = req.pdf_page;
            if (pageNum) {
              if (!groupedByPage[pageNum]) {
                groupedByPage[pageNum] = [];
              }
              groupedByPage[pageNum].push(req);
            } else {
              // Requirements without page numbers shown separately
              requirementsWithoutPage.push(req);
            }
          });

          // Sort page groups by page number (ascending order)
          const sortedPageGroups = Object.entries(groupedByPage)
            .sort(([pageA], [pageB]) => parseInt(pageA) - parseInt(pageB));

          return (
            <div key={category.category} className="border border-purple-100 rounded-lg overflow-hidden bg-white">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.category)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-purple-50/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-full hover:bg-purple-100 transition-colors">
                    {isExpanded ? (
                      <ChevronDown className="w-6 h-6 text-purple-700" />
                    ) : (
                      <ChevronRight className="w-6 h-6 text-purple-700" />
                    )}
                  </div>
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

              {/* Category Requirements - Grouped by PDF Page */}
              {isExpanded && (
                <div className="border-t border-purple-100">
                  {sortedPageGroups.map(([pageNumStr, requirements]) => {
                    const pdfPage = parseInt(pageNumStr);
                    const pdfUrl = requirements[0]?.pdf_page_image_url;
                    const hasMultiple = requirements.length > 1;

                    return (
                      <div key={`page-${pdfPage}`} className="border-b border-purple-50 last:border-b-0">

                        {/* Requirements in this page group */}
                        <div className="divide-y divide-purple-50">
                          {requirements.map((req, idx) => (
                            <div key={req.id} className="px-4 py-3">
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
                                <>
                      {/* Requirement Header */}
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex-1">
                          <p className="text-sm text-gray-900 leading-relaxed">
                            {req.requirement_text}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {req.validated && (
                            <Badge className="bg-blue-100 text-blue-800 text-xs">
                              <CheckCircle className="w-3 h-3" />
                            </Badge>
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
                                  <div className="text-sm text-gray-700">
                                    <FormattedProvisionText
                                      text={stripSectionHeader(provision.provision_text, provision.section_header)}
                                      compact
                                      theme="green"
                                    />
                                  </div>

                                  {/* Provision Footer */}
                                  <div className="mt-2 pt-2 border-t border-gray-200">
                                    <div className="flex items-center gap-3 text-xs text-gray-500 mb-1">
                                      {provision.pdf_name && (
                                        <span>📄 {provision.pdf_name}</span>
                                      )}
                                      {provision.page_number && (
                                        <span>Page {provision.page_number}</span>
                                      )}
                                    </div>
                                    {provision.pdf_page_image_url && (
                                      <PdfPageButton
                                        pageNumber={provision.page_number}
                                        pdfUrl={provision.pdf_page_image_url}
                                        onClick={() => setViewingPdfImage(provision.pdf_page_image_url)}
                                        variant="inline"
                                      />
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                    </div>
                          ))}
                        </div>

                        {/* PDF Page Footer - Standardized button at END of page group */}
                        {pdfPage && pdfUrl && (
                          <PdfPageFooter
                            pageNumber={pdfPage}
                            requirementCount={requirements.length}
                            pdfUrl={pdfUrl}
                            onViewPdf={() => {
                              console.log('[PDF Button] Clicked! URL:', pdfUrl);
                              setViewingPdfImage(pdfUrl);
                            }}
                            accentColor="purple"
                          />
                        )}
                      </div>
                    );
                  })}

                  {/* Requirements without page numbers */}
                  {requirementsWithoutPage.length > 0 && (
                    <div className="border-b border-purple-50 last:border-b-0">
                      <div className="px-4 py-2 bg-gray-50 text-xs text-gray-600">
                        Heritage Requirements
                      </div>
                      <div className="divide-y divide-purple-50">
                        {requirementsWithoutPage.map((req) => (
                          <div key={req.id} className="px-4 py-3">
                            <div className="flex items-start gap-2">
                              <span className="text-purple-600 font-bold">✓</span>
                              <p className="text-sm text-gray-800 flex-1">{req.requirement_text}</p>
                            </div>
                            {/* Show PDF button if URL is available */}
                            {req.pdf_page_image_url && (
                              <div className="mt-2">
                                <button
                                  onClick={() => setViewingPdfImage(req.pdf_page_image_url!)}
                                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-purple-100 text-purple-700 text-xs font-medium rounded hover:bg-purple-200 transition-colors"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  View heritage controls
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
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

      {/* PDF Image Viewer Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        imageUrl={viewingPdfImage}
        title="DCP Source Document"
      />
    </Card>
  );
}
