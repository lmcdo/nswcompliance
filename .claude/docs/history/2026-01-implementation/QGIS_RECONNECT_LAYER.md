# QGIS: Reconnect to Updated Precinct Boundaries

## Quick Method: Remove and Re-add Layer

Since there's no "Reload Layer" option, follow these steps:

### Step 1: Remove Current Layer

1. **Right-click** on "precint boundaries leichhardt"
2. Select **"Remove Layer"** or **"Remove"**
3. Click **Yes** to confirm

(Don't worry - the data is still in the database!)

### Step 2: Re-add from Database

1. **Layer** menu → **Add Layer** → **Add PostGIS Layers...**

2. **In the Add PostGIS Table(s) dialog:**
   - Click **"New"** if you don't have a connection, OR
   - Select existing connection to `nsw_planning`

3. **If creating new connection:**
   - Name: `nsw_planning`
   - Host: `localhost`
   - Port: `5432`
   - Database: `nsw_planning`
   - Username: `postgres`
   - Password: `Solvyra2024!`
   - Click **Test Connection** → Should say "Connection successful"
   - Click **OK**

4. **Click "Connect"** button

5. **Find the table:**
   - Expand "public" schema
   - Check the box next to **`dcp_precinct_boundaries`**
   - You should see geometry type is now: `MultiPolygon (EPSG:4326)`

6. **Click "Add"** at the bottom

### Step 3: Enable Multi-Part Editing

1. **Settings** menu → **Options**
2. Click **"Digitizing"** tab on the left
3. Check the box: **"Enable multi-part features"**
4. Click **OK**

### Step 4: Test Multi-Polygon Creation

1. Select the new layer in Layers panel
2. Click **Toggle Editing** (pencil icon)
3. Click **Add Polygon Feature** (polygon icon)
4. **Draw first polygon:**
   - Click points around first area
   - Right-click to close polygon
5. **Draw second polygon (without pressing Enter yet!):**
   - Click points around second area
   - Right-click to close second polygon
6. **Press Enter** when all parts are complete
7. Fill in precinct attributes
8. Click **Save** (floppy disk icon)

## Alternative: Close and Reopen QGIS

Sometimes QGIS needs a full restart to recognize geometry changes:

1. **Save your QGIS project** (if needed)
2. **Close QGIS completely**
3. **Reopen QGIS**
4. **Open your project** or re-add the layer

## Verification

After reconnecting, check the layer properties:

1. **Right-click** on the layer
2. Select **"Properties"**
3. Go to **"Information"** tab
4. Look for: **Geometry: MultiPolygon (4326)**

If you see "MultiPolygon", you're ready to create multi-part precincts!

## What Changed in the Database

The database table `dcp_precinct_boundaries` now:
- ✅ Accepts MULTIPOLYGON geometry (was POLYGON)
- ✅ Can store precincts with 2+ separate areas
- ✅ All existing 46 precincts converted (still 1 part each)
- ✅ Spatial index updated

You're all set to add precincts with multiple polygons!
