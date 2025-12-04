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

import { useState, useEffect, useMemo } from 'react';
import useSWR from 'swr';
import { ChevronDown, ChevronRight, FileText, MapPin, Building, Shield, Info, HelpCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { COUNCIL_CONFIGS, TOPIC_LABELS, INNER_WEST_OVERVIEW, type CouncilConfig } from '@/lib/council-config';
// HeritageProvisions removed - using v2_dcp_part + v2_heritage_hca grouping instead
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
  hcaName?: string;  // Property's HCA name for filtering (e.g., "Summer Hill Central Heritage Conservation Area")
  heritageItemNumber?: string;  // Heritage item number from Planning Portal (e.g., "HCA 26", "C26")
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

// Descriptive labels for DCP parts by council
const DCP_PART_LABELS: Record<string, Record<string, string>> = {
  ashfield: {
    'Chapter A': 'Chapter A – Introduction & General',
    'Chapter C': 'Chapter C – Sustainability',
    'Chapter D': 'Chapter D – Village Precincts',
    'Chapter E1': 'Chapter E1 – Heritage',
    'Chapter F': 'Chapter F – Development Types',
  },
  marrickville: {
    'Part 2': 'Part 2 – Signs & Advertising',
    'Part 4.1': 'Part 4.1 – R2 Low Density',
    'Part 4.2': 'Part 4.2 – R3/R4 Medium Density',
    'Part 5': 'Part 5 – Business Zones',
    'Part 6': 'Part 6 – Industrial Zones',
    'Part 8': 'Part 8 – Heritage',
    'Part 9': 'Part 9 – Suburb Precincts',
  },
  leichhardt: {
    'Part C Section 1': 'Part C.1 – Place Controls',
    'Part C Section 2': 'Part C.2 – Specific Areas',
    'Part D': 'Part D – Energy',
    'Part E': 'Part E – Water',
    'Part F': 'Part F – Food Premises',
    'Part G': 'Part G – Neighbourhoods',
  },
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

// SWR fetcher with error handling
const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch provisions');
  const json = await res.json();
  if (!json.success) throw new Error(json.error || 'Unknown error');
  return json.data;
};

/**
 * Convert HCA name to slug format for matching against v2_heritage_hca in database.
 * Examples:
 * - "Summer Hill Central Heritage Conservation Area" → "summer_hill"
 * - "Ashfield Heights Heritage Conservation Area" → "ashfield_heights"
 * - "Queen Street" → "queen_street"
 * - "HCA 26" → "hca_26"
 * - "C26" → "hca_26"
 */
function hcaNameToSlug(hcaName: string): string {
  if (!hcaName) return '';
  // Already in hca_XX format
  if (/^hca_\d+$/i.test(hcaName)) {
    return hcaName.toLowerCase();
  }
  // Handle "HCA 26" or "HCA26" format
  const hcaMatch = hcaName.match(/^hca\s*(\d+)$/i);
  if (hcaMatch) {
    return `hca_${hcaMatch[1]}`;
  }
  // Handle "C26" format (common shorthand)
  const cMatch = hcaName.match(/^c(\d+)$/i);
  if (cMatch) {
    return `hca_${cMatch[1]}`;
  }
  // Remove common suffixes and convert to slug
  let slug = hcaName
    .replace(/heritage conservation area/gi, '')
    .replace(/conservation area/gi, '')
    .replace(/heritage area/gi, '')
    .replace(/central|north|south|east|west/gi, '')
    .trim();
  // Convert to snake_case
  slug = slug.toLowerCase().replace(/\s+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
  return slug;
}

/**
 * Convert heritageItemNumber (e.g., "HCA 26", "C26") to database format "hca_26"
 */
function heritageItemNumberToSlug(itemNumber: string): string {
  if (!itemNumber) return '';
  // Already in hca_XX format
  if (/^hca_\d+$/i.test(itemNumber)) {
    return itemNumber.toLowerCase();
  }
  // Handle "HCA 26" or "HCA26" format
  const hcaMatch = itemNumber.match(/hca\s*(\d+)/i);
  if (hcaMatch) {
    return `hca_${hcaMatch[1]}`;
  }
  // Handle "C26" format
  const cMatch = itemNumber.match(/^c(\d+)$/i);
  if (cMatch) {
    return `hca_${cMatch[1]}`;
  }
  // Handle just a number like "26"
  const numMatch = itemNumber.match(/^(\d+)$/);
  if (numMatch) {
    return `hca_${numMatch[1]}`;
  }
  return '';
}

export function ProvisionsByTopic({
  zone,
  heritage = false,
  flood = false,
  precinctId,
  devType: initialDevType,
  council,
  professionalMode = 'certifier',
  hcaName,
  heritageItemNumber,
}: ProvisionsByTopicProps) {
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());
  const [expandedProvisions, setExpandedProvisions] = useState<Set<number>>(new Set());
  const [expandedDcpParts, setExpandedDcpParts] = useState<Set<string>>(new Set());
  const [expandedHcas, setExpandedHcas] = useState<Set<string>>(new Set());
  const [selectedDevType, setSelectedDevType] = useState(initialDevType || '');

  // Threshold for showing DCP part sub-grouping
  const DCP_PART_GROUPING_THRESHOLD = 50;
  // Threshold for showing HCA sub-grouping within heritage DCP parts
  const HCA_GROUPING_THRESHOLD = 100;
  const [selectedTopic, setSelectedTopic] = useState<string>('');
  const [viewingPdfImage, setViewingPdfImage] = useState<{ url: string; page: number } | null>(null);
  const [showInnerWestOverview, setShowInnerWestOverview] = useState(false);

  // Get council config (default to marrickville if unknown)
  const councilConfig: CouncilConfig = council ? COUNCIL_CONFIGS[council] || COUNCIL_CONFIGS.marrickville : COUNCIL_CONFIGS.marrickville;
  const topicOrder = professionalMode === 'certifier' ? councilConfig.topicOrder.certifier : councilConfig.topicOrder.planner;

  // Build API URL for SWR caching
  // NOTE: selectedTopic is NOT included - we filter client-side for stable counts
  const apiUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (zone) params.set('zone', zone);
    if (heritage) params.set('heritage', 'true');
    if (flood) params.set('flood', 'true');
    if (precinctId) params.set('precinct_id', precinctId);
    if (selectedDevType) params.set('dev_type', selectedDevType);
    if (council) params.set('former_council', council);
    // Pass HCA code for server-side heritage filtering (only property's HCA + general controls)
    // API will resolve C-code (e.g., "C67") to db_slug via heritage_conservation_areas table
    if (heritageItemNumber) {
      params.set('hca', heritageItemNumber);
    } else if (hcaName) {
      // Fallback to name-based slug for properties without item number
      params.set('hca', hcaNameToSlug(hcaName));
    }
    return `/api/provisions/for-property?${params}`;
  }, [zone, heritage, flood, precinctId, selectedDevType, council, hcaName, heritageItemNumber]);

  // SWR for cached data fetching - same URL = instant from cache
  const { data, error, isLoading } = useSWR<{
    by_layer: LayerResult[];
    by_topic: Record<string, Provision[]>;
    summary: any;
  }>(apiUrl, fetcher, {
    revalidateOnFocus: false,  // Don't refetch when window regains focus
    dedupingInterval: 60000,   // Dedupe requests within 60 seconds
    keepPreviousData: true,    // Show stale data while revalidating
  });

  // Compute topic counts from data (memoized for performance)
  const originalTopicCounts = useMemo(() => {
    if (!data?.by_topic) return {};
    const counts: Record<string, number> = {};
    Object.entries(data.by_topic).forEach(([topic, provisions]) => {
      counts[topic] = (provisions as Provision[]).length;
    });
    return counts;
  }, [data?.by_topic]);

  // Reset selected topic when address changes
  useEffect(() => {
    setSelectedTopic('');
  }, [zone, heritage, flood, precinctId, council]);

  // Auto-expand first 3 topics on initial load
  useEffect(() => {
    if (data?.by_topic && expandedTopics.size === 0) {
      const topics = Object.keys(data.by_topic);
      const sortedTopics = sortTopicsByPriority(topics, topicOrder);
      setExpandedTopics(new Set(sortedTopics.slice(0, 3)));
    }
  }, [data?.by_topic, topicOrder, expandedTopics.size]);

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

  const toggleDcpPart = (partKey: string) => {
    setExpandedDcpParts(prev => {
      const next = new Set(prev);
      if (next.has(partKey)) {
        next.delete(partKey);
      } else {
        next.add(partKey);
      }
      return next;
    });
  };

  // Group provisions by DCP part for large topics
  // Takes topic name to avoid redundant groupings like "Heritage" under Heritage topic
  const groupByDcpPart = (provisions: Provision[], topicName?: string): Map<string, Provision[]> => {
    const grouped = new Map<string, Provision[]>();
    const topicLower = topicName?.toLowerCase().replace(/_/g, ' ') || '';

    provisions.forEach(p => {
      // Ensure v2_dcp_part is a valid string label
      let part = p.v2_dcp_part;
      const partLower = (typeof part === 'string') ? part.toLowerCase() : '';

      if (part === null || part === undefined || part === '') {
        part = 'General Controls';
      } else if (typeof part !== 'string') {
        part = 'General Controls';
      } else if (/^\d+$/.test(part)) {
        // Skip purely numeric values (data quality issue)
        part = 'General Controls';
      } else if (partLower === 'unknown' || partLower === 'other' || partLower === 'general controls') {
        // Merge all generic labels into one
        part = 'General Controls';
      } else if (topicLower && partLower === topicLower) {
        // Avoid redundant "Heritage" under Heritage topic
        part = 'General Controls';
      }

      if (!grouped.has(part)) {
        grouped.set(part, []);
      }
      grouped.get(part)!.push(p);
    });
    // Sort by count descending
    return new Map([...grouped.entries()].sort((a, b) => b[1].length - a[1].length));
  };

  // Group heritage provisions by HCA (Heritage Conservation Area)
  const groupByHca = (provisions: Provision[]): Map<string, Provision[]> => {
    const grouped = new Map<string, Provision[]>();
    provisions.forEach(p => {
      const hca = p.v2_heritage_hca || 'General Heritage Controls';
      if (!grouped.has(hca)) {
        grouped.set(hca, []);
      }
      grouped.get(hca)!.push(p);
    });
    // Sort: General first, then by count descending
    return new Map([...grouped.entries()].sort((a, b) => {
      if (a[0] === 'General Heritage Controls') return -1;
      if (b[0] === 'General Heritage Controls') return 1;
      return b[1].length - a[1].length;
    }));
  };

  const toggleHca = (hcaKey: string) => {
    setExpandedHcas(prev => {
      const next = new Set(prev);
      if (next.has(hcaKey)) {
        next.delete(hcaKey);
      } else {
        next.add(hcaKey);
      }
      return next;
    });
  };

  // Format HCA name for display
  const formatHcaName = (hca: string): string => {
    if (hca === 'General Heritage Controls') return hca;
    return hca.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') + ' HCA';
  };

  // Format DCP part with descriptive label
  const formatDcpPart = (part: string): string => {
    // Handle empty/null part
    if (!part || part === 'Other') return 'General Controls';

    if (council && DCP_PART_LABELS[council]?.[part]) {
      return DCP_PART_LABELS[council][part];
    }
    return part;
  };

  // Get layer label with fallback for unknown/null
  const getLayerLabel = (layer: string | null | undefined): string => {
    if (!layer || layer === 'unknown' || layer === 'null') return 'General';
    return LAYER_LABELS[layer] || layer;
  };

  // Get layer color with fallback for unknown/null
  const getLayerColor = (layer: string | null | undefined): string => {
    if (!layer || layer === 'unknown' || layer === 'null') return LAYER_COLORS.generic;
    return LAYER_COLORS[layer] || 'bg-gray-100';
  };

  if (isLoading) {
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
          <p className="text-red-600">Error: {error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  // Convert property's HCA name to slug for matching
  const propertyHcaSlug = hcaName ? hcaNameToSlug(hcaName) : '';

  // Filter heritage provisions to only show General + property's specific HCA
  const filterHeritageProvisions = (provisions: Provision[]): Provision[] => {
    if (!propertyHcaSlug) {
      // No HCA specified - show all general heritage controls (null HCA) only
      return provisions.filter(p => !p.v2_heritage_hca);
    }
    // Show: General (null HCA) + property's specific HCA
    return provisions.filter(p =>
      !p.v2_heritage_hca || // General heritage controls
      p.v2_heritage_hca === propertyHcaSlug || // Exact match
      p.v2_heritage_hca.includes(propertyHcaSlug) || // Partial match (e.g., "summer_hill" in "summer_hill_central")
      propertyHcaSlug.includes(p.v2_heritage_hca) // Reverse partial match
    );
  };

  // Sort topics by council-specific professional priority, not just count
  const topicEntries = Object.entries(data.by_topic || {});
  const sortedTopicNames = sortTopicsByPriority(topicEntries.map(([name]) => name), topicOrder);
  // Filter by selectedTopic client-side (API returns all, we filter here)
  const filteredTopicNames = selectedTopic
    ? sortedTopicNames.filter(name => name === selectedTopic)
    : sortedTopicNames;
  const topics = filteredTopicNames.map(name => {
    const entry = topicEntries.find(([n]) => n === name);
    if (!entry) return [name, []];
    const [topicName, provisions] = entry;
    // Apply HCA filtering for heritage topic
    const filteredProvisions = topicName.toLowerCase() === 'heritage'
      ? filterHeritageProvisions(provisions as Provision[])
      : provisions;
    return [topicName, filteredProvisions];
  }).filter(([, provisions]) => (provisions as Provision[]).length > 0) as [string, Provision[]][];

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
          {/* DCP Explanation - Clean Typography with styled layer terms */}
          {councilConfig?.dcpExplanation && (
            <div className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
              {councilConfig.dcpExplanation.split(/(\[[^\]]+\])/).map((part, i) => {
                const match = part.match(/^\[(.+)\]$/);
                if (match) {
                  const term = match[1];
                  // Map terms to badge colors matching the summary pills
                  const colorClass =
                    term === 'Base Controls' || term === 'Universal' ? 'bg-slate-100 text-slate-700' :
                    term === 'Zone Controls' ? 'bg-sky-100 text-sky-700' :
                    term === 'Heritage' ? 'bg-amber-100 text-amber-700' :
                    term === 'Precinct Character' || term === 'Village Precinct' || term === 'Distinct Neighbourhood' ? 'bg-emerald-100 text-emerald-700' :
                    'bg-gray-100 text-gray-700';
                  return (
                    <span key={i} className={`${colorClass} px-1.5 py-0.5 rounded text-xs font-medium`}>
                      {term}
                    </span>
                  );
                }
                return <span key={i}>{part}</span>;
              })}
            </div>
          )}


          {/* Topic Filter Pills */}
          <div className="space-y-2">
            <p className="text-xs text-slate-600">Choose topics to filter provisions for this address:</p>
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
              {/* Show ALL topics with stable counts (client-side filtering, API returns all) */}
              {Object.entries(originalTopicCounts)
                .sort((a, b) => b[1] - a[1])
                .map(([topic, count]) => (
                <button
                  key={topic}
                  onClick={() => setSelectedTopic(topic)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${selectedTopic === topic
                      ? 'bg-slate-800 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                >
                  {TOPIC_LABELS[topic] || topic} ({count})
                </button>
              ))}
            </div>
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
              className="cursor-pointer hover:bg-gray-50 active:bg-gray-100 transition-colors py-2 px-3"
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
                <div className="flex items-center gap-1.5">
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  <Icon className="h-4 w-4" />
                  <span className="font-medium text-sm">
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
                {/* HeritageProvisions removed - v2_heritage_type data not populated, using v2_dcp_part grouping instead */}
                <div className="space-y-2">
                    {provisions.length > DCP_PART_GROUPING_THRESHOLD ? (
                      // Large topic: Group by DCP Part with sub-accordions
                      <div className="space-y-2">
                        {Array.from(groupByDcpPart(provisions, topic)).map(([dcpPart, partProvisions]) => {
                          const partKey = `${topic}-${dcpPart}`;
                          const isPartExpanded = expandedDcpParts.has(partKey);

                          return (
                            <div key={partKey} className="border border-gray-200 rounded-lg overflow-hidden">
                              {/* DCP Part Header */}
                              <button
                                onClick={() => toggleDcpPart(partKey)}
                                className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 hover:bg-slate-100 transition-colors"
                              >
                                <div className="flex items-center gap-2">
                                  {isPartExpanded ? (
                                    <ChevronDown className="h-4 w-4 text-slate-500" />
                                  ) : (
                                    <ChevronRight className="h-4 w-4 text-slate-500" />
                                  )}
                                  <span className="font-medium text-sm text-slate-700">{formatDcpPart(dcpPart)}</span>
                                  <Badge variant="secondary" className="text-xs">
                                    {partProvisions.length}
                                  </Badge>
                                </div>
                              </button>

                              {/* DCP Part Provisions */}
                              {isPartExpanded && (
                                <div className="p-2 space-y-2 bg-white">
                                  {/* Heritage topics with large parts get HCA sub-grouping */}
                                  {topic.toLowerCase() === 'heritage' && partProvisions.length > HCA_GROUPING_THRESHOLD ? (
                                    <div className="space-y-2">
                                      {Array.from(groupByHca(partProvisions)).map(([hca, hcaProvisions]) => {
                                        const hcaKey = `${partKey}-${hca}`;
                                        const isHcaExpanded = expandedHcas.has(hcaKey);

                                        return (
                                          <div key={hcaKey} className="border border-amber-200 rounded-lg overflow-hidden">
                                            {/* HCA Header */}
                                            <button
                                              onClick={() => toggleHca(hcaKey)}
                                              className="w-full flex items-center justify-between px-3 py-2 bg-amber-50 hover:bg-amber-100 transition-colors"
                                            >
                                              <div className="flex items-center gap-2">
                                                {isHcaExpanded ? (
                                                  <ChevronDown className="h-3 w-3 text-amber-600" />
                                                ) : (
                                                  <ChevronRight className="h-3 w-3 text-amber-600" />
                                                )}
                                                <span className="font-medium text-xs text-amber-800">{formatHcaName(hca)}</span>
                                                <Badge variant="secondary" className="text-[10px] bg-amber-100">
                                                  {hcaProvisions.length}
                                                </Badge>
                                              </div>
                                            </button>

                                            {/* HCA Provisions */}
                                            {isHcaExpanded && (
                                              <div className="p-2 space-y-2 bg-white">
                                                {hcaProvisions.slice(0, 15).map((provision, idx) => {
                                                  const layer = provision.layer || provision.v2_dcp_layer;
                                                  const layerBorderColor = layer === 'generic' ? 'border-l-slate-400' :
                                                    layer === 'use_specific' ? 'border-l-sky-400' :
                                                    layer === 'condition' ? 'border-l-amber-400' :
                                                    layer === 'precinct' ? 'border-l-emerald-400' : 'border-l-gray-300';
                                                  const zebraStripe = idx % 2 === 1 ? 'bg-teal-50' : 'bg-white';

                                                  return (
                                                    <div
                                                      key={provision.id}
                                                      className={`${zebraStripe} border border-gray-200 rounded-lg overflow-hidden transition-all hover:shadow-md ${layerBorderColor} border-l-4`}
                                                    >
                                                      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50/50 border-b border-gray-100">
                                                        <div className="flex items-center gap-2">
                                                          {provision.v2_marker && (
                                                            <span className="font-mono text-xs font-semibold text-slate-700">
                                                              {provision.v2_marker}
                                                            </span>
                                                          )}
                                                          <Badge className={`text-[10px] ${getLayerColor(layer)}`}>
                                                            {getLayerLabel(layer)}
                                                          </Badge>
                                                        </div>
                                                        {provision.pdf_page_image_url && (() => {
                                                          const pageNum = provision.pdf_page || parseInt(provision.pdf_page_image_url!.match(/page_(\d+)/)?.[1] || '0');
                                                          return (
                                                            <Button
                                                              size="sm"
                                                              variant="ghost"
                                                              className="h-6 px-2 text-[10px] bg-teal-700 text-white hover:bg-teal-800"
                                                              onClick={(e) => {
                                                                e.stopPropagation();
                                                                setViewingPdfImage({
                                                                  url: provision.pdf_page_image_url!,
                                                                  page: pageNum
                                                                });
                                                              }}
                                                            >
                                                              <FileText className="h-3 w-3 mr-1" />
                                                              Page {pageNum}
                                                            </Button>
                                                          );
                                                        })()}
                                                      </div>
                                                      <div className="px-3 py-2">
                                                        <div
                                                          className={`text-sm text-gray-700 leading-relaxed cursor-pointer ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-2'}`}
                                                          onClick={() => toggleProvision(provision.id)}
                                                        >
                                                          <FormattedProvisionText text={provision.provision_text} compact />
                                                        </div>
                                                        {provision.provision_text.length > 100 && (
                                                          <button
                                                            className="text-xs text-slate-500 hover:text-slate-700 mt-1 font-medium"
                                                            onClick={() => toggleProvision(provision.id)}
                                                          >
                                                            {expandedProvisions.has(provision.id) ? '↑ Less' : '↓ More'}
                                                          </button>
                                                        )}
                                                      </div>
                                                    </div>
                                                  );
                                                })}
                                                {hcaProvisions.length > 15 && (
                                                  <p className="text-xs text-gray-500 text-center py-1">
                                                    Showing 15 of {hcaProvisions.length} in {formatHcaName(hca)}
                                                  </p>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        );
                                      })}
                                    </div>
                                  ) : (
                                    /* Regular provisions list for non-heritage or small heritage parts */
                                    <>
                                      {partProvisions.slice(0, 20).map((provision, idx) => {
                                        const layer = provision.layer || provision.v2_dcp_layer;
                                        const layerBorderColor = layer === 'generic' ? 'border-l-slate-400' :
                                          layer === 'use_specific' ? 'border-l-sky-400' :
                                          layer === 'condition' ? 'border-l-amber-400' :
                                          layer === 'precinct' ? 'border-l-emerald-400' : 'border-l-gray-300';
                                        const zebraStripe = idx % 2 === 1 ? 'bg-teal-50' : 'bg-white';

                                        return (
                                          <div
                                            key={provision.id}
                                            className={`${zebraStripe} border border-gray-200 rounded-lg overflow-hidden transition-all hover:shadow-md ${layerBorderColor} border-l-4`}
                                          >
                                            <div className="flex items-center justify-between px-4 py-2 bg-gray-50/50 border-b border-gray-100">
                                              <div className="flex items-center gap-2">
                                                {provision.v2_marker && (
                                                  <span className="font-mono text-sm font-semibold text-slate-700">
                                                    {provision.v2_marker}
                                                  </span>
                                                )}
                                                <Badge className={`text-[10px] ${getLayerColor(layer)}`}>
                                                  {getLayerLabel(layer)}
                                                </Badge>
                                              </div>
                                              {provision.pdf_page_image_url && (() => {
                                                const pageNum = provision.pdf_page || parseInt(provision.pdf_page_image_url!.match(/page_(\d+)/)?.[1] || '0');
                                                return (
                                                  <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-7 px-2 text-xs bg-teal-700 text-white hover:bg-teal-800"
                                                    onClick={(e) => {
                                                      e.stopPropagation();
                                                      setViewingPdfImage({
                                                        url: provision.pdf_page_image_url!,
                                                        page: pageNum
                                                      });
                                                    }}
                                                  >
                                                    <FileText className="h-3 w-3 mr-1" />
                                                    View DCP page {pageNum}
                                                  </Button>
                                                );
                                              })()}
                                            </div>
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
                                      {partProvisions.length > 20 && (
                                        <p className="text-sm text-gray-500 text-center py-2">
                                          Showing 20 of {partProvisions.length} provisions
                                        </p>
                                      )}
                                    </>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      // Small topic: Flat list (original behavior)
                      <>
                        {provisions.slice(0, 20).map((provision, idx) => {
                          const layer = provision.layer || provision.v2_dcp_layer;
                          const layerBorderColor = layer === 'generic' ? 'border-l-slate-400' :
                            layer === 'use_specific' ? 'border-l-sky-400' :
                            layer === 'condition' ? 'border-l-amber-400' :
                            layer === 'precinct' ? 'border-l-emerald-400' : 'border-l-gray-300';
                          const zebraStripe = idx % 2 === 1 ? 'bg-teal-50' : 'bg-white';

                          return (
                            <div
                              key={provision.id}
                              className={`${zebraStripe} border border-gray-200 rounded-lg overflow-hidden transition-all hover:shadow-md ${layerBorderColor} border-l-4`}
                            >
                              <div className="flex items-center justify-between px-4 py-2 bg-gray-50/50 border-b border-gray-100">
                                <div className="flex items-center gap-2">
                                  {provision.v2_marker && (
                                    <span className="font-mono text-sm font-semibold text-slate-700">
                                      {provision.v2_marker}
                                    </span>
                                  )}
                                  <Badge className={`text-[10px] ${getLayerColor(layer)}`}>
                                    {getLayerLabel(layer)}
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
                                      className="h-7 px-2 text-xs bg-teal-700 text-white hover:bg-teal-800"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setViewingPdfImage({
                                          url: provision.pdf_page_image_url!,
                                          page: pageNum
                                        });
                                      }}
                                    >
                                      <FileText className="h-3 w-3 mr-1" />
                                      View DCP page {pageNum}
                                    </Button>
                                  );
                                })()}
                              </div>
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
                        {provisions.length > 20 && (
                          <p className="text-sm text-gray-500 text-center py-2">
                            Showing 20 of {provisions.length} provisions
                          </p>
                        )}
                      </>
                    )}
                </div>
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
