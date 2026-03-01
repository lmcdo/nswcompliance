# General DCP Provisions - Category Schema
**For Option A Extraction**
**Date**: 2025-10-29

## Purpose
Define comprehensive categories for extracting structured requirements from general DCP provisions (Parts 2, 4, 7, 8, etc.) across all zones and development types.

---

## Category Naming Convention

Format: `{topic}_{context}_{zone/devtype}` (optional zone/devtype suffix)

Examples:
- `setback_front` - General front setback (all zones)
- `setback_front_r2` - Front setback specific to R2 zone
- `parking_dwelling` - Parking for dwelling houses
- `parking_multi_dwelling` - Parking for multi-dwelling development

---

## Core Categories (Universal)

### Building Envelope & Form
```
setback_front              - Front building setback from street
setback_front_r2           - Front setback R2 zone specific
setback_front_r3           - Front setback R3 zone specific
setback_front_b1           - Front setback B1 zone specific
setback_side               - Side building setbacks
setback_side_r2            - Side setback R2 specific
setback_rear               - Rear building setbacks
setback_rear_r2            - Rear setback R2 specific
building_height            - Building height controls
building_height_r2         - Height controls R2 specific
building_depth             - Maximum building depth
building_width             - Building width controls
floor_space_ratio          - FSR controls
fsr_r2                     - FSR for R2 zone
site_coverage              - Maximum site coverage percentage
building_articulation      - Building articulation and modulation
building_materials         - Materials and finishes
building_bulk              - Bulk and scale controls
```

### Parking & Access
```
parking_residential        - General residential parking
parking_dwelling           - Dwelling house parking (R2)
parking_multi_dwelling     - Multi-dwelling parking
parking_visitor            - Visitor parking requirements
parking_commercial         - Commercial parking rates
parking_retail             - Retail parking rates
parking_bicycle            - Bicycle parking requirements
parking_accessible         - Accessible parking spaces
parking_design             - Parking layout and design
parking_location           - Parking location on site
driveway_width             - Driveway width requirements
driveway_grade             - Driveway gradient limits
access_vehicle             - Vehicular access requirements
access_pedestrian          - Pedestrian access
```

### Landscaping & Open Space
```
landscaping_front_yard     - Front yard landscaping
landscaping_rear_yard      - Rear yard landscaping
landscaping_deep_soil      - Deep soil planting requirements
landscaping_canopy         - Tree canopy coverage
open_space_private         - Private open space per dwelling
open_space_communal        - Communal open space requirements
open_space_usable          - Usable open space dimensions
garden_retention           - Retention of existing gardens/trees
tree_removal               - Tree removal controls
planting_species           - Plant species requirements
```

### Privacy & Solar Access
```
privacy_windows            - Window placement for privacy
privacy_balconies          - Balcony privacy requirements
privacy_screening          - Privacy screening requirements
privacy_setbacks           - Privacy-related setbacks
solar_access_neighbours    - Solar access to neighbouring properties
solar_access_own           - Solar access to own dwelling
solar_access_hours         - Solar access duration requirements (e.g., 3 hours mid-winter)
overshadowing              - Overshadowing controls
```

### Environmental & Sustainability
```
water_efficiency           - Water efficiency requirements
water_basix                - BASIX water targets
water_tanks                - Rainwater tank requirements
stormwater_management      - Stormwater management
stormwater_detention       - Detention requirements
energy_efficiency          - Energy efficiency standards
energy_basix               - BASIX energy targets
energy_solar_panels        - Solar panel requirements
biodiversity               - Biodiversity protection
contamination              - Contaminated land controls
flooding                   - Flood-prone land controls
bushfire                   - Bushfire hazard controls
```

### Design & Character
```
character_streetscape      - Streetscape character
character_architectural    - Architectural character
character_heritage         - Heritage character (non-HCA)
design_excellence          - Design excellence requirements
design_principles          - General design principles
streetscape_contribution   - Contribution to street character
fencing_front              - Front fence height/design
fencing_side               - Side fence requirements
fencing_materials          - Fence materials and style
```

### Built Form - Residential Specific
```
dwelling_type_detached     - Detached dwelling controls
dwelling_type_semi         - Semi-detached dwelling controls
dwelling_type_terrace      - Terrace dwelling controls
dwelling_type_dual_occ     - Dual occupancy controls
dwelling_design_contemp    - Contemporary dwelling design
dwelling_design_period     - Period dwelling controls (Victorian, Federation, etc.)
dwelling_size_min          - Minimum dwelling size
dwelling_rooms_min         - Minimum room requirements
dwelling_ceiling_height    - Ceiling height requirements
dormer_windows             - Dormer window controls
garage_location            - Garage location and design
garage_doors               - Garage door design
```

### Commercial/Mixed Use
```
commercial_frontage        - Commercial frontage requirements
commercial_awnings         - Awning requirements
commercial_signage         - Signage controls
commercial_loading         - Loading dock requirements
commercial_hours           - Hours of operation
mixed_use_interface        - Residential/commercial interface
```

### Subdivision
```
subdivision_lot_size       - Minimum lot size
subdivision_lot_width      - Minimum lot frontage width
subdivision_lot_depth      - Minimum lot depth
subdivision_access         - Access requirements for new lots
subdivision_services       - Services for new lots
```

### Other
```
acoustic_privacy           - Acoustic privacy standards
visual_impact              - Visual impact assessment
site_analysis              - Site analysis requirements
context_analysis           - Context analysis
demolition                 - Demolition controls
excavation                 - Excavation limits
retaining_walls            - Retaining wall controls
outbuildings               - Outbuilding/shed controls
swimming_pools             - Swimming pool requirements
air_conditioning           - Air conditioning unit placement
services_utilities         - Utility services location
signage_general            - General signage controls
lighting_external          - External lighting controls
waste_management           - Waste management requirements
construction_management    - Construction management plans
```

---

## Zone-Specific Suffix Guide

Append when requirement is zone-specific:
```
_r1    - R1 General Residential
_r2    - R2 Low Density Residential
_r3    - R3 Medium Density Residential
_r4    - R4 High Density Residential
_b1    - B1 Neighbourhood Centre
_b2    - B2 Local Centre
_b4    - B4 Mixed Use
_re1   - RE1 Public Recreation
_re2   - RE2 Private Recreation
_in1   - IN1 General Industrial
_in2   - IN2 Light Industrial
_sp2   - SP2 Infrastructure
```

---

## Development Type Suffix Guide

Append when requirement is development-type specific:
```
_dwelling_house            - Single dwelling house
_multi_dwelling            - Multi-dwelling housing
_dual_occupancy            - Dual occupancy
_manor_house               - Manor house
_townhouse                 - Townhouse
_apartment                 - Residential flat building
_boarding_house            - Boarding house
_seniors_housing           - Seniors housing
_group_home                - Group home
_commercial                - Commercial development
_retail                    - Retail premises
_office                    - Office premises
_industrial                - Industrial development
_warehouse                 - Warehouse/distribution
```

---

## Usage Examples

### Example 1: Zone-Specific Setback
```json
{
  "category": "setback_front_r2",
  "subcategory": "Low Density Residential",
  "requirement_text": "Front setback: Minimum 5.5 metres for R2 zone",
  "applicable_zones": ["R2"],
  "development_types": ["dwelling_house", "dual_occupancy"],
  "value_numeric": 5.5,
  "unit": "metres"
}
```

### Example 2: Universal Requirement
```json
{
  "category": "parking_visitor",
  "subcategory": "Visitor Parking",
  "requirement_text": "Visitor parking: 1 space per 5 dwellings for multi-dwelling developments",
  "applicable_zones": ["R2", "R3", "R4", "B4"],
  "development_types": ["multi_dwelling", "apartment"],
  "value_numeric": 0.2,
  "unit": "spaces per dwelling"
}
```

### Example 3: Solar Access
```json
{
  "category": "solar_access_neighbours",
  "subcategory": "Solar Access to Neighbours",
  "requirement_text": "Minimum 3 hours solar access to neighbouring living areas between 9am-3pm on June 21",
  "applicable_zones": ["R2", "R3", "R4"],
  "development_types": ["dwelling_house", "multi_dwelling"],
  "value_numeric": 3,
  "unit": "hours"
}
```

---

## Priority Categories for Initial Extraction

For Marrickville Parts 2, 4.1, focus on:

### Tier 1 (Most Requested)
1. `setback_front`, `setback_front_r2`
2. `setback_side`, `setback_side_r2`
3. `setback_rear`, `setback_rear_r2`
4. `parking_dwelling`, `parking_multi_dwelling`, `parking_visitor`
5. `building_height`, `building_height_r2`
6. `fsr`, `fsr_r2`

### Tier 2 (Common Requirements)
7. `site_coverage`
8. `landscaping_front_yard`, `open_space_private`
9. `solar_access_neighbours`, `privacy_windows`
10. `dwelling_design_contemp`, `dwelling_design_period`

### Tier 3 (Supporting Controls)
11. `garage_location`, `driveway_width`
12. `fencing_front`, `character_streetscape`
13. `water_efficiency`, `stormwater_management`
14. `building_materials`, `building_articulation`

---

## Confidence Levels

Assign confidence based on extraction clarity:

**High**: Direct quote from DCP with clear numeric value
```
"A minimum setback of 5.5 metres..." → high confidence
```

**Medium**: Paraphrased or conditional requirement
```
"Setbacks should generally be 5-6m" → medium confidence
```

**Low**: Vague or discretionary requirement
```
"Setbacks determined on merit" → low confidence
```

---

## Summary

**Total Categories**: ~80-100 base categories
**With Zone/DevType Variants**: ~200-300 potential combinations
**Focus for Initial Extraction**: ~40 high-priority categories

This schema provides comprehensive coverage while remaining flexible for future expansion.
