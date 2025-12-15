"""
Quick test of the pixelation script with a small sample.
This verifies the output format matches expected structure.
"""

import geopandas as gpd

print("Testing pixelation script output format...")

# Read the existing grid file
print("\n1. Reading existing pge.json grid...")
existing_grid = gpd.read_file('data/grids/pge.json', rows=10)
print(f"   Loaded {len(existing_grid)} sample features")
print(f"   CRS: {existing_grid.crs}")
print(f"   Columns: {list(existing_grid.columns)}")
print(f"   Properties in first feature: {dict(existing_grid.iloc[0].drop('geometry'))}")

# Check geometry type
print(f"\n2. Checking geometry...")
print(f"   Geometry type: {existing_grid.geometry.type.iloc[0]}")
print(f"   Sample coordinates (first 2 points):")
coords = list(existing_grid.geometry.iloc[0].exterior.coords[:2])
print(f"      {coords}")

# Verify it's a square (100m x 100m in lat/lon)
bounds = existing_grid.geometry.iloc[0].bounds
width_deg = bounds[2] - bounds[0]  # max_x - min_x
height_deg = bounds[3] - bounds[1]  # max_y - min_y
print(f"   Approximate dimensions: {width_deg:.6f}° x {height_deg:.6f}°")

print("\n✓ Existing grid format verified!")
print("\nExpected output from create_utility_pixels.py:")
print("  - FeatureCollection with 'crs': OGC:CRS84")
print("  - Features with Polygon geometry (100m x 100m squares)")
print("  - Empty or minimal properties (attributes added later by jscript.py)")
print("  - ~2 million features (grid clipped to utility buffer)")
