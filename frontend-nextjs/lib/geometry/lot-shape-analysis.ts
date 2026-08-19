/**
 * Lot Shape Analysis
 *
 * Detects battleaxe lots (flag lots/panhandle lots) from cadastre geometry.
 *
 * Battleaxe signature (NSW Standard Instrument LEP definition):
 * - A lot that relies on a strip of land ("the handle") narrower than
 *   the remainder of the lot to provide access to a road.
 * - Detection is proportion-based: handle must be < 40% of head width.
 *   This covers small suburban battleaxes (3-5m handle) and large rural
 *   ones (e.g. 18-20m handle on a 60m+ lot) equally.
 *
 * NSW SEPP Housing 2021 Requirements:
 * - Minimum access way width: 3m
 * - Minimum main lot dimensions: 12m × 12m (excluding laneway)
 *
 * Algorithm: Width profile analysis
 * 1. Find lot's principal axis (longest dimension)
 * 2. Take perpendicular cross-sections
 * 3. Detect narrow→wide pattern using proportion-based threshold
 */

import { scaleFactorForRing } from './mercator';
import type { LotGeometry } from '@/types/property';

// NSW average latitude for Web Mercator scale correction
// Mercator correction now comes from the ring's own latitude — see ./mercator.

// SEPP Housing 2021 requirements
const MIN_ACCESS_WAY_WIDTH = 3.0; // meters
const MIN_MAIN_LOT_DIMENSION = 12.0; // meters
const MIN_MAIN_LOT_AREA = 144.0; // 12m × 12m in sqm

// Detection thresholds
// Proportion-based: handle must be < 40% of head width (per legislative definition
// of battleaxe as a lot with a handle "narrower than the remainder"). This works
// for both small suburban handles (3-5m on 12-15m lots) and large rural ones.
const HANDLE_TO_HEAD_MAX_RATIO = 0.40;
const MIN_HEAD_WIDTH = 9.0; // Head must be wider than this
const MAX_NARROW_PERCENTAGE = 0.65; // Handle must be <65% of lot length (typically 30-50%, allow up to 60%)
const MIN_WIDTH_RATIO = 0.65; // Handle/head width ratio must be below this

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
  /** Whether lot meets SEPP Housing 2021 minimum requirements */
  meetsMinimumRequirements: boolean;
  /** Specific compliance issues */
  complianceIssues: string[];
  /** Width measurements at each cross-section (for debugging) */
  widthProfile?: number[];
}

export interface LotShapeAnalysis {
  /** Lot shape classification */
  lotType: 'rectangular' | 'battleaxe' | 'irregular';
  /** Battleaxe details if applicable */
  battleaxe?: BattleaxeDetectionResult;
}

interface Point {
  x: number;
  y: number;
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
 * Detect if lot is a battleaxe shape using width profile analysis
 */
export function detectBattleaxeLot(geometry: LotGeometry): BattleaxeDetectionResult {
  const defaultResult: BattleaxeDetectionResult = {
    isBattleaxe: false,
    confidence: 0,
    accessWayWidth: 0,
    accessWayLength: 0,
    mainLotWidth: 0,
    mainLotArea: 0,
    meetsMinimumRequirements: false,
    complianceIssues: [],
  };

  if (!geometry?.rings?.length || !geometry.rings[0]?.length) {
    return defaultResult;
  }

  const coordinates = geometry.rings[0];

  // Convert to real-world meters
  const scaleFactor = scaleFactorForRing(coordinates);
  const points: Point[] = coordinates.map((coord) => ({
    x: coord[0] / scaleFactor,
    y: coord[1] / scaleFactor,
  }));

  // Remove closing point if duplicate
  const polygon = removeClosingPoint(points);

  if (polygon.length < 6) {
    // Battleaxe typically has 6+ vertices (L-shape minimum)
    return defaultResult;
  }

  // Find bounding box and principal axis
  const bbox = getBoundingBox(polygon);
  const isVerticallyOriented = bbox.height > bbox.width;

  // Take cross-sections perpendicular to the longest axis
  const numSlices = 20;
  const widths = measureWidthProfile(polygon, bbox, isVerticallyOriented, numSlices);

  if (widths.length < numSlices) {
    return defaultResult;
  }

  // Analyze width pattern
  const minWidth = Math.min(...widths);
  const maxWidth = Math.max(...widths);
  const widthRatio = minWidth / maxWidth;

  // Proportion-based narrow threshold: handle must be < 40% of head width.
  // Using maxWidth as a proxy for head width at this stage.
  const narrowThreshold = maxWidth * HANDLE_TO_HEAD_MAX_RATIO;

  // Count narrow vs wide sections
  const narrowSlices = widths.filter((w) => w < narrowThreshold).length;
  const narrowPercentage = narrowSlices / widths.length;

  // Battleaxe detection criteria
  const hasNarrowHandle = minWidth < narrowThreshold && minWidth > 0;
  const hasWideHead = maxWidth >= MIN_HEAD_WIDTH;
  const hasSignificantContrast = widthRatio < MIN_WIDTH_RATIO;
  const handleIsMinority = narrowPercentage < MAX_NARROW_PERCENTAGE;
  const hasConsecutiveNarrow = hasConsecutiveNarrowSection(widths, 3, narrowThreshold);

  const isBattleaxe =
    hasNarrowHandle &&
    hasWideHead &&
    hasSignificantContrast &&
    handleIsMinority &&
    hasConsecutiveNarrow;

  if (!isBattleaxe) {
    return { ...defaultResult, widthProfile: widths };
  }

  // Calculate dimensions
  const { handleLength, headLength } = estimateHandleHeadLengths(
    widths,
    isVerticallyOriented ? bbox.height : bbox.width,
    narrowThreshold
  );
  const mainLotArea = estimateMainLotArea(widths, narrowThreshold, headLength);

  // Calculate confidence
  const confidence = calculateConfidence(widths, minWidth, maxWidth, narrowPercentage);

  // Check SEPP compliance
  const complianceIssues: string[] = [];
  if (minWidth < MIN_ACCESS_WAY_WIDTH) {
    complianceIssues.push(
      `Access way width ${minWidth.toFixed(1)}m is below minimum ${MIN_ACCESS_WAY_WIDTH}m`
    );
  }
  if (maxWidth < MIN_MAIN_LOT_DIMENSION) {
    complianceIssues.push(
      `Main lot width ${maxWidth.toFixed(1)}m is below minimum ${MIN_MAIN_LOT_DIMENSION}m`
    );
  }
  if (mainLotArea < MIN_MAIN_LOT_AREA) {
    complianceIssues.push(
      `Main lot area ${mainLotArea.toFixed(0)}m² is below minimum ${MIN_MAIN_LOT_AREA}m²`
    );
  }

  const meetsMinimumRequirements =
    minWidth >= MIN_ACCESS_WAY_WIDTH &&
    maxWidth >= MIN_MAIN_LOT_DIMENSION &&
    mainLotArea >= MIN_MAIN_LOT_AREA;

  return {
    isBattleaxe: true,
    confidence,
    accessWayWidth: Math.round(minWidth * 100) / 100,
    accessWayLength: Math.round(handleLength * 100) / 100,
    mainLotWidth: Math.round(maxWidth * 100) / 100,
    mainLotArea: Math.round(mainLotArea),
    meetsMinimumRequirements,
    complianceIssues,
    widthProfile: widths,
  };
}

/**
 * Remove duplicate closing point from polygon
 */
function removeClosingPoint(points: Point[]): Point[] {
  if (points.length < 2) return points;
  const first = points[0];
  const last = points[points.length - 1];
  if (Math.abs(first.x - last.x) < 0.01 && Math.abs(first.y - last.y) < 0.01) {
    return points.slice(0, -1);
  }
  return points;
}

/**
 * Get bounding box of polygon
 */
function getBoundingBox(points: Point[]): {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  width: number;
  height: number;
} {
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX,
    maxX,
    minY,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

/**
 * Measure width of polygon at regular intervals along principal axis
 */
function measureWidthProfile(
  polygon: Point[],
  bbox: { minX: number; maxX: number; minY: number; maxY: number; width: number; height: number },
  isVertical: boolean,
  numSlices: number
): number[] {
  const widths: number[] = [];

  for (let i = 0; i < numSlices; i++) {
    const t = (i + 0.5) / numSlices; // Center of each slice

    let width: number;
    if (isVertical) {
      // Slice horizontally, measure width
      const y = bbox.minY + t * bbox.height;
      width = measureWidthAtY(polygon, y);
    } else {
      // Slice vertically, measure height
      const x = bbox.minX + t * bbox.width;
      width = measureWidthAtX(polygon, x);
    }

    if (width > 0) {
      widths.push(width);
    }
  }

  return widths;
}

/**
 * Measure polygon width at a specific Y coordinate
 */
function measureWidthAtY(polygon: Point[], y: number): number {
  const intersections: number[] = [];

  for (let i = 0; i < polygon.length; i++) {
    const p1 = polygon[i];
    const p2 = polygon[(i + 1) % polygon.length];

    // Check if edge crosses this Y level
    if ((p1.y <= y && p2.y > y) || (p2.y <= y && p1.y > y)) {
      // Calculate X at intersection
      const t = (y - p1.y) / (p2.y - p1.y);
      const x = p1.x + t * (p2.x - p1.x);
      intersections.push(x);
    }
  }

  if (intersections.length < 2) return 0;

  intersections.sort((a, b) => a - b);
  return intersections[intersections.length - 1] - intersections[0];
}

/**
 * Measure polygon height at a specific X coordinate
 */
function measureWidthAtX(polygon: Point[], x: number): number {
  const intersections: number[] = [];

  for (let i = 0; i < polygon.length; i++) {
    const p1 = polygon[i];
    const p2 = polygon[(i + 1) % polygon.length];

    // Check if edge crosses this X level
    if ((p1.x <= x && p2.x > x) || (p2.x <= x && p1.x > x)) {
      // Calculate Y at intersection
      const t = (x - p1.x) / (p2.x - p1.x);
      const y = p1.y + t * (p2.y - p1.y);
      intersections.push(y);
    }
  }

  if (intersections.length < 2) return 0;

  intersections.sort((a, b) => a - b);
  return intersections[intersections.length - 1] - intersections[0];
}

/**
 * Check if there are consecutive narrow sections (handle pattern)
 */
function hasConsecutiveNarrowSection(widths: number[], minConsecutive: number, threshold: number): boolean {
  let consecutive = 0;
  for (const w of widths) {
    if (w < threshold) {
      consecutive++;
      if (consecutive >= minConsecutive) return true;
    } else {
      consecutive = 0;
    }
  }
  return false;
}

/**
 * Estimate handle and head lengths from width profile
 */
function estimateHandleHeadLengths(
  widths: number[],
  totalLength: number,
  narrowThreshold: number
): { handleLength: number; headLength: number } {
  // The handle is the run of "narrow" slices (width < narrowThreshold) at one end
  // of the principal axis. Use the SAME proportional threshold that battleaxe
  // detection uses — not a fixed width — so wide rural handles (e.g. 16m on a 70m
  // head) are still recognised as the handle rather than collapsing to length 0.
  const isNarrow = (w: number) => w < narrowThreshold;

  let leadingNarrow = 0;
  for (let i = 0; i < widths.length && isNarrow(widths[i]); i++) {
    leadingNarrow++;
  }

  let trailingNarrow = 0;
  for (let i = widths.length - 1; i >= 0 && isNarrow(widths[i]); i--) {
    trailingNarrow++;
  }

  // Handle sits at whichever end the narrow run is longer.
  const handleSlices = Math.max(leadingNarrow, trailingNarrow);
  const handleRatio = handleSlices / widths.length;
  const handleLength = handleRatio * totalLength;
  const headLength = totalLength - handleLength;

  return { handleLength, headLength };
}

/**
 * Estimate main lot area (excluding handle)
 */
function estimateMainLotArea(widths: number[], narrowThreshold: number, headLength: number): number {
  // Average width of the head (non-handle) slices × head length. Filter on the
  // proportional narrowThreshold so handle slices are excluded — otherwise a wide
  // handle inflates both the average width and (via headLength) the area, which
  // previously produced a "main lot" larger than the whole lot.
  const headWidths = widths.filter((w) => w >= narrowThreshold);
  if (headWidths.length === 0) return 0;

  const avgWidth = headWidths.reduce((sum, w) => sum + w, 0) / headWidths.length;
  return avgWidth * headLength;
}

/**
 * Calculate confidence score based on pattern clarity
 */
function calculateConfidence(
  widths: number[],
  minWidth: number,
  maxWidth: number,
  narrowPercentage: number
): number {
  let confidence = 0.5; // Base confidence

  // Stronger contrast = higher confidence
  const widthRatio = minWidth / maxWidth;
  if (widthRatio < 0.3) confidence += 0.2;
  else if (widthRatio < 0.5) confidence += 0.1;

  // Clear narrow section = higher confidence
  if (narrowPercentage < 0.3) confidence += 0.15;
  else if (narrowPercentage < 0.4) confidence += 0.1;

  // Typical battleaxe handle width (3-5m) = higher confidence
  if (minWidth >= 3 && minWidth <= 5) confidence += 0.1;

  // Typical battleaxe head width (10-20m) = higher confidence
  if (maxWidth >= 10 && maxWidth <= 20) confidence += 0.05;

  return Math.min(0.95, confidence);
}
