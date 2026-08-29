# WIEMIP Post-Processing Pipeline

This directory contains the automated pipeline for downloading, merging, converting, and plotting the DVM-DOS-TEM output data for the WIEMIP project.

## 1. Preparing and Running the Pipeline

### Configuration
Before running, you should configure the pipeline by editing `config.sh`:
- **`VAR_NAMES=(...)`**: Add or remove the variables you want to process in this space-separated list.
- **`AGG_*`**: Set the time aggregation method (`mean` or `sum`) used when plotting spatial maps for each variable.
- **`WET_RUN` and `BASE_RUN`**: Ensure the GCS bucket links point to your intended simulation folders.
- **`GCM_PATTERN` and `EXPERIMENT`**: These metadata tags are used by the Python script to build the standardized WIEMIP output filenames (e.g., `DVMDOSTEM_CRUJRA_historical_...nc`).

### How to Run
Once your `config.sh` is configured, simply execute the `setup.sh` script:

```bash
cd ~/dvmdostem-wiemip/post-processing
time ./setup.sh
```

**What the script does automatically:**
1. Creates the necessary local output folders.
2. Uses `gsutil cp` to download the specific `VAR_NAMES` from your Google Cloud Storage buckets into `base_run/` and `wet_run/` local directories.
3. Activates the Python virtual environment (`~/venv/bin/activate`).
4. Executes the Python processing engine (`process_wiemip.py`), which generates the final `.nc` datasets and `.png` figures.

## 2. Output Paths and Data Structure

By default, all downloaded data, processed output, and generated figures are routed to the external mounted disk.

**Default Output Path:** `/mnt/disks/wiemip-data/output`

You can change this target directory by opening the `setup.sh` file and editing the `OUTPUT_DIR` variable near the top of the file:
```bash
# Target directories expected by the postprocessing script
OUTPUT_DIR="/mnt/disks/wiemip-data/output"
```

Inside this directory, the following structure will be created:
- `base_run/`: Holds the raw `.nc` files downloaded from the BASE_RUN bucket.
- `wet_run/`: Holds the raw `.nc` files downloaded from the WET_RUN bucket.
- `wiemip_output/`: Contains the final, merged, and unit-converted NetCDF datasets using the standardized WIEMIP naming convention.
- `figures/`: Contains the generated 3x3 summary diagnostic plots (`.png`), and additional depth profile plots for multi-layer variables.

## 3. The Merging Equation

For variables marked with a `1` in the "merge" column of `output_conversion_table.csv`, the pipeline blends the data from the `BASE_RUN` and `WET_RUN` datasets based on the fractional wetland vegetation coverage.

The coverage map is automatically loaded from `vegetation1_stable.nc` (`veg_pct_cov`). 
The fractional coverage is calculated as `veg_cov_fraction = veg_pct_cov * 0.01`.

For valid, common grid cells where both `wet` and `base` data exist, the equation applied is:
```
Merged Value = (Base_Data * veg_cov_fraction) + (Wet_Data * (1.0 - veg_cov_fraction))
```

*Note: Missing ocean cells (e.g., `_FillValue = -9999.0` or `NaN`) are carefully tracked and preserved throughout the calculations so they remain fully transparent in the spatial map plots.*

## 4. Handling 4-Dimensional Variables

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