'use client';

import { ChevronDown, Search } from 'lucide-react';
import { normalizeTopicKey } from '@/lib/see/intake';
import { PageGroupedProvisions } from './PageGroupedProvisions';
import type { DaResponse, SectionResponse } from '@/hooks/useDASession';

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
  chapterPdfUrls?: Record<string, string>;
  formerCouncil: string;
  zone?: string;
  heritage?: boolean;
  hcaName?: string;
  precinctId?: string;
  isDaMode?: boolean;
  sessionToken: string | null;
  daResponses?: Map<number, DaResponse>;
  sectionResponses?: Map<string, SectionResponse>;
  excludableTopics: Set<string>;
  onResponseSaved?: (provisionId: number, response: DaResponse) => void;
  onSectionResponseSaved?: (sectionKey: string, response: SectionResponse) => void;
  canonicalSectionTitles?: Map<string, string | null>;
  /** Sections with only objectives/descriptives — no assessable controls, shown separately */
  suppressedOnlySections?: Map<string, string | null>;
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
  // DA mode suppressed provisions toggle (audit/transparency)
  showSuppressedInDA?: boolean;
  onToggleSuppressedInDA?: () => void;
  /** DCP numeric check values from NumericChecker inputs. */
  numericCheckValues?: import('./NumericChecker').NumericCheckValues;
  /** LEP/DCP reference values for inline chips. */
  lepReference?: {
    height?: string | null;
    fsr?: string | null;
  } | null;
}

export function DcpProvisionList({
  displayProvisions, triageExcludedProvisions, filteredProvisions,
  hasMarkers, showTriageExcluded, onToggleTriageExcluded,
  chapterPdfUrls, formerCouncil, zone, heritage, hcaName, precinctId,
  isDaMode, sessionToken, daResponses, sectionResponses, excludableTopics, onResponseSaved, onSectionResponseSaved, canonicalSectionTitles, suppressedOnlySections, onViewPdf,
  debouncedSearch, provisionView, layerFilter, onClearLayer,
  topicFilters, onClearTopics, searchScope, onSearchScopeChange,
  onSearchQueryChange, baseProvisions, showSuppressedInDA, onToggleSuppressedInDA, lepReference, numericCheckValues,
}: DcpProvisionListProps) {
  // In non-DA mode, excluded provisions are greyed out inline rather than split out.
  // Show a count so the planner knows how many are not applicable to this site.
  const nonApplicableCount = !isDaMode && excludableTopics.size > 0
    ? displayProvisions.filter(p => {
        const cat = p.v2_structural_category;
        return cat && excludableTopics.has(cat);
      }).length
    : 0;

  // DA mode: count suppressed provisions (objectives, procedural, descriptive) for audit trail
  const suppressedProvisions = isDaMode && baseProvisions
    ? baseProvisions.filter(p =>
        p.v2_provision_type === 'objective' ||
        p.v2_provision_type === 'procedural' ||
        p.v2_provision_type === 'descriptive' ||
        p.v2_heritage_type === 'descriptive'
      )
    : [];

  return (
    <div className="p-4">
      {/* Non-DA mode: note how many provisions are greyed out as not applicable */}
      {nonApplicableCount > 0 && (
        <div className="mb-3 flex items-center gap-2 text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
          <span className="inline-block w-3 h-3 rounded-sm bg-gray-300 opacity-60 shrink-0" />
          <span>
            {nonApplicableCount} provision{nonApplicableCount !== 1 ? 's' : ''} greyed out — not applicable to this site based on SEPP/LEP data
          </span>
        </div>
      )}

      {/* HCA filter transparency — provisions are scoped to this site's HCA */}
      {heritage && hcaName && (
        <div className="mb-3 flex items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <span className="shrink-0">Heritage:</span>
          <span>Showing provisions for <strong>{hcaName}</strong> only — other precincts are not shown</span>
        </div>
      )}

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
          {/* Provision count — always show so user knows scope */}
          {!isDaMode && displayProvisions.length > 0 && (
            <p className="text-xs text-gray-500 mb-3">
              Showing {Math.min(30, displayProvisions.length)} of {displayProvisions.length} provision{displayProvisions.length !== 1 ? 's' : ''}
              {displayProvisions.length > 30 && ` — use "Show more" below to see all`}
            </p>
          )}
          {displayProvisions.length > 0 && (
            <>
              <PageGroupedProvisions provisionTheme="green"
                provisions={displayProvisions}
                formerCouncil={formerCouncil}
                councilKey={formerCouncil?.toLowerCase()}
                chapterPdfUrls={chapterPdfUrls}
                showLayerBadges={true}
                onViewPdf={onViewPdf}
                highlightQuery={debouncedSearch}
                zone={zone}
                heritage={heritage}
                hcaName={hcaName}
                precinctName={precinctId}
                isDaMode={isDaMode}
                sectionGrouped={isDaMode}
                maxProvisions={isDaMode ? undefined : 30}
                sessionToken={sessionToken}
                daResponses={daResponses}
                sectionResponses={sectionResponses}
                excludableTopics={excludableTopics}
                onResponseSaved={onResponseSaved}
                onSectionResponseSaved={onSectionResponseSaved}
                canonicalSectionTitles={canonicalSectionTitles}
                suppressedSections={suppressedOnlySections}
                hideShowMoreButton={isDaMode}
                lepReference={lepReference}
                numericCheckValues={numericCheckValues}
              />
              {/* Guidance items toggle */}
              {suppressedProvisions.length > 0 && (
                <div className="mt-3 border-t pt-3">
                  <button
                    onClick={onToggleSuppressedInDA}
                    className="flex flex-col items-center gap-1 px-3 py-2.5 rounded border border-amber-200 hover:bg-amber-50 transition-colors w-full"
                  >
                    <span className="text-sm font-medium text-amber-700">
                      View {suppressedProvisions.length} guidance item{suppressedProvisions.length !== 1 ? 's' : ''}
                    </span>
                    <span className="text-xs text-amber-700/70">objectives &amp; descriptives</span>
                  </button>
                </div>
              )}
            </>
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
                    chapterPdfUrls={chapterPdfUrls}
                    showLayerBadges={true}
                    maxProvisions={20}
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
                    onResponseSaved={onResponseSaved}
                    hideShowMoreButton={true}
                  />
                </div>
              )}
            </div>
          )}

          {/* DA mode: suppressed provisions (objectives + heritage descriptives) — audit trail */}
          {isDaMode && suppressedProvisions.length > 0 && (
            <div className="mt-4 border border-amber-200 rounded-lg overflow-hidden bg-amber-50">
              <button
                onClick={onToggleSuppressedInDA}
                className="w-full flex items-center justify-between px-4 py-2.5 bg-amber-100 hover:bg-amber-200 transition-colors text-sm text-amber-700 font-medium"
              >
                <span>{suppressedProvisions.length} non-enforceable items not assessed — objectives &amp; heritage descriptions</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${showSuppressedInDA ? 'rotate-180' : ''}`} />
              </button>
              {showSuppressedInDA && (
                <div className="border-t border-amber-200 bg-white/50 p-3">
                  <p className="text-xs text-amber-700 mb-3 italic">
                    Not included in the assessment scope: <strong>objectives</strong> state planning intent but impose no specific requirement; <strong>heritage descriptions</strong> describe character and significance but are not enforceable controls.
                    Neither type requires a Complies/Varies/N/A response. Shown here for audit transparency.
                  </p>
                  <PageGroupedProvisions provisionTheme={"gray" as any}
                    provisions={suppressedProvisions}
                    formerCouncil={formerCouncil}
                    councilKey={formerCouncil?.toLowerCase()}
                    chapterPdfUrls={chapterPdfUrls}
                    showLayerBadges={true}
                    maxProvisions={undefined}
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
                    onResponseSaved={onResponseSaved}
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
