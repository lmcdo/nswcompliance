
# Clause Number Fix Report - compliance-engine

**Date:** 2025-08-30 23:07:37  
**Issue:** CNFS-001 - PDF page number contamination and invalid clause structure

## Summary

### JSON Files (AutoSchemaKG Data)
- **Files Processed:** 217
- **Total Issues Fixed:** 64
- **Files with Issues:** 21
- **Errors:** 0

### CSV Files (Triple Data)
- **Files Processed:** 5
- **Rows Updated:** 40
- **Errors:** 0

## Issues Fixed

### Common Patterns Corrected:
- `4.2.4.2 Building heights . 5` → `4.2.4(b) Building heights`
- `4.2.4.3 Building setbacks.. 5` → `4.2.4(c) Building setbacks`  
- `4.2.4.1 Floor space ratio . /4` → `4.2.4(a) Floor space ratio`

## Files with Issues Fixed

### nsw_planning_docs_000.json
- Issues Fixed: 1
  - `Clause 2.12.4.6 - height_limit (development_control): Signage on high-rise buildings (in excess of 15 metres)` → `Clause 2.12.4(f) - height_limit: Signage on high-rise buildings (in excess of 15 metres)`

### nsw_planning_docs_014.json
- Issues Fixed: 6
  - `Clause 4.2.4.2 - height_limit (development_control): 4.2.4.2 Building heights . 5` → `Clause 4.2.4(b) - height_limit: Building heights`
  - `Clause 4.2.4.3 - setback (development_control): 4.2.4.3 Building setbacks.. 5` → `Clause 4.2.4(c) - setback: Building setbacks`
  - `Clause 4.2.4.1 - fsr_control (development_control): 4.2.4.1 Floor space ratio and site coverage . /4` → `Clause 4.2.4(a) - fsr_control: 4.2.4.1 Floor space ratio and site coverage`
  - `Clause 4.2.10 - heritage (development_control): 4.2.10 Period residential flat buildings...... .. 13` → `Clause 4.2.10 - heritage: Period residential flat buildings`

### nsw_planning_docs_015.json
- Issues Fixed: 3
  - `Clause 4.3.3.1 - other (development_control): C1 The design of a boarding house is to be compatible with the character of the local area, and ensure there are no negative impacts on the amenity of the local area. The Planning Context identifies what matters will be considered in the assessment of a boarding house, in addition to the following, to achieve compatibility with the character of the local area and minimise negative impact on amenity.` → `Clause 4.3.3(a) - other: C1 The design of a boarding house is to be compatible with the character of the local area, and ensure there are no negative impacts on the amenity of the local area. The Planning Context identifies what matters will be considered in the assessment of a boarding house, in addition to the following, to achieve compatibility with the character of the local area and minimise negative impact on amenity`
  - `Clause 4.3.3.2 - other (development_control): C2 Resident numbers will be determined based on the gross floor area of the boarding room (excluding any area used for the purposes of private kitchen or bathroom facilities).` → `Clause 4.3.3(b) - other: C2 Resident numbers will be determined based on the gross floor area of the boarding room (excluding any area used for the purposes of private kitchen or bathroom facilities)`
  - `Clause 4.3.3.4 - other (development_control): An area of private open space, at least 8 square metres with a minimum dimension of 2.5 metres is required to be provided adjacent to each boarding house manager’s accommodation with any such private open space not being provided within the front setback area.` → `Clause 4.3.3(d) - other: An area of private open space, at least 8 square metres with a minimum dimension of 2.5 metres is required to be provided adjacent to each boarding house manager’s accommodation with any such private open space not being provided within the front setback area`

### nsw_planning_docs_018.json
- Issues Fixed: 4
  - `Clause 5.1.3.1 - fsr_control (development_control): Floor space ratio (FSR). 5` → `Clause 5.1.3(a) - fsr_control: Floor space ratio (FSR)`
  - `Clause 5.1.3.2 - height_limit (development_control): Height .. . 6` → `Clause 5.1.3(b) - height_limit: Height`
  - `Clause 5.1.3.3 - setback (development_control): Massing and setbacks . . 7` → `Clause 5.1.3(c) - setback: Massing and setbacks`
  - `Clause 5.3.1.3 - environmental_protection (environmental_protection): Environmental protection . 28` → `Clause 5.3.1(c) - environmental_protection: Environmental protection`

### nsw_planning_docs_019.json
- Issues Fixed: 5
  - `Clause 6.1.2.5 - height_limit (development_control): Building height .. . 3` → `Clause 6.1.2(e) - height_limit: Building height`
  - `Clause 6.1.2.2 - fsr_control (development_control): Floor space ratio (FSR) Error! Bookmark not defined.` → `Clause 6.1.2(b) - fsr_control: Floor space ratio (FSR) Error! Bookmark not defined`
  - `Clause 6.1.2.7 - setback (development_control): Setbacks. 6` → `Clause 6.1.2(g) - setback: Setbacks`
  - `Clause 6.1.2.1 - parking (development_control): Where there is to be a strata plan of subdivision, any space for parking or other purposes forming a part of a sole occupancy unit must be included in the same strata lot as the unit.` → `Clause 6.1.2(a) - parking: Where there is to be a strata plan of subdivision, any space for parking or other purposes forming a part of a sole occupancy unit must be included in the same strata lot as the unit`
  - `Clause 6.1.2.2 - zoning (land_use_zoning): Frontages of allotments to be developed for light industrial purposes (in zones where light industry is a permissible land use under Inner West LEP 2022) will be assessed on factors such as location of the site, access to the site, streetscape and surrounding development.` → `Clause 6.1.2(b) - zoning: Frontages of allotments to be developed for light industrial purposes (in zones where light industry is a permissible land use under Inner West LEP 2022) will be assessed on factors such as location of the site, access to the site, streetscape and surrounding development`

### nsw_planning_docs_041.json
- Issues Fixed: 3
  - `Clause 9.23.5.1 - building_control (development_control): The redevelopment of the land shaded in Figure (23.1a) must wherever possible conform to the amalgamation pattern in the control diagram in Figure (23.1b).` → `Clause 9.23.5(a) - building_control: The redevelopment of the land shaded in Figure (23.1a) must wherever possible conform to the amalgamation pattern in the control diagram in Figure (23.1b)`
  - `Clause 9.23.5.1 - building_control (development_control): Amalgamation of allotments must not result in any adjoining sites being isolated to the extent that it is not possible for development to occur in accordance with the urban design vision for the Masterplan Area.` → `Clause 9.23.5(a) - building_control: Amalgamation of allotments must not result in any adjoining sites being isolated to the extent that it is not possible for development to occur in accordance with the urban design vision for the Masterplan Area`
  - `Clause 9.23.5.1 - height_limit (development_control): The height of proposed buildings on the land shaded in Figure (23.1a) must conform to the control diagram(s) in Figures (23.1b) and (23.1c). The height is expressed in number of storeys.` → `Clause 9.23.5(a) - height_limit: The height of proposed buildings on the land shaded in Figure (23.1a) must conform to the control diagram(s) in Figures (23.1b) and (23.1c). The height is expressed in number of storeys`

### nsw_planning_docs_044.json
- Issues Fixed: 8
  - `Clause 9.26.4.1 - building_height (development_control): The following maximum height limits relate to the building heights (in metres) and floor space ratio controls set in MLEP 2011.` → `Clause 9.26.4(a) - building_height: The following maximum height limits relate to the building heights (in metres) and floor space ratio controls set in MLEP 2011`
  - `Clause 9.26.4.1 - height_limit (development_control): The heights of proposed buildings must conform to the controls in Figure 26.1. The height is expressed in number of storeys.` → `Clause 9.26.4(a) - height_limit: The heights of proposed buildings must conform to the controls in Figure 26.1. The height is expressed in number of storeys`
  - `Clause 9.26.4.1 - setback (development_control): Five storey buildings fronting the Princes Highway are to have the fifth level and roof (including any open pergolas) set back from the external wall of the floor below by a distance of 3 metres, measured from the building alignment facing the Princes Highway.` → `Clause 9.26.4(a) - setback: Five storey buildings fronting the Princes Highway are to have the fifth level and roof (including any open pergolas) set back from the external wall of the floor below by a distance of 3 metres, measured from the building alignment facing the Princes Highway`
  - `Clause 9.26.4.1 - building_height (development_control): Opportunities for greater building height exist along the Princes Highway, however the design of new development must respect other buildings for retention.` → `Clause 9.26.4(a) - building_height: Opportunities for greater building height exist along the Princes Highway, however the design of new development must respect other buildings for retention`
  - `Clause 9.26.4.1 - setback (development_control): Upper level setbacks are to reinforce the desired scale of the buildings on the street.` → `Clause 9.26.4(a) - setback: Upper level setbacks are to reinforce the desired scale of the buildings on the street`
  - `Clause 9.26.4.1 - building_height (development_control): A larger scale building at the corner of the Princes Highway and Barwon Park Road will help define this acute corner and will signify the northern gateway to the precinct.` → `Clause 9.26.4(a) - building_height: A larger scale building at the corner of the Princes Highway and Barwon Park Road will help define this acute corner and will signify the northern gateway to the precinct`
  - `Clause 9.26.4.1 - building_height (development_control): New development on the Princes Highway should respond in part to the scale and function of existing residential buildings on Crown Street.` → `Clause 9.26.4(a) - building_height: New development on the Princes Highway should respond in part to the scale and function of existing residential buildings on Crown Street`
  - `Clause 9.26.4.1 - building_height (development_control): The transition between taller development and adjacent lower scaled buildings must be done with development of an intermediate scale.` → `Clause 9.26.4(a) - building_height: The transition between taller development and adjacent lower scaled buildings must be done with development of an intermediate scale`

### nsw_planning_docs_060.json
- Issues Fixed: 1
  - `Clause 9.40.3.1 - heritage (development_control): The Civic Precinct Heritage Conservation Area is a high quality and substantially intact example of the local civic precinct.` → `Clause 9.40.3(a) - heritage: The Civic Precinct Heritage Conservation Area is a high quality and substantially intact example of the local civic precinct`

### nsw_planning_docs_066.json
- Issues Fixed: 1
  - `Clause 9.47.1.3 - zoning (land_use_zoning): Development within the precinct will need to have regard to this section of the DCP as well as other relevant provisions in the DCP.` → `Clause 9.47.1(c) - zoning: Development within the precinct will need to have regard to this section of the DCP as well as other relevant provisions in the DCP`

### nsw_planning_docs_070.json
- Issues Fixed: 1
  - `Clause 9.8.5.1 - setback (development_control): Building mass on the first and second storey must: a. Generally be massed in a U shape, to the southern, eastern and northern side of the property, and open as a courtyard in the middle; b. Be setback 1 metre from the southern boundary; 1 metre from the eastern boundary; 1 metre from the northern boundary (from the north-eastern corner to a point in line with the southeastern edge of the residential flat building located on No. 2B Gladstone Street, Newtown); and 6 metres from the northern boundary (from a point in line with the south-eastern edge of the residential flat building located on No. 2B Gladstone Street, Newtown to the north-western corner of the first and second storey mass); and c. Have approximately a 15 metre envelope depth.` → `Clause 9.8.5(a) - setback: Building mass on the first and second storey must: a. Generally be massed in a U shape, to the southern, eastern and northern side of the property, and open as a courtyard in the middle; b. Be setback 1 metre from the southern boundary; 1 metre from the eastern boundary; 1 metre from the northern boundary (from the north-eastern corner to a point in line with the southeastern edge of the residential flat building located on No. 2B Gladstone Street, Newtown); and 6 metres from the northern boundary (from a point in line with the south-eastern edge of the residential flat building located on No. 2B Gladstone Street, Newtown to the north-western corner of the first and second storey mass); and c. Have approximately a 15 metre envelope depth`

### nsw_planning_docs_145.json
- Issues Fixed: 1
  - `Clause 2.5.4.1 - other (development_control): The DDA also makes it unlawful for public places to be inaccessible to people with a` → `Clause 2.5.4(a) - other: The DDA also makes it unlawful for public places to be inaccessible to people with a`

### nsw_planning_docs_155.json
- Issues Fixed: 4
  - `Clause 4.1.6.1 - fsr_control (development_control): Floor space ratio and height` → `Clause 4.1.6(a) - fsr_control: Floor space ratio and height`
  - `Clause 4.1.6.2 - setback (development_control): Building  setbacks` → `Clause 4.1.6(b) - setback: Building setbacks`
  - `Clause 4.1.6.1 - height_limit (development_control): height` → `Clause 4.1.6(a) - height_limit: height`
  - `Clause 4.1.6.3 - setback (development_control): Site coverage` → `Clause 4.1.6(c) - setback: Site coverage`

### nsw_planning_docs_156.json
- Issues Fixed: 4
  - `Clause 5.1.3.2 - height_limit (development_control): Height` → `Clause 5.1.3(b) - height_limit: Height`
  - `Clause 5.1.3.1 - fsr_control (development_control): Floor space ratio (FSR)` → `Clause 5.1.3(a) - fsr_control: Floor space ratio (FSR)`
  - `Clause 5.1.3.3 - setback (development_control): Massing and setbacks` → `Clause 5.1.3(c) - setback: Massing and setbacks`
  - `Clause 5.3.1.3 - environmental_protection (environmental_protection): Environmental protection` → `Clause 5.3.1(c) - environmental_protection: Environmental protection`

### nsw_planning_docs_157.json
- Issues Fixed: 4
  - `Clause 6.1.2.1 - land_use_zoning (land_use_zoning): Where development or use of a number of existing lots is p roposed, the lots must  be consolidated into o ne parcel, and the plan of consolidation lodged with the relevant authority .` → `Clause 6.1.2(a) - land_use_zoning: Where development or use of a number of existing lots is p roposed, the lots must be consolidated into o ne parcel, and the plan of consolidation lodged with the relevant authority`
  - `Clause 6.1.2.1 - land_use_zoning (land_use_zoning): No part of any site is to be separately leased from the remainder of the property for the purpose of a separate occupation or oper ation from an approved use except where the prior  development consent of Coun cil has been sought and obtain ed to any such lease, occupation or operation.` → `Clause 6.1.2(a) - land_use_zoning: No part of any site is to be separately leased from the remainder of the property for the purpose of a separate occupation or oper ation from an approved use except where the prior development consent of Coun cil has been sought and obtain ed to any such lease, occupation or operation`
  - `Clause 6.1.2.1 - parking (development_control): Where there is to be a strata plan of subdivision , any space for parking or other purposes forming a part of a sole occupancy unit must be included in the same strata lot as the unit.` → `Clause 6.1.2(a) - parking: Where there is to be a strata plan of subdivision , any space for parking or other purposes forming a part of a sole occupancy unit must be included in the same strata lot as the unit`
  - `Clause 6.1.2.2 - parking (development_control): To ensure all loading and unloading, turning movements, queuing and parking of vehicles, including delivery vehicles as sociated with the new development , occurs wholly within the site.` → `Clause 6.1.2(b) - parking: To ensure all loading and unloading, turning movements, queuing and parking of vehicles, including delivery vehicles as sociated with the new development , occurs wholly within the site`

### nsw_planning_docs_162.json
- Issues Fixed: 1
  - `Clause 8.1.7.2 - heritage (development_control): Development in the vicinity of a heritage item` → `Clause 8.1.7(b) - heritage: Development in the vicinity of a heritage item`

### nsw_planning_docs_167.json
- Issues Fixed: 1
  - `Clause 9.11.3.2 - heritage (heritage): This precinct also contains the Hoskins Park & Environs  Heritage C onservation Area.` → `Clause 9.11.3(b) - heritage: This precinct also contains the Hoskins Park & Environs Heritage C onservation Area`

### nsw_planning_docs_183.json
- Issues Fixed: 8
  - `Clause 9.26.4.1 - height_limit (development_control): The following maximum height limits relate to the building heights (in metres) and floor` → `Clause 9.26.4(a) - height_limit: The following maximum height limits relate to the building heights (in metres) and floor`
  - `Clause 9.26.4.1 - height_limit (development_control): Five storey buildings fronting the Princes Highway are to have the fifth level and roof` → `Clause 9.26.4(a) - height_limit: Five storey buildings fronting the Princes Highway are to have the fifth level and roof`
  - `Clause 9.26.4.1 - setback (development_control): Five storey buildings fronting the Princes Highway are to have the fifth level and roof` → `Clause 9.26.4(a) - setback: Five storey buildings fronting the Princes Highway are to have the fifth level and roof`
  - `Clause 9.26.4.1 - height_limit (development_control): Opportunities for greater building height exist along the Princes Highway, however the design of new development must respect other buildings for retention.  U pper level setbacks are to  reinfor ce the desired scale of the buildings on the street.` → `Clause 9.26.4(a) - height_limit: Opportunities for greater building height exist along the Princes Highway, however the design of new development must respect other buildings for retention. U pper level setbacks are to reinfor ce the desired scale of the buildings on the street`
  - `Clause 9.26.4.1 - height_limit (development_control): A larger scale building at the corner of the Princes Highway and Barwon Park Road will help define this acute corner and will signify the northern gateway to the precinct.` → `Clause 9.26.4(a) - height_limit: A larger scale building at the corner of the Princes Highway and Barwon Park Road will help define this acute corner and will signify the northern gateway to the precinct`
  - `Clause 9.26.4.1 - height_limit (development_control): New development on the Princes Highway should respond in part to the scale and function of existing residential buildings on Crown Street.` → `Clause 9.26.4(a) - height_limit: New development on the Princes Highway should respond in part to the scale and function of existing residential buildings on Crown Street`
  - `Clause 9.26.4.1 - height_limit (development_control): The transition between taller development and adjacent lower scaled buildings must be done with development of an  intermediate scale.` → `Clause 9.26.4(a) - height_limit: The transition between taller development and adjacent lower scaled buildings must be done with development of an intermediate scale`
  - `Clause 9.26.4.1 - other (development_control): While a maximu m buildi ng height has been set under  MLEP 2011  it does not mean it can always be achieved or is desirable. All development must fit within its context and not impact adversely on adjoining properties` → `Clause 9.26.4(a) - other: While a maximu m buildi ng height has been set under MLEP 2011 it does not mean it can always be achieved or is desirable. All development must fit within its context and not impact adversely on adjoining properties`

### nsw_planning_docs_186.json
- Issues Fixed: 3
  - `Clause 9.29.2 - heritage (heritage): 2. To protect the identified  Heritage Items  within the precinct.` → `Clause 9.29.2 - heritage: To protect the identified Heritage Items within the precinct`
  - `Clause 9.29.2 - height_limit (development_control): 3. To maintain distinctly single storey streetscapes that exist within the precinct.` → `Clause 9.29.2 - height_limit: To maintain distinctly single storey streetscapes that exist within the precinct`
  - `Clause 9.29.2 - zoning (land_use_zoning): 6. To preserve the predominantly medium to high density residen tial character of the precinct.` → `Clause 9.29.2 - zoning: To preserve the predominantly medium to high density residen tial character of the precinct`

### nsw_planning_docs_193.json
- Issues Fixed: 1
  - `Clause 9.32.3.1 - heritage (heritage): Parramatta Road Commercial Precinct Heritage Conservation Area (HCA 5)` → `Clause 9.32.3(a) - heritage: Parramatta Road Commercial Precinct Heritage Conservation Area (HCA 5)`

### nsw_planning_docs_196.json
- Issues Fixed: 1
  - `Clause 9.38.3.1 - heritage (heritage): The Du lwich Hill Commercial Precinct H eritage C onservation A rea is of aesthetic` → `Clause 9.38.3(a) - heritage: The Du lwich Hill Commercial Precinct H eritage C onservation A rea is of aesthetic`

### nsw_planning_docs_198.json
- Issues Fixed: 3
  - `Clause 9.4.3.1 - heritage (heritage): HCA 10: Camperdown Park Heritage` → `Clause 9.4.3(a) - heritage: HCA 10: Camperdown Park Heritage`
  - `Clause 9.4.3.2 - heritage (heritage): HCA 11: North Kingston Estate Heritage` → `Clause 9.4.3(b) - heritage: HCA 11: North Kingston Estate Heritage`
  - `Clause 9.4.3.3 - heritage (heritage): HCA 9: Hopetoun -Roberts -Federation` → `Clause 9.4.3(c) - heritage: HCA 9: Hopetoun -Roberts -Federation`


## Next Steps

1. **Validate Results:** Test requirement connections with corrected clause numbers
2. **Update Knowledge Graph:** Refresh LightRAG with cleaned data  
3. **Test UI:** Verify "Show Connected Requirements" displays clean clause numbers
4. **Monitor:** Watch for any remaining numbering issues

## Backup Information

- All original files backed up with `.backup` extension
- Rollback available if issues found: `mv file.json.backup file.json`
