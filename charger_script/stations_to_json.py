"""
Alternative Fuels Data Conversion

This script converts the CSV of Alternative Fuels Station Data into JSON for use in
the isochrone scripts (to_isochrone.py)

Latest input dataset can be downloaded from here: https://afdc.energy.gov/data_download

Usage:
    stations_to_json.py --input path_to_afdc_station_csv

Input:
    - AFDC station CSV file

Output:
    - L2 and DCF EV charging stations as JSONs in the ./data directory
"""
import argparse
import geopandas as gpd

def run (input):
    chg_all_df = gpd.read_file(input)
    chg_all = gpd.GeoDataFrame(chg_all_df,geometry=gpd.points_from_xy(chg_all_df.Longitude, chg_all_df.Latitude, crs='EPSG:4326'))
    chg_all.loc[(chg_all['EV Network']=='Tesla'), 'EV DC Fast Count'].astype(int).sum()
    chg_all.loc[(~chg_all['EV Level2 EVSE Num'].isna()) & (chg_all['EV Level2 EVSE Num']!='')].to_file(r'data\EVChargingStations_L2.json', driver='GeoJSON')
    chg_all.loc[(~chg_all['EV DC Fast Count'].isna()) & (chg_all['EV DC Fast Count']!='')].to_file(r'data\EVChargingStations_DCF.json', driver='GeoJSON')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Alternative Fuels Data Conversion',
        description='Converts the CSV of Alternative Fuels Station Data into JSON.'
    )

    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Alternative Fuels Data Center station CSV file path.'
    )

    args = parser.parse_args()

    run(args.input)

