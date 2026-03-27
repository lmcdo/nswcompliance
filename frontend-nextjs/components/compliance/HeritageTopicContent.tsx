'use client';

// Renders the heritage grouping accordion for a single DCP part within the Heritage topic.
// Handles three nesting levels: subcategory → HCA → heritage type → element filter → provisions.

import { ChevronDown, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { PageGroupedProvisions } from './PageGroupedProvisions';
import {
  Provision,
  HERITAGE_TYPE_CONFIG,
  ELEMENT_LABELS,
  groupByHca,
  groupByHeritageSubcategory,
  groupByHeritageType,
  getElementTotals,
  splitByExclusivity,
  filterByElement,
  formatHcaName,
} from '@/lib/provision-grouping';

interface HeritageTopicContentProps {
  partProvisions: Provision[];
  partKey: string;
  propertyHcaSlug: string;
  // State
  expandedHcas: Set<string>;
  expandedHeritageTypes: Set<string>;
  showAllHeritageTypes: Set<string>;
  elementFilters: Record<string, string>;
  expandedProvisions: Set<number>;
  // Handlers
  toggleHca: (key: string) => void;
  toggleHeritageType: (key: string) => void;
  toggleShowAllHeritageType: (key: string) => void;
  setElementFilter: (key: string, element: string | null) => void;
  toggleProvision: (id: number) => void;
  setViewingPdfImage: (v: { url: string; page: number } | null) => void;
  // Property context
  zone?: string;
  heritage?: boolean;
  hcaName?: string;
  precinctId?: string;
}

export function HeritageTopicContent({
  partProvisions, partKey, propertyHcaSlug,
  expandedHcas, expandedHeritageTypes, showAllHeritageTypes, elementFilters, expandedProvisions,
  toggleHca, toggleHeritageType, toggleShowAllHeritageType, setElementFilter,
  toggleProvision, setViewingPdfImage,
  zone, heritage, hcaName, precinctId,
}: HeritageTopicContentProps) {
  const isPropertyHca = (hca: string) => propertyHcaSlug !== '' && hca === propertyHcaSlug;

  // Check if provisions have subcategory (condition layer) vs HCA (regulatory_provisions)
  const hasSubcategories = partProvisions.some(
    p => p.v2_heritage_subcategory && p.v2_heritage_subcategory !== 'Heritage'
  );

  if (hasSubcategories) {
    return (
      <div className="space-y-2">
        {Array.from(groupByHeritageSubcategory(partProvisions)).map(([subcategory, subcatProvisions]) => {
          const subcatKey = `${partKey}-subcat-${subcategory}`;
          const isSubcatExpanded = expandedHcas.has(subcatKey);

          return (
            <div key={subcatKey} className="border rounded-lg overflow-hidden border-amber-200">
              <button
                onClick={() => toggleHca(subcatKey)}
                className="w-full flex items-center justify-between px-3 py-2 bg-amber-50 hover:bg-amber-100 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {isSubcatExpanded
                    ? <ChevronDown className="h-3 w-3 text-amber-600" />
                    : <ChevronRight className="h-3 w-3 text-amber-600" />
                  }
                  <span className="font-medium text-xs text-amber-800">{subcategory}</span>
                  <Badge variant="secondary" className="text-[10px]">{subcatProvisions.length}</Badge>
                </div>
              </button>

              {isSubcatExpanded && (
                <div className="p-2 bg-white">
                  <PageGroupedProvisions
                    provisionTheme="green"
                    provisions={subcatProvisions}
                    expandedProvisions={expandedProvisions}
                    onToggleProvision={toggleProvision}
                    onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                    theme={{
                      zebraStripeBg: 'bg-amber-50/50',
                      zebraStripeAltBg: 'bg-white',
                      borderColorClass: 'border-amber-200',
                      textClampLines: 2,
                      expandThreshold: 200,
                    }}
                    maxProvisions={20}
                    zone={zone}
                    heritage={heritage}
                    hcaName={hcaName}
                    precinctName={precinctId}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // HCA-grouped path
  return (
    <div className="space-y-2">
      {Array.from(groupByHca(partProvisions, propertyHcaSlug)).map(([hca, hcaProvisions]) => {
        const hcaKey = `${partKey}-hca-${hca}`;
        const isHcaExpanded = expandedHcas.has(hcaKey);
        const isPropertyHcaFlag = isPropertyHca(hca);

        return (
          <div
            key={hcaKey}
            className={`border rounded-lg overflow-hidden ${isPropertyHcaFlag ? 'border-teal-300' : 'border-gray-200'}`}
          >
            <button
              onClick={() => toggleHca(hcaKey)}
              className={`w-full flex items-center justify-between px-3 py-2 transition-colors ${
                isPropertyHcaFlag ? 'bg-teal-50 hover:bg-teal-100' : 'bg-slate-50 hover:bg-slate-100'
              }`}
            >
              <div className="flex items-center gap-2">
                {isHcaExpanded
                  ? <ChevronDown className="h-3 w-3 text-slate-500" />
                  : <ChevronRight className="h-3 w-3 text-slate-500" />
                }
                <span className={`font-medium text-xs ${isPropertyHcaFlag ? 'text-teal-800' : 'text-slate-700'}`}>
                  {formatHcaName(hca)}
                  {isPropertyHcaFlag && <span className="ml-1 text-teal-600">(your property)</span>}
                </span>
                <Badge variant="secondary" className="text-[10px]">{hcaProvisions.length}</Badge>
              </div>
            </button>

            {isHcaExpanded && (
              <div className="p-2 bg-white space-y-2">
                {Array.from(groupByHeritageType(hcaProvisions)).map(([heritageType, typeProvisions]) => {
                  const typeKey = `${hcaKey}-${heritageType}`;
                  const isTypeExpanded = expandedHeritageTypes.has(typeKey);
                  const typeConfig = HERITAGE_TYPE_CONFIG[heritageType] || HERITAGE_TYPE_CONFIG.descriptive;
                  const isShowingAll = showAllHeritageTypes.has(typeKey);
                  const selectedElement = elementFilters[typeKey];
                  const elementTotals = getElementTotals(typeProvisions);
                  const filteredProvisions = filterByElement(typeProvisions, selectedElement);
                  const shouldSplit = selectedElement && selectedElement !== '_general' && elementTotals;
                  const splitResults = shouldSplit ? splitByExclusivity(typeProvisions, selectedElement) : null;
                  const displayLimit = heritageType === 'control' ? 10 : 8;

                  return (
                    <div key={typeKey} className={`border rounded-lg overflow-hidden ${typeConfig.border}`}>
                      <button
                        onClick={() => toggleHeritageType(typeKey)}
                        className={`w-full flex items-center justify-between px-3 py-1.5 ${typeConfig.bg} hover:opacity-90 transition-opacity`}
                      >
                        <div className="flex items-center gap-2">
                          {isTypeExpanded
                            ? <ChevronDown className="h-3 w-3 text-slate-500" />
                            : <ChevronRight className="h-3 w-3 text-slate-500" />
                          }
                          <span className={`font-medium text-xs ${typeConfig.accent}`}>{typeConfig.label}</span>
                          <Badge variant="secondary" className="text-[10px]">{typeProvisions.length}</Badge>
                        </div>
                      </button>

                      {isTypeExpanded && (
                        <div className={`p-2 ${typeConfig.bg}`}>
                          {/* Element filter pills */}
                          {elementTotals.totals.size > 0 && (
                            <div className="mb-2 p-2 bg-white/70 rounded-md border border-gray-200">
                              <div className="flex flex-wrap gap-1">
                                <button
                                  onClick={() => setElementFilter(typeKey, null)}
                                  className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                                    !selectedElement ? 'bg-teal-600 text-white' : 'bg-white text-teal-700 border border-teal-300 hover:bg-teal-50'
                                  }`}
                                >
                                  All ({typeProvisions.length})
                                </button>
                                {Array.from(elementTotals.totals).map(([elem, count]) => (
                                  <button
                                    key={elem}
                                    onClick={() => setElementFilter(typeKey, selectedElement === elem ? null : elem)}
                                    className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                                      selectedElement === elem ? 'bg-teal-600 text-white' : 'bg-white text-teal-700 border border-teal-300 hover:bg-teal-50'
                                    }`}
                                  >
                                    {ELEMENT_LABELS[elem] || elem} ({count})
                                  </button>
                                ))}
                                {elementTotals.generalCount > 0 && (
                                  <button
                                    onClick={() => setElementFilter(typeKey, selectedElement === '_general' ? null : '_general')}
                                    className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                                      selectedElement === '_general' ? 'bg-gray-500 text-white' : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
                                    }`}
                                  >
                                    General ({elementTotals.generalCount})
                                  </button>
                                )}
                              </div>
                            </div>
                          )}

                          {splitResults ? (
                            <>
                              {splitResults.onlyThis.length > 0 && (
                                <div className="mb-3">
                                  <div className="bg-blue-100 border border-blue-300 rounded-md px-3 py-1.5 mb-2">
                                    <p className="text-sm font-semibold text-blue-800">
                                      {ELEMENT_LABELS[selectedElement!] || selectedElement} only ({splitResults.onlyThis.length})
                                    </p>
                                  </div>
                                  <PageGroupedProvisions
                                    provisionTheme="green"
                                    provisions={splitResults.onlyThis}
                                    expandedProvisions={expandedProvisions}
                                    onToggleProvision={toggleProvision}
                                    onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                    theme={{
                                      zebraStripeBg: 'bg-green-50/50',
                                      zebraStripeAltBg: 'bg-white',
                                      borderColorClass: 'border-green-200',
                                      textClampLines: 2,
                                      expandThreshold: 200,
                                    }}
                                    maxProvisions={isShowingAll ? undefined : 10}
                                    zone={zone}
                                    heritage={heritage}
                                    hcaName={hcaName}
                                    precinctName={precinctId}
                                  />
                                  {splitResults.onlyThis.length > 10 && (
                                    <button
                                      onClick={() => toggleShowAllHeritageType(typeKey)}
                                      className="w-full text-xs text-center py-1 text-green-600 hover:underline"
                                    >
                                      {isShowingAll ? '↑ Show fewer' : `Show all ${splitResults.onlyThis.length}`}
                                    </button>
                                  )}
                                </div>
                              )}
                              {splitResults.plusOthers.length > 0 && (
                                <div>
                                  <div className="bg-amber-100 border border-amber-300 rounded-md px-3 py-1.5 mb-2">
                                    <p className="text-sm font-semibold text-amber-800">
                                      {ELEMENT_LABELS[selectedElement!] || selectedElement} + other elements ({splitResults.plusOthers.length})
                                    </p>
                                  </div>
                                  <PageGroupedProvisions
                                    provisionTheme="green"
                                    provisions={splitResults.plusOthers}
                                    expandedProvisions={expandedProvisions}
                                    onToggleProvision={toggleProvision}
                                    onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                    theme={{
                                      zebraStripeBg: 'bg-amber-50/50',
                                      zebraStripeAltBg: 'bg-white',
                                      borderColorClass: 'border-amber-200',
                                      textClampLines: 2,
                                      expandThreshold: 200,
                                    }}
                                    maxProvisions={isShowingAll ? undefined : 5}
                                    zone={zone}
                                    heritage={heritage}
                                    hcaName={hcaName}
                                    precinctName={precinctId}
                                  />
                                  {splitResults.plusOthers.length > 5 && (
                                    <button
                                      onClick={() => toggleShowAllHeritageType(typeKey)}
                                      className="w-full text-xs text-center py-1 text-amber-600 hover:underline"
                                    >
                                      {isShowingAll ? '↑ Show fewer' : `Show all ${splitResults.plusOthers.length}`}
                                    </button>
                                  )}
                                </div>
                              )}
                            </>
                          ) : (
                            <>
                              <PageGroupedProvisions
                                provisionTheme="green"
                                provisions={filteredProvisions}
                                expandedProvisions={expandedProvisions}
                                onToggleProvision={toggleProvision}
                                onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                theme={{
                                  zebraStripeBg: typeConfig.bg,
                                  zebraStripeAltBg: 'bg-white',
                                  borderColorClass: typeConfig.border,
                                  textClampLines: 2,
                                  expandThreshold: 200,
                                }}
                                maxProvisions={isShowingAll ? undefined : displayLimit}
                                zone={zone}
                                heritage={heritage}
                                hcaName={hcaName}
                                precinctName={precinctId}
                              />
                              {filteredProvisions.length > displayLimit && (
                                <button
                                  onClick={() => toggleShowAllHeritageType(typeKey)}
                                  className={`w-full text-xs text-center py-2 rounded ${
                                    isShowingAll ? 'text-gray-500 hover:text-gray-700' : `${typeConfig.accent} font-medium hover:underline`
                                  }`}
                                >
                                  {isShowingAll
                                    ? `↑ Show fewer (${displayLimit})`
                                    : `↓ Show all ${filteredProvisions.length} ${typeConfig.label.toLowerCase()}`
                                  }
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
