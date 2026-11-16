# PF-AK v0.1 Observational Data

## Dataset Description

**PF-AK v0.1**: Alaska Permafrost Synthesis Dataset (Wang et al., 2018)

**Citation**: Wang, K., Jafarov, E., Overeem, I., Romanovsky, V., Schaefer, K., Clow, G., Urban, F., Cable, W., Piper, M., Schwalm, C., Zhang, T., Kholodov, A., Sousanes, P., Loso, M., and Hill, K. (2018). A synthesis dataset of permafrost-affected soil thermal conditions for Alaska, USA. *Earth System Science Data*, 10(4), 2311-2328. https://doi.org/10.18739/A2KG55

---

## Files

### Full Dataset
- `PF_AK_v0.1_b4e8.csv` - Processed dataset (954 KB, 9,733 rows) **[PRIMARY]**
- `PF_AK_v0.1_058a.csv` - Duplicate copy
- `PF_AK_v0.1_raw_4594.csv` - Raw dataset (803 KB, 6,489 rows)
- `PF_AK_v0.1_raw_90a9.csv` - Duplicate copy

### Station-Specific Extracts

**Phase 1 Prototype Stations**:
- `stations/deadhorse/pfak_deadhorse.csv` (240 months, 1997-2016)
- `stations/imnaviat/pfak_imnaviat.csv` (132 months, 2006-2016)
- `stations/smith_lake_1/pfak_smith_lake_1.csv` (240 months, 1997-2016)

---

## Data Structure

### Columns (14 total)

| Column | Description | Units | Notes |
|--------|-------------|-------|-------|
| Name | Station name | string | 72 unique stations |
| Code | Station code | integer | 5-digit code |
| Lat | Latitude | degrees N | 60.9-71.3°N range |
| Lon | Longitude | degrees W | Negative values (141.8-164.9°W) |
| Year | Year | integer | 1997-2016 |
| Month | Month | string | "Jan", "Feb", ..., "Dec" |
| Snod | Snow depth | cm (TBD) | Missing: -999.99 |
| Tair | Air temperature | °C | Missing: -999.99 |
| Ts100cm | Ground temperature 100cm | °C | Missing: -999.99 |
| Ts25cm | Ground temperature 25cm | °C | Missing: -999.99 |
| Ts50cm | Ground temperature 50cm | °C | Missing: -999.99 |
| Ts75cm | Ground temperature 75cm | °C | Missing: -999.99 |
| Tsur | Surface temperature | °C | Missing: -999.99 |
| VWC_top | Soil moisture (VWC) | m³/m³ | Missing: -999.99 |

**Note**: Depths are 25, 50, 75, 100 cm (equivalent to 0.25, 0.50, 0.75, 1.00 m)

---

## Coverage Summary

**Total**: 72 stations, 9,732 monthly observations  
**Period**: 1997-2016 (20 years)  
**Region**: Alaska permafrost zones

### Networks
- **GI-UAF** (Geophysical Institute, University of Alaska Fairbanks): 27 sites
- **USGS** (U.S. Geological Survey): 17 sites
- **NPS** (National Park Service): 28 sites

---

## Phase 1 Prototype Stations

### 1. Deadhorse (Code: 88005)
- **Location**: 70.161°N, 148.465°W, 10m elevation
- **Ecosystem**: North Slope tundra, Arctic Coastal Plain
- **Permafrost**: Continuous (>90%)
- **Period**: 1997-2016 (240 months)
- **Data availability**:
  - Air temperature: 40.4%
  - Snow depth: 15.8%
  - Ground temp (25-75cm): 53.3%
  - Soil moisture: 50.8%

### 2. Imnaviat (Code: 88013) 
- **Location**: 68.640°N, 149.352°W, 930m elevation
- **Ecosystem**: Arctic foothills tundra, Brooks Range
- **Permafrost**: Continuous
- **Period**: 2006-2016 (132 months)
- **Note**: Closest station to Toolik Lake coordinates (68.625°N, 149.597°W)
- **Data availability**:
  - Air temperature: 79.5% ✓
  - Snow depth: 25.0%
  - Ground temp (25-75cm): 86.4% ✓✓
  - Soil moisture: 0% (not available)

### 3. Smith Lake 1 (Code: 88020)
- **Location**: 64.869°N, 147.861°W, 700m elevation
- **Ecosystem**: Interior Alaska boreal forest
- **Permafrost**: Discontinuous (50-90%)
- **Period**: 1997-2016 (240 months)
- **Data availability**:
  - Air temperature: 48.3%
  - Snow depth: 19.6%
  - Ground temp (25-100cm): 48.3%
  - Soil moisture: 83.8% ✓✓

---

## Data Quality

### Processing (Wang et al. 2018)
- ✓ Harmonized across 3 networks
- ✓ Frost heave corrections applied
- ✓ Quality controlled
- ✓ Monthly aggregations
- ✓ Standardized depths

### Known Limitations
- Missing data varies by station/variable (40-85% complete)
- Limited 100cm depth data (many stations have 0%)
- Sparse snow depth observations (15-25%)
- Soil moisture only available at subset of stations

---

## Usage Notes

### For Model Input Preparation
1. **Use processed dataset**: `PF_AK_v0.1_b4e8.csv`
2. **Handle missing values**: Replace -999.99 with appropriate fill or gap-filling strategy
3. **Time format**: Convert "Month" string to numeric (1-12) or datetime
4. **Coordinate convention**: Longitude is negative (western hemisphere)
5. **Depth units**: 25, 50, 75, 100 cm = 0.25, 0.50, 0.75, 1.00 m

### For Model Validation
1. **Calculate metrics only for non-missing months**
2. **Primary depths**: 25, 50, 75 cm (best coverage)
3. **Secondary depth**: 100 cm (limited, station-dependent)
4. **Validation period**: 1997-2016 (observations available)
5. **Simulation period**: 1900-2024 (model runs full period)

---

## Analysis Scripts

- `../../scripts/download_data/analyze_pfak.sh` - Dataset analysis (bash)
- `../../scripts/download_data/analyze_pfak.py` - Dataset analysis (Python, requires pandas)

**Run analysis**:
```bash
cd /agent/repos/dvmdostem-wiemip/benchmarking/data/observations
bash ../../scripts/download_data/analyze_pfak.sh PF_AK_v0.1_b4e8.csv
```

---

## References

**Primary**:
Wang et al. (2018), *Earth System Science Data*, 10(4), 2311-2328  
DOI: https://doi.org/10.18739/A2KG55

**Dataset**: Arctic Data Center  
https://arcticdata.io/catalog/view/doi:10.18739/A2KG55

---

**Last Updated**: November 16, 2026  
**Status**: Dataset received, analyzed, and extracted for Phase 1 prototype stations
