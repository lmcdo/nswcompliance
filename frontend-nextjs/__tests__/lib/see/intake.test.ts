import {
  normalizeTopicKey,
  getExcludableTopics,
  getTopicExclusionReason,
  isProvisionExcluded,
  DEFAULT_INTAKE_ANSWERS,
  type IntakeAnswers,
} from '@/lib/see/intake';

const allNo: IntakeAnswers = {
  new_impervious_surfaces: 'no',
  trees_affected: 'no',
  pool_or_spa: 'no',
  new_fencing: 'no',
  new_parking_or_driveway: 'no',
  new_signage: 'no',
};

const allYes: IntakeAnswers = {
  new_impervious_surfaces: 'yes',
  trees_affected: 'yes',
  pool_or_spa: 'yes',
  new_fencing: 'yes',
  new_parking_or_driveway: 'yes',
  new_signage: 'yes',
};

describe('normalizeTopicKey', () => {
  it('lowercases and replaces spaces with underscores', () => {
    expect(normalizeTopicKey('Vehicle Access')).toBe('vehicle_access');
    expect(normalizeTopicKey('Trees')).toBe('trees');
    expect(normalizeTopicKey('Open Space')).toBe('open_space');
  });

  it('returns empty string for null', () => {
    expect(normalizeTopicKey(null)).toBe('');
  });

  it('returns empty string for undefined', () => {
    expect(normalizeTopicKey(undefined)).toBe('');
  });

  it('handles already-normalized topics', () => {
    expect(normalizeTopicKey('parking')).toBe('parking');
  });
});

describe('getExcludableTopics', () => {
  it('excludes topics when answer is no', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, trees_affected: 'no' };
    const result = getExcludableTopics(answers);
    expect(result.has('trees')).toBe(true);
  });

  it('does not exclude topics when answer is yes', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, trees_affected: 'yes' };
    const result = getExcludableTopics(answers);
    expect(result.has('trees')).toBe(false);
  });

  it('does not exclude topics when answer is unknown', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, trees_affected: 'unknown' };
    const result = getExcludableTopics(answers);
    expect(result.has('trees')).toBe(false);
  });

  it('excludes all mapped topics for parking when no', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, new_parking_or_driveway: 'no' };
    const result = getExcludableTopics(answers);
    expect(result.has('parking')).toBe(true);
    expect(result.has('vehicle_access')).toBe(true);
    expect(result.has('carport')).toBe(true);
  });

  it('excludes both fencing topics when no', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, new_fencing: 'no' };
    const result = getExcludableTopics(answers);
    expect(result.has('fencing')).toBe(true);
    expect(result.has('fence')).toBe(true);
  });

  it('returns empty set when all answers are unknown (default)', () => {
    const result = getExcludableTopics(DEFAULT_INTAKE_ANSWERS);
    expect(result.size).toBe(0);
  });

  it('excludes all topics when all answers are no', () => {
    const result = getExcludableTopics(allNo);
    expect(result.size).toBeGreaterThan(0);
    expect(result.has('trees')).toBe(true);
    expect(result.has('signage')).toBe(true);
    expect(result.has('stormwater')).toBe(true);
  });

  it('excludes nothing when all answers are yes', () => {
    const result = getExcludableTopics(allYes);
    expect(result.size).toBe(0);
  });
});

describe('getTopicExclusionReason', () => {
  it('returns a reason for known topics', () => {
    expect(getTopicExclusionReason('trees')).toBe('No trees affected confirmed');
    expect(getTopicExclusionReason('signage')).toBe('No signage in proposal confirmed');
    expect(getTopicExclusionReason('parking')).toBe('No new parking or driveway works confirmed');
    expect(getTopicExclusionReason('fencing')).toBe('No new fencing confirmed');
    expect(getTopicExclusionReason('stormwater')).toBe('No new impervious surfaces confirmed');
  });

  it('falls back for unknown topics', () => {
    expect(getTopicExclusionReason('unknown_topic')).toBe('Excluded by intake triage');
  });

  it('the assembled intake response_text starts with Excluded by intake:', () => {
    // This mirrors the format used in handleIntakeApply in ProvisionsByTocStructure
    // and the split logic in SEEDocument (startsWith check)
    const responseText = `Excluded by intake: ${getTopicExclusionReason('trees')}`;
    expect(responseText.startsWith('Excluded by intake:')).toBe(true);
    expect(responseText).toBe('Excluded by intake: No trees affected confirmed');
  });
});

describe('isProvisionExcluded', () => {
  it('returns true when provision topic is excluded by intake answer', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, trees_affected: 'no' };
    expect(isProvisionExcluded('trees', answers)).toBe(true);
    expect(isProvisionExcluded('Trees', answers)).toBe(true);
  });

  it('returns false when provision topic is not in any trigger mapping', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, trees_affected: 'no' };
    expect(isProvisionExcluded('open_space', answers)).toBe(false);
    expect(isProvisionExcluded('heritage', answers)).toBe(false);
  });

  it('returns false when topic is in trigger but answer is yes', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, trees_affected: 'yes' };
    expect(isProvisionExcluded('trees', answers)).toBe(false);
  });

  it('returns false for null or undefined topic', () => {
    const answers: IntakeAnswers = { ...DEFAULT_INTAKE_ANSWERS, trees_affected: 'no' };
    expect(isProvisionExcluded(null, answers)).toBe(false);
    expect(isProvisionExcluded(undefined, answers)).toBe(false);
  });
});
