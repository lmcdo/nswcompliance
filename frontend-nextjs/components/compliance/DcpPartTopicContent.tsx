'use client';

// Renders the provision list for a single non-heritage DCP part accordion.
// Handles element filtering (Building Form) and split-by-exclusivity display.

import { FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { PageGroupedProvisions } from './PageGroupedProvisions';
import { FormattedProvisionText } from './FormattedProvisionText';
import { stripSectionHeader } from '@/lib/provision-text-formatter';
import {
  Provision,
  ELEMENT_LABELS,
  getElementTotals,
  splitByExclusivity,
  filterByElement,
  getLayerLabel,
  getLayerColor,
} from '@/lib/provision-grouping';

interface DcpPartTopicContentProps {
  partProvisions: Provision[];
  topic: string;
  partFilterKey: string;
  expandedProvisions: Set<number>;
  elementFilters: Record<string, string>;
  showPdfButtonIds: Set<number>;
  council?: string;
  zone?: string;
  heritage?: boolean;
  hcaName?: string;
  precinctId?: string;
  toggleProvision: (id: number) => void;
  setElementFilter: (key: string, element: string | null) => void;
  setViewingPdfImage: (v: { url: string; page: number } | null) => void;
}

export function DcpPartTopicContent({
  partProvisions, topic, partFilterKey,
  expandedProvisions, elementFilters, showPdfButtonIds,
  council, zone, heritage, hcaName, precinctId,
  toggleProvision, setElementFilter, setViewingPdfImage,
}: DcpPartTopicContentProps) {

  const selectedPartElement = elementFilters[partFilterKey];
  const isBuildingForm = topic.toLowerCase() === 'building form';
  const partElementTotals = isBuildingForm ? getElementTotals(partProvisions) : null;
  const partFilteredProvisions = filterByElement(partProvisions, selectedPartElement);
  const partShouldSplit = selectedPartElement && selectedPartElement !== '_general' && partElementTotals;
  const partSplitResults = partShouldSplit ? splitByExclusivity(partProvisions, selectedPartElement) : null;

  const renderProvision = (provision: Provision, idx: number, showTags = false) => {
    const layer = provision.layer || provision.v2_dcp_layer;
    const layerBorderColor =
      layer === 'generic' ? 'border-l-slate-400' :
      layer === 'use_specific' ? 'border-l-sky-400' :
      layer === 'condition' ? 'border-l-amber-400' :
      layer === 'precinct' ? 'border-l-purple-400' : 'border-l-gray-300';
    const zebraStripe = idx % 2 === 1 ? 'bg-green-50' : 'bg-white';
    const displayPage = provision.pdf_printed_page || provision.pdf_page || 1;
    const sectionInfo = provision.v2_dcp_part || '';

    return (
      <div
        key={provision.id}
        className={`${zebraStripe} border border-gray-200 rounded-lg overflow-hidden transition-all hover:shadow-md ${layerBorderColor} border-l-4`}
      >
        <div className="flex items-center justify-between px-4 py-2 bg-gray-50/50 border-b border-gray-100">
          <div className="flex items-center gap-2 flex-wrap">
            {provision.toc_section_number && (
              <span className="font-mono text-sm font-semibold text-slate-700">
                {provision.toc_section_number}
              </span>
            )}
            {provision.v2_marker && (
              <span className="font-mono text-sm font-semibold text-slate-700">
                {provision.v2_marker}
              </span>
            )}
            <Badge className={`text-[10px] ${getLayerColor(layer)}`}>
              {getLayerLabel(layer)}
            </Badge>
            {showTags && provision.v2_heritage_element && provision.v2_heritage_element.length > 1 && (
              <span className="text-[9px] text-gray-500">
                [{provision.v2_heritage_element.map(e => ELEMENT_LABELS[e] || e).join(', ')}]
              </span>
            )}
          </div>
          {provision.pdf_page_image_url && showPdfButtonIds.has(provision.id) && (
            <button
              className="p-1 rounded hover:bg-green-100 transition-colors flex-shrink-0"
              title={`${sectionInfo ? sectionInfo + ' - ' : ''}Page ${displayPage}`}
              onClick={(e) => {
                e.stopPropagation();
                setViewingPdfImage({ url: provision.pdf_page_image_url!, page: displayPage });
              }}
            >
              <FileText className="w-4 h-4 text-green-600 hover:text-green-800" />
            </button>
          )}
        </div>
        <div className="px-4 py-3">
          <div
            className={`text-sm text-gray-700 leading-relaxed cursor-pointer ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-3'}`}
            onClick={() => toggleProvision(provision.id)}
          >
            <FormattedProvisionText
              text={stripSectionHeader(provision.provision_text, undefined)}
              compact
              councilKey={council}
            />
          </div>
          {provision.provision_text.length > 300 && (
            <button
              className="text-xs text-slate-500 hover:text-slate-700 mt-2 font-medium"
              onClick={() => toggleProvision(provision.id)}
            >
              {expandedProvisions.has(provision.id) ? '↑ Show less' : '↓ Show more'}
            </button>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Element filter pills for Building Form */}
      {isBuildingForm && partElementTotals && partElementTotals.totals.size > 0 && (
        <div className="mb-3 p-2 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex flex-wrap gap-1">
            <button
              onClick={() => setElementFilter(partFilterKey, null)}
              className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                !selectedPartElement
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-blue-700 border border-blue-300 hover:bg-blue-100'
              }`}
            >
              All ({partProvisions.length})
            </button>
            {Array.from(partElementTotals.totals).map(([elem, count]) => (
              <button
                key={elem}
                onClick={() => setElementFilter(partFilterKey, selectedPartElement === elem ? null : elem)}
                className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                  selectedPartElement === elem
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-blue-700 border border-blue-300 hover:bg-blue-100'
                }`}
              >
                {ELEMENT_LABELS[elem] || elem} ({count})
              </button>
            ))}
            {partElementTotals.generalCount > 0 && (
              <button
                onClick={() => setElementFilter(partFilterKey, selectedPartElement === '_general' ? null : '_general')}
                className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                  selectedPartElement === '_general'
                    ? 'bg-gray-500 text-white'
                    : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-100'
                }`}
              >
                General ({partElementTotals.generalCount})
              </button>
            )}
          </div>
        </div>
      )}

      {/* Split results if element selected */}
      {partSplitResults ? (
        <>
          {partSplitResults.onlyThis.length > 0 && (
            <div className="mb-4">
              <div className="bg-blue-100 border border-blue-300 rounded-md px-3 py-1.5 mb-2">
                <p className="text-sm font-semibold text-blue-800">
                  {ELEMENT_LABELS[selectedPartElement!] || selectedPartElement} only ({partSplitResults.onlyThis.length})
                </p>
              </div>
              <PageGroupedProvisions
                provisionTheme="green"
                provisions={partSplitResults.onlyThis}
                expandedProvisions={expandedProvisions}
                onToggleProvision={toggleProvision}
                onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                maxProvisions={20}
                zone={zone}
                heritage={heritage}
                hcaName={hcaName}
                precinctName={precinctId}
              />
            </div>
          )}
          {partSplitResults.plusOthers.length > 0 && (
            <div>
              <div className="bg-amber-100 border border-amber-300 rounded-md px-3 py-1.5 mb-2">
                <p className="text-sm font-semibold text-amber-800">
                  {ELEMENT_LABELS[selectedPartElement!] || selectedPartElement} + other elements ({partSplitResults.plusOthers.length})
                </p>
              </div>
              <PageGroupedProvisions
                provisionTheme="green"
                provisions={partSplitResults.plusOthers}
                expandedProvisions={expandedProvisions}
                onToggleProvision={toggleProvision}
                onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                maxProvisions={10}
                zone={zone}
                heritage={heritage}
                hcaName={hcaName}
                precinctName={precinctId}
              />
            </div>
          )}
        </>
      ) : (
        <PageGroupedProvisions
          provisionTheme="green"
          provisions={partFilteredProvisions}
          expandedProvisions={expandedProvisions}
          onToggleProvision={toggleProvision}
          onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
          maxProvisions={20}
          zone={zone}
          heritage={heritage}
          hcaName={hcaName}
          precinctName={precinctId}
        />
      )}
    </>
  );
}
