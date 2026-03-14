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
import { TocSidebar, formatPartDisplay } from './TocSidebar';
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
import { DAModeCard } from './DAModeCard';
import { getExcludableTopics, getTopicExclusionReason, normalizeTopicKey, autoPopulateFromConstraints, DEFAULT_INTAKE_ANSWERS, type IntakeAnswers } from '@/lib/see/intake';
import { buildPropertyContext, preparePdfProvisions, sanitizeText } from '@/lib/see/propertyContext';
import { NUMERIC_MEASUREMENT_RE, filterAndDedupeProvisions } from '@/lib/see/provisionUtils';
import { assembleDescription, buildSeeIntro, DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';
import { deriveIntakeFromScope, getScopeDevTypeTags } from '@/lib/see/ancillaryWorks';
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

// DA mode: sort generic/use_specific provisions before precinct, and condition (heritage) last.
const DA_LAYER_SORT_ORDER: Record<string, number> = {
  generic: 1, use_specific: 2, precinct: 3, condition: 4,
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

  // On DA mode activation: switch to Document view (requires TOC for chapter dismissal).
  // On exit: intentionally preserve the current view — don't reset user's navigation context.
  useEffect(() => {
    if (isDaMode) setProvisionView('structure');
  }, [isDaMode]);
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
  const [showSuppressedInDA, setShowSuppressedInDA] = useState(false); // Toggle to show suppressed (objective/descriptive) provisions in DA mode

  // TODO: Rework numeric checker feature - temporarily disabled
  // Numeric checker values
  // const [numericCheckValues, setNumericCheckValues] = useState<NumericCheckValues | undefined>(undefined);
  // const [complianceResults, setComplianceResults] = useState<ComplianceResult[]>([]);

  // DA Mode session
  const { sessionToken, isLoading: sessionIsLoading, daResponses, refreshResponses, updateSingleResponse, developmentDescription, saveDescription, intakeAnswers, saveIntakeAnswers, ancillaryWorks: savedAncillaryWorks, saveScope, topicAssertions, saveTopicAssertion, chapterAssertions, saveChapterAssertion, bulkSaveResponses } = useDASession(
    isDaMode ? (address || null) : null,
    formerCouncil,
    zone
  );

  // Clear scope form fields whenever the address changes — form always starts fresh.
  // Intake answers and DA responses persist server-side via useDASession.
  useEffect(() => {
    setDevType('');
    setDevWorksText('');
    setAncillaryWorksLocal([]);
    setClientRef('');
    setPreparedBy('');
  }, [address]);

  // Structured development description state
  const [devType, setDevType] = useState<string>('');
  const [devWorksText, setDevWorksText] = useState<string>('');
  const [ancillaryWorksLocal, setAncillaryWorksLocal] = useState<string[]>([]);
  const [clientRef, setClientRef] = useState<string>('');
  const [preparedBy, setPreparedBy] = useState<string>('');
  const devDescriptionLocal = useMemo(() => assembleDescription(devType, ancillaryWorksLocal, devWorksText), [devType, ancillaryWorksLocal, devWorksText]);
  const descriptionDebounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Refs for latest values — avoids stale closures in debounced callbacks
  const devTypeRef = useRef(devType);
  devTypeRef.current = devType;
  const devWorksTextRef = useRef(devWorksText);
  devWorksTextRef.current = devWorksText;
  const intakeAnswersRef = useRef(intakeAnswers);
  intakeAnswersRef.current = intakeAnswers;


  // Clear any pending debounce on unmount to avoid state updates after teardown
  useEffect(() => {
    return () => {
      if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    };
  }, []);

  const handleDevTypeChange = (newType: string) => {
    setDevType(newType);
    if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    descriptionDebounceTimer.current = setTimeout(() => { saveDescription(assembleDescription(newType, ancillaryWorksLocal, devWorksText)); }, 800);
  };

  const handleAncillaryWorksChange = (works: string[]) => {
    setAncillaryWorksLocal(works);
    if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    descriptionDebounceTimer.current = setTimeout(() => {
      // Use refs to avoid stale closures in debounced callback
      const currentDevType = devTypeRef.current;
      const currentWorksText = devWorksTextRef.current;
      const currentIntake = intakeAnswersRef.current;
      const autoAnswers = propertyData?.constraints
        ? autoPopulateFromConstraints({ ...propertyData.constraints, anefData: propertyData.anefData })
        : {};
      const derived = deriveIntakeFromScope(currentDevType, works);
      const merged = { ...DEFAULT_INTAKE_ANSWERS, ...autoAnswers, ...derived, ...(currentIntake ?? {}) } as IntakeAnswers;
      saveScope(currentDevType, works, currentWorksText, merged);
    }, 800);
  };

  const handleDevWorksChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setDevWorksText(text);
    if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    descriptionDebounceTimer.current = setTimeout(() => { saveDescription(assembleDescription(devType, ancillaryWorksLocal, text)); }, 800);
  };

  const handleClientRefChange = (val: string) => setClientRef(val);
  const handlePreparedByChange = (val: string) => setPreparedBy(val);
  const handleProposedValuesChange = (field: 'proposed_height' | 'proposed_gfa', value: string) => {
    if (intakeAnswers) {
      saveIntakeAnswers({ ...intakeAnswers, [field]: value });
    }
  };

  // Keep a ref so the effect below can call the latest refreshResponses without
  // re-registering the effect whenever the callback identity changes
  const refreshResponsesRef = useRef(refreshResponses);
  refreshResponsesRef.current = refreshResponses;

  // Load responses when DA Mode activates
  useEffect(() => {
    if (isDaMode && address) refreshResponsesRef.current();
  }, [isDaMode, address]);

  // Restore ancillary works from session when loaded
  useEffect(() => {
    if (savedAncillaryWorks.length > 0 && ancillaryWorksLocal.length === 0) {
      setAncillaryWorksLocal(savedAncillaryWorks);
    }
  }, [savedAncillaryWorks]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-derive intake from scope (dev type + ancillary checkboxes).
  // When ancillary works are selected, intake is auto-derived — no modal needed.
  // Scope-derived answers layer between auto-answers and saved planner overrides.
  const scopeDerivedIntake = useMemo(() => {
    if (!devType && ancillaryWorksLocal.length === 0) return {};
    return deriveIntakeFromScope(devType, ancillaryWorksLocal);
  }, [devType, ancillaryWorksLocal]);

  // Auto-save scope when ancillary or devType changes (debounced via description timer)
  const scopeSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    return () => { if (scopeSaveTimer.current) clearTimeout(scopeSaveTimer.current); };
  }, []);

  // Intake is auto-derived from dev type + ancillary checkboxes.
  // No manual modal interaction needed — scope automatically updates.

  // Merge auto-answers from LEP constraints + scope-derived + saved planner answers.
  // Priority: defaults < auto-from-constraints < saved planner overrides < scope-derived
  // Scope-derived answers take precedence because they're auto-determined by current dev type + ancillary works.
  // When dev type/ancillary changes, scope-derived must override any previously-saved answers.
  const mergedIntakeAnswers = useMemo(() => {
    const autoAnswers = propertyData?.constraints
      ? autoPopulateFromConstraints({
          ...propertyData.constraints,
          // anefData lives at propertyData.anefData (top level), not inside constraints
          anefData: propertyData.anefData,
        })
      : {};
    return { ...DEFAULT_INTAKE_ANSWERS, ...autoAnswers, ...(intakeAnswers ?? {}), ...scopeDerivedIntake };
  }, [intakeAnswers, propertyData?.constraints, propertyData?.anefData, scopeDerivedIntake]);

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
  // dev_types intentionally excluded from URL — provisions are property-specific, not dev-type-specific.
  // Relevance and chapter match counts are computed client-side from v2_applicable_dev_types.

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
      chapter_pdf_urls?: Record<string, string> | null;
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

  // Expanded dev type tags — computed client-side, no network round-trip needed
  const expandedDevTypes = useMemo(
    () => (isDaMode && devType) ? getScopeDevTypeTags(devType, ancillaryWorksLocal) : [],
    [isDaMode, devType, ancillaryWorksLocal]
  );

  // Overlay relevance_level/relevance_reason on provisions from v2_applicable_dev_types.
  // Keeps the SWR cache key stable (property-only) — dev type changes never trigger a refetch.
  const tocStructure = useMemo(() => {
    const base = data?.data?.by_toc || {};
    if (expandedDevTypes.length === 0) return base;
    const result: Record<string, any> = {};
    for (const [partId, part] of Object.entries(base as Record<string, any>)) {
      result[partId] = {
        ...part,
        sections: Object.fromEntries(
          Object.entries(part.sections || {}).map(([secId, sec]: [string, any]) => [
            secId,
            {
              ...sec,
              provisions: (sec.provisions || []).map((p: any) => {
                const appTypes = p.v2_applicable_dev_types as string[] | null;
                const isPrimary = appTypes && expandedDevTypes.some((t: string) => appTypes.includes(t));
                const isGeneral = !appTypes || appTypes.includes('ALL');
                return {
                  ...p,
                  relevance_level: isPrimary ? 'primary' : isGeneral ? 'general' : 'secondary',
                  relevance_reason: isPrimary
                    ? 'Specifically written for selected development type'
                    : isGeneral
                    ? 'Applies to all development types'
                    : 'May apply if objectives relevant (EP&A Act s 4.15)',
                };
              }),
            },
          ])
        ),
      };
    }
    return result;
  }, [data?.data?.by_toc, expandedDevTypes]);

  const totalProvisions = data?.data?.summary?.total_provisions || 0;

  // Get provisions for selected part/section - memoized to avoid unnecessary recalculations
  const rawSelectedProvisions = useMemo(() => {
    if (!selectedPart || !tocStructure[selectedPart]) return [];

    const part = tocStructure[selectedPart];

    if (selectedSection && part.sections[selectedSection]) {
      return part.sections[selectedSection].provisions;
    }

    // Return all provisions for the part
    return (Object.values(part.sections) as any[]).flatMap(s => s.provisions);
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
    const deduped = filterAndDedupeProvisions(flat);

    console.log('[AllProvisions] Constructed:', {
      flatCount: flat.length,
      dedupedCount: deduped.length,
      byLayer: {
        generic: deduped.filter(p => (p.v2_dcp_layer || p.layer) === 'generic').length,
        use_specific: deduped.filter(p => (p.v2_dcp_layer || p.layer) === 'use_specific').length,
        condition: deduped.filter(p => (p.v2_dcp_layer || p.layer) === 'condition').length,
        precinct: deduped.filter(p => (p.v2_dcp_layer || p.layer) === 'precinct').length,
      },
      byType: {
        control: deduped.filter(p => p.v2_provision_type === 'control').length,
        objective: deduped.filter(p => p.v2_provision_type === 'objective').length,
        other: deduped.filter(p => !p.v2_provision_type || (p.v2_provision_type !== 'control' && p.v2_provision_type !== 'objective')).length,
      },
      byHeritageType: {
        descriptive: deduped.filter(p => p.v2_heritage_type === 'descriptive').length,
        other: deduped.filter(p => !p.v2_heritage_type || p.v2_heritage_type !== 'descriptive').length,
      },
    });

    return deduped;
  }, [tocStructure]);

  // Per-part filtered provision counts — matches what the right panel actually shows.
  // by_toc.provision_count is the raw API count (includes TOC entries, non-actionable, definitions).
  // Must account for intake triage so numbers match the assessment scope.
  const filteredPartCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    // In DA mode: exclude both intake-filtered topics AND objectives/descriptives
    // This makes DCP structure total match the waterfall (363, not 395)
    let provisionsToCount = allProvisions;

    console.log('[FilteredPartCounts] Starting:', {
      allProvisionsCount: allProvisions.length,
      isDaMode,
    });

    if (isDaMode) {
      provisionsToCount = allProvisions.filter(p => {
        // Exclude intake-triaged provisions by structural category (DD-1)
        if (excludableTopics.size > 0) {
          const cat = p.v2_structural_category;
          if (cat && excludableTopics.has(cat)) return false;
        }
        // Exclude objectives and heritage descriptives (hidden in DA mode)
        if (p.v2_provision_type === 'objective') return false;
        if (p.v2_heritage_type === 'descriptive') return false;
        return true;
      });

      console.log('[FilteredPartCounts] After DA filters:', {
        beforeCount: allProvisions.length,
        afterCount: provisionsToCount.length,
        filtered: allProvisions.length - provisionsToCount.length,
      });
    }

    for (const p of provisionsToCount) {
      const partId = (p.v2_dcp_part && p.v2_dcp_part !== 'unknown')
        ? p.v2_dcp_part
        : (p.source_chapter_key || 'Other');
      counts[partId] = (counts[partId] || 0) + 1;
    }

    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    console.log('[FilteredPartCounts] Final result:', { counts, total });

    return counts;
  }, [allProvisions, isDaMode, excludableTopics]);

  // completeTocStructure: overlay dev_type_match_count client-side from allProvisions.
  // complete_toc has no provision data (just structure) so we derive counts from allProvisions.
  const completeTocStructure = useMemo(() => {
    const base = data?.data?.complete_toc || {};
    if (expandedDevTypes.length === 0 || allProvisions.length === 0) return base;
    const matchCounts: Record<string, number> = {};
    for (const p of allProvisions) {
      const part = (p as any).v2_dcp_part;
      if (!part) continue;
      if ((p as any).relevance_level !== 'secondary') {
        matchCounts[part] = (matchCounts[part] || 0) + 1;
      }
    }
    const result: Record<string, any> = {};
    for (const [partId, partData] of Object.entries(base as Record<string, any>)) {
      result[partId] = { ...partData, dev_type_match_count: matchCounts[partId] ?? 0 };
    }
    return result;
  }, [data?.data?.complete_toc, allProvisions, expandedDevTypes]);

  // Intake filtering is now handled by handleAncillaryWorksChange via ancillary work checkboxes
  // Modal-based questions have been removed in favor of the cleaner checkbox UI

    const baseProvisions = useMemo(() => {
    let base;
    if (provisionView === 'task') {
      // Task mode: ALL provisions across all parts
      base = allProvisions;
    } else {
      // Structure mode: Current behavior (TOC-filtered)
      base = selectedProvisions;
    }

    console.log('[BaseProvisions] Set:', {
      provisionView,
      count: base.length,
      byLayer: {
        generic: base.filter(p => (p.v2_dcp_layer || p.layer) === 'generic').length,
        use_specific: base.filter(p => (p.v2_dcp_layer || p.layer) === 'use_specific').length,
        condition: base.filter(p => (p.v2_dcp_layer || p.layer) === 'condition').length,
        precinct: base.filter(p => (p.v2_dcp_layer || p.layer) === 'precinct').length,
      },
    });

    return base;
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

  // Count provisions by layer (must match DCP structure total = 363)
  // CRITICAL: Use allProvisions (not baseProvisions) so layer breakdown shows ALL provisions in scope,
  // not just the ones in the current view. This ensures consistency with filteredPartCounts.
  // In DA mode: apply intake triage + chapter/topic dismissals + objectives/descriptives hiding
  // so layerCounts sum matches the waterfall scopeTotal
  const layerCounts = useMemo(() => {
    let base = allProvisions;

    console.log('[LayerCounts] Starting calculation:', {
      allProvisionsCount: allProvisions.length,
      isDaMode,
      excludableTopicsSize: excludableTopics.size,
      chapterAssertionsCount: Object.keys(chapterAssertions).length,
      topicAssertionsCount: Object.keys(topicAssertions).length,
    });

    // In DA mode: apply ALL filters to match DCP structure total
    if (isDaMode) {
      const assertedChapters = new Set(Object.keys(chapterAssertions));
      const assertedTopics = new Set(Object.keys(topicAssertions));

      console.log('[LayerCounts] DA Mode - applying filters:', {
        assertedChapters: Array.from(assertedChapters),
        assertedTopics: Array.from(assertedTopics),
        excludableTopic: Array.from(excludableTopics),
      });

      const beforeCount = base.length;
      base = allProvisions.filter(p => {
        // Exclude intake-triaged provisions by structural category (DD-1)
        if (excludableTopics.size > 0) {
          const cat = p.v2_structural_category;
          if (cat && excludableTopics.has(cat)) return false;
        }

        // Exclude objectives and heritage descriptives (hidden in DA mode)
        if (p.v2_provision_type === 'objective') return false;
        if (p.v2_heritage_type === 'descriptive') return false;

        // Heritage (condition layer) is never filtered by chapter/topic assertions
        if ((p.v2_dcp_layer || p.layer) === 'condition') return true;

        // Check chapter dismissal
        const chKey = (p.v2_dcp_part && p.v2_dcp_part !== 'unknown') ? p.v2_dcp_part : p.source_chapter_key;
        if (chKey && assertedChapters.has(chKey)) return false;

        // Check topic dismissal
        const topic = normalizeTopicKey(p.v2_topic);
        if (topic && assertedTopics.has(topic)) return false;

        return true;
      });

      console.log('[LayerCounts] After DA filters:', {
        beforeCount,
        afterCount: base.length,
        filtered: beforeCount - base.length,
      });
    }

    const counts = {
      generic: base.filter(p => (p.v2_dcp_layer || p.layer) === 'generic').length,
      use_specific: base.filter(p => (p.v2_dcp_layer || p.layer) === 'use_specific').length,
      condition: base.filter(p => (p.v2_dcp_layer || p.layer) === 'condition').length,
      precinct: base.filter(p => (p.v2_dcp_layer || p.layer) === 'precinct').length,
    };

    const total = counts.generic + counts.use_specific + counts.condition + counts.precinct;
    console.log('[LayerCounts] Final breakdown:', counts, { total });

    return counts;
  }, [allProvisions, isDaMode, chapterAssertions, topicAssertions, excludableTopics]);

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

    // Topic filter removed — v2_topic labels are unreliable (30% false positive rate).
    // Structural navigation (DCP ToC) replaces topic-based filtering.

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

    // Chapter assertion filter — remove provisions whose DCP chapter the planner has dismissed.
    // Heritage (condition layer) is never filtered.
    if (isDaMode && Object.keys(chapterAssertions).length > 0) {
      const assertedChapters = new Set(Object.keys(chapterAssertions));
      filtered = filtered.filter(p => {
        if ((p.v2_dcp_layer || p.layer) === 'condition') return true;
        const chKey = (p.v2_dcp_part && p.v2_dcp_part !== 'unknown') ? p.v2_dcp_part : p.source_chapter_key;
        return !chKey || !assertedChapters.has(chKey);
      });
    }

    // DA mode: suppress objective provisions AND heritage descriptive provisions.
    // Objectives (v2_provision_type = 'objective') and heritage descriptives
    // (v2_heritage_type = 'descriptive') are policy intent statements, not enforceable
    // controls — they are not assessed individually in a SEE compliance table.
    // Can be toggled back on for audit/transparency via showSuppressedInDA.
    if (isDaMode && !showSuppressedInDA) {
      filtered = filtered.filter(p =>
        p.v2_provision_type !== 'objective' &&
        p.v2_heritage_type !== 'descriptive'
      );
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
      // Sort by priority (default), with DA mode layer-based tiebreaker (heritage last)
      return filtered.sort((a, b) => {
        const priorityOrder = { critical: 1, important: 2, guideline: 3, contextual: 4 };
        if (isDaMode) {
          const aLayer = DA_LAYER_SORT_ORDER[a.v2_dcp_layer || a.layer] ?? 2;
          const bLayer = DA_LAYER_SORT_ORDER[b.v2_dcp_layer || b.layer] ?? 2;
          if (aLayer !== bLayer) return aLayer - bLayer;
        }
        const aPriority = priorityOrder[a.v2_display_priority || 'important'] || 2;
        const bPriority = priorityOrder[b.v2_display_priority || 'important'] || 2;
        return aPriority - bPriority;
      });
    }
  }, [baseProvisions, layerFilteredProvisions, layerFilter, searchScope, debouncedSearch, refinements, heritageTypeFilter, heritage, zone, precinctId, isDaMode, topicAssertions, chapterAssertions]);

  // Scope helper — true when a provision is in the active DA assessment scope
  const isInDaScope = useCallback((p: any) => {
    const cat = p.v2_structural_category;
    if (cat && excludableTopics.has(cat)) return false;            // intake triage (DD-1: structural)
    const topic = normalizeTopicKey(p.v2_topic);
    if (topic && topicAssertions[topic]) return false;             // planner dismissed topic
    if (p.v2_provision_type === 'objective') return false;         // objectives hidden in DA
    if (p.v2_heritage_type === 'descriptive') return false;        // heritage descriptives hidden
    const chKey = (p.v2_dcp_part && p.v2_dcp_part !== 'unknown')
      ? p.v2_dcp_part : (p.source_chapter_key || 'unknown');
    if (chapterAssertions[chKey]) return false;                    // planner dismissed chapter
    return true;
  }, [excludableTopics, topicAssertions, chapterAssertions]);

  // Per-chapter assessment progress — scope-aware, used by TocSidebar progress bars
  const chapterProgress = useMemo(() => {
    if (!isDaMode) return undefined;
    const map: Record<string, { assessed: number; total: number }> = {};
    for (const p of allProvisions) {
      if (!isInDaScope(p)) continue;
      const chKey = (p.v2_dcp_part && p.v2_dcp_part !== 'unknown')
        ? p.v2_dcp_part : (p.source_chapter_key || 'unknown');
      if (!map[chKey]) map[chKey] = { assessed: 0, total: 0 };
      map[chKey].total++;
      if (daResponses.has(p.id)) map[chKey].assessed++;
    }
    return map;
  }, [isDaMode, allProvisions, daResponses, isInDaScope]);

  // Global progress with reduction waterfall — single source of truth for all DA progress UI
  const globalProgress = useMemo(() => {
    if (!isDaMode) return null;
    const total = allProvisions.length;
    let triaged = 0, chapterDismissed = 0, topicDismissed = 0, suppressed = 0;
    let scopeTotal = 0, assessed = 0;
    for (const p of allProvisions) {
      const cat = p.v2_structural_category;
      const topic = normalizeTopicKey(p.v2_topic);
      const chKey = (p.v2_dcp_part && p.v2_dcp_part !== 'unknown')
        ? p.v2_dcp_part : (p.source_chapter_key || 'unknown');
      // Count each exclusion reason (priority order — first match wins)
      if (cat && excludableTopics.has(cat)) { triaged++; continue; }
      if (chapterAssertions[chKey]) { chapterDismissed++; continue; }
      if (topic && topicAssertions[topic]) { topicDismissed++; continue; }
      if (p.v2_provision_type === 'objective' || p.v2_heritage_type === 'descriptive') { suppressed++; continue; }
      scopeTotal++;
      if (daResponses.has(p.id)) assessed++;
    }
    return { total, triaged, chapterDismissed, topicDismissed, suppressed, scopeTotal, assessed, remaining: scopeTotal - assessed };
  }, [isDaMode, allProvisions, daResponses, excludableTopics, topicAssertions, chapterAssertions]);

  // Count of non-actionable provisions hidden in DA mode (objectives + heritage descriptives)
  const hiddenObjectiveCount = useMemo(() => {
    if (!isDaMode) return 0;
    return baseProvisions.filter(p =>
      p.v2_provision_type === 'objective' || p.v2_heritage_type === 'descriptive'
    ).length;
  }, [isDaMode, baseProvisions]);

  // Triage split — lifted out of JSX so header count and provision list use the same values.
  const splitByTriage = isDaMode && excludableTopics.size > 0;
  const displayProvisions = useMemo(() => {
    if (!splitByTriage) return filteredProvisions;
    return filteredProvisions.filter(p => {
      const cat = p.v2_structural_category;
      return !cat || !excludableTopics.has(cat);
    });
  }, [splitByTriage, filteredProvisions, excludableTopics]);
  const triageExcludedProvisions = useMemo(() => {
    if (!splitByTriage) return [];
    return filteredProvisions.filter(p => {
      const cat = p.v2_structural_category;
      return cat && excludableTopics.has(cat);
    });
  }, [splitByTriage, filteredProvisions, excludableTopics]);


  // Topic chips removed — v2_topic labels unreliable. Structure view replaces topic navigation.
  const availableTopics: string[] = [];

  // Check if any provisions have C/O markers (use baseProvisions - mode-aware)
  const hasMarkers = useMemo(() =>
    baseProvisions.some(p => p.v2_marker),
    [baseProvisions]
  );

  // Topic priority stats removed — topic chips no longer displayed
  const topicPriorityStats: Record<string, { critical: number; total: number }> = {};

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

  // Auto-navigate to next active chapter after dismiss
  const handleAssertChapter = async (chapterKey: string, reason: string | null) => {
    await saveChapterAssertion(chapterKey, reason);
    // On dismiss (not undo), navigate to next active chapter
    if (reason !== null && selectedPart === chapterKey) {
      const parts = Object.keys(completeTocStructure);
      const updatedAssertions = { ...chapterAssertions, [chapterKey]: reason };
      const nextPart = parts.find(p => p !== chapterKey && !updatedAssertions[p] && completeTocStructure[p]?.provision_count > 0);
      if (nextPart) {
        handleSelectPart(nextPart);
      }
    }
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
      const lepAssessableStandards = buildLepStandards(propertyContext, lepClauseData, {
        height: intakeAnswers?.proposed_height,
        gfa: intakeAnswers?.proposed_gfa,
        lotArea: propertyData?.lotDimensions?.area ?? propertyContext.lot_dimensions?.area,
      });

      const resolvedAddress = address || propertyData?.address || '';
      const seeData: SEEDocumentData = {
        property: propertyContext,
        development_description: devDescriptionLocal,
        see_intro: devType ? buildSeeIntro(devType, ancillaryWorksLocal, devWorksText, resolvedAddress) : undefined,
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
        ...(Object.keys(chapterAssertions).length > 0 ? {
          chapter_assertions: Object.entries(chapterAssertions).map(([chapterKey, reason]) => {
            const { label, desc } = formatPartDisplay(chapterKey);
            return { chapter_key: chapterKey, chapter_label: label, chapter_desc: desc || '', reason };
          }),
        } : {}),
        ...(ancillaryWorksLocal.length > 0 ? { ancillary_works: ancillaryWorksLocal } : {}),
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
      {/* Intake filtering via ancillary checkboxes in assessment page — no modal needed */}

      {/* ① Enable DA Mode — rendered here so it only appears after provisions load */}
      {onToggleDaMode && (
        isDaMode ? (
          <div className="flex items-start gap-3 mb-5">
            <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">1</span>
            <div>
              <p className="text-base font-semibold text-gray-800">DA Mode active</p>
              <p className="text-sm text-gray-700 mt-0.5 mb-3">Tell us what you're actually building, and we'll filter to only the rules that matter for your project. Then assess each provision and export your SEE draft.</p>
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
            <p className="text-base font-semibold text-gray-800">Define your works</p>
            <p className="text-sm text-gray-700 mt-0.5 mb-2">Select your development type and any ancillary development. Controls that don't apply are automatically removed.</p>
            <DAModeCard
              devType={devType}
              devWorksText={devWorksText}
              devDescriptionLocal={devDescriptionLocal}
              intakeAnswers={intakeAnswers}
              ancillaryWorks={ancillaryWorksLocal}
              onAncillaryWorksChange={handleAncillaryWorksChange}
              daResponses={daResponses}
              allProvisions={allProvisions}
              excludableTopics={excludableTopics}
              onDevTypeChange={handleDevTypeChange}
              onDevWorksChange={handleDevWorksChange}
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
              onProposedValuesChange={handleProposedValuesChange}
              globalProgress={globalProgress}
            />
          </div>
        </div>
      )}

      {/* ③ Review provisions — DA mode only */}
      {isDaMode && (
        <div className="flex items-start gap-3 mb-3">
          <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">3</span>
          <div>
            <p className="text-base font-semibold text-gray-800">Assess applicable provisions</p>
            <p className="text-sm text-gray-700 mt-0.5">
              Use the DCP chapter list on the left to dismiss entire chapters that don{"'"}t apply. Use the topic filter chips to focus on one category at a time. For each remaining provision, record:{' '}
              <span className="inline-flex items-center gap-0.5">
                <span className="px-1.5 py-0.5 rounded border text-xs font-medium bg-green-100 text-green-800 border-green-300">Complies</span>
                {', '}
                <span className="px-1.5 py-0.5 rounded border text-xs font-medium bg-amber-100 text-amber-800 border-amber-300">Varies</span>
                {', or '}
                <span className="px-1.5 py-0.5 rounded border text-xs font-medium bg-gray-100 text-gray-600 border-gray-300">N/A</span>
              </span>
              .
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
            filteredPartCounts={filteredPartCounts}
            selectedPart={selectedPart}
            selectedSection={selectedSection}
            onSelectPart={handleSelectPart}
            onSelectSection={handleSelectSection}
            formerCouncil={formerCouncil}
            isDaMode={isDaMode}
            chapterAssertions={chapterAssertions}
            onAssertChapter={handleAssertChapter}
            chapterProgress={chapterProgress}
            devType={isDaMode && devType ? getScopeDevTypeTags(devType, ancillaryWorksLocal).join(',') : undefined}
            devTypeLabel={isDaMode && devType ? DEV_TYPE_OPTIONS.find(o => o.value === devType)?.label : undefined}
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
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                {/* View mode toggle — only shown when TOC data exists for this council */}
                {Object.keys(completeTocStructure).length > 1 && (
                  <div className="inline-flex rounded border border-gray-200 text-xs overflow-hidden flex-shrink-0">
                    <button
                      onClick={enterTaskMode}
                      className={`px-2.5 py-1 transition-colors ${provisionView === 'task' ? 'bg-gray-800 text-white' : 'text-gray-500 hover:bg-gray-50'}`}
                    >
                      Topic
                    </button>
                    <button
                      onClick={enterStructureMode}
                      className={`px-2.5 py-1 transition-colors border-l border-gray-200 ${provisionView === 'structure' ? 'bg-gray-800 text-white' : 'text-gray-500 hover:bg-gray-50'}`}
                    >
                      Document
                    </button>
                  </div>
                )}
                {provisionView === 'task' && (
                  <p className="text-xs text-gray-400">
                    {isDaMode ? 'Filter by topic, review each provision.' : 'Filter by topic or search.'}
                  </p>
                )}
              </div>
              {provisionView === 'structure' && selectedSection && selectedPart && (
                <p className="text-sm text-gray-600 mt-0.5">
                  {sanitizeText(completeTocStructure[selectedPart]?.sections[selectedSection]?.section_title)}
                </p>
              )}
              {/* X14: high canopy coverage note — only relevant context for DCP provisions */}
              {propertyData?.constraints?.treeCanopy?.coverageClass &&
                /high/i.test(propertyData.constraints.treeCanopy.coverageClass) && (
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-xs bg-green-100 text-green-800 border border-green-200 rounded px-1.5 py-0.5">
                    🌳 {propertyData.constraints.treeCanopy.coverageClass} canopy — confirm tree impacts
                  </span>
                </div>
              )}
            </div>
            <div className="text-right">
              {isDaMode && globalProgress ? (
                <>
                  {/* Waterfall: one line showing how we got from total to scope */}
                  <div className="text-xs text-gray-400 mb-1">
                    {globalProgress.total} total
                    {globalProgress.total !== globalProgress.scopeTotal && (
                      <> → {globalProgress.scopeTotal} in scope</>
                    )}
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {globalProgress.assessed}
                    <span className="text-base font-normal text-gray-400"> / {globalProgress.scopeTotal}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">provisions assessed</div>
                  {displayProvisions.length < globalProgress.scopeTotal && (
                    <div className="text-xs text-gray-400 mt-0.5">
                      viewing {displayProvisions.length}
                      {topicFilters.length > 0 && ` (topic: ${topicFilters.join(', ')})`}
                      {layerFilter && !topicFilters.length && ` (layer: ${layerFilter})`}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-gray-900">{displayProvisions.length}</div>
                  <div className="text-xs text-gray-500 mt-0.5">of {allProvisions.length} for property</div>
                </>
              )}
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
            isDaMode={isDaMode}
          />

        </div>

        {/* Action Toolbar - Export */}
        {filteredProvisions.length > 0 && (
          <div className="px-4 py-3 border-b bg-gray-50">
            {isDaMode ? (
              <div className="space-y-2">
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
                {hiddenObjectiveCount > 0 && (
                  <p className="text-xs text-gray-400 text-center">
                    {hiddenObjectiveCount} objective{hiddenObjectiveCount !== 1 ? 's' : ''} hidden — disable DA Mode to view
                  </p>
                )}
              </div>
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
          chapterPdfUrls={data?.meta?.chapter_pdf_urls ?? undefined}
          formerCouncil={formerCouncil}
          zone={zone}
          heritage={heritage}
          hcaName={hcaName}
          precinctId={precinctId}
          isDaMode={isDaMode}
          sessionToken={sessionToken}
          daResponses={daResponses}
          excludableTopics={excludableTopics}
          onResponseSaved={updateSingleResponse}
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
          showSuppressedInDA={showSuppressedInDA}
          onToggleSuppressedInDA={() => setShowSuppressedInDA(v => !v)}
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
