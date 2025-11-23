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
import { ChevronDown, ChevronRight, FileText, MapPin, Building, Shield } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

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
  layer?: string;
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
  assessmentType?: 'CDC' | 'DA';
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

const TOPIC_LABELS: Record<string, string> = {
  setbacks: 'Setbacks',
  height: 'Height & Envelope',
  parking: 'Parking',
  heritage: 'Heritage',
  landscaping: 'Landscaping',
  solar: 'Solar Access',
  privacy: 'Privacy',
  access: 'Access & Movement',
  building_form: 'Building Form',
  water: 'Water Management',
  food_premises: 'Food Premises',
  unknown: 'Other Requirements',
};

const LAYER_COLORS: Record<string, string> = {
  generic: 'bg-gray-100 text-gray-800',
  use_specific: 'bg-blue-100 text-blue-800',
  condition: 'bg-amber-100 text-amber-800',
  precinct: 'bg-green-100 text-green-800',
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

export function ProvisionsByTopic({
  zone,
  heritage = false,
  flood = false,
  precinctId,
  devType: initialDevType,
  assessmentType: initialAssessmentType,
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
  const [selectedAssessmentType, setSelectedAssessmentType] = useState<'CDC' | 'DA' | ''>(initialAssessmentType || '');

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
        if (selectedAssessmentType) params.set('assessment_type', selectedAssessmentType);

        const response = await fetch(`/api/provisions/for-property?${params}`);
        if (!response.ok) throw new Error('Failed to fetch provisions');

        const result = await response.json();
        if (result.success) {
          setData(result.data);
          // Auto-expand first 3 topics
          const topics = Object.keys(result.data.by_topic || {}).slice(0, 3);
          setExpandedTopics(new Set(topics));
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
  }, [zone, heritage, flood, precinctId, selectedDevType, selectedAssessmentType]);

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

  const topics = Object.entries(data.by_topic || {}).sort((a, b) => b[1].length - a[1].length);

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
          {/* Filters Row */}
          <div className="flex flex-wrap items-center gap-4">
            {/* Dev Type Selector */}
            <div className="flex items-center gap-2 flex-1 min-w-[200px]">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                Dev Type:
              </label>
              <select
                value={selectedDevType}
                onChange={(e) => setSelectedDevType(e.target.value)}
                className="flex-1 px-3 py-1.5 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {DEV_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Assessment Type Toggle */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                Assessment:
              </label>
              <div className="flex rounded-md border overflow-hidden">
                <button
                  onClick={() => setSelectedAssessmentType('')}
                  className={`px-3 py-1.5 text-sm transition-colors ${
                    selectedAssessmentType === ''
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setSelectedAssessmentType('DA')}
                  className={`px-3 py-1.5 text-sm border-l transition-colors ${
                    selectedAssessmentType === 'DA'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                  title="Development Application - All provisions"
                >
                  DA
                </button>
                <button
                  onClick={() => setSelectedAssessmentType('CDC')}
                  className={`px-3 py-1.5 text-sm border-l transition-colors ${
                    selectedAssessmentType === 'CDC'
                      ? 'bg-green-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                  title="Complying Development Certificate - Quantitative only"
                >
                  CDC
                </button>
              </div>
            </div>
          </div>
          {selectedAssessmentType === 'CDC' && (
            <p className="text-xs text-green-700 bg-green-50 px-2 py-1 rounded">
              CDC mode: Showing only quantitative, checkable controls
            </p>
          )}

          {/* Layer Summary */}
          <div className="flex flex-wrap gap-2 text-sm">
            <Badge variant="outline">
              Total: {data.summary?.total_provisions || 0}
            </Badge>
            <Badge className={LAYER_COLORS.generic}>
              General: {data.summary?.layer_1_generic || 0}
            </Badge>
            <Badge className={LAYER_COLORS.use_specific}>
              Zone: {data.summary?.layer_2_use_specific || 0}
            </Badge>
            <Badge className={LAYER_COLORS.condition}>
              Condition: {data.summary?.layer_3_condition || 0}
            </Badge>
            <Badge className={LAYER_COLORS.precinct}>
              Precinct: {data.summary?.layer_4_precinct || 0}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Topics */}
      {topics.map(([topic, provisions]) => {
        const Icon = TOPIC_ICONS[topic] || FileText;
        const isExpanded = expandedTopics.has(topic);

        return (
          <Card key={topic}>
            <CardHeader
              className="cursor-pointer hover:bg-gray-50 transition-colors py-3"
              onClick={() => toggleTopic(topic)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  <Icon className="h-4 w-4" />
                  <span className="font-medium">
                    {TOPIC_LABELS[topic] || topic}
                  </span>
                  <Badge variant="secondary" className="ml-2">
                    {provisions.length}
                  </Badge>
                </div>
              </div>
            </CardHeader>

            {isExpanded && (
              <CardContent className="pt-0">
                <div className="space-y-2">
                  {provisions.slice(0, 20).map((provision) => (
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
                            {provision.v2_marker && (
                              <Badge variant="outline" className="text-xs bg-purple-50">
                                {provision.v2_marker}
                              </Badge>
                            )}
                          </div>
                          <p
                            className={`text-sm ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-2'}`}
                            onClick={() => toggleProvision(provision.id)}
                          >
                            {provision.provision_text}
                          </p>
                          {provision.provision_text.length > 150 && (
                            <button
                              className="text-xs text-blue-600 mt-1"
                              onClick={() => toggleProvision(provision.id)}
                            >
                              {expandedProvisions.has(provision.id) ? 'Show less' : 'Show more'}
                            </button>
                          )}
                        </div>
                        {provision.pdf_page && (
                          <Badge variant="outline" className="text-xs shrink-0">
                            p.{provision.pdf_page}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                  {provisions.length > 20 && (
                    <p className="text-sm text-gray-500 text-center py-2">
                      Showing 20 of {provisions.length} provisions
                    </p>
                  )}
                </div>
              </CardContent>
            )}
          </Card>
        );
      })}
    </div>
  );
}
