import { NUMERIC_MEASUREMENT_RE } from '@/lib/see/provisionUtils';

// W1-3: NUMERIC_MEASUREMENT_RE
describe('NUMERIC_MEASUREMENT_RE', () => {
  const matches = [
    '10m',
    '2.5m',
    '500mm',
    '10cm',
    '1.5km',
    '40%',
    '1.5ha',
    '10 ha',
    '200sqm',
    '1500 sqm',
    '3 metres',
    '3 metre',
    '10 meters',
    '5 hectares',
  ];

  const nonMatches = [
    'fencing',
    'any development',
    '10',
    'clause 4.3',
    'section 5',
  ];

  test.each(matches)('matches: %s', (input) => {
    expect(NUMERIC_MEASUREMENT_RE.test(input)).toBe(true);
  });

  test.each(nonMatches)('does not match: %s', (input) => {
    expect(NUMERIC_MEASUREMENT_RE.test(input)).toBe(false);
  });

  test('matches within a longer provision text', () => {
    const text = 'The maximum height of buildings is 10m as measured from natural ground level.';
    expect(NUMERIC_MEASUREMENT_RE.test(text)).toBe(true);
  });

  test('matches FSR-style provision text', () => {
    expect(NUMERIC_MEASUREMENT_RE.test('Maximum floor space ratio is 40%')).toBe(true);
  });

  test('matches setback in mm', () => {
    expect(NUMERIC_MEASUREMENT_RE.test('Minimum setback 900mm from boundary')).toBe(true);
  });

  test('case insensitive for unit words', () => {
    expect(NUMERIC_MEASUREMENT_RE.test('2 Metres')).toBe(true);
    expect(NUMERIC_MEASUREMENT_RE.test('5 HECTARES')).toBe(true);
  });

  test('does not match bare number in clause reference', () => {
    expect(NUMERIC_MEASUREMENT_RE.test('clause 4.3 applies')).toBe(false);
  });
});
