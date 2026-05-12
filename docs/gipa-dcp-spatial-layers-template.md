# GIPA Request — DCP Spatial Layers

> Template letter for requesting DCP spatial data from NSW councils under the Government Information (Public Access) Act 2009. Customise the [BRACKETED] fields per council.

---

**From:**
Lawrence McDonell
Solvyra Pty Ltd
[ADDRESS]
[EMAIL]
[PHONE]

**To:**
Right to Information Officer
[COUNCIL NAME]
[COUNCIL ADDRESS]

**Date:** [DATE]

---

**RE: Informal request for access to DCP spatial data layers (GIS/shapefile format)**

Dear Right to Information Officer,

I am writing to request access to geospatial datasets associated with the [COUNCIL NAME] Development Control Plan ([DCP NAME AND VERSION]), pursuant to the Government Information (Public Access) Act 2009 (GIPA Act).

## Information Requested

I am seeking the following spatial data layers referenced in the DCP, in GIS-compatible format (Shapefile, GeoJSON, GeoPackage, or File Geodatabase):

[SELECT APPLICABLE LAYERS — delete those not relevant to this council]

1. **DCP Map — Site Coverage**: The spatial layer assigning maximum site coverage percentages to lots/areas, as referenced in [DCP SECTION REF, e.g., "Warringah DCP 2011, Section B4 — Site Coverage"].

2. **DCP Map — Landscape Area / Landscaped Open Space**: Any spatial layer defining minimum landscaped area requirements by lot or precinct.

3. **DCP Precinct Boundaries**: The spatial boundaries of DCP character areas, planning precincts, or locality-specific control areas as defined in [DCP SECTION REF].

4. **Foreshore Scenic Protection Area / Special Character Area boundaries**: Any spatial boundary referenced in the DCP or LEP for the purpose of applying differential development controls.

5. **DCP Map — Setbacks**: Any spatial layer defining variable setback requirements by lot or area.

6. **DCP Map — Building Envelope / Height Plane**: Any spatial layer defining lot-specific building envelope or height plane controls beyond the LEP HOB map.

## Preferred Format

In order of preference:
- ESRI Shapefile (.shp + .shx + .dbf + .prj)
- GeoJSON
- GeoPackage (.gpkg)
- File Geodatabase (.gdb)
- KML/KMZ

Coordinate reference system: GDA2020 / MGA Zone 56 (EPSG:7856) or GDA94 / MGA Zone 56 (EPSG:28356) preferred, but any projected or geographic CRS is acceptable.

## Purpose of Request

This data is being sought for the purpose of building a planning compliance assessment tool that helps applicants, planners, and consultants understand the development controls applicable to specific lots in [COUNCIL NAME]. The tool cross-references DCP and LEP controls with lot-level spatial data to provide accurate, up-to-date planning information.

The data will be used solely for planning compliance assessment purposes and will not be redistributed as raw spatial data. It will be ingested into a spatial database and queried per-lot at the time of a compliance check.

## Nature of Request

I am making this request informally in the first instance, as encouraged by Section 8 of the GIPA Act. Many of these datasets are already served through Council's online GIS mapping viewers (e.g., [COUNCIL MAPPING URL IF KNOWN]) — I am requesting the underlying spatial data files rather than rendered map images.

If this data can be provided informally without a formal GIPA application, I would greatly appreciate that. If a formal application is required, please advise and I will submit the appropriate form and processing fee.

## Relevant Provisions

- **Section 5 GIPA Act**: There is a presumption in favour of disclosure of government information.
- **Section 8 GIPA Act**: Agencies are encouraged to release information proactively and informally where possible.
- **Section 18 GIPA Act**: Open access information includes information contained in documents held by the agency that relates to the exercise of its functions.

This spatial data underpins published DCP controls and is already rendered publicly through Council's online mapping tools. It does not contain personal information and there is a clear public interest in its release to support informed planning applications.

## Contact

Please do not hesitate to contact me if you require any clarification regarding this request.

Kind regards,

**Lawrence McDonell**
Solvyra Pty Ltd

---

## Council-Specific Customisations

### Northern Beaches Council
- **DCP:** Warringah DCP 2011 (as amended May 2016)
- **Key layer:** DCP Map — Site Coverage (Section B4)
- **Mapping URL:** pubapp.northernbeaches.nsw.gov.au/icongis/planningmap.html
- **ArcGIS REST (locked):** maps.northernbeaches.nsw.gov.au/arcgis/rest/services/NBC_PWM_LEPs/MapServer
- **Contact:** council@northernbeaches.nsw.gov.au
- **Address:** 725 Pittwater Road, Dee Why NSW 2099

### Sutherland Shire Council
- **DCP/LEP:** Sutherland Shire LEP 2015, cl 6.14 Landscape Area Map
- **Key layer:** Landscape Area Map (defines landscaping % by area)
- **Contact:** ssc@ssc.nsw.gov.au
- **Address:** 4-20 Eton Street, Sutherland NSW 2232

### Woollahra Municipal Council
- **DCP:** Woollahra DCP 2015 (amended December 2024)
- **Key layers:** Residential Precincts (Ch B1), Heritage Conservation Area boundaries
- **Contact:** records@woollahra.nsw.gov.au
- **Address:** 536 New South Head Road, Double Bay NSW 2028

### Georges River Council
- **LEP:** Georges River LEP 2021, cl 6.12 Foreshore Scenic Protection Area
- **Key layer:** FSPA boundary
- **Contact:** mail@georgesriver.nsw.gov.au
- **Address:** Corner of Macarthur Street and MacMahon Street, Hurstville NSW 2220

### Canterbury-Bankstown Council
- **DCP:** Canterbury Bankstown DCP 2023 (Amendment 11)
- **Key layers:** Former LGA boundary (Bankstown/Canterbury split), any precinct maps
- **Contact:** council@cbcity.nsw.gov.au
- **Address:** 66 Rickard Road, Bankstown NSW 2200

### Marrickville (Inner West Council)
- **DCP:** Marrickville DCP 2011
- **Key layer:** Planning Precincts Map (Part 9, 48 precincts)
- **Contact:** council@innerwest.nsw.gov.au
- **Address:** 2-14 Fisher Street, Petersham NSW 2049

### Ku-ring-gai Council
- **DCP:** Ku-ring-gai DCP (amended)
- **Key layers:** Character area maps, heritage conservation area precincts
- **Contact:** kmc@kmc.nsw.gov.au
- **Address:** 818 Pacific Highway, Gordon NSW 2072
