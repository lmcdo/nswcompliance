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
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, FileText, ChevronDown, ChevronRight, Search, X, Ruler, Download } from 'lucide-react';
import { COUNCIL_CONFIGS, isUniversalChapter, getDaDevTypeRole } from '@/lib/council-config';
import { pdf } from '@react-pdf/renderer';
import { ProvisionReport, SEEDocument } from '@/components/pdf';
import { PropertyContext, ProvisionForPDF } from '@/lib/pdf/types';
import { SEEDocumentData, SectionAssessment } from '@/lib/see/types';
import { deriveProvisionPartKey, inferSectionNumberFromHeader, buildSectionKey, deriveSectionTitleFromProvision } from '@/lib/see/sectionKey';
import { matchesSearchWithSynonyms, scoreProvision, getSearchSuggestions } from '@/lib/search-utils';
import { SearchAutocomplete } from '@/components/ui/SearchAutocomplete';
import { useDASession } from '@/hooks/useDASession';
import { DAModeCard } from './DAModeCard';
import { DAIntakeModal } from './DAIntakeModal';
import { getExcludableTopics, getTopicExclusionReason, normalizeTopicKey, autoPopulateFromConstraints, DEFAULT_INTAKE_ANSWERS, type IntakeAnswers } from '@/lib/see/intake';
import { buildPropertyContext, preparePdfProvisions, sanitizeText, cleanSectionTitle } from '@/lib/see/propertyContext';
import { NUMERIC_MEASUREMENT_RE, filterAndDedupeProvisions } from '@/lib/see/provisionUtils';
import { assembleDescription, buildSeeIntro, DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';
import { deriveIntakeFromScope, getScopeDevTypeTags } from '@/lib/see/ancillaryWorks';
import { deriveQuestionnaireTopics, deriveQuestionnaireDevTypeExclusions, type WorksScopeAnswers } from '@/lib/see/worksScope';
import { autoPopulateWorksScopeFromLep, type LepPermissibilityEntry } from '@/lib/see/lepScope';
import { buildPathwayDetermination, buildSeppControls, buildLepStandards } from '@/lib/see/seeBuilders';
import { DCPInterestForm } from './DCPInterestForm';
import { DcpStructuredControls } from './DcpStructuredControls';
import { DcpFilterBar } from './DcpFilterBar';
import { DcpProvisionList } from './DcpProvisionList';
import { NumericChecker, type NumericCheckValues } from './NumericChecker';
import { checkProvisionsAgainstValues, type ComplianceResult } from '@/lib/numericCompliance';


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
  const [provisionView] = useState<'task' | 'structure'>('structure');
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
  const [showIntakeModal, setShowIntakeModal] = useState(false);
  // PDF export always uses filtered provisions (respects layer, topic, and search filters)
  const [showExportModal, setShowExportModal] = useState(false); // PDF export modal visibility
  const [showTriageExcluded, setShowTriageExcluded] = useState(false);
  const [showSuppressedInDA, setShowSuppressedInDA] = useState(false); // Toggle to show suppressed (objective/descriptive) provisions in DA mode
  const [numericCheckValues, setNumericCheckValues] = useState<NumericCheckValues | undefined>(undefined);
  const [complianceResults, setComplianceResults] = useState<ComplianceResult[]>([]);
  const [guideExpanded, setGuideExpanded] = useState(false);

  // DA Mode session
  const { sessionToken, isLoading: sessionIsLoading, daResponses, refreshResponses, updateSingleResponse, sectionResponses, updateSingleSectionResponse, saveSectionResponse, developmentDescription, saveDescription, intakeAnswers, saveIntakeAnswers, ancillaryWorks: savedAncillaryWorks, primaryDevType, savedWorksText, saveScope, topicAssertions, saveTopicAssertion, chapterAssertions, saveChapterAssertion, bulkSaveResponses, worksScopeAnswers, saveWorksScopeAnswers } = useDASession(
    isDaMode ? (address || null) : null,
    formerCouncil,
    zone
  );

  // Clear scope form fields whenever the address changes — form always starts fresh.
  // Intake answers and DA responses persist server-side via useDASession.
  // Refs are cleared immediately (synchronously) so any debounced callbacks that fire
  // before the next render don't read stale dev type or works text values.
  useEffect(() => {
    setDevType('');
    setDevWorksText('');
    setAncillaryWorksLocal([]);
    setClientRef('');
    setPreparedBy('');
    devTypeRef.current = '';
    devWorksTextRef.current = '';
    ancillaryInitializedRef.current = false;
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
  // Tracks whether ancillary works have been initialised from server session.
  // Prevents re-applying server state after the user has made local edits.
  const ancillaryInitializedRef = useRef(false);


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

  // Restore ancillary works from session when loaded — one-time initialisation only.
  // ancillaryInitializedRef prevents re-applying server state after the user has
  // made local edits (which would clobber their changes on the next savedAncillaryWorks update).
  useEffect(() => {
    if (!ancillaryInitializedRef.current && savedAncillaryWorks.length > 0) {
      setAncillaryWorksLocal(savedAncillaryWorks);
      ancillaryInitializedRef.current = true;
    }
  }, [savedAncillaryWorks]);

  // Restore dev type and works text from session when loaded.
  // Only restores if the planner hasn't already entered values in this session.
  // Runs when sessionToken changes (new session loaded) or when saved values arrive.
  // devType and devWorksText intentionally omitted from deps — we only want
  // to sync once on session load, not re-trigger on every user edit.
  useEffect(() => {
    if (!sessionToken) return;
    if (primaryDevType && devType === '') {
      setDevType(primaryDevType);
    }
    if (savedWorksText && devWorksText === '') {
      setDevWorksText(savedWorksText);
    }
  }, [sessionToken, primaryDevType, savedWorksText]); // eslint-disable-line react-hooks/exhaustive-deps


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
  const daDevTypeRole = getDaDevTypeRole(formerCouncil?.toLowerCase() ?? null);

  // LGA-specific top-level structural term — derived from config key prefix ("Part A" → "part", "Chapter A" → "chapter")
  const tocTopLevelTerm: 'part' | 'chapter' = (() => {
    const firstKey = councilConfig?.universalPartKeys?.[0] ?? '';
    return firstKey.toLowerCase().startsWith('chapter') ? 'chapter' : 'part';
  })();
  const TocTopLevelTermCap = tocTopLevelTerm === 'chapter' ? 'Chapter' : 'Part';

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
      precinct_warning?: boolean;
      dcp_currency?: {
        verified_at: string | null;
        amendment_pending: boolean;
      } | null;
    };
  }>(apiUrl, fetcher, {
    dedupingInterval: 2000,   // Reduced from 60s to 2s - allow fresh data
    revalidateOnFocus: false, // Don't refetch on window focus
    revalidateOnMount: true,  // Always fetch on mount
    errorRetryCount: 3,       // Retry up to 3 times on error
    errorRetryInterval: 1000, // Wait 1s between retries
    shouldRetryOnError: true, // Enable retry on error
  });

  // Setback reference chips REMOVED. /api/setbacks/reference read `setback_rules`,
  // which has 0 rows in production and never had any — the only thing that would
  // have filled it was migrations/seed_setback_rules_inner_west.sql, 11 hand-written
  // values marked manual_verified=false, which was never run and which
  // .claude/rules/regulatory-data.md forbids shipping. The endpoint returned
  // {"data":null} for every zone and council, so the chip never rendered.
  // The verified numbers live in dcp_setback_controls and are served by
  // /api/dcp/structured-controls -> DcpStructuredControls.tsx.

  // LEP permissibility — fetched once per zone/lga to auto-populate scope exclusions.
  // Only fires in DA mode and only when both zone and lga are known.
  // Gated server-side by lep_zone_coverage.is_complete.
  // zone prop may be "E4 Local Centre" — extract code only for LEP lookup
  const zoneCode = zone?.split(' ')[0];
  const lepPermUrl = (isDaMode && zoneCode && lga)
    ? `/api/lep/permissibility?zone=${encodeURIComponent(zoneCode)}&lga=${encodeURIComponent(lga)}`
    : null;
  const { data: lepPermData } = useSWR<{
    covered: boolean;
    entries: LepPermissibilityEntry[];
  }>(lepPermUrl, fetcher, { revalidateOnFocus: false, revalidateOnMount: true });

  // SEPP exempt development counts — fetched once per zone to badge ancillary works.
  // Returns notApplicable=true for non-housing zones (E1–E4, MU1, SP, RE, W, etc.)
  const seppExemptUrl = (isDaMode && zoneCode)
    ? `/api/sepp/exempt-complying?zone=${encodeURIComponent(zoneCode)}`
    : null;
  const { data: seppExemptData } = useSWR<{
    notApplicable?: boolean;
    counts?: Record<string, number>;
  }>(seppExemptUrl, fetcher, { revalidateOnFocus: false, revalidateOnMount: true });

  // Map SEPP work type names to ancillary work values where counts > 0.
  const SEPP_TO_ANCILLARY: Record<string, string> = {
    Deck: 'deck', Pool: 'pool', Fence: 'fencing', Carport: 'parking',
  };
  const seppExemptWorks = useMemo((): Set<string> => {
    if (seppExemptData?.notApplicable || !seppExemptData?.counts) return new Set();
    const result = new Set<string>();
    for (const [seppType, ancillaryValue] of Object.entries(SEPP_TO_ANCILLARY)) {
      if ((seppExemptData.counts[seppType] ?? 0) > 0) result.add(ancillaryValue);
    }
    return result;
  }, [seppExemptData]);

  // LEP-derived scope: fields auto-set to false when use type is provably prohibited.
  // Merged as lowest priority — explicit user answers (worksScopeAnswers) always win.
  const lepAutoScope = useMemo(
    () => autoPopulateWorksScopeFromLep(
      lepPermData?.entries ?? [],
      lepPermData?.covered ?? false,
    ),
    [lepPermData]
  );

  const lepProhibitedDevTypes = useMemo(
    () => new Set(
      (lepPermData?.entries ?? [])
        .filter(e => e.permissibility === 'prohibited')
        .map(e => e.development_type)
    ),
    [lepPermData]
  );

  // Effective works scope: LEP auto-scope as lowest-priority base, user answers on top.
  // lepAutoScope provides false for provably-prohibited uses; user can override to null/true.
  const effectiveWorksScopeAnswers = useMemo(
    () => Object.keys(lepAutoScope).length > 0
      ? { ...lepAutoScope, ...(worksScopeAnswers ?? {}) } as WorksScopeAnswers
      : worksScopeAnswers,
    [worksScopeAnswers, lepAutoScope]
  );

  // DCP names for each council
  const councilDcpNames: Record<string, string> = {
    leichhardt: 'Leichhardt DCP 2013',
    ashfield: 'Ashfield Comprehensive DCP 2016',
    marrickville: 'Marrickville DCP 2011',
    waverley: 'Waverley DCP 2012',
    woollahra: 'Woollahra DCP 2015',
    ku_ring_gai: 'Ku-ring-gai DCP',
    city_of_sydney: 'City of Sydney DCP 2012',
    bayside: 'Bayside DCP 2023',
    blacktown: 'Blacktown DCP 2015',
    campbelltown: 'Campbelltown DCP 2018',
    canterbury_bankstown: 'Canterbury Bankstown DCP 2023',
    cumberland: 'Cumberland DCP 2021',
    georges_river: 'Georges River DCP 2022',
    hornsby: 'Hornsby DCP 2013',
    liverpool: 'Liverpool DCP 2008',
    northern_beaches: 'Northern Beaches DCP 2022',
    parramatta: 'Parramatta DCP 2023',
    penrith: 'Penrith DCP 2014',
    randwick: 'Randwick DCP 2013',
    sutherland_shire: 'Sutherland Shire DCP 2015',
    ryde: 'Ryde DCP 2014',
    strathfield: 'Strathfield DCP 2005',
    the_hills: 'The Hills DCP 2012',
    camden: 'Camden DCP 2019',
    canada_bay: 'Canada Bay DCP',
    burwood: 'Burwood DCP',
    fairfield: 'Fairfield City Wide DCP 2024',
  };

  // Currency data from API (instrument_currency table, updated by weekly PDF hash monitor)
  const dcpCurrency = data?.meta?.dcp_currency ?? null;
  const verifiedAtRaw = dcpCurrency?.verified_at ?? null;
  const amendmentPending = dcpCurrency?.amendment_pending ?? false;

  // Format verified_at ISO string → human-readable "14 Apr 2026"
  const verifiedDateLabel = verifiedAtRaw
    ? new Date(verifiedAtRaw).toLocaleDateString('en-AU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : null;

  // Staleness: warn if verified_at is null or >35 days ago.
  // Guard on data !== undefined — during SWR loading, data is undefined and verifiedAtRaw is null,
  // which would incorrectly trigger the stale warning before the API responds.
  const isStale = data !== undefined && (
    !verifiedAtRaw
      ? true
      : (Date.now() - new Date(verifiedAtRaw).getTime()) > 35 * 24 * 60 * 60 * 1000
  );

  // Extract heritage provisions from condition layer (Layer 3)
  const councilLower = formerCouncil?.toLowerCase() || '';

  // Auto-select first part on load ONLY in non-DA structure mode
  useEffect(() => {
    if (provisionView === 'structure' && !isDaMode && data?.data?.complete_toc && !selectedPart) {
      const parts = Object.keys(data.data.complete_toc);
      if (parts.length > 0) {
        // Sort: extract trailing letter (Part A → "A"), handle sub-parts (Part C.1 → "C.1"),
        // fall back to raw string so "Part A" always beats "Part C.1"
        const partSortKey = (p: string) => {
          const m = p.match(/Part\s+([A-Z])(?:\.(\d+))?/i);
          if (m) return m[1].toUpperCase() + (m[2] ? `.${m[2].padStart(3, '0')}` : '');
          const n = p.match(/\d+/);
          return n ? n[0].padStart(6, '0') : p;
        };
        const sortedParts = parts.sort((a, b) => partSortKey(a).localeCompare(partSortKey(b)));
        setSelectedPart(sortedParts[0]);
      }
    }
  }, [provisionView, isDaMode, data, selectedPart]);

  // Debounce search input with 300ms delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Questionnaire-derived topic exclusions — computed from effective scope answers.
  // Separate from manual topicAssertions so they auto-recalculate on answer change.
  const questionnaireTopics = useMemo(
    () => isDaMode ? deriveQuestionnaireTopics(effectiveWorksScopeAnswers) : new Map<string, string>(),
    [isDaMode, effectiveWorksScopeAnswers]
  );

  // Questionnaire-derived dev type exclusions — uses v2_applicable_dev_types directly.
  // More reliable than topic exclusion for cross-LGA provisions.
  // A provision is excluded when ALL its tagged dev types are in this confirmed-absent set.
  const questionnaireDevTypeExclusions = useMemo(
    () => isDaMode ? deriveQuestionnaireDevTypeExclusions(effectiveWorksScopeAnswers) : new Set<string>(),
    [isDaMode, effectiveWorksScopeAnswers]
  );

  // Heritage element scope — which building elements the proposal affects.
  // When set, heritage chapter shows only controls for those elements (+ general controls).
  const heritageElementScope = useMemo((): Set<string> | null => {
    const elems = effectiveWorksScopeAnswers?.heritage_elements;
    if (!elems || elems.length === 0) return null;
    return new Set(elems);
  }, [effectiveWorksScopeAnswers]);

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
    return (Object.values(part.sections) as any[]).flatMap(s => s.provisions);
  }, [selectedPart, selectedSection, tocStructure]);

  // Filter and deduplicate provisions for the currently selected part/section.
  // Shared logic lives in filterAndDedupeProvisions (provisionUtils.ts).
  const selectedProvisions = useMemo(
    () => filterAndDedupeProvisions(rawSelectedProvisions),
    [rawSelectedProvisions],
  );

  // Compute numeric compliance results whenever check values or provisions change.
  // Uses allProvisions (already deduped) — no need to re-extract from tocStructure.
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
  // True when ANY provision in scope carries a dev-type narrower than ALL.
  // Drives the copy above so it cannot claim 'removes nothing' once the
  // applicability tagger starts producing real dev types for this council.
  const anyDevTypeSpecific = allProvisions.some(
    (p: { v2_applicable_dev_types?: string[] | null }) =>
      Array.isArray(p.v2_applicable_dev_types)
      && p.v2_applicable_dev_types.length > 0
      && !p.v2_applicable_dev_types.includes('ALL'),
  );

  // Compute DCP numeric reference results whenever check values or provisions change.
  useEffect(() => {
    if (!numericCheckValues || allProvisions.length === 0) {
      setComplianceResults([]);
      return;
    }
    setComplianceResults(checkProvisionsAgainstValues(allProvisions, numericCheckValues));
  }, [numericCheckValues, allProvisions]);

  // Derives the canonical part key for a provision, normalising source_chapter_key slugs to the
  // same "Part N" / "Appendix X" labels used in completeTocStructure.
  // Used in filteredPartCounts, chapterProgress, globalProgress, and isInDaScope so all
  // chapter-level grouping / assertion lookups are consistent.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const derivePartKey = useCallback((p: any): string => {
    // Delegates to the shared utility in sectionKey.ts — single source of truth
    // for part key derivation across PageGroupedProvisions, progress counting, and PDF export.
    return deriveProvisionPartKey(p);
  }, []);

  // Auto-dismiss chapters where every non-heritage provision has explicit dev type tags
  // that exclude the current expanded dev types (no ALL tag, no matching tag).
  // Heritage (condition layer) chapters are never auto-dismissed.
  // Only active when a dev type is selected in DA mode.
  //
  // STRUCTURE MODEL GUARD: Universal chapters (per council scope config) are always
  // excluded from auto-dismiss regardless of dev type tags. For zone_organized councils
  // (Marrickville) and topic_universal councils (Leichhardt), Part 2 / Parts A-E are
  // must-show-to-planner — the planner addresses each section or records N/A explicitly.
  // Only devTypeGatedPartKeys (e.g. Ashfield Chapter F) are legitimately auto-dismissible.
  const councilId = formerCouncil?.toLowerCase() || null;
  const autoDismissedChapters = useMemo((): Set<string> => {
    if (!isDaMode || expandedDevTypes.length === 0) return new Set();
    const partProvisions = new Map<string, any[]>();
    for (const p of allProvisions) {
      if ((p.v2_dcp_layer || p.layer) === 'condition') continue;
      const partKey = derivePartKey(p);
      if (!partKey) continue;
      // Structure model guard: never auto-dismiss universal chapters
      if (isUniversalChapter(councilId, partKey)) continue;
      if (!partProvisions.has(partKey)) partProvisions.set(partKey, []);
      partProvisions.get(partKey)!.push(p);
    }
    const result = new Set<string>();
    for (const [partKey, provisions] of partProvisions) {
      const noneMatch = provisions.every(p => {
        const appTypes: string[] | null = p.v2_applicable_dev_types;
        if (!appTypes || appTypes.includes('ALL')) return false;
        return !expandedDevTypes.some((t: string) => appTypes.includes(t));
      });
      if (noneMatch) result.add(partKey);
    }
    return result;
  }, [isDaMode, allProvisions, expandedDevTypes, derivePartKey, councilId]);

  /** Section key used in sectionResponses and da_section_responses table.
   * Resolution: toc_section_number → inferred from section_header → "general" */
  const deriveSectionKey = useCallback((p: any): string => {
    const partKey    = derivePartKey(p);
    const sectionNum = p.toc_section_number
      || inferSectionNumberFromHeader(p.section_header)
      || 'general';
    return `${partKey}::${sectionNum}`;
  }, [derivePartKey]);

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

  // Merged set of dismissed chapters — manual (chapterAssertions) + auto-dismissed.
  // Expanded to include child chapters: dismissing a parent like "Part C" also dismisses
  // "Part C.1", "Part C.2" etc. (period-separated children present in completeTocStructure).
  // All filter sites use .has() on this set — expansion here is the single fix point.
  const allDismissedChapters = useMemo(() => {
    const base = new Set([...Object.keys(chapterAssertions), ...autoDismissedChapters]);
    const allPartKeys = Object.keys(completeTocStructure);
    for (const dismissed of [...base]) {
      for (const partKey of allPartKeys) {
        if (partKey.startsWith(dismissed + '.') && !base.has(partKey)) {
          base.add(partKey);
        }
      }
    }
    return base;
  }, [chapterAssertions, autoDismissedChapters, completeTocStructure]);

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
        const partKey = derivePartKey(p);
        // Exclude intake-triaged provisions by structural category (DD-1)
        // Guard: universal chapters (Mville Part 2, Leichhardt B/C1/D/E) are never
        // removed from scope by intake triage — planner must address or mark N/A.
        const cat = p.v2_structural_category;
        if (cat && excludableTopics.has(cat) && !isUniversalChapter(councilId, partKey)) return false;
        // Exclude chapter dismissals (manual + auto) so sidebar totals match assessment scope
        if (allDismissedChapters.has(partKey)) return false;
        // Exclude topic dismissals (also guarded for universal chapters)
        const topic = normalizeTopicKey(p.v2_topic);
        if (topic && topicAssertions[topic] && !isUniversalChapter(councilId, partKey)) return false;
        // Exclude objectives, procedural, descriptive, and heritage descriptives (hidden in DA mode).
        // Must match the suppressed filter in globalProgress to keep sidebar totals consistent.
        if (p.v2_provision_type === 'objective' || p.v2_provision_type === 'procedural' || p.v2_provision_type === 'descriptive') return false;
        if (p.v2_heritage_type === 'descriptive') return false;
        // Exclude questionnaire-derived topic scope (non-heritage only)
        const layer = p.v2_dcp_layer || p.layer;
        if (layer !== 'condition' && questionnaireTopics.size > 0) {
          const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
          if (t && questionnaireTopics.has(t)) return false;
        }
        // Exclude questionnaire-derived dev type scope (non-heritage only)
        if (layer !== 'condition' && questionnaireDevTypeExclusions.size > 0) {
          const dts: string[] = p.v2_applicable_dev_types || [];
          if (dts.length > 0 && dts.every((dt: string) => questionnaireDevTypeExclusions.has(dt))) return false;
        }
        // Exclude heritage elements outside selected element scope
        if (layer === 'condition' && heritageElementScope && heritageElementScope.size > 0) {
          const elems: string[] = p.v2_heritage_element || [];
          if (elems.length > 0 && !elems.some((e: string) => heritageElementScope.has(e))) return false;
        }
        return true;
      });

      console.log('[FilteredPartCounts] After DA filters:', {
        beforeCount: allProvisions.length,
        afterCount: provisionsToCount.length,
        filtered: allProvisions.length - provisionsToCount.length,
      });
    }

    for (const p of provisionsToCount) {
      // When a layer filter is active, only count provisions in that layer
      if (layerFilter && (p.v2_dcp_layer || p.layer) !== layerFilter) continue;
      counts[derivePartKey(p)] = (counts[derivePartKey(p)] || 0) + 1;
    }

    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    console.log('[FilteredPartCounts] Final result:', { counts, total });

    return counts;
  }, [allProvisions, isDaMode, excludableTopics, allDismissedChapters, topicAssertions, layerFilter, derivePartKey, questionnaireTopics, questionnaireDevTypeExclusions, heritageElementScope]);

  // Canonical section titles — two-pass build to guarantee key format consistency.
  //
  // Pass 1: complete_toc (structural data from API). Reliable when the API normalises
  // part keys to the same format as deriveProvisionPartKey ("Part N", "Appendix X").
  //
  // Canonical section titles indexed by section key (partKey::sectionNumber).
  // Pass 1: from complete_toc structural data (section_title on TOC entries).
  //   Also builds slugTitleMap (slug → section_title) for the Pass 2 fallback.
  // Pass 2: from provisions — fills gaps where TOC slug keys don't match provision
  //   section keys (e.g. Leichhardt: slug "part-c-s1-general" vs. "Part C::C1.2").
  //   Strategy: try deriveSectionTitleFromProvision (all-caps section_header → "C1.2 Demolition").
  //   If that only returns the bare section number (content text headers), fall back to
  //   the TOC slug title: "C2" + "Urban Character" → "C2 Urban Character".
  const canonicalSectionTitles = useMemo(() => {
    const map = new Map<string, string | null>();
    const slugTitleMap = new Map<string, string>(); // TOC section slug → human title

    // Pass 1: complete_toc structural data
    for (const [partId, part] of Object.entries(completeTocStructure as Record<string, any>)) {
      for (const [sectionId, section] of Object.entries((part.sections || {}) as Record<string, any>)) {
        const title = section.section_title || null;
        map.set(`${partId}::${sectionId}`, title);
        if (title) slugTitleMap.set(sectionId, title);
      }
    }

    // Pass 2: provision-derived titles for any keys not covered by Pass 1.
    for (const p of allProvisions) {
      const key = buildSectionKey(p);
      if (!map.has(key)) {
        let title: string | null = (p as any).toc_section_title ?? deriveSectionTitleFromProvision(p);
        // If derivation returned only the bare section number (non-heading content text),
        // try the slug title as a suffix: "C2 Urban Character", "C3 Residential", "C1.10 General".
        const secNum = p.toc_section_number?.trim() ?? null;
        if (title === secNum) {
          const slugTitle = p.source_chapter_key ? slugTitleMap.get(p.source_chapter_key) : null;
          if (slugTitle) title = secNum ? `${secNum} ${slugTitle}` : slugTitle;
        }
        if (title) map.set(key, title);
      }
    }
    return map;
  }, [completeTocStructure, allProvisions]);

  // Intake filtering is now handled by handleAncillaryWorksChange via ancillary work checkboxes
  // Modal-based questions have been removed in favor of the cleaner checkbox UI

    const baseProvisions = useMemo(() => {
    let base;
    if (provisionView === 'task' || layerFilter) {
      // Task mode or layer filter active: use ALL provisions so the layer filter
      // shows all matching provisions across every section, not just the selected one.
      base = allProvisions;
    } else {
      // Structure mode: TOC-filtered to selected section
      base = selectedProvisions;
    }

    console.log('[BaseProvisions] Set:', {
      provisionView,
      layerFilter,
      count: base.length,
      byLayer: {
        generic: base.filter(p => (p.v2_dcp_layer || p.layer) === 'generic').length,
        use_specific: base.filter(p => (p.v2_dcp_layer || p.layer) === 'use_specific').length,
        condition: base.filter(p => (p.v2_dcp_layer || p.layer) === 'condition').length,
        precinct: base.filter(p => (p.v2_dcp_layer || p.layer) === 'precinct').length,
      },
    });

    return base;
  }, [provisionView, layerFilter, allProvisions, selectedProvisions]);

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
      chapterAssertionsCount: allDismissedChapters.size,
      topicAssertionsCount: Object.keys(topicAssertions).length,
    });

    // In DA mode: apply ALL filters to match DCP structure total
    if (isDaMode) {
      const assertedChapters = allDismissedChapters;
      const assertedTopics = new Set(Object.keys(topicAssertions));

      console.log('[LayerCounts] DA Mode - applying filters:', {
        assertedChapters: Array.from(assertedChapters),
        assertedTopics: Array.from(assertedTopics),
        excludableTopic: Array.from(excludableTopics),
      });

      const beforeCount = base.length;
      base = allProvisions.filter(p => {
        const layer = p.v2_dcp_layer || p.layer;
        // Exclude intake-triaged provisions by structural category (DD-1)
        if (excludableTopics.size > 0) {
          const cat = p.v2_structural_category;
          if (cat && excludableTopics.has(cat)) return false;
        }

        // Exclude objectives and heritage descriptives (hidden in DA mode)
        if (p.v2_provision_type === 'objective') return false;
        if (p.v2_heritage_type === 'descriptive') return false;

        // Heritage element scope — must apply before the early 'return true' for condition layer
        if (layer === 'condition' && heritageElementScope && heritageElementScope.size > 0) {
          const elems: string[] = p.v2_heritage_element || [];
          if (elems.length > 0 && !elems.some((e: string) => heritageElementScope.has(e))) return false;
        }

        // Heritage (condition layer) is never filtered by chapter/topic assertions or questionnaire
        if (layer === 'condition') return true;

        // Questionnaire-derived topic scope (non-heritage only)
        if (questionnaireTopics.size > 0) {
          const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
          if (t && questionnaireTopics.has(t)) return false;
        }
        // Questionnaire-derived dev type scope (non-heritage only)
        if (questionnaireDevTypeExclusions.size > 0) {
          const dts: string[] = p.v2_applicable_dev_types || [];
          if (dts.length > 0 && dts.every((dt: string) => questionnaireDevTypeExclusions.has(dt))) return false;
        }

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
  }, [allProvisions, isDaMode, allDismissedChapters, topicAssertions, excludableTopics, questionnaireTopics, questionnaireDevTypeExclusions, heritageElementScope]);

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

    // X11: questionnaire-derived scope — auto-excluded based on works questionnaire answers.
    // Heritage (condition layer) is never filtered here.
    if (isDaMode && (questionnaireTopics.size > 0 || questionnaireDevTypeExclusions.size > 0)) {
      filtered = filtered.filter(p => {
        if ((p.v2_dcp_layer || p.layer) === 'condition') return true;
        if (questionnaireTopics.size > 0) {
          const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
          if (t && questionnaireTopics.has(t)) return false;
        }
        if (questionnaireDevTypeExclusions.size > 0) {
          const dts: string[] = p.v2_applicable_dev_types || [];
          if (dts.length > 0 && dts.every((dt: string) => questionnaireDevTypeExclusions.has(dt))) return false;
        }
        return true;
      });
    }

    // X12: heritage element scope — show only controls for building elements in scope.
    // General heritage controls (no specific element) always show.
    if (isDaMode && heritageElementScope && heritageElementScope.size > 0) {
      filtered = filtered.filter(p => {
        if ((p.v2_dcp_layer || p.layer) !== 'condition') return true;
        if (!p.v2_heritage_element || p.v2_heritage_element.length === 0) return true;
        return p.v2_heritage_element.some((elem: string) => heritageElementScope.has(elem));
      });
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

    // Chapter assertion filter — remove provisions whose DCP chapter has been dismissed (manual or auto).
    // Heritage (condition layer) is never filtered.
    if (isDaMode && allDismissedChapters.size > 0) {
      const assertedChapters = allDismissedChapters;
      filtered = filtered.filter(p => {
        if ((p.v2_dcp_layer || p.layer) === 'condition') return true;
        const chKey = (p.v2_dcp_part && p.v2_dcp_part !== 'unknown') ? p.v2_dcp_part : p.source_chapter_key;
        return !chKey || !assertedChapters.has(chKey);
      });
    }

    // DA mode: suppress non-assessable provisions.
    // 'objective' and 'procedural' (process/admin text) and 'descriptive' (informational/artefact)
    // are not enforceable controls — they do not require a Complies/Varies/N/A response.
    // Heritage 'descriptive' types are also suppressed.
    // Can be toggled back on for audit/transparency via showSuppressedInDA.
    if (isDaMode && !showSuppressedInDA) {
      filtered = filtered.filter(p =>
        p.v2_provision_type !== 'objective' &&
        p.v2_provision_type !== 'procedural' &&
        p.v2_provision_type !== 'descriptive' &&
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
      // Sort by priority (default), with DA mode relevance-first sort when dev type is selected.
      const priorityOrder = { critical: 1, important: 2, guideline: 3, contextual: 4 };
      const hasDaDevType = isDaMode && expandedDevTypes.length > 0;

      if (hasDaDevType) {
        // Q4 relevance sort: score provisions by specificity to the selected dev type + zone/precinct.
        // Higher score = more directly applicable = shown first within each section.
        // Ties broken by display priority.
        const relevanceScore = (p: any): number => {
          let score = 0;
          const appTypes: string[] | null = p.v2_applicable_dev_types;
          const layer = p.v2_dcp_layer || p.layer;
          // Dev type match (+3): provision is specifically tagged for the selected dev type
          if (appTypes && !appTypes.includes('ALL') && expandedDevTypes.some((t: string) => appTypes.includes(t))) {
            score += 3;
          }
          // Zone-specific (+2): use_specific layer provisions are more targeted than LGA-wide
          if (layer === 'use_specific') score += 2;
          // Precinct-specific (+2): precinct layer applies to this site only
          if (layer === 'precinct') score += 2;
          return score;
        };
        return filtered.sort((a, b) => {
          // Heritage (condition layer) always last — not zone/dev-type specific
          const aIsHeritage = (a.v2_dcp_layer || a.layer) === 'condition' ? 1 : 0;
          const bIsHeritage = (b.v2_dcp_layer || b.layer) === 'condition' ? 1 : 0;
          if (aIsHeritage !== bIsHeritage) return aIsHeritage - bIsHeritage;
          const scoreDiff = relevanceScore(b) - relevanceScore(a);
          if (scoreDiff !== 0) return scoreDiff;
          const aPriority = (priorityOrder as any)[a.v2_display_priority || 'important'] || 2;
          const bPriority = (priorityOrder as any)[b.v2_display_priority || 'important'] || 2;
          return aPriority - bPriority;
        });
      }

      return filtered.sort((a, b) => {
        const aLayer = DA_LAYER_SORT_ORDER[a.v2_dcp_layer || a.layer] ?? 2;
        const bLayer = DA_LAYER_SORT_ORDER[b.v2_dcp_layer || b.layer] ?? 2;
        if (aLayer !== bLayer) return aLayer - bLayer;
        const aPriority = (priorityOrder as any)[a.v2_display_priority || 'important'] || 2;
        const bPriority = (priorityOrder as any)[b.v2_display_priority || 'important'] || 2;
        return aPriority - bPriority;
      });
    }
  }, [baseProvisions, layerFilteredProvisions, layerFilter, searchScope, debouncedSearch, refinements, heritageTypeFilter, heritage, zone, precinctId, isDaMode, expandedDevTypes, topicAssertions, allDismissedChapters]);

  // Provisions for SEE export — baseProvisions filtered only by DA-mode scope rules.
  // Intentionally ignores layerFilter, search, and refinements so the exported document
  // always covers all in-scope DCP provisions regardless of what the user has filtered in the UI.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const provisionsForSeeExport = useMemo((): any[] => {
    if (!isDaMode) return baseProvisions;
    // In DA mode use allProvisions (full unfiltered set) — the comment above is the intent:
    // "all in-scope DCP provisions regardless of what the user has filtered in the UI."
    // baseProvisions = selectedProvisions in structure mode (TOC-selected section only), which
    // would produce a scopeMap covering only the chapter currently open in the left panel.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let p: any[] = allProvisions;
    if (Object.keys(topicAssertions).length > 0) {
      const assertedOut = new Set(Object.keys(topicAssertions));
      p = p.filter((prov: any) => {
        if ((prov.v2_dcp_layer || prov.layer) === 'condition') return true;
        // Universal chapters (Mville Part 2, Leichhardt B/C1/D/E) must appear in the
        // SEE PDF regardless of topic assertions — planner records N/A, not system removal.
        if (isUniversalChapter(councilId, derivePartKey(prov))) return true;
        const t = (prov.v2_topic || '').toLowerCase().replace(/ /g, '_');
        return !t || !assertedOut.has(t);
      });
    }
    if (allDismissedChapters.size > 0) {
      const assertedChapters = allDismissedChapters;
      p = p.filter((prov: any) => {
        if ((prov.v2_dcp_layer || prov.layer) === 'condition') return true;
        const chKey = (prov.v2_dcp_part && prov.v2_dcp_part !== 'unknown') ? prov.v2_dcp_part : prov.source_chapter_key;
        return !chKey || !assertedChapters.has(chKey);
      });
    }
    if (!showSuppressedInDA) {
      p = p.filter((prov: any) =>
        prov.v2_provision_type !== 'objective' &&
        prov.v2_heritage_type !== 'descriptive'
      );
    }
    return p;
  }, [allProvisions, baseProvisions, isDaMode, topicAssertions, allDismissedChapters, showSuppressedInDA, councilId, derivePartKey]);

  // Scope helper — true when a provision is in the active DA assessment scope
  const isInDaScope = useCallback((p: any) => {
    const cat = p.v2_structural_category;
    if (cat && excludableTopics.has(cat)) return false;            // intake triage (DD-1: structural)
    const topic = normalizeTopicKey(p.v2_topic);
    if (topic && topicAssertions[topic]) return false;             // planner dismissed topic
    if (p.v2_provision_type === 'objective') return false;         // objectives hidden in DA
    if (p.v2_provision_type === 'procedural') return false;        // procedural/admin text hidden in DA
    if (p.v2_provision_type === 'descriptive') return false;       // non-heritage descriptives hidden in DA
    if (p.v2_heritage_type === 'descriptive') return false;        // heritage descriptives hidden
    if (allDismissedChapters.has(derivePartKey(p))) return false;  // chapter dismissed (manual or auto)
    const layer = p.v2_dcp_layer || p.layer;
    if (layer !== 'condition') {
      if (questionnaireTopics.size > 0) {                           // questionnaire topic scope
        const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
        if (t && questionnaireTopics.has(t)) return false;
      }
      if (questionnaireDevTypeExclusions.size > 0) {               // questionnaire dev type scope
        const dts: string[] = p.v2_applicable_dev_types || [];
        if (dts.length > 0 && dts.every((dt: string) => questionnaireDevTypeExclusions.has(dt))) return false;
      }
    }
    if (layer === 'condition' && heritageElementScope && heritageElementScope.size > 0) {  // heritage element scope
      const elems: string[] = p.v2_heritage_element || [];
      if (elems.length > 0 && !elems.some((e: string) => heritageElementScope.has(e))) return false;
    }
    return true;
  }, [excludableTopics, topicAssertions, allDismissedChapters, derivePartKey, questionnaireTopics, questionnaireDevTypeExclusions, heritageElementScope]);

  // Per-chapter assessment progress — section-based, used by TocSidebar progress bars
  const chapterProgress = useMemo(() => {
    if (!isDaMode) return undefined;
    // Count unique sections per chapter; a section is assessed when sectionResponses has an entry for it
    const chapterSections: Record<string, Set<string>> = {};
    const chapterAssessedSections: Record<string, Set<string>> = {};
    for (const p of allProvisions) {
      if (!isInDaScope(p)) continue;
      // Exclude non-enforceable items — mirrors globalProgress suppression so counts are consistent
      if (p.v2_provision_type === 'objective' || p.v2_heritage_type === 'descriptive') continue;
      const chKey = derivePartKey(p);
      const secKey = deriveSectionKey(p);
      if (!chapterSections[chKey]) chapterSections[chKey] = new Set();
      chapterSections[chKey].add(secKey);
      if (sectionResponses.has(secKey)) {
        if (!chapterAssessedSections[chKey]) chapterAssessedSections[chKey] = new Set();
        chapterAssessedSections[chKey].add(secKey);
      }
    }
    const map: Record<string, { assessed: number; total: number }> = {};
    for (const chKey of Object.keys(chapterSections)) {
      map[chKey] = {
        total:    chapterSections[chKey].size,
        assessed: chapterAssessedSections[chKey]?.size ?? 0,
      };
    }
    return map;
  }, [isDaMode, allProvisions, sectionResponses, isInDaScope, derivePartKey, deriveSectionKey]);

  // In-scope section keys for the currently selected chapter — drives State A section list
  const sectionScopeForPart = useMemo(() => {
    if (!isDaMode || !selectedPart) return new Set<string>();
    const inScope = new Set<string>();
    for (const p of allProvisions) {
      if (!isInDaScope(p)) continue;
      if (derivePartKey(p) !== selectedPart) continue;
      inScope.add(deriveSectionKey(p));
    }
    return inScope;
  }, [isDaMode, selectedPart, allProvisions, isInDaScope, derivePartKey, deriveSectionKey]);

  // Next unassessed in-scope section ID after selectedSection — drives State B "Next" button
  const nextUnassessedSectionId = useMemo(() => {
    if (!isDaMode || !selectedPart || !selectedSection) return null;
    // Derive section IDs from sectionScopeForPart — works even when complete_toc.sections is empty
    const prefix = selectedPart + '::';
    const sectionIds = [...sectionScopeForPart]
      .filter(k => k.startsWith(prefix))
      .map(k => k.slice(prefix.length))
      .sort((a, b) => {
        const na = parseFloat(a), nb = parseFloat(b);
        return (!isNaN(na) && !isNaN(nb)) ? na - nb : a.localeCompare(b);
      });
    const currentIdx = sectionIds.indexOf(selectedSection);
    for (let i = currentIdx + 1; i < sectionIds.length; i++) {
      const secId = sectionIds[i];
      const secKey = `${selectedPart}::${secId}`;
      if (!sectionResponses.has(secKey)) return secId;
    }
    return null;
  }, [isDaMode, selectedPart, selectedSection, sectionScopeForPart, sectionResponses]);

  // Global progress with reduction waterfall — single source of truth for all DA progress UI
  // scopeTotal / assessed / remaining are section-based (each section = one unit of work)
  const globalProgress = useMemo(() => {
    if (!isDaMode) return null;
    const total = allProvisions.length;
    let triaged = 0, chapterDismissed = 0, autoChapterDismissed = 0, topicDismissed = 0, suppressed = 0;
    let questionnaireScoped = 0, heritageElementScoped = 0;
    // Collect unique section keys that are in scope
    const inScopeSectionKeys = new Set<string>();
    let provisionScopeTotal = 0;
    for (const p of allProvisions) {
      const cat = p.v2_structural_category;
      const topic = normalizeTopicKey(p.v2_topic);
      const layer = p.v2_dcp_layer || p.layer;
      // Count each exclusion reason (priority order — first match wins)
      if (cat && excludableTopics.has(cat)) { triaged++; continue; }
      if (allDismissedChapters.has(derivePartKey(p))) {
        // Split manual vs auto so waterfall can distinguish them
        if (autoDismissedChapters.has(derivePartKey(p))) autoChapterDismissed++;
        else chapterDismissed++;
        continue;
      }
      if (topic && topicAssertions[topic]) { topicDismissed++; continue; }
      if (p.v2_provision_type === 'objective' || p.v2_provision_type === 'procedural' || p.v2_provision_type === 'descriptive' || p.v2_heritage_type === 'descriptive') { suppressed++; continue; }
      // Questionnaire-derived exclusions (not manual — counted separately)
      if (layer !== 'condition') {
        if (questionnaireTopics.size > 0 && topic && questionnaireTopics.has(topic)) {
          questionnaireScoped++; continue;
        }
        if (questionnaireDevTypeExclusions.size > 0) {
          const dts: string[] = p.v2_applicable_dev_types || [];
          if (dts.length > 0 && dts.every((dt: string) => questionnaireDevTypeExclusions.has(dt))) {
            questionnaireScoped++; continue;
          }
        }
      }
      // Heritage element scope exclusions
      if (layer === 'condition' && heritageElementScope && heritageElementScope.size > 0) {
        const elems: string[] = p.v2_heritage_element || [];
        if (elems.length > 0 && !elems.some((e: string) => heritageElementScope.has(e))) {
          heritageElementScoped++; continue;
        }
      }
      inScopeSectionKeys.add(deriveSectionKey(p));
      provisionScopeTotal++;
    }
    const scopeTotal = inScopeSectionKeys.size;
    const assessed   = [...inScopeSectionKeys].filter(k => sectionResponses.has(k)).length;
    return {
      total, triaged, chapterDismissed, autoChapterDismissed, topicDismissed, suppressed,
      questionnaireScoped, heritageElementScoped,
      scopeTotal, provisionScopeTotal, assessed, remaining: scopeTotal - assessed,
    };
  }, [isDaMode, allProvisions, sectionResponses, excludableTopics, topicAssertions, allDismissedChapters, autoDismissedChapters, derivePartKey, deriveSectionKey, questionnaireTopics, questionnaireDevTypeExclusions, heritageElementScope]);


  // Triage split — lifted out of JSX so header count and provision list use the same values.
  // Universal chapters (Mville Part 2, Leichhardt B/C1/D/E) are never moved to the
  // triage-excluded accordion — planner must see them and record N/A explicitly.
  const splitByTriage = isDaMode && excludableTopics.size > 0;
  const displayProvisions = useMemo(() => {
    if (!splitByTriage) return filteredProvisions;
    return filteredProvisions.filter(p => {
      if (isUniversalChapter(councilId, derivePartKey(p))) return true;
      const cat = p.v2_structural_category;
      return !cat || !excludableTopics.has(cat);
    });
  }, [splitByTriage, filteredProvisions, excludableTopics, councilId, derivePartKey]);
  const triageExcludedProvisions = useMemo(() => {
    if (!splitByTriage) return [];
    return filteredProvisions.filter(p => {
      if (isUniversalChapter(councilId, derivePartKey(p))) return false;
      const cat = p.v2_structural_category;
      return cat && excludableTopics.has(cat);
    });
  }, [splitByTriage, filteredProvisions, excludableTopics, councilId, derivePartKey]);

  // Sections that contain ONLY objectives/descriptives — not shown in the normal assessment list
  // because they have no enforceable controls, but planners may want to record an acknowledgement
  // narrative (e.g. "the proposal is consistent with the objectives of this section").
  // Scoped to the current selected part/section view so it tracks what's on screen.
  //
  // NOTE: deliberately does NOT call isInDaScope(p) — that function returns false for
  // objectives/descriptives by design (they are not in the assessable scope). Instead we
  // apply the chapter/topic/questionnaire scope rules directly, skipping only the provision
  // type rule, so we can correctly identify sections that are otherwise in scope but contain
  // only non-enforceable items.
  const suppressedOnlySections = useMemo(() => {
    if (!isDaMode || !selectedPart) return undefined;
    const displaySectionKeys = new Set(displayProvisions.map((p: any) => deriveSectionKey(p)));
    const map = new Map<string, string | null>();
    for (const p of baseProvisions) {
      if (p.v2_provision_type !== 'objective' && p.v2_provision_type !== 'procedural' && p.v2_provision_type !== 'descriptive' && p.v2_heritage_type !== 'descriptive') continue;
      // Scope check WITHOUT the provision-type exclusion (we want these types — we just need
      // to know whether their section is otherwise in scope or has been dismissed).
      const cat = p.v2_structural_category;
      if (cat && excludableTopics.has(cat)) continue;
      const topic = normalizeTopicKey(p.v2_topic);
      if (topic && topicAssertions[topic]) continue;
      if (allDismissedChapters.has(derivePartKey(p))) continue;
      const layer = p.v2_dcp_layer || p.layer;
      if (layer !== 'condition') {
        if (questionnaireTopics.size > 0) {
          const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
          if (t && questionnaireTopics.has(t)) continue;
        }
        if (questionnaireDevTypeExclusions.size > 0) {
          const dts: string[] = p.v2_applicable_dev_types || [];
          if (dts.length > 0 && dts.every((dt: string) => questionnaireDevTypeExclusions.has(dt))) continue;
        }
      }
      if (layer === 'condition' && heritageElementScope && heritageElementScope.size > 0) {
        const elems: string[] = p.v2_heritage_element || [];
        if (elems.length > 0 && !elems.some((e: string) => heritageElementScope.has(e))) continue;
      }
      const secKey = deriveSectionKey(p);
      if (!displaySectionKeys.has(secKey) && !map.has(secKey)) {
        map.set(secKey, canonicalSectionTitles.get(secKey) ?? p.toc_section_title ?? null);
      }
    }
    return map.size > 0 ? map : undefined;
  }, [isDaMode, selectedPart, baseProvisions, displayProvisions, deriveSectionKey, canonicalSectionTitles,
      excludableTopics, topicAssertions, allDismissedChapters, derivePartKey,
      questionnaireTopics, questionnaireDevTypeExclusions, heritageElementScope]);

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

  // No DCP provision TEXT for this council. That is not the same as having no
  // DCP data: the numeric controls come from a different table and may well be
  // present. This used to render the controls AND the "not yet processed"
  // interest form together, so Canterbury-Bankstown showed 20 controls sourced
  // from "Canterbury-Bankstown DCP 2023" directly above a form offering to
  // notify the user when that council's DCP went live.
  //
  // The interest form is now the FALLBACK, shown only when the controls fetch
  // comes back empty - which is what the old comment claimed and the old code
  // did not do.
  if (!data?.data?.by_toc || Object.keys(tocStructure).length === 0) {
    return (
      <div className="space-y-4">
        <DcpStructuredControls
          formerCouncil={formerCouncil}
          fallback={
            <DCPInterestForm
              councilName={lga || formerCouncil || 'your council'}
              address={address || ''}
            />
          }
        />
      </div>
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
    // On dismiss (not undo), navigate away if viewing the dismissed chapter or a child of it
    // e.g. dismissing "Part C" while viewing "Part C.1" should also trigger navigation
    const viewingDismissedChapter =
      reason !== null &&
      selectedPart !== null &&
      (selectedPart === chapterKey || selectedPart.startsWith(chapterKey + '.'));
    if (viewingDismissedChapter) {
      const parts = Object.keys(completeTocStructure);
      const updatedDismissed = new Set([...allDismissedChapters, chapterKey]);
      // Expand to include children of the newly dismissed key
      for (const p of parts) {
        if (p.startsWith(chapterKey + '.')) updatedDismissed.add(p);
      }
      const nextPart = parts.find(p => p !== chapterKey && !updatedDismissed.has(p) && completeTocStructure[p]?.provision_count > 0);
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

  // Bulk-mark all unassessed sections in the current chapter view

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
      const hasResponses = isDaMode && (sectionResponses.size > 0 || (daResponses && daResponses.size > 0));
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
    // Soft completeness gate — warn if sections are unassessed, don't hard-block
    // (partial export for review is a legitimate workflow step).
    if (globalProgress && globalProgress.remaining > 0) {
      const n = globalProgress.remaining;
      const confirmed = window.confirm(
        `⚠ INCOMPLETE DOCUMENT\n\n` +
        `${n} section${n !== 1 ? 's' : ''} in scope ${n === 1 ? 'has' : 'have'} not been assessed.\n\n` +
        `The exported PDF will be marked INCOMPLETE and will list the unassessed sections in Section 6.5.\n\n` +
        `This document must not be lodged with a Development Application until all sections are addressed.\n\n` +
        `Export for review only?`
      );
      if (!confirmed) return;
    }
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

      // Use provisionsForSeeExport (baseProvisions + DA-mode scope filters only) so the SEE document
      // always covers all in-scope provisions, regardless of active layerFilter/search/refinements in the UI.
      const provisionsForPdf = await preparePdfProvisions(provisionsForSeeExport, daResponses ?? undefined);
      const annotatedProvisions = provisionsForPdf.filter(p => p.da_status);

      // Section-level model: build section_responses + section_scope for the PDF.
      // After refreshResponses(), sectionResponses has section_title populated from DB.
      let sectionResponsesForPdf: SectionAssessment[] | undefined;
      let sectionScopeForPdf: { section_key: string; section_title: string | null }[] | undefined;
      if (sectionResponses.size > 0) {
        // Build ordered scope (unique section keys in provision order).
        // Prefer canonical title from complete_toc; fall back to DB-stored title from sectionResponses.
        const scopeMap = new Map<string, string | null>();
        for (const p of provisionsForSeeExport) {
          const key = deriveSectionKey(p);
          if (!scopeMap.has(key)) {
            const canonicalTitle = canonicalSectionTitles.get(key);
            scopeMap.set(key, canonicalTitle !== undefined ? canonicalTitle : (sectionResponses.get(key)?.section_title ?? null));
          }
        }
        // Only activate section model if provisions actually loaded — empty scope means
        // something went wrong upstream; fall back to provision-based PDF render.
        if (scopeMap.size > 0) {
          sectionScopeForPdf = [...scopeMap.entries()].map(([k, t]) => ({ section_key: k, section_title: t }));
          // Only include responses for sections that are currently in scope.
          // Stale responses from dismissed chapters would otherwise inflate assessed counts
          // and could show "✓ Fully assessed" incorrectly in the PDF.

          // Build provision requirement text per section for the compliance table.
          // Takes the first actionable (non-objective) provision text per section (first line, max 150 chars).
          // Filtered to v2_is_actionable=true to avoid showing objective text (O1 — To ensure...) as requirements.
          const provisionsBySectionKey = new Map<string, string[]>();
          for (const p of provisionsForSeeExport) {
            if (!p.v2_is_actionable) continue;
            const key = deriveSectionKey(p);
            if (!provisionsBySectionKey.has(key)) provisionsBySectionKey.set(key, []);
            const texts = provisionsBySectionKey.get(key)!;
            if (texts.length < 1 && p.provision_text) {
              const firstLine = p.provision_text.split('\n')[0].trim().substring(0, 150);
              const clausePrefix = (p as any).clause_label ? `[${(p as any).clause_label}] ` : '';
              if (firstLine) texts.push(`${clausePrefix}${firstLine}`);
            }
          }

          sectionResponsesForPdf = [...sectionResponses.entries()]
            .filter(([key]) => scopeMap.has(key))
            .map(([key, resp]) => {
              const canonicalTitle = canonicalSectionTitles.get(key);
              return {
                section_key: key,
                section_title: canonicalTitle !== undefined ? canonicalTitle : (resp.section_title ?? null),
                status: resp.status,
                narrative: resp.narrative,
                key_provisions: provisionsBySectionKey.get(key),
              };
            });
        }
      }

      // Gate 2: N/A sections without a reason — checked after refresh and scope build so the
      // count reflects the final in-scope set, not stale pre-refresh state.
      // A justification is required for every N/A section — omitting it is a leading RAI cause.
      if (sectionResponsesForPdf) {
        const naWithoutReason = sectionResponsesForPdf.filter(
          r => r.status === 'not_applicable' && !r.narrative?.trim()
        );
        if (naWithoutReason.length > 0) {
          const n = naWithoutReason.length;
          const confirmed = window.confirm(
            `⚠ N/A SECTIONS WITHOUT REASON\n\n` +
            `${n} section${n !== 1 ? 's' : ''} ${n === 1 ? 'is' : 'are'} marked N/A but ${n === 1 ? 'has' : 'have'} no reason recorded.\n\n` +
            `Council assessors require a specific reason for each N/A — e.g. 'No swimming pool proposed', 'Site is not flood prone'.\n\n` +
            `The exported PDF will show [No reason recorded] for ${n === 1 ? 'this section' : 'these sections'}.\n\n` +
            `Export for review only?`
          );
          if (!confirmed) return;
        }
      }

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
        lepCitation: councilConfig?.lepCitation,
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
        ...(sectionResponsesForPdf ? { section_responses: sectionResponsesForPdf } : {}),
        ...(sectionScopeForPdf ? { section_scope: sectionScopeForPdf } : {}),
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

      // Mark session as exported — fire-and-forget, non-blocking
      if (sessionToken) {
        fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ exported_at: new Date().toISOString() }),
        }).catch(() => {});
      }
    } catch (error) {
      alert(`Failed to generate SEE PDF: ${error instanceof Error ? error.message : 'Unknown error'}. Check console for details.`);
    }
  };

  return (
    <div className="space-y-0">
      {/* DCP currency status — source document, last verified date, amendment/staleness states */}
      {councilDcpNames[councilLower] && (
        <div className="mb-4 space-y-1">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isStale ? 'bg-amber-400' : amendmentPending ? 'bg-amber-400' : 'bg-green-500'}`} />
            <span className="font-medium text-gray-700">{councilDcpNames[councilLower]}</span>
            <span>·</span>
            <span>Monitored weekly</span>
            {verifiedDateLabel && (
              <>
                <span>·</span>
                <span>Last verified {verifiedDateLabel}</span>
              </>
            )}
            {!verifiedDateLabel && data !== undefined && (
              <>
                <span>·</span>
                <span className="text-amber-600">Verification date unavailable</span>
              </>
            )}
          </div>
          {amendmentPending && !isStale && (
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              Amendment detected — updated provisions pending review. Check council website for the latest version.
            </div>
          )}
          {isStale && (
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              Currency data overdue — weekly check has not run recently. Provisions shown are from the last verified version.
            </div>
          )}
          <p className="text-xs text-gray-400">
            Provisions sourced from the council&apos;s published DCP. Currency checked via weekly PDF hash monitor. This is planning intelligence for due diligence review — not a substitute for a Section 10.7 planning certificate.
          </p>
        </div>
      )}

      {/* Structured DCP controls — extracted numeric values (setbacks, parking, landscaping etc.) */}
      <DcpStructuredControls formerCouncil={formerCouncil} />

      {/* Intake filtering via ancillary checkboxes in assessment page — no modal needed */}

      {/* Enable DA Mode — rendered here so it only appears after provisions load */}
      {onToggleDaMode && (
        isDaMode ? (
          <div className="mb-5">
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
        ) : (
          <div className="mb-5 p-4 rounded-lg border border-teal-200 bg-teal-50">
            <p className="text-sm font-semibold text-teal-900 mb-1">Preparing a DA?</p>
            <p className="text-sm text-teal-800 mb-3">Scope these {allProvisions.length.toLocaleString()} provisions to your works and export a SEE draft.</p>
            <button
              onClick={() => onToggleDaMode(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold bg-teal-600 text-white hover:bg-teal-700 shadow-sm transition-all"
            >
              <span className="w-2 h-2 rounded-full inline-block bg-white" />
              Enable DA Mode
            </button>
          </div>
        )
      )}

      {/* ① Set your scope — DA mode only */}
      {isDaMode && (
        <div className="flex items-start gap-3 mb-5">
          <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">1</span>
          <div className="flex-1">
            <p className="text-base font-semibold text-gray-800">Define your works</p>
            <p className="text-sm text-gray-700 mt-0.5 mb-2">
              {daDevTypeRole === 'sort_only'
                ? (anyDevTypeSpecific
                    // DQ-33: this used to assert "all N provisions apply regardless of
                    // dev type … does not remove any" unconditionally. Correcting the
                    // applicability tagger gave Leichhardt Part F (food premises) real
                    // dev types, at which point that sentence was simply false. It is now
                    // derived from the data rather than assumed, so it stays true whichever
                    // way the corpus goes.
                    ? `Select your development type. For ${formerCouncil ? `${formerCouncil} DCP` : 'this council'}, most of the ${globalProgress?.total ?? allProvisions.length} provisions apply regardless of dev type and are re-ordered by relevance; a small number are written for specific development types and are filtered out when they do not apply.`
                    : `Select your development type. For ${formerCouncil ? `${formerCouncil} DCP` : 'this council'}, all ${globalProgress?.total ?? allProvisions.length} provisions apply regardless of dev type — your selection re-orders them by relevance but does not remove any.`)
                : daDevTypeRole === 'chapter_selector'
                ? 'Select your development type. Chapters that don\'t apply to your dev type are automatically removed from scope.'
                : 'Select your development type and any ancillary development. Controls that don\'t apply are automatically removed.'}
            </p>
            <DAModeCard
              onRunIntake={() => setShowIntakeModal(true)}
              onToggleObjectives={() => toggleRefinement('objectivesOnly')}
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
              worksScopeAnswers={worksScopeAnswers}
              onWorksScopeChange={saveWorksScopeAnswers}
              lepScopeDefaults={lepAutoScope}
              lepProhibitedDevTypes={lepProhibitedDevTypes}
              lepPermCovered={lepPermData?.covered ?? false}
              seppExemptWorks={seppExemptWorks}
              lotArea={propertyData?.lotDimensions?.area ?? null}
            />
          </div>
        </div>
      )}

      {/* Intake modal — site constraints questionnaire */}
      {isDaMode && (
        <DAIntakeModal
          open={showIntakeModal}
          onApply={async (answers) => {
            await saveIntakeAnswers(answers);
            setShowIntakeModal(false);
          }}
          onSkip={() => setShowIntakeModal(false)}
          provisions={allProvisions}
          initialAnswers={mergedIntakeAnswers}
          heritage={heritage}
          hcaName={hcaName}
          precinctName={precinctName}
          hasAncillaryScope={ancillaryWorksLocal.length > 0}
        />
      )}

      {/* Step 1 → Step 2 transition hint */}
      {isDaMode && devType && (
        <p className="text-xs text-teal-700 -mt-3 mb-4 pl-12">
          → In the <span className="font-semibold">DCP Structure</span> panel, dismiss {tocTopLevelTerm}s that don{"'"}t apply, then select each remaining {tocTopLevelTerm} to assess its sections.
        </p>
      )}

      {/* ② DCP numeric reference — enter proposed values to see DCP limits inline */}
      {isDaMode && allProvisions.length > 0 && (
        <div className="mb-5">
          <NumericChecker
            onValuesChange={setNumericCheckValues}
            results={complianceResults}
          />
        </div>
      )}

      {/* ② Assess sections — DA mode only */}
      {isDaMode && (
        <div className="mb-3 space-y-3">
          {/* Step 2 */}
          <div className="flex items-start gap-3">
            <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">2</span>
            <div className="flex-1 min-w-0">
              <p className="text-base font-semibold text-gray-800">Assess each section</p>
              <p className="text-sm text-gray-700 mt-0.5">
                In the <span className="font-semibold text-gray-800">DCP Structure</span> panel, select a {tocTopLevelTerm} to see its sections.
                In the <span className="font-semibold text-gray-800">Provisions</span> panel, read each section and record{' '}
                <span className="inline-flex items-center gap-0.5 flex-wrap">
                  <span className="px-1.5 py-0.5 rounded border text-xs font-medium bg-green-100 text-green-800 border-green-300">Complies</span>
                  {', '}
                  <span className="px-1.5 py-0.5 rounded border text-xs font-medium bg-amber-100 text-amber-800 border-amber-300">Varies</span>
                  {', or '}
                  <span className="px-1.5 py-0.5 rounded border text-xs font-medium bg-gray-100 text-gray-600 border-gray-300">N/A</span>
                </span>
                .{' '}
                <button
                  onClick={() => setGuideExpanded(v => !v)}
                  className="text-xs text-teal-600 hover:underline underline-offset-2"
                >
                  {guideExpanded ? 'Hide guide' : 'How does this work?'}
                </button>
              </p>
              {guideExpanded && (
                <div className="mt-2 text-xs text-gray-600 bg-teal-50 border border-teal-100 rounded p-2.5 space-y-1.5">
                  <p><span className="font-semibold text-gray-700">DCP Structure panel (left) — Step 1:</span> Dismiss {tocTopLevelTerm}s that don{"'"}t apply to this development. Dismissed {tocTopLevelTerm}s are recorded as not addressed in Schedule B of your SEE.</p>
                  <p><span className="font-semibold text-gray-700">DCP Structure panel (left) — Step 2:</span> Select each remaining {tocTopLevelTerm} to open it. You{"'"}ll see a list of its sections with their assessment status.</p>
                  <p><span className="font-semibold text-gray-700">Provisions panel (right):</span> Select a section to read its provisions, then record a response at the top of the panel. Work through all sections in the {tocTopLevelTerm} before moving to the next.</p>
                  <p><span className="font-semibold text-gray-700">Varies:</span> Use when a non-compliance needs justification — these become Schedule A of your SEE with space for your written response.</p>
                </div>
              )}
            </div>
          </div>

          {/* Step 3 — Export SEE */}
          <div className="flex items-start gap-3">
            <span className="font-serif text-4xl font-black leading-none flex-shrink-0 text-teal-500 select-none">3</span>
            <div className="flex-1 min-w-0">
              <p className="text-base font-semibold text-gray-800">Export your SEE</p>
              <p className="text-sm text-gray-700 mt-0.5">
                When all sections are assessed, export a working draft of your Statement of Environmental Effects.
              </p>
            </div>
            <button
              onClick={handleExportSee}
              title="Export working draft — requires professional review before DA lodgement"
              className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
            >
              <FileText className="h-4 w-4" />
              <span>Export SEE</span>
            </button>
          </div>
        </div>
      )}

      {/* Precinct warning — shown when LGA has precinct provisions but no precinct_id was resolved */}
      {data?.meta?.precinct_warning && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5 mb-3">
          Precinct data is not available for this property — site-specific precinct controls may not be shown.
        </p>
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
            autoDismissedChapters={autoDismissedChapters}
            onAssertChapter={handleAssertChapter}
            chapterProgress={chapterProgress}
            devType={isDaMode && devType ? getScopeDevTypeTags(devType, ancillaryWorksLocal).join(',') : undefined}
            devTypeLabel={isDaMode && devType ? DEV_TYPE_OPTIONS.find(o => o.value === devType)?.label : undefined}
            topLevelTerm={tocTopLevelTerm}
            daDevTypeRole={daDevTypeRole}
          />
        </div>
      )}

      {/* Right: Provisions content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b bg-white">
          <div className="flex items-center justify-between">
            <div>
              {provisionView === 'structure' && (
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-0.5">Provisions</p>
              )}
              <h3 className="text-lg font-semibold text-gray-900">
                {provisionView === 'task' ? (
                  'DCP Provisions'
                ) : selectedPart ? (
                  sanitizeText(completeTocStructure[selectedPart]?.part_name) || selectedPart
                ) : (
                  `Select a ${tocTopLevelTerm} from the DCP Structure panel`
                )}
              </h3>
              {provisionView === 'structure' && selectedSection && selectedPart && (
                <p className="text-sm text-gray-600 mt-0.5">
                  {cleanSectionTitle(completeTocStructure[selectedPart]?.sections[selectedSection]?.section_title)}
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
                      <> → {globalProgress.scopeTotal} sections in scope</>
                    )}
                    {(globalProgress.suppressed > 0 || globalProgress.triaged > 0) && (
                      <span className="block text-[11px] text-gray-300 mt-0.5">
                        {[
                          globalProgress.suppressed > 0 && `${globalProgress.suppressed} objectives/guidance not assessed`,
                          globalProgress.triaged > 0 && `${globalProgress.triaged} excluded by intake`,
                        ].filter(Boolean).join(' · ')}
                      </span>
                    )}
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {globalProgress.assessed}
                    <span className="text-base font-normal text-gray-400"> / {globalProgress.scopeTotal}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">sections assessed</div>
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

          {/* Global progress bar — DA mode, shows overall session completion */}
          {isDaMode && globalProgress && globalProgress.scopeTotal > 0 && (
            <div className="mt-2 -mx-0.5">
              <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-1 rounded-full transition-all ${globalProgress.remaining === 0 ? 'bg-green-500' : 'bg-teal-500'}`}
                  style={{ width: `${Math.round((globalProgress.assessed / globalProgress.scopeTotal) * 100)}%` }}
                />
              </div>
            </div>
          )}

          {/* Filter bar — hidden in State A (DA mode + chapter selected, no section yet) */}
          {!(isDaMode && selectedPart && !selectedSection) && (
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
          )}

        </div>

        {/* State A — part selected, no section: show section list */}
        {isDaMode && selectedPart && !selectedSection ? (
          <div className="flex-1 overflow-auto">
            {(() => {
              // Derive sections from allProvisions scope — works when complete_toc.sections is empty
              const prefix = selectedPart + '::';
              const sectionIds = [...sectionScopeForPart]
                .filter(k => k.startsWith(prefix))
                .map(k => k.slice(prefix.length))
                .sort((a, b) => {
                  const na = parseFloat(a), nb = parseFloat(b);
                  return (!isNaN(na) && !isNaN(nb)) ? na - nb : a.localeCompare(b);
                });
              const chProgress = chapterProgress?.[selectedPart];
              const allAssessed = chProgress && chProgress.total > 0 && chProgress.assessed === chProgress.total;
              if (sectionIds.length === 0) return (
                <p className="p-4 text-sm text-gray-500">No sections found for this part.</p>
              );
              return (
                <>
                  <div className="px-4 py-2 border-b bg-gray-50 flex items-center justify-between">
                    <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                      Sections <span className="font-normal normal-case tracking-normal text-gray-400 ml-1">— select one to assess</span>
                    </p>
                    <span className="text-xs text-gray-400">{sectionIds.length} section{sectionIds.length !== 1 ? 's' : ''}</span>
                  </div>
                  {allAssessed && (
                    <div className="px-4 py-2 bg-green-50 border-b border-green-100 text-xs text-green-700 font-medium">
                      All {chProgress.total} section{chProgress.total !== 1 ? 's' : ''} assessed — part complete
                    </div>
                  )}
                  <div className="divide-y divide-gray-100">
                    {sectionIds.map((sectionId) => {
                      const secKey = `${selectedPart}::${sectionId}`;
                      const tocSection = (completeTocStructure[selectedPart]?.sections as Record<string, any>)?.[sectionId];
                      const rawTitle = canonicalSectionTitles.get(secKey) || tocSection?.section_title || '';
                      const title = cleanSectionTitle(rawTitle) || sectionId;
                      const inScope = sectionScopeForPart.has(secKey);
                      const response = sectionResponses.get(secKey);
                      const status = response?.status;
                      return (
                        <button
                          key={sectionId}
                          onClick={() => handleSelectSection(selectedPart, sectionId)}
                          className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 text-left transition-colors ${!inScope ? 'opacity-50' : ''}`}
                        >
                          {/* Status indicator */}
                          <span className={`flex-shrink-0 w-2.5 h-2.5 rounded-full ${
                            !inScope ? 'bg-gray-200' :
                            status === 'complies' ? 'bg-green-500' :
                            status === 'varies' ? 'bg-amber-500' :
                            status === 'not_applicable' ? 'bg-gray-400' :
                            'border-2 border-gray-300 bg-white'
                          }`} />
                          <span className={`flex-1 text-sm ${inScope ? 'text-gray-800' : 'text-gray-400'}`}>
                            {title}
                          </span>
                          {status && (
                            <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${
                              status === 'complies' ? 'bg-green-100 text-green-800 border-green-300' :
                              status === 'varies' ? 'bg-amber-100 text-amber-800 border-amber-300' :
                              'bg-gray-100 text-gray-600 border-gray-300'
                            }`}>
                              {status === 'not_applicable' ? 'N/A' : status.charAt(0).toUpperCase() + status.slice(1)}
                            </span>
                          )}
                          <ChevronRight className="flex-shrink-0 w-4 h-4 text-gray-300" />
                        </button>
                      );
                    })}
                  </div>
                </>
              );
            })()}
          </div>
        ) : (
          <>
            {/* State B breadcrumb + next-section nav */}
            {isDaMode && selectedSection && selectedPart && (
              <div className="px-4 py-2 border-b bg-gray-50 flex items-center justify-between">
                <button
                  onClick={() => setSelectedSection(null)}
                  className="flex items-center gap-1 text-xs text-teal-700 hover:text-teal-900 font-medium"
                >
                  <ChevronRight className="w-3.5 h-3.5 rotate-180" />
                  {sanitizeText(completeTocStructure[selectedPart]?.part_name) || selectedPart}
                </button>
                {nextUnassessedSectionId && (
                  <button
                    onClick={() => handleSelectSection(selectedPart, nextUnassessedSectionId)}
                    className="flex items-center gap-1 text-xs text-teal-700 hover:text-teal-900 font-medium"
                  >
                    Next unassessed
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            )}

            {/* Action Toolbar - Export (disabled until export is fixed) */}
            {filteredProvisions.filter((p: any) => p.v2_provision_type !== 'procedural' && p.v2_provision_type !== 'descriptive').length > 0 && !isDaMode && (
              <div className="px-4 py-3 border-b bg-gray-50">
                <button
                  disabled
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-300 text-gray-500 text-sm font-medium rounded-lg cursor-not-allowed"
                >
                  <Download className="h-4 w-4" />
                  {topicFilters.length > 0
                    ? `Export ${filteredProvisions.length} ${topicFilters.map(t => t.replace(/_/g, ' ')).join(' + ')} provision${filteredProvisions.length !== 1 ? 's' : ''}`
                    : `Export ${filteredProvisions.length === allProvisions.length ? 'all ' : ''}${filteredProvisions.length} provision${filteredProvisions.length !== 1 ? 's' : ''}`}
                </button>
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
          sectionResponses={sectionResponses}
          excludableTopics={excludableTopics}
          onResponseSaved={updateSingleResponse}
          onSectionResponseSaved={updateSingleSectionResponse}
          canonicalSectionTitles={canonicalSectionTitles}
          suppressedOnlySections={suppressedOnlySections}
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
          numericCheckValues={numericCheckValues}
          lepReference={
            (lepClauseData?.height_limit || lepClauseData?.fsr)
              ? {
                  height: lepClauseData?.height_limit ?? null,
                  fsr: lepClauseData?.fsr ?? null,
                }
              : null
          }
        />
          </>
        )}

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
