# Geospatial Innovation Facility (GIF) Edit, Transform, Load (ETL) Pipeline (2026)

## Overview

This document describes the GIF modified process for updating both the feasibility and priority sides of the EVMAP website data. It streamlines the process of retrieving the utility line data, and creating the feasibility data from it (pixelation). Outlines the process for creating the priority data from isochrones and population data with added federal funding zones, environmental indicators, and demographic data. And finally creates a statewide automated process for creating the individual jurisdiction-level data that is used in the website.

**Update Frequency**: Utility circuit line data should be updated twice annually. Other datasets are updated as needed based on availability from source agencies.

## GIF ETL PIPELINE

1. **Retrieve Utility Line Data** - Download utility circuit line data from each provider
2. **Data Cleaning** - Standardize columns, convert units, add utility identifiers
3. **Concatenation** - Combine all utility lines into single dataset
4. **Pixelation** - Convert utility lines to 100m x 100m pixel grid
5. **Attribute Joining** - Add demographic, environmental, and funding attributes
6. **Output Generation** - Create jurisdiction-specific priority and feasibility files

---

## Part 1: Retrieve Utility Line Data

In order to automate the utility line retrieval process the ArcGIS Server REST Service URL for each of the utilities, PGE, SDGE, LADWP, and SOCALED, was tracked down. The URLS are as follows:

1. PGE: https://services2.arcgis.com/mJaJSax0KPHoCNB6/arcgis/rest/services/DRPComplianceRelProd/FeatureServer/3/query
2. SDGE: https://services.arcgis.com/S0EUI1eVapjRPS5e/ArcGIS/rest/services/ICA_MAP_PROD_LoadCapacityGrids_VW/FeatureServer/0/query
3. LADWP: https://services7.arcgis.com/ZzOj15zjzIfDG8aL/arcgis/rest/services/PowerCapacity/FeatureServer/0/query
4. SOCALED: https://drpep.sce.com/arcgis_server/rest/services/Hosted/ICA_Layer/FeatureServer/2/query and https://drpep.sce.com/arcgis_server/rest/services/Hosted/ICA_Layer/FeatureServer/3/query

SOCALED has two map services as they break out the high tension wires into a separate service.

With direct connections available to the data via the Internet all the data is now able to be retrieved using 1000 record requests until all the data is retrieved. The python script has built in robustness to retry failed attempts if something goes wrong in the long download process. Once downloaded the raw data is processed to make it uniform across all 4 datasets and written out to GEOJSON.

Utility Line Data Retrieval Python Script usage:

```
python retrieve_utility_data.py
```

Optionally a subset of data can be retrieved using the `-ul` argument:

```
python retrieve_utility_data.py -ul pge # Only retrieves the PGE dataset
```

The script take a hour or so to run through all the data downloading and processing.

The outputs of the script are:

`pge_load.geojson` `sdge_load.geojson` `ladwp_load.geojson` `socaled_load.geojson`

## Part 2: Combining Utility Line Data

Once the utility line data has been successfully downloaded, standardized and output as GEOJSON by the `retrieve_utility_data.py` script, the data needs to be combined into the statewide utility line dataset in order for it to be pixelated to create the feasibility layer.

This is accomplished by running the simple combining script:

```
python utility_data_combiner.py -f pge_load.geojson sdge_load.geojson ladwp_load.geojson socaled_load.geojson
```

The individual utility files are concatenated into one file:

`utility_lines.geojson`

This can then be copied into the `jurisdiction_script/data/other` directory for use in the utility line pixelation script located in the `jurisdiction_script` directory:

```
python create_utility_pixels.py --input data/other/utility_lines.geojson --output data/grids/utilities_pixels.json
```

This process does require 20-30GB of RAM. This will produce the following file:

`data/grids/utilities_pixels.json`

These are the final utility datasets needed for the jurisdiction script to create the individual feasibility layers.

## Part 3: Updating the Priority Dataset

The process of updating the priority side of the website data involves downloading the new set of EV charging stations CSV, processing it, then using that as a basis for calculating the number of stations within 10 mins walking and driving distance using the MapBox Isochrones API. This is then combined with the raw population pixels to form the updated population dataset used in the jurisdicion script.

**Download AFDC Data**

The latest version of the Alternative Fuels Data Center dataset can be acquired by filling out the form at this URL:

[Alternative Fuels Data Center Data Downloads](https://afdc.energy.gov/data_download)

It wil be named similarly to this example:

`alt_fuel_stations (Mar 2 2026).csv`

Place the file in the `charger_script/data` directory.

**Create EVChargingStations GEOJSON files**

You can then run the following python script in the `charger_script` directory to generate the needed GEOJSON files:

```
python stations_to_json.py -i alt_fuel_stations (Mar 2 2026).csv
```

This outputs the L2 and DCF charging station locations to the following files in the `charger_script/data` directory:

`EVChargingStations_DCF.json` `EVChargingStations_L2.json`

**Generate Isochrones**

The `EVChargingStations` are the input files needed for the Isochrones generation step that follows. The [MapBox Isochrone API](https://docs.mapbox.com/api/navigation/isochrone/) is used to calculate for each EV charging station how many chargers are in a 10 min travel time (L2: walk, DCF: drive). The following script will generate the isochrone files:

```
python generate_isochrones.py 
```

This will output the following files to the `charger_script\isochrones` directory:

`isochrones_drive_DCF_10.json` `isochrones_walk_L2_10.json`

**Generate Updated Population Dataset**

Once the isochrone datasets are created the updated population dataset can be generated that is the main input into the priority dataset. The following command will generate the updated population dataset:

```
python iso_to_px.py i2p_march_2026
```

Where `i2p_march_2026` is a configuration file in `charger_script/config` that contains the paths to the raw population dataset, the isochrones directory, the EV charging stations CSV, and the output directory. The `mode: 2` option tells the script to use the L2 (walk) and DCF (drive) 10 min travel times. The output of this command will be in `charger_script/data/out` and it will be:

`pop_updated.json`

This can then be copied to the `jurisdiction_script/data/pop` directory for use by the jurisdiction scripting.

## Part 4: Jurisdiction Processing

A modified jurisdiction script can now run through all the jurisdictions in the state that are a part of the web application and generate the feasibility and priority datasets for each of these jurisdictions. The `jscript_statewide.py` script reads the contents of the `jursidiction_script/data/boundaries` directory to determine which jurisdictions to process. It follows the structure that exists on the S3 bucket with county directories followed by the cities to include. Another mirror directory structure exists in `jurisdiction_script/out/CA` that accepts the output feasibility/priority datasets. These directory structures need to be synced for the script to function properly.

To execute the statewide jurisdiction script run:

```
python jscript_statewide.py statewide
```

This will use the `jurisdiction_scripts/config/statewide.yaml` config file, whcih contains all the necessary parameters for the feasibility and priority layer generation, but is missing the `jurisdiction` section that the single jurisdiction generation script uses. The jurisdictions are controlled by the directory structure of the `boundaries` directory.

This script takes an hour or so to generate all the feasibility and priority data for the website. They will be outputed to `jurisdiction_script/out/CA` with the form:

`[jurisdiction]_feasibility.json` `[jurisdiction]_priority.json`

These files are then ready to be uploaded to the S3 bucket using `AWS CLI` once you have acquired the necessary keys from bCloud:

```
aws s3 cp CA s3://ev-map-2/CA --recursive
```

First use the `--dryrun` option to test the copy.