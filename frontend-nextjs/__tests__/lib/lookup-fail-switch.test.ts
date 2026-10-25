// prior-art-checked: no existing test covers forcedLookupFailure (new in lib/lookup-not-checked.ts).
import { forcedLookupFailure } from '@/lib/lookup-not-checked';

describe('LOOKUP_FAIL_CHECKS preview switch', () => {
  const saved = { ...process.env };
  afterEach(() => { process.env = { ...saved }; });

  it('fails a named check on preview', () => {
    process.env.VERCEL_ENV = 'preview';
    process.env.LOOKUP_FAIL_CHECKS = 'roads, precinct';
    expect(forcedLookupFailure('precinct')).toBeInstanceOf(Error);
    expect(forcedLookupFailure('roads')).toBeInstanceOf(Error);
  });

  it('leaves checks that are not named alone', () => {
    process.env.VERCEL_ENV = 'preview';
    process.env.LOOKUP_FAIL_CHECKS = 'precinct';
    expect(forcedLookupFailure('flood')).toBeNull();
  });

  it('does nothing when the switch is unset', () => {
    delete process.env.LOOKUP_FAIL_CHECKS;
    expect(forcedLookupFailure('precinct')).toBeNull();
  });

  it('is ignored on production even when set', () => {
    process.env.VERCEL_ENV = 'production';
    process.env.LOOKUP_FAIL_CHECKS = 'precinct';
    expect(forcedLookupFailure('precinct')).toBeNull();
  });
});
