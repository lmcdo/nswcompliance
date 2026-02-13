'use client';

/**
 * ProvisionsByTocStructure - TOC-based provision display
 *
 * Two-panel layout:
 * - Left: TocSidebar for navigation
 * - Right: Provisions for selected part/section
 */

import { useState, useEffect, useMemo } from 'react';
import useSWR from 'swr';
import { TocSidebar } from './TocSidebar';
import { PageGroupedProvisions, Provision } from './PageGroupedProvisions';
import { LayerExplanation } from './LayerExplanation';
import { EPAAct415ComplianceNotice } from './EPAAct415Notice';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, FileText, Filter, HelpCircle, ChevronDown, ChevronRight, Shield, Search, X, Ruler } from 'lucide-react';
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
  precinctName?: string;
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
  precinctId,
  precinctName
}: ProvisionsByTocStructureProps) {
  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [topicFilter, setTopicFilter] = useState<string | null>(null);
  const [layerFilter, setLayerFilter] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
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
      complete_toc: Record<string, TocPart>;  // Complete unfiltered TOC for sidebar
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

  // Extract heritage provisions from condition layer (Layer 3)
  const councilLower = formerCouncil?.toLowerCase() || '';

  // Get heritage provisions from the main API response's condition layer
  const conditionLayer = data?.data?.by_layer?.[2]; // Layer 3 = condition
  const allConditionProvisions = conditionLayer?.provisions || [];

  // Filter for heritage marker provisions
  const heritageProvisions = allConditionProvisions.filter((p: any) =>
    p.v2_marker?.toLowerCase() === 'heritage'
  );

  // Group heritage provisions by DCP part for the HCA section
  const hcaByPart: Record<string, any[]> = {};
  heritageProvisions.forEach((provision: any) => {
    const part = provision.v2_dcp_part || 'Other';
    if (!hcaByPart[part]) {
      hcaByPart[part] = [];
    }
    hcaByPart[part].push(provision);
  });

  // Convert to category structure for display
  const hcaByCategory = Object.entries(hcaByPart).map(([part, provisions]) => ({
    category: part,
    displayName: part,
    provisions: provisions
  })).filter(cat => cat.provisions.length > 0);

  // Flat list for total count
  const hcaProvisions = heritageProvisions;
  const hcaLoading = isLoading;

  // Auto-select first part on load (use complete TOC)
  useEffect(() => {
    if (data?.data?.complete_toc && !selectedPart) {
      const parts = Object.keys(data.data.complete_toc);
      if (parts.length > 0) {
        setSelectedPart(parts[0]);
      }
    }
  }, [data, selectedPart]);

  // Debounce search input with 300ms delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Extract data with safe defaults (for use in hooks below)
  const tocStructure = data?.data?.by_toc || {};  // Filtered provisions for selected part
  const completeTocStructure = data?.data?.complete_toc || {};  // Complete TOC for sidebar navigation
  const totalProvisions = data?.data?.summary?.total_provisions || 0;

  // Get provisions for selected part/section - memoized to avoid unnecessary recalculations
  const rawSelectedProvisions = useMemo(() => {
    if (!selectedPart || !tocStructure[selectedPart]) return [];

    const part = tocStructure[selectedPart];

    if (selectedSection && part.sections[selectedSection]) {
      return part.sections[selectedSection].provisions;
    }

    // Return all provisions for the part
    return Object.values(part.sections).flatMap(s => s.provisions);
  }, [selectedPart, selectedSection, tocStructure]);

  // Deduplicate provisions by text content (safety net for any DB/API duplicates)
  const selectedProvisions = useMemo(() => {
    const seenTexts = new Set<string>();
    return rawSelectedProvisions.filter(p => {
      const key = `${(p.provision_text || '').substring(0, 100)}|${p.pdf_page || 0}`;
      if (seenTexts.has(key)) return false;
      seenTexts.add(key);
      return true;
    });
  }, [rawSelectedProvisions]);

  // Count provisions by layer (always from full set — layer buttons always visible)
  const layerCounts = useMemo(() => ({
    generic: selectedProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'generic').length,
    use_specific: selectedProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'use_specific').length,
    condition: selectedProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'condition').length,
    precinct: selectedProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'precinct').length,
  }), [selectedProvisions]);

  // Layer-filtered base: excludes TOC entries and applies active layer.
  // Used by both filteredProvisions (rendered list) and topic chips (counts).
  const layerFilteredProvisions = useMemo(() => {
    const base = selectedProvisions.filter(p => p.v2_provision_type !== 'TOC');
    if (!layerFilter) return base;
    return base.filter(p => (p.v2_dcp_layer || p.layer) === layerFilter);
  }, [selectedProvisions, layerFilter]);

  // Apply search + topic filter on top of layer-filtered base, then sort by priority
  const filteredProvisions = useMemo(() => {
    let filtered = layerFilteredProvisions;

    if (debouncedSearch) {
      const searchLower = debouncedSearch.toLowerCase();
      filtered = filtered.filter(p =>
        p.provision_text?.toLowerCase().includes(searchLower)
      );
    }

    if (topicFilter) {
      filtered = filtered.filter(p =>
        p.v2_topic?.toLowerCase().replace(/ /g, '_') === topicFilter
      );
    }

    return filtered.sort((a, b) => {
      const priorityOrder = { critical: 1, important: 2, guideline: 3, contextual: 4 };
      const aPriority = priorityOrder[a.v2_display_priority || 'important'] || 2;
      const bPriority = priorityOrder[b.v2_display_priority || 'important'] || 2;
      return aPriority - bPriority;
    });
  }, [layerFilteredProvisions, debouncedSearch, topicFilter]);

  // Get unique topics for filter chips — scoped to selected layer
  const availableTopics = useMemo(() =>
    [...new Set(layerFilteredProvisions.map(p => p.v2_topic).filter(Boolean))].sort(),
    [layerFilteredProvisions]
  );

  // Check if any provisions have C/O markers
  const hasMarkers = useMemo(() =>
    selectedProvisions.some(p => p.v2_marker),
    [selectedProvisions]
  );

  // Calculate priority stats per topic — scoped to selected layer
  const topicPriorityStats = useMemo(() => {
    const stats: Record<string, { critical: number; total: number }> = {};
    layerFilteredProvisions.forEach(p => {
      const topic = p.v2_topic?.toLowerCase().replace(/ /g, '_') || 'other';
      if (!stats[topic]) stats[topic] = { critical: 0, total: 0 };
      stats[topic].total++;
      if (p.v2_display_priority === 'critical') stats[topic].critical++;
    });
    return stats;
  }, [layerFilteredProvisions]);

  // NOW handle loading/error states AFTER all hooks are called
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

      {/* EP&A Act s 4.15 Compliance Disclaimer */}
      <EPAAct415ComplianceNotice />

      {/* Universal HCA Provisions Banner - shown for heritage properties in any Inner West council */}
      {heritage && ['leichhardt', 'ashfield', 'marrickville'].includes(councilLower) && hcaProvisions.length > 0 && (
        <div id="dcp-hca-section" className="border border-blue-200 rounded-lg overflow-hidden bg-blue-50/30">
          <button
            onClick={() => setShowHcaSection(!showHcaSection)}
            className="w-full flex items-center gap-2 px-4 py-3 text-sm hover:bg-blue-100/50 transition-colors"
          >
            <Shield className="h-4 w-4 text-blue-700" />
            <span className="font-semibold text-blue-900">Heritage Conservation Area Controls</span>
            <Badge className="ml-2 bg-blue-100 text-blue-800 text-xs">
              {hcaLoading ? '...' : `${hcaProvisions.length} total provisions`}
            </Badge>
            {showHcaSection ? <ChevronDown className="h-4 w-4 ml-auto text-blue-600" /> : <ChevronRight className="h-4 w-4 ml-auto text-blue-600" />}
          </button>
          {showHcaSection && (
            <div className="px-4 pb-4 border-t border-blue-200">
              <p className="text-xs text-blue-800 mt-3 mb-3 bg-blue-100 rounded px-2 py-1.5">
                <strong>{hcaProvisions.length} total heritage provisions</strong> across all DCP parts for this property.
                {councilLower === 'leichhardt' && (
                  <span> Leichhardt DCP has general heritage controls that apply to all HCAs (no HCA-specific provisions).</span>
                )}
                {(councilLower === 'ashfield' || councilLower === 'marrickville') && (
                  <span> Includes both general heritage controls and HCA-specific provisions.</span>
                )}
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
          tocStructure={completeTocStructure}
          filteredTocStructure={tocStructure}
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
                  ? sanitizeText(completeTocStructure[selectedPart]?.part_name) || selectedPart
                  : 'Select a section'}
              </h3>
              {selectedSection && selectedPart && (
                <p className="text-sm text-gray-600">
                  {sanitizeText(completeTocStructure[selectedPart]?.sections[selectedSection]?.section_title)}
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

          {/* Search box */}
          <div className="mt-3 relative">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search provisions..."
                className="w-full pl-10 pr-10 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            {debouncedSearch && (
              <div className="mt-1 text-xs text-gray-500">
                {filteredProvisions.length} provision{filteredProvisions.length !== 1 ? 's' : ''} match your search
              </div>
            )}
          </div>

          {/* Why am I seeing these provisions? */}
          <LayerExplanation
            zone={zone}
            heritage={heritage}
            hcaName={hcaName}
            precinctName={precinctName}
            formerCouncil={formerCouncil}
          />

          {/* Combined filters section */}
          <div className="mt-3 space-y-2">
            {/* Layer filter - primary filter row */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-500 font-medium min-w-[70px]">Applies because:</span>
              {[
                { key: null, label: 'All layers', color: '#6b7280' },
                { key: 'generic', color: '#14b8a6' },
                { key: 'use_specific', color: '#3b82f6' },
                { key: 'condition', color: '#f59e0b' },
                { key: 'precinct', color: '#8b5cf6' },
              ].map((item) => {
                if (item.key === null) {
                  // "All layers" button
                  const totalCount = Object.values(layerCounts).reduce((a, b) => a + b, 0);
                  return (
                    <button
                      key="all"
                      onClick={() => { setLayerFilter(null); setTopicFilter(null); }}
                      className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md transition-colors ${
                        !layerFilter && !topicFilter
                          ? 'bg-gray-800 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      All ({totalCount})
                    </button>
                  );
                }

                const councilLabels = formerCouncil?.toLowerCase() && COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()];
                const label = councilLabels ? councilLabels[item.key] : DEFAULT_LAYER_LABELS[item.key];
                const count = layerCounts[item.key as keyof typeof layerCounts] || 0;
                const hasProvisions = count > 0;

                return (
                  <button
                    key={item.key}
                    onClick={() => hasProvisions && (setLayerFilter(layerFilter === item.key ? null : item.key), setTopicFilter(null))}
                    disabled={!hasProvisions}
                    className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md transition-colors ${
                      !hasProvisions
                        ? 'bg-gray-50 text-gray-400 cursor-not-allowed opacity-50'
                        : layerFilter === item.key
                        ? 'text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    style={layerFilter === item.key ? { backgroundColor: item.color } : undefined}
                    title={!hasProvisions ? 'No provisions with this layer' : undefined}
                  >
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: hasProvisions ? item.color : '#d1d5db' }}
                    />
                    {label} ({count})
                  </button>
                );
              })}
            </div>

            {/* Topic filter chips - secondary filter row */}
            {availableTopics.length > 1 && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-gray-500 font-medium min-w-[70px]">Filter topic:</span>
                  <button
                    onClick={() => setTopicFilter(null)}
                    className={`px-2 py-0.5 text-xs rounded-full transition-colors ${
                      !topicFilter
                        ? 'bg-teal-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    All topics
                  </button>
                  {availableTopics.map(topic => {
                    const topicKey = topic.toLowerCase().replace(/ /g, '_');
                    const stats = topicPriorityStats[topicKey] || { critical: 0, total: 0 };
                    const hasCritical = stats.critical > 0;

                    return (
                      <button
                        key={topic}
                        onClick={() => setTopicFilter(topicFilter === topicKey ? null : topicKey)}
                        className={`px-2 py-0.5 text-xs rounded-full transition-colors flex items-center gap-1 ${
                          topicFilter === topicKey
                            ? 'bg-teal-600 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {topic} ({stats.total})
                        {hasCritical && (
                          <Ruler className={`w-3 h-3 ${topicFilter === topicKey ? 'text-white/80' : 'text-gray-500'}`} />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Status line — plain-language summary of active filters */}
            {(layerFilter || topicFilter) && (
              <div className="text-xs text-gray-500 pt-1 border-t border-gray-100 mt-0.5">
                {(() => {
                  const labels = COUNCIL_LAYER_LABELS[(formerCouncil || '').toLowerCase()] || DEFAULT_LAYER_LABELS;
                  const count = filteredProvisions.length;
                  const base = `Showing ${count} provision${count !== 1 ? 's' : ''}`;
                  const layerLabel = layerFilter ? labels[layerFilter] : null;
                  const topicLabel = topicFilter ? topicFilter.replace(/_/g, ' ') : null;
                  if (layerLabel && topicLabel) return `${base} — ${topicLabel} within ${layerLabel}`;
                  if (layerLabel) return `${base} from ${layerLabel}`;
                  return `${base} about ${topicLabel}`;
                })()}
              </div>
            )}
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
          {console.log(`[ProvisionsByTocStructure] filteredProvisions: ${filteredProvisions.length}, selectedPart: ${selectedPart}`)}
          {filteredProvisions.length > 0 && filteredProvisions.some(p => p.v2_marker === 'heritage' && p.pdf_page === 20) && console.log(`[ProvisionsByTocStructure] FOUND page 20 provision:`, { id: filteredProvisions.find(p => p.pdf_page === 20)?.id, pdf_printed_page: filteredProvisions.find(p => p.pdf_page === 20)?.pdf_printed_page })}
          {filteredProvisions.length > 0 ? (
            <PageGroupedProvisions
              provisions={filteredProvisions}
              formerCouncil={formerCouncil}
              showLayerBadges={true}
              maxProvisions={100}
              onViewPdf={(url, page) => setPdfModal({ url, page })}
              highlightQuery={debouncedSearch}
              zone={zone}
              heritage={heritage}
              hcaName={hcaName}
              precinctName={precinctId}
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
