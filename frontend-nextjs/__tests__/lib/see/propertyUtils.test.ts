import {
  calculateGFA,
  anefStatusConfig,
  floodBlockTypeAnnotation,
  bushfireCategoryAnnotation,
} from '@/lib/see/propertyUtils';

// ── calculateGFA ──────────────────────────────────────────────────────────────

describe('calculateGFA', () => {
  test('standard residential: 0.5:1 × 450m²', () => {
    expect(calculateGFA(0.5, 450)).toBe(225);
  });

  test('TOD bonus: 4:1 × 600m²', () => {
    expect(calculateGFA(4, 600)).toBe(2400);
  });

  test('rounds to nearest m²', () => {
    // 0.6 × 333 = 199.8 → 200
    expect(calculateGFA(0.6, 333)).toBe(200);
  });

  test('1:1 ratio equals lot area', () => {
    expect(calculateGFA(1, 1200)).toBe(1200);
  });
});

// ── anefStatusConfig ──────────────────────────────────────────────────────────

describe('anefStatusConfig', () => {
  test('acceptable returns green badge classes', () => {
    const cfg = anefStatusConfig('acceptable');
    expect(cfg.label).toBe('Acceptable');
    expect(cfg.badgeClass).toContain('green');
    expect(cfg.iconColor).toContain('green');
  });

  test('conditional returns amber badge classes', () => {
    const cfg = anefStatusConfig('conditional');
    expect(cfg.label).toBe('Conditional');
    expect(cfg.badgeClass).toContain('amber');
    expect(cfg.iconColor).toContain('amber');
  });

  test('unacceptable returns red badge classes', () => {
    const cfg = anefStatusConfig('unacceptable');
    expect(cfg.label).toBe('Unacceptable');
    expect(cfg.badgeClass).toContain('red');
    expect(cfg.iconColor).toContain('red');
  });

  test('each status returns a distinct label', () => {
    const labels = (['acceptable', 'conditional', 'unacceptable'] as const).map(
      s => anefStatusConfig(s).label
    );
    expect(new Set(labels).size).toBe(3);
  });
});

// ── floodBlockTypeAnnotation ──────────────────────────────────────────────────

describe('floodBlockTypeAnnotation', () => {
  test('Floodway → mentions high flood risk and evacuation', () => {
    const ann = floodBlockTypeAnnotation('Floodway');
    expect(ann.toLowerCase()).toContain('high flood risk');
    expect(ann.toLowerCase()).toContain('evacuation');
  });

  test('Flood Planning Area → mentions floor level and materials', () => {
    const ann = floodBlockTypeAnnotation('Flood Planning Area');
    expect(ann.toLowerCase()).toContain('floor level');
    expect(ann.toLowerCase()).toContain('materials');
  });

  test('Flood Planning Level → treated as Flood Planning Area (contains "flood planning")', () => {
    const ann = floodBlockTypeAnnotation('Flood Planning Level');
    expect(ann.toLowerCase()).toContain('floor level');
  });

  test('unknown type → generic flood assessment message', () => {
    const ann = floodBlockTypeAnnotation('Unknown Flood Type');
    expect(ann.length).toBeGreaterThan(0);
    expect(ann.toLowerCase()).toContain('flood');
  });

  test('case insensitive matching', () => {
    expect(floodBlockTypeAnnotation('FLOODWAY')).toContain('high flood risk');
    expect(floodBlockTypeAnnotation('flood planning area')).toContain('floor level');
  });
});

// ── bushfireCategoryAnnotation ────────────────────────────────────────────────

describe('bushfireCategoryAnnotation', () => {
  test('Flame Zone → CDC blocked, annotation mentions CDC and BAL', () => {
    const result = bushfireCategoryAnnotation('Flame Zone');
    expect(result.cdcBlocked).toBe(true);
    expect(result.annotation.toLowerCase()).toContain('cdc');
    expect(result.annotation.toLowerCase()).toContain('bal');
  });

  test('Inner Protection Area → CDC blocked', () => {
    expect(bushfireCategoryAnnotation('Inner Protection Area').cdcBlocked).toBe(true);
  });

  test('Asset Protection Zone → CDC not blocked, mentions BAL assessment', () => {
    const result = bushfireCategoryAnnotation('Asset Protection Zone');
    expect(result.cdcBlocked).toBe(false);
    expect(result.annotation.toLowerCase()).toContain('bal');
  });

  test('Vegetation Buffer → CDC not blocked', () => {
    const result = bushfireCategoryAnnotation('Vegetation Buffer');
    expect(result.cdcBlocked).toBe(false);
    expect(result.annotation.length).toBeGreaterThan(0);
  });

  test('unknown category → CDC not blocked, generic message', () => {
    const result = bushfireCategoryAnnotation('Unknown BAZ Category');
    expect(result.cdcBlocked).toBe(false);
    expect(result.annotation.toLowerCase()).toContain('bushfire');
  });

  test('case insensitive: flame zone lowercase', () => {
    expect(bushfireCategoryAnnotation('flame zone').cdcBlocked).toBe(true);
  });
});
