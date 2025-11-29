'use client';

/**
 * Provisions By Topic Component
 * Displays DCP provisions grouped by topic using the 4-layer API
 *
 * Features:
 * - Fetches provisions via /api/provisions/for-property
 * - Groups by topic (setbacks, parking, heritage, etc.)
 * - Shows layer badges (Generic, Zone-Specific, Condition, Precinct)
 * - Expandable provision cards
 */

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, FileText, MapPin, Building, Shield, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { COUNCIL_CONFIGS, TOPIC_LABELS, type CouncilConfig } from '@/lib/council-config';
import { HeritageProvisions } from './HeritageProvisions';
import { FormattedProvisionText } from './FormattedProvisionText';

interface Provision {
  id: number;
  provision_text: string;
  v2_dcp_layer: string;
  v2_dcp_part: string;
  v2_topic: string;
  v2_provision_type: string;
  v2_precinct_id: string;
  v2_marker: string;
  pdf_page: number;
  pdf_page_image_url?: string;
  layer?: string;
  v2_heritage_type?: 'control' | 'character' | 'descriptive';
  v2_heritage_element?: string[];
  v2_heritage_hca?: string;
}

interface LayerResult {
  layer: string;
  layer_name: string;
  provisions: Provision[];
  count: number;
}

interface ProvisionsByTopicProps {
  zone?: string;
  heritage?: boolean;
  flood?: boolean;
  precinctId?: string;
  devType?: string;
  council?: string;  // 'marrickville' | 'leichhardt' | 'ashfield'
  professionalMode?: 'certifier' | 'planner';
}

const TOPIC_ICONS: Record<string, any> = {
  setbacks: Building,
  height: Building,
  parking: MapPin,
  heritage: Shield,
  landscaping: MapPin,
  solar: Building,
  privacy: Shield,
  access: MapPin,
  building_form: Building,
  water: MapPin,
};

// TOPIC_LABELS imported from council-config.ts (has 26 entries)

import { LayerBadges } from '@/lib/design-tokens';

// ... other imports ...

// TOPIC_LABELS imported from council-config.ts (has 26 entries)

const LAYER_COLORS: Record<string, string> = {
  generic: `${LayerBadges.generic.bg} ${LayerBadges.generic.text}`,
  use_specific: `${LayerBadges.use_specific.bg} ${LayerBadges.use_specific.text}`,
  condition: `${LayerBadges.condition.bg} ${LayerBadges.condition.text}`,
  precinct: `${LayerBadges.precinct.bg} ${LayerBadges.precinct.text}`,
};

const LAYER_LABELS: Record<string, string> = {
  generic: 'General',
  use_specific: 'Zone-Specific',
  condition: 'Condition',
  precinct: 'Precinct',
};

/**
 * Granular development types for filtering.
 * Hierarchical structure: selecting a child includes parent provisions.
 */
const DEV_TYPE_OPTIONS = [
  { value: '', label: 'All Development Types' },
  // Dwelling house
  { value: 'dwelling_house', label: 'Dwelling House (any)', group: 'Residential' },
  { value: 'dwelling_house_new', label: '  New Dwelling', group: 'Residential' },
  { value: 'dwelling_addition', label: '  Addition (any)', group: 'Residential' },
  { value: 'dwelling_addition_ground', label: '    Ground Floor Addition', group: 'Residential' },
  { value: 'dwelling_addition_first', label: '    First Floor Addition', group: 'Residential' },
  { value: 'dwelling_addition_rear', label: '    Rear Addition', group: 'Residential' },
  { value: 'dwelling_house_alteration', label: '  Internal Alteration', group: 'Residential' },
  // Secondary dwelling
  { value: 'secondary_dwelling', label: 'Secondary Dwelling (Granny Flat)', group: 'Residential' },
  // Dual occupancy
  { value: 'dual_occupancy', label: 'Dual Occupancy (any)', group: 'Residential' },
  { value: 'dual_occupancy_attached', label: '  Attached Dual Occupancy', group: 'Residential' },
  { value: 'dual_occupancy_detached', label: '  Detached Dual Occupancy', group: 'Residential' },
  // Multi-dwelling
  { value: 'multi_dwelling_housing', label: 'Multi-Dwelling Housing', group: 'Multi-Dwelling' },
  { value: 'residential_flat_building', label: 'Residential Flat Building', group: 'Multi-Dwelling' },
  { value: 'shop_top_housing', label: 'Shop Top Housing', group: 'Multi-Dwelling' },
  { value: 'boarding_house', label: 'Boarding House', group: 'Multi-Dwelling' },
  // Commercial
  { value: 'commercial_premises', label: 'Commercial (any)', group: 'Commercial' },
  { value: 'retail_premises', label: '  Retail Premises', group: 'Commercial' },
  { value: 'office_premises', label: '  Office Premises', group: 'Commercial' },
  { value: 'food_and_drink_premises', label: '  Food & Drink Premises', group: 'Commercial' },
  // Industrial
  { value: 'industrial_development', label: 'Industrial (any)', group: 'Industrial' },
  { value: 'light_industry', label: '  Light Industry', group: 'Industrial' },
  { value: 'warehouse', label: '  Warehouse', group: 'Industrial' },
];

// Use imported COUNCIL_CONFIGS from council-config.ts

export function ProvisionsByTopic({
  zone,
  heritage = false,
  flood = false,
  precinctId,
  devType: initialDevType,
  council,
  professionalMode = 'certifier',
}: ProvisionsByTopicProps) {
  const [data, setData] = useState<{
    by_layer: LayerResult[];
    by_topic: Record<string, Provision[]>;
    summary: any;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());
  const [expandedProvisions, setExpandedProvisions] = useState<Set<number>>(new Set());
  const [selectedDevType, setSelectedDevType] = useState(initialDevType || '');
  const [selectedTopic, setSelectedTopic] = useState<string>('');
  const [viewingPdfImage, setViewingPdfImage] = useState<{ url: string; page: number } | null>(null);

  // Get council config (default to marrickville if unknown)
  const councilConfig: CouncilConfig = council ? COUNCIL_CONFIGS[council] || COUNCIL_CONFIGS.marrickville : COUNCIL_CONFIGS.marrickville;
  const topicOrder = professionalMode === 'certifier' ? councilConfig.topicOrder.certifier : councilConfig.topicOrder.planner;

  useEffect(() => {
    async function fetchProvisions() {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        if (zone) params.set('zone', zone);
        if (heritage) params.set('heritage', 'true');
        if (flood) params.set('flood', 'true');
        if (precinctId) params.set('precinct_id', precinctId);
        if (selectedDevType) params.set('dev_type', selectedDevType);
        if (selectedTopic) params.set('topic', selectedTopic);
        if (council) params.set('former_council', council);

        const response = await fetch(`/api/provisions/for-property?${params}`);
        if (!response.ok) throw new Error('Failed to fetch provisions');

        const result = await response.json();
        if (result.success) {
          setData(result.data);
          // Auto-expand first 3 topics (sorted by council priority)
          const topics = Object.keys(result.data.by_topic || {});
          const sortedTopics = sortTopicsByPriority(topics, topicOrder);
          setExpandedTopics(new Set(sortedTopics.slice(0, 3)));
        } else {
          throw new Error(result.error || 'Unknown error');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchProvisions();
  }, [zone, heritage, flood, precinctId, selectedDevType, selectedTopic, topicOrder]);

  // Sort topics by professional priority
  function sortTopicsByPriority(topics: string[], priorityOrder: string[]): string[] {
    return [...topics].sort((a, b) => {
      const aIndex = priorityOrder.indexOf(a);
      const bIndex = priorityOrder.indexOf(b);
      if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
      if (aIndex !== -1) return -1;
      if (bIndex !== -1) return 1;
      return a.localeCompare(b);
    });
  }

  const toggleTopic = (topic: string) => {
    setExpandedTopics(prev => {
      const next = new Set(prev);
      if (next.has(topic)) {
        next.delete(topic);
      } else {
        next.add(topic);
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

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-red-600">Error: {error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  // Sort topics by council-specific professional priority, not just count
  const topicEntries = Object.entries(data.by_topic || {});
  const sortedTopicNames = sortTopicsByPriority(topicEntries.map(([name]) => name), topicOrder);
  const topics = sortedTopicNames.map(name => {
    const entry = topicEntries.find(([n]) => n === name);
    return entry || [name, []];
  }).filter(([, provisions]) => provisions.length > 0) as [string, Provision[]][];

  return (
    <div className="space-y-4">
      {/* Summary Header with Dev Type Filter */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5" />
              DCP Provisions (4-Layer Filter)
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* DCP Citation and Explanation */}
          {council && (
            <div className="bg-teal-50/50 border border-teal-100 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-teal-600 mt-0.5 flex-shrink-0" />
                <div className="space-y-2">
                  <p className="text-sm font-semibold text-teal-900">
                    {councilConfig.dcpCitation}
                  </p>
                  <p className="text-sm text-gray-700">
                    {councilConfig.dcpExplanation}
                  </p>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600 pt-2">
                    <span className="font-medium text-gray-500">Provisions are filtered into 4 layers:</span>
                    <span className="flex items-center gap-1">
                      <span className="inline-block w-2 h-2 rounded-full bg-slate-400"></span>General (apply to all)
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="inline-block w-2 h-2 rounded-full bg-sky-500"></span>Zone-specific
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="inline-block w-2 h-2 rounded-full bg-amber-500"></span>Site conditions (heritage/flood)
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>Precinct/suburb
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Council-specific guidance for Leichhardt */}
          {council === 'leichhardt' && !selectedTopic && (
            <div className="bg-amber-50 border-l-4 border-amber-400 p-3 rounded-r">
              <p className="text-sm text-amber-800">
                <strong>Tip:</strong> Select a topic below to narrow results.
                Without topic filter, you may see 2,000+ provisions.
              </p>
            </div>
          )}

          {/* Topic Filter - Prominent for Leichhardt */}
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-sm font-medium text-gray-500">Topic:</label>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedTopic('')}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${selectedTopic === ''
                    ? 'bg-teal-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
                  }`}
              >
                All
              </button>
              {councilConfig.suggestedTopics.map((topic) => (
                <button
                  key={topic}
                  onClick={() => setSelectedTopic(topic)}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${selectedTopic === topic
                      ? 'bg-teal-600 text-white'
                      : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
                    }`}
                >
                  {TOPIC_LABELS[topic] || topic}
                </button>
              ))}
            </div>
          </div>

          {/* Filters Row */}
          <div className="flex flex-wrap items-center gap-4">
            {/* Dev Type Selector - only show for councils where dev type filtering is effective */}
            {councilConfig.devTypeFilterEffective ? (
              <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                  Dev Type:
                </label>
                <select
                  value={selectedDevType}
                  onChange={(e) => setSelectedDevType(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Development Types</option>
                  {councilConfig.availableDevTypes?.map((dt) => (
                    <option key={dt.id} value={dt.id}>
                      {dt.name} ({dt.count})
                    </option>
                  )) || DEV_TYPE_OPTIONS.slice(1).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            ) : councilConfig.devTypeNote ? (
              <div className="flex-1 min-w-[200px] text-sm text-amber-800 bg-amber-50 px-3 py-2 rounded-md border border-amber-200">
                {councilConfig.devTypeNote}
              </div>
            ) : null}

          </div>

          {/* Warning if too many results */}
          {data && data.summary?.total_provisions > councilConfig.warningThreshold && !selectedTopic && (
            <div className="bg-amber-50 border border-amber-200 rounded p-2">
              <p className="text-xs text-amber-800">
                <strong>{data.summary.total_provisions} provisions</strong> - Consider selecting a topic above to narrow results
              </p>
            </div>
          )}

          {/* Layer Summary with Legend */}
          <div className="flex flex-wrap gap-2 text-sm">
            <Badge variant="outline">
              Total: {data.summary?.total_provisions || 0}
            </Badge>
            <Badge className={LAYER_COLORS.generic}>
              <span className="inline-block w-2 h-2 rounded-full bg-gray-400 mr-1"></span>
              General: {data.summary?.layer_1_generic || 0}
            </Badge>
            <Badge className={LAYER_COLORS.use_specific}>
              <span className="inline-block w-2 h-2 rounded-full bg-blue-400 mr-1"></span>
              Zone: {data.summary?.layer_2_use_specific || 0}
            </Badge>
            <Badge className={LAYER_COLORS.condition}>
              <span className="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1"></span>
              Condition: {data.summary?.layer_3_condition || 0}
            </Badge>
            <Badge className={LAYER_COLORS.precinct}>
              <span className="inline-block w-2 h-2 rounded-full bg-green-400 mr-1"></span>
              Precinct: {data.summary?.layer_4_precinct || 0}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Topics */}
      {topics.map(([topic, provisions]) => {
        const Icon = TOPIC_ICONS[topic] || FileText;
        const isExpanded = expandedTopics.has(topic);

        // Calculate layer breakdown for this topic
        const layerCounts: Record<string, number> = {};
        provisions.forEach(p => {
          const layer = p.layer || p.v2_dcp_layer || 'unknown';
          layerCounts[layer] = (layerCounts[layer] || 0) + 1;
        });

        return (
          <Card key={topic}>
            <CardHeader
              className="cursor-pointer hover:bg-gray-50 active:bg-gray-100 transition-colors py-4 md:py-3 min-h-[56px] md:min-h-0"
              onClick={() => toggleTopic(topic)}
              role="button"
              aria-expanded={isExpanded}
              aria-controls={`topic-content-${topic}`}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggleTopic(topic);
                }
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="h-5 w-5 md:h-4 md:w-4" />
                  ) : (
                    <ChevronRight className="h-5 w-5 md:h-4 md:w-4" />
                  )}
                  <Icon className="h-5 w-5 md:h-4 md:w-4" />
                  <span className="font-medium text-sm md:text-base">
                    {TOPIC_LABELS[topic] || topic}
                  </span>
                  <Badge variant="secondary" className="ml-2">
                    {provisions.length}
                  </Badge>
                  {/* Layer breakdown badges - hidden on mobile */}
                  <span className="text-xs text-gray-500 ml-2 hidden md:inline">
                    {Object.entries(layerCounts).map(([layer, count]) => (
                      <span key={layer} className="mr-2">
                        <span className={`inline-block w-2 h-2 rounded-full mr-1 ${layer === 'generic' ? 'bg-gray-400' :
                            layer === 'use_specific' ? 'bg-blue-400' :
                              layer === 'condition' ? 'bg-amber-400' :
                                layer === 'precinct' ? 'bg-green-400' : 'bg-gray-300'
                          }`}></span>
                        {count}
                      </span>
                    ))}
                  </span>
                </div>
              </div>
            </CardHeader>

            {isExpanded && (
              <CardContent className="pt-0" id={`topic-content-${topic}`}>
                {topic === 'heritage' && council === 'ashfield' && (
                  <HeritageProvisions provisions={provisions} />
                )}
                {!(topic === 'heritage' && council === 'ashfield') && (
                  <div className="space-y-2">
                    {(() => {
                      // Group provisions by PDF page (extract from image URL as source of truth)
                      const groupedByPage: { [page: number]: Provision[] } = {};
                      const provisionsWithoutPage: Provision[] = [];

                      provisions.slice(0, 20).forEach(prov => {
                        // Use pdf_page field (corrected for offset) as primary source
                        let pageNum: number | null = null;
                        if (prov.pdf_page) {
                          pageNum = prov.pdf_page;
                        }
                        // Fallback to URL only if pdf_page is missing
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

                      // Sort page groups by page number
                      const sortedPageGroups = Object.entries(groupedByPage)
                        .sort(([pageA], [pageB]) => parseInt(pageA) - parseInt(pageB));

                      return (
                        <>
                          {sortedPageGroups.map(([pageNumStr, pageProvisions], groupIdx) => {
                            const pdfUrl = pageProvisions[0]?.pdf_page_image_url;
                            const pdfPage = parseInt(pageNumStr); // Already extracted from URL in grouping logic

                            return (
                              <div key={`page-${pdfPage}`} className={groupIdx > 0 ? 'border-t pt-2' : ''}>
                                {/* Provisions in this page group */}
                                {pageProvisions.map((provision) => (
                                  <div
                                    key={provision.id}
                                    className="border rounded-lg p-3 hover:bg-gray-50 mb-2"
                                  >
                                    <div className="flex items-start justify-between gap-2">
                                      <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                          <Badge className={LAYER_COLORS[provision.layer || provision.v2_dcp_layer] || 'bg-gray-100'}>
                                            {LAYER_LABELS[provision.layer || provision.v2_dcp_layer] || provision.v2_dcp_layer}
                                          </Badge>
                                          {provision.v2_dcp_part && (
                                            <Badge variant="outline" className="text-xs">
                                              {provision.v2_dcp_part}
                                            </Badge>
                                          )}
                                          {provision.v2_marker && (
                                            <Badge variant="outline" className="text-xs bg-purple-50">
                                              {provision.v2_marker}
                                            </Badge>
                                          )}
                                        </div>
                                        <div
                                          className={`text-sm cursor-pointer ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-3'}`}
                                          onClick={() => toggleProvision(provision.id)}
                                        >
                                          <FormattedProvisionText text={provision.provision_text} compact />
                                        </div>
                                        {provision.provision_text.length > 150 && (
                                          <button
                                            className="text-xs md:text-xs text-blue-600 mt-2 py-2 px-3 -ml-3 min-h-[44px] flex items-center hover:bg-blue-50 rounded transition-colors"
                                            onClick={() => toggleProvision(provision.id)}
                                          >
                                            {expandedProvisions.has(provision.id) ? 'Show less' : 'Show more'}
                                          </button>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                ))}

                                {/* PDF Page Button - after all provisions from this page */}
                                {pdfPage && pdfUrl && (
                                  <div className="flex justify-end mt-1 mb-3">
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-300"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setViewingPdfImage({ url: pdfUrl, page: pdfPage });
                                      }}
                                    >
                                      <FileText className="h-3 w-3 mr-1" />
                                      View PDF page {pdfPage}
                                    </Button>
                                  </div>
                                )}
                              </div>
                            );
                          })}

                          {/* Provisions without page numbers */}
                          {provisionsWithoutPage.map((provision) => (
                            <div
                              key={provision.id}
                              className="border rounded-lg p-3 hover:bg-gray-50"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <Badge className={LAYER_COLORS[provision.layer || provision.v2_dcp_layer] || 'bg-gray-100'}>
                                      {LAYER_LABELS[provision.layer || provision.v2_dcp_layer] || provision.v2_dcp_layer}
                                    </Badge>
                                    {provision.v2_dcp_part && (
                                      <Badge variant="outline" className="text-xs">
                                        {provision.v2_dcp_part}
                                      </Badge>
                                    )}
                                  </div>
                                  <FormattedProvisionText text={provision.provision_text} compact />
                                </div>
                              </div>
                            </div>
                          ))}
                        </>
                      );
                    })()}

                    {provisions.length > 20 && (
                      <p className="text-sm text-gray-500 text-center py-2">
                        Showing 20 of {provisions.length} provisions
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        );
      })}

      {/* PDF Page Viewer Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        imageUrl={viewingPdfImage?.url}
        pageNumber={viewingPdfImage?.page}
      />
    </div>
  );
}
