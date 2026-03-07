'use client';

import { ChevronDown, Search } from 'lucide-react';
import { PageGroupedProvisions } from './PageGroupedProvisions';
import type { DaResponse } from '@/hooks/useDASession';

interface DcpProvisionListProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  displayProvisions: any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  triageExcludedProvisions: any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  filteredProvisions: any[];
  hasMarkers: boolean;
  showTriageExcluded: boolean;
  onToggleTriageExcluded: () => void;
  councilPdfUrl?: string;
  formerCouncil: string;
  zone?: string;
  heritage?: boolean;
  hcaName?: string;
  precinctId?: string;
  isDaMode?: boolean;
  sessionToken: string | null;
  daResponses?: Map<number, DaResponse>;
  excludableTopics: Set<string>;
  onViewPdf: (url: string, page: number) => void;
  debouncedSearch: string;
  // Empty state
  provisionView: 'task' | 'structure';
  layerFilter: string | null;
  onClearLayer: () => void;
  topicFilters: string[];
  onClearTopics: () => void;
  searchScope: 'all' | 'filtered';
  onSearchScopeChange: (v: 'all' | 'filtered') => void;
  onSearchQueryChange: (v: string) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  baseProvisions: any[];
}

export function DcpProvisionList({
  displayProvisions, triageExcludedProvisions, filteredProvisions,
  hasMarkers, showTriageExcluded, onToggleTriageExcluded,
  councilPdfUrl, formerCouncil, zone, heritage, hcaName, precinctId,
  isDaMode, sessionToken, daResponses, excludableTopics, onViewPdf,
  debouncedSearch, provisionView, layerFilter, onClearLayer,
  topicFilters, onClearTopics, searchScope, onSearchScopeChange,
  onSearchQueryChange, baseProvisions,
}: DcpProvisionListProps) {
  return (
    <div className="p-4">
      {/* Marker key */}
      {filteredProvisions.length > 0 && hasMarkers && (
        <div className="mb-3 flex items-center gap-3 text-xs text-gray-500">
          <span className="italic">Some provisions include DCP reference codes:</span>
          <span className="flex items-center gap-1">
            <span className="px-1.5 py-0.5 bg-white border border-gray-300 rounded font-mono text-gray-700">C</span>
            <span>= Control</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="px-1.5 py-0.5 bg-white border border-gray-300 rounded font-mono text-gray-700">O</span>
            <span>= Objective</span>
          </span>
        </div>
      )}

      {(displayProvisions.length > 0 || triageExcludedProvisions.length > 0) && (
        <>
          {displayProvisions.length > 0 && (
            <PageGroupedProvisions provisionTheme="green"
              provisions={displayProvisions}
              formerCouncil={formerCouncil}
              councilKey={formerCouncil?.toLowerCase()}
              councilPdfUrl={councilPdfUrl}
              showLayerBadges={true}
              maxProvisions={100}
              onViewPdf={onViewPdf}
              highlightQuery={debouncedSearch}
              zone={zone}
              heritage={heritage}
              hcaName={hcaName}
              precinctName={precinctId}
              isDaMode={isDaMode}
              sessionToken={sessionToken}
              daResponses={daResponses}
              excludableTopics={excludableTopics}
            />
          )}
          {triageExcludedProvisions.length > 0 && (
            <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={onToggleTriageExcluded}
                className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-sm text-gray-500"
              >
                <span>{triageExcludedProvisions.length} provision{triageExcludedProvisions.length !== 1 ? 's' : ''} removed by triage</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${showTriageExcluded ? 'rotate-180' : ''}`} />
              </button>
              {showTriageExcluded && (
                <div className="border-t border-gray-200">
                  <PageGroupedProvisions provisionTheme="green"
                    provisions={triageExcludedProvisions}
                    formerCouncil={formerCouncil}
                    councilKey={formerCouncil?.toLowerCase()}
                    councilPdfUrl={councilPdfUrl}
                    showLayerBadges={true}
                    maxProvisions={100}
                    onViewPdf={onViewPdf}
                    highlightQuery={debouncedSearch}
                    zone={zone}
                    heritage={heritage}
                    hcaName={hcaName}
                    precinctName={precinctId}
                    isDaMode={isDaMode}
                    sessionToken={sessionToken}
                    daResponses={daResponses}
                    excludableTopics={excludableTopics}
                  />
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {filteredProvisions.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <Search className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          {debouncedSearch ? (
            <>
              <p className="font-medium mb-2">No provisions match "{debouncedSearch}"</p>
              {searchScope === 'filtered' && (
                <button onClick={() => onSearchScopeChange('all')} className="text-teal-600 hover:underline mb-2 block mx-auto">
                  Try searching all {baseProvisions.length} provisions instead?
                </button>
              )}
              <div className="text-sm mt-4">
                <p className="mb-2">Try searching for:</p>
                <div className="flex gap-2 justify-center flex-wrap">
                  {['setback', 'FSR', 'heritage', 'parking', 'height'].map(term => (
                    <button key={term} onClick={() => onSearchQueryChange(term)} className="px-2 py-1 bg-gray-100 rounded hover:bg-gray-200 text-xs">
                      {term}
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <>
              <p>No provisions {provisionView === 'structure' ? 'in this section' : 'match your filters'}</p>
              {(topicFilters.length > 0 || layerFilter) && (
                <div className="mt-2 space-x-2">
                  {topicFilters.length > 0 && (
                    <button onClick={onClearTopics} className="text-teal-600 text-sm hover:underline">Clear topics</button>
                  )}
                  {layerFilter && (
                    <button onClick={onClearLayer} className="text-teal-600 text-sm hover:underline">Clear layer filter</button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
