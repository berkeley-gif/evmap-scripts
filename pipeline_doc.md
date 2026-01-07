# Data Processing Pipeline

## Overview

This document outlines the complete data processing pipeline for generating jurisdiction-level EV charging infrastructure maps. The pipeline processes utility circuit line data, federal funding zones, environmental indicators, and demographic data to create priority and feasibility pixel grids.

**Update Frequency**: Utility circuit line data should be updated twice annually. Other datasets are updated as needed based on availability from source agencies.

## Pipeline Workflow

1. **Data Acquisition** - Download utility circuit line data from each provider
2. **Data Cleaning** - Standardize columns, convert units, add utility identifiers
3. **Concatenation** - Combine all utility lines into single dataset
4. **Pixelation** - Convert utility lines to 100m x 100m pixel grid
5. **Attribute Joining** - Add demographic, environmental, and funding attributes
6. **Output Generation** - Create jurisdiction-specific priority and feasibility files

---

## Part 1: Utility Circuit Line Processing

### 1.1 Pacific Gas & Electric (PG&E)

**Source**: [PG&E GRIP Portal](https://grip.pge.com/)

**Two acquisition methods available:**

#### Method A: Direct Download
1. Navigate to the GRIP portal
2. In the layer list, expand ICA > ICA Results
3. Click options menu (three dots) for "ICA, Load Capacity (kW)"
4. Select Export > GeoJSON

**Note**: This method may encounter server timeout issues with large datasets.

#### Method B: API Access (Recommended)

Pull data directly from the ArcGIS Feature Server:

```python
import requests
import geopandas as gpd

base_url = "https://services2.arcgis.com/mJaJSax0KPHoCNB6/arcgis/rest/services/DRPComplianceRelProd/FeatureServer/3/query"

params = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
    "resultOffset": 0,
    "resultRecordCount": 1000,
}

features = []

while True:
    print(f"Fetching offset {params['resultOffset']}")
    response = requests.get(base_url, params=params)
    data = response.json()

    if "features" not in data or not data["features"]:
        break

    features.extend(data["features"])
    params["resultOffset"] += params["resultRecordCount"]

pge = gpd.GeoDataFrame.from_features(features)
```

**Data Processing:**

```python
# Retain only necessary columns
pge = pge[['LoadCapacity_kW', 'geometry']]

# Add utility identifier
pge['Utility'] = 'pge'

# Set CRS and save
pge = gpd.GeoDataFrame(pge, geometry='geometry')
pge.set_crs(epsg=4326, inplace=True)
pge.to_file('pge_load.geojson', driver='GeoJSON')
```

> [!NOTE]
> Downloading manually using website times out.
>
> Downloading using python script above sometimes hangs part way making it hard to script this automatically. Currently, looks like this dataset has 1289568 records.

### 1.2 San Diego Gas & Electric (SDG&E)

**Source**: [SDG&E ICM API Explorer](https://icm-api-explorer.sdge.com/)

**Data Acquisition:**
1. Access the ICM API Explorer (account creation may be required)
2. Navigate to Load Capacity Grids map
3. Download as GeoJSON or Shapefile

**Data Processing:**

```python
import geopandas as gpd

# Load data
sdge = gpd.read_file("path/to/sdge.geojson")

# Verify load columns are identical
sdge['equal'] = sdge['ICAWOF_UNILOAD'] == sdge['ICAWNOF_UNILOAD']
sdge.loc[sdge['equal'] == False]  # Should return empty table

# Convert MW to kW
sdge['load_kw'] = sdge['ICAWOF_UNILOAD'] * 1000

# Retain only necessary columns
sdge = sdge[['load_kw', 'geometry']]

# Add utility identifier
sdge['Utility'] = 'sdge'

# Set CRS and save
sdge = gpd.GeoDataFrame(sdge, geometry='geometry')
sdge.set_crs(epsg=4326, inplace=True)
sdge.to_file('sdge_load.geojson', driver='GeoJSON')
```
> [!NOTE]
> No login was required for me to download. Attempt to download GeoJSON fails to execute. Was able to download Shapefile. Shapefile has shortened field names so the script needs to be modified to deal with that. ICAWOF_UNILOAD -> ICAWOF_UNI, ICAWNOF_UNILOAD -> ICAWNOF_UN
> Shapefile is in PseudoMercator so the set_crs command instead needs to be to_crs.

### 1.3 Los Angeles Department of Water and Power (LADWP)

**Source**: [LADWP Power GIS Portal](https://ladwp-power.maps.arcgis.com/apps/webappviewer/index.html?id=290be9aa52694ef39bf3088940079f62)

**Data Acquisition:**
1. Click "Download the 34.5 KV data" link
2. Unzip downloaded file to extract .kmz file
3. Convert .kmz to .gdb using ArcGIS "KMZ to Layer" tool

**Data Processing:**

```python
import geopandas as gpd
import pandas as pd
from bs4 import BeautifulSoup

# Load geodatabase
ladwp = gpd.read_file("path/to/ladwp.gdb")

# Extract popup information
def extract_popup_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}
    table = soup.find_all('table')[1]

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) == 2:
            key = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            data[key] = value

    return data

popup_info_df = ladwp['PopupInfo'].apply(extract_popup_info)
popup_info_expanded = pd.json_normalize(popup_info_df)
gdf_expanded = ladwp.drop(columns=['PopupInfo']).join(popup_info_expanded)

# Extract minimum capacity value from range
gdf_expanded['min_value'] = gdf_expanded['CAPACITY_RANGE_KW'].str.extract(r'^\s*(\d+)')

# Retain only necessary columns
ladwp = gdf_expanded[['min_value', 'geometry']]

# Add utility identifier
ladwp['Utility'] = 'ladwp'

# Set CRS and save
ladwp = gpd.GeoDataFrame(ladwp, geometry='geometry')
ladwp.set_crs(epsg=4326, inplace=True)
ladwp.to_file('ladwp_load.geojson', driver='GeoJSON')
```

### 1.4 Southern California Edison (SCE)

**Source**: [SCE DRP Portal](https://drpep.sce.com/drpep/)

**Data Acquisition:**
1. Click "ESRI API" tab
2. Navigate to "ICA Layer" > "ICA - Circuit Segments"
3. Download as GeoJSON or Shapefile
4. Also download "ICA - Circuit Segments, Non-3 Phase" if available

**Note**: SCE provides separate files for 3-phase and non-3-phase circuits. Verify whether these datasets contain unique data before concatenating. If datasets are identical, only one is needed.

**Data Processing:**

```python
import geopandas as gpd

# Load data
socaled = gpd.read_file("path/to/socaled.geojson")

# Convert MW to kW (column is stored as string)
socaled['load_kw'] = (socaled['ica_overall_load'].astype('float')) * 1000

# Retain only necessary columns
socaled = socaled[['load_kw', 'geometry']]

# Add utility identifier
socaled['Utility'] = 'socaled'

# Set CRS and save
socaled = gpd.GeoDataFrame(socaled, geometry='geometry')
socaled.set_crs(epsg=4326, inplace=True)
socaled.to_file('socaled_load.geojson', driver='GeoJSON')
```

### 1.5 Concatenate All Utility Lines

Combine all processed utility datasets into a single file:

```python
import pandas as pd
import geopandas as gpd

# Load all utility files
pge = gpd.read_file('pge_load.geojson')
ladwp = gpd.read_file('ladwp_load.geojson')
sdge = gpd.read_file('sdge_load.geojson')
socaled = gpd.read_file('socaled_load.geojson')

# Concatenate
utility_lines = pd.concat([pge, ladwp, sdge, socaled], ignore_index=True)

# Set CRS and save
utility_lines = gpd.GeoDataFrame(utility_lines, geometry='geometry')
utility_lines.set_crs(epsg=4326, inplace=True)
utility_lines.to_file('utility_lines.geojson', driver='GeoJSON')
```

**Output**: Save `utility_lines.geojson` to `jurisdiction_script/data/other/`

---

## Part 2: Pixelation

Convert utility circuit lines into a 100m x 100m pixel grid covering areas within 75 meters of utility infrastructure.

**Command:**

```bash
cd jurisdiction_script
python create_utility_pixels.py \
  -i data/other/utility_lines.geojson \
  -o data/grids/utilities_pixels.json \
  -b 75
```

**Process:**
1. Creates 100m x 100m grid covering California (~98 million grid points)
2. Buffers utility lines by 75 meters
3. Clips grid to areas within utility buffer (~2 million pixels)
4. Converts point centroids to square polygons
5. Saves output to `data/grids/utilities_pixels.json`

**Performance Requirements:**
- **Memory**: 16-32GB RAM
- **Processing Time**: 45-90 minutes
- **Output Size**: ~400-500MB

**Output**: Save `utilities_pixels.json` to `jurisdiction_script/data/grids/`

---

## Part 3: Configuration and Execution

### 3.1 Update Configuration Files

Configuration files are located in `jurisdiction_script/config/` as YAML files.

**Update the following paths:**
- **Feasibility pixels**: Update to reference new `utilities_pixels.json`
- **Utility lines**: Update to reference new `utility_lines.geojson`

### 3.2 Run Jurisdiction Processing

Execute the main processing script:

```bash
cd jurisdiction_script
python jscript.py config_file
```

Replace `config_file` with the appropriate configuration file name (without .yaml extension).

**Example:**
```bash
python jscript.py alameda_berkeley
```

**Output**: Priority and feasibility JSON files will be generated in `jurisdiction_script/out/`
- `[jurisdiction]_priority.json`
- `[jurisdiction]_feasibility.json`

---

## Part 4: Data Sources

### Jurisdiction Boundary Files
| Data Type | Source |
|-----------|--------|
| California County Boundaries | [US Census TIGER/Line](https://www2.census.gov/geo/tiger/TIGER2023/) |
| California Place Boundaries | [US Census TIGER/Line Places](https://www2.census.gov/geo/tiger/TIGER2023/PLACE/) |

### Electric Utility Circuit Line Load Capacity
| Utility | Source |
|---------|--------|
| Pacific Gas & Electric (PG&E) | [PG&E DRP Integration Capacity Map](https://www.pge.com/b2b/distribution-resource-planning/integration-capacity-map.shtml) |
| Southern California Edison (SCE) | [SCE DRP Portal](https://drpep.sce.com/drpep/) |
| San Diego Gas & Electric (SDG&E) | [SDG&E ICM API Explorer](https://icm-api-explorer.sdge.com/datasets/b5e555b96d974256b8d0da77797ea3cd/explore) |
| Los Angeles Dept. of Water & Power (LADWP) | [LADWP Power GIS Portal](https://ladwp-power.maps.arcgis.com/apps/webappviewer/index.html?id=290be9aa52694ef39bf3088940079f62) |

### Environmental Indicator Data
| Data Type | Source |
|-----------|--------|
| CalEnviroScreen 4.0 | [OEHHA CalEnviroScreen](https://oehha.ca.gov/calenviroscreen/report/calenviroscreen-40) |
| EJScreen | [Harvard Dataverse](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/JISNPL) |
| CEJST | [Harvard Dataverse](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/B6ULET) |

### Census Data (American Community Survey)
| Data Type | Source |
|-----------|--------|
| Non-White Population (2021 5-yr ACS) | [Census Data Portal](https://data.census.gov/table/ACSDP5Y2021.DP05?q=ACSDP5Y2021.DP05&g=040XX00US06$1400000) |
| Disability Characteristics (2021 5-yr ACS) | [Census Data Portal](https://data.census.gov/table/ACSST5Y2021.S1810?q=ACSST5Y2021.S1810&g=040XX00US06$1400000) |
| Commute Time (2021 5-yr ACS) | [Census Data Portal](https://data.census.gov/table/ACSDT5Y2021.B08303?q=ACSDT5Y2021.B08303&g=040XX00US06$1400000) |

---

## Notes on Environmental Indicators

**Current Implementation:**
- EJScreen and CEJST indicators use percentile rankings across US census tracts
- CalEnviroScreen provides intra-state (California-only) percentile comparisons
- This provides both interstate and intrastate comparisons for California

**Future Considerations:**
When expanding to states outside California:
- CalEnviroScreen is California-specific and unavailable for other states
- Consider using EJScreen's intrastate tract comparison option
- This would maintain both inter- and intra-state comparison capabilities using CEJST (interstate) and EJScreen (intrastate)

---

## Troubleshooting

**Common Issues:**

1. **API URL Changes**: Utility provider API endpoints may change. Check source portals for updated URLs.

2. **Memory Issues**: Pixelation process requires significant RAM. Close other applications or use a machine with more memory.

3. **Timeout Errors**: When downloading large datasets, use API-based methods rather than direct downloads.

4. **Missing Dependencies**: Ensure all required Python packages are installed:
   ```bash
   conda install -c conda-forge geopandas numpy pandas scipy matplotlib pyyaml fiona shapely beautifulsoup4
   ```

5. **CRS Mismatches**: All output files should use EPSG:4326 (WGS84). Verify CRS after loading external datasets.
