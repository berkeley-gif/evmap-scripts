# Test Run Documentation

### Input Files Present:
1. **utility_lines.geojson** (757MB)
   - Location: `jurisdiction_script/data/other/utility_lines.geojson`
   - Format: GeoJSON FeatureCollection
   - Content: LineString geometries with properties (OBJECTID, Load_kW, Shape_Length)
   - Features: Thousands of utility circuit line segments
   - Sample verified: First 85 features inspected

2. **pge.json** (423MB)
   - Location: `jurisdiction_script/data/grids/pge.json`
   - Format: GeoJSON FeatureCollection with CRS84
   - Content: Polygon geometries (100m x 100m squares)
   - Properties: Empty `{}` (as expected - attributes added by jscript.py)
   - This is the **existing** utility pixel grid

### Command:
```bash
cd jurisdiction_script
python3 create_utility_pixels.py \
  -i data/other/utility_lines.geojson \
  -o data/grids/utilities_pixels_NEW.json \
  -b 75
```

### Expected Process:

**Step 1: Create California Grid**
```
Creating California grid...
  Grid dimensions: 9220 x 10630 = 98,017,660 points
  Created 98,017,660 grid points
```

**Step 2: Load Utility Lines**
```
Reading utility lines from data/other/utility_lines.geojson...
  Loaded ~2,000,000 utility line features
  CRS: EPSG:4326
```

**Step 3: Clip Grid to Utility Buffer**
```
Clipping grid to areas within 75m of utility lines...
  Utility lines: ~2,000,000 features
  Buffering utility lines by 75m...
  Clipping grid to utility buffer...
  Clipped to ~1,960,000 points (2.0% of original)
```

**Step 4: Convert to Squares**
```
Converting centroids to 100m x 100m squares...
  Created ~1,960,000 square polygons
```

**Step 5: Save Output**
```
Saving output to data/grids/utilities_pixels_NEW.json...
  Saved ~1,960,000 features
  CRS: urn:ogc:def:crs:OGC:1.3:CRS84
```

**Final Output:**
```
======================================================================
COMPLETE!
======================================================================
```

### Expected Output File Format:

**utilities_pixels_NEW.json**
```json
{
  "type": "FeatureCollection",
  "name": "utilities_pixels_NEW",
  "crs": {
    "type": "name",
    "properties": {
      "name": "urn:ogc:def:crs:OGC::CRS84"
    }
  },
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-120.498302309955861, 34.566459382905272],
            [-120.498296579809860, 34.565558391050210],
            [-120.499386804890733, 34.565553650373033],
            [-120.499392547573279, 34.566454642177618],
            [-120.498302309955861, 34.566459382905272]
          ]
        ]
      }
    },
    // ... ~1,960,000 more features
  ]
}
```

**Required packages:**
- geopandas
- numpy
- pandas
- shapely (dependency of geopandas)

## To Actually Run the Script

### Option 1: Install packages globally
```bash
pip3 install geopandas numpy pandas
```

### Option 2: Use conda environment (recommended)
```bash
conda create -n geo python=3.10
conda activate geo
conda install -c conda-forge geopandas numpy pandas
cd jurisdiction_script
python create_utility_pixels.py -i data/other/utility_lines.geojson -o data/grids/utilities_pixels_NEW.json
```

### Option 3: Use existing environment
If you already have a Python environment with geospatial tools (like the one used to create the notebooks), activate it and run:
```bash
cd jurisdiction_script
python create_utility_pixels.py -i data/other/utility_lines.geojson -o data/grids/utilities_pixels_NEW.json
```

## Performance Notes

**Memory Requirements:**
- Creating 98 million grid points: ~8-16GB RAM
- Buffering utility lines: ~4-8GB RAM
- Spatial clipping operation: ~8-16GB RAM
- **Total:** Expect to need 16-32GB available RAM

**Time Estimates:**
- Grid creation: 2-5 minutes
- Loading utility lines: 30-60 seconds
- Buffering: 5-10 minutes
- Clipping (most intensive): 30-60 minutes
- Saving output: 2-5 minutes
- **Total:** 45-90 minutes depending on hardware

**Optimization Tip:**
The existing `pge.json` file works perfectly fine. You only need to regenerate it when:
- Utility circuit line data is updated
- The buffer distance needs to change (currently 75m)
- Coverage area needs to expand beyond current grid

## Next Steps After Pixelation

Once you have the new utility pixel grid, use it with jscript.py:

```bash
# Test with one jurisdiction
python jscript.py alameda_berkeley

# This will create:
# - out/alameda_berkeley_priority.json
# - out/alameda_berkeley_feasibility.json
```

The feasibility file will have attributes added by spatial joins:
- `nevi`: From data/other/nevi.json
- `irs30c`: From data/other/irs30c.json
- `pge`: From data/other/pgelines.json

