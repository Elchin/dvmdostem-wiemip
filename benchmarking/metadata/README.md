# DVM-DOS-TEM Ground Temperature Benchmarking - Phase 1

## Directory Structure

This directory contains all data, scripts, and results for the DVM-DOS-TEM ground temperature benchmarking project.

### Structure Overview

```
benchmarking/
├── data/
│   ├── observations/
│   │   ├── stations/
│   │   │   └── alaska/          # Station data from GI-UAF, USGS, NPS networks
│   │   └── synthesis/           # PF-AK v0.1 processed files
│   ├── climate/
│   │   └── ERA5/                # ERA5 reanalysis data for gap-filling
│   └── gridded/                 # Spatial products (Obu et al., SMAP)
├── model/
│   ├── inputs/                  # DVM-DOS-TEM input files for prototype stations
│   ├── outputs/                 # Model output files
│   └── point_extracts/          # Extracted model outputs at station locations
├── metadata/
│   ├── station_inventory.csv   # Comprehensive station metadata
│   └── data_sources.md         # Documentation of data sources and DOIs
├── scripts/
│   ├── download_data/          # Data acquisition scripts
│   ├── prepare_inputs/         # Input file preparation scripts
│   ├── run_model/              # Model execution scripts
│   └── calculate_metrics/      # Benchmarking metric calculation
├── results/
│   ├── point_scale/            # Station-level results
│   ├── regional/               # Regional aggregation results
│   ├── spatial/                # Gridded comparison results
│   └── trends/                 # Trend analysis results
└── figures/
    ├── point_scale/            # Time series, scatter plots, depth profiles
    ├── regional/               # Regional summary plots
    ├── spatial/                # Spatial pattern maps
    └── process/                # Process-oriented diagnostic plots
```

## Phase 1: Initial Setup and Prototype (1-2 Stations)

### Objectives
1. Set up directory structure ✓
2. Download PF-AK v0.1 dataset from Arctic Data Center
3. Download prototype station data (Deadhorse or Toolik from GI-UAF network)
4. Download ERA5 climate data at prototype station coordinates for 1997-2016
5. Prepare single-pixel DVM-DOS-TEM input files for 1-2 prototype stations
6. Run DVM-DOS-TEM for prototype stations
7. Calculate benchmark metrics
8. Document workflow for Phase 2 scale-up

### Prototype Stations
- **Station 1**: Deadhorse (GI-UAF network)
  - Location: North Slope tundra, continuous permafrost
  - Long record, well-documented
- **Station 2**: Smith Lake or Healy (GI-UAF network)
  - Location: Interior Alaska, boreal forest, discontinuous permafrost

### Model Configuration
- **Repository**: https://github.com/Elchin/dvm-dos-tem
- **Branch**: wetland/reburn-switch (with enthalpy thermal method)
- **Input Strategy**: Station-observed air temperature + ERA5 gap-fill (precip, radiation, vapor pressure)
- **Period**: 1997-2016 (with pre-1997 spin-up)

## Data Sources

### Primary Datasets

1. **PF-AK v0.1: Alaska Permafrost Synthesis**
   - DOI: https://doi.org/10.18739/A2KG55
   - Coverage: 72 monitoring stations across Alaska (1997-2016)
   - Variables: Monthly ground temperatures (0.25, 0.50, 0.75, 1.00 m), soil moisture (VWC), snow depth, air temperature
   - Networks: GI-UAF (27 sites), USGS (17 sites), NPS (28 sites)

2. **ERA5 Reanalysis**
   - Source: Copernicus Climate Data Store
   - Variables: Precipitation, surface solar radiation, 2m dewpoint temperature
   - Resolution: 0.25° x 0.25°
   - Period: 1997-2016

### Secondary/Future Datasets

3. **Obu et al. (2018) Northern Hemisphere Permafrost Map**
   - DOI: 10.1594/PANGAEA.888600
   - Resolution: 1 km²
   - For Phase 3 spatial benchmarking

4. **SMAP L4 Surface and Root Zone Soil Moisture**
   - Source: NSIDC (https://nsidc.org/data/spl4smgp)
   - Resolution: 9 km
   - Period: 2015-present
   - For Phase 3 soil moisture validation

## Setup Date
Created: November 16, 2026

## References
- Wang et al. (2018): Earth System Science Data, 10, 2311-2328
- Obu et al. (2019): Earth-Science Reviews, 193, 299-316
- Detailed plan: /cursor/stores/self/docs/ground-temperature-benchmarking-plan.md
