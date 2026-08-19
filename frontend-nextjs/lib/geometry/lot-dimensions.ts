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
  /** Primary frontage width in meters */
  frontage: number;
  /** Average depth (side boundary length) in meters */
  depth: number;
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

  // Extract key dimensions
  const frontBoundary = boundaries.find((b) => b.type === 'front');
  const rearBoundary = boundaries.find((b) => b.type === 'rear');
  const leftSide = boundaries.find((b) => b.type === 'side_left');
  const rightSide = boundaries.find((b) => b.type === 'side_right');

  // Frontage is the front boundary length
  const frontage = frontBoundary?.length || 0;

  // Depth is average of side boundaries
  const sideLeft = leftSide?.length || 0;
  const sideRight = rightSide?.length || 0;
  const depth = sideLeft && sideRight ? (sideLeft + sideRight) / 2 : sideLeft || sideRight;

  // Confidence based on how well we could classify boundaries
  let confidence = 0.9;
  if (!frontBoundary) {
    confidence -= 0.2;
    notes.push('Could not identify front boundary');
  }
  if (!leftSide || !rightSide) {
    confidence -= 0.1;
    notes.push('Could not identify both side boundaries');
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
    frontage: Math.round(frontage * 100) / 100,
    depth: Math.round(depth * 100) / 100,
    boundaries,
    confidence: Math.max(0.5, confidence),
    notes,
    lotType,
    battleaxe,
  };
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
): { frontage: number; depth: number } | null {
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
