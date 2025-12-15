"""
Utility Line Pixelation Script

This script converts utility circuit line data into a 100m x 100m pixel grid.
It clips the grid to areas within 75 meters of utility infrastructure.

Usage:
    python create_utility_pixels.py --input data/other/utility_lines.geojson --output data/grids/utilities_pixels.json

Input:
    - Utility lines GeoJSON file (combined from PG&E, SDG&E, LADWP, SoCal Edison)

Output:
    - Pixel grid GeoJSON file clipped to areas near utility infrastructure
"""

import argparse
import numpy as np
import pandas as pd
import geopandas as gpd
from itertools import product
import warnings
warnings.filterwarnings('ignore')


def create_california_grid():
    """
    Create a 100m x 100m grid covering California.
    Uses NAD83 / California Albers projection (EPSG:3310).

    Returns:
        GeoDataFrame: Grid centroids in EPSG:3310
    """
    print("Creating California grid...")

    # Grid parameters (100m spacing in California Albers projection)
    # These coordinates cover all of California
    xcoords = np.arange(-381105 + 50, -381105 + (100 * 9220), 100)
    ycoords = np.arange(456105 - (100 * 10630) - 50, 456105, 100)

    print(f"  Grid dimensions: {len(xcoords)} x {len(ycoords)} = {len(xcoords) * len(ycoords):,} points")

    # Create all combinations of x,y coordinates
    combinations = np.array(list(product(xcoords, ycoords)))

    # Create GeoDataFrame with point centroids
    centroids = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(combinations[:, 0], combinations[:, 1])
    )
    centroids.set_crs('EPSG:3310', inplace=True)

    print(f"  Created {len(centroids):,} grid points")
    return centroids


def clip_to_utility_lines(centroids, utility_lines, buffer_meters=75):
    """
    Clip grid to areas within buffer_meters of utility lines.

    Args:
        centroids: GeoDataFrame of grid centroids
        utility_lines: GeoDataFrame of utility line geometries
        buffer_meters: Distance in meters to buffer utility lines (default: 75)

    Returns:
        GeoDataFrame: Clipped centroids near utility infrastructure
    """
    print(f"\nClipping grid to areas within {buffer_meters}m of utility lines...")

    # Reproject utility lines to match centroids CRS
    utility_lines_reproj = utility_lines.to_crs(centroids.crs)
    print(f"  Utility lines: {len(utility_lines_reproj):,} features")

    # Buffer utility lines
    print(f"  Buffering utility lines by {buffer_meters}m...")
    utility_buffer = utility_lines_reproj.buffer(buffer_meters)

    # Clip centroids to buffered utility lines
    print("  Clipping grid to utility buffer...")
    centroids_clipped = centroids.clip(utility_buffer)

    print(f"  Clipped to {len(centroids_clipped):,} points ({len(centroids_clipped)/len(centroids)*100:.1f}% of original)")

    return centroids_clipped


def centroids_to_squares(centroids, square_size=50):
    """
    Convert point centroids to square polygons.

    Args:
        centroids: GeoDataFrame of point geometries
        square_size: Half-width of square in meters (default: 50 for 100m squares)

    Returns:
        GeoDataFrame: Square polygons with empty properties
    """
    print("\nConverting centroids to 100m x 100m squares...")

    # Buffer points with square cap style (cap_style=3)
    # This creates 100m x 100m squares from point centroids
    squares = centroids.buffer(square_size, cap_style=3)

    # Create GeoDataFrame with empty properties (attributes will be added by jscript.py)
    squares_gdf = gpd.GeoDataFrame(geometry=squares, crs=centroids.crs)

    print(f"  Created {len(squares_gdf):,} square polygons")

    return squares_gdf


def save_output(gdf, output_path, output_crs="EPSG:4326"):
    """
    Save GeoDataFrame to file in specified CRS.

    Args:
        gdf: GeoDataFrame to save
        output_path: Output file path
        output_crs: Target CRS (default: EPSG:4326 / WGS84)
    """
    print(f"\nSaving output to {output_path}...")

    # Convert to output CRS
    if output_crs == "EPSG:4326":
        # Use OGC CRS84 for better GeoJSON compatibility
        gdf_out = gdf.to_crs("urn:ogc:def:crs:OGC:1.3:CRS84")
    else:
        gdf_out = gdf.to_crs(output_crs)

    # Save to file
    gdf_out.to_file(output_path, driver='GeoJSON')

    print(f"  Saved {len(gdf_out):,} features")
    print(f"  CRS: {gdf_out.crs}")


def run(input_file, output_file, buffer_meters=75):
    """
    Main pipeline to create utility pixel grid.

    Args:
        input_file: Path to utility lines GeoJSON
        output_file: Path for output pixel grid GeoJSON
        buffer_meters: Buffer distance in meters (default: 75)
    """
    print("=" * 70)
    print("UTILITY LINE PIXELATION")
    print("=" * 70)

    # Step 1: Create California grid
    centroids = create_california_grid()

    # Step 2: Read utility lines
    print(f"\nReading utility lines from {input_file}...")
    utility_lines = gpd.read_file(input_file)
    print(f"  Loaded {len(utility_lines):,} utility line features")
    print(f"  CRS: {utility_lines.crs}")

    # Step 3: Clip grid to utility buffer
    centroids_clipped = clip_to_utility_lines(centroids, utility_lines, buffer_meters)

    # Step 4: Convert centroids to squares
    squares = centroids_to_squares(centroids_clipped)

    # Step 5: Save output
    save_output(squares, output_file)

    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Utility Pixel Generator',
        description='Creates a 100m x 100m pixel grid clipped to areas near utility infrastructure'
    )

    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input utility lines GeoJSON file'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output pixel grid GeoJSON file'
    )

    parser.add_argument(
        '-b', '--buffer',
        type=float,
        default=75,
        help='Buffer distance in meters (default: 75)'
    )

    args = parser.parse_args()

    run(args.input, args.output, args.buffer)
