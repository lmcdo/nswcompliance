# Final Category Schema - 31 Core Categories

## Category Definitions (Semantic, Not Keyword-Based)

### Heritage & Character (3 categories)
**heritage** - Heritage conservation requirements
- Applies to: Heritage items, conservation areas, archaeological sites
- Examples: "Maintain original windows", "Repair in matching materials", "Heritage impact statement required"
- NOT just: Any mention of "heritage" word

**character** - Neighborhood/streetscape character
- Applies to: Fit with existing built form, streetscape consistency, neighborhood amenity
- Examples: "Compatible with surrounding development", "Reflect prevailing street setback", "Maintain low-scale character"
- NOT: Heritage items (use 'heritage' instead)

**streetscape** - Public realm and street interface
- Applies to: Frontages, street trees, footpath, public domain
- Examples: "Active street frontage", "Street tree planting", "Footpath width"
- NOT: Private landscaping (use 'landscaping' instead)

### Building Design (5 categories)
**building_form** - Overall building mass, scale, articulation
- Applies to: Building bulk, massing, modulation, articulation, façade design
- Examples: "Break up building bulk", "Upper level setbacks", "Varied roofline"
- NOT: Specific setback measurements (use setback_* instead)

**building_height** - Height controls and limits
- Applies to: Maximum height, floor-to-floor, storeys
- Examples: "Maximum 2 storeys", "11m height limit", "Floor-to-floor minimum 3m"
- ONLY when specifying height/storey limits

**setback_front** - Front boundary setback
- Applies to: Distance from front boundary, building line
- Examples: "6m front setback", "Minimum 3m from street"
- NOT: Side or rear setbacks

**setback_side** - Side boundary setback
- Applies to: Distance from side boundaries
- Examples: "900mm side setback", "Zero lot line permitted"

**setback_rear** - Rear boundary setback
- Applies to: Distance from rear boundary
- Examples: "6m rear setback", "Lesser of 6m or prevailing"

**setbacks** - General setback requirements (when not specific to one side)
- Applies to: Combined setback requirements, general principles
- Examples: "Setbacks must allow deep soil", "Varied setbacks encouraged"
- NOT: Specific front/side/rear (use specific categories)

### Environmental (10 categories)
**waste_management** - Waste and recycling
- Applies to: Bin storage, collection, waste room, recycling facilities
- Examples: "Waste room minimum 6m²", "Separate recycling bins", "Screened from street"
- NOT: Construction waste (that's 'process')

**sustainability** - Sustainable design, green buildings, BASIX
- Applies to: BASIX, Green Star, sustainable materials, lifecycle
- Examples: "BASIX certificate required", "Recycled materials encouraged", "Green Star rated"
- NOT: Specific energy/water (use those categories)

**contamination** - Contaminated land management
- Applies to: Site contamination assessment and remediation
- Examples: "Phase 1 contamination assessment", "Remediation action plan"
- ONLY for contaminated land, not general pollution

**water_management** - Water sensitive design, stormwater quality
- Applies to: WSUD, rainwater tanks, water quality treatment
- Examples: "Rainwater tank required", "Bioretention", "Water quality treatment"
- NOT: Drainage infrastructure (use 'drainage' or 'stormwater')

**drainage** - Drainage and flood infrastructure
- Applies to: Drainage systems, flood mitigation, OSD
- Examples: "On-site detention required", "Drainage to street", "Flood-free access"

**stormwater** - Stormwater management
- Applies to: Stormwater collection, discharge, quality
- Examples: "Stormwater to street", "Gross pollutant trap"
- OVERLAP with drainage/water_management - use if specifically mentions "stormwater"

**energy_efficiency** - Energy performance
- Applies to: Insulation, glazing, thermal performance, solar panels
- Examples: "R3.5 ceiling insulation", "Solar panels encouraged"
- NOT: General sustainability (use 'sustainability')

**solar_access** - Solar access and overshadowing
- Applies to: Sunlight access, overshadowing controls
- Examples: "3 hours solar access to living areas", "Shadow diagrams required"

**tree_preservation** - Tree protection and retention
- Applies to: Existing tree protection, tree removal, tree reports
- Examples: "Retain significant trees", "Arborist report required"
- NOT: New tree planting (use 'landscaping')

**biodiversity** - Biodiversity conservation
- Applies to: Native vegetation, habitat, ecology
- Examples: "Native planting required", "Habitat assessment"

### Landscaping & Open Space (3 categories)
**landscaping** - Landscape design and planting
- Applies to: Landscape plans, planting, soft landscaping, gardens
- Examples: "Landscape plan required", "Native species", "Screen planting"
- NOT: Open space area calculations (use 'open_space')

**open_space** - Open space area requirements
- Applies to: Private open space area, communal open space calculations
- Examples: "45m² private open space", "Minimum 3m dimension"
- ONLY for area/dimension requirements

**deep_soil** - Deep soil zones
- Applies to: Deep soil area for tree planting
- Examples: "7% deep soil", "Minimum 6m² continuous"

### Site Development (5 categories)
**parking** - Car and bicycle parking
- Applies to: Parking rates, dimensions, access, bicycle parking
- Examples: "1 space per dwelling", "5.5m x 2.5m", "Visitor parking"

**subdivision** - Land subdivision
- Applies to: Lot size, subdivision design, services
- Examples: "Minimum 450m² lot", "Subdivision road design"

**fencing** - Fences and walls
- Applies to: Fence height, materials, design
- Examples: "1.8m max front fence", "Transparent above 1m"

**accessibility** - Universal access and mobility
- Applies to: Disability access, AS1428, accessible parking
- Examples: "AS1428 compliant", "Accessible entry", "Adaptable housing"

**safety** - Safety and security (CPTED, fire)
- Applies to: Crime prevention, lighting, sightlines, fire safety
- Examples: "CPTED principles", "Passive surveillance", "Fire safety upgrade"

### Special Uses (2 categories)
**signage** - Signs and advertising
- Applies to: Business signs, wayfinding, advertising
- Examples: "Maximum 2m² sign", "Illuminated signs prohibited"

**da_requirements** - DA submission requirements
- Applies to: What must be submitted with DA, required reports
- Examples: "Traffic impact assessment required", "Shadow diagrams"
- NOT: Actual design requirements (use relevant category)

### Other (2 categories)
**environmental** - General environmental (not covered above)
- Applies to: Environmental requirements not fitting specific categories
- Fallback for: Air quality, noise, general environmental protection

**other** - Does not fit any category above
- LAST RESORT: Only when truly doesn't fit elsewhere
- Examples: Construction hours, notification requirements

**flood_management** - Flood planning and controls
- Applies to: Flood planning levels, flood-free areas
- Examples: "FPL + 500mm", "Flood-free habitable areas"

## Category Assignment Rules

1. **Read the ENTIRE requirement** - Don't just keyword match
2. **Understand the PURPOSE** - What is this controlling?
3. **Choose MOST SPECIFIC category** - Don't default to broad categories
4. **Use examples as guide** - Similar requirements should use same category
5. **Fallback order**: Specific → General → Environmental → Other

## Common Mistakes to Avoid

❌ "Heritage overlay applies" → DON'T use 'heritage' (it's not a heritage requirement, use 'other' or 'da_requirements')
✅ "Retain heritage fabric" → heritage (actual heritage requirement)

❌ "Trees must be retained" → DON'T use 'landscaping' (it's about existing trees)
✅ "Trees must be retained" → tree_preservation (protection of existing)

❌ "Landscape plan required" → DON'T use 'da_requirements' (it's about landscaping)
✅ "Landscape plan required" → landscaping (it's a landscape requirement)

❌ "Compatible with streetscape" → DON'T use 'streetscape' (too vague)
✅ "Compatible with streetscape" → character (about neighborhood compatibility)

❌ "Setback allows deep soil" → DON'T use 'setbacks' alone
✅ "Setback allows deep soil" → Consider primary purpose: deep_soil (if about soil), setback_* (if about distance)
