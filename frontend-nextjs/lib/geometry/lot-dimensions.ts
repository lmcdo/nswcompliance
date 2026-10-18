/**
 * Lot Dimensions Calculator
 *
 * Extracts frontage, depth, area, and boundary information from lot geometry.
 * Uses polygon rings from NSW Planning Portal or Cadastre API.
 *
 * Coordinate System: NSW Planning Portal uses Web Mercator (EPSG:3857)
 */

import type { LotGeometry } from '@/types/property';
import { analyzeLotShape, type BattleaxeDetectionResult } from './lot-shape-analysis';
import { scaleFactorForRing, usableRing } from './mercator';

export interface LotDimensions {
  /** Lot area in square meters */
  area: number;
  /**
   * Shorter side of the lot's minimum-area bounding rectangle, in metres, or
   * null when the lot is too irregular for a rectangle to describe it. NOT the
   * road-facing edge: nothing here knows where the road is. The shorter side is
   * never more than the true frontage, so a minimum-frontage test cannot pass on it
   * wrongly. Same method as services/lot_dimensions.py (#499).
   */
  frontage: number | null;
  /** Longer side of the same rectangle, in metres, or null with frontage. */
  depth: number | null;
  /** All boundary segments with classification */
  boundaries: BoundarySegment[];
  /** Confidence in measurements (0-1) */
  confidence: number;
  /** Notes about the calculation */
  notes: string[];
  /** Lot shape classification */
  lotType?: 'rectangular' | 'battleaxe' | 'irregular';
  /** Battleaxe lot details (if applicable) */
  battleaxe?: BattleaxeDetectionResult;
}

export interface BoundarySegment {
  type: 'front' | 'rear' | 'side_left' | 'side_right' | 'unknown';
  length: number;
  bearing: number;
  startPoint: { x: number; y: number };
  endPoint: { x: number; y: number };
}

// NSW average latitude for Web Mercator scale correction
// Mercator correction now comes from the ring's own latitude — see ./mercator.
// A single state-wide constant read a Tweed Heads lot ~9.8% small.

/**
 * Calculate lot dimensions from geometry rings
 */
export function calculateLotDimensions(geometry: LotGeometry): LotDimensions | null {
  if (!geometry?.rings?.length || !geometry.rings[0]?.length) {
    return null;
  }

  const notes: string[] = [];
  const coordinates = geometry.rings[0];

  // Need at least 4 points for a closed polygon (triangle minimum)
  if (coordinates.length < 4) {
    notes.push('Insufficient coordinates for boundary analysis');
    return null;
  }

  // Convert to real-world meters and close the polygon if needed
  // Reject a malformed ring outright — a fallback scale does not make NaN
  // coordinates safe, it only stops the divisor being NaN, and a NaN area then
  // slips past every `> 0` check because comparisons with NaN are false.
  const safeRing = usableRing(coordinates);
  if (safeRing == null) {
    notes.push('Lot geometry contains non-finite coordinates');
    return null;
  }

  const scaleFactor = scaleFactorForRing(safeRing);
  const points = safeRing.map((coord) => ({
    x: coord[0] / scaleFactor,
    y: coord[1] / scaleFactor,
  }));

  // Calculate area using shoelace formula
  const area = calculatePolygonArea(points);

  // Extract boundary segments
  const boundaries = extractBoundarySegments(points);

  // Classify boundaries based on position and bearing
  classifyBoundaries(boundaries);

  // Frontage/depth from the minimum-area bounding rectangle, not from boundary
  // classification. The classifier picked ONE segment per side, so a curved side
  // stored as eight 1.67 m pieces made 6 Berrigan St Winston Hills (688 m2) read
  // 38.4 m x 3.9 m. The rectangle does not care how a side is cut up.
  const { frontage, depth } = frontageDepthFromRect(points, area);

  let confidence = 0.9;
  if (frontage == null) {
    confidence -= 0.2;
    notes.push('Lot too irregular for frontage and depth to be measured');
  }
  if (boundaries.length !== 4) {
    confidence -= 0.1;
    notes.push(`Irregular lot shape (${boundaries.length} boundaries)`);
  }

  // Analyze lot shape for battleaxe detection
  const shapeAnalysis = analyzeLotShape(geometry);
  const lotType = shapeAnalysis.lotType;
  const battleaxe = shapeAnalysis.battleaxe;

  if (battleaxe?.isBattleaxe) {
    notes.push(`Battleaxe lot detected (handle: ${battleaxe.accessWayWidth}m, head: ${battleaxe.mainLotWidth}m)`);
    if (!battleaxe.meetsMinimumRequirements) {
      notes.push('WARNING: Does not meet SEPP Housing 2021 minimum requirements');
    }
  }

  return {
    area: Math.round(area * 100) / 100,
    frontage: frontage == null ? null : Math.round(frontage * 100) / 100,
    depth: depth == null ? null : Math.round(depth * 100) / 100,
    boundaries,
    confidence: Math.max(0.5, confidence),
    notes,
    lotType,
    battleaxe,
  };
}

/** Below this share of its bounding rectangle a lot is not rectangle-shaped. */
const MIN_RECT_FILL = 0.6;

/**
 * Shorter and longer side of the minimum-area bounding rectangle, or nulls when
 * the polygon fills less than 60% of it (L-shapes, battleaxe handles). Port of
 * _frontage_depth_obb in services/lot_dimensions.py, so both stacks agree.
 */
function frontageDepthFromRect(
  points: { x: number; y: number }[],
  polygonArea: number
): { frontage: number | null; depth: number | null } {
  const rect = minAreaRect(points);
  if (!rect) return { frontage: null, depth: null };
  const [a, b] = rect;
  if (!(a > 0) || !(b > 0)) return { frontage: null, depth: null };
  if (polygonArea / (a * b) < MIN_RECT_FILL) return { frontage: null, depth: null };
  return { frontage: Math.min(a, b), depth: Math.max(a, b) };
}

/** Andrew's monotone-chain convex hull (counter-clockwise, no repeated point). */
function convexHull(points: { x: number; y: number }[]): { x: number; y: number }[] {
  const seen = new Set<string>();
  const pts = points
    .filter((p) => {
      const k = `${p.x},${p.y}`;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .sort((p, q) => p.x - q.x || p.y - q.y);
  if (pts.length <= 2) return pts;
  const cross = (o: { x: number; y: number }, a: { x: number; y: number }, b: { x: number; y: number }) =>
    (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower: { x: number; y: number }[] = [];
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper: { x: number; y: number }[] = [];
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}

/**
 * Side lengths of the minimum-area bounding rectangle (rotating calipers): the
 * best rectangle always has one side along a hull edge, so try each edge.
 */
function minAreaRect(points: { x: number; y: number }[]): [number, number] | null {
  const hull = convexHull(points);
  const n = hull.length;
  if (n < 3) return null;
  let best: [number, number, number] | null = null; // [area, w, h]
  for (let i = 0; i < n; i++) {
    const a = hull[i];
    const b = hull[(i + 1) % n];
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    if (len === 0) continue;
    const ux = (b.x - a.x) / len;
    const uy = (b.y - a.y) / len;
    const vx = -uy;
    const vy = ux;
    let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity;
    for (const p of hull) {
      const du = p.x * ux + p.y * uy;
      const dv = p.x * vx + p.y * vy;
      minU = Math.min(minU, du); maxU = Math.max(maxU, du);
      minV = Math.min(minV, dv); maxV = Math.max(maxV, dv);
    }
    const w = maxU - minU;
    const h = maxV - minV;
    if (best == null || w * h < best[0]) best = [w * h, w, h];
  }
  return best ? [best[1], best[2]] : null;
}

/**
 * Calculate polygon area using shoelace formula
 */
function calculatePolygonArea(points: { x: number; y: number }[]): number {
  // Remove duplicate closing point if present
  const pts =
    points[0].x === points[points.length - 1].x &&
    points[0].y === points[points.length - 1].y
      ? points.slice(0, -1)
      : points;

  let area = 0;
  for (let i = 0; i < pts.length; i++) {
    const j = (i + 1) % pts.length;
    area += pts[i].x * pts[j].y;
    area -= pts[j].x * pts[i].y;
  }

  return Math.abs(area) / 2;
}

/**
 * Extract boundary segments from polygon points
 */
function extractBoundarySegments(
  points: { x: number; y: number }[]
): BoundarySegment[] {
  // Remove duplicate closing point if present
  const pts =
    points[0].x === points[points.length - 1].x &&
    points[0].y === points[points.length - 1].y
      ? points.slice(0, -1)
      : points;

  const boundaries: BoundarySegment[] = [];

  for (let i = 0; i < pts.length; i++) {
    const start = pts[i];
    const end = pts[(i + 1) % pts.length];

    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const length = Math.sqrt(dx * dx + dy * dy);
    const bearing = (Math.atan2(dx, dy) * (180 / Math.PI) + 360) % 360;

    boundaries.push({
      type: 'unknown',
      length,
      bearing,
      startPoint: start,
      endPoint: end,
    });
  }

  return boundaries;
}

/**
 * Classify boundaries as front, rear, side_left, side_right
 * Based on:
 * - Position relative to centroid
 * - Bearing (roughly N/S vs E/W)
 * - Length patterns (fronts are often shorter than sides)
 */
function classifyBoundaries(boundaries: BoundarySegment[]): void {
  if (boundaries.length === 4) {
    // Rectangular lot - use predictable classification
    // Assume first boundary is front (street-facing), clockwise order
    const types: BoundarySegment['type'][] = [
      'front',
      'side_right',
      'rear',
      'side_left',
    ];
    boundaries.forEach((b, i) => {
      b.type = types[i];
    });
    return;
  }

  // For irregular lots, use bearing-based classification
  // This is a heuristic - real classification would need street data
  const centroidY =
    boundaries.reduce((sum, b) => sum + b.startPoint.y, 0) / boundaries.length;

  for (const boundary of boundaries) {
    const midY = (boundary.startPoint.y + boundary.endPoint.y) / 2;
    const bearing = boundary.bearing;

    // Roughly horizontal boundaries (E-W, bearing 45-135 or 225-315)
    const isHorizontal =
      (bearing >= 45 && bearing < 135) || (bearing >= 225 && bearing < 315);

    if (isHorizontal) {
      // Front is typically the boundary closer to the street (lower Y in most cases)
      boundary.type = midY < centroidY ? 'front' : 'rear';
    } else {
      // Vertical boundaries are sides
      const midX = (boundary.startPoint.x + boundary.endPoint.x) / 2;
      const centroidX =
        boundaries.reduce((sum, b) => sum + b.startPoint.x, 0) /
        boundaries.length;
      boundary.type = midX < centroidX ? 'side_left' : 'side_right';
    }
  }
}

/**
 * Quick utility to get just frontage and depth
 */
export function getLotFrontageAndDepth(
  geometry: LotGeometry
): { frontage: number | null; depth: number | null } | null {
  const dims = calculateLotDimensions(geometry);
  if (!dims) return null;
  return {
    frontage: dims.frontage,
    depth: dims.depth,
  };
}

/**
 * Quick utility to get lot area from geometry
 */
export function getLotAreaFromGeometry(geometry: LotGeometry): number | null {
  const dims = calculateLotDimensions(geometry);
  return dims?.area || null;
}

/**
 * Parse lot area from string (e.g., "450 m²" -> 450)
 */
export function parseLotAreaString(areaString: string | undefined): number | null {
  if (!areaString) return null;
  const match = areaString.match(/([\d,]+\.?\d*)/);
  if (!match) return null;
  return parseFloat(match[1].replace(',', ''));
}
