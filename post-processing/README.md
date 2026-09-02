# WIEMIP Post-Processing Pipeline

This directory contains the automated pipeline for downloading, merging, converting, and plotting the DVM-DOS-TEM output data for the WIEMIP project.

## 1. Preparing and Running the Pipeline

### Configuration
Before running, you should configure the pipeline by editing `config.sh`:
- **`PROCESS_FROM_LIST`**: Set to `"true"` to enable batch processing of multiple cases using CSV lists, or `"false"` to run a single case.
- **`VAR_NAMES=(...)`**: Add or remove the variables you want to process in this space-separated list.
- **`AGG_*`**: Set the time aggregation method (`mean` or `sum`) used when plotting spatial maps for each variable.
- **`WET_RUN` and `BASE_RUN`**: (Single-case mode only) Ensure the GCS bucket links point to your intended simulation folders.
- **`GCM_PATTERN` and `EXPERIMENT`**: These metadata tags are used by the Python script to build the standardized WIEMIP output filenames (e.g., `DVMDOSTEM_CRUJRA_historical_...nc`).

### Batch Processing Mode
When `PROCESS_FROM_LIST="true"`, the pipeline dynamically processes multiple cases based on two CSV files:
1. **`path_gs_merge.csv`**: Maps a specific `run_case` to its Google Cloud Storage `location`.
2. **`processing_combine_list.csv`**: Defines the cases to process. For each row, it specifies the `WIEMIP_Experiment_Prefix`, the `Base_Run`, the `Wet_Run`, and a boolean `Combine` flag. 
   - The script automatically creates isolated output directories for each prefix.
   - It downloads the necessary files via `gsutil`.
   - If `Combine` is `FALSE`, the script overrides the merging logic and processes the base run only.

### How to Run
Once your `config.sh` is configured, simply execute the `setup.sh` script:

```bash
cd ~/dvmdostem-wiemip/post-processing
time ./setup.sh
```

**What the script does automatically:**
1. Creates the necessary local output folders (dynamically per case if in batch mode).
2. Uses `gsutil cp` to download the specific `VAR_NAMES` from your Google Cloud Storage buckets into `base_run/` and `wet_run/` local directories.
3. Activates the Python virtual environment (`~/venv/bin/activate`).
4. Executes the Python processing engine (`process_wiemip.py`), which generates the final `.nc` datasets and `.png` figures.

## 2. Output Paths and Data Structure

By default, all downloaded data, processed output, and generated figures are routed to the external mounted disk.

**Default Output Path:** `/mnt/disks/wiemip-data/output`
*(In batch mode, subdirectories are created dynamically based on the `WIEMIP_Experiment_Prefix`)*

You can change this target directory by opening the `setup.sh` file and editing the `OUTPUT_DIR` variable near the top of the file.

Inside this directory, the following structure will be created:
- `base_run/`: Holds the raw `.nc` files downloaded from the BASE_RUN bucket.
- `wet_run/`: Holds the raw `.nc` files downloaded from the WET_RUN bucket.
- `wiemip_output/`: Contains the final, merged, and unit-converted NetCDF datasets using the standardized WIEMIP naming convention.
- `figures/`: Contains the generated 3x3 summary diagnostic plots (`.png`), and additional depth profile plots for multi-layer variables.

## 3. Variable Classes and Math Operations

The `output_conversion_table.csv` drives the processing logic and supports five `VarClass` types:
- **`1_Units_only`**: Converts units while preserving the file structure.
- **`2_Sum_by_PFT`**: Aggregates data across Plant Functional Types (PFTs).
- **`3_Sum_by_layer`**: Aggregates data across soil layers.
- **`4_Math`**: Applies mathematical operations (Add, Subtract, Multiply, Divide) between two previously processed WIEMIP variables.
- **`5_Ignore_for_now`**: Skips processing for the variable.

## 4. The Merging Equation

For variables marked with a `1` in the "merge" column of `output_conversion_table.csv` (and when `Combine` is TRUE in batch mode), the pipeline blends the data from the `BASE_RUN` and `WET_RUN` datasets based on the fractional wetland vegetation coverage.

The coverage map is automatically loaded from `wetland.nc` (`veg_pct_cov`). 
The fractional coverage is calculated as `veg_cov_fraction = veg_pct_cov * 0.01`.

For valid, common grid cells where both `wet` and `base` data exist, the equation applied is:
```
Merged Value = (Base_Data * veg_cov_fraction) + (Wet_Data * (1.0 - veg_cov_fraction))
```

*Note: Missing ocean cells (e.g., `_FillValue = -9999.0` or `NaN`) are carefully tracked and preserved throughout the calculations so they remain fully transparent in the spatial map plots.*

## 5. Handling 4-Dimensional Variables

4D variables (Time, Layer, Y, X) such as `TLAYER`, `VWCLAYER`, and `RHSOM` are extremely massive files (e.g., up to ~5GB compressed per variable) and require specialized handling to prevent Out-Of-Memory (OOM) crashes in Python.

**Memory-Optimized Streaming:**
Instead of loading the entire dataset into memory simultaneously (which would cause a Dask graph explosion consuming 50+ GB of RAM), `process_wiemip.py` dynamically probes the dataset's native internal time-chunking layout. It processes the dataset using a highly optimized pure-`netCDF4` memory stream:
1. It reads native time chunks directly from the disk into memory (typically 120 time-steps, equal to 10 years of data, peaking at a very safe ~1.5 to 2.5 GB of RAM).
2. It strictly enforces `float32` typing and applies the merging equations and unit conversions entirely in-place.
3. It immediately syncs the processed block directly back to the final output file on the disk and forcefully purges memory before loading the next chunk.

**Specialized Plotting:**
For 4-dimensional data, the script provides advanced plotting logic:
- The 3x3 summary figures average the timeseries plot across the **top layer [0]** and **bottom layer [N]** to give a bound representation of the soil profile.
- A secondary diagnostic plot (`*_depth_climatology.png`) is exclusively generated for 4D datasets. It collapses the geographic dimensions to show a full monthly Climatology Profile heatmap (Time vs. Depth) and an overall statistical bounding profile (Min, Mean, Max values across depths).