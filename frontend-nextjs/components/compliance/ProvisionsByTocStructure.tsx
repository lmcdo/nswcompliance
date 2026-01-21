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
import { Loader2, FileText, Filter, HelpCircle, ChevronDown, ChevronRight, Shield } from 'lucide-react';
import { INNER_WEST_OVERVIEW, COUNCIL_CONFIGS } from '@/lib/council-config';

// Council-specific layer labels (must match PageGroupedProvisions.tsx)
const COUNCIL_LAYER_LABELS: Record<string, Record<string, string>> = {
  ashfield: {
    generic: 'Ashfield-wide',
    use_specific: 'Zone-Specific',
    condition: 'Heritage',
    precinct: 'Village Precinct',
  },
  leichhardt: {
    generic: 'Leichhardt-wide',
    use_specific: 'Zone-Specific',
    condition: 'Heritage',
    precinct: 'Distinct Neighbourhood',
  },
  marrickville: {
    generic: 'Marrickville-wide',
    use_specific: 'Zone-Specific',
    condition: 'Heritage',
    precinct: 'Precinct Character',
  },
};

const DEFAULT_LAYER_LABELS: Record<string, string> = {
  generic: 'LGA-wide',
  use_specific: 'Zone-Specific',
  condition: 'Condition',
  precinct: 'Precinct',
};

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
    // Fix spacing artifacts in numbers
    .replace(/(\d)\s+(\d)\s+(\d)\s+(m|c|k)\s+m\s+\$/g, '$1$2$3$4m')  // "1 8 0 m m $" -> "180mm"
    .replace(/\s+\$/g, '')  // Remove trailing "$" artifacts
    .replace(/,\s*#\s*/g, ', ')  // ", #" -> ", "
    .replace(/[\u2018\u2019\u201C\u201D]/g, (match) => {  // Smart quotes to regular quotes
      return match === '\u2018' || match === '\u2019' ? "'" : '"';
    })
    .replace(/·/g, ' · ')  // Fix middle dot spacing
    .replace(/\s{2,}/g, ' ')  // Multiple spaces to single
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

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) {
    const error = new Error('Failed to fetch provisions');
    throw error;
  }
  return res.json();
};

// POST fetcher for HCA provisions API
const hcaFetcher = async ([url, body]: [string, any]) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return response.json();
};

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
  const [layerFilter, setLayerFilter] = useState<string | null>(null);
  const [pdfModal, setPdfModal] = useState<{ url: string; page: number } | null>(null);
  const [showAbout, setShowAbout] = useState(false); // Collapsed by default
  const [showHcaSection, setShowHcaSection] = useState(false); // HCA section collapsed by default
  const [expandedHcaCategories, setExpandedHcaCategories] = useState<Set<string>>(new Set(['heritage'])); // Heritage expanded by default

  // Get council config
  const councilConfig = formerCouncil?.toLowerCase() && COUNCIL_CONFIGS[formerCouncil.toLowerCase()]
    ? COUNCIL_CONFIGS[formerCouncil.toLowerCase()]
    : null;

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
  }>(apiUrl, fetcher, {
    dedupingInterval: 60000,  // Dedupe requests within 60 seconds
    revalidateOnFocus: false, // Don't refetch on window focus
    errorRetryCount: 3,       // Retry up to 3 times on error
    errorRetryInterval: 1000, // Wait 1s between retries
    shouldRetryOnError: true, // Enable retry on error
  });

  // DCP names for each council
  const councilDcpNames: Record<string, string> = {
    leichhardt: 'Leichhardt DCP 2013',
    ashfield: 'Ashfield Comprehensive DCP 2016',
    marrickville: 'Marrickville DCP 2011',
  };

  // Fetch universal HCA provisions when heritage=true for any Inner West council
  const councilLower = formerCouncil?.toLowerCase() || '';
  const hcaRequestBody = heritage && ['leichhardt', 'ashfield', 'marrickville'].includes(councilLower) ? {
    precinctId: 'HCA',
    lga: 'Inner West',
    heritage: true
  } : null;

  const { data: hcaData, isLoading: hcaLoading } = useSWR(
    hcaRequestBody ? ['/api/compliance/precinct-requirements', hcaRequestBody] : null,
    hcaFetcher,
    {
      dedupingInterval: 60000,
      revalidateOnFocus: false,
    }
  );

  const hcaCategories = hcaData?.data?.hca_categories || hcaData?.data?.categories || [];
  const hcaCount = hcaCategories.reduce((sum: number, cat: any) => sum + (cat.requirements?.length || 0), 0);

  // Filter HCA requirements by council and exclude TOC pages
  const filterHcaRequirement = (req: any) => {
    // Exclude TOC pages (pdf_page 0 in DB)
    if (req.pdf_page === 0) return false;

    const url = req.pdf_page_image_url || '';
    if (councilLower === 'leichhardt') return url.includes('leichhardt');
    if (councilLower === 'ashfield') return url.includes('ashfield');
    if (councilLower === 'marrickville') return url.includes('marr');
    return true;
  };

  // Group provisions by category, each category has its own provisions array
  const hcaByCategory = hcaCategories
    .map((cat: any) => {
      const filteredReqs = (cat.requirements || []).filter(filterHcaRequirement);
      return {
        category: cat.category,
        displayName: cat.display_name || cat.category?.replace(/_/g, ' '),
        provisions: filteredReqs.map((req: any) => ({
          id: req.id,
          provision_text: req.requirement_text,
          // HCA provisions have 0-indexed page numbers from extraction, add +1 for display
          pdf_page: req.pdf_page != null ? req.pdf_page + 1 : undefined,
          pdf_page_image_url: req.pdf_page_image_url,
          v2_dcp_layer: 'condition',
          v2_topic: cat.display_name || cat.category,
        })),
      };
    })
    .filter((cat: any) => cat.provisions.length > 0)
    .sort((a: any, b: any) => b.provisions.length - a.provisions.length);

  // Flat list for total count
  const hcaProvisions = hcaByCategory.flatMap((cat: any) => cat.provisions);

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
  let filteredProvisions = topicFilter
    ? selectedProvisions.filter(p =>
        p.v2_topic?.toLowerCase().replace(/ /g, '_') === topicFilter
      )
    : selectedProvisions;

  // Apply layer filter if set
  if (layerFilter) {
    filteredProvisions = filteredProvisions.filter(p =>
      (p.v2_dcp_layer || p.layer) === layerFilter
    );
  }

  // Get unique topics for filter chips
  const availableTopics = [...new Set(
    selectedProvisions.map(p => p.v2_topic).filter(Boolean)
  )].sort();

  // Count provisions by layer for the current selection
  const layerCounts = {
    generic: selectedProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'generic').length,
    use_specific: selectedProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'use_specific').length,
    condition: selectedProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'condition').length,
    precinct: selectedProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'precinct').length,
  };

  // Check if any provisions have C/O markers
  const hasMarkers = selectedProvisions.some(p => p.v2_marker);

  const handleSelectPart = (partId: string) => {
    setSelectedPart(partId);
    setSelectedSection(null);
    setTopicFilter(null);
    setLayerFilter(null); // Reset layer filter when changing parts
  };

  const handleSelectSection = (partId: string, sectionId: string) => {
    setSelectedPart(partId);
    setSelectedSection(sectionId);
    setTopicFilter(null);
    setLayerFilter(null); // Reset layer filter when changing sections
  };

  return (
    <div className="space-y-4">
      {/* About Inner West DCPs - Collapsible */}
      {formerCouncil && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <button
            onClick={() => setShowAbout(!showAbout)}
            className="w-full flex items-center gap-2 px-4 py-3 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-50 transition-colors"
          >
            <HelpCircle className="h-4 w-4" />
            <span className="font-medium">About Inner West DCPs</span>
            {showAbout ? <ChevronDown className="h-4 w-4 ml-auto" /> : <ChevronRight className="h-4 w-4 ml-auto" />}
          </button>
          {showAbout && (
            <div className="px-4 pb-4 border-t bg-slate-50">
              {/* DCP Title Bar */}
              {councilConfig && (
                <div className="bg-gradient-to-r from-slate-800 to-slate-700 px-4 py-3 -mx-4 mb-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-white" />
                      <span className="font-semibold text-white text-sm">
                        {councilConfig.dcpCitation}
                      </span>
                    </div>
                    <Badge variant="outline" className="bg-white/10 text-white border-white/20 text-xs">
                      {totalProvisions} provisions applicable to this address
                    </Badge>
                  </div>
                </div>
              )}
              <p className="text-sm text-slate-700 whitespace-pre-line leading-relaxed">{INNER_WEST_OVERVIEW}</p>
            </div>
          )}
        </div>
      )}

      {/* Universal HCA Provisions Banner - shown for heritage properties in any Inner West council */}
      {heritage && ['leichhardt', 'ashfield', 'marrickville'].includes(councilLower) && (
        <div id="dcp-hca-section" className="border border-blue-200 rounded-lg overflow-hidden bg-blue-50/30">
          <button
            onClick={() => setShowHcaSection(!showHcaSection)}
            className="w-full flex items-center gap-2 px-4 py-3 text-sm hover:bg-blue-100/50 transition-colors"
          >
            <Shield className="h-4 w-4 text-blue-700" />
            <span className="font-semibold text-blue-900">Universal Heritage Conservation Area Controls</span>
            <Badge className="ml-2 bg-blue-100 text-blue-800 text-xs">
              {hcaLoading ? '...' : `${hcaProvisions.length} provisions`}
            </Badge>
            {showHcaSection ? <ChevronDown className="h-4 w-4 ml-auto text-blue-600" /> : <ChevronRight className="h-4 w-4 ml-auto text-blue-600" />}
          </button>
          {showHcaSection && (
            <div className="px-4 pb-4 border-t border-blue-200">
              <p className="text-xs text-blue-800 mt-3 mb-3 bg-blue-100 rounded px-2 py-1.5">
                These controls apply to <strong>all Heritage Conservation Area properties</strong> in the former {formerCouncil} council area ({councilDcpNames[councilLower] || 'DCP'}).
                They are in addition to the site-specific DCP provisions shown below.
              </p>
              {hcaLoading ? (
                <div className="flex items-center gap-2 py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  <span className="text-sm text-blue-700">Loading HCA provisions...</span>
                </div>
              ) : hcaByCategory.length > 0 ? (
                <div className="space-y-2">
                  {hcaByCategory.map((cat: any) => {
                    const isExpanded = expandedHcaCategories.has(cat.category);
                    return (
                      <div key={cat.category} className="border border-blue-100 rounded-lg overflow-hidden bg-white">
                        <button
                          onClick={() => {
                            const newSet = new Set(expandedHcaCategories);
                            if (isExpanded) newSet.delete(cat.category);
                            else newSet.add(cat.category);
                            setExpandedHcaCategories(newSet);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-blue-50 transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4 text-blue-500" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-blue-500" />
                          )}
                          <span className="font-medium text-blue-900 capitalize">{cat.displayName}</span>
                          <Badge variant="outline" className="ml-auto text-xs bg-blue-50 text-blue-700">
                            {cat.provisions.length}
                          </Badge>
                        </button>
                        {isExpanded && (
                          <div className="border-t border-blue-100 p-2">
                            <PageGroupedProvisions
                              provisions={cat.provisions}
                              onViewPdf={(url, page) => setPdfModal({ url, page })}
                              theme={{
                                zebraStripeBg: 'bg-blue-50/30',
                                zebraStripeAltBg: 'bg-white',
                                borderColorClass: 'border-blue-100',
                              }}
                              showLayerBadges={false}
                              formerCouncil="leichhardt"
                              maxProvisions={50}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-gray-500 py-2">No universal HCA provisions found.</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Main two-panel layout */}
      <div className="flex border rounded-lg bg-white overflow-hidden">
      {/* Left: TOC Sidebar */}
      <div className="w-64 border-r bg-gray-50 flex-shrink-0">
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
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedPart
                  ? sanitizeText(tocStructure[selectedPart]?.part_name) || selectedPart
                  : 'Select a section'}
              </h3>
              {selectedSection && selectedPart && (
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

          {/* Topic filter chips - show all topics */}
          {availableTopics.length > 1 && (
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <Filter className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-xs text-gray-500 font-medium">Topics:</span>
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
              {availableTopics.map(topic => (
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
            </div>
          )}

          {/* Layer filter - clickable legend */}
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <Filter className="h-3.5 w-3.5 text-gray-400" />
            <span className="text-xs text-gray-500 font-medium">Layers:</span>
            <button
              onClick={() => setLayerFilter(null)}
              className={`px-2 py-0.5 text-xs rounded-full transition-colors ${
                !layerFilter
                  ? 'bg-teal-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All
            </button>
            {[
              { key: 'generic', color: '#14b8a6' },
              { key: 'use_specific', color: '#3b82f6' },
              { key: 'condition', color: '#f59e0b' },
              { key: 'precinct', color: '#8b5cf6' },
            ].map(({ key, color }) => {
              const councilLabels = formerCouncil?.toLowerCase() && COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()];
              const label = councilLabels ? councilLabels[key] : DEFAULT_LAYER_LABELS[key];
              const count = layerCounts[key as keyof typeof layerCounts] || 0;
              const hasProvisions = count > 0;

              return (
                <button
                  key={key}
                  onClick={() => hasProvisions && setLayerFilter(layerFilter === key ? null : key)}
                  disabled={!hasProvisions}
                  className={`flex items-center gap-1.5 px-2 py-0.5 text-xs rounded-full transition-colors ${
                    !hasProvisions
                      ? 'bg-gray-50 text-gray-400 cursor-not-allowed opacity-50'
                      : layerFilter === key
                      ? 'bg-gray-800 text-white ring-2 ring-offset-1'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  style={layerFilter === key ? { ringColor: color } : undefined}
                  title={!hasProvisions ? 'No provisions with this layer in selected section' : undefined}
                >
                  <div
                    className="w-2.5 h-2.5 rounded-sm"
                    style={{ backgroundColor: hasProvisions ? color : '#d1d5db' }}
                  />
                  {label} ({count})
                </button>
              );
            })}
          </div>

          {/* Marker key - explains C1/O1 badges (only show if markers exist) */}
          {hasMarkers && (
            <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
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
        </div>

        {/* Provisions list */}
        <div className="p-4">
          {filteredProvisions.length > 0 ? (
            <PageGroupedProvisions
              provisions={filteredProvisions}
              formerCouncil={formerCouncil}
              showLayerBadges={true}
              showLegend={true}
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
    </div>
  );
}
