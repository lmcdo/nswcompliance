/**
 * NSW Planning Portal API integration
 * Handles the 3-step API process: address lookup, layer intersection, and geometry retrieval
 */

export interface PlanningPortalProperty {
  address: string;
  propId: number;
  GURASID: number;
}

export interface PlanningPortalLayer {
  id: string;
  layerName: string;
  results: Array<{
    [key: string]: string;
  }>;
}

export interface PlanningPortalGeometry {
  hasM: boolean;
  hasZ: boolean;
  rings: number[][][];
  spatialReference: {
    wkid: number;
    latestWkid?: number;
    vcsWkid?: number;
    latestVcsWkid?: number;
    wkt?: string;
  };
}

export interface PlanningPortalResponse {
  property: PlanningPortalProperty;
  layers: PlanningPortalLayer[];
  geometry: PlanningPortalGeometry;
}

/**
 * Step 1: Get property ID from address
 */
export async function getPropertyFromAddress(address: string): Promise<PlanningPortalProperty | null> {
  const encodedAddress = encodeURIComponent(address);
  const url = `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a=${encodedAddress}&noOfRecords=1`;
  
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Address lookup failed: ${response.status}`);
    }
    
    const data = await response.json();
    if (!data || data.length === 0) {
      return null;
    }
    
    return data[0] as PlanningPortalProperty;
  } catch (error) {
    console.error('Planning Portal address lookup error:', error);
    return null;
  }
}

/**
 * Step 2: Get planning layers for property
 */
export async function getPlanningLayersForProperty(propId: number): Promise<PlanningPortalLayer[]> {
  const url = `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=${propId}&layers=epi`;
  
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Layer intersection failed: ${response.status}`);
    }
    
    const data = await response.json();
    return data as PlanningPortalLayer[];
  } catch (error) {
    console.error('Planning Portal layer lookup error:', error);
    return [];
  }
}

/**
 * Step 3: Get property geometry
 */
export async function getPropertyGeometry(propId: number): Promise<PlanningPortalGeometry | null> {
  const url = `https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query?where=propid=${propId}&outFields=propid,address,val1_bd,val1_lv,prop_area,zone_desc,urbanity&f=json`;
  
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Geometry lookup failed: ${response.status}`);
    }
    
    const data = await response.json();
    if (!data.features || data.features.length === 0) {
      return null;
    }
    
    return data.features[0].geometry as PlanningPortalGeometry;
  } catch (error) {
    console.error('Planning Portal geometry lookup error:', error);
    return null;
  }
}

/**
 * Complete planning data lookup - executes all 3 API calls
 */
export async function getCompletePlanningData(address: string): Promise<PlanningPortalResponse | null> {
  try {
    // Step 1: Get property info
    const property = await getPropertyFromAddress(address);
    if (!property) {
      console.error('Property not found for address:', address);
      return null;
    }
    
    // Step 2 & 3: Get layers and geometry in parallel
    const [layers, geometry] = await Promise.all([
      getPlanningLayersForProperty(property.propId),
      getPropertyGeometry(property.propId)
    ]);
    
    if (!geometry) {
      console.error('Geometry not found for property:', property.propId);
      return null;
    }
    
    return {
      property,
      layers,
      geometry
    };
  } catch (error) {
    console.error('Complete planning data lookup failed:', error);
    return null;
  }
}

/**
 * Extract key planning information from layer data
 */
export function extractKeyPlanningInfo(layers: PlanningPortalLayer[]) {
  const info: { [key: string]: any } = {};
  
  for (const layer of layers) {
    switch (layer.layerName) {
      case 'Land Zoning Map':
        if (layer.results[0]) {
          info.zone = layer.results[0].Zone;
          info.landUse = layer.results[0]['Land Use'];
          info.lgaName = layer.results[0]['LGA Name'];
        }
        break;
        
      case 'Height of Buildings Map':
        if (layer.results[0]) {
          info.maxHeight = parseFloat(layer.results[0]['Maximum Building Height'] || '0');
          info.heightUnits = layer.results[0].Units;
        }
        break;
        
      case 'Floor Space Ratio Map':
        if (layer.results[0]) {
          info.fsr = parseFloat(layer.results[0]['Floor Space Ratio'] || '0');
        }
        break;
        
      case 'Lot Size Map':
        if (layer.results[0]) {
          info.minLotSize = parseFloat(layer.results[0]['Lot Size'] || '0');
          info.lotSizeUnits = layer.results[0].Units;
        }
        break;
    }
  }
  
  return info;
}