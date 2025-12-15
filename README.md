# EV Map Scripts

A geospatial data processing pipeline for generating EV charging infrastructure priority and feasibility maps across California jurisdictions.

## Overview

This repository contains Python scripts that process utility circuit line data, federal funding zones, environmental indicators, and demographic data to create pixel-based maps for identifying optimal EV charging infrastructure locations.

The pipeline outputs two types of maps for each jurisdiction:
- **Priority maps**: Identify high-priority areas based on demographic, environmental, and equity factors
- **Feasibility maps**: Show technical feasibility based on proximity to utility infrastructure and available grid capacity

## Repository Structure

```
ev_map_scripts/
├── jurisdiction_script/          # Main processing scripts
│   ├── jscript.py               # Main jurisdiction processor
│   ├── create_utility_pixels.py # Utility line pixelation script
│   ├── config/                  # YAML configuration files
│   ├── data/                    # Input data files
│   │   ├── grids/              # Pixel grid files
│   │   ├── other/              # Utility lines, funding zones, etc.
│   │   └── [county_boundary_files]
│   └── out/                     # Output JSON files
├── pipeline_doc.md              # Detailed pipeline documentation
└── TEST_RUN.md                  # Test run verification docs
```

## Requirements

### Python Environment

```bash
# Using conda (recommended)
conda create -n geo python=3.10
conda activate geo
conda install -c conda-forge geopandas numpy pandas scipy matplotlib pyyaml fiona shapely

# Or using pip
pip install geopandas numpy pandas scipy matplotlib pyyaml fiona shapely
```

### System Requirements

- **RAM**: 16-32GB recommended for pixelation process
- **Storage**: ~5GB for data files
- **OS**: macOS, Linux, or Windows

## Usage

### 1. Generate Utility Pixel Grid (Optional)

Only run this when utility circuit line data is updated (typically 2x per year).

```bash
cd jurisdiction_script
python create_utility_pixels.py \
  -i data/other/utility_lines.geojson \
  -o data/grids/utilities_pixels.json \
  -b 75
```

**What this does:**
- Creates a 100m x 100m grid covering California (~98 million points)
- Buffers utility lines by 75 meters
- Clips grid to areas near utility infrastructure (~2 million pixels)
- Takes 45-90 minutes depending on hardware

### 2. Process Jurisdictions

Generate priority and feasibility maps for specific jurisdictions:

```bash
cd jurisdiction_script
python jscript.py config_file
```

Replace `config_file` with the name of your YAML config file (without .yaml extension).

**Example:**
```bash
python jscript.py alameda_berkeley
```

**Output files:**
- `out/[jurisdiction]_priority.json` - Priority pixel map
- `out/[jurisdiction]_feasibility.json` - Feasibility pixel map

### Configuration Files

Config files are located in `jurisdiction_script/config/` and specify:
- Jurisdiction names and boundary files
- Pixel grid sources (priority vs feasibility)
- Data attributes to join (funding zones, demographics, environmental indicators)
- Join methods (binary, numeric, nearest, etc.)

## Data Sources

### Utility Circuit Lines
- Pacific Gas & Electric (PG&E)
- Southern California Edison (SCE)
- San Diego Gas & Electric (SDG&E)
- Los Angeles Department of Water and Power (LADWP)

### Federal Funding Zones
- NEVI (National Electric Vehicle Infrastructure)
- IRS 30C Tax Credit eligible areas

### Environmental & Demographic Data
- CalEnviroScreen
- EPA EJScreen
- CEJST (Climate and Economic Justice Screening Tool)
- US Census ACS data (population, disabilities, commute times, etc.)

### Jurisdiction Boundaries
- US Census Bureau TIGER Line shapefiles

See [pipeline_doc.md](pipeline_doc.md) for detailed data source URLs and update procedures.

## Pipeline Workflow

1. **Data Acquisition**: Download and process utility circuit line data from each utility provider
2. **Data Cleaning**: Standardize columns, convert units, add utility identifiers
3. **Concatenation**: Combine all utility lines into single `utility_lines.geojson`
4. **Pixelation**: Convert utility lines to 100m x 100m pixel grid
5. **Attribute Joining**: Add demographic, environmental, and funding attributes via spatial joins
6. **Output**: Generate priority and feasibility JSON files for each jurisdiction

## Key Scripts

### `create_utility_pixels.py`

Converts utility line data into a pixel grid covering areas within 75m of utility infrastructure.

**Arguments:**
- `-i, --input`: Input utility lines GeoJSON file
- `-o, --output`: Output pixel grid GeoJSON file
- `-b, --buffer`: Buffer distance in meters (default: 75)

### `jscript.py`

Main processing script that clips pixel grids to jurisdiction boundaries and joins attributes.

**Arguments:**
- `config`: Name of YAML config file (without extension)

**Process:**
- Reads jurisdiction boundaries
- Clips priority/feasibility pixel grids to each jurisdiction
- Performs spatial joins to add attributes (binary, numeric, nearest neighbor, etc.)
- Exports jurisdiction-specific priority and feasibility JSON files

## Output Format

Output files are GeoJSON FeatureCollections with 100m x 100m polygon features:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [...]
      },
      "properties": {
        "nevi": 1,
        "irs30c": 0,
        "pge": 1,
        "pop": 2500,
        ...
      }
    }
  ]
}
```

## Performance Notes

- **Pixelation**: Memory-intensive, requires 16-32GB RAM, takes 45-90 minutes
- **Jurisdiction processing**: Faster, typically minutes per jurisdiction
- **File sizes**: Output files are 300-500MB per jurisdiction

## Documentation

- [pipeline_doc.md](pipeline_doc.md) - Comprehensive pipeline documentation with data processing steps
- [TEST_RUN.md](TEST_RUN.md) - Test run verification and expected outputs
