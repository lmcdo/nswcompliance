// types/property.ts
export interface PropertyData {
 address: string;
 prop_id: number | null;
 gurasid?: number;
 zone: string | null;
 height_limit: number | null;
 height_units?: string;
 fsr_limit: number | null;
 land_area?: number;
 land_value?: string;
 heritage_status?: string;
 heritage_overlays?: string[];
 lga_name?: string;
 applicable_lep?: string;
 coordinates?: {
 lat: number;
 lng: number;
 };
 /** API availability status for fallback handling */
 api_status?: 'available' | 'unavailable';
}

export interface LotGeometry {
 hasM: boolean;
 hasZ: boolean;
 rings: number[][][]; // NSW format: rings[0][0] = [x,y] coordinate pair
 spatialReference: {
 wkid: number;
 latestWkid?: number | null;
 vcsWkid?: number | null;
 latestVcsWkid?: number | null;
 wkt?: string | null;
 };
}

export interface LotData {
 geometry: LotGeometry;
 attributes: {
 CADID: number;
 LotDescription: string;
 };
}

export interface PlanningControl {
 layer_name: string;
 value: string;
 units?: string;
 legislative_clause?: string;
 epi_name?: string;
 lga_name?: string;
}

export interface PropertyIntelligenceRequest {
 address: string;
 lat?: number;
 lng?: number;
}

export interface LotDimensions {
 area: number;
 /** Shorter side of the best-fit rectangle; null when the lot is too irregular. */
 frontage: number | null;
 /** Longer side of the best-fit rectangle; null with frontage. */
 depth: number | null;
 boundaries: BoundarySegment[];
 confidence: number;
 notes: string[];
}

export interface BoundarySegment {
 type: 'front' | 'rear' | 'side_left' | 'side_right' | 'unknown';
 length: number;
 bearing: number;
 startPoint: { x: number; y: number };
 endPoint: { x: number; y: number };
}

export interface CornerLotInfo {
  /** Whether lot is a corner lot (2+ adjacent roads); null when the road map did not answer (not checked). */
  isCornerLot: boolean | null;
  /** Names of adjacent roads */
  adjacentRoads: string[];
  /** Number of distinct road boundaries; null when not checked. */
  roadCount: number | null;
  /** Confidence in detection (1.0 if API returned data, null if not checked) */
  confidence: number | null;
  /** Error message if detection failed */
  error?: string;
  /** Street edges per named road and the lot's width range back from each (lib/geometry/street-frontage.ts). */
  streetFrontage?: import('@/lib/geometry/street-frontage').StreetFrontage;
}

export interface PropertyIntelligenceResponse {
 success: boolean;
 property: PropertyData | null;
 lotGeometry: LotGeometry | null;
 lot_description?: string | null;   // e.g. "Lot 1 SP 87654" or "Lot 12 DP 123456"
 lotDimensions?: LotDimensions | null;
 cornerLot?: CornerLotInfo | null;
 error?: string;
 warning?: string;
 processing_time_ms?: number;
}