import { strataPlanFromLots } from '@/lib/property/strata-plan';

describe('strataPlanFromLots', () => {
  it('reads the plan and unit count from the lot records (14 Gale St Concord)', () => {
    expect(strataPlanFromLots(['CP/-/SP9807', '2/-/SP9807', '3/-/SP9807', '1/-/SP9807', '4/-/SP9807']))
      .toEqual({ plan: 'SP9807', units: 4 });
  });
  it('a single unit record is still that plan', () => {
    expect(strataPlanFromLots(['3/-/SP12345'])).toEqual({ plan: 'SP12345', units: 1 });
  });
  it('an ordinary deposited-plan lot is not strata', () => {
    expect(strataPlanFromLots(['23/-/DP217713'])).toBeNull();
  });
  it('a mixed parcel is not called strata on one record', () => {
    expect(strataPlanFromLots(['1/-/DP1', 'CP/-/SP9807'])).toBeNull();
  });
  it('two different plans are not one scheme', () => {
    expect(strataPlanFromLots(['1/-/SP40111', '1/-/SP52872'])).toBeNull();
  });
  it('no records, or blanks, are not strata', () => {
    expect(strataPlanFromLots([])).toBeNull();
    expect(strataPlanFromLots([null, ''])).toBeNull();
  });
});
