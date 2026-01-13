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
import { PageGroupedProvisions } from './PageGroupedProvisions';
import { stripSectionHeader } from '@/lib/provision-text-formatter';

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
  v2_heritage_type?: 'control' | 'guidance' | 'character' | 'descriptive';
  v2_heritage_element?: string[];
  v2_heritage_hca?: string;
  v2_heritage_subcategory?: string;  // For Heritage topic sub-grouping (character, fencing, etc.)
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
 * Group provisions by PDF page for grouped rendering with page headers.
 * Returns array of page groups, each with page info and provisions.
 */
interface PageGroup {
  pageNumber: number | null;
  pageUrl: string | null;
  provisions: Provision[];
}

function groupProvisionsByPage(provisions: Provision[]): PageGroup[] {
  const pageMap = new Map<string, { pageNumber: number | null; pageUrl: string; provisions: Provision[] }>();
  const ungrouped: Provision[] = [];

  for (const prov of provisions) {
    if (prov.pdf_page_image_url) {
      const key = prov.pdf_page_image_url;
      if (!pageMap.has(key)) {
        pageMap.set(key, {
          pageNumber: prov.pdf_page || null,
          pageUrl: prov.pdf_page_image_url,
          provisions: []
        });
      }
      pageMap.get(key)!.provisions.push(prov);
    } else {
      ungrouped.push(prov);
    }
  }

  // Sort by page number, ungrouped at end
  const groups = Array.from(pageMap.values())
    .sort((a, b) => (a.pageNumber || 999) - (b.pageNumber || 999));

  // Add ungrouped provisions at end if any
  if (ungrouped.length > 0) {
    groups.push({ pageNumber: null, pageUrl: null, provisions: ungrouped });
  }

  return groups;
}

/**
 * Given an array of provisions, returns a Set of provision IDs that should show the PDF button.
 * Now only used as fallback - prefer page grouping with header buttons.
 */
function getProvisionsWithPdfButton(provisions: Provision[]): Set<number> {
  const result = new Set<number>();

  // Show PDF button for every provision that has a PDF page
  for (const prov of provisions) {
    if (prov.pdf_page_image_url) {
      result.add(prov.id);
    }
  }

  return result;
}

/**
 * Get page grouping info for provisions - which provisions share a PDF page
 */
function getPageGroupInfo(provisions: Provision[]): Map<number, { isFirst: boolean; isLast: boolean; pageUrl: string }> {
  const result = new Map<number, { isFirst: boolean; isLast: boolean; pageUrl: string }>();
  const pageGroups = new Map<string, number[]>();

  // Group provision IDs by page URL
  for (const prov of provisions) {
    if (prov.pdf_page_image_url) {
      if (!pageGroups.has(prov.pdf_page_image_url)) {
        pageGroups.set(prov.pdf_page_image_url, []);
      }
      pageGroups.get(prov.pdf_page_image_url)!.push(prov.id);
    }
  }

  // Mark first/last in each group
  for (const [pageUrl, ids] of pageGroups.entries()) {
    if (ids.length > 1) {
      ids.forEach((id, idx) => {
        result.set(id, {
          isFirst: idx === 0,
          isLast: idx === ids.length - 1,
          pageUrl
        });
      });
    }
  }

  return result;
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
    // Only pass heritageItemNumber if it looks like an HCA code (C26, HCA 26, etc), not heritage items (I262)
    if (heritageItemNumber && /^[CA]\d+$/i.test(heritageItemNumber)) {
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
    // Removed keepPreviousData to ensure loading state shows on new address
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

  // Compute which provision IDs should show the PDF button (only last provision on each page)
  const showPdfButtonIds = useMemo(() => {
    if (!data?.by_topic) return new Set<number>();
    // Flatten all provisions to compute page groupings
    const allProvisions: Provision[] = [];
    Object.values(data.by_topic).forEach((provisions) => {
      allProvisions.push(...(provisions as Provision[]));
    });
    return getProvisionsWithPdfButton(allProvisions);
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

  // Get property's HCA slug for sorting and highlighting
  const propertyHcaSlug = useMemo(() => {
    if (heritageItemNumber) return heritageItemNumberToSlug(heritageItemNumber);
    if (hcaName) return hcaNameToSlug(hcaName);
    return '';
  }, [heritageItemNumber, hcaName]);

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
    // Sort: Property's HCA first, then General, then by count descending
    return new Map([...grouped.entries()].sort((a, b) => {
      // Property's specific HCA comes first
      if (propertyHcaSlug && a[0] === propertyHcaSlug) return -1;
      if (propertyHcaSlug && b[0] === propertyHcaSlug) return 1;
      // Then General Heritage Controls
      if (a[0] === 'General Heritage Controls') return -1;
      if (b[0] === 'General Heritage Controls') return 1;
      // Then by count descending
      return b[1].length - a[1].length;
    }));
  };

  // Check if HCA matches property's HCA (for highlighting)
  const isPropertyHca = (hca: string): boolean => {
    return propertyHcaSlug !== '' && hca === propertyHcaSlug;
  };

  // Group heritage provisions by subcategory (character, fencing, heritage, etc.)
  // Used for consolidated Heritage topic from condition layer
  const groupByHeritageSubcategory = (provisions: Provision[]): Map<string, Provision[]> => {
    const grouped = new Map<string, Provision[]>();
    provisions.forEach(p => {
      const subcat = p.v2_heritage_subcategory || 'Heritage';
      if (!grouped.has(subcat)) {
        grouped.set(subcat, []);
      }
      grouped.get(subcat)!.push(p);
    });
    // Sort: Heritage first, then by count descending
    return new Map([...grouped.entries()].sort((a, b) => {
      if (a[0] === 'Heritage') return -1;
      if (b[0] === 'Heritage') return 1;
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

  // Heritage type labels and colors for layered display
  const HERITAGE_TYPE_CONFIG: Record<string, { label: string; bg: string; border: string; accent: string }> = {
    control: {
      label: 'Controls',
      bg: 'bg-green-50',
      border: 'border-green-200',
      accent: 'text-green-700'
    },
    guidance: {
      label: 'Guidance',
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      accent: 'text-blue-700'
    },
    character: {
      label: 'Character Statements',
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      accent: 'text-blue-700'
    },
    descriptive: {
      label: 'Background Info',
      bg: 'bg-gray-50',
      border: 'border-gray-200',
      accent: 'text-gray-600'
    },
  };

  // Group heritage provisions by type within an HCA
  const groupByHeritageType = (provisions: Provision[]): Map<string, Provision[]> => {
    const grouped = new Map<string, Provision[]>();
    // Ensure order: control first, then guidance/character, then descriptive
    grouped.set('control', []);
    grouped.set('guidance', []);
    grouped.set('character', []);
    grouped.set('descriptive', []);

    provisions.forEach(p => {
      const type = p.v2_heritage_type || 'descriptive';
      if (!grouped.has(type)) {
        grouped.set(type, []);
      }
      grouped.get(type)!.push(p);
    });

    // Remove empty groups
    for (const [type, provs] of grouped.entries()) {
      if (provs.length === 0) grouped.delete(type);
    }

    return grouped;
  };

  // Track expanded heritage types within HCAs
  const [expandedHeritageTypes, setExpandedHeritageTypes] = useState<Set<string>>(new Set());
  // Track which heritage type groups show all provisions (no limit)
  const [showAllHeritageTypes, setShowAllHeritageTypes] = useState<Set<string>>(new Set());
  // Track element filter per heritage type section (e.g., "hcaKey-control" -> "roof")
  const [elementFilters, setElementFilters] = useState<Record<string, string>>({});

  // Element labels for display (Heritage + Building Form)
  const ELEMENT_LABELS: Record<string, string> = {
    // Heritage elements
    roof: 'Roof',
    fence: 'Fencing',
    materials: 'Materials',
    verandah: 'Verandah',
    window: 'Windows',
    facade: 'Facade',
    chimney: 'Chimney',
    door: 'Doors',
    car_parking: 'Parking',
    scale: 'Scale',
    infill: 'Infill',
    demolition: 'Demolition',
    setback: 'Setbacks',
    garden: 'Garden',
    interior: 'Interior',
    // Building Form - building types
    secondary_dwelling: 'Secondary Dwelling',
    multi_dwelling: 'Multi Dwelling',
    residential_flat: 'Residential Flat',
    boarding_house: 'Boarding House',
    child_care: 'Child Care',
    neighbourhood_shop: 'Neighbourhood Shop',
    mixed_use: 'Mixed Use',
    commercial: 'Commercial',
    industrial: 'Industrial',
    all_residential: 'All Residential',
    all_development: 'All Development',
  };

  // Get unique elements from provisions with counts
  const getElementCounts = (provisions: Provision[]): Map<string, number> => {
    const counts = new Map<string, number>();
    provisions.forEach(p => {
      if (p.v2_heritage_element) {
        p.v2_heritage_element.forEach(elem => {
          counts.set(elem, (counts.get(elem) || 0) + 1);
        });
      }
    });
    // Sort by count descending
    return new Map([...counts.entries()].sort((a, b) => b[1] - a[1]));
  };

  // Get element totals (single + multi combined) and general count
  const getElementTotals = (provisions: Provision[]) => {
    const totals = new Map<string, number>();
    let generalCount = 0;

    provisions.forEach(p => {
      if (!p.v2_heritage_element || p.v2_heritage_element.length === 0) {
        generalCount++;
      } else {
        p.v2_heritage_element.forEach(elem => {
          totals.set(elem, (totals.get(elem) || 0) + 1);
        });
      }
    });

    // Sort by count descending
    const sorted = new Map([...totals.entries()].sort((a, b) => b[1] - a[1]));
    return { totals: sorted, generalCount };
  };

  // Split filtered provisions into "only this element" and "this + others"
  const splitByExclusivity = (provisions: Provision[], element: string) => {
    const onlyThis: Provision[] = [];
    const plusOthers: Provision[] = [];

    provisions.forEach(p => {
      if (p.v2_heritage_element && p.v2_heritage_element.includes(element)) {
        if (p.v2_heritage_element.length === 1) {
          onlyThis.push(p);
        } else {
          plusOthers.push(p);
        }
      }
    });

    return { onlyThis, plusOthers };
  };

  // Filter provisions by selected element
  const filterByElement = (provisions: Provision[], element: string | undefined): Provision[] => {
    if (!element) return provisions;
    if (element === '_general') {
      return provisions.filter(p => !p.v2_heritage_element || p.v2_heritage_element.length === 0);
    }
    return provisions.filter(p =>
      p.v2_heritage_element && p.v2_heritage_element.includes(element)
    );
  };

  const setElementFilter = (typeKey: string, element: string | null) => {
    setElementFilters(prev => {
      if (element === null) {
        const next = { ...prev };
        delete next[typeKey];
        return next;
      }
      return { ...prev, [typeKey]: element };
    });
  };

  const toggleHeritageType = (typeKey: string) => {
    setExpandedHeritageTypes(prev => {
      const next = new Set(prev);
      if (next.has(typeKey)) {
        next.delete(typeKey);
      } else {
        next.add(typeKey);
      }
      return next;
    });
  };

  const toggleShowAllHeritageType = (typeKey: string) => {
    setShowAllHeritageTypes(prev => {
      const next = new Set(prev);
      if (next.has(typeKey)) {
        next.delete(typeKey);
      } else {
        next.add(typeKey);
      }
      return next;
    });
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

  // Sort topics by council-specific professional priority, not just count
  // Note: HCA filtering is now done server-side via the hca parameter
  const topicEntries = Object.entries(data.by_topic || {});
  const sortedTopicNames = sortTopicsByPriority(topicEntries.map(([name]) => name), topicOrder);
  // Filter by selectedTopic client-side (API returns all, we filter here)
  const filteredTopicNames = selectedTopic
    ? sortedTopicNames.filter(name => name === selectedTopic)
    : sortedTopicNames;
  const topics = filteredTopicNames.map(name => {
    const entry = topicEntries.find(([n]) => n === name);
    if (!entry) return [name, []];
    return entry;
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
                  {/* Control/Guidance breakdown for Building Form */}
                  {topic.toLowerCase() === 'building_form' && (() => {
                    const controlCount = provisions.filter(p => p.v2_heritage_type === 'control').length;
                    const guidanceCount = provisions.filter(p => p.v2_heritage_type === 'guidance').length;
                    if (controlCount > 0 || guidanceCount > 0) {
                      return (
                        <span className="text-xs text-gray-600 ml-2 hidden md:inline">
                          {controlCount > 0 && <span className="text-green-700 font-medium">{controlCount} controls</span>}
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
                {/* HeritageProvisions removed - v2_heritage_type data not populated, using v2_dcp_part grouping instead */}
                <div className="space-y-2">
                    {/* Show grouped view for large topics OR for Building Form (which has control/guidance types) */}
                    {(provisions.length > DCP_PART_GROUPING_THRESHOLD || topic.toLowerCase() === 'building_form') ? (
                      // Large topic or Building Form: Group by DCP Part with sub-accordions
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
                                  {/* Heritage topics: check if provisions have subcategory (from condition layer) or HCA (from regulatory_provisions) */}
                                  {topic.toLowerCase() === 'heritage' && partProvisions.length > HCA_GROUPING_THRESHOLD ? (
                                    // Check if provisions have subcategory (condition layer) vs HCA (regulatory_provisions)
                                    partProvisions.some(p => p.v2_heritage_subcategory && p.v2_heritage_subcategory !== 'Heritage') ? (
                                      // Subcategory grouping for consolidated Heritage provisions from condition layer
                                      <div className="space-y-2">
                                        {Array.from(groupByHeritageSubcategory(partProvisions)).map(([subcategory, subcatProvisions]) => {
                                          const subcatKey = `${partKey}-subcat-${subcategory}`;
                                          const isSubcatExpanded = expandedHcas.has(subcatKey);

                                          return (
                                            <div key={subcatKey} className="border rounded-lg overflow-hidden border-amber-200">
                                              {/* Subcategory Header */}
                                              <button
                                                onClick={() => toggleHca(subcatKey)}
                                                className="w-full flex items-center justify-between px-3 py-2 bg-amber-50 hover:bg-amber-100 transition-colors"
                                              >
                                                <div className="flex items-center gap-2">
                                                  {isSubcatExpanded ? (
                                                    <ChevronDown className="h-3 w-3 text-amber-600" />
                                                  ) : (
                                                    <ChevronRight className="h-3 w-3 text-amber-600" />
                                                  )}
                                                  <span className="font-medium text-xs text-amber-800">
                                                    {subcategory}
                                                  </span>
                                                  <Badge variant="secondary" className="text-[10px]">
                                                    {subcatProvisions.length}
                                                  </Badge>
                                                </div>
                                              </button>

                                              {/* Subcategory Provisions - Page grouped */}
                                              {isSubcatExpanded && (
                                                <div className="p-2 bg-white">
                                                  <PageGroupedProvisions
                                                    provisions={subcatProvisions}
                                                    expandedProvisions={expandedProvisions}
                                                    onToggleProvision={toggleProvision}
                                                    onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                                    theme={{
                                                      zebraStripeBg: 'bg-amber-50/50',
                                                      zebraStripeAltBg: 'bg-white',
                                                      borderColorClass: 'border-amber-200',
                                                      textClampLines: 2,
                                                      expandThreshold: 200,
                                                    }}
                                                    maxProvisions={20}
                                                  />
                                                </div>
                                              )}
                                            </div>
                                          );
                                        })}
                                      </div>
                                    ) : (
                                    // HCA grouping for regulatory_provisions heritage data
                                    <div className="space-y-2">
                                      {Array.from(groupByHca(partProvisions)).map(([hca, hcaProvisions]) => {
                                        const hcaKey = `${partKey}-${hca}`;
                                        const isHcaExpanded = expandedHcas.has(hcaKey);

                                        const isThisPropertyHca = isPropertyHca(hca);

                                        // Count by heritage type for upfront breakdown
                                        const typeBreakdown = {
                                          control: hcaProvisions.filter(p => p.v2_heritage_type === 'control').length,
                                          character: hcaProvisions.filter(p => p.v2_heritage_type === 'character').length,
                                          descriptive: hcaProvisions.filter(p => p.v2_heritage_type === 'descriptive' || !p.v2_heritage_type).length,
                                        };

                                        return (
                                          <div key={hcaKey} className={`border rounded-lg overflow-hidden ${isThisPropertyHca ? 'border-teal-400 ring-2 ring-teal-200' : 'border-amber-200'}`}>
                                            {/* HCA Header */}
                                            <button
                                              onClick={() => toggleHca(hcaKey)}
                                              className={`w-full flex items-center justify-between px-3 py-2 transition-colors ${isThisPropertyHca ? 'bg-teal-50 hover:bg-teal-100' : 'bg-amber-50 hover:bg-amber-100'}`}
                                            >
                                              <div className="flex items-center gap-2">
                                                {isHcaExpanded ? (
                                                  <ChevronDown className={`h-3 w-3 ${isThisPropertyHca ? 'text-teal-600' : 'text-amber-600'}`} />
                                                ) : (
                                                  <ChevronRight className={`h-3 w-3 ${isThisPropertyHca ? 'text-teal-600' : 'text-amber-600'}`} />
                                                )}
                                                <span className={`font-medium text-xs ${isThisPropertyHca ? 'text-teal-800' : 'text-amber-800'}`}>
                                                  {isThisPropertyHca ? '★ ' : ''}{formatHcaName(hca)}
                                                  {isThisPropertyHca ? ' (Your Property)' : ''}
                                                </span>
                                              </div>
                                              <div className="flex items-center gap-1.5 text-[10px]">
                                                {typeBreakdown.control > 0 && (
                                                  <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                                                    {typeBreakdown.control} controls
                                                  </span>
                                                )}
                                                {typeBreakdown.character > 0 && (
                                                  <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                                                    {typeBreakdown.character} character
                                                  </span>
                                                )}
                                                {typeBreakdown.descriptive > 0 && (
                                                  <span className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                                                    {typeBreakdown.descriptive} background
                                                  </span>
                                                )}
                                              </div>
                                            </button>

                                            {/* HCA Provisions - Grouped by Heritage Type */}
                                            {isHcaExpanded && (
                                              <div className="p-2 space-y-2 bg-white">
                                                {/* Group by heritage type: controls first, then character, then descriptive */}
                                                {Array.from(groupByHeritageType(hcaProvisions)).map(([heritageType, typeProvisions]) => {
                                                  const typeConfig = HERITAGE_TYPE_CONFIG[heritageType] || HERITAGE_TYPE_CONFIG.descriptive;
                                                  const typeKey = `${hcaKey}-${heritageType}`;
                                                  // Controls auto-expand, others collapsed by default
                                                  const isTypeExpanded = heritageType === 'control' || expandedHeritageTypes.has(typeKey);
                                                  const displayLimit = heritageType === 'control' ? 15 : 5;

                                                  const isShowingAll = showAllHeritageTypes.has(typeKey);
                                                  const actualLimit = isShowingAll ? typeProvisions.length : displayLimit;

                                                  return (
                                                    <div key={typeKey} className={`border rounded-lg overflow-hidden ${typeConfig.border}`}>
                                                      {/* Heritage Type Header */}
                                                      <button
                                                        onClick={() => heritageType !== 'control' && toggleHeritageType(typeKey)}
                                                        className={`w-full flex items-center justify-between px-3 py-1.5 ${typeConfig.bg} ${heritageType !== 'control' ? 'cursor-pointer hover:opacity-80' : ''}`}
                                                      >
                                                        <div className="flex items-center gap-2">
                                                          {heritageType !== 'control' && (
                                                            isTypeExpanded ? (
                                                              <ChevronDown className={`h-3 w-3 ${typeConfig.accent}`} />
                                                            ) : (
                                                              <ChevronRight className={`h-3 w-3 ${typeConfig.accent}`} />
                                                            )
                                                          )}
                                                          <span className={`font-medium text-xs ${typeConfig.accent}`}>
                                                            {heritageType === 'control' ? '✓ ' : ''}{typeConfig.label}
                                                          </span>
                                                          <Badge variant="secondary" className="text-[10px]">
                                                            {typeProvisions.length}
                                                          </Badge>
                                                        </div>
                                                        {heritageType === 'control' && (
                                                          <span className="text-[10px] text-green-600">Must comply</span>
                                                        )}
                                                      </button>

                                                      {/* Heritage Type Provisions */}
                                                      {isTypeExpanded && (() => {
                                                        const selectedElement = elementFilters[typeKey];
                                                        const filteredProvisions = filterByElement(typeProvisions, selectedElement);
                                                        const elementTotals = heritageType === 'control' ? getElementTotals(typeProvisions) : null;

                                                        // Split results if element selected (not "All" or "General")
                                                        const shouldSplit = selectedElement && selectedElement !== '_general' && elementTotals;
                                                        const splitResults = shouldSplit ? splitByExclusivity(typeProvisions, selectedElement) : null;

                                                        // Get page grouping info for visual grouping
                                                        const pageGroupInfo = getPageGroupInfo(typeProvisions);

                                                        // Helper to render a provision card
                                                        const renderProvision = (provision: Provision, idx: number, showElementTags: boolean = false) => {
                                                          const layer = provision.layer || provision.v2_dcp_layer;
                                                          const layerBorderColor = layer === 'generic' ? 'border-l-slate-400' :
                                                            layer === 'use_specific' ? 'border-l-sky-400' :
                                                            layer === 'condition' ? 'border-l-amber-400' :
                                                            layer === 'precinct' ? 'border-l-emerald-400' : 'border-l-gray-300';
                                                          const zebraStripe = idx % 2 === 1 ? `${typeConfig.bg}` : 'bg-white';

                                                          // Check if this provision is part of a multi-provision page group
                                                          const groupInfo = pageGroupInfo.get(provision.id);
                                                          const isInGroup = !!groupInfo;
                                                          const isGroupStart = groupInfo?.isFirst;
                                                          const isGroupEnd = groupInfo?.isLast;
                                                          // Rounded corners: normal if not in group, top-only for first, bottom-only for last, none for middle
                                                          const groupRounding = !isInGroup ? 'rounded-lg' :
                                                            isGroupStart ? 'rounded-t-lg rounded-b-none' :
                                                            isGroupEnd ? 'rounded-b-lg rounded-t-none' : 'rounded-none';
                                                          // Remove bottom margin for grouped items except last
                                                          const groupMargin = isInGroup && !isGroupEnd ? 'mb-0' : '';

                                                          return (
                                                            <div
                                                              key={provision.id}
                                                              className={`${zebraStripe} border border-gray-200 ${groupRounding} overflow-hidden transition-all hover:shadow-md ${layerBorderColor} border-l-4 ${groupMargin} ${isInGroup && !isGroupEnd ? 'border-b-0' : ''}`}
                                                            >
                                                              <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50/50 border-b border-gray-100">
                                                                <div className="flex items-center gap-2 flex-wrap">
                                                                  {provision.v2_marker && (
                                                                    <span className="font-mono text-xs font-semibold text-slate-700">
                                                                      {provision.v2_marker}
                                                                    </span>
                                                                  )}
                                                                  <Badge className={`text-[10px] ${getLayerColor(layer)}`}>
                                                                    {getLayerLabel(layer)}
                                                                  </Badge>
                                                                  {showElementTags && provision.v2_heritage_element && provision.v2_heritage_element.length > 1 && (
                                                                    <span className="text-[9px] text-gray-500">
                                                                      [{provision.v2_heritage_element.map(e => ELEMENT_LABELS[e] || e).join(', ')}]
                                                                    </span>
                                                                  )}
                                                                </div>
                                                                {provision.pdf_page_image_url && showPdfButtonIds.has(provision.id) && (() => {
                                                                  // Use pdf_page (DCP page), fallback to URL extraction page
                                                                  const urlPage = parseInt(provision.pdf_page_image_url!.match(/page_(\d+)/)?.[1] || '0');
                                                                  const displayPage = provision.pdf_page || urlPage;
                                                                  return (
                                                                    <Button
                                                                      size="sm"
                                                                      variant="ghost"
                                                                      className="h-6 px-2 text-[10px] bg-teal-700 text-white hover:bg-teal-800"
                                                                      onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        setViewingPdfImage({
                                                                          url: provision.pdf_page_image_url!,
                                                                          page: displayPage
                                                                        });
                                                                      }}
                                                                    >
                                                                      <FileText className="h-3 w-3 mr-1" />
                                                                      View DCP Page {displayPage}
                                                                    </Button>
                                                                  );
                                                                })()}
                                                              </div>
                                                              <div className="px-3 py-2">
                                                                <div
                                                                  className={`text-sm text-gray-700 leading-relaxed cursor-pointer ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-2'}`}
                                                                  onClick={() => toggleProvision(provision.id)}
                                                                >
                                                                  <FormattedProvisionText
                                                                    text={stripSectionHeader(provision.provision_text, undefined)}
                                                                    compact
                                                                  />
                                                                </div>
                                                                {provision.provision_text.length > 200 && (
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
                                                        };

                                                        return (
                                                        <div className="p-2 space-y-1.5 bg-white">
                                                          {/* Element Filter - Only for Controls */}
                                                          {heritageType === 'control' && elementTotals && (
                                                            <div className="mb-3 p-2 bg-green-50 rounded-lg border border-green-200">
                                                              <div className="flex flex-wrap gap-1">
                                                                <button
                                                                  onClick={() => setElementFilter(typeKey, null)}
                                                                  className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                                                                    !selectedElement
                                                                      ? 'bg-green-600 text-white'
                                                                      : 'bg-white text-green-700 border border-green-300 hover:bg-green-100'
                                                                  }`}
                                                                >
                                                                  All ({typeProvisions.length})
                                                                </button>
                                                                {Array.from(elementTotals.totals).map(([elem, count]) => (
                                                                  <button
                                                                    key={elem}
                                                                    onClick={() => setElementFilter(typeKey, selectedElement === elem ? null : elem)}
                                                                    className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                                                                      selectedElement === elem
                                                                        ? 'bg-green-600 text-white'
                                                                        : 'bg-white text-green-700 border border-green-300 hover:bg-green-100'
                                                                    }`}
                                                                  >
                                                                    {ELEMENT_LABELS[elem] || elem} ({count})
                                                                  </button>
                                                                ))}
                                                                {elementTotals.generalCount > 0 && (
                                                                  <button
                                                                    onClick={() => setElementFilter(typeKey, selectedElement === '_general' ? null : '_general')}
                                                                    className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                                                                      selectedElement === '_general'
                                                                        ? 'bg-gray-500 text-white'
                                                                        : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-100'
                                                                    }`}
                                                                  >
                                                                    General ({elementTotals.generalCount})
                                                                  </button>
                                                                )}
                                                              </div>
                                                            </div>
                                                          )}

                                                          {/* Results - Split into sections if element selected */}
                                                          {splitResults ? (
                                                            <>
                                                              {/* Only this element section */}
                                                              {splitResults.onlyThis.length > 0 && (
                                                                <div className="mb-4">
                                                                  <div className="bg-green-100 border border-green-300 rounded-md px-3 py-1.5 mb-2">
                                                                    <p className="text-sm font-semibold text-green-800">
                                                                      {ELEMENT_LABELS[selectedElement] || selectedElement} only ({splitResults.onlyThis.length})
                                                                    </p>
                                                                  </div>
                                                                  <PageGroupedProvisions
                                                                    provisions={splitResults.onlyThis}
                                                                    expandedProvisions={expandedProvisions}
                                                                    onToggleProvision={toggleProvision}
                                                                    onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                                                    theme={{
                                                                      zebraStripeBg: typeConfig.bg,
                                                                      zebraStripeAltBg: 'bg-white',
                                                                      borderColorClass: 'border-green-200',
                                                                      textClampLines: 2,
                                                                      expandThreshold: 200,
                                                                    }}
                                                                    maxProvisions={isShowingAll ? undefined : 10}
                                                                  />
                                                                  {splitResults.onlyThis.length > 10 && (
                                                                    <button
                                                                      onClick={() => toggleShowAllHeritageType(typeKey)}
                                                                      className="w-full text-xs text-center py-1 text-green-600 hover:underline"
                                                                    >
                                                                      {isShowingAll ? '↑ Show fewer' : `Show all ${splitResults.onlyThis.length}`}
                                                                    </button>
                                                                  )}
                                                                </div>
                                                              )}

                                                              {/* Plus other elements section */}
                                                              {splitResults.plusOthers.length > 0 && (
                                                                <div>
                                                                  <div className="bg-amber-100 border border-amber-300 rounded-md px-3 py-1.5 mb-2">
                                                                    <p className="text-sm font-semibold text-amber-800">
                                                                      {ELEMENT_LABELS[selectedElement] || selectedElement} + other elements ({splitResults.plusOthers.length})
                                                                    </p>
                                                                  </div>
                                                                  <PageGroupedProvisions
                                                                    provisions={splitResults.plusOthers}
                                                                    expandedProvisions={expandedProvisions}
                                                                    onToggleProvision={toggleProvision}
                                                                    onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                                                    theme={{
                                                                      zebraStripeBg: 'bg-amber-50/50',
                                                                      zebraStripeAltBg: 'bg-white',
                                                                      borderColorClass: 'border-amber-200',
                                                                      textClampLines: 2,
                                                                      expandThreshold: 200,
                                                                    }}
                                                                    maxProvisions={isShowingAll ? undefined : 5}
                                                                  />
                                                                  {splitResults.plusOthers.length > 5 && (
                                                                    <button
                                                                      onClick={() => toggleShowAllHeritageType(typeKey)}
                                                                      className="w-full text-xs text-center py-1 text-amber-600 hover:underline"
                                                                    >
                                                                      {isShowingAll ? '↑ Show fewer' : `Show all ${splitResults.plusOthers.length}`}
                                                                    </button>
                                                                  )}
                                                                </div>
                                                              )}
                                                            </>
                                                          ) : (
                                                            /* Regular flat list for All or General */
                                                            <>
                                                              <PageGroupedProvisions
                                                                provisions={filteredProvisions}
                                                                expandedProvisions={expandedProvisions}
                                                                onToggleProvision={toggleProvision}
                                                                onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                                                theme={{
                                                                  zebraStripeBg: typeConfig.bg,
                                                                  zebraStripeAltBg: 'bg-white',
                                                                  borderColorClass: typeConfig.border,
                                                                  textClampLines: 2,
                                                                  expandThreshold: 200,
                                                                }}
                                                                maxProvisions={isShowingAll ? undefined : displayLimit}
                                                              />
                                                              {filteredProvisions.length > displayLimit && (
                                                                <button
                                                                  onClick={() => toggleShowAllHeritageType(typeKey)}
                                                                  className={`w-full text-xs text-center py-2 rounded ${isShowingAll ? 'text-gray-500 hover:text-gray-700' : `${typeConfig.accent} font-medium hover:underline`}`}
                                                                >
                                                                  {isShowingAll
                                                                    ? `↑ Show fewer (${displayLimit})`
                                                                    : `↓ Show all ${filteredProvisions.length} ${typeConfig.label.toLowerCase()}`
                                                                  }
                                                                </button>
                                                              )}
                                                            </>
                                                          )}
                                                        </div>
                                                        );
                                                      })()}
                                                    </div>
                                                  );
                                                })}
                                              </div>
                                            )}
                                          </div>
                                        );
                                      })}
                                    </div>
                                    )
                                  ) : (
                                    /* Regular provisions list for non-heritage or small heritage parts */
                                    (() => {
                                      const partFilterKey = `part-${partKey}`;
                                      const selectedPartElement = elementFilters[partFilterKey];
                                      const partElementTotals = topic.toLowerCase() === 'building form' ? getElementTotals(partProvisions) : null;
                                      const partFilteredProvisions = filterByElement(partProvisions, selectedPartElement);
                                      const partShouldSplit = selectedPartElement && selectedPartElement !== '_general' && partElementTotals;
                                      const partSplitResults = partShouldSplit ? splitByExclusivity(partProvisions, selectedPartElement) : null;

                                      // Helper to render a provision in this context
                                      const renderPartProvision = (provision: Provision, idx: number, showTags: boolean = false) => {
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
                                              <div className="flex items-center gap-2 flex-wrap">
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
                                              {provision.pdf_page_image_url && showPdfButtonIds.has(provision.id) && (() => {
                                                // Use pdf_page (DCP page), fallback to URL extraction page
                                                const urlPage = parseInt(provision.pdf_page_image_url!.match(/page_(\d+)/)?.[1] || '0');
                                                const displayPage = provision.pdf_page || urlPage;
                                                return (
                                                  <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-7 px-2 text-xs bg-teal-700 text-white hover:bg-teal-800"
                                                    onClick={(e) => {
                                                      e.stopPropagation();
                                                      setViewingPdfImage({
                                                        url: provision.pdf_page_image_url!,
                                                        page: displayPage
                                                      });
                                                    }}
                                                  >
                                                    <FileText className="h-3 w-3 mr-1" />
                                                    View DCP Page {displayPage}
                                                  </Button>
                                                );
                                              })()}
                                            </div>
                                            <div className="px-4 py-3">
                                              <div
                                                className={`text-sm text-gray-700 leading-relaxed cursor-pointer ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-3'}`}
                                                onClick={() => toggleProvision(provision.id)}
                                              >
                                                <FormattedProvisionText
                                                  text={stripSectionHeader(provision.provision_text, undefined)}
                                                  compact
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
                                        {/* Element Filter for Building Form */}
                                        {topic.toLowerCase() === 'building form' && partElementTotals && partElementTotals.totals.size > 0 && (
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
                                                  provisions={partSplitResults.onlyThis}
                                                  expandedProvisions={expandedProvisions}
                                                  onToggleProvision={toggleProvision}
                                                  onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                                  maxProvisions={20}
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
                                                  provisions={partSplitResults.plusOthers}
                                                  expandedProvisions={expandedProvisions}
                                                  onToggleProvision={toggleProvision}
                                                  onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                                  maxProvisions={10}
                                                />
                                              </div>
                                            )}
                                          </>
                                        ) : (
                                          /* Page-grouped provisions list */
                                          <PageGroupedProvisions
                                            provisions={partFilteredProvisions}
                                            expandedProvisions={expandedProvisions}
                                            onToggleProvision={toggleProvision}
                                            onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                                            maxProvisions={20}
                                          />
                                        )}
                                      </>
                                      );
                                    })()
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      // Small topic: Page-grouped provisions with collapsible page headers
                      <PageGroupedProvisions
                        provisions={provisions}
                        expandedProvisions={expandedProvisions}
                        onToggleProvision={toggleProvision}
                        onViewPdf={(url, page) => setViewingPdfImage({ url, page })}
                        showDcpPart={true}
                        maxProvisions={20}
                      />
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
