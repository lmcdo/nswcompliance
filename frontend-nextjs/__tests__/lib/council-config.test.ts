import {
  detectCouncil,
  getCouncilConfig,
  getConfiguredCouncils,
  isCouncilConfigured,
  getCouncilConfigByLGA,
  getSetbackFallback,
  sortTopicsByPriority,
  getSortedCategoryGroups,
  getCategoryGroup,
  COUNCIL_CONFIGS,
  CouncilConfig,
} from '@/lib/council-config';

describe('Council Config', () => {
  describe('COUNCIL_CONFIGS', () => {
    test('contains all three Inner West councils', () => {
      expect(COUNCIL_CONFIGS).toHaveProperty('marrickville');
      expect(COUNCIL_CONFIGS).toHaveProperty('leichhardt');
      expect(COUNCIL_CONFIGS).toHaveProperty('ashfield');
    });

    test('each council has required fields', () => {
      const requiredFields: (keyof CouncilConfig)[] = [
        'id',
        'name',
        'dcpCitation',
        'dcpExplanation',
        'totalProvisions',
        'primaryLayer',
        'layerLabels',
        'categoryGroups',
      ];

      for (const [councilId, config] of Object.entries(COUNCIL_CONFIGS)) {
        for (const field of requiredFields) {
          expect(config).toHaveProperty(field);
        }
      }
    });

    test('marrickville has correct provision count', () => {
      expect(COUNCIL_CONFIGS.marrickville.totalProvisions).toBe(1866);
    });

    test('leichhardt has correct provision count', () => {
      expect(COUNCIL_CONFIGS.leichhardt.totalProvisions).toBe(3355);
    });

    test('ashfield has correct provision count', () => {
      expect(COUNCIL_CONFIGS.ashfield.totalProvisions).toBe(1892);
    });
  });

  describe('detectCouncil', () => {
    test('detects marrickville from formerCouncil', () => {
      expect(detectCouncil(undefined, 'Marrickville')).toBe('marrickville');
      expect(detectCouncil(undefined, 'marrickville')).toBe('marrickville');
    });

    test('detects leichhardt from formerCouncil', () => {
      expect(detectCouncil(undefined, 'Leichhardt')).toBe('leichhardt');
    });

    test('detects ashfield from formerCouncil', () => {
      expect(detectCouncil(undefined, 'Ashfield')).toBe('ashfield');
    });

    test('detects council from LGA name', () => {
      expect(detectCouncil('Marrickville', undefined)).toBe('marrickville');
      expect(detectCouncil('Leichhardt', undefined)).toBe('leichhardt');
    });

    test('returns null for Inner West without specific council', () => {
      expect(detectCouncil('Inner West', undefined)).toBeNull();
    });

    test('returns null for unknown LGA', () => {
      expect(detectCouncil('Wollongong', undefined)).toBeNull();
      expect(detectCouncil('Central Coast', undefined)).toBeNull();
    });

    test('handles empty/undefined inputs', () => {
      expect(detectCouncil(undefined, undefined)).toBeNull();
      expect(detectCouncil('', '')).toBeNull();
    });
  });

  describe('getCouncilConfig', () => {
    test('returns config for valid council ID', () => {
      const config = getCouncilConfig('marrickville');
      expect(config.id).toBe('marrickville');
      expect(config.name).toBe('Marrickville');
    });

    test('returns marrickville as fallback for null', () => {
      const config = getCouncilConfig(null);
      expect(config.id).toBe('marrickville');
    });

    test('returns marrickville as fallback for unknown council', () => {
      const config = getCouncilConfig('unknown');
      expect(config.id).toBe('marrickville');
    });
  });

  describe('getConfiguredCouncils', () => {
    test('returns array of council IDs', () => {
      const councils = getConfiguredCouncils();
      expect(councils).toContain('marrickville');
      expect(councils).toContain('leichhardt');
      expect(councils).toContain('ashfield');
    });

    test('returns at least 3 councils', () => {
      expect(getConfiguredCouncils().length).toBeGreaterThanOrEqual(3);
    });
  });

  describe('isCouncilConfigured', () => {
    test('returns true for configured councils', () => {
      expect(isCouncilConfigured('marrickville')).toBe(true);
      expect(isCouncilConfigured('leichhardt')).toBe(true);
      expect(isCouncilConfigured('ashfield')).toBe(true);
    });

    test('returns false for unconfigured councils', () => {
      expect(isCouncilConfigured('parramatta')).toBe(false);
      expect(isCouncilConfigured('central_coast')).toBe(false);
      expect(isCouncilConfigured('sydney')).toBe(false);
    });
  });

  describe('getCouncilConfigByLGA', () => {
    test('returns config for known LGA', () => {
      const config = getCouncilConfigByLGA('Marrickville');
      expect(config?.id).toBe('marrickville');
    });

    test('returns null for unknown LGA', () => {
      expect(getCouncilConfigByLGA('Wollongong')).toBeNull();
    });
  });

  describe('getSetbackFallback', () => {
    test('returns setback guidance for marrickville', () => {
      const fallback = getSetbackFallback('marrickville');
      expect(fallback.type).toBe('prevailing');
      expect(fallback.message).toContain('character-based');
      expect(fallback.guidance).toBeDefined();
    });

    test('returns setback guidance for leichhardt', () => {
      const fallback = getSetbackFallback('leichhardt');
      expect(fallback.type).toBe('prevailing');
      expect(fallback.guidance?.length).toBeGreaterThan(0);
    });

    test('returns setback guidance for ashfield', () => {
      const fallback = getSetbackFallback('ashfield');
      expect(fallback.type).toBe('prevailing');
    });

    test('returns default fallback for unknown council', () => {
      const fallback = getSetbackFallback('unknown');
      // Falls back to marrickville config
      expect(fallback.type).toBe('prevailing');
    });
  });

  describe('sortTopicsByPriority', () => {
    test('sorts topics by certifier priority', () => {
      const topics = ['parking', 'heritage', 'setbacks'];
      const sorted = sortTopicsByPriority(topics, 'marrickville', 'certifier');

      // Marrickville certifier order starts with setbacks
      expect(sorted.indexOf('setbacks')).toBeLessThan(sorted.indexOf('parking'));
    });

    test('sorts topics by planner priority', () => {
      const topics = ['setbacks', 'building_form', 'heritage'];
      const sorted = sortTopicsByPriority(topics, 'marrickville', 'planner');

      // Marrickville planner order starts with building_form
      expect(sorted[0]).toBe('building_form');
    });

    test('places unlisted topics at end', () => {
      const topics = ['setbacks', 'unknown_topic'];
      const sorted = sortTopicsByPriority(topics, 'marrickville', 'certifier');

      expect(sorted.indexOf('setbacks')).toBeLessThan(sorted.indexOf('unknown_topic'));
    });
  });

  describe('getSortedCategoryGroups', () => {
    test('returns category groups in priority order', () => {
      const groups = getSortedCategoryGroups('marrickville');

      // Should be sorted by priority
      for (let i = 0; i < groups.length - 1; i++) {
        expect(groups[i].group.priority).toBeLessThanOrEqual(groups[i + 1].group.priority);
      }
    });

    test('includes heritage group for marrickville', () => {
      const groups = getSortedCategoryGroups('marrickville');
      const heritageGroup = groups.find(g => g.key === 'heritage');

      expect(heritageGroup).toBeDefined();
      expect(heritageGroup?.group.label).toBe('Heritage');
    });
  });

  describe('getCategoryGroup', () => {
    test('returns correct group for heritage category', () => {
      const result = getCategoryGroup('heritage', 'marrickville');
      expect(result?.groupKey).toBe('heritage');
    });

    test('returns correct group for parking category', () => {
      const result = getCategoryGroup('parking', 'marrickville');
      expect(result?.groupKey).toBe('parking');
    });

    test('returns other group for unknown category', () => {
      const result = getCategoryGroup('unknown_category', 'marrickville');
      expect(result?.groupKey).toBe('other');
    });

    test('is case insensitive', () => {
      const result1 = getCategoryGroup('Heritage', 'marrickville');
      const result2 = getCategoryGroup('HERITAGE', 'marrickville');

      expect(result1?.groupKey).toBe(result2?.groupKey);
    });
  });

  describe('Layer labels', () => {
    test('marrickville has custom layer labels', () => {
      const config = COUNCIL_CONFIGS.marrickville;
      expect(config.layerLabels.generic).toBe('Base Controls');
      expect(config.layerLabels.precinct).toBe('Precinct Character');
    });

    test('leichhardt has custom layer labels', () => {
      const config = COUNCIL_CONFIGS.leichhardt;
      expect(config.layerLabels.generic).toBe('Universal');
      expect(config.layerLabels.precinct).toBe('Distinct Neighbourhood');
    });

    test('ashfield has custom layer labels', () => {
      const config = COUNCIL_CONFIGS.ashfield;
      expect(config.layerLabels.precinct).toBe('Village Precinct');
    });
  });

  describe('Primary layers', () => {
    test('marrickville uses generic as primary layer', () => {
      expect(COUNCIL_CONFIGS.marrickville.primaryLayer).toBe('generic');
    });

    test('leichhardt uses generic as primary layer', () => {
      expect(COUNCIL_CONFIGS.leichhardt.primaryLayer).toBe('generic');
    });

    test('ashfield uses condition as primary layer', () => {
      expect(COUNCIL_CONFIGS.ashfield.primaryLayer).toBe('condition');
    });
  });

  describe('Hidden layers', () => {
    test('marrickville has no hidden layers', () => {
      expect(COUNCIL_CONFIGS.marrickville.hideLayers).toEqual([]);
    });

    test('leichhardt hides use_specific layer', () => {
      expect(COUNCIL_CONFIGS.leichhardt.hideLayers).toContain('use_specific');
    });

    test('ashfield hides use_specific layer', () => {
      expect(COUNCIL_CONFIGS.ashfield.hideLayers).toContain('use_specific');
    });
  });
});
