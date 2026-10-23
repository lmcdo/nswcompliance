/**
 * Starting a Site Report from the link (?address=&plan=).
 *
 * The plotdetect.com.au hero form sends visitors here. The rule this file
 * protects: what the link carries is untrusted — an address must be real text
 * within a cap, and a plan must be one of the intent chips, or it is dropped.
 */
import { readBriefStartParams, MAX_URL_ADDRESS_LENGTH } from '@/app/reports/intelligence-brief/url-start';
import { INTENT_CHIPS } from '@/components/reports/BriefIntentOverlay';

const params = (query: string) => new URLSearchParams(query);

describe('readBriefStartParams', () => {
  it('reads a typed address and a known plan', () => {
    expect(readBriefStartParams(params('address=14+Stanley+St%2C+Concord&plan=granny_flat'))).toEqual({
      address: '14 Stanley St, Concord',
      intent: 'granny_flat',
    });
  });

  it('accepts every intent chip the page shows, and only those', () => {
    for (const chip of INTENT_CHIPS) {
      expect(readBriefStartParams(params(`plan=${chip.value}`)).intent).toBe(chip.value);
    }
    expect(readBriefStartParams(params('plan=hotel')).intent).toBeNull();
    expect(readBriefStartParams(params('plan=Granny+flat')).intent).toBeNull();
  });

  it('trims the address', () => {
    expect(readBriefStartParams(params('address=++1+Main+St++')).address).toBe('1 Main St');
  });

  it('drops an empty or whitespace-only address', () => {
    expect(readBriefStartParams(params('address=')).address).toBeNull();
    expect(readBriefStartParams(params('address=+++')).address).toBeNull();
  });

  it('drops an address over the cap rather than truncating it', () => {
    const long = 'a'.repeat(MAX_URL_ADDRESS_LENGTH + 1);
    expect(readBriefStartParams(params(`address=${long}`)).address).toBeNull();
    const atCap = 'a'.repeat(MAX_URL_ADDRESS_LENGTH);
    expect(readBriefStartParams(params(`address=${atCap}`)).address).toBe(atCap);
  });

  it('returns nothing for a bare link or no params', () => {
    expect(readBriefStartParams(params(''))).toEqual({ address: null, intent: null });
    expect(readBriefStartParams(null)).toEqual({ address: null, intent: null });
  });

  it('keeps a valid plan when the address is missing', () => {
    expect(readBriefStartParams(params('plan=duplex'))).toEqual({ address: null, intent: 'duplex' });
  });
});
