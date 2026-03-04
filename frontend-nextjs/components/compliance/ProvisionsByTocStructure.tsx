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
import { getExcludableTopics, getTopicExclusionReason, normalizeTopicKey, type IntakeAnswers } from '@/lib/see/intake';
import { assembleDescription, buildSeeIntro } from '@/lib/see/devTypes';
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
  precinctName,
  address,
  hcaCode,
  heritageItem,
  heritageItemName,
  heritageItemNumber,
  propertyData,
  lepClauseData,
  isDaMode = false,
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
  });
  const [pdfModal, setPdfModal] = useState<{ url: string; page: number } | null>(null);
  // PDF export always uses filtered provisions (respects layer, topic, and search filters)
  const [showExportModal, setShowExportModal] = useState(false); // PDF export modal visibility
  const [showTriageExcluded, setShowTriageExcluded] = useState(false);

  // TODO: Rework numeric checker feature - temporarily disabled
  // Numeric checker values
  // const [numericCheckValues, setNumericCheckValues] = useState<NumericCheckValues | undefined>(undefined);
  // const [complianceResults, setComplianceResults] = useState<ComplianceResult[]>([]);

  // DA Mode session
  const { sessionToken, daResponses, refreshResponses, developmentDescription, saveDescription, intakeAnswers, saveIntakeAnswers, bulkSaveResponses } = useDASession(
    isDaMode ? (address || null) : null,
    formerCouncil,
    zone
  );

  // Intake modal state
  const [showIntakeModal, setShowIntakeModal] = useState(false);

  // Restore per-address UI state from localStorage when the address changes
  useEffect(() => {
    if (!address) return;
    const savedDevType = localStorage.getItem(`ce_devType_${address}`) || '';
    const savedDevWorksText = localStorage.getItem(`ce_devWorksText_${address}`) || '';
    const savedClientRef = localStorage.getItem(`ce_clientRef_${address}`) || '';
    const savedPreparedBy = localStorage.getItem(`ce_preparedBy_${address}`) || '';
    setDevType(savedDevType);
    setDevWorksText(savedDevWorksText);
    setClientRef(savedClientRef);
    setPreparedBy(savedPreparedBy);
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
    if (address) localStorage.setItem(`ce_devType_${address}`, newType);
    if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    descriptionDebounceTimer.current = setTimeout(() => { saveDescription(assembleDescription(newType, devWorksText)); }, 800);
  };

  const handleDevWorksChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setDevWorksText(text);
    if (address) localStorage.setItem(`ce_devWorksText_${address}`, text);
    if (descriptionDebounceTimer.current) clearTimeout(descriptionDebounceTimer.current);
    descriptionDebounceTimer.current = setTimeout(() => { saveDescription(assembleDescription(devType, text)); }, 800);
  };

  const handleClientRefChange = (val: string) => {
    setClientRef(val);
    if (address) localStorage.setItem(`ce_clientRef_${address}`, val);
  };

  const handlePreparedByChange = (val: string) => {
    setPreparedBy(val);
    if (address) localStorage.setItem(`ce_preparedBy_${address}`, val);
  };

  // Keep a ref so the effect below can call the latest refreshResponses without
  // re-registering the effect whenever the callback identity changes
  const refreshResponsesRef = useRef(refreshResponses);
  refreshResponsesRef.current = refreshResponses;

  // Load responses when DA Mode activates
  useEffect(() => {
    if (isDaMode && address) refreshResponsesRef.current();
  }, [isDaMode, address]);


  // Compute excludable topics from intake answers
  const excludableTopics = useMemo(() => {
    if (!intakeAnswers) return new Set<string>();
    return getExcludableTopics(intakeAnswers);
  }, [intakeAnswers]);


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

  // Deduplicate provisions by text content (safety net for any DB/API duplicates)
  // Strip C1/O1/01 markers and normalize whitespace before comparison
  // Also exclude TOC, definitions, and non-actionable provisions
  // NOTE: Do NOT filter by negative page numbers - they're just PDF numbering artifacts
  const selectedProvisions = useMemo(() => {
    // First pass: Exclude non-provisions
    const validProvisions = rawSelectedProvisions.filter(p => {
      const text = p.provision_text || '';

      // Exclude TOC entries (by type or pattern)
      if (p.v2_provision_type === 'TOC') return false;

      // Text-based TOC detection: multiple section numbers in sequence
      const sectionNumberPattern = /\d+\.\d+(?:\.\d+)*\s+[A-Z][a-z]/g;
      const sectionMatches = text.match(sectionNumberPattern);
      if (sectionMatches && sectionMatches.length >= 3) return false;

      // Exclude non-actionable provisions (intro text, section headers, cross-references)
      if (p.v2_is_actionable === false) return false;

      // Exclude definitions
      const isDefinitions =
        text.includes('KEY TERMS') ||
        (text.includes('Definitions') && text.includes('means a')) ||
        p.v2_topic?.toLowerCase() === 'definitions';
      if (isDefinitions) return false;

      return true;
    });

    // Second pass: Deduplicate
    const seenTexts = new Set<string>();
    return validProvisions.filter(p => {
      // Normalize: strip markers, collapse whitespace
      const normalized = (p.provision_text || '')
        .replace(/^(C|O)?\d+\s+/gm, '')  // Strip "C1 ", "O1 ", "01 " from line starts
        .replace(/\s+/g, ' ')  // Collapse all whitespace to single spaces
        .trim()
        .substring(0, 100);
      const key = `${normalized}|${p.pdf_page || 0}`;
      if (seenTexts.has(key)) return false;
      seenTexts.add(key);
      return true;
    });
  }, [rawSelectedProvisions]);

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

  // Get ALL provisions across all parts (for "export all" option and task mode)
  // Use tocStructure (by_toc) which has actual provision data, not completeTocStructure (navigation only)
  // Excludes TOC entries, negative pages, and definitions at source (not counted anywhere)
  const allProvisions = useMemo(() => {
    if (!tocStructure || Object.keys(tocStructure).length === 0) return [];
    const allParts = Object.values(tocStructure);
    const provisions = allParts.flatMap((part: any) =>
      Object.values(part.sections || {}).flatMap((section: any) => section.provisions || [])
    );

    // First pass: Exclude non-provisions (TOC, definitions, non-actionable)
    // NOTE: Do NOT filter by negative page numbers - they're just PDF numbering artifacts.
    // Heritage controls for HCAs often have negative printed page numbers but are real provisions.
    const validProvisions = provisions.filter((p: any) => {
      const text = p.provision_text || '';

      // Exclude TOC entries (by type or pattern)
      if (p.v2_provision_type === 'TOC') return false;

      // Text-based TOC detection: multiple section numbers in sequence
      // e.g., "8.4.1.1 Public domain elements 8.4.1.2 Subdivision 8.4.1.3 Setbacks..."
      const sectionNumberPattern = /\d+\.\d+(?:\.\d+)*\s+[A-Z][a-z]/g;
      const sectionMatches = text.match(sectionNumberPattern);
      if (sectionMatches && sectionMatches.length >= 3) return false; // 3+ section numbers = TOC

      // Exclude non-actionable provisions (intro text, section headers, cross-references)
      if (p.v2_is_actionable === false) return false;

      // Exclude definitions (informational reference, not actionable controls)
      const isDefinitions =
        text.includes('KEY TERMS') ||
        (text.includes('Definitions') && text.includes('means a')) ||
        p.v2_topic?.toLowerCase() === 'definitions';
      if (isDefinitions) return false;

      return true;
    });

    // Second pass: Deduplicate - strip markers and normalize whitespace
    const seenTexts = new Set<string>();
    return validProvisions.filter((p: any) => {
      // Normalize: strip markers, collapse whitespace
      const normalized = (p.provision_text || '')
        .replace(/^(C|O)?\d+\s+/gm, '')  // Strip "C1 ", "O1 ", "01 " from line starts
        .replace(/\s+/g, ' ')  // Collapse all whitespace to single spaces
        .trim()
        .substring(0, 100);
      const key = `${normalized}|${p.pdf_page || 0}`;
      if (seenTexts.has(key)) return false;
      seenTexts.add(key);
      return true;
    });
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
        const hasNumeric = /\b\d+(?:\.\d+)?\s*(?:m²|m|mm|cm|km|%|metres?|meters?|sqm|ha)\b/i.test(text);
        return hasNumeric;
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
  }, [baseProvisions, layerFilteredProvisions, layerFilter, searchScope, debouncedSearch, topicFilters, refinements, heritage, zone, precinctId]);

  // Get NUMERIC provisions only (contains numbers for measurements, setbacks, etc.)
  const numericProvisions = useMemo(() => {
    return allProvisions.filter((p: any) => {
      const text = p.provision_text || '';
      // Check if provision contains numeric measurements - comprehensive pattern for planning regulations
      // Matches: 6m, 9.5m, 450m², 50sqm, 60 square metres, 15%, 900mm, 2.5cm, etc.
      const hasNumeric = /\b\d+(?:\.\d+)?\s*(?:m²|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?|sqm|square metres?|ha|hectares?)\b/i.test(text);
      // Exclude if it's primarily an objective, principle, or qualitative statement
      const isObjective = /^O\d+|objective|principle|aim|purpose|encourages|promotes|protecting|minimising|preventing|ensuring|must be consistent|contribution|significance|character|attributes|elements that/i.test(text);
      return hasNumeric && !isObjective;
    });
  }, [allProvisions]);

  // Get unique topics for filter chips — scoped to selected layer
  // Deduplicate by normalized key (lowercase) to avoid "Signage" and "signage" appearing separately
  const availableTopics = useMemo(() => {
    const topicMap = new Map<string, string>();
    layerFilteredProvisions.forEach(p => {
      if (p.v2_topic) {
        const normalized = p.v2_topic.toLowerCase().replace(/ /g, '_');
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
      const hasNumeric = /\b\d+(?:\.\d+)?\s*(?:m²|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?|sqm|square metres?|ha|hectares?)\b/i.test(text);
      const isObjective = /^O\d+|objective|principle|aim|purpose|encourages|promotes|protecting|minimising|preventing|ensuring|must be consistent|contribution|significance|character|attributes|elements that/i.test(text);

      if (hasNumeric && !isObjective) stats[topic].critical++;
    });
    return stats;
  }, [layerFilteredProvisions]);

  // NOW handle loading/error states AFTER all hooks are called
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
      // Helper to sanitize numbers for PDF rendering (convert to safe strings)
      const sanitizeNumberToString = (value: any, fieldName?: string): string | undefined => {
        if (value === null || value === undefined) return undefined;

        // Log the raw value
        console.log(`[PDF Number Sanitize] ${fieldName || 'unknown'}: raw value =`, value, `(type: ${typeof value})`);

        const num = typeof value === 'number' ? value : parseFloat(value);

        // Filter out: NaN, Infinity, very large numbers, AND NEGATIVE NUMBERS (invalid page numbers)
        if (isNaN(num) || !isFinite(num) || Math.abs(num) > 1e15 || num < 0) {
          console.error(`[PDF Number Sanitize] REJECTED ${fieldName || 'unknown'}: ${value} (parsed: ${num})`);
          return undefined;
        }

        const result = String(Math.round(num * 100) / 100);
        console.log(`[PDF Number Sanitize] ${fieldName || 'unknown'}: accepted = ${result}`);
        return result;
      };

      // Detect corner lot from nearby roads
      const nearbyRoads = propertyData?.nearbyRoads || [];
      const isCornerLot = nearbyRoads.length >= 2;
      const cornerRoadNames = isCornerLot ? nearbyRoads.slice(0, 2).map((r: any) => r.road_name) : [];

      // Extract lot dimensions from property data (sanitize all numbers to strings)
      const areaStr = sanitizeNumberToString(propertyData?.lotDimensions?.area, 'lot_area');
      const frontageStr = sanitizeNumberToString(propertyData?.lotDimensions?.frontage, 'lot_frontage');
      const depthStr = sanitizeNumberToString(propertyData?.lotDimensions?.depth, 'lot_depth');

      const lotDimensions = (areaStr || frontageStr || depthStr) ? {
        area: areaStr ? parseFloat(areaStr) : undefined,
        frontage: frontageStr ? parseFloat(frontageStr) : undefined,
        depth: depthStr ? parseFloat(depthStr) : undefined,
        is_corner: isCornerLot,
        corner_roads: cornerRoadNames,
      } : undefined;

      // Extract LEP controls from lepClauseData
      const lepControls = lepClauseData ? {
        height: lepClauseData.height_limit || undefined,
        fsr: lepClauseData.fsr || undefined,
        acid_sulfate_soils: lepClauseData.acid_sulfate_soils || undefined,
        permitted_uses: lepClauseData.permitted_uses || [],
        prohibited_uses: lepClauseData.prohibited_uses || [],
      } : undefined;

      // Extract ALL planning portal layers with their numeric values (sanitize to strings)
      // Log to debug what layers we actually have
      console.log('=== PLANNING LAYERS DEBUG ===');
      console.log('propertyData exists?', !!propertyData);
      console.log('propertyData.planningLayers exists?', !!propertyData?.planningLayers);
      console.log('propertyData.planningLayers:', propertyData?.planningLayers);
      console.log('propertyData.planningLayers length:', propertyData?.planningLayers?.length);

      // Log each layer's results to see actual field names
      if (propertyData?.planningLayers) {
        propertyData.planningLayers.forEach((layer: any) => {
          console.log(`\nLayer: ${layer.layerName}`);
          console.log(`  Results count: ${layer.results?.length}`);
          if (layer.results?.[0]) {
            console.log(`  First result keys:`, Object.keys(layer.results[0]));
            console.log(`  First result data:`, layer.results[0]);
          }
        });
      }

      // Extract actual constraint values from each planning portal layer
      // Helper to get the primary value field (exclude metadata like Legislative Clause, EPI Name, etc.)
      const getLayerValue = (results: any[] | undefined): string | undefined => {
        if (!results?.[0]) return undefined;
        const result = results[0];
        const metadataKeys = ['Legislative Clause', 'legislationUrl', 'EPI Name', 'Amendment', 'Commenced Date',
                             'Published Date', 'Currency Date', 'LGA Name', 'Units', 'title', 'OBJECTID',
                             'Shape', 'Shape_Length', 'Shape_Area', 'GlobalID'];
        const valuesToSkip = ['LEP', 'SEPP', '']; // Skip generic "LEP" labels

        // Find first non-metadata key with a meaningful value
        for (const key of Object.keys(result)) {
          const value = result[key];
          if (!metadataKeys.includes(key) && value != null && !valuesToSkip.includes(value)) {
            return String(value);
          }
        }
        return undefined;
      };

      const planningPortalLayers = propertyData?.planningLayers ? {
        heritage_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Heritage'))?.results),
        fsr_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Floor Space'))?.results),
        height_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Height'))?.results),
        acid_sulfate_soils_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Acid Sulfate'))?.results),
        local_aboriginal_land_council: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Aboriginal'))?.results),
        sepp_requirements: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Special Provisions'))?.results),
        land_application_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Land Application'))?.results),
        regional_plan_boundary: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Regional Plan'))?.results),
        land_zoning_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Zoning'))?.results),
        tree_canopy_2019: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('2019'))?.results),
        tree_canopy_2022: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('2022'))?.results),
        terrestrial_biodiversity_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Biodiversity'))?.results),
      } : undefined;

      console.log('[PDF Planning Layers] Mapped values:', planningPortalLayers);

      // Check for any scientific notation in the raw layer data
      if (propertyData?.planningLayers) {
        propertyData.planningLayers.forEach((layer: any, idx: number) => {
          if (layer.results?.[0]) {
            console.log(`[PDF Layer ${idx}] ${layer.layerName}:`, JSON.stringify(layer.results[0]).substring(0, 200));
            // Check for scientific notation
            const jsonStr = JSON.stringify(layer.results[0]);
            if (/e[+-]\d+/i.test(jsonStr)) {
              console.error(`[PDF Layer ${idx}] CONTAINS SCIENTIFIC NOTATION:`, layer.layerName);
            }
          }
        });
      }

      // Build environmental constraints from propertyData
      const envC = propertyData?.constraints;
      const anef = propertyData?.anefData;
      const environmentalConstraints = envC ? {
        flood_prone: !!envC.floodProne,
        bushfire_prone: !!envC.bushfireProne,
        acid_sulfate_soils: envC.acidSulfateSoils || undefined,
        anef_zone: !!anef?.inAnefZone,
        anef_level: anef?.anefLevel,
        anef_code: anef?.anefCode,
        mine_subsidence: !!envC.mineSubsidence?.inDistrict,
        mine_subsidence_district: envC.mineSubsidence?.districtName,
        landslide_risk: !!envC.landslideRisk?.hasRisk,
        contaminated_land: !!envC.contaminatedLand?.hasNotifiedSites,
        contaminated_site_name: envC.contaminatedLand?.nearestSite?.name,
        contaminated_site_distance: envC.contaminatedLand?.nearestSite?.distance,
        drinking_water_catchment: !!envC.drinkingWaterCatchment?.inCatchment,
        terrestrial_biodiversity: !!envC.terrestrialBiodiversity?.inBiodiversityArea,
        coastal_management: !!(envC.coastalEnvironment?.inCoastalArea && envC.coastalEnvironment?.zones?.length),
        coastal_zones: envC.coastalEnvironment?.zones,
      } : undefined;

      // Extract Additional Local Provisions from constraints
      const additionalLocalProvisions: string[] | undefined =
        envC?.localProvisions && envC.localProvisions.length > 0
          ? envC.localProvisions
              .filter((p: any) => !p.isNearby)
              .map((p: any) => {
                const clause = p.clauseNumber ? `Clause ${p.clauseNumber}: ` : '';
                const desc = p.description ? ` — ${p.description}` : '';
                return `${clause}${p.title}${desc}`;
              })
          : undefined;

      // Fetch Pattern Book CDC eligibility
      let patternBookData = undefined;
      let pathwaySummary = undefined;

      try {
        const patternBookResponse = await fetch('/api/pathway/pattern-book-eligibility', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ propertyData })
        });

        if (patternBookResponse.ok) {
          const patternBookResult = await patternBookResponse.json();
          const eligibility = patternBookResult.data?.eligibility || patternBookResult;

          patternBookData = {
            status: eligibility.status || 'INELIGIBLE',
            exclusion_count: 217,
            numeric_standards_count: 199,
            override_rules_count: 9,
            blockers: eligibility.exclusionCheck?.exclusions?.map((e: any) => e.constraint) || [],
            pathway_timeframe: eligibility.status === 'ELIGIBLE' ? '10-day approval' : undefined
          };

          // Build pathway summary based on eligibility
          const pathways = [];

          // Pattern Book CDC
          pathways.push({
            name: 'Pattern Book CDC',
            status: eligibility.status === 'ELIGIBLE' ? 'Available' :
                   eligibility.status === 'CONDITIONAL' ? 'Conditional' : 'Not Available',
            timeframe: '10 days',
            notes: eligibility.status === 'ELIGIBLE' ? undefined :
                   patternBookData.blockers.length > 0 ? patternBookData.blockers[0] : 'See exclusions'
          });

          // Exempt & Complying
          const isResidentialZone = ['R1', 'R2', 'R3', 'R4', 'RU5'].includes(zone?.split(' ')[0] || '');
          pathways.push({
            name: 'Exempt & Complying Development',
            status: isResidentialZone ? 'Available' : 'Not Available',
            timeframe: '20 days',
            notes: isResidentialZone ? 'For eligible work types (deck, fence, carport, pool)' : 'Zone not eligible'
          });

          // Housing SEPP Low-Mid Rise
          const isHousingSEPPZone = ['R1', 'R2', 'R3', 'R4'].includes(zone?.split(' ')[0] || '');
          pathways.push({
            name: 'Housing SEPP (Low-Mid Rise)',
            status: isHousingSEPPZone && !heritage ? 'Available' : 'Not Available',
            timeframe: '25 days',
            notes: !isHousingSEPPZone ? 'Zone not eligible' : heritage ? 'Heritage area excluded' : undefined
          });

          // Standard DA
          pathways.push({
            name: 'Development Application (DA)',
            status: 'Available',
            timeframe: '50+ days',
            notes: 'Always available — required when other pathways excluded'
          });

          // Determine recommended pathway
          const recommendedPathway = eligibility.status === 'ELIGIBLE' ? 'Pattern Book CDC' :
                                    isResidentialZone ? 'Exempt & Complying Development' :
                                    isHousingSEPPZone && !heritage ? 'Housing SEPP (Low-Mid Rise)' :
                                    'Development Application (DA)';

          pathwaySummary = {
            recommended_pathway: recommendedPathway,
            pathways
          };
        }
      } catch (err) {
        console.error('Failed to fetch Pattern Book eligibility for PDF:', err);
        // Continue without Pattern Book data
      }

      // Build property context with real data
      const propertyContext: PropertyContext = {
        address: address || propertyData?.address || 'Property Address',
        zone: zone || 'Unknown',
        former_council: formerCouncil,
        heritage_status: {
          in_hca: heritage || false,
          hca_name: hcaName,
          hca_code: hcaCode || hcaName,
          heritage_item: heritageItem,
          item_name: heritageItemName,
          item_number: heritageItemNumber,
        },
        lot_dimensions: lotDimensions,
        lep_controls: lepControls,
        planning_portal_layers: planningPortalLayers,
        environmental_constraints: environmentalConstraints,
        additional_local_provisions: additionalLocalProvisions,
        hca_details: undefined, // TODO: Fetch from HCA data
        pattern_book_cdc: patternBookData,
        pathway_summary: pathwaySummary,
        development_description: developmentDescription || undefined,
      };

      // Always export filtered provisions (respects layer, topic, and search filters)
      const provisionsToExport = filteredProvisions;

      // Check if we have provisions to export
      if (!provisionsToExport || provisionsToExport.length === 0) {
        alert('No provisions to export. Please adjust your filters.');
        return;
      }

      console.log(`Exporting ${provisionsToExport.length} filtered provisions`);

      // Build active filters array for context
      const activeFilters: string[] = [];
      if (layerFilter) {
        const councilLabels = formerCouncil?.toLowerCase() && COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()];
        const label = councilLabels ? councilLabels[layerFilter] : DEFAULT_LAYER_LABELS[layerFilter];
        activeFilters.push(label);
      }
      if (topicFilters.length > 0) {
        activeFilters.push(topicFilters.map(t => t.replace(/_/g, ' ')).join(' + '));
      }
      if (debouncedSearch) {
        activeFilters.push(`Search: "${debouncedSearch}"`);
      }
      if (refinements.mandatoryOnly) {
        activeFilters.push('Mandatory only');
      }
      if (refinements.withMeasurements) {
        activeFilters.push('With measurements');
      }
      if (!layerFilter && topicFilters.length === 0 && !debouncedSearch && !refinements.mandatoryOnly && !refinements.withMeasurements) {
        activeFilters.push('All provisions for this property');
      }

      // Filter out Table of Contents entries before converting to PDF
      const { isTableOfContents } = await import('@/lib/pdf/formatProvisions');
      const actualProvisions = provisionsToExport.filter((p: any) => {
        const isTOC = isTableOfContents(p.provision_text || '');
        if (isTOC) {
          console.log(`[PDF Filter] Excluding TOC entry: ID ${p.id}`);
        }
        return !isTOC;
      });

      // Convert provisions to PDF format (sanitize ALL numeric fields)
      const provisionsForPdf: ProvisionForPDF[] = actualProvisions.map((p: any, idx: number) => {
        // Sanitize page numbers
        console.log(`[PDF Provision ${idx}] ID: ${p.id}, processing...`);
        const pdfPage = sanitizeNumberToString(p.pdf_page, `provision_${p.id}_pdf_page`);
        const pdfPrintedPage = sanitizeNumberToString(p.pdf_printed_page, `provision_${p.id}_pdf_printed_page`);

        // Log if we're sanitizing the known problematic provisions
        if (p.id === 78593 || p.id === 86746) {
          console.log(`Sanitizing provision ${p.id}:`);
          console.log(`  Original: pdf_page=${p.pdf_page}, pdf_printed_page=${p.pdf_printed_page}`);
          console.log(`  Sanitized: pdfPage=${pdfPage}, pdfPrintedPage=${pdfPrintedPage}`);
        }

        const finalPdfPage = pdfPage ? parseInt(pdfPage) : undefined;
        const finalPdfPrintedPage = pdfPrintedPage ? parseInt(pdfPrintedPage) : pdfPage ? parseInt(pdfPage) : 1;

        if (p.id === 78593 || p.id === 86746) {
          console.log(`  Final: pdf_page=${finalPdfPage}, pdf_printed_page=${finalPdfPrintedPage}`);
        }

        const daResponse = isDaMode ? daResponses?.get(p.id) : undefined;
        return {
          id: p.id,
          provision_text: sanitizeText(p.provision_text),
          v2_marker: p.v2_marker || '',
          v2_topic: p.v2_topic || '',
          document_name: p.document_name || '',
          v2_dcp_part: p.v2_dcp_part || '',
          section_header: p.section_header,
          pdf_page: finalPdfPage,
          pdf_printed_page: finalPdfPrintedPage,
          v2_is_actionable: p.v2_is_actionable,
          zone_applicability: p.zone_applicability,
          ref_number: p.ref_number,
          ...(daResponse?.compliance_status && {
            da_status: daResponse.compliance_status as 'complies' | 'varies' | 'not_applicable' | undefined,
            ...(daResponse.response_text && { da_response: daResponse.response_text }),
          }),
        };
      });

      // Log to find any bad data
      console.log('Provisions for PDF (first 3):', provisionsForPdf.slice(0, 3));

      // Check for scientific notation in provision text
      let scientificNotationFound = false;
      provisionsForPdf.forEach((p, idx) => {
        const text = p.provision_text || '';
        if (/e[+-]\d+/i.test(text)) {
          console.error(`[PDF SCIENTIFIC NOTATION] Found in provision ${p.id} (index ${idx}): ${text.substring(0, 100)}`);
          scientificNotationFound = true;
        }
      });
      if (!scientificNotationFound) {
        console.log('[PDF] No scientific notation found in provision text');
      }

      // Log property context for debugging
      console.log('Property context for PDF:', JSON.stringify(propertyContext, null, 2));
      console.log('Number of provisions:', provisionsForPdf.length);

      // Generate PDF
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

      console.log('[PDF Generation] Creating PDF with property context:', propertyContext);
      console.log('[PDF Generation] Lot dimensions:', propertyContext.lot_dimensions);
      console.log('[PDF Generation] Total provisions:', provisionsForPdf.length);

      console.log('Generating PDF blob...');
      const blob = await pdf(doc).toBlob();
      console.log('PDF blob generated successfully');

      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const dateStr = new Date().toISOString().split('T')[0];
      link.download = hasResponses
        ? `Draft-SEE-${formerCouncil}-${dateStr}.pdf`
        : `DCP-Provisions-${formerCouncil}-${dateStr}.pdf`;
      link.click();

      // Cleanup
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('PDF export failed:', error);
      console.error('Error details:', error instanceof Error ? error.message : String(error));
      console.error('Stack trace:', error instanceof Error ? error.stack : 'No stack trace');
      alert(`Failed to generate PDF: ${error instanceof Error ? error.message : 'Unknown error'}. Check console for details.`);
    }
  };

  // SEE Draft export — uses SEEDocument with annotated provisions only
  const handleExportSee = async () => {
    try {
      // Refresh responses from DB before building PDF — ensures per-provision annotations
      // saved by DAResponseCapture (which doesn't update parent daResponses state) are current.
      await refreshResponses();

      // Build provisionsForPdf (same pipeline as DCP export)
      const { isTableOfContents } = await import('@/lib/pdf/formatProvisions');
      // Use allProvisions — topic filter is a navigation tool, not a scope gate.
      // The SEE must cover the full provision set regardless of what filter is active.
      const actualProvisions = allProvisions.filter((p: any) => !isTableOfContents(p.provision_text || ''));

      const provisionsForPdf: ProvisionForPDF[] = actualProvisions.map((p: any) => {
        const pdfPage = p.pdf_page ? parseInt(String(p.pdf_page)) : undefined;
        const pdfPrintedPage = p.pdf_printed_page ? parseInt(String(p.pdf_printed_page)) : pdfPage ?? 1;
        const daResponse = daResponses?.get(p.id);
        return {
          id: p.id,
          provision_text: sanitizeText(p.provision_text),
          v2_marker: p.v2_marker || '',
          v2_topic: p.v2_topic || '',
          document_name: p.document_name || '',
          v2_dcp_part: p.v2_dcp_part || '',
          section_header: p.section_header,
          pdf_page: pdfPage,
          pdf_printed_page: pdfPrintedPage,
          v2_is_actionable: p.v2_is_actionable,
          zone_applicability: p.zone_applicability,
          ref_number: p.ref_number,
          ...(daResponse?.compliance_status && {
            da_status: daResponse.compliance_status as 'complies' | 'varies' | 'not_applicable' | undefined,
            ...(daResponse.response_text && { da_response: daResponse.response_text }),
          }),
        };
      });

      const annotatedProvisions = provisionsForPdf.filter(p => p.da_status);

      // Build property context — same field paths as handleExportPdf (propertyData uses camelCase)
      const nearbyRoads = propertyData?.nearbyRoads || [];
      const isCornerLot = nearbyRoads.length >= 2;
      const lotDimensions = (propertyData?.lotDimensions?.area || propertyData?.lotDimensions?.frontage) ? {
        area: propertyData?.lotDimensions?.area,
        frontage: propertyData?.lotDimensions?.frontage,
        depth: propertyData?.lotDimensions?.depth,
        is_corner: isCornerLot,
        corner_roads: isCornerLot ? nearbyRoads.slice(0, 2).map((r: any) => r.road_name) : [],
      } : undefined;

      const lepControls = lepClauseData ? {
        height: lepClauseData.height_limit || undefined,
        fsr: lepClauseData.fsr || undefined,
        acid_sulfate_soils: lepClauseData.acid_sulfate_soils || undefined,
        permitted_uses: lepClauseData.permitted_uses || [],
        prohibited_uses: lepClauseData.prohibited_uses || [],
      } : undefined;

      const getLayerValue = (results: any[] | undefined): string | undefined => {
        if (!results?.[0]) return undefined;
        const result = results[0];
        const metadataKeys = ['Legislative Clause', 'legislationUrl', 'EPI Name', 'Amendment', 'Commenced Date',
                             'Published Date', 'Currency Date', 'LGA Name', 'Units', 'title', 'OBJECTID',
                             'Shape', 'Shape_Length', 'Shape_Area', 'GlobalID'];
        const valuesToSkip = ['LEP', 'SEPP', ''];
        for (const key of Object.keys(result)) {
          const value = result[key];
          if (!metadataKeys.includes(key) && value != null && !valuesToSkip.includes(String(value))) return String(value);
        }
        return undefined;
      };

      const planningPortalLayers = propertyData?.planningLayers ? {
        heritage_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Heritage'))?.results),
        fsr_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Floor Space'))?.results),
        height_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Height'))?.results),
        acid_sulfate_soils_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Acid Sulfate'))?.results),
        regional_plan_boundary: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Regional Plan'))?.results),
        land_zoning_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Zoning'))?.results),
        tree_canopy_2022: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('2022'))?.results),
        terrestrial_biodiversity_map: getLayerValue(propertyData.planningLayers.find((l: any) => l.layerName?.includes('Biodiversity'))?.results),
      } : undefined;

      const envC = propertyData?.constraints;
      const anef = propertyData?.anefData;
      const environmentalConstraints = envC ? {
        flood_prone: !!envC.floodProne,
        bushfire_prone: !!envC.bushfireProne,
        acid_sulfate_soils: envC.acidSulfateSoils || undefined,
        anef_zone: !!anef?.inAnefZone,
        anef_level: anef?.anefLevel,
        anef_code: anef?.anefCode,
        mine_subsidence: !!envC.mineSubsidence?.inDistrict,
        mine_subsidence_district: envC.mineSubsidence?.districtName,
        landslide_risk: !!envC.landslideRisk?.hasRisk,
        contaminated_land: !!envC.contaminatedLand?.hasNotifiedSites,
        contaminated_site_name: envC.contaminatedLand?.nearestSite?.name,
        contaminated_site_distance: envC.contaminatedLand?.nearestSite?.distance,
        drinking_water_catchment: !!envC.drinkingWaterCatchment?.inCatchment,
        terrestrial_biodiversity: !!envC.terrestrialBiodiversity?.inBiodiversityArea,
        coastal_management: !!(envC.coastalEnvironment?.inCoastalArea && envC.coastalEnvironment?.zones?.length),
        coastal_zones: envC.coastalEnvironment?.zones,
      } : undefined;

      const additionalLocalProvisions: string[] | undefined =
        envC?.localProvisions && envC.localProvisions.length > 0
          ? envC.localProvisions
              .filter((p: any) => !p.isNearby)
              .map((p: any) => {
                const clause = p.clauseNumber ? `Clause ${p.clauseNumber}: ` : '';
                const desc = p.description ? ` — ${p.description}` : '';
                return `${clause}${p.title}${desc}`;
              })
          : undefined;

      const propertyContext: PropertyContext = {
        address: address || propertyData?.address || 'Property Address',
        zone: zone || 'Unknown',
        former_council: formerCouncil,
        heritage_status: {
          in_hca: heritage || false,
          hca_name: hcaName,
          hca_code: hcaCode || hcaName,
          heritage_item: heritageItem,
          item_name: heritageItemName,
          item_number: heritageItemNumber,
        },
        lot_dimensions: lotDimensions,
        lep_controls: lepControls,
        planning_portal_layers: planningPortalLayers,
        environmental_constraints: environmentalConstraints,
        additional_local_provisions: additionalLocalProvisions,
        development_description: devDescriptionLocal || undefined,
      };

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
      console.error('SEE export failed:', error);
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
        initialAnswers={intakeAnswers ?? undefined}
        heritage={heritage}
        hcaName={hcaName}
        precinctName={precinctName}
      />

      {/* ② Set your scope — DA mode only */}
      {isDaMode && (
        <div className="flex items-start gap-3 mb-5">
          <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">2</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-800">Set your scope</p>
            <p className="text-xs text-gray-500 mt-0.5 mb-2">Name the development type, describe the works, and answer factual questions to automatically exclude provisions that can't apply to your project. What survives triage is your assessment scope — the provisions your SEE must address.</p>
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
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-gray-900">
                {filteredProvisions.length}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                <>of {allProvisions.length} for property</>
              </div>
            </div>
          </div>

          {/* Search box */}
          <div className="mt-3 relative">
            {/* Search scope toggle - only show when user has applied filters */}
            {(layerFilter || topicFilters.length > 0 || refinements.mandatoryOnly || refinements.withMeasurements) && (
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                <span>Search in:</span>
                <button
                  onClick={() => setSearchScope('all')}
                  className={`px-2 py-1 rounded-md transition-colors ${
                    searchScope === 'all'
                      ? 'bg-teal-100 text-teal-700 font-medium'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  All provisions ({baseProvisions.length})
                </button>
                <button
                  onClick={() => setSearchScope('filtered')}
                  className={`px-2 py-1 rounded-md transition-colors ${
                    searchScope === 'filtered'
                      ? 'bg-teal-100 text-teal-700 font-medium'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  Filtered results only ({layerFilteredProvisions.length})
                </button>
              </div>
            )}

            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 z-10" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowAutocomplete(true);
                }}
                onFocus={() => setShowAutocomplete(true)}
                onBlur={() => {
                  // Delay to allow click on suggestion
                  setTimeout(() => setShowAutocomplete(false), 200);
                }}
                placeholder="Search provisions... (try: setback, FSR, heritage)"
                className="w-full pl-10 pr-10 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
              {searchQuery && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setShowAutocomplete(false);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 z-10"
                >
                  <X className="h-4 w-4" />
                </button>
              )}

              {/* Autocomplete dropdown */}
              {showAutocomplete && (
                <SearchAutocomplete
                  query={searchQuery}
                  suggestions={getSearchSuggestions(searchQuery)}
                  onSelect={(term) => {
                    setSearchQuery(term);
                    setShowAutocomplete(false);
                  }}
                  onClose={() => setShowAutocomplete(false)}
                />
              )}
            </div>
            {debouncedSearch && (
              <div className="mt-1 text-xs text-gray-500">
                {filteredProvisions.length} provision{filteredProvisions.length !== 1 ? 's' : ''} match your search
              </div>
            )}
          </div>

          {/* Export PDF Modal */}
          {showExportModal && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowExportModal(false)}>
              <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">DCP Provisions Schedule</h3>
                  <p className="text-xs text-gray-500 mb-4">Reference document — not a compliance assessment.</p>

                  {/* What will be exported */}
                  <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mb-6">
                    <div className="text-sm font-medium text-teal-900 mb-2">
                      Exporting {filteredProvisions.length} provision{filteredProvisions.length !== 1 ? 's' : ''}
                    </div>
                    <div className="text-xs text-teal-700 space-y-1">
                      {(() => {
                        const items = [];
                        const firstProv = filteredProvisions[0];

                        // Get DCP name (short form like "Marrickville DCP 2011")
                        const dcpName = formerCouncil === 'Ashfield' ? 'Ashfield DCP 2016'
                          : formerCouncil === 'Leichhardt' ? 'Leichhardt DCP 2013'
                          : formerCouncil === 'Marrickville' ? 'Marrickville DCP 2011'
                          : 'DCP';

                        // Only show part if in structure mode with a selected part
                        if (provisionView === 'structure' && selectedPart && firstProv?.v2_dcp_part) {
                          items.push(`${dcpName} • ${firstProv.v2_dcp_part}`);
                        } else {
                          // In task mode, just show DCP name without specific part
                          items.push(dcpName);
                        }

                        // Layer (e.g., "Marrickville-wide", "All")
                        if (layerFilter) {
                          const councilLabels = formerCouncil?.toLowerCase() && COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()];
                          const layerLabel = councilLabels ? councilLabels[layerFilter] : DEFAULT_LAYER_LABELS[layerFilter];
                          items.push(`Layer: ${layerLabel}`);
                        } else {
                          items.push(`Layer: All`);
                        }

                        // Topic (multi-select)
                        if (topicFilters.length > 0) {
                          const topics = topicFilters.map(t => t.replace(/_/g, ' ')).join(' + ');
                          items.push(`Topics: ${topics}`);
                        }

                        // Search
                        if (debouncedSearch) {
                          items.push(`Search: "${debouncedSearch}"`);
                        }

                        if (items.length === 0) {
                          return <div>• All provisions for this property</div>;
                        }

                        return items.map((item, idx) => <div key={idx}>• {item}</div>);
                      })()}
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-3">
                    <button
                      onClick={() => setShowExportModal(false)}
                      className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        setShowExportModal(false);
                        handleExportPdf();
                      }}
                      disabled={filteredProvisions.length === 0}
                      className="flex-1 px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      <Download className="h-4 w-4" />
                      Generate PDF
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Topic filter chips */}
          <div className="mt-3 space-y-2">
            {availableTopics.length > 1 && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  {topicFilters.length > 0 && (
                    <button
                      onClick={() => setTopicFilters([])}
                      className="px-2 py-0.5 text-xs rounded-full transition-colors bg-gray-100 text-gray-600 hover:bg-gray-200 flex items-center gap-1"
                    >
                      Clear <X className="w-3 h-3" />
                    </button>
                  )}
                  {availableTopics.map(topic => {
                    const topicKey = topic.toLowerCase().replace(/ /g, '_');
                    const stats = topicPriorityStats[topicKey] || { critical: 0, total: 0 };
                    const hasCritical = stats.critical > 0;
                    const isSelected = topicFilters.includes(topicKey);
                    return (
                      <button
                        key={topic}
                        onClick={() => toggleTopic(topicKey)}
                        className={`px-2 py-0.5 text-xs rounded-full transition-colors flex items-center gap-1 ${
                          isSelected
                            ? 'bg-teal-600 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {topic} ({stats.total})
                        {hasCritical && (
                          <Ruler className={`w-3 h-3 ${isSelected ? 'text-white/80' : 'text-gray-500'}`} />
                        )}
                        {isSelected && <X className="w-3 h-3 ml-0.5" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Refinement filters - only show when there are results to refine */}
            {(layerFilter || topicFilters.length > 0 || debouncedSearch) && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-500 font-medium">Refine:</span>

                <button
                  onClick={() => toggleRefinement('mandatoryOnly')}
                  className={`px-2 py-1 text-xs rounded-md transition-colors flex items-center gap-1 ${
                    refinements.mandatoryOnly
                      ? 'bg-red-100 text-red-800 border border-red-300'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {refinements.mandatoryOnly && <X className="w-3 h-3" />}
                  Mandatory only
                </button>

                <button
                  onClick={() => toggleRefinement('withMeasurements')}
                  className={`px-2 py-1 text-xs rounded-md transition-colors flex items-center gap-1 ${
                    refinements.withMeasurements
                      ? 'bg-blue-100 text-blue-800 border border-blue-300'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {refinements.withMeasurements ? (
                    <X className="w-3 h-3" />
                  ) : (
                    <Ruler className="w-3 h-3" />
                  )}
                  With measurements
                </button>
              </div>
            )}

            {/* Status line — plain-language summary of active filters */}
            {(layerFilter || topicFilters.length > 0 || refinements.mandatoryOnly || refinements.withMeasurements) && (
              <div className="text-xs text-gray-500 pt-1 border-t border-gray-100 mt-0.5">
                {(() => {
                  const labels = COUNCIL_LAYER_LABELS[(formerCouncil || '').toLowerCase()] || DEFAULT_LAYER_LABELS;
                  const count = filteredProvisions.length;
                  let message = `Showing ${count} provision${count !== 1 ? 's' : ''}`;

                  const layerLabel = layerFilter ? labels[layerFilter] : null;
                  const topicLabels = topicFilters.length > 0
                    ? topicFilters.map(t => t.replace(/_/g, ' ')).join(' + ')
                    : null;

                  // Add layer/topic context
                  if (layerLabel && topicLabels) {
                    message += ` — ${topicLabels} within ${layerLabel}`;
                  } else if (layerLabel) {
                    message += ` from ${layerLabel}`;
                  } else if (topicLabels) {
                    message += ` about ${topicLabels}`;
                  }

                  // Add refinement context
                  const refinementParts = [];
                  if (refinements.mandatoryOnly) refinementParts.push('mandatory only');
                  if (refinements.withMeasurements) refinementParts.push('with measurements');
                  if (refinementParts.length > 0) {
                    message += ` (${refinementParts.join(', ')})`;
                  }

                  return message;
                })()}
              </div>
            )}
          </div>

          {/* Why am I seeing these provisions? - now includes layer filters */}
          <LayerExplanation
            zone={zone}
            heritage={heritage}
            hcaName={hcaName}
            precinctName={precinctName}
            formerCouncil={formerCouncil}
            layerCounts={layerCounts}
            layerFilter={layerFilter}
            onLayerFilterChange={(layer) => {
              setLayerFilter(layer);
              setTopicFilters([]);  // Clear topic filters when changing layer
            }}
            // Heritage HCA details
            generalHeritageCount={generalHeritageCount}
            hcaSpecificCount={hcaSpecificCount}
            totalHeritageCount={totalHeritageCount}
          />

        </div>

        {/* Action Toolbar - Export */}
        {filteredProvisions.length > 0 && (
          <div className="px-4 py-3 border-b bg-gray-50">
            {isDaMode ? (
              <button
                onClick={handleExportSee}
                disabled={!devDescriptionLocal.trim()}
                title={!devDescriptionLocal.trim() ? 'Add a development description above to enable' : 'Export working draft — requires professional review before DA lodgement'}
                className="w-full flex items-center gap-2 px-3 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
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
        <div className="p-4">
          {/* Marker key - explains C/O reference codes (only show if markers exist) */}
          {filteredProvisions.length > 0 && hasMarkers && (
            <div className="mb-3 flex items-center gap-3 text-xs text-gray-500">
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

          {/* TODO: Rework numeric checker feature - temporarily disabled */}
          {/* Numeric Compliance Checker - always available when DCP provisions are loaded */}
          {/* <NumericChecker
            onValuesChange={(vals) => {
              const hasAnyValue = Object.values(vals).some(v => v !== '');
              setNumericCheckValues(hasAnyValue ? vals : undefined);
            }}
            results={complianceResults}
          /> */}

          {(() => {
            const splitByTriage = isDaMode && intakeAnswers && excludableTopics.size > 0;
            const displayProvisions = splitByTriage
              ? filteredProvisions.filter(p => {
                  const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
                  return !t || !excludableTopics.has(t);
                })
              : filteredProvisions;
            const triageExcludedProvisions = splitByTriage
              ? filteredProvisions.filter(p => {
                  const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
                  return t && excludableTopics.has(t);
                })
              : [];

            if (displayProvisions.length === 0 && triageExcludedProvisions.length === 0) return null;

            return (
              <>
                {displayProvisions.length > 0 && (
                  <PageGroupedProvisions provisionTheme="green"
                    provisions={displayProvisions}
                    formerCouncil={formerCouncil}
                    councilKey={formerCouncil?.toLowerCase()}
                    councilPdfUrl={data?.meta?.council_pdf_url ?? undefined}
                    showLayerBadges={true}
                    maxProvisions={100}
                    onViewPdf={(url, page) => setPdfModal({ url, page })}
                    highlightQuery={debouncedSearch}
                    zone={zone}
                    heritage={heritage}
                    hcaName={hcaName}
                    precinctName={precinctId}
                    isDaMode={isDaMode}
                    sessionToken={sessionToken}
                    daResponses={daResponses}
                    excludableTopics={excludableTopics}
                    // numericCheckValues={numericCheckValues} // TODO: Rework numeric checker feature
                  />
                )}
                {triageExcludedProvisions.length > 0 && (
                  <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
                    <button
                      onClick={() => setShowTriageExcluded(v => !v)}
                      className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-sm text-gray-500"
                    >
                      <span>{triageExcludedProvisions.length} provision{triageExcludedProvisions.length !== 1 ? 's' : ''} removed by triage</span>
                      <ChevronDown className={`w-4 h-4 transition-transform ${showTriageExcluded ? 'rotate-180' : ''}`} />
                    </button>
                    {showTriageExcluded && (
                      <div className="border-t border-gray-200">
                        <PageGroupedProvisions provisionTheme="green"
                          provisions={triageExcludedProvisions}
                          formerCouncil={formerCouncil}
                          councilKey={formerCouncil?.toLowerCase()}
                          councilPdfUrl={data?.meta?.council_pdf_url ?? undefined}
                          showLayerBadges={true}
                          maxProvisions={100}
                          onViewPdf={(url, page) => setPdfModal({ url, page })}
                          highlightQuery={debouncedSearch}
                          zone={zone}
                          heritage={heritage}
                          hcaName={hcaName}
                          precinctName={precinctId}
                          isDaMode={isDaMode}
                          sessionToken={sessionToken}
                          daResponses={daResponses}
                          excludableTopics={excludableTopics}
                        />
                      </div>
                    )}
                  </div>
                )}
              </>
            );
          })()}
          {filteredProvisions.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <Search className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              {debouncedSearch ? (
                <>
                  <p className="font-medium mb-2">
                    No provisions match "{debouncedSearch}"
                  </p>

                  {searchScope === 'filtered' && (
                    <button
                      onClick={() => setSearchScope('all')}
                      className="text-teal-600 hover:underline mb-2 block mx-auto"
                    >
                      Try searching all {baseProvisions.length} provisions instead?
                    </button>
                  )}

                  <div className="text-sm mt-4">
                    <p className="mb-2">Try searching for:</p>
                    <div className="flex gap-2 justify-center flex-wrap">
                      {['setback', 'FSR', 'heritage', 'parking', 'height'].map(term => (
                        <button
                          key={term}
                          onClick={() => setSearchQuery(term)}
                          className="px-2 py-1 bg-gray-100 rounded hover:bg-gray-200 text-xs"
                        >
                          {term}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <p>No provisions {provisionView === 'structure' ? 'in this section' : 'match your filters'}</p>
                  {(topicFilters.length > 0 || layerFilter) && (
                    <div className="mt-2 space-x-2">
                      {topicFilters.length > 0 && (
                        <button
                          onClick={() => setTopicFilters([])}
                          className="text-teal-600 text-sm hover:underline"
                        >
                          Clear topics
                        </button>
                      )}
                      {layerFilter && (
                        <button
                          onClick={() => setLayerFilter(null)}
                          className="text-teal-600 text-sm hover:underline"
                        >
                          Clear layer filter
                        </button>
                      )}
                    </div>
                  )}
                </>
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
