"""
Utility line data retrieval script. It robustly donwloads Geojson of the utility line data from ArcGIS Service REST services. It handles errors
in ArcGIS server (connection drops and timeouts) so all the data can be downloaded without interuption. It can download data from PGE, SDGE, LADWP
and SOCALED, with the option to download all or just a set of utilities.

Usage
-----

python retrieve_utility_data.py

optionally

python retrieve_utility_data.py -ul pge
python retrieve_utility_data.py -ul sdge socaled

Output
------

[utility_name]_load.geojson

By default downloads all utility data: pge_load.geojson, sdge_load.geojson, ladwp_load.geojson, socaled_load.geojson

Created Mar 2026 by Eric Lehmer (elehmer@berkeley.edu)
"""
import argparse
import requests
import time
from requests.exceptions import ConnectionError
import sys
import pandas as pd
import geopandas as gpd

# Maximum numbers of ArGIS Service errors to bridge
max_retries = 20
# Pause URL requests for n secs
delay = 3

# Reset param function, only does get_all_geojson at present
# but could be expanded in future
def set_params(option="get_all_geojson"):
    match option:
        case "get_all_geojson":
            params = {
                "where": "1=1",
                "outFields": "*",
                "f": "geojson",
                "resultOffset": 0,
                "resultRecordCount": 1000,
            }
            return params
        case _:
            params = {
                "where": "1=1",
                "outFields": "*",
                "f": "geojson",
                "resultOffset": 0,
                "resultRecordCount": 1000,
            }
            return params

# Function that retrieves data from ArcGIS Server REST service URL
# Uses global max_retries and delay to control how many attempts to
# make to get data without interuption.
def load_features_from_arcgis(base_url, params):
    features = []
    while True:
        print(f"Fetching offset {params['resultOffset']}")
        for attempt in range(max_retries):
            try:
                response = requests.get(base_url, params=params, timeout=60)
                data = response.json()
                features.extend(data["features"])
                params["resultOffset"] += params["resultRecordCount"]
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("Max retries exceeded. Exiting.")
                    raise
        if "features" not in data or not data["features"]:
            break
    return gpd.GeoDataFrame.from_features(features)

# Function that writes GeoDataFrame to GeoJSON in the same directory
def write_geojson_file(features, utility):
    features.set_crs(epsg=4326, inplace=True)
    features.to_file(utility + '_load.geojson', driver='GeoJSON')

# Function that gets the minimum capcity value from a range in certain
# utility datasets. This may need to modified in future if utility changes
# how they attribute the Capacity_Range_KW field. Check sources before running.
def update_min_value_utility(row):
    if row['Capacity_Range_KW'] == '>7500':
        return 7500.0
    elif '-' in row['Capacity_Range_KW']:
        return int(row['Capacity_Range_KW'].split('-')[0])

# Default utility list, if no -ul arguments then it runs on all of them
utility_list = ["pge", "sdge", "ladwp", "socaled"]

# Dictionary of utility line data URLS. These may need to be updated in the future if
# changes are made to the ArcGIS Server REST services. Check sources before running.
urls = {
    "pge" : "https://services2.arcgis.com/mJaJSax0KPHoCNB6/arcgis/rest/services/DRPComplianceRelProd/FeatureServer/3/query",
    "sdge" : "https://services.arcgis.com/S0EUI1eVapjRPS5e/ArcGIS/rest/services/ICA_MAP_PROD_LoadCapacityGrids_VW/FeatureServer/0/query",
    "ladwp" : "https://services7.arcgis.com/ZzOj15zjzIfDG8aL/arcgis/rest/services/PowerCapacity/FeatureServer/0/query",
    "socaled" : ["https://drpep.sce.com/arcgis_server/rest/services/Hosted/ICA_Layer/FeatureServer/2/query", "https://drpep.sce.com/arcgis_server/rest/services/Hosted/ICA_Layer/FeatureServer/3/query"],
}

# Main run function that takes list of utilities
def run(utility_list):
    for ul in utility_list:
        print("Working on utility:" + ul)
                
        match ul:
            # For PGE capacity is in KW already. Just rename column.
            case "pge":
                features = load_features_from_arcgis(urls["pge"], set_params("get_all_geojson"))
                features = features[['LoadCapacity_kW', 'geometry']]
                features = features.rename(columns={'LoadCapacity_kW': 'load_kw'})
                features['Utility'] = 'pge'
                write_geojson_file(features, 'pge')
            # SDGE capacity is in MW so convert and add column.
            case "sdge":
                features = load_features_from_arcgis(urls["sdge"], set_params("get_all_geojson"))
                features['load_kw'] = features['ICAWOF_UNILOAD'] * 1000
                features = features[['load_kw', 'geometry']]
                features['Utility'] = 'sdge'
                write_geojson_file(features, 'sdge')
            # LADWP capcity is given as a range (i.e. >7500, 1000-1500). Take minimum value in column.
            case "ladwp":
                features = load_features_from_arcgis(urls["ladwp"], set_params("get_all_geojson"))
                features['load_kw'] = features.apply(update_min_value_utility, axis=1)
                features = features[['load_kw', 'geometry']]
                features['Utility'] = 'ladwp'
                write_geojson_file(features, 'ladwp')
            # SOCALED capcity data are in 2 services and a range in MW. Convert and concat.
            case "socaled":
                features1 = load_features_from_arcgis(urls["socaled"][0], set_params("get_all_geojson"))
                features1['load_kw'] = (features1['ica_overall_load'].astype('float')) * 1000
                features1 = features1[['load_kw', 'geometry']]
                features2 = load_features_from_arcgis(urls["socaled"][1], set_params("get_all_geojson"))
                features2['load_kw'] = (features2['ica_overall_load'].astype('float')) * 1000
                features2 = features2[['load_kw', 'geometry']]
                features = pd.concat([features1, features2], ignore_index=True)
                features['Utility'] = 'socaled'
                write_geojson_file(features, 'socaled')
            case _:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Utility Data Retriever',
        description='Downloads utility data from ArcGIS services and write it to GeoJson.'
    )

    parser.add_argument(
        '-ul', '--utility_list',
        nargs='+',
        type=str,
        default=["pge", "sdge", "ladwp", "socaled"],
        help='List of utilities to retrieve, can be any of ["pge", "sdge", "ladwp", "socaled"].'
    )

    args = parser.parse_args()

    run(args.utility_list)

