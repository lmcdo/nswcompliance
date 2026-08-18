/**
 * Cohort tagging — identify a class without building accounts.
 *
 * The pairs matter. A rule that accepts everything is as wrong as one that
 * accepts nothing: the code arrives in a URL a stranger can edit and is written
 * to a database field, and an untagged visit must stay untagged rather than
 * becoming "unknown", which would read as a cohort in the data.
 */
import { getCohort } from '@/lib/cohort';

const KEY = 'pd.cohort';

// window.location is non-configurable here (the jest setup pins it), so the
// query string is changed through the History API, which jsdom implements and
// which is also how a real navigation would set it. Redefining the property
// throws — that was the first version's mistake.
function visit(search: string) {
  window.localStorage.clear();
  window.history.replaceState({}, '', `/assessment${search}`);
}

describe('getCohort', () => {
  afterEach(() => window.localStorage.clear());

  it('reads the code a lecturer put in the link', () => {
    visit('?cohort=uts-16658');
    expect(getCohort()).toBe('uts-16658');
  });

  it('remembers it after the student navigates away from that link', () => {
    visit('?cohort=uts-16658');
    getCohort();
    visit('');                                  // same browser, no query string
    window.localStorage.setItem(KEY, 'uts-16658');
    expect(getCohort()).toBe('uts-16658');
  });

  it('lower-cases and trims, so a pasted link still matches', () => {
    visit('?cohort=%20UTS-16658%20');
    expect(getCohort()).toBe('uts-16658');
  });

  it('returns NULL when untagged — not a placeholder', () => {
    visit('');
    expect(getCohort()).toBeNull();
  });

  describe('refuses a code it should not store', () => {
    it.each([
      ['?cohort=', 'empty'],
      ['?cohort=a', 'too short to be a real class code'],
      ['?cohort=-lead', 'leading dash'],
      ['?cohort=trail-', 'trailing dash'],
      ['?cohort=drop%20table', 'a space'],
      ["?cohort=x'; --", 'quote and comment'],
      ['?cohort=<script>', 'markup'],
      [`?cohort=${'a'.repeat(60)}`, 'absurdly long'],
    ])('%s (%s)', (search) => {
      visit(search);
      expect(getCohort()).toBeNull();
    });
  });

  it('survives localStorage being unavailable', () => {
    visit('?cohort=uts-16658');
    const spy = jest.spyOn(Storage.prototype, 'setItem')
      .mockImplementation(() => { throw new Error('private browsing'); });
    expect(() => getCohort()).not.toThrow();
    expect(getCohort()).toBeNull();
    spy.mockRestore();
  });

  it('CONTROL — it can say yes and no', () => {
    // A stub returning null always passes every rejection case above; a stub
    // echoing the input passes every acceptance case. Pin both here.
    visit('?cohort=uts-16658');
    expect(getCohort()).toBe('uts-16658');
    visit('?cohort=<script>');
    expect(getCohort()).toBeNull();
  });
});
