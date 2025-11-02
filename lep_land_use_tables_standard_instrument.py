"""
NSW Standard Instrument Land Use Tables
Source: Environmental Planning and Assessment (Standard Instrument) Order 2006

These are the STANDARD tables that apply to ALL Standard Instrument LEPs in NSW,
including Inner West LEP 2022, unless specifically varied by local provisions.

Note: Some older zones (E1, E2, etc.) may be transitional and should be checked
against the specific LEP for any variations.
"""

# Standard Instrument Land Use Tables
# Extracted from Standard Instrument Order 2006

STANDARD_LAND_USE_TABLES = {
    "R1": {
        "zone_name": "General Residential",
        "permitted_without_consent": [
            "Home occupations"
        ],
        "permitted_with_consent": [
            "Attached dwellings",
            "Boarding houses",
            "Community facilities",
            "Dual occupancies",
            "Dwelling houses",
            "Environmental facilities",
            "Exhibition homes",
            "Group homes",
            "Home businesses",
            "Home industries",
            "Hospitals",
            "Hostels",
            "Multi dwelling housing",
            "Neighbourhood shops",
            "Places of public worship",
            "Respite day care centres",
            "Roads",
            "Semi-detached dwellings",
            "Seniors housing"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "R2": {
        "zone_name": "Low Density Residential",
        "permitted_without_consent": [
            "Home occupations"
        ],
        "permitted_with_consent": [
            "Attached dwellings",
            "Boarding houses",
            "Child care centres",
            "Community facilities",
            "Dual occupancies",
            "Dwelling houses",
            "Environmental facilities",
            "Exhibition homes",
            "Extractive industries",
            "Group homes",
            "Home-based child care",
            "Home businesses",
            "Home industries",
            "Hospitals",
            "Hostels",
            "Information and education facilities",
            "Medical centres",
            "Neighbourhood shops",
            "Places of public worship",
            "Recreation areas",
            "Recreation facilities (outdoor)",
            "Respite day care centres",
            "Roads",
            "Schools",
            "Seniors housing",
            "Veterinary hospitals"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "R3": {
        "zone_name": "Medium Density Residential",
        "permitted_without_consent": [
            "Home occupations"
        ],
        "permitted_with_consent": [
            "Attached dwellings",
            "Boarding houses",
            "Centre-based child care facilities",
            "Community facilities",
            "Dual occupancies",
            "Dwelling houses",
            "Environmental facilities",
            "Exhibition homes",
            "Group homes",
            "Home-based child care",
            "Home businesses",
            "Home industries",
            "Hospitals",
            "Hostels",
            "Information and education facilities",
            "Medical centres",
            "Multi dwelling housing",
            "Neighbourhood shops",
            "Places of public worship",
            "Recreation areas",
            "Recreation facilities (outdoor)",
            "Residential flat buildings",
            "Respite day care centres",
            "Roads",
            "Schools",
            "Seniors housing",
            "Shop top housing",
            "Veterinary hospitals"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "R4": {
        "zone_name": "High Density Residential",
        "permitted_without_consent": [
            "Home occupations"
        ],
        "permitted_with_consent": [
            "Attached dwellings",
            "Boarding houses",
            "Centre-based child care facilities",
            "Community facilities",
            "Dwelling houses",
            "Environmental facilities",
            "Exhibition homes",
            "Group homes",
            "Home-based child care",
            "Home businesses",
            "Home industries",
            "Hospitals",
            "Hostels",
            "Information and education facilities",
            "Medical centres",
            "Multi dwelling housing",
            "Neighbourhood shops",
            "Places of public worship",
            "Recreation areas",
            "Recreation facilities (outdoor)",
            "Registered clubs",
            "Residential flat buildings",
            "Respite day care centres",
            "Roads",
            "Schools",
            "Seniors housing",
            "Shop top housing",
            "Tourist and visitor accommodation"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "B1": {
        "zone_name": "Neighbourhood Centre",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Boarding houses",
            "Centre-based child care facilities",
            "Community facilities",
            "Environmental facilities",
            "Food and drink premises",
            "Garden centres",
            "Hardware and building supplies",
            "Kiosks",
            "Markets",
            "Medical centres",
            "Neighbourhood shops",
            "Office premises",
            "Passenger transport facilities",
            "Places of public worship",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Registered clubs",
            "Respite day care centres",
            "Restricted premises",
            "Roads",
            "Retail premises",
            "Self-storage units",
            "Seniors housing",
            "Service stations",
            "Shop top housing",
            "Veterinary hospitals"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "B2": {
        "zone_name": "Local Centre",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Amusement centres",
            "Boarding houses",
            "Centre-based child care facilities",
            "Community facilities",
            "Educational establishments",
            "Entertainment facilities",
            "Function centres",
            "Hardware and building supplies",
            "Health consulting rooms",
            "Hotel or motel accommodation",
            "Information and education facilities",
            "Kiosks",
            "Light industries",
            "Markets",
            "Medical centres",
            "Neighbourhood shops",
            "Office premises",
            "Passenger transport facilities",
            "Places of public worship",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Registered clubs",
            "Respite day care centres",
            "Restricted premises",
            "Retail premises",
            "Roads",
            "Self-storage units",
            "Seniors housing",
            "Service stations",
            "Shop top housing",
            "Storage premises",
            "Take away food and drink premises",
            "Veterinary hospitals"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "B4": {
        "zone_name": "Mixed Use",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Boarding houses",
            "Centre-based child care facilities",
            "Community facilities",
            "Educational establishments",
            "Entertainment facilities",
            "Function centres",
            "Health consulting rooms",
            "Hotel or motel accommodation",
            "Information and education facilities",
            "Kiosks",
            "Light industries",
            "Markets",
            "Medical centres",
            "Neighbourhood shops",
            "Office premises",
            "Passenger transport facilities",
            "Places of public worship",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Registered clubs",
            "Residential accommodation",
            "Respite day care centres",
            "Restricted premises",
            "Retail premises",
            "Roads",
            "Self-storage units",
            "Seniors housing",
            "Service stations",
            "Shop top housing",
            "Storage premises",
            "Take away food and drink premises",
            "Veterinary hospitals",
            "Warehouse or distribution centres"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "B6": {
        "zone_name": "Enterprise Corridor",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Bulky goods premises",
            "Centre-based child care facilities",
            "Depots",
            "Food and drink premises",
            "Garden centres",
            "Hardware and building supplies",
            "Health consulting rooms",
            "Home improvement centres",
            "Kiosks",
            "Landscaping material supplies",
            "Light industries",
            "Liquid fuel depots",
            "Markets",
            "Medical centres",
            "Office premises",
            "Passenger transport facilities",
            "Places of public worship",
            "Plant nurseries",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Registered clubs",
            "Respite day care centres",
            "Restricted premises",
            "Retail premises",
            "Roads",
            "Self-storage units",
            "Service stations",
            "Storage premises",
            "Take away food and drink premises",
            "Timber yards",
            "Transport depots",
            "Veterinary hospitals",
            "Vehicle repair stations",
            "Warehouse or distribution centres"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "B7": {
        "zone_name": "Business Park",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Depots",
            "Food and drink premises",
            "Garden centres",
            "Hardware and building supplies",
            "Kiosks",
            "Light industries",
            "Medical centres",
            "Office premises",
            "Passenger transport facilities",
            "Places of public worship",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Respite day care centres",
            "Restricted premises",
            "Roads",
            "Self-storage units",
            "Service stations",
            "Storage premises",
            "Take away food and drink premises",
            "Transport depots",
            "Warehouse or distribution centres"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "IN1": {
        "zone_name": "General Industrial",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Depots",
            "Freight transport facilities",
            "General industries",
            "Hardware and building supplies",
            "Industrial training facilities",
            "Kiosks",
            "Landscaping material supplies",
            "Light industries",
            "Liquid fuel depots",
            "Neighbourhood shops",
            "Oyster aquaculture",
            "Passenger transport facilities",
            "Places of public worship",
            "Plant nurseries",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Roads",
            "Rural industries",
            "Self-storage units",
            "Service stations",
            "Storage premises",
            "Take away food and drink premises",
            "Timber yards",
            "Transport depots",
            "Truck depots",
            "Vehicle body repair workshops",
            "Vehicle repair stations",
            "Warehouse or distribution centres"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "IN2": {
        "zone_name": "Light Industrial",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Depots",
            "Food and drink premises",
            "Garden centres",
            "Hardware and building supplies",
            "Industrial training facilities",
            "Kiosks",
            "Light industries",
            "Neighbourhood shops",
            "Office premises",
            "Oyster aquaculture",
            "Passenger transport facilities",
            "Places of public worship",
            "Plant nurseries",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Respite day care centres",
            "Roads",
            "Rural industries",
            "Self-storage units",
            "Service stations",
            "Storage premises",
            "Take away food and drink premises",
            "Timber yards",
            "Transport depots",
            "Vehicle repair stations",
            "Warehouse or distribution centres"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "RE1": {
        "zone_name": "Public Recreation",
        "permitted_without_consent": [
            "Environmental protection works"
        ],
        "permitted_with_consent": [
            "Airports",
            "Boat launching ramps",
            "Boat sheds",
            "Community facilities",
            "Food and drink premises",
            "Helipads",
            "Horticulture",
            "Information and education facilities",
            "Jetties",
            "Kiosks",
            "Markets",
            "Mooring pens",
            "Moorings",
            "Passenger transport facilities",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Recreation facilities (major)",
            "Recreation facilities (outdoor)",
            "Registered clubs",
            "Respite day care centres",
            "Roads",
            "Take away food and drink premises",
            "Water recreation structures"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "RE2": {
        "zone_name": "Private Recreation",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Boat launching ramps",
            "Boat sheds",
            "Charter and tourism boating facilities",
            "Food and drink premises",
            "Jetties",
            "Kiosks",
            "Marinas",
            "Mooring pens",
            "Moorings",
            "Recreation areas",
            "Recreation facilities (indoor)",
            "Recreation facilities (major)",
            "Recreation facilities (outdoor)",
            "Registered clubs",
            "Respite day care centres",
            "Roads",
            "Take away food and drink premises",
            "Water recreation structures"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    },

    "SP2": {
        "zone_name": "Infrastructure",
        "permitted_without_consent": [
            "Nil"
        ],
        "permitted_with_consent": [
            "Air transport facilities",
            "Biosolids treatment facilities",
            "Boat launching ramps",
            "Boat sheds",
            "Correctional centres",
            "Crematoriums",
            "Depots",
            "Electricity generating works",
            "Environmental facilities",
            "Flood mitigation works",
            "Forestry",
            "Freight transport facilities",
            "Health services facilities",
            "Heavy industrial storage establishments",
            "Helipads",
            "Jetties",
            "Mortuaries",
            "Moorings",
            "Passenger transport facilities",
            "Recreation areas",
            "Research stations",
            "Roads",
            "Sewage treatment plants",
            "Signage",
            "Stormwater management systems",
            "Transport depots",
            "Truck depots",
            "Waste or resource management facilities",
            "Water supply systems",
            "Wharf or boating facilities"
        ],
        "prohibited": "Any development not specified in item 2 or 3"
    }
}

# Note: E1, E2 zones are transitional/legacy zones from former councils
# These may have local variations - check Schedule 1 of Inner West LEP 2022

LEGACY_ZONES = {
    "E1": {
        "zone_name": "Local Centre (Ashfield legacy)",
        "note": "Transitional zone - typically equivalent to B2 Local Centre",
        "permitted_with_consent": [
            # Typically similar to B2, but check Schedule 1 for variations
            "Business premises",
            "Office premises",
            "Retail premises",
            "Shop top housing",
            "Residential accommodation",
            "Community facilities",
            "Entertainment facilities"
        ]
    },
    "E2": {
        "zone_name": "Commercial (Marrickville/Leichhardt legacy)",
        "note": "Transitional zone - typically equivalent to B4 Mixed Use",
        "permitted_with_consent": [
            # Typically similar to B4, but check Schedule 1 for variations
            "Business premises",
            "Office premises",
            "Retail premises",
            "Shop top housing",
            "Residential accommodation",
            "Light industries"
        ]
    }
}

if __name__ == "__main__":
    print("Standard Instrument Land Use Tables loaded")
    print(f"Standard zones: {len(STANDARD_LAND_USE_TABLES)}")
    print(f"Legacy zones: {len(LEGACY_ZONES)}")

    # Example: Check R2 zone
    r2 = STANDARD_LAND_USE_TABLES["R2"]
    print(f"\nZone R2: {r2['zone_name']}")
    print(f"Permitted with consent: {len(r2['permitted_with_consent'])} uses")
    print(f"Sample uses: {r2['permitted_with_consent'][:5]}")
