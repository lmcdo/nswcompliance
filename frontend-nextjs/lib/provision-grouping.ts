// Pure helper functions and constants for DCP provision grouping/filtering.
// No React, no state, no side effects — safe to unit-test directly.

import { LayerBadges } from '@/lib/design-tokens';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Provision {
  id: number;
  provision_text: string;
  v2_dcp_layer: string;
  v2_dcp_part: string;
  v2_topic: string;
  v2_provision_type: string;
  v2_precinct_id: string;
  v2_marker: string;
  pdf_page: number;
  pdf_printed_page?: number;
  pdf_page_image_url?: string;
  layer?: string;
  v2_heritage_type?: 'control' | 'guidance' | 'character' | 'descriptive';
  v2_heritage_element?: string[];
  v2_heritage_hca?: string;
  v2_heritage_subcategory?: string;
  toc_section_number?: string | null;
  toc_section_title?: string | null;
}

export interface LayerResult {
  layer: string;
  layer_name: string;
  provisions: Provision[];
  count: number;
}

export interface PageGroup {
  pageNumber: number | null;
  pageUrl: string | null;
  provisions: Provision[];
}

// ---------------------------------------------------------------------------
// Display constants
// ---------------------------------------------------------------------------

export const LAYER_COLORS: Record<string, string> = {
  generic: `${LayerBadges.generic.bg} ${LayerBadges.generic.text}`,
  use_specific: `${LayerBadges.use_specific.bg} ${LayerBadges.use_specific.text}`,
  condition: `${LayerBadges.condition.bg} ${LayerBadges.condition.text}`,
  precinct: `${LayerBadges.precinct.bg} ${LayerBadges.precinct.text}`,
};

export const LAYER_LABELS: Record<string, string> = {
  generic: 'General',
  use_specific: 'Zone-Specific',
  condition: 'Condition',
  precinct: 'Precinct',
};

export const DCP_PART_LABELS: Record<string, Record<string, string>> = {
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

export const HERITAGE_TYPE_CONFIG: Record<string, { label: string; bg: string; border: string; accent: string }> = {
  control:     { label: 'Controls',           bg: 'bg-teal-50',  border: 'border-teal-200',  accent: 'text-teal-700' },
  guidance:    { label: 'Guidance',           bg: 'bg-blue-50',  border: 'border-blue-200',  accent: 'text-blue-700' },
  character:   { label: 'Character Statements', bg: 'bg-blue-50', border: 'border-blue-200', accent: 'text-blue-700' },
  descriptive: { label: 'Background Info',    bg: 'bg-gray-50',  border: 'border-gray-200',  accent: 'text-gray-600' },
};

export const ELEMENT_LABELS: Record<string, string> = {
  // Heritage elements
  roof: 'Roof', fence: 'Fencing', materials: 'Materials', verandah: 'Verandah',
  window: 'Windows', facade: 'Facade', chimney: 'Chimney', door: 'Doors',
  car_parking: 'Parking', scale: 'Scale', infill: 'Infill', demolition: 'Demolition',
  setback: 'Setbacks', garden: 'Garden', interior: 'Interior',
  // Building Form - building types
  secondary_dwelling: 'Secondary Dwelling', multi_dwelling: 'Multi Dwelling',
  residential_flat: 'Residential Flat', boarding_house: 'Boarding House',
  child_care: 'Child Care', neighbourhood_shop: 'Neighbourhood Shop',
  mixed_use: 'Mixed Use', commercial: 'Commercial', industrial: 'Industrial',
  all_residential: 'All Residential', all_development: 'All Development',
};

// ---------------------------------------------------------------------------
// Slug helpers
// ---------------------------------------------------------------------------

export function hcaNameToSlug(hcaName: string): string {
  if (!hcaName) return '';
  if (/^hca_\d+$/i.test(hcaName)) return hcaName.toLowerCase();
  const hcaMatch = hcaName.match(/^hca\s*(\d+)$/i);
  if (hcaMatch) return `hca_${hcaMatch[1]}`;
  const cMatch = hcaName.match(/^c(\d+)$/i);
  if (cMatch) return `hca_${cMatch[1]}`;
  let slug = hcaName
    .replace(/heritage conservation area/gi, '')
    .replace(/conservation area/gi, '')
    .replace(/heritage area/gi, '')
    .replace(/central|north|south|east|west/gi, '')
    .trim();
  slug = slug.toLowerCase().replace(/\s+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
  return slug;
}

export function heritageItemNumberToSlug(itemNumber: string): string {
  if (!itemNumber) return '';
  if (/^hca_\d+$/i.test(itemNumber)) return itemNumber.toLowerCase();
  const hcaMatch = itemNumber.match(/hca\s*(\d+)/i);
  if (hcaMatch) return `hca_${hcaMatch[1]}`;
  const cMatch = itemNumber.match(/^c(\d+)$/i);
  if (cMatch) return `hca_${cMatch[1]}`;
  const numMatch = itemNumber.match(/^(\d+)$/);
  if (numMatch) return `hca_${numMatch[1]}`;
  return '';
}

// ---------------------------------------------------------------------------
// PDF button helpers
// ---------------------------------------------------------------------------

export function groupProvisionsByPage(provisions: Provision[]): PageGroup[] {
  const pageMap = new Map<string, { pageNumber: number | null; pageUrl: string | null; provisions: Provision[] }>();
  const ungrouped: Provision[] = [];

  for (const prov of provisions) {
    if (prov.pdf_page_image_url) {
      const key = prov.pdf_page_image_url;
      if (!pageMap.has(key)) {
        pageMap.set(key, { pageNumber: prov.pdf_page || null, pageUrl: prov.pdf_page_image_url, provisions: [] });
      }
      pageMap.get(key)!.provisions.push(prov);
    } else {
      ungrouped.push(prov);
    }
  }

  const groups = Array.from(pageMap.values()).sort((a, b) => (a.pageNumber || 999) - (b.pageNumber || 999));
  if (ungrouped.length > 0) groups.push({ pageNumber: null, pageUrl: null, provisions: ungrouped });
  return groups;
}

export function getProvisionsWithPdfButton(provisions: Provision[]): Set<number> {
  const result = new Set<number>();
  for (const prov of provisions) {
    if (prov.pdf_page_image_url) result.add(prov.id);
  }
  return result;
}

export function getPageGroupInfo(provisions: Provision[]): Map<number, { isFirst: boolean; isLast: boolean; pageUrl: string }> {
  const result = new Map<number, { isFirst: boolean; isLast: boolean; pageUrl: string }>();
  const pageGroups = new Map<string, number[]>();

  for (const prov of provisions) {
    if (prov.pdf_page_image_url) {
      if (!pageGroups.has(prov.pdf_page_image_url)) pageGroups.set(prov.pdf_page_image_url, []);
      pageGroups.get(prov.pdf_page_image_url)!.push(prov.id);
    }
  }

  for (const [pageUrl, ids] of pageGroups.entries()) {
    if (ids.length > 1) {
      ids.forEach((id, idx) => {
        result.set(id, { isFirst: idx === 0, isLast: idx === ids.length - 1, pageUrl });
      });
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Grouping functions
// ---------------------------------------------------------------------------

export function groupByDcpPart(provisions: Provision[], topicName?: string): Map<string, Provision[]> {
  const grouped = new Map<string, Provision[]>();
  const topicLower = topicName?.toLowerCase().replace(/_/g, ' ') || '';

  provisions.forEach(p => {
    let part = p.v2_dcp_part;
    const partLower = (typeof part === 'string') ? part.toLowerCase() : '';

    if (part === null || part === undefined || part === '') {
      part = 'General Controls';
    } else if (typeof part !== 'string') {
      part = 'General Controls';
    } else if (/^\d+$/.test(part)) {
      part = 'General Controls';
    } else if (partLower === 'unknown' || partLower === 'other' || partLower === 'general controls') {
      part = 'General Controls';
    } else if (topicLower && partLower === topicLower) {
      part = 'General Controls';
    }

    if (!grouped.has(part)) grouped.set(part, []);
    grouped.get(part)!.push(p);
  });

  return new Map([...grouped.entries()].sort((a, b) => b[1].length - a[1].length));
}

export function groupByHca(provisions: Provision[], propertyHcaSlug: string): Map<string, Provision[]> {
  const grouped = new Map<string, Provision[]>();
  provisions.forEach(p => {
    const hca = p.v2_heritage_hca || 'General Heritage Controls';
    if (!grouped.has(hca)) grouped.set(hca, []);
    grouped.get(hca)!.push(p);
  });

  return new Map([...grouped.entries()].sort((a, b) => {
    if (propertyHcaSlug && a[0] === propertyHcaSlug) return -1;
    if (propertyHcaSlug && b[0] === propertyHcaSlug) return 1;
    if (a[0] === 'General Heritage Controls') return -1;
    if (b[0] === 'General Heritage Controls') return 1;
    return b[1].length - a[1].length;
  }));
}

export function groupByHeritageSubcategory(provisions: Provision[]): Map<string, Provision[]> {
  const grouped = new Map<string, Provision[]>();
  provisions.forEach(p => {
    const subcat = p.v2_heritage_subcategory || 'Heritage';
    if (!grouped.has(subcat)) grouped.set(subcat, []);
    grouped.get(subcat)!.push(p);
  });
  return new Map([...grouped.entries()].sort((a, b) => {
    if (a[0] === 'Heritage') return -1;
    if (b[0] === 'Heritage') return 1;
    return b[1].length - a[1].length;
  }));
}

export function groupByHeritageType(provisions: Provision[]): Map<string, Provision[]> {
  const grouped = new Map<string, Provision[]>();
  grouped.set('control', []);
  grouped.set('guidance', []);
  grouped.set('character', []);
  grouped.set('descriptive', []);

  provisions.forEach(p => {
    const type = p.v2_heritage_type || 'descriptive';
    if (!grouped.has(type)) grouped.set(type, []);
    grouped.get(type)!.push(p);
  });

  for (const [type, provs] of grouped.entries()) {
    if (provs.length === 0) grouped.delete(type);
  }
  return grouped;
}

// ---------------------------------------------------------------------------
// Element filter helpers
// ---------------------------------------------------------------------------

export function getElementCounts(provisions: Provision[]): Map<string, number> {
  const counts = new Map<string, number>();
  provisions.forEach(p => {
    if (p.v2_heritage_element) {
      p.v2_heritage_element.forEach(elem => counts.set(elem, (counts.get(elem) || 0) + 1));
    }
  });
  return new Map([...counts.entries()].sort((a, b) => b[1] - a[1]));
}

export function getElementTotals(provisions: Provision[]): { totals: Map<string, number>; generalCount: number } {
  const totals = new Map<string, number>();
  let generalCount = 0;

  provisions.forEach(p => {
    if (!p.v2_heritage_element || p.v2_heritage_element.length === 0) {
      generalCount++;
    } else {
      p.v2_heritage_element.forEach(elem => totals.set(elem, (totals.get(elem) || 0) + 1));
    }
  });

  return { totals: new Map([...totals.entries()].sort((a, b) => b[1] - a[1])), generalCount };
}

export function splitByExclusivity(provisions: Provision[], element: string): { onlyThis: Provision[]; plusOthers: Provision[] } {
  const onlyThis: Provision[] = [];
  const plusOthers: Provision[] = [];
  provisions.forEach(p => {
    if (p.v2_heritage_element && p.v2_heritage_element.includes(element)) {
      if (p.v2_heritage_element.length === 1) onlyThis.push(p);
      else plusOthers.push(p);
    }
  });
  return { onlyThis, plusOthers };
}

export function filterByElement(provisions: Provision[], element: string | undefined): Provision[] {
  if (!element) return provisions;
  if (element === '_general') return provisions.filter(p => !p.v2_heritage_element || p.v2_heritage_element.length === 0);
  return provisions.filter(p => p.v2_heritage_element && p.v2_heritage_element.includes(element));
}

// ---------------------------------------------------------------------------
// Sort + display helpers
// ---------------------------------------------------------------------------

export function sortTopicsByPriority(topics: string[], priorityOrder: string[]): string[] {
  return [...topics].sort((a, b) => {
    const aIndex = priorityOrder.indexOf(a);
    const bIndex = priorityOrder.indexOf(b);
    if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
    if (aIndex !== -1) return -1;
    if (bIndex !== -1) return 1;
    return a.localeCompare(b);
  });
}

export function getLayerLabel(layer: string | null | undefined): string {
  if (!layer || layer === 'unknown' || layer === 'null') return 'General';
  return LAYER_LABELS[layer] || layer;
}

export function getLayerColor(layer: string | null | undefined): string {
  if (!layer || layer === 'unknown' || layer === 'null') return LAYER_COLORS.generic;
  return LAYER_COLORS[layer] || 'bg-gray-100';
}

export function formatHcaName(hca: string): string {
  if (hca === 'General Heritage Controls') return hca;
  return hca.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') + ' HCA';
}

export function formatDcpPart(part: string, council?: string): string {
  if (!part || part === 'Other') return 'General Controls';
  if (council && DCP_PART_LABELS[council]?.[part]) return DCP_PART_LABELS[council][part];
  return part;
}
