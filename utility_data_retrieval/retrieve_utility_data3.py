import argparse
import requests
import time
from requests.exceptions import ConnectionError
import sys
import geopandas as gpd

max_retries = 20
delay = 3

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

def write_geojson_file(features, utility):
    features.set_crs(epsg=4326, inplace=True)
    features.to_file(utility + '_load.geojson', driver='GeoJSON')

def update_min_value_utility(row):
    if row['Capacity_Range_KW'] == '>7500':
        return 7500.0
    elif '-' in row['Capacity_Range_KW']:
        return int(row['Capacity_Range_KW'].split('-')[0])

utility_list = ["pge", "sdge", "ladwp", "socaled"]

urls = {
    "pge" : "https://services2.arcgis.com/mJaJSax0KPHoCNB6/arcgis/rest/services/DRPComplianceRelProd/FeatureServer/3/query",
    "sdge" : "https://services.arcgis.com/S0EUI1eVapjRPS5e/ArcGIS/rest/services/ICA_MAP_PROD_LoadCapacityGrids_VW/FeatureServer/0/query",
    "ladwp" : "https://services7.arcgis.com/ZzOj15zjzIfDG8aL/arcgis/rest/services/PowerCapacity/FeatureServer/0/query",
    "socaled" : ["https://drpep.sce.com/arcgis_server/rest/services/Hosted/ICA_Layer/FeatureServer/2/query", "https://drpep.sce.com/arcgis_server/rest/services/Hosted/ICA_Layer/FeatureServer/3/query"],
}

params = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
    "resultOffset": 0,
    "resultRecordCount": 1000,
}

def run(utility_list):
    for ul in utility_list:
        match ul:
            case "pge":
                features = load_features_from_arcgis(urls["pge"], params)
                features = features[['LoadCapacity_kW', 'geometry']]
                features = features.rename(columns={'LoadCapacity_kW': 'load_kw'})
                features['Utility'] = 'pge'
                write_geojson_file(features, 'pge')
            case "sdge":
                features = load_features_from_arcgis(urls["sdge"], params)
                features['load_kw'] = features['ICAWOF_UNILOAD'] * 1000
                features = features[['load_kw', 'geometry']]
                features['Utility'] = 'sdge'
                write_geojson_file(features, 'sdge')
            case "ladwp":
                features = load_features_from_arcgis(urls["ladwp"], params)
                features['load_kw'] = features.apply(update_min_value_utility, axis=1)
                features = features[['load_kw', 'geometry']]
                features['Utility'] = 'ladwp'
                write_geojson_file(features, 'ladwp')
            case "socaled":
                features1 = load_features_from_arcgis(urls["socaled"][0])
                features1['load_kw'] = (features1['ica_overall_load'].astype('float')) * 1000
                features1 = features1[['load_kw', 'geometry']]
                features2 = load_features_from_arcgis(urls["socaled"][1])
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

