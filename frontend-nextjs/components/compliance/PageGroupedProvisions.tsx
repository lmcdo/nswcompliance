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
import type { DaResponse } from '@/hooks/useDASession';
import type { NumericCheckValues } from './NumericChecker';

// ─── Numeric Compliance Check Utilities ──────────────────────────────────────

/**
 * Extract the first numeric value (with unit) from provision text.
 * Returns { value, isMin, isMax } or null.
 */
function extractNumericLimit(text: string): { value: number; isMin: boolean; isMax: boolean } | null {
  // Find all numeric values with context — look for a value adjacent to a direction keyword
  // Pattern: "maximum X m" or "must not exceed X m" or "minimum X m" etc.
  const maxPattern = /(?:maximum|must not exceed|not exceed|no more than)\s+(\d+(?:\.\d+)?)\s*(?:m²|m2|m|%|metres?)/gi;
  const minPattern = /(?:minimum|not less than|at least)\s+(\d+(?:\.\d+)?)\s*(?:m²|m2|m|%|metres?)/gi;

  const maxMatch = maxPattern.exec(text);
  const minMatch = minPattern.exec(text);

  if (maxMatch) return { value: parseFloat(maxMatch[1]), isMin: false, isMax: true };
  if (minMatch) return { value: parseFloat(minMatch[1]), isMin: true, isMax: false };

  // Fallback: bare number with unit near direction word anywhere in text
  const isMin = /\bminimum\b|\bnot less than\b|\bat least\b/i.test(text);
  const isMax = /\bmaximum\b|\bnot exceed\b|\bmust not exceed\b|\bno more than\b/i.test(text);
  if (!isMin && !isMax) return null;

  const match = text.match(/\b(\d+(?:\.\d+)?)\s*(?:m²|m2|m|%|metres?)\b/i);
  if (!match) return null;

  return { value: parseFloat(match[1]), isMin, isMax };
}

type NumericComplianceResult = 'complies' | 'borderline' | 'fails' | null;

/**
 * Compare a user's proposed value against a provision's numeric limit.
 */
function checkNumericCompliance(
  provisionText: string,
  v2Topic: string | undefined,
  v2Marker: string | undefined,
  checkValues: NumericCheckValues
): { result: NumericComplianceResult; chip: string } | null {
  const topic = (v2Topic || '').toLowerCase();
  const marker = (v2Marker || '').toLowerCase();

  // Route metric to the right input field
  let userValueStr = '';
  if (topic.includes('height') || marker === 'height') {
    userValueStr = checkValues.height;
  } else if (topic.includes('built_form') || topic.includes('floor_space') || topic.includes('fsr')) {
    userValueStr = checkValues.gfa;
  } else if (topic.includes('site_coverage') || topic.includes('coverage')) {
    userValueStr = checkValues.siteCoverage;
  } else if (topic.includes('parking') || marker === 'parking') {
    userValueStr = checkValues.carSpaces;
  } else {
    return null; // No matching metric
  }

  if (!userValueStr) return null;
  const userValue = parseFloat(userValueStr);
  if (isNaN(userValue)) return null;

  const limit = extractNumericLimit(provisionText);
  if (!limit) return null;

  const { value: limitValue, isMin, isMax } = limit;
  const BORDERLINE_THRESHOLD = 0.1; // 10% within limit

  let result: NumericComplianceResult = null;
  let chip = '';

  if (isMax) {
    if (userValue <= limitValue) {
      const ratio = userValue / limitValue;
      result = ratio >= (1 - BORDERLINE_THRESHOLD) ? 'borderline' : 'complies';
      chip = result === 'complies' ? `✓ ${userValue} ≤ ${limitValue} max` : `~ ${userValue} ≈ ${limitValue} max`;
    } else {
      result = 'fails';
      chip = `✗ ${userValue} > ${limitValue} max`;
    }
  } else if (isMin) {
    if (userValue >= limitValue) {
      const ratio = limitValue / userValue;
      result = ratio >= (1 - BORDERLINE_THRESHOLD) ? 'borderline' : 'complies';
      chip = result === 'complies' ? `✓ ${userValue} ≥ ${limitValue} min` : `~ ${userValue} ≈ ${limitValue} min`;
    } else {
      result = 'fails';
      chip = `✗ ${userValue} < ${limitValue} min`;
    }
  } else {
    return null; // No direction detected
  }

  return { result, chip };
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
  v2_display_priority?: 'critical' | 'important' | 'guideline' | 'contextual';
  // Dev type relevance scoring
  relevance_level?: 'primary' | 'general' | 'secondary';
  relevance_reason?: string;
  v2_applicable_dev_types?: string[];
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
  councilPdfUrl?: string;       // R2 public PDF URL for councils without per-page screenshots
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
  /** Normalized v2_topic values that were auto-excluded by structured intake */
  excludableTopics?: Set<string>;
  onResponseSaved?: (provisionId: number, response: DaResponse) => void;
  // Numeric compliance check
  numericCheckValues?: NumericCheckValues;
}

// Compliance status badge config for DA mode header — keyed on DaResponse['compliance_status']
// Using Exclude<..., null> so TypeScript enforces exhaustiveness if the union grows.
const DA_STATUS_BADGE: Record<Exclude<DaResponse['compliance_status'], null>, { label: string; cls: string }> = {
  complies:       { label: 'Complies', cls: 'bg-green-100 text-green-700 border-green-200' },
  varies:         { label: 'Varies',   cls: 'bg-amber-100 text-amber-700 border-amber-200' },
  not_applicable: { label: 'N/A',      cls: 'bg-gray-100  text-gray-500  border-gray-200'  },
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
function groupProvisionsByPage(provisions: Provision[], councilPdfUrl?: string): PageGroup[] {
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
    } else if (councilPdfUrl && prov.pdf_page) {
      // No page image but we have a direct PDF URL — group by raw pdf_page
      const key = `direct-${prov.pdf_page}`;
      if (!pageMap.has(key)) {
        pageMap.set(key, {
          pageNumber: prov.pdf_page,
          displayPageNumber: null,  // Direct-PDF: no reliable printed page number, omit label
          pageUrl: `${councilPdfUrl}#page=${prov.pdf_page}`,
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
  councilPdfUrl: councilPdfUrlProp,
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
  excludableTopics,
  onResponseSaved,
  numericCheckValues,
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
  const councilPdfUrl = councilPdfUrlProp || undefined;
  const pageGroups = useMemo(() => groupProvisionsByPage(provisions, councilPdfUrl), [provisions, councilPdfUrl]);

  // Track expanded page groups
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

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
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
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
    () => groupProvisionsByPage(displayProvisions, councilPdfUrl),
    [displayProvisions, councilPdfUrl]
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
                    <span className="text-gray-500"> · Page {group.displayPageNumber}</span>
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
                  title={`${group.dcpPart && group.dcpPart !== 'unknown' ? group.dcpPart + ' - ' : ''}Page ${group.displayPageNumber || 1}`}
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
                  // Grey out provisions whose topic is excluded by SEPP/LEP/intake data.
                  // In DA mode this never triggers — excluded provisions are split out upstream.
                  const isExcludedByTriage = !isDaMode && !!excludableTopics?.has(
                    (provision.v2_topic || '').toLowerCase().replace(/ /g, '_')
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

                        {/* Topic Badge - separate pill (skip if duplicates layer label) */}
                        {provision.v2_topic && getLayerLabel(layer).toLowerCase() !== provision.v2_topic.toLowerCase() && (
                          <Badge variant="outline" className="text-sm shrink-0 bg-white border-gray-300 text-gray-700">
                            {formatTopic(provision.v2_topic)}
                          </Badge>
                        )}

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
                          const status = daResponses?.get(provision.id)?.compliance_status;
                          if (!status) return null;
                          const badge = DA_STATUS_BADGE[status];
                          return (
                            <span className={`text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0 ${badge.cls}`}>
                              {badge.label}
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

                      {/* Numeric Compliance Check Chip */}
                      {numericCheckValues && provision.v2_has_numeric_value && (() => {
                        const check = checkNumericCompliance(
                          provision.provision_text,
                          provision.v2_topic,
                          provision.v2_marker,
                          numericCheckValues
                        );
                        if (!check) return null;
                        const chipStyle = check.result === 'complies'
                          ? 'bg-green-100 text-green-800 border-green-300'
                          : check.result === 'borderline'
                          ? 'bg-amber-100 text-amber-800 border-amber-300'
                          : 'bg-red-100 text-red-800 border-red-300';
                        return (
                          <div className={`inline-flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded border mb-1 ${chipStyle}`}>
                            <Ruler className="w-3 h-3" />
                            {check.chip}
                          </div>
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
                      {showCrossReferences && crossReferencesMap?.[provision.id]?.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-gray-100">
                          <CrossReferenceList
                            references={crossReferencesMap[provision.id]}
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
                          isLocked={excludableTopics ? excludableTopics.has((provision.v2_topic || '').toLowerCase().replace(/ /g, '_')) : false}
                          onSaved={(response) => onResponseSaved?.(provision.id, response)}
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

      {/* Show more button */}
      {limitedCount > 0 && (
        <button
          onClick={() => setShowAll(true)}
          className="w-full py-2.5 text-sm text-teal-600 hover:text-teal-800 font-medium border-t border-gray-100 hover:bg-teal-50 transition-colors"
        >
          Show {limitedCount - (maxProvisions ?? 0)} more provisions
        </button>
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
