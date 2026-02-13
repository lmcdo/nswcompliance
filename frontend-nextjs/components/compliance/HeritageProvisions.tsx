'use client';

/**
 * Heritage Provisions Sub-Component (DQ-11)
 * Groups Ashfield heritage provisions by type: control, character, descriptive
 * With PDF page grouping and View PDF buttons matching main component pattern
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, Info } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { FormattedProvisionText } from './FormattedProvisionText';
import { stripSectionHeader } from '@/lib/provision-text-formatter';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface Provision {
  id: number;
  provision_text: string;
  v2_heritage_type?: 'control' | 'character' | 'descriptive';
  v2_heritage_element?: string[];
  v2_heritage_hca?: string;
  pdf_page_image_url?: string;
  pdf_page?: number;
  pdf_printed_page?: number; // Human-readable page number from PDF document
}

interface HeritageProvisionsProps {
  provisions: Provision[];
}

const HERITAGE_TYPE_LABELS: Record<string, string> = {
  control: 'Actionable Controls',
  character: 'HCA Character Statements',
  descriptive: 'Background Information',
};

const HERITAGE_TYPE_COLORS: Record<string, string> = {
  control: 'bg-green-100 text-green-800 border-green-300',
  character: 'bg-blue-100 text-blue-800 border-blue-300',
  descriptive: 'bg-gray-100 text-gray-600 border-gray-300',
};

const HERITAGE_ELEMENT_LABELS: Record<string, string> = {
  roof: 'Roof',
  verandah: 'Verandah',
  window: 'Windows',
  door: 'Doors',
  fence: 'Fencing',
  garden: 'Gardens',
  facade: 'Facade',
  chimney: 'Chimney',
  infill: 'Infill',
  car_parking: 'Parking',
  demolition: 'Demolition',
  interior: 'Interior',
  materials: 'Materials',
  setback: 'Setbacks',
  scale: 'Scale',
  general: 'General',
};

export function HeritageProvisions({ provisions }: HeritageProvisionsProps) {
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(['control']));
  const [expandedProvisions, setExpandedProvisions] = useState<Set<number>>(new Set());
  const [viewingPdfImage, setViewingPdfImage] = useState<{ url: string; page: number } | null>(null);
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(
    new Set(['control', 'character', 'descriptive'])
  );

  // Group by heritage type
  const byType: Record<string, Provision[]> = { control: [], character: [], descriptive: [] };
  provisions.forEach(p => {
    const type = p.v2_heritage_type || 'descriptive';
    if (!byType[type]) byType[type] = [];
    byType[type].push(p);
  });

  const toggleType = (type: string) => {
    setExpandedTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const toggleProvision = (id: number) => {
    setExpandedProvisions(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleTypeFilter = (type: string) => {
    setEnabledTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  // Group provisions by PDF page
  const groupByPage = (typeProvisions: Provision[], limit: number) => {
    const groupedByPage: { [page: number]: Provision[] } = {};
    const provisionsWithoutPage: Provision[] = [];

    typeProvisions.slice(0, limit).forEach(prov => {
      let pageNum: number | null = null;
      // Use printed page number if available (human-readable page from PDF)
      if (prov.pdf_printed_page) {
        pageNum = prov.pdf_printed_page;
        console.log(`[Heritage DEBUG] ID ${prov.id}: using pdf_printed_page=${pageNum}`);
      } else if (prov.pdf_page) {
        // Fallback to extraction page number
        pageNum = prov.pdf_page;
        console.log(`[Heritage DEBUG] ID ${prov.id}: using pdf_page=${pageNum} (no printed_page available)`);
      }
      // Final fallback to URL if pdf_page is missing
      // Handle both formats: "_page_X." (Marrickville) and "/page_X." (Ashfield)
      if (!pageNum && prov.pdf_page_image_url) {
        const match = prov.pdf_page_image_url.match(/[/_]page_(\d+)\./);
        if (match) {
          pageNum = parseInt(match[1]);
        }
      }

      if (pageNum) {
        if (!groupedByPage[pageNum]) {
          groupedByPage[pageNum] = [];
        }
        groupedByPage[pageNum].push(prov);
      } else {
        provisionsWithoutPage.push(prov);
      }
    });

    const sortedPageGroups = Object.entries(groupedByPage)
      .sort(([pageA], [pageB]) => parseInt(pageA) - parseInt(pageB));

    return { sortedPageGroups, provisionsWithoutPage };
  };

  // Filter chips component
  const FilterChips = () => (
    <div className="flex items-center gap-1.5 mb-3 flex-wrap">
      <span className="text-xs text-gray-500 mr-1">Show:</span>

      <button
        onClick={() => toggleTypeFilter('control')}
        className={`px-2 py-1 rounded text-xs font-medium transition-all ${
          enabledTypes.has('control')
            ? 'bg-green-100 text-green-800 border border-green-300'
            : 'text-gray-400 bg-white border border-gray-200 line-through opacity-60'
        }`}
      >
        {enabledTypes.has('control') ? '✓ ' : ''}Controls {byType.control.length}
      </button>

      <button
        onClick={() => toggleTypeFilter('character')}
        className={`px-2 py-1 rounded text-xs font-medium transition-all ${
          enabledTypes.has('character')
            ? 'bg-blue-100 text-blue-800 border border-blue-300'
            : 'text-gray-400 bg-white border border-gray-200 line-through opacity-60'
        }`}
      >
        {enabledTypes.has('character') ? '✓ ' : ''}Character {byType.character.length}
      </button>

      <button
        onClick={() => toggleTypeFilter('descriptive')}
        className={`px-2 py-1 rounded text-xs font-medium transition-all ${
          enabledTypes.has('descriptive')
            ? 'bg-gray-100 text-gray-600 border border-gray-300'
            : 'text-gray-400 bg-white border border-gray-200 line-through opacity-60'
        }`}
      >
        {enabledTypes.has('descriptive') ? '✓ ' : ''}Descriptive {byType.descriptive.length}
      </button>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button className="ml-1 text-gray-400 hover:text-gray-600 transition-colors">
              <Info className="h-3 w-3" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            <TypesTooltip />
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );

  // Tooltip content
  const TypesTooltip = () => (
    <div className="text-xs space-y-2">
      <div>
        <div className="font-semibold text-green-800">CONTROLS</div>
        <div className="text-gray-600">Actionable requirements (C1-C999, "must", "shall")</div>
      </div>
      <div>
        <div className="font-semibold text-blue-800">CHARACTER</div>
        <div className="text-gray-600">HCA descriptions and heritage significance</div>
      </div>
      <div>
        <div className="font-semibold text-gray-600">DESCRIPTIVE</div>
        <div className="text-gray-600">Background information and policy context</div>
      </div>
    </div>
  );

  const typeOrder = ['control', 'character', 'descriptive'];

  return (
    <>
      <FilterChips />

      <div className="space-y-3">
        {typeOrder.map(type => {
          const typeProvisions = byType[type];

          // Hide if type is disabled via filter
          if (!enabledTypes.has(type)) return null;

          if (!typeProvisions || typeProvisions.length === 0) return null;

          const isExpanded = expandedTypes.has(type);
          const displayLimit = type === 'control' ? 20 : 5;
          const { sortedPageGroups, provisionsWithoutPage } = groupByPage(typeProvisions, displayLimit);

          return (
            <div key={type} className={`border rounded-lg ${HERITAGE_TYPE_COLORS[type]}`}>
              <div
                className="px-3 py-2 cursor-pointer flex items-center justify-between"
                onClick={() => toggleType(type)}
              >
                <div className="flex items-center gap-2">
                  {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  <span className="font-medium">{HERITAGE_TYPE_LABELS[type]}</span>
                  <Badge variant="secondary" className="text-xs">{typeProvisions.length}</Badge>
                </div>
                {type === 'control' && (
                  <span className="text-xs opacity-75">Checkable requirements</span>
                )}
              </div>

              {isExpanded && (
                <div className="px-3 pb-3 bg-white rounded-b-lg">
                  {sortedPageGroups.map(([pageNumStr, pageProvisions], groupIdx) => {
                    const pdfUrl = pageProvisions[0]?.pdf_page_image_url;
                    const pdfPage = parseInt(pageNumStr);

                    return (
                      <div key={`page-${pdfPage}`} className={groupIdx > 0 ? 'border-t pt-2 mt-2' : ''}>
                        {/* Provisions in this page group */}
                        {pageProvisions.map((provision) => (
                          <div key={provision.id} className="border rounded p-2 bg-white mb-2">
                            <div className="flex items-center gap-1 mb-1 flex-wrap">
                              {provision.v2_heritage_element?.map(elem => (
                                <Badge key={elem} variant="outline" className="text-xs bg-purple-50">
                                  {HERITAGE_ELEMENT_LABELS[elem] || elem}
                                </Badge>
                              ))}
                              {provision.v2_heritage_hca && (
                                <Badge variant="outline" className="text-xs bg-amber-50">
                                  {provision.v2_heritage_hca.replace(/_/g, ' ')}
                                </Badge>
                              )}
                            </div>
                            <div
                              className={`text-sm cursor-pointer ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-3'}`}
                              onClick={() => toggleProvision(provision.id)}
                            >
                              <FormattedProvisionText
                                text={stripSectionHeader(provision.provision_text, undefined)}
                                compact
                              />
                            </div>
                            {provision.provision_text.length > 150 && (
                              <button
                                className="text-xs text-blue-600 mt-1"
                                onClick={() => toggleProvision(provision.id)}
                              >
                                {expandedProvisions.has(provision.id) ? 'Show less' : 'Show more'}
                              </button>
                            )}
                          </div>
                        ))}

                        {/* PDF Page Button - icon only with tooltip */}
                        {pdfPage && pdfUrl && (
                          <div className="flex justify-end mt-1 mb-1">
                            <button
                              className="p-1.5 rounded hover:bg-slate-200 transition-colors"
                              title={`Part 8 Heritage - Page ${pdfPage}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                setViewingPdfImage({ url: pdfUrl, page: pdfPage });
                              }}
                            >
                              <FileText className="w-4 h-4 text-slate-600 hover:text-slate-800" />
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Provisions without page numbers */}
                  {provisionsWithoutPage.map((provision) => (
                    <div key={provision.id} className="border rounded p-2 bg-white mb-2">
                      <div className="flex items-center gap-1 mb-1 flex-wrap">
                        {provision.v2_heritage_element?.map(elem => (
                          <Badge key={elem} variant="outline" className="text-xs bg-purple-50">
                            {HERITAGE_ELEMENT_LABELS[elem] || elem}
                          </Badge>
                        ))}
                      </div>
                      <FormattedProvisionText
                        text={stripSectionHeader(provision.provision_text, undefined)}
                        compact
                      />
                    </div>
                  ))}

                  {typeProvisions.length > displayLimit && (
                    <p className="text-xs text-gray-500 text-center mt-2">
                      Showing {displayLimit} of {typeProvisions.length}
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* PDF Image Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        imageUrl={viewingPdfImage?.url}
        pageNumber={viewingPdfImage?.page}
      />
    </>
  );
}
