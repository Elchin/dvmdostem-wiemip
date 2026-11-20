# Data Sources for DVM-DOS-TEM Ground Temperature Benchmarking

## Primary Observational Data

### 1. PF-AK v0.1: Alaska Permafrost Synthesis

**Citation**: Wang, K., Jafarov, E., Overeem, I., Romanovsky, V., Schaefer, K., Clow, G., Urban, F., Cable, W., Piper, M., Schwalm, C., Zhang, T., Kholodov, A., Sousanes, P., Loso, M., and Hill, K. (2018). A synthesis dataset of permafrost-affected soil thermal conditions for Alaska, USA. *Earth System Science Data*, 10(4), 2311-2328.

**DOI**: https://doi.org/10.18739/A2KG55

**Source**: Arctic Data Center

**Direct URL**: https://arcticdata.io/catalog/view/doi:10.18739/A2KG55

**Coverage**:
- **Spatial**: 72 monitoring stations across Alaska
- **Temporal**: 1997-2016 (varies by station)
- **Networks**: 
  - GI-UAF (Geophysical Institute, University of Alaska Fairbanks): 27 sites
  - USGS (U.S. Geological Survey): 17 sites
  - NPS (National Park Service): 28 sites

**Variables**:
- Monthly ground temperature at standardized depths: 0.25, 0.50, 0.75, 1.00 m
- Volumetric soil water content (VWC) at shallow active layer depths (subset of stations)
- Snow depth (mean and maximum seasonal)
- Air temperature (monthly means)
- Derived thermal indices: DDF, DDT, Frost Number (FN)

**Data Format**: CSV and NetCDF files

**Quality Control**: Pre-processed, frost heave corrected, harmonized across networks

**Data Completeness**: 77% (41,667 monthly data points)

**Access Method**:
1. **Web Interface**: Download from Arctic Data Center portal
2. **DataONE API**: Using R dataone package or Python d1_client
3. **Direct Download**: Use package identifiers with Arctic Data Center API

**License**: CC0 1.0 Universal (Public Domain Dedication)

---

### 2. ERA5 Reanalysis

**Citation**: Hersbach, H., Bell, B., Berrisford, P., et al. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999-2049.

**DOI**: https://doi.org/10.1002/qj.3803

**Source**: Copernicus Climate Data Store (CDS)

**Direct URL**: https://cds.climate.copernicus.eu/

**Coverage**:
- **Spatial**: Global, 0.25° × 0.25° (~31 km at equator)
- **Temporal**: 1940-present (updated continuously)
- **Frequency**: Hourly (we use monthly aggregations)

**Variables Used**:
- Total precipitation (tp) [m]
- Surface solar radiation downwards (ssrd) [J/m²]
- 2m dewpoint temperature (d2m) [K] → converted to vapor pressure
- 2m temperature (t2m) [K] (for validation/gap-filling)
- Surface pressure (sp) [Pa]

**Data Format**: NetCDF (CF-compliant)

**Usage Strategy**:
- **Station-observed air temperature** from PF-AK (primary)
- **ERA5 gap-filling** for precipitation, radiation, vapor pressure
- Extract nearest grid point to each station
- Monthly aggregations (1997-2016)

**Access Method**:
1. **CDS API (cdsapi)**: Python client with API key
2. **Web Interface**: Manual download from CDS portal

**Setup Required**:
```bash
# Register at https://cds.climate.copernicus.eu/
# Get API key from https://cds.climate.copernicus.eu/api-how-to
# Create ~/.cdsapirc:
echo "url: https://cds.climate.copernicus.eu/api/v2" > ~/.cdsapirc
echo "key: YOUR_UID:YOUR_API_KEY" >> ~/.cdsapirc
chmod 600 ~/.cdsapirc

# Install Python client
pip install cdsapi
```

**License**: Copernicus License (free for non-commercial and commercial use with attribution)

---

## Secondary/Validation Data

### 3. Obu et al. (2018) Northern Hemisphere Permafrost Map

**Citation**: Obu, J., Westermann, S., Bartsch, A., Berdnikov, N., Christiansen, H. H., Dashtseren, A., et al. (2019). Northern Hemisphere permafrost map based on TTOP modelling for 2000–2016 at 1 km² scale. *Earth-Science Reviews*, 193, 299-316.

**DOI**: https://doi.org/10.1594/PANGAEA.888600

**Source**: PANGAEA Data Publisher

**Direct URL**: https://doi.org/10.1594/PANGAEA.888600

**Coverage**:
- **Spatial**: Northern Hemisphere to 25°N, 1 km² resolution
- **Temporal**: 2000-2016 average
- **Variables**:
  - Mean Annual Ground Temperature (MAGT) at top of permafrost [°C]
  - Permafrost probability (0-1 fraction)
  - Permafrost zonation (continuous, discontinuous, sporadic, isolated)
  - MAGT standard deviation [°C]

**Data Format**: GeoTIFF

**Method**: TTOP (Temperature at Top Of Permafrost) model driven by MODIS LST and ERA-Interim

**Validation**: RMSE ±2.0°C against GTN-P/TSP borehole data

**Use Case**: Phase 3 spatial benchmarking (gridded model output comparison)

**Access Method**: Direct download from PANGAEA

**License**: CC BY 4.0

---

### 4. SMAP L4 Surface and Root Zone Soil Moisture

**Citation**: Reichle, R. H., et al. (2019). Version 4 of the SMAP Level-4 Soil Moisture Algorithm and Data Product. *Journal of Advances in Modeling Earth Systems*, 11(10), 3106-3130.

**DOI**: https://doi.org/10.5067/60HB8VIP2T8W

**Source**: NASA NSIDC DAAC

**Direct URL**: https://nsidc.org/data/spl4smgp

**Coverage**:
- **Spatial**: Global land (excluding ice), 9 km resolution
- **Temporal**: April 2015 - present (3-hourly)
- **Variables**:
  - Surface soil moisture (0-5 cm) [m³/m³]
  - Root zone soil moisture (0-100 cm) [m³/m³]
  - Land surface temperature [K]

**Data Format**: HDF5

**Method**: Data assimilation (SMAP L-band radiometer + Catchment Land Surface Model)

**Use Case**: 
- Phase 3 spatial soil moisture validation
- 2015-2016 overlap with PF-AK benchmark period
- Extended validation beyond 2016

**Limitations**:
- Only 2015-present (limited overlap with 1997-2016 benchmark)
- Coarser resolution (9 km) than Obu temperature product (1 km)

**Access Method**:
1. NASA Earthdata Login required
2. Download via HTTPS, OPeNDAP, or earthaccess Python package
3. Alaska Satellite Facility (ASF) mirror

**License**: NASA Earth Science Data Policy (free and open)

---

## Model Code

### DVM-DOS-TEM (Dynamic Vegetation Model - Dynamic Organic Soil Terrestrial Ecosystem Model)

**Repository**: https://github.com/Elchin/dvm-dos-tem

**Branch**: `wetland/reburn-switch` (includes enthalpy thermal method)

**Description**: Process-based terrestrial ecosystem model for high-latitude regions

**Key Features**:
- Multi-layer soil thermal and hydrological dynamics
- Permafrost and active layer processes
- Vegetation dynamics (multiple PFTs)
- Organic soil representation
- Snow dynamics

**Language**: C++

**Dependencies**:
- NetCDF4
- Boost
- jsoncpp
- readline

**Build System**: CMake

**Documentation**: See repository README and docs/

**License**: GPLv3 (check repository for current license)

---

## Additional Resources

### GTN-P (Global Terrestrial Network for Permafrost)
- **URL**: https://gtnp.arcticportal.org/
- **Description**: International network of permafrost observations
- **Potential future use**: Deep borehole validation

### CALM (Circumpolar Active Layer Monitoring)
- **URL**: https://www2.gwu.edu/~calm/
- **Description**: Active layer thickness measurements
- **Potential future use**: Active layer benchmarking

### ESA CCI Soil Moisture
- **URL**: https://www.esa-soilmoisture-cci.org/
- **Coverage**: 1978-present, 0.25° resolution
- **Limitation**: Poor performance in permafrost regions (see benchmarking plan)
- **Use**: Summer-only supplementary validation

---

## Data Management

### Local Storage Structure

```
benchmarking/data/
├── observations/
│   ├── stations/alaska/          # PF-AK station data
│   └── synthesis/                # PF-AK aggregated files
├── climate/
│   └── ERA5/                     # ERA5 reanalysis
│       ├── deadhorse/
│       ├── toolik/
│       └── ...
└── gridded/
    ├── obu_magt/                 # Obu et al. 2018 MAGT grids
    └── smap/                     # SMAP soil moisture
```

### Archive and Reproducibility

- **Observation data**: Archived at original sources (Arctic Data Center, PANGAEA, NSIDC)
- **Processed inputs**: Archive on Zenodo or institutional repository
- **Version control**: All scripts in Git
- **Documentation**: This file and benchmarking plan

---

## Citation Guidance

When using this benchmarking framework, cite:

1. **PF-AK data**: Wang et al. (2018) - primary observational dataset
2. **ERA5**: Hersbach et al. (2020) - climate forcing
3. **Obu et al. (2019)**: If using spatial MAGT comparison
4. **SMAP**: Reichle et al. (2019) if using soil moisture validation
5. **DVM-DOS-TEM**: Model repository and relevant publications

---

Last updated: November 16, 2026
