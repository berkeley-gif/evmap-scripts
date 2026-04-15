import argparse
import pandas as pd
import geopandas as gpd

def run(files):
    utility_files = {}
    filenum = 1

    for f in files:
        utility_files[filenum] = gpd.read_file(f)
        filenum += 1

    statewide = pd.concat(utility_files, ignore_index=True)
    statewide = gpd.GeoDataFrame(statewide, geometry='geometry')
    statewide.set_crs(epsg=4326, inplace=True)
    statewide.to_file('utility_lines.geojson', driver='GeoJSON')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Utility Data Combiner',
        description='Combine separate utility line data into whole state file.'
    )

    parser.add_argument(
        '-f', '--files',
        required=True,
        nargs=4,
        type=str,
        help='List of 4 utility file paths to combine. Must be to PGE, SDGE, LADWP, SOCALED.'
    )

    args = parser.parse_args()

    run(args.files)
