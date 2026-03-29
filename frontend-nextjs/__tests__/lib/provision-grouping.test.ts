import {
  hcaNameToSlug,
  heritageItemNumberToSlug,
  groupByDcpPart,
  groupByHca,
  groupByHeritageType,
  groupByHeritageSubcategory,
  groupProvisionsByPage,
  getProvisionsWithPdfButton,
  getElementTotals,
  splitByExclusivity,
  filterByElement,
  sortTopicsByPriority,
  formatHcaName,
  formatDcpPart,
  getLayerLabel,
} from '@/lib/provision-grouping';
import type { Provision } from '@/lib/provision-grouping';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeProvision(overrides: Partial<Provision> & { id: number }): Provision {
  return {
    provision_text: 'Sample text',
    v2_dcp_layer: 'generic',
    v2_dcp_part: 'Part 4',
    v2_topic: 'setbacks',
    v2_provision_type: 'control',
    v2_precinct_id: '',
    v2_marker: '',
    pdf_page: 1,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// hcaNameToSlug
// ---------------------------------------------------------------------------

describe('hcaNameToSlug', () => {
  test('empty string returns empty', () => expect(hcaNameToSlug('')).toBe(''));

  test('already in hca_N format — passthrough lowercase', () => {
    expect(hcaNameToSlug('hca_26')).toBe('hca_26');
    expect(hcaNameToSlug('HCA_26')).toBe('hca_26');
  });

  test('"HCA 26" format', () => expect(hcaNameToSlug('HCA 26')).toBe('hca_26'));
  test('"HCA26" no space', () => expect(hcaNameToSlug('HCA26')).toBe('hca_26'));

  test('"C26" shorthand', () => expect(hcaNameToSlug('C26')).toBe('hca_26'));

  test('full name strips suffixes and converts to slug', () => {
    expect(hcaNameToSlug('Summer Hill Heritage Conservation Area')).toBe('summer_hill');
    expect(hcaNameToSlug('Ashfield Heights Heritage Conservation Area')).toBe('ashfield_heights');
    expect(hcaNameToSlug('Queen Street Conservation Area')).toBe('queen_street');
  });

  test('directional words stripped from slug', () => {
    // "Summer Hill Central Heritage Conservation Area" → "summer_hill"
    const result = hcaNameToSlug('Summer Hill Central Heritage Conservation Area');
    expect(result).toBe('summer_hill');
  });
});

// ---------------------------------------------------------------------------
// heritageItemNumberToSlug
// ---------------------------------------------------------------------------

describe('heritageItemNumberToSlug', () => {
  test('empty string returns empty', () => expect(heritageItemNumberToSlug('')).toBe(''));

  test('already hca_N passthrough', () => expect(heritageItemNumberToSlug('hca_26')).toBe('hca_26'));

  test('"HCA 26"', () => expect(heritageItemNumberToSlug('HCA 26')).toBe('hca_26'));
  test('"HCA26"', () => expect(heritageItemNumberToSlug('HCA26')).toBe('hca_26'));

  test('"C26"', () => expect(heritageItemNumberToSlug('C26')).toBe('hca_26'));

  test('bare number "26"', () => expect(heritageItemNumberToSlug('26')).toBe('hca_26'));

  test('unrecognised format returns empty', () => {
    expect(heritageItemNumberToSlug('I262')).toBe('');
    expect(heritageItemNumberToSlug('random')).toBe('');
  });
});

// ---------------------------------------------------------------------------
// groupByDcpPart
// ---------------------------------------------------------------------------

describe('groupByDcpPart', () => {
  test('null/empty part falls back to General Controls', () => {
    const provisions = [
      makeProvision({ id: 1, v2_dcp_part: '' }),
      makeProvision({ id: 2, v2_dcp_part: null as any }),
    ];
    const groups = groupByDcpPart(provisions);
    expect(groups.has('General Controls')).toBe(true);
    expect(groups.get('General Controls')!.length).toBe(2);
  });

  test('purely numeric part falls back to General Controls', () => {
    const provisions = [makeProvision({ id: 1, v2_dcp_part: '4' })];
    const groups = groupByDcpPart(provisions);
    expect(groups.has('General Controls')).toBe(true);
  });

  test('"unknown" and "other" merge into General Controls', () => {
    const provisions = [
      makeProvision({ id: 1, v2_dcp_part: 'unknown' }),
      makeProvision({ id: 2, v2_dcp_part: 'Other' }),
    ];
    const groups = groupByDcpPart(provisions);
    expect(groups.get('General Controls')!.length).toBe(2);
  });

  test('part name matching topic name collapses to General Controls', () => {
    // heritage provisions under "Heritage" DCP part — redundant label, should collapse
    const provisions = [makeProvision({ id: 1, v2_dcp_part: 'Heritage', v2_topic: 'heritage' })];
    const groups = groupByDcpPart(provisions, 'heritage');
    expect(groups.has('General Controls')).toBe(true);
    expect(groups.has('Heritage')).toBe(false);
  });

  test('valid distinct parts are preserved', () => {
    const provisions = [
      makeProvision({ id: 1, v2_dcp_part: 'Part 4.1' }),
      makeProvision({ id: 2, v2_dcp_part: 'Part 4.1' }),
      makeProvision({ id: 3, v2_dcp_part: 'Part 8' }),
    ];
    const groups = groupByDcpPart(provisions);
    expect(groups.get('Part 4.1')!.length).toBe(2);
    expect(groups.get('Part 8')!.length).toBe(1);
  });

  test('sorted by count descending', () => {
    const provisions = [
      makeProvision({ id: 1, v2_dcp_part: 'Part A' }),
      makeProvision({ id: 2, v2_dcp_part: 'Part B' }),
      makeProvision({ id: 3, v2_dcp_part: 'Part B' }),
      makeProvision({ id: 4, v2_dcp_part: 'Part B' }),
    ];
    const keys = Array.from(groupByDcpPart(provisions).keys());
    expect(keys[0]).toBe('Part B');
    expect(keys[1]).toBe('Part A');
  });
});

// ---------------------------------------------------------------------------
// groupByHca
// ---------------------------------------------------------------------------

describe('groupByHca', () => {
  test('provisions without v2_heritage_hca go to General Heritage Controls', () => {
    const provisions = [makeProvision({ id: 1 })];
    const groups = groupByHca(provisions, '');
    expect(groups.has('General Heritage Controls')).toBe(true);
  });

  test("property's HCA sorted first", () => {
    const provisions = [
      makeProvision({ id: 1, v2_heritage_hca: 'General Heritage Controls' }),
      makeProvision({ id: 2, v2_heritage_hca: 'summer_hill' }),
      makeProvision({ id: 3, v2_heritage_hca: 'ashfield_heights' }),
    ];
    const keys = Array.from(groupByHca(provisions, 'summer_hill').keys());
    expect(keys[0]).toBe('summer_hill');
  });

  test('General Heritage Controls sorted after property HCA but before others', () => {
    const provisions = [
      makeProvision({ id: 1, v2_heritage_hca: 'General Heritage Controls' }),
      makeProvision({ id: 2, v2_heritage_hca: 'ashfield_heights' }),
      makeProvision({ id: 3, v2_heritage_hca: 'summer_hill' }),
    ];
    const keys = Array.from(groupByHca(provisions, 'summer_hill').keys());
    expect(keys[0]).toBe('summer_hill');
    expect(keys[1]).toBe('General Heritage Controls');
    expect(keys[2]).toBe('ashfield_heights');
  });

  test('no property HCA — General Heritage Controls first', () => {
    const provisions = [
      makeProvision({ id: 1, v2_heritage_hca: 'ashfield_heights' }),
      makeProvision({ id: 2, v2_heritage_hca: 'General Heritage Controls' }),
    ];
    const keys = Array.from(groupByHca(provisions, '').keys());
    expect(keys[0]).toBe('General Heritage Controls');
  });
});

// ---------------------------------------------------------------------------
// groupByHeritageType
// ---------------------------------------------------------------------------

describe('groupByHeritageType', () => {
  test('control/guidance/character/descriptive buckets created in order', () => {
    const provisions = [
      makeProvision({ id: 1, v2_heritage_type: 'descriptive' }),
      makeProvision({ id: 2, v2_heritage_type: 'control' }),
      makeProvision({ id: 3, v2_heritage_type: 'guidance' }),
    ];
    const groups = groupByHeritageType(provisions);
    const keys = Array.from(groups.keys());
    // control always first (defined first in Map initialisation)
    expect(keys[0]).toBe('control');
    expect(keys[1]).toBe('guidance');
    expect(keys[2]).toBe('descriptive');
  });

  test('empty buckets removed', () => {
    const provisions = [makeProvision({ id: 1, v2_heritage_type: 'control' })];
    const groups = groupByHeritageType(provisions);
    expect(groups.has('guidance')).toBe(false);
    expect(groups.has('character')).toBe(false);
    expect(groups.has('descriptive')).toBe(false);
  });

  test('undefined heritage type falls back to descriptive', () => {
    const provisions = [makeProvision({ id: 1 })];
    const groups = groupByHeritageType(provisions);
    expect(groups.has('descriptive')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// groupByHeritageSubcategory
// ---------------------------------------------------------------------------

describe('groupByHeritageSubcategory', () => {
  test('"Heritage" subcategory sorted first', () => {
    const provisions = [
      makeProvision({ id: 1, v2_heritage_subcategory: 'fencing' }),
      makeProvision({ id: 2, v2_heritage_subcategory: 'Heritage' }),
    ];
    const keys = Array.from(groupByHeritageSubcategory(provisions).keys());
    expect(keys[0]).toBe('Heritage');
  });

  test('undefined subcategory defaults to Heritage', () => {
    const provisions = [makeProvision({ id: 1 })];
    const groups = groupByHeritageSubcategory(provisions);
    expect(groups.has('Heritage')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// groupProvisionsByPage
// ---------------------------------------------------------------------------

describe('groupProvisionsByPage', () => {
  test('provisions sharing a URL grouped together', () => {
    const provisions = [
      makeProvision({ id: 1, pdf_page: 5, pdf_page_image_url: 'http://r2/p5.jpg' }),
      makeProvision({ id: 2, pdf_page: 5, pdf_page_image_url: 'http://r2/p5.jpg' }),
      makeProvision({ id: 3, pdf_page: 6, pdf_page_image_url: 'http://r2/p6.jpg' }),
    ];
    const groups = groupProvisionsByPage(provisions);
    expect(groups.length).toBe(2);
    expect(groups[0].provisions.length).toBe(2);
    expect(groups[1].provisions.length).toBe(1);
  });

  test('provisions without URL collected in trailing ungrouped bucket', () => {
    const provisions = [
      makeProvision({ id: 1, pdf_page_image_url: 'http://r2/p1.jpg' }),
      makeProvision({ id: 2 }), // no URL
    ];
    const groups = groupProvisionsByPage(provisions);
    // last group has null pageUrl
    const last = groups[groups.length - 1];
    expect(last.pageUrl).toBeNull();
    expect(last.provisions[0].id).toBe(2);
  });

  test('groups sorted by page number ascending', () => {
    const provisions = [
      makeProvision({ id: 1, pdf_page: 10, pdf_page_image_url: 'http://r2/p10.jpg' }),
      makeProvision({ id: 2, pdf_page: 3, pdf_page_image_url: 'http://r2/p3.jpg' }),
      makeProvision({ id: 3, pdf_page: 7, pdf_page_image_url: 'http://r2/p7.jpg' }),
    ];
    const groups = groupProvisionsByPage(provisions);
    expect(groups[0].pageNumber).toBe(3);
    expect(groups[1].pageNumber).toBe(7);
    expect(groups[2].pageNumber).toBe(10);
  });

  test('empty input returns empty array', () => {
    expect(groupProvisionsByPage([])).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// getProvisionsWithPdfButton
// ---------------------------------------------------------------------------

describe('getProvisionsWithPdfButton', () => {
  test('returns IDs of provisions that have a PDF URL', () => {
    const provisions = [
      makeProvision({ id: 1, pdf_page_image_url: 'http://r2/p1.jpg' }),
      makeProvision({ id: 2 }),
    ];
    const ids = getProvisionsWithPdfButton(provisions);
    expect(ids.has(1)).toBe(true);
    expect(ids.has(2)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// getElementTotals
// ---------------------------------------------------------------------------

describe('getElementTotals', () => {
  test('provisions with no element array counted as general', () => {
    const provisions = [
      makeProvision({ id: 1 }),
      makeProvision({ id: 2, v2_heritage_element: [] }),
    ];
    const { totals, generalCount } = getElementTotals(provisions);
    expect(generalCount).toBe(2);
    expect(totals.size).toBe(0);
  });

  test('element counts accumulated correctly', () => {
    const provisions = [
      makeProvision({ id: 1, v2_heritage_element: ['roof', 'fence'] }),
      makeProvision({ id: 2, v2_heritage_element: ['roof'] }),
    ];
    const { totals } = getElementTotals(provisions);
    expect(totals.get('roof')).toBe(2);
    expect(totals.get('fence')).toBe(1);
  });

  test('sorted by count descending', () => {
    const provisions = [
      makeProvision({ id: 1, v2_heritage_element: ['fence'] }),
      makeProvision({ id: 2, v2_heritage_element: ['roof', 'fence', 'window'] }),
      makeProvision({ id: 3, v2_heritage_element: ['fence'] }),
    ];
    const { totals } = getElementTotals(provisions);
    const keys = Array.from(totals.keys());
    expect(keys[0]).toBe('fence'); // count 3
    expect(keys[1]).toBe('roof');  // count 1 (tied with window, localeCompare determines order)
  });
});

// ---------------------------------------------------------------------------
// splitByExclusivity
// ---------------------------------------------------------------------------

describe('splitByExclusivity', () => {
  const provisions = [
    makeProvision({ id: 1, v2_heritage_element: ['roof'] }),           // only roof
    makeProvision({ id: 2, v2_heritage_element: ['roof', 'fence'] }), // roof + others
    makeProvision({ id: 3, v2_heritage_element: ['fence'] }),          // no roof
    makeProvision({ id: 4 }),                                          // no elements
  ];

  test('onlyThis contains provisions where roof is the sole element', () => {
    const { onlyThis } = splitByExclusivity(provisions, 'roof');
    expect(onlyThis.map(p => p.id)).toEqual([1]);
  });

  test('plusOthers contains provisions where roof is one of multiple elements', () => {
    const { plusOthers } = splitByExclusivity(provisions, 'roof');
    expect(plusOthers.map(p => p.id)).toEqual([2]);
  });

  test('provisions not containing the element excluded from both buckets', () => {
    const { onlyThis, plusOthers } = splitByExclusivity(provisions, 'roof');
    const allIds = [...onlyThis, ...plusOthers].map(p => p.id);
    expect(allIds).not.toContain(3);
    expect(allIds).not.toContain(4);
  });
});

// ---------------------------------------------------------------------------
// filterByElement
// ---------------------------------------------------------------------------

describe('filterByElement', () => {
  const provisions = [
    makeProvision({ id: 1, v2_heritage_element: ['roof'] }),
    makeProvision({ id: 2, v2_heritage_element: ['fence'] }),
    makeProvision({ id: 3 }), // no element (general)
  ];

  test('undefined element returns all provisions', () => {
    expect(filterByElement(provisions, undefined).length).toBe(3);
  });

  test('"_general" returns provisions with no element', () => {
    const result = filterByElement(provisions, '_general');
    expect(result.map(p => p.id)).toEqual([3]);
  });

  test('specific element filters correctly', () => {
    const result = filterByElement(provisions, 'roof');
    expect(result.map(p => p.id)).toEqual([1]);
  });
});

// ---------------------------------------------------------------------------
// sortTopicsByPriority
// ---------------------------------------------------------------------------

describe('sortTopicsByPriority', () => {
  test('topics in priority order sorted to front', () => {
    const topics = ['heritage', 'setbacks', 'parking'];
    const order = ['parking', 'setbacks'];
    const result = sortTopicsByPriority(topics, order);
    expect(result[0]).toBe('parking');
    expect(result[1]).toBe('setbacks');
  });

  test('topics not in priority list sorted alphabetically after priority topics', () => {
    const topics = ['zebra', 'setbacks', 'alpha'];
    const order = ['setbacks'];
    const result = sortTopicsByPriority(topics, order);
    expect(result[0]).toBe('setbacks');
    expect(result[1]).toBe('alpha');
    expect(result[2]).toBe('zebra');
  });

  test('empty priority order — alphabetical only', () => {
    const result = sortTopicsByPriority(['c', 'a', 'b'], []);
    expect(result).toEqual(['a', 'b', 'c']);
  });

  test('does not mutate input array', () => {
    const topics = ['b', 'a'];
    sortTopicsByPriority(topics, []);
    expect(topics).toEqual(['b', 'a']);
  });
});

// ---------------------------------------------------------------------------
// formatHcaName
// ---------------------------------------------------------------------------

describe('formatHcaName', () => {
  test('"General Heritage Controls" returned as-is', () => {
    expect(formatHcaName('General Heritage Controls')).toBe('General Heritage Controls');
  });

  test('slug converted to title case with HCA suffix', () => {
    expect(formatHcaName('summer_hill')).toBe('Summer Hill HCA');
    expect(formatHcaName('ashfield_heights')).toBe('Ashfield Heights HCA');
  });
});

// ---------------------------------------------------------------------------
// formatDcpPart
// ---------------------------------------------------------------------------

describe('formatDcpPart', () => {
  test('empty/Other returns General Controls', () => {
    expect(formatDcpPart('')).toBe('General Controls');
    expect(formatDcpPart('Other')).toBe('General Controls');
  });

  test('council label lookup used when available', () => {
    expect(formatDcpPart('Part 8', 'marrickville')).toBe('Part 8 – Heritage');
    expect(formatDcpPart('Chapter F', 'ashfield')).toBe('Chapter F – Development Types');
  });

  test('unknown council falls back to raw part string', () => {
    expect(formatDcpPart('Part 4.1', 'unknown_council')).toBe('Part 4.1');
  });

  test('no council returns raw part string', () => {
    expect(formatDcpPart('Part 4.1')).toBe('Part 4.1');
  });
});

// ---------------------------------------------------------------------------
// getLayerLabel
// ---------------------------------------------------------------------------

describe('getLayerLabel', () => {
  test('known layers return labels', () => {
    expect(getLayerLabel('generic')).toBe('General');
    expect(getLayerLabel('use_specific')).toBe('Zone-Specific');
    expect(getLayerLabel('condition')).toBe('Condition');
    expect(getLayerLabel('precinct')).toBe('Precinct');
  });

  test('null/undefined/unknown/null-string all return General', () => {
    expect(getLayerLabel(null)).toBe('General');
    expect(getLayerLabel(undefined)).toBe('General');
    expect(getLayerLabel('unknown')).toBe('General');
    expect(getLayerLabel('null')).toBe('General');
  });

  test('unrecognised layer value returned as-is', () => {
    expect(getLayerLabel('custom_layer')).toBe('custom_layer');
  });
});
