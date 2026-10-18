/**
 * 6 Berrigan St Winston Hills, 2026-10-19: the SEPP Requirements card listed "SEPP 2022" and
 * "SEPP 2021". The identifier was built from the first number after "SEPP", which for a named
 * instrument is its year, so every named SEPP collapsed to its year.
 */
import { NSWPlanningPortalService } from '@/lib/nsw-planning-portal';

function seppsFor(result: Record<string, string>): string[] {
  const constraints = { applicableSepps: [] as string[] } as Parameters<
    typeof NSWPlanningPortalService.extractApplicableSepps
  >[1];
  NSWPlanningPortalService.extractApplicableSepps(result, constraints);
  return constraints.applicableSepps ?? [];
}

describe('extractApplicableSepps - identifiers name the instrument, not its year', () => {
  it('a named instrument keeps its name', () => {
    const ids = seppsFor({ 'EPI Name': 'State Environmental Planning Policy (Precincts—Western Parkland City) 2021' });
    expect(ids).toEqual(['SEPP (Precincts—Western Parkland City) 2021']);
  });

  it('Sustainable Buildings maps to its known identifier and nothing year-only', () => {
    const ids = seppsFor({ 'EPI Name': 'State Environmental Planning Policy (Sustainable Buildings) 2022' });
    expect(ids).toEqual(['SEPP_SUSTAINABLE_BUILDINGS_2022']);
  });

  it('a map title naming a repealed instrument adds no identifier of its own', () => {
    const ids = seppsFor({ 'Map Type': 'SEPP (Western Sydney Aerotropolis) 2020 Wind Turbines Map' });
    expect(ids).toEqual([]);
  });

  it('a numbered policy keeps its number', () => {
    expect(seppsFor({ 'EPI Name': 'SEPP 65' })).toEqual(['SEPP_65']);
  });

  it('no identifier is ever just a year', () => {
    const ids = seppsFor({
      'EPI Name': 'State Environmental Planning Policy (Housing) 2021',
      Description: 'State Environmental Planning Policy (Resilience and Hazards) 2021',
    });
    expect(ids.some(id => /^SEPP_\d{4}$/.test(id))).toBe(false);
    expect(ids).toEqual(expect.arrayContaining(['SEPP_HOUSING_2021', 'SEPP_RESILIENCE_HAZARDS_2021']));
  });
});
