'use client';

/**
 * ProvisionsByTocStructure - TOC-based provision display
 *
 * Two-panel layout:
 * - Left: TocSidebar for navigation
 * - Right: Provisions for selected part/section
 */

import { useState, useEffect } from 'react';
import useSWR from 'swr';
import { TocSidebar } from './TocSidebar';
import { PageGroupedProvisions } from './PageGroupedProvisions';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, FileText, Filter } from 'lucide-react';

/**
 * Fix common UTF-8 encoding artifacts (mojibake)
 */
function sanitizeText(text: string | undefined | null): string {
  if (!text) return '';
  return text
    .replace(/â€"/g, '—')
    .replace(/â€˜/g, "'")
    .replace(/â€™/g, "'")
    .replace(/â€œ/g, '"')
    .replace(/â€\u009D/g, '"')
    .replace(/â˜…/g, '★')
    .replace(/Â²/g, '²')
    .replace(/Â°/g, '°')
    .replace(/â€¢/g, '•')
    .replace(/â€¦/g, '…')
    .replace(/Ã©/g, 'é')
    .replace(/Ã¨/g, 'è')
    .replace(/^[â€"\s]+/, '')
    .trim();
}

interface TocSection {
  section_id: string;
  section_title: string;
  provision_count: number;
  provisions: any[];
}

interface TocPart {
  part_id: string;
  part_name: string;
  provision_count: number;
  sections: Record<string, TocSection>;
}

interface ProvisionsByTocStructureProps {
  formerCouncil: string;
  zone?: string;
  heritage?: boolean;
  hcaName?: string;
  precinctId?: string;
}

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function ProvisionsByTocStructure({
  formerCouncil,
  zone,
  heritage,
  hcaName,
  precinctId
}: ProvisionsByTocStructureProps) {
  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [topicFilter, setTopicFilter] = useState<string | null>(null);
  const [pdfModal, setPdfModal] = useState<{ url: string; page: number } | null>(null);

  // Build API URL with groupBy=toc
  const params = new URLSearchParams();
  params.set('groupBy', 'toc');
  if (formerCouncil) params.set('former_council', formerCouncil);
  if (zone) params.set('zone', zone);
  if (heritage !== undefined) params.set('heritage', String(heritage));
  if (hcaName) params.set('hca', hcaName);
  if (precinctId) params.set('precinct_id', precinctId);

  const apiUrl = `/api/provisions/for-property?${params.toString()}`;

  const { data, error, isLoading } = useSWR<{
    success: boolean;
    data: {
      by_toc: Record<string, TocPart>;
      by_topic: Record<string, any[]>;
      summary: {
        total_provisions: number;
      };
    };
  }>(apiUrl, fetcher);

  // Auto-select first part on load
  useEffect(() => {
    if (data?.data?.by_toc && !selectedPart) {
      const parts = Object.keys(data.data.by_toc);
      if (parts.length > 0) {
        setSelectedPart(parts[0]);
      }
    }
  }, [data, selectedPart]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-8 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-teal-600 mr-2" />
          <span className="text-gray-600">Loading DCP structure...</span>
        </CardContent>
      </Card>
    );
  }

  if (error || !data?.success) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-red-600">
          Failed to load provisions. Please try again.
        </CardContent>
      </Card>
    );
  }

  const tocStructure = data?.data?.by_toc || {};
  const totalProvisions = data?.data?.summary?.total_provisions || 0;

  // Safety check - if no TOC data, show message
  if (!data?.data?.by_toc || Object.keys(tocStructure).length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-gray-500">
          No DCP provisions found for this property.
        </CardContent>
      </Card>
    );
  }

  // Get provisions for selected part/section
  const getSelectedProvisions = (): any[] => {
    if (!selectedPart || !tocStructure[selectedPart]) return [];

    const part = tocStructure[selectedPart];

    if (selectedSection && part.sections[selectedSection]) {
      return part.sections[selectedSection].provisions;
    }

    // Return all provisions for the part
    return Object.values(part.sections).flatMap(s => s.provisions);
  };

  const selectedProvisions = getSelectedProvisions();

  // Apply topic filter if set
  const filteredProvisions = topicFilter
    ? selectedProvisions.filter(p =>
        p.v2_topic?.toLowerCase().replace(/ /g, '_') === topicFilter
      )
    : selectedProvisions;

  // Get unique topics for filter chips
  const availableTopics = [...new Set(
    selectedProvisions.map(p => p.v2_topic).filter(Boolean)
  )].sort();

  const handleSelectPart = (partId: string) => {
    setSelectedPart(partId);
    setSelectedSection(null);
    setTopicFilter(null);
  };

  const handleSelectSection = (partId: string, sectionId: string) => {
    setSelectedPart(partId);
    setSelectedSection(sectionId);
    setTopicFilter(null);
  };

  return (
    <div className="flex h-[calc(100vh-200px)] min-h-[500px] border rounded-lg bg-white overflow-hidden">
      {/* Left: TOC Sidebar */}
      <div className="w-64 border-r bg-gray-50 flex-shrink-0 overflow-hidden">
        <TocSidebar
          tocStructure={tocStructure}
          selectedPart={selectedPart}
          selectedSection={selectedSection}
          onSelectPart={handleSelectPart}
          onSelectSection={handleSelectSection}
          formerCouncil={formerCouncil}
        />
      </div>

      {/* Right: Provisions content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedPart
                  ? sanitizeText(tocStructure[selectedPart]?.part_name) || selectedPart
                  : 'Select a section'}
              </h3>
              {selectedSection && (
                <p className="text-sm text-gray-600">
                  {sanitizeText(tocStructure[selectedPart]?.sections[selectedSection]?.section_title)}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-teal-700 font-medium">
                {filteredProvisions.length} provisions in this section
              </span>
              <span className="text-gray-400">|</span>
              <span className="text-gray-500">
                {totalProvisions} total for this property
              </span>
            </div>
          </div>

          {/* Topic filter chips */}
          {availableTopics.length > 1 && (
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <Filter className="h-3.5 w-3.5 text-gray-400" />
              <button
                onClick={() => setTopicFilter(null)}
                className={`px-2 py-0.5 text-xs rounded-full transition-colors ${
                  !topicFilter
                    ? 'bg-teal-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                All
              </button>
              {availableTopics.slice(0, 8).map(topic => (
                <button
                  key={topic}
                  onClick={() => setTopicFilter(
                    topic.toLowerCase().replace(/ /g, '_')
                  )}
                  className={`px-2 py-0.5 text-xs rounded-full transition-colors ${
                    topicFilter === topic.toLowerCase().replace(/ /g, '_')
                      ? 'bg-teal-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {topic}
                </button>
              ))}
              {availableTopics.length > 8 && (
                <span className="text-xs text-gray-400">
                  +{availableTopics.length - 8} more
                </span>
              )}
            </div>
          )}
        </div>

        {/* Provisions list */}
        <div className="flex-1 overflow-y-auto p-4">
          {filteredProvisions.length > 0 ? (
            <PageGroupedProvisions
              provisions={filteredProvisions}
              formerCouncil={formerCouncil}
              showLayerBadges={true}
              maxProvisions={100}
              onViewPdf={(url, page) => setPdfModal({ url, page })}
            />
          ) : (
            <div className="text-center py-12 text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>No provisions in this section</p>
              {topicFilter && (
                <button
                  onClick={() => setTopicFilter(null)}
                  className="mt-2 text-teal-600 text-sm hover:underline"
                >
                  Clear filter
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* PDF Modal */}
      <PdfImageModal
        isOpen={!!pdfModal}
        onClose={() => setPdfModal(null)}
        imageUrl={pdfModal?.url}
        pageNumber={pdfModal?.page}
        title={selectedPart ? `${formerCouncil} DCP - ${selectedPart}` : undefined}
      />
    </div>
  );
}
