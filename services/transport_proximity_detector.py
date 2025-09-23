#!/usr/bin/env python3
"""
Transport Proximity Detection Service
Detects and classifies transport infrastructure near properties
"""

import json
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TransportService:
    """Transport service data model"""
    type: str  # heavy_rail, light_rail, bus, ferry
    name: str
    stop_name: str
    distance: int  # meters
    latitude: float
    longitude: float
    frequency: str  # high, medium, low
    routes: List[str] = None
    confidence_score: float = 0.95

class TransportProximityDetector:
    """Detects transport services near properties"""

    # NSW major transport hubs (sample data for MVP)
    TRANSPORT_HUBS = [
        # Heavy Rail
        {"type": "heavy_rail", "name": "Chatswood Station", "lat": -33.7969, "lng": 151.1846, "frequency": "high"},
        {"type": "heavy_rail", "name": "North Sydney Station", "lat": -33.8416, "lng": 151.2067, "frequency": "high"},
        {"type": "heavy_rail", "name": "Burwood Station", "lat": -33.8777, "lng": 151.1044, "frequency": "high"},
        {"type": "heavy_rail", "name": "Strathfield Station", "lat": -33.8716, "lng": 151.0935, "frequency": "high"},
        {"type": "heavy_rail", "name": "Parramatta Station", "lat": -33.8151, "lng": 151.0041, "frequency": "high"},
        {"type": "heavy_rail", "name": "Central Station", "lat": -33.8823, "lng": 151.2062, "frequency": "high"},
        {"type": "heavy_rail", "name": "Town Hall Station", "lat": -33.8736, "lng": 151.2070, "frequency": "high"},
        {"type": "heavy_rail", "name": "Wynyard Station", "lat": -33.8657, "lng": 151.2061, "frequency": "high"},
        {"type": "heavy_rail", "name": "Circular Quay Station", "lat": -33.8616, "lng": 151.2111, "frequency": "high"},

        # Light Rail
        {"type": "light_rail", "name": "Dulwich Hill Light Rail", "lat": -33.9111, "lng": 151.1403, "frequency": "medium"},
        {"type": "light_rail", "name": "Central Light Rail", "lat": -33.8823, "lng": 151.2062, "frequency": "high"},
        {"type": "light_rail", "name": "Circular Quay Light Rail", "lat": -33.8616, "lng": 151.2111, "frequency": "high"},
        {"type": "light_rail", "name": "Moore Park Light Rail", "lat": -33.8928, "lng": 151.2234, "frequency": "medium"},

        # Bus (Major interchanges)
        {"type": "bus", "name": "Chatswood Interchange", "lat": -33.7969, "lng": 151.1846, "frequency": "high"},
        {"type": "bus", "name": "Bondi Junction Interchange", "lat": -33.8920, "lng": 151.2469, "frequency": "high"},
        {"type": "bus", "name": "Wynyard Bus Terminal", "lat": -33.8657, "lng": 151.2061, "frequency": "high"},
        {"type": "bus", "name": "QVB Bus Stop", "lat": -33.8717, "lng": 151.2067, "frequency": "high"},

        # Ferry
        {"type": "ferry", "name": "Circular Quay Ferry Terminal", "lat": -33.8616, "lng": 151.2111, "frequency": "high"},
        {"type": "ferry", "name": "Manly Wharf", "lat": -33.7981, "lng": 151.2845, "frequency": "high"},
        {"type": "ferry", "name": "Parramatta Ferry Wharf", "lat": -33.8151, "lng": 151.0041, "frequency": "medium"},
    ]

    def __init__(self):
        """Initialize transport proximity detector"""
        self.cache = {}

    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in meters
        """
        R = 6371000  # Earth's radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)

        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def detect_nearby_transport(self, latitude: float, longitude: float, radius: int = 1000) -> List[TransportService]:
        """
        Detect transport services within radius of given coordinates

        Args:
            latitude: Property latitude
            longitude: Property longitude
            radius: Search radius in meters (default 1000m)

        Returns:
            List of nearby transport services
        """
        cache_key = f"{latitude:.5f},{longitude:.5f},{radius}"

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        nearby_services = []

        for hub in self.TRANSPORT_HUBS:
            distance = self.calculate_distance(latitude, longitude, hub['lat'], hub['lng'])

            if distance <= radius:
                service = TransportService(
                    type=hub['type'],
                    name=hub['name'],
                    stop_name=hub['name'],
                    distance=int(distance),
                    latitude=hub['lat'],
                    longitude=hub['lng'],
                    frequency=hub['frequency']
                )
                nearby_services.append(service)

        # Sort by distance
        nearby_services.sort(key=lambda x: x.distance)

        # Cache result
        self.cache[cache_key] = nearby_services

        return nearby_services

    def get_service_frequency(self, stop_id: str, time_window: str = 'peak') -> Dict:
        """
        Get service frequency for a transport stop

        Args:
            stop_id: Transport stop identifier
            time_window: Time period (peak, off-peak, weekend)

        Returns:
            Service frequency information
        """
        # Mock data for MVP - would integrate with TfNSW GTFS in production
        frequency_data = {
            'peak': {
                'heavy_rail': {'services_per_hour': 12, 'average_wait': 5},
                'light_rail': {'services_per_hour': 8, 'average_wait': 7.5},
                'bus': {'services_per_hour': 6, 'average_wait': 10},
                'ferry': {'services_per_hour': 4, 'average_wait': 15}
            },
            'off-peak': {
                'heavy_rail': {'services_per_hour': 6, 'average_wait': 10},
                'light_rail': {'services_per_hour': 4, 'average_wait': 15},
                'bus': {'services_per_hour': 3, 'average_wait': 20},
                'ferry': {'services_per_hour': 2, 'average_wait': 30}
            }
        }

        # Default to peak frequencies
        return frequency_data.get(time_window, frequency_data['peak'])

    def classify_transport_access(self, services: List[TransportService]) -> str:
        """
        Classify overall transport access level

        Args:
            services: List of nearby transport services

        Returns:
            Access level: premium, high, medium, standard, low
        """
        if not services:
            return 'low'

        # Check for premium access (heavy rail within 400m + high frequency bus)
        has_close_heavy_rail = any(
            s.type == 'heavy_rail' and s.distance <= 400
            for s in services
        )
        has_high_freq_bus = any(
            s.type == 'bus' and s.frequency == 'high' and s.distance <= 400
            for s in services
        )

        if has_close_heavy_rail and has_high_freq_bus:
            return 'premium'

        # Check for high access (heavy rail within 800m OR light rail within 400m)
        has_heavy_rail = any(
            s.type == 'heavy_rail' and s.distance <= 800
            for s in services
        )
        has_close_light_rail = any(
            s.type == 'light_rail' and s.distance <= 400
            for s in services
        )

        if has_heavy_rail or has_close_light_rail:
            return 'high'

        # Check for medium access (high frequency bus within 400m)
        if has_high_freq_bus:
            return 'medium'

        # Check for standard access (any bus within 800m)
        has_bus = any(
            s.type == 'bus' and s.distance <= 800
            for s in services
        )

        if has_bus:
            return 'standard'

        return 'low'

    def get_transport_summary(self, latitude: float, longitude: float) -> Dict:
        """
        Get comprehensive transport summary for a location

        Args:
            latitude: Property latitude
            longitude: Property longitude

        Returns:
            Transport summary with services and classification
        """
        services = self.detect_nearby_transport(latitude, longitude)

        summary = {
            'location': {
                'latitude': latitude,
                'longitude': longitude
            },
            'transport_services': [
                {
                    'type': s.type,
                    'name': s.name,
                    'distance': s.distance,
                    'frequency': s.frequency,
                    'confidence': s.confidence_score
                } for s in services
            ],
            'access_level': self.classify_transport_access(services),
            'service_count': len(services),
            'closest_service': None,
            'has_heavy_rail': any(s.type == 'heavy_rail' for s in services),
            'has_light_rail': any(s.type == 'light_rail' for s in services),
            'has_bus': any(s.type == 'bus' for s in services),
            'has_ferry': any(s.type == 'ferry' for s in services),
            'timestamp': datetime.now().isoformat()
        }

        if services:
            closest = services[0]
            summary['closest_service'] = {
                'type': closest.type,
                'name': closest.name,
                'distance': closest.distance,
                'frequency': closest.frequency
            }

        return summary

# CLI interface for testing
if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Transport Proximity Detection')
    parser.add_argument('--lat', type=float, help='Latitude')
    parser.add_argument('--lng', type=float, help='Longitude')
    parser.add_argument('--radius', type=int, default=1000, help='Search radius in meters')
    parser.add_argument('--format', default='json', choices=['json', 'text'], help='Output format')

    args = parser.parse_args()

    if not args.lat or not args.lng:
        # Default to Chatswood for testing
        args.lat = -33.7969
        args.lng = 151.1846

    detector = TransportProximityDetector()
    summary = detector.get_transport_summary(args.lat, args.lng)

    if args.format == 'json':
        print(json.dumps(summary, indent=2))
    else:
        print(f"Transport Access Summary for ({args.lat}, {args.lng})")
        print(f"Access Level: {summary['access_level'].upper()}")
        print(f"Total Services Found: {summary['service_count']}")

        if summary['closest_service']:
            print(f"\nClosest Service:")
            print(f"  {summary['closest_service']['name']}")
            print(f"  Type: {summary['closest_service']['type']}")
            print(f"  Distance: {summary['closest_service']['distance']}m")
            print(f"  Frequency: {summary['closest_service']['frequency']}")

        if summary['transport_services']:
            print(f"\nAll Services:")
            for service in summary['transport_services']:
                print(f"  - {service['name']}: {service['distance']}m ({service['type']})")