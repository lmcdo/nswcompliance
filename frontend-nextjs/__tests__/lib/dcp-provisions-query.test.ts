/**
 * The query the assessment page sends to /api/provisions/for-property.
 *
 * PR #1259 taught the route to withhold site-only Inner West LEP rules when given land_facts, and
 * wired land_facts into hooks/useFullPropertyData.ts -- which nothing mounts. The page users see
 * kept sending no land_facts, so the fix never reached them. These tests pin both halves: the
 * builder sends it, and the MOUNTED component builds its query with the builder.
 */
import * as fs from 'fs';
import * as path from 'path';
import { buildForPropertyParams } from '@/lib/dcp-provisions-query';
import { decodeLandFacts } from '@/lib/lep-land-condition';

const FACTS = { zone: 'R1', layers: { 'Key Sites Map': ['Area 19'] } };

describe('buildForPropertyParams', () => {
  it('sends the lot land facts, and the route can read them back', () => {
    const p = buildForPropertyParams({ formerCouncil: 'Leichhardt', zone: 'R1', landFacts: FACTS });
    expect(p.get('land_facts')).not.toBeNull();
    expect(decodeLandFacts(p.get('land_facts'))).toEqual(FACTS);
  });

  it('omits land_facts when the portal gave none (route then marks rules unconfirmed)', () => {
    expect(buildForPropertyParams({ formerCouncil: 'Leichhardt', landFacts: null }).has('land_facts')).toBe(false);
  });

  it('keeps every parameter the page sent before', () => {
    const p = buildForPropertyParams({
      formerCouncil: 'Leichhardt', zone: 'R1', heritage: false, hcaName: 'Annandale HCA', precinctId: 'C2.2.1.1',  // noqa: zone-codes -- a fixture's own zone and precinct, not a lookup list
      landApplicationInstruments: [{ name: 'Inner West Local Environmental Plan 2022', type: 'Included' }],
    });
    expect(p.get('groupBy')).toBe('toc');
    expect(p.get('former_council')).toBe('Leichhardt');
    expect(p.get('zone')).toBe('R1');
    expect(p.get('heritage')).toBe('false');
    expect(p.get('hca')).toBe('Annandale HCA');
    expect(p.get('precinct_id')).toBe('C2.2.1.1');
    expect(JSON.parse(p.get('land_application')!)).toEqual([
      { name: 'Inner West Local Environmental Plan 2022', type: 'Included' },
    ]);
  });
});

describe('the mounted assessment page uses the builder', () => {
  const src = fs.readFileSync(
    path.join(__dirname, '../../components/compliance/ProvisionsByTocStructure.tsx'), 'utf8');

  it('ProvisionsByTocStructure builds its query with buildForPropertyParams and passes landFacts', () => {
    expect(src).toMatch(/buildForPropertyParams\(\{[\s\S]*?landFacts:\s*propertyData\?\.constraints\?\.landFacts/);
  });

  it('the assessment page still mounts ProvisionsByTocStructure', () => {
    const page = fs.readFileSync(path.join(__dirname, '../../app/assessment/page.tsx'), 'utf8');
    expect(page).toMatch(/<ProvisionsByTocStructure[\s\S]*?propertyData=\{selectedProperty\}/);
  });
});
