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
import { Search, Filter, ChevronDown, ChevronRight } from 'lucide-react';

interface ProvisionResult {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
  pdf_page: number;
  zone: string;
  development_type: string;
}

interface DCPProvisionsBrowserProps {
  lga: string;
  zone: string;
  developmentType: string;
  address?: string;
  onViewProvision: (provision: ProvisionResult) => void;
}

const CATEGORY_OPTIONS = [
  { id: 'setback', label: 'Setbacks', keywords: 'setback|boundary' },
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
  onViewProvision
}: DCPProvisionsBrowserProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [provisions, setProvisions] = useState<ProvisionResult[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [expandedProvisionId, setExpandedProvisionId] = useState<number | null>(null);

  // Filter state
  const [search, setSearch] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [provisionType, setProvisionType] = useState('all');
  const [offset, setOffset] = useState(0);
  const limit = 10;

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setOffset(0); // Reset pagination on search change
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Fetch provisions when filters change
  useEffect(() => {
    if (!expanded) return;

    const fetchProvisions = async () => {
      try {
        setLoading(true);

        // Build category keywords (OR pattern)
        const categoryKeywords = selectedCategories.length > 0
          ? selectedCategories
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
          }
        }
      } catch (error) {
        console.error('[DCPProvisionsBrowser] Failed to fetch provisions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProvisions();
  }, [expanded, lga, zone, developmentType, address, debouncedSearch, selectedCategories, provisionType, offset, limit]);

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
          <span className="font-semibold text-sm">📚 Browse All DCP Provisions</span>
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
              placeholder="Search provisions (e.g., 'setback', 'landscaping', 'privacy')..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 text-sm"
            />
          </div>

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

          {/* Results Count */}
          <div className="text-sm text-gray-600">
            {loading && offset === 0 ? (
              <span>Searching...</span>
            ) : (
              <span>
                Found <strong>{totalCount}</strong> provision{totalCount !== 1 ? 's' : ''}
                {selectedCategories.length > 0 && (
                  <span className="ml-1">
                    matching: {selectedCategories.map(id =>
                      CATEGORY_OPTIONS.find(c => c.id === id)?.label
                    ).join(', ')}
                  </span>
                )}
              </span>
            )}
          </div>

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
                          <span className="text-xs text-gray-400">
                            Page {provision.pdf_page}
                          </span>
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
                          <div className="flex items-center gap-2 mb-1">
                            <Badge className={`text-xs px-2 py-0.5 border ${typeColor}`}>
                              {typeLabel}
                            </Badge>
                            <span className="text-xs text-gray-500">
                              {provision.ref_number} • Page {provision.pdf_page}
                            </span>
                          </div>
                          {provision.section_header && (
                            <div className="text-sm font-semibold text-gray-800">
                              {provision.section_header}
                            </div>
                          )}
                        </div>
                        <div
                          className="text-sm text-gray-700 prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{
                            __html: provision.provision_text
                              .replace(/<table/g, '<table class="min-w-full border-collapse border border-gray-300 my-2"')
                              .replace(/<td/g, '<td class="border border-gray-300 px-2 py-1 text-xs"')
                              .replace(/<th/g, '<th class="border border-gray-300 px-2 py-1 text-xs font-semibold bg-gray-100"')
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
    </div>
  );
}
