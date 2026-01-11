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

import { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { FormattedProvisionText } from './FormattedProvisionText';
import { LayerBadges } from '@/lib/design-tokens';

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
 * Get the actual DCP page number for display, applying council-specific offsets.
 */
function getDcpPageNumber(pdfPage: number | null | undefined, dcpPart?: string): number | null {
  if (pdfPage == null) return null;

  // Apply Leichhardt offset if applicable
  if (dcpPart && LEICHHARDT_PAGE_OFFSETS[dcpPart] !== undefined) {
    return pdfPage + LEICHHARDT_PAGE_OFFSETS[dcpPart];
  }

  // Default: assume pdf_page is already the correct DCP page
  return pdfPage;
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

interface Provision {
  id: number;
  provision_text: string;
  v2_dcp_layer: string;
  v2_dcp_part?: string;
  v2_topic?: string;
  v2_provision_type?: string;
  v2_precinct_id?: string;
  v2_marker?: string;
  pdf_page?: number;
  pdf_page_image_url?: string;
  layer?: string;
  v2_heritage_type?: 'control' | 'guidance' | 'character' | 'descriptive';
  v2_heritage_element?: string[];
  v2_heritage_hca?: string;
  v2_heritage_subcategory?: string;
  // TOC section info (from dcp_table_of_contents)
  toc_section_number?: string | null;
  toc_section_title?: string | null;
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
  showMarkers?: boolean;
  showDcpPart?: boolean;
  showLayerBadges?: boolean;    // Show layer badges (default: true)
  showLegend?: boolean;         // Show layer legend above results (default: false)
  maxProvisions?: number;       // Limit display count (e.g., 20)
  formerCouncil?: string;       // For council-specific layer labels
}

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
};

/**
 * Group provisions by PDF page and calculate display page numbers with offsets
 */
function groupProvisionsByPage(provisions: Provision[]): PageGroup[] {
  const pageMap = new Map<string, PageGroup>();
  const ungrouped: Provision[] = [];

  for (const prov of provisions) {
    if (prov.pdf_page_image_url) {
      const key = prov.pdf_page_image_url;
      if (!pageMap.has(key)) {
        const dcpPart = prov.v2_dcp_part || null;
        const rawPage = prov.pdf_page || null;
        pageMap.set(key, {
          pageNumber: rawPage,
          displayPageNumber: getDcpPageNumber(rawPage, dcpPart || undefined),
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
    } else {
      ungrouped.push(prov);
    }
  }

  // Sort by display page number
  const groups = Array.from(pageMap.values())
    .sort((a, b) => (a.displayPageNumber || 999) - (b.displayPageNumber || 999));

  // Add ungrouped at end
  if (ungrouped.length > 0) {
    groups.push({ pageNumber: null, displayPageNumber: null, pageUrl: null, provisions: ungrouped, dcpPart: null, tocSectionNumber: null, tocSectionTitle: null });
  }

  return groups;
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
    { key: 'generic', color: '#14b8a6' },    // teal
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
  showMarkers = true,
  showDcpPart = false,
  showLayerBadges = true,
  showLegend = false,
  maxProvisions,
  formerCouncil,
}: PageGroupedProvisionsProps) {
  const theme = { ...DEFAULT_THEME, ...themeOverrides };

  // Group provisions by page
  const pageGroups = useMemo(() => groupProvisionsByPage(provisions), [provisions]);

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

  // Apply max provisions limit if specified
  // useMemo to ensure stable reference when limit changes
  const { displayProvisions, limitedCount } = useMemo(() => {
    if (maxProvisions && provisions.length > maxProvisions) {
      return {
        displayProvisions: provisions.slice(0, maxProvisions),
        limitedCount: provisions.length
      };
    }
    return {
      displayProvisions: provisions,
      limitedCount: 0
    };
  }, [provisions, maxProvisions]);

  // Re-group after limiting
  const displayGroups = useMemo(
    () => groupProvisionsByPage(displayProvisions),
    [displayProvisions]
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

  // Format topic for display (snake_case → Title Case)
  const formatTopic = (topic: string | null | undefined): string => {
    if (!topic) return 'General';
    return topic
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  let globalIndex = 0;

  return (
    <div className="space-y-3">
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
                  {/* DCP Part (if no TOC info) */}
                  {!group.tocSectionNumber && group.dcpPart && (
                    <span className="font-medium text-gray-700">{group.dcpPart} · </span>
                  )}
                  {/* Page number */}
                  {group.displayPageNumber ? (
                    <span className="text-gray-500">Page {group.displayPageNumber}</span>
                  ) : (
                    <span className="text-gray-400">No page reference</span>
                  )}
                  <span className="text-gray-400 ml-1">
                    · {group.provisions.length} provision{group.provisions.length !== 1 ? 's' : ''}
                  </span>
                </span>
              </div>

              {/* PDF Button in header */}
              {group.pageUrl && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewPdf(group.pageUrl!, group.displayPageNumber || 0);
                  }}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-teal-600 text-white hover:bg-teal-700 rounded transition-colors"
                >
                  <FileText className="h-3 w-3" />
                  View {group.dcpPart ? `${group.dcpPart} ` : 'DCP '}Page{group.displayPageNumber ? ` ${group.displayPageNumber}` : ''}
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

                  return (
                    <div
                      key={provision.id}
                      className={`px-4 py-3 ${bgClass} border-l-4`}
                      style={{ borderLeftColor: layer === 'precinct' ? '#8b5cf6' : layer === 'condition' ? '#f59e0b' : layer === 'use_specific' ? '#3b82f6' : '#14b8a6' }}
                    >
                      {/* Provision Header Row */}
                      <div className="flex items-start gap-2 mb-1">
                        {/* Marker Badge */}
                        {showMarkers && provision.v2_marker && (
                          <Badge variant="outline" className="text-sm font-mono bg-white shrink-0">
                            {provision.v2_marker}
                          </Badge>
                        )}

                        {/* Layer Badge - council-specific label with larger font */}
                        <Badge className={`text-sm font-medium shrink-0 ${getLayerColor(layer)}`}>
                          {getLayerLabel(layer)}
                        </Badge>

                        {/* Topic Badge - separate pill */}
                        {provision.v2_topic && (
                          <Badge variant="outline" className="text-sm shrink-0 bg-white border-gray-300 text-gray-700">
                            {formatTopic(provision.v2_topic)}
                          </Badge>
                        )}

                        {/* DCP Part (optional) */}
                        {showDcpPart && provision.v2_dcp_part && (
                          <span className="text-xs text-gray-400 shrink-0">
                            {provision.v2_dcp_part}
                          </span>
                        )}
                      </div>

                      {/* Provision Text */}
                      <div
                        className={`text-sm text-gray-700 cursor-pointer ${
                          !isExpanded ? (theme.textClampLines === 2 ? 'line-clamp-2' : 'line-clamp-3') : ''
                        }`}
                        onClick={() => onToggleProvision(provision.id)}
                      >
                        <FormattedProvisionText text={provision.provision_text} compact />
                      </div>

                      {/* Expand/Collapse Button */}
                      {provision.provision_text.length > theme.expandThreshold && (
                        <button
                          className="text-xs text-slate-500 hover:text-slate-700 mt-1 font-medium"
                          onClick={() => onToggleProvision(provision.id)}
                        >
                          {isExpanded ? '↑ Show less' : '↓ Show more'}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}

      {/* Limited count message */}
      {limitedCount > 0 && (
        <p className="text-xs text-gray-500 text-center py-2">
          Showing {maxProvisions} of {limitedCount} provisions
        </p>
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
