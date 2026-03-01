# Manual Georeferencing Instructions for Precinct Maps

**Total maps to georeference:** 20 precincts
**Estimated time:** 5-10 minutes per map = 2-3 hours total
**Difficulty:** Medium (repetitive but straightforward)

---

## 20 Precinct Maps to Georeference

1. Precinct 3_: Stanmore North Precinct 3
2. Precinct 7_: Stanmore South
3. Precinct 11_: Hoskins Park Precinct 11
4. Precinct 14_: Camdenville Precinct 14
5. Precinct 15_: Enmore Park
6. Precinct 16_: Abergeldie Estate
7. Precinct 17_: New Canterbury Road West
8. Precinct 19_: Marrickville Road, Central
9. Precinct 22_: Dulwich Hill Station South Precinct 22
10. Precinct 25_: St Peters Triangle Precinct 25
11. Precinct 27_: Barwon Park South
12. Precinct 30_: The Warren
13. Precinct 33_: Princes Highway
14. Precinct 34_: Tempe Reserve
15. Precinct 35_: Parramatta Road
16. Precinct 37_: King Street and Enmore Road Commercial Precinct
17. Precinct 41_: Bridge Road
18. Precinct 42_: Camperdown North
19. Precinct 44_: Carrington Road
20. Precinct 46_: Tempe Lands Precinct

---

## Georeferencing Workflow (Step-by-Step)

### Step 1: Find the Map PDF

**IMPORTANT:** The boundary maps are in the `_span.pdf` files, NOT in the images directories.

Each precinct has a PDF with the boundary map:

```
output\Marrickville DCP 2011 - 9 [NUMBER] [Name]\auto\[Name]_span.pdf
```

**Example for Precinct 3 (Stanmore North):**
```
output\Marrickville DCP 2011 - 9 3 Stanmore North Precinct 3\auto\Marrickville DCP 2011 - 9 3 Stanmore North Precinct 3_span.pdf
```

**All 20 precincts follow this pattern** - the boundary map is always in the `_span.pdf` file.

**Note:** The `images/` directories only contain diagrams/text, not the boundary maps.

---

### Step 2: Open QGIS Georeferencer

1. In QGIS, go to **Layer → Georeferencer**
2. The Georeferencer window opens
3. Click **File → Open Raster** and select the precinct map image
4. The map image will display

---

### Step 3: Identify Control Points

You need **at least 4 street intersections** that are:
- Clearly visible on the map
- Easy to identify on Google Maps
- Spread across the entire map (not clustered)

**Good control points:**
- Major road intersections (e.g., "Crystal Street & Parramatta Road")
- Railway crossings with streets
- Corner of parks or landmarks

**Example for Precinct 3 (Stanmore North):**
1. Crystal Street & Parramatta Road (NW corner)
2. Kingston Road & Parramatta Road (NE corner)
3. Railway line & Crystal Street (SW corner)
4. Railway line & Kingston Road (SE corner)

---

### Step 4: Get Real Coordinates for Control Points

For each control point:

1. **Open Google Maps** (https://maps.google.com)
2. **Search for the intersection** (e.g., "Crystal Street & Parramatta Road, Petersham NSW")
3. **Right-click on the exact intersection** → **Click the coordinates** shown at top
4. **Copy the coordinates** (format: lat, lon)

**Example:**
- Crystal St & Parramatta Rd = `-33.8945, 151.1605`

**Write down all 4+ coordinates** before proceeding.

---

### Step 5: Add Ground Control Points in QGIS

For each control point:

1. **Click "Add Point" button** (yellow star icon) in Georeferencer toolbar
2. **Click the street intersection on the map image**
3. **Enter Coordinates window opens**
   - Enter **X (longitude):** e.g., `151.1605`
   - Enter **Y (latitude):** e.g., `-33.8945`
   - Click **OK**
4. **Repeat for all 4+ control points**

**Important:**
- X = Longitude (151.xxx for Sydney)
- Y = Latitude (-33.xxx for Sydney)
- Use negative for Southern latitudes

---

### Step 6: Configure Transformation Settings

1. Click **Settings → Transformation settings**
2. Set the following:
   - **Transformation type:** Polynomial 1 (Linear)
   - **Resampling method:** Cubic
   - **Target SRS:** EPSG:4326 - WGS 84
   - **Output raster:** Save to `output\[precinct_folder]\georeferenced_map.tif`
   - Check: ☑ Load in QGIS when done
   - Check: ☑ Use 0 for transparency
3. Click **OK**

---

### Step 7: Run Georeferencing

1. Click **File → Start Georeferencing** (green play button)
2. QGIS processes the transformation (~10 seconds)
3. Georeferenced map loads in QGIS main window
4. **Verify:** The map should align with OpenStreetMap base layer

---

### Step 8: Save Control Points

1. In Georeferencer: **File → Save GCP Points As...**
2. Save as: `output\[precinct_folder]\control_points.points`
3. This allows you to reload if you need to adjust

---

### Step 9: Verify Alignment

1. In QGIS main window, add **OpenStreetMap base layer**:
   - Layer → Add Layer → Add XYZ Layer
   - URL: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
2. Toggle the georeferenced map on/off to check alignment
3. Streets should match reasonably well (within ~50m is acceptable)

**If misaligned:**
- Go back to Georeferencer
- File → Load GCP Points (load your saved .points file)
- Adjust control points
- Re-run georeferencing

---

### Step 10: Note Completion

Once satisfied with alignment:
1. **Leave the georeferenced map open in QGIS**
2. **Move to next precinct**
3. After all 20 are done, tell Claude to digitize the boundaries via MCP

---

## Tips for Speed

1. **Use consistent intersections** - If Crystal St appears in multiple precincts, use it as a control point (coordinates are cached in your memory)

2. **Work in batches** - Do all maps that share similar geography together

3. **Don't over-optimize** - 4 control points with ~50m accuracy is sufficient for precinct boundary matching

4. **Save as you go** - Always save .points files so you can redo if needed

---

## Checklist Per Precinct

- [ ] Found map image in precinct directory
- [ ] Identified 4+ street intersections
- [ ] Got real coordinates from Google Maps
- [ ] Added control points in Georeferencer
- [ ] Configured transformation settings (EPSG:4326)
- [ ] Ran georeferencing
- [ ] Verified alignment with OpenStreetMap
- [ ] Saved control points file
- [ ] Saved georeferenced .tif file

---

## After All 20 Are Done

Tell Claude: "All 20 precinct maps are georeferenced. Ready to digitize boundaries."

Claude will then:
1. Load each georeferenced raster via QGIS MCP
2. Create a new polygon layer
3. You manually trace the boundary shown on each map
4. Claude saves to PostGIS database

**OR** if tracing is also manual:
- You trace all 20 boundaries in QGIS manually
- Save to the `Existing Precinct Boundaries` PostGIS layer
- Claude verifies they're all in the database

---

## Estimated Timeline

- **Setup first precinct:** 15 minutes (learning)
- **Each additional precinct:** 5-7 minutes
- **Total:** ~2.5 hours

**Start with Precinct 3 (Stanmore North) as it has clear boundaries in the markdown.**

Good luck! This is real cartography work - you're creating actual GIS data assets.
