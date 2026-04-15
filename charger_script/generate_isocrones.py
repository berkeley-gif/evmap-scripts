"""
Generate Isochrones from EV Charging Stations (L2 and DCF)

This script generates the isochone (number of charging stations from each "pixel"). By default creates 10 min walk and drive
distances. This can be modified by editing the main section.

Usage:
    generate_isocrones.py

Input:
    - data/EVChargingStations_L2.json
    - data/EVChargingStations_DCF.json
Output:
    - data/isochrones_walk_L2_10.json
    - data/isochrones_drive_DCF_10.json
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

from routingpy.routers import MapboxOSRM
from ratelimit import limits, sleep_and_retry

# API for MapBox Isochrones API
api_key = "GET_FROM_MAPBOX_WEBSITE"

def mb_isochrone(mb, gdf, radius = [5, 10, 15], mode="walk", t1=0):
    if mode=="walk":
        profile = "walking"
    else:
        profile = "driving"

    # Grab X and Y values in 4326
    gdf["LON_VALUE"] = gdf.to_crs(4326).geometry.x
    gdf["LAT_VALUE"] = gdf.to_crs(4326).geometry.y

    coordinates = gdf[["LON_VALUE", "LAT_VALUE"]].values.tolist()

    # Build a list of shapes
    isochrone_shapes = []

    if type(radius) is not list:
        radius = [radius]

    # Use minutes as input, but the API requires seconds
    time_seconds = [60 * x for x in radius]

    # Given the way that routingpy works, we need to iterate through the list of 
    # coordinate pairs, then iterate through the object returned and extract the 
    # isochrone geometries.  
    
    @sleep_and_retry
    @limits(calls=300, period=75)
    def call_api(c, profile, time_seconds):
        try:
            iso_request = mb.isochrones(locations = c, profile = profile,
                                        intervals = time_seconds, polygons = "true")

            for i in iso_request:
                iso_geom = Polygon(i.geometry[0])
                isochrone_shapes.append(iso_geom)
        except Exception as e:
            print(f"Caught exception: {e}")
            isochrone_shapes.append(np.nan)
    counter=0
    for c in coordinates:
        call_api(c, profile, time_seconds)
        if counter%300 == 0:
            print("Coordinate: " + str(counter))
        counter+=1

    # Here, we re-build the dataset but with isochrone geometries
    df_values = gdf.drop(columns = ["geometry", "LON_VALUE", "LAT_VALUE"])

    time_col = radius * len(df_values)

    # We'll need to repeat the dataframe to account for multiple time intervals
    df_values_rep = pd.DataFrame(np.repeat(df_values.values, len(time_seconds), axis = 0))
    df_values_rep.columns = df_values.columns

    isochrone_gdf = gpd.GeoDataFrame(
        data = df_values_rep,
        geometry = isochrone_shapes,
        crs = 4326
    )

    isochrone_gdf["time"] = time_col

    # We are sorting the dataframe in descending order of time to improve visualization
    # (the smallest isochrones should go on top, which means they are plotted last)
    # isochrone_gdf = isochrone_gdf.sort_values('time', ascending = False)

    # print(list(isochrone_gdf.columns))
    # print(isochrone_gdf)

    return(isochrone_gdf)

def run(mb, ev_chargers_list, mins, mode):
    # MapBox API instance
    mb = mb
    # Type of charger (L2, DCF)
    charger_type = ev_chargers_list[0]
    # Read in locations of chargers
    ev_chargers = gpd.read_file(ev_chargers_list[1])
    # How far to search in mins
    mins = mins
    # Walk or Drive mode
    mode = mode
    t1 = 0

    # Run the MapBox isochrone API
    isochrones = mb_isochrone(mb, ev_chargers, mins, mode, t1)

    # Use subset of DataFrame
    isochrones = isochrones[["EV Level2 EVSE Num", "EV DC Fast Count", "time", "geometry"]]
    # Convert L2 column to int
    isochrones["EV Level2 EVSE Num"] = isochrones["EV Level2 EVSE Num"].astype(int)
    # Convert DCF blank entries to NaN
    isochrones["EV DC Fast Count"] = isochrones["EV DC Fast Count"].replace("",np.nan)
    # set num_chg to either total L2 or total DCF chargers
    if mode == "walk":
        isochrones["num_chg"] = isochrones["EV Level2 EVSE Num"]
    elif mode == "drive":
        isochrones['num_chg'] = isochrones['EV DC Fast Count']

    isochrones.to_file("data/isochrones_" + mode + "_" + charger_type + "_" + mins + ".json", driver="GeoJSON")

if __name__ == "__main__":
    mb = MapboxOSRM(api_key=api_key)

    charger_files = {"walk": ["L2", "data/EVChargingStations_L2.json"],
                    "drive": ["DCF", "data/EVChargingStations_DCF.json"]}
    travel_times = [10]
    travel_modes = ["walk", "drive"]

    for mins in travel_times:
        for mode in travel_modes:
            run(mb, charger_files[mode], mins, mode)
