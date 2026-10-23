/**
 * Battle-axe detection measured on real NSW cadastre lots (EPSG:3857 rings from the
 * Spatial Services Lot layer, Belmore / Bowral / St Ives, 2026-10-24).
 *
 * Labels: each shape judged by eye at metre scale (real = an even-width access strip that
 * opens into a wider lot). One ambiguous shape is excluded. Not a survey — a regression
 * floor. The previous rule flagged ~51 of 1,200 lots, ~8 of them real.
 */
import { readFileSync } from 'fs';
import { join } from 'path';
import { detectBattleaxeLot } from '../lot-shape-analysis';

type Labelled = { id: string; real: boolean; ambiguous: boolean; ring: number[][] };
const LOTS: Labelled[] = JSON.parse(readFileSync(join(__dirname, 'fixtures/battleaxe-labelled-lots.json'), 'utf8'));

describe('battle-axe detection on labelled real lots', () => {
  const scored = LOTS.filter((l) => !l.ambiguous).map((l) => ({ ...l, flagged: detectBattleaxeLot({ rings: [l.ring] } as never).isBattleaxe }));
  const tp = scored.filter((l) => l.flagged && l.real).length;
  const fp = scored.filter((l) => l.flagged && !l.real).length;
  const fn = scored.filter((l) => !l.flagged && l.real).length;

  it('precision is at least 90%', () => {
    expect(tp / (tp + fp)).toBeGreaterThanOrEqual(0.9);
  });

  it('recall is at least 90%', () => {
    expect(tp / (tp + fn)).toBeGreaterThanOrEqual(0.9);
  });

  it('a rectangle tilted on the map is never a battle-axe', () => {
    for (const deg of [0, 17, 30, 45, 63]) {
      const a = (deg * Math.PI) / 180;
      const pts = [[0, 0], [40, 0], [40, 15], [0, 15], [0, 0]].map(([x, y]) => [
        16800000 + x * Math.cos(a) - y * Math.sin(a),
        -4010000 + x * Math.sin(a) + y * Math.cos(a),
      ]);
      expect(detectBattleaxeLot({ rings: [pts] } as never).isBattleaxe).toBe(false);
    }
  });

  it('a tilted real battle-axe shape is still found', () => {
    // 4 m wide, 25 m long strip opening into a 20 m x 25 m lot (projected units ~ metres x 1.2 at -33.9)
    const shape = [[0, 0], [4, 0], [4, 25], [20, 25], [20, 50], [0, 50], [0, 0]];
    for (const deg of [0, 30, 45]) {
      const a = (deg * Math.PI) / 180;
      const pts = shape.map(([x, y]) => [
        16800000 + 1.2 * (x * Math.cos(a) - y * Math.sin(a)),
        -4010000 + 1.2 * (x * Math.sin(a) + y * Math.cos(a)),
      ]);
      expect(detectBattleaxeLot({ rings: [pts] } as never).isBattleaxe).toBe(true);
    }
  });
});
