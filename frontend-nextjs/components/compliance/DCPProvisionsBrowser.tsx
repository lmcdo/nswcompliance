'use client';

/**
 * DCP Provisions Browser
 * User-controlled browsing of all 220k DCP provisions with search and filtering
 */

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, Filter, ChevronDown, ChevronRight, FileImage } from 'lucide-react';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { getProvisionDisplayTitle } from '@/lib/provision-title-utils';

interface ProvisionResult {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
  pdf_page: number;
  zone: string;
  development_type: string;
  pdf_page_image_url?: string;
}

interface DCPProvisionsBrowserProps {
  lga: string;
  zone: string;
  developmentType: string;
  address?: string;
  onViewProvision: (provision: ProvisionResult) => void;
  // Precinct cross-reference data
  precinctDetected?: boolean;
  precinctName?: string;
  precinctCategories?: Record<string, number>; // e.g., { setback_front: 1, landscaping: 2 }
}

const CATEGORY_OPTIONS = [
  { id: 'setback', label: 'Setbacks', keywords: 'setback|building line|(front|side|rear).{0,20}(boundary|wall|metre|meter|m\\s)' },
  { id: 'landscaping', label: 'Landscaping', keywords: 'landscap|garden|planting|deep soil' },
  { id: 'privacy', label: 'Privacy', keywords: 'privacy|screening|overlooking' },
  { id: 'solar', label: 'Solar Access', keywords: 'solar|shadow|overshadow|sunlight' },
  { id: 'design', label: 'Building Design', keywords: 'design|character|appearance|facade|material' },
  { id: 'open_space', label: 'Open Space', keywords: 'open space|courtyard|balcon' }
];

const PROVISION_TYPE_OPTIONS = [
  { id: 'all', label: 'All Types' },
  { id: 'table', label: 'Tables Only' },
  { id: 'control', label: 'Controls Only' },
  { id: 'objective', label: 'Objectives Only' }
];

export function DCPProvisionsBrowser({
  lga,
  zone,
  developmentType,
  address,
  onViewProvision,
  precinctDetected = false,
  precinctName,
  precinctCategories = {}
}: DCPProvisionsBrowserProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [provisions, setProvisions] = useState<ProvisionResult[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [expandedProvisionId, setExpandedProvisionId] = useState<number | null>(null);
  const [viewingPdfImage, setViewingPdfImage] = useState<string | null>(null);

  // Query metadata from API
  const [queryMetadata, setQueryMetadata] = useState<any>(null);

  // Filter state
  const [search, setSearch] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [provisionType, setProvisionType] = useState('all');
  const [offset, setOffset] = useState(0);
  const limit = 10;

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [debouncedCategories, setDebouncedCategories] = useState<string[]>([]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setOffset(0); // Reset pagination on search change
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Debounce category changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedCategories(selectedCategories);
      setOffset(0); // Reset pagination on category change
    }, 150); // Faster than search (150ms vs 300ms)
    return () => clearTimeout(timer);
  }, [selectedCategories]);

  // Fetch provisions when filters change
  useEffect(() => {
    if (!expanded) return;

    const fetchProvisions = async () => {
      try {
        setLoading(true);

        // Build category keywords (OR pattern)
        const categoryKeywords = debouncedCategories.length > 0
          ? debouncedCategories
              .map(catId => CATEGORY_OPTIONS.find(c => c.id === catId)?.keywords)
              .filter(Boolean)
          : undefined;

        const response = await fetch('/api/dcp/provisions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lga,
            zone,
            developmentType,
            address,
            search: debouncedSearch || undefined,
            categories: categoryKeywords,
            provisionType,
            limit,
            offset
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            // Append or replace based on offset
            if (offset === 0) {
              setProvisions(data.data.provisions);
            } else {
              setProvisions(prev => [...prev, ...data.data.provisions]);
            }
            setTotalCount(data.data.totalCount);
            setHasMore(data.data.hasMore);
            // Store query metadata for display
            setQueryMetadata(data.metadata);
          }
        }
      } catch (error) {
        console.error('[DCPProvisionsBrowser] Failed to fetch provisions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProvisions();
  }, [expanded, lga, zone, developmentType, address, debouncedSearch, debouncedCategories, provisionType, offset, limit]);

  const toggleCategory = (categoryId: string) => {
    setSelectedCategories(prev => {
      if (prev.includes(categoryId)) {
        return prev.filter(id => id !== categoryId);
      } else {
        return [...prev, categoryId];
      }
    });
    setOffset(0); // Reset pagination
  };

  const loadMore = () => {
    setOffset(prev => prev + limit);
  };

  const getProvisionTypeLabel = (provisionText: string): string => {
    if (provisionText.includes('<table')) return 'TABLE';
    if (provisionText.match(/[0-9]+\.?[0-9]*\s*(m|metre|%|sqm|m²)/)) return 'NUMERIC';
    if (provisionText.match(/^(Control|Controls)/i)) return 'CONTROL';
    if (provisionText.match(/^(Objective|Objectives)/i)) return 'OBJECTIVE';
    return 'TEXT';
  };

  const getTypeColor = (type: string): string => {
    switch (type) {
      case 'TABLE': return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'NUMERIC': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'CONTROL': return 'bg-green-100 text-green-800 border-green-300';
      case 'OBJECTIVE': return 'bg-gray-100 text-gray-700 border-gray-300';
      default: return 'bg-gray-100 text-gray-600 border-gray-300';
    }
  };

  return (
    <div className="border-t pt-4 mt-4">
      {/* Expandable Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left hover:bg-gray-50 p-2 rounded-lg transition-colors"
      >
        <div className="flex items-center gap-2">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          <span className="font-semibold text-sm">
            📚 Browse All {developmentType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Provisions
          </span>
          {!expanded && totalCount > 0 && (
            <Badge variant="outline" className="ml-2">{totalCount} provisions</Badge>
          )}
        </div>
        {!expanded && (
          <span className="text-xs text-gray-500">Click to search & filter</span>
        )}
      </button>

      {/* Expanded Filter Panel */}
      {expanded && (
        <div className="mt-4 space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              type="text"
              placeholder={`Search provisions for ${developmentType.replace(/_/g, ' ')} (filtered by Development Type above)...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 text-sm"
            />
          </div>
          <div className="text-xs text-gray-500 -mt-2 bg-blue-50 border border-blue-200 rounded p-3">
            <strong>ℹ️ Showing {totalCount} provisions for {developmentType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong>
            <ul className="ml-4 mt-1 list-disc text-gray-700">
              <li><strong>Part 2:</strong> General controls (parking, fencing, privacy, solar access, landscaping)</li>
              <li><strong>Part 4.X:</strong> Development-specific requirements for {developmentType.replace(/_/g, ' ')}</li>
            </ul>
            <div className="text-blue-700 font-medium mt-2">
              💡 Change "Development Type" dropdown above to see different provisions
            </div>
          </div>

          {/* Precinct Cross-Reference Warning */}
          {(() => {
            if (!precinctDetected || !precinctCategories || Object.keys(precinctCategories).length === 0) {
              return null;
            }

            // Detect overlap between user's search/filters and precinct categories
            const searchLower = debouncedSearch.toLowerCase();
            const selectedCatIds = debouncedCategories;

            // Category mapping: search term/filter ID -> precinct category names
            const categoryMapping: Record<string, string[]> = {
              'setback': ['setback_front', 'setback_side', 'setback_rear'],
              'landscaping': ['landscaping'],
              'privacy': ['privacy'],
              'solar': ['solar'],
              'design': ['character', 'design'],
              'open_space': ['open_space']
            };

            // Find overlapping precinct categories
            let matchingPrecinctCategories: string[] = [];
            let totalPrecinctReqs = 0;
            let searchContext = '';

            // Check active category filters
            if (selectedCatIds.length > 0) {
              selectedCatIds.forEach(filterId => {
                const precinctCatNames = categoryMapping[filterId] || [];
                precinctCatNames.forEach(precinctCat => {
                  if (precinctCategories[precinctCat]) {
                    matchingPrecinctCategories.push(precinctCat);
                    totalPrecinctReqs += precinctCategories[precinctCat];
                  }
                });
              });
              searchContext = selectedCatIds.map(id =>
                CATEGORY_OPTIONS.find(c => c.id === id)?.label || id
              ).join(', ');
            }
            // Check search term
            else if (searchLower) {
              Object.entries(categoryMapping).forEach(([keyword, precinctCatNames]) => {
                if (searchLower.includes(keyword)) {
                  precinctCatNames.forEach(precinctCat => {
                    if (precinctCategories[precinctCat]) {
                      matchingPrecinctCategories.push(precinctCat);
                      totalPrecinctReqs += precinctCategories[precinctCat];
                    }
                  });
                  searchContext = keyword;
                }
              });
            }

            // Show warning if overlap detected
            if (matchingPrecinctCategories.length > 0 && totalPrecinctReqs > 0) {
              const scrollToPrecinct = () => {
                const element = document.getElementById('precinct-requirements-card');
                if (element) {
                  element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  // Flash the element to draw attention
                  element.classList.add('ring-4', 'ring-purple-400', 'ring-opacity-50');
                  setTimeout(() => {
                    element.classList.remove('ring-4', 'ring-purple-400', 'ring-opacity-50');
                  }, 2000);
                }
              };

              return (
                <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-3 mt-3">
                  <div className="flex items-start gap-2">
                    <span className="text-yellow-600 text-lg flex-shrink-0">⚠️</span>
                    <div className="text-sm flex-1">
                      <strong className="text-yellow-900">Don't miss precinct-specific controls:</strong>
                      <p className="mt-1 text-gray-700">
                        This address is in <strong>{precinctName}</strong>.
                      </p>
                      <button
                        onClick={scrollToPrecinct}
                        className="mt-2 text-blue-600 hover:text-blue-800 font-medium underline flex items-center gap-1"
                      >
                        <span>→ View {totalPrecinctReqs} additional {searchContext || 'requirement'}{totalPrecinctReqs !== 1 ? 's' : ''}</span>
                        <span className="text-xs">specific to this precinct below</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            }

            // Show general precinct notice even without overlap
            return (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mt-3">
                <div className="flex items-start gap-2">
                  <span className="text-purple-600 text-lg flex-shrink-0">📍</span>
                  <div className="text-sm text-gray-700">
                    This address is in <strong>{precinctName}</strong>.
                    <button
                      onClick={() => {
                        const element = document.getElementById('precinct-requirements-card');
                        element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                      }}
                      className="ml-1 text-purple-600 hover:text-purple-800 font-medium underline"
                    >
                      View precinct-specific requirements below
                    </button>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Category Filters */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-xs font-medium text-gray-700">Quick Filters:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {CATEGORY_OPTIONS.map(category => (
                <button
                  key={category.id}
                  onClick={() => toggleCategory(category.id)}
                  className={`
                    px-3 py-1 rounded-full text-xs font-medium border transition-colors
                    ${selectedCategories.includes(category.id)
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
                    }
                  `}
                >
                  {selectedCategories.includes(category.id) && '✓ '}
                  {category.label}
                </button>
              ))}
            </div>
          </div>

          {/* Provision Type Filter */}
          <div className="flex gap-2">
            {PROVISION_TYPE_OPTIONS.map(option => (
              <button
                key={option.id}
                onClick={() => {
                  setProvisionType(option.id);
                  setOffset(0);
                }}
                className={`
                  px-3 py-1 rounded text-xs font-medium border transition-colors
                  ${provisionType === option.id
                    ? 'bg-gray-800 text-white border-gray-800'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'
                  }
                `}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* QUERY SUMMARY PANEL - Shows exactly what's being searched */}
          {queryMetadata && (
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-300 rounded-lg p-4">
              <div className="text-sm font-bold text-purple-900 mb-2 flex items-center gap-2">
                <span className="text-lg">🔍</span>
                QUERY SUMMARY - What You're Actually Seeing:
              </div>

              <div className="space-y-2 text-xs">
                {/* Development Type */}
                <div className="bg-white rounded px-3 py-2 border border-purple-200">
                  <span className="font-semibold text-gray-700">Development Type:</span>
                  <span className="ml-2 text-purple-700 font-bold">
                    {queryMetadata.developmentType.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </div>

                {/* DCP Sections Being Searched */}
                <div className="bg-white rounded px-3 py-2 border border-purple-200">
                  <div className="font-semibold text-gray-700 mb-1">Searching DCP Sections:</div>
                  <div className="text-purple-700 font-medium">{queryMetadata.dcpSection}</div>
                </div>

                {/* Active Filters */}
                {(queryMetadata.filters?.search || queryMetadata.filters?.categories || queryMetadata.filters?.provisionType) && (
                  <div className="bg-white rounded px-3 py-2 border border-purple-200">
                    <div className="font-semibold text-gray-700 mb-1">Active Filters:</div>
                    <ul className="list-disc list-inside text-purple-700 space-y-0.5">
                      {queryMetadata.filters.search && (
                        <li>Search: "{queryMetadata.filters.search}"</li>
                      )}
                      {queryMetadata.filters.categories && (
                        <li>Categories: {queryMetadata.filters.categories.join(', ')}</li>
                      )}
                      {queryMetadata.filters.provisionType && (
                        <li>Type: {queryMetadata.filters.provisionType}</li>
                      )}
                    </ul>
                  </div>
                )}

                {/* Why These Sections */}
                <div className="bg-yellow-50 rounded px-3 py-2 border border-yellow-300">
                  <div className="font-semibold text-gray-700 mb-1">💡 Why These Sections?</div>
                  <ul className="list-disc list-inside text-gray-700 space-y-0.5">
                    <li><strong>Part 2:</strong> General controls apply to ALL developments</li>
                    <li><strong>Part 4.X:</strong> Specific controls for {queryMetadata.developmentType.replace(/_/g, ' ')}</li>
                  </ul>
                </div>

                {/* Result Count */}
                <div className="bg-green-50 rounded px-3 py-2 border border-green-300 text-center">
                  <span className="text-lg font-bold text-green-700">{totalCount}</span>
                  <span className="text-gray-700 ml-2">provisions match this query</span>
                </div>
              </div>
            </div>
          )}

          {/* Results List */}
          <div className="space-y-2">
            {provisions.map((provision, index) => {
              const typeLabel = getProvisionTypeLabel(provision.provision_text);
              const typeColor = getTypeColor(typeLabel);
              const textPreview = provision.provision_text
                .replace(/<[^>]+>/g, ' ') // Strip HTML
                .substring(0, 150)
                .trim();
              const isExpanded = expandedProvisionId === provision.id;

              return (
                <div key={`${provision.id}-${index}`}>
                  <Card
                    className={`p-3 hover:shadow-md transition-shadow cursor-pointer ${
                      isExpanded ? 'ring-2 ring-blue-500' : ''
                    }`}
                    onClick={() => {
                      if (isExpanded) {
                        setExpandedProvisionId(null);
                      } else {
                        setExpandedProvisionId(provision.id);
                      }
                    }}
                  >
                    <div className="flex items-start gap-2">
                      <Badge className={`text-xs px-2 py-0.5 border ${typeColor}`}>
                        {typeLabel}
                      </Badge>
                      <div className="flex-1 min-w-0">
                        {provision.section_header && (
                          <div className="text-xs font-semibold text-gray-700 mb-1">
                            {provision.section_header}
                          </div>
                        )}
                        <div className="text-xs text-gray-600 line-clamp-2">
                          {textPreview}...
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-blue-600 hover:text-blue-700 font-medium">
                            {isExpanded ? 'Hide Full Text ▲' : 'View Full Text ▼'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Card>

                  {/* Expanded Full Text */}
                  {isExpanded && (
                    <div className="mt-2 mb-4 border rounded-lg bg-gray-50 p-4 relative">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedProvisionId(null);
                        }}
                        className="absolute top-2 right-2 text-gray-500 hover:text-gray-700 bg-white rounded-full p-1 shadow-sm"
                        aria-label="Close"
                      >
                        <span className="text-lg leading-none">×</span>
                      </button>
                      <div className="pr-8">
                        <div className="mb-2 pb-2 border-b">
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <Badge className={`text-xs px-2 py-0.5 border ${typeColor}`}>
                                {typeLabel}
                              </Badge>
                              <span className="text-xs text-gray-500">
                                {getProvisionDisplayTitle({
                                  id: provision.id,
                                  ref_number: provision.ref_number,
                                  section_header: provision.section_header || '',
                                  provision_text: provision.provision_text,
                                  document_id: provision.document_id
                                })}
                              </span>
                            </div>
                            {provision.pdf_page_image_url && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setViewingPdfImage(provision.pdf_page_image_url || null);
                                }}
                                className="p-1.5 rounded hover:bg-blue-100 transition-colors"
                                title={`View PDF page ${provision.pdf_page}`}
                              >
                                <FileImage className="w-5 h-5 text-blue-500 hover:text-blue-700" />
                              </button>
                            )}
                          </div>
                        </div>
                        <div
                          className="text-sm text-gray-700 prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{
                            __html: (() => {
                              let html = provision.provision_text;

                              // Remove the first markdown heading if it duplicates section_header
                              // This happens because extraction script adds "# section_number section_title" at start
                              if (provision.section_header) {
                                // Remove lines like "# 2.7.3 Solar access for surrounding buildings"
                                html = html.replace(/^#\s+[\d.]+\s+[^\n]+\n\n?/m, '');
                              }

                              // Strip remaining markdown formatting
                              // Remove markdown headings (# text) - but not at start if already removed
                              html = html.replace(/^#+\s+(.+)$/gm, '<h3 class="font-semibold text-base mt-2 mb-1">$1</h3>');

                              // Remove markdown bold (**text**) - for table captions
                              html = html.replace(/\*\*Table\s+\d+\*\*\s*\(Page\s+\d+\)/g, ''); // Remove "**Table 1** (Page 13)"

                              // Remove markdown bold in general
                              html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

                              // Remove markdown separators (---) - these create huge gaps
                              html = html.replace(/^---+$/gm, '');

                              // Remove excessive blank lines around tables
                              html = html.replace(/\n{2,}(<table)/g, '\n$1'); // Before tables
                              html = html.replace(/(<\/table>)\n{2,}/g, '$1\n'); // After tables

                              // Format tables with proper styling
                              html = html.replace(/<table/g, '<table class="min-w-full border-collapse border border-gray-300 my-4"');
                              html = html.replace(/<td/g, '<td class="border border-gray-300 px-2 py-1 text-xs"');
                              html = html.replace(/<th/g, '<th class="border border-gray-300 px-2 py-1 text-xs font-semibold bg-gray-100"');

                              // Remove ALL newlines inside tables (they create huge gaps when converted to <br/>)
                              html = html.replace(/(<table[^>]*>)([\s\S]*?)(<\/table>)/g, (match, openTag, content, closeTag) => {
                                // Strip newlines from table content
                                const cleanContent = content.replace(/\n/g, '');
                                return openTag + cleanContent + closeTag;
                              });

                              // Clean up excessive whitespace in text
                              html = html.replace(/\n{4,}/g, '\n\n'); // Max 2 newlines anywhere

                              // Convert line breaks to <br> for paragraphs (but NOT inside tables)
                              html = html.replace(/\n\n/g, '<br/><br/>');
                              html = html.replace(/\n/g, '<br/>');

                              return html;
                            })()
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="text-center pt-2">
              <Button
                onClick={loadMore}
                disabled={loading}
                variant="outline"
                size="sm"
              >
                {loading ? 'Loading...' : `Load More (${totalCount - provisions.length} remaining)`}
              </Button>
            </div>
          )}

          {/* Empty State */}
          {!loading && provisions.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <div className="text-sm">No provisions found</div>
              <div className="text-xs mt-1">Try different search terms or filters</div>
            </div>
          )}
        </div>
      )}

      {/* PDF Page Image Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        imageUrl={viewingPdfImage}
        title="DCP Source Document"
      />
    </div>
  );
}
