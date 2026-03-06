import { buildSeppControls, buildPathwayDetermination, buildLepStandards } from '@/lib/see/seeBuilders';

// ---------------------------------------------------------------------------
// buildSeppControls — existing controls (regression)
// ---------------------------------------------------------------------------

describe('buildSeppControls', () => {
  test('returns empty array for undefined constraints', () => {
    expect(buildSeppControls(undefined)).toEqual([]);
  });

  test('returns empty array for empty constraints', () => {
    expect(buildSeppControls({})).toEqual([]);
  });

  test('includes BASIX water row when basixWater present', () => {
    const controls = buildSeppControls({ basixWater: 40, basixClimate: '6' });
    const water = controls.find(c => c.control === 'BASIX — Water Efficiency');
    expect(water).toBeDefined();
    expect(water!.instrument).toBe('SEPP (Sustainable Buildings) 2022');
    expect(water!.requirement).toContain('40');
  });

  test('includes BASIX energy row when basixClimate present', () => {
    const controls = buildSeppControls({ basixWater: 40, basixClimate: '6' });
    expect(controls.find(c => c.control === 'BASIX — Energy & Thermal Comfort')).toBeDefined();
  });

  test('includes TOD parking row when inTODArea true', () => {
    const controls = buildSeppControls({ todPrecinct: { inTODArea: true, stationName: 'Marrickville', stationDistance: 400 } });
    const tod = controls.find(c => c.control === 'TOD Parking Reduction');
    expect(tod).toBeDefined();
    expect(tod!.requirement).toContain('Marrickville');
  });

  test('includes ANEF row when inAnefZone true', () => {
    const controls = buildSeppControls({ anefData: { inAnefZone: true, anefLevel: '20', airport: { name: 'Sydney Airport' } } });
    const anef = controls.find(c => c.control === 'Aircraft Noise Attenuation');
    expect(anef).toBeDefined();
    expect(anef!.requirement).toContain('Sydney Airport');
  });

  test('includes contamination row when hasNotifiedSites true', () => {
    const controls = buildSeppControls({ contaminatedLand: { hasNotifiedSites: true } });
    expect(controls.find(c => c.control === 'Site Contamination — Chapter 4')).toBeDefined();
  });

  // W1-7: new constraints
  test('includes mine subsidence row when inDistrict true', () => {
    const controls = buildSeppControls({ mineSubsidence: { inDistrict: true, districtName: 'Southern Coalfield' } });
    const row = controls.find(c => c.control === 'Mine Subsidence — Chapter 3');
    expect(row).toBeDefined();
    expect(row!.instrument).toBe('SEPP (Resilience and Hazards) 2021');
    expect(row!.requirement).toContain('Southern Coalfield');
  });

  test('mine subsidence row omitted when inDistrict false', () => {
    const controls = buildSeppControls({ mineSubsidence: { inDistrict: false } });
    expect(controls.find(c => c.control === 'Mine Subsidence — Chapter 3')).toBeUndefined();
  });

  test('mine subsidence row omitted when mineSubsidence absent', () => {
    expect(buildSeppControls({}).find(c => c.control === 'Mine Subsidence — Chapter 3')).toBeUndefined();
  });

  test('includes landslide risk row when hasRisk true', () => {
    const controls = buildSeppControls({ landslideRisk: { hasRisk: true } });
    const row = controls.find(c => c.control === 'Landslide Risk');
    expect(row).toBeDefined();
    expect(row!.requirement).toContain('Geotechnical assessment');
  });

  test('landslide risk row omitted when hasRisk false', () => {
    expect(buildSeppControls({ landslideRisk: { hasRisk: false } }).find(c => c.control === 'Landslide Risk')).toBeUndefined();
  });

  test('includes drinking water catchment row when inCatchment true', () => {
    const controls = buildSeppControls({ drinkingWaterCatchment: { inCatchment: true } });
    const row = controls.find(c => c.control === 'Drinking Water Catchment — Chapter 2');
    expect(row).toBeDefined();
    expect(row!.instrument).toBe('SEPP (Resilience and Hazards) 2021');
  });

  test('drinking water catchment row omitted when inCatchment false', () => {
    expect(buildSeppControls({ drinkingWaterCatchment: { inCatchment: false } }).find(c => c.control === 'Drinking Water Catchment — Chapter 2')).toBeUndefined();
  });

  test('all status fields are pending by default', () => {
    const controls = buildSeppControls({
      basixWater: 40, basixClimate: '6',
      mineSubsidence: { inDistrict: true },
      landslideRisk: { hasRisk: true },
      drinkingWaterCatchment: { inCatchment: true },
    });
    for (const c of controls) { expect(c.status).toBe('pending'); }
  });
});
