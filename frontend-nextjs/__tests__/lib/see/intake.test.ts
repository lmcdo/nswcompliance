import {
  normalizeTopicKey, getExcludableTopics, autoPopulateFromConstraints,
  DEFAULT_INTAKE_ANSWERS, INTAKE_QUESTIONS, AUTO_ANSWER_SOURCES, TRIGGER_TO_TOPICS,
  type IntakeAnswers,
} from '@/lib/see/intake';

describe('normalizeTopicKey', () => {
  test('lowercases', () => { expect(normalizeTopicKey('Flooding')).toBe('flooding'); });
  test('spaces to underscores', () => { expect(normalizeTopicKey('vehicle access')).toBe('vehicle_access'); });
  test('multiple spaces', () => { expect(normalizeTopicKey('acid sulfate soils')).toBe('acid_sulfate_soils'); });
  test('null returns empty', () => { expect(normalizeTopicKey(null)).toBe(''); });
  test('undefined returns empty', () => { expect(normalizeTopicKey(undefined)).toBe(''); });
  test('empty string returns empty', () => { expect(normalizeTopicKey('')).toBe(''); });
  test('already normalized', () => { expect(normalizeTopicKey('vehicle_access')).toBe('vehicle_access'); });
});

describe('DEFAULT_INTAKE_ANSWERS', () => {
  const ALL_FIELDS: (keyof IntakeAnswers)[] = [
    'new_impervious_surfaces', 'trees_affected', 'pool_or_spa', 'new_fencing',
    'new_parking_or_driveway', 'new_signage', 'flood_prone', 'bushfire_prone',
    'acid_sulfate_soils', 'coastal', 'biodiversity', 'acoustic_zone', 'demolition',
  ];
  test('all fields default to unknown', () => {
    for (const field of ALL_FIELDS) { expect(DEFAULT_INTAKE_ANSWERS[field]).toBe('unknown'); }
  });
  test('contains exactly the expected fields', () => {
    expect(Object.keys(DEFAULT_INTAKE_ANSWERS).sort()).toEqual(ALL_FIELDS.slice().sort());
  });
});

describe('getExcludableTopics', () => {
  const base: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS };
  test('empty set when all unknown', () => { expect(getExcludableTopics(base).size).toBe(0); });
  test('empty set when all yes', () => {
    const allYes = Object.fromEntries(Object.keys(base).map(k => [k, 'yes'])) as IntakeAnswers;
    expect(getExcludableTopics(allYes).size).toBe(0);
  });
  const cases: [keyof IntakeAnswers, string[]][] = [
    ['new_impervious_surfaces', ['stormwater', 'drainage']],
    ['trees_affected',          ['trees']],
    ['pool_or_spa',             ['pool']],
    ['new_fencing',             ['fencing', 'fence']],
    ['new_parking_or_driveway', ['parking', 'vehicle_access', 'carport']],
    ['new_signage',             ['signage']],
    ['flood_prone',             ['flooding']],
    ['bushfire_prone',          ['bushfire']],
    ['acid_sulfate_soils',      ['acid_sulfate']], // contamination removed: general contamination != ASS
    ['coastal',                 ['coastal']],
    ['biodiversity',            ['biodiversity']],
    ['acoustic_zone',           ['acoustic', 'noise', 'anef']],
    ['demolition',              ['demolition']],
  ];
  test.each(cases)('%s=no excludes %j', (field, topics) => {
    const a = { ...base, [field]: 'no' as const };
    for (const t of topics) { expect(getExcludableTopics(a).has(t)).toBe(true); }
  });
  test('unknown does not exclude', () => {
    expect(getExcludableTopics({ ...base, flood_prone: 'unknown' as const }).has('flooding')).toBe(false);
  });
  test('yes does not exclude', () => {
    expect(getExcludableTopics({ ...base, new_fencing: 'yes' as const }).has('fencing')).toBe(false);
  });
  test('accumulates from multiple no answers', () => {
    const t = getExcludableTopics({ ...base, new_fencing: 'no' as const, flood_prone: 'no' as const });
    expect(t.has('fencing')).toBe(true);
    expect(t.has('flooding')).toBe(true);
    expect(t.has('trees')).toBe(false);
  });
});

describe('autoPopulateFromConstraints', () => {
  test('flood_prone=no when floodProne false', () => {
    expect(autoPopulateFromConstraints({ floodProne: false }).flood_prone).toBe('no');
  });
  test('flood_prone unset when floodProne true', () => {
    expect(autoPopulateFromConstraints({ floodProne: true }).flood_prone).toBeUndefined();
  });
  test('flood_prone unset when floodProne absent', () => {
    expect(autoPopulateFromConstraints({}).flood_prone).toBeUndefined();
  });
  test('bushfire_prone=no when bushfireProne false', () => {
    expect(autoPopulateFromConstraints({ bushfireProne: false }).bushfire_prone).toBe('no');
  });
  test('bushfire_prone unset when bushfireProne true', () => {
    expect(autoPopulateFromConstraints({ bushfireProne: true }).bushfire_prone).toBeUndefined();
  });
  test('acid_sulfate_soils=no when acidSulfateSoils null', () => {
    expect(autoPopulateFromConstraints({ acidSulfateSoils: null }).acid_sulfate_soils).toBe('no');
  });
  test('acid_sulfate_soils=no when acidSulfateSoils absent', () => {
    expect(autoPopulateFromConstraints({}).acid_sulfate_soils).toBe('no');
  });
  test('acid_sulfate_soils unset when acidSulfateSoils has value', () => {
    expect(autoPopulateFromConstraints({ acidSulfateSoils: 'Class 2' }).acid_sulfate_soils).toBeUndefined();
  });
  test('coastal=no when coastalEnvironment.inCoastalArea false', () => {
    expect(autoPopulateFromConstraints({ coastalEnvironment: { inCoastalArea: false } }).coastal).toBe('no');
  });
  test('coastal unset when coastalEnvironment.inCoastalArea true', () => {
    expect(autoPopulateFromConstraints({ coastalEnvironment: { inCoastalArea: true } }).coastal).toBeUndefined();
  });
  test('coastal=no when coastalEnvironment absent (portal absence = not in coastal area)', () => {
    expect(autoPopulateFromConstraints({}).coastal).toBe('no');
  });
  test('biodiversity=no when inBiodiversityArea false', () => {
    expect(autoPopulateFromConstraints({ terrestrialBiodiversity: { inBiodiversityArea: false } }).biodiversity).toBe('no');
  });
  test('biodiversity unset when inBiodiversityArea true', () => {
    expect(autoPopulateFromConstraints({ terrestrialBiodiversity: { inBiodiversityArea: true } }).biodiversity).toBeUndefined();
  });
  test('biodiversity=no when terrestrialBiodiversity absent (portal absence = not in biodiversity area)', () => {
    expect(autoPopulateFromConstraints({}).biodiversity).toBe('no');
  });
  test('acoustic_zone=no when anefData.inAnefZone false', () => {
    expect(autoPopulateFromConstraints({ anefData: { inAnefZone: false } }).acoustic_zone).toBe('no');
  });
  test('acoustic_zone unset when inAnefZone true', () => {
    expect(autoPopulateFromConstraints({ anefData: { inAnefZone: true } }).acoustic_zone).toBeUndefined();
  });
  test('acoustic_zone unset when anefData absent', () => {
    expect(autoPopulateFromConstraints({}).acoustic_zone).toBeUndefined();
  });
  test('populates all fields for unconstrained site', () => {
    const r = autoPopulateFromConstraints({
      floodProne: false, bushfireProne: false,
      coastalEnvironment: { inCoastalArea: false },
      terrestrialBiodiversity: { inBiodiversityArea: false },
      anefData: { inAnefZone: false },
    });
    expect(r.flood_prone).toBe('no');
    expect(r.bushfire_prone).toBe('no');
    expect(r.coastal).toBe('no');
    expect(r.biodiversity).toBe('no');
    expect(r.acid_sulfate_soils).toBe('no');
    expect(r.acoustic_zone).toBe('no');
  });
});

// W1-6: AUTO_ANSWER_SOURCES parity
describe('AUTO_ANSWER_SOURCES parity', () => {
  test('every auto-answer field exists in DEFAULT_INTAKE_ANSWERS', () => {
    for (const f of Object.keys(AUTO_ANSWER_SOURCES) as (keyof IntakeAnswers)[]) {
      expect(DEFAULT_INTAKE_ANSWERS).toHaveProperty(f);
    }
  });
  test('auto-answer fields not in INTAKE_QUESTIONS (shown in pre-confirmed section)', () => {
    const autoFields = new Set(Object.keys(AUTO_ANSWER_SOURCES));
    const qFields = new Set(INTAKE_QUESTIONS.map(q => q.field));
    for (const f of autoFields) { expect(qFields.has(f as keyof IntakeAnswers)).toBe(false); }
  });
  test('each entry has non-empty citation, rationale, propertyField', () => {
    for (const [, src] of Object.entries(AUTO_ANSWER_SOURCES)) {
      expect(src!.citation.length).toBeGreaterThan(0);
      expect(src!.rationale.length).toBeGreaterThan(0);
      expect(src!.propertyField.length).toBeGreaterThan(0);
    }
  });
});

// W2-3: TRIGGER_TO_TOPICS exported and coverage valid
describe('TRIGGER_TO_TOPICS coverage (W2-3)', () => {
  test('every IntakeAnswers field has an entry in TRIGGER_TO_TOPICS', () => {
    const triggerKeys = Object.keys(TRIGGER_TO_TOPICS);
    const answerKeys = Object.keys(DEFAULT_INTAKE_ANSWERS);
    expect(triggerKeys.sort()).toEqual(answerKeys.sort());
  });

  test('contamination topic is NOT in acid_sulfate_soils trigger (W2-2)', () => {
    expect(TRIGGER_TO_TOPICS.acid_sulfate_soils).not.toContain('contamination');
  });

  test('acid_sulfate topic IS in acid_sulfate_soils trigger', () => {
    expect(TRIGGER_TO_TOPICS.acid_sulfate_soils).toContain('acid_sulfate');
  });

  test('no topic appears in more than one trigger field', () => {
    const seen = new Map<string, string>();
    for (const [field, topics] of Object.entries(TRIGGER_TO_TOPICS)) {
      for (const topic of topics) {
        if (seen.has(topic)) {
          throw new Error(`Topic "${topic}" appears in both "${seen.get(topic)}" and "${field}"`);
        }
        seen.set(topic, field);
      }
    }
  });
});
