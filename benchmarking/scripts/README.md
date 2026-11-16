# Benchmarking Scripts

This directory contains all scripts for the DVM-DOS-TEM ground temperature benchmarking workflow.

## Directory Structure

```
scripts/
├── download_data/           # Data acquisition scripts
│   ├── 00_master_download.sh       # Master coordinator for all downloads
│   ├── download_pfak.py            # PF-AK dataset download helper
│   └── download_era5.py            # ERA5 climate data download
├── prepare_inputs/          # Input file preparation (to be created)
├── run_model/               # Model execution scripts (to be created)
└── calculate_metrics/       # Benchmarking metrics (to be created)
```

## Phase 1 Workflow

### 1. Data Acquisition

**Master Script**: `download_data/00_master_download.sh`

Coordinates all data downloads for Phase 1 prototype stations (Deadhorse, Toolik).

```bash
cd download_data
./00_master_download.sh
```

This script:
- Generates PF-AK download instructions (manual download required)
- Downloads ERA5 climate data (requires CDS API setup)
- Reports status and next steps

---

#### PF-AK Dataset Download

**Script**: `download_data/download_pfak.py`

**Usage**:
```bash
python3 download_pfak.py --dest-dir ../data/observations/synthesis
```

**What it does**:
- Generates download instructions for PF-AK v0.1 dataset
- Creates placeholder directory structure
- Documents required files

**Manual Steps Required**:
1. Visit https://arcticdata.io/catalog/view/doi:10.18739/A2KG55
2. Download all data files (ground temperature, metadata, snow, soil moisture)
3. Place in `../data/observations/synthesis/`

---

#### ERA5 Climate Data Download

**Script**: `download_data/download_era5.py`

**Prerequisites**:
1. Register at https://cds.climate.copernicus.eu/
2. Get API key from https://cds.climate.copernicus.eu/api-how-to
3. Create `~/.cdsapirc`:
   ```
   url: https://cds.climate.copernicus.eu/api/v2
   key: YOUR_UID:YOUR_API_KEY
   ```
4. Install Python client: `pip install cdsapi`

**Usage**:
```bash
# Download for default prototype stations (Deadhorse, Toolik)
python3 download_era5.py --dest-dir ../data/climate/ERA5

# Download for specific stations
python3 download_era5.py \
    --dest-dir ../data/climate/ERA5 \
    --stations Deadhorse Toolik Smith_Lake \
    --start-year 1997 \
    --end-year 2016
```

**What it does**:
- Downloads ERA5 monthly data for specified stations
- Variables: precipitation, solar radiation, dewpoint, temperature, pressure
- Creates station-specific subdirectories
- Generates metadata files

**Runtime**: 10-30 minutes (depends on CDS queue)

---

### 2. Model Setup

**Script**: `01_setup_model.sh` (in parent `scripts/` directory)

**Usage**:
```bash
cd ..  # Go to scripts/ directory
./01_setup_model.sh
```

**What it does**:
- Clones DVM-DOS-TEM from https://github.com/Elchin/dvm-dos-tem
- Checks out `wetland/reburn-switch` branch
- Checks for required dependencies
- Builds the model with CMake
- Tests the executable

**Dependencies** (Ubuntu/Debian):
```bash
sudo apt-get install -y build-essential cmake libnetcdf-dev \
    libboost-all-dev libjsoncpp-dev libreadline-dev git
```

**Dependencies** (macOS):
```bash
brew install cmake netcdf boost jsoncpp readline
```

---

### 3. Input Preparation (To Be Created)

**Planned Scripts**:
- `prepare_inputs/extract_pfak_station.py` - Extract station data from PF-AK
- `prepare_inputs/extract_era5_station.py` - Extract ERA5 at station coordinates
- `prepare_inputs/create_climate_forcing.py` - Combine into historic-climate.nc
- `prepare_inputs/create_auxiliary_inputs.py` - Create vegetation, drainage, topo files
- `prepare_inputs/00_prepare_all_inputs.sh` - Master coordinator

**Purpose**: Convert observational data to DVM-DOS-TEM input format (NetCDF)

---

### 4. Model Execution (To Be Created)

**Planned Scripts**:
- `run_model/run_station.sh` - Run model for single station
- `run_model/run_all_prototypes.sh` - Run all Phase 1 stations

**Purpose**: Execute spin-up and transient model runs

---

### 5. Metric Calculation (To Be Created)

**Planned Scripts**:
- `calculate_metrics/extract_model_output.py` - Extract at observation depths
- `calculate_metrics/calculate_temperature_metrics.py` - Bias, RMSE, correlation
- `calculate_metrics/calculate_derived_indices.py` - MAAT, MAGST, MAGT, DDF, DDT, FN
- `calculate_metrics/plot_time_series.py` - Model vs observed time series
- `calculate_metrics/plot_scatter.py` - Scatter plots with regression
- `calculate_metrics/plot_depth_profiles.py` - Temperature depth profiles
- `calculate_metrics/generate_metric_table.py` - Summary tables
- `calculate_metrics/calculate_all_metrics.sh` - Master coordinator

**Purpose**: Calculate benchmarking metrics and generate validation plots

---

## Script Development Status

| Directory | Status | Scripts |
|-----------|--------|---------|
| `download_data/` | ✓ Complete | 3 scripts ready |
| `prepare_inputs/` | ⚬ Pending | 5 scripts planned |
| `run_model/` | ⚬ Pending | 2 scripts planned |
| `calculate_metrics/` | ⚬ Pending | 8 scripts planned |

**Legend**: ✓ Complete | ⚬ Pending

---

## Python Environment

**Required Packages**:
```bash
pip install cdsapi netCDF4 numpy pandas xarray matplotlib scipy
```

**Optional** (for advanced analysis):
```bash
pip install cartopy geopandas rasterio
```

---

## Common Issues and Solutions

### CDS API Issues

**Problem**: `cdsapi` not configured  
**Solution**: Create `~/.cdsapirc` with your API key (see ERA5 section above)

**Problem**: ERA5 download fails with timeout  
**Solution**: CDS service may be busy. Try again later or use smaller date ranges.

---

### NetCDF Library Issues

**Problem**: `libnetcdf.so` not found during model build  
**Solution**: Install NetCDF development package:
```bash
# Ubuntu/Debian
sudo apt-get install libnetcdf-dev

# macOS
brew install netcdf
```

---

### Model Build Issues

**Problem**: CMake cannot find Boost  
**Solution**: Install Boost development package:
```bash
# Ubuntu/Debian
sudo apt-get install libboost-all-dev

# macOS
brew install boost
```

---

## Documentation

- **Workflow Guide**: `../PHASE1_WORKFLOW.md` - Complete Phase 1 workflow
- **Data Sources**: `../metadata/data_sources.md` - Data source documentation
- **Station Inventory**: `../metadata/station_inventory.csv` - Station metadata
- **Benchmarking Plan**: `/cursor/stores/self/docs/ground-temperature-benchmarking-plan.md`

---

## References

- **PF-AK**: Wang et al. (2018), *Earth System Science Data*, 10, 2311-2328
- **ERA5**: Hersbach et al. (2020), *QJRMS*, 146, 1999-2049
- **Obu et al.**: (2019), *Earth-Science Reviews*, 193, 299-316

---

**Last Updated**: November 16, 2026  
**Phase**: 1 (Prototype setup)
