# Phase 1 Workflow: DVM-DOS-TEM Ground Temperature Benchmarking

**Prototype Station Validation (1-2 Representative Stations)**

---

## Overview

Phase 1 establishes and validates the complete benchmarking workflow using 1-2 representative stations before scaling to all 72 PF-AK stations in Phase 2. This prototype phase ensures data pipelines, model configuration, and metric calculations work correctly.

**Duration**: 2-4 weeks  
**Status**: Setup initiated (Nov 16, 2026)

---

## Objectives

1. ✓ Set up directory structure for benchmarking data and model runs
2. ⚬ Download PF-AK v0.1 dataset from Arctic Data Center
3. ⚬ Download prototype station data (Deadhorse, Toolik from GI-UAF network)
4. ⚬ Download ERA5 climate data at prototype station coordinates (1997-2016)
5. ⚬ Clone and build DVM-DOS-TEM model (wetland/reburn-switch branch)
6. ⚬ Prepare single-pixel DVM-DOS-TEM input files for 1-2 prototype stations
7. ⚬ Run DVM-DOS-TEM for prototype stations (spin-up + 1997-2016)
8. ⚬ Calculate benchmark metrics (temperature, snow, soil moisture)
9. ⚬ Generate prototype plots and visualization
10. ⚬ Document complete workflow for Phase 2 scale-up

**Legend**: ✓ Complete | ⚬ Pending | ✗ Blocked

---

## Prototype Stations

### Station 1: Deadhorse
- **Network**: GI-UAF (Geophysical Institute, UAF)
- **Location**: 70.1997°N, 148.4597°W
- **Elevation**: 10 m
- **Ecosystem**: Tundra (Arctic Coastal Plain)
- **Permafrost**: Continuous (>90% coverage)
- **Drainage**: Upland (well-drained)
- **CMT**: CMT05 (Arctic/alpine tundra)
- **Rationale**: Long record, well-documented, North Slope tundra, continuous permafrost

### Station 2: Toolik
- **Network**: GI-UAF
- **Location**: 68.6250°N, 149.5972°W
- **Elevation**: 760 m
- **Ecosystem**: Tundra (Arctic foothills)
- **Permafrost**: Continuous
- **Drainage**: Upland
- **CMT**: CMT05
- **Rationale**: Arctic foothills, different elevation and microclimate from Deadhorse

### Optional Station 3: Smith Lake or Healy
- **Network**: GI-UAF
- **Location**: 63.9897°N, 145.4019°W (Smith Lake)
- **Ecosystem**: Boreal forest (black spruce)
- **Permafrost**: Discontinuous (50-90% coverage)
- **Drainage**: Lowland (poorly-drained)
- **CMT**: CMT04 (Boreal forest)
- **Rationale**: Different ecosystem (boreal vs tundra), different permafrost regime

---

## Detailed Workflow

### Step 1: Directory Setup ✓

**Status**: COMPLETE

Created comprehensive directory structure:

```
benchmarking/
├── data/
│   ├── observations/
│   │   ├── stations/alaska/      # PF-AK station data
│   │   └── synthesis/            # PF-AK aggregated files
│   ├── climate/ERA5/             # ERA5 reanalysis by station
│   └── gridded/                  # Spatial products (Phase 3)
├── model/
│   ├── dvm-dos-tem/              # Model source code (to be cloned)
│   ├── inputs/                   # Input files for prototype stations
│   ├── outputs/                  # Model output files
│   └── point_extracts/           # Extracted outputs at station depths
├── metadata/
│   ├── README.md                 # Directory overview
│   ├── station_inventory.csv    # All 72 stations with metadata
│   └── data_sources.md          # Data source documentation
├── scripts/
│   ├── download_data/           # Data acquisition scripts
│   ├── prepare_inputs/          # Input file preparation
│   ├── run_model/               # Model execution
│   └── calculate_metrics/       # Metric calculation
├── results/
│   ├── point_scale/             # Station-level results
│   ├── regional/                # Regional aggregation (Phase 2+)
│   ├── spatial/                 # Gridded comparison (Phase 3)
│   └── trends/                  # Trend analysis
└── figures/
    ├── point_scale/             # Time series, scatter, profiles
    ├── regional/                # Regional summary plots
    ├── spatial/                 # Spatial maps
    └── process/                 # Process diagnostics
```

**Files Created**:
- `metadata/README.md` - Directory structure documentation
- `metadata/station_inventory.csv` - Station metadata for all 72 sites
- `metadata/data_sources.md` - Comprehensive data source documentation

---

### Step 2: Data Acquisition ⚬

**Status**: Scripts created, awaiting execution

#### 2.1 PF-AK v0.1 Dataset

**Data Source**: Arctic Data Center  
**DOI**: https://doi.org/10.18739/A2KG55  
**URL**: https://arcticdata.io/catalog/view/doi:10.18739/A2KG55

**Required Files**:
1. Monthly ground temperature data (0.25, 0.50, 0.75, 1.00 m depths)
2. Station metadata (coordinates, CMT, soil type, drainage)
3. Soil moisture data (VWC) - subset of stations
4. Snow depth data (monthly mean and max)
5. Air temperature data (monthly means)

**Download Method**: Manual download from Arctic Data Center portal

**Script**: `scripts/download_data/download_pfak.py`
- Generates download instructions
- Documents required files
- Creates placeholder directory structure

**Action Required**:
```bash
cd benchmarking/scripts/download_data
python3 download_pfak.py --dest-dir ../../data/observations/synthesis
```

Then manually download files from Arctic Data Center.

---

#### 2.2 ERA5 Climate Data

**Data Source**: Copernicus Climate Data Store (CDS)  
**URL**: https://cds.climate.copernicus.eu/

**Variables**:
- Total precipitation (m)
- Surface solar radiation downwards (J/m²)
- 2m dewpoint temperature (K) → vapor pressure
- 2m temperature (K) - for validation/gap-fill
- Surface pressure (Pa)

**Period**: 1997-2016 (monthly means)  
**Spatial**: Nearest grid point to each station (0.25° resolution)

**Prerequisites**:
1. Register at CDS: https://cds.climate.copernicus.eu/
2. Get API key: https://cds.climate.copernicus.eu/api-how-to
3. Create `~/.cdsapirc`:
   ```
   url: https://cds.climate.copernicus.eu/api/v2
   key: YOUR_UID:YOUR_API_KEY
   ```
4. Install Python client: `pip install cdsapi`

**Script**: `scripts/download_data/download_era5.py`

**Action Required**:
```bash
# Configure CDS API first (see prerequisites above)

cd benchmarking/scripts/download_data
python3 download_era5.py \
    --dest-dir ../../data/climate/ERA5 \
    --stations Deadhorse Toolik \
    --start-year 1997 \
    --end-year 2016
```

**Expected Runtime**: 10-30 minutes (depends on CDS queue)

**Output**: 
- `data/climate/ERA5/deadhorse/era5_monthly_deadhorse_1997_2016.nc`
- `data/climate/ERA5/toolik/era5_monthly_toolik_1997_2016.nc`
- Metadata files for each station

---

#### 2.3 Master Download Script

**Script**: `scripts/download_data/00_master_download.sh`

Coordinates all data acquisition steps:
1. Runs PF-AK download script (generates instructions)
2. Checks CDS API configuration
3. Downloads ERA5 data for prototype stations
4. Reports status and next steps

**Action Required**:
```bash
cd benchmarking/scripts/download_data
./00_master_download.sh
```

---

### Step 3: Model Setup ⚬

**Status**: Script created, awaiting execution

#### 3.1 Clone DVM-DOS-TEM Repository

**Repository**: https://github.com/Elchin/dvm-dos-tem  
**Branch**: `wetland/reburn-switch` (includes enthalpy thermal method)

**Script**: `scripts/01_setup_model.sh`

This script:
1. Clones the repository (or verifies existing clone)
2. Checks out the correct branch
3. Checks for build dependencies
4. Compiles the model with CMake
5. Tests the executable

**Dependencies** (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    libnetcdf-dev \
    libboost-all-dev \
    libjsoncpp-dev \
    libreadline-dev \
    git
```

**Dependencies** (macOS):
```bash
brew install cmake netcdf boost jsoncpp readline
```

**Action Required**:
```bash
cd benchmarking/scripts
./01_setup_model.sh
```

**Expected Output**:
- Model cloned to `benchmarking/model/dvm-dos-tem/`
- Executable built at `benchmarking/model/dvm-dos-tem/build/dvmdostem`

---

### Step 4: Input File Preparation ⚬

**Status**: Pending (awaits data acquisition and model setup)

#### Required Input Files (per station)

DVM-DOS-TEM requires the following NetCDF input files for each single-pixel simulation:

1. **historic-climate.nc**
   - Air temperature (from PF-AK station observations)
   - Precipitation (from ERA5)
   - Solar radiation (from ERA5)
   - Vapor pressure (calculated from ERA5 dewpoint)
   - Monthly time series (1997-2016)

2. **run-mask.nc**
   - Single pixel mask (1 = run, 0 = skip)

3. **vegetation.nc**
   - CMT (Climate-Mapping-Terrain vegetation type)
   - From station metadata or site description

4. **drainage.nc**
   - Drainage classification (upland/lowland)
   - From station metadata

5. **topo.nc**
   - Slope, aspect, elevation
   - From DEM (Alaska IFSAR or SRTM)

6. **soil-texture.nc**
   - Soil texture class
   - From site description or regional database

7. **co2.nc**
   - Atmospheric CO₂ concentrations
   - Standard file from repository

#### Preparation Steps

1. **Extract station data from PF-AK**
   - Air temperature time series
   - Ground temperature for validation
   - Snow depth for validation
   - Soil moisture for validation

2. **Extract ERA5 data at station coordinates**
   - Nearest grid point
   - Monthly aggregations
   - Convert units as needed

3. **Combine into historic-climate.nc**
   - Station tair (primary)
   - ERA5 precip, radiation, vapor pressure
   - Fill any gaps in station data with ERA5 tair

4. **Create single-pixel auxiliary files**
   - run-mask: Single true pixel
   - vegetation: CMT from metadata
   - drainage: From station classification
   - topo: From coordinates and DEM
   - soil-texture: From site data

**Scripts to Create**:
- `scripts/prepare_inputs/extract_pfak_station.py`
- `scripts/prepare_inputs/extract_era5_station.py`
- `scripts/prepare_inputs/create_climate_forcing.py`
- `scripts/prepare_inputs/create_auxiliary_inputs.py`
- `scripts/prepare_inputs/00_prepare_all_inputs.sh` (master)

---

### Step 5: Model Execution ⚬

**Status**: Pending

#### Simulation Configuration

1. **Spin-up Phase**
   - Duration: 100+ years
   - Purpose: Equilibrate soil thermal regime
   - Climate: Recycled early period or climatology
   - Output: Final soil state for transient run

2. **Transient Phase**
   - Duration: 1997-2016 (20 years)
   - Climate: Observed + ERA5 forcing
   - Output: Monthly soil temperature, moisture, snow

#### Output Variables

**Required for Benchmarking**:
- Soil temperature at multiple depths (0.25, 0.50, 0.75, 1.00 m)
- Soil moisture (liquid water content)
- Snow depth
- Active layer thickness
- Surface temperature

**Output Format**: NetCDF (monthly or daily)

#### Run Commands

```bash
cd benchmarking/model/dvm-dos-tem/build

# Spin-up run (example)
./dvmdostem \
    --input-dir ../../inputs/deadhorse \
    --output-dir ../../outputs/deadhorse/spinup \
    --run-stage spinup \
    --max-eq-years 100 \
    --output-spec ../../config/spinup_output_spec.csv

# Transient run
./dvmdostem \
    --input-dir ../../inputs/deadhorse \
    --output-dir ../../outputs/deadhorse/transient \
    --run-stage transient \
    --start-year 1997 \
    --end-year 2016 \
    --restart-file ../../outputs/deadhorse/spinup/final_state.nc \
    --output-spec ../../config/transient_output_spec.csv
```

**Scripts to Create**:
- `scripts/run_model/run_station.sh`
- `scripts/run_model/run_all_prototypes.sh`

---

### Step 6: Benchmark Metric Calculation ⚬

**Status**: Pending

#### Point-Scale Metrics

**Temperature Metrics** (at 0.25, 0.50, 0.75, 1.00 m):
- Bias: Mean(Model - Obs) [°C]
- RMSE: Root mean squared error [°C]
- Correlation: Temporal correlation coefficient
- Phase error: Timing of annual max/min [days]
- Amplitude ratio: Model_amplitude / Obs_amplitude

**Derived Thermal Indices**:
- MAAT (Mean Annual Air Temperature)
- MAGST (Mean Annual Ground Surface Temperature)
- MAGT (Mean Annual Ground Temperature at depth)
- DDF (Degree Days Freezing)
- DDT (Degree Days Thawing)
- Frost Number (FN)
- Active layer thickness
- Freeze-up and thaw onset dates

**Snow Metrics**:
- Snow depth: Bias, RMSE, correlation
- Snow season length
- Maximum snow depth

**Soil Moisture Metrics**:
- VWC (Volumetric Water Content): Bias, RMSE
- Seasonal cycle (thawed periods only)
- Maximum summer VWC

**Scripts to Create**:
- `scripts/calculate_metrics/extract_model_output.py`
- `scripts/calculate_metrics/calculate_temperature_metrics.py`
- `scripts/calculate_metrics/calculate_derived_indices.py`
- `scripts/calculate_metrics/calculate_all_metrics.sh`

---

### Step 7: Visualization and Validation ⚬

**Status**: Pending

#### Prototype Plots

1. **Time Series**
   - Model vs. observed temperature by depth
   - Model vs. observed snow depth
   - Model vs. observed soil moisture

2. **Scatter Plots**
   - Observed vs. modeled (by depth, season)
   - 1:1 line and regression

3. **Depth Profiles**
   - Mean annual temperature with depth
   - Seasonal temperature profiles

4. **Metric Summary**
   - Table of bias, RMSE, correlation by depth
   - Comparison between stations

**Scripts to Create**:
- `scripts/calculate_metrics/plot_time_series.py`
- `scripts/calculate_metrics/plot_scatter.py`
- `scripts/calculate_metrics/plot_depth_profiles.py`
- `scripts/calculate_metrics/generate_metric_table.py`

---

### Step 8: Workflow Documentation ⚬

**Status**: In progress (this document)

#### Documentation Deliverables

1. **Workflow Guide** (this document)
   - Step-by-step instructions
   - Scripts and commands
   - Expected outputs

2. **Issue Log**
   - Problems encountered
   - Solutions implemented
   - Lessons learned

3. **Phase 2 Scale-Up Guide**
   - Batch processing approach
   - Parallelization strategy
   - Quality control procedures

**Files to Create**:
- `PHASE1_WORKFLOW.md` (this file) ✓
- `PHASE1_ISSUES.md`
- `PHASE2_SCALEUP_GUIDE.md`

---

## Progress Tracking

### Completed Tasks ✓

1. Directory structure created
2. Station inventory compiled (72 stations)
3. Data source documentation created
4. Download scripts written:
   - PF-AK download (with manual instructions)
   - ERA5 download (with CDS API)
   - Master download coordinator
5. Model setup script written
6. Workflow documentation initiated

### In Progress ⚬

- Data acquisition (manual steps required)
- Model cloning and building

### Pending ⚬

1. Input file preparation scripts
2. Model execution scripts
3. Metric calculation scripts
4. Visualization scripts
5. Actual model runs for prototype stations
6. Benchmark results analysis

### Blocked ✗

None currently

---

## Next Actions (Priority Order)

1. **Execute data download**:
   ```bash
   cd benchmarking/scripts/download_data
   ./00_master_download.sh
   ```
   - Follow manual instructions for PF-AK download
   - Configure CDS API for ERA5 download

2. **Setup and build model**:
   ```bash
   cd benchmarking/scripts
   ./01_setup_model.sh
   ```
   - Install dependencies if needed
   - Verify build completes successfully

3. **Create input preparation scripts**:
   - Extract station data from PF-AK
   - Extract ERA5 data at station coordinates
   - Combine into DVM-DOS-TEM input format

4. **Prepare inputs for Deadhorse and Toolik**:
   - Run input preparation scripts
   - Validate input files

5. **Execute model runs**:
   - Spin-up run (equilibration)
   - Transient run (1997-2016)
   - Verify outputs

6. **Calculate metrics and generate plots**:
   - Extract model outputs at observation depths
   - Calculate all benchmark metrics
   - Generate prototype plots

7. **Review and refine**:
   - Identify issues in workflow
   - Document lessons learned
   - Prepare Phase 2 scale-up guide

---

## Success Criteria

Phase 1 is complete when:

1. ✓ DVM-DOS-TEM builds and runs successfully
2. ✓ Input files prepared correctly for 2 prototype stations
3. ✓ Model runs complete without errors for both stations
4. ✓ Output files in correct format with expected variables
5. ✓ Metrics calculated successfully with reasonable values
6. ✓ Prototype plots generated and reviewed
7. ✓ Scripts are reusable with minimal modification
8. ✓ Workflow documented for Phase 2 replication

**Sanity Check Thresholds**:
- RMSE < 5°C (initial check; target < 2.5°C for production)
- Correlation > 0.5 for seasonal cycle
- Bias within ±3°C
- Model captures freeze/thaw timing within ±30 days

---

## Estimated Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| Data download (manual PF-AK) | 1-2 hours | None |
| ERA5 download | 0.5-1 hour | CDS API setup |
| Model setup and build | 0.5-1 hour | Dependencies installed |
| Input preparation scripts | 2-3 days | Data downloaded |
| Prepare inputs (2 stations) | 2-4 hours | Scripts complete |
| Model runs (spin-up + transient) | 4-8 hours | Inputs ready |
| Metric calculation scripts | 2-3 days | Model outputs available |
| Calculate metrics | 1-2 hours | Scripts complete |
| Visualization scripts | 1-2 days | Metrics calculated |
| Generate plots | 1-2 hours | Scripts complete |
| Review and documentation | 2-3 days | All tasks complete |

**Total**: 2-3 weeks (assuming serial workflow with 50% effort)

---

## Contact and Support

**Project**: DVM-DOS-TEM Ground Temperature Benchmarking  
**Reference Plan**: `/cursor/stores/self/docs/ground-temperature-benchmarking-plan.md`  
**Repository**: https://github.com/Elchin/dvmdostem-wiemip

**Key References**:
- Wang et al. (2018): *Earth System Science Data*, 10, 2311-2328
- Obu et al. (2019): *Earth-Science Reviews*, 193, 299-316
- Hersbach et al. (2020): *QJRMS*, 146, 1999-2049

---

**Last Updated**: November 16, 2026  
**Status**: Phase 1 setup initiated, data acquisition scripts ready
