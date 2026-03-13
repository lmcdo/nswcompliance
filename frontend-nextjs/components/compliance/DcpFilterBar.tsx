'use client';

import { useState, useEffect } from 'react';
import { Search, X, Ruler, Download } from 'lucide-react';
import { SearchAutocomplete } from '@/components/ui/SearchAutocomplete';
import { getSearchSuggestions } from '@/lib/search-utils';
import { normalizeTopicKey } from '@/lib/see/intake';

interface DcpFilterBarProps {
  // Search
  searchQuery: string;
  onSearchQueryChange: (v: string) => void;
  debouncedSearch: string;
  showAutocomplete: boolean;
  onShowAutocompleteChange: (v: boolean) => void;
  searchScope: 'all' | 'filtered';
  onSearchScopeChange: (v: 'all' | 'filtered') => void;
  // Provision counts
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  baseProvisions: any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  layerFilteredProvisions: any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  filteredProvisions: any[];
  // Topic chips
  availableTopics: string[];
  topicFilters: string[];
  onToggleTopic: (key: string) => void;
  onClearTopics: () => void;
  topicPriorityStats: Record<string, { critical: number; total: number }>;
  excludableTopics: Set<string>;
  // Refinements
  refinements: { mandatoryOnly: boolean; withMeasurements: boolean; objectivesOnly: boolean };
  onToggleRefinement: (key: 'mandatoryOnly' | 'withMeasurements' | 'objectivesOnly') => void;
  // Layer filter
  layerFilter: string | null;
  onLayerFilterChange: (layer: string | null) => void;
  layerCounts: { generic: number; use_specific: number; condition: number; precinct: number };
  /** Precomputed layer label map for the current council (COUNCIL_LAYER_LABELS lookup). */
  layerLabels: Record<string, string>;
  zone?: string;
  heritage?: boolean;
  hcaName?: string;
  precinctName?: string;
  formerCouncil: string;
  generalHeritageCount: number;
  hcaSpecificCount: number;
  totalHeritageCount: number;
  // Export modal
  showExportModal: boolean;
  onShowExportModal: (v: boolean) => void;
  onExportPdf: () => void;
  selectedPart?: string | null;
  provisionView: 'task' | 'structure';
  heritageTypeFilter?: string | null;
  onHeritageTypeFilterChange?: (v: string | null) => void;
  // DA mode context
  isDaMode?: boolean;
}

const MAX_VISIBLE_CHIPS = 8;

export function DcpFilterBar({
  searchQuery, onSearchQueryChange, debouncedSearch, showAutocomplete, onShowAutocompleteChange,
  searchScope, onSearchScopeChange, baseProvisions, layerFilteredProvisions, filteredProvisions,
  availableTopics, topicFilters, onToggleTopic, onClearTopics, topicPriorityStats, excludableTopics,
  refinements, onToggleRefinement,
  layerFilter, onLayerFilterChange, layerCounts, layerLabels,
  zone, heritage, hcaName, precinctName, formerCouncil,
  generalHeritageCount, hcaSpecificCount, totalHeritageCount,
  showExportModal, onShowExportModal, onExportPdf, selectedPart, provisionView,
  heritageTypeFilter, onHeritageTypeFilterChange, isDaMode,
}: DcpFilterBarProps) {
  const [showAllChips, setShowAllChips] = useState(false);

  // Collapse back to max-visible whenever the topic list itself changes
  // (e.g. user switches layer filter, changing which topics are available)
  useEffect(() => { setShowAllChips(false); }, [availableTopics.length]);

  return (
    <>
      {/* Search box */}
      <div className="mt-3 relative">
        {/* Search scope toggle — only when filters are active */}
        {(layerFilter || refinements.mandatoryOnly || refinements.withMeasurements || refinements.objectivesOnly || heritageTypeFilter) && (
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
            <span>Search in:</span>
            <button
              onClick={() => onSearchScopeChange('all')}
              className={`px-2 py-1 rounded-md transition-colors ${
                searchScope === 'all' ? 'bg-teal-100 text-teal-700 font-medium' : 'hover:bg-gray-100'
              }`}
            >
              All provisions ({baseProvisions.length})
            </button>
            <button
              onClick={() => onSearchScopeChange('filtered')}
              className={`px-2 py-1 rounded-md transition-colors ${
                searchScope === 'filtered' ? 'bg-teal-100 text-teal-700 font-medium' : 'hover:bg-gray-100'
              }`}
            >
              Filtered results only ({layerFilteredProvisions.length})
            </button>
          </div>
        )}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 z-10" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => { onSearchQueryChange(e.target.value); onShowAutocompleteChange(true); }}
            onFocus={() => onShowAutocompleteChange(true)}
            onBlur={() => setTimeout(() => onShowAutocompleteChange(false), 200)}
            placeholder="Search provisions... (try: setback, FSR, heritage)"
            className="w-full pl-10 pr-10 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          />
          {searchQuery && (
            <button
              onClick={() => { onSearchQueryChange(''); onShowAutocompleteChange(false); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 z-10"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          {showAutocomplete && (
            <SearchAutocomplete
              query={searchQuery}
              suggestions={getSearchSuggestions(searchQuery)}
              onSelect={(term) => { onSearchQueryChange(term); onShowAutocompleteChange(false); }}
              onClose={() => onShowAutocompleteChange(false)}
            />
          )}
        </div>
        {debouncedSearch && (
          <div className="mt-1 text-xs text-gray-500">
            {filteredProvisions.length} provision{filteredProvisions.length !== 1 ? 's' : ''} match your search
          </div>
        )}
      </div>

      {/* Export PDF Modal */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => onShowExportModal(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-1">DCP Provisions Schedule</h3>
              <p className="text-xs text-gray-500 mb-4">Reference document — not a compliance assessment.</p>
              <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mb-6">
                <div className="text-sm font-medium text-teal-900 mb-2">
                  Exporting {filteredProvisions.length} provision{filteredProvisions.length !== 1 ? 's' : ''}
                </div>
                <div className="text-xs text-teal-700 space-y-1">
                  {(() => {
                    const items: string[] = [];
                    const firstProv = filteredProvisions[0];
                    const dcpName = formerCouncil === 'Ashfield' ? 'Ashfield DCP 2016'
                      : formerCouncil === 'Leichhardt' ? 'Leichhardt DCP 2013'
                      : formerCouncil === 'Marrickville' ? 'Marrickville DCP 2011'
                      : 'DCP';
                    if (provisionView === 'structure' && selectedPart && firstProv?.v2_dcp_part) {
                      items.push(`${dcpName} • ${firstProv.v2_dcp_part}`);
                    } else {
                      items.push(dcpName);
                    }
                    if (layerFilter) items.push(`Layer: ${layerLabels[layerFilter] || layerFilter}`);
                    else items.push('Layer: All');
                    if (debouncedSearch) items.push(`Search: "${debouncedSearch}"`);
                    return items.map((item, idx) => <div key={idx}>• {item}</div>);
                  })()}
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={() => onShowExportModal(false)} className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">Cancel</button>
                <button
                  onClick={() => { onShowExportModal(false); onExportPdf(); }}
                  disabled={filteredProvisions.length === 0}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  <Download className="h-4 w-4" />
                  Generate PDF
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Refinement & filter controls */}
      <div className="mt-3 space-y-2">
        {/* Refinement filters */}
        {(layerFilter || debouncedSearch) && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500 font-medium">Refine:</span>
            <button
              onClick={() => onToggleRefinement('mandatoryOnly')}
              className={`px-2 py-1 text-xs rounded-md transition-colors flex items-center gap-1 ${
                refinements.mandatoryOnly ? 'bg-red-100 text-red-800 border border-red-300' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {refinements.mandatoryOnly && <X className="w-3 h-3" />}
              Mandatory only
            </button>
            <button
              onClick={() => onToggleRefinement('withMeasurements')}
              className={`px-2 py-1 text-xs rounded-md transition-colors flex items-center gap-1 ${
                refinements.withMeasurements ? 'bg-blue-100 text-blue-800 border border-blue-300' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {refinements.withMeasurements ? <X className="w-3 h-3" /> : <Ruler className="w-3 h-3" />}
              With measurements
            </button>
            <button
              onClick={() => onToggleRefinement('objectivesOnly')}
              className={`px-2 py-1 text-xs rounded-md transition-colors flex items-center gap-1 ${
                refinements.objectivesOnly ? 'bg-purple-100 text-purple-800 border border-purple-300' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {refinements.objectivesOnly && <X className="w-3 h-3" />}
              Objectives only
            </button>
          </div>
        )}

        {/* Heritage type filter — X10: only shown when on a heritage property */}
        {heritage && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500 font-medium">Heritage type:</span>
            {(['control', 'character', 'descriptive'] as const).map(ht => (
              <button
                key={ht}
                onClick={() => onHeritageTypeFilterChange?.(heritageTypeFilter === ht ? null : ht)}
                className={`px-2 py-1 text-xs rounded-md transition-colors flex items-center gap-1 ${
                  heritageTypeFilter === ht
                    ? 'bg-amber-100 text-amber-800 border border-amber-300'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {heritageTypeFilter === ht && <X className="w-3 h-3" />}
                {ht.charAt(0).toUpperCase() + ht.slice(1)}
              </button>
            ))}
          </div>
        )}

        {/* Status line */}
        {(layerFilter || refinements.mandatoryOnly || refinements.withMeasurements) && (
          <div className="text-xs text-gray-500 pt-1 border-t border-gray-100 mt-0.5">
            {(() => {
              const count = filteredProvisions.length;
              let message = `Showing ${count} provision${count !== 1 ? 's' : ''}`;
              const layerLabel = layerFilter ? layerLabels[layerFilter] : null;
              if (layerLabel) message += ` from ${layerLabel}`;
              const refinementParts: string[] = [];
              if (refinements.mandatoryOnly) refinementParts.push('mandatory only');
              if (refinements.withMeasurements) refinementParts.push('with measurements');
              if (refinements.objectivesOnly) refinementParts.push('objectives only');
              if (heritageTypeFilter) refinementParts.push(`${heritageTypeFilter} provisions`);
              if (refinementParts.length > 0) message += ` (${refinementParts.join(', ')})`;
              return message;
            })()}
          </div>
        )}
      </div>

    </>
  );
}
