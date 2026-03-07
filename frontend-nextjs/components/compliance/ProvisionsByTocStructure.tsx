'use client';

/**
 * ProvisionsByTocStructure - TOC-based provision display
 *
 * Two-panel layout:
 * - Left: TocSidebar for navigation
 * - Right: Provisions for selected part/section
 */

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import useSWR from 'swr';
import { TocSidebar } from './TocSidebar';
import { PageGroupedProvisions, Provision } from './PageGroupedProvisions';
import { LayerExplanation } from './LayerExplanation';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, FileText, ChevronDown, Search, X, Ruler, Download } from 'lucide-react';
import { COUNCIL_CONFIGS } from '@/lib/council-config';
import { pdf } from '@react-pdf/renderer';
import { ProvisionReport, SEEDocument } from '@/components/pdf';
import { PropertyContext, ProvisionForPDF } from '@/lib/pdf/types';
import { SEEDocumentData } from '@/lib/see/types';
import { matchesSearchWithSynonyms, scoreProvision, getSearchSuggestions } from '@/lib/search-utils';
import { SearchAutocomplete } from '@/components/ui/SearchAutocomplete';
import { useDASession } from '@/hooks/useDASession';
import { DAIntakeModal } from './DAIntakeModal';
import { DAModeCard } from './DAModeCard';
import { getExcludableTopics, getTopicExclusionReason, normalizeTopicKey, autoPopulateFromConstraints, DEFAULT_INTAKE_ANSWERS, type IntakeAnswers } from '@/lib/see/intake';
import { buildPropertyContext, preparePdfProvisions, sanitizeText } from '@/lib/see/propertyContext';
import { NUMERIC_MEASUREMENT_RE, filterAndDedupeProvisions } from '@/lib/see/provisionUtils';
import { assembleDescription, buildSeeIntro } from '@/lib/see/devTypes';
import { buildPathwayDetermination, buildSeppControls, buildLepStandards } from '@/lib/see/seeBuilders';
import { DCPInterestForm } from './DCPInterestForm';
import { DcpFilterBar } from './DcpFilterBar';
import { DcpProvisionList } from './DcpProvisionList';
// TODO: Rework numeric checker feature - temporarily disabled
// import { NumericChecker, type NumericCheckValues } from './NumericChecker';
// import { checkProvisionsAgainstValues, type ComplianceResult } from '@/lib/numericCompliance';


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
  waverley: {
    generic: 'Waverley-wide',
    use_specific: 'Zone-Specific',
    condition: 'Heritage',
    precinct: 'Site-Specific Precinct',
  },
};

const DEFAULT_LAYER_LABELS: Record<string, string> = {
  generic: 'LGA-wide',
  use_specific: 'Zone-Specific',
  condition: 'Condition',
  precinct: 'Precinct',
};


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
  lga?: string;
  formerCouncil: string;
  zone?: string;
  heritage?: boolean;
  hcaName?: string;
  precinctId?: string;
  precinctName?: string;
  // PDF export data
  address?: string;
  hcaCode?: string;
  heritageItem?: boolean;
  heritageItemName?: string;
  heritageItemNumber?: string;
  // Real data for PDF context
  propertyData?: any;  // Full property data from NSW Planning Portal
  lepClauseData?: any; // LEP clause data (height, FSR, zone table, etc.)
  // DA Mode
  isDaMode?: boolean;
  /** Callback to enable/disable DA mode — button renders inside this component after provisions load */
  onToggleDaMode?: (enabled: boolean) => void;
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
  lga,
  formerCouncil,
  zone,
  heritage,
  hcaName,
  precinctId,
  precinctName,
  address,
  hcaCode,
  heritageItem,
  heritageItemName,
  heritageItemNumber,
  propertyData,
  lepClauseData,
  isDaMode = false,
  onToggleDaMode,
}: ProvisionsByTocStructureProps) {
  // Provision view: 'task' shows all provisions, 'structure' requires TOC selection
  const [provisionView, setProvisionView] = useState<'task' | 'structure'>('task');
  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [topicFilters, setTopicFilters] = useState<string[]>([]); // Multi-select topics
  const [layerFilter, setLayerFilter] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [searchScope, setSearchScope] = useState<'all' | 'filtered'>('all'); // Search all or filtered
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [refinements, setRefinements] = useState({
    mandatoryOnly: false,
    withMeasurements: false,
    objectivesOnly: false,
  });
  const [heritageTypeFilter, setHeritageTypeFilter] = useState<string | null>(null);
  const [pdfModal, setPdfModal] = useState<{ url: string; page: number } | null>(null);
  // PDF export always uses filtered provisions (respects layer, topic, and search filters)
  const [showExportModal, setShowExportModal] = useState(false); // PDF export modal visibility
  const [showTriageExcluded, setShowTriageExcluded] = useState(false);

  // TODO: Rework numeric checker feature - temporarily disabled
  // Numeric checker values
  // const [numericCheckValues, setNumericCheckValues] = useState<NumericCheckValues | undefined>(undefined);
  // const [complianceResults, setComplianceResults] = useState<ComplianceResult[]>([]);

  // DA Mode session
  const { sessionToken, isLoading: sessionIsLoading, daResponses, refreshResponses, developmentDescription, saveDescription, intakeAnswers, saveIntakeAnswers, topicAssertions, saveTopicAssertion, bulkSaveResponses } = useDASession(
    isDaMode ? (address || null) : null,
    formerCouncil,
    zone
  );

  // Intake modal state
  const [showIntakeModal, setShowIntakeModal] = useState(false);

  // Clear scope form fields whenever the address changes — form always starts fresh.
  // Intake answers and DA responses persist server-side via useDASession.
  useEffect(() => {
    setDevType('');
    setDevWorksText('');
    setClientRef('');
    setPreparedBy('');
  }, [address]);

  // Structured development description state
  const [devType, setDevType] = useState<string>('');
  const [devWorksText, setDevWorksText] = useState<string>('');
  const [clientRef, setClientRef] = useState<string>('');
  const [preparedBy, setPreparedBy] = useState<string>('');
  const devDescriptionLocal = useMemo(() => assembleDescription(devType, devWorksText), [devType, devWorksText]);
  const descriptionDebounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear any pending debounce on unmount to avoid state updates after teardown
  useEffect(() => {
    return () => {
      if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    };
  }, []);

  const handleDevTypeChange = (newType: string) => {
    setDevType(newType);
    if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    descriptionDebounceTimer.current = setTimeout(() => { saveDescription(assembleDescription(newType, devWorksText)); }, 800);
  };

  const handleDevWorksChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setDevWorksText(text);
    if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    descriptionDebounceTimer.current = setTimeout(() => { saveDescription(assembleDescription(devType, text)); }, 800);
  };

  const handleClientRefChange = (val: string) => setClientRef(val);
  const handlePreparedByChange = (val: string) => setPreparedBy(val);

  // Keep a ref so the effect below can call the latest refreshResponses without
  // re-registering the effect whenever the callback identity changes
  const refreshResponsesRef = useRef(refreshResponses);
  refreshResponsesRef.current = refreshResponses;

  // Load responses when DA Mode activates
  useEffect(() => {
    if (isDaMode && address) refreshResponsesRef.current();
  }, [isDaMode, address]);

  // Auto-open triage modal when DA mode is active and no answers have been saved yet.
  // Only fires when deps change — dismissing the modal does not re-trigger it in the
  // same session. On page reload, sessionToken changes and triggers again, reminding
  // the user to complete triage. DAIntakeModal resets its own state via useLayoutEffect.
  // Gate modal auto-open on sessionIsLoading to avoid race condition:
  // setSessionToken fires before loadResponses completes, so intakeAnswers is
  // briefly null even when a saved session exists. Wait until loading is done.
  useEffect(() => {
    if (isDaMode && sessionToken && !sessionIsLoading && intakeAnswers === null) {
      setShowIntakeModal(true);
    }
  }, [isDaMode, intakeAnswers, sessionToken, sessionIsLoading]);

  // Merge auto-answers from LEP constraints with saved intake answers.
  // Auto-answers fill unknowns; saved planner answers always override.
  const mergedIntakeAnswers = useMemo(() => {
    const autoAnswers = propertyData?.constraints
      ? autoPopulateFromConstraints({
          ...propertyData.constraints,
          // anefData lives at propertyData.anefData (top level), not inside constraints
          anefData: propertyData.anefData,
        })
      : {};
    // Saved answers take priority — planner override is preserved
    return { ...DEFAULT_INTAKE_ANSWERS, ...autoAnswers, ...(intakeAnswers ?? {}) };
  }, [intakeAnswers, propertyData?.constraints, propertyData?.anefData]);

  // Compute excludable topics from merged answers (auto-populated + saved planner answers).
  // mergedIntakeAnswers always has a value; auto-answers (flood=No etc.) take effect immediately.
  const excludableTopics = useMemo(() => {
    return getExcludableTopics(mergedIntakeAnswers);
  }, [mergedIntakeAnswers]);


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

  // If no formerCouncil, council DCP is not processed — skip fetch entirely
  const apiUrl = formerCouncil ? `/api/provisions/for-property?${params.toString()}` : null;

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
    meta?: {
      council_pdf_url?: string | null;
    };
  }>(apiUrl, fetcher, {
    dedupingInterval: 2000,   // Reduced from 60s to 2s - allow fresh data
    revalidateOnFocus: false, // Don't refetch on window focus
    revalidateOnMount: true,  // Always fetch on mount
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

  // Auto-select first part on load ONLY in structure mode
  useEffect(() => {
    if (provisionView === 'structure' && data?.data?.complete_toc && !selectedPart) {
      const parts = Object.keys(data.data.complete_toc);
      if (parts.length > 0) {
        // Sort parts numerically (extract number from "Part X" or "Chapter X")
        const sortedParts = parts.sort((a, b) => {
          const numA = parseInt(a.match(/\d+/)?.[0] || '999');
          const numB = parseInt(b.match(/\d+/)?.[0] || '999');
          return numA - numB;
        });
        setSelectedPart(sortedParts[0]);
      }
    }
  }, [provisionView, data, selectedPart]);

  // Debounce search input with 300ms delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Extract data with safe defaults (for use in hooks below) - memoized to prevent infinite loops
  const tocStructure = useMemo(() => data?.data?.by_toc || {}, [data?.data?.by_toc]);
  const completeTocStructure = useMemo(() => data?.data?.complete_toc || {}, [data?.data?.complete_toc]);
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

  // Filter and deduplicate provisions for the currently selected part/section.
  // Shared logic lives in filterAndDedupeProvisions (provisionUtils.ts).
  const selectedProvisions = useMemo(
    () => filterAndDedupeProvisions(rawSelectedProvisions),
    [rawSelectedProvisions],
  );

  // TODO: Rework numeric checker feature - temporarily disabled
  // Compute numeric compliance results when check values or provisions change
  // useEffect(() => {
  //   if (!numericCheckValues || !tocStructure) {
  //     setComplianceResults([]);
  //     return;
  //   }

  //   // Extract all provisions from TOC structure
  //   const allParts = Object.values(tocStructure);
  //   const allProvisions = allParts.flatMap((part: any) =>
  //     Object.values(part.sections || {}).flatMap((section: any) => section.provisions || [])
  //   );

  //   // Check provisions against user values
  //   const results = checkProvisionsAgainstValues(allProvisions, numericCheckValues);
  //   setComplianceResults(results);
  // }, [numericCheckValues, tocStructure]);

  // Get ALL provisions across all parts (for "export all" option and task mode).
  // Uses tocStructure (by_toc) which has actual provision data.
  // Shared filter+dedupe logic lives in filterAndDedupeProvisions (provisionUtils.ts).
  const allProvisions = useMemo(() => {
    if (!tocStructure || Object.keys(tocStructure).length === 0) return [];
    const flat = (Object.values(tocStructure) as any[]).flatMap((part: any) =>
      Object.values(part.sections || {}).flatMap((section: any) => section.provisions || [])
    );
    return filterAndDedupeProvisions(flat);
  }, [tocStructure]);

  // Base provisions - mode-aware: task mode shows all, structure mode shows selected
  const handleIntakeApply = useCallback(async (answers: IntakeAnswers) => {
    await saveIntakeAnswers(answers);        // throws on failure
    const excludable = getExcludableTopics(answers);
    const toExclude = allProvisions
      .filter(prov => {
        const t = normalizeTopicKey(prov.v2_topic);
        return t && excludable.has(t);
      })
      .map(prov => ({
        provision_id: prov.id,
        compliance_status: 'not_applicable',
        response_text: `Excluded by intake: ${getTopicExclusionReason(normalizeTopicKey(prov.v2_topic))}`,
      }));
    if (toExclude.length > 0) {
      await bulkSaveResponses(toExclude);   // throws on failure, updates daResponses Map locally
    }
    setShowIntakeModal(false);              // only reached on success
  }, [allProvisions, saveIntakeAnswers, bulkSaveResponses]);

  const handleIntakeSkip = useCallback(() => {
    setShowIntakeModal(false);
  }, []);

    const baseProvisions = useMemo(() => {
    if (provisionView === 'task') {
      // Task mode: ALL provisions across all parts
      return allProvisions;
    } else {
      // Structure mode: Current behavior (TOC-filtered)
      return selectedProvisions;
    }
  }, [provisionView, allProvisions, selectedProvisions]);

  // Heritage counts: Always use allProvisions (full unfiltered set) so the badge
  // shows stable property-level totals regardless of selected part/topic/search.
  const heritageProvisions = useMemo(() => {
    if (!allProvisions) return [];
    return allProvisions.filter((p: any) =>
      (p.v2_dcp_layer || p.layer) === 'condition' &&
      p.v2_marker?.toLowerCase() === 'heritage'
    );
  }, [allProvisions]);

  const generalHeritageCount = useMemo(() =>
    heritageProvisions.filter((p: any) => !p.v2_heritage_hca).length,
    [heritageProvisions]
  );
  const hcaSpecificCount = useMemo(() =>
    heritageProvisions.filter((p: any) => p.v2_heritage_hca).length,
    [heritageProvisions]
  );
  const totalHeritageCount = heritageProvisions.length;

  // Precomputed layer labels for the current council (used by DcpFilterBar)
  const layerLabels = COUNCIL_LAYER_LABELS[formerCouncil?.toLowerCase()] || DEFAULT_LAYER_LABELS;

  // Count provisions by layer (from base provisions - mode-aware)
  const layerCounts = useMemo(() => ({
    generic: baseProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'generic').length,
    use_specific: baseProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'use_specific').length,
    condition: baseProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'condition').length,
    precinct: baseProvisions.filter(p => (p.v2_dcp_layer || p.layer) === 'precinct').length,
  }), [baseProvisions]);

  // Layer-filtered base: applies active layer filter only
  // Used by both filteredProvisions (rendered list) and topic chips (counts).
  // TOC/negative pages/definitions already excluded upstream in baseProvisions
  const layerFilteredProvisions = useMemo(() => {
    if (!layerFilter) return baseProvisions;
    return baseProvisions.filter(p => (p.v2_dcp_layer || p.layer) === layerFilter);
  }, [baseProvisions, layerFilter]);

  // Apply search + topic filters, then sort by relevance or priority
  const filteredProvisions = useMemo(() => {
    // ALWAYS start with layer-filtered provisions if layer filter is active
    // This ensures layer filter works in both task and structure modes
    let filtered = layerFilter ? layerFilteredProvisions : baseProvisions;

    // Apply search if present (multi-field with synonyms)
    if (debouncedSearch) {
      // Search scope: 'all' searches across all provisions (ignoring topic filter),
      // but layer filter is always respected — searching "Summer Hill" in a layer-filtered
      // view should not pull in provisions from other layers.
      const searchBase = searchScope === 'all'
        ? (layerFilter ? layerFilteredProvisions : baseProvisions)
        : filtered;
      filtered = searchBase.filter(p => matchesSearchWithSynonyms(p, debouncedSearch));
    }

    // Multi-topic filter with OR logic (applied after search)
    if (topicFilters.length > 0) {
      filtered = filtered.filter(p => {
        const provisionTopic = p.v2_topic?.toLowerCase().replace(/ /g, '_');
        return topicFilters.some(topic => topic === provisionTopic);
      });
    }

    // Apply refinement filters
    if (refinements.mandatoryOnly) {
      filtered = filtered.filter(p => {
        // Mandatory = Controls (C) or critical priority
        return p.v2_marker?.startsWith('C') || p.v2_display_priority === 'critical';
      });
    }

    if (refinements.withMeasurements) {
      filtered = filtered.filter(p => {
        const text = p.provision_text || '';
        // Contains numeric measurements
        return NUMERIC_MEASUREMENT_RE.test(text);
      });
    }

    // X9: objectives-only filter
    if (refinements.objectivesOnly) {
      filtered = filtered.filter(p => p.v2_provision_type === 'objective');
    }

    // X10: heritage type filter (control / character / descriptive)
    if (heritageTypeFilter) {
      filtered = filtered.filter(p => p.v2_heritage_type === heritageTypeFilter);
    }

    // Topic assertion filter — remove provisions whose topic the planner has dismissed.
    // Heritage (condition layer) is never filtered — it has no dismissible topic.
    if (isDaMode && Object.keys(topicAssertions).length > 0) {
      const assertedOut = new Set(Object.keys(topicAssertions));
      filtered = filtered.filter(p => {
        if ((p.v2_dcp_layer || p.layer) === 'condition') return true;
        const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
        return !t || !assertedOut.has(t);
      });
    }

    // Sort by relevance if searching, otherwise by priority
    if (debouncedSearch) {
      // Rank by search relevance
      const context = { heritage, zone, precinct: precinctId };
      const scored = filtered.map(p => ({
        provision: p,
        score: scoreProvision(p, debouncedSearch, context)
      }));

      // Sort by score (highest first)
      scored.sort((a, b) => b.score - a.score);

      // Return just provisions
      return scored.map(s => s.provision);
    } else {
      // Sort by priority (default)
      return filtered.sort((a, b) => {
        const priorityOrder = { critical: 1, important: 2, guideline: 3, contextual: 4 };
        const aPriority = priorityOrder[a.v2_display_priority || 'important'] || 2;
        const bPriority = priorityOrder[b.v2_display_priority || 'important'] || 2;
        return aPriority - bPriority;
      });
    }
  }, [baseProvisions, layerFilteredProvisions, layerFilter, searchScope, debouncedSearch, topicFilters, refinements, heritageTypeFilter, heritage, zone, precinctId, isDaMode, topicAssertions]);

  // Triage split — lifted out of JSX so header count and provision list use the same values.
  const splitByTriage = isDaMode && excludableTopics.size > 0;
  const displayProvisions = useMemo(() => {
    if (!splitByTriage) return filteredProvisions;
    return filteredProvisions.filter(p => {
      const t = normalizeTopicKey(p.v2_topic);
      return !t || !excludableTopics.has(t);
    });
  }, [splitByTriage, filteredProvisions, excludableTopics]);
  const triageExcludedProvisions = useMemo(() => {
    if (!splitByTriage) return [];
    return filteredProvisions.filter(p => {
      const t = normalizeTopicKey(p.v2_topic);
      return t && excludableTopics.has(t);
    });
  }, [splitByTriage, filteredProvisions, excludableTopics]);


  // Get unique topics for filter chips — scoped to selected layer
  // Deduplicate by normalized key (lowercase) to avoid "Signage" and "signage" appearing separately
  const availableTopics = useMemo(() => {
    const topicMap = new Map<string, string>();
    layerFilteredProvisions.forEach(p => {
      if (p.v2_topic) {
        const normalized = normalizeTopicKey(p.v2_topic);
        // Prefer lowercase version if we have both "Signage" and "signage"
        if (!topicMap.has(normalized) || p.v2_topic === p.v2_topic.toLowerCase()) {
          topicMap.set(normalized, p.v2_topic);
        }
      }
    });
    return Array.from(topicMap.values()).sort();
  }, [layerFilteredProvisions]);

  // Check if any provisions have C/O markers (use baseProvisions - mode-aware)
  const hasMarkers = useMemo(() =>
    baseProvisions.some(p => p.v2_marker),
    [baseProvisions]
  );

  // Calculate priority stats per topic — scoped to selected layer
  const topicPriorityStats = useMemo(() => {
    const stats: Record<string, { critical: number; total: number }> = {};
    layerFilteredProvisions.forEach(p => {
      const topic = p.v2_topic?.toLowerCase().replace(/ /g, '_') || 'other';
      if (!stats[topic]) stats[topic] = { critical: 0, total: 0 };
      stats[topic].total++;

      // Only mark as "critical/numeric" if provision actually contains measurements
      const text = p.provision_text || '';
      // Comprehensive pattern matching planning regulation measurements
      const isObjective = /^O\d+|objective|principle|aim|purpose|encourages|promotes|protecting|minimising|preventing|ensuring|must be consistent|contribution|significance|character|attributes|elements that/i.test(text);
      if (NUMERIC_MEASUREMENT_RE.test(text) && !isObjective) stats[topic].critical++;
    });
    return stats;
  }, [layerFilteredProvisions]);

  // NOW handle loading/error states AFTER all hooks are called

  // No formerCouncil means council DCP not yet processed — show interest form immediately
  if (!formerCouncil) {
    return (
      <DCPInterestForm
        councilName={lga || 'your council'}
        address={address || ''}
      />
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-8 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-green-600 mr-2" />
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

  // No DCP data — council processed but returned empty. Show register-interest UI.
  if (!data?.data?.by_toc || Object.keys(tocStructure).length === 0) {
    return (
      <DCPInterestForm
        councilName={lga || formerCouncil || 'your council'}
        address={address || ''}
      />
    );
  }

  const handleSelectPart = (partId: string) => {
    setSelectedPart(partId);
    setSelectedSection(null);
    setTopicFilters([]); // Reset topic filters when changing parts
    setLayerFilter(null); // Reset layer filter when changing parts
  };

  const handleSelectSection = (partId: string, sectionId: string) => {
    setSelectedPart(partId);
    setSelectedSection(sectionId);
    setTopicFilters([]); // Reset topic filters when changing sections
    setLayerFilter(null); // Reset layer filter when changing sections
  };

  // Toggle topic filter (multi-select)
  const toggleTopic = (topic: string) => {
    setTopicFilters(prev =>
      prev.includes(topic)
        ? prev.filter(t => t !== topic)
        : [...prev, topic]
    );
  };

  // Toggle refinement filter
  const toggleRefinement = (key: keyof typeof refinements) => {
    setRefinements(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Mode switch handlers
  const enterTaskMode = () => {
    setProvisionView('task');
    setSelectedPart(null);
    setSelectedSection(null);
  };

  const enterStructureMode = () => {
    setProvisionView('structure');
    // Auto-select first part if none selected
    if (!selectedPart && Object.keys(completeTocStructure).length > 0) {
      const firstPart = Object.keys(completeTocStructure)[0];
      setSelectedPart(firstPart);
    }
  };

  // Export PDF handler
  const handleExportPdf = async () => {
    try {
      const heritageCtx = {
        in_hca: heritage || false,
        hca_name: hcaName,
        hca_code: hcaCode || hcaName,
        heritage_item: heritageItem,
        item_name: heritageItemName,
        item_number: heritageItemNumber,
      };
      const baseContext = buildPropertyContext(
        propertyData, lepClauseData, address, zone, formerCouncil,
        heritageCtx, devDescriptionLocal || undefined,
      );

      // Pattern Book CDC eligibility (PDF-only — not needed for SEE export)
      let patternBookData: PropertyContext['pattern_book_cdc'] = undefined;
      let pathwaySummary: PropertyContext['pathway_summary'] = undefined;
      try {
        const pbRes = await fetch('/api/pathway/pattern-book-eligibility', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ propertyData }),
        });
        if (pbRes.ok) {
          const pbResult = await pbRes.json();
          const eligibility = pbResult.data?.eligibility || pbResult;
          patternBookData = {
            status: eligibility.status || 'INELIGIBLE',
            exclusion_count: 217,
            numeric_standards_count: 199,
            override_rules_count: 9,
            blockers: eligibility.exclusionCheck?.exclusions?.map((e: any) => e.constraint) || [],
            pathway_timeframe: eligibility.status === 'ELIGIBLE' ? '10-day approval' : undefined,
          };
          const isResZone = ['R1', 'R2', 'R3', 'R4', 'RU5'].includes(zone?.split(' ')[0] || '');
          const isHousingZone = ['R1', 'R2', 'R3', 'R4'].includes(zone?.split(' ')[0] || '');
          const recommended =
            eligibility.status === 'ELIGIBLE' ? 'Pattern Book CDC' :
            isResZone ? 'Exempt & Complying Development' :
            isHousingZone && !heritage ? 'Housing SEPP (Low-Mid Rise)' :
            'Development Application (DA)';
          pathwaySummary = {
            recommended_pathway: recommended,
            pathways: [
              { name: 'Pattern Book CDC', status: eligibility.status === 'ELIGIBLE' ? 'Available' : eligibility.status === 'CONDITIONAL' ? 'Conditional' : 'Not Available', timeframe: '10 days', notes: eligibility.status === 'ELIGIBLE' ? undefined : patternBookData.blockers?.length ? patternBookData.blockers[0] : 'See exclusions' },
              { name: 'Exempt & Complying Development', status: isResZone ? 'Available' : 'Not Available', timeframe: '20 days', notes: isResZone ? 'For eligible work types (deck, fence, carport, pool)' : 'Zone not eligible' },
              { name: 'Housing SEPP (Low-Mid Rise)', status: isHousingZone && !heritage ? 'Available' : 'Not Available', timeframe: '25 days', notes: !isHousingZone ? 'Zone not eligible' : heritage ? 'Heritage area excluded' : undefined },
              { name: 'Development Application (DA)', status: 'Available', timeframe: '50+ days', notes: 'Always available — required when other pathways excluded' },
            ],
          };
        }
      } catch {
        // Continue without Pattern Book data
      }

      const propertyContext: PropertyContext = {
        ...baseContext,
        pattern_book_cdc: patternBookData,
        pathway_summary: pathwaySummary,
      };

      const provisionsForPdf = await preparePdfProvisions(filteredProvisions, daResponses ?? undefined);
      if (provisionsForPdf.length === 0) {
        alert('No provisions to export. Please adjust your filters.');
        return;
      }

      const activeFilters: string[] = [];
      if (layerFilter) {
        const councilLabels = formerCouncil?.toLowerCase() && COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()];
        const label = councilLabels ? councilLabels[layerFilter] : DEFAULT_LAYER_LABELS[layerFilter];
        activeFilters.push(label);
      }
      if (topicFilters.length > 0) activeFilters.push(topicFilters.map(t => t.replace(/_/g, ' ')).join(' + '));
      if (debouncedSearch) activeFilters.push(`Search: "${debouncedSearch}"`);
      if (refinements.mandatoryOnly) activeFilters.push('Mandatory only');
      if (refinements.withMeasurements) activeFilters.push('With measurements');
      if (refinements.objectivesOnly) activeFilters.push('Objectives only');
      if (heritageTypeFilter) activeFilters.push(`Heritage type: ${heritageTypeFilter}`);
      if (activeFilters.length === 0) activeFilters.push('All provisions for this property');

      const noFiltersActive = !layerFilter && topicFilters.length === 0 && !debouncedSearch;
      const hasResponses = isDaMode && daResponses && daResponses.size > 0;
      const doc = (
        <ProvisionReport
          provisions={provisionsForPdf}
          property={propertyContext}
          totalProvisions={totalProvisions}
          activeFilters={activeFilters}
          includeNonActionable={!noFiltersActive}
          isSeeMode={hasResponses}
          devType={devDescriptionLocal || undefined}
        />
      );

      const blob = await pdf(doc).toBlob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const dateStr = new Date().toISOString().split('T')[0];
      link.download = hasResponses
        ? `Draft-SEE-${formerCouncil}-${dateStr}.pdf`
        : `DCP-Provisions-${formerCouncil}-${dateStr}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Failed to generate PDF: ${error instanceof Error ? error.message : 'Unknown error'}. Check console for details.`);
    }
  };

  // SEE Draft export — uses SEEDocument with annotated provisions only
  const handleExportSee = async () => {
    try {
      // Refresh responses from DB before building PDF — ensures per-provision annotations
      // saved by DAResponseCapture (which doesn't update parent daResponses state) are current.
      await refreshResponses();

      const heritageCtx = {
        in_hca: heritage || false,
        hca_name: hcaName,
        hca_code: hcaCode || hcaName,
        heritage_item: heritageItem,
        item_name: heritageItemName,
        item_number: heritageItemNumber,
      };
      const propertyContext = buildPropertyContext(
        propertyData, lepClauseData, address, zone, formerCouncil,
        heritageCtx, devDescriptionLocal || undefined,
      );

      // Use filteredProvisions so topic assertions are already applied (asserted-out topics excluded).
      // filteredProvisions in DA mode has topicAssertions filter applied upstream.
      const provisionsForPdf = await preparePdfProvisions(filteredProvisions, daResponses ?? undefined);
      const annotatedProvisions = provisionsForPdf.filter(p => p.da_status);

      const pathwayDetermination = buildPathwayDetermination(
        propertyContext.zone,
        propertyContext.heritage_status?.in_hca ?? false,
        propertyContext.heritage_status?.heritage_item ?? false,
        propertyData?.constraints,
      );
      const seppAssessableControls = buildSeppControls(propertyData?.constraints, lepClauseData);
      const lepAssessableStandards = buildLepStandards(propertyContext, lepClauseData);

      const resolvedAddress = address || propertyData?.address || '';
      const seeData: SEEDocumentData = {
        property: propertyContext,
        development_description: devDescriptionLocal,
        see_intro: devType ? buildSeeIntro(devType, devWorksText, resolvedAddress) : undefined,
        annotated_provisions: annotatedProvisions,
        all_provisions: provisionsForPdf,
        generated_date: new Date().toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' }),
        ...(intakeAnswers ? { intake_answers: intakeAnswers } : {}),
        ...(clientRef.trim() ? { client_ref: clientRef.trim() } : {}),
        ...(preparedBy.trim() ? { prepared_by: preparedBy.trim() } : {}),
        pathway_determination: pathwayDetermination,
        ...(seppAssessableControls.length > 0 ? { sepp_assessable_controls: seppAssessableControls } : {}),
        ...(lepAssessableStandards.length > 0 ? { lep_assessable_standards: lepAssessableStandards } : {}),
        ...(Object.keys(topicAssertions).length > 0 ? {
          topic_assertions: Object.entries(topicAssertions).map(([topic, reason]) => ({ topic, reason })),
        } : {}),
      };

      const doc = <SEEDocument data={seeData} />;
      const blob = await pdf(doc).toBlob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const dateStr = new Date().toISOString().split('T')[0];
      link.download = `Draft-SEE-${formerCouncil}-${dateStr}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Failed to generate SEE PDF: ${error instanceof Error ? error.message : 'Unknown error'}. Check console for details.`);
    }
  };

  return (
    <div className="space-y-0">
      {/* Structured intake modal */}
      <DAIntakeModal
        open={showIntakeModal}
        onApply={handleIntakeApply}
        onSkip={handleIntakeSkip}
        provisions={allProvisions}
        initialAnswers={mergedIntakeAnswers}
        heritage={heritage}
        hcaName={hcaName}
        precinctName={precinctName}
        propertyConstraints={propertyData?.constraints}
      />

      {/* ① Enable DA Mode — rendered here so it only appears after provisions load */}
      {onToggleDaMode && (
        isDaMode ? (
          <div className="flex items-start gap-3 mb-5">
            <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">1</span>
            <div>
              <p className="text-sm font-semibold text-gray-800">DA Mode</p>
              <p className="text-xs text-gray-500 mt-0.5 mb-2">Active — record compliance positions against each provision and export a working SEE draft. Complete steps 2 and 3 below.</p>
              <button
                onClick={() => onToggleDaMode(false)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border bg-teal-600 text-white border-teal-600 shadow-sm transition-all"
              >
                <span className="w-3 h-3 rounded-full inline-block bg-white" />
                DA Mode on
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between mb-5">
            <p className="text-xs text-gray-500">Preparing a DA? Enable DA Mode to record compliance notes and export a working SEE draft.</p>
            <button
              onClick={() => onToggleDaMode(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border bg-white text-teal-700 border-teal-300 hover:bg-teal-50 transition-all flex-shrink-0 ml-3"
            >
              <span className="w-3 h-3 rounded-full inline-block bg-teal-300" />
              Enable DA Mode
            </button>
          </div>
        )
      )}

      {/* ② Set your scope — DA mode only */}
      {isDaMode && (
        <div className="flex items-start gap-3 mb-5">
          <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">2</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-800">Set your scope</p>
            <p className="text-xs text-gray-500 mt-0.5 mb-2">Name the development type, describe the works, then run triage to auto-exclude provisions that can't apply. After triage, hover any in-scope topic and click × to dismiss whole categories — Roof, Retail, Parking, Demolition — that have nothing to do with your works. What survives becomes your Schedule A.</p>
            <DAModeCard
              devType={devType}
              devWorksText={devWorksText}
              devDescriptionLocal={devDescriptionLocal}
              intakeAnswers={intakeAnswers}

              daResponses={daResponses}
              allProvisions={allProvisions}
              excludableTopics={excludableTopics}
              onDevTypeChange={handleDevTypeChange}
              onDevWorksChange={handleDevWorksChange}
              onRunIntake={() => setShowIntakeModal(true)}
              clientRef={clientRef}
              preparedBy={preparedBy}
              onClientRefChange={handleClientRefChange}
              onPreparedByChange={handlePreparedByChange}
              lepHeight={lepClauseData?.height_limit || undefined}
              lepFsr={lepClauseData?.fsr || undefined}
              heritage={heritage}
              hcaName={hcaName}
              precinctName={precinctName}
              layerCounts={layerCounts}
              genericLabel={layerLabels.generic}
              topicAssertions={topicAssertions}
              onAssertTopicNA={saveTopicAssertion}
            />
          </div>
        </div>
      )}

      {/* ③ Review provisions — DA mode only */}
      {isDaMode && (
        <div className="flex items-start gap-3 mb-3">
          <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">3</span>
          <div>
            <p className="text-sm font-semibold text-gray-800">Review applicable provisions</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Work through each applicable provision below. Record Complies, Varies, or N/A — triage has already removed controls that cannot apply. Export your SEE draft when done.
            </p>
          </div>
        </div>
      )}

      {/* Main two-panel layout */}
      <div className="flex border rounded-lg bg-white">
      {/* Left: TOC Sidebar - Only in structure mode */}
      {provisionView === 'structure' && (
        <div className="w-64 border-r bg-gray-50 flex-shrink-0 overflow-hidden rounded-l-lg">
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
      )}

      {/* Right: Provisions content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {provisionView === 'task' ? (
                  'DCP Provisions'
                ) : selectedPart ? (
                  sanitizeText(completeTocStructure[selectedPart]?.part_name) || selectedPart
                ) : (
                  'Select a section'
                )}
              </h3>
              {provisionView === 'task' ? (
                <p className="text-xs text-gray-400 mt-0.5">
                  {isDaMode
                    ? 'Filter by topic, review each provision, record your compliance status.'
                    : 'Filter by topic to focus on one area, or search.'}
                </p>
              ) : (
                <button onClick={enterTaskMode} className="text-xs text-teal-600 hover:underline mt-0.5">
                  ← Back to topic view
                </button>
              )}
              {provisionView === 'structure' && selectedSection && selectedPart && (
                <p className="text-sm text-gray-600 mt-0.5">
                  {sanitizeText(completeTocStructure[selectedPart]?.sections[selectedSection]?.section_title)}
                </p>
              )}
              {/* X22: Lot dimensions — compact context bar */}
              {(propertyData?.lotDimensions?.area || propertyData?.lotDimensions?.frontage) && (
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  {propertyData.lotDimensions.area && (
                    <span className="text-xs bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">
                      {Math.round(propertyData.lotDimensions.area).toLocaleString()}m²
                    </span>
                  )}
                  {propertyData.lotDimensions.frontage && (
                    <span className="text-xs bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">
                      {propertyData.lotDimensions.frontage.toFixed(1)}m frontage
                    </span>
                  )}
                  {propertyData.lotDimensions.lotType && (
                    <span className="text-xs bg-gray-100 text-gray-600 rounded px-1.5 py-0.5 capitalize">
                      {propertyData.lotDimensions.lotType}
                    </span>
                  )}
                  {/* X14: high canopy coverage note */}
                  {propertyData?.constraints?.treeCanopy?.coverageClass &&
                    /high/i.test(propertyData.constraints.treeCanopy.coverageClass) && (
                    <span className="text-xs bg-green-100 text-green-800 border border-green-200 rounded px-1.5 py-0.5">
                      🌳 {propertyData.constraints.treeCanopy.coverageClass} canopy — confirm tree impacts
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-gray-900">
                {displayProvisions.length}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                <>of {allProvisions.length} for property</>
              </div>
            </div>
          </div>

          <DcpFilterBar
            searchQuery={searchQuery}
            onSearchQueryChange={(v) => { setSearchQuery(v); setShowAutocomplete(true); }}
            debouncedSearch={debouncedSearch}
            showAutocomplete={showAutocomplete}
            onShowAutocompleteChange={setShowAutocomplete}
            searchScope={searchScope}
            onSearchScopeChange={setSearchScope}
            baseProvisions={baseProvisions}
            layerFilteredProvisions={layerFilteredProvisions}
            filteredProvisions={filteredProvisions}
            availableTopics={availableTopics}
            topicFilters={topicFilters}
            onToggleTopic={toggleTopic}
            onClearTopics={() => setTopicFilters([])}
            topicPriorityStats={topicPriorityStats}
            excludableTopics={excludableTopics}
            refinements={refinements}
            onToggleRefinement={toggleRefinement}
            heritageTypeFilter={heritageTypeFilter}
            onHeritageTypeFilterChange={setHeritageTypeFilter}
            layerFilter={layerFilter}
            onLayerFilterChange={setLayerFilter}
            layerCounts={layerCounts}
            layerLabels={layerLabels}
            zone={zone}
            heritage={heritage}
            hcaName={hcaName}
            precinctName={precinctName}
            formerCouncil={formerCouncil}
            generalHeritageCount={generalHeritageCount}
            hcaSpecificCount={hcaSpecificCount}
            totalHeritageCount={totalHeritageCount}
            showExportModal={showExportModal}
            onShowExportModal={setShowExportModal}
            onExportPdf={handleExportPdf}
            selectedPart={selectedPart}
            provisionView={provisionView}
          />

        </div>

        {/* Action Toolbar - Export */}
        {filteredProvisions.length > 0 && (
          <div className="px-4 py-3 border-b bg-gray-50">
            {isDaMode ? (
              <button
                onClick={handleExportSee}
                title="Export working draft — requires professional review before DA lodgement"
                className="w-full flex items-center gap-2 px-3 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors"
              >
                <FileText className="h-4 w-4 flex-shrink-0" />
                <div className="text-left">
                  <div className="text-sm font-medium">Export SEE Draft</div>
                  <div className="text-xs font-normal opacity-80">Working draft — requires professional review</div>
                </div>
              </button>
            ) : (
              <button
                onClick={() => setShowExportModal(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
              >
                <Download className="h-4 w-4" />
                {topicFilters.length > 0
                  ? `Export ${filteredProvisions.length} ${topicFilters.map(t => t.replace(/_/g, ' ')).join(' + ')} provision${filteredProvisions.length !== 1 ? 's' : ''}`
                  : `Export ${filteredProvisions.length === allProvisions.length ? 'all ' : ''}${filteredProvisions.length} provision${filteredProvisions.length !== 1 ? 's' : ''}`}
              </button>
            )}
          </div>
        )}

        {/* Provisions list */}
        <DcpProvisionList
          displayProvisions={displayProvisions}
          triageExcludedProvisions={triageExcludedProvisions}
          filteredProvisions={filteredProvisions}
          hasMarkers={hasMarkers}
          showTriageExcluded={showTriageExcluded}
          onToggleTriageExcluded={() => setShowTriageExcluded(v => !v)}
          councilPdfUrl={data?.meta?.council_pdf_url ?? undefined}
          formerCouncil={formerCouncil}
          zone={zone}
          heritage={heritage}
          hcaName={hcaName}
          precinctId={precinctId}
          isDaMode={isDaMode}
          sessionToken={sessionToken}
          daResponses={daResponses}
          excludableTopics={excludableTopics}
          onViewPdf={(url, page) => setPdfModal({ url, page })}
          debouncedSearch={debouncedSearch}
          provisionView={provisionView}
          layerFilter={layerFilter}
          onClearLayer={() => setLayerFilter(null)}
          topicFilters={topicFilters}
          onClearTopics={() => setTopicFilters([])}
          searchScope={searchScope}
          onSearchScopeChange={setSearchScope}
          onSearchQueryChange={setSearchQuery}
          baseProvisions={baseProvisions}
        />

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
