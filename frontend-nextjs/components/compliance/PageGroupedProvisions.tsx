'use client';

/**
 * PageGroupedProvisions Component
 *
 * Renders provisions grouped by PDF page with:
 * - Page header showing "Page X (N provisions)" with PDF button
 * - Provisions listed within each page group
 * - Consistent styling across all rendering paths
 *
 * Replaces 4 different provision rendering paths in ProvisionsByTopic.tsx
 */

import { useState, useMemo, useCallback } from 'react';
import { ChevronDown, ChevronRight, FileText, Ruler } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { FormattedProvisionText } from './FormattedProvisionText';
import { LayerBadges, AuthorityColors } from '@/lib/design-tokens';
import { stripSectionHeader } from '@/lib/provision-text-formatter';
import { CrossReferenceList, type DocumentType } from './CrossReferenceLink';
import type { CrossReference } from '@/hooks/useCrossReferences';
import { DAResponseCapture } from './DAResponseCapture';
import { SectionResponseCapture } from './SectionResponseCapture';
import type { DaResponse, SectionResponse } from '@/hooks/useDASession';
import { buildSectionKey, parseSectionKey } from '@/lib/see/sectionKey';
import { resolveCitationUrl } from '@/lib/citation-instrument-urls';
import type { NumericCheckValues } from './NumericChecker';


/**
 * Extract first numeric limit from DCP provision text and compare against proposed value.
 * Returns a compact display string like "max 3.5m / proposed 4m" or null if not extractable.
 * Framed as reference only — not a compliance assertion.
 */
function checkNumericComplianceRef(
  text: string,
  v2Topic: string | undefined,
  v2Marker: string | undefined,
  values: NumericCheckValues
): string | null {
  const topic = (v2Topic || '').toLowerCase();
  const marker = (v2Marker || '').toLowerCase();

  let userValueStr = '';
  let metricLabel = '';
  if (topic.includes('height') || marker === 'height') {
    userValueStr = values.height; metricLabel = 'm';
  } else if (topic.includes('floor_space') || topic.includes('fsr') || topic.includes('built_form')) {
    userValueStr = values.gfa; metricLabel = 'm²';
  } else if (topic.includes('site_coverage') || topic.includes('coverage')) {
    userValueStr = values.siteCoverage; metricLabel = '%';
  } else if (topic.includes('parking') || marker === 'parking') {
    userValueStr = values.carSpaces; metricLabel = ' spaces';
  }
  if (!userValueStr) return null;

  const maxMatch = text.match(/(?:maximum|must not exceed|not exceed|no more than)\s+(\d+(?:\.\d+)?)\s*(?:m²|m2|m|%|metres?)/i);
  const minMatch = text.match(/(?:minimum|not less than|at least)\s+(\d+(?:\.\d+)?)\s*(?:m²|m2|m|%|metres?)/i);
  if (!maxMatch && !minMatch) return null;

  const limitValue = parseFloat((maxMatch || minMatch)![1]);
  const qualifier = maxMatch ? 'max' : 'min';
  const proposed = parseFloat(userValueStr);
  if (isNaN(proposed)) return `${qualifier} ${limitValue}${metricLabel}`;
  return `${qualifier} ${limitValue}${metricLabel} · proposed ${proposed}${metricLabel}`;
}

/**
 * Page offsets for Leichhardt DCP parts.
 * Each Part is a separate PDF with its own page numbering that corresponds
 * to the original full DCP document. The offset converts pdf_page (0-based
 * extract page) to the actual DCP page number shown in the PDF footer.
 *
 * Verified via OCR of PDF page footers on 2024-12-09.
 */
const LEICHHARDT_PAGE_OFFSETS: Record<string, number> = {
  'Part C Section 1': 0,
  'Part C Section 2': 110,  // page_19.png shows DCP page 129 (19+110=129)
  'Part D': 0,
  'Part E': 0,
  'Part F': 0,
  'Part G': 1,
};

/**
 * Extract page number from PDF image URL.
 * URLs follow pattern: ...page_N.png where N is the extraction page number.
 */
function extractPageFromUrl(url: string | null | undefined): number | null {
  if (!url) return null;
  const match = url.match(/page_(\d+)\./);
  return match ? parseInt(match[1], 10) : null;
}

/**
 * Get the DCP page number for display.
 * Uses pdf_printed_page (human-readable page from PDF) if available.
 * Falls back to pdf_page with Leichhardt offset, then URL extraction.
 */
function getDcpPageNumber(
  pdfPrintedPage: number | null | undefined,
  pdfPage: number | null | undefined,
  dcpPart?: string,
  pdfUrl?: string | null
): number | null {
  // PRIORITY 1: Use pdf_printed_page if available (already has correct page number)
  if (pdfPrintedPage != null) {
    return pdfPrintedPage;
  }

  // PRIORITY 2: Use pdf_page with offset (legacy extraction page numbers)
  // Fall back to URL extraction page only if pdf_page is missing
  const basePage = pdfPage ?? extractPageFromUrl(pdfUrl);

  if (basePage == null) return null;

  // Apply Leichhardt offset if applicable
  if (dcpPart && LEICHHARDT_PAGE_OFFSETS[dcpPart] !== undefined) {
    return basePage + LEICHHARDT_PAGE_OFFSETS[dcpPart];
  }

  return basePage;
}

/**
 * Fix common UTF-8 encoding artifacts (mojibake)
 */
function sanitizeText(text: string | null | undefined): string {
  if (!text) return '';
  return text
    .replace(/â€"/g, '—')  // em-dash
    .replace(/â€˜/g, "'")  // left single quote
    .replace(/â€™/g, "'")  // right single quote
    .replace(/â€œ/g, '"')  // left double quote
    .replace(/â€\u009D/g, '"')  // right double quote
    .replace(/â€¢/g, '•')  // bullet
    .replace(/â€¦/g, '…')  // ellipsis
    .replace(/Ã©/g, 'é')   // e-acute
    .replace(/Ã¨/g, 'è')   // e-grave
    .replace(/â˜…/g, '★')  // star
    .replace(/Â²/g, '²')   // superscript 2
    .replace(/Â°/g, '°')   // degree
    // Fix spacing artifacts in numbers
    .replace(/(\d)\s+(\d)\s+(\d)\s+(m|c|k)\s+m\s+\$/g, '$1$2$3$4m')  // "1 8 0 m m $" -> "180mm"
    .replace(/\s+\$/g, '')  // Remove trailing "$" artifacts
    .replace(/,\s*#\s*/g, ', ')  // ", #" -> ", "
    .replace(/[\u2018\u2019\u201C\u201D]/g, (match) => {  // Smart quotes to regular quotes
      return match === '\u2018' || match === '\u2019' ? "'" : '"';
    })
    .replace(/·/g, ' · ')  // Fix middle dot spacing
    .replace(/\s{2,}/g, ' ')  // Multiple spaces to single
    .replace(/^[â€"\s]+/, '')  // Remove leading artifacts
    .trim();
}

export interface Provision {
  id: number;
  provision_text: string;
  v2_dcp_layer: string;
  v2_dcp_part?: string;
  v2_topic?: string;
  v2_structural_category?: string;
  v2_provision_type?: string;
  v2_precinct_id?: string;
  v2_marker?: string;
  v2_has_numeric_value?: boolean;
  pdf_page?: number;
  pdf_printed_page?: number;  // Human-readable page number from PDF document
  pdf_page_image_url?: string;
  layer?: string;
  v2_heritage_type?: 'control' | 'guidance' | 'character' | 'descriptive';
  v2_heritage_element?: string[];
  v2_heritage_hca?: string;
  v2_heritage_subcategory?: string;
  // TOC section info (from dcp_table_of_contents)
  toc_section_number?: string | null;
  toc_section_title?: string | null;
  section_header?: string | null;
  v2_display_priority?: 'critical' | 'important' | 'guideline' | 'contextual';
  // Dev type relevance scoring
  relevance_level?: 'primary' | 'general' | 'secondary';
  relevance_reason?: string;
  v2_applicable_dev_types?: string[];
  source_chapter_key?: string;
  // Clause reference parsed from ref_number (e.g. "2.6 C3", "C2.2.1.1")
  clause_label?: string | null;
  // Present on the raw DB row (rp.document_id) but not previously typed here —
  // needed as the key for the instrument_registry citation fallback.
  document_id?: string;
}

interface PageGroup {
  pageNumber: number | null;      // Raw pdf_page from database
  displayPageNumber: number | null; // Actual DCP page after applying offset
  pageUrl: string | null;
  provisions: Provision[];
  dcpPart: string | null;         // For offset calculation
  // TOC section info (from first provision with TOC data)
  tocSectionNumber: string | null;
  tocSectionTitle: string | null;
}

/** Section-based group — used in DA mode instead of PDF page groups */
interface SectionGroup {
  sectionKey: string;
  sectionNumber: string | null;
  sectionTitle: string | null;
  provisions: Provision[];
}

function groupProvisionsBySection(
  provisions: Provision[],
  canonicalSectionTitles?: Map<string, string | null>,
): SectionGroup[] {
  const sectionMap = new Map<string, SectionGroup>();
  for (const prov of provisions) {
    const key = buildSectionKey(prov);
    if (!sectionMap.has(key)) {
      // Prefer canonical title from complete_toc; fall back to provision field
      const canonicalTitle = canonicalSectionTitles?.get(key);
      const sectionTitle = canonicalTitle !== undefined ? canonicalTitle : (prov.toc_section_title || null);
      sectionMap.set(key, {
        sectionKey: key,
        sectionNumber: prov.toc_section_number || null,
        sectionTitle,
        provisions: [],
      });
    }
    sectionMap.get(key)!.provisions.push(prov);
  }
  // Sort by section number (natural sort), undefined sections at end
  return Array.from(sectionMap.values()).sort((a, b) => {
    if (!a.sectionNumber && !b.sectionNumber) return 0;
    if (!a.sectionNumber) return 1;
    if (!b.sectionNumber) return -1;
    return a.sectionNumber.localeCompare(b.sectionNumber, undefined, { numeric: true });
  });
}

interface ThemeConfig {
  zebraStripeBg: string;        // e.g., 'bg-teal-50' or 'bg-amber-50/50'
  zebraStripeAltBg: string;     // e.g., 'bg-white' or 'bg-transparent'
  borderColorClass: string;     // e.g., 'border-teal-200'
  textClampLines: 2 | 3;        // line-clamp-2 or line-clamp-3
  expandThreshold: number;      // chars before showing expand button (200 or 300)
}

interface PageGroupedProvisionsProps {
  provisions: Provision[];
  expandedProvisions?: Set<number>;   // Optional - uses internal state if not provided
  onToggleProvision?: (id: number) => void;  // Optional - uses internal toggle if not provided
  onViewPdf?: (url: string, page: number) => void;  // Optional - opens in new tab if not provided
  theme?: Partial<ThemeConfig>;
  provisionTheme?: 'purple' | 'green' | 'amber';  // Color theme for control markers (C1, O1, etc.)
  showMarkers?: boolean;
  showDcpPart?: boolean;
  showLayerBadges?: boolean;    // Show layer badges (default: true)
  showLegend?: boolean;         // Show layer legend above results (default: false)
  maxProvisions?: number;       // Limit display count (e.g., 20)
  formerCouncil?: string;       // For council-specific layer labels
  councilKey?: string;          // formerCouncil.toLowerCase() — for provision text artifact cleanup
  chapterPdfUrls?: Record<string, string>;  // R2 public PDF URLs keyed by chapter_key
  highlightQuery?: string;      // Search query to highlight in provision text
  // Layer tooltip context
  zone?: string;                // Property zone (for use_specific tooltip)
  heritage?: boolean;           // Heritage classification (for condition tooltip)
  hcaName?: string;             // Heritage Conservation Area name (for condition tooltip)
  precinctName?: string;        // Precinct name (for precinct tooltip)
  // Cross-reference support
  crossReferencesMap?: Record<number, CrossReference[]>;  // Map of provisionId -> cross-references
  showCrossReferences?: boolean;  // Whether to display cross-references (default: false)
  onNavigateCrossRef?: (provisionId: number, docType: DocumentType) => void;  // Navigate to different doc
  onScrollToCrossRef?: (provisionId: number) => void;  // Scroll to provision in same doc
  // DA Mode
  isDaMode?: boolean;
  sessionToken?: string | null;
  daResponses?: Map<number, { response_text: string | null; compliance_status: string | null }>;
  /** Section-level responses — keyed by section_key */
  sectionResponses?: Map<string, SectionResponse>;
  /** Canonical section titles from complete_toc — prevents non-deterministic title from first-provision heuristic */
  canonicalSectionTitles?: Map<string, string | null>;
  /** Sections containing only objectives/descriptives — no assessable controls.
   * Rendered below the main list so planners can optionally record an acknowledgement narrative. */
  suppressedSections?: Map<string, string | null>;
  /** Normalized v2_topic values that were auto-excluded by structured intake */
  excludableTopics?: Set<string>;
  onResponseSaved?: (provisionId: number, response: DaResponse) => void;
  onSectionResponseSaved?: (sectionKey: string, response: SectionResponse) => void;
  /** DCP numeric reference — proposed values entered by planner for inline limit comparison. */
  numericCheckValues?: NumericCheckValues;
  /** LEP/DCP reference values for inline chips. Reference only — not assessed. */
  lepReference?: {
    height?: string | null;
    fsr?: string | null;
  } | null;
  // Pagination control
  hideShowMoreButton?: boolean;   // Hide the "Show more" button (for custom button layout)
  remainingCount?: number;        // Number of additional provisions available to load
  /** Force section-grouped layout without DA session (browsing mode). Sections start expanded. */
  sectionGrouped?: boolean;
}

// Compliance status badge config for DA mode header — keyed on DaResponse['compliance_status']
// Using Exclude<..., null> so TypeScript enforces exhaustiveness if the union grows.
const DA_STATUS_BADGE: Record<Exclude<DaResponse['compliance_status'], null>, { label: string; cls: string }> = {
  complies:       { label: 'Complies', cls: 'bg-green-100 text-green-700 border-green-200' },
  varies:         { label: 'Varies',   cls: 'bg-amber-100 text-amber-700 border-amber-200' },
  not_applicable: { label: 'N/A',      cls: 'bg-gray-100  text-gray-500  border-gray-200'  },
};

const SECTION_STATUS_BADGE: Record<Exclude<SectionResponse['status'], null>, { label: string; cls: string }> = {
  complies:       { label: 'Complies', cls: 'bg-green-100 text-green-700 border-green-200' },
  varies:         { label: 'Varies',   cls: 'bg-amber-100 text-amber-700 border-amber-200' },
  not_applicable: { label: 'N/A',      cls: 'bg-gray-100  text-gray-500  border-gray-200'  },
  flagged:        { label: 'Flagged',  cls: 'bg-red-50   text-red-700   border-red-200'    },
};

// Default theme (teal, used by most paths)
const DEFAULT_THEME: ThemeConfig = {
  zebraStripeBg: 'bg-teal-50',
  zebraStripeAltBg: 'bg-white',
  borderColorClass: 'border-teal-200',
  textClampLines: 3,
  expandThreshold: 300,
};

// Layer color mapping
const LAYER_COLORS: Record<string, string> = {
  generic: `${LayerBadges.generic.bg} ${LayerBadges.generic.text}`,
  use_specific: `${LayerBadges.use_specific.bg} ${LayerBadges.use_specific.text}`,
  condition: `${LayerBadges.condition.bg} ${LayerBadges.condition.text}`,
  precinct: `${LayerBadges.precinct.bg} ${LayerBadges.precinct.text}`,
};

// Default labels (used when formerCouncil not specified)
const LAYER_LABELS: Record<string, string> = {
  generic: 'LGA-wide',
  use_specific: 'Zone-Specific',
  condition: 'Condition',
  precinct: 'Precinct',
};

// Council-specific layer labels for the "generic" layer
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

/**
 * Group provisions by PDF page and calculate display page numbers with offsets
 */
function groupProvisionsByPage(provisions: Provision[], chapterPdfUrls?: Record<string, string>): PageGroup[] {
  const pageMap = new Map<string, PageGroup>();
  const ungrouped: Provision[] = [];

  for (const prov of provisions) {
    if (prov.pdf_page_image_url) {
      const key = prov.pdf_page_image_url;
      if (!pageMap.has(key)) {
        const dcpPart = prov.v2_dcp_part || null;
        const rawPage = prov.pdf_page || null;
        const printedPage = prov.pdf_printed_page || null;

        // DEBUG: Log what we're receiving for heritage provisions
        if (prov.v2_marker === 'heritage' && rawPage === 20) {
          console.log(`[PageGroupedProvisions DEBUG] ID ${prov.id}: pdf_page=${rawPage}, pdf_printed_page=${printedPage}, hasField=${prov.hasOwnProperty('pdf_printed_page')}`);
        }

        pageMap.set(key, {
          pageNumber: rawPage,
          displayPageNumber: getDcpPageNumber(printedPage, rawPage, dcpPart || undefined, prov.pdf_page_image_url),
          pageUrl: prov.pdf_page_image_url,
          provisions: [],
          dcpPart: dcpPart,
          tocSectionNumber: prov.toc_section_number || null,
          tocSectionTitle: prov.toc_section_title || null,
        });
      } else {
        // If this provision has TOC info and the group doesn't, capture it
        const group = pageMap.get(key)!;
        if (!group.tocSectionNumber && prov.toc_section_number) {
          group.tocSectionNumber = prov.toc_section_number;
          group.tocSectionTitle = prov.toc_section_title || null;
        }
      }
      pageMap.get(key)!.provisions.push(prov);
    } else if (prov.pdf_page && chapterPdfUrls && prov.source_chapter_key && chapterPdfUrls[prov.source_chapter_key]) {
      // No page image but we have a chapter-specific PDF URL — group by chapter+page
      const chapterUrl = chapterPdfUrls[prov.source_chapter_key];
      const key = `direct-${prov.source_chapter_key}-${prov.pdf_page}`;
      if (!pageMap.has(key)) {
        pageMap.set(key, {
          pageNumber: prov.pdf_page,
          displayPageNumber: null,  // Direct-PDF: no reliable printed page number, omit label
          pageUrl: `${chapterUrl}#page=${prov.pdf_page}`,
          provisions: [],
          dcpPart: prov.v2_dcp_part || null,
          tocSectionNumber: prov.toc_section_number || null,
          tocSectionTitle: prov.toc_section_title || null,
        });
      }
      pageMap.get(key)!.provisions.push(prov);
    } else {
      ungrouped.push(prov);
    }
  }

  // Sort by display page number
  const groups = Array.from(pageMap.values())
    .sort((a, b) => (a.displayPageNumber ?? a.pageNumber ?? 999) - (b.displayPageNumber ?? b.pageNumber ?? 999));

  // Add ungrouped at end
  if (ungrouped.length > 0) {
    groups.push({ pageNumber: null, displayPageNumber: null, pageUrl: null, provisions: ungrouped, dcpPart: null, tocSectionNumber: null, tocSectionTitle: null });
  }

  return groups;
}

/**
 * Legend for Control/Objective markers (C1, O1, etc.)
 * Only shown when provisions contain these DCP markers
 */
function MarkerLegend() {
  return (
    <div className="flex items-center gap-4 text-xs text-gray-600 py-1.5 px-3 bg-teal-50 border border-teal-100 rounded-lg mb-3">
      <span className="font-medium text-teal-700">DCP Markers:</span>
      <div className="flex items-center gap-1.5">
        <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-teal-100 text-teal-700 font-bold text-[10px]">C</span>
        <span>Control (development requirement)</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-teal-100 text-teal-700 font-bold text-[10px]">O</span>
        <span>Objective (design goal)</span>
      </div>
    </div>
  );
}

/**
 * Inline legend showing layer colors and labels
 */
function LayerLegend({ formerCouncil }: { formerCouncil?: string }) {
  const council = formerCouncil?.toLowerCase();
  const labels = council && COUNCIL_LAYER_LABELS[council]
    ? COUNCIL_LAYER_LABELS[council]
    : LAYER_LABELS;

  const layers = [
    { key: 'generic', color: '#22c55e' },    // teal
    { key: 'use_specific', color: '#3b82f6' }, // blue
    { key: 'condition', color: '#f59e0b' },  // amber
    { key: 'precinct', color: '#8b5cf6' },   // purple
  ];

  return (
    <div className="flex items-center gap-4 text-sm text-gray-600 py-2 px-3 bg-gray-50 rounded-lg mb-3">
      <span className="font-medium text-gray-700">Layer Key:</span>
      {layers.map(({ key, color }) => (
        <div key={key} className="flex items-center gap-1.5">
          <div
            className="w-3 h-3 rounded-sm"
            style={{ backgroundColor: color }}
          />
          <span>{labels[key]}</span>
        </div>
      ))}
    </div>
  );
}

export function PageGroupedProvisions({
  provisions,
  expandedProvisions: externalExpandedProvisions,
  onToggleProvision: externalToggleProvision,
  onViewPdf: externalViewPdf,
  theme: themeOverrides,
  provisionTheme = 'purple',
  showMarkers = true,
  showDcpPart = false,
  showLayerBadges = true,
  showLegend = false,
  maxProvisions,
  formerCouncil,
  councilKey,
  chapterPdfUrls,
  highlightQuery,
  crossReferencesMap,
  showCrossReferences = false,
  onNavigateCrossRef,
  onScrollToCrossRef,
  zone,
  heritage,
  hcaName,
  precinctName,
  isDaMode = false,
  sessionToken,
  daResponses,
  sectionResponses,
  canonicalSectionTitles,
  suppressedSections,
  excludableTopics,
  onResponseSaved,
  onSectionResponseSaved,
  numericCheckValues,
  lepReference,
  hideShowMoreButton,
  remainingCount,
  sectionGrouped = false,
}: PageGroupedProvisionsProps) {
  const theme = { ...DEFAULT_THEME, ...themeOverrides };

  // DEBUG: Log provision theme
  console.log(`[PageGroupedProvisions] Using provisionTheme: ${provisionTheme}`);

  // DEBUG: Log component render
  console.log(`[PageGroupedProvisions] Rendering with ${provisions.length} provisions`);
  const heritageCount = provisions.filter(p => p.v2_marker === 'heritage').length;
  if (heritageCount > 0) {
    console.log(`[PageGroupedProvisions] ${heritageCount} heritage provisions`);
    const sample = provisions.find(p => p.v2_marker === 'heritage' && p.pdf_page === 20);
    if (sample) {
      console.log(`[PageGroupedProvisions] Page 20 provision:`, {
        id: sample.id,
        pdf_page: sample.pdf_page,
        pdf_printed_page: sample.pdf_printed_page,
        has_field: 'pdf_printed_page' in sample
      });
    }
  }

  // Group provisions by page
  const pageGroups = useMemo(() => groupProvisionsByPage(provisions, chapterPdfUrls), [provisions, chapterPdfUrls]);

  // Track expanded page groups (non-DA mode and suppressed sections in browse mode)
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // DA mode: tracks which sections the planner has explicitly opened.
  // Starts empty = all sections collapsed (assess-first workflow).
  const [daExpandedSections, setDaExpandedSections] = useState<Set<string>>(new Set());

  // Internal state for expanded provisions (used when prop not provided)
  const [internalExpandedProvisions, setInternalExpandedProvisions] = useState<Set<number>>(new Set());

  // Use external props if provided, otherwise use internal state
  const expandedProvisions = externalExpandedProvisions ?? internalExpandedProvisions;

  const onToggleProvision = externalToggleProvision ?? ((id: number) => {
    setInternalExpandedProvisions(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  });

  const onViewPdf = externalViewPdf ?? ((url: string, page: number) => {
    // Default: open PDF in new tab
    window.open(url, '_blank');
  });

  const toggleGroup = (key: string) => {
    if (isDaMode) {
      setDaExpandedSections(prev => {
        const next = new Set(prev);
        if (next.has(key)) next.delete(key); else next.add(key);
        return next;
      });
    } else {
      setCollapsedGroups(prev => {
        const next = new Set(prev);
        if (next.has(key)) next.delete(key); else next.add(key);
        return next;
      });
    }
  };

  // Advance to the next section without a status response — linear progression through assessment.
  const handleNextSection = (currentKey: string) => {
    const currentIdx = sectionGroups.findIndex(s => s.sectionKey === currentKey);
    const nextSection = sectionGroups.slice(currentIdx + 1)
      .find(s => !sectionResponses?.get(s.sectionKey)?.status);
    if (!nextSection) return;
    setDaExpandedSections(prev => {
      const next = new Set(prev);
      next.delete(currentKey);
      next.add(nextSection.sectionKey);
      return next;
    });
    setTimeout(() => {
      document.querySelector(`[data-section-key="${nextSection.sectionKey}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  };

  const [showAll, setShowAll] = useState(false);

  // Apply max provisions limit if specified — reset showAll when provisions change
  const { displayProvisions, limitedCount } = useMemo(() => {
    if (maxProvisions && !showAll && provisions.length > maxProvisions) {
      return {
        displayProvisions: provisions.slice(0, maxProvisions),
        limitedCount: provisions.length
      };
    }
    return {
      displayProvisions: provisions,
      limitedCount: 0
    };
  }, [provisions, maxProvisions, showAll]);

  // Re-group after limiting
  const displayGroups = useMemo(
    () => groupProvisionsByPage(displayProvisions, chapterPdfUrls),
    [displayProvisions, chapterPdfUrls]
  );

  // Section groups for DA mode or TOC browse mode (sectionGrouped) — group by toc_section_number
  const sectionGroups = useMemo(
    () => (isDaMode || sectionGrouped) ? groupProvisionsBySection(displayProvisions, canonicalSectionTitles) : [],
    [isDaMode, sectionGrouped, displayProvisions, canonicalSectionTitles]
  );

  const getLayerColor = (layer: string | null | undefined): string => {
    if (!layer || layer === 'unknown' || layer === 'null') return LAYER_COLORS.generic;
    return LAYER_COLORS[layer] || 'bg-gray-100 text-gray-700';
  };

  const getLayerLabel = (layer: string | null | undefined): string => {
    if (!layer || layer === 'unknown' || layer === 'null') {
      // Use council-specific label for generic layer
      if (formerCouncil && COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()]) {
        return COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()].generic;
      }
      return LAYER_LABELS.generic;
    }
    // Use council-specific labels if available
    if (formerCouncil && COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()]) {
      return COUNCIL_LAYER_LABELS[formerCouncil.toLowerCase()][layer] || LAYER_LABELS[layer] || layer;
    }
    return LAYER_LABELS[layer] || layer;
  };

  // Get tooltip explanation for why a layer applies
  const getLayerTooltip = (layer: string | null | undefined): string => {
    const councilName = formerCouncil || 'this council';

    if (!layer || layer === 'unknown' || layer === 'null' || layer === 'generic') {
      return `These provisions apply to ALL properties in ${councilName}`;
    }

    if (layer === 'use_specific') {
      if (zone) {
        return `These provisions apply because your property is in ${zone} zone`;
      }
      return 'These provisions apply based on your property\'s zoning';
    }

    if (layer === 'condition') {
      if (heritage && hcaName) {
        return `These provisions apply because your property is in ${hcaName}`;
      } else if (heritage) {
        return 'These provisions apply because your property has heritage classification';
      }
      return 'These provisions apply based on site conditions (heritage, flood, bushfire, etc.)';
    }

    if (layer === 'precinct') {
      if (precinctName) {
        return `These provisions apply because your property is in ${precinctName}`;
      }
      return 'These provisions apply based on your property\'s precinct location';
    }

    return `These provisions are relevant to your property`;
  };

  // Format topic for display (snake_case → Title Case)
  const formatTopic = (topic: string | null | undefined): string => {
    if (!topic) return 'General';
    return topic
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  let globalIndex = 0;

  // Check if any provisions have C/O markers
  const hasMarkers = useMemo(() =>
    showMarkers && provisions.some(p => p.v2_marker && /^[CO]\d+$/.test(p.v2_marker)),
    [provisions, showMarkers]
  );

  // Section-grouped rendering — used in DA mode (assess workflow) and TOC browse mode.
  // When sectionGroups is empty (all provisions filtered by search/layer), render an
  // empty state rather than falling through to page-grouped rendering, which would
  // surface provision-level DAResponseCapture widgets and break the section model.
  if (isDaMode || sectionGrouped) {
    if (sectionGroups.length === 0) {
      return (
        <div className="py-6 text-center text-sm text-gray-400 italic">
          No sections visible — adjust your search or filter to see assessable sections.
        </div>
      );
    }
    return (
      <div className="space-y-3">
        {hasMarkers && <MarkerLegend />}
        {sectionGroups.map((section) => {
          const sectionResp = sectionResponses?.get(section.sectionKey);
          const sectionStatus = sectionResp?.status ?? null;
          const sectionBadge = sectionStatus ? SECTION_STATUS_BADGE[sectionStatus] : null;
          // DA mode: collapsed-first (assess workflow — planner opens one section at a time).
          // Browse mode: expanded-first (reading workflow — provisions visible immediately).
          const isCollapsed = isDaMode
            ? !daExpandedSections.has(section.sectionKey)
            : collapsedGroups.has(section.sectionKey);

          return (
            <div key={section.sectionKey} data-section-key={section.sectionKey} className={`border rounded-lg overflow-hidden ${theme.borderColorClass}`}>
              {/* Section header */}
              <div
                className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => toggleGroup(section.sectionKey)}
              >
                <div className="flex items-center gap-2 min-w-0">
                  {isCollapsed ? (
                    <ChevronRight className="h-4 w-4 text-gray-500 shrink-0" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-500 shrink-0" />
                  )}
                  <span className="text-sm text-gray-600 truncate">
                    {section.sectionNumber && (
                      <span className="font-semibold text-teal-700">{section.sectionNumber}</span>
                    )}
                    {section.sectionNumber && section.sectionTitle && ' '}
                    {section.sectionTitle && (
                      <span className="font-medium text-gray-700">
                        {(() => {
                          const clean = sanitizeText(section.sectionTitle);
                          return clean.length > 60 ? clean.substring(0, 60) + '…' : clean;
                        })()}
                      </span>
                    )}
                    {!section.sectionNumber && !section.sectionTitle && (
                      <span className="text-gray-400 italic">General provisions</span>
                    )}
                    <span className="text-gray-400 ml-1.5">
                      · {section.provisions.length} provision{section.provisions.length !== 1 ? 's' : ''}
                    </span>
                  </span>
                </div>
                {sectionBadge && (
                  <span className={`text-xs px-2 py-0.5 rounded border font-medium shrink-0 ml-2 ${sectionBadge.cls}`}>
                    {sectionBadge.label}
                  </span>
                )}
              </div>

              {/* Expanded section content — assess-first layout */}
              {!isCollapsed && (
                <div>
                  {/* Section assessment — above provisions so planner assesses before reading */}
                  {isDaMode && !!onSectionResponseSaved && (
                    <div className="border-b border-gray-100">
                      <SectionResponseCapture
                        sectionKey={section.sectionKey}
                        sectionTitle={section.sectionTitle}
                        sessionToken={sessionToken ?? null}
                        existingResponse={sectionResp}
                        onSaved={(key, response) => {
                          onSectionResponseSaved(key, response);
                          // Auto-collapse once planner has set a status
                          if (response.status !== null) {
                            setDaExpandedSections(prev => {
                              const next = new Set(prev);
                              next.delete(section.sectionKey);
                              return next;
                            });
                          }
                        }}
                      />
                      {/* Next → linear progression — advances to next unassessed section */}
                      {(() => {
                        const currentIdx = sectionGroups.findIndex(s => s.sectionKey === section.sectionKey);
                        const nextSection = sectionGroups.slice(currentIdx + 1)
                          .find(s => !sectionResponses?.get(s.sectionKey)?.status);
                        if (!nextSection) return null;
                        const nextLabel = nextSection.sectionNumber
                          ? `§${nextSection.sectionNumber}`
                          : nextSection.sectionTitle
                            ? nextSection.sectionTitle.substring(0, 30)
                            : 'next section';
                        return (
                          <div className="px-3 pb-2 flex justify-end">
                            <button
                              onClick={() => handleNextSection(section.sectionKey)}
                              className="text-xs text-teal-700 hover:text-teal-900 font-medium"
                            >
                              Next: {nextLabel} →
                            </button>
                          </div>
                        );
                      })()}
                    </div>
                  )}

                  {/* Provisions — read-only reference text */}
                  <div className="divide-y divide-gray-100">
                    {section.provisions.map((provision, provIdx) => {
                      const isExpanded = expandedProvisions.has(provision.id);
                      const layer = provision.v2_dcp_layer || provision.layer;
                      const isEven = provIdx % 2 === 0;
                      const bgClass = isEven ? theme.zebraStripeBg : theme.zebraStripeAltBg;

                      return (
                        <div
                          key={provision.id}
                          data-provision-id={provision.id}
                          className={`px-4 py-3 ${bgClass} border-l-4`}
                          style={{ borderLeftColor: layer === 'precinct' ? '#8b5cf6' : layer === 'condition' ? '#f59e0b' : layer === 'use_specific' ? '#3b82f6' : '#14b8a6' }}
                        >
                          {/* Provision header */}
                          <div className="flex items-start gap-2 mb-1">
                            {showMarkers && provision.v2_marker && getLayerLabel(layer).toLowerCase() !== provision.v2_marker.toLowerCase() && (
                              <Badge
                                variant="outline"
                                className="text-sm font-mono bg-white shrink-0 cursor-help"
                                title={provision.v2_marker.startsWith('C') ? `Control ${provision.v2_marker.slice(1)}` : provision.v2_marker.startsWith('O') ? `Objective ${provision.v2_marker.slice(1)}` : provision.v2_marker}
                              >
                                {provision.v2_marker}
                              </Badge>
                            )}
                            {/* Clause Label */}
                            {provision.clause_label && (
                              <span
                                className="text-xs font-mono px-1.5 py-0.5 bg-slate-100 text-slate-600 border border-slate-300 rounded shrink-0"
                                title={`DCP clause reference: ${provision.clause_label}`}
                              >
                                {provision.clause_label}
                              </span>
                            )}
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Badge className={`text-sm font-medium shrink-0 ${getLayerColor(layer)}`}>
                                  {getLayerLabel(layer)}
                                </Badge>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>{getLayerTooltip(layer)}</p>
                              </TooltipContent>
                            </Tooltip>
                            {/* PDF/citation link for individual provision — image URL, then R2
                                chapter URL, then the instrument_registry-derived whole-of-instrument
                                link (see lib/citation-instrument-urls.ts). */}
                            {(() => {
                              const resolved = resolveCitationUrl(provision, chapterPdfUrls);
                              if (!resolved) return null;
                              if (resolved.kind === 'image') {
                                return (
                                  <button
                                    onClick={() => onViewPdf(resolved.url, provision.pdf_printed_page || provision.pdf_page || 0)}
                                    className="p-0.5 rounded hover:bg-teal-100 shrink-0"
                                    title={`PDF page ${provision.pdf_printed_page || provision.pdf_page}`}
                                  >
                                    <FileText className="w-3.5 h-3.5 text-teal-500 hover:text-teal-700" />
                                  </button>
                                );
                              }
                              if (resolved.kind === 'chapter') {
                                // resolveCitationUrl no longer requires pdf_page to return a
                                // chapter match (2026-09-01 fix) — the anchor is added here,
                                // only when a page number actually exists.
                                const hasPage = Boolean(provision.pdf_page);
                                const chapterHref = hasPage
                                  ? `${resolved.url}#page=${provision.pdf_page}`
                                  : resolved.url;
                                return (
                                  <button
                                    onClick={() => onViewPdf(chapterHref, provision.pdf_page || 0)}
                                    className="p-0.5 rounded hover:bg-teal-100 shrink-0"
                                    title={hasPage ? `PDF page ${provision.pdf_page}` : 'View chapter PDF'}
                                  >
                                    <FileText className="w-3.5 h-3.5 text-teal-500 hover:text-teal-700" />
                                  </button>
                                );
                              }
                              // 'instrument' — a plain external link, not routed through onViewPdf:
                              // this is an HTML legislation.nsw.gov.au page, not a PDF, and some
                              // parents override onViewPdf with a PDF-only viewer.
                              return (
                                <a
                                  href={resolved.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="p-0.5 rounded hover:bg-teal-100 shrink-0"
                                  title="View on legislation.nsw.gov.au"
                                >
                                  <FileText className="w-3.5 h-3.5 text-teal-500 hover:text-teal-700" />
                                </a>
                              );
                            })()}
                          </div>

                          {/* Provision text */}
                          <div
                            className="text-sm text-gray-700 cursor-pointer"
                            onClick={() => onToggleProvision(provision.id)}
                          >
                            {isExpanded ? (
                              <FormattedProvisionText
                                text={stripSectionHeader(provision.provision_text, provision.toc_section_title)}
                                compact
                                stripMarker={showMarkers && provision.v2_marker ? provision.v2_marker : undefined}
                                highlightQuery={highlightQuery}
                                theme={provisionTheme}
                                councilKey={councilKey}
                              />
                            ) : (
                              <p className={theme.textClampLines === 2 ? 'line-clamp-2' : 'line-clamp-3'}>
                                {showMarkers && provision.v2_marker
                                  ? stripSectionHeader(provision.provision_text, provision.toc_section_title)
                                      .replace(new RegExp(`^\\s*${provision.v2_marker}\\s+`, 'i'), '')
                                  : stripSectionHeader(provision.provision_text, provision.toc_section_title)}
                              </p>
                            )}
                          </div>
                          {provision.provision_text.length > theme.expandThreshold && (
                            <button
                              className="text-xs text-blue-600 hover:text-blue-800 mt-1 font-medium"
                              onClick={(e) => { e.stopPropagation(); onToggleProvision(provision.id); }}
                            >
                              {isExpanded ? '↑ Show less' : '+ Show more'}
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Show more */}
        {!hideShowMoreButton && maxProvisions && provisions.length > maxProvisions && (
          showAll ? (
            <button onClick={() => setShowAll(false)} className="w-full py-2.5 text-sm text-gray-400 hover:text-gray-600 font-medium border-t border-gray-100 hover:bg-gray-50 transition-colors">
              Hide {provisions.length - maxProvisions} provisions
            </button>
          ) : (
            <button onClick={() => setShowAll(true)} className="w-full py-2.5 text-sm text-teal-600 hover:text-teal-800 font-medium border-t border-gray-100 hover:bg-teal-50 transition-colors">
              Show {provisions.length - maxProvisions} more provisions
            </button>
          )
        )}

        {/* Objectives-only sections — no enforceable controls, not in assessment scope,
            but planner may optionally record a consistency narrative for professional completeness */}
        {suppressedSections && suppressedSections.size > 0 && (
          <div className="mt-1 space-y-2">
            <p className="text-xs text-gray-400 italic px-1 pt-2 border-t border-gray-100">
              Objectives &amp; design guidance — no enforceable controls, not counted in scope:
            </p>
            {[...suppressedSections.entries()].map(([sectionKey, sectionTitle]) => {
              const { sectionNumber } = parseSectionKey(sectionKey);
              const displayNum = sectionNumber === 'general' ? null : sectionNumber;
              const sectionResp = sectionResponses?.get(sectionKey);
              const sectionStatus = sectionResp?.status ?? null;
              const sectionBadge = sectionStatus ? SECTION_STATUS_BADGE[sectionStatus] : null;
              const isCollapsed = isDaMode
                ? !daExpandedSections.has(sectionKey)
                : collapsedGroups.has(sectionKey);
              return (
                <div key={sectionKey} className="border border-dashed border-gray-200 rounded-lg overflow-hidden opacity-75">
                  <div
                    className="flex items-center justify-between px-3 py-2 bg-gray-50/50 cursor-pointer hover:bg-gray-100/50 transition-colors"
                    onClick={() => toggleGroup(sectionKey)}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {isCollapsed ? (
                        <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                      )}
                      <span className="text-xs text-gray-500 truncate">
                        {displayNum && <span className="font-medium text-gray-500">{displayNum}</span>}
                        {displayNum && sectionTitle && ' '}
                        {sectionTitle && <span className="text-gray-500">{sanitizeText(sectionTitle)}</span>}
                        {!displayNum && !sectionTitle && <span className="italic text-gray-400">General objectives</span>}
                        <span className="text-gray-400 ml-1.5">· objectives only</span>
                      </span>
                    </div>
                    {sectionBadge && (
                      <span className={`text-xs px-2 py-0.5 rounded border font-medium shrink-0 ml-2 ${sectionBadge.cls}`}>
                        {sectionBadge.label}
                      </span>
                    )}
                  </div>
                  {!isCollapsed && (
                    <div className="px-3 pb-1 bg-white/50">
                      <p className="text-xs text-gray-400 italic py-2">
                        This section contains only objectives and design guidance. No enforceable controls apply.
                        You may optionally record a consistency statement below.
                      </p>
                      {isDaMode && !!onSectionResponseSaved && (
                        <SectionResponseCapture
                          sectionKey={sectionKey}
                          sectionTitle={sectionTitle}
                          sessionToken={sessionToken ?? null}
                          existingResponse={sectionResp}
                          onSaved={onSectionResponseSaved}
                        />
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Non-DA mode: page-grouped rendering (original)
  return (
    <div className="space-y-3">
      {/* Marker Legend - shown only when provisions have C/O markers */}
      {hasMarkers && <MarkerLegend />}

      {/* Layer Legend - shown above results when enabled */}
      {showLegend && <LayerLegend formerCouncil={formerCouncil} />}

      {displayGroups.map((group, groupIdx) => {
        const groupKey = group.pageUrl || `ungrouped-${groupIdx}`;
        const isCollapsed = collapsedGroups.has(groupKey);

        return (
          <div
            key={groupKey}
            className={`border rounded-lg overflow-hidden ${theme.borderColorClass}`}
          >
            {/* Page Group Header */}
            <div
              className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => toggleGroup(groupKey)}
            >
              <div className="flex items-center gap-2">
                {isCollapsed ? (
                  <ChevronRight className="h-4 w-4 text-gray-500" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-gray-500" />
                )}
                <span className="text-sm text-gray-600">
                  {/* TOC Section info (if available) */}
                  {group.tocSectionNumber && (
                    <span className="font-semibold text-teal-700">{group.tocSectionNumber}</span>
                  )}
                  {group.tocSectionNumber && group.tocSectionTitle && ' '}
                  {group.tocSectionTitle && (
                    <span className="font-medium text-gray-700">
                      {(() => {
                        const clean = sanitizeText(group.tocSectionTitle);
                        return clean.length > 40 ? clean.substring(0, 40) + '...' : clean;
                      })()}
                    </span>
                  )}
                  {/* Separator after TOC info */}
                  {(group.tocSectionNumber || group.tocSectionTitle) && (
                    <span className="text-gray-400 mx-1">·</span>
                  )}
                  {/* DCP Part (if no TOC info) - skip if "unknown" */}
                  {!group.tocSectionNumber && group.dcpPart && group.dcpPart !== 'unknown' && (
                    <span className="font-medium text-gray-700">{group.dcpPart}</span>
                  )}
                  {/* Page number — only for screenshot-based provisions with a reliable printed page */}
                  {group.displayPageNumber ? (
                    <span className="text-gray-500"> · PDF page {group.displayPageNumber}</span>
                  ) : !group.pageUrl?.includes('#page=') && (
                    <span className="text-gray-400"> · No page reference</span>
                  )}
                  <span className="text-gray-400 ml-1">
                    · {group.provisions.length} provision{group.provisions.length !== 1 ? 's' : ''}
                  </span>
                </span>
              </div>

              {/* PDF Button in header - icon only with tooltip */}
              {group.pageUrl && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewPdf(group.pageUrl!, group.displayPageNumber || 0);
                  }}
                  className="p-1.5 rounded hover:bg-teal-100 transition-colors flex-shrink-0"
                  title={`${group.dcpPart && group.dcpPart !== 'unknown' ? group.dcpPart + ' - ' : ''}PDF page ${group.displayPageNumber || 1}`}
                >
                  <FileText className="w-4 h-4 text-teal-600 hover:text-teal-800" />
                </button>
              )}
            </div>

            {/* Provisions List (collapsible) */}
            {!isCollapsed && (
              <div className="divide-y divide-gray-100">
                {group.provisions.map((provision, provIdx) => {
                  const isExpanded = expandedProvisions.has(provision.id);
                  const layer = provision.v2_dcp_layer || provision.layer;
                  const isEven = globalIndex++ % 2 === 0;
                  const bgClass = isEven ? theme.zebraStripeBg : theme.zebraStripeAltBg;
                  // Grey out provisions whose structural category is excluded by intake data (DD-1).
                  // In DA mode this never triggers — excluded provisions are split out upstream.
                  const isExcludedByTriage = !isDaMode && !!excludableTopics?.has(
                    provision.v2_structural_category || ''
                  );
                  // Subtle dimming for secondary-relevance provisions in DA mode
                  const isSecondaryDevType = isDaMode && provision.relevance_level === 'secondary';

                  return (
                    <div
                      key={provision.id}
                      data-provision-id={provision.id}
                      className={`px-4 py-3 ${bgClass} border-l-4 ${isExcludedByTriage ? 'opacity-35' : isSecondaryDevType ? 'opacity-60' : ''}`}
                      title={isSecondaryDevType ? (provision.relevance_reason || 'May not apply to your development type') : undefined}
                      style={{ borderLeftColor: layer === 'precinct' ? '#8b5cf6' : layer === 'condition' ? '#f59e0b' : layer === 'use_specific' ? '#3b82f6' : '#14b8a6' }}
                    >
                      {/* Provision Header Row */}
                      <div className="flex items-start gap-2 mb-1">
                        {/* Marker Badge - C=Control, O=Objective from DCP structure */}
                        {showMarkers && provision.v2_marker && getLayerLabel(layer).toLowerCase() !== provision.v2_marker.toLowerCase() && (
                          <Badge
                            variant="outline"
                            className="text-sm font-mono bg-white shrink-0 cursor-help"
                            title={provision.v2_marker.startsWith('C') ? `Control ${provision.v2_marker.slice(1)} - A specific development requirement` : provision.v2_marker.startsWith('O') ? `Objective ${provision.v2_marker.slice(1)} - A design goal/principle` : provision.v2_marker}
                          >
                            {provision.v2_marker}
                          </Badge>
                        )}

                        {/* Clause Label - DCP clause reference (e.g. "2.6 C3", "C2.2.1.1") */}
                        {provision.clause_label && (
                          <span
                            className="text-xs font-mono px-1.5 py-0.5 bg-slate-100 text-slate-600 border border-slate-300 rounded shrink-0"
                            title={`DCP clause reference: ${provision.clause_label}`}
                          >
                            {provision.clause_label}
                          </span>
                        )}

                        {/* Layer Badge - council-specific label with larger font */}
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge className={`text-sm font-medium shrink-0 ${getLayerColor(layer)}`}>
                              {getLayerLabel(layer)}
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{getLayerTooltip(layer)}</p>
                          </TooltipContent>
                        </Tooltip>

                        {/* HCA Badge - show if HCA-specific */}
                        {provision.v2_heritage_hca && (
                          <Badge className="text-sm shrink-0 bg-amber-100 text-amber-800 border-amber-300">
                            {provision.v2_heritage_hca.replace(/_/g, ' ').replace(/hca /i, 'HCA ')}
                          </Badge>
                        )}
                        {provision.v2_marker === 'heritage' && !provision.v2_heritage_hca && (
                          <Badge variant="outline" className="text-sm shrink-0 bg-gray-100 text-gray-700 border-gray-300">
                            All HCAs
                          </Badge>
                        )}

                        {/* Numeric Badge - provisions with numeric standards */}
                        {provision.v2_display_priority === 'critical' && (
                          <Badge className="text-sm shrink-0 bg-red-100 text-red-800 border-red-300 inline-flex items-center gap-1">
                            <Ruler className="w-3 h-3" /> Numeric
                          </Badge>
                        )}

                        {/* Relevance Badge - Dev type matching */}
                        {provision.relevance_level === 'primary' && (
                          <Badge className="text-sm shrink-0 bg-blue-100 text-blue-800 border-blue-300">
                            Primary Match
                          </Badge>
                        )}
                        {provision.relevance_level === 'secondary' && !isDaMode && (
                          <Badge variant="outline" className="text-sm shrink-0 bg-gray-50 text-gray-600 border-gray-300">
                            May Apply
                          </Badge>
                        )}

                        {/* DA Mode status badge — shows saved compliance status inline */}
                        {isDaMode && (() => {
                          const resp = daResponses?.get(provision.id);
                          const status = resp?.compliance_status;
                          if (!status) return null;
                          const badge = DA_STATUS_BADGE[status as keyof typeof DA_STATUS_BADGE];
                          const isPreFilled = status === 'not_applicable' &&
                            typeof resp?.response_text === 'string' &&
                            resp.response_text.includes('Override if the purpose');
                          return (
                            <span className="inline-flex items-center gap-1 flex-shrink-0">
                              <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${badge.cls}`}>
                                {badge.label}
                              </span>
                              {isPreFilled && (
                                <span className="text-xs text-gray-400 italic">pre-filled</span>
                              )}
                            </span>
                          );
                        })()}

                        {/* DCP Part (optional) */}
                        {showDcpPart && provision.v2_dcp_part && (
                          <span className="text-xs text-gray-400 shrink-0">
                            {provision.v2_dcp_part}
                          </span>
                        )}
                      </div>

                      {/* LEP/DCP reference chips — shown on relevant provisions, reference only */}
                      {lepReference && (() => {
                        const cat = provision.v2_structural_category;

                        if (cat === 'height' && lepReference.height) {
                          return (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="inline-flex items-center text-xs px-1.5 py-0.5 rounded border bg-blue-50 text-blue-700 border-blue-200 font-medium mb-1 cursor-default">
                                  LEP max: {lepReference.height}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="right" className="max-w-xs">
                                LEP height limit — reference only. Not assessed by this tool. Verify against current LEP schedules.
                              </TooltipContent>
                            </Tooltip>
                          );
                        }

                        if ((cat === 'site_coverage' || cat === 'fsr') && lepReference.fsr) {
                          return (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="inline-flex items-center text-xs px-1.5 py-0.5 rounded border bg-blue-50 text-blue-700 border-blue-200 font-medium mb-1 cursor-default">
                                  LEP max FSR: {lepReference.fsr}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="right" className="max-w-xs">
                                LEP floor space ratio — reference only. Not assessed by this tool. Verify against current LEP schedules.
                              </TooltipContent>
                            </Tooltip>
                          );
                        }

                        // The 'setbacks' branch was removed with /api/setbacks/reference.
                        // It read `setback_rules`, a table with 0 rows in production that
                        // never had any, so this chip could never render. Verified setback
                        // numbers are served by /api/dcp/structured-controls instead.

                        return null;
                      })()}

                      {/* DCP numeric reference chip — shows DCP limit from provision text vs proposed value */}
                      {numericCheckValues && (() => {
                        const topic = (provision.v2_topic || '').toLowerCase();
                        const cat = provision.v2_structural_category || '';
                        // Only attempt on categories where DCP has hard limits
                        const relevant = cat === 'height' || cat === 'site_coverage' || cat === 'parking' ||
                          topic.includes('height') || topic.includes('coverage') || topic.includes('parking');
                        if (!relevant) return null;
                        const check = checkNumericComplianceRef(
                          provision.provision_text,
                          provision.v2_topic,
                          provision.v2_marker,
                          numericCheckValues
                        );
                        if (!check) return null;
                        return (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded border bg-slate-50 text-slate-600 border-slate-200 font-medium mb-1 cursor-default font-mono">
                                DCP: {check}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent side="right" className="max-w-xs">
                              DCP provision limit — indicative reference only. Not a compliance determination. Verify against the full provision text.
                            </TooltipContent>
                          </Tooltip>
                        );
                      })()}

                      {/* Provision Text - truncated when collapsed, formatted when expanded */}
                      <div
                        className="text-sm text-gray-700 cursor-pointer"
                        onClick={() => onToggleProvision(provision.id)}
                      >
                        {isExpanded ? (
                          <FormattedProvisionText
                            text={stripSectionHeader(
                              provision.provision_text,
                              provision.toc_section_title || group.tocSectionTitle
                            )}
                            compact
                            stripMarker={showMarkers && provision.v2_marker ? provision.v2_marker : undefined}
                            highlightQuery={highlightQuery}
                            theme={provisionTheme}
                            councilKey={councilKey}
                          />
                        ) : (
                          <p className={theme.textClampLines === 2 ? 'line-clamp-2' : 'line-clamp-3'}>
                            {/* Strip marker from display if shown as badge */}
                            {showMarkers && provision.v2_marker
                              ? stripSectionHeader(
                                  provision.provision_text,
                                  provision.toc_section_title || group.tocSectionTitle
                                ).replace(new RegExp(`^\\s*${provision.v2_marker}\\s+`, 'i'), '')
                              : stripSectionHeader(
                                  provision.provision_text,
                                  provision.toc_section_title || group.tocSectionTitle
                                )}
                          </p>
                        )}
                      </div>

                      {/* Expand/Collapse Button - always show for long text */}
                      {provision.provision_text.length > theme.expandThreshold && (
                        <button
                          className="text-xs text-blue-600 hover:text-blue-800 mt-1 font-medium"
                          onClick={(e) => {
                            e.stopPropagation();
                            onToggleProvision(provision.id);
                          }}
                        >
                          {isExpanded ? '↑ Show less' : '+ Show more'}
                        </button>
                      )}

                      {/* Cross-References - shown when enabled and available */}
                      {showCrossReferences && (crossReferencesMap?.[provision.id]?.length ?? 0) > 0 && (
                        <div className="mt-2 pt-2 border-t border-gray-100">
                          <CrossReferenceList
                            references={crossReferencesMap![provision.id]}
                            currentDocType="dcp"
                            currentProvisionId={provision.id}
                            onNavigate={onNavigateCrossRef}
                            onScrollTo={onScrollToCrossRef}
                            maxVisible={3}
                          />
                        </div>
                      )}

                      {/* DA Mode Response Capture */}
                      {isDaMode && (
                        <DAResponseCapture
                          provisionId={provision.id}
                          sessionToken={sessionToken ?? null}
                          existingResponse={daResponses?.get(provision.id) as any}
                          isLocked={excludableTopics ? excludableTopics.has(provision.v2_structural_category || '') : false}
                          onSaved={(response) => onResponseSaved?.(provision.id, response)}
                          provisionContext={{
                            category: provision.v2_structural_category,
                            topic: provision.v2_topic,
                            marker: provision.v2_marker,
                            sectionHeader: provision.section_header,
                          }}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}

      {/* Show more / hide button */}
      {!hideShowMoreButton && maxProvisions && provisions.length > maxProvisions && (
        showAll ? (
          <button
            onClick={() => setShowAll(false)}
            className="w-full py-2.5 text-sm text-gray-400 hover:text-gray-600 font-medium border-t border-gray-100 hover:bg-gray-50 transition-colors"
          >
            Hide {provisions.length - maxProvisions} provisions
          </button>
        ) : (
          <button
            onClick={() => setShowAll(true)}
            className="w-full py-2.5 text-sm text-teal-600 hover:text-teal-800 font-medium border-t border-gray-100 hover:bg-teal-50 transition-colors"
          >
            Show {provisions.length - maxProvisions} more provisions
          </button>
        )
      )}
    </div>
  );
}

// Theme presets for different paths
export const THEME_PRESETS = {
  teal: DEFAULT_THEME,
  amber: {
    zebraStripeBg: 'bg-amber-50/50',
    zebraStripeAltBg: 'bg-transparent',
    borderColorClass: 'border-amber-200',
    textClampLines: 2 as const,
    expandThreshold: 200,
  },
};
