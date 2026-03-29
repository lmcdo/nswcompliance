'use client';

// State management hook for the ProvisionsByTopic browser.
// Centralises all SWR fetching, derived data, and toggle handlers so the
// component stays a thin renderer.

import { useState, useEffect, useMemo } from 'react';
import useSWR from 'swr';
import { COUNCIL_CONFIGS, CouncilConfig } from '@/lib/council-config';
import {
  Provision, LayerResult,
  hcaNameToSlug, heritageItemNumberToSlug,
  getProvisionsWithPdfButton, sortTopicsByPriority,
  formatDcpPart as pureFmtDcpPart,
  formatHcaName as pureFmtHcaName,
  getLayerLabel, getLayerColor,
} from '@/lib/provision-grouping';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProvisionsByTopicInput {
  zone?: string;
  heritage?: boolean;
  flood?: boolean;
  precinctId?: string;
  selectedDevType: string;
  council?: string;
  hcaName?: string;
  heritageItemNumber?: string;
  professionalMode?: 'certifier' | 'planner';
}

export interface ProvisionBrowserReturn {
  // Fetched data
  data: { by_layer: LayerResult[]; by_topic: Record<string, Provision[]>; summary: any } | undefined;
  isLoading: boolean;
  error: Error | undefined;
  // Derived counts
  originalTopicCounts: Record<string, number>;
  showPdfButtonIds: Set<number>;
  propertyHcaSlug: string;
  // Sorted/filtered topics ready to render
  topics: [string, Provision[]][];
  // Council config
  councilConfig: CouncilConfig | null;
  // UI state
  selectedDevType: string;
  setSelectedDevType: (v: string) => void;
  selectedTopic: string;
  setSelectedTopic: (v: string) => void;
  expandedTopics: Set<string>;
  expandedProvisions: Set<number>;
  expandedDcpParts: Set<string>;
  expandedHcas: Set<string>;
  expandedHeritageTypes: Set<string>;
  showAllHeritageTypes: Set<string>;
  elementFilters: Record<string, string>;
  viewingPdfImage: { url: string; page: number } | null;
  setViewingPdfImage: (v: { url: string; page: number } | null) => void;
  showInnerWestOverview: boolean;
  setShowInnerWestOverview: (v: boolean) => void;
  // Toggle handlers
  toggleTopic: (t: string) => void;
  toggleProvision: (id: number) => void;
  toggleDcpPart: (key: string) => void;
  toggleHca: (key: string) => void;
  toggleHeritageType: (key: string) => void;
  toggleShowAllHeritageType: (key: string) => void;
  setElementFilter: (key: string, element: string | null) => void;
  // Formatting helpers (need runtime context)
  formatDcpPart: (part: string) => string;
  formatHcaName: (hca: string) => string;
  isPropertyHca: (hca: string) => boolean;
  getLayerLabel: (layer: string | null | undefined) => string;
  getLayerColor: (layer: string | null | undefined) => string;
  // Thresholds
  DCP_PART_GROUPING_THRESHOLD: number;
  HCA_GROUPING_THRESHOLD: number;
}

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch provisions');
  const json = await res.json();
  if (!json.success) throw new Error(json.error || 'Unknown error');
  return json.data;
};

function makeToggle(setter: React.Dispatch<React.SetStateAction<Set<string>>>) {
  return (key: string) => {
    setter(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useProvisionBrowser({
  zone, heritage = false, flood = false, precinctId,
  selectedDevType: initialDevType,
  council, hcaName, heritageItemNumber,
  professionalMode = 'certifier',
}: ProvisionsByTopicInput & { selectedDevType?: string }): ProvisionBrowserReturn {

  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());
  const [expandedProvisions, setExpandedProvisions] = useState<Set<number>>(new Set());
  const [expandedDcpParts, setExpandedDcpParts] = useState<Set<string>>(new Set());
  const [expandedHcas, setExpandedHcas] = useState<Set<string>>(new Set());
  const [expandedHeritageTypes, setExpandedHeritageTypes] = useState<Set<string>>(new Set());
  const [showAllHeritageTypes, setShowAllHeritageTypes] = useState<Set<string>>(new Set());
  const [elementFilters, setElementFiltersState] = useState<Record<string, string>>({});
  const [selectedDevType, setSelectedDevType] = useState(initialDevType || '');
  const [selectedTopic, setSelectedTopic] = useState('');
  const [viewingPdfImage, setViewingPdfImage] = useState<{ url: string; page: number } | null>(null);
  const [showInnerWestOverview, setShowInnerWestOverview] = useState(false);

  const DCP_PART_GROUPING_THRESHOLD = 50;
  const HCA_GROUPING_THRESHOLD = 100;

  const councilConfig = council ? (COUNCIL_CONFIGS[council] ?? null) : null;
  const topicOrder = councilConfig
    ? (professionalMode === 'certifier' ? councilConfig.topicOrder.certifier : councilConfig.topicOrder.planner)
    : [];

  const apiUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (zone) params.set('zone', zone);
    if (heritage) params.set('heritage', 'true');
    if (flood) params.set('flood', 'true');
    if (precinctId) params.set('precinct_id', precinctId);
    if (selectedDevType) params.set('dev_type', selectedDevType);
    if (council) params.set('former_council', council);
    if (heritageItemNumber && /^[CA]\d+$/i.test(heritageItemNumber)) {
      params.set('hca', heritageItemNumber);
    } else if (hcaName) {
      params.set('hca', hcaNameToSlug(hcaName));
    }
    return `/api/provisions/for-property?${params}`;
  }, [zone, heritage, flood, precinctId, selectedDevType, council, hcaName, heritageItemNumber]);

  const { data, error, isLoading } = useSWR<{
    by_layer: LayerResult[];
    by_topic: Record<string, Provision[]>;
    summary: any;
  }>(apiUrl, fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 60000,
  });

  const originalTopicCounts = useMemo(() => {
    if (!data?.by_topic) return {};
    const counts: Record<string, number> = {};
    Object.entries(data.by_topic).forEach(([topic, provisions]) => {
      counts[topic] = (provisions as Provision[]).length;
    });
    return counts;
  }, [data?.by_topic]);

  const showPdfButtonIds = useMemo(() => {
    if (!data?.by_topic) return new Set<number>();
    const all: Provision[] = [];
    Object.values(data.by_topic).forEach(provisions => all.push(...(provisions as Provision[])));
    return getProvisionsWithPdfButton(all);
  }, [data?.by_topic]);

  const propertyHcaSlug = useMemo(() => {
    if (heritageItemNumber) return heritageItemNumberToSlug(heritageItemNumber);
    if (hcaName) return hcaNameToSlug(hcaName);
    return '';
  }, [heritageItemNumber, hcaName]);

  const topics = useMemo<[string, Provision[]][]>(() => {
    if (!data?.by_topic) return [];
    const entries = Object.entries(data.by_topic);
    const sorted = sortTopicsByPriority(entries.map(([name]) => name), topicOrder);
    const filtered = selectedTopic ? sorted.filter(n => n === selectedTopic) : sorted;
    return filtered
      .map(name => {
        const entry = entries.find(([n]) => n === name);
        if (!entry) return [name, []] as [string, Provision[]];
        return entry as [string, Provision[]];
      })
      .filter(([, provisions]) => (provisions as Provision[]).length > 0);
  }, [data?.by_topic, topicOrder, selectedTopic]);

  // Reset selected topic when property changes
  useEffect(() => {
    setSelectedTopic('');
  }, [zone, heritage, flood, precinctId, council]);

  // Auto-expand first 3 topics on initial load
  useEffect(() => {
    if (data?.by_topic && expandedTopics.size === 0) {
      const topicNames = Object.keys(data.by_topic);
      const sorted = sortTopicsByPriority(topicNames, topicOrder);
      setExpandedTopics(new Set(sorted.slice(0, 3)));
    }
  }, [data?.by_topic, topicOrder, expandedTopics.size]);

  // Toggle callbacks
  const toggleTopic = makeToggle(setExpandedTopics);
  const toggleDcpPart = makeToggle(setExpandedDcpParts);
  const toggleHca = makeToggle(setExpandedHcas);
  const toggleHeritageType = makeToggle(setExpandedHeritageTypes);
  const toggleShowAllHeritageType = makeToggle(setShowAllHeritageTypes);

  const toggleProvision = (id: number) => {
    setExpandedProvisions(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const setElementFilter = (typeKey: string, element: string | null) => {
    setElementFiltersState(prev => {
      if (element === null) {
        const next = { ...prev };
        delete next[typeKey];
        return next;
      }
      return { ...prev, [typeKey]: element };
    });
  };

  // Formatting helpers bound to runtime state
  const fmtDcpPart = (part: string) => pureFmtDcpPart(part, council);
  const fmtHcaName = (hca: string) => pureFmtHcaName(hca);
  const isPropertyHca = (hca: string) => propertyHcaSlug !== '' && hca === propertyHcaSlug;

  return {
    data,
    isLoading,
    error,
    originalTopicCounts,
    showPdfButtonIds,
    propertyHcaSlug,
    topics,
    councilConfig,
    selectedDevType,
    setSelectedDevType,
    selectedTopic,
    setSelectedTopic,
    expandedTopics,
    expandedProvisions,
    expandedDcpParts,
    expandedHcas,
    expandedHeritageTypes,
    showAllHeritageTypes,
    elementFilters,
    viewingPdfImage,
    setViewingPdfImage,
    showInnerWestOverview,
    setShowInnerWestOverview,
    toggleTopic,
    toggleProvision,
    toggleDcpPart,
    toggleHca,
    toggleHeritageType,
    toggleShowAllHeritageType,
    setElementFilter,
    formatDcpPart: fmtDcpPart,
    formatHcaName: fmtHcaName,
    isPropertyHca,
    getLayerLabel,
    getLayerColor,
    DCP_PART_GROUPING_THRESHOLD,
    HCA_GROUPING_THRESHOLD,
  };
}
