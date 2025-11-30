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
import { ChevronDown, ChevronRight, FileText, MapPin, Building, Shield, Info, HelpCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { COUNCIL_CONFIGS, TOPIC_LABELS, INNER_WEST_OVERVIEW, type CouncilConfig } from '@/lib/council-config';
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
  const [showInnerWestOverview, setShowInnerWestOverview] = useState(false);

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
      {/* Inner West Overview - Collapsible */}
      {council && (
        <button
          onClick={() => setShowInnerWestOverview(!showInnerWestOverview)}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-50 rounded-lg transition-colors"
        >
          <HelpCircle className="h-4 w-4" />
          <span>About Inner West DCPs</span>
          {showInnerWestOverview ? <ChevronDown className="h-4 w-4 ml-auto" /> : <ChevronRight className="h-4 w-4 ml-auto" />}
        </button>
      )}
      {showInnerWestOverview && (
        <Card className="bg-slate-50 border-slate-200">
          <CardContent className="p-4">
            <p className="text-sm text-slate-700 whitespace-pre-line">{INNER_WEST_OVERVIEW}</p>
          </CardContent>
        </Card>
      )}

      {/* Compact Header */}
      <Card className="overflow-hidden">
        {/* DCP Title Bar */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-white" />
              <span className="font-semibold text-white text-sm">
                {councilConfig?.dcpCitation || 'Development Control Plan'}
              </span>
            </div>
            <Badge variant="outline" className="bg-white/10 text-white border-white/20 text-xs">
              {data.summary?.total_provisions || 0} provisions
            </Badge>
          </div>
        </div>

        <CardContent className="p-4 space-y-4">
          {/* DCP Explanation - Clean Typography */}
          {council && councilConfig.dcpExplanation && (
            <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
              {councilConfig.dcpExplanation}
            </p>
          )}

          {/* Dev Type Prompt for Ashfield */}
          {council === 'ashfield' && (
            <p className="text-sm font-medium text-blue-700 mt-2">
              Select your development type below to filter relevant provisions.
            </p>
          )}

          {/* Layer Summary - Compact Inline with meaningful labels */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-slate-100 text-slate-600 rounded">
              <span className="font-semibold">{data.summary?.layer_1_generic || 0}</span> General
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-sky-100 text-sky-700 rounded">
              <span className="font-semibold">{data.summary?.layer_2_use_specific || 0}</span> Zone
            </span>
            {(data.summary?.layer_3_condition || 0) > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-700 rounded">
                <span className="font-semibold">{data.summary?.layer_3_condition}</span> Site Conditions
              </span>
            )}
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-100 text-emerald-700 rounded">
              <span className="font-semibold">{data.summary?.layer_4_precinct || 0}</span> Precinct
            </span>
          </div>

          {/* Topic Filter Pills */}
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setSelectedTopic('')}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${selectedTopic === ''
                  ? 'bg-slate-800 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
            >
              All Topics
            </button>
            {councilConfig.suggestedTopics.map((topic) => (
              <button
                key={topic}
                onClick={() => setSelectedTopic(topic)}
                className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${selectedTopic === topic
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
              >
                {TOPIC_LABELS[topic] || topic}
              </button>
            ))}
          </div>

          {/* Dev Type selector or note */}
          {councilConfig.devTypeFilterEffective ? (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <label className="block text-xs font-semibold text-blue-800 mb-1.5">
                Development Type
              </label>
              <select
                value={selectedDevType}
                onChange={(e) => setSelectedDevType(e.target.value)}
                className="w-full px-3 py-2 text-sm border-2 border-blue-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium"
              >
                <option value="">Select development type...</option>
                {councilConfig.availableDevTypes?.map((dt) => (
                  <option key={dt.id} value={dt.id}>
                    {dt.name} ({dt.count} provisions)
                  </option>
                )) || DEV_TYPE_OPTIONS.slice(1).map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          ) : councilConfig.devTypeNote && (
            <p className="text-xs text-slate-500 italic">
              {councilConfig.devTypeNote}
            </p>
          )}

          {/* Warning banner - only if needed */}
          {data && data.summary?.total_provisions > councilConfig.warningThreshold && !selectedTopic && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              <Info className="h-4 w-4 text-amber-600 flex-shrink-0" />
              <p className="text-xs text-amber-800">
                <strong>{data.summary.total_provisions} provisions</strong> — Select a topic to narrow results
              </p>
            </div>
          )}
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
                        <span className={`inline-block w-2 h-2 rounded-full mr-1 ${layer === 'generic' ? 'bg-slate-500' :
                            layer === 'use_specific' ? 'bg-sky-500' :
                              layer === 'condition' ? 'bg-amber-500' :
                                layer === 'precinct' ? 'bg-emerald-500' : 'bg-gray-300'
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

                      // Flatten all provisions for cleaner rendering
                      const allProvisions = [
                        ...sortedPageGroups.flatMap(([, provs]) => provs),
                        ...provisionsWithoutPage
                      ];

                      return (
                        <div className="space-y-2">
                          {allProvisions.map((provision) => {
                            const layer = provision.layer || provision.v2_dcp_layer;
                            const layerBorderColor = layer === 'generic' ? 'border-l-slate-400' :
                              layer === 'use_specific' ? 'border-l-sky-400' :
                              layer === 'condition' ? 'border-l-amber-400' :
                              layer === 'precinct' ? 'border-l-emerald-400' : 'border-l-gray-300';

                            return (
                              <div
                                key={provision.id}
                                className={`bg-white border border-gray-200 rounded-lg overflow-hidden transition-all hover:shadow-md ${layerBorderColor} border-l-4`}
                              >
                                {/* Card Header */}
                                <div className="flex items-center justify-between px-4 py-2 bg-gray-50/50 border-b border-gray-100">
                                  <div className="flex items-center gap-2">
                                    {provision.v2_marker && (
                                      <span className="font-mono text-sm font-semibold text-slate-700">
                                        {provision.v2_marker}
                                      </span>
                                    )}
                                    <Badge className={`text-[10px] ${LAYER_COLORS[layer] || 'bg-gray-100'}`}>
                                      {LAYER_LABELS[layer] || layer}
                                    </Badge>
                                    {provision.v2_dcp_part && (
                                      <span className="text-xs text-gray-500">{provision.v2_dcp_part}</span>
                                    )}
                                  </div>
                                  {provision.pdf_page_image_url && (() => {
                                    const pageNum = provision.pdf_page || parseInt(provision.pdf_page_image_url!.match(/page_(\d+)/)?.[1] || '0');
                                    return (
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-7 px-2 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          setViewingPdfImage({
                                            url: provision.pdf_page_image_url!,
                                            page: pageNum
                                          });
                                        }}
                                      >
                                        <FileText className="h-3 w-3 mr-1" />
                                        View PDF Page {pageNum}
                                      </Button>
                                    );
                                  })()}
                                </div>

                                {/* Card Content */}
                                <div className="px-4 py-3">
                                  <div
                                    className={`text-sm text-gray-700 leading-relaxed cursor-pointer ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-3'}`}
                                    onClick={() => toggleProvision(provision.id)}
                                  >
                                    <FormattedProvisionText text={provision.provision_text} compact />
                                  </div>
                                  {provision.provision_text.length > 150 && (
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
                          })}
                        </div>
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
