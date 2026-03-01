# Simple Georeferencing with OSM Base Layer

## The Problem with the "Automated" Method

The automated scripts I created are **more complicated** than just doing it manually because:
- You still have to click points in QGIS anyway
- Geocoding can fail and need manual fixes
- Managing Python scripts adds complexity

## The Better Way: Manual + OSM Base Layer

**Key insight**: QGIS Georeferencer has a **"From Map Canvas"** button that lets you click coordinates from the main QGIS window instead of typing them!

### Setup (One Time Only)

**Option 1: Use QGIS MCP** (Already done for you!)
```python
# Run via MCP - ALREADY COMPLETED
# OpenStreetMap layer is now in your QGIS
```

**Option 2: Add OSM Manually**
1. In QGIS main window: Layer → Add Layer → Add XYZ Tiles
2. Click "New"
3. Name: `OpenStreetMap`
4. URL: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
5. Click OK → Add

**You now have a street map base layer showing all of Sydney!**

---

## Improved Workflow (Per Precinct)

### Step 1: Find the Precinct on OSM
1. In QGIS main window, zoom to the precinct area
   - Example for Precinct 3 (Stanmore North):
   - Type in search bar: "Stanmore, NSW"
   - Or manually zoom to the area

### Step 2: Open Georeferencer
1. Layer → Georeferencer
2. File → Open Raster
3. Load the `*_span.pdf` file for the precinct

### Step 3: Add Control Points (THE EASY WAY)

For each control point (need 4 minimum):

**Old way** (complicated):
1. Open Google Maps in browser
2. Search for intersection
3. Right-click to get coordinates
4. Copy coordinates
5. Paste into QGIS

**NEW way** (simple):
1. Click **"Add Point"** button in Georeferencer
2. Click an **intersection on the PDF map**
3. **Click "From Map Canvas"** button (instead of entering coordinates)
4. QGIS switches to main window showing OSM layer
5. **Click the same intersection on the OSM map**
6. Coordinates are captured automatically!
7. Repeat for 3-4 more points

### Step 4: Configure & Run
1. Settings → Transformation settings:
   - Transformation type: **Polynomial 1**
   - Resampling: **Cubic**
   - Target SRS: **EPSG:4326**
   - Output raster: `output/precinct_X_georeferenced.tif`
   - Check: ☑ Load in QGIS when done

2. File → **Start Georeferencing**

3. Toggle the georeferenced layer on/off to verify alignment with OSM

---

## Why This Is Better

| Approach | Time per Precinct | Complexity | Reliability |
|----------|-------------------|------------|-------------|
| **Google Maps lookups** | ~8 minutes | Medium (switch apps) | High |
| **My automated scripts** | ~5 minutes | High (manage scripts, fix failures) | Medium |
| **OSM + "From Map Canvas"** | **~3 minutes** | **Low (all in QGIS)** | **High** |

---

## Complete Example: Precinct 3 (Stanmore North)

### 1. Load the PDF in Georeferencer
```
output/Marrickville DCP 2011 - 9 3 Stanmore North Precinct 3/auto/Marrickville DCP 2011 - 9 3 Stanmore North Precinct 3_span.pdf
```

### 2. Add 4 Control Points Using "From Map Canvas"

Look for these intersections on both the PDF and OSM:

| Point | Intersection | Location |
|-------|-------------|----------|
| 1 | Crystal Street & Parramatta Road | NW corner |
| 2 | Kingston Road & Parramatta Road | NE corner |
| 3 | Crystal Street & Railway line | SW corner (near Stanmore Station) |
| 4 | Kingston Road & Railway line | SE corner |

**For each**:
- Click it on the PDF
- Click "From Map Canvas"
- Click the same spot on OSM
- Done!

### 3. Run Georeferencing

Settings:
- Polynomial 1, Cubic, EPSG:4326

Click: **Start Georeferencing**

### 4. Verify Alignment

Once loaded:
- Toggle the georeferenced layer on/off
- Streets on the PDF should align with OSM streets
- Within ~50m is acceptable

---

## Tips for Speed

1. **Keep OSM zoomed to the right area** - Don't zoom out too far
2. **Use obvious intersections** - Major roads are easier to spot
3. **Spread points across the map** - Don't cluster them
4. **4 points is enough** - Don't overthink it

---

## What About the Scripts?

**You don't need them!** The OSM + "From Map Canvas" method is simpler.

**Keep the scripts if**:
- You want to batch process later
- You need exact coordinates for documentation

**Delete them if**:
- You're doing this manually anyway
- They're confusing

---

## Time Estimate

| Task | Time |
|------|------|
| One-time OSM setup | Already done! |
| Per precinct (4 control points + georeferencing) | ~3 minutes |
| All 20 precincts | ~60 minutes |

**Same as the automated method, but simpler and more reliable!**

---

## Next Steps

1. ✅ OSM layer is already loaded in QGIS
2. Open Georeferencer
3. Load the first precinct PDF
4. Use "From Map Canvas" to add 4 control points
5. Run georeferencing
6. Repeat for remaining 19 precincts

**No Python scripts, no batch files, no geocoding failures to debug!**

Just you, QGIS, and a good cup of coffee. ☕

---

## List of 20 Precincts to Process

| # | Precinct | PDF Path |
|---|----------|----------|
| 1 | 3_ Stanmore North | `output/Marrickville DCP 2011 - 9 3 Stanmore North Precinct 3/auto/*_span.pdf` |
| 2 | 7_ Stanmore South | `output/Marrickville DCP 2011 - 9 7 Stanmore South/auto/*_span.pdf` |
| 3 | 11_ Hoskins Park | `output/Marrickville DCP 2011 - 9 11 Hoskins Park Precinct 11/auto/*_span.pdf` |
| 4 | 14_ Camdenville | `output/Marrickville DCP 2011 - 9 14 Camdenville Precinct 14/auto/*_span.pdf` |
| 5 | 15_ Enmore Park | `output/Marrickville DCP 2011 - 9 15 Enmore Park/auto/*_span.pdf` |
| 6 | 16_ Abergeldie Estate | `output/Marrickville DCP 2011 - 9 16 Abergeldie Estate/auto/*_span.pdf` |
| 7 | 17_ New Canterbury Road West | `output/Marrickville DCP 2011 - 9 17 New Canterbury Road West/auto/*_span.pdf` |
| 8 | 19_ Marrickville Road, Central | `output/Marrickville DCP 2011 - 9 19 Marrickville Road, Central/auto/*_span.pdf` |
| 9 | 22_ Dulwich Hill Station South | `output/Marrickville DCP 2011 - 9 22 Dulwich Hill Station South Precinct 22/auto/*_span.pdf` |
| 10 | 25_ St Peters Triangle | `output/Marrickville DCP 2011 - 9 25 St Peters Triangle Precinct 25/auto/*_span.pdf` |
| 11 | 27_ Barwon Park South | `output/Marrickville DCP 2011 - 9 27 Barwon Park South/auto/*_span.pdf` |
| 12 | 30_ The Warren | `output/Marrickville DCP 2011 - 9 30 The Warren/auto/*_span.pdf` |
| 13 | 33_ Princes Highway | `output/Marrickville DCP 2011 - 9 33 Princes Highway/auto/*_span.pdf` |
| 14 | 34_ Tempe Reserve | `output/Marrickville DCP 2011 - 9 34 Tempe Reserve/auto/*_span.pdf` |
| 15 | 35_ Parramatta Road | `output/Marrickville DCP 2011 - 9 35 Parramatta Road/auto/*_span.pdf` |
| 16 | 37_ King Street and Enmore Road | `output/Marrickville DCP 2011 - 9 37 King Street and Enmore Road Commercial Precinct/auto/*_span.pdf` |
| 17 | 41_ Bridge Road | `output/Marrickville DCP 2011 - 9 41 Bridge Road/auto/*_span.pdf` |
| 18 | 42_ Camperdown North | `output/Marrickville DCP 2011 - 9 42 Camperdown North/auto/*_span.pdf` |
| 19 | 44_ Carrington Road | `output/Marrickville DCP 2011 - 9 44 Carrington Road/auto/*_span.pdf` |
| 20 | 46_ Tempe Lands | `output/Marrickville DCP 2011 - 9 46 Tempe Lands Precinct/auto/*_span.pdf` |

Find them easily:
```bash
find output -name "*_span.pdf" | grep "Marrickville DCP 2011 - 9 " | sort
```

---

**TL;DR**: Use OSM layer + "From Map Canvas" in QGIS Georeferencer. Way simpler than scripts!
