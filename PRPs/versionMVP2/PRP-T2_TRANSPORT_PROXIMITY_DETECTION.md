# PRP-T2: Transport Proximity Detection & Autocomplete System

## Overview
Implement automated transport proximity detection with intelligent autocomplete for TOD development assessments.

## Technical Requirements

### T2.1 Transport Proximity Engine
- **File**: `services/transport_proximity_detector.py`
- **Functionality**: Detect and classify transport infrastructure near properties
- **Data Sources**:
  - NSW Planning Portal transport layers
  - TfNSW GTFS feeds for real-time schedules
  - OpenStreetMap transport infrastructure
  - Cached proximity database for performance

### T2.2 Detection Categories
- **Heavy Rail**: Train stations with distance and frequency data
- **Light Rail**: Tram/light rail stops with service frequency
- **Bus Services**: Bus stops with route frequency analysis
- **Active Transport**: Bike paths, walking infrastructure
- **Future Transport**: Planned infrastructure from TfNSW

### T2.3 Autocomplete System
- **File**: `frontend-nextjs/components/tod/TransportAutocomplete.tsx`
- **Features**:
  - Real-time transport service suggestions
  - Smart filtering by transport type and frequency
  - Visual distance indicators (color-coded)
  - Confidence scoring for proximity data

### T2.4 Caching Strategy
- **Performance**: Sub-200ms response for cached queries
- **Storage**: PostgreSQL transport_proximity table
- **Refresh**: Daily sync with TfNSW GTFS feeds
- **Fallback**: Manual proximity entry if detection fails

## Verification Criteria

### V2.1 Detection Accuracy
- Correctly identify transport within 1km radius
- Accurate distance calculations (±10m tolerance)
- Proper frequency classification (high/medium/low)
- Handle multiple transport types per property

### V2.2 Autocomplete Performance
- Results appear within 150ms of typing
- Relevant suggestions ranked by proximity and frequency
- Clear visual indicators for transport quality
- Graceful handling of no results

### V2.3 Data Quality
- Successfully sync with TfNSW GTFS data
- Handle service disruptions and changes
- Maintain 95%+ uptime for proximity detection
- Accurate caching with proper invalidation

## Implementation Steps

1. Create transport_proximity_detector.py with basic distance calculation
2. Integrate NSW Planning Portal transport layer queries
3. Build TransportAutocomplete component with fuzzy search
4. Implement caching layer with PostgreSQL storage
5. Add TfNSW GTFS feed integration for live data
6. Create comprehensive test suite with mock data

## API Integration Points

### NSW Planning Portal
```python
# Transport layer query
layers = [
    'Heavy Rail',
    'Light Rail',
    'Bus Routes',
    'Cycling Infrastructure',
    'Future Transport'
]
```

### TfNSW GTFS Integration
```python
# Service frequency analysis
def get_service_frequency(stop_id: str, time_window: str = 'peak') -> dict:
    # Returns frequency classification and next service times
    pass
```

## Database Schema

```sql
CREATE TABLE transport_proximity (
    id SERIAL PRIMARY KEY,
    property_id INTEGER,
    transport_type VARCHAR(50),
    stop_name VARCHAR(200),
    distance_meters INTEGER,
    service_frequency VARCHAR(20),
    confidence_score DECIMAL(3,2),
    last_updated TIMESTAMP DEFAULT NOW()
);
```

## Success Metrics
- 95% accuracy in transport proximity detection
- Sub-150ms autocomplete response times
- Successfully processes 1000+ properties per hour
- 99% uptime for proximity detection service

## Timeline
- Core detection engine: 2 days
- NSW Planning Portal integration: 1 day
- Autocomplete UI component: 2 days
- Caching and optimization: 1 day
- GTFS integration: 2 days
- Total: 8 days