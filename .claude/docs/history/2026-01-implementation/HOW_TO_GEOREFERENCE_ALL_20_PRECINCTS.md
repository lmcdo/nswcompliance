# How to Georeference All 20 Precincts

## Quick Start (Automated Workflow)

### Option 1: Run Everything at Once (Windows)

```cmd
georeference_all_20_precincts.bat
```

This will:
1. Geocode all 20 precincts automatically
2. Display instructions for each successful precinct one by one
3. Pause between each precinct so you can follow the instructions in QGIS

### Option 2: Manual Step-by-Step

#### Step 1: Batch Geocode All Precincts

```bash
python batch_geocode_all_precincts.py
```

This will:
- Extract boundary streets from all 20 precincts
- Geocode control points automatically
- Save control points to JSON files (e.g., `precinct_3__control_points.json`)
- Show success/failure summary

**Estimated time**: ~5 minutes (with API rate limiting)

#### Step 2: Display Instructions for Each Precinct

For each successfully geocoded precinct, run:

```bash
python display_gcp_instructions.py --precinct "3_"
python display_gcp_instructions.py --precinct "7_"
python display_gcp_instructions.py --precinct "11_"
# ... etc
```

This displays formatted instructions with:
- Exact PDF file path
- Control point coordinates ready to copy-paste
- Step-by-step QGIS Georeferencer workflow

#### Step 3: Follow Instructions in QGIS

For each precinct:
1. Open QGIS Georeferencer (Layer → Georeferencer)
2. Load the PDF file shown in instructions
3. Add control points using the coordinates displayed
4. Configure transformation settings
5. Run georeferencing
6. Save .points file
7. Move to next precinct

---

## Which Precincts Will Be Processed?

**20 precincts total**:

| Precinct ID | Name |
|-------------|------|
| 3_ | Stanmore North Precinct 3 |
| 7_ | Stanmore South |
| 11_ | Hoskins Park Precinct 11 |
| 14_ | Camdenville Precinct 14 |
| 15_ | Enmore Park |
| 16_ | Abergeldie Estate |
| 17_ | New Canterbury Road West |
| 19_ | Marrickville Road, Central |
| 22_ | Dulwich Hill Station South Precinct 22 |
| 25_ | St Peters Triangle Precinct 25 |
| 27_ | Barwon Park South |
| 30_ | The Warren |
| 33_ | Princes Highway |
| 34_ | Tempe Reserve |
| 35_ | Parramatta Road |
| 37_ | King Street and Enmore Road Commercial Precinct |
| 41_ | Bridge Road |
| 42_ | Camperdown North |
| 44_ | Carrington Road |
| 46_ | Tempe Lands Precinct |

---

## Expected Success Rate

Based on Precinct 3 testing:
- **Geocoding success**: ~75% (3/4 control points)
- **Minimum required**: 3 control points per precinct
- **Expected result**: 15-18 out of 20 precincts will succeed automatically

### If a Precinct Fails

If a precinct has fewer than 3 successfully geocoded control points:

1. Check `precinct_{id}_control_points.json` to see what failed
2. Manually define control points by:
   - Reading the boundary description in `precinct_boundaries_extracted.json`
   - Identifying 4 street intersections
   - Looking up coordinates on Google Maps
   - Adding them to the JSON file

3. Re-run `display_gcp_instructions.py --precinct "{id}"`

---

## File Outputs

After running the batch script, you'll have:

| File Pattern | Description |
|--------------|-------------|
| `precinct_3__control_points.json` | Geocoded control points for Precinct 3 |
| `precinct_7__control_points.json` | Geocoded control points for Precinct 7 |
| ... | (one JSON file per successful precinct) |

After georeferencing in QGIS:

| File Pattern | Description |
|--------------|-------------|
| `output/precinct_3__georeferenced.tif` | Georeferenced map (GeoTIFF) |
| `output/precinct_3__control_points.points` | QGIS control points file |
| ... | (one set per precinct) |

---

## Troubleshooting

### "No streets extracted" Error

**Cause**: The boundary description doesn't contain clear street names

**Fix**: Manually define control points in `automate_georeferencing.py`:

```python
def parse_precinct_X_control_points() -> List[Dict]:
    return [
        {
            "description": "Street A & Street B (NW)",
            "queries": [
                "Street A, Suburb NSW",
                "Street B, Suburb NSW",
            ]
        },
        # ... 3-4 control points total
    ]
```

### "Only X control points geocoded" (X < 3)

**Cause**: Geocoding queries failed to find locations

**Fix**: Try alternative query formats or use Google Maps to manually get coordinates

### "PDF NOT FOUND"

**Cause**: The precinct PDF doesn't exist in the expected location

**Fix**: Check if the PDF exists:
```bash
find output -name "*_span.pdf" | grep "9 {precinct_num}"
```

---

## After All Precincts Are Georeferenced

Once you've georeferenced all 20 precincts in QGIS:

1. **Load all georeferenced rasters** in QGIS
2. **Create new polygon layer**: Layer → Create Layer → New Shapefile Layer
3. **Enable editing**: Click pencil icon
4. **Trace boundaries**: For each precinct map, manually digitize the boundary polygon
5. **Save to PostGIS**: Export layer to `dcp_precinct_boundaries` table

**OR** use QGIS MCP to automate polygon creation (future enhancement).

---

## Time Estimate

| Task | Time |
|------|------|
| Run batch geocoding | ~5 minutes |
| Georeference each precinct in QGIS | ~3 minutes × 20 = 60 minutes |
| Handle failed precincts manually | ~10 minutes |
| **Total** | **~1.25 hours** |

Compare to **manual workflow**: ~8 minutes × 20 = 160 minutes (~2.7 hours)

**Time saved**: ~1.5 hours

---

## Summary

**What's Automated**:
- ✅ Geocoding street intersections
- ✅ Finding PDF file paths
- ✅ Generating formatted instructions

**What's Still Manual**:
- ❌ Clicking control points in QGIS (requires visual map)
- ❌ Running transformation (1 click per precinct)
- ❌ Digitizing boundary polygons (requires judgment)

**Next Steps**: Run the batch script and start georeferencing!

```cmd
georeference_all_20_precincts.bat
```
