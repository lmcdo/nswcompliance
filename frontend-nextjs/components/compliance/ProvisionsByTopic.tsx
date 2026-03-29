'use client';

/**
 * Provisions By Topic Component
 * Displays DCP provisions grouped by topic using the 4-layer API.
 * State management: useProvisionBrowser hook
 * Heritage rendering: HeritageTopicContent
 * Non-heritage DCP part rendering: DcpPartTopicContent
 */

import { ChevronDown, ChevronRight, FileText, MapPin, Building, Shield, Info, HelpCircle } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { TOPIC_LABELS, INNER_WEST_OVERVIEW } from '@/lib/council-config';
import { PageGroupedProvisions } from './PageGroupedProvisions';
import { LayerBadges } from '@/lib/design-tokens';
import { LayerExplanation } from './LayerExplanation';
import { groupByDcpPart } from '@/lib/provision-grouping';
import { useProvisionBrowser } from '@/hooks/useProvisionBrowser';
import { HeritageTopicContent } from './HeritageTopicContent';
import { DcpPartTopicContent } from './DcpPartTopicContent';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TOPIC_ICONS: Record<string, any> = {
  setbacks: Building, height: Building, parking: MapPin, heritage: Shield,
  landscaping: MapPin, solar: Building, privacy: Shield, access: MapPin,
  building_form: Building, water: MapPin,
};

const DEV_TYPE_OPTIONS = [
  { value: '', label: 'All Development Types' },
  { value: 'dwelling_house', label: 'Dwelling House (any)', group: 'Residential' },
  { value: 'dwelling_house_new', label: '  New Dwelling', group: 'Residential' },
  { value: 'dwelling_addition', label: '  Addition (any)', group: 'Residential' },
  { value: 'dwelling_addition_ground', label: '    Ground Floor Addition', group: 'Residential' },
  { value: 'dwelling_addition_first', label: '    First Floor Addition', group: 'Residential' },
  { value: 'dwelling_addition_rear', label: '    Rear Addition', group: 'Residential' },
  { value: 'dwelling_house_alteration', label: '  Internal Alteration', group: 'Residential' },
  { value: 'secondary_dwelling', label: 'Secondary Dwelling (Granny Flat)', group: 'Residential' },
  { value: 'dual_occupancy', label: 'Dual Occupancy (any)', group: 'Residential' },
  { value: 'dual_occupancy_attached', label: '  Attached Dual Occupancy', group: 'Residential' },
  { value: 'dual_occupancy_detached', label: '  Detached Dual Occupancy', group: 'Residential' },
  { value: 'multi_dwelling_housing', label: 'Multi-Dwelling Housing', group: 'Multi-Dwelling' },
  { value: 'residential_flat_building', label: 'Residential Flat Building', group: 'Multi-Dwelling' },
  { value: 'shop_top_housing', label: 'Shop Top Housing', group: 'Multi-Dwelling' },
  { value: 'boarding_house', label: 'Boarding House', group: 'Multi-Dwelling' },
  { value: 'commercial_premises', label: 'Commercial (any)', group: 'Commercial' },
  { value: 'retail_premises', label: '  Retail Premises', group: 'Commercial' },
  { value: 'office_premises', label: '  Office Premises', group: 'Commercial' },
  { value: 'food_and_drink_premises', label: '  Food & Drink Premises', group: 'Commercial' },
  { value: 'industrial_development', label: 'Industrial (any)', group: 'Industrial' },
  { value: 'light_industry', label: '  Light Industry', group: 'Industrial' },
  { value: 'warehouse', label: '  Warehouse', group: 'Industrial' },
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ProvisionsByTopicProps {
  zone?: string;
  heritage?: boolean;
  flood?: boolean;
  precinctId?: string;
  devType?: string;
  council?: string;
  professionalMode?: 'certifier' | 'planner';
  hcaName?: string;
  heritageItemNumber?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ProvisionsByTopic({
  zone, heritage = false, flood = false, precinctId,
  devType: initialDevType, council, professionalMode = 'certifier',
  hcaName, heritageItemNumber,
}: ProvisionsByTopicProps) {

  const browser = useProvisionBrowser({
    zone, heritage, flood, precinctId,
    selectedDevType: initialDevType ?? '',
    council, hcaName, heritageItemNumber, professionalMode,
  });

  const {
    data, isLoading, error,
    originalTopicCounts, showPdfButtonIds, propertyHcaSlug, topics,
    councilConfig,
    selectedDevType, setSelectedDevType,
    selectedTopic, setSelectedTopic,
    expandedTopics, expandedProvisions, expandedDcpParts,
    expandedHcas, expandedHeritageTypes, showAllHeritageTypes, elementFilters,
    viewingPdfImage, setViewingPdfImage,
    showInnerWestOverview, setShowInnerWestOverview,
    toggleTopic, toggleProvision, toggleDcpPart,
    toggleHca, toggleHeritageType, toggleShowAllHeritageType, setElementFilter,
    formatDcpPart,
    DCP_PART_GROUPING_THRESHOLD, HCA_GROUPING_THRESHOLD,
  } = browser;

  if (isLoading) {
    return (
      <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading DCP provisions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-red-600">Error: {error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading DCP provisions...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Inner West Overview - Collapsible */}
      {council && (
        <button
          onClick={() => setShowInnerWestOverview(!showInnerWestOverview)}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-50 rounded-lg transition-colors"
        >
          {showInnerWestOverview ? <ChevronDown className="h-4 w-4 flex-shrink-0" /> : <ChevronRight className="h-4 w-4 flex-shrink-0" />}
          <HelpCircle className="h-4 w-4" />
          <span className="flex-1">About Inner West DCPs</span>
        </button>
      )}
      {showInnerWestOverview && (
        <Card className="bg-slate-50 border-slate-200">
          <CardContent className="p-4">
            <p className="text-sm text-slate-700 whitespace-pre-line">{INNER_WEST_OVERVIEW}</p>
          </CardContent>
        </Card>
      )}

      {/* Compact Header Card */}
      <Card className="overflow-hidden">
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
          {councilConfig?.dcpExplanation && (
            <div className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
              {councilConfig.dcpExplanation.split(/(\[[^\]]+\])/).map((part: string, i: number) => {
                const match = part.match(/^\[(.+)\]$/);
                if (match) {
                  const term = match[1];
                  const colorClass =
                    term === 'Base Controls' || term === 'Universal' ? 'bg-slate-100 text-slate-700' :
                    term === 'Zone Controls' ? 'bg-sky-100 text-sky-700' :
                    term === 'Heritage' ? 'bg-amber-100 text-amber-700' :
                    term === 'Precinct Character' || term === 'Village Precinct' || term === 'Distinct Neighbourhood' ? 'bg-purple-100 text-purple-700' :
                    'bg-gray-100 text-gray-700';
                  return <span key={i} className={`${colorClass} px-1.5 py-0.5 rounded text-xs font-medium`}>{term}</span>;
                }
                return <span key={i}>{part}</span>;
              })}
            </div>
          )}

          {/* Topic filter pills */}
          <div className="space-y-2">
            <p className="text-xs text-slate-600">Choose topics to filter provisions for this address:</p>
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setSelectedTopic('')}
                className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${
                  selectedTopic === '' ? 'bg-slate-800 text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                All Topics
              </button>
              {Object.entries(originalTopicCounts)
                .sort((a, b) => b[1] - a[1])
                .map(([topic, count]) => (
                  <button
                    key={topic}
                    onClick={() => setSelectedTopic(topic)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${
                      selectedTopic === topic ? 'bg-slate-800 text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {TOPIC_LABELS[topic] || topic} ({count})
                  </button>
                ))}
            </div>
          </div>

          {/* Dev type selector */}
          {councilConfig?.devTypeFilterEffective ? (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <label className="block text-xs font-semibold text-blue-800 mb-1.5">Development Type</label>
              <select
                value={selectedDevType}
                onChange={(e) => setSelectedDevType(e.target.value)}
                className="w-full px-3 py-2 text-sm border-2 border-blue-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium"
              >
                <option value="">Select development type...</option>
                {councilConfig.availableDevTypes?.map((dt: any) => (
                  <option key={dt.id} value={dt.id}>{dt.name} ({dt.count} provisions)</option>
                )) || DEV_TYPE_OPTIONS.slice(1).map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          ) : councilConfig?.devTypeNote && (
            <p className="text-xs text-slate-500 italic">{councilConfig.devTypeNote}</p>
          )}

          {/* Warning banner */}
          {data && councilConfig && data.summary?.total_provisions > councilConfig.warningThreshold && !selectedTopic && (
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

        const layerCounts: Record<string, number> = {};
        provisions.forEach(p => {
          const layer = p.layer || p.v2_dcp_layer || 'unknown';
          layerCounts[layer] = (layerCounts[layer] || 0) + 1;
        });

        return (
          <Card key={topic}>
            <CardHeader
              className="cursor-pointer hover:bg-gray-50 active:bg-gray-100 transition-colors py-2 px-3"
              onClick={() => toggleTopic(topic)}
              role="button"
              aria-expanded={isExpanded}
              aria-controls={`topic-content-${topic}`}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleTopic(topic); }
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  <Icon className="h-4 w-4" />
                  <span className="font-medium text-sm">{TOPIC_LABELS[topic] || topic}</span>
                  <Badge variant="secondary" className="ml-2">{provisions.length}</Badge>
                  <span className="text-xs text-gray-500 ml-2 hidden md:inline">
                    {Object.entries(layerCounts).map(([layer, count]) => (
                      <span key={layer} className="mr-2">
                        <span className={`inline-block w-2 h-2 rounded-full mr-1 ${
                          layer === 'generic' ? 'bg-slate-500' :
                          layer === 'use_specific' ? 'bg-sky-500' :
                          layer === 'condition' ? 'bg-amber-500' :
                          layer === 'precinct' ? 'bg-purple-500' : 'bg-gray-300'
                        }`}></span>
                        {count}
                      </span>
                    ))}
                  </span>
                  {topic.toLowerCase() === 'building_form' && (() => {
                    const controlCount = provisions.filter(p => p.v2_heritage_type === 'control').length;
                    const guidanceCount = provisions.filter(p => p.v2_heritage_type === 'guidance').length;
                    if (controlCount > 0 || guidanceCount > 0) {
                      return (
                        <span className="text-xs text-gray-600 ml-2 hidden md:inline">
                          {controlCount > 0 && <span className="text-teal-700 font-medium">{controlCount} controls</span>}
                          {controlCount > 0 && guidanceCount > 0 && <span className="mx-1">·</span>}
                          {guidanceCount > 0 && <span className="text-blue-700">{guidanceCount} guidance</span>}
                        </span>
                      );
                    }
                    return null;
                  })()}
                </div>
              </div>
            </CardHeader>

            {isExpanded && (
              <CardContent className="pt-0" id={`topic-content-${topic}`}>
                <div className="space-y-2">
                  {(provisions.length > DCP_PART_GROUPING_THRESHOLD || topic.toLowerCase() === 'building_form') ? (
                    // Large topic or Building Form: group by DCP Part
                    <div className="space-y-2">
                      {Array.from(groupByDcpPart(provisions, topic)).map(([dcpPart, partProvisions]) => {
                        const partKey = `${topic}-${dcpPart}`;
                        const isPartExpanded = expandedDcpParts.has(partKey);

                        return (
                          <div key={partKey} className="border border-gray-200 rounded-lg overflow-hidden">
                            <button
                              onClick={() => toggleDcpPart(partKey)}
                              className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 hover:bg-slate-100 transition-colors"
                            >
                              <div className="flex items-center gap-2">
                                {isPartExpanded
                                  ? <ChevronDown className="h-4 w-4 text-slate-500" />
                                  : <ChevronRight className="h-4 w-4 text-slate-500" />
                                }
                                <span className="font-medium text-sm text-slate-700">{formatDcpPart(dcpPart)}</span>
                                <Badge variant="secondary" className="text-xs">{partProvisions.length}</Badge>
                              </div>
                            </button>

                            {isPartExpanded && (
                              <div className="p-2 space-y-2 bg-white">
                                {topic.toLowerCase() === 'heritage' && partProvisions.length > HCA_GROUPING_THRESHOLD ? (
                                  <HeritageTopicContent
                                    partProvisions={partProvisions}
                                    partKey={partKey}
                                    propertyHcaSlug={propertyHcaSlug}
                                    expandedHcas={expandedHcas}
                                    expandedHeritageTypes={expandedHeritageTypes}
                                    showAllHeritageTypes={showAllHeritageTypes}
                                    elementFilters={elementFilters}
                                    expandedProvisions={expandedProvisions}
                                    toggleHca={toggleHca}
                                    toggleHeritageType={toggleHeritageType}
                                    toggleShowAllHeritageType={toggleShowAllHeritageType}
                                    setElementFilter={setElementFilter}
                                    toggleProvision={toggleProvision}
                                    setViewingPdfImage={setViewingPdfImage}
                                    zone={zone}
                                    heritage={heritage}
                                    hcaName={hcaName}
                                    precinctId={precinctId}
                                  />
                                ) : (
                                  <DcpPartTopicContent
                                    partProvisions={partProvisions}
                                    topic={topic}
                                    partFilterKey={`part-${partKey}`}
                                    expandedProvisions={expandedProvisions}
                                    elementFilters={elementFilters}
                                    showPdfButtonIds={showPdfButtonIds}
                                    council={council}
                                    zone={zone}
                                    heritage={heritage}
                                    hcaName={hcaName}
                                    precinctId={precinctId}
                                    toggleProvision={toggleProvision}
                                    setElementFilter={setElementFilter}
                                    setViewingPdfImage={setViewingPdfImage}
                                  />
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    // Small topic: flat provision list
                    <PageGroupedProvisions
                      provisionTheme="green"
                      provisions={provisions}
                      expandedProvisions={expandedProvisions}
                      onToggleProvision={toggleProvision}
                      onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                      showDcpPart={true}
                      maxProvisions={20}
                      zone={zone}
                      heritage={heritage}
                      hcaName={hcaName}
                      precinctName={precinctId}
                    />
                  )}
                </div>
              </CardContent>
            )}
          </Card>
        );
      })}

      <PdfImageModal
        isOpen={!!viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        imageUrl={viewingPdfImage?.url}
        pageNumber={viewingPdfImage?.page}
      />
    </div>
  );
}
