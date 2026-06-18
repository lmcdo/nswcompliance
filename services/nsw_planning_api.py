#!/usr/bin/env python3
"""NSW Government Planning API Integration

Provides property intelligence by integrating with NSW Planning Portal APIs
to get accurate location-specific planning data including zones, height limits,
heritage overlays, and other planning constraints.

API Documentation: nsw_planning_apis.md
"""

import asyncio
import aiohttp
import urllib.parse
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

@dataclass
class PlanningControl:
    """Individual planning control (height, zone, etc.)"""
    layer_name: str
    value: str
    units: Optional[str] = None
    legislative_clause: Optional[str] = None
    epi_name: Optional[str] = None
    lga_name: Optional[str] = None

@dataclass 
class PropertyIntelligence:
    """Complete property intelligence from NSW APIs"""
    address: str
    prop_id: Optional[int] = None
    gurasid: Optional[int] = None
    zone: Optional[PlanningControl] = None
    height_limit: Optional[PlanningControl] = None
    lot_size_req: Optional[PlanningControl] = None
    fsr_limit: Optional[PlanningControl] = None
    land_area: Optional[str] = None
    land_value: Optional[str] = None
    heritage_items: List[PlanningControl] = None
    other_controls: List[PlanningControl] = None
    
    def __post_init__(self):
        if self.heritage_items is None:
            self.heritage_items = []
        if self.other_controls is None:
            self.other_controls = []

class NSWPlanningAPI:
    """NSW Government Planning Portal API Client"""
    
    BASE_URL = "https://api.apps1.nsw.gov.au/planning"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'Origin': 'https://www.planningportal.nsw.gov.au',
                'Referer': 'https://www.planningportal.nsw.gov.au/'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def lookup_property_id(self, address: str) -> Optional[Dict[str, Any]]:
        """Get property ID and basic info from address"""
        if not self.session:
            raise RuntimeError("API client not initialized - use async context manager")
        
        encoded_address = urllib.parse.quote(address)
        url = f"{self.BASE_URL}/viewersf/V1/ePlanningApi/address"
        params = {
            "a": address,  # Don't double-encode - let requests handle it
            "noOfRecords": 1  # Match mapviewer exactly
        }
        
        # Debug: show exact URL being called
        print(f"DEBUG: Calling NSW API URL: {url}?a={urllib.parse.quote(address)}&noOfRecords=1")
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"DEBUG: NSW API response for '{address}': {data}")
                    logger.info(f"NSW API response for '{address}': {data}")
                    if data and len(data) > 0:
                        # GATE-0 (parcel identity): the Portal /address search is
                        # fuzzy — refuse a resolved parcel whose street number/name
                        # does not match the request (fail closed).
                        from services.address_identity import parcel_identity_match
                        _label = data[0].get("address") or ""
                        if not parcel_identity_match(address, _label):
                            logger.warning(
                                "[GATE-0] address identity mismatch — requested %r "
                                "resolved to %r; suppressing (fail-closed)", address, _label
                            )
                            return None
                        print(f"DEBUG: Found {len(data)} properties. First result: address='{data[0].get('address')}', propId={data[0].get('propId')}")
                        logger.info(f"Found {len(data)} properties. First result: address='{data[0].get('address')}', propId={data[0].get('propId')}")
                        return data  # Return all results for coordinate validation
                    else:
                        logger.warning(f"No property found for address: {address}")
                        return None
                else:
                    logger.error(f"Address lookup failed: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Address lookup error: {e}")
            return None
    
    async def lookup_property_by_coordinates(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """Get property ID from coordinates (more accurate)"""
        if not self.session:
            raise RuntimeError("API client not initialized - use async context manager")
        
        url = f"{self.BASE_URL}/viewersf/V1/ePlanningApi/address"
        params = {
            "lat": lat,
            "lng": lng,
            "noOfRecords": 1
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"DEBUG: Coordinate lookup response for {lat},{lng}: {data}")
                    if data and len(data) > 0:
                        logger.info(f"Found property by coordinates: {data[0].get('address')} (ID: {data[0].get('propId')})")
                        return data
                    else:
                        print(f"DEBUG: No property found at coordinates: {lat}, {lng}")
                        logger.warning(f"No property found at coordinates: {lat}, {lng}")
                        return None
                else:
                    print(f"DEBUG: Coordinate lookup failed: HTTP {response.status}")
                    logger.error(f"Coordinate lookup failed: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Coordinate lookup error: {e}")
            return None
    
    async def get_planning_controls(self, prop_id: int) -> List[Dict[str, Any]]:
        """Get all planning controls for a property"""
        if not self.session:
            raise RuntimeError("API client not initialized - use async context manager")
        
        url = f"{self.BASE_URL}/viewersf/V1/ePlanningApi/layerintersect"
        params = {
            "type": "property",
            "id": prop_id,
            "layers": "epi"  # Environmental Planning Instrument layers
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.error(f"Planning controls lookup failed: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Planning controls error: {e}")
            return []
    
    async def get_lot_data(self, prop_id: int) -> List[Dict[str, Any]]:
        """Get lot data including geometry (like map viewer)"""
        if not self.session:
            raise RuntimeError("API client not initialized - use async context manager")
        
        url = f"{self.BASE_URL}/viewersf/V1/ePlanningApi/lot"
        params = {"propId": prop_id}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.error(f"Lot data lookup failed: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Lot data error: {e}")
            return []
    
    async def get_valuation_data(self, prop_id: int) -> Optional[Dict[str, Any]]:
        """Get valuation data including land area and value from NSW Valuation service"""
        if not self.session:
            raise RuntimeError("API client not initialized - use async context manager")
        
        # Use the correct NSW valuation endpoint from HAR file
        url = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query"
        params = {
            "where": f"propid={prop_id}",
            "outFields": "propid,address,val1_bd,val1_lv,prop_area,zone_desc,urbanity",
            "f": "json"
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    # Handle potential content-type issues by getting text first
                    response_text = await response.text()
                    try:
                        import json
                        data = json.loads(response_text)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON response: {response_text[:200]}")
                        return None
                    
                    # Extract valuation data from features
                    if isinstance(data, dict) and 'features' in data and data['features']:
                        feature = data['features'][0]
                        attributes = feature.get('attributes', {})
                        return {
                            'land_area': attributes.get('prop_area'),
                            'land_value': attributes.get('val1_lv')
                        }
                    return None
                else:
                    logger.error(f"Valuation data lookup failed: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Valuation data error: {e}")
            return None
    
    async def get_property_intelligence(self, address: str, google_coords: Optional[Dict[str, float]] = None) -> PropertyIntelligence:
        """Get complete property intelligence from NSW APIs using map viewer approach"""
        
        # Step 1: Try multiple address formats for NSW API
        logger.info(f"Trying multiple address formats for: {address}")
        
        # Try original address first
        prop_results = await self.lookup_property_id(address)
        print(f"DEBUG: Original address '{address}' found: {bool(prop_results)}")
        
        # If that fails, try variations
        if not prop_results:
            # Try without full postal part
            short_address = address.replace(", Australia", "").strip()
            prop_results = await self.lookup_property_id(short_address)
            print(f"DEBUG: Short address '{short_address}' found: {bool(prop_results)}")
            
        if not prop_results:
            # Try just street + suburb
            parts = address.split(",")
            if len(parts) >= 3:
                street_suburb = f"{parts[0].strip()}, {parts[1].strip()}"
                prop_results = await self.lookup_property_id(street_suburb)
                print(f"DEBUG: Street+suburb '{street_suburb}' found: {bool(prop_results)}")
                
        print(f"DEBUG: Final address search results: {prop_results}")
        
        # Check if address lookup returned wrong results, use coordinates as primary if so
        if prop_results and google_coords:
            # Check if any returned address actually matches what we're looking for
            address_match_found = False
            search_parts = address.upper().split()
            street_number = search_parts[0] if search_parts else ""
            street_name_words = set(word for word in search_parts[1:3] if word and word not in ['ST', 'STREET', 'RD', 'ROAD', 'AVE', 'AVENUE'])
            suburb_words = set(word for word in search_parts if word not in ['NSW', 'AUSTRALIA', 'ST', 'STREET', 'RD', 'ROAD'])
            
            print(f"DEBUG: Looking for street number: {street_number}, street words: {street_name_words}, in search: {address}")
            
            for result in prop_results:
                result_addr = result.get('address', '').upper()
                print(f"DEBUG: Checking result: {result_addr}")
                
                # Check if street number and key words match
                if street_number and street_number in result_addr:
                    # Check if key street name words appear
                    if any(word in result_addr for word in street_name_words):
                        print(f"DEBUG: Found match! {result_addr}")
                        address_match_found = True
                        # Use this specific result instead of first
                        prop_results = [result]
                        break
            
            if not address_match_found:
                print(f"DEBUG: NSW API returned wrong addresses, trying coordinate lookup")
                lat, lng = google_coords['lat'], google_coords['lng']
                logger.info(f"Address lookup returned wrong results, using coordinate lookup: {lat}, {lng}")
                print(f"DEBUG: About to call lookup_property_by_coordinates({lat}, {lng})")
                coord_results = await self.lookup_property_by_coordinates(lat, lng)
                print(f"DEBUG: lookup_property_by_coordinates returned: {coord_results}")
                if coord_results:
                    print(f"DEBUG: Coordinate lookup returned: {coord_results}")
                    prop_results = coord_results
        
        # If still no results and we have coordinates, try coordinate lookup as final fallback
        elif not prop_results and google_coords:
            try:
                lat, lng = google_coords['lat'], google_coords['lng']
                logger.info(f"Address lookup failed, trying coordinate fallback: {lat}, {lng}")
                prop_results = await self.lookup_property_by_coordinates(lat, lng)
            except Exception as e:
                logger.warning(f"Coordinate fallback also failed: {e}")
                prop_results = None
        if not prop_results:
            return PropertyIntelligence(address=address)
        
        # Take first result like map viewer does
        first_prop = prop_results[0] if isinstance(prop_results, list) else prop_results
        
        prop_id = first_prop.get("propId")
        gurasid = first_prop.get("GURASID")
        
        if not prop_id:
            return PropertyIntelligence(
                address=address,
                gurasid=gurasid
            )
        
        # Step 2: Get planning controls, lot data, and valuation data (like map viewer)
        controls_data = await self.get_planning_controls(prop_id)
        print(f"DEBUG: Planning controls for propId {prop_id}: {controls_data}")
        lot_data = await self.get_lot_data(prop_id)
        valuation_data = await self.get_valuation_data(prop_id)
        
        # Step 3: Parse and categorize controls
        intelligence = PropertyIntelligence(
            address=address,
            prop_id=prop_id,
            gurasid=gurasid
        )
        
        # Populate valuation data
        if valuation_data:
            intelligence.land_area = valuation_data.get('land_area')
            intelligence.land_value = valuation_data.get('land_value')
        
        for control in controls_data:
            layer_name = control.get("layerName") or ""
            results = control.get("results") or []
            
            for result in results:
                planning_control = PlanningControl(
                    layer_name=layer_name,
                    value=self._extract_primary_value(result),
                    units=result.get("Units"),
                    legislative_clause=result.get("Legislative Clause"),
                    epi_name=result.get("EPI Name"),
                    lga_name=result.get("LGA Name")
                )
                
                # Categorize by layer type
                if "height" in layer_name.lower():
                    intelligence.height_limit = planning_control
                elif "zoning" in layer_name.lower() or "zone" in layer_name.lower():
                    intelligence.zone = planning_control
                elif "lot size" in layer_name.lower():
                    intelligence.lot_size_req = planning_control
                elif "floor space" in layer_name.lower() or "fsr" in layer_name.lower():
                    intelligence.fsr_limit = planning_control
                elif "heritage" in layer_name.lower():
                    intelligence.heritage_items.append(planning_control)
                else:
                    intelligence.other_controls.append(planning_control)
        
        return intelligence
    
    def _extract_primary_value(self, result: Dict[str, Any]) -> str:
        """Extract the primary value from a planning control result"""
        # Try common field names in order of preference
        # For FSR, prefer "title" field which contains the ratio format (e.g., "0.6:1")
        for field in ["Maximum Building Height", "Zone", "Lot Size", "title", "Floor Space Ratio", "FSR", "Heritage", "Value"]:
            if field in result:
                return str(result[field])
        
        # If no standard field found, try to find any meaningful value
        for key, value in result.items():
            if key not in ["Units", "Legislative Clause", "EPI Name", "LGA Name", "Amendment", "Commenced Date", "Currency Date", "Published Date"] and value:
                return str(value)
        
        return "Not specified"
    
    def _select_property_by_coordinates(self, candidates: List[Dict[str, Any]], google_coords: Dict[str, float]) -> Dict[str, Any]:
        """Select the property candidate closest to Google Maps coordinates"""
        import math
        
        def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            """Calculate distance between two coordinates using Haversine formula"""
            R = 6371  # Earth's radius in kilometers
            
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            return R * c
        
        google_lat = google_coords.get('lat')
        google_lng = google_coords.get('lng')
        
        if not google_lat or not google_lng:
            return candidates[0]  # Fallback to first result
        
        best_candidate = candidates[0]
        min_distance = float('inf')
        
        logger.info(f"Selecting property from {len(candidates)} candidates using coordinates")
        logger.info(f"Google coordinates: {google_lat}, {google_lng}")
        
        for candidate in candidates:
            candidate_address = candidate.get('address', '')
            # For now, return first candidate - we'd need to get coordinates for each candidate
            # This is a simplified implementation
            logger.info(f"Candidate: {candidate_address} (PropID: {candidate.get('propId')})")
        
        # TODO: Get coordinates for each candidate property and calculate distances
        # For now, return first candidate as fallback
        logger.info(f"Selected property: {best_candidate.get('address')} (PropID: {best_candidate.get('propId')})")
        return best_candidate
    
    def _find_best_address_match(self, search_address: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the best matching address from multiple results"""
        if len(results) == 1:
            return results[0]
        
        # Normalize search address for comparison
        search_normalized = self._normalize_address(search_address)
        
        # Score each result
        best_match = results[0]
        best_score = 0
        
        for result in results:
            result_address = result.get("address", "")
            result_normalized = self._normalize_address(result_address)
            
            # Calculate similarity score
            score = self._calculate_address_similarity(search_normalized, result_normalized)
            
            if score > best_score:
                best_score = score
                best_match = result
        
        return best_match
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address for comparison"""
        return address.upper().replace(",", "").replace("  ", " ").strip()
    
    def _calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate similarity between two normalized addresses"""
        words1 = set(addr1.split())
        words2 = set(addr2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0


# Convenience functions for direct use
async def get_property_intelligence(address: str, google_coords: Optional[Dict[str, float]] = None) -> PropertyIntelligence:
    """Get property intelligence for an address with optional Google coordinates"""
    async with NSWPlanningAPI() as api:
        return await api.get_property_intelligence(address, google_coords)

async def test_nsw_api():
    """Test function to verify NSW API integration"""
    test_addresses = [
        "45 Liverpool Street, Ashfield NSW 2131",
        "15 Norton Street, Leichhardt NSW 2040", 
        "5 Carlyle St, Wollstonecraft NSW 2065"
    ]
    
    for address in test_addresses:
        print(f"\nTesting: {address}")
        intelligence = await get_property_intelligence(address)
        
        print(f"  PropID: {intelligence.prop_id}")
        if intelligence.zone:
            print(f"  Zone: {intelligence.zone.value} ({intelligence.zone.epi_name})")
        if intelligence.height_limit:
            print(f"  Height: {intelligence.height_limit.value} {intelligence.height_limit.units or ''}")
        if intelligence.heritage_items:
            print(f"  Heritage: {len(intelligence.heritage_items)} items")

if __name__ == "__main__":
    asyncio.run(test_nsw_api())