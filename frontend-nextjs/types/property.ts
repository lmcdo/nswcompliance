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

export interface PropertyIntelligenceResponse {
  success: boolean;
  property: PropertyData | null;
  lotGeometry: LotGeometry | null;
  error?: string;
  processing_time_ms?: number;
}