/**
 * Lot Shape Analysis
 *
 * Detects battle-axe lots from cadastre geometry. A battle-axe lot reaches the road through
 * an access strip ("handle") that is narrower than the rest of the lot.
 *
 * Signature used (measured 2026-10-24 on 1,200 real lots in Belmore, Bowral and St Ives:
 * 10 of 11 flags real, against ~8 of 51 for the previous width-profile rule):
 * 1. Turn the lot to its own long axis (minimum-area bounding rectangle), so a lot that
 *    sits at an angle to the map grid does not look pointed at both ends.
 * 2. Measure the width across the lot at even steps along that axis.
 * 3. A battle-axe lot has, at one end, an even-width strip (widths within EVEN_RATIO of
 *    each other, at least MIN_STRIP_M wide and MIN_RUN_M long; no absolute cap) that
 *    opens suddenly (within JUMP_WITHIN_M, by at least STEP_RATIO) into a main lot that
 *    reaches at least JUMP_RATIO times the strip width (a flag lot may widen in steps).
 * Triangles, wedges and tilted rectangles narrow gradually, so they do not match.
 *
 * These are shape-recognition thresholds, not planning rules. The CDC battle-axe limits
 * are read from cdc_eligibility_standards and applied by lib/cdc/battleaxe-cdc.ts.
 */

import { scaleFactorForRing } from './mercator';
import type { LotGeometry } from '@/types/property';

const SLICES = 60;
const MIN_STRIP_M = 1.5;
const EVEN_RATIO = 1.3;
const MIN_RUN_M = 8;
/** The first step out of the strip must be at least this many times wider... */
const STEP_RATIO = 2.0;
/** ...and the main lot must reach at least this many times the strip width. */
const JUMP_RATIO = 3.0;
const JUMP_WITHIN_M = 4;
/** Slices under this share of the strip's median at the street end are a cut corner, not strip. */
const END_TRIM_RATIO = 0.75;

export interface BattleaxeDetectionResult {
  /** Whether lot appears to be battleaxe shape */
  isBattleaxe: boolean;
  /** Confidence in detection (0-1) */
  confidence: number;
  /** Estimated access way (handle) width in meters */
  accessWayWidth: number;
  /** Estimated access way length in meters */
  accessWayLength: number;
  /** Estimated main lot (head) width in meters */
  mainLotWidth: number;
  /** Estimated main lot area in sqm (excluding handle) */
  mainLotArea: number;
  /** Estimated main lot (head) length along the lot, metres (excluding handle) */
  mainLotLength?: number;
  /** Narrowest width across the main lot (head), metres */
  mainLotMinWidth?: number;
  /**
   * Whether the lot meets the stored CDC battle-axe limits. null until
   * applyBattleaxeLimits() runs, and when the limits could not be read or a
   * measurement is close to a limit.
   */
  meetsMinimumRequirements: boolean | null;
  /** Route-labelled messages from applyBattleaxeLimits(); empty from detection alone */
  complianceIssues: string[];
  /** Set by applyBattleaxeLimits(): meets / fails / near / not_checked */
  cdcStatus?: 'meets' | 'fails' | 'near' | 'not_checked';
  /** Set by applyBattleaxeLimits(): instrument and clause the limits came from */
  cdcRef?: string | null;
  /** Set by applyBattleaxeLimits(): PDF page of that clause */
  cdcPdfPage?: number | null;
  /** Width measurements at each cross-section (for debugging) */
  widthProfile?: number[];
}

export interface LotShapeAnalysis {
  /** Lot shape classification */
  lotType: 'rectangular' | 'battleaxe' | 'irregular';
  /** Battleaxe details if applicable */
  battleaxe?: BattleaxeDetectionResult;
}

/**
 * Analyze lot shape and detect battleaxe configuration
 */
export function analyzeLotShape(geometry: LotGeometry): LotShapeAnalysis {
  if (!geometry?.rings?.length || !geometry.rings[0]?.length) {
    return { lotType: 'irregular' };
  }

  const coordinates = geometry.rings[0];
  if (coordinates.length < 5) {
    // Need at least 5 points for battleaxe (minimum 4 sides + closing point)
    return { lotType: coordinates.length === 5 ? 'rectangular' : 'irregular' };
  }

  const battleaxe = detectBattleaxeLot(geometry);

  if (battleaxe.isBattleaxe) {
    return {
      lotType: 'battleaxe',
      battleaxe,
    };
  }

  // Simple rectangular detection (4 boundaries)
  const isRectangular = coordinates.length === 5; // 4 sides + closing point
  return {
    lotType: isRectangular ? 'rectangular' : 'irregular',
  };
}

/**
 * Detect a battle-axe lot: straighten the lot, then look for an even-width strip at one end
 * that opens suddenly into a much wider part.
 */
export function detectBattleaxeLot(geometry: LotGeometry): BattleaxeDetectionResult {
  const none: BattleaxeDetectionResult = {
    isBattleaxe: false,
    confidence: 0,
    accessWayWidth: 0,
    accessWayLength: 0,
    mainLotWidth: 0,
    mainLotArea: 0,
    meetsMinimumRequirements: null,
    complianceIssues: [],
  };
  const ring = geometry?.rings?.[0];
  if (!ring || ring.length < 4) return none;

  const k = 1 / scaleFactorForRing(ring); // metres per projected unit (EPSG:3857 is stretched by 1/cos(lat))
  const poly = straighten(ring);
  if (poly[0][0] !== poly[poly.length - 1][0] || poly[0][1] !== poly[poly.length - 1][1]) poly.push(poly[0]);
  let x0 = Infinity;
  let x1 = -Infinity;
  for (const [x] of poly) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); }
  if (!(x1 > x0)) return none;
  const step = (x1 - x0) / SLICES;
  const stepM = step * k;
  const widths: number[] = [];
  for (let i = 0; i < SLICES; i++) widths.push(widthAt(poly, x0 + (i + 0.5) * step) * k);

  for (const seq of [widths, widths.slice().reverse()]) {
    // Skip a sliver where the lot meets the street, then trim a cut corner: slices well
    // under the next few slices' median are not yet strip.
    let i = 0;
    while (i < seq.length && seq[i] < MIN_STRIP_M * 0.5) i++;
    const probe = seq.slice(i, i + 5);
    if (!probe.length) continue;
    const probeMed = median(probe);
    while (i < seq.length && seq[i] < probeMed * END_TRIM_RATIO) i++;
    // Grow the strip while widths stay even (within EVEN_RATIO of the narrowest so far).
    const start = i;
    let lo = Infinity;
    let hi = -Infinity;
    while (i < seq.length) {
      const nlo = Math.min(lo, seq[i]);
      const nhi = Math.max(hi, seq[i]);
      if (nhi > nlo * EVEN_RATIO) break;
      lo = nlo;
      hi = nhi;
      i++;
    }
    const run = seq.slice(start, i);
    if (run.length * stepM < MIN_RUN_M || lo < MIN_STRIP_M) continue;
    const strip = median(run);
    const within = Math.max(1, Math.round(JUMP_WITHIN_M / stepM));
    if (!seq.slice(i, i + within).some((v) => v >= strip * STEP_RATIO)) continue;

    // Main lot = everything after the strip, minus a sliver at the far boundary.
    const head = seq.slice(i).filter((v) => v >= MIN_STRIP_M * 0.5);
    if (!head.length || Math.max(...head) < strip * JUMP_RATIO) continue;
    const headArea = head.reduce((a, v) => a + v * stepM, 0);
    return {
      isBattleaxe: true,
      confidence: 0.8,
      accessWayWidth: round2(strip),
      accessWayLength: round2(run.length * stepM),
      mainLotWidth: round2(Math.max(...head)),
      mainLotArea: Math.round(headArea),
      mainLotLength: round2(head.length * stepM),
      mainLotMinWidth: round2(Math.min(...head)),
      meetsMinimumRequirements: null,
      complianceIssues: [],
      widthProfile: widths.map(round2),
    };
  }
  return { ...none, widthProfile: widths.map(round2) };
}

function round2(v: number): number {
  return Math.round(v * 100) / 100;
}

function median(v: number[]): number {
  const s = v.slice().sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
}

function convexHull(pts: number[][]): number[][] {
  const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o: number[], a: number[], b: number[]) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo: number[][] = [];
  const up: number[][] = [];
  for (const q of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  for (const q of p.reverse()) { while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
  return lo.slice(0, -1).concat(up.slice(0, -1));
}

/** Rotate the ring so the long side of its minimum-area bounding rectangle lies along x. */
function straighten(ring: number[][]): number[][] {
  const h = convexHull(ring);
  let best = { area: Infinity, ang: 0 };
  for (let i = 0; i < h.length; i++) {
    const a = h[i];
    const b = h[(i + 1) % h.length];
    const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
    const c = Math.cos(-ang);
    const s = Math.sin(-ang);
    let mnx = Infinity; let mxx = -Infinity; let mny = Infinity; let mxy = -Infinity;
    for (const [x, y] of h) {
      const rx = x * c - y * s;
      const ry = x * s + y * c;
      mnx = Math.min(mnx, rx); mxx = Math.max(mxx, rx); mny = Math.min(mny, ry); mxy = Math.max(mxy, ry);
    }
    const area = (mxx - mnx) * (mxy - mny);
    if (area < best.area) best = { area, ang: ang + ((mxx - mnx) >= (mxy - mny) ? 0 : Math.PI / 2) };
  }
  const c = Math.cos(-best.ang);
  const s = Math.sin(-best.ang);
  return ring.map(([x, y]) => [x * c - y * s, x * s + y * c]);
}

/** Total length of the line x = X that lies inside the polygon. */
function widthAt(poly: number[][], X: number): number {
  const ys: number[] = [];
  for (let i = 0; i < poly.length - 1; i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[i + 1];
    if ((x1 <= X && x2 > X) || (x2 <= X && x1 > X)) ys.push(y1 + ((X - x1) * (y2 - y1)) / (x2 - x1));
  }
  ys.sort((a, b) => a - b);
  let w = 0;
  for (let i = 0; i + 1 < ys.length; i += 2) w += ys[i + 1] - ys[i];
  return w;
}
